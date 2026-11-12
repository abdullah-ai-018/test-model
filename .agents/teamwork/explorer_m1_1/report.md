# Technical Implementation Design: Central Configuration, Coordinate Geometry & Hardware Profiling
**Document ID:** ARCH-M1-COORDS-HW-001  
**Author:** explorer_m1_1 (M1 Coords & Hardware Architecture Explorer)  
**Date:** 2026-11-08  
**Project:** QTO Engine — Isolated Drywall Detection Module (`drywall_detection/`)  
**Milestone:** M1 (Workspace and Dataset Audit)  
**Target Modules:**  
1. `drywall_detection/config.py`  
2. `drywall_detection/utils/coords.py`  
3. `drywall_detection/utils/hardware.py`  
**Reference Document Notice:** MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728 x 2592 pt unrotated MediaBox / 2592 x 1728 pt visual, Rotation 90° CW, "PROGRESS SET 95% CDs 10/02/2026"). This reference PDF represents a 95% CDs progress set, not an approved final construction document. Pages represent a single project and cannot prove cross-domain generalization.

---

## Executive Summary

This document establishes the comprehensive technical blueprint, exact mathematical derivations, functional contracts, and unit test specifications for three foundational components of the `drywall_detection` package:
1. **Central Configuration (`drywall_detection/config.py`)**: Centralizes all filesystem paths, reference PDF parameters (71 pages, 1728 x 2592 pt unrotated, 90° CW rotation), DPI scales, disk safety limits (5 GB free minimum, 10 GB download warning), 4-class classification guardrails, partition review lockfile definitions, and material precedence keywords (enforcing Tag 1A CMU non-drywall classification).
2. **Reversible Affine Coordinate Transformation (`drywall_detection/utils/coords.py`)**: Establishes an exact, bijective mathematical coordinate transformation ($M$ and $M^{-1}$) between native PDF vector point space `[0..1728, 0..2592]` pt and visual raster pixel space `[0..2592*scale, 0..1728*scale]` px under 90° clockwise rotation. Provides forward and inverse mappings for scalar points, bounding boxes, vectorized numpy arrays, and arbitrary Shapely geometries (preserving topological validity and orientation). Proven roundtrip bijection: $|\Delta x| < 10^{-4}$ pt, $|\Delta y| < 10^{-4}$ pt.
3. **Hardware Environment Detection & Dynamic Configuration (`drywall_detection/utils/hardware.py`)**: Probes host hardware (CPU, RAM, GPU, CUDA, VRAM, disk space, Python, PyTorch) into a structured `HardwareProfile`. Implements a 5-tier auto-configuration engine (`TrainingConfig`) that scales segmentation batch sizes (1 to 16), gradient accumulation steps (1 to 8), input resolutions (256 to 512), and dataloader worker counts based on detected memory. Specifically accommodates the current constrained host environment (0.72–0.90 GB free RAM, CPU-only PyTorch) by configuring batch size 2, resolution 256x256, and 0 workers, while maintaining 100% Google Colab compatibility for GPU acceleration.

---

## 1. Central Configuration: `drywall_detection/config.py`

### 1.1 Architectural Purpose & Requirements
`config.py` serves as the single source of truth for the entire `drywall_detection` pipeline. All submodules (`audit`, `data`, `vector`, `models`, `classification`, `pipeline`, and `tests`) import constants and directory references from `config.py`.

Key requirements addressed:
- **Reference PDF Grounding**: Encapsulates verified metadata for MTA Contract C-48526 (`file-1793194362940-560626729.pdf`).
- **Disk Safety Guardrails**: Enforces 5.0 GB minimum free disk space and the mandatory 10.0 GB threshold requiring user notification.
- **4-Class Material Precedence Guardrail**: Defines classes 0 (Background), 1 (Drywall, Green), 2 (Non-Drywall, Red), and 3 (Uncertain, Yellow).
- **Tag 1A Safety Rule**: Hardcodes Tag 1A as Non-Drywall (CMU masonry).
- **Human Review Protocol**: Defines `REVIEW_REQUIRED.lock` and Exit Code `2`.
- **Dynamic Path Resolution**: Anchors all paths to `PACKAGE_ROOT` and `WORKSPACE_ROOT` with environment variable overrides.

### 1.2 Exact Implementation Blueprint for `drywall_detection/config.py`

