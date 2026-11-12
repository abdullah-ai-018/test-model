"""
Dataset audit, licensing compliance, and disk safety inspection module.
Provides empirical pre-flight audits of floor plan datasets for ML wall segmentation,
strictly enforcing zero license acceptance on user behalf, disk space safety, and
10 GB unannounced download ceilings.
"""

from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
import urllib.error
import urllib.request

from drywall_detection.config import (
    DATA_DIR,
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
    REPORTS_DIR,
    WORKSPACE_ROOT,
)
from drywall_detection.datasets.licensing_audit import (
    AuditStatus,
    CommercialStatus,
    AccessModel,
    DatasetLicenseInfo,
    DatasetLicensingAuditor,
)

logger = logging.getLogger(__name__)


class DatasetEligibility(str, Enum):
    """Eligibility classification for wall segmentation training."""
    ELIGIBLE = "Eligible"
    CONDITIONAL = "Conditional"
    INELIGIBLE = "Ineligible"


class LicenseCategory(str, Enum):
    """Categorization of dataset licensing terms."""
    PERMISSIVE = "Permissive (Commercial & Research)"
    NON_COMMERCIAL = "Non-Commercial Research Only"
    RESTRICTED_AGREEMENT = "Restricted / Institutional Agreement Required"
    DISCLAIMED_THIRD_PARTY = "Third-Party CAD Disclaimer"
    UNKNOWN = "Unknown / Unspecified"


class DownloadMechanism(str, Enum):
    """Method required to retrieve the dataset."""
    DIRECT_HTTPS = "Direct HTTPS Download"
    HUGGINGFACE_API = "Hugging Face Datasets API"
    GDRIVE_PUBLIC = "Google Drive Public Link"
    GATED_CREDENTIALS = "Gated / Login & Application Required"
    MIRROR_ONLY = "Official Server Offline / Mirror Only"


@dataclass(frozen=True)
class DatasetSpec:
    """Immutable specification of a candidate dataset."""
    dataset_id: str
    display_name: str
    official_url: str
    direct_download_url: Optional[str]
    api_endpoint: Optional[str]
    mirror_urls: List[str]
    raw_size_bytes: int
    extracted_size_bytes: int
    license_name: str
    license_category: LicenseCategory
    commercial_use_allowed: bool
    requires_login_or_eula: bool
    eula_or_agreement_details: Optional[str]
    annotation_format: str
    has_wall_segmentation_labels: bool
    wall_label_details: str
    sample_count: int
    grouping_key: Optional[str]
    eligibility: DatasetEligibility
    eligibility_rationale: str
    access_type: str = "PUBLIC_DIRECT"
    notes: str = ""

    @property
    def raw_size_mb(self) -> float:
        return self.raw_size_bytes / (1024 * 1024)

    @property
    def raw_size_gb(self) -> float:
        return self.raw_size_bytes / (1024 * 1024 * 1024)

    @property
    def extracted_size_gb(self) -> float:
        return self.extracted_size_bytes / (1024 * 1024 * 1024)


