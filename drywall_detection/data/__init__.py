"""
drywall_detection.data
======================
Milestone M2 Dataset Preparation package.
Provides dataset downloading, format unification, mask rasterization,
project-isolated partitioning, and visual quality control.
"""

from drywall_detection.data.downloader import (
    MSDDownloader,
    MSD_CATALOG,
    DatasetFileSpec,
    DownloadResult,
    ChecksumMismatchError,
    DiskSpaceSafetyError,
    compute_file_sha256,
)
from drywall_detection.data.preparer import (
    PreparationConfig,
    ParsedDrawing,
    UnifiedFloorPlan,
    GeometryRasterizer,
    DrawingSanitizer,
    MSDAnnotationParser,
    DatasetPreparer,
    PALETTE_256,
    DrawingSplitManager,
    SplitManifest,
    TileRecord,
    SplitStats,
    verify_split_isolation,
)
from drywall_detection.data.splitter import (
    SampleRecord,
    SplitPartitionStats,
    SplitManifestBundle,
    ProjectDataSplitter,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    assert_zero_leakage,
)
from drywall_detection.data.qc import (
    QCInspectionRecord,
    VisualQCGenerator,
    VisualQCPipeline,
)

__all__ = [
    # Downloader
    "MSDDownloader",
    "MSD_CATALOG",
    "DatasetFileSpec",
    "DownloadResult",
    "ChecksumMismatchError",
    "DiskSpaceSafetyError",
    "compute_file_sha256",
    # Preparer & Geometry
    "PreparationConfig",
    "ParsedDrawing",
    "UnifiedFloorPlan",
    "GeometryRasterizer",
    "DrawingSanitizer",
    "MSDAnnotationParser",
    "DatasetPreparer",
    "PALETTE_256",
    # Backward compatibility re-exports
    "DrawingSplitManager",
    "SplitManifest",
    "TileRecord",
    "SplitStats",
    "verify_split_isolation",
    # Splitter
    "SampleRecord",
    "SplitPartitionStats",
    "SplitManifestBundle",
    "ProjectDataSplitter",
    "SplitLeakageError",
    "InsufficientGroupsError",
    "InvalidSplitRatioError",
    "assert_zero_leakage",
    # QC
    "QCInspectionRecord",
    "VisualQCGenerator",
    "VisualQCPipeline",
]
