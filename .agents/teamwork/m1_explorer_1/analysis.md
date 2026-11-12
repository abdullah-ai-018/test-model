# Technical Analysis: Dataset Research, Licensing Audit & Module Architecture

**Author:** `m1_explorer_1` (Dataset Licensing & Research Explorer)  
**Milestone:** M1 (Dataset Research, Licensing Audit & Unified Preparation)  
**Target Module:** `drywall_detection/datasets/licensing_audit.py` & `drywall_detection/audit/dataset_auditor.py`  
**Target Report:** `drywall_detection/datasets/DATASET_LICENSING_REPORT.md` & `drywall_detection/data/dataset_licensing_audit.json`  
**Date:** 2026-11-07T20:46:00Z  

---

## 1. Executive Summary & Audit Scope

This investigation comprehensively audits the seven candidate architectural datasets cited in `ORIGINAL_REQUEST.md` and `PROJECT.md`:
1. **Modified Swiss Dwellings (MSD)**
2. **CubiCasa5K**
3. **FloorPlanCAD**
4. **CVC-FP**
5. **R2V (Raster-to-Vector)**
6. **SESYD Floorplans**
7. **ArchCAD-400k**

The audit evaluates each dataset along seven strict dimensions:
- **Official Provenance & Persistent Identifiers (DOIs, Repositories)**
- **Verbatim Legal Licensing & Copyright Ownership**
- **Commercial Usability & Legal Enforceability**
- **Redistribution Terms & Derivative Works Compatibility**
- **Mandatory Attribution Clauses & Citation Schemas**
- **Operational Download Feasibility (Zero-credential compliance, no click-through acceptance on user's behalf)**
- **Annotation Availability & Representation of Structural Walls vs CSI Drywall**

### Core Findings Matrix

| Dataset | Primary Source / DOI | License | Commercial Use | Autonomous Download Feasibility | Wall Annotation Format | CSI Drywall Distinction | Final Eligibility Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Modified Swiss Dwellings (MSD)** | Zenodo `10.5281/zenodo.7788422` / HF `philippds/modified-swiss-dwellings-enriched` | **CC BY 4.0** | **YES (Unencumbered)** | Direct Open HTTP / HF API (173.8 MB) | Clean WKT Polygons & `struct_in` channels | None (Generic Walls) | **TOP RECOMMENDED (PRIMARY INGESTION)** |
| **CubiCasa5K** | Zenodo `10.5281/zenodo.2613548` / GitHub `CubiCasa/CubiCasa5k` | **CC BY-NC 4.0** / CC BY-NC-SA 4.0 | **NO (Academic Only)** | Direct Open Zenodo CDN (5.09 GB zip) | Vector SVG (`<polygon class="Wall">`) | None (Generic Walls) | **ELIGIBLE (ACADEMIC BENCHMARK)** |
| **FloorPlanCAD** | `floorplancad.github.io` / HF `Voxel51/FloorPlanCAD` | Annotations: **CC BY-NC 4.0**; CAD drawings: 3rd-Party | **NO (Third-party copyright risk)** | HF API (454 MB) / Google Drive (3.5 GB) | Vector SVG primitives (Class 0 Wall) | None (Generic CAD) | **CONDITIONALLY ELIGIBLE (SECONDARY)** |
| **CVC-FP** | Figshare `10.6084/m9.figshare.12082131` / Zenodo `10.5281/zenodo.7921780` | **CC BY 4.0** (Figshare) / Academic (CVC) | **YES (via Figshare distribution)** | Direct Open Figshare HTTP (353.6 MB) | Vector SVG & binary PNG masks | None (Generic Walls) | **ELIGIBLE (FAST CPU SMOKE TESTING)** |
| **R2V** | ICCV 2017 / `art-programmer/FloorplanTransformation` | Code: MIT; Raster Images: **Proprietary LIFULL HOME'S** | **STRICTLY PROHIBITED** | **BLOCKED (Gated NII IDR Institutional Agreement)** | Vector text coordinates only; **Zero images** | None | **DISQUALIFIED (GATED / INCOMPLETE)** |
| **SESYD** | IJDAR 2010 / `delalandre.free.fr/projects/sesyd/` | Open Academic Research | Academic Only | Direct Open HTTP (~6 MB per subset) | **NONE (Zero wall annotations)** | None | **DISQUALIFIED (FATAL ANNOTATION DEFECT)** |
| **ArchCAD-400k** | arXiv `2503.22346v3` / HF `jackluoluo/ArchCAD` | **CC BY-NC 4.0** | **PROHIBITED** | **BLOCKED (Gated manual application, 3-day review)** | Vector SVG layers (`A-WALL-*`, `S-WALL-*`) | Detailed CAD, no US CSI drywall | **DISQUALIFIED (MANUAL CREDENTIAL GATE)** |

---

## 2. In-Depth Legal & Technical Dataset Profiles

### 2.1 Modified Swiss Dwellings (MSD)
- **Official References**:
  - Matthias Standfest, Michael Franzen, Yvonne Schröder, Luis Gonzalez Medina, Yarilo Villanueva Hernandez, Jan Hendrik Buck, Yen-Ling Tan, Milena Niedzwiecka, Rachele Colmegna (Archilyse AG & ETH Zurich).
  - Workshop: Computer Vision for Architecture, Art and Design (CVAAD), ECCV 2024.
  - 4TU.ResearchData: `doi:10.4121/e1d89cb5-6872-48fc-be63-aadd687ee6f9`.
  - Zenodo: `doi:10.5281/zenodo.7788422` (v3.0.0, released 2022-09-20).
  - Curated Hugging Face Mirror: `philippds/modified-swiss-dwellings-enriched`.
- **Verbatim Licensing & Legal Rights**:
  - Distributed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.
  - **Commercial Rights**: Explicitly granted. Permitted to share, copy, redistribute, adapt, remix, transform, and build upon the material for any purpose, including commercially.
  - **Redistribution Terms**: Allowed without restriction, provided that appropriate credit is given, a link to the license is provided, and any modifications are indicated.
  - **Attribution Text**:
    > Standfest, M., Franzen, M., Schröder, Y., Gonzalez Medina, L., Villanueva Hernandez, Y., Buck, J. H., Tan, Y.-L., Niedzwiecka, M., & Colmegna, R. (2022). Swiss Dwellings: A large dataset of apartment models. Zenodo. https://doi.org/10.5281/zenodo.7788422
- **Download Accessibility & Feasibility**:
  - 100% open HTTP/API access. Requires zero authentication, no API token, and no click-through form.
  - Hugging Face parquet endpoint provides pre-tiled, enriched data totaling **173.8 MB** download size (uncompressed ~1.5 GB).
  - Zenodo v3.0.0 provides a single archive `swiss-dwellings-v3.0.0.zip` (931,868,205 bytes, MD5 `3b7915ecd5bf8e492a3e78c598b74123`).
  - Completely compliant with system disk safety rules (<10 GB limit; local system has 16.3 GB free disk space on C:\).
- **Annotation Schema & Wall Representation**:
  - Tabular relational geometry records (`geometries.csv` / Hugging Face `geometries` split) with 1,086,846 entries.
  - Coordinates stored in Well-Known Text (WKT) standard: `POLYGON ((...))` and `MULTIPOLYGON (((...)))`.
  - Wall isolation filter:
    $$\text{entity\_type} == \text{'separator'} \quad \land \quad \text{entity\_subtype} == \text{'WALL'}$$
  - Also separates structural columns, exterior perimeter walls, and interior room dividers.
  - Dual modality: Vector WKT + 2D raster channels (`struct_in` image feature representing structural and partition boundaries).
  - Hierarchical grouping keys: `site_id`, `building_id`, `plan_id`, and `unit_id`.
- **Eligibility Verdict**: **TOP RECOMMENDED / ELIGIBLE**. Unencumbered commercial license, high-fidelity vector polygons, zero-credential access, and compact download size.

---

### 2.2 CubiCasa5K
- **Official References**:
  - Ahti Kalervo, Juha Ylioinas, Markus Häikiö, Antti Karhu, Juho Kannala (University of Oulu, Finland & CubiCasa Oy).
  - Conference: International Conference on Pattern Recognition (ICPR 2019).
  - Zenodo Record: `10.5281/zenodo.2613548`.
  - GitHub: `https://github.com/CubiCasa/CubiCasa5k`.
- **Verbatim Licensing & Legal Rights**:
  - GitHub `LICENSE`: **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.
  - Zenodo metadata record: `cc-by-nc-sa-4.0` (Attribution-NonCommercial-ShareAlike 4.0 International).
  - **Commercial Rights**: Strictly prohibited without an explicit commercial license negotiated with CubiCasa Oy.
  - **Redistribution Terms**: Allowed exclusively for non-commercial research, academic benchmarking, and educational purposes. Derivatives must carry equivalent attribution and licensing.
  - **Attribution Text**:
    > Kalervo, A., Ylioinas, J., Häikiö, M., Karhu, A., & Kannala, J. (2019). CubiCasa5K: A Dataset for Floorplan Image Analysis. In International Conference on Pattern Recognition (ICPR). Zenodo. https://doi.org/10.5281/zenodo.2613548
- **Download Accessibility & Feasibility**:
  - Direct HTTP GET from Zenodo CDN: `https://zenodo.org/records/2613548/files/cubicasa5k.zip`.
  - Fully unauthenticated; does not require credentials or token.
  - Archive file: `cubicasa5k.zip`, 5,469,495,706 bytes (~5.09 GB). MD5: `0ce0b203d1e3c125b51087b219bd23b9`.
  - **Operational Disk Warning**: While the compressed archive is 5.09 GB (below the 10 GB prompt threshold), uncompressing the entire 5,000 floor plan dataset requires ~18 GB of free disk space. Given that local drive C: has 16.35 GB free, uncompressing the full dataset locally risks filling the disk. Therefore, in Milestone M2, CubiCasa5K should either be streamed, extracted selectively (e.g. 100–500 sample evaluation slice), or downloaded on a drive with larger capacity (E:\ has 30.45 GB free).
- **Annotation Schema & Wall Representation**:
  - 5,000 residential floor plans in SVG vector format (`model.svg`) paired with high-resolution scans and CAD renders (`F1_original.png`, `F1_scaled.png`).
  - Walls are explicitly marked with SVG polygon tags: `<polygon class="Wall" points="...">`.
  - Captures 80+ fine-grained architectural classes (doors, windows, fixtures, stairs).
- **Eligibility Verdict**: **ELIGIBLE (ACADEMIC BENCHMARK)**. Essential for comparative validation on unseen public drawings. Must be tagged with non-commercial usage restrictions.

---

### 2.3 FloorPlanCAD
- **Official References**:
  - Ruolin Zhi, Hao Shen et al. (Alibaba A.I. Labs & Simon Fraser University).
  - Conference: IEEE/CVF International Conference on Computer Vision (ICCV 2021).
  - Project Homepage: `https://floorplancad.github.io/`.
  - Hugging Face Mirror: `Voxel51/FloorPlanCAD`.
  - GitHub: `https://github.com/zl-aslan/FloorPlanCAD`.
- **Verbatim Licensing & Legal Rights**:
  - Annotations: **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.
  - CAD Drawings: Third-party industry copyright.
  - Verbatim Website Disclaimer:
    > *"The annotations in this dataset along with this website belong to us and are licensed under a Creative Commons Attribution-NonCommercial 4.0 License. We do not own the copyright of the drawings. By downloading the dataset you agree to the following terms: The authors give no warranties regarding the dataset. The users of the dataset accept full responsibility for the use of the dataset, including but not limited to the use of any copies of copyrighted dataset that they may create from the dataset."*
  - **Commercial Rights**: Prohibited for annotations; high legal exposure for underlying CAD drawings due to third-party copyright retention.
  - **Redistribution Terms**: High legal risk for full drawing redistribution.
  - **Attribution Text**:
    > Zhi, R., Shen, H., Zheng, L., Wei, Y., & Zhang, H. (2021). FloorPlanCAD: A Large-Scale CAD Drawing Dataset for Panoptic Symbol Spotting. In ICCV.
- **Download Accessibility & Feasibility**:
  - Official Google Drive links are large (~3.5 GB) and experience periodic quota locks.
  - Hugging Face mirror (`Voxel51/FloorPlanCAD`) provides direct API access to the test split (454 MB).
- **Annotation Schema & Wall Representation**:
  - 15,000+ vector CAD drawings cropped into standardized $20\text{m} \times 20\text{m}$ sub-drawings.
  - Vector SVG primitives (lines, polylines, arcs, circles).
  - Walls are designated as Panoptic Stuff Class 0 (`Wall`), with doors/windows as Thing classes.
  - **Structural Limitation**: The artificial $20\text{m} \times 20\text{m}$ cropping introduces tile boundary seams, cutting continuous partition runs and distorting room topology.
- **Eligibility Verdict**: **CONDITIONALLY ELIGIBLE (SECONDARY BENCHMARK)**. Usable for CAD line-style evaluation, but less favorable than MSD due to third-party copyright disclaimers and tile boundary artifacts.

---

### 2.4 CVC-FP
- **Official References**:
  - Lluis-Pere de las Heras, Ernest Valveny, Oriol Ramos Terrades (Computer Vision Center, Universitat Autònoma de Barcelona).
  - Journal/Project: CVC Technical Report 2015.
  - Official Site: `dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/`.
  - Figshare Distribution: `doi:10.6084/m9.figshare.12082131.v1`.
  - Zenodo Derivative (FP-TXT): `doi:10.5281/zenodo.7921780`.
- **Verbatim Licensing & Legal Rights**:
  - Original CVC Repository: Non-commercial academic research agreement.
  - Figshare Distribution (Zheng et al.): Explicitly licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
  - **Commercial Rights**: Permitted under Figshare distribution (CC BY 4.0).
  - **Redistribution Terms**: Permitted with attribution to CVC and authors.
  - **Attribution Text**:
    > de las Heras, L.P., Valveny, E., & Ramos Terrades, O. (2015). CVC-FP database for structural floor plan analysis. Computer Vision Center, Universitat Autònoma de Barcelona. Figshare DOI: 10.6084/m9.figshare.12082131.
- **Download Accessibility & Feasibility**:
  - Original CVC host (`dag.cvc.uab.es`) experiences frequent network timeouts.
  - Figshare CDN is fully online and accessible via direct HTTP GET (`1-WID512_ROTATE.tar.gz`, 370,815,867 bytes ~353.6 MB).
  - Completely unauthenticated.
- **Annotation Schema & Wall Representation**:
  - 122 scanned floor plans in 4 graphic styles: Black, Textured1, Textured2, Parallel.
  - SVG vector structural annotations and binary PNG masks for walls, doors, windows, and rooms.
  - Wall ground truth is pixel-accurate and topological (wall junctions and room boundaries).
  - **Limitation**: Very small volume (122 images). Insufficient alone for deep generalized network training.
- **Eligibility Verdict**: **ELIGIBLE (FAST CPU SMOKE TESTING)**. Ideal for local CPU test runners, sanity checks, and pipeline verification where fast download and light footprint are required.

---

### 2.5 R2V (Raster-to-Vector)
- **Official References**:
  - Chen Liu, Jiajun Wu, Pushmeet Kohli, Yasutaka Furukawa (Simon Fraser University & Microsoft Research).
  - Conference: IEEE International Conference on Computer Vision (ICCV 2017).
  - Paper: `http://art-programmer.github.io/floorplan-transformation/paper.pdf`.
  - GitHub: `https://github.com/art-programmer/FloorplanTransformation`.
- **Verbatim Licensing & Legal Rights**:
  - GitHub parser code: MIT License.
  - Floor Plan Raster Images: **Proprietary property of LIFULL HOME'S Co., Ltd. (Japan)**.
  - Verbatim Author Disclosure in GitHub README:
    > *"We don't have the permission to share the rasterized images, which are from the LIFULL dataset. Here we only share our vector-graphics annotations which might be helpful for other tasks... Note that, since we cannot share the image data, you might need to change the code..."*
  - To access raster images, researchers must submit a formal institutional application to the National Institute of Informatics (NII) Informatics Research Data Repository (IDR) in Japan and execute a legal contract with LIFULL Co., Ltd.
- **Download Accessibility & Feasibility**:
  - **BLOCKED / GATED**. Autonomous download of raster images is legally and technically impossible.
  - Vector text coordinates exist in Google Drive, but without the underlying raster drawings, image segmentation models cannot be trained or evaluated.
- **System Integrity Violation**:
  - Requirement R1 and System Instructions explicitly forbid:
    - Bypassing access controls or signing agreements on the user's behalf.
    - Fabricating fake images or hardcoding dummy data.
- **Eligibility Verdict**: **DISQUALIFIED (GATED / INCOMPLETE)**. Must not be used for autonomous ingestion.

---

### 2.6 SESYD Floorplans
- **Official References**:
  - Mathieu Delalandre, Ernest Valveny, Philippe Trupin et al.
  - Journal: International Journal on Document Analysis and Recognition (IJDAR 2010).
  - Official Repository: `http://mathieu.delalandre.free.fr/projects/sesyd/`.
  - Mirror: `https://hyper.ai/en/datasets/34280`.
- **Verbatim Licensing & Legal Rights**:
  - Freely available open-access academic benchmark for document analysis systems.
  - Commercial use is restricted/unstated.
- **Download Accessibility & Feasibility**:
  - Fully open HTTP download of zip archives (~6 MB per subset). Unauthenticated.
- **Annotation Schema & Fatal Defect**:
  - SESYD was synthetically generated using the 3gT system specifically to benchmark **symbol spotting and character recognition** under graphical noise (salt-and-pepper, vector distortions).
  - Ground truth XML files annotate only 16 isolated furniture and sanitary symbols: `armchair`, `bed`, `table`, `chair`, `sink1`, `sink2`, `tub`, `window1`, `window2`, `door1`, `door2`, etc.
  - **FATAL GROUND TRUTH DEFECT**: **ZERO wall or partition annotations exist**.
  - The floor plan walls are merely static raster/vector background noise upon which symbols were stamped. No bounding boxes, segmentation masks, or centerline coordinates exist for the walls.
- **Eligibility Verdict**: **DISQUALIFIED (FATAL ANNOTATION DEFECT)**. Completely unsuitable for wall segmentation training, validation, or evaluation.

---

### 2.7 ArchCAD-400k
- **Official References**:
  - Jack Luo et al. (Tsinghua University & collaborative partners).
  - Preprint: arXiv:2503.22346v3 ("ArchCAD-400K: A Large-Scale CAD Drawings Dataset and New Baseline for Panoptic Symbol Spotting", March 2025).
  - Official Repository: Hugging Face `jackluoluo/ArchCAD`.
- **Verbatim Licensing & Legal Rights**:
  - Distributed under a customized **CC BY-NC 4.0** license governed by institutional CAD data security agreements.
  - Commercial use is strictly prohibited.
- **Download Accessibility & Feasibility**:
  - **STRICTLY GATED**. Hugging Face API live response:
    ```json
    {
      "id": "jackluoluo/ArchCAD",
      "gated": "manual",
      "private": false,
      "extra_gated_fields": {
        "full_name": {"type": "text"},
        "affiliation": {"type": "text"},
        "email": {"type": "text", "label": "Institutional Email (preferred)"},
        "country": {"type": "country"},
        "intended_use": {"type": "select"},
        "non_commercial_use": {"type": "checkbox"},
        "data_protection_ack": {"type": "checkbox"}
      },
      "extra_gated_prompt": "To request access to the ArchCAD dataset, please complete the following form... approval may take up to 3 business days."
    }
    ```
  - Requires manual user form completion, institutional email verification, and a 3 business day manual approval turnaround.
- **System Integrity Violation**:
  - Requirement R1 mandates: *"without bypassing access restrictions or accepting licenses on the user's behalf"*.
  - An autonomous agent cannot legally or operationally complete personal identification forms or sign non-commercial affidavits.
- **Eligibility Verdict**: **DISQUALIFIED FOR AUTONOMOUS INGESTION (GATED)**. Documented as a premier recommendation for future human-in-the-loop ingestion if the user supplies pre-approved Hugging Face credentials.

---

## 3. Compliance with System Integrity Rules

1. **Zero License Acceptance on User's Behalf**:
   - The licensing audit module strictly segregates datasets by access barrier.
   - Any dataset requiring click-through agreements, personal data submission, or institutional contracts (R2V, ArchCAD-400k) is programmatically marked `ELIGIBILITY_DISQUALIFIED_GATED`.
   - The system will never forge credentials, scrape gated pages, or accept terms.

2. **Disk Safety Guardrails**:
   - The local compute environment has **16.35 GB free** on drive C:.
   - In accordance with the project rule *"Disk safety guards: free disk space check prior to download, mandatory notification for downloads > 10 GB"*:
     * MSD is safely under threshold: 173.8 MB (HF) / 888.7 MB (Zenodo).
     * CVC-FP is safely under threshold: 353.6 MB.
     * CubiCasa5K archive is 5.09 GB; extracting all 5,000 floor plans requires ~18 GB, which exceeds free drive C: space. The worker must be instructed to either extract a compact subset or verify free space dynamically.

3. **Weak Pseudo-Labeling Guardrail for 99th Street PDF**:
   - The 99th Street MTA drawing set is a commercial 95% CDs progress set.
   - Any wall annotations derived from this PDF must be tagged explicitly as `weak_pseudo_label`.
   - Weak pseudo-labels must be strictly quarantined from the validation and test splits to prevent data leakage and benchmark contamination.

---

## 4. Architectural Design: `licensing_audit.py`

### 4.1 Module Location & Layout Strategy
To satisfy both `PROJECT.md` section 5 (`drywall_detection/audit/dataset_auditor.py`) and the Milestone prompt (`drywall_detection/datasets/licensing_audit.py`), the codebase must establish:
1. `drywall_detection/datasets/licensing_audit.py`: The canonical implementation defining the data models, dataset catalog, audit logic, Markdown generator, JSON exporter, and CLI.
2. `drywall_detection/audit/dataset_auditor.py`: A wrapper/facade module that exposes identical interfaces:
   ```python
   from drywall_detection.datasets.licensing_audit import (
       DatasetLicenseInfo,
       DatasetLicensingAuditor,
       AuditStatus,
       main
   )
   ```
3. `drywall_detection/datasets/__init__.py`: Exports `DatasetLicenseInfo` and `DatasetLicensingAuditor`.

### 4.2 Data Models & Enums

```python
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

class AuditStatus(str, Enum):
    ELIGIBLE_PRIMARY = "ELIGIBLE_PRIMARY"
    ELIGIBLE_BENCHMARK = "ELIGIBLE_BENCHMARK"
    ELIGIBLE_SMOKE_TEST = "ELIGIBLE_SMOKE_TEST"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    DISQUALIFIED_GATED = "DISQUALIFIED_GATED"
    DISQUALIFIED_NO_ANNOTATIONS = "DISQUALIFIED_NO_ANNOTATIONS"

class CommercialStatus(str, Enum):
    PERMITTED = "PERMITTED"
    NON_COMMERCIAL_ONLY = "NON_COMMERCIAL_ONLY"
    DISCLAIMED_THIRD_PARTY = "DISCLAIMED_THIRD_PARTY"
    RESTRICTED = "RESTRICTED"

class AccessModel(str, Enum):
    DIRECT_OPEN = "DIRECT_OPEN"
    GATED_INSTITUTIONAL = "GATED_INSTITUTIONAL"
    GATED_MANUAL_REVIEW = "GATED_MANUAL_REVIEW"
    MIRRORED_ONLY = "MIRRORED_ONLY"

@dataclass
class DatasetLicenseInfo:
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
```

### 4.3 Class `DatasetLicensingAuditor` Interface Contract

```python
class DatasetLicensingAuditor:
    """Audits, validates, and exports licensing terms for candidate architectural datasets."""
    
    def __init__(self):
        self._registry: Dict[str, DatasetLicenseInfo] = {}
        self._populate_registry()
        
    def _populate_registry(self) -> None:
        """Populates the 7 candidate datasets with verified legal and technical metadata."""
        ...
        
    def get_dataset(self, dataset_id: str) -> DatasetLicenseInfo:
        """Retrieves a specific dataset by ID or alias. Raises KeyError if not found."""
        ...
        
    def list_all(self) -> List[DatasetLicenseInfo]:
        """Returns all registered candidate datasets."""
        ...
        
    def get_eligible(self, commercial_only: bool = False) -> List[DatasetLicenseInfo]:
        """Filters datasets that are eligible for autonomous download and wall segmentation."""
        ...
        
    def get_disqualified(self) -> List[DatasetLicenseInfo]:
        """Filters datasets that are disqualified due to gating or lack of wall labels."""
        ...
        
    def generate_markdown_report(self) -> str:
        """Renders the complete formal Markdown audit report according to project requirements."""
        ...
        
    def export_markdown(self, output_path: Path) -> Path:
        """Writes the Markdown report to disk, creating parent directories if needed."""
        ...
        
    def export_json(self, output_path: Path) -> Path:
        """Exports the structured dataset catalog to a standardized JSON schema."""
        ...
        
    def verify_connectivity(self, timeout_seconds: int = 5) -> Dict[str, Dict[str, Any]]:
        """Safely verifies HTTP status for dataset endpoints with graceful timeout handling.
        Does not raise exceptions if offline; returns connectivity status dictionary."""
        ...
```

### 4.4 JSON Export Schema (`drywall_detection/data/dataset_licensing_audit.json`)
The exported JSON structure must follow this strict schema:
```json
{
  "audit_version": "1.0.0",
  "audit_timestamp": "2026-11-07T20:46:00Z",
  "auditor_role": "m1_explorer_1",
  "zero_tolerance_rules": {
    "zero_license_acceptance_on_user_behalf": true,
    "max_unannounced_download_mb": 10240,
    "no_dummy_implementations": true
  },
  "summary": {
    "total_audited": 7,
    "eligible_count": 4,
    "disqualified_count": 3,
    "commercial_eligible_count": 2,
    "primary_recommended": "modified_swiss_dwellings"
  },
  "datasets": [
    {
      "dataset_id": "modified_swiss_dwellings",
      "name": "Modified Swiss Dwellings (MSD)",
      "official_sources": [
        "https://doi.org/10.5281/zenodo.7788422",
        "https://data.4tu.nl/datasets/e1d89cb5-6872-48fc-be63-aadd687ee6f9",
        "https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched"
      ],
      "doi": "10.5281/zenodo.7788422",
      "license_id": "CC-BY-4.0",
      "license_name": "Creative Commons Attribution 4.0 International",
      "commercial_status": "PERMITTED",
      "commercial_allowed": true,
      "redistribution_allowed": true,
      "attribution_required": true,
      "attribution_text": "Standfest et al. (2022). Swiss Dwellings: A large dataset of apartment models. Zenodo. https://doi.org/10.5281/zenodo.7788422",
      "access_model": "DIRECT_OPEN",
      "download_feasibility": "Fully Feasible Autonomously",
      "archive_size_mb": 173.8,
      "uncompressed_size_estimate_mb": 1500.0,
      "wall_annotations_available": true,
      "wall_annotation_format": "WKT Polygons and struct_in raster masks",
      "drywall_labels_available": false,
      "drywall_notes": "Generic structural wall boundaries only. No US CSI drywall specifications.",
      "eligibility_status": "ELIGIBLE_PRIMARY",
      "eligibility_rationale": "Permissive CC BY 4.0 commercial license, clean vector WKT polygons, compact download size (173.8 MB), open API access.",
      "verification_date": "2026-11-07",
      "verification_method": "Zenodo API, Hugging Face API, and 4TU verification"
    }
  ]
}
```

---

## 5. Specification of Deliverable Report (`DATASET_LICENSING_REPORT.md`)

The file `drywall_detection/datasets/DATASET_LICENSING_REPORT.md` must be automatically generated by the module and committed to disk. It must adhere to the following section structure:

1. **Title & Document Metadata**:
   - Title: `# Candidate Architectural Dataset Licensing & Feasibility Audit Report`
   - Metadata: Generation Date, Auditor Subagent, Integrity Mode, Zero-Tolerance Statement.
2. **Executive Summary & Eligibility Scorecard**:
   - Total datasets audited: 7.
   - Status summary table with columns: `Dataset`, `License`, `Commercial Use`, `Download Size`, `Wall Annotations`, `Verdict`.
3. **Zero-Tolerance Compliance & Legal Safeguards**:
   - Detailed justification for disqualification of R2V (NII IDR institutional gate) and ArchCAD-400k (Hugging Face manual credential gate).
   - Disk space verification statement (<10 GB rule, C: drive status).
4. **Individual Dataset Dossiers (Sections 4.1 to 4.7)**:
   - For each dataset: Official Sources, DOIs, Exact License Text, Commercial Rights, Redistribution Clauses, Attribution Requirement, Wall Schema, Drywall Limitations, and Eligibility Justification.
5. **Downstream Recommendations for Milestone M2 (Dataset Preparation)**:
   - Ingestion hierarchy:
     1. **MSD**: Primary pretraining dataset.
     2. **CVC-FP**: Small-footprint baseline for smoke tests and CI/CD.
     3. **CubiCasa5K**: Primary academic benchmark for held-out validation.
     4. **99th Street MTA Progress Set**: Quarantined strictly for Stage 2 fine-tuning / drywall classification (weak pseudo-labeling guardrail).

---

## 6. Worker Implementation Plan & Instructions

When the M1 Worker receives this task, they should execute the following steps in sequence:

### Step 1: Create Module Directories
Ensure the following directories exist under workspace root:
- `drywall_detection/datasets/`
- `drywall_detection/audit/`
- `drywall_detection/data/`
- `drywall_detection/tests/`
- `drywall_detection/reports/`

### Step 2: Implement `drywall_detection/datasets/licensing_audit.py`
- Define `AuditStatus`, `CommercialStatus`, `AccessModel` enums.
- Define `DatasetLicenseInfo` dataclass with type hints and helper serialization methods.
- Implement `DatasetLicensingAuditor` class containing verified data for all 7 datasets.
- Implement helper methods: `get_dataset`, `list_all`, `get_eligible`, `get_disqualified`, `generate_markdown_report`, `export_markdown`, `export_json`, and `verify_connectivity`.
- Implement CLI block (`if __name__ == "__main__":`) that parses arguments (`--json`, `--markdown`, `--verify-urls`, `--stdout`) and exports reports.

### Step 3: Implement Aliasing Wrapper `drywall_detection/audit/dataset_auditor.py`
- Re-export `DatasetLicensingAuditor`, `DatasetLicenseInfo`, `AuditStatus` from `drywall_detection.datasets.licensing_audit`.
- Provide identical CLI compatibility so both invocations work identically.

### Step 4: Run Module to Generate Deliverables
Execute:
```powershell
python -m drywall_detection.datasets.licensing_audit --json drywall_detection/data/dataset_licensing_audit.json --markdown drywall_detection/datasets/DATASET_LICENSING_REPORT.md
```
Also copy or generate into `drywall_detection/reports/` if referenced by PROJECT.md.

### Step 5: Implement Unit Tests in `drywall_detection/tests/test_licensing_audit.py`
The unit tests must thoroughly verify:
1. `test_registry_completeness`: Exactly 7 candidate datasets are registered.
2. `test_msd_licensing`: MSD is CC-BY-4.0, commercial_allowed is True, status is ELIGIBLE_PRIMARY.
3. `test_cubicasa_licensing`: CubiCasa5K is CC-BY-NC-4.0 / CC-BY-NC-SA-4.0, commercial_allowed is False, status is ELIGIBLE_BENCHMARK.
4. `test_disqualified_gated_datasets`: R2V and ArchCAD-400k are disqualified with status DISQUALIFIED_GATED.
5. `test_disqualified_sesyd_no_annotations`: SESYD is disqualified with status DISQUALIFIED_NO_ANNOTATIONS and `wall_annotations_available == False`.
6. `test_json_export`: `export_json` produces valid JSON matching schema with expected keys.
7. `test_markdown_export`: `export_markdown` produces Markdown containing all 7 dataset names and summary table.
8. `test_connectivity_safe_offline`: `verify_connectivity` does not throw an unhandled exception when given mock or offline URLs.
9. `test_audit_facade_alias`: `drywall_detection.audit.dataset_auditor` exports identical classes and methods.

### Step 6: Execute Test Suite
Run:
```powershell
pytest drywall_detection/tests/test_licensing_audit.py -v
```
Ensure 100% test pass rate with zero failures.

---

## 7. Edge Cases & Safeguards

1. **Air-Gapped / Offline Execution**:
   - The licensing audit module must not depend on live internet connectivity to function.
   - All licensing terms, DOIs, URLs, and metadata must be baked into the catalog registry.
   - The `verify_connectivity()` method must catch all socket/URLError exceptions, log them gracefully, and report `status: "offline / unreachable"` without crashing.

2. **File Path Handling**:
   - Use `pathlib.Path` throughout to ensure compatibility across Windows and Linux (Google Colab / CI).
   - Ensure parent directories are created via `path.parent.mkdir(parents=True, exist_ok=True)`.

3. **Casing & Typo Resilience**:
   - Dataset lookups (`get_dataset`) must normalize strings using `.strip().lower().replace("-", "_")` to allow queries like `"CubiCasa5k"`, `"cubicasa"`, `"MSD"`, or `"modified-swiss-dwellings"`.
