# Project: Isolated Drywall Detection Module (`drywall_detection/`)

## 1. Architecture Overview
The `drywall_detection/` module is an isolated component of the QTO Engine project designed to detect architectural walls, parse partition schedules, and classify drywall using a vector-first pipeline combined with machine learning segmentation on architectural drawings.

### Core Architectural Tracks:
1. **Vector-First Extraction & Schedule Parsing Track**:
   - Direct extraction of vector paths, lines, rectangles, fills, hatches, and text layers using PyMuPDF, pdfplumber, Shapely, and OpenCV.
   - Vector presence verification with fallback detection routing.
   - Exact reversible affine transformations ($M$ and $M^{-1}$) handling 90° clockwise page rotation.
   - Partition tag discovery on floor plans (Sheets A-100 to A-105) matching 11.2 x 11.3 pt vector symbols and leader lines.
   - Parsing of partition schedule sheets (A-900 & A-901) transcribing all 24 assembly details into structured tabular schemas.
   - 3-tier spatial matching associating tags to walls with strict unassigned guardrails (eliminating hallucinations).
   - CSV export (`partition_schedule_mapping.csv`) with mandatory human-in-the-loop review stopping mechanism (`REVIEW_REQUIRED.lock` / exit code 2).

2. **Dataset Audit & Multi-Dataset Preparation Track**:
   - Empirical audit of 6 candidate datasets: CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD Floorplans, and Modified Swiss Dwellings (MSD).
   - Strict project-isolated splitting (70% train, 15% val, 15% independent test) with zero project overlap between splits.
   - Disk safety guards: free disk space check prior to download, mandatory notification for downloads > 10 GB, zero license acceptance on user's behalf.
   - Visual QC pipeline producing original, mask, and overlay triplets.

3. **Machine Learning Wall Segmentation Track**:
   - Implementation and comparative evaluation of two segmentation architectures: U-Net with pretrained encoder (e.g. ResNet34) and SegFormer (B0/B1).
   - Compound Soft Dice + Focal Loss addressing the 90:10 background-to-wall class imbalance.
   - Evaluation metrics: mIoU, Wall IoU, Dice/F1, Precision, Recall, and Boundary IoU.
   - Hardware-aware dynamic configuration: auto-detects CPU/CUDA, scales batch sizes and resolutions, ensures 100% Google Colab compatibility.
   - Best model checkpoint persistence in `drywall_detection/checkpoints/best_model/` with standalone `infer.py`.
   - Weak pseudo-labeling guardrail for 99th Street PDF: explicit tagging as `weak_pseudo_label`, visual spot-checking (5–10 regions), and strict quarantine from validation and test sets.

4. **Evidence-Based Drywall Classification Track**:
   - Strict material precedence:
     - **Drywall (Green)**: Verified Gypsum Wallboard / GWB assemblies (e.g., Details 1B-1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A-7C, 7E-7G, 8A, 10).
     - **Non-Drywall (Red)**: CMU masonry block (Detail 1A: `6" FIRE RATED CMU`), architectural glass systems (GL1, GL2), concrete encasements (11).
     - **Uncertain (Yellow)**: Unassigned walls, ambiguous tags, specialty millwork (09 TV screen).
   - Downstream execution locked until `partition_schedule_mapping.approved.csv` is provided.
   - Vector pipeline accuracy evaluated against expert ground truth (`drywall_walls_marked_red_by_Usman.pdf`, 478 red markups) across 5–10 plan regions.

---

## 2. Feature Inventory
Every feature identified during the Survey phase and user requirements is inventoried below and mapped to a specific milestone.

