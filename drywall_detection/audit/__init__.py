"""
Dataset audit and licensing compliance module.
Exports are lazily loaded via __getattr__ to prevent runpy shadowing
and RuntimeWarnings during CLI execution (e.g. python -m drywall_detection.audit.dataset_auditor).
"""

from typing import Any, List

__all__: List[str] = [
    "DatasetAuditor",
    "DatasetEligibility",
    "LicenseCategory",
    "DownloadMechanism",
    "DatasetSpec",
    "DiskAuditResult",
    "DiskCheckResult",
    "DatasetAuditResult",
    "DatasetAuditRecord",
    "DownloadThresholdResult",
    "LicenseValidationResult",
    "AuditReport",
    "CANDIDATE_DATASETS",
    "AuditStatus",
    "CommercialStatus",
    "AccessModel",
    "DatasetLicenseInfo",
    "DatasetLicensingAuditor",
]


def __getattr__(name: str) -> Any:
    """Lazily load symbols from dataset_auditor upon attribute access."""
    if name in __all__:
        import drywall_detection.audit.dataset_auditor as _mod
        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    """Support dir() and autocompletion for lazily exported symbols."""
    return __all__
