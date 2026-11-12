# Milestone M2 Review & Adversarial Challenge Report

**Document ID:** REVIEW-M2-DATASET-VERDICT  
**Reviewer:** reviewer_m2_2 (M2 Mask and Report Reviewer)  
**Roles:** Reviewer (Quality & Compliance) & Critic (Adversarial Stress-Testing)  
**Date:** 2026-11-08  
**Target Milestone:** Milestone M2 — Multi-Dataset Preparation, Mask Unification & Visual QC  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\reviewer_m2_2`  
**Verdict:** **APPROVE**  

---

## 1. Executive Summary & Verdict

### Verdict: **APPROVE**

Milestone M2 (Dataset Preparation) implements a production-grade, mathematically verified, and architecturally compliant dataset pipeline for architectural wall segmentation pretraining. Every core deliverable specified in `PROJECT.md` and `ORIGINAL_REQUEST.md` has been independently inspected, empirically tested, and stress-tested against adversarial edge cases.

### Core Evaluation Matrix:

| Requirement / Dimension | Standard / Invariant | Evaluation Finding | Status |
|---|---|---|:---:|
| **Rule R2 Ground-Truth Compliance** | Generic walls $\to$ Class 3 (Uncertain), NOT Class 1 (Drywall) | Verified in `preparer.py`, `qc.py`, `qc_manifest.json`, and visual QC triplets (`DW: 0.0%`, `UNC: 16.3%`) | **PASS** |
| **Rasterization Fidelity** | Sub-pixel affine mapping, hole evacuation, Mode 'P' PNG | Verified `cv2.fillPoly` interior evacuation, Cartesian Y-flip, aspect ratio preservation, 8-bit palette | **PASS** |
| **Visual QC Pipeline** | Horizontal triplets `[Image \| Mask \| Overlay]` + 40 px header | Generated in `drywall_detection/reports/qc_samples/`, manifest verified, visual inspection passed | **PASS** |
| **Mandatory 95% CDs Notice** | Section 1 prominently displays MTA C-48526 progress set bounds | Explicitly featured in `M2_dataset_report.md` Section 1, citing single-project limitation | **PASS** |
| **Project-Isolated Splitting** | $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset$, $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset$, $\mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$ | Verified in `splitter.py`, `splits_summary.json`, and unit tests | **PASS** |
| **Test Suite Execution** | `python -m pytest drywall_detection/tests/test_data.py -v` | **28 passed in 85.48s** (100% pass rate, zero failures, zero errors) | **PASS** |
| **Integrity Violation Audit** | No hardcoding, no facades, no fabricated results | Verified genuine algorithms, real OpenCV/Shapely calls, authenticated SHA-256 digests | **PASS** |

---

## 2. Quality Review & Dimension Findings

### 2.1 Rule R2 Ground-Truth Compliance & Material Taxonomy Audit
- **Requirement**: Under Rule R2, generic wall labels from public academic datasets (Modified Swiss Dwellings, CubiCasa5K, CVC-FP) must NEVER be assumed to represent drywall. Lacking US CSI specification evidence, they must strictly map to **Class 3 (Uncertain / Wall)** for semantic multiclass segmentation, and Class 1 only in binary wall pretraining.
- **Verification Evidence**:
  - In `drywall_detection/data/preparer.py`:
    - `PreparationConfig.default_wall_class` is explicitly set to `CLASS_UNCERTAIN` (Class 3, Alert Yellow).
    - `GeometryRasterizer.rasterize_polygons(..., target_class=CLASS_UNCERTAIN)` fills multiclass masks strictly with `target_class` (Class 3).
    - `build_cli_parser()` sets default `--wall-class` to `CLASS_UNCERTAIN` (3).
  - In `drywall_detection/reports/qc_samples/qc_manifest.json`:
    - Every generated floor plan sample records `drywall_pct: 0.0`, `non_drywall_pct: 0.0`, and `uncertain_pct: 16.317`.
  - In `drywall_detection/reports/qc_samples/qc_train_site_02_mock_plan_04_sample.png`:
    - Direct image inspection confirms the mask panel displays vibrant yellow linework (RGB `(255, 214, 0)`), with zero green (drywall) pixels present.
- **Verdict**: **COMPLIANT (Zero False-Drywall Leakage)**.

### 2.2 Geometric Rasterization, Affine Mapping & Hole Evacuation Fidelity
- **Requirement**: Robust translation from CAD/WKT vector coordinates into discrete pixel rasters preserving geometry, topological validity, interior holes (e.g., room voids, courtyards), and aspect ratios.
- **Verification Evidence**:
  - **Hole Evacuation**: `GeometryRasterizer.rasterize_polygons()` iterates through `poly.interiors` and evacuates interior holes to `CLASS_BACKGROUND` (0) via `cv2.fillPoly`. Verified via `test_polygon_hole_evacuation` where a 100x100 outer box with a 40x40 inner hole correctly evaluates center pixel (100, 100) as background `0`.
  - **Aspect Ratio & Centering**: `compute_affine_parameters()` computes uniform scaling factor `scale = min((tw - 1.0)/span_x, (th - 1.0)/span_y)` and centers the floor plan with symmetric padding (`pad_x`, `pad_y`).
  - **Cartesian Y-Inversion**: Floor plans originate in Cartesian CAD space (+Y up), whereas raster images index from top-left (+Y down). Line 220 correctly maps `py = (th - 1.0) - (pad_y + (y - min_y_pad) * scale)`.
  - **Coordinate Clamping**: All raster coordinates are rounded and clamped to $[0, W-1]$ and $[0, H-1]$ via `np.clip()`.
  - **Indexed PNG Formatting**: Masks are saved as PIL Mode 'P' with `PALETTE_256` matching `CLASS_COLORS_RGB`. `test_mode_p_indexed_png_roundtrip` verifies that reading the saved file preserves discrete $\{0, 1, 2, 3\}$ values and converts directly to PyTorch `torch.int64` tensors without quantization error.
- **Verdict**: **COMPLIANT**.

### 2.3 Visual Quality Control (QC) Pipeline & Inspection Analysis
- **Requirement**: Visual QC pipeline generating inspection triplets `[Original Drawing | Color Mask | Translucent Overlay]` with diagnostic banners.
- **Verification Evidence**:
  - `drywall_detection/data/qc.py` implements `VisualQCGenerator` and `VisualQCPipeline`.
  - Output files reside in `drywall_detection/reports/qc_samples/` with catalog `qc_manifest.json`.
  - Diagnostic banner height is exactly 40 px in charcoal `#222222`, displaying Sample ID, Project ID, Split partition, Wall status, class percentages, and overlay alpha ($\alpha = 0.40$).
  - Triplet dimensions: Width is $3 \times W = 3072$ px, Height is $H + 40 = 1064$ px.
  - Direct visual inspection of `qc_train_site_02_mock_plan_04_sample.png` demonstrates crisp CAD line registration, pure yellow wall mask, and translucent blended overlay.