| # | Feature ID | Feature Description | Milestone | Source |
|---|---|---|:---:|---|
| 1 | F-ENV-AUDIT | Hardware environment profiling (CPU, GPU, RAM, disk, Python, CUDA) | M1 | Survey / R3 |
| 2 | F-WORKSPACE-AUDIT | Workspace cleanliness and isolation audit (`drywall_detection/` boundary) | M1 | Survey / R5 |
| 3 | F-PDF-SURVEY | Master PDF audit (71 pages, 90° rotation, MediaBox 1728x2592 pt, sheets mapped) | M1 | Survey / R1 |
| 4 | F-DATASET-AUDIT | 6 dataset audit (CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, MSD) & license check | M1 | Survey / R2 |
| 5 | F-AUDIT-REPORT | Formal Milestone M1 Audit Report saved in `drywall_detection/reports/` | M1 | R1, R2, R5 |
| 6 | F-DATA-DOWNLOAD | Secure, authenticated-free download of eligible dataset (MSD 174 MB, CubiCasa5K) | M1 | R2 |
| 7 | F-DATA-UNIFY | Unified data schema: raster images and binary/multiclass wall masks | M1 | R2 |
| 8 | F-DATA-SPLIT | Strict project-isolated data partitioning (zero building/project overlap) | M1 | R2 |
| 9 | F-DATA-QC | Visual QC sample generator (original, mask, overlay triplets) | M1 | R2 |
| 10 | F-DATA-REPORT | Milestone M1 Dataset Preparation Report saved in `drywall_detection/reports/` | M1 | R2, R5 |
| 11 | F-VEC-EXTRACT | PyMuPDF/pdfplumber/Shapely vector geometry & text layer extraction | M2 | R1 |
| 12 | F-VEC-TRANSFORM | Bijective affine coordinate transformation ($M$ and $M^{-1}$) handling 90° rotation | M2 | R1 |
| 13 | F-TAG-DISCOVERY | Floor plan partition tag discovery (11.2x11.3 pt square boxes, leader lines) | M2 | R1 |
| 14 | F-SCHED-PARSE | Partition schedule parsing (A-900 & A-901, 24 assembly details) | M2 | R1 |
| 15 | F-SPATIAL-MATCH | 3-tier spatial matching (leader line raycast, buffer proximity, unassigned fallback) | M2 | R1 |
| 16 | F-CSV-EXPORT-STOP | CSV export & human-in-the-loop review stopping mechanism (`REVIEW_REQUIRED.lock`) | M2 | R1 |
| 17 | F-VEC-REPORT | Milestone M2 Vector PDF Processing Report saved in `drywall_detection/reports/` | M2 | R1, R5 |
| 18 | F-MODEL-ARCH | Implementation of candidate models (U-Net ResNet18/34 and SegFormer-B0) | M3 | R3 |
| 19 | F-LOSS-METRICS | Compound Soft Dice + Focal Loss, mIoU, Dice, Precision, Recall, Boundary IoU | M3 | R3 |
| 20 | F-MODEL-TRAIN | Hardware-aware training script with Google Colab compatibility | M3 | R3 |
| 21 | F-MODEL-COMPARE | Comparative validation evaluation and champion model selection | M3 | R3 |
| 22 | F-CHECKPOINT-SAVE | Champion checkpoint package saved in `drywall_detection/checkpoints/best_model/` | M3 | R3, R5 |
| 23 | F-PSEUDO-GUARD | Weak pseudo-labeling guardrail for 99th Street PDF (quarantine from val/test) | M3 | R3 |
| 24 | F-TRAIN-REPORT | Milestone M3 Wall Segmentation Report saved in `drywall_detection/reports/` | M3 | R3, R5 |
| 25 | F-CLASS-RULE | Rule-based drywall classification (Green GWB, Red CMU/glass, Yellow Uncertain) | M2 | R2, R4 |
| 26 | F-CLASS-SAFETY | Tag 1A CMU non-drywall safety override | M2 | R2, R4 |
| 27 | F-CLASS-EVAL | Vector pipeline accuracy evaluation on 5–10 plan regions vs Usman markup | M2 | R2, R4 |
| 28 | F-CLASS-REPORT | Milestone M2 Drywall Classification Report saved in `drywall_detection/reports/` | M2 | R2, R4, R5 |
| 29 | F-CHECKPOINT-RELOAD| Reload champion checkpoint from disk and execute offline inference | M3 | R3, R5 |
| 30 | F-ANNOTATED-OUTPUT | Generate annotated PDFs and floor plan image overlays with color-coded classes | M4 | R4 |
| 31 | F-LIMITATIONS-REPORT| Final Limitations Report (95% CD status, domain gap, single-project bounds) | M5 | R5 |
| 32 | F-DELIVERY-PKG | Full deliverable package verification (code, configs, tests, README) | M5 | R5 |

