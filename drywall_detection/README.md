# AI Drywall Detection & Wall Classification Module (`drywall_detection`)

> **MANDATORY NOTICE — PROGRESS SET STATUS & SINGLE-PROJECT BOUNDS**  
> The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set), authored by TPG Architecture LLP. It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
> All 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, vector extractions, and model segmentations on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards. Any vector extractions utilized during Milestone M4/M5 strictly observe weak pseudo-labeling guardrails and evaluation quarantine.  
> **Scope Boundary:** This module provides evidence-based material classification and geometric delineation of wall assemblies; it does NOT implement complete QTO engine features (bid-ready quantity takeoffs, wall dimensions, costing, or financial estimation).

---

## 1. Overview & Architecture

The `drywall_detection/` module is an isolated component designed to detect architectural walls, parse partition schedules, and classify drywall using a vector-first pipeline combined with deep learning segmentation on architectural drawings.

### Core Architectural Tracks:
1. **Vector-First CAD Extraction**: Direct extraction of vector linework, parallel-pair wall polygons, text layers, and partition tags at native sub-atomic coordinate precision using PyMuPDF and Shapely.
2. **Schedule Mining & Human Review Lock**: Mining multi-sheet partition schedules (Sheets A-900 & A-901) into structured schemas with an automated review-stopping mechanism (`REVIEW_REQUIRED.lock` / exit code 2).
3. **Evidence-Based Material Precedence**: Strict 4-class classification where human-approved schedule truth dominates and Detail 1A (`6" FIRE RATED CMU`) is unconditionally protected as Non-Drywall (Red `#D50000`).
4. **Offline Deep Learning Segmentation**: Self-contained SegFormer-B0 architecture with Compound Soft Dice + Focal Loss, executing 100% offline with 2D Hann apodization window tile stitching.
5. **Zero-Rasterization Vector Annotation**: Direct injection of translucent classification shapes into the PDF vector stream, preserving 100% of underlying CAD linework, fonts, and dimensions.

---

## 2. Installation & Environment Setup

### 2.1 Prerequisites
- Python 3.10 or higher (64-bit AMD64).
- Windows 10/11, macOS, or Linux.
- Minimum 4 GB RAM (8 GB recommended). Local GPU is supported via CUDA, but CPU-only execution is fully auto-tuned.

### 2.2 Virtual Environment & Dependencies
```powershell
# 1. Clone repository and navigate to workspace root
cd "c:\Users\TEC ZONE\OneDrive\Desktop\test-model"

# 2. Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install PyTorch (CPU or CUDA build)
# For CPU execution:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# For CUDA 11.8+ execution (if GPU is available):
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 4. Install core project dependencies
pip install PyMuPDF pdfplumber shapely opencv-python Pillow streamlit pandas psutil pytest
```

---

## 3. Quick Start: Local Web Testing Interface

To launch the local interactive testing interface for uploading drawings, previewing annotations, and downloading annotated deliverables:

```powershell
# Using the Windows launcher script:
.\run_app.bat

# Or directly with Streamlit:
streamlit run drywall_detection/app.py
```

The web interface will automatically open at `http://localhost:8501`.

### Interface Capabilities:
- **Universal Drawing Ingestion**: Upload any vector or scanned architectural PDF (`.pdf`) or floor-plan image (`.png`, `.jpg`, `.tiff`).
- **Interactive Multi-Page Viewer**: Toggle between original linework, 4-class colored overlay, and raw segmentation masks.
- **Session-Cached Ultra-Fast Rendering**: NumPy session-state caching enables sub-50 ms opacity and layer toggling without re-running inference.
- **High-Fidelity Downloads**:
  * *Annotated Vector PDF*: 100% vector linework preservation with translucent overlays.
  * *High-Resolution PNG*: 150 DPI raster preview with architectural legend card.
  * *RFC 7946 GeoJSON*: Machine-readable wall polygon geometries and classification properties.

---

## 4. Unified Production CLI Usage Guide

The package provides a unified production command-line interface via `python -m drywall_detection`:

```powershell
python -m drywall_detection <subcommand> [options]
```

### 4.1 Available Subcommands & Examples

#### 1. System Profile & Checkpoint Inspection (`info` / `version`)
Displays host hardware, CPU/RAM/disk profile, and champion model status:
```powershell
# Formatted text table
python -m drywall_detection info

# Machine-readable JSON output
python -m drywall_detection info --json
```

#### 2. Candidate Dataset Audit (`audit-datasets`)
Audits candidate datasets (MSD, CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD) for licensing compliance, disk space safety, and wall label availability:
```powershell
# Display Markdown comparison table
python -m drywall_detection audit-datasets --format table

# Audit single dataset with JSON output
python -m drywall_detection audit-datasets --dataset-id msd --format json

# Run audit and save report artifacts to disk
python -m drywall_detection audit-datasets --output-dir drywall_detection/reports --save
```