```python
"""
Central configuration module for the drywall_detection package.
All paths, geometry constants, hardware limits, and classification rules
are defined here as the single source of truth.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Tuple

# ==============================================================================
# 1. DIRECTORY & PATH DEFINITIONS
# ==============================================================================
# Base directory anchors
PACKAGE_ROOT: Path = Path(__file__).resolve().parent
WORKSPACE_ROOT: Path = PACKAGE_ROOT.parent

# Subdirectory structure
DATA_DIR: Path = PACKAGE_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
QC_SAMPLES_DIR: Path = DATA_DIR / "qc_samples"
CACHE_DIR: Path = DATA_DIR / "cache"

REPORTS_DIR: Path = PACKAGE_ROOT / "reports"
CHECKPOINTS_DIR: Path = PACKAGE_ROOT / "checkpoints"
BEST_MODEL_DIR: Path = CHECKPOINTS_DIR / "best_model"
CONFIG_DIR: Path = PACKAGE_ROOT / "config"
TESTS_DIR: Path = PACKAGE_ROOT / "tests"

# Ensure essential runtime directories exist
for _dir in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, QC_SAMPLES_DIR, CACHE_DIR, REPORTS_DIR, CHECKPOINTS_DIR, BEST_MODEL_DIR, CONFIG_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 2. MASTER REFERENCE PDF SPECIFICATION
# ==============================================================================
# Default path to the master 71-page architectural interior set
DEFAULT_MASTER_PDF_PATH: Path = Path(
    os.environ.get(
        "DRYWALL_MASTER_PDF_PATH",
        r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf"
    )
)

# Reference document notice (Mandatory citation)
REFERENCE_SET_NOTICE: str = (
    "MTA Contract C-48526, 99th Street Phase 2 Interior Set "
    "(71 pages, 1728x2592 pt unrotated, 90 deg CW rotation, 'PROGRESS SET 95% CDs 10/02/2026'). "
    "Notice: This reference PDF represents a 95% CDs progress set, not an approved final construction "
    "document. Pages represent a single project and cannot prove cross-domain generalization."
)

# Native geometric dimensions of unrotated PDF MediaBox (Points, 72 pt = 1 inch)
MASTER_PDF_TOTAL_PAGES: int = 71
MASTER_PDF_MEDIABOX_WIDTH_PT: float = 1728.0   # 24 inches
MASTER_PDF_MEDIABOX_HEIGHT_PT: float = 2592.0  # 36 inches
MASTER_PDF_ROTATION_DEG: int = 90              # Clockwise rotation on all 71 pages

# Rendered visual dimensions at base resolution (72 DPI)
MASTER_PDF_VISUAL_WIDTH_PT: float = 2592.0     # Landscape visual width
MASTER_PDF_VISUAL_HEIGHT_PT: float = 1728.0    # Landscape visual height

# Auxiliary Reference Datasets in Downloads directory
USMAN_GROUND_TRUTH_PDF: Path = Path(
    os.environ.get(
        "DRYWALL_USMAN_GT_PDF",
        r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf"
    )
)
RELEVANT_FULL_PAGES_PDF: Path = Path(
    os.environ.get(
        "DRYWALL_RELEVANT_PAGES_PDF",
        r"C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf"
    )
)
ANNOTATED_FLOOR_PLANS_PDF: Path = Path(
    os.environ.get(
        "DRYWALL_ANNOTATED_PLANS_PDF",
        r"C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf"
    )
)

# Critical Sheet Index Mapping (0-indexed page indices)
SHEET_INDEX_MAP: Dict[str, int] = {
    "COVER": 0,
    "G-001": 1,
    "G-002": 2,    # Master Sheet List / Index
    "G-003": 3,
    "A-100": 13,   # Cellar Construction Plan
    "A-101": 14,   # First Floor Construction Plan
    "A-102": 15,   # Second Floor Construction Plan
    "A-103": 16,   # Third Floor Construction Plan
    "A-104": 17,   # Fourth Floor Construction Plan
    "A-105": 18,   # Roof Construction Plan
    "A-900": 62,   # Partition Types Sheet I (Types 1A-1E, 2B-2C, 3A, 3D, 5B, 5D, 5E)
    "A-901": 63,   # Partition Types Sheet II (Types 7A-7G, 8A, GL1, GL2, 09, 10, 11)
}


# ==============================================================================
# 3. RENDERING & DPI CONFIGURATION
# ==============================================================================
BASE_DPI: int = 72
DEFAULT_DPI: int = 150       # Standard resolution for segmentation & vector alignment
HIGH_RES_DPI: int = 300      # High-detail inspection / publication quality
THUMBNAIL_DPI: int = 72      # Fast preview resolution


# ==============================================================================
# 4. DISK & STORAGE SAFETY LIMITS
# ==============================================================================
# Minimum free disk space (GB) required on working drive before starting heavy operations
DISK_FREE_MIN_GB: float = 5.0

# Mandatory notification threshold: Downloads or dataset extractions > 10 GB
# require explicit user notification / prompt before downloading.
DISK_LARGE_DOWNLOAD_THRESHOLD_GB: float = 10.0

# Maximum local temporary cache ceiling
MAX_CACHE_SIZE_GB: float = 8.0


# ==============================================================================
# 5. 4-CLASS MATERIAL CLASSIFICATION & GUARDRAILS
# ==============================================================================
# Class ID enumeration
CLASS_BACKGROUND: int = 0
CLASS_DRYWALL: int = 1
CLASS_NON_DRYWALL: int = 2
CLASS_UNCERTAIN: int = 3
NUM_CLASSES: int = 4

CLASS_NAMES: Dict[int, str] = {
    CLASS_BACKGROUND: "Background",
    CLASS_DRYWALL: "Drywall",
    CLASS_NON_DRYWALL: "Non-Drywall",
    CLASS_UNCERTAIN: "Uncertain",
}

# Standardized visualization colors
CLASS_COLORS_HEX: Dict[str, str] = {
    "Background": "#FFFFFF",
    "Drywall": "#00C853",       # Vibrant Green
    "Non-Drywall": "#D50000",   # High-visibility Red
    "Uncertain": "#FFD600",     # Alert Yellow
}

CLASS_COLORS_RGB: Dict[int, Tuple[int, int, int]] = {
    CLASS_BACKGROUND: (255, 255, 255),
    CLASS_DRYWALL: (0, 200, 83),
    CLASS_NON_DRYWALL: (213, 0, 0),
    CLASS_UNCERTAIN: (255, 214, 0),
}

CLASS_COLORS_BGR: Dict[int, Tuple[int, int, int]] = {
    CLASS_BACKGROUND: (255, 255, 255),
    CLASS_DRYWALL: (83, 200, 0),
    CLASS_NON_DRYWALL: (0, 0, 213),
    CLASS_UNCERTAIN: (0, 214, 255),
}

# Alpha transparency for mask overlay on architectural drawings
DEFAULT_OVERLAY_ALPHA: float = 0.40


# ==============================================================================
# 6. MATERIAL PRECEDENCE & SCHEDULE GUARDRAILS
# ==============================================================================
# Non-drywall material keywords (preempt any drywall classification)
NON_DRYWALL_KEYWORDS: List[str] = [
    "CMU", "MASONRY", "CONCRETE", "GLASS", "GLAZED",
    "GLAZING", "STEEL COLUMN", "BRICK", "STONE"
]

# Drywall material keywords (Gypsum Wallboard assemblies)
DRYWALL_KEYWORDS: List[str] = [
    "GYPSUM", "GWB", "DRYWALL", "SHEETROCK",
    "SHAFTLINER", "SCX", "TYPE X", "TYPE C", "FURRING"
]

# Critical safety enforcement: Detail 1A is strictly 6" CMU masonry block
TAG_1A_OVERRIDE_CLASS: int = CLASS_NON_DRYWALL
TAG_1A_OVERRIDE_REASON: str = "Detail 1A on Sheet A-900 is explicitly 6\" FIRE RATED CMU (masonry / Non-Drywall)."


# ==============================================================================
# 7. PARTITION SCHEDULE PARSING & HUMAN REVIEW STOPPING PROTOCOL
# ==============================================================================
SCHEDULE_CSV_PATH: Path = DATA_DIR / "partition_schedule_mapping.csv"
APPROVED_SCHEDULE_CSV_PATH: Path = DATA_DIR / "partition_schedule_mapping.approved.csv"
REVIEW_LOCKFILE_PATH: Path = DATA_DIR / "REVIEW_REQUIRED.lock"

# Process exit code when human review is required before proceeding
EXIT_CODE_AWAITING_REVIEW: int = 2

SCHEDULE_CSV_COLUMNS: List[str] = [
    "tag",
    "sheet_source",
    "detail_label",
    "stud_spec",
    "gypsum_spec",
    "cmu_masonry_spec",
    "fire_rating",
    "acoustic_insulation",
    "full_description",
    "proposed_class",
    "classification_reason",
    "human_approved_class",
    "review_status",
    "reviewer_notes",
]


# ==============================================================================
# 8. VECTOR SYMBOL & SPATIAL GEOMETRY TOLERANCES
# ==============================================================================
TAG_BOX_WIDTH_PT: float = 11.2
TAG_BOX_HEIGHT_PT: float = 11.3
TAG_BOX_TOLERANCE_PT: float = 2.5
LEADER_LINE_MAX_GAP_PT: float = 3.0
PROXIMITY_BUFFER_RADIUS_PT: float = 25.0
PROXIMITY_BUFFER_EXPANDED_RADIUS_PT: float = 50.0


# ==============================================================================
# 9. VALIDATION HELPER
# ==============================================================================
def validate_environment() -> Dict[str, bool]:
    """
    Validates essential environment configurations and filesystem paths.
    Returns a dictionary of status checks.
    """
    return {
        "master_pdf_exists": DEFAULT_MASTER_PDF_PATH.is_file(),
        "usman_gt_pdf_exists": USMAN_GROUND_TRUTH_PDF.is_file(),
        "package_root_writable": os.access(PACKAGE_ROOT, os.W_OK),
        "data_dir_exists": DATA_DIR.is_dir(),
        "reports_dir_exists": REPORTS_DIR.is_dir(),
        "checkpoints_dir_exists": CHECKPOINTS_DIR.is_dir(),
    }
```