---

## 3. Milestones Schedule
Execution follows strict sequential order from M1 through M6 aligned with ORIGINAL_REQUEST.md requirements:

| # | Name | Scope & Deliverables | Dependencies | Status |
|---|---|---|---|:---:|
| **M1** | **Workspace and Dataset Audit** | Inspect workspace, master PDF, hardware; audit 6 candidate datasets (CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, MSD); licensing report; produce `reports/M1_audit_report.md`. | None | **DONE** |
| **M2** | **Dataset Preparation** | Download eligible dataset (MSD 174 MB, CubiCasa5K); unify schemas; project-isolated splits (zero project overlap); visual QC triplets; produce `reports/M2_dataset_report.md`. | M1 | **DONE** |
| **M3** | **Vector PDF Processing & Schedule Parsing** | Vector geometry & text extraction (PyMuPDF); 90° rotation transform; partition schedule parsing (A-900 & A-901, 24 details); 3-tier spatial matching; approved CSV export with review lock; produce `reports/M3_vector_schedule_report.md`. | M2 | **DONE** |
| **M4** | **Wall Segmentation Training** | Candidate models (SegFormer-B0 & U-Net); Compound Soft Dice + Focal Loss; Tier 5 hardware auto-tuning; Google Colab runner; champion bundle in `checkpoints/best_model/`; produce `reports/M4_model_training_report.md`. | M3 | **DONE** |
| **M5** | **Drywall Classification & Verification** | Rule-based classification from approved CSV; four-layer Detail 1A CMU veto; hybrid vector-ML fusion; native vector PDF annotations & raster overlays; benchmark vs 478 Usman markups; produce `reports/M5_classification_report.md`. | M4 | **DONE** |
| **M6** | **Final Validation, Delivery & Limitations Report** | Reload champion checkpoint from disk; run inference via reload-and-infer script; production CLI interface; full E2E validation; author `reports/M6_final_limitations_report.md` (95% CDs notice, domain gap, single-project bounds). | M5 | **IN_PROGRESS** |

---

## 4. Interface Contracts

### 4.1 Coordinate Transformation Contract (`drywall_detection.utils.coords`)
- `pdf_to_pixel(x: float, y: float, dpi: int = 150) -> Tuple[float, float]`
  - Formula: $px = (2592.0 - y) \cdot \frac{dpi}{72.0}$, $py = x \cdot \frac{dpi}{72.0}$
- `pixel_to_pdf(px: float, py: float, dpi: int = 150) -> Tuple[float, float]`
  - Formula: $x = \frac{py}{dpi/72.0}$, $y = 2592.0 - \frac{px}{dpi/72.0}$
- Invariant: Roundtrip bijection $|\text{pixel\_to\_pdf}(\text{pdf\_to\_pixel}(p)) - p| < 10^{-4}$ pt.

### 4.2 Schedule Parsing & CSV Review Contract (`drywall_detection.vector`)
- Output file: `drywall_detection/data/partition_schedule_mapping.csv`
- Columns: `[tag, sheet, detail_title, description, studs, layers, gwb_thickness, fire_rating, acoustic, finish, material_trade, proposed_class, confidence, notes]`
- Stopping Protocol:
  - Writes CSV file.
  - Creates sentinel lockfile: `drywall_detection/data/REVIEW_REQUIRED.lock`.
  - Exits with code `2` (Review Required).
  - Milestone M5 classification requires `drywall_detection/data/partition_schedule_mapping.approved.csv`.

### 4.3 Data Split Protocol (`drywall_detection.data.preparer`)
- Input: Dataset metadata with `site_id` / `building_id`.
- Output: Split manifests (`train.json`, `val.json`, `test.json`).
- Invariant: $\text{Projects}(\text{train}) \cap \text{Projects}(\text{val}) = \emptyset$, $\text{Projects}(\text{train}) \cap \text{Projects}(\text{test}) = \emptyset$, $\text{Projects}(\text{val}) \cap \text{Projects}(\text{test}) = \emptyset$.

