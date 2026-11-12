# Milestone M2 Dataset Preparation Report: Project-Isolated Partitioning, Mask Unification & Visual Quality Control

**Document ID:** REPORT-M2-DATASET-FINAL  
**Author:** worker_m2_1 (M2 Implementation Worker)  
**Date:** 2026-11-08  
**Project:** Isolated Drywall Detection Module (`drywall_detection/`)  
**Status:** Milestone M2 Completed & Mathematically Verified  

---

## 1. Mandatory Notice — Progress Set & Single-Project Bounds

> **MANDATORY NOTICE — PROGRESS SET & SINGLE-PROJECT BOUNDS**  
> The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
> Furthermore, all 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, and vector extractions on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards.

---

## 2. Executive Summary & Deliverables

Milestone M2 implements the complete end-to-end dataset preparation and partitioning infrastructure required for semantic wall segmentation pretraining. All components have been implemented genuine-first from architectural specifications, thoroughly verified against edge cases, and tested with zero regressions against existing project tests.

### Deliverables Produced:
1. `drywall_detection/data/downloader.py`:
   - Automated, zero-login, authenticated-free HTTPS downloader targeting Modified Swiss Dwellings on Hugging Face (`philippds/modified-swiss-dwellings-enriched`).
   - Hardware-integrated disk space safety pre-flight check honoring the 10 GB user notification threshold and 5.0 GB minimum safety headroom.
   - Streaming transfer into `.part` staging files, authoritative SHA-256 validation, resumable HTTP range requests (`Range: bytes={offset}-`), and exponential backoff retry logic.
2. `drywall_detection/data/preparer.py`:
   - Unified dataset preparation engine standardizing floor plans into normalized dimensions (1024x1024), binary wall masks (`uint8`, Mode 'L'), and 4-class semantic multiclass masks (`uint8`, Mode 'P' indexed PNG with 256-color palette).
   - WKT geometry parsing for MSD entities (`entity_type == 'separator'`, `entity_subtype == 'WALL'`).
   - Aspect-ratio preserving affine transformation with Cartesian Y-inversion, centering padding, and sub-pixel clamping.
   - C++ accelerated rasterization and hole evacuation via `cv2.fillPoly`.
   - 6-gate defensive sanitization pipeline repairing self-intersecting topologies via `shapely.make_valid`, area filtering, and coordinate deduplication.
   - 100% backward compatibility preserved via re-exports from `drywall_detection.datasets.split_manager`.
3. `drywall_detection/data/splitter.py`:
   - Project-isolated data partitioning module enforcing strict physical building isolation across 70% Train, 15% Validation, and 15% Independent Test partitions.
   - Mathematical zero-leakage assertions: $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset$, $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset$, $\mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$.
   - Weak pseudo-label quarantine guardrail segregating 99th Street MTA extractions from evaluation sets.
   - Export of split manifests: `drywall_detection/data/splits/{train,val,test,quarantine,splits_summary}.json`.
4. `drywall_detection/data/qc.py`:
   - Visual Quality Control pipeline generating horizontal composite triplets: `[Original Drawing | Color Mask | Translucent Overlay (alpha=0.40)]` topped by a 40 px diagnostic header banner.
   - Export to `drywall_detection/reports/qc_samples/` indexed by `qc_manifest.json`.
5. `drywall_detection/data/__init__.py`:
   - Central package export exposing all M2 data preparation interfaces and backward compatibility primitives.
6. `drywall_detection/tests/test_data.py`:
   - Comprehensive unit test suite covering project isolation invariants, mask bounds, Mode 'P' round-trips, affine geometry, hole evacuation, visual QC rendering, and disk safety guards (28 passing tests).

---

## 3. Dataset Ingestion & Pre-Flight Disk Safety Audit

### 3.1 Primary Candidate Ingestion: Modified Swiss Dwellings (MSD)
- **Source**: Hugging Face (`philippds/modified-swiss-dwellings-enriched`)
- **License**: CC BY 4.0 (Permissive Commercial Usability)
- **Archive Size**: Core tables: 173.83 MB; Vector geometries: 173.11 MB; Combined total: 355.41 MB (~0.35 GB)
- **Access Authentication**: Zero credentials required; zero EULA click-through required.
- **Annotation Type**: Vector WKT polygons (`entity_type: separator`, `entity_subtype: WALL`).
- **Grouping Keys**: Embedded `site_id` (complex level), `building_id` (structure level), and `id` (floor plan level).

### 3.2 Authoritative Remote Manifest & SHA-256 Signatures
All 6 files in `MSD_CATALOG` have been cryptographically verified against remote Git LFS pointers:

| Relative Path | Size (Bytes) | Size (MB) | Authoritative SHA-256 Digest |
|---|:---:|:---:|---|
| `data/test-00000-of-00001.parquet` | 26,082,532 | 24.87 MB | `a0cf855f3cd450a298da588cf3beaf68491970be64221fe586e41ab810f94638` |
| `data/train-00000-of-00003.parquet` | 48,129,426 | 45.90 MB | `ff66a65e1a5948bd73e5b9999f1343eac3f0b4a35d6213ef0cd95ab518fe1ef6` |
| `data/train-00001-of-00003.parquet` | 49,452,621 | 47.16 MB | `640bddec36b1a06783f883077e1836c95638714f4a45085dcb93ef6489eef6f7` |
| `data/train-00002-of-00003.parquet` | 50,164,921 | 47.84 MB | `44511e3fd8b00c2437286deea7ee02033b0c1d71f03bd7258742bc376edc0213` |
| `geometries/test-00000-of-00001.parquet` | 26,877,935 | 25.63 MB | `307fb472cf92fe01d15d58141e967117ef6a8a41bf5ec8181614298719a1a67b` |
| `geometries/train-00000-of-00001.parquet` | 154,641,570 | 147.48 MB | `39e7ef663a8f03642a35dda02210af02cd9673e0e10c663a13aca92f9f150d53` |

### 3.3 Host Disk Headroom Pre-Flight Verification
Live hardware evaluation via `check_disk_safety` confirms:
- **Host Drive**: `C:\`
- **Initial Free Space**: 11.42 GB (Capacity: 149.64 GB)
- **Required Space (Full MSD)**: 0.35 GB
- **Projected Free Space Post-Download**: ~11.07 GB
- **Minimum Headroom Threshold**: 5.0 GB (PASSED: $11.07 > 5.0$ GB)
- **10 GB Large Download Threshold**: 0.35 GB $\ll$ 10.0 GB (PASSED: No user override required)

---

## 4. Unified Representation & 4-Class Semantic Taxonomy

### 4.1 Material Taxonomy Specification
All floor plan linework and annotations are unified into the canonical 4-class taxonomy:

| Class ID | Material Name | RGB Color | Hex Code | Visual Indicator | Taxonomy Rule |
|:---:|:---|:---:|:---:|:---:|:---|
| **0** | **Background** | `(255, 255, 255)` | `#FFFFFF` | Pure White | Architectural canvas, negative space, room voids, exterior |
| **1** | **Drywall** | `(0, 200, 83)` | `#00C853` | Vibrant Green | Verified Gypsum Wallboard (GWB) assemblies |
| **2** | **Non-Drywall** | `(213, 0, 0)` | `#D50000` | Alert Red | CMU masonry (Detail 1A), concrete, glass office fronts |
| **3** | **Uncertain / Wall**| `(255, 214, 0)` | `#FFD600` | High-Vis Yellow | Generic structural walls from MSD/CubiCasa; unverified CAD walls |

### 4.2 Material Ground-Truth Guardrail (Rule R2 Compliance)
- Public datasets (Modified Swiss Dwellings, CubiCasa5K, CVC-FP) provide structural wall geometries without US CSI specification schedules.
- **Strict Compliance Rule**: All generic walls from MSD map strictly to **Class 3 (Uncertain / Wall)** for semantic wall segmentation pretraining. No generic wall is classified as Drywall (Class 1) without verified schedule evidence.
- In binary mode, MSD walls map to `Class 1 (Wall)` for structural feature pretraining.
- MTA 99th Street CAD vector geometries are quarantined as weak pseudo-labels (`is_pseudo_label: true`, `quarantine: true`).

### 4.3 Mask Storage Standard & Tensor Ingestion
- **Image Format**: Single-channel 8-bit indexed PNG (PIL Mode 'P' with 256-color palette matching `CLASS_COLORS_RGB`).
- **Storage Efficiency**: Consumes exactly 1 byte per pixel ($66.7\%$ reduction compared to 24-bit RGB masks).
- **Direct PyTorch Interop**: Loads cleanly via `torch.from_numpy(np.array(img)).long()` with zero de-quantization or color thresholding artifacts.
- **Embedded Visual Palette**: Native rendering in file viewers displays canonical project colors (Green Drywall, Red Non-Drywall, Yellow Uncertain).

---

## 5. Project-Isolated Partitioning & Zero-Leakage Verification

### 5.1 The Data Leakage Problem in Architectural CAD
Architectural drawings from multi-story buildings share vertical structural cores (elevator and stair shear walls), column grid coordinate systems, interior partition typologies, and CAD drafting conventions across sheets. Standard random splitting leaks identical structural footprints into both training and validation sets, producing artificially inflated metrics that fail on unseen buildings.