---

## 2. Reversible Coordinate Transformations: `drywall_detection/utils/coords.py`

### 2.1 Mathematical Derivation & Proof of Bijection

Architectural floor plans in the reference set are authored in native CAD space:
- **Native Unrotated PDF Space** ($\mathbb{R}^2_{pdf}$):
  - Width: $W_{pdf} = 1728.0$ pt
  - Height: $H_{pdf} = 2592.0$ pt
  - Origin $(0, 0)$ is at the top-left corner of the unrotated page.
  - Coordinate range: $x \in [0.0, 1728.0]$, $y \in [0.0, 2592.0]$.
  - Native vector display lists (`page.get_drawings()`) and text bounding boxes (`page.get_text('words')`) are returned in this unrotated space.

- **Rotated Visual Raster Space** ($\mathbb{R}^2_{raster}$):
  - In the reference set, the PDF contains `/Rotate 90` (90° clockwise).
  - The rendered image width corresponds to the unrotated height: $W_{rot} = 2592.0$ pt.
  - The rendered image height corresponds to the unrotated width: $H_{rot} = 1728.0$ pt.
  - At resolution $DPI$, the scale factor is $S = \frac{DPI}{72.0}$.
  - Visual pixel dimensions: $W_{px} = 2592.0 \cdot S$, $H_{px} = 1728.0 \cdot S$.
  - At $150$ DPI: $W_{px} = 5400$, $H_{px} = 3600$.
  - At $72$ DPI: $W_{px} = 2592$, $H_{px} = 1728$.

#### 2.1.1 Forward Affine Mapping ($M$)
A point $(x, y) \in \mathbb{R}^2_{pdf}$ undergoes 90° clockwise rotation followed by translation and scaling:
$$\begin{pmatrix} px \\ py \\ 1 \end{pmatrix} = \begin{pmatrix} 0 & -S & S \cdot H_{pdf} \\ S & 0 & 0 \\ 0 & 0 & 1 \end{pmatrix} \begin{pmatrix} x \\ y \\ 1 \end{pmatrix}$$

Expanding into scalar algebraic equations:
$$px = S \cdot (H_{pdf} - y) = \frac{dpi}{72.0} \cdot (2592.0 - y)$$
$$py = S \cdot x = \frac{dpi}{72.0} \cdot x$$

#### 2.1.2 Inverse Affine Mapping ($M^{-1}$)
To map from visual pixel $(px, py) \in \mathbb{R}^2_{raster}$ back to unrotated native PDF space:
$$\begin{pmatrix} x \\ y \\ 1 \end{pmatrix} = \begin{pmatrix} 0 & \frac{1}{S} & 0 \\ -\frac{1}{S} & 0 & H_{pdf} \\ 0 & 0 & 1 \end{pmatrix} \begin{pmatrix} px \\ py \\ 1 \end{pmatrix}$$

Expanding into scalar algebraic equations:
$$x = \frac{py}{S} = py \cdot \frac{72.0}{dpi}$$
$$y = H_{pdf} - \frac{px}{S} = 2592.0 - px \cdot \frac{72.0}{dpi}$$

#### 2.1.3 Proof of Bijection and Determinant Invariance
1. **Invertibility**:
   The determinant of the forward matrix $M$ is:
   $$\det(M) = 0 \cdot 0 - (-S) \cdot S = +S^2$$
   Since $DPI > 0$, $S = \frac{dpi}{72.0} > 0 \implies \det(M) = S^2 > 0$.
   Because $\det(M) \ne 0$, $M$ is strictly invertible and bijective.
   Furthermore, because $\det(M) > 0$, the transformation preserves chirality (polygon orientation and winding order are preserved without reflection).

2. **Matrix Product Verification**:
   $$M \cdot M^{-1} = \begin{pmatrix} 0 & -S & S \cdot H \\ S & 0 & 0 \\ 0 & 0 & 1 \end{pmatrix} \begin{pmatrix} 0 & \frac{1}{S} & 0 \\ -\frac{1}{S} & 0 & H \\ 0 & 0 & 1 \end{pmatrix} = \begin{pmatrix} (-S)(-\frac{1}{S}) & 0 & (-S)(H) + S \cdot H \\ 0 & S \cdot \frac{1}{S} & 0 \\ 0 & 0 & 1 \end{pmatrix} = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix} = I_{3 \times 3}$$

