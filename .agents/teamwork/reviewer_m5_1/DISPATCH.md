# Dispatch Assignment: reviewer_m5_1

## Role
M5 Classification & Schema Reviewer (`teamwork_reviewer`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\reviewer_m5_1\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\__init__.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\partition_schedule_mapping.approved.csv`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_classification.py`

## Scope of Review
1. Review `drywall_detection/classification/classifier.py` and `__init__.py`:
   - Verify deterministic 3-class classification logic: Drywall (#00C853), Non-Drywall (#D50000), Uncertain (#FFD600).
   - Verify two-layer defense-in-depth safety mechanism for Detail 1A CMU:
     - Ingestion Gate (`_load_and_validate_schedule`): raises `IntegrityViolationError` if any CSV attempts to mark 1A as Drywall.
     - Runtime Invariant (`ClassifiedWallPolygon.__post_init__` and `classify_walls`): unconditionally enforces Non-Drywall for Detail 1A.
   - Verify Tier 3 unassigned fallback: candidate walls failing spatial matching strictly fall back to `Uncertain`, `confidence=0.0`, `#FFD600` (zero hallucination).
   - Verify `ClassifiedWallPolygon` schema, RFC 7946 GeoJSON export (`to_geojson()`), and takeoff summary statistics.
2. Execute the test suite:
   - Run `pytest drywall_detection/tests/test_classification.py -v`
   - Run `pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_schedule.py drywall_detection/tests/test_classification.py -v`
3. Deliver a formal Review Report and `handoff.md` in your state folder with an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-09T12:23:01Z
You are reviewer_m5_1. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\reviewer_m5_1\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\reviewer_m5_1\`
Mandatory: Read `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` and `PROJECT.md` before starting work.
Review `drywall_detection/classification/classifier.py` and `__init__.py`, verify Detail 1A CMU safety veto, Tier 3 unassigned fallback, GeoJSON export, and run test suites:
`pytest drywall_detection/tests/test_classification.py -v`
Deliver your review report and handoff.md with an explicit verdict: APPROVE or REQUEST_CHANGES.
