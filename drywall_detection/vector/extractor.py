"""
drywall_detection/vector/extractor.py

High-performance CAD vector extraction and coordinate transformation engine.
Extracts vector paths, linework, filled assemblies, text layers, and partition tags
from architectural PDF drawings. Reconstructs wall geometry using parallel line pair
matching and associates partition tags via 3-tier spatial matching.
"""

from __future__ import annotations
import argparse
import json
import math
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF
import numpy as np
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon, mapping
from shapely.ops import unary_union

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
    TAG_BOX_WIDTH_PT,
    TAG_BOX_HEIGHT_PT,
    TAG_BOX_TOLERANCE_PT,
    PROXIMITY_BUFFER_RADIUS_PT,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
)
from drywall_detection.utils.coords import (
    pdf_to_pixel,
    pixel_to_pdf,
    pdf_bbox_to_pixel,
    pixel_bbox_to_pdf,
    pdf_geom_to_pixel,
    pixel_geom_to_pdf,
)


@dataclass
class VectorPageProfile:
    """Diagnostic profile of a PDF page determining processing modality."""
    page_number: int
    path_count: int
    line_count: int
    rect_count: int
    curve_count: int
    word_count: int
    image_count: int
    image_coverage: float
    is_pure_vector: bool
    is_scanned_raster: bool
    is_hybrid: bool
    recommended_pipeline: str  # "VECTOR_FIRST", "RASTER_ML", "HYBRID"

    @property
    def is_vector_page(self) -> bool:
        """Returns True if page contains usable vector linework."""
        return self.is_pure_vector or self.is_hybrid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "path_count": self.path_count,
            "line_count": self.line_count,
            "rect_count": self.rect_count,
            "curve_count": self.curve_count,
            "word_count": self.word_count,
            "image_count": self.image_count,
            "image_coverage": self.image_coverage,
            "is_pure_vector": self.is_pure_vector,
            "is_scanned_raster": self.is_scanned_raster,
            "is_hybrid": self.is_hybrid,
            "is_vector_page": self.is_vector_page,
            "recommended_pipeline": self.recommended_pipeline,
        }


@dataclass
class TextElement:
    """Extracted text element with native and pixel-transformed coordinates."""
    text: str
    bbox_pdf: Tuple[float, float, float, float]
    bbox_pixel: Tuple[float, float, float, float]
    font_name: str
    font_size: float
    direction: Tuple[float, float]
    confidence: float = 1.0