### 4.4 Model Checkpoint Contract (`drywall_detection.checkpoints.best_model`)
Required files in `drywall_detection/checkpoints/best_model/`:
- `best_model.pt` (PyTorch state dict & weights)
- `config.json` (architecture type, backbone, input resolution, normalization parameters)
- `class_mapping.json` (`{"0": "background", "1": "wall"}`)
- `training_log.json` (loss history, validation metrics per epoch)
- `metrics.json` (mIoU, Wall IoU, Dice, Precision, Recall, Boundary IoU)
- `infer.py` (standalone reload-and-infer CLI script)
- `README.md` (model description and invocation instructions)
- `sample_overlays/` (visual predictions vs ground truth)

### 4.5 Classification Output Contract (`drywall_detection.classification`)
- Schema: GeoJSON / JSON containing wall polygons with properties:
  - `wall_id`: unique identifier
  - `geometry`: Shapely Polygon coordinates
  - `assigned_tag`: matched partition tag (or `null`)
  - `match_method`: `"leader_line"`, `"buffer_proximity"`, or `"unassigned"`
  - `classification`: `"Drywall"` (Green), `"Non-Drywall"` (Red), or `"Uncertain"` (Yellow)
  - `color_hex`: `"#00FF00"` (Green), `"#FF0000"` (Red), `"#FFFF00"` (Yellow)
  - `evidence`: schedule detail text or reason for uncertainty

---

## 5. Code Layout
All project implementation resides exclusively inside `drywall_detection/` at workspace root:

```
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\
└── drywall_detection/
    ├── __init__.py
    ├── config.py
    ├── utils/
    │   ├── __init__.py
    │   ├── coords.py
    │   └── hardware.py
    ├── audit/
    │   ├── __init__.py
    │   └── dataset_auditor.py
    ├── data/
    │   ├── __init__.py
    │   ├── downloader.py
    │   ├── preparer.py
    │   └── qc.py
    ├── vector/
    │   ├── __init__.py
    │   ├── extractor.py
    │   ├── schedule_parser.py
    │   └── spatial_matcher.py
    ├── models/
    │   ├── __init__.py
    │   ├── unet.py
    │   ├── segformer.py
    │   ├── losses.py
    │   ├── metrics.py
    │   ├── trainer.py
    │   └── evaluate.py
    ├── classification/
    │   ├── __init__.py
    │   └── classifier.py
    ├── pipeline/
    │   ├── __init__.py
    │   ├── infer.py
    │   └── annotate.py
    ├── checkpoints/
    │   └── best_model/
    │       ├── best_model.pt
    │       ├── config.json
    │       ├── class_mapping.json
    │       ├── training_log.json
    │       ├── metrics.json
    │       ├── infer.py
    │       ├── README.md
    │       └── sample_overlays/
    ├── tests/
    │   ├── __init__.py
    │   ├── test_coords.py
    │   ├── test_audit.py
    │   ├── test_data.py
    │   ├── test_vector.py
    │   ├── test_schedule.py
    │   ├── test_models.py
    │   ├── test_classification.py
    │   └── test_e2e.py
    └── reports/
        ├── M1_audit_report.md
        ├── M2_dataset_report.md
        ├── M3_vector_schedule_report.md
        ├── M4_model_training_report.md
        ├── M5_classification_report.md
        └── M6_final_limitations_report.md
```

---

## 6. Zero-Tolerance Integrity Rules
1. **Never hardcode test results** or create dummy/facade implementations.
2. **Never fabricate** dataset links, download statistics, model metrics, or evaluation numbers.
3. **Never classify Tag 1A as Drywall**: Detail 1A is explicitly 6" CMU masonry block and must be classified as Non-Drywall.
4. **Mandatory Forensic Auditor Veto**: A report of INTEGRITY VIOLATION from `teamwork_auditor` fails the milestone unconditionally.
5. **Always cite progress set limitations**: All reports must note that 99th Street is a 95% CDs progress set and a single-project calibration sample.
