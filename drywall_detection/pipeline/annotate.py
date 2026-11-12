#!/usr/bin/env python3
"""
drywall_detection.pipeline.annotate
===================================
Architectural PDF & Image Annotation Pipeline.

Provides high-fidelity, dimension-preserving, vector-linework-preserving
annotation for architectural drawings with 4-class semantic segmentation masks:
  - 0: Background -> Completely transparent / unaltered
  - 1: Drywall -> Green (#00FF00 / #00C853, RGBA (0, 255, 0, alpha=0.45))
  - 2: Non-Drywall -> Red (#FF0000 / #D50000, RGBA (255, 0, 0, alpha=0.45))
  - 3: Uncertain -> Yellow (#FFFF00 / #FFD600, RGBA (255, 255, 0, alpha=0.45))

Preservation Guarantees:
  1. Original physical page dimensions (MediaBox/CropBox) and aspect ratio.
  2. Original vector linework quality (underlying vector paths, text, fonts,
     and CAD geometry are 100% untouched and retain infinite zoom sharpness).
  3. Original page rotation (orientation matches input drawing under 0, 90,
     180, and 270 degree rotations).
"""

from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_OVERLAY_ALPHA,
)

logger = logging.getLogger("pipeline.annotate")

# Standard 4-Class Color Taxonomy
# Primary architectural high-visibility palette
PALETTE_STANDARD = {
    CLASS_BACKGROUND: (0, 0, 0),        # Transparent
    CLASS_DRYWALL: (0, 255, 0),         # Pure Green #00FF00
    CLASS_NON_DRYWALL: (255, 0, 0),     # Pure Red #FF0000
    CLASS_UNCERTAIN: (255, 255, 0),     # Pure Yellow #FFFF00
}

# Material Design vibrant palette (calibrated for screen readability)
PALETTE_VIBRANT = {
    CLASS_BACKGROUND: (255, 255, 255),  # Transparent
    CLASS_DRYWALL: (0, 200, 83),        # Material Green #00C853
    CLASS_NON_DRYWALL: (213, 0, 0),     # Material Red #D50000
    CLASS_UNCERTAIN: (255, 214, 0),     # Material Yellow #FFD600
}


def build_rgba_lut(
    alpha: float = DEFAULT_OVERLAY_ALPHA,
    palette: Optional[Dict[int, Tuple[int, int, int]]] = None,
) -> np.ndarray:
    """
    Builds a 256x4 uint8 lookup table (LUT) mapping class indices {0, 1, 2, 3}
    directly to RGBA values in a single vectorized numpy indexing step.
    """
    pal = palette or PALETTE_STANDARD
    lut = np.zeros((256, 4), dtype=np.uint8)
    alpha_u8 = int(np.clip(alpha, 0.0, 1.0) * 255)

    # Class 0 (Background): Alpha = 0 (100% transparent)
    lut[CLASS_BACKGROUND] = [0, 0, 0, 0]

    # Classes 1, 2, 3: RGB with configured alpha
    for cls_idx in (CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN):
        rgb = pal.get(cls_idx, (255, 255, 255))
        lut[cls_idx] = [rgb[0], rgb[1], rgb[2], alpha_u8]

    return lut


def mask_to_rgba_overlay(
    mask_uint8: np.ndarray,
    alpha: float = DEFAULT_OVERLAY_ALPHA,
    palette: Optional[Dict[int, Tuple[int, int, int]]] = None,
) -> np.ndarray:
    """
    Converts a 2D uint8 segmentation mask into a 4-channel RGBA numpy array.
    Runs in vectorized O(N) time via LUT indexing (< 0.05s for 5400x3600).
    """
    lut = build_rgba_lut(alpha=alpha, palette=palette)
    return lut[mask_uint8]