3. **Roundtrip Invariant Proof**:
   Substituting $(px, py)$ into the inverse equations:
   $$x_{inv} = \frac{py}{S} = \frac{S \cdot x}{S} = x$$
   $$y_{inv} = H_{pdf} - \frac{px}{S} = H_{pdf} - \frac{S \cdot (H_{pdf} - y)}{S} = H_{pdf} - (H_{pdf} - y) = y$$
   Hence $|x_{inv} - x| = 0$ and $|y_{inv} - y| = 0$. In 64-bit IEEE 754 floating point representation, roundtrip error $|\Delta| < 10^{-14} \ll 10^{-4}$ pt.

#### 2.1.4 Bounding Box Mapping
For an axis-aligned bounding box $B = (x_0, y_0, x_1, y_1)$ where $x_0 \le x_1$ and $y_0 \le y_1$:
Because $px$ is a strictly decreasing function of $y$ ($px = S \cdot (H_{pdf} - y)$), the minimum $px$ corresponds to $y_1$ and the maximum $px$ corresponds to $y_0$:
$$px_{min} = S \cdot (H_{pdf} - y_1)$$
$$px_{max} = S \cdot (H_{pdf} - y_0)$$
$$py_{min} = S \cdot x_0$$
$$py_{max} = S \cdot x_1$$
Transformed Pixel Bounding Box:
$$\text{PixelBBox} = (px_{min}, py_{min}, px_{max}, py_{max})$$

Inverse Bounding Box Mapping:
Given $(px_0, py_0, px_1, py_1)$ with $px_0 \le px_1$ and $py_0 \le py_1$:
$$x_{min} = \frac{py_0}{S}, \quad x_{max} = \frac{py_1}{S}$$
$$y_{min} = H_{pdf} - \frac{px_1}{S}, \quad y_{max} = H_{pdf} - \frac{px_0}{S}$$
$$\text{PDFBBox} = (x_{min}, y_{min}, x_{max}, y_{max})$$

#### 2.1.5 Shapely Geometry Transformation
For general Shapely geometries (`Point`, `LineString`, `Polygon`, `MultiPolygon`, etc.), transformations are applied via `shapely.transform` using vectorized numpy operations on $(N, 2)$ coordinate blocks:
- Forward:
  $$\text{coords}[:, 0] = (H_{pdf} - \text{coords}[:, 1]) \cdot S$$
  $$\text{coords}[:, 1] = \text{coords}[:, 0]_{orig} \cdot S$$
- Inverse:
  $$\text{coords}[:, 0] = \text{coords}[:, 1]_{orig} / S$$
  $$\text{coords}[:, 1] = H_{pdf} - (\text{coords}[:, 0]_{orig} / S)$$
This preserves internal and external rings of Polygons without memory fragmentation or polygon self-intersections.

### 2.2 Exact Implementation Blueprint for `drywall_detection/utils/coords.py`

```python
"""
Mathematical coordinate transformation module.
Provides exact, reversible affine transformations between unrotated native PDF vector
point space [0..1728, 0..2592] and rotated visual pixel space [0..2592*scale, 0..1728*scale]
under 90-degree clockwise rotation.
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
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_ROTATION_DEG,
)


def get_forward_matrix(
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Returns the 3x3 homogeneous affine transformation matrix mapping from
    unrotated native PDF coordinates to rotated visual pixel coordinates.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if rotation != 90:
        raise NotImplementedError(f"Only 90 degree CW rotation supported, got {rotation}")
    
    s = dpi / float(BASE_DPI)
    return np.array([
        [0.0, -s,  s * page_height],
        [s,    0.0, 0.0           ],
        [0.0,  0.0, 1.0           ],
    ], dtype=np.float64)


def get_inverse_matrix(
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
    rotation: int = MASTER_PDF_ROTATION_DEG,
) -> np.ndarray:
    """
    Returns the 3x3 homogeneous affine transformation matrix mapping from
    rotated visual pixel coordinates back to unrotated native PDF coordinates.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if rotation != 90:
        raise NotImplementedError(f"Only 90 degree CW rotation supported, got {rotation}")
    
    s = dpi / float(BASE_DPI)
    inv_s = 1.0 / s
    return np.array([
        [0.0,    inv_s, 0.0        ],
        [-inv_s, 0.0,   page_height],
        [0.0,    0.0,   1.0        ],
    ], dtype=np.float64)


def pdf_to_pixel(
    x: float,
    y: float,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> Tuple[float, float]:
    """
    Transforms an unrotated native PDF point (x, y) in points to visual rotated pixel space.

    Formula:
        px = (page_height - y) * (dpi / 72.0)
        py = x * (dpi / 72.0)

    Args:
        x: X-coordinate in PDF unrotated points [0..1728]
        y: Y-coordinate in PDF unrotated points [0..2592]
        dpi: Target pixel rendering resolution (default 150)
        page_height: Unrotated page height in points (default 2592.0)

    Returns:
        (px, py) coordinates in visual rotated pixel space
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"Coordinates must be finite, got ({x}, {y})")

    scale = dpi / float(BASE_DPI)
    px = (page_height - y) * scale
    py = x * scale
    return (px, py)


def pixel_to_pdf(
    px: float,
    py: float,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> Tuple[float, float]:
    """
    Transforms a rotated visual pixel point (px, py) back to unrotated native PDF points.

    Formula:
        x = py / (dpi / 72.0)
        y = page_height - px / (dpi / 72.0)

    Args:
        px: X-coordinate in visual rotated pixel space [0..2592*scale]
        py: Y-coordinate in visual rotated pixel space [0..1728*scale]
        dpi: Pixel rendering resolution (default 150)
        page_height: Unrotated page height in points (default 2592.0)

    Returns:
        (x, y) coordinates in unrotated native PDF point space
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if not (math.isfinite(px) and math.isfinite(py)):
        raise ValueError(f"Pixel coordinates must be finite, got ({px}, {py})")

    scale = dpi / float(BASE_DPI)
    x = py / scale
    y = page_height - (px / scale)
    return (x, y)


def pdf_bbox_to_pixel(
    bbox: Tuple[float, float, float, float],
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> Tuple[float, float, float, float]:
    """
    Transforms an axis-aligned bounding box (x0, y0, x1, y1) in unrotated native PDF space
    to an axis-aligned bounding box (px_min, py_min, px_max, py_max) in rotated pixel space.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    x0, y0, x1, y1 = bbox
    if x0 > x1 or y0 > y1:
        raise ValueError(f"Invalid bounding box ordering: ({x0}, {y0}, {x1}, {y1})")

    scale = dpi / float(BASE_DPI)
    px_min = (page_height - y1) * scale
    px_max = (page_height - y0) * scale
    py_min = x0 * scale
    py_max = x1 * scale
    return (px_min, py_min, px_max, py_max)


def pixel_bbox_to_pdf(
    pbbox: Tuple[float, float, float, float],
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> Tuple[float, float, float, float]:
    """
    Transforms an axis-aligned bounding box (px0, py0, px1, py1) in rotated pixel space
    back to an axis-aligned bounding box (x_min, y_min, x_max, y_max) in unrotated native PDF space.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    px0, py0, px1, py1 = pbbox
    if px0 > px1 or py0 > py1:
        raise ValueError(f"Invalid pixel bounding box ordering: ({px0}, {py0}, {px1}, {py1})")

    scale = dpi / float(BASE_DPI)
    x_min = py0 / scale
    x_max = py1 / scale
    y_min = page_height - (px1 / scale)
    y_max = page_height - (px0 / scale)
    return (x_min, y_min, x_max, y_max)


def pdf_points_to_pixel(
    points: np.ndarray,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> np.ndarray:
    """
    Vectorized forward transformation of an (N, 2) array of PDF points to pixel space.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"Expected (N, 2) array of points, got shape {pts.shape}")

    scale = dpi / float(BASE_DPI)
    out = np.empty_like(pts)
    out[:, 0] = (page_height - pts[:, 1]) * scale
    out[:, 1] = pts[:, 0] * scale
    return out


def pixel_points_to_pdf(
    pixels: np.ndarray,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> np.ndarray:
    """
    Vectorized inverse transformation of an (N, 2) array of pixel points to PDF space.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    pxs = np.asarray(pixels, dtype=np.float64)
    if pxs.ndim != 2 or pxs.shape[1] != 2:
        raise ValueError(f"Expected (N, 2) array of pixel coordinates, got shape {pxs.shape}")

    scale = dpi / float(BASE_DPI)
    out = np.empty_like(pxs)
    out[:, 0] = pxs[:, 1] / scale
    out[:, 1] = page_height - (pxs[:, 0] / scale)
    return out


def pdf_geom_to_pixel(
    geom: BaseGeometry,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> BaseGeometry:
    """
    Transforms any Shapely geometry (Point, LineString, Polygon, MultiPolygon, etc.)
    from native unrotated PDF point space into rotated visual pixel space.
    Preserves topological validity and winding orientation.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if geom is None or geom.is_empty:
        return geom

    scale = dpi / float(BASE_DPI)

    def _transform_coords(coords: np.ndarray) -> np.ndarray:
        c = np.asarray(coords, dtype=np.float64)
        out = np.empty_like(c)
        out[:, 0] = (page_height - c[:, 1]) * scale
        out[:, 1] = c[:, 0] * scale
        return out

    return shapely_transform(geom, _transform_coords)


def pixel_geom_to_pdf(
    geom: BaseGeometry,
    dpi: int = DEFAULT_DPI,
    page_height: float = MASTER_PDF_MEDIABOX_HEIGHT_PT,
) -> BaseGeometry:
    """
    Transforms any Shapely geometry from rotated visual pixel space back into
    native unrotated PDF point space.
    """
    if dpi <= 0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    if geom is None or geom.is_empty:
        return geom

    scale = dpi / float(BASE_DPI)

    def _transform_coords(coords: np.ndarray) -> np.ndarray:
        c = np.asarray(coords, dtype=np.float64)
        out = np.empty_like(c)
        out[:, 0] = c[:, 1] / scale
        out[:, 1] = page_height - (c[:, 0] / scale)
        return out

    return shapely_transform(geom, _transform_coords)
```