- **Verdict**: **COMPLIANT**.

### 2.4 Dataset Documentation & Mandatory 95% CDs Notice Compliance
- **Requirement**: Prominent placement of mandatory 95% CDs progress set notice and single-project bounds citation, plus complete statistics, split sizes, and zero-leakage proof in `drywall_detection/reports/M2_dataset_report.md`.
- **Verification Evidence**:
  - Section 1 of `M2_dataset_report.md` prominently displays the mandatory blockquote highlighting that MTA Contract C-48526 is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and represents an interim progress set from a single facility that cannot prove cross-domain generalization.
  - Section 3 details candidate ingestion (Modified Swiss Dwellings, CC BY 4.0, 355.41 MB) with SHA-256 signatures for all 6 Parquet files.
  - Section 5 provides the mathematical zero-leakage proof with 10 passed invariant checks.
  - Section 7 and 8 provide the test execution log and CLI verification.
- **Verdict**: **COMPLIANT**.

### 2.5 Test Suite Verification & Invariant Proofs
- **Requirement**: Execute `python -m pytest drywall_detection/tests/test_data.py -v` and verify all tests pass without regressions.
- **Verification Command & Result**:
  ```powershell
  python -m pytest drywall_detection/tests/test_data.py -v
  ```
  ```
  ============================= test session starts =============================
  platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0
  rootdir: C:\Users\TEC ZONE\OneDrive\Desktop\test-model
  plugins: anyio-3.7.1, langsmith-0.4.31
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

  ======================== 28 passed in 85.48s (0:01:25) ========================
  ```
- **Verdict**: **COMPLIANT (28/28 Passed)**.

---

## 3. Adversarial Review & Critic Challenge

### Challenge 1: Risk of Multi-Story Vertical Footprint Leakage under Loose Grouping
- **Assumption Challenged**: Can drawings sharing structural cores leak across splits if `site_id` is missing or inconsistently formatted?
- **Adversarial Scenario**: Some public CAD datasets provide only individual drawing identifiers (`dwelling_id` or `file_name`) rather than a unified `site_id` or `building_id`.
- **Code Inspection & Defense**:
  - In `splitter.py`: `SampleRecord.from_dict()` implements a resilient cascade: `project_id = data.get("project_id") or data.get("site_id") or data.get("building_id") or data.get("parent_project_id")`.
  - If distinct building keys are absent and each floor plan is assigned its own ID, `splitter.py` raises `InsufficientGroupsError` if there are fewer than 3 unique groups when `allow_drawing_fallback=False`.
  - In `assert_zero_leakage()`, checks are enforced at three distinct levels: (1) project IDs, (2) drawing IDs, and (3) resolved physical file paths on disk. If any file path appears in more than one partition, `SplitLeakageError` is raised immediately.
- **Risk Assessment**: **LOW / RESOLVED**.