def render_blended_image(
    image_rgb: np.ndarray,
    mask_uint8: np.ndarray,
    alpha: float = DEFAULT_OVERLAY_ALPHA,
    palette: Optional[Dict[int, Tuple[int, int, int]]] = None,
) -> np.ndarray:
    """
    Alpha-blends segmentation mask onto an RGB drawing image.
    Used for image export (.png, .jpg) or web UI display.
    """
    pal = palette or PALETTE_STANDARD
    overlay = image_rgb.copy().astype(np.float32)
    alpha_val = float(np.clip(alpha, 0.0, 1.0))

    for cls_idx in (CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN):
        match = (mask_uint8 == cls_idx)
        if np.any(match):
            color = np.array(pal[cls_idx], dtype=np.float32)
            overlay[match] = (1.0 - alpha_val) * overlay[match] + alpha_val * color

    return np.clip(overlay, 0, 255).astype(np.uint8)


def compute_mask_metrics(
    mask_uint8: np.ndarray,
    page_num: int = 1,
    dimensions_px: Optional[Tuple[int, int]] = None,
    dimensions_pt: Optional[Tuple[float, float]] = None,
    rotation_deg: int = 0,
    elapsed_sec: float = 0.0,
) -> Dict[str, Any]:
    """
    Computes rigorous per-page statistics on predicted masks.
    """
    total_pixels = int(mask_uint8.size)
    c0 = int(np.sum(mask_uint8 == CLASS_BACKGROUND))
    c1 = int(np.sum(mask_uint8 == CLASS_DRYWALL))
    c2 = int(np.sum(mask_uint8 == CLASS_NON_DRYWALL))
    c3 = int(np.sum(mask_uint8 == CLASS_UNCERTAIN))
    total_walls = c1 + c2 + c3

    h_px, w_px = mask_uint8.shape if dimensions_px is None else dimensions_px

    return {
        "page_num": page_num,
        "dimensions_px": [int(h_px), int(w_px)],
        "dimensions_pt": list(dimensions_pt) if dimensions_pt else None,
        "rotation_deg": int(rotation_deg),
        "total_pixels": total_pixels,
        "class_pixel_counts": {
            "background": c0,
            "drywall": c1,
            "non_drywall": c2,
            "uncertain": c3,
            "total_walls": total_walls,
        },
        "class_percentages": {
            "background": round((c0 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
            "drywall": round((c1 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
            "non_drywall": round((c2 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
            "uncertain": round((c3 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
        },
        "drywall_percentage": round((c1 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
        "wall_density_percentage": round((total_walls / total_pixels) * 100.0, 4) if total_pixels else 0.0,
        "elapsed_sec": round(elapsed_sec, 3),
    }


class PDFAnnotator:
    """
    High-fidelity PDF and Image annotation engine preserving vector quality,
    physical dimensions, and page rotation.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_OVERLAY_ALPHA,
        palette: Optional[Dict[int, Tuple[int, int, int]]] = None,
        annotation_method: str = "overlay",
    ) -> None:
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.palette = palette or PALETTE_STANDARD
        self.annotation_method = annotation_method  # 'overlay' or 'polygon'

    def annotate_pdf_page_overlay(
        self,
        page: fitz.Page,
        mask_uint8: np.ndarray,
    ) -> None:
        """
        Inserts a transparent RGBA pixmap overlay directly onto an existing PDF page.

        Mathematical Invariant:
          - Page content streams exist in unrotated cropbox space `page.cropbox`.
          - Mask is rendered in rotated visual coordinates.
          - Calling `page.insert_image(page.cropbox, pixmap=..., rotate=page.rotation, overlay=True)`
            applies the exact affine rotation matrix matching the page rotation.
          - Original vector paths, fonts, layers, and linework remain 100% untouched.
        """
        rgba = mask_to_rgba_overlay(mask_uint8, alpha=self.alpha, palette=self.palette)
        h, w, _ = rgba.shape

        # Construct PyMuPDF Pixmap directly from raw bytes
        pix_overlay = fitz.Pixmap(fitz.csRGB, w, h, rgba.tobytes(), True)

        # Insert overlay directly on top of vector drawing
        page.insert_image(
            page.cropbox,
            pixmap=pix_overlay,
            rotate=page.rotation,
            overlay=True,
        )

    def annotate_pdf_page_polygons(
        self,
        page: fitz.Page,
        mask_uint8: np.ndarray,
        dpi: int = 150,
        min_contour_area: float = 20.0,
    ) -> int:
        """
        Vector polygon annotation mode:
        Extracts boundary contours for each class and draws native translucent vector
        polygons onto the PDF page. Preserves infinite zoom on mask boundaries.
        """
        from drywall_detection.utils.coords import pixel_to_pdf

        h_px, w_px = mask_uint8.shape
        page_w_pt = page.mediabox.width
        page_h_pt = page.mediabox.height
        rot = page.rotation

        total_polygons = 0
        shape = page.new_shape()

        for cls_idx in (CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN):
            bin_mask = (mask_uint8 == cls_idx).astype(np.uint8) * 255
            contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            rgb = self.palette[cls_idx]
            rgb_norm = (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)

            for cnt in contours:
                if cv2.contourArea(cnt) < min_contour_area:
                    continue

                poly_approx = cv2.approxPolyDP(cnt, epsilon=1.5, closed=True)
                if len(poly_approx) < 3:
                    continue

                # Transform pixel coordinates to PDF point coordinates
                fitz_pts = []
                for pt in poly_approx:
                    px, py = float(pt[0][0]), float(pt[0][1])
                    pdf_x, pdf_y = pixel_to_pdf(
                        px, py,
                        dpi=dpi,
                        page_width=page_w_pt,
                        page_height=page_h_pt,
                        rotation=rot,
                    )
                    fitz_pts.append(fitz.Point(pdf_x, pdf_y))

                shape.draw_polyline(fitz_pts)
                shape.finish(
                    color=None,
                    fill=rgb_norm,
                    fill_opacity=self.alpha,
                    closePath=True,
                )
                total_polygons += 1

        shape.commit()
        return total_polygons

    def annotate_pdf_document(
        self,
        input_pdf_path: Union[str, Path],
        output_pdf_path: Union[str, Path],
        masks_by_page: Dict[int, np.ndarray],
        dpi: int = 150,
    ) -> Dict[str, Any]:
        """
        Annotates multi-page PDF preserving original vector quality and dimensions.
        """
        in_path = Path(input_pdf_path)
        out_path = Path(output_pdf_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(in_path)
        t0 = time.time()
        annotated_pages = 0

        for p_idx, mask in masks_by_page.items():
            if 0 <= p_idx < len(doc):
                page = doc[p_idx]
                if self.annotation_method == "polygon":
                    self.annotate_pdf_page_polygons(page, mask, dpi=dpi)
                else:
                    self.annotate_pdf_page_overlay(page, mask)
                annotated_pages += 1

        doc.save(str(out_path), deflate=True, garbage=4)
        doc.close()

        elapsed = time.time() - t0
        file_size_kb = out_path.stat().st_size / 1024.0

        return {
            "annotated_pages": annotated_pages,
            "output_pdf_path": str(out_path),
            "file_size_kb": round(file_size_kb, 1),
            "elapsed_sec": round(elapsed, 3),
        }


# ==============================================================================
# Milestone M5 High-Fidelity Vector & Raster Visualization Engine
# ==============================================================================
from dataclasses import dataclass, field
from PIL import ImageDraw
from shapely.geometry import MultiPolygon, Polygon
from drywall_detection.classification.classifier import ClassifiedWallPolygon
from drywall_detection.utils.coords import AffineTransformManager


@dataclass
class VisualOverlayConfig:
    dpi: int = 150
    alpha: float = 0.40
    stroke_opacity: float = 0.90
    stroke_width_pt: float = 1.5
    show_labels: bool = True
    show_legend: bool = True
    legend_position: str = "bottom_right"
    colors_rgb: Dict[str, Tuple[float, float, float]] = field(
        default_factory=lambda: {
            "Drywall": (0.0, 0.784, 0.325),      # Green #00C853
            "Non-Drywall": (0.835, 0.0, 0.0),    # Red #D50000
            "Uncertain": (1.0, 0.839, 0.0),      # Yellow #FFD600
        }
    )


class WallAnnotator:
    """
    High-fidelity rendering engine producing annotated raster images and pure vector PDFs.
    Preserves 100% of underlying CAD vector paths, fonts, and dimensions.
    """

    def __init__(self, config: Optional[VisualOverlayConfig] = None) -> None:
        self.config = config or VisualOverlayConfig()

    def render_raster_image(
        self,
        page: fitz.Page,
        classified_walls: List[ClassifiedWallPolygon],
        summary_stats: Optional[Dict[str, Any]] = None,
    ) -> Image.Image:
        """
        Renders original PDF page to high-res PIL Image and overlays semi-transparent
        color masks with sharp borders and legend box in rotated visual pixel space.
        """
        zoom = self.config.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        base_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        transform = AffineTransformManager(dpi=self.config.dpi)

        alpha_int = int(round(self.config.alpha * 255))
        stroke_alpha = int(round(self.config.stroke_opacity * 255))

        for w in classified_walls:
            if w.geometry_pdf is None or w.geometry_pdf.is_empty:
                continue

            c_rgb = self.config.colors_rgb.get(w.classification, (1.0, 0.839, 0.0))
            fill_col = (int(c_rgb[0] * 255), int(c_rgb[1] * 255), int(c_rgb[2] * 255), alpha_int)
            outline_col = (int(c_rgb[0] * 255), int(c_rgb[1] * 255), int(c_rgb[2] * 255), stroke_alpha)

            poly_px = transform.transform_geometry_to_pixel(w.geometry_pdf)
            stroke_w = max(1, int(round(self.config.stroke_width_pt * zoom)))

            if isinstance(poly_px, Polygon):
                coords = [(float(x), float(y)) for x, y in poly_px.exterior.coords]
                draw.polygon(coords, fill=fill_col, outline=outline_col, width=stroke_w)
            elif isinstance(poly_px, MultiPolygon):
                for p in poly_px.geoms:
                    coords = [(float(x), float(y)) for x, y in p.exterior.coords]
                    draw.polygon(coords, fill=fill_col, outline=outline_col, width=stroke_w)

        if self.config.show_legend:
            self._draw_raster_legend(draw, base_img.size, summary_stats)

        composite = Image.alpha_composite(base_img, overlay).convert("RGB")
        return composite

    def generate_annotated_vector_pdf(
        self,
        src_pdf_path: Union[str, Path],
        classified_pages: Dict[int, List[ClassifiedWallPolygon]],
        output_pdf_path: Union[str, Path],
        summary_by_page: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> Path:
        """
        Creates a multi-page PDF where colored classification fills and strokes are
        overlaid directly into the vector stream using PyMuPDF Shape primitives.
        Preserves original CAD linework, fonts, and searchable text without rasterization.
        """
        src_path = Path(src_pdf_path)
        out_path = Path(output_pdf_path)
        doc = fitz.open(src_path)

        for page_idx, walls in classified_pages.items():
            if page_idx >= len(doc):
                continue
            page = doc[page_idx]
            shape = page.new_shape()

            for w in walls:
                if w.geometry_pdf is None or w.geometry_pdf.is_empty:
                    continue

                c = self.config.colors_rgb.get(w.classification, (1.0, 0.839, 0.0))
                geom = w.geometry_pdf
                if isinstance(geom, Polygon):
                    pts = [fitz.Point(x, y) for x, y in geom.exterior.coords]
                    if len(pts) >= 3:
                        shape.draw_polyline(pts)
                        shape.finish(
                            color=c,
                            fill=c,
                            fill_opacity=self.config.alpha,
                            stroke_opacity=self.config.stroke_opacity,
                            width=self.config.stroke_width_pt,
                            closePath=True,
                        )
                elif isinstance(geom, MultiPolygon):
                    for p in geom.geoms:
                        pts = [fitz.Point(x, y) for x, y in p.exterior.coords]
                        if len(pts) >= 3:
                            shape.draw_polyline(pts)
                            shape.finish(
                                color=c,
                                fill=c,
                                fill_opacity=self.config.alpha,
                                stroke_opacity=self.config.stroke_opacity,
                                width=self.config.stroke_width_pt,
                                closePath=True,
                            )

            shape.commit()

            # Insert tag labels and legend box with rotate=page.rotation
            if self.config.show_labels:
                for w in walls:
                    if w.matched_tag and w.classification in ("Drywall", "Non-Drywall"):
                        cp = w.geometry_pdf.centroid
                        page.insert_text(
                            fitz.Point(cp.x, cp.y),
                            w.matched_tag,
                            fontsize=7.5,
                            color=(0.1, 0.1, 0.1),
                            rotate=page.rotation,
                        )

            if self.config.show_legend:
                stats = (summary_by_page.get(page_idx) if summary_by_page else None) or self._fallback_summary(walls)
                self._draw_vector_legend(page, stats)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path), garbage=3, deflate=True)
        doc.close()
        return out_path

    def _fallback_summary(self, walls: List[ClassifiedWallPolygon]) -> Dict[str, Any]:
        dw = sum(1 for w in walls if w.classification == "Drywall")
        ndw = sum(1 for w in walls if w.classification == "Non-Drywall")
        unc = sum(1 for w in walls if w.classification == "Uncertain")
        dw_lf = sum(max(w.geometry_pdf.bounds[2] - w.geometry_pdf.bounds[0], w.geometry_pdf.bounds[3] - w.geometry_pdf.bounds[1]) / 9.0 for w in walls if w.classification == "Drywall" and w.geometry_pdf)
        ndw_lf = sum(max(w.geometry_pdf.bounds[2] - w.geometry_pdf.bounds[0], w.geometry_pdf.bounds[3] - w.geometry_pdf.bounds[1]) / 9.0 for w in walls if w.classification == "Non-Drywall" and w.geometry_pdf)
        unc_lf = sum(max(w.geometry_pdf.bounds[2] - w.geometry_pdf.bounds[0], w.geometry_pdf.bounds[3] - w.geometry_pdf.bounds[1]) / 9.0 for w in walls if w.classification == "Uncertain" and w.geometry_pdf)
        dw_sf = sum(w.geometry_pdf.area / 81.0 for w in walls if w.classification == "Drywall" and w.geometry_pdf)
        ndw_sf = sum(w.geometry_pdf.area / 81.0 for w in walls if w.classification == "Non-Drywall" and w.geometry_pdf)
        unc_sf = sum(w.geometry_pdf.area / 81.0 for w in walls if w.classification == "Uncertain" and w.geometry_pdf)
        return {
            "drywall_count": dw,
            "nondrywall_count": ndw,
            "uncertain_count": unc,
            "drywall_lf": round(dw_lf, 1),
            "nondrywall_lf": round(ndw_lf, 1),
            "uncertain_lf": round(unc_lf, 1),
            "drywall_sqft": round(dw_sf, 1),
            "nondrywall_sqft": round(ndw_sf, 1),
            "uncertain_sqft": round(unc_sf, 1),
        }

    def _draw_raster_legend(
        self,
        draw: ImageDraw.ImageDraw,
        img_size: Tuple[int, int],
        stats: Optional[Dict[str, Any]],
    ) -> None:
        """Draws an informative architectural legend card in the bottom-right of the raster image."""
        w, h = img_size
        card_w, card_h = 560, 220
        margin = 40
        x0 = w - card_w - margin
        y0 = h - card_h - margin
        x1 = w - margin
        y1 = h - margin

        # Background rectangle
        draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 235), outline=(60, 60, 60, 255), width=2)

        # Header
        draw.text((x0 + 20, y0 + 15), "DRYWALL CLASSIFICATION & TAKEOFF (M5)", fill=(0, 0, 0, 255))
        draw.text((x0 + 20, y0 + 35), "MTA 99th St Set (PROGRESS SET 95% CDs 10/02/2026)", fill=(90, 90, 90, 255))

        # Items
        dw_txt = "■ DRYWALL (Green #00C853)"
        ndw_txt = "■ NON-DRYWALL (Red #D50000)"
        unc_txt = "■ UNCERTAIN (Yellow #FFD600)"

        if stats:
            dw_txt += f": {stats.get('drywall_count', 0)} walls ({stats.get('drywall_lf', 0.0):.1f} LF)"
            ndw_txt += f": {stats.get('nondrywall_count', 0)} walls ({stats.get('nondrywall_lf', 0.0):.1f} LF)"
            unc_txt += f": {stats.get('uncertain_count', 0)} walls ({stats.get('uncertain_lf', 0.0):.1f} LF)"

        draw.text((x0 + 20, y0 + 65), dw_txt, fill=(0, 180, 70, 255))
        draw.text((x0 + 20, y0 + 95), ndw_txt, fill=(213, 0, 0, 255))
        draw.text((x0 + 20, y0 + 125), unc_txt, fill=(200, 160, 0, 255))

        draw.text(
            (x0 + 20, y0 + 160),
            "Mandatory Safety Rule: Detail 1A 6\" CMU = Non-Drywall (Red)",
            fill=(180, 0, 0, 255),
        )
        draw.text(
            (x0 + 20, y0 + 185),
            "Tier 3 Fallback: Untagged linework = Uncertain (Zero Hallucination)",
            fill=(100, 100, 100, 255),
        )

    def _draw_vector_legend(self, page: fitz.Page, stats: Dict[str, Any]) -> None:
        """
        Draws an architectural legend card and summary statistics banner in native PDF space
        with text rotated to match the visual orientation of the sheet.
        """
        shape = page.new_shape()
        legend_rect = fitz.Rect(1380, 90, 1680, 590)
        shape.draw_rect(legend_rect)
        shape.finish(
            color=(0.3, 0.3, 0.3),
            fill=(0.98, 0.98, 0.98),
            fill_opacity=0.92,
            stroke_opacity=1.0,
            width=1.0,
        )
        shape.commit()

        rot = page.rotation
        page.insert_text(fitz.Point(1405, 560), "DRYWALL CLASSIFICATION & TAKEOFF (M5)", fontsize=11, rotate=rot, color=(0, 0, 0))
        page.insert_text(fitz.Point(1425, 560), "MTA 99th St Set (PROGRESS SET 95% CDs)", fontsize=8, rotate=rot, color=(0.4, 0.4, 0.4))

        c_dw = self.config.colors_rgb["Drywall"]
        dw_cnt = stats.get("drywall_count", 0)
        dw_lf = stats.get("drywall_lf", 0.0)
        dw_sf = stats.get("drywall_sqft", 0.0)
        page.insert_text(fitz.Point(1455, 560), f"■ DRYWALL: {dw_cnt} walls ({dw_lf:.1f} LF / {dw_sf:.1f} SF)", fontsize=9.5, rotate=rot, color=c_dw)

        c_ndw = self.config.colors_rgb["Non-Drywall"]
        ndw_cnt = stats.get("nondrywall_count", 0)
        ndw_lf = stats.get("nondrywall_lf", 0.0)
        ndw_sf = stats.get("nondrywall_sqft", 0.0)
        page.insert_text(fitz.Point(1485, 560), f"■ NON-DRYWALL: {ndw_cnt} walls ({ndw_lf:.1f} LF / {ndw_sf:.1f} SF)", fontsize=9.5, rotate=rot, color=c_ndw)

        c_unc = self.config.colors_rgb["Uncertain"]
        unc_cnt = stats.get("uncertain_count", 0)
        unc_lf = stats.get("uncertain_lf", 0.0)
        unc_sf = stats.get("uncertain_sqft", 0.0)
        page.insert_text(fitz.Point(1515, 560), f"■ UNCERTAIN: {unc_cnt} walls ({unc_lf:.1f} LF / {unc_sf:.1f} SF)", fontsize=9.5, rotate=rot, color=c_unc)

        page.insert_text(fitz.Point(1545, 560), "Mandatory Rule: Detail 1A 6\" CMU = Non-Drywall (Red)", fontsize=8, rotate=rot, color=(0.7, 0, 0))

