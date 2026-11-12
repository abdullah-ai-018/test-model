# Dispatch Assignment: challenger_m5_iter2_2

## Role
M5 Fusion & Coordinate Challenger (`teamwork_challenger`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_iter2_2\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\coords.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\router.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\fusion.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\annotate.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\sample_overlays\M5_annotated_sample_drawings.pdf`

## Scope of Adversarial Verification
You are an adversarial challenger.
1. Write and run an empirical fusion/coordinate stress test (e.g. `drywall_detection/tests/test_challenger_m5_fusion.py`):
   - Adversarially probe coordinate transforms under non-standard DPIs and arbitrary rotations (0°, 90°, 180°, 270°). Verify $< 10^{-10}$ pt drift.
   - Probe hybrid fusion invariants: conflicting ML probability vs vector schedule tag (verify schedule strictly dominates), conflicting Detail 1A ML prediction (verify CMU veto unconditionally overrides ML), degenerate or empty mask inputs.
   - Inspect vector PDF overlay preservation in `drywall_detection/reports/sample_overlays/M5_annotated_sample_drawings.pdf` using PyMuPDF to assert that native vector streams, fonts, and searchable text are preserved without rasterization.
2. Run your tests with `pytest drywall_detection/tests/test_challenger_m5_fusion.py -v`.
3. Deliver a formal Challenger Report and `handoff.md` in your state folder with an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-09T17:16:07Z
You are challenger_m5_iter2_2. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_iter2_2\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_iter2_2\`
Mandatory: Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `worker_m5_iter2/handoff.md`, `coords.py`, `fusion.py`, `router.py`, `annotate.py`, and `M5_annotated_sample_drawings.pdf`.
Write and execute an empirical fusion/coordinate stress test (`test_challenger_m5_fusion.py`):
- Probe coordinate transforms across non-standard DPIs and arbitrary rotations (0°, 90°, 180°, 270°), asserting drift < 1e-10 pt.
- Probe hybrid fusion invariants: conflicting ML probability vs vector schedule tag, Detail 1A CMU veto override, degenerate mask inputs.
- Inspect `M5_annotated_sample_drawings.pdf` via PyMuPDF (zero rasterized pages, 100% searchable text, native Shape operators).
Execute: `pytest drywall_detection/tests/test_challenger_m5_fusion.py -v`.
Deliver your challenger report and handoff.md with an explicit verdict: APPROVE or REQUEST_CHANGES.