---

## 3. Hardware Profiling & Dynamic Training Configuration: `drywall_detection/utils/hardware.py`

### 3.1 Architectural Purpose & Requirements
Milestone M1 requires empirical hardware environment detection and dynamic training adaptation.
Empirical survey findings of the target host:
- CPU: Intel Core 4 physical / 8 logical cores
- Integrated Graphics: Intel UHD Graphics 620, **no CUDA, no dedicated GPU**
- PyTorch: `2.1.0+cpu` (CPU execution only)
- Available System RAM: **~0.72–0.90 GB available** (extreme RAM constraint)
- Free Disk Space: C:\ has 12.84 GB free, E:\ has 30.45 GB free

`drywall_detection/utils/hardware.py` must:
1. Probe CPU, RAM, GPU/CUDA, disk space, and runtime libraries into a structured `HardwareProfile` dataclass.
2. Provide a dynamic 5-tier memory auto-configuration engine (`auto_configure_training`) that selects training hyperparameters (batch size, input resolution, gradient accumulation, num_workers, AMP).
3. Enforce disk space safety guards: check minimum available disk before downloads and trigger warning/rejection if download exceeds 10 GB.
4. Provide a standalone CLI interface for CI and human inspection.

### 3.2 Dynamic Configuration Hierarchy (5 Tiers)

| Tier | Environment Profile | Device | Batch Size | Grad Accum | Eff. Batch | Resolution | Workers | AMP | Recommended Backbone | Target Platform |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---|
| **1** | CUDA, VRAM $\ge 14$ GB | `cuda` | 16 | 1 | 16 | $512 \times 512$ | 4 | True | `resnet34` / `mit_b1` | Local GPU / Cloud A100 |
| **2** | CUDA, $6 \le \text{VRAM} < 14$ GB | `cuda` | 8 | 2 | 16 | $512 \times 512$ | 2 | True | `resnet34` / `mit_b0` | Local RTX 3060 / Colab T4 |
| **3** | CUDA, $\text{VRAM} < 6$ GB | `cuda` | 4 | 4 | 16 | $384 \times 384$ | 0 | True | `resnet18` / `mit_b0` | Low-end laptop GPU |
| **4** | CPU, RAM available $\ge 4.0$ GB | `cpu` | 4 | 4 | 16 | $256 \times 256$ | 0 | False | `resnet18` | Standard Dev PC |
| **5** | **Constrained Host** (CPU, RAM free $< 2.0$ GB) | `cpu` | **2** | **8** | **16** | **$256 \times 256$** | **0** | **False** | `resnet18` | **Current Local Host** |

*Crucial Host Adaptation*: On the current Windows host with ~0.72 GB free RAM and CPU-only PyTorch, `num_workers` MUST be set to `0` (avoiding multiprocessing worker fork memory duplication) and batch size to `2` with `gradient_accumulation_steps=8` to prevent Out-Of-Memory termination.

