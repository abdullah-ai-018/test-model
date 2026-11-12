# Dispatch Assignment: explorer_m5_iter2_2

## Role
M5 Fallback and Exception Explorer (`teamwork_explorer`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_2\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\vector\spatial_matcher.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_challenger_m5_safety.py`

## Scope of Investigation
Challenger `challenger_m5_1` reported 5 vulnerabilities in Milestone M5 Iteration 1. Your task is to investigate and design the exact fix strategy for:
1. **VULN-M5-03 (HIGH)**: Whitespace-only tag (`tag="   "`) bypasses Tier 3 unassigned fallback.
   - In `classifier.py:294-374`, candidate walls with whitespace tags are treated as matched to `""` with `confidence=0.30` and `matched_tag=""`.
   - Investigate how `classify_walls` inspects `match_res.assigned_tag`. Design the fix: `if match_res is not None and match_res.assigned_tag and match_res.assigned_tag.strip():` so that empty/whitespace tags strictly fall back to Tier 3 unassigned fallback (`confidence=0.0`, `matched_tag=None`, `classification="Uncertain"`).
2. **VULN-M5-04 (HIGH)**: `SpatialMatcher._resolve_classification` crashes with `AttributeError: 'NoneType' object has no attribute 'upper'` when a tag has `tag_id = None` or `tag = None`.
   - In `spatial_matcher.py:145-147` and `298`, inspect where `tag_name` is processed. Design the fix: ensure robust null-checking (`if not tag_name: return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])`).
3. Do NOT modify source code directly (you are read-only Explorer).
4. Deliver your investigation and proposed fix strategy in `handoff.md` in your state folder.


## 2026-11-09T13:15:36Z
You are explorer_m5_iter2_2. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_2\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_iter2_2\`
Mandatory: Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `challenger_m5_1/handoff.md`, `drywall_detection/classification/classifier.py`, `drywall_detection/vector/spatial_matcher.py`, and `drywall_detection/tests/test_challenger_m5_safety.py`.
Investigate fix strategy for VULN-M5-03 (whitespace tags bypassing Tier 3 unassigned fallback) and VULN-M5-04 (SpatialMatcher crashing on None tag with AttributeError).
Deliver your findings and recommended fix strategy in `handoff.md` in your state folder. You are read-only; do NOT modify source code.