#### 3. Vector CAD Extraction (`extract-vector`)
Extracts vector paths, parallel-pair wall polygons, text tokens, and partition tags from architectural drawings:
```powershell
# Extract Sheet A-101 (page 14) and export GeoJSON
python -m drywall_detection extract-vector --pdf "path/to/drawings.pdf" --pages 14 --output-dir ./output/ --format geojson

# Run fast vector presence profiling only
python -m drywall_detection extract-vector --pdf "path/to/drawings.pdf" --pages 14 --detect-only
```

#### 4. Partition Schedule Parsing (`parse-schedule`)
Parses assembly details from schedule sheets (A-900 / A-901) and enforces the human review stopping mechanism:
```powershell
# Normal parsing with human review lock enforcement
python -m drywall_detection parse-schedule --pdf "path/to/drawings.pdf" --output-csv ./schedule.csv --approved-csv drywall_detection/data/partition_schedule_mapping.approved.csv --verify-detail-1a
```

#### 5. Wall Classification (`classify`)
Classifies wall geometries using approved schedule mapping and the 4-layer Detail 1A CMU veto:
```powershell
# Classify walls on Sheet A-101 and export annotated vector PDF
python -m drywall_detection classify --pdf "path/to/drawings.pdf" --pages 14 --schedule-csv drywall_detection/data/partition_schedule_mapping.approved.csv --output-dir ./output/ --export-annotated-pdf
```

#### 6. Deep Learning Segmentation (`infer-segmentation`)
Runs SegFormer-B0 sliding-window semantic segmentation on drawings or floor-plan images:
```powershell
# Run inference on a floor plan image
python -m drywall_detection infer-segmentation --input floorplan.png --output-dir ./output/ --checkpoint drywall_detection/checkpoints/best_model/ --device cpu
```

#### 7. Full End-to-End Pipeline (`run-pipeline`)
Executes the complete multi-modal pipeline with automatic modality routing (`VECTOR_FIRST`, `RASTER_ML`, `HYBRID`):
```powershell
# Process Sheet A-101 end-to-end
python -m drywall_detection run-pipeline --pdf "path/to/drawings.pdf" --pages 14 --output-dir ./output/ --schedule-csv drywall_detection/data/partition_schedule_mapping.approved.csv
```

### 4.2 Strict POSIX Exit Codes

| Exit Code | Meaning | Trigger Condition |
|:---:|---|---|
| **`0`** | **Success** | All operations completed successfully without error. |
| **`1`** | **Fatal Error** | Unhandled exception, file not found, or syntax error. |
| **`2`** | **Review Required** | `REVIEW_REQUIRED.lock` active; approved schedule CSV is missing or pending human sign-off. |
| **`3`** | **CMU Safety Veto Violation** | `IntegrityViolationError` triggered: attempt to classify Detail 1A CMU as Drywall. |

---

## 5. Standalone Checkpoint Reload & Offline Inference

The champion model bundle in `drywall_detection/checkpoints/best_model/` is entirely self-contained and operates without access to training scripts or internet connectivity:

```powershell
# Run standalone inference directly from checkpoint bundle
python drywall_detection/checkpoints/best_model/infer.py `
  --image "path/to/drawing.png" `
  --output "annotated_drawing.png" `
  --device cpu
```

### Checkpoint Deliverables Inventory:
- `best_model.pt`: Full PyTorch state dict (3,715,172 trainable parameters).
- `config.json`: Hyperparameters, 512x512 tile size, and normalization constants.
- `class_mapping.json`: Canonical 4-class taxonomy and color mappings.
- `training_log.json`: Training history across epochs with loss curves.
- `metrics.json`: Final held-out evaluation metrics and 4x4 confusion matrix.
- `infer.py`: Standalone CLI with Hann window apodization stitching.
- `README.md`: Model card, minimal reproduction snippet, and Colab runner instructions.
- `sample_overlays/`: Visual validation prediction overlays.

---

## 6. 4-Class Material Taxonomy & Mandatory Safety Rules

| Class ID | Class Name | Color Code | RGB / Hex | Assembly Definitions & Precedence Rules |
|:---:|:---:|:---:|:---:|---|
| **0** | **Background** | White / Transparent | `(255, 255, 255)` / `#FFFFFF` | Non-wall canvas, room voids, dimension strings, annotations, text. |
| **1** | **Drywall** | Green | `(0, 200, 83)` / `#00C853` | Gypsum Wallboard (GWB) partitions (Details 1B–1E, 2B–2C, 3A, 3D, 5B, 5D, 5E, 7A–7G, 8A, 10). |
| **2** | **Non-Drywall** | Red | `(213, 0, 0)` / `#D50000` | 6" CMU block masonry (**Detail 1A mandatory veto**), concrete piers (Detail 11), glazed officefronts (GL1, GL2). |
| **3** | **Uncertain** | Yellow | `(255, 214, 0)` / `#FFD600` | Unassigned partitions, ambiguous tags, electrical TV niches (Detail 09), generic exterior walls. |

