"""
drywall_detection.datasets package.
Exports unified dataset preparation, licensing audit, split manager, and DataLoader interfaces.
"""

from drywall_detection.datasets.licensing_audit import (
    AuditStatus,
    CommercialStatus,
    AccessModel,
    DatasetLicenseInfo,
    DatasetLicensingAuditor,
)

from drywall_detection.datasets.unified_format import (
    DatasetClass,
    PALETTE_256,
    UnifiedDatasetConfig,
    TileCoordinates,
    TileMetadata,
    MaskValidationError,
    validate_mask_array,
    UnifiedMask,
    MSDConverter,
    CubiCasaConverter,
    RasterMaskConverter,
    SlidingWindowTiler,
    VisualQCGenerator,
)

from drywall_detection.datasets.split_manager import (
    TileRecord,
    SplitStats,
    SplitManifest,
    DrawingSplitManager,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    verify_split_isolation,
)

from drywall_detection.datasets.loader import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    SynchronizedTransform,
    DrywallTileDataset,
    safe_collate_fn,
    get_tile_dataloader,
)

__all__ = [
    # Licensing
    "AuditStatus",
    "CommercialStatus",
    "AccessModel",
    "DatasetLicenseInfo",
    "DatasetLicensingAuditor",
    # Unified Format
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
    # Split Manager
    "TileRecord",
    "SplitStats",
    "SplitManifest",
    "DrawingSplitManager",
    "SplitLeakageError",
    "InsufficientGroupsError",
    "InvalidSplitRatioError",
    "verify_split_isolation",
    # Loader
    "IMAGENET_MEAN",
    "IMAGENET_STD",
    "SynchronizedTransform",
    "DrywallTileDataset",
    "safe_collate_fn",
    "get_tile_dataloader",
]
