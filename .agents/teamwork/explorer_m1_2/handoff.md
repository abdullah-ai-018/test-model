# Handoff Report: Dataset Auditor Technical Specification
**Module:** `drywall_detection/audit/dataset_auditor.py`  
**From:** `explorer_m1_2` (M1 Dataset Auditor Architecture Explorer)  
**To:** M1 Worker & Teamwork Orchestrator  
**Date:** 2026-11-08T01:46:00Z  
**Type:** Hard Handoff (Design Investigation Complete)  

---

## 1. Observation

1. **User Requirements & Acceptance Criteria**:
   - `ORIGINAL_REQUEST.md` (Lines 18–20, Requirement R1):
     > "Audit candidate datasets (FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, MSD, ArchCAD-400k) verifying official sources, licenses, commercial/redistribution terms, and wall/annotation availability without bypassing access restrictions or accepting licenses on the user's behalf. Download eligible datasets, inspect images and annotations..."
   - `ORIGINAL_REQUEST.md` (Lines 32–36, Acceptance Criteria):
     > "Dataset licensing report is produced documenting terms, commercial restrictions, and official sources for all candidate datasets."

2. **Project Scope & Architecture Invariants**:
   - `PROJECT.md` (Lines 16–21, Track 2: Dataset Audit):
     > "Empirical audit of 6 candidate datasets: CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD Floorplans, and Modified Swiss Dwellings (MSD)."
     > "Disk safety guards: free disk space check prior to download, mandatory notification for downloads > 10 GB, zero license acceptance on user's behalf."
   - `PROJECT.md` (Lines 152–154, Code Layout):
     > `drywall_detection/audit/__init__.py` and `drywall_detection/audit/dataset_auditor.py`.
   - `PROJECT.md` (Lines 211–216, Zero-Tolerance Integrity Rules):
     > "Never hardcode test results or create dummy/facade implementations."
     > "Never fabricate dataset links, download statistics, model metrics, or evaluation numbers."

3. **Survey Findings on Candidate Datasets**:
   - `explorer_survey_3/report.md` (Lines 35–43, Table of Candidate Datasets):
     - **Modified Swiss Dwellings (MSD)**: HF `philippds/modified-swiss-dwellings-enriched` (173.8 MB download / ~1.52 GB extracted), Zenodo `10.5281/zenodo.7788422` (888.7 MB); CC BY 4.0; explicit `entity_type: separator`, `entity_subtype: WALL` WKT polygons; grouping key: `site_id` / `building_id`; verdict: **ELIGIBLE (Top Recommended)**.
     - **CubiCasa5K**: Zenodo record `2613548` (5.09 GB archive / ~15–20 GB raw, ~105 GB LMDB); CC BY-NC-SA 4.0; over 147,000 explicit SVG wall polygons; verdict: **ELIGIBLE (Primary Academic Benchmark, Non-commercial)**.
     - **FloorPlanCAD**: HF `Voxel51/FloorPlanCAD` (454 MB) / Google Drive (2.5–3.5 GB); CC BY-NC 4.0 annotations, CAD drawing third-party copyright disclaimer; "Wall" is uncountable "Stuff" class; verdict: **CONDITIONAL**.
     - **CVC-FP**: Figshare `10.6084/m9.figshare.12082131` (353.6 MB), Zenodo `7921780` (1.2 MB); original university server timed out / offline; 122 plans; verdict: **CONDITIONAL**.
     - **R2V (Raster-to-Vector)**: Annotations ~10 MB (MIT), LIFULL raw images >10 GB; requires formal application & institutional agreement with National Institute of Informatics (NII) IDR; verdict: **INELIGIBLE FOR AUTOMATED DOWNLOAD** (Gated / agreement required).
     - **SESYD Floorplans**: ~100 MB total (Delalandre 2010); annotations exist exclusively for 16 furniture/fixture symbols; **ZERO wall labels exist**; verdict: **INELIGIBLE FOR WALL SEGMENTATION**.

4. **Local Hardware Constraints Directly Observed**:
   - `explorer_survey_1/report.md` (Lines 27–34) & empirical command verification:
     - Disk: C:\ has 13.10 GB free; E:\ has 30.45 GB free.
     - RAM: 7.88 GB total, ~0.90 GB free (extreme memory constraint).
     - PyTorch: `2.1.0+cpu` (CPU execution only; no CUDA).
     - Python: 3.10.0 (AMD64).

