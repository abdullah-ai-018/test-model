# Handoff Report: M2 Project-Isolated Data Partitioning, Visual QC & Test Suite

**Agent ID:** explorer_m2_3 (M2 Data Splitter & QC Explorer)  
**Recipient:** Orchestrator (Conversation ID: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`)  
**Date:** 2026-11-07  
**Artifact:** `.agents/teamwork/explorer_m2_3/analysis.md`  

---

## 1. Observation

1. **Foundational Directives & Rules (`PROJECT.md:152-170`, `config.py:123-176`)**:
   - `PROJECT.md` Section 6.2 enforces the strict project-level isolation invariant:
     $$\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset, \quad \mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset, \quad \mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$$
   - `config.py` lines 139-176 specify the authoritative 4-class semantic taxonomy: Background (0, White), Drywall (1, Green `#00C853`), Non-Drywall (2, Red `#D50000`), Uncertain (3, Yellow `#FFD600`).
   - `config.py` lines 123-134 specify `DISK_FREE_MIN_GB = 5.0` and `DISK_LARGE_DOWNLOAD_THRESHOLD_GB = 10.0`.
   - `config.py` line 175 sets `DEFAULT_OVERLAY_ALPHA = 0.40`.

2. **Current Codebase State & Regression Baseline (`drywall_detection/`)**:
   - `drywall_detection/data/` contains `preparer.py` and `dataset_licensing_audit.json`.
   - Neither `drywall_detection/data/splitter.py`, `drywall_detection/data/qc.py`, nor `drywall_detection/tests/test_data.py` currently exist on disk (`Test-Path` returned `False` for all three).
   - Test suite execution via `pytest drywall_detection/tests/ -v` passed all 261 existing tests in 81.37s with zero failures:
     `================== 261 passed, 1 warning in 81.37s ==================`

3. **Peer Explorer Coordination (`explorer_m2_1/DISPATCH.md`, `explorer_m2_2/DISPATCH.md`)**:
   - `explorer_m2_1` is architecting `drywall_detection/data/downloader.py` targeting Modified Swiss Dwellings (MSD, CC BY 4.0, ~174 MB parquet, WKT separator/WALL polygons) with download destination `drywall_detection/data/raw/msd/`.
   - `explorer_m2_2` is architecting `drywall_detection/data/preparer.py` standardizing floor plan rasters and vector WKT/SVG into single-channel 8-bit indexed PNG masks (Mode 'P', uint8, values 0..3) with sliding-window tiling (512x512, 20% overlap, stride 410 px) into `drywall_detection/data/processed/`.

4. **Reference Progress Set Mandatory Citation (`ORIGINAL_REQUEST.md:21-29`, `config.py:59-64`)**:
   - `config.py:59-64`: `"MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728x2592 pt unrotated, 90 deg CW rotation, 'PROGRESS SET 95% CDs 10/02/2026'). Notice: This reference PDF represents a 95% CDs progress set, not an approved final construction document. Pages represent a single project and cannot prove cross-domain generalization."`

---

## 2. Logic Chain

1. **Preventing Architectural CAD Data Leakage (Observation 1 -> Component 1)**:
   - Because multi-story floor plans share vertical structural footprints, shear walls, and CAD drafting conventions across sheets, standard random partitioning allows identical building geometries into both train and test partitions.
   - Therefore, grouping must be enforced strictly by `project_id` (resolving `site_id`, `building_id`, or `parent_project_id`).
   - Using a greedy multi-way deficit-maximizing algorithm, groups are partitioned into 70% Train, 15% Validation, and 15% Independent Test partitions.
   - Zero-overlap invariants are mathematically asserted before manifest generation:
     `assert len(train_projs & val_projs) == 0`
     `assert len(train_projs & test_projs) == 0`
     `assert len(val_projs & test_projs) == 0`
   - Manifests are exported to `drywall_detection/data/splits/{train,val,test,splits_summary}.json`.

2. **Visual Inspection & Label Validation (Observation 1, 3 -> Component 2)**:
   - Automated datasets can contain alignment errors, boundary clipping, or inverted masks.
   - `VisualQCGenerator` and `VisualQCPipeline` in `drywall_detection/data/qc.py` generate horizontal composite triplets: `[Original Drawing | Color Mask | Translucent Overlay]` topped by a 40 px diagnostic header banner detailing sample ID, split, and class distribution percentages.
   - The overlay uses $\alpha = 0.40$ blending directly onto CAD linework, and outputs are saved to `drywall_detection/reports/qc_samples/` with an index catalog `qc_manifest.json`.

3. **Exhaustive Testing of Split Invariants & Disk Safety (Observations 1, 2 -> Component 3)**:
   - Because `test_data.py` does not yet exist, a comprehensive pytest test suite is designed in `drywall_detection/tests/test_data.py` covering:
     - Project-isolated splitting invariants (0% leakage, greedy ratios, determinism with seed, quarantine isolation).
     - Mask dimensions, uint8 2D arrays, discrete $\{0, 1, 2, 3\}$ values, and bounding box bounds.
     - Visual QC triplet rendering geometry, color mapping, and numerical alpha blending accuracy.
     - Disk safety pre-flight checks and 10 GB user notification threshold.

4. **Transparent Documentation & Compliance (Observation 4 -> Component 4)**:
   - `drywall_detection/reports/M2_dataset_report.md` requires the verbatim 95% CDs notice, empirical split statistics, zero-leakage mathematical proofs, and visual QC observations.
   - A complete, production-ready markdown structure is provided in `analysis.md`.

---

## 3. Caveats

1. **Processed Data Availability**:
   - `drywall_detection/data/processed/` is currently empty pending execution of `downloader.py` (by worker_m2_1) and `preparer.py` (by worker_m2_2). The splitter architecture and test suite design include robust synthetic generators and schema validators to enable immediate worker implementation and unit testing without blocking on external dataset download.
2. **Read-Only Explorer Constraint**:
   - In accordance with the Explorer archetype instructions, no source files were written into `drywall_detection/`. All blueprints, code templates, and test suites are documented in `.agents/teamwork/explorer_m2_3/analysis.md`.
3. **Single-Project Fallback Assumption**:
   - In datasets containing fewer than 3 distinct projects (e.g. if running exclusively on the 99th Street standalone set), the splitter provides a loud fallback to `drawing_id` (sheet level) when `allow_drawing_fallback=True`, but raises `InsufficientGroupsError` if fallback is disabled.

---

## 4. Conclusion

The architectural design for Milestone M2's data partitioning, visual quality control, test suite, and report template is complete, rigorous, and ready for worker implementation:
1. **Data Splitter (`drywall_detection/data/splitter.py`)**: Defines `ProjectDataSplitter`, `SampleRecord`, `SplitManifestBundle`, greedy 70/15/15 group partitioning, mathematical zero-leakage assertions, and manifest exports to `drywall_detection/data/splits/{train,val,test,splits_summary}.json`.
2. **Visual QC (`drywall_detection/data/qc.py`)**: Defines `VisualQCGenerator` and `VisualQCPipeline` producing `[Original | Color Mask | Translucent Overlay (alpha=0.40)]` triplets with diagnostic header banners saved to `drywall_detection/reports/qc_samples/`.
3. **Test Suite (`drywall_detection/tests/test_data.py`)**: Designs comprehensive unit tests validating 0% project leakage, mask bounds and values, Mode 'P' round-trips, visual QC geometries, and disk safety pre-flight checks.
4. **Report Structure (`drywall_detection/reports/M2_dataset_report.md`)**: Fully outlines the report template embedding the mandatory 95% CDs notice, split distribution tables, zero-leakage proofs, and visual QC findings.

---

## 5. Verification Method

To independently verify the architecture and its downstream implementation:
1. **Inspect Blueprint File**:
   - Read `.agents/teamwork/explorer_m2_3/analysis.md` for complete code blueprints, class signatures, algorithms, and test designs.
2. **Worker Implementation Verification**:
   - After the implementation worker creates `drywall_detection/data/splitter.py`, `drywall_detection/data/qc.py`, and `drywall_detection/tests/test_data.py`, execute:
     ```powershell
     pytest drywall_detection/tests/test_data.py -v
     ```
   - Invalidation conditions: Any test failure in `test_data.py`, any non-empty intersection between `train`, `val`, and `test` project IDs, or any mask value outside $\{0, 1, 2, 3\}$.
3. **Regression Verification**:
   - Execute the entire project test suite:
     ```powershell
     pytest drywall_detection/tests/ -v
     ```
   - Invalidation conditions: Any failure among the existing 261 passing unit tests.