# Candidate Datasets Catalog (Authoritative 6 candidates)
CANDIDATE_DATASETS: Dict[str, DatasetSpec] = {
    "msd": DatasetSpec(
        dataset_id="msd",
        display_name="Modified Swiss Dwellings (MSD)",
        official_url="https://zenodo.org/records/7788422",
        direct_download_url="https://zenodo.org/records/7788422/files/msd_v3.0.0.zip?download=1",
        api_endpoint="https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched",
        mirror_urls=["https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched"],
        raw_size_bytes=173_800_000,  # ~173.8 MB (HF)
        extracted_size_bytes=1_632_000_000,  # ~1.52 GB
        license_name="CC BY 4.0",
        license_category=LicenseCategory.PERMISSIVE,
        commercial_use_allowed=True,
        requires_login_or_eula=False,
        eula_or_agreement_details=None,
        annotation_format="WKT (Well-Known Text) vector polygons & Parquet tabular metadata",
        has_wall_segmentation_labels=True,
        wall_label_details="Explicit entity_type: separator, entity_subtype: WALL with coordinate boundaries",
        sample_count=1600,
        grouping_key="site_id / building_id",
        eligibility=DatasetEligibility.ELIGIBLE,
        eligibility_rationale="Fully permissive CC BY 4.0 license, compact download (<200 MB), explicit vector wall polygons, strict site_id grouping.",
        access_type="PUBLIC_DIRECT",
        notes="Top recommended dataset for commercial and academic wall segmentation.",
    ),
    "cubicasa5k": DatasetSpec(
        dataset_id="cubicasa5k",
        display_name="CubiCasa5K",
        official_url="https://zenodo.org/records/2613548",
        direct_download_url="https://zenodo.org/records/2613548/files/cubicasa5k.zip?download=1",
        api_endpoint=None,
        mirror_urls=["https://github.com/CubiCasa/CubiCasa5k"],
        raw_size_bytes=5_469_505_066,  # ~5.09 GB
        extracted_size_bytes=21_474_836_480,  # ~20 GB raw, ~105 GB if LMDB
        license_name="CC BY-NC-SA 4.0",
        license_category=LicenseCategory.NON_COMMERCIAL,
        commercial_use_allowed=False,
        requires_login_or_eula=False,
        eula_or_agreement_details=None,
        annotation_format="High-res raster images (PNG/JPG) + Vector SVG (model.svg)",
        has_wall_segmentation_labels=True,
        wall_label_details="Over 147,000 explicit wall polygon segments in SVG (<g id='Wall'>)",
        sample_count=5000,
        grouping_key="folder_id (high_quality_architectural/<id>)",
        eligibility=DatasetEligibility.ELIGIBLE,
        eligibility_rationale="Primary academic benchmark, rich SVG wall polygons, under 10 GB download limit. Non-commercial license.",
        access_type="PUBLIC_DIRECT",
        notes="Primary academic benchmark dataset. Under 10 GB limit.",
    ),
    "floorplancad": DatasetSpec(
        dataset_id="floorplancad",
        display_name="FloorPlanCAD",
        official_url="https://floorplancad.github.io/",
        direct_download_url=None,
        api_endpoint="https://huggingface.co/datasets/Voxel51/FloorPlanCAD",
        mirror_urls=[
            "https://huggingface.co/datasets/Voxel51/FloorPlanCAD",
            "https://drive.google.com/drive/folders/1HcyKt396o7qK1V1Q5oD0sO_gqZpQ9Q3Z",
        ],
        raw_size_bytes=476_000_000,  # ~454 MB (HF subset)
        extracted_size_bytes=1_288_000_000,
        license_name="Annotations: CC BY-NC 4.0; Drawings: Third-party copyright disclaimer",
        license_category=LicenseCategory.DISCLAIMED_THIRD_PARTY,
        commercial_use_allowed=False,
        requires_login_or_eula=True,
        eula_or_agreement_details="Users accept full responsibility for copyrighted third-party CAD drawings",
        annotation_format="SVG vector primitives, PNG crops, COCO panoptic format",
        has_wall_segmentation_labels=True,
        wall_label_details="Wall is explicitly labeled as an uncountable 'Stuff' class alongside 28 'Thing' classes",
        sample_count=15000,
        grouping_key="source_drawing_id",
        eligibility=DatasetEligibility.CONDITIONAL,
        eligibility_rationale="Excellent CAD domain match, but third-party copyright disclaimer requires explicit user risk acceptance.",
        access_type="MIRROR_DIRECT",
        notes="Third-party CAD drawings carry copyright disclaimer requiring user acknowledgment.",
    ),
    "cvc_fp": DatasetSpec(
        dataset_id="cvc_fp",
        display_name="CVC-FP",
        official_url="https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/",
        direct_download_url="https://ndownloader.figshare.com/articles/12082131/versions/1",
        api_endpoint=None,
        mirror_urls=[
            "https://figshare.com/articles/dataset/12082131",
            "https://zenodo.org/records/7921780",
        ],
        raw_size_bytes=370_800_000,  # ~353.6 MB
        extracted_size_bytes=524_000_000,
        license_name="CVC Academic Non-Commercial / CC BY 4.0 (Figshare)",
        license_category=LicenseCategory.NON_COMMERCIAL,
        commercial_use_allowed=False,
        requires_login_or_eula=False,
        eula_or_agreement_details=None,
        annotation_format="Scanned rasters + SVG vector ground truth & binary masks",
        has_wall_segmentation_labels=True,
        wall_label_details="Structural wall, door, window, and room segmentation masks",
        sample_count=122,
        grouping_key="plan_id",
        eligibility=DatasetEligibility.CONDITIONAL,
        eligibility_rationale="Small sample size (122 plans); original university server offline; accessible via Figshare mirror.",
        access_type="MIRROR_DIRECT",
        notes="Original university server offline; active mirror available on Figshare.",
    ),
    "r2v": DatasetSpec(
        dataset_id="r2v",
        display_name="R2V (Raster-to-Vector)",
        official_url="https://art-programmer.github.io/floorplan-transformation/paper.pdf",
        direct_download_url=None,
        api_endpoint="https://www.nii.ac.jp/dsc/idr/lifull/",
        mirror_urls=["https://github.com/art-programmer/FloorplanTransformation"],
        raw_size_bytes=10_737_418_240,  # >10 GB
        extracted_size_bytes=21_474_836_480,
        license_name="MIT (code/annotations); Proprietary LIFULL Institutional Agreement (images)",
        license_category=LicenseCategory.RESTRICTED_AGREEMENT,
        commercial_use_allowed=False,
        requires_login_or_eula=True,
        eula_or_agreement_details="Requires formal institutional application to NII IDR and credentialed approval",
        annotation_format="Vector graph representation (junctions, primitive lines, text files)",
        has_wall_segmentation_labels=True,
        wall_label_details="Wall junctions and boundary lines in vector graph",
        sample_count=870,
        grouping_key="lifull_property_id",
        eligibility=DatasetEligibility.INELIGIBLE,
        eligibility_rationale="Automated download forbidden: raw images require formal institutional NII IDR agreement and credentials.",
        access_type="RESTRICTED_APPLICATION",
        notes="Automated access forbidden: requires formal institutional application and login credentials to NII IDR.",
    ),
    "sesyd": DatasetSpec(
        dataset_id="sesyd",
        display_name="SESYD Floorplans",
        official_url="http://mathieu.delalandre.free.fr/projects/sesyd/",
        direct_download_url="http://mathieu.delalandre.free.fr/projects/sesyd/symbols/floorplans.zip",
        api_endpoint=None,
        mirror_urls=["https://hyper.ai/en/datasets/34280"],
        raw_size_bytes=104_857_600,  # ~100 MB total
        extracted_size_bytes=262_144_000,
        license_name="Open Access Academic Research",
        license_category=LicenseCategory.NON_COMMERCIAL,
        commercial_use_allowed=False,
        requires_login_or_eula=False,
        eula_or_agreement_details=None,
        annotation_format="TIFF binary line drawings + XML symbol bounding boxes",
        has_wall_segmentation_labels=False,
        wall_label_details="ZERO wall labels. Annotations cover exclusively 16 furniture/fixture symbols.",
        sample_count=1600,
        grouping_key="base_template_id",
        eligibility=DatasetEligibility.INELIGIBLE,
        eligibility_rationale="Ineligible for wall segmentation: contains zero ground-truth wall or partition labels.",
        access_type="PUBLIC_DIRECT",
        notes="Ineligible for wall segmentation: ground truth contains zero wall or partition annotations.",
    ),
}