### 3.3 Exact Implementation Blueprint for `drywall_detection/utils/hardware.py`

```python
"""
Hardware environment detection and dynamic training configuration module.
Probes CPU, RAM, GPU, CUDA, disk space, and runtime libraries, and dynamically
configures training parameters tailored to local or cloud hardware constraints.
"""

from __future__ import annotations
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import psutil
import torch

from drywall_detection.config import (
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
    WORKSPACE_ROOT,
)


@dataclass
class HardwareProfile:
    """Represents a comprehensive snapshot of the host execution environment."""
    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_model: str
    ram_total_gb: float
    ram_available_gb: float
    ram_used_gb: float
    ram_percent: float
    cuda_available: bool
    gpu_count: int
    gpu_name: Optional[str]
    vram_total_gb: float
    vram_free_gb: float
    disk_path: str
    disk_total_gb: float
    disk_free_gb: float
    python_version: str
    torch_version: str
    torch_cuda_version: Optional[str]
    platform_system: str
    platform_release: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown_table(self) -> str:
        gpu_desc = f"{self.gpu_name} ({self.vram_total_gb:.2f} GB)" if self.cuda_available else "None (CPU only)"
        return (
            "| Resource | Detected Specification |\n"
            "|---|---|\n"
            f"| Host OS | {self.platform_system} {self.platform_release} ({platform.machine()}) |\n"
            f"| CPU Processor | {self.cpu_model} ({self.cpu_physical_cores}P / {self.cpu_logical_cores}L cores) |\n"
            f"| System RAM | Total: {self.ram_total_gb:.2f} GB, Available: {self.ram_available_gb:.2f} GB ({self.ram_percent}% used) |\n"
            f"| GPU / Acceleration | {gpu_desc} |\n"
            f"| CUDA Support | {'Available' if self.cuda_available else 'Unavailable'} |\n"
            f"| Primary Disk Space | Path: {self.disk_path}, Free: {self.disk_free_gb:.2f} GB / Total: {self.disk_total_gb:.2f} GB |\n"
            f"| Python Runtime | {self.python_version} ({sys.executable}) |\n"
            f"| PyTorch Runtime | {self.torch_version} (CUDA build: {self.torch_cuda_version or 'None'}) |\n"
        )


@dataclass
class TrainingConfig:
    """Auto-configured hyperparameters for segmentation model training."""
    device: str
    batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    image_height: int
    image_width: int
    num_workers: int
    pin_memory: bool
    mixed_precision: bool
    amp_dtype: str
    encoder_backbone: str
    max_epochs: int
    early_stopping_patience: int
    colab_recommended: bool
    hardware_tier: int
    tier_description: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def probe_hardware(disk_path: Union[str, Path] = WORKSPACE_ROOT) -> HardwareProfile:
    """
    Probes the host system and returns a complete HardwareProfile.
    """
    cpu_phys = psutil.cpu_count(logical=False) or 1
    cpu_log = psutil.cpu_count(logical=True) or 1
    vmem = psutil.virtual_memory()

    cuda_avail = torch.cuda.is_available()
    gpu_cnt = torch.cuda.device_count() if cuda_avail else 0
    gpu_nm = torch.cuda.get_device_name(0) if cuda_avail else None
    
    vram_tot = 0.0
    vram_fr = 0.0
    if cuda_avail and gpu_cnt > 0:
        props = torch.cuda.get_device_properties(0)
        vram_tot = props.total_memory / (1024.0 ** 3)
        try:
            mem_info = torch.cuda.mem_get_info()
            vram_fr = mem_info[0] / (1024.0 ** 3)
        except Exception:
            vram_fr = vram_tot

    resolved_disk = Path(disk_path).resolve()
    # On Windows, drive root is needed for shutil.disk_usage
    drive_root = resolved_disk.anchor or str(resolved_disk)
    try:
        usage = shutil.disk_usage(drive_root)
        disk_tot = usage.total / (1024.0 ** 3)
        disk_fr = usage.free / (1024.0 ** 3)
    except Exception:
        disk_tot = 0.0
        disk_fr = 0.0

    return HardwareProfile(
        cpu_physical_cores=cpu_phys,
        cpu_logical_cores=cpu_log,
        cpu_model=platform.processor() or "Unknown CPU",
        ram_total_gb=round(vmem.total / (1024.0 ** 3), 2),
        ram_available_gb=round(vmem.available / (1024.0 ** 3), 2),
        ram_used_gb=round(vmem.used / (1024.0 ** 3), 2),
        ram_percent=float(vmem.percent),
        cuda_available=cuda_avail,
        gpu_count=gpu_cnt,
        gpu_name=gpu_nm,
        vram_total_gb=round(vram_tot, 2),
        vram_free_gb=round(vram_fr, 2),
        disk_path=drive_root,
        disk_total_gb=round(disk_tot, 2),
        disk_free_gb=round(disk_fr, 2),
        python_version=sys.version.split()[0],
        torch_version=str(torch.__version__),
        torch_cuda_version=getattr(torch.version, "cuda", None),
        platform_system=platform.system(),
        platform_release=platform.release(),
    )


def auto_configure_training(
    profile: Optional[HardwareProfile] = None,
    task: str = "segmentation",
) -> TrainingConfig:
    """
    Dynamically configures training parameters based on detected or provided hardware profile.
    Implements a 5-tier memory and accelerator classification hierarchy.
    """
    if profile is None:
        profile = probe_hardware()

    # Tier 1: High-End Dedicated GPU (VRAM >= 14 GB)
    if profile.cuda_available and profile.vram_total_gb >= 14.0:
        return TrainingConfig(
            device="cuda",
            batch_size=16,
            gradient_accumulation_steps=1,
            effective_batch_size=16,
            image_height=512,
            image_width=512,
            num_workers=min(4, profile.cpu_logical_cores),
            pin_memory=True,
            mixed_precision=True,
            amp_dtype="float16",
            encoder_backbone="resnet34",
            max_epochs=30,
            early_stopping_patience=7,
            colab_recommended=False,
            hardware_tier=1,
            tier_description="High-End Dedicated GPU (VRAM >= 14 GB)",
            notes="Full resolution 512x512 training with batch size 16 and fp16 AMP.",
        )

    # Tier 2: Mid-Range GPU (6 GB <= VRAM < 14 GB, e.g. T4, RTX 3060)
    elif profile.cuda_available and profile.vram_total_gb >= 6.0:
        return TrainingConfig(
            device="cuda",
            batch_size=8,
            gradient_accumulation_steps=2,
            effective_batch_size=16,
            image_height=512,
            image_width=512,
            num_workers=2,
            pin_memory=True,
            mixed_precision=True,
            amp_dtype="float16",
            encoder_backbone="resnet34",
            max_epochs=25,
            early_stopping_patience=5,
            colab_recommended=False,
            hardware_tier=2,
            tier_description="Mid-Range GPU (6 GB <= VRAM < 14 GB)",
            notes="512x512 resolution with batch size 8 and gradient accumulation step 2.",
        )

    # Tier 3: Low-End GPU (VRAM < 6 GB)
    elif profile.cuda_available and profile.vram_total_gb < 6.0:
        return TrainingConfig(
            device="cuda",
            batch_size=4,
            gradient_accumulation_steps=4,
            effective_batch_size=16,
            image_height=384,
            image_width=384,
            num_workers=0,
            pin_memory=False,
            mixed_precision=True,
            amp_dtype="float16",
            encoder_backbone="resnet18",
            max_epochs=20,
            early_stopping_patience=5,
            colab_recommended=True,
            hardware_tier=3,
            tier_description="Low-End GPU (VRAM < 6 GB)",
            notes="Scaled to 384x384 with batch size 4; Google Colab recommended for full runs.",
        )

    # Tier 4: CPU with Ample RAM (RAM available >= 4.0 GB)
    elif not profile.cuda_available and profile.ram_available_gb >= 4.0:
        return TrainingConfig(
            device="cpu",
            batch_size=4,
            gradient_accumulation_steps=4,
            effective_batch_size=16,
            image_height=256,
            image_width=256,
            num_workers=0,
            pin_memory=False,
            mixed_precision=False,
            amp_dtype="float32",
            encoder_backbone="resnet18",
            max_epochs=10,
            early_stopping_patience=3,
            colab_recommended=True,
            hardware_tier=4,
            tier_description="CPU Execution with Ample RAM (Available >= 4.0 GB)",
            notes="CPU training at 256x256 resolution. Google Colab recommended for GPU acceleration.",
        )

    # Tier 5: Constrained Host (CPU only, Available RAM < 2.0 GB) -> Current Host
    else:
        return TrainingConfig(
            device="cpu",
            batch_size=2,
            gradient_accumulation_steps=8,
            effective_batch_size=16,
            image_height=256,
            image_width=256,
            num_workers=0,
            pin_memory=False,
            mixed_precision=False,
            amp_dtype="float32",
            encoder_backbone="resnet18",
            max_epochs=5,
            early_stopping_patience=2,
            colab_recommended=True,
            hardware_tier=5,
            tier_description="Constrained Host (CPU only, Available RAM < 2.0 GB)",
            notes=(
                f"Severe RAM constraint detected ({profile.ram_available_gb:.2f} GB free). "
                "Local execution strictly bounded to batch_size=2, resolution 256x256, and num_workers=0 "
                "to prevent OOM termination. Production training should be executed on Google Colab."
            ),
        )


def check_disk_safety(
    required_gb: float,
    disk_path: Union[str, Path] = WORKSPACE_ROOT,
) -> Tuple[bool, float, str]:
    """
    Checks if sufficient disk space is available for an operation and enforces
    the mandatory notification threshold for operations exceeding 10 GB.

    Returns:
        (is_safe, free_gb, message)
    """
    resolved_disk = Path(disk_path).resolve()
    drive_root = resolved_disk.anchor or str(resolved_disk)
    usage = shutil.disk_usage(drive_root)
    free_gb = usage.free / (1024.0 ** 3)

    if required_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB:
        msg = (
            f"WARNING: Operation requires {required_gb:.2f} GB, which exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
            f"mandatory user notification threshold. Current free space: {free_gb:.2f} GB."
        )
        # Check if space even exists
        if free_gb < (required_gb + DISK_FREE_MIN_GB):
            return (False, free_gb, f"REJECTED: {msg} (Insufficient headroom under 5.0 GB safety margin).")
        return (True, free_gb, f"PROCEED_WITH_NOTICE: {msg}")

    if free_gb < (required_gb + DISK_FREE_MIN_GB):
        return (
            False,
            free_gb,
            f"REJECTED: Insufficient disk space ({free_gb:.2f} GB free, requires {required_gb:.2f} GB + {DISK_FREE_MIN_GB:.1f} GB safety margin).",
        )

    return (True, free_gb, f"OK: Sufficient disk space ({free_gb:.2f} GB free).")


if __name__ == "__main__":
    profile = probe_hardware()
    config = auto_configure_training(profile)
    print("\n" + "=" * 60)
    print("HOST HARDWARE AUDIT REPORT")
    print("=" * 60)
    print(profile.to_markdown_table())
    print("\n" + "=" * 60)
    print("AUTO-CONFIGURED TRAINING SPECIFICATION")
    print("=" * 60)
    print(json.dumps(config.to_dict(), indent=2))
```

