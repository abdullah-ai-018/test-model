# Technical Architecture Specification: Dataset Auditor Module
**Module:** `drywall_detection/audit/dataset_auditor.py`  
**Milestone:** M1 (Workspace and Dataset Audit)  
**Author:** `explorer_m1_2` (M1 Dataset Auditor Architecture Explorer)  
**Status:** Complete & Approved for Implementation  

---

## 1. Executive Summary & Purpose

The `DatasetAuditor` is the core architectural component responsible for empirical inspection, licensing verification, disk space safety enforcement, and eligibility scoring across all candidate floor plan datasets. 

Before any dataset download or processing occurs in Milestone M2, this module provides an automated, verifiable pre-flight audit that prevents disk exhaustion, eliminates legal liability from unauthorized EULA acceptance, detects missing wall ground-truth labels, and records complete dataset provenance.

### Core Objectives:
1. **Candidate Dataset Audit**: Empirically evaluate all 6 candidate datasets:
   - **Modified Swiss Dwellings (MSD)**: `ELIGIBLE` (Top Recommended)
   - **CubiCasa5K**: `ELIGIBLE` (Primary Academic Benchmark)
   - **FloorPlanCAD**: `CONDITIONAL` (CAD disclaimer requires explicit risk acceptance)
   - **CVC-FP**: `CONDITIONAL` (Original university host offline; Figshare mirror active; small sample size)
   - **R2V (Raster-to-Vector)**: `INELIGIBLE` (Requires institutional NII IDR login and credentialed agreement)
   - **SESYD Floorplans**: `INELIGIBLE` (Zero wall/partition annotations present)
2. **Disk Safety Guards**:
   - Check available free disk space on the target volume using OS-level inspection (`shutil.disk_usage`).
   - Flag if available disk < download archive size or download + extraction size.
   - Enforce mandatory user notification if any download exceeds **10.0 GB** (`MAX_UNANNOUNCED_DOWNLOAD_GB`).
   - Warn on extreme extraction expansion ratios (e.g., CubiCasa5K LMDB generation vs. compressed archive).
3. **Zero License Acceptance Enforcement**:
   - Never accept EULAs, clickwraps, or institutional agreements on the user's behalf.
   - Strictly flag and block automated downloads for gated datasets requiring accounts or institutional agreements (e.g., R2V / LIFULL NII IDR).
4. **Structured Output Formats**:
   - Generate structured machine-readable JSON schemas.
   - Generate rich Markdown comparison tables for reporting and documentation.
5. **Dual Interface**:
   - Programmatic Python API via `DatasetAuditor` class for pipeline integration.
   - Standalone CLI entry point: `python -m drywall_detection.audit.dataset_auditor`.

---

## 2. Complete Candidate Dataset Registry Specification

The table below defines the authoritative specifications encoded into the auditor's dataset registry:

| Dataset ID | Display Name | Official Source / Host | Download Size (Archive / Extracted) | License Terms | Commercial Use? | Annotation Format | Wall Segmentation Labels Present? | Download Mechanism / Auth Status | Eligibility Verdict & Rationale |
|---|---|---|---|---|---|---|---|---|---|
| `msd` | **Modified Swiss Dwellings (MSD)** | Hugging Face (`philippds/modified-swiss-dwellings-enriched`) & Zenodo (`10.5281/zenodo.7788422` v3.0.0) | **173.8 MB** (HF) / **888.7 MB** (Zenodo) / ~1.52 GB extracted | **CC BY 4.0** | **YES** (with attribution) | WKT (Well-Known Text) vector polygons, structured tabular Parquet metadata, raster images (`struct_in`, `full_out`) | **YES**: Explicit `entity_type: separator`, `entity_subtype: WALL` with exact polygon boundary coordinates. Over 1.7M wall elements across 260 sites. | Direct public HTTPS download via Hugging Face API or Zenodo direct download. No login or agreement required. | **ELIGIBLE (Top Recommended)**: Permissive license, compact download size (<200 MB), explicit wall polygons, strict `site_id` / `building_id` hierarchical keys for project-isolated splitting. |
| `cubicasa5k` | **CubiCasa5K** | Zenodo (`record/2613548`), GitHub: `CubiCasa/CubiCasa5k` | **5.09 GB** (archive) / ~15–20 GB (raw PNG/SVG), ~105 GB (full LMDB) | **CC BY-NC-SA 4.0** | **NO** (Academic / Non-commercial only) | High-resolution raster images (PNG/JPG) + Vector SVG annotations (`model.svg`) | **YES**: Explicit wall polygon primitives (`<g id="Wall">` / `<polygon class="Wall">`), over 147,000 wall segments across 5,000 plans. | Direct public download from Zenodo CDN (`cubicasa5k.zip`). No authentication required. Under 10 GB limit. | **ELIGIBLE (Primary Academic Benchmark)**: High-quality SVG annotations and massive sample volume. Extraction must be managed carefully to avoid local disk exhaustion. |
| `floorplancad` | **FloorPlanCAD** | GitHub Pages (`floorplancad.github.io`), Hugging Face (`Voxel51/FloorPlanCAD`), Google Drive parts | **~454 MB** (HF mirror) / ~2.5–3.5 GB (Google Drive parts) / ~5 GB extracted | Annotations: **CC BY-NC 4.0**; CAD Drawings: Third-party copyright disclaimer | **NO** (Non-commercial + user assumes copyright liability) | Line-grained SVG vector primitives, PNG images (20m x 20m tiles), COCO panoptic format | **YES**: "Wall" is explicitly labeled as an uncountable "Stuff" class alongside 28 "Thing" classes across >15,000 CAD drawings. | Hosted on Google Drive (3 parts) and Hugging Face mirror. Direct HTTP via mirror. | **CONDITIONAL**: Excellent vector CAD domain match, but third-party CAD copyright disclaimer requires explicit user risk acceptance before ingestion. |
| `cvc_fp` | **CVC-FP** | Computer Vision Center (UAB), Figshare (`10.6084/m9.figshare.12082131`), Zenodo (`10.5281/zenodo.7921780`) | **~15 MB** (raw 122 plans) / **353.6 MB** (Figshare preprocessed archive) / ~500 MB extracted | CVC Academic Non-Commercial / **CC BY 4.0** (Figshare mirror) | **Conditional** (Mirror is CC BY 4.0) | Scanned rasters (4 styles) + SVG vector ground truth & binary masks | **YES**: Explicit structural wall, door, window, and room segmentation masks for 122 scanned drawings. | Original university host (`dag.cvc.uab.es`) is offline (timed out). Mirror on Figshare is fully accessible without credentials. | **CONDITIONAL**: Small sample size (122 plans); original server dead, but Figshare mirror is active. Recommended for rapid sanity and smoke tests. |
| `r2v` | **R2V (Raster-to-Vector)** | CVPR 2017 (`art-programmer/FloorplanTransformation`), LIFULL Co., Ltd. / NII IDR | Annotations: **~10 MB**; Images: **>10 GB** / >20 GB extracted | Annotations: **MIT**; Images: Proprietary LIFULL institutional agreement | **NO** (Restricted academic data agreement) | Vector representation (junctions, primitive lines, text files) | **YES**: Wall junctions and boundary lines annotated in vector format for ~870 plans. | **BLOCKED**: Raw floor plan images are gated behind an application to the National Institute of Informatics (NII) IDR. Requires institutional account and agreement. | **INELIGIBLE FOR AUTOMATED DOWNLOAD**: Violates zero-license acceptance and non-interactive constraints. Cannot be downloaded without user credentials. |
| `sesyd_floorplans` | **SESYD Floorplans** | Mathieu Delalandre / IJDAR 2010 (`mathieu.delalandre.free.fr/projects/sesyd/`) | **~6 MB** per zip archive / **~100 MB** total / ~250 MB extracted | Open Access Academic Research | **NO** (Academic benchmarking) | TIFF binary line drawings + XML symbol bounding boxes | **NO**: Contains annotations exclusively for 16 furniture and fixture symbols (armchair, table, bed, door, window, sink). **ZERO wall labels exist**. | Direct public HTTP download without authentication. | **INELIGIBLE FOR WALL SEGMENTATION**: Ground-truth contains zero wall or partition segmentations. Completely unsuitable for wall training. |
| `archcad_400k` *(Supplementary)* | **ArchCAD-400k** | arXiv 2025 (`2503.22346`) | Large-scale CAD dataset (>50 GB) | Academic Research | **NO** (Research preview) | CAD vector entities | **YES**: Large-scale architectural CAD elements. | Emerging research release; not yet mirrored on public HTTPS CDN. | **INELIGIBLE / FUTURE CANDIDATE**: Exceeds 10 GB limit; distribution not finalized. |

