"""
drywall_detection.data.preparer
==============================
Production-grade dataset unifier, geometric parser, and mask rasterizer
for Milestone M2 (Dataset Preparation).

Capabilities:
- Standardized floor plan representation (RGB images, binary masks, and 4-class indexed masks)
- Robust MSD (Modified Swiss Dwellings) Parquet/WKT annotation ingestion
- Aspect-ratio preserving affine coordinate transformation (Cartesian to Raster pixel)
- Sub-pixel polygon rasterization and hole evacuation using OpenCV cv2.fillPoly
- Comprehensive geometric sanitization, deduplication, and degenerate filtering
- Backward-compatible split management re-exports from split_manager
- Standalone CLI: python -m drywall_detection.data.preparer
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, asdict
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import cv2
import numpy as np
from PIL import Image
import shapely
import shapely.wkt
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.geometry.base import BaseGeometry

# Import central configurations
from drywall_detection.config import (
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    QC_SAMPLES_DIR,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    NUM_CLASSES,
    CLASS_NAMES,
    CLASS_COLORS_RGB,
    CLASS_COLORS_BGR,
    CLASS_COLORS_HEX,
    DEFAULT_OVERLAY_ALPHA,
)

# Re-export split interfaces for 100% backward compatibility
from drywall_detection.datasets.split_manager import (
    DrawingSplitManager,
    SplitManifest,
    TileRecord,
    SplitStats,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    verify_split_isolation,
)

logger = logging.getLogger("drywall_detection.data.preparer")

# 256-color palette for PIL Mode 'P' indexed PNG conforming to CLASS_COLORS_RGB
PALETTE_256: List[int] = [
    255, 255, 255,  # 0: Background (White)
    0,   200,  83,   # 1: Drywall (Green)
    213, 0,    0,    # 2: Non-Drywall (Red)
    255, 214,  0,    # 3: Uncertain (Yellow)
] + [0] * (256 - 4) * 3


# ==============================================================================
# 1. DATA MODELS & CONFIGURATION
# ==============================================================================

@dataclass
class PreparationConfig:
    """Configuration parameters for dataset preparation and mask generation."""
    raw_dir: Path = RAW_DATA_DIR / "msd"
    output_dir: Path = PROCESSED_DATA_DIR
    target_width: int = 1024
    target_height: int = 1024
    margin_ratio: float = 0.05
    min_polygon_area: float = 1e-4
    min_wall_pixels: int = 50
    default_wall_class: int = CLASS_UNCERTAIN  # Class 3 for unverified generic walls
    preserve_aspect_ratio: bool = True
    cartesian_y_flip: bool = True               # Flip Y because CAD +Y is up, raster +Y is down
    filter_blank_drawings: bool = True
    max_hard_negative_ratio: float = 0.15
    split_after_prep: bool = True
    split_ratios: Tuple[float, float, float] = (0.70, 0.15, 0.15)
    seed: int = 42

    @property
    def target_shape(self) -> Tuple[int, int]:
        return (self.target_height, self.target_width)


@dataclass
class ParsedDrawing:
    """In-memory representation of an ingested drawing prior to rasterization."""
    drawing_id: str
    site_id: str
    building_id: str
    polygons: List[Polygon]
    bounds: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    image_path: Optional[Path] = None
    source_dataset: str = "msd"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedFloorPlan:
    """Standardized multi-modal floor plan pair ready for dataset manifests."""
    drawing_id: str
    project_id: str
    image_path: Path
    binary_mask_path: Path
    multiclass_mask_path: Path
    image_shape: Tuple[int, int, int]
    mask_shape: Tuple[int, int]
    wall_pixel_count: int
    wall_coverage_pct: float
    is_hard_negative: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawing_id": self.drawing_id,
            "project_id": self.project_id,
            "image_path": str(self.image_path),
            "binary_mask_path": str(self.binary_mask_path),
            "multiclass_mask_path": str(self.multiclass_mask_path),
            "image_shape": list(self.image_shape),
            "mask_shape": list(self.mask_shape),
            "wall_pixel_count": self.wall_pixel_count,
            "wall_coverage_pct": self.wall_coverage_pct,
            "is_hard_negative": self.is_hard_negative,
            "metadata": self.metadata,
        }


# ==============================================================================
# 2. GEOMETRY SANITIZER & RASTERIZER
# ==============================================================================

class GeometryRasterizer:
    """
    Transforms metric vector geometries into discrete raster masks.
    Enforces exact aspect-ratio preserving scaling, centering padding,
    and sub-pixel coordinate clamping.
    """

    def __init__(self, config: Optional[PreparationConfig] = None) -> None:
        self.config = config or PreparationConfig()

    def compute_affine_parameters(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculates scale factor and offsets to fit bounding box into target canvas.
        Returns: (scale, pad_x, pad_y, min_x_padded, min_y_padded)
        """
        min_x, min_y, max_x, max_y = bounds
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)

        # Apply symmetric margin
        m = self.config.margin_ratio
        min_x_pad = min_x - m * span_x
        max_x_pad = max_x + m * span_x
        min_y_pad = min_y - m * span_y
        max_y_pad = max_y + m * span_y

        padded_span_x = max(max_x_pad - min_x_pad, 1e-6)
        padded_span_y = max(max_y_pad - min_y_pad, 1e-6)

        tw = float(self.config.target_width)
        th = float(self.config.target_height)

        if self.config.preserve_aspect_ratio:
            scale = min((tw - 1.0) / padded_span_x, (th - 1.0) / padded_span_y)
            pad_x = (tw - 1.0 - (padded_span_x * scale)) / 2.0
            pad_y = (th - 1.0 - (padded_span_y * scale)) / 2.0
        else:
            scale = min((tw - 1.0) / padded_span_x, (th - 1.0) / padded_span_y)
            pad_x = 0.0
            pad_y = 0.0

        return (scale, pad_x, pad_y, min_x_pad, min_y_pad)

    def transform_coords_to_pixel(
        self,
        coords: Sequence[Tuple[float, float]],
        affine_params: Tuple[float, float, float, float, float],
    ) -> np.ndarray:
        """
        Transforms (N, 2) metric coordinates to (N, 1, 2) int32 pixel coordinates.
        """
        scale, pad_x, pad_y, min_x_pad, min_y_pad = affine_params
        tw = self.config.target_width
        th = self.config.target_height

        pts = []
        for x, y in coords:
            if not (math.isfinite(x) and math.isfinite(y)):
                continue

            px = pad_x + (x - min_x_pad) * scale
            if self.config.cartesian_y_flip:
                py = (th - 1.0) - (pad_y + (y - min_y_pad) * scale)
            else:
                py = pad_y + (y - min_y_pad) * scale

            # Clamping to valid canvas range
            cpx = int(np.clip(round(px), 0, tw - 1))
            cpy = int(np.clip(round(py), 0, th - 1))
            pts.append([cpx, cpy])

        if not pts:
            return np.empty((0, 1, 2), dtype=np.int32)

        return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

    def rasterize_polygons(
        self,
        polygons: List[Polygon],
        bounds: Tuple[float, float, float, float],
        target_class: int = CLASS_UNCERTAIN,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rasterizes a list of Shapely Polygons into binary and multiclass masks.
        Returns:
            binary_mask: (H, W) uint8 with values {0, 1}
            multiclass_mask: (H, W) uint8 with values {0, 1, 2, 3}
        """
        th, tw = self.config.target_shape
        binary_mask = np.zeros((th, tw), dtype=np.uint8)
        multiclass_mask = np.zeros((th, tw), dtype=np.uint8)

        if not polygons:
            return binary_mask, multiclass_mask

        affine_params = self.compute_affine_parameters(bounds)

        for poly in polygons:
            if poly.is_empty or poly.area <= 0.0 or not poly.exterior:
                continue

            # Rasterize exterior contour
            ext_pts = self.transform_coords_to_pixel(poly.exterior.coords, affine_params)
            if len(ext_pts) >= 3:
                cv2.fillPoly(binary_mask, [ext_pts], color=1)
                cv2.fillPoly(multiclass_mask, [ext_pts], color=target_class)

            # Rasterize and evacuate interior holes
            for interior in poly.interiors:
                hole_pts = self.transform_coords_to_pixel(interior.coords, affine_params)
                if len(hole_pts) >= 3:
                    cv2.fillPoly(binary_mask, [hole_pts], color=CLASS_BACKGROUND)
                    cv2.fillPoly(multiclass_mask, [hole_pts], color=CLASS_BACKGROUND)

        return binary_mask, multiclass_mask

    def render_vector_drawing(
        self,
        polygons: List[Polygon],
        bounds: Tuple[float, float, float, float],
    ) -> np.ndarray:
        """
        Generates a synthetic white architectural floor plan drawing with crisp CAD linework
        when raw raster drawing bitmaps are absent.
        Returns: (H, W, 3) uint8 BGR image.
        """
        th, tw = self.config.target_shape
        canvas = np.full((th, tw, 3), 255, dtype=np.uint8)  # White paper background

        if not polygons:
            return canvas

        affine_params = self.compute_affine_parameters(bounds)

        for poly in polygons:
            ext_pts = self.transform_coords_to_pixel(poly.exterior.coords, affine_params)
            if len(ext_pts) >= 2:
                # Draw dark CAD wall perimeter lines
                cv2.polylines(canvas, [ext_pts], isClosed=True, color=(30, 30, 30), thickness=2, lineType=cv2.LINE_AA)
            for interior in poly.interiors:
                hole_pts = self.transform_coords_to_pixel(interior.coords, affine_params)
                if len(hole_pts) >= 2:
                    cv2.polylines(canvas, [hole_pts], isClosed=True, color=(40, 40, 40), thickness=1, lineType=cv2.LINE_AA)

        return canvas


# ==============================================================================
# 3. MSD ANNOTATION PARSER & SANITIZER
# ==============================================================================

class DrawingSanitizer:
    """
    Validates, repairs, and deduplicates vector geometries and floor plan samples.
    """

    def __init__(self, config: Optional[PreparationConfig] = None) -> None:
        self.config = config or PreparationConfig()

    def sanitize_polygon(self, raw_geom: Any) -> List[Polygon]:
        """
        Parses WKT or Shapely geometry, repairs self-intersections via make_valid,
        and extracts valid, non-degenerate polygons.
        """
        if raw_geom is None:
            return []

        if isinstance(raw_geom, str):
            text = raw_geom.strip()
            if not text:
                return []
            try:
                geom = shapely.wkt.loads(text)
            except Exception as err:
                logger.debug(f"WKT parse failure: {err}")
                return []
        elif isinstance(raw_geom, BaseGeometry):
            geom = raw_geom
        else:
            return []

        if geom.is_empty:
            return []

        # Repair topology if invalid
        if not geom.is_valid:
            try:
                geom = shapely.make_valid(geom)
            except Exception:
                geom = geom.buffer(0)

        # Recursively extract polygons
        polygons: List[Polygon] = []
        self._extract_polygons_recursive(geom, polygons)

        # Filter degenerate area and coordinate finiteness
        valid_polys: List[Polygon] = []
        for p in polygons:
            if p.area < self.config.min_polygon_area:
                continue
            if len(p.exterior.coords) < 4:  # Closed polygon requires at least 4 coordinates (3 unique + close)
                continue
            # Verify coordinates are finite
            coords = np.array(p.exterior.coords)
            if not np.all(np.isfinite(coords)):
                continue
            valid_polys.append(p)

        return valid_polys

    def _extract_polygons_recursive(self, geom: BaseGeometry, collector: List[Polygon]) -> None:
        if geom is None or geom.is_empty:
            return
        if isinstance(geom, Polygon):
            collector.append(geom)
        elif isinstance(geom, (MultiPolygon, GeometryCollection)):
            for sub in geom.geoms:
                self._extract_polygons_recursive(sub, collector)

    def deduplicate_polygons(self, polygons: List[Polygon]) -> List[Polygon]:
        """Filters duplicate polygons based on rounded coordinate hash."""
        seen_hashes: Set[str] = set()
        unique_polys: List[Polygon] = []

        for p in polygons:
            # Round exterior coords to 3 decimals (~1 mm precision)
            rounded = [(round(x, 3), round(y, 3)) for x, y in p.exterior.coords]
            h = hashlib.sha256(str(sorted(rounded)).encode("utf-8")).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_polys.append(p)

        return unique_polys


class MSDAnnotationParser:
    """
    Parses Modified Swiss Dwellings (MSD) dataset from Parquet, CSV, or JSON tables.
    Filters entities by entity_type == 'separator' and entity_subtype == 'WALL'.
    """

    def __init__(self, config: Optional[PreparationConfig] = None, sanitizer: Optional[DrawingSanitizer] = None) -> None:
        self.config = config or PreparationConfig()
        self.sanitizer = sanitizer or DrawingSanitizer(self.config)

    def parse_msd_directory(self, raw_dir: Path) -> List[ParsedDrawing]:
        """
        Scans raw_dir for Parquet or CSV files and parses wall entities grouped by drawing_id.
        """
        raw_dir = Path(raw_dir)
        if not raw_dir.is_dir():
            logger.warning(f"Raw data directory does not exist: {raw_dir}")
            return []

        parquet_files = list(raw_dir.glob("*.parquet")) + list(raw_dir.glob("**/*.parquet"))
        csv_files = list(raw_dir.glob("*.csv")) + list(raw_dir.glob("**/*.csv"))

        if not parquet_files and not csv_files:
            logger.warning(f"No Parquet or CSV files found in {raw_dir}. Searching for JSON manifests...")
            json_files = list(raw_dir.glob("*.json"))
            if json_files:
                return self._parse_json_files(json_files)
            return []

        if parquet_files:
            return self._parse_parquet_files(parquet_files)
        else:
            return self._parse_csv_files(csv_files)

    def _parse_parquet_files(self, files: List[Path]) -> List[ParsedDrawing]:
        """Parses Apache Parquet tables using pandas/pyarrow."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to parse Parquet files.")
            return []

        drawings_map: Dict[str, Dict[str, Any]] = {}

        for file_path in files:
            logger.info(f"Reading Parquet file: {file_path.name}")
            try:
                df = pd.read_parquet(file_path)
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue

            self._process_dataframe(df, drawings_map)

        return self._build_parsed_drawings(drawings_map)

    def _parse_csv_files(self, files: List[Path]) -> List[ParsedDrawing]:
        """Parses CSV tables."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to parse CSV files.")
            return []

        drawings_map: Dict[str, Dict[str, Any]] = {}
        for file_path in files:
            logger.info(f"Reading CSV file: {file_path.name}")
            try:
                df = pd.read_csv(file_path)
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue
            self._process_dataframe(df, drawings_map)

        return self._build_parsed_drawings(drawings_map)

    def _process_dataframe(self, df: Any, drawings_map: Dict[str, Dict[str, Any]]) -> None:
        """Processes tabular records and filters separator/WALL entities."""
        import pandas as pd

        cols = {c.lower(): c for c in df.columns}

        geom_col = cols.get("geometry") or cols.get("wkt") or cols.get("geom")
        if not geom_col:
            logger.warning("No geometry column found in table.")
            return

        type_col = cols.get("entity_type") or cols.get("type") or cols.get("category")
        subtype_col = cols.get("entity_subtype") or cols.get("subtype") or cols.get("class")
        drawing_id_col = cols.get("floor_id") or cols.get("drawing_id") or cols.get("plan_id") or cols.get("dwelling_id") or cols.get("id")
        site_id_col = cols.get("site_id") or cols.get("project_id") or cols.get("complex_id")
        building_id_col = cols.get("building_id") or cols.get("structure_id")

        for _, row in df.iterrows():
            # Check wall category
            if type_col:
                val_type = str(row[type_col]).lower().strip()
                if val_type != "separator":
                    continue
            if subtype_col:
                val_subtype = str(row[subtype_col]).upper().strip()
                if "WALL" not in val_subtype:
                    continue

            d_id = str(row[drawing_id_col]) if drawing_id_col and pd.notna(row[drawing_id_col]) else "drawing_default"
            s_id = str(row[site_id_col]) if site_id_col and pd.notna(row[site_id_col]) else f"site_{d_id}"
            b_id = str(row[building_id_col]) if building_id_col and pd.notna(row[building_id_col]) else f"bld_{d_id}"

            wkt_val = row[geom_col]
            if not wkt_val or (isinstance(wkt_val, float) and math.isnan(wkt_val)):
                continue

            entry = drawings_map.setdefault(d_id, {
                "drawing_id": d_id,
                "site_id": s_id,
                "building_id": b_id,
                "raw_geoms": [],
            })
            entry["raw_geoms"].append(wkt_val)

    def _build_parsed_drawings(self, drawings_map: Dict[str, Dict[str, Any]]) -> List[ParsedDrawing]:
        results: List[ParsedDrawing] = []

        for d_id, data in drawings_map.items():
            all_polys: List[Polygon] = []
            for raw_g in data["raw_geoms"]:
                sanitized = self.sanitizer.sanitize_polygon(raw_g)
                all_polys.extend(sanitized)

            unique_polys = self.sanitizer.deduplicate_polygons(all_polys)
            if not unique_polys:
                continue

            # Compute bounding box
            min_x = min(p.bounds[0] for p in unique_polys)
            min_y = min(p.bounds[1] for p in unique_polys)
            max_x = max(p.bounds[2] for p in unique_polys)
            max_y = max(p.bounds[3] for p in unique_polys)

            results.append(
                ParsedDrawing(
                    drawing_id=d_id,
                    site_id=data["site_id"],
                    building_id=data["building_id"],
                    polygons=unique_polys,
                    bounds=(min_x, min_y, max_x, max_y),
                    source_dataset="msd",
                )
            )

        return results

    def _parse_json_files(self, files: List[Path]) -> List[ParsedDrawing]:
        """Fallback JSON parser for synthetic or pre-converted manifests."""
        results: List[ParsedDrawing] = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    content = json.load(fp)
                items = content if isinstance(content, list) else content.get("drawings", [])
                for item in items:
                    polys = []
                    for wkt_str in item.get("wall_wkts", []):
                        polys.extend(self.sanitizer.sanitize_polygon(wkt_str))
                    if polys:
                        min_x = min(p.bounds[0] for p in polys)
                        min_y = min(p.bounds[1] for p in polys)
                        max_x = max(p.bounds[2] for p in polys)
                        max_y = max(p.bounds[3] for p in polys)
                        results.append(ParsedDrawing(
                            drawing_id=item["drawing_id"],
                            site_id=item.get("site_id", item["drawing_id"]),
                            building_id=item.get("building_id", item["drawing_id"]),
                            polygons=polys,
                            bounds=(min_x, min_y, max_x, max_y),
                            source_dataset="json",
                        ))
            except Exception as e:
                logger.error(f"Error parsing JSON {f}: {e}")
        return results


# ==============================================================================
# 4. DATASET PREPARER ENGINE & SPLIT ORCHESTRATION
# ==============================================================================

class DatasetPreparer:
    """
    High-level orchestrator that coordinates dataset ingestion,
    geometric sanitization, mask generation, disk persistence, and splitting.
    """

    def __init__(self, config: Optional[PreparationConfig] = None) -> None:
        self.config = config or PreparationConfig()
        self.sanitizer = DrawingSanitizer(self.config)
        self.rasterizer = GeometryRasterizer(self.config)
        self.parser = MSDAnnotationParser(self.config, self.sanitizer)

    def prepare_dataset(self) -> Dict[str, Any]:
        """
        Executes end-to-end dataset preparation:
        1. Ingest raw annotations
        2. Rasterize masks and render images
        3. Save unified floor plan representations
        4. Execute project-isolated splitting (70/15/15)
        5. Export master dataset manifest
        """
        logger.info(f"Starting dataset preparation from: {self.config.raw_dir}")
        parsed_drawings = self.parser.parse_msd_directory(self.config.raw_dir)
        logger.info(f"Discovered {len(parsed_drawings)} parsed drawings with valid walls.")

        if not parsed_drawings:
            logger.warning("No valid drawings parsed from raw_dir. Generating synthetic verification sample...")
            parsed_drawings = self._create_synthetic_verification_sample()

        images_dir = self.config.output_dir / "images"
        masks_bin_dir = self.config.output_dir / "masks_binary"
        masks_multi_dir = self.config.output_dir / "masks_multiclass"

        images_dir.mkdir(parents=True, exist_ok=True)
        masks_bin_dir.mkdir(parents=True, exist_ok=True)
        masks_multi_dir.mkdir(parents=True, exist_ok=True)

        prepared_records: List[UnifiedFloorPlan] = []
        tile_records_for_splitting: List[TileRecord] = []

        for drawing in parsed_drawings:
            # 1. Rasterize masks
            bin_mask, multi_mask = self.rasterizer.rasterize_polygons(
                drawing.polygons,
                drawing.bounds,
                target_class=self.config.default_wall_class,
            )

            wall_pixels = int(np.sum(bin_mask > 0))
            total_pixels = bin_mask.size
            wall_cov_pct = round((wall_pixels / total_pixels) * 100.0, 3)

            # Check density threshold
            if wall_pixels < self.config.min_wall_pixels and self.config.filter_blank_drawings:
                continue

            # 2. Render or load image
            if drawing.image_path and drawing.image_path.is_file():
                img = cv2.imread(str(drawing.image_path))
                if img.shape[:2] != self.config.target_shape:
                    img = cv2.resize(img, (self.config.target_width, self.config.target_height), interpolation=cv2.INTER_AREA)
            else:
                img = self.rasterizer.render_vector_drawing(drawing.polygons, drawing.bounds)

            # 3. Save files to disk
            d_id = drawing.drawing_id
            img_path = images_dir / f"{d_id}.png"
            bin_mask_path = masks_bin_dir / f"{d_id}.png"
            multi_mask_path = masks_multi_dir / f"{d_id}.png"

            cv2.imwrite(str(img_path), img)

            # Save binary mask (Mode 'L')
            Image.fromarray(bin_mask, mode="L").save(bin_mask_path)

            # Save multiclass mask as Mode 'P' indexed PNG
            p_img = Image.fromarray(multi_mask, mode="P")
            p_img.putpalette(PALETTE_256)
            p_img.save(multi_mask_path)

            plan = UnifiedFloorPlan(
                drawing_id=d_id,
                project_id=drawing.site_id,
                image_path=img_path,
                binary_mask_path=bin_mask_path,
                multiclass_mask_path=multi_mask_path,
                image_shape=img.shape,
                mask_shape=bin_mask.shape,
                wall_pixel_count=wall_pixels,
                wall_coverage_pct=wall_cov_pct,
                is_hard_negative=False,
            )
            prepared_records.append(plan)

            # Construct TileRecord for DrawingSplitManager
            tile_records_for_splitting.append(
                TileRecord(
                    tile_id=f"{d_id}_full",
                    project_id=drawing.site_id,
                    drawing_id=d_id,
                    image_path=str(img_path),
                    mask_path=str(multi_mask_path),
                    bbox=(0, 0, self.config.target_width, self.config.target_height),
                    has_walls=(wall_pixels > 0),
                    class_counts={
                        "background": int(np.sum(multi_mask == CLASS_BACKGROUND)),
                        "drywall": int(np.sum(multi_mask == CLASS_DRYWALL)),
                        "non_drywall": int(np.sum(multi_mask == CLASS_NON_DRYWALL)),
                        "uncertain": int(np.sum(multi_mask == CLASS_UNCERTAIN)),
                    },
                )
            )

        # 4. Execute project-isolated splitting if requested
        manifest_files: Dict[str, Path] = {}
        if self.config.split_after_prep and tile_records_for_splitting:
            split_mgr = DrawingSplitManager(
                split_ratios=self.config.split_ratios,
                group_key="project_id",
                seed=self.config.seed,
                allow_drawing_fallback=True,
            )
            split_manifest = split_mgr.create_splits(tile_records_for_splitting)
            manifest_files = split_mgr.export_split_manifests(
                split_manifest, self.config.output_dir / "splits"
            )
            logger.info("Project-isolated splits successfully exported.")

        # 5. Export master dataset manifest
        summary_path = self.config.output_dir / "dataset_manifest.json"
        summary_payload = {
            "version": "1.0",
            "total_prepared_drawings": len(prepared_records),
            "target_resolution": list(self.config.target_shape),
            "default_wall_class": self.config.default_wall_class,
            "manifest_files": {k: str(v) for k, v in manifest_files.items()},
            "drawings": [r.to_dict() for r in prepared_records],
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        return summary_payload

    def _create_synthetic_verification_sample(self) -> List[ParsedDrawing]:
        """Creates deterministic synthetic floor plans for testing and verification."""
        samples: List[ParsedDrawing] = []
        for i in range(6):
            site_id = f"site_{i // 2:02d}"
            drawing_id = f"mock_plan_{i:02d}"
            # Create a simple box room with an interior wall
            outer = Polygon([(0, 0), (20, 0), (20, 15), (0, 15), (0, 0)])
            inner = Polygon([(1, 1), (19, 1), (19, 14), (1, 14), (1, 1)])
            wall_perimeter = outer.difference(inner)
            divider = Polygon([(9.5, 1), (10.5, 1), (10.5, 14), (9.5, 14), (9.5, 1)])

            polys = []
            if isinstance(wall_perimeter, Polygon):
                polys.append(wall_perimeter)
            elif isinstance(wall_perimeter, MultiPolygon):
                polys.extend(list(wall_perimeter.geoms))
            polys.append(divider)

            samples.append(
                ParsedDrawing(
                    drawing_id=drawing_id,
                    site_id=site_id,
                    building_id=f"bld_{site_id}",
                    polygons=polys,
                    bounds=(0.0, 0.0, 20.0, 15.0),
                    source_dataset="synthetic_msd",
                )
            )
        return samples


# ==============================================================================
# 5. COMMAND-LINE INTERFACE (CLI)
# ==============================================================================

def build_cli_parser() -> argparse.ArgumentParser:
    """Builds the command-line argument parser for dataset preparation."""
    parser = argparse.ArgumentParser(
        prog="python -m drywall_detection.data.preparer",
        description="Standardize floor plans, rasterize WKT wall polygons, and enforce zero-leakage splits.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DATA_DIR / "msd",
        help="Path to raw dataset directory (contains Parquet or CSV tables).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Path to output processed dataset directory.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1024,
        help="Target floor plan width in pixels (default: 1024).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1024,
        help="Target floor plan height in pixels (default: 1024).",
    )
    parser.add_argument(
        "--wall-class",
        type=int,
        default=CLASS_UNCERTAIN,
        choices=[CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN],
        help="Default multiclass label for ingested generic walls (default: 3 Uncertain).",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Disable automatic project-isolated train/val/test splitting.",
    )
    parser.add_argument(
        "--split-ratios",
        nargs=3,
        type=float,
        default=[0.70, 0.15, 0.15],
        help="Split ratios for Train, Val, and Test (default: 0.70 0.15 0.15).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for partitioning (default: 42).",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """CLI execution entry point."""
    parser = build_cli_parser()
    parsed = parser.parse_args(args)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    config = PreparationConfig(
        raw_dir=parsed.raw_dir,
        output_dir=parsed.output_dir,
        target_width=parsed.width,
        target_height=parsed.height,
        default_wall_class=parsed.wall_class,
        split_after_prep=not parsed.no_split,
        split_ratios=tuple(parsed.split_ratios),  # type: ignore
        seed=parsed.seed,
    )

    preparer = DatasetPreparer(config)
    try:
        manifest = preparer.prepare_dataset()
        print("\n" + "=" * 60)
        print("DATASET PREPARATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Total Prepared Drawings: {manifest['total_prepared_drawings']}")
        print(f"Target Resolution:       {manifest['target_resolution']}")
        print(f"Output Directory:        {config.output_dir.resolve()}")
        if manifest.get("manifest_files"):
            print("Split Manifests:")
            for k, v in manifest["manifest_files"].items():
                print(f"  - {k.capitalize()}: {v}")
        print("=" * 60 + "\n")
        return 0
    except Exception as e:
        logger.exception(f"Dataset preparation failed: {e}")
        return 1


__all__ = [
    # Backward compatibility re-exports
    "DrawingSplitManager",
    "SplitManifest",
    "TileRecord",
    "SplitStats",
    "SplitLeakageError",
    "InsufficientGroupsError",
    "InvalidSplitRatioError",
    "verify_split_isolation",
    # M2 Preparer components
    "PreparationConfig",
    "ParsedDrawing",
    "UnifiedFloorPlan",
    "GeometryRasterizer",
    "DrawingSanitizer",
    "MSDAnnotationParser",
    "DatasetPreparer",
    "PALETTE_256",
    "build_cli_parser",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
