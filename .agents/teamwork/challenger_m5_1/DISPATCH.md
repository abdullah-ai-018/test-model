# Dispatch Assignment: challenger_m5_1

## Role
M5 Safety Veto & Schema Challenger (`teamwork_challenger`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\__init__.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\partition_schedule_mapping.approved.csv`

## Scope of Adversarial Verification
You are an adversarial challenger. You must write an empirical stress-test script (`drywall_detection/tests/test_challenger_m5_safety.py`) and execute it with pytest to stress-test:
1. Detail 1A CMU Safety Veto Attacks:
   - Attempt to bypass the Ingestion Gate with tampered CSVs (case variations: "drywall", "DRYWALL", "Gypsum Wallboard", "GWB", leading/trailing whitespace, UTF-8 BOM, zero-byte CSV, CSV omitting 1A row, CSV with corrupted headers). Verify that `DrywallClassifier` raises `IntegrityViolationError` or rejects the CSV.
   - Attempt to bypass the Runtime Invariant by directly instantiating `ClassifiedWallPolygon` with `tag="1A"` and `classification="Drywall"` or modifying its fields. Verify fatal `IntegrityViolationError`.
   - Verify that `DrywallClassifier.classify_walls()` unconditionally classifies Detail 1A as `Non-Drywall` (`#D50000`).
2. Tier 3 Unassigned Fallback Attacks:
   - Test candidate walls with missing tags, whitespace tags, unknown tags, empty strings, None, or invalid formats.
   - Verify strictly `Uncertain`, `confidence=0.0`, `#FFD600` (zero material hallucination).
3. GeoJSON Schema & Takeoff Stress:
   - Test RFC 7946 GeoJSON export with degenerate Shapely geometries (empty polygon, 0-area polygon, self-intersecting, MultiPolygon).
   - Test takeoff calculations with zero length, negative bounds, or large numbers.
4. Run the tests:
   `pytest drywall_detection/tests/test_challenger_m5_safety.py -v`
5. Deliver a formal Challenger Report and `handoff.md` in your state folder with an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-09T12:23:28Z
[Message] timestamp=2026-11-09T12:23:28Z sender=3cdc71fe-4915-41ee-8ce4-6e81878e6b7a priority=MESSAGE_PRIORITY_HIGH content=You are challenger_m5_1. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\`
Mandatory: Read `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` and `PROJECT.md` before starting work.
Write an empirical stress-test script (`drywall_detection/tests/test_challenger_m5_safety.py`) to adversarially probe Detail 1A CMU safety veto bypass attempts (tampered CSVs, case variations, whitespace, synonym injections), Tier 3 unassigned fallback (untagged geometry non-hallucination), and GeoJSON schema boundaries.
Execute: `pytest drywall_detection/tests/test_challenger_m5_safety.py -v`
Deliver your challenger report and handoff.md with an explicit verdict: APPROVE or REQUEST_CHANGES.