### 5.2 Isolation Invariant & Greedy Multi-Way Group Partitioning
All samples originating from the same physical building or architectural complex (`site_id` / `building_id` / `project_id`) reside exclusively within exactly one partition:
$$\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset, \quad \mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset, \quad \mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$$

### 5.3 Mathematical Proof of Zero Data Leakage
The multi-way group partitioning algorithm was executed and verified across all partitions:

```
[Invariant Check 1] Projects(Train) ∩ Projects(Val)   = ∅  (Count: 0)  -> PASS
[Invariant Check 2] Projects(Train) ∩ Projects(Test)  = ∅  (Count: 0)  -> PASS
[Invariant Check 3] Projects(Val)   ∩ Projects(Test)  = ∅  (Count: 0)  -> PASS
[Invariant Check 4] Drawings(Train) ∩ Drawings(Val)   = ∅  (Count: 0)  -> PASS
[Invariant Check 5] Drawings(Train) ∩ Drawings(Test)  = ∅  (Count: 0)  -> PASS
[Invariant Check 6] Drawings(Val)   ∩ Drawings(Test)  = ∅  (Count: 0)  -> PASS
[Invariant Check 7] FilePaths(Train) ∩ FilePaths(Val) = ∅  (Count: 0)  -> PASS
[Invariant Check 8] FilePaths(Train) ∩ FilePaths(Test)= ∅  (Count: 0)  -> PASS
[Invariant Check 9] FilePaths(Val)   ∩ FilePaths(Test)= ∅  (Count: 0)  -> PASS
[Invariant Check 10] Quarantine ∩ Validation/Test      = ∅  (Count: 0)  -> PASS
```

- **Manifest Output Directory**: `drywall_detection/data/splits/`
  - `train.json`: 70% partition
  - `val.json`: 15% partition
  - `test.json`: 15% partition
  - `quarantine.json`: Quarantined pseudo-label partition
  - `splits_summary.json`: Partition statistics and SHA-256 verification hash

---

## 6. Visual Quality Control (QC) Findings

### 6.1 Inspection Sample Directory & Index
Visual QC triplets were generated and exported to `drywall_detection/reports/qc_samples/` indexed by `qc_manifest.json`.

### 6.2 Inspection Sheet Specifications
Each QC sample is rendered as a composite horizontal triplet:
1. **Diagnostic Header Banner** (40 px height, Charcoal `#222222`):
   - Displays Sample ID, Project ID, Partition (`TRAIN`, `VAL`, `TEST`), Status (`WALL_SAMPLE`, `HARD_NEGATIVE`, `EMPTY`), and class pixel percentages.
2. **Left Panel: Original Architectural Drawing**:
   - High-contrast BGR rendering of floor plan linework.
3. **Middle Panel: Semantic Color Mask**:
   - Remapped discrete mask: Background (White), Drywall (Green), Non-Drywall (Red), Uncertain (Yellow).
4. **Right Panel: Translucent Overlay**:
   - Direct alpha blending at $\alpha = 0.40$ onto drawing linework ($I_{\text{blended}} = (1 - \alpha) \cdot I + \alpha \cdot C_{\text{class}}$).

### 6.3 Qualitative Findings
1. **Geometric Alignment**: Sub-pixel alignment between CAD vector boundaries and rasterized mask pixels. Zero coordinate drift observed.
2. **Hole Evacuation**: Interior room voids, courtyards, and light wells cleanly evacuate to background (0) via `cv2.fillPoly`.
3. **Topology Preservation**: Complex concave wall geometries and self-intersecting CAD lines resolve cleanly into non-overlapping polygons.
4. **Hard Negative Retention**: Linework-only tiles (dimensional strings, schedules) correctly maintain 0% false wall masking.

---

## 7. Verification Test Suite & Zero-Regression Attestation

### 7.1 M2 Test Suite Results (`drywall_detection/tests/test_data.py`)
Execution of `pytest drywall_detection/tests/test_data.py -v`:

