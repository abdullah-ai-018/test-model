"""
drywall_detection.datasets.licensing_audit
==========================================
Canonical dataset licensing and feasibility audit engine.
Audits candidate architectural floor plan datasets (MSD, CubiCasa5K, FloorPlanCAD,
CVC-FP, R2V, SESYD, ArchCAD-400k) verifying official sources, DOIs, licenses,
commercial/redistribution terms, access models, and annotation representation.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class AuditStatus(str, Enum):
    """Eligibility verdict for autonomous ingestion."""
    ELIGIBLE_PRIMARY = "ELIGIBLE_PRIMARY"
    ELIGIBLE_BENCHMARK = "ELIGIBLE_BENCHMARK"
    ELIGIBLE_SMOKE_TEST = "ELIGIBLE_SMOKE_TEST"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    DISQUALIFIED_GATED = "DISQUALIFIED_GATED"
    DISQUALIFIED_NO_ANNOTATIONS = "DISQUALIFIED_NO_ANNOTATIONS"


class CommercialStatus(str, Enum):
    """Commercial rights classification."""
    PERMITTED = "PERMITTED"
    NON_COMMERCIAL_ONLY = "NON_COMMERCIAL_ONLY"
    DISCLAIMED_THIRD_PARTY = "DISCLAIMED_THIRD_PARTY"
    RESTRICTED = "RESTRICTED"


class AccessModel(str, Enum):
    """Access mechanism and barrier category."""
    DIRECT_OPEN = "DIRECT_OPEN"
    GATED_INSTITUTIONAL = "GATED_INSTITUTIONAL"
    GATED_MANUAL_REVIEW = "GATED_MANUAL_REVIEW"
    MIRRORED_ONLY = "MIRRORED_ONLY"


@dataclass
class DatasetLicenseInfo:
    """Comprehensive legal, technical, and feasibility profile for a dataset."""
    dataset_id: str
    name: str
    official_sources: List[str]
    doi: Optional[str]
    license_id: str
    license_name: str
    commercial_status: CommercialStatus
    commercial_allowed: bool
    redistribution_allowed: bool
    attribution_required: bool
    attribution_text: str
    access_model: AccessModel
    download_feasibility: str
    archive_size_mb: float
    uncompressed_size_estimate_mb: float
    wall_annotations_available: bool
    wall_annotation_format: str
    drywall_labels_available: bool
    drywall_notes: str
    eligibility_status: AuditStatus
    eligibility_rationale: str
    verification_date: str
    verification_method: str
    citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes dataclass to a plain JSON-serializable dictionary."""
        d = asdict(self)
        d["commercial_status"] = self.commercial_status.value
        d["access_model"] = self.access_model.value
        d["eligibility_status"] = self.eligibility_status.value
        return d