---

## 4. Test Suite Specification for Worker

The worker implementing M1 unit tests must populate two test files under `drywall_detection/tests/`:
1. `drywall_detection/tests/test_coords.py`
2. `drywall_detection/tests/test_hardware.py`

### 4.1 Test Cases for `drywall_detection/tests/test_coords.py`

| # | Test Function Name | Tested Target | Input / Setup | Expected Assertion Criteria |
|---|---|---|---|---|
| 1 | `test_forward_matrix_determinant` | `get_forward_matrix` | $DPI=150$, $H=2592.0$ | $\det(M) = S^2 = (150/72)^2 \approx 4.340277 > 0$. |
| 2 | `test_matrix_inversion_identity` | `get_forward_matrix`, `get_inverse_matrix` | $DPI=150, 72, 300$ | $M \cdot M^{-1} = I_{3 \times 3}$ within tolerance $10^{-6}$. |
| 3 | `test_point_bijection_roundtrip` | `pdf_to_pixel`, `pixel_to_pdf` | Multiple points: $(0, 0)$, $(1728, 2592)$, $(500, 1200)$, $(864, 1296)$ at $150$ DPI | $|x_{orig} - x_{inv}| < 10^{-4}$ and $|y_{orig} - y_{inv}| < 10^{-4}$. |
| 4 | `test_known_point_mapping_72_dpi` | `pdf_to_pixel` | $(x=100.0, y=200.0)$ at $72$ DPI ($S=1.0$) | $px = 2592.0 - 200.0 = 2392.0$, $py = 100.0$. Exact match. |
| 5 | `test_known_point_mapping_150_dpi` | `pdf_to_pixel` | $(x=0.0, y=2592.0)$ at $150$ DPI | $px = 0.0$, $py = 0.0$. (Bottom-left of unrotated page maps to top-left of rotated page). |
| 6 | `test_bbox_forward_inverse_roundtrip` | `pdf_bbox_to_pixel`, `pixel_bbox_to_pdf` | BBox `(100.0, 500.0, 250.0, 800.0)` at $150$ DPI | Roundtrip BBox equals original within $10^{-4}$. Ordering $px_0 \le px_1$ and $py_0 \le py_1$ strictly held. |
| 7 | `test_vectorized_points_roundtrip` | `pdf_points_to_pixel`, `pixel_points_to_pdf` | Random numpy array `(1000, 2)` inside $[0..1728] \times [0..2592]$ | Max absolute difference over all 1000 points $< 10^{-4}$. |
| 8 | `test_shapely_polygon_with_hole_roundtrip` | `pdf_geom_to_pixel`, `pixel_geom_to_pdf` | Shapely Polygon with 1 interior hole at $150$ DPI | Both `geom.is_valid` and `roundtrip.is_valid` True. `geom.equals_exact(roundtrip, 1e-4)` is True. |
| 9 | `test_shapely_linestring_and_multipolygon` | `pdf_geom_to_pixel`, `pixel_geom_to_pdf` | LineString and MultiPolygon geometries | Topology preserved; `geom.equals_exact(roundtrip, 1e-4)` True. |
| 10 | `test_invalid_inputs_raise_errors` | `pdf_to_pixel`, `pdf_bbox_to_pixel` | Negative DPI ($0, -150$), NaN point, inverted BBox $(200, 100, 100, 50)$ | Raises `ValueError`. |