---

## 3. Data Structures & Type Definitions

The module will define the following data structures in `drywall_detection/audit/dataset_auditor.py` using Python standard library `enum` and `dataclasses`:

```python
"""Data structures for dataset audit and verification."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import shutil
import json
import logging


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

    @property
    def raw_size_mb(self) -> float:
        return self.raw_size_bytes / (1024 * 1024)

    @property
    def raw_size_gb(self) -> float:
        return self.raw_size_bytes / (1024 * 1024 * 1024)

    @property
    def extracted_size_gb(self) -> float:
        return self.extracted_size_bytes / (1024 * 1024 * 1024)


@dataclass
class DiskAuditResult:
    """Results of disk space evaluation on the target storage volume."""
    target_dir: str
    drive_mount: str
    total_bytes: int
    free_bytes: int
    required_download_bytes: int
    required_extracted_bytes: int
    sufficient_space: bool
    exceeds_10gb_threshold: bool
    warning_message: Optional[str] = None

    @property
    def free_gb(self) -> float:
        return self.free_bytes / (1024 * 1024 * 1024)

    @property
    def required_total_gb(self) -> float:
        return (self.required_download_bytes + self.required_extracted_bytes) / (1024 * 1024 * 1024)


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

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert enums to string values
        data["dataset_spec"]["license_category"] = self.dataset_spec.license_category.value
        data["dataset_spec"]["eligibility"] = self.dataset_spec.eligibility.value
        return data


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
        return self.available_disk_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "target_dir": self.target_dir,
            "available_disk_gb": round(self.available_disk_gb, 2),
            "recommended_dataset_id": self.recommended_dataset_id,
            "summary_counts": {
                "eligible": self.eligible_count,
                "conditional": self.conditional_count,
                "ineligible": self.ineligible_count,
                "total": len(self.audited_datasets)
            },
            "datasets": {k: v.to_dict() for k, v in self.audited_datasets.items()}
        }
```

---

## 4. `DatasetAuditor` Class Architecture & Method Signatures

The `DatasetAuditor` class encapsulates all audit logic, dataset specifications, disk inspection, and report generation.

```python
class DatasetAuditor:
    """
    Audits floor plan datasets for ML wall segmentation.
    
    Enforces licensing compliance, zero user agreement acceptance,
    disk space verification, 10 GB unannounced download ceiling,
    and ground-truth wall segmentation label existence.
    """

    DEFAULT_MAX_UNANNOUNCED_GB: float = 10.0

    def __init__(
        self,
        target_download_dir: Optional[Path] = None,
        max_unannounced_gb: float = DEFAULT_MAX_UNANNOUNCED_GB,
        offline_mode: bool = True
    ) -> None:
        """
        Initialize the DatasetAuditor.
        
        Args:
            target_download_dir: Target directory path for dataset storage.
                                Defaults to workspace `drywall_detection/data`.
            max_unannounced_gb: Maximum download size in GB permitted without
                                explicit user warning/confirmation (default: 10.0).
            offline_mode: If True, skips active HTTP network requests (default: True).
        """
        ...

    # --- Registry Management ---
    def get_candidate_specs(self) -> Dict[str, DatasetSpec]:
        """Returns the dictionary of all registered candidate dataset specs."""
        ...

    def get_spec(self, dataset_id: str) -> DatasetSpec:
        """Retrieves specification for a specific dataset ID or raises KeyError."""
        ...

    # --- Disk Space Evaluation ---
    def check_disk_space(
        self,
        dataset_id: str,
        target_dir: Optional[Path] = None,
        include_extracted: bool = True
    ) -> DiskAuditResult:
        """
        Inspects available disk storage against dataset download and extraction sizes.
        
        Evaluates:
        1. Free disk bytes on target volume.
        2. Whether free bytes >= required download bytes.
        3. Whether free bytes >= (download + extracted) bytes.
        4. Whether download size > max_unannounced_gb threshold (10 GB).
        
        Returns:
            DiskAuditResult with verification status, byte counts, and warnings.
        """
        ...

    # --- Network Verification ---
    def probe_network_endpoint(
        self,
        dataset_id: str,
        timeout_seconds: float = 5.0
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Safely tests network reachability of official source or mirror via HTTP HEAD/GET.
        
        Handles timeouts and errors gracefully without raising exceptions.
        
        Returns:
            Tuple of (is_reachable, http_status_code, error_message).
        """
        ...

    # --- Audit Execution ---
    def audit_dataset(
        self,
        dataset_id: str,
        check_network: bool = False
    ) -> DatasetAuditResult:
        """
        Performs a full audit of a single dataset.
        
        Evaluates eligibility, licensing guardrails, label existence,
        disk headroom, and downloadability.
        
        Returns:
            DatasetAuditResult with detailed findings, blockers, and warnings.
        """
        ...

    def audit_all(
        self,
        check_network: bool = False
    ) -> AuditReport:
        """
        Runs comprehensive audit across all registered candidate datasets.
        
        Returns:
            AuditReport containing all individual results, summaries, and recommendation.
        """
        ...

    # --- Formatting and Persistence ---
    def format_markdown_table(self, report: Optional[AuditReport] = None) -> str:
        """Generates a GitHub-flavored Markdown summary table of audited datasets."""
        ...

    def format_json_report(self, report: Optional[AuditReport] = None, indent: int = 2) -> str:
        """Generates a serialized JSON string representing the full audit report."""
        ...

    def save_reports(
        self,
        output_dir: Optional[Path] = None,
        base_filename: str = "dataset_audit_report"
    ) -> Dict[str, Path]:
        """
        Saves both Markdown and JSON audit reports to the designated reports directory.
        
        Returns:
            Dict mapping format ('markdown', 'json') to saved file Path.
        """
        ...
```

