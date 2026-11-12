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
for _dir in [
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    QC_SAMPLES_DIR,
    CACHE_DIR,
    REPORTS_DIR,
    CHECKPOINTS_DIR,
    BEST_MODEL_DIR,
    CONFIG_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 2. MASTER REFERENCE PDF SPECIFICATION
# ==============================================================================
# Default path to the master 71-page architectural interior set
DEFAULT_MASTER_PDF_PATH: Path = Path(
    os.environ.get(
        "DRYWALL_MASTER_PDF_PATH",
        r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf",
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
        r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf",
    )
)
RELEVANT_FULL_PAGES_PDF: Path = Path(
    os.environ.get(
        "DRYWALL_RELEVANT_PAGES_PDF",
        r"C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf",
    )
)
ANNOTATED_FLOOR_PLANS_PDF: Path = Path(
    os.environ.get(
        "DRYWALL_ANNOTATED_PLANS_PDF",
        r"C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf",
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
