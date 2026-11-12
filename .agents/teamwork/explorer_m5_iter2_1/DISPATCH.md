# Dispatch Assignment: explorer_m5_iter2_1

## Role
M5 Safety Veto Remediation Explorer (`teamwork_explorer`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_1\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_challenger_m5_safety.py`

## Scope of Investigation
Challenger `challenger_m5_1` reported 5 vulnerabilities in Milestone M5 Iteration 1. Your task is to investigate and design the exact fix strategy for:
1. **VULN-M5-01 (CRITICAL)**: Detail 1A runtime invariant bypassed with unregistered drywall synonyms (`gyp bd`, `gyp board`, `gypsum board`, `dry wall`, `gyp`).
   - Examine `ClassifiedWallPolygon.__post_init__` and `DRYWALL_SYNONYMS`.
   - Formulate a fix strategy: Detail 1A (and detail 1A variations) must STRICTLY and ONLY be classified as `Non-Drywall` or `2`. If `matched_tag == "1A"` or `detail_number == "1A"`, ANY classification other than `Non-Drywall` (or numerical `2`) must be rejected with `IntegrityViolationError`, or expand the synonym list/classification check so that all drywall-like terms raise `IntegrityViolationError`.
2. **VULN-M5-02 (CRITICAL)**: Detail 1A runtime invariant bypassed via post-initialization field mutation (`poly.classification = 'Drywall'`).
   - Examine how `ClassifiedWallPolygon` is structured.
   - Formulate a fix strategy: Implement a `__setattr__` guard (or `frozen=True` dataclass, or custom property setters) so that any attempt to mutate `classification` to Drywall when `matched_tag` is 1A raises `IntegrityViolationError`.
3. Do NOT modify source code directly (you are read-only Explorer).
4. Deliver your investigation and proposed fix strategy in `handoff.md` in your state folder.


## 2026-11-09T13:15:27Z
You are explorer_m5_iter2_1. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_1\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_1\`
Mandatory: Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `challenger_m5_1/handoff.md`, `drywall_detection/classification/classifier.py`, and `drywall_detection/tests/test_challenger_m5_safety.py`.
Investigate fix strategy for VULN-M5-01 (Detail 1A synonym whitelist bypass) and VULN-M5-02 (Detail 1A post-init attribute mutation bypass).
Deliver your findings and recommended fix strategy in `handoff.md` in your state folder. You are read-only; do NOT modify source code.