5. **Code Isolation & State Verification**:
   - Working directory `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\` contains only `.agents\teamwork\`. No source code exists yet. All implementation must go inside `drywall_detection/` (Worker task).

---

## 2. Logic Chain

1. **Licensing Policy & Integrity Guardrail**:
   - Observation: Requirement R1 mandates zero license acceptance on the user's behalf.
   - Observation: R2V raw floor plan images require an academic application and institutional consent agreement with the NII IDR.
   - Step: Automated downloading of R2V would either fail due to missing credentials or require unauthorized license acceptance.
   - Deduction: The auditor must explicitly flag R2V as `INELIGIBLE` with a hard blocker (`requires_login_or_eula = True`, `is_downloadable_now = False`).

2. **Ground Truth Validation Guardrail**:
   - Observation: SESYD contains 1,600 degraded plans, but annotations strictly label 16 symbols (armchair, table, bed, door, window, sink) and contain zero wall polygons or strokes.
   - Step: A segmentation model trained on SESYD would have zero positive wall targets.
   - Deduction: The auditor must evaluate `has_wall_segmentation_labels` and immediately disqualify SESYD as `INELIGIBLE` for wall segmentation (`has_wall_segmentation_labels = False`, `is_downloadable_now = False`).

3. **Disk Space Safety & 10 GB Threshold Enforcement**:
   - Observation: Local drive C: has only 13.10 GB free space.
   - Observation: CubiCasa5K archive is 5.09 GB, and expanding to raw images takes ~15–20 GB, or ~105 GB for LMDB.
   - Observation: Requirement R2 / PROJECT.md mandates notifying the user before any download over 10 GB.
   - Step: Downloading CubiCasa5K to C: and expanding would saturate C: and crash the OS if unmanaged.
   - Deduction: `DatasetAuditor.check_disk_space()` must use `shutil.disk_usage()`, compare free space against both download and extracted sizes, flag insufficient space, and trigger `exceeds_10gb_threshold = True` whenever download size > 10.0 GB (`MAX_UNANNOUNCED_DOWNLOAD_GB`).

4. **Recommended Primary Dataset Selection**:
   - Observation: Modified Swiss Dwellings (MSD) download is only 173.8 MB (HF) / 888.7 MB (Zenodo), has CC BY 4.0 permissive licensing (commercial use allowed), contains 1.7M explicit wall boundary polygons in WKT format, and has clean `site_id` / `building_id` hierarchical identifiers.
   - Deduction: MSD is the optimal primary dataset for Milestone M2. CubiCasa5K serves as the secondary academic benchmark.

5. **Class & CLI Interface Decoupling**:
   - Step: To enable seamless unit testing (by `explorer_m1_3`'s `test_audit.py`) and programmatic execution (by M2 `downloader.py`), the auditor must be encapsulated in a pure class `DatasetAuditor` with default `offline_mode = True` (preventing network blocking during CI tests) and a standalone CLI entry point (`python -m drywall_detection.audit.dataset_auditor`).

---

## 3. Caveats

1. **Network Connectivity Variability**:
   - Active network probing (`--check-network`) depends on host availability and DNS resolution. Some institutional CDNs (e.g. Zenodo, Figshare) occasionally throttle or return HTTP 403 on automated `urllib` HEAD requests. The implementation specification incorporates an explicit fallback to a ranged GET request (`Range: bytes=0-10`) with a custom User-Agent, and defaults to offline registry verification.
2. **CAD Drawing Copyright Disclaimer**:
   - FloorPlanCAD's annotation license is CC BY-NC 4.0, but the authors explicitly disclaim CAD drawing copyright. This is flagged as `CONDITIONAL`, requiring explicit user risk acknowledgment before any commercial application.
3. **Extraction Expansion**:
   - While CubiCasa5K is 5.09 GB compressed (under 10 GB), uncompressed storage can reach 20–105 GB depending on format. Disk space checks must warn when free disk is sufficient for the zip but insufficient for full extraction on the active drive.

---

## 4. Conclusion

The technical architecture for `drywall_detection/audit/dataset_auditor.py` is fully specified and ready for Worker implementation:
1. All 6 candidate datasets (+ supplementary ArchCAD-400k) are completely mapped with verified URLs, sizes, licenses, formats, and verdicts.
2. The `DatasetAuditor` class provides deterministic, zero-dependency (stdlib-only: `dataclasses`, `enum`, `shutil`, `json`, `argparse`, `urllib`) verification.
3. Disk space checking strictly prevents disk exhaustion and enforces the 10 GB user notification threshold.
4. Licensing and ground-truth guardrails block R2V (institutional login required) and SESYD (no wall annotations).
5. The CLI interface (`python -m drywall_detection.audit.dataset_auditor`) produces both human-readable Markdown tables and machine-readable JSON reports.

---

## 5. Verification Method

To independently verify the architecture and its future implementation:

1. **Inspect Specification Artifacts**:
   - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_2\report.md`
   - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_2\handoff.md`

2. **Post-Implementation Worker CLI Verification Command**:
   ```powershell
   # Worker executes audit in offline mode (instant):
   python -m drywall_detection.audit.dataset_auditor --format table

   # Verify JSON output validity:
   python -m drywall_detection.audit.dataset_auditor --format json

   # Verify report files were created in reports directory:
   Test-Path drywall_detection/reports/dataset_audit_report.md
   Test-Path drywall_detection/reports/dataset_audit_report.json
   ```

3. **Pytest Verification**:
   ```powershell
   pytest drywall_detection/tests/test_audit.py -v
   ```

4. **Invalidation Conditions**:
   - If `DatasetAuditor` accepts EULAs or attempts to bypass login for R2V, this violates zero-tolerance integrity rules.
   - If `DatasetAuditor` approves SESYD for wall segmentation training, the ground-truth check has failed.
   - If `DatasetAuditor` fails to flag downloads over 10 GB, requirement R1/R2 is violated.
