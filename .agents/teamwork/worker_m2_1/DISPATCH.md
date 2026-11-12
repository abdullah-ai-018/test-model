## 2026-11-08T03:36:46Z
You are worker_m2_1 (M2 Implementation Worker).
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m2_1
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model

Read these files first before starting work:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read before starting work)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_1\analysis.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_1\handoff.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_2\analysis.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_2\handoff.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_3\analysis.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Ownership:
You exclusively own:
- `drywall_detection/data/downloader.py`
- `drywall_detection/data/preparer.py`
- `drywall_detection/data/splitter.py`
- `drywall_detection/data/qc.py`
- `drywall_detection/data/__init__.py`
- `drywall_detection/tests/test_data.py`
- `drywall_detection/reports/M2_dataset_report.md`
DO NOT modify files outside `drywall_detection/data/`, `drywall_detection/tests/test_data.py`, `drywall_detection/reports/`, and your state folder.

Your Mission:
Implement all components for Milestone M2 (Dataset Preparation) using the verified architectural blueprints from the Explorer triad:
1. `drywall_detection/data/downloader.py`:
   - Implement `MSDDownloader` and CLI targeting Modified Swiss Dwellings on Hugging Face (`philippds/modified-swiss-dwellings-enriched`).
   - Include pre-flight disk safety headroom validation using `drywall_detection.utils.hardware.check_disk_safety` and 10 GB limit check.
   - Include streaming download to `.part`, atomic promotion, authoritative SHA-256 validation from catalog, resumable HTTP range requests, and exponential backoff retry logic.
2. `drywall_detection/data/preparer.py`:
   - Implement `MSDAnnotationParser`, `GeometryRasterizer`, `DrawingSanitizer`, `DatasetPreparer`, and CLI.
   - Retain re-exports of `DrawingSplitManager`, `SplitManifest`, `TileRecord`, `verify_split_isolation`, etc. for 100% backward compatibility with existing tests.
   - Parse WKT wall polygons (`entity_type='separator'`, `entity_subtype='WALL'`).
   - In accordance with Rule R2, map generic MSD walls to `Class 3 (Uncertain)` in semantic multiclass masks, and `Class 1 (Wall)` in binary masks.
   - Implement aspect-ratio preserving affine mapping with Y inversion, letterboxing, and `cv2.fillPoly` hole evacuation.
   - Implement 6-gate defensive sanitization (topology repair, area checks, deduplication, and <= 15% hard-negative capping).
3. `drywall_detection/data/splitter.py`:
   - Implement `ProjectDataSplitter` enforcing strict project/building isolation (`site_id` / `building_id`) across 70% Train, 15% Validation, and 15% Test partitions.
   - Assert mathematical zero-leakage invariant: `len(train_projs & val_projs) == 0`, `len(train_projs & test_projs) == 0`, `len(val_projs & test_projs) == 0`.
   - Export split manifests to `drywall_detection/data/splits/{train,val,test,splits_summary}.json`.
4. `drywall_detection/data/qc.py`:
   - Implement `VisualQCGenerator` and `VisualQCPipeline` generating horizontal composite triplets `[Original | Color Mask | Translucent Overlay (alpha=0.40)]` with diagnostic header banners saved to `drywall_detection/reports/qc_samples/`.
5. `drywall_detection/tests/test_data.py`:
   - Implement the comprehensive test suite covering 0% project leakage invariants, mask dimensions, discrete values {0, 1, 2, 3}, Mode 'P' roundtrips, visual QC rendering, and disk safety pre-flight checks.
6. `drywall_detection/reports/M2_dataset_report.md`:
   - Write the authoritative Milestone M2 report containing the mandatory 95% CDs notice, dataset statistics, split sizes, zero-leakage mathematical verification, and visual QC observations.
7. Run the tests and CLIs:
   - Run `python -m pytest drywall_detection/tests/test_data.py -v` (all tests must pass).
   - Run `python -m pytest drywall_detection/tests/ -v` (all 261+ tests must pass with 0 regressions).
   - Verify CLIs: `python -m drywall_detection.data.downloader --help`, `python -m drywall_detection.data.preparer --help`, `python -m drywall_detection.data.splitter --help`, `python -m drywall_detection.data.qc --help`.
8. Write `handoff.md` in your state folder and notify the orchestrator when complete.
