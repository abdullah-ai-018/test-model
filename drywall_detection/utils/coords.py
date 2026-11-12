"""
Mathematical coordinate transformation module.
Provides exact, reversible affine transformations between unrotated native PDF vector
point space [0..1728, 0..2592] and rotated visual pixel space [0..2592*scale, 0..1728*scale]
under 90-degree clockwise (and general multi-quadrant) rotations.
"""

from __future__ import annotations
import math
from typing import Sequence, Tuple, Union
import numpy as np
from shapely.geometry.base import BaseGeometry
from shapely import transform as shapely_transform

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
)

VALID_ROTATIONS = (0, 90, 180, 270)


def _validate_params(
    dpi: int,
    rotation: int,
) -> None:
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if rotation not in VALID_ROTATIONS:
        raise ValueError(
            f"Unsupported rotation: {rotation}. Supported rotations are {VALID_ROTATIONS}"
        )


def get_forward_matrix(
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Returns the 3x3 homogeneous affine transformation matrix mapping from
    unrotated native PDF coordinates to rotated visual pixel coordinates.
    """
    _validate_params(dpi, rotation)
    s = dpi / float(BASE_DPI)

    if rotation == 0:
        return np.array([
            [s,   0.0, 0.0],
            [0.0, s,   0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)
    elif rotation == 90:
        return np.array([
            [0.0, -s,  s * page_height],
            [s,    0.0, 0.0           ],
            [0.0,  0.0, 1.0           ],
        ], dtype=np.float64)
    elif rotation == 180:
        return np.array([
            [-s,  0.0, s * page_width ],
            [0.0, -s,  s * page_height],
            [0.0, 0.0, 1.0           ],
        ], dtype=np.float64)
    elif rotation == 270:
        return np.array([
            [0.0, s,   0.0           ],
            [-s,  0.0, s * page_width],
            [0.0, 0.0, 1.0           ],
        ], dtype=np.float64)
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")


def get_inverse_matrix(
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Returns the 3x3 homogeneous affine transformation matrix mapping from
    rotated visual pixel coordinates back to unrotated native PDF coordinates.
    """
    _validate_params(dpi, rotation)
    s = dpi / float(BASE_DPI)
    inv_s = 1.0 / s

    if rotation == 0:
        return np.array([
            [inv_s, 0.0,   0.0],
            [0.0,   inv_s, 0.0],
            [0.0,   0.0,   1.0],
        ], dtype=np.float64)
    elif rotation == 90:
        return np.array([
            [0.0,    inv_s, 0.0        ],
            [-inv_s, 0.0,   page_height],
            [0.0,    0.0,   1.0        ],
        ], dtype=np.float64)
    elif rotation == 180:
        return np.array([
            [-inv_s, 0.0,    page_width ],
            [0.0,    -inv_s, page_height],
            [0.0,    0.0,    1.0        ],
        ], dtype=np.float64)
    elif rotation == 270:
        return np.array([
            [0.0,   -inv_s, page_width],
            [inv_s, 0.0,    0.0       ],
            [0.0,   0.0,    1.0       ],
        ], dtype=np.float64)
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")


def pdf_to_pixel(
    x: float,
    y: float,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> Tuple[float, float]:
    """
    Transforms an unrotated native PDF point (x, y) in points to visual rotated pixel space.

    Formula for 90 deg rotation:
        px = (page_height - y) * (dpi / 72.0)
        py = x * (dpi / 72.0)
    """
    _validate_params(dpi, rotation)
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"Coordinates must be finite, got ({x}, {y})")

    scale = dpi / float(BASE_DPI)
    if rotation == 0:
        px = x * scale
        py = y * scale
    elif rotation == 90:
        px = (page_height - y) * scale
        py = x * scale
    elif rotation == 180:
        px = (page_width - x) * scale
        py = (page_height - y) * scale
    elif rotation == 270:
        px = y * scale
        py = (page_width - x) * scale
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")

    return (float(px), float(py))


def pixel_to_pdf(
    px: float,
    py: float,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> Tuple[float, float]:
    """
    Transforms a rotated visual pixel point (px, py) back to unrotated native PDF points.

    Formula for 90 deg rotation:
        x = py / (dpi / 72.0)
        y = page_height - px / (dpi / 72.0)
    """
    _validate_params(dpi, rotation)
    if not (math.isfinite(px) and math.isfinite(py)):
        raise ValueError(f"Pixel coordinates must be finite, got ({px}, {py})")

    scale = dpi / float(BASE_DPI)
    if rotation == 0:
        x = px / scale
        y = py / scale
    elif rotation == 90:
        x = py / scale
        y = page_height - (px / scale)
    elif rotation == 180:
        x = page_width - (px / scale)
        y = page_height - (py / scale)
    elif rotation == 270:
        x = page_width - (py / scale)
        y = px / scale
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")

    return (float(x), float(y))


def pdf_bbox_to_pixel(
    bbox: Tuple[float, float, float, float],
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> Tuple[float, float, float, float]:
    """
    Transforms an axis-aligned bounding box (x0, y0, x1, y1) in unrotated native PDF space
    to a normalized axis-aligned bounding box (px_min, py_min, px_max, py_max) in rotated pixel space.
    """
    _validate_params(dpi, rotation)
    x0, y0, x1, y1 = bbox
    if x0 > x1 or y0 > y1:
        raise ValueError(f"Invalid bounding box ordering: ({x0}, {y0}, {x1}, {y1})")

    corners = [
        pdf_to_pixel(x0, y0, dpi, page_width, page_height, rotation),
        pdf_to_pixel(x1, y0, dpi, page_width, page_height, rotation),
        pdf_to_pixel(x1, y1, dpi, page_width, page_height, rotation),
        pdf_to_pixel(x0, y1, dpi, page_width, page_height, rotation),
    ]
    px_coords = [c[0] for c in corners]
    py_coords = [c[1] for c in corners]
    return (min(px_coords), min(py_coords), max(px_coords), max(py_coords))


def pixel_bbox_to_pdf(
    pbbox: Tuple[float, float, float, float],
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> Tuple[float, float, float, float]:
    """
    Transforms an axis-aligned bounding box (px0, py0, px1, py1) in rotated pixel space
    back to a normalized axis-aligned bounding box (x_min, y_min, x_max, y_max) in unrotated native PDF space.
    """
    _validate_params(dpi, rotation)
    px0, py0, px1, py1 = pbbox
    if px0 > px1 or py0 > py1:
        raise ValueError(f"Invalid pixel bounding box ordering: ({px0}, {py0}, {px1}, {py1})")

    corners = [
        pixel_to_pdf(px0, py0, dpi, page_width, page_height, rotation),
        pixel_to_pdf(px1, py0, dpi, page_width, page_height, rotation),
        pixel_to_pdf(px1, py1, dpi, page_width, page_height, rotation),
        pixel_to_pdf(px0, py1, dpi, page_width, page_height, rotation),
    ]
    x_coords = [c[0] for c in corners]
    y_coords = [c[1] for c in corners]
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


# Aliases for interface compliance
transform_bbox_to_pixel = pdf_bbox_to_pixel
transform_bbox_to_pdf = pixel_bbox_to_pdf


def pdf_points_to_pixel(
    points: np.ndarray,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Vectorized forward transformation of an (N, 2) array of PDF points to pixel space.
    """
    _validate_params(dpi, rotation)
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"Expected (N, 2) array of points, got shape {pts.shape}")

    scale = dpi / float(BASE_DPI)
    out = np.empty_like(pts)
    if rotation == 0:
        out[:, 0] = pts[:, 0] * scale
        out[:, 1] = pts[:, 1] * scale
    elif rotation == 90:
        out[:, 0] = (page_height - pts[:, 1]) * scale
        out[:, 1] = pts[:, 0] * scale
    elif rotation == 180:
        out[:, 0] = (page_width - pts[:, 0]) * scale
        out[:, 1] = (page_height - pts[:, 1]) * scale
    elif rotation == 270:
        out[:, 0] = pts[:, 1] * scale
        out[:, 1] = (page_width - pts[:, 0]) * scale
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")

    return out


def pixel_points_to_pdf(
    pixels: np.ndarray,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Vectorized inverse transformation of an (N, 2) array of pixel points to PDF space.
    """
    _validate_params(dpi, rotation)
    pxs = np.asarray(pixels, dtype=np.float64)
    if pxs.ndim != 2 or pxs.shape[1] != 2:
        raise ValueError(f"Expected (N, 2) array of pixel coordinates, got shape {pxs.shape}")

    scale = dpi / float(BASE_DPI)
    out = np.empty_like(pxs)
    if rotation == 0:
        out[:, 0] = pxs[:, 0] / scale
        out[:, 1] = pxs[:, 1] / scale
    elif rotation == 90:
        out[:, 0] = pxs[:, 1] / scale
        out[:, 1] = page_height - (pxs[:, 0] / scale)
    elif rotation == 180:
        out[:, 0] = page_width - (pxs[:, 0] / scale)
        out[:, 1] = page_height - (pxs[:, 1] / scale)
    elif rotation == 270:
        out[:, 0] = page_width - (pxs[:, 1] / scale)
        out[:, 1] = pxs[:, 0] / scale
    else:
        raise ValueError(f"Unsupported rotation: {rotation}")

    return out


def pdf_geom_to_pixel(
    geom: BaseGeometry,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> BaseGeometry:
    """
    Transforms any Shapely geometry (Point, LineString, Polygon, MultiPolygon, etc.)
    from native unrotated PDF point space into rotated visual pixel space.
    Preserves topological validity and winding orientation.
    """
    _validate_params(dpi, rotation)
    if geom is None or geom.is_empty:
        return geom

    def _transform_coords(coords: np.ndarray) -> np.ndarray:
        return pdf_points_to_pixel(coords, dpi, page_width, page_height, rotation)

    return shapely_transform(geom, _transform_coords)


def pixel_geom_to_pdf(
    geom: BaseGeometry,
    dpi: int = DEFAULT_DPI,
    page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> BaseGeometry:
    """
    Transforms any Shapely geometry from rotated visual pixel space back into
    native unrotated PDF point space.
    """
    _validate_params(dpi, rotation)
    if geom is None or geom.is_empty:
        return geom

    def _transform_coords(coords: np.ndarray) -> np.ndarray:
        return pixel_points_to_pdf(coords, dpi, page_width, page_height, rotation)

    return shapely_transform(geom, _transform_coords)


# Aliases for interface compliance
transform_polygon_to_pixel = pdf_geom_to_pixel
transform_polygon_to_pdf = pixel_geom_to_pdf


class AffineTransformManager:
    """
    Production-grade affine transformation manager providing exact, bidirectional
    coordinate mappings between native unrotated PDF point space [0..W, 0..H] and
    rotated visual pixel space [0..W_vis*s, 0..H_vis*s] across all standard rotations.
    """

    def __init__(
        self,
        dpi: int = DEFAULT_DPI,
        page_width: float = MASTER_PDF_MEDIABOX_WIDTH_PT,
        page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
        rotation: int = MASTER_PDF_ROTATION_DEG,
    ) -> None:
        self.dpi = dpi
        self.page_width = float(page_width)
        self.page_height = float(page_height)
        self.rotation = int(rotation)
        self.scale = self.dpi / float(BASE_DPI)

    @property
    def visual_width_pt(self) -> float:
        return self.page_height if self.rotation in (90, 270) else self.page_width

    @property
    def visual_height_pt(self) -> float:
        return self.page_width if self.rotation in (90, 270) else self.page_height

    @property
    def visual_dimensions_px(self) -> Tuple[int, int]:
        """Returns (width_px, height_px) of rendered visual raster image."""
        w_px = int(round(self.visual_width_pt * self.scale))
        h_px = int(round(self.visual_height_pt * self.scale))
        return (w_px, h_px)

    def pdf_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """Transforms native unrotated PDF point (x, y) to visual rotated pixel coordinates."""
        return pdf_to_pixel(x, y, dpi=self.dpi, page_width=self.page_width,
                            page_height=self.page_height, rotation=self.rotation)

    def pixel_to_pdf(self, px: float, py: float) -> Tuple[float, float]:
        """Transforms visual rotated pixel coordinates (px, py) back to native PDF point."""
        return pixel_to_pdf(px, py, dpi=self.dpi, page_width=self.page_width,
                            page_height=self.page_height, rotation=self.rotation)

    def pdf_bbox_to_pixel(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Transforms native PDF bounding box (x0, y0, x1, y1) to visual pixel bbox."""
        return pdf_bbox_to_pixel(bbox, dpi=self.dpi, page_width=self.page_width,
                                 page_height=self.page_height, rotation=self.rotation)

    def pixel_bbox_to_pdf(self, pbbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Transforms visual pixel bounding box (px0, py0, px1, py1) back to native PDF bbox."""
        return pixel_bbox_to_pdf(pbbox, dpi=self.dpi, page_width=self.page_width,
                                 page_height=self.page_height, rotation=self.rotation)

    def transform_geometry_to_pixel(self, geom: BaseGeometry) -> BaseGeometry:
        """Transforms any Shapely geometry from native PDF points to rotated visual pixel coordinates."""
        return pdf_geom_to_pixel(geom, dpi=self.dpi, page_width=self.page_width,
                                 page_height=self.page_height, rotation=self.rotation)

    def transform_geometry_to_pdf(self, geom: BaseGeometry) -> BaseGeometry:
        """Transforms any Shapely geometry from rotated visual pixels back to native PDF points."""
        return pixel_geom_to_pdf(geom, dpi=self.dpi, page_width=self.page_width,
                                 page_height=self.page_height, rotation=self.rotation)

    def pdf_points_to_pixel(self, points: np.ndarray) -> np.ndarray:
        return pdf_points_to_pixel(points, dpi=self.dpi, page_width=self.page_width,
                                   page_height=self.page_height, rotation=self.rotation)

    def pixel_points_to_pdf(self, pixels: np.ndarray) -> np.ndarray:
        return pixel_points_to_pdf(pixels, dpi=self.dpi, page_width=self.page_width,
                                   page_height=self.page_height, rotation=self.rotation)

    def get_forward_matrix(self) -> np.ndarray:
        return get_forward_matrix(dpi=self.dpi, page_width=self.page_width,
                                  page_height=self.page_height, rotation=self.rotation)

    def get_inverse_matrix(self) -> np.ndarray:
        return get_inverse_matrix(dpi=self.dpi, page_width=self.page_width,
                                  page_height=self.page_height, rotation=self.rotation)