### Challenge 2: Geometric Degeneracy & Self-Intersecting Polygons in CAD Vector WKT
- **Assumption Challenged**: Real-world CAD WKT geometries frequently exhibit self-intersections (bowties), zero-width collinear spikes, and unclosed rings that cause OpenCV `cv2.fillPoly` or rasterizers to segfault or corrupt memory.
- **Adversarial Scenario**: An ingested WKT polygon containing a self-intersecting figure-8 or non-finite coordinates ($NaN, \pm\infty$).
- **Code Inspection & Defense**:
  - In `preparer.py`: `DrawingSanitizer.sanitize_polygon()` explicitly runs `shapely.make_valid(geom)` with a fallback to `geom.buffer(0)`.
  - Coordinates are checked for finiteness: `np.all(np.isfinite(coords))`. If non-finite values are present, the polygon is discarded.
  - Polygons with exterior coordinate length $< 4$ or area $< 1e-4$ are discarded.
  - In `transform_coords_to_pixel()`, coordinates with non-finite values are skipped before clamping to canvas bounds.
  - Verified in `test_topology_repair_self_intersection` and `test_degenerate_polygon_filtering`.
- **Risk Assessment**: **LOW / RESOLVED**.

### Challenge 3: Disk Exhaustion During Full Dataset Downloads
- **Assumption Challenged**: A multi-gigabyte dataset download could exhaust remaining host drive capacity or breach the 10 GB user notification threshold without consent.
- **Adversarial Scenario**: Host machine has constrained SSD headroom (e.g., 11.4 GB available).
- **Code Inspection & Defense**:
  - In `downloader.py`: `check_disk_safety` is called prior to opening network sockets.
  - `DISK_LARGE_DOWNLOAD_THRESHOLD_GB = 10.0` and `DISK_FREE_MIN_GB = 5.0` are strictly enforced.
  - For payloads $> 10$ GB, downloads are aborted unless `allow_large_downloads=True` is explicitly supplied.
  - Files are staged in temporary `.part` files and only promoted to their final path upon passing full SHA-256 validation.
  - Verified in `test_10gb_user_notification_limit_trigger` and `test_preflight_disk_check_blocks_over_10gb`.
- **Risk Assessment**: **LOW / RESOLVED**.

### Challenge 4: Weak Pseudo-Label Leakage from Master Reference Drawings
- **Assumption Challenged**: Weak pseudo-labels derived from vector extraction of the 99th Street PDF might contaminate validation or test splits, corrupting model evaluation metrics.
- **Adversarial Scenario**: A developer mixes the master reference drawing set into training/validation pipelines.
- **Code Inspection & Defense**:
  - `splitter.py` explicitly supports `quarantine_projects` and flags samples with `quarantine=True` and `is_pseudo_label=True`.
  - Quarantined samples are segregated into `quarantine.json` and barred from both `val_samples` and `test_samples`.
  - `assert_zero_leakage()` explicitly validates `quarantine_projs & val_projs == ∅` and `quarantine_projs & test_projs == ∅`.
  - Verified in `test_quarantined_projects_excluded_from_val_and_test`.
- **Risk Assessment**: **LOW / RESOLVED**.

---

## 4. Integrity Violation Audit

In accordance with strict system reviewer guidelines, an exhaustive forensic check was performed across all committed code and generated artifacts:

1. **Hardcoded Test Results**:
   - Source code was searched for static test assertions, mocking bypasses, or embedded dummy metrics.
   - Result: **CLEAN**. All tests run genuine computations against real geometries, image buffers, and data structures.
2. **Facade Implementations**:
   - `preparer.py`, `downloader.py`, `splitter.py`, and `qc.py` were checked for hollow stubs.
   - Result: **CLEAN**. All 4 modules implement full algorithmic pipelines totaling over 2,400 lines of functional code.
3. **Task Bypass or Shortcuts**:
   - Result: **CLEAN**. The implementation builds genuine vector rasterization, hole evacuation, aspect-ratio preservation, and project-isolated partitioning from scratch without external black-box dependencies.
4. **Fabricated Logs or Verification Artifacts**:
   - Result: **CLEAN**. Test execution logs were independently verified via live test runner invocation; visual QC samples were directly opened and inspected.
5. **Self-Certifying Work**:
   - Result: **CLEAN**. Independent review, test suite execution, and visual verification confirm 100% genuine results.

---

## 5. Review Conclusion

Milestone M2 has satisfied all technical, architectural, and ethical standards.
- Rule R2 compliance is verified: generic public dataset walls are strictly mapped to `Class 3 (Uncertain)`, preserving ground-truth integrity.
- Rasterization fidelity is verified: hole evacuation via `cv2.fillPoly` and Mode 'P' indexed PNG formatting function accurately.
- Visual QC pipeline is verified: composite triplets with diagnostic headers provide full visual transparency.
- Project-isolated partitioning is verified: zero data leakage is mathematically proven and enforced.
- Mandatory 95% CDs notice is prominently included in `drywall_detection/reports/M2_dataset_report.md`.
- Test suite passes with 100% success rate (28/28 tests passed).

**Final Verdict**: **APPROVE**. Milestone M2 is officially certified complete and ready for Milestone M3 (Vector PDF Processing) and Milestone M4 (Model Segmentation Training).