@dataclass
class ExtractedWallCandidate:
    """Reconstructed architectural wall candidate assembly."""
    wall_id: str = ""
    geometry_pdf: Union[Polygon, MultiPolygon] = field(default_factory=Polygon)
    geometry_pixel: Union[Polygon, MultiPolygon] = field(default_factory=Polygon)
    thickness_pt: float = 0.0
    estimated_thickness_in: float = 0.0
    orientation: str = "HORIZONTAL"  # "HORIZONTAL", "VERTICAL", "DIAGONAL"
    source_type: str = "PARALLEL_PAIR"  # "PARALLEL_PAIR", "FILLED_RECT", "GRAY_CORE"
    matched_tag: Optional[str] = None
    match_method: str = "unassigned"  # "leader_line", "buffer_proximity", "unassigned"
    match_confidence: float = 0.0
    proposed_class: int = CLASS_UNCERTAIN
    polygon: Optional[Union[Polygon, MultiPolygon]] = None
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.wall_id:
            self.wall_id = f"w_{uuid.uuid4().hex[:8]}"
        if self.polygon is not None:
            if self.geometry_pdf.is_empty:
                self.geometry_pdf = self.polygon
            if self.geometry_pixel.is_empty:
                self.geometry_pixel = self.polygon
        elif not self.geometry_pdf.is_empty:
            self.polygon = self.geometry_pdf

        if self.confidence is not None and self.match_confidence == 0.0:
            self.match_confidence = float(self.confidence)
        elif self.confidence is None:
            self.confidence = self.match_confidence

    @property
    def geometry(self) -> Union[Polygon, MultiPolygon]:
        """Alias for geometry_pdf to maintain seamless compatibility."""
        return self.geometry_pdf

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Serializes the wall candidate to a standard GeoJSON feature."""
        return {
            "type": "Feature",
            "geometry": mapping(self.geometry_pdf),
            "properties": {
                "wall_id": self.wall_id,
                "thickness_pt": self.thickness_pt,
                "estimated_thickness_in": self.estimated_thickness_in,
                "orientation": self.orientation,
                "source_type": self.source_type,
                "matched_tag": self.matched_tag,
                "match_method": self.match_method,
                "match_confidence": self.match_confidence,
                "proposed_class": self.proposed_class,
            },
        }


@dataclass
class VectorGeometry:
    """Raw vector linework and geometry extracted from a page."""
    heavy_lines: List[Tuple[Point, Point, float]] = field(default_factory=list)  # (p1, p2, width)
    light_lines: List[Tuple[Point, Point, float]] = field(default_factory=list)
    filled_rects: List[Tuple[Polygon, Any]] = field(default_factory=list)  # (poly, fill_color)
    curves: List[Any] = field(default_factory=list)


class VectorExtractor:
    """
    Production-grade Vector Extraction & Coordinate Engine for Architectural Drawings.
    Handles exact reversible affine coordinate transformations under 90° CW rotation,
    profiles vector pages, filters drafting linework, extracts parallel wall boundaries,
    and identifies partition tags.
    """

    TAG_REGEX = re.compile(
        r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEFG]|8A|GL[12]|09|10|11)$"
    )

    def __init__(
        self,
        dpi: int = DEFAULT_DPI,
        rotation: int = MASTER_PDF_ROTATION_DEG,
        page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
        page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
        scale_ratio: float = 1.0 / 96.0,  # 1/8" = 1'-0" standard architectural scale
    ) -> None:
        self.dpi = dpi
        self.rotation = rotation
        self.page_width = page_width
        self.page_height = page_height
        self.scale_ratio = scale_ratio
        # 1 inch in PDF points at 1/8" = 1'-0" scale: (1/96) * 72 pt = 0.75 pt/inch
        # (1 real foot = 12 real inches = 12 * 0.75 = 9.0 pt)
        self.pt_per_inch = self.scale_ratio * 72.0

    # --------------------------------------------------------------------------
    # Reversible Affine Coordinate Transformation API
    # --------------------------------------------------------------------------
    def pdf_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transforms native unrotated PDF point (x, y) to rotated visual pixel coordinates.
        For 90° CW rotation:
            px = (page_height - y) * (dpi / 72.0)
            py = x * (dpi / 72.0)
        """
        return pdf_to_pixel(
            x,
            y,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    def pixel_to_pdf(self, px: float, py: float) -> Tuple[float, float]:
        """
        Transforms visual pixel coordinates (px, py) back to native unrotated PDF point.
        For 90° CW rotation:
            x = py / (dpi / 72.0)
            y = page_height - (px / (dpi / 72.0))
        """
        return pixel_to_pdf(
            px,
            py,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    def pdf_bbox_to_pixel(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        return pdf_bbox_to_pixel(
            bbox,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    def pixel_bbox_to_pdf(self, pbbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        return pixel_bbox_to_pdf(
            pbbox,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    def pdf_geom_to_pixel(self, geom: Any) -> Any:
        return pdf_geom_to_pixel(
            geom,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    def pixel_geom_to_pdf(self, geom: Any) -> Any:
        return pixel_geom_to_pdf(
            geom,
            dpi=self.dpi,
            page_width=self.page_width,
            page_height=self.page_height,
            rotation=self.rotation,
        )

    # --------------------------------------------------------------------------
    # Vector Presence Detection Engine
    # --------------------------------------------------------------------------
    def detect_vector_content(self, page: Any) -> VectorPageProfile:
        """
        Profiles a PDF page to determine whether native CAD vector linework and text
        layers are present, routing between VECTOR_FIRST, RASTER_ML, and HYBRID pipelines.
        """
        drawings = page.get_drawings() if hasattr(page, "get_drawings") else []
        path_count = len(drawings)
        line_count = 0
        rect_count = 0
        curve_count = 0

        for d in drawings:
            for item in d.get("items", []):
                itype = item[0]
                if itype == "l":
                    line_count += 1
                elif itype == "re":
                    rect_count += 1
                elif itype == "c":
                    curve_count += 1

        words = page.get_text("words") if hasattr(page, "get_text") else []
        word_count = len(words)

        images = page.get_images() if hasattr(page, "get_images") else []
        image_count = len(images)
        page_area = self.page_width * self.page_height
        image_coverage = 0.0

        if hasattr(page, "get_image_rects"):
            for img in images:
                try:
                    rects = page.get_image_rects(img[0])
                    for r in rects:
                        image_coverage += (r.width * r.height) / max(page_area, 1.0)
                except Exception:
                    pass

        is_pure_vector = (path_count >= 100 and image_coverage < 0.50 and word_count >= 20)
        is_scanned_raster = (path_count < 50 and (image_coverage >= 0.70 or word_count == 0))
        is_hybrid = not is_pure_vector and not is_scanned_raster

        if is_pure_vector:
            recommended = "VECTOR_FIRST"
        elif is_scanned_raster:
            recommended = "RASTER_ML"
        else:
            recommended = "HYBRID"

        page_num = getattr(page, "number", 0)

        return VectorPageProfile(
            page_number=page_num,
            path_count=path_count,
            line_count=line_count,
            rect_count=rect_count,
            curve_count=curve_count,
            word_count=word_count,
            image_count=image_count,
            image_coverage=round(image_coverage, 4),
            is_pure_vector=is_pure_vector,
            is_scanned_raster=is_scanned_raster,
            is_hybrid=is_hybrid,
            recommended_pipeline=recommended,
        )

    def analyze_page(self, page: Any, **kwargs: Any) -> VectorPageProfile:
        """Alias for detect_vector_content for diagnostic profiling of a PDF page."""
        return self.detect_vector_content(page, **kwargs)

    # --------------------------------------------------------------------------
    # Text Layer Extraction
    # --------------------------------------------------------------------------
    def extract_text_elements(
        self,
        page: Any,
        clip_viewport: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[TextElement]:
        """
        Extracts all searchable text tokens with exact bounding boxes and font metadata.
        """
        elements: List[TextElement] = []
        if not hasattr(page, "get_text"):
            return elements

        text_dict = page.get_text("dict")
        clip_rect = fitz.Rect(clip_viewport) if clip_viewport else None

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    dir_vec = tuple(line.get("dir", (1.0, 0.0)))
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if not txt:
                            continue
                        bbox_raw = span.get("bbox")
                        if not bbox_raw or len(bbox_raw) != 4:
                            continue
                        bbox_pdf = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))

                        if clip_rect and not clip_rect.intersects(fitz.Rect(bbox_pdf)):
                            continue

                        bbox_pixel = self.pdf_bbox_to_pixel(bbox_pdf)

                        elements.append(
                            TextElement(
                                text=txt,
                                bbox_pdf=bbox_pdf,
                                bbox_pixel=bbox_pixel,
                                font_name=span.get("font", ""),
                                font_size=float(span.get("size", 0.0)),
                                direction=dir_vec,
                                confidence=1.0,
                            )
                        )

        return elements

    # --------------------------------------------------------------------------
    # Linework & Geometry Categorization
    # --------------------------------------------------------------------------
    def extract_raw_geometry(
        self,
        page: Any,
        clip_viewport: Optional[Tuple[float, float, float, float]] = None,
    ) -> VectorGeometry:
        """
        Categorizes page vector drawings into heavy lines, light lines, and filled shapes.
        Applies solid stroke filter (dashes == '[] 0' or None) and lineweight threshold (w >= 0.84 pt).
        """
        geom = VectorGeometry()
        if not hasattr(page, "get_drawings"):
            return geom

        clip_rect = fitz.Rect(clip_viewport) if clip_viewport else None

        for d in page.get_drawings():
            rect = d.get("rect")
            if rect is not None and clip_rect and not clip_rect.intersects(rect):
                continue

            dtype = d.get("type")
            width = round(float(d.get("width", 0.0)), 2)
            dashes = d.get("dashes")

            # Solid line check: in PyMuPDF solid lines are '[] 0', '[]', None, or []
            is_solid = (
                dashes is None
                or dashes == "[] 0"
                or dashes == "[]"
                or dashes == []
                or dashes == ""
            )

            # Handle filled elements
            if dtype in ("f", "fs") and rect is not None:
                fill_color = d.get("fill")
                poly = box(rect.x0, rect.y0, rect.x1, rect.y1)
                geom.filled_rects.append((poly, fill_color))

            # Handle line strokes
            if dtype in ("s", "fs") and is_solid:
                for it in d.get("items", []):
                    if it[0] == "l":
                        p1, p2 = it[1], it[2]
                        pt1 = Point(p1.x, p1.y)
                        pt2 = Point(p2.x, p2.y)
                        if width >= 0.84:
                            geom.heavy_lines.append((pt1, pt2, width))
                        else:
                            geom.light_lines.append((pt1, pt2, width))

        return geom

    # --------------------------------------------------------------------------
    # Parallel Line Pair Wall Reconstruction Algorithm
    # --------------------------------------------------------------------------
    def extract_wall_candidates(
        self,
        page: Any,
        min_thickness_in: float = 2.0,
        max_thickness_in: float = 14.0,
        min_wall_len_pt: float = 5.0,
        clip_viewport: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[ExtractedWallCandidate]:
        """
        Reconstructs wall assemblies using parallel line pair detection on heavy strokes
        within the architectural thickness range (1.5 to 10.5 pt at 1/8" = 1'-0" scale)
        and merges overlapping pieces into clean Shapely wall polygons.
        """
        raw_geom = self.extract_raw_geometry(page, clip_viewport)
        min_thick_pt = min_thickness_in * self.pt_per_inch  # 2.0 * 0.75 = 1.5 pt
        max_thick_pt = max_thickness_in * self.pt_per_inch  # 14.0 * 0.75 = 10.5 pt

        h_lines: List[Tuple[float, float, float, float]] = []
        v_lines: List[Tuple[float, float, float, float]] = []

        for p1, p2, w in raw_geom.heavy_lines:
            dx = abs(p2.x - p1.x)
            dy = abs(p2.y - p1.y)
            length = math.hypot(dx, dy)
            if length < min_wall_len_pt:
                continue

            if dy < 0.15:  # Horizontal line
                x_min, x_max = min(p1.x, p2.x), max(p1.x, p2.x)
                h_lines.append((x_min, p1.y, x_max, p1.y))
            elif dx < 0.15:  # Vertical line
                y_min, y_max = min(p1.y, p2.y), max(p1.y, p2.y)
                v_lines.append((p1.x, y_min, p1.x, y_max))

        wall_polys: List[Polygon] = []

        # Sort lines by primary coordinate for sweep-line optimization
        h_lines.sort(key=lambda l: (l[1], l[0]))
        v_lines.sort(key=lambda l: (l[0], l[1]))

        # 1. Horizontal parallel line pairs
        for i in range(len(h_lines)):
            l1 = h_lines[i]
            y1 = l1[1]
            for j in range(i + 1, len(h_lines)):
                l2 = h_lines[j]
                dist = l2[1] - y1
                if dist > max_thick_pt:
                    break
                if dist >= min_thick_pt:
                    ox1 = max(l1[0], l2[0])
                    ox2 = min(l1[2], l2[2])
                    if ox2 - ox1 >= min_wall_len_pt:
                        y_low, y_high = min(l1[1], l2[1]), max(l1[1], l2[1])
                        p = box(ox1, y_low, ox2, y_high)
                        if p.is_valid and not p.is_empty:
                            wall_polys.append(p)

        # 2. Vertical parallel line pairs
        for i in range(len(v_lines)):
            l1 = v_lines[i]
            x1 = l1[0]
            for j in range(i + 1, len(v_lines)):
                l2 = v_lines[j]
                dist = l2[0] - x1
                if dist > max_thick_pt:
                    break
                if dist >= min_thick_pt:
                    oy1 = max(l1[1], l2[1])
                    oy2 = min(l1[3], l2[3])
                    if oy2 - oy1 >= min_wall_len_pt:
                        x_low, x_high = min(l1[0], l2[0]), max(l1[0], l2[0])
                        p = box(x_low, oy1, x_high, oy2)
                        if p.is_valid and not p.is_empty:
                            wall_polys.append(p)

        # 3. Check for gray-core concrete or solid filled wall rectangles
        for poly, fill_col in raw_geom.filled_rects:
            minx, miny, maxx, maxy = poly.bounds
            w = maxx - minx
            h = maxy - miny
            short_side = min(w, h)
            long_side = max(w, h)
            # Wall-like filled rectangle: thickness between min/max thickness and sufficient length
            if min_thick_pt <= short_side <= max_thick_pt and long_side >= min_wall_len_pt * 2.0:
                if poly.is_valid and not poly.is_empty:
                    wall_polys.append(poly)

        if not wall_polys:
            return []

        # Merge intersecting and collinear pieces
        merged_geom = unary_union(wall_polys)
        candidates: List[ExtractedWallCandidate] = []

        if isinstance(merged_geom, MultiPolygon):
            geoms = list(merged_geom.geoms)
        elif isinstance(merged_geom, Polygon):
            geoms = [merged_geom]
        else:
            geoms = []

        page_num = getattr(page, "number", 0)

        for idx, g in enumerate(geoms):
            if g.is_empty or not g.is_valid:
                continue

            minx, miny, maxx, maxy = g.bounds
            width = maxx - minx
            height = maxy - miny
            thick_pt = min(width, height)
            thick_in = thick_pt / max(self.pt_per_inch, 1e-6)

            orientation = "HORIZONTAL" if width >= height else "VERTICAL"

            geom_pixel = self.pdf_geom_to_pixel(g)

            candidates.append(
                ExtractedWallCandidate(
                    wall_id=f"wall_{page_num}_{idx:04d}",
                    geometry_pdf=g,
                    geometry_pixel=geom_pixel,
                    thickness_pt=round(thick_pt, 2),
                    estimated_thickness_in=round(thick_in, 2),
                    orientation=orientation,
                    source_type="PARALLEL_PAIR",
                    proposed_class=CLASS_UNCERTAIN,
                )
            )

        return candidates

    # --------------------------------------------------------------------------
    # Partition Tag Discovery
    # --------------------------------------------------------------------------
    def find_partition_tags(
        self,
        page: Any,
        clip_viewport: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[Tuple[TextElement, fitz.Rect]]:
        """
        Discovers verified partition tags and their enclosing 11.2 x 11.3 pt symbol boxes.
        Returns a list of tuples (TextElement, fitz.Rect).
        """
        text_elements = self.extract_text_elements(page, clip_viewport)
        tag_candidates: List[Tuple[TextElement, fitz.Rect]] = []

        drawings = page.get_drawings() if hasattr(page, "get_drawings") else []
        box_rects: List[fitz.Rect] = []
        for d in drawings:
            r = d.get("rect")
            if r is not None:
                if (
                    abs(r.width - TAG_BOX_WIDTH_PT) <= TAG_BOX_TOLERANCE_PT
                    and abs(r.height - TAG_BOX_HEIGHT_PT) <= TAG_BOX_TOLERANCE_PT
                ):
                    box_rects.append(r)

        for te in text_elements:
            if self.TAG_REGEX.match(te.text):
                t_rect = fitz.Rect(te.bbox_pdf)
                # Find enclosing or adjacent box
                matched_box = None
                for br in box_rects:
                    if br.intersects(t_rect):
                        matched_box = br
                        break

                if matched_box is None:
                    # Synthetic box centered on text
                    cx = (t_rect.x0 + t_rect.x1) / 2.0
                    cy = (t_rect.y0 + t_rect.y1) / 2.0
                    matched_box = fitz.Rect(
                        cx - TAG_BOX_WIDTH_PT / 2.0,
                        cy - TAG_BOX_HEIGHT_PT / 2.0,
                        cx + TAG_BOX_WIDTH_PT / 2.0,
                        cy + TAG_BOX_HEIGHT_PT / 2.0,
                    )

                tag_candidates.append((te, matched_box))

        return tag_candidates

    def extract_walls(
        self,
        page: Any,
        **kwargs: Any,
    ) -> List[ExtractedWallCandidate]:
        """Convenience alias for extract_wall_candidates."""
        return self.extract_wall_candidates(page, **kwargs)

    def extract_tags(
        self,
        page: Any,
        **kwargs: Any,
    ) -> List[Any]:
        """Convenience alias for find_partition_tags."""
        return self.find_partition_tags(page, **kwargs)


def main() -> int:
    """Command-line interface for VectorExtractor."""
    parser = argparse.ArgumentParser(
        description="VectorExtractor: Architectural vector extraction and coordinate engine."
    )
    parser.add_argument("--pdf", type=str, required=True, help="Path to input architectural PDF")
    parser.add_argument("--page", type=int, default=14, help="Page index (default: 14 for A-101)")
    parser.add_argument("--detect-only", action="store_true", help="Run only vector presence detection")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI resolution (default: 150)")
    parser.add_argument("--export-geojson", type=str, default="", help="Path to export extracted walls GeoJSON")

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return 1

    doc = fitz.open(pdf_path)
    if args.page < 0 or args.page >= len(doc):
        print(f"Error: Page index {args.page} out of bounds (total pages: {len(doc)})")
        return 1

    page = doc[args.page]
    extractor = VectorExtractor(dpi=args.dpi)

    profile = extractor.detect_vector_content(page)
    print(f"--- Vector Profile (Page {args.page}) ---")
    print(json.dumps(profile.to_dict(), indent=2))

    if args.detect_only:
        return 0

    walls = extractor.extract_wall_candidates(page)
    print(f"Extracted {len(walls)} wall candidates.")

    tags = extractor.find_partition_tags(page)
    print(f"Discovered {len(tags)} partition tag candidates.")

    if args.export_geojson:
        out_p = Path(args.export_geojson)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fc = {
            "type": "FeatureCollection",
            "features": [w.to_geojson_feature() for w in walls],
        }
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(fc, f, indent=2)
        print(f"Exported walls to {out_p}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