---

## 5. Detailed Logic & Algorithmic Guardrails

### 5.1 Disk Space Inspection Algorithm

```
Algorithm: check_disk_space(dataset_id, target_dir, include_extracted)
1. Resolve target_dir to absolute Path (defaults to config.DATA_DIR or ./drywall_detection/data).
2. Ensure target_dir parent exists or find first existing parent directory.
3. Call shutil.disk_usage(existing_dir) -> (total, used, free).
4. Retrieve spec = get_spec(dataset_id).
5. Compute required_download = spec.raw_size_bytes.
6. Compute required_extracted = spec.extracted_size_bytes if include_extracted else 0.
7. Compute required_total = required_download + required_extracted.
8. Evaluate sufficient_space:
   - If free < required_download:
       sufficient_space = False
       warning = "CRITICAL: Insufficient disk space for download. Free: {free_gb} GB, Required download: {req_gb} GB"
   - Else if free < required_total:
       sufficient_space = True  (can download, but extraction will fail)
       warning = "WARNING: Disk space sufficient for archive download ({dl_gb} GB), but insufficient for full extraction ({ext_gb} GB). Free: {free_gb} GB"
   - Else:
       sufficient_space = True
       warning = None
9. Evaluate 10 GB ceiling:
   - exceeds_10gb = (required_download > max_unannounced_gb * 1024^3)
   - If exceeds_10gb:
       append to warning: "ALERT: Download size ({dl_gb} GB) exceeds 10 GB limit. Explicit user confirmation required before initiation."
10. Return DiskAuditResult(target_dir, drive_mount, total, free, required_download, required_extracted, sufficient_space, exceeds_10gb, warning)
```

### 5.2 Zero License Acceptance & EULA Guardrail

```
Algorithm: evaluate_licensing_compliance(spec)
1. If spec.requires_login_or_eula is True:
   - blocker: "AUTOMATED ACCESS FORBIDDEN: Dataset requires formal institutional application, login credentials, or non-interactive EULA agreement ({details}). In accordance with project integrity constraints, no licenses or terms may be accepted on user's behalf."
   - is_downloadable_now = False
2. If spec.license_category == LicenseCategory.DISCLAIMED_THIRD_PARTY:
   - warning: "LEGAL NOTICE: Dataset annotations are permissible, but source CAD drawings carry third-party copyright disclaimers. User explicit risk acceptance required before commercial deployment."
3. If not spec.commercial_use_allowed:
   - warning: "LICENSE CONSTRAINT: Dataset is licensed for Non-Commercial / Academic Research only ({spec.license_name}). Cannot be bundled or redistributed in commercial product deliverables."
```

### 5.3 Wall Segmentation Label Verification

