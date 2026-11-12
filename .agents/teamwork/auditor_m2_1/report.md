# Forensic Audit Report: Milestone M2 (Dataset Preparation)

**Document ID:** AUDIT-REPORT-M2-01  
**Auditor:** auditor_m2_1 (M2 Forensic Auditor)  
**Date:** 2026-11-08  
**Profile:** General Project (Forensic Integrity)  
**Target Work Product:** Milestone M2 Implementation (`drywall_detection/data/`, `drywall_detection/tests/test_data.py`, `drywall_detection/reports/M2_dataset_report.md`)  
**Integrity Mode:** Development (with Demo/Benchmark checks executed)  
**Verdict:** **CLEAN**

---

## 1. Executive Summary

A comprehensive forensic audit of Milestone M2 (Dataset Preparation) was conducted with zero trust. Every claim, code component, test assertion, licensing term, ground-truth label mapping, and documentation artifact was independently verified.

All 6 core forensic dimensions passed without integrity violations:
1. **Cheating & Facade Audit**: PASS — All modules contain genuine mathematical, geometrical, and algorithmic implementations. Zero mock facades, stub returns, or hardcoded test expectations detected.
2. **Test Suite Authenticity**: PASS — `test_data.py` comprises 28 rigorous unit tests asserting mathematical invariants, geometry transformations, hole evacuations, and isolation properties.
3. **Licensing & Access Compliance**: PASS — Zero EULAs or click-through agreements accepted on the user's behalf. Preflight disk checks enforce the 10 GB notification threshold. Modified Swiss Dwellings confirmed to be CC BY 4.0.
4. **Ground-Truth Integrity (Rule R2)**: PASS — Ingested generic public dataset walls default strictly to `CLASS_UNCERTAIN` (Class 3, Yellow). Generic walls are never falsely marked as Drywall (Class 1).
5. **Progress Set Notice Audit**: PASS — `M2_dataset_report.md` prominently features the mandatory 95% CDs progress set notice in Section 1.
6. **Empirical Execution Validation**: PASS — 28/28 tests passed in `test_data.py` (96.18s); 389/389 tests passed across the full test suite (215.82s) with zero regressions.

---

## 2. Forensic Phase Results

### Phase 1: Source Code & Implementation Analysis

| Check Name | Target Module | Status | Forensic Evidence & Details |
|---|---|:---:|---|
| **Hardcoded Test Results** | All M2 files | **PASS** | Source code searched for hardcoded return values, expected output tables, or test mock bypasses. None found. |
| **Facade Implementation Detection** | `downloader.py` | **PASS** | Genuine resumable HTTP downloading using `urllib.request`, Range header slicing (`bytes={offset}-`), exponential backoff retry loop with randomized jitter, streaming chunk SHA-256 calculation (`compute_file_sha256`), and atomic `.part` file promotion. |
| **Facade Implementation Detection** | `preparer.py` | **PASS** | Genuine affine coordinate transformation ($px, py$ with aspect ratio preservation and padding), sub-pixel polygon rasterization, interior hole evacuation via OpenCV `cv2.fillPoly`, `shapely.make_valid` topology repair, area filtering, and PIL Mode 'P' 256-color palette indexing. |
| **Facade Implementation Detection** | `splitter.py` | **PASS** | Genuine multi-way deficit-maximizing greedy group partitioning, dynamic fallback to `drawing_id` when project counts are limited, and deterministic SHA-256 manifest hashing. |
| **Facade Implementation Detection** | `qc.py` | **PASS** | Genuine horizontal triplet assembly (`[Original | Color Mask | Translucent Overlay]`), alpha blending via `cv2.addWeighted`, and 40 px diagnostic header banner rendering. |
| **Backward Compatibility Re-exports** | `preparer.py` | **PASS** | Re-exports all legacy classes (`DrawingSplitManager`, `SplitManifest`, `TileRecord`, `verify_split_isolation`, etc.) ensuring 100% backward compatibility for M1 unit tests. |

### Phase 2: Test Suite Authenticity Analysis

