"""
drywall_detection.datasets.unified_format
=========================================
Authoritative specification and conversion engine for the unified dataset format:
- Single-channel 8-bit indexed PNG masks (uint8, values 0..3)
- 256-color palette (0: White Background, 1: Green Drywall, 2: Red Non-Drywall, 3: Yellow Uncertain)
- Multi-dataset converters (MSD WKT, CubiCasa5K SVG, Raster masks)
- Sliding-window tiling engine (512x512 with 20% overlap, stride 410 px)
- Seamless 2D Hann apodization stitching
- Corrupt and blank tile filtering with controlled hard-negative retention
- Visual Quality Control (QC) sample generator producing triplet composite images
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

__all__ = [
    "DatasetClass",
    "PALETTE_256",
    "UnifiedDatasetConfig",
    "TileCoordinates",
    "TileMetadata",
    "MaskValidationError",
    "validate_mask_array",
    "UnifiedMask",
    "MSDConverter",
    "CubiCasaConverter",
    "RasterMaskConverter",
    "SlidingWindowTiler",
    "VisualQCGenerator",
]


class DatasetClass(IntEnum):
    """Authoritative 4-class semantic segmentation taxonomy."""
    BACKGROUND = 0
    DRYWALL = 1
    NON_DRYWALL = 2
    UNCERTAIN = 3

    @property
    def label(self) -> str:
        names = {
            0: "Background",
            1: "Drywall",
            2: "Non-Drywall",
            3: "Uncertain",
        }
        return names[self.value]

    @property
    def rgb_color(self) -> Tuple[int, int, int]:
        colors = {
            0: (255, 255, 255),  # White
            1: (0, 255, 0),      # Green
            2: (255, 0, 0),      # Red
            3: (255, 255, 0),    # Yellow
        }
        return colors[self.value]

    @property
    def bgr_color(self) -> Tuple[int, int, int]:
        r, g, b = self.rgb_color
        return (b, g, r)

    @property
    def hex_color(self) -> str:
        hexes = {
            0: "#FFFFFF",
            1: "#00FF00",
            2: "#FF0000",
            3: "#FFFF00",
        }
        return hexes[self.value]


# Standard 256-color palette for 8-bit indexed PNG (Mode 'P')
# Index 0: White (255, 255, 255)
# Index 1: Green (0, 255, 0)
# Index 2: Red   (255, 0, 0)
# Index 3: Yellow (255, 255, 0)
# Index 4..255: Black (0, 0, 0)
PALETTE_256: List[int] = [
    255, 255, 255,  # 0: Background
    0,   255,   0,  # 1: Drywall
    255,   0,   0,  # 2: Non-Drywall
    255, 255,   0,  # 3: Uncertain
] + [0] * (256 - 4) * 3


@dataclass
class UnifiedDatasetConfig:
    """Configuration parameters for dataset conversion, tiling, and QC."""
    tile_size: int = 512
    overlap_ratio: float = 0.20
    target_dpi: int = 150
    min_variance_threshold: float = 2.0
    blank_mean_threshold: float = 250.0
    max_hard_negative_ratio: float = 0.15
    nominal_hard_negative_min: int = 0
    nominal_hard_negatives_zero_walls: int = 0
    alpha_overlay: float = 0.40
    export_indexed_palette: bool = True

    @property
    def stride(self) -> int:
        return int(round(self.tile_size * (1.0 - self.overlap_ratio)))


@dataclass
class TileCoordinates:
    """Exact spatial bounding box of a tile within its parent drawing canvas."""
    row_idx: int
    col_idx: int
    y_min: int
    x_min: int
    y_max: int
    x_max: int
    parent_height: int
    parent_width: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "row_idx": self.row_idx,
            "col_idx": self.col_idx,
            "y_min": self.y_min,
            "x_min": self.x_min,
            "y_max": self.y_max,
            "x_max": self.x_max,
            "parent_height": self.parent_height,
            "parent_width": self.parent_width,
        }


@dataclass
class TileMetadata:
    """Structured metadata record generated alongside each tiled sample."""
    tile_id: str
    parent_drawing_id: str
    dataset_source: str
    split: str
    coordinates: TileCoordinates
    class_pixel_counts: Dict[str, int]
    class_percentages: Dict[str, float]
    has_walls: bool
    is_pure_blank: bool
    is_hard_negative: bool
    is_corrupt: bool
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "parent_drawing_id": self.parent_drawing_id,
            "dataset_source": self.dataset_source,
            "split": self.split,
            "coordinates": self.coordinates.to_dict(),
            "class_pixel_counts": self.class_pixel_counts,
            "class_percentages": self.class_percentages,
            "has_walls": self.has_walls,
            "is_pure_blank": self.is_pure_blank,
            "is_hard_negative": self.is_hard_negative,
            "is_corrupt": self.is_corrupt,
            "rejection_reason": self.rejection_reason,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class MaskValidationError(ValueError):
    """Raised when a segmentation mask violates format invariants."""
    pass


def validate_mask_array(
    mask: Any,
    expected_shape: Optional[Tuple[int, int]] = None,
    raise_on_error: bool = True,
    return_bool: bool = False,
) -> Union[np.ndarray, bool]:
    """
    Validates that a numpy array conforms strictly to the unified segmentation mask standard:
    1. Must be an instance of numpy.ndarray.
    2. Data type must strictly be uint8 (np.uint8).
    3. Array dimensionality must be exactly 2D (H, W).
    4. Array dimensions must be non-empty (H > 0 and W > 0).
    5. If expected_shape is provided, mask.shape must match expected_shape exactly.
    6. Pixel values must strictly be a subset of {0, 1, 2, 3}:
       - 0: Background (White)
       - 1: Drywall (Green)
       - 2: Non-Drywall (Red)
       - 3: Uncertain (Yellow)

    Args:
        mask: Array or object to validate.
        expected_shape: Optional (H, W) tuple to enforce specific spatial dimensions.
        raise_on_error: If True, raises MaskValidationError on any violation.
                        If False, suppresses exception and returns False on violation.
        return_bool: If True, returns True on success instead of the array.

    Returns:
        The validated numpy.ndarray (or True if return_bool) on success.
        Returns False if invalid and raise_on_error is False.

    Raises:
        MaskValidationError: If any invariant is violated and raise_on_error is True.
    """
    try:
        if not isinstance(mask, np.ndarray):
            raise MaskValidationError(f"Expected numpy ndarray, got {type(mask)}")
        if mask.dtype != np.uint8:
            raise MaskValidationError(f"Expected dtype uint8, got {mask.dtype}")
        if mask.ndim != 2:
            raise MaskValidationError(f"Expected 2D array (H, W), got shape {mask.shape}")
        if mask.shape[0] == 0 or mask.shape[1] == 0:
            raise MaskValidationError(f"Empty dimensions not permitted, got shape {mask.shape}")
        if expected_shape is not None and mask.shape != tuple(expected_shape):
            raise MaskValidationError(f"Expected shape {expected_shape}, got {mask.shape}")

        # Invariant check: values must strictly be in {0, 1, 2, 3}
        unique_vals = np.unique(mask)
        invalid_vals = [int(v) for v in unique_vals if v not in (0, 1, 2, 3)]
        if invalid_vals:
            raise MaskValidationError(f"Invalid mask values found: {invalid_vals}. Allowed values are {{0, 1, 2, 3}}.")

        return True if return_bool else mask
    except MaskValidationError:
        if raise_on_error:
            raise
        return False


class UnifiedMask:
    """Encapsulates a single-channel 8-bit segmentation mask with strict invariant validation."""

    def __init__(self, data: np.ndarray) -> None:
        validate_mask_array(data, raise_on_error=True)
        self.data = data

    @property
    def shape(self) -> Tuple[int, int]:
        return self.data.shape

    @property
    def height(self) -> int:
        return self.data.shape[0]

    @property
    def width(self) -> int:
        return self.data.shape[1]

    @classmethod
    def zeros(cls, height: int, width: int) -> 'UnifiedMask':
        return cls(np.zeros((height, width), dtype=np.uint8))

    @classmethod
    def load(cls, path: Union[str, Path]) -> 'UnifiedMask':
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Mask file not found: {path}")
        img = Image.open(path)
        arr = np.array(img, dtype=np.uint8)
        if arr.ndim == 3:
            # If accidentally saved as RGB, take first channel
            arr = arr[:, :, 0]
        return cls(arr)

    def save(self, path: Union[str, Path], as_indexed_palette: bool = True) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if as_indexed_palette:
            img = Image.fromarray(self.data, mode='P')
            img.putpalette(PALETTE_256)
            img.save(path)
        else:
            img = Image.fromarray(self.data, mode='L')
            img.save(path)
        return path

    def get_class_counts(self) -> Dict[str, int]:
        return {
            "background": int(np.sum(self.data == DatasetClass.BACKGROUND.value)),
            "drywall": int(np.sum(self.data == DatasetClass.DRYWALL.value)),
            "non_drywall": int(np.sum(self.data == DatasetClass.NON_DRYWALL.value)),
            "uncertain": int(np.sum(self.data == DatasetClass.UNCERTAIN.value)),
        }

    def get_class_percentages(self) -> Dict[str, float]:
        total = max(self.data.size, 1)
        counts = self.get_class_counts()
        return {k: round((v / total) * 100.0, 3) for k, v in counts.items()}

    def has_walls(self) -> bool:
        return bool(np.any(self.data > 0))

    def to_rgb_color_mask(self) -> np.ndarray:
        """Converts mask to (H, W, 3) RGB color rendering for display."""
        h, w = self.shape
        rgb = np.full((h, w, 3), 255, dtype=np.uint8)
        for cls in (DatasetClass.DRYWALL, DatasetClass.NON_DRYWALL, DatasetClass.UNCERTAIN):
            m = (self.data == cls.value)
            if np.any(m):
                rgb[m] = cls.rgb_color
        return rgb


class MSDConverter:
    """Converts Modified Swiss Dwellings WKT geometries to UnifiedMask."""

    def __init__(self, config: Optional[UnifiedDatasetConfig] = None) -> None:
        self.config = config or UnifiedDatasetConfig()

    def parse_wkt_geometries(
        self,
        wkt_list: List[str],
        target_shape: Tuple[int, int],
        bounds: Optional[Tuple[float, float, float, float]] = None,
        target_class: DatasetClass = DatasetClass.UNCERTAIN,
    ) -> UnifiedMask:
        """
        Parses WKT wall polygons and rasterizes to target canvas.
        All structural walls map strictly to target_class (defaults to Class 3 Uncertain).
        """
        import shapely.wkt
        from shapely.geometry import Polygon, MultiPolygon

        h, w = target_shape
        canvas = np.zeros((h, w), dtype=np.uint8)

        polys = []
        for wkt in wkt_list:
            try:
                geom = shapely.wkt.loads(wkt)
                if geom.geom_type in ('Polygon', 'MultiPolygon'):
                    polys.append(geom)
            except Exception as e:
                logger.warning(f"Error parsing WKT geometry: {e}")

        if not polys:
            return UnifiedMask(canvas)

        if bounds is None:
            min_x = min(p.bounds[0] for p in polys)
            min_y = min(p.bounds[1] for p in polys)
            max_x = max(p.bounds[2] for p in polys)
            max_y = max(p.bounds[3] for p in polys)
        else:
            min_x, min_y, max_x, max_y = bounds

        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)

        def transform_coords(pts):
            scaled = []
            for px, py in pts:
                sx = int(round(((px - min_x) / span_x) * (w - 1)))
                sy = int(round(((max_y - py) / span_y) * (h - 1)))
                scaled.append([sx, sy])
            return np.array(scaled, dtype=np.int32)

        for poly in polys:
            if poly.geom_type == 'Polygon':
                ext = transform_coords(poly.exterior.coords)
                cv2.fillPoly(canvas, [ext], color=target_class.value)
                for hole in poly.interiors:
                    hole_pts = transform_coords(hole.coords)
                    cv2.fillPoly(canvas, [hole_pts], color=DatasetClass.BACKGROUND.value)
            elif poly.geom_type == 'MultiPolygon':
                for p in poly.geoms:
                    ext = transform_coords(p.exterior.coords)
                    cv2.fillPoly(canvas, [ext], color=target_class.value)
                    for hole in p.interiors:
                        hole_pts = transform_coords(hole.coords)
                        cv2.fillPoly(canvas, [hole_pts], color=DatasetClass.BACKGROUND.value)

        return UnifiedMask(canvas)


class CubiCasaConverter:
    """Converts CubiCasa5K SVG vector annotations to UnifiedMask."""

    def __init__(self, config: Optional[UnifiedDatasetConfig] = None) -> None:
        self.config = config or UnifiedDatasetConfig()

    def parse_svg(
        self,
        svg_content_or_path: Union[str, Path],
        target_shape: Tuple[int, int],
        target_class: DatasetClass = DatasetClass.UNCERTAIN,
    ) -> UnifiedMask:
        """
        Parses CubiCasa5K SVG (file path or XML string) and rasterizes Wall elements.
        Maps structural walls strictly to target_class (defaults to Class 3 Uncertain).
        """
        import xml.etree.ElementTree as ET

        if isinstance(svg_content_or_path, Path) or (isinstance(svg_content_or_path, str) and not svg_content_or_path.strip().startswith("<")):
            tree = ET.parse(str(svg_content_or_path))
            root = tree.getroot()
        else:
            root = ET.fromstring(svg_content_or_path)

        target_h, target_w = target_shape
        canvas = np.zeros((target_h, target_w), dtype=np.uint8)

        viewbox = root.attrib.get('viewBox', f'0 0 {target_w} {target_h}').split()
        if len(viewbox) == 4:
            vb_w, vb_h = float(viewbox[2]), float(viewbox[3])
        else:
            vb_w, vb_h = float(target_w), float(target_h)

        scale_x = target_w / max(vb_w, 1.0)
        scale_y = target_h / max(vb_h, 1.0)

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            cls_name = elem.attrib.get('class', '')
            if tag == 'polygon' and 'Wall' in cls_name:
                points_str = elem.attrib.get('points', '')
                pts = []
                for pair in points_str.strip().split():
                    if ',' in pair:
                        try:
                            x, y = map(float, pair.split(','))
                            pts.append([int(round(x * scale_x)), int(round(y * scale_y))])
                        except ValueError:
                            continue
                if pts:
                    pts_arr = np.array(pts, dtype=np.int32)
                    cv2.fillPoly(canvas, [pts_arr], color=target_class.value)

        return UnifiedMask(canvas)


class RasterMaskConverter:
    """Converts binary or multi-class raster masks (e.g., CVC-FP) into UnifiedMask."""

    def __init__(self, config: Optional[UnifiedDatasetConfig] = None) -> None:
        self.config = config or UnifiedDatasetConfig()

    def convert_raster(
        self,
        raster: Union[np.ndarray, str, Path],
        target_shape: Optional[Tuple[int, int]] = None,
        wall_threshold: int = 127,
        target_class: DatasetClass = DatasetClass.UNCERTAIN,
    ) -> UnifiedMask:
        """
        Converts raster mask to UnifiedMask.
        Foreground (> wall_threshold) is mapped to target_class.
        """
        if isinstance(raster, (str, Path)):
            img = Image.open(raster).convert("L")
            arr = np.array(img, dtype=np.uint8)
        else:
            arr = raster.copy()
            if arr.ndim == 3:
                arr = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)

        if target_shape is not None and arr.shape != target_shape:
            arr = cv2.resize(arr, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)

        mask_data = np.zeros(arr.shape, dtype=np.uint8)
        mask_data[arr > wall_threshold] = target_class.value

        return UnifiedMask(mask_data)


class SlidingWindowTiler:
    """
    Sliding-window tiling engine:
    - Generates 512x512 patches with 20% overlap (stride 410 px)
    - Enforces boundary clamping (100% surface coverage without edge truncation)
    - Seamless 2D Hann apodization reverse stitching
    - Filters corrupt/empty tiles and controls hard-negative retention
    """

    def __init__(self, config: Optional[UnifiedDatasetConfig] = None) -> None:
        self.config = config or UnifiedDatasetConfig()

    def compute_tile_grid(self, height: int, width: int) -> Tuple[List[int], List[int]]:
        """Computes y_steps and x_steps covering the entire canvas with boundary clamping."""
        tile_size = self.config.tile_size
        stride = self.config.stride

        def get_steps(dim: int) -> List[int]:
            if dim <= tile_size:
                return [0]
            steps = []
            pos = 0
            while pos + tile_size <= dim:
                steps.append(pos)
                pos += stride
            if not steps or steps[-1] + tile_size < dim:
                steps.append(max(0, dim - tile_size))
            return sorted(list(set(steps)))

        return get_steps(height), get_steps(width)

    def tile_drawing(
        self,
        image: np.ndarray,
        mask: UnifiedMask,
        drawing_id: str,
        dataset_source: str,
        split: str = "train",
    ) -> List[Tuple[np.ndarray, UnifiedMask, TileMetadata]]:
        """
        Synchronously tiles drawing and mask into fixed-size overlapping patches.
        Applies corruption checks, filters pure blank tiles, and strictly enforces
        the hard negative retention quota based on self.config.max_hard_negative_ratio.

        Candidate hard negative tiles are deterministically ranked by linework variance
        descending to prioritize the most informative background patterns (schedules,
        text, structural lines), with deterministic coordinate tie-breaking.

        Args:
            image: Full-scale drawing image array (H, W, 3) or (H, W) uint8.
            mask: UnifiedMask instance containing ground truth segmentation labels.
            drawing_id: Unique identifier for the parent drawing sheet.
            dataset_source: Origin dataset identifier (e.g., 'MSD', 'CubiCasa5K', 'MTA_99th').
            split: Target dataset split partition ('train', 'val', 'test').

        Returns:
            List of (image_tile, mask_tile, metadata) tuples, sorted in canonical
            raster-scan spatial order (row_idx, col_idx).
        """
        h, w = mask.shape
        y_steps, x_steps = self.compute_tile_grid(h, w)
        tile_size = self.config.tile_size

        wall_tiles: List[Tuple[np.ndarray, UnifiedMask, TileMetadata]] = []
        candidate_hn: List[Tuple[np.ndarray, UnifiedMask, TileMetadata, float]] = []

        for r_idx, y0 in enumerate(y_steps):
            for c_idx, x0 in enumerate(x_steps):
                y1 = y0 + tile_size
                x1 = x0 + tile_size

                img_tile = image[y0:y1, x0:x1]
                mask_tile_data = mask.data[y0:y1, x0:x1]

                tile_id = f"{drawing_id}_r{r_idx:02d}_c{c_idx:02d}"
                coords = TileCoordinates(
                    row_idx=r_idx,
                    col_idx=c_idx,
                    y_min=y0,
                    x_min=x0,
                    y_max=y1,
                    x_max=x1,
                    parent_height=h,
                    parent_width=w,
                )

                # Check corruption
                is_corrupt = False
                rejection_reason = None
                if img_tile.shape[:2] != (tile_size, tile_size) or mask_tile_data.shape != (tile_size, tile_size):
                    is_corrupt = True
                    rejection_reason = "SHAPE_MISMATCH"
                elif np.any(mask_tile_data > 3):
                    is_corrupt = True
                    rejection_reason = "INVALID_MASK_VALUE"

                if is_corrupt:
                    continue

                mask_tile = UnifiedMask(mask_tile_data)
                has_walls = mask_tile.has_walls()

                # Evaluate image variance and blankness
                if img_tile.ndim == 3:
                    img_gray = cv2.cvtColor(img_tile, cv2.COLOR_BGR2GRAY)
                else:
                    img_gray = img_tile

                img_std = float(np.std(img_gray))
                img_mean = float(np.mean(img_gray))

                is_pure_blank = (img_std < self.config.min_variance_threshold) and (img_mean > self.config.blank_mean_threshold)
                is_hard_negative = (not has_walls) and (not is_pure_blank)

                # Pure blank tiles without walls are 100% discarded
                if is_pure_blank and not has_walls:
                    continue

                metadata = TileMetadata(
                    tile_id=tile_id,
                    parent_drawing_id=drawing_id,
                    dataset_source=dataset_source,
                    split=split,
                    coordinates=coords,
                    class_pixel_counts=mask_tile.get_class_counts(),
                    class_percentages=mask_tile.get_class_percentages(),
                    has_walls=has_walls,
                    is_pure_blank=is_pure_blank,
                    is_hard_negative=is_hard_negative,
                    is_corrupt=is_corrupt,
                    rejection_reason=rejection_reason,
                )

                if has_walls:
                    wall_tiles.append((img_tile, mask_tile, metadata))
                elif is_hard_negative:
                    candidate_hn.append((img_tile, mask_tile, metadata, img_std))

        # Enforce hard negative retention quota
        ratio = self.config.max_hard_negative_ratio
        nom_min = max(
            getattr(self.config, "nominal_hard_negative_min", 0),
            getattr(self.config, "nominal_hard_negatives_zero_walls", 0),
        )
        num_walls = len(wall_tiles)

        if ratio <= 0.0:
            max_hn = nom_min if num_walls == 0 else 0
        elif ratio >= 1.0:
            max_hn = len(candidate_hn)
        elif num_walls > 0:
            quota_float = num_walls * ratio / (1.0 - ratio)
            quota_cap = int(np.ceil(quota_float))
            max_hn = max(nom_min, quota_cap)
        else:
            # num_walls == 0
            if len(candidate_hn) == 1:
                # Single-tile test crop or detail sheet: retain the 1 tile
                max_hn = max(1, nom_min)
            else:
                # Multi-tile unannotated drawing: retain 0 (or configured nominal minimum)
                max_hn = nom_min

        # Sort candidate hard negatives by linework variance descending with spatial tie-break
        candidate_hn.sort(
            key=lambda item: (-item[3], item[2].coordinates.row_idx, item[2].coordinates.col_idx, item[2].tile_id)
        )
        retained_hn = [item[:3] for item in candidate_hn[:max_hn]]

        # Combine and sort all retained tiles in canonical spatial raster order
        results = wall_tiles + retained_hn
        results.sort(key=lambda t: (t[2].coordinates.row_idx, t[2].coordinates.col_idx))

        return results

    def stitch_predictions(
        self,
        tiles: List[np.ndarray],
        coords: List[TileCoordinates],
        parent_shape: Tuple[int, int],
        num_classes: int = 4,
    ) -> np.ndarray:
        """
        Reassembles overlapping predicted tile probability tensors into a global prediction mask
        using 2D Hann window apodization weighting.
        """
        h, w = parent_shape
        tile_size = self.config.tile_size

        # 2D Hann apodization window
        wx = np.hanning(tile_size)
        wy = np.hanning(tile_size)
        window_2d = np.outer(wy, wx).astype(np.float32)
        window_2d = np.clip(window_2d, 1e-4, 1.0)
        window_3d = np.expand_dims(window_2d, axis=-1)

        num_accum = np.zeros((h, w, num_classes), dtype=np.float32)
        den_accum = np.zeros((h, w, 1), dtype=np.float32)

        for tile_prob, coord in zip(tiles, coords):
            y0, y1 = coord.y_min, coord.y_max
            x0, x1 = coord.x_min, coord.x_max

            # If tile_prob has shape (H, W) or (C, H, W) or (H, W, C)
            if tile_prob.ndim == 2:
                # 2D discrete labels -> one-hot
                prob_tile = np.zeros((tile_size, tile_size, num_classes), dtype=np.float32)
                for c in range(num_classes):
                    prob_tile[:, :, c] = (tile_prob == c).astype(np.float32)
            elif tile_prob.ndim == 3 and tile_prob.shape[0] == num_classes:
                # (C, H, W) -> (H, W, C)
                prob_tile = np.transpose(tile_prob, (1, 2, 0)).astype(np.float32)
            else:
                prob_tile = tile_prob.astype(np.float32)

            num_accum[y0:y1, x0:x1, :] += prob_tile * window_3d
            den_accum[y0:y1, x0:x1, :] += window_3d

        den_accum = np.maximum(den_accum, 1e-6)
        global_prob = num_accum / den_accum
        global_mask = np.argmax(global_prob, axis=-1).astype(np.uint8)

        return global_mask


class VisualQCGenerator:
    """Generates visual Quality Control (QC) artifacts and inspection triplets."""

    def __init__(self, config: Optional[UnifiedDatasetConfig] = None) -> None:
        self.config = config or UnifiedDatasetConfig()

    def render_overlay(self, image_bgr: np.ndarray, mask: UnifiedMask) -> np.ndarray:
        """Overlays translucent color masks directly onto floor plan images."""
        alpha = self.config.alpha_overlay
        overlay = image_bgr.copy()

        for cls in (DatasetClass.DRYWALL, DatasetClass.NON_DRYWALL, DatasetClass.UNCERTAIN):
            cls_mask = (mask.data == cls.value)
            if np.any(cls_mask):
                colored_layer = np.zeros_like(image_bgr)
                colored_layer[cls_mask] = cls.bgr_color
                blended = cv2.addWeighted(image_bgr, 1.0 - alpha, colored_layer, alpha, 0)
                overlay[cls_mask] = blended[cls_mask]

        return overlay

    def create_triplet(
        self,
        image_bgr: np.ndarray,
        mask: UnifiedMask,
        metadata: Optional[TileMetadata] = None,
    ) -> np.ndarray:
        """
        Creates horizontal triplet: [Original Drawing | Color Mask | Translucent Overlay]
        with diagnostic header banner.
        """
        overlay = self.render_overlay(image_bgr, mask)

        h, w = mask.shape
        vis_mask = np.full((h, w, 3), 255, dtype=np.uint8)
        for cls in (DatasetClass.DRYWALL, DatasetClass.NON_DRYWALL, DatasetClass.UNCERTAIN):
            m = (mask.data == cls.value)
            if np.any(m):
                vis_mask[m] = cls.bgr_color

        triplet = np.hstack([image_bgr, vis_mask, overlay])

        if metadata is not None:
            banner_h = 36
            banner = np.full((banner_h, triplet.shape[1], 3), 35, dtype=np.uint8)
            status = "HARD_NEG" if metadata.is_hard_negative else ("WALL_SAMPLE" if metadata.has_walls else "EMPTY")
            text = (
                f"ID: {metadata.tile_id} | SRC: {metadata.dataset_source} | "
                f"DW: {metadata.class_percentages['drywall']:.1f}% | "
                f"NON-DW: {metadata.class_percentages['non_drywall']:.1f}% | "
                f"UNC: {metadata.class_percentages['uncertain']:.1f}% | STATUS: {status}"
            )
            cv2.putText(banner, text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
            triplet = np.vstack([banner, triplet])

        return triplet

    def save_qc_sample(
        self,
        output_path: Union[str, Path],
        image_bgr: np.ndarray,
        mask: UnifiedMask,
        metadata: Optional[TileMetadata] = None,
    ) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        triplet = self.create_triplet(image_bgr, mask, metadata)
        cv2.imwrite(str(out), triplet)
        return out