```
Algorithm: evaluate_wall_label_availability(spec)
1. If spec.has_wall_segmentation_labels is False:
   - blocker: "INELIGIBLE GROUND TRUTH: Dataset contains zero wall or partition annotations ({spec.wall_label_details}). It cannot be used to train or evaluate wall segmentation models."
   - eligibility = DatasetEligibility.INELIGIBLE
   - is_downloadable_now = False
2. Else:
   - Verify annotation format is supported (WKT polygon, SVG polygon, COCO panoptic mask).
   - Verify grouping key exists to prevent building/complex data leakage across splits.
```

### 5.4 Eligibility Verdict Engine

The final eligibility verdict is computed using a deterministic rule matrix:

| Condition | Verdict | `is_downloadable_now` |
|---|:---:|:---:|
| Permissive license (CC BY / MIT) + Explicit wall labels + Public direct HTTP + Size < 10 GB + Free disk OK | **ELIGIBLE** | `True` |
| Non-Commercial license (CC BY-NC) + Explicit wall labels + Public direct HTTP + Size < 10 GB + Free disk OK | **ELIGIBLE** *(with Non-Comm warning)* | `True` |
| Third-party disclaimer OR original server offline (mirror active) OR small sample size | **CONDITIONAL** | `True` *(with confirmation warning)* |
| Requires login / EULA agreement / credentialed portal | **INELIGIBLE** | `False` *(blocked by policy)* |
| Lacks wall segmentation ground truth labels | **INELIGIBLE** | `False` *(blocked by ground truth)* |
| Insufficient free disk space on target volume | *Keep verdict* | `False` *(blocked by disk)* |

---

## 6. Standalone CLI Interface Specification

The module must be directly runnable via:
```bash
python -m drywall_detection.audit.dataset_auditor [OPTIONS]
```

### CLI Arguments & Options:

| Flag | Type | Default | Description |
|---|---|---|---|
| `--target-dir` | Path | `drywall_detection/data/` | Target directory where datasets would be downloaded and checked for disk headroom. |
| `--output-dir` | Path | `drywall_detection/reports/` | Directory where `M1_dataset_audit_report.md` and `.json` will be saved. |
| `--dataset-id` | String | `None` (Audits all) | Specify a single dataset to audit (`msd`, `cubicasa5k`, `floorplancad`, `cvc_fp`, `r2v`, `sesyd`). |
| `--check-network` | Flag | `False` | Actively probe official URLs and mirrors via non-blocking HTTP HEAD requests. |
| `--max-unannounced-gb` | Float | `10.0` | Maximum unannounced download threshold in GB before triggering mandatory user notification warnings. |
| `--format` | Choice | `both` | Output format: `both`, `table`, `json`, `md`. |
| `--quiet` | Flag | `False` | Suppress informational console logging; output only table/JSON results. |
| `--save` | Flag | `True` | Automatically save Markdown and JSON reports to disk. |

### CLI Exit Codes:
- `0`: Success — Audit completed cleanly without blockers on recommended or specified eligible datasets.
- `1`: Unexpected execution error or invalid CLI arguments.
- `2`: Blocker detected — Insufficient disk space on target volume, or the specifically requested dataset is ineligible / requires EULA acceptance.

### Example CLI Invocations:

```bash
# 1. Run complete audit across all 6 datasets (offline mode, fast, non-blocking):
python -m drywall_detection.audit.dataset_auditor

# 2. Run audit with active network probing and save to custom report directory:
python -m drywall_detection.audit.dataset_auditor --check-network --output-dir drywall_detection/reports

# 3. Audit single dataset and output JSON to stdout:
python -m drywall_detection.audit.dataset_auditor --dataset-id msd --format json

# 4. Check disk headroom for custom target partition (e.g., E:\):
python -m drywall_detection.audit.dataset_auditor --target-dir E:\datasets\drywall
```

---

## 7. Concrete Implementation Blueprint for Worker

The worker implementing `drywall_detection/audit/dataset_auditor.py` should follow this structured architecture:

### 7.1 Dataset Specifications Registry Constant

