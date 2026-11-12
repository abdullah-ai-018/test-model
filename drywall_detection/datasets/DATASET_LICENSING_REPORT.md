# Candidate Architectural Dataset Licensing & Feasibility Audit Report

- **Author / Subagent**: `m1_worker_1` (incorporating `m1_explorer_1` findings)
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Date**: 2026-11-08
- **Status**: AUDIT COMPLETE — ZERO-TOLERANCE INTEGRITY VERIFIED
- **Project**: Isolated Drywall Detection Module (`drywall_detection/`)

---

## 1. Executive Summary & Audit Scorecard

A comprehensive audit was conducted across all **7 candidate datasets** specified in `ORIGINAL_REQUEST.md` and `PROJECT.md`.
Of the candidate datasets, **4 are eligible for autonomous training and evaluation**, **2 are fully unencumbered for commercial use**, and **3 are strictly disqualified** due to access control barriers or absence of wall annotations.

| Dataset | Official Source / DOI | License | Commercial Use | Download Size | Wall Annotations | CSI Drywall Distinction | Final Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Modified Swiss Dwellings (MSD)** | [10.5281/zenodo.7788422](https://doi.org/10.5281/zenodo.7788422) | CC-BY-4.0 | **YES** | 173.8 MB | Yes | None (Generic Walls) | **ELIGIBLE_PRIMARY** |
| **CubiCasa5K** | [10.5281/zenodo.2613548](https://doi.org/10.5281/zenodo.2613548) | CC-BY-NC-4.0 | NO | 5090.0 MB | Yes | None (Generic Walls) | **ELIGIBLE_BENCHMARK** |
| **FloorPlanCAD** | [Link](https://floorplancad.github.io/) | CC-BY-NC-4.0 (Annotations) / 3rd-Party CAD Drawings | *Disclaimed* | 454.0 MB | Yes | None (Generic Walls) | **CONDITIONALLY_ELIGIBLE** |
| **CVC-FP** | [10.6084/m9.figshare.12082131.v1](https://doi.org/10.6084/m9.figshare.12082131.v1) | CC-BY-4.0 | **YES** | 353.6 MB | Yes | None (Generic Walls) | **ELIGIBLE_SMOKE_TEST** |
| **R2V (Raster-to-Vector)** | [Link](https://github.com/art-programmer/FloorplanTransformation) | MIT (Code) / Proprietary LIFULL HOME'S (Images) | NO | Gated / N/A | **NO** | None (Generic Walls) | **DISQUALIFIED_GATED** |
| **SESYD Floorplans** | [Link](http://mathieu.delalandre.free.fr/projects/sesyd/) | Open Academic Research | NO | 6.0 MB | **NO** | None (Generic Walls) | **DISQUALIFIED_NO_ANNOTATIONS** |
| **ArchCAD-400k** | [Link](https://huggingface.co/datasets/jackluoluo/ArchCAD) | CC-BY-NC-4.0 | NO | Gated / N/A | Yes | None (Generic Walls) | **DISQUALIFIED_GATED** |

---

## 2. Zero-Tolerance Compliance & Legal Safeguards

### 2.1 Zero License Acceptance on User's Behalf
- **R2V (Raster-to-Vector)**: The author README explicitly reveals: *'We don't have the permission to share the rasterized images, which are from the LIFULL dataset...'* Gaining access requires executing a formal institutional contract with LIFULL Co., Ltd. through the National Institute of Informatics (NII) in Japan. Autonomous download is legally barred and technically incomplete.
- **ArchCAD-400k**: Live Hugging Face API queries verify that ArchCAD is gated (`'gated': 'manual'`) requiring submission of personal full name, institutional email, affiliation, and a 3-business-day manual review. An autonomous agent cannot legally or operationally complete credential forms or sign non-commercial affidavits.
- **SESYD Floorplans**: Authoritative XML ground truth audit revealed that SESYD annotates exclusively 16 furniture and sanitary symbols. **Zero wall or partition annotations exist**. Using SESYD for wall segmentation would produce severe garbage-in/garbage-out degradation.

### 2.2 Host Storage & Hardware Safeguards
- The host C: drive has ~16.3 GB free storage. Downloading archives larger than 10 GB is forbidden by project safety rules.
- **Modified Swiss Dwellings (MSD)**: Ingestion via curated Hugging Face parquet files requires only **173.8 MB** (uncompressed ~1.5 GB), safely within disk bounds.
- **CVC-FP**: Ingestion via Figshare archive requires only **353.6 MB**, safely within disk bounds.
- **CubiCasa5K**: The Zenodo archive is 5.09 GB; extracting all 5,000 floor plans requires ~18 GB, which would exceed free space on C:. In Milestone M2, CubiCasa5K will be processed via selective streaming/extraction or targeted on secondary drive E: (30.4 GB free).

---

## 3. Individual Dataset Dossiers

### 3.1 Modified Swiss Dwellings (MSD)
- **Dataset ID**: `modified_swiss_dwellings`
- **DOI**: `10.5281/zenodo.7788422`
- **Official Sources**:
  - <https://doi.org/10.5281/zenodo.7788422>
  - <https://data.4tu.nl/datasets/e1d89cb5-6872-48fc-be63-aadd687ee6f9>
  - <https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched>
- **License**: **Creative Commons Attribution 4.0 International** (`CC-BY-4.0`)
- **Commercial Usability**: `PERMITTED` (Allowed: `True`)
- **Redistribution Rights**: Allowed: `True`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Standfest, M., Franzen, M., Schröder, Y., Gonzalez Medina, L., Villanueva Hernandez, Y., Buck, J. H., Tan, Y.-L., Niedzwiecka, M., & Colmegna, R. (2022). Swiss Dwellings: A large dataset of apartment models. Zenodo. https://doi.org/10.5281/zenodo.7788422
- **Access Model**: `DIRECT_OPEN` (Fully Feasible Autonomously)
- **Archive Size**: `173.8 MB` (Estimated uncompressed: `1500.0 MB`)
- **Wall Annotations**: Available: `True` (WKT Polygons (entity_type='separator', entity_subtype='WALL') and struct_in raster masks)
- **CSI Drywall Distinction**: Available: `False` (Generic structural and partition wall boundaries only. No US CSI drywall specifications.)
- **Eligibility Verdict**: **`ELIGIBLE_PRIMARY`**
- **Eligibility Rationale**: Permissive CC BY 4.0 commercial license, clean vector WKT polygons, compact download size (173.8 MB), and unauthenticated API access.
- **Verification Provenance**: Verified on `2026-11-07` via `Zenodo API, Hugging Face API, and 4TU verification`.

### 3.2 CubiCasa5K
- **Dataset ID**: `cubicasa5k`
- **DOI**: `10.5281/zenodo.2613548`
- **Official Sources**:
  - <https://doi.org/10.5281/zenodo.2613548>
  - <https://github.com/CubiCasa/CubiCasa5k>
- **License**: **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0 / CC BY-NC-SA 4.0)** (`CC-BY-NC-4.0`)
- **Commercial Usability**: `NON_COMMERCIAL_ONLY` (Allowed: `False`)
- **Redistribution Rights**: Allowed: `True`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Kalervo, A., Ylioinas, J., Häikiö, M., Karhu, A., & Kannala, J. (2019). CubiCasa5K: A Dataset for Floorplan Image Analysis. In International Conference on Pattern Recognition (ICPR). Zenodo. https://doi.org/10.5281/zenodo.2613548
- **Access Model**: `DIRECT_OPEN` (Direct Open Zenodo CDN (Selective extraction recommended due to disk size))
- **Archive Size**: `5090.0 MB` (Estimated uncompressed: `18000.0 MB`)
- **Wall Annotations**: Available: `True` (Vector SVG (<polygon class='Wall'>) and CAD raster renderings)
- **CSI Drywall Distinction**: Available: `False` (Generic residential wall outlines. No material or gypsum drywall distinction.)
- **Eligibility Verdict**: **`ELIGIBLE_BENCHMARK`**
- **Eligibility Rationale**: Rich vector SVG wall polygons across 5,000 floor plans; highly eligible for academic evaluation and held-out benchmark validation. Non-commercial license prohibits unencumbered commercial deployment; full archive requires selective extraction to comply with host disk limits.
- **Verification Provenance**: Verified on `2026-11-07` via `Zenodo API and GitHub repository inspection`.

### 3.3 FloorPlanCAD
- **Dataset ID**: `floorplancad`
- **DOI**: `N/A`
- **Official Sources**:
  - <https://floorplancad.github.io/>
  - <https://huggingface.co/datasets/Voxel51/FloorPlanCAD>
  - <https://github.com/zl-aslan/FloorPlanCAD>
- **License**: **Creative Commons Attribution-NonCommercial 4.0 (Annotations only)** (`CC-BY-NC-4.0 (Annotations) / 3rd-Party CAD Drawings`)
- **Commercial Usability**: `DISCLAIMED_THIRD_PARTY` (Allowed: `False`)
- **Redistribution Rights**: Allowed: `False`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Zhi, R., Shen, H., Zheng, L., Wei, Y., & Zhang, H. (2021). FloorPlanCAD: A Large-Scale CAD Drawing Dataset for Panoptic Symbol Spotting. In ICCV.
- **Access Model**: `DIRECT_OPEN` (Hugging Face API test split (454 MB) / Google Drive (3.5 GB))
- **Archive Size**: `454.0 MB` (Estimated uncompressed: `3500.0 MB`)
- **Wall Annotations**: Available: `True` (Vector SVG primitives (Panoptic Stuff Class 0 Wall))
- **CSI Drywall Distinction**: Available: `False` (Generic CAD wall linework in 20m x 20m crops. No drywall material verification.)
- **Eligibility Verdict**: **`CONDITIONALLY_ELIGIBLE`**
- **Eligibility Rationale**: Annotations are CC BY-NC 4.0, but authors expressly disclaim copyright on underlying CAD drawings. Artificial 20m x 20m sub-drawing crops introduce boundary seam artifacts cutting continuous partitions.
- **Verification Provenance**: Verified on `2026-11-07` via `Official website disclaimer audit and Hugging Face API`.

### 3.4 CVC-FP
- **Dataset ID**: `cvc_fp`
- **DOI**: `10.6084/m9.figshare.12082131.v1`
- **Official Sources**:
  - <https://doi.org/10.6084/m9.figshare.12082131.v1>
  - <https://doi.org/10.5281/zenodo.7921780>
  - <https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/>
- **License**: **Creative Commons Attribution 4.0 International (Figshare Distribution)** (`CC-BY-4.0`)
- **Commercial Usability**: `PERMITTED` (Allowed: `True`)
- **Redistribution Rights**: Allowed: `True`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > de las Heras, L.P., Valveny, E., & Ramos Terrades, O. (2015). CVC-FP database for structural floor plan analysis. Figshare DOI: 10.6084/m9.figshare.12082131.
- **Access Model**: `DIRECT_OPEN` (Direct Open Figshare HTTP (353.6 MB))
- **Archive Size**: `353.6 MB` (Estimated uncompressed: `1200.0 MB`)
- **Wall Annotations**: Available: `True` (Vector SVG and binary PNG wall masks)
- **CSI Drywall Distinction**: Available: `False` (Generic structural and partition walls across 4 drafting styles. No drywall material properties.)
- **Eligibility Verdict**: **`ELIGIBLE_SMOKE_TEST`**
- **Eligibility Rationale**: Permissive CC BY 4.0 license via Figshare, compact archive size (353.6 MB), and high-quality SVG/PNG masks. Ideal for CPU smoke testing and fast pipeline validation.
- **Verification Provenance**: Verified on `2026-11-07` via `Figshare API and Zenodo metadata verification`.

### 3.5 R2V (Raster-to-Vector)
- **Dataset ID**: `r2v`
- **DOI**: `N/A`
- **Official Sources**:
  - <https://github.com/art-programmer/FloorplanTransformation>
  - <http://art-programmer.github.io/floorplan-transformation/paper.pdf>
- **License**: **Code MIT; Raster images strictly proprietary to LIFULL Co., Ltd.** (`MIT (Code) / Proprietary LIFULL HOME'S (Images)`)
- **Commercial Usability**: `RESTRICTED` (Allowed: `False`)
- **Redistribution Rights**: Allowed: `False`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Liu, C., Wu, J., Kohli, P., & Furukawa, Y. (2017). Raster-to-Vector: Revisiting Floorplan Transformation. In ICCV.
- **Access Model**: `GATED_INSTITUTIONAL` (Blocked / Gated (Requires NII IDR application & institutional contract))
- **Archive Size**: `0.0 MB` (Estimated uncompressed: `0.0 MB`)
- **Wall Annotations**: Available: `False` (Vector text coordinates only; raster drawing images completely withheld)
- **CSI Drywall Distinction**: Available: `False` (No drywall material classification. Missing underlying raster images.)
- **Eligibility Verdict**: **`DISQUALIFIED_GATED`**
- **Eligibility Rationale**: Raster images are proprietary to LIFULL Co., Ltd. Access requires formal institutional legal contract via NII IDR. Autonomous download violates zero-license-acceptance rules; unusable without paired drawings.
- **Verification Provenance**: Verified on `2026-11-07` via `GitHub README author disclosure inspection`.

### 3.6 SESYD Floorplans
- **Dataset ID**: `sesyd`
- **DOI**: `N/A`
- **Official Sources**:
  - <http://mathieu.delalandre.free.fr/projects/sesyd/>
  - <https://hyper.ai/en/datasets/34280>
- **License**: **Open Academic Research Benchmark** (`Open Academic Research`)
- **Commercial Usability**: `RESTRICTED` (Allowed: `False`)
- **Redistribution Rights**: Allowed: `True`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Delalandre, M., Valveny, E., Trupin, P., et al. (2010). Generation of synthetic documents for performance evaluation of symbol recognition & spotting systems. IJDAR.
- **Access Model**: `DIRECT_OPEN` (Direct Open HTTP (~6 MB per subset))
- **Archive Size**: `6.0 MB` (Estimated uncompressed: `30.0 MB`)
- **Wall Annotations**: Available: `False` (None (zero wall annotations; 16 symbol bounding boxes only))
- **CSI Drywall Distinction**: Available: `False` (Walls are unannotated background raster noise.)
- **Eligibility Verdict**: **`DISQUALIFIED_NO_ANNOTATIONS`**
- **Eligibility Rationale**: Fatal annotation defect: contains ground truth exclusively for 16 furniture/sanitary symbols. Zero wall annotations exist in dataset.
- **Verification Provenance**: Verified on `2026-11-07` via `Authoritative ground truth XML schema audit`.

### 3.7 ArchCAD-400k
- **Dataset ID**: `archcad_400k`
- **DOI**: `N/A`
- **Official Sources**:
  - <https://huggingface.co/datasets/jackluoluo/ArchCAD>
  - <https://arxiv.org/abs/2503.22346>
- **License**: **Creative Commons Attribution-NonCommercial 4.0 (Gated Access)** (`CC-BY-NC-4.0`)
- **Commercial Usability**: `RESTRICTED` (Allowed: `False`)
- **Redistribution Rights**: Allowed: `False`
- **Attribution Requirement**: Mandatory: `True`
- **Official Citation**: > Luo, J., et al. (2025). ArchCAD-400K: A Large-Scale CAD Drawings Dataset and New Baseline for Panoptic Symbol Spotting. arXiv:2503.22346.
- **Access Model**: `GATED_MANUAL_REVIEW` (Blocked / Gated (Requires manual web application form and 3 business days approval))
- **Archive Size**: `0.0 MB` (Estimated uncompressed: `0.0 MB`)
- **Wall Annotations**: Available: `True` (Vector SVG CAD layers (A-WALL, S-WALL))
- **CSI Drywall Distinction**: Available: `False` (Standard CAD layer names without verified US CSI drywall specifications.)
- **Eligibility Verdict**: **`DISQUALIFIED_GATED`**
- **Eligibility Rationale**: Strictly gated behind manual Hugging Face application form requiring user's full name, institutional email, affiliation, and up to 3 business days review. Autonomous download violates zero-credential-acceptance rules.
- **Verification Provenance**: Verified on `2026-11-07` via `Hugging Face API gated parameter verification`.

---

## 4. Downstream Recommendations for Milestone M2 (Dataset Preparation)

1. **Primary Pretraining Dataset**: **Modified Swiss Dwellings (MSD)**
   - Format: WKT vector coordinates converted to single-channel 8-bit indexed PNG masks.
   - Target Class: Class 3 (Uncertain / Generic Wall) — strictly preventing unverified drywall assumptions.
   - Volume: 173.8 MB download size.

2. **Fast Local CPU Smoke Testing**: **CVC-FP**
   - Format: SVG / binary PNG masks.
   - Volume: 122 scanned drawings (353.6 MB).

3. **Academic Evaluation Benchmark**: **CubiCasa5K**
   - Format: SVG `<polygon class='Wall'>` tags.
   - Deployment: Selective extraction of held-out evaluation slice (200–500 drawings).

4. **Fine-Tuning & Verified Ground Truth**: **MTA 99th Street Commercial Drawing Set**
   - Expert markups from `drywall_walls_marked_red_by_Usman.pdf` coupled with partition schedule sheets A-900 / A-901.
   - Strictly quarantined from validation/test splits in accordance with weak pseudo-labeling guardrails.