| Check Name | Target Test File | Status | Forensic Evidence & Details |
|---|---|:---:|---|
| **Trivial Assertion Check** | `test_data.py` | **PASS** | No tautological tests (`assert True`, `assert 1 == 1`, dummy passes). Every test asserts substantive state changes or invariants. |
| **Mathematical Invariant Verification** | `TestProjectIsolatedSplitting` | **PASS** | Genuinely asserts disjoint sets across partitions ($\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset$, $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset$, $\mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$). Deliberate leakage injection test verifies that `SplitLeakageError` is raised immediately upon overlap. |
| **Geometry & Rasterization Invariants** | `TestGeometryRasterizerAndSanitizer` | **PASS** | Genuinely constructs a doughnut polygon with an interior hole and verifies that the center coordinate (100, 100) is evacuated to background class 0 while the perimeter is class 3. Verifies bowtie self-intersection repair. |
| **Numerical Blending Precision** | `TestVisualQCPipeline` | **PASS** | Asserts that overlay pixel values match the theoretical formula $(1 - \alpha) \cdot I + \alpha \cdot C_{\text{class}}$ within 1 intensity unit. |
| **Mode 'P' Indexed PNG Invariants** | `TestMaskDimensionsClassValuesAndBounds` | **PASS** | Verifies that saved 8-bit indexed PNG masks round-trip cleanly into PyTorch int64 tensors with discrete values $\{0, 1, 2, 3\}$. |

### Phase 3: Licensing, Access & Threshold Audit

| Check Name | Policy / Rule | Status | Forensic Evidence & Details |
|---|---|:---:|---|
| **EULA & License Acceptance** | Rule R1 / Anti-EULA | **PASS** | Zero automated acceptance of licenses, EULAs, or Terms of Service. Downloads use standard public HTTPS GET requests with generic User-Agent headers. |
| **10 GB Download Limit** | Safety Constraint | **PASS** | `preflight_disk_check` blocks payloads exceeding `DISK_LARGE_DOWNLOAD_THRESHOLD_GB` (10.0 GB) unless explicit user override (`--allow-large-downloads`) is passed. Full MSD payload is 355.41 MB (~0.35 GB), safely within limits. |
| **Disk Headroom Safety** | System Constraint | **PASS** | `check_disk_safety` verifies minimum 5.0 GB free headroom prior to download. Host volume has 11.42 GB free. |
| **MSD Licensing Validity** | License Verification | **PASS** | Modified Swiss Dwellings (MSD) confirmed to be released under Creative Commons Attribution 4.0 International (`CC BY 4.0`), allowing commercial reuse and modification with attribution. |

### Phase 4: Ground Truth Integrity (Rule R2)

| Check Name | Target Rule | Status | Forensic Evidence & Details |
|---|---|:---:|---|
| **Rule R2 Drywall Precedence** | Rule R2 | **PASS** | Generic public dataset walls (MSD) are strictly configured to `CLASS_UNCERTAIN` (Class 3, Yellow) in `preparer.py` (`default_wall_class = CLASS_UNCERTAIN`). No generic wall is falsely marked as Drywall (Class 1). |
| **Binary Structural Mode** | Rule R2 | **PASS** | In binary mode, walls are classified as `1` (Wall) solely for structural geometry pretraining without claiming drywall material identity. |
| **Pseudo-label Quarantine** | Rule R2 / M2 Guardrail | **PASS** | MTA 99th Street extractions are flagged with `quarantine = True` and segregated into `quarantine.json`, preventing contamination of validation or test sets. |

### Phase 5: Progress Set Notice Audit

| Check Name | Target File | Status | Forensic Evidence & Details |
|---|---|:---:|---|
| **95% CDs Interim Notice** | `M2_dataset_report.md` | **PASS** | Section 1 prominently features the mandatory notice: *"The reference PDF file-1793194362940-560626729.pdf represents MTA Contract C-48526... explicitly stamped 'PROGRESS SET 95% CDs 10/02/2026' and constitutes an interim construction design progress set... serving strictly as a single-project calibration sample."* |

---

## 3. Empirical Test Execution Log

### 3.1 M2 Test Suite Execution
```
Command: python -m pytest drywall_detection/tests/test_data.py -v
Output:
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
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

======================== 28 passed in 96.18s (0:01:36) ========================
```

### 3.2 Full Project Regression Execution
```
Command: python -m pytest drywall_detection/tests/ -v
Output:
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0
collected 389 items
...
================= 389 passed, 1 warning in 215.82s (0:03:35) ==================
```

---

## 4. Final Verdict

**FINAL FORENSIC VERDICT: CLEAN**

Milestone M2 (Dataset Preparation) demonstrates exemplary integrity, authentic implementation, robust zero-leakage mathematical guarantees, strict adherence to Rule R2 material classification, and zero regressions across the codebase.
The milestone is unconditionally **ACCEPTED**.