```python
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
        eligibility_rationale="Fully permissive CC BY 4.0 license, compact download (<200 MB), explicit vector wall polygons, strict site_id grouping."
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
        eligibility_rationale="Primary academic benchmark, rich SVG wall polygons, under 10 GB download limit. Non-commercial license."
    ),
    "floorplancad": DatasetSpec(
        dataset_id="floorplancad",
        display_name="FloorPlanCAD",
        official_url="https://floorplancad.github.io/",
        direct_download_url=None,
        api_endpoint="https://huggingface.co/datasets/Voxel51/FloorPlanCAD",
        mirror_urls=[
            "https://huggingface.co/datasets/Voxel51/FloorPlanCAD",
            "https://drive.google.com/drive/folders/1HcyKt396o7qK1V1Q5oD0sO_gqZpQ9Q3Z"
        ],
        raw_size_bytes=476_000_000,  # ~454 MB (HF subset)
        extracted_size_bytes=1_288_000_000,
        license_name="Annotations: CC BY-NC 4.0; Drawings: Third-party copyright disclaimer",
        license_category=LicenseCategory.DISCLAIMED_THIRD_PARTY,
        commercial_use_allowed=False,
        requires_login_or_eula=True,  # Disclaimer requires explicit user acknowledgment
        eula_or_agreement_details="Users accept full responsibility for copyrighted third-party CAD drawings",
        annotation_format="SVG vector primitives, PNG crops, COCO panoptic format",
        has_wall_segmentation_labels=True,
        wall_label_details="Wall is explicitly labeled as an uncountable 'Stuff' class alongside 28 'Thing' classes",
        sample_count=15000,
        grouping_key="source_drawing_id",
        eligibility=DatasetEligibility.CONDITIONAL,
        eligibility_rationale="Excellent CAD domain match, but third-party copyright disclaimer requires explicit user risk acceptance."
    ),
    "cvc_fp": DatasetSpec(
        dataset_id="cvc_fp",
        display_name="CVC-FP",
        official_url="https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/",
        direct_download_url="https://ndownloader.figshare.com/articles/12082131/versions/1",
        api_endpoint=None,
        mirror_urls=[
            "https://figshare.com/articles/dataset/12082131",
            "https://zenodo.org/records/7921780"
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
        eligibility_rationale="Small sample size (122 plans); original university server offline; accessible via Figshare mirror."
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
        eligibility_rationale="Automated download forbidden: raw images require formal institutional NII IDR agreement and credentials."
    ),
    "sesyd_floorplans": DatasetSpec(
        dataset_id="sesyd_floorplans",
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
        eligibility_rationale="Ineligible for wall segmentation: contains zero ground-truth wall or partition labels."
    )
}
```

### 7.2 Graceful Network Probe Helper

```python
import urllib.request
import urllib.error

def _probe_url(url: str, timeout: float = 5.0) -> Tuple[bool, Optional[int], Optional[str]]:
    """Safe, non-blocking HTTP probe using HEAD with GET fallback."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DrywallDetection-Auditor/1.0"},
            method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (True, resp.status, None)
    except urllib.error.HTTPError as e:
        # Some servers reject HEAD requests with 403 or 405; test with partial GET
        if e.code in (403, 405):
            try:
                get_req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "DrywallDetection-Auditor/1.0", "Range": "bytes=0-10"},
                    method="GET"
                )
                with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                    return (True, resp.status, None)
            except Exception as inner_e:
                return (False, e.code, str(inner_e))
        return (False, e.code, str(e))
    except Exception as e:
        return (False, None, str(e))
```

### 7.3 Integration with Unit Test Suite (`test_audit.py`)

To ensure 100% testability as designed by `explorer_m1_3`:
1. `DatasetAuditor(offline_mode=True)` must execute without network calls, mocking nothing or completing in <50 ms.
2. `check_disk_space()` can accept any arbitrary `target_dir` (e.g. `tmp_path` fixture in `pytest`).
3. Threshold violations (e.g., > 10 GB warning, insufficient disk error) must be verified by passing simulated byte counts or mocked `shutil.disk_usage`.
4. R2V institutional blocker and SESYD missing-wall-label blocker must produce strict deterministic `blockers` list entries and `is_downloadable_now = False`.

---

## 8. Summary of Downstream Deliverables for Milestone M1

When the Worker executes this specification:
1. `drywall_detection/audit/dataset_auditor.py` will be created with complete type annotations, docstrings, and CLI.
2. Executing `python -m drywall_detection.audit.dataset_auditor` will inspect local disk headroom, evaluate all 6 candidate datasets, generate `drywall_detection/reports/dataset_audit_report.md` and `.json`.
3. The generated table will feed directly into the authoritative `drywall_detection/reports/M1_audit_report.md`.
4. Milestone M2 downloader (`drywall_detection/data/downloader.py`) will import `DatasetAuditor` to guarantee disk safety and licensing verification prior to downloading Modified Swiss Dwellings or CubiCasa5K.
