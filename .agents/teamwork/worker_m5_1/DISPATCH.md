## 2026-11-09T10:14:29Z
You are worker_m5_1 (Milestone M5 Implementation Worker).

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_1\
Original request path: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

## Reference Architectures & Explorer Handoffs (READ ALL BEFORE CODING)
- Explorer 1 (Classification Engine): c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_1\handoff.md
- Explorer 2 (Fusion & Visualization): c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_2\handoff.md
- Explorer 3 (Ground Truth & Benchmark): c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_3\handoff.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Detail 1A CMU Non-Drywall Rule
Detail 1A on Sheet A-900 (Page 62/63) is explicitly 6" FIRE RATED CMU masonry block. It MUST be classified as Non-Drywall (Red, #D50000) and NEVER Drywall. Enforce defense-in-depth: if any approved CSV or caller attempts to classify 1A as Drywall, raise an immediate fatal IntegrityViolationError.

## Mandatory 95% CDs Progress Set Notice
Include prominently in reports and user outputs that the 99th Street PDF (MTA Contract C-48526) is a "PROGRESS SET 95% CDs 10/02/2026" interim design set, representing a single project calibration sample that cannot prove generalization.

## Exclusive Write Ownership
You exclusively own and must implement the following files:
1. `drywall_detection/classification/__init__.py`: Package exports for classification.
2. `drywall_detection/classification/classifier.py`: `DrywallClassifier`, `ClassifiedWallPolygon`, `ClassificationSummary`, `ClassificationFeatureCollection`, approved CSV validation, two-layer Detail 1A CMU veto, Tier 3 unassigned zero-hallucination fallback, and RFC 7946 GeoJSON export.
3. `drywall_detection/utils/coords.py`: Extend with `AffineTransformManager` (exact bijection under 90° CW rotation for points, bboxes, arrays, and Shapely geometries).
4. `drywall_detection/pipeline/__init__.py`: Exports for pipeline components.
5. `drywall_detection/pipeline/router.py`: `ModalityRouter` (automatic vector presence detection vs raster ML fallback).
6. `drywall_detection/pipeline/fusion.py`: `HybridFusionPipeline` (schedule authority, confidence cross-validation, ML advisory for unassigned partitions).
7. `drywall_detection/pipeline/annotate.py`: `WallAnnotator` (pure vector PDF overlays via PyMuPDF Shape primitives + high-res raster PNG overlays with legend card and linear/square feet takeoff summary).
8. `drywall_detection/tests/test_classification.py`: Complete test suite covering approved CSV loading, Detail 1A CMU safety veto, GeoJSON schema, hybrid router/fusion, 10 human-review benchmark regions (R01-R10), and visual overlay generator.
9. `drywall_detection/reports/M5_classification_report.md`: Formal Milestone M5 report following the 10-section blueprint in Explorer 3's handoff.

## Implementation Tasks
1. Implement `drywall_detection/classification/classifier.py` and `__init__.py` per Explorer 1 handoff specifications.
2. Implement `drywall_detection/utils/coords.py` (`AffineTransformManager`), `drywall_detection/pipeline/router.py`, `fusion.py`, and `annotate.py` per Explorer 2 handoff specifications.
3. Implement `drywall_detection/tests/test_classification.py` per Explorer 3 handoff specifications.
4. Run `pytest drywall_detection/tests/test_classification.py -v` and all regression test suites (`test_coords.py`, `test_schedule.py`, `test_vector.py`, `test_models.py`, `test_training.py`). Ensure 100% pass rate.
5. Generate visual verification sample overlays (PNG and PDF) for at least 3 benchmark plan regions (e.g. R01, R02, R03) saving them in `drywall_detection/reports/sample_overlays/`.
6. Author the formal milestone report in `drywall_detection/reports/M5_classification_report.md` including the mandatory 95% CDs notice, 10 benchmark regions table, and 5 quantitative error verification metrics.
7. Write your handoff report to: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_1\handoff.md`.

When complete, send a message to the orchestrator with test results and handoff path.