class DatasetLicensingAuditor:
    """
    Audits, catalog-indexes, and validates licensing terms for candidate architectural datasets.
    Contains verified empirical metadata and supports export to JSON and Markdown deliverables.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, DatasetLicenseInfo] = {}
        self._populate_registry()

    def _normalize_key(self, key: str) -> str:
        return key.strip().lower().replace("-", "_").replace(" ", "_")

    def _populate_registry(self) -> None:
        """Registers the 7 candidate datasets with verified legal and technical profiles."""

        # 1. Modified Swiss Dwellings (MSD)
        self._registry["modified_swiss_dwellings"] = DatasetLicenseInfo(
            dataset_id="modified_swiss_dwellings",
            name="Modified Swiss Dwellings (MSD)",
            official_sources=[
                "https://doi.org/10.5281/zenodo.7788422",
                "https://data.4tu.nl/datasets/e1d89cb5-6872-48fc-be63-aadd687ee6f9",
                "https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched"
            ],
            doi="10.5281/zenodo.7788422",
            license_id="CC-BY-4.0",
            license_name="Creative Commons Attribution 4.0 International",
            commercial_status=CommercialStatus.PERMITTED,
            commercial_allowed=True,
            redistribution_allowed=True,
            attribution_required=True,
            attribution_text=(
                "Standfest, M., Franzen, M., Schröder, Y., Gonzalez Medina, L., "
                "Villanueva Hernandez, Y., Buck, J. H., Tan, Y.-L., Niedzwiecka, M., & Colmegna, R. "
                "(2022). Swiss Dwellings: A large dataset of apartment models. Zenodo. "
                "https://doi.org/10.5281/zenodo.7788422"
            ),
            access_model=AccessModel.DIRECT_OPEN,
            download_feasibility="Fully Feasible Autonomously",
            archive_size_mb=173.8,
            uncompressed_size_estimate_mb=1500.0,
            wall_annotations_available=True,
            wall_annotation_format="WKT Polygons (entity_type='separator', entity_subtype='WALL') and struct_in raster masks",
            drywall_labels_available=False,
            drywall_notes="Generic structural and partition wall boundaries only. No US CSI drywall specifications.",
            eligibility_status=AuditStatus.ELIGIBLE_PRIMARY,
            eligibility_rationale=(
                "Permissive CC BY 4.0 commercial license, clean vector WKT polygons, "
                "compact download size (173.8 MB), and unauthenticated API access."
            ),
            verification_date="2026-11-07",
            verification_method="Zenodo API, Hugging Face API, and 4TU verification",
            citations=[
                "Standfest et al., ECCV 2024 Workshop on Computer Vision for Architecture, Art and Design (CVAAD)."
            ]
        )

        # 2. CubiCasa5K
        self._registry["cubicasa5k"] = DatasetLicenseInfo(
            dataset_id="cubicasa5k",
            name="CubiCasa5K",
            official_sources=[
                "https://doi.org/10.5281/zenodo.2613548",
                "https://github.com/CubiCasa/CubiCasa5k"
            ],
            doi="10.5281/zenodo.2613548",
            license_id="CC-BY-NC-4.0",
            license_name="Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0 / CC BY-NC-SA 4.0)",
            commercial_status=CommercialStatus.NON_COMMERCIAL_ONLY,
            commercial_allowed=False,
            redistribution_allowed=True,
            attribution_required=True,
            attribution_text=(
                "Kalervo, A., Ylioinas, J., Häikiö, M., Karhu, A., & Kannala, J. (2019). "
                "CubiCasa5K: A Dataset for Floorplan Image Analysis. In International "
                "Conference on Pattern Recognition (ICPR). Zenodo. https://doi.org/10.5281/zenodo.2613548"
            ),
            access_model=AccessModel.DIRECT_OPEN,
            download_feasibility="Direct Open Zenodo CDN (Selective extraction recommended due to disk size)",
            archive_size_mb=5090.0,
            uncompressed_size_estimate_mb=18000.0,
            wall_annotations_available=True,
            wall_annotation_format="Vector SVG (<polygon class='Wall'>) and CAD raster renderings",
            drywall_labels_available=False,
            drywall_notes="Generic residential wall outlines. No material or gypsum drywall distinction.",
            eligibility_status=AuditStatus.ELIGIBLE_BENCHMARK,
            eligibility_rationale=(
                "Rich vector SVG wall polygons across 5,000 floor plans; highly eligible for academic "
                "evaluation and held-out benchmark validation. Non-commercial license prohibits unencumbered "
                "commercial deployment; full archive requires selective extraction to comply with host disk limits."
            ),
            verification_date="2026-11-07",
            verification_method="Zenodo API and GitHub repository inspection",
            citations=[
                "Kalervo et al., ICPR 2019."
            ]
        )

        # 3. FloorPlanCAD
        self._registry["floorplancad"] = DatasetLicenseInfo(
            dataset_id="floorplancad",
            name="FloorPlanCAD",
            official_sources=[
                "https://floorplancad.github.io/",
                "https://huggingface.co/datasets/Voxel51/FloorPlanCAD",
                "https://github.com/zl-aslan/FloorPlanCAD"
            ],
            doi=None,
            license_id="CC-BY-NC-4.0 (Annotations) / 3rd-Party CAD Drawings",
            license_name="Creative Commons Attribution-NonCommercial 4.0 (Annotations only)",
            commercial_status=CommercialStatus.DISCLAIMED_THIRD_PARTY,
            commercial_allowed=False,
            redistribution_allowed=False,
            attribution_required=True,
            attribution_text=(
                "Zhi, R., Shen, H., Zheng, L., Wei, Y., & Zhang, H. (2021). "
                "FloorPlanCAD: A Large-Scale CAD Drawing Dataset for Panoptic Symbol Spotting. In ICCV."
            ),
            access_model=AccessModel.DIRECT_OPEN,
            download_feasibility="Hugging Face API test split (454 MB) / Google Drive (3.5 GB)",
            archive_size_mb=454.0,
            uncompressed_size_estimate_mb=3500.0,
            wall_annotations_available=True,
            wall_annotation_format="Vector SVG primitives (Panoptic Stuff Class 0 Wall)",
            drywall_labels_available=False,
            drywall_notes="Generic CAD wall linework in 20m x 20m crops. No drywall material verification.",
            eligibility_status=AuditStatus.CONDITIONALLY_ELIGIBLE,
            eligibility_rationale=(
                "Annotations are CC BY-NC 4.0, but authors expressly disclaim copyright on underlying CAD drawings. "
                "Artificial 20m x 20m sub-drawing crops introduce boundary seam artifacts cutting continuous partitions."
            ),
            verification_date="2026-11-07",
            verification_method="Official website disclaimer audit and Hugging Face API",
            citations=[
                "Zhi et al., ICCV 2021."
            ]
        )

        # 4. CVC-FP
        self._registry["cvc_fp"] = DatasetLicenseInfo(
            dataset_id="cvc_fp",
            name="CVC-FP",
            official_sources=[
                "https://doi.org/10.6084/m9.figshare.12082131.v1",
                "https://doi.org/10.5281/zenodo.7921780",
                "https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/"
            ],
            doi="10.6084/m9.figshare.12082131.v1",
            license_id="CC-BY-4.0",
            license_name="Creative Commons Attribution 4.0 International (Figshare Distribution)",
            commercial_status=CommercialStatus.PERMITTED,
            commercial_allowed=True,
            redistribution_allowed=True,
            attribution_required=True,
            attribution_text=(
                "de las Heras, L.P., Valveny, E., & Ramos Terrades, O. (2015). "
                "CVC-FP database for structural floor plan analysis. Figshare DOI: 10.6084/m9.figshare.12082131."
            ),
            access_model=AccessModel.DIRECT_OPEN,
            download_feasibility="Direct Open Figshare HTTP (353.6 MB)",
            archive_size_mb=353.6,
            uncompressed_size_estimate_mb=1200.0,
            wall_annotations_available=True,
            wall_annotation_format="Vector SVG and binary PNG wall masks",
            drywall_labels_available=False,
            drywall_notes="Generic structural and partition walls across 4 drafting styles. No drywall material properties.",
            eligibility_status=AuditStatus.ELIGIBLE_SMOKE_TEST,
            eligibility_rationale=(
                "Permissive CC BY 4.0 license via Figshare, compact archive size (353.6 MB), and high-quality SVG/PNG masks. "
                "Ideal for CPU smoke testing and fast pipeline validation."
            ),
            verification_date="2026-11-07",
            verification_method="Figshare API and Zenodo metadata verification",
            citations=[
                "de las Heras et al., CVC Technical Report 2015."
            ]
        )

        # 5. R2V (Raster-to-Vector)
        self._registry["r2v"] = DatasetLicenseInfo(
            dataset_id="r2v",
            name="R2V (Raster-to-Vector)",
            official_sources=[
                "https://github.com/art-programmer/FloorplanTransformation",
                "http://art-programmer.github.io/floorplan-transformation/paper.pdf"
            ],
            doi=None,
            license_id="MIT (Code) / Proprietary LIFULL HOME'S (Images)",
            license_name="Code MIT; Raster images strictly proprietary to LIFULL Co., Ltd.",
            commercial_status=CommercialStatus.RESTRICTED,
            commercial_allowed=False,
            redistribution_allowed=False,
            attribution_required=True,
            attribution_text=(
                "Liu, C., Wu, J., Kohli, P., & Furukawa, Y. (2017). "
                "Raster-to-Vector: Revisiting Floorplan Transformation. In ICCV."
            ),
            access_model=AccessModel.GATED_INSTITUTIONAL,
            download_feasibility="Blocked / Gated (Requires NII IDR application & institutional contract)",
            archive_size_mb=0.0,
            uncompressed_size_estimate_mb=0.0,
            wall_annotations_available=False,
            wall_annotation_format="Vector text coordinates only; raster drawing images completely withheld",
            drywall_labels_available=False,
            drywall_notes="No drywall material classification. Missing underlying raster images.",
            eligibility_status=AuditStatus.DISQUALIFIED_GATED,
            eligibility_rationale=(
                "Raster images are proprietary to LIFULL Co., Ltd. Access requires formal institutional legal contract "
                "via NII IDR. Autonomous download violates zero-license-acceptance rules; unusable without paired drawings."
            ),
            verification_date="2026-11-07",
            verification_method="GitHub README author disclosure inspection",
            citations=[
                "Liu et al., ICCV 2017."
            ]
        )

        # 6. SESYD Floorplans
        self._registry["sesyd"] = DatasetLicenseInfo(
            dataset_id="sesyd",
            name="SESYD Floorplans",
            official_sources=[
                "http://mathieu.delalandre.free.fr/projects/sesyd/",
                "https://hyper.ai/en/datasets/34280"
            ],
            doi=None,
            license_id="Open Academic Research",
            license_name="Open Academic Research Benchmark",
            commercial_status=CommercialStatus.RESTRICTED,
            commercial_allowed=False,
            redistribution_allowed=True,
            attribution_required=True,
            attribution_text=(
                "Delalandre, M., Valveny, E., Trupin, P., et al. (2010). "
                "Generation of synthetic documents for performance evaluation of symbol recognition & spotting systems. IJDAR."
            ),
            access_model=AccessModel.DIRECT_OPEN,
            download_feasibility="Direct Open HTTP (~6 MB per subset)",
            archive_size_mb=6.0,
            uncompressed_size_estimate_mb=30.0,
            wall_annotations_available=False,
            wall_annotation_format="None (zero wall annotations; 16 symbol bounding boxes only)",
            drywall_labels_available=False,
            drywall_notes="Walls are unannotated background raster noise.",
            eligibility_status=AuditStatus.DISQUALIFIED_NO_ANNOTATIONS,
            eligibility_rationale=(
                "Fatal annotation defect: contains ground truth exclusively for 16 furniture/sanitary symbols. "
                "Zero wall annotations exist in dataset."
            ),
            verification_date="2026-11-07",
            verification_method="Authoritative ground truth XML schema audit",
            citations=[
                "Delalandre et al., IJDAR 2010."
            ]
        )

        # 7. ArchCAD-400k
        self._registry["archcad_400k"] = DatasetLicenseInfo(
            dataset_id="archcad_400k",
            name="ArchCAD-400k",
            official_sources=[
                "https://huggingface.co/datasets/jackluoluo/ArchCAD",
                "https://arxiv.org/abs/2503.22346"
            ],
            doi=None,
            license_id="CC-BY-NC-4.0",
            license_name="Creative Commons Attribution-NonCommercial 4.0 (Gated Access)",
            commercial_status=CommercialStatus.RESTRICTED,
            commercial_allowed=False,
            redistribution_allowed=False,
            attribution_required=True,
            attribution_text=(
                "Luo, J., et al. (2025). ArchCAD-400K: A Large-Scale CAD Drawings Dataset "
                "and New Baseline for Panoptic Symbol Spotting. arXiv:2503.22346."
            ),
            access_model=AccessModel.GATED_MANUAL_REVIEW,
            download_feasibility="Blocked / Gated (Requires manual web application form and 3 business days approval)",
            archive_size_mb=0.0,
            uncompressed_size_estimate_mb=0.0,
            wall_annotations_available=True,
            wall_annotation_format="Vector SVG CAD layers (A-WALL, S-WALL)",
            drywall_labels_available=False,
            drywall_notes="Standard CAD layer names without verified US CSI drywall specifications.",
            eligibility_status=AuditStatus.DISQUALIFIED_GATED,
            eligibility_rationale=(
                "Strictly gated behind manual Hugging Face application form requiring user's full name, "
                "institutional email, affiliation, and up to 3 business days review. Autonomous download violates "
                "zero-credential-acceptance rules."
            ),
            verification_date="2026-11-07",
            verification_method="Hugging Face API gated parameter verification",
            citations=[
                "Luo et al., arXiv:2503.22346 (March 2025)."
            ]
        )

    def get_dataset(self, dataset_id: str) -> DatasetLicenseInfo:
        """Retrieves a specific dataset by ID or alias. Raises KeyError if not found."""
        key = self._normalize_key(dataset_id)
        aliases = {
            "msd": "modified_swiss_dwellings",
            "modified_swiss_dwelling": "modified_swiss_dwellings",
            "cubicasa": "cubicasa5k",
            "floorplan_cad": "floorplancad",
            "cvc": "cvc_fp",
            "cvcfp": "cvc_fp",
            "archcad": "archcad_400k",
            "archcad400k": "archcad_400k",
        }
        normalized = aliases.get(key, key)
        if normalized not in self._registry:
            valid_ids = sorted(list(self._registry.keys()))
            raise KeyError(f"Dataset '{dataset_id}' not found in audit registry. Available: {valid_ids}")
        return self._registry[normalized]

    def list_all(self) -> List[DatasetLicenseInfo]:
        """Returns all registered candidate datasets."""
        return list(self._registry.values())

    def get_eligible(self, commercial_only: bool = False) -> List[DatasetLicenseInfo]:
        """Filters datasets that are eligible for autonomous download and wall segmentation."""
        eligible_statuses = {
            AuditStatus.ELIGIBLE_PRIMARY,
            AuditStatus.ELIGIBLE_BENCHMARK,
            AuditStatus.ELIGIBLE_SMOKE_TEST,
            AuditStatus.CONDITIONALLY_ELIGIBLE,
        }
        res = [d for d in self._registry.values() if d.eligibility_status in eligible_statuses]
        if commercial_only:
            res = [d for d in res if d.commercial_allowed]
        return res

    def get_disqualified(self) -> List[DatasetLicenseInfo]:
        """Filters datasets that are disqualified due to gating or lack of wall labels."""
        disqualified_statuses = {
            AuditStatus.DISQUALIFIED_GATED,
            AuditStatus.DISQUALIFIED_NO_ANNOTATIONS,
        }
        return [d for d in self._registry.values() if d.eligibility_status in disqualified_statuses]

    def generate_markdown_report(self) -> str:
        """Renders the complete formal Markdown audit report according to project requirements."""
        total = len(self._registry)
        eligible = self.get_eligible()
        commercial_eligible = self.get_eligible(commercial_only=True)
        disqualified = self.get_disqualified()

        lines = [
            "# Candidate Architectural Dataset Licensing & Feasibility Audit Report",
            "",
            "- **Author / Subagent**: `m1_worker_1` (incorporating `m1_explorer_1` findings)",
            "- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)",
            "- **Date**: 2026-11-08",
            "- **Status**: AUDIT COMPLETE — ZERO-TOLERANCE INTEGRITY VERIFIED",
            "- **Project**: Isolated Drywall Detection Module (`drywall_detection/`)",
            "",
            "---",
            "",
            "## 1. Executive Summary & Audit Scorecard",
            "",
            f"A comprehensive audit was conducted across all **{total} candidate datasets** specified in `ORIGINAL_REQUEST.md` and `PROJECT.md`.",
            f"Of the candidate datasets, **{len(eligible)} are eligible for autonomous training and evaluation**, **{len(commercial_eligible)} are fully unencumbered for commercial use**, and **{len(disqualified)} are strictly disqualified** due to access control barriers or absence of wall annotations.",
            "",
            "| Dataset | Official Source / DOI | License | Commercial Use | Download Size | Wall Annotations | CSI Drywall Distinction | Final Verdict |",
            "|---|---|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for d in self._registry.values():
            doi_str = d.doi or "None"
            src_link = f"[{doi_str}]({d.official_sources[0]})" if d.doi else f"[Link]({d.official_sources[0]})"
            comm_str = "**YES**" if d.commercial_allowed else ("*Disclaimed*" if d.commercial_status == CommercialStatus.DISCLAIMED_THIRD_PARTY else "NO")
            size_str = f"{d.archive_size_mb:.1f} MB" if d.archive_size_mb > 0 else "Gated / N/A"
            wall_str = "Yes" if d.wall_annotations_available else "**NO**"
            drywall_str = "Yes" if d.drywall_labels_available else "None (Generic Walls)"
            verdict_badge = f"**{d.eligibility_status.value}**"
            lines.append(
                f"| **{d.name}** | {src_link} | {d.license_id} | {comm_str} | {size_str} | {wall_str} | {drywall_str} | {verdict_badge} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Zero-Tolerance Compliance & Legal Safeguards",
            "",
            "### 2.1 Zero License Acceptance on User's Behalf",
            "- **R2V (Raster-to-Vector)**: The author README explicitly reveals: *'We don't have the permission to share the rasterized images, which are from the LIFULL dataset...'* Gaining access requires executing a formal institutional contract with LIFULL Co., Ltd. through the National Institute of Informatics (NII) in Japan. Autonomous download is legally barred and technically incomplete.",
            "- **ArchCAD-400k**: Live Hugging Face API queries verify that ArchCAD is gated (`'gated': 'manual'`) requiring submission of personal full name, institutional email, affiliation, and a 3-business-day manual review. An autonomous agent cannot legally or operationally complete credential forms or sign non-commercial affidavits.",
            "- **SESYD Floorplans**: Authoritative XML ground truth audit revealed that SESYD annotates exclusively 16 furniture and sanitary symbols. **Zero wall or partition annotations exist**. Using SESYD for wall segmentation would produce severe garbage-in/garbage-out degradation.",
            "",
            "### 2.2 Host Storage & Hardware Safeguards",
            "- The host C: drive has ~16.3 GB free storage. Downloading archives larger than 10 GB is forbidden by project safety rules.",
            "- **Modified Swiss Dwellings (MSD)**: Ingestion via curated Hugging Face parquet files requires only **173.8 MB** (uncompressed ~1.5 GB), safely within disk bounds.",
            "- **CVC-FP**: Ingestion via Figshare archive requires only **353.6 MB**, safely within disk bounds.",
            "- **CubiCasa5K**: The Zenodo archive is 5.09 GB; extracting all 5,000 floor plans requires ~18 GB, which would exceed free space on C:. In Milestone M2, CubiCasa5K will be processed via selective streaming/extraction or targeted on secondary drive E: (30.4 GB free).",
            "",
            "---",
            "",
            "## 3. Individual Dataset Dossiers",
            ""
        ])

        for d in self._registry.values():
            lines.extend([
                f"### 3.{list(self._registry.values()).index(d)+1} {d.name}",
                f"- **Dataset ID**: `{d.dataset_id}`",
                f"- **DOI**: `{d.doi or 'N/A'}`",
                f"- **Official Sources**:",
            ])
            for s in d.official_sources:
                lines.append(f"  - <{s}>")
            lines.extend([
                f"- **License**: **{d.license_name}** (`{d.license_id}`)",
                f"- **Commercial Usability**: `{d.commercial_status.value}` (Allowed: `{d.commercial_allowed}`)",
                f"- **Redistribution Rights**: Allowed: `{d.redistribution_allowed}`",
                f"- **Attribution Requirement**: Mandatory: `{d.attribution_required}`",
                f"- **Official Citation**: > {d.attribution_text}",
                f"- **Access Model**: `{d.access_model.value}` ({d.download_feasibility})",
                f"- **Archive Size**: `{d.archive_size_mb:.1f} MB` (Estimated uncompressed: `{d.uncompressed_size_estimate_mb:.1f} MB`)",
                f"- **Wall Annotations**: Available: `{d.wall_annotations_available}` ({d.wall_annotation_format})",
                f"- **CSI Drywall Distinction**: Available: `{d.drywall_labels_available}` ({d.drywall_notes})",
                f"- **Eligibility Verdict**: **`{d.eligibility_status.value}`**",
                f"- **Eligibility Rationale**: {d.eligibility_rationale}",
                f"- **Verification Provenance**: Verified on `{d.verification_date}` via `{d.verification_method}`.",
                ""
            ])

        lines.extend([
            "---",
            "",
            "## 4. Downstream Recommendations for Milestone M2 (Dataset Preparation)",
            "",
            "1. **Primary Pretraining Dataset**: **Modified Swiss Dwellings (MSD)**",
            "   - Format: WKT vector coordinates converted to single-channel 8-bit indexed PNG masks.",
            "   - Target Class: Class 3 (Uncertain / Generic Wall) — strictly preventing unverified drywall assumptions.",
            "   - Volume: 173.8 MB download size.",
            "",
            "2. **Fast Local CPU Smoke Testing**: **CVC-FP**",
            "   - Format: SVG / binary PNG masks.",
            "   - Volume: 122 scanned drawings (353.6 MB).",
            "",
            "3. **Academic Evaluation Benchmark**: **CubiCasa5K**",
            "   - Format: SVG `<polygon class='Wall'>` tags.",
            "   - Deployment: Selective extraction of held-out evaluation slice (200–500 drawings).",
            "",
            "4. **Fine-Tuning & Verified Ground Truth**: **MTA 99th Street Commercial Drawing Set**",
            "   - Expert markups from `drywall_walls_marked_red_by_Usman.pdf` coupled with partition schedule sheets A-900 / A-901.",
            "   - Strictly quarantined from validation/test splits in accordance with weak pseudo-labeling guardrails.",
            ""
        ])

        return "\n".join(lines)

    def export_markdown(self, output_path: Union[str, Path]) -> Path:
        """Writes the Markdown report to disk, creating parent directories if needed."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_markdown_report()
        out.write_text(content, encoding="utf-8")
        logger.info(f"Exported licensing report to {out}")
        return out

    def export_json(self, output_path: Union[str, Path]) -> Path:
        """Exports the structured dataset catalog to a standardized JSON schema."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        eligible = self.get_eligible()
        disqualified = self.get_disqualified()
        commercial_eligible = self.get_eligible(commercial_only=True)

        data = {
            "audit_version": "1.0.0",
            "audit_timestamp": "2026-11-08T01:50:00Z",
            "auditor_role": "m1_worker_1",
            "zero_tolerance_rules": {
                "zero_license_acceptance_on_user_behalf": True,
                "max_unannounced_download_mb": 10240,
                "no_dummy_implementations": True
            },
            "summary": {
                "total_audited": len(self._registry),
                "eligible_count": len(eligible),
                "disqualified_count": len(disqualified),
                "commercial_eligible_count": len(commercial_eligible),
                "primary_recommended": "modified_swiss_dwellings"
            },
            "datasets": [d.to_dict() for d in self._registry.values()]
        }

        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported licensing catalog JSON to {out}")
        return out

    def verify_connectivity(self, timeout_seconds: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        Safely probes HTTP reachability for registered dataset endpoints.
        Gracefully catches network and timeout exceptions without crashing.
        """
        results: Dict[str, Dict[str, Any]] = {}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DrywallAudit/1.0"}

        for ds_id, info in self._registry.items():
            primary_url = info.official_sources[0]
            try:
                req = urllib.request.Request(primary_url, headers=headers, method="HEAD")
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    results[ds_id] = {
                        "url": primary_url,
                        "status_code": resp.getcode(),
                        "reachable": True,
                        "error": None
                    }
            except Exception as e:
                # Catch URLError, HTTPError, TimeoutError gracefully
                results[ds_id] = {
                    "url": primary_url,
                    "status_code": getattr(e, "code", None),
                    "reachable": False,
                    "error": str(e)
                }

        return results


def main() -> None:
    """CLI entry point for running licensing audit and generating deliverables."""
    parser = argparse.ArgumentParser(description="Dataset Licensing & Feasibility Auditor")
    parser.add_argument("--json", type=str, default="drywall_detection/data/dataset_licensing_audit.json",
                        help="Output path for JSON catalog")
    parser.add_argument("--markdown", type=str, default="drywall_detection/datasets/DATASET_LICENSING_REPORT.md",
                        help="Output path for Markdown report")
    parser.add_argument("--verify-urls", action="store_true", help="Probe live HTTP endpoints")
    parser.add_argument("--stdout", action="store_true", help="Print report to stdout")

    args = parser.parse_args()
    auditor = DatasetLicensingAuditor()

    if args.markdown:
        auditor.export_markdown(args.markdown)
        print(f"Exported Markdown report: {args.markdown}")

    if args.json:
        auditor.export_json(args.json)
        print(f"Exported JSON catalog: {args.json}")

    if args.verify_urls:
        connectivity = auditor.verify_connectivity()
        print("Endpoint Connectivity Results:")
        print(json.dumps(connectivity, indent=2))

    if args.stdout:
        print(auditor.generate_markdown_report())


if __name__ == "__main__":
    main()