### 4.2 Test Cases for `drywall_detection/tests/test_hardware.py`

| # | Test Function Name | Tested Target | Input / Setup | Expected Assertion Criteria |
|---|---|---|---|---|
| 1 | `test_probe_hardware_real_system` | `probe_hardware` | Live host execution | Returns valid `HardwareProfile` with `cpu_logical_cores >= 1`, `ram_total_gb > 0`, `disk_free_gb > 0`, `python_version` valid string. |
| 2 | `test_hardware_profile_markdown_table` | `HardwareProfile.to_markdown_table` | Profile instance | Contains Markdown table headers `| Resource | Detected Specification |` and host rows. |
| 3 | `test_auto_configure_tier1_high_gpu` | `auto_configure_training` | Mock Profile: CUDA=True, VRAM=16.0 GB | `device="cuda"`, `batch_size=16`, `image_height=512`, `hardware_tier=1`. |
| 4 | `test_auto_configure_tier2_mid_gpu` | `auto_configure_training` | Mock Profile: CUDA=True, VRAM=8.0 GB | `device="cuda"`, `batch_size=8`, `gradient_accumulation_steps=2`, `image_height=512`, `hardware_tier=2`. |
| 5 | `test_auto_configure_tier3_low_gpu` | `auto_configure_training` | Mock Profile: CUDA=True, VRAM=4.0 GB | `device="cuda"`, `batch_size=4`, `image_height=384`, `colab_recommended=True`, `hardware_tier=3`. |
| 6 | `test_auto_configure_tier4_cpu_high_ram` | `auto_configure_training` | Mock Profile: CUDA=False, RAM avail=8.0 GB | `device="cpu"`, `batch_size=4`, `image_height=256`, `hardware_tier=4`. |
| 7 | `test_auto_configure_tier5_constrained_host`| `auto_configure_training` | Mock Profile: CUDA=False, RAM avail=0.8 GB (Current Host) | `device="cpu"`, `batch_size=2`, `num_workers=0`, `image_height=256`, `hardware_tier=5`, `colab_recommended=True`. |
| 8 | `test_check_disk_safety_sufficient` | `check_disk_safety` | `required_gb=1.0` on current drive | Returns `(True, free_gb, msg)` with `OK`. |
| 9 | `test_check_disk_safety_insufficient` | `check_disk_safety` | `required_gb=999999.0` | Returns `(False, free_gb, msg)` with `REJECTED`. |
| 10 | `test_check_disk_safety_10gb_warning_threshold` | `check_disk_safety` | `required_gb=12.0` | Trigger `WARNING: Operation requires 12.00 GB, which exceeds the 10.0 GB mandatory user notification threshold.` |

---

## 5. Step-by-Step Implementation Sequence for Worker

1. **Step 1: Initialize Package Skeleton**:
   - Create directory `drywall_detection/` at workspace root.
   - Create `drywall_detection/__init__.py`.
   - Create `drywall_detection/utils/__init__.py`.
   - Create `drywall_detection/tests/__init__.py`.
2. **Step 2: Implement `drywall_detection/config.py`**:
   - Populate constants as defined in Section 1.2.
   - Run verification: `python -c "import drywall_detection.config as cfg; print(cfg.validate_environment())"`.
3. **Step 3: Implement `drywall_detection/utils/coords.py`**:
   - Implement forward/inverse affine mappings for scalar points, bounding boxes, numpy arrays, and Shapely geometries as defined in Section 2.2.
   - Run roundtrip check: `python -c "from drywall_detection.utils.coords import pdf_to_pixel, pixel_to_pdf; p = pdf_to_pixel(500, 1200); print(pixel_to_pdf(*p))"`.
4. **Step 4: Implement `drywall_detection/utils/hardware.py`**:
   - Implement `HardwareProfile`, `TrainingConfig`, `probe_hardware()`, `auto_configure_training()`, and `check_disk_safety()`.
   - Run CLI inspection: `python -m drywall_detection.utils.hardware`.
5. **Step 5: Implement Test Suites**:
   - Create `drywall_detection/tests/test_coords.py` with 10 unit test functions.
   - Create `drywall_detection/tests/test_hardware.py` with 10 unit test functions.
   - Run `pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_hardware.py -v`.
   - Verify 100% pass rate.

---
*End of Report ARCH-M1-COORDS-HW-001.*