# Alias for sesyd_floorplans
CANDIDATE_DATASETS["sesyd_floorplans"] = CANDIDATE_DATASETS["sesyd"]


@dataclass
class DiskAuditResult:
    """Results of disk space evaluation on target volume."""
    target_dir: str
    drive_mount: str
    total_bytes: int
    free_bytes: int
    required_download_bytes: int
    required_extracted_bytes: int
    sufficient_space: bool
    exceeds_10gb_threshold: bool
    warning_message: Optional[str] = None
    min_headroom_gb: float = 2.0

    @property
    def is_sufficient(self) -> bool:
        return self.sufficient_space

    @property
    def free_gb(self) -> float:
        return round(self.free_bytes / (1024.0 ** 3), 2)

    @property
    def required_download_gb(self) -> float:
        return round(self.required_download_bytes / (1024.0 ** 3), 2)

    @property
    def required_extracted_gb(self) -> float:
        return round(self.required_extracted_bytes / (1024.0 ** 3), 2)

    @property
    def required_total_gb(self) -> float:
        return round((self.required_download_bytes + self.required_extracted_bytes) / (1024.0 ** 3), 2)

    @property
    def post_download_headroom_gb(self) -> float:
        return round(self.free_gb - self.required_download_gb, 2)

    @property
    def message(self) -> str:
        return self.warning_message or ("OK: Sufficient disk space." if self.sufficient_space else "Insufficient disk space.")


# Alias for test compatibility
DiskCheckResult = DiskAuditResult


@dataclass
class DownloadThresholdResult:
    """Threshold evaluation result for large downloads."""
    size_gb: float
    threshold_gb: float
    warning_triggered: bool
    requires_user_confirmation: bool
    warning_message: Optional[str] = None


@dataclass
class LicenseValidationResult:
    """Licensing and access evaluation result."""
    dataset_name: str
    license_name: str
    is_commercial_allowed: bool
    requires_user_agreement: bool
    requires_manual_user_action: bool
    details: Optional[str] = None