### Detail 1A CMU Safety Veto (4-Layer Defense-in-Depth):
1. **Layer 1 (Ingestion Gate)**: `DrywallClassifier` asserts `records["1A"]["proposed_class"] == "Non-Drywall"`. Any tampered CSV marking 1A as Drywall raises `IntegrityViolationError`.
2. **Layer 2 (Runtime Assignment Invariant)**: In `classify_walls()`, Tag 1A unconditionally assigns `Non-Drywall` (`#D50000`), bypassing all conflicting text or heuristics.
3. **Layer 3 (Post-Init & Mutator Guard)**: `ClassifiedWallPolygon.__post_init__` and `__setattr__` intercept runtime mutation attempts, immediately halting with `IntegrityViolationError`.
4. **Layer 4 (Fusion Veto)**: `HybridFusionPipeline` unconditionally protects Tag 1A from neural probability overrides.

---

## 7. Complete Test Suite Reproduction Commands

To independently reproduce the entire test suite and verify 100% compliance:

```powershell
# 1. Run Checkpoint Reload & Determinism Test Suite (21 tests)
pytest drywall_detection/tests/test_checkpoint_infer.py -v

# 2. Run Unified Production CLI Test Suite (29 tests)
pytest drywall_detection/tests/test_cli.py -v

# 3. Run Delivery Packaging & Integrity Test Suite (7 tests)
pytest drywall_detection/tests/test_delivery_packaging.py -v

# 4. Run Core Classification & Usman Ground Truth Benchmark Tests (20 tests)
pytest drywall_detection/tests/test_classification.py -v

# 5. Run Challenger Safety & CMU Veto Stress Tests (62 tests)
pytest drywall_detection/tests/test_challenger_m5_safety.py -v

# 6. Run Complete Repository Test Suite (>200 tests)
pytest drywall_detection/tests/ -v
```

---

## 8. Hardware Profiling & Dynamic Auto-Configuration

The system includes an automatic hardware profiler (`drywall_detection/utils/hardware.py`) that probes CPU cores, RAM, GPU/CUDA, and disk space, dynamically selecting from 5 operational tiers:

- **Tier 1 (High-End Cloud GPU)**: NVIDIA A100/H100, batch size 32, 512x512 resolution, mixed precision (FP16/BF16).
- **Tier 2 (Standard Workstation GPU)**: RTX 3090/4090, batch size 16, 512x512 resolution.
- **Tier 3 (Entry/Consumer GPU)**: RTX 3060/4060, batch size 8, 384x384 resolution.
- **Tier 4 (Standard Multi-Core CPU)**: 8+ cores, >16 GB RAM, batch size 4.
- **Tier 5 (Constrained Edge Host)**: Automatically active on host (Intel Core i5, <2 GB free RAM). Configures batch size 2, gradient accumulation steps 8 (effective batch size 16), 256x256 training resolution, `num_workers=0`, and `torch.set_num_threads(4)` to prevent Out-Of-Memory (OOM) crashes.

---

## 9. Comprehensive Limitations & Disclaimers

1. **Progress Set Status**: All reference drawings originate from MTA Contract C-48526 (99th Street Phase 2 Interior Set), explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"`. This is an unapproved interim design development progress set, not an approved final as-built construction document.
2. **Single-Project Calibration Scope**: All 71 reference sheets depict a single transit facility drafted by TPG Architecture LLP. Accuracy metrics demonstrate calibration to this project; cross-domain generalization across arbitrary architectural styles, Revit export styles, or other drafting firms requires project-specific schedule review.
3. **Domain Gap**: Pure machine learning models trained on residential academic datasets (CubiCasa5K, MSD) cannot be directly applied to commercial transit drawings without the vector schedule parsing pipeline due to severe false positives on non-wall linework and material blindness.
4. **Partition Schedule Requirement**: High-confidence drywall classification depends on approved partition schedules. Untagged walls are strictly marked as **Uncertain (Yellow)** with 0% material hallucination.
5. **No Commercial Quantity Takeoffs or Cost Estimating**: This software does NOT calculate bid-ready quantities, certified wall lengths, or construction cost estimates. Professional estimators must independently verify all materials and geometries.