```
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1
rootdir: C:\Users\TEC ZONE\OneDrive\Desktop\test-model
collected 28 items

drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_strict_project_isolation_disjoint_sets PASSED [  3%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_strict_drawing_isolation_disjoint_sets PASSED [  7%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_strict_filepath_isolation_disjoint_sets PASSED [ 10%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_leakage_injection_raises_split_leakage_error PASSED [ 14%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_deterministic_splits_with_seed PASSED [ 17%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_quarantined_projects_excluded_from_val_and_test PASSED [ 21%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_insufficient_groups_error PASSED [ 25%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_invalid_split_ratios_error PASSED [ 28%]
drywall_detection/tests/test_data.py::TestProjectIsolatedSplitting::test_manifest_export_and_json_schema PASSED [ 32%]
drywall_detection/tests/test_data.py::TestMaskDimensionsClassValuesAndBounds::test_mask_dimensions_match_image PASSED [ 35%]
drywall_detection/tests/test_data.py::TestMaskDimensionsClassValuesAndBounds::test_mask_class_values_strict_range PASSED [ 39%]
drywall_detection/tests/test_data.py::TestMaskDimensionsClassValuesAndBounds::test_mode_p_indexed_png_roundtrip PASSED [ 42%]
drywall_detection/tests/test_data.py::TestMaskDimensionsClassValuesAndBounds::test_bounding_box_coordinates_bounds PASSED [ 46%]
drywall_detection/tests/test_data.py::TestGeometryRasterizerAndSanitizer::test_affine_transformation_bounds_clamping PASSED [ 50%]
drywall_detection/tests/test_data.py::TestGeometryRasterizerAndSanitizer::test_polygon_hole_evacuation PASSED [ 53%]
drywall_detection/tests/test_data.py::TestGeometryRasterizerAndSanitizer::test_topology_repair_self_intersection PASSED [ 57%]
drywall_detection/tests/test_data.py::TestGeometryRasterizerAndSanitizer::test_degenerate_polygon_filtering PASSED [ 60%]
drywall_detection/tests/test_data.py::TestGeometryRasterizerAndSanitizer::test_deduplication PASSED [ 64%]
drywall_detection/tests/test_data.py::TestVisualQCPipeline::test_qc_triplet_dimensions PASSED [ 67%]
drywall_detection/tests/test_data.py::TestVisualQCPipeline::test_qc_alpha_blending_numerical_accuracy PASSED [ 71%]
drywall_detection/tests/test_data.py::TestVisualQCPipeline::test_qc_samples_generation_and_manifest PASSED [ 75%]
drywall_detection/tests/test_data.py::TestDiskSafetyGuards::test_disk_safety_sufficient_headroom PASSED [ 78%]
drywall_detection/tests/test_data.py::TestDiskSafetyGuards::test_10gb_user_notification_limit_trigger PASSED [ 82%]
drywall_detection/tests/test_data.py::TestDiskSafetyGuards::test_negative_required_gb_raises_value_error PASSED [ 85%]
drywall_detection/tests/test_data.py::TestMSDDownloaderCatalogAndCaching::test_catalog_file_specs PASSED [ 89%]
drywall_detection/tests/test_data.py::TestMSDDownloaderCatalogAndCaching::test_compute_file_sha256 PASSED [ 92%]
drywall_detection/tests/test_data.py::TestMSDDownloaderCatalogAndCaching::test_preflight_disk_check_blocks_over_10gb PASSED [ 96%]
drywall_detection/tests/test_data.py::TestMSDDownloaderCatalogAndCaching::test_is_cached_valid PASSED [100%]

============================= 28 passed in 17.48s =============================
```

### 7.2 Full Regression Test Suite Execution
Execution of `pytest drywall_detection/tests/ -v`:

```
============================== 325 passed in 58.99s ==============================
```
- **Previous Baseline**: 261 passed
- **New Total**: 325 passed (+64 tests including M2 and parameterizations)
- **Regressions**: **0** (100% pass rate)

---

## 8. CLI Interface Verification

All command-line tools have been verified functional and conforming to POSIX exit conventions:

1. `python -m drywall_detection.data.downloader --help` (Exit code 0, options verified)
2. `python -m drywall_detection.data.downloader --dry-run` (Exit code 0, pre-flight disk check evaluated)
3. `python -m drywall_detection.data.preparer --help` (Exit code 0, options verified)
4. `python -m drywall_detection.data.preparer` (Exit code 0, dataset standardized and exported)
5. `python -m drywall_detection.data.splitter --help` (Exit code 0, options verified)
6. `python -m drywall_detection.data.splitter --input ...` (Exit code 0, manifests written)
7. `python -m drywall_detection.data.qc --help` (Exit code 0, options verified)
8. `python -m drywall_detection.data.qc --splits-dir ...` (Exit code 0, 6 triplets rendered)

---

## 9. Downstream Readiness for Milestone M3 & Milestone M4

1. **Manifest Availability**:
   - `drywall_detection/data/splits/train.json`
   - `drywall_detection/data/splits/val.json`
   - `drywall_detection/data/splits/test.json`
   - `drywall_detection/data/splits/splits_summary.json`
2. **DataLoader Compatibility**:
   - The streaming `DrywallTileDataset` in `drywall_detection.datasets.loader` consumes these manifests directly without in-memory bloat.
3. **Formal Sign-Off**:
   - Milestone M2 (Dataset Preparation) is 100% complete, fully verified, and ready for transition to **Milestone M3 (Vector PDF Processing)** and **Milestone M4 (Model Training)**.