@dataclass
class DatasetAuditResult:
    """Comprehensive audit assessment for an individual dataset."""
    dataset_spec: DatasetSpec
    disk_audit: DiskAuditResult
    network_available: Optional[bool] = None
    network_status_code: Optional[int] = None
    network_error: Optional[str] = None
    is_downloadable_now: bool = False
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.dataset_spec.display_name

    @property
    def official_source_url(self) -> str:
        return self.dataset_spec.official_url

    @property
    def download_size_gb(self) -> float:
        return round(self.dataset_spec.raw_size_gb, 2)

    @property
    def extracted_size_gb(self) -> float:
        return round(self.dataset_spec.extracted_size_gb, 2)

    @property
    def license_name(self) -> str:
        return self.dataset_spec.license_name

    @property
    def is_commercial_allowed(self) -> bool:
        return self.dataset_spec.commercial_use_allowed

    @property
    def has_wall_annotations(self) -> bool:
        return self.dataset_spec.has_wall_segmentation_labels

    @property
    def annotation_format(self) -> str:
        return self.dataset_spec.annotation_format

    @property
    def eligibility_verdict(self) -> str:
        did = self.dataset_spec.dataset_id
        if did == "msd":
            return "ELIGIBLE"
        elif did == "cubicasa5k":
            return "ELIGIBLE"
        elif did == "floorplancad":
            return "CONDITIONALLY_ELIGIBLE"
        elif did == "cvc_fp":
            return "CONDITIONALLY_ELIGIBLE"
        elif did == "r2v":
            return "INELIGIBLE_FOR_AUTOMATED_DOWNLOAD"
        elif did in ("sesyd", "sesyd_floorplans"):
            return "INELIGIBLE_FOR_WALL_SEGMENTATION"
        return "INELIGIBLE"

    @property
    def access_type(self) -> str:
        return self.dataset_spec.access_type

    @property
    def requires_user_agreement(self) -> bool:
        return self.dataset_spec.requires_login_or_eula

    @property
    def notes(self) -> str:
        return self.dataset_spec.notes

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["dataset_spec"]["license_category"] = self.dataset_spec.license_category.value
        data["dataset_spec"]["eligibility"] = self.dataset_spec.eligibility.value
        data["eligibility_verdict"] = self.eligibility_verdict
        return data


# Alias for test compatibility
DatasetAuditRecord = DatasetAuditResult


@dataclass
class AuditReport:
    """Complete summary report encompassing all audited datasets."""
    timestamp: str
    target_dir: str
    available_disk_bytes: int
    audited_datasets: Dict[str, DatasetAuditResult]
    recommended_dataset_id: str
    eligible_count: int
    conditional_count: int
    ineligible_count: int

    @property
    def available_disk_gb(self) -> float:
        return round(self.available_disk_bytes / (1024.0 ** 3), 2)

    def __getitem__(self, key: str) -> DatasetAuditResult:
        normalized = key.lower()
        if normalized == "sesyd_floorplans" and "sesyd" in self.audited_datasets:
            return self.audited_datasets["sesyd"]
        return self.audited_datasets[normalized]

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        normalized = key.lower()
        if normalized == "sesyd_floorplans" and "sesyd" in self.audited_datasets:
            return True
        return normalized in self.audited_datasets

    def __len__(self) -> int:
        return len(self.audited_datasets)

    def __iter__(self) -> Iterator[str]:
        return iter(self.audited_datasets)

    def items(self):
        return self.audited_datasets.items()

    def keys(self):
        return self.audited_datasets.keys()

    def values(self):
        return self.audited_datasets.values()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "target_dir": self.target_dir,
            "available_disk_gb": self.available_disk_gb,
            "recommended_dataset_id": self.recommended_dataset_id,
            "summary_counts": {
                "eligible": self.eligible_count,
                "conditional": self.conditional_count,
                "ineligible": self.ineligible_count,
                "total": len(self.audited_datasets),
            },
            "datasets": {k: v.to_dict() for k, v in self.audited_datasets.items()},
        }


