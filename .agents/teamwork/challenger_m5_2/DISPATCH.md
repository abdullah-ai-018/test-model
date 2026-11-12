# Dispatch Assignment: challenger_m5_2

## Role
M5 Coordinate & Fusion Challenger (`teamwork_challenger`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_2\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\coords.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\router.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\fusion.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\annotate.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\sample_overlays\M5_annotated_sample_drawings.pdf`

## Scope of Adversarial Verification
You are an adversarial challenger. You must write an empirical stress-test script (`drywall_detection/tests/test_challenger_m5_fusion.py`) and execute it with pytest to stress-test:
1. Coordinate Transformation Precision:
   - Test `AffineTransformManager` across non-standard DPIs (72, 96, 144, 150, 200, 300, 600) and arbitrary page rotations (0°, 90°, 180°, 270°).
   - Assert roundtrip bijection precision on points, bounding boxes, polygon vertices, and complex geometries (drift must be $< 10^{-10}$ pt).
   - Test edge cases: points at boundary extremes (0,0), (1728, 2592), negative coordinates, floating point coordinates.
2. Hybrid Fusion Invariants & Conflicts:
   - Test conflicting ML probability vs vector schedule tag: verify vector schedule strictly dominates ML predictions.
   - Test conflicting ML predicting high drywall confidence for Detail 1A CMU wall: verify Detail 1A CMU veto unconditionally overrides ML.
   - Test degenerate ML segmentation masks (all zeros, all ones, all NaNs, dimension mismatches).
   - Test `ModalityRouter` on edge cases (empty text, zero vector paths, raster-only pages).
3. Native Vector PDF Overlay Preservation:
   - Inspect `drywall_detection/reports/sample_overlays/M5_annotated_sample_drawings.pdf` using PyMuPDF:
     - Verify native vector linework and content streams are preserved (not rasterized to a bitmap image).
     - Verify text remains searchable across pages.
     - Verify Shape annotations are valid vector path operators with proper opacity (`fill_opacity=0.40`).
4. Run the tests:
   `pytest drywall_detection/tests/test_challenger_m5_fusion.py -v`
5. Deliver a formal Challenger Report and `handoff.md` in your state folder with an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-09T12:23:37Z
You are challenger_m5_2. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_2\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_2\`
Mandatory: Read `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` and `PROJECT.md` before starting work.
Write an empirical stress-test script (`drywall_detection/tests/test_challenger_m5_fusion.py`) to adversarially probe coordinate transforms under non-standard DPIs and arbitrary rotations (0°, 90°, 180°, 270°), hybrid fusion edge cases (conflicting ML/vector predictions, degenerate masks), and inspect vector PDF overlay preservation in `drywall_detection/reports/sample_overlays/M5_annotated_sample_drawings.pdf` (vector linework, fonts, searchable text).
Execute: `pytest drywall_detection/tests/test_challenger_m5_fusion.py -v`
Deliver your challenger report and handoff.md with an explicit verdict: APPROVE or REQUEST_CHANGES.