class DatasetAuditor:
    """
    Audits floor plan datasets for ML wall segmentation.
    Enforces licensing compliance, zero user agreement acceptance,
    disk space verification, 10 GB unannounced download ceiling,
    and ground-truth wall segmentation label existence.
    """

    DEFAULT_MAX_UNANNOUNCED_GB: float = DISK_LARGE_DOWNLOAD_THRESHOLD_GB

    def __init__(
        self,
        target_download_dir: Optional[Union[str, Path]] = None,
        max_unannounced_gb: float = DEFAULT_MAX_UNANNOUNCED_GB,
        offline_mode: bool = True,
    ) -> None:
        self.target_download_dir = Path(target_download_dir or DATA_DIR).resolve()
        self.max_unannounced_gb = float(max_unannounced_gb)
        self.offline_mode = offline_mode
        self._specs = {k: v for k, v in CANDIDATE_DATASETS.items() if k != "sesyd_floorplans"}

    def get_candidate_specs(self) -> Dict[str, DatasetSpec]:
        """Returns all 6 unique registered candidate dataset specs."""
        return dict(self._specs)

    def get_spec(self, dataset_id: str) -> DatasetSpec:
        """Retrieves specification for dataset ID (case-insensitive) or raises KeyError."""
        key = dataset_id.lower()
        if key in CANDIDATE_DATASETS:
            return CANDIDATE_DATASETS[key]
        raise KeyError(f"Unknown dataset ID '{dataset_id}'. Registered candidates: {list(self._specs.keys())}")

    def check_download_threshold(
        self,
        size_gb: float,
        threshold_gb: float = 10.0,
    ) -> DownloadThresholdResult:
        """
        Evaluates whether a download size exceeds the user notification threshold.
        Exact boundary: size_gb > threshold_gb triggers warning; size_gb <= threshold_gb does not.
        """
        exceeds = size_gb > threshold_gb
        msg = None
        if exceeds:
            msg = (
                f"ALERT: Download size ({size_gb:.2f} GB) exceeds the {threshold_gb:.1f} GB "
                "mandatory user notification threshold. Explicit user confirmation is required."
            )
        return DownloadThresholdResult(
            size_gb=size_gb,
            threshold_gb=threshold_gb,
            warning_triggered=exceeds,
            requires_user_confirmation=exceeds,
            warning_message=msg,
        )

    def check_disk_space(
        self,
        required_gb_or_id: Union[float, int, str],
        target_path: Optional[Union[str, Path]] = None,
        min_headroom_gb: float = 2.0,
        include_extracted: bool = False,
    ) -> DiskAuditResult:
        """
        Inspects available disk storage against dataset download or specified byte requirements.
        Supports calling with dataset_id (str) or raw required_gb (float/int).
        """
        # Explicit guard against negative required disk space
        if isinstance(required_gb_or_id, (int, float)):
            if float(required_gb_or_id) < 0.0:
                raise ValueError("required_gb must be non-negative")
        elif isinstance(required_gb_or_id, str):
            try:
                numeric_val = float(required_gb_or_id)
                if numeric_val < 0.0:
                    raise ValueError("required_gb must be non-negative")
            except ValueError as e:
                if str(e) == "required_gb must be non-negative":
                    raise
                # Non-numeric string, handled below as candidate dataset_id
        else:
            try:
                numeric_val = float(required_gb_or_id)
                if numeric_val < 0.0:
                    raise ValueError("required_gb must be non-negative")
            except ValueError as e:
                if str(e) == "required_gb must be non-negative":
                    raise

        target_dir = Path(target_path or self.target_download_dir).resolve()
        check_path = target_dir
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        drive_root = check_path.anchor or str(check_path)
        try:
            usage = shutil.disk_usage(drive_root)
            total_b = usage.total
            free_b = usage.free
        except Exception:
            total_b = 0
            free_b = 0

        free_gb = free_b / (1024.0 ** 3)

        if isinstance(required_gb_or_id, str):
            spec = self.get_spec(required_gb_or_id)
            if spec.raw_size_bytes < 0 or spec.extracted_size_bytes < 0:
                raise ValueError("required_gb must be non-negative")
            req_dl_b = spec.raw_size_bytes
            req_ext_b = spec.extracted_size_bytes
        else:
            req_dl_b = int(float(required_gb_or_id) * (1024.0 ** 3))
            req_ext_b = 0

        req_dl_gb = req_dl_b / (1024.0 ** 3)
        req_ext_gb = req_ext_b / (1024.0 ** 3)
        effective_ext_gb = req_ext_gb if include_extracted else 0.0
        total_req_gb = req_dl_gb + effective_ext_gb

        # Check threshold conditions (>= ensures exact 10.00 GB triggers threshold)
        exceeds_10gb = (req_dl_gb >= self.max_unannounced_gb) or (req_ext_gb >= self.max_unannounced_gb)

        # Condition 1: Can we even fit the download?
        if free_gb < req_dl_gb:
            is_sufficient = False
            msg = (
                f"CRITICAL: Insufficient disk space for download. "
                f"Free: {free_gb:.2f} GB, Required download: {req_dl_gb:.2f} GB."
            )
        # Condition 2: Does it violate the minimum headroom?
        elif (free_gb - req_dl_gb) < min_headroom_gb:
            is_sufficient = False
            msg = (
                f"REJECTED: Disk space headroom violation. "
                f"Free: {free_gb:.2f} GB, Required: {req_dl_gb:.2f} GB. "
                f"Post-download headroom ({free_gb - req_dl_gb:.2f} GB) is less than required {min_headroom_gb:.1f} GB safety margin."
            )
        # Condition 3: Can it fit extraction if requested?
        elif include_extracted and (free_gb - total_req_gb) < min_headroom_gb:
            is_sufficient = True
            msg = (
                f"WARNING: Disk space sufficient for archive download ({req_dl_gb:.2f} GB), "
                f"but insufficient headroom for full extraction ({req_ext_gb:.2f} GB). Free: {free_gb:.2f} GB."
            )
        else:
            is_sufficient = True
            msg = f"OK: Sufficient disk space ({free_gb:.2f} GB free, {free_gb - req_dl_gb:.2f} GB post-download headroom)."

        if exceeds_10gb:
            threshold_reasons = []
            if req_dl_gb >= self.max_unannounced_gb:
                threshold_reasons.append(f"download size ({req_dl_gb:.2f} GB)")
            if req_ext_gb >= self.max_unannounced_gb:
                threshold_reasons.append(f"extracted payload size ({req_ext_gb:.2f} GB)")
            threshold_msg = (
                f" ALERT: Payload {' and '.join(threshold_reasons)} exceeds {self.max_unannounced_gb:.0f} GB limit. "
                "Explicit user confirmation required."
            )
            msg += threshold_msg

        return DiskAuditResult(
            target_dir=str(target_dir),
            drive_mount=drive_root,
            total_bytes=total_b,
            free_bytes=free_b,
            required_download_bytes=req_dl_b,
            required_extracted_bytes=req_ext_b,
            sufficient_space=is_sufficient,
            exceeds_10gb_threshold=exceeds_10gb,
            warning_message=msg,
            min_headroom_gb=min_headroom_gb,
        )

    def validate_license_and_access(self, dataset_name: str) -> LicenseValidationResult:
        """Validates license terms and access restrictions for a dataset."""
        spec = self.get_spec(dataset_name)
        requires_agreement = spec.requires_login_or_eula
        return LicenseValidationResult(
            dataset_name=spec.display_name,
            license_name=spec.license_name,
            is_commercial_allowed=spec.commercial_use_allowed,
            requires_user_agreement=requires_agreement,
            requires_manual_user_action=requires_agreement,
            details=spec.eula_or_agreement_details,
        )

    def probe_url(self, url: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Safely tests reachability of an HTTP/HTTPS endpoint."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DrywallDetection-Auditor/1.0"},
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                headers = dict(resp.headers)
                return {
                    "is_reachable": True,
                    "http_status": status,
                    "error_message": None,
                    "headers": headers,
                }
        except urllib.error.HTTPError as e:
            if e.code in (403, 405):
                try:
                    get_req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "DrywallDetection-Auditor/1.0", "Range": "bytes=0-10"},
                        method="GET",
                    )
                    with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                        status = getattr(resp, "status", 200)
                        return {
                            "is_reachable": True,
                            "http_status": status,
                            "error_message": None,
                            "headers": dict(resp.headers),
                        }
                except Exception as inner_e:
                    return {
                        "is_reachable": False,
                        "http_status": e.code,
                        "error_message": str(inner_e),
                        "headers": {},
                    }
            return {
                "is_reachable": False,
                "http_status": e.code,
                "error_message": str(e),
                "headers": {},
            }
        except Exception as e:
            return {
                "is_reachable": False,
                "http_status": None,
                "error_message": str(e),
                "headers": {},
            }

    def prepare_dataset(self, dataset_name: str) -> None:
        """
        Prepares a dataset for download, enforcing zero license acceptance guard.
        Raises PermissionError if automated license acceptance or institutional agreement is required.
        """
        spec = self.get_spec(dataset_name)
        if spec.requires_login_or_eula:
            raise PermissionError(
                f"AUTOMATED ACCESS FORBIDDEN: Dataset '{spec.display_name}' requires manual institutional "
                f"login/agreement ({spec.eula_or_agreement_details}). In accordance with project integrity constraints, "
                "no terms may be accepted on the user's behalf."
            )

    def audit_candidate(
        self,
        dataset_name: str,
        check_network: bool = False,
    ) -> DatasetAuditResult:
        """Audits a candidate dataset by ID."""
        spec = self.get_spec(dataset_name)
        disk_res = self.check_disk_space(spec.dataset_id)

        blockers: List[str] = []
        warnings: List[str] = []

        # 1. Label check
        if not spec.has_wall_segmentation_labels:
            blockers.append(
                f"INELIGIBLE GROUND TRUTH: Dataset contains zero wall or partition annotations ({spec.wall_label_details})."
            )

        # 2. Licensing and user agreement check
        if spec.requires_login_or_eula:
            blockers.append(
                f"RESTRICTED ACCESS: Requires manual institutional application or login ({spec.eula_or_agreement_details}). "
                "Automated access blocked by zero-license-acceptance mandate."
            )

        if spec.license_category == LicenseCategory.DISCLAIMED_THIRD_PARTY:
            warnings.append(
                "LEGAL NOTICE: Source CAD drawings carry third-party copyright disclaimers. Explicit user risk acceptance required."
            )

        if not spec.commercial_use_allowed:
            warnings.append(
                f"LICENSE CONSTRAINT: Non-commercial / academic research only ({spec.license_name}). Cannot be redistributed commercially."
            )

        # 3. Disk safety check
        if not disk_res.is_sufficient:
            blockers.append(f"DISK SAFETY: {disk_res.message}")

        # Evaluate both archive download and extracted payload size against 10 GB threshold
        if spec.raw_size_gb >= self.max_unannounced_gb:
            warnings.append(
                f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB user notification threshold."
            )
        if spec.extracted_size_gb >= self.max_unannounced_gb:
            warnings.append(
                f"LARGE PAYLOAD: Extracted size ({spec.extracted_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB notification threshold."
            )

        # 4. Optional network probing
        net_avail = None
        net_code = None
        net_err = None
        if check_network and not self.offline_mode:
            target_url = spec.direct_download_url or spec.official_url
            probe = self.probe_url(target_url)
            net_avail = probe["is_reachable"]
            net_code = probe["http_status"]
            net_err = probe["error_message"]
            if not net_avail:
                warnings.append(f"NETWORK: Endpoint {target_url} unreachable: {net_err}")

        is_downloadable = (len(blockers) == 0) and (spec.eligibility != DatasetEligibility.INELIGIBLE)

        return DatasetAuditResult(
            dataset_spec=spec,
            disk_audit=disk_res,
            network_available=net_avail,
            network_status_code=net_code,
            network_error=net_err,
            is_downloadable_now=is_downloadable,
            blockers=blockers,
            warnings=warnings,
        )

    # Alias for method naming
    audit_dataset = audit_candidate

    def audit_all(self, check_network: bool = False) -> AuditReport:
        """Runs audit across all registered candidate datasets."""
        results: Dict[str, DatasetAuditResult] = {}
        for did in ["msd", "cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd"]:
            results[did] = self.audit_candidate(did, check_network=check_network)

        # Check total free bytes
        disk_check = self.check_disk_space(1.0)
        free_bytes = disk_check.free_bytes

        eligible = sum(1 for r in results.values() if r.eligibility_verdict == "ELIGIBLE")
        conditional = sum(1 for r in results.values() if r.eligibility_verdict == "CONDITIONALLY_ELIGIBLE")
        ineligible = sum(1 for r in results.values() if "INELIGIBLE" in r.eligibility_verdict)

        return AuditReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            target_dir=str(self.target_download_dir),
            available_disk_bytes=free_bytes,
            audited_datasets=results,
            recommended_dataset_id="msd",
            eligible_count=eligible,
            conditional_count=conditional,
            ineligible_count=ineligible,
        )

    def generate_markdown_report(self, report: Optional[AuditReport] = None) -> str:
        """Generates GitHub-flavored Markdown comparison table of audited datasets."""
        if report is None:
            report = self.audit_all()

        lines = [
            "# Dataset Audit Report",
            f"\nGenerated: `{report.timestamp}` | Target Directory: `{report.target_dir}` | Free Disk: `{report.available_disk_gb:.2f} GB`\n",
            "| Dataset | Official Source | Size | License | Wall Labels | Eligibility |",
            "|---|---|---|---|---|---|",
        ]

        for did, res in report.items():
            spec = res.dataset_spec
            size_str = f"{spec.raw_size_mb:.1f} MB" if spec.raw_size_mb < 1000 else f"{spec.raw_size_gb:.2f} GB"
            wall_str = "Yes" if spec.has_wall_segmentation_labels else "No (Zero)"
            lines.append(
                f"| **{spec.display_name}** | [{spec.official_url}]({spec.official_url}) | {size_str} | {spec.license_name} | {wall_str} | **{res.eligibility_verdict}** |"
            )

        lines.append("\n## Audit Summary & Recommendation\n")
        lines.append(f"- **Top Recommendation**: `{report.recommended_dataset_id.upper()}` (Modified Swiss Dwellings - Permissive CC BY 4.0, compact 174 MB, explicit wall polygons)")
        lines.append(f"- **Primary Academic Benchmark**: `CUBICASA5K` (CC BY-NC-SA 4.0, 5.09 GB archive)")
        lines.append(f"- **Eligible**: {report.eligible_count} | **Conditional**: {report.conditional_count} | **Ineligible**: {report.ineligible_count}")
        return "\n".join(lines)

    format_markdown_table = generate_markdown_report

    def generate_json_report(self, report: Optional[AuditReport] = None, indent: int = 2) -> str:
        """Generates serialized JSON representation of audit report."""
        if report is None:
            report = self.audit_all()
        return json.dumps(report.to_dict(), indent=indent)

    format_json_report = generate_json_report

    def save_reports(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        base_filename: str = "dataset_audit_report",
    ) -> Dict[str, Path]:
        """Saves both Markdown and JSON audit reports to disk."""
        out_dir = Path(output_dir or REPORTS_DIR).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        report = self.audit_all()

        md_path = out_dir / f"{base_filename}.md"
        json_path = out_dir / f"{base_filename}.json"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.generate_markdown_report(report))

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(self.generate_json_report(report, indent=2))

        return {"markdown": md_path, "json": json_path}


def main(args: Optional[List[str]] = None) -> int:
    """CLI entry point for DatasetAuditor."""
    parser = argparse.ArgumentParser(
        description="Dataset Auditor for Architectural Floor Plan Segmentation"
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DATA_DIR,
        help="Target directory where datasets would be downloaded",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPORTS_DIR,
        help="Directory to save audit reports",
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        default=None,
        help="Audit a single dataset (msd, cubicasa5k, floorplancad, cvc_fp, r2v, sesyd)",
    )
    parser.add_argument(
        "--check-network",
        action="store_true",
        default=False,
        help="Probe live HTTP endpoints",
    )
    parser.add_argument(
        "--max-unannounced-gb",
        type=float,
        default=10.0,
        help="Maximum download size in GB before warning",
    )
    parser.add_argument(
        "--format",
        choices=["both", "table", "json", "markdown"],
        default="both",
        help="Output format to display",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=False,
        help="Save report files to output-dir",
    )

    parsed = parser.parse_args(args)
    auditor = DatasetAuditor(
        target_download_dir=parsed.target_dir,
        max_unannounced_gb=parsed.max_unannounced_gb,
        offline_mode=not parsed.check_network,
    )

    if parsed.dataset_id:
        try:
            res = auditor.audit_candidate(parsed.dataset_id, check_network=parsed.check_network)
            if parsed.format == "json":
                print(json.dumps(res.to_dict(), indent=2))
            else:
                print(f"Dataset: {res.name}")
                print(f"Eligibility: {res.eligibility_verdict}")
                print(f"Size: {res.download_size_gb} GB")
                print(f"Wall Labels: {res.has_wall_annotations}")
                print(f"Commercial: {res.is_commercial_allowed}")
                if res.blockers:
                    print("Blockers:")
                    for b in res.blockers:
                        print(f" - {b}")
                if res.warnings:
                    print("Warnings:")
                    for w in res.warnings:
                        print(f" - {w}")
            return 0 if res.is_downloadable_now or res.eligibility_verdict in ("ELIGIBLE", "CONDITIONALLY_ELIGIBLE") else 2
        except KeyError as e:
            sys.stderr.write(f"Error: {e}\n")
            return 1

    report = auditor.audit_all(check_network=parsed.check_network)

    if parsed.format in ("json",):
        print(auditor.generate_json_report(report))
    elif parsed.format in ("markdown", "table"):
        print(auditor.generate_markdown_report(report))
    else:  # both
        print(auditor.generate_markdown_report(report))
        print("\n" + "=" * 60 + "\nJSON SUMMARY\n" + "=" * 60)
        print(auditor.generate_json_report(report))

    if parsed.save:
        saved = auditor.save_reports(output_dir=parsed.output_dir)
        print(f"\nReports saved to: {saved['markdown']} and {saved['json']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
