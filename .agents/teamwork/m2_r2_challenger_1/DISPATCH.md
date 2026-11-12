# Task Assignment: Milestone M2 Challenger 1 (Geometry, Rotation & Spatial Matcher Adversarial Stress)

- **Assigned Agent**: `m2_r2_challenger_1` (`teamwork_challenger`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_1`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Date**: 2026-11-08

## 1. Required Reading
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Verbatim user requirements)
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Architecture, contracts, zero-tolerance rules)
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md` (Worker implementation report)

## 2. Adversarial Testing Mission
Empirically stress-test the vector extraction engine and spatial matching pipeline:
1. **Coordinate & Rotation Stress**:
   - Test extreme corner coordinates ($[0, 0]$, $[1728, 2592]$) at various DPI resolutions (72, 150, 300, 600).
   - Test sub-pixel floating point roundtrip precision ($M$ and $M^{-1}$).
2. **Linework & Parallel Pairing Stress**:
   - Test scaling with 1,000+ synthetic parallel lines to ensure sweep-line $O(N \log N)$ optimization avoids timeouts.
   - Test degenerate collinear lines, zero-length paths, and extreme thickness thresholds ($< 1.5$ pt and $> 10.5$ pt).
3. **Spatial Matcher Stress**:
   - Test dense tag clusters pointing to adjacent parallel walls.
   - Test ambiguous equidistant proximity buffers (confirming 8 pt delta disambiguation enforces unassigned fallback).
   - Test leader lines terminating far outside geometry, crossing orthogonal lines, and zero-length leaders.
4. Run:
   `python -m pytest drywall_detection/tests/test_vector.py drywall_detection/tests/test_vector_adversarial_stress.py -v`
5. Write `handoff.md` in your state folder with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`. Include concrete empirical findings and test output.
6. Send a message to the orchestrator with your verdict.


## 2026-11-08T11:36:27Z
You are m2_r2_challenger_1 (Milestone M2 Geometry, Rotation & Spatial Matcher Challenger).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_1

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_1\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md

Adversarially challenge drywall_detection/vector/extractor.py and spatial_matcher.py.
Run the test commands:
python -m pytest drywall_detection/tests/test_vector.py drywall_detection/tests/test_vector_adversarial_stress.py -v
Stress test extreme coordinate limits, 90° CW rotation floating point precision, sweep-line parallel wall pairing scaling with 1,000+ lines, dense tag clusters, ambiguous equidistant proximity buffers, and degenerate leader lines.
Author handoff.md with an explicit verdict (APPROVE or REQUEST_CHANGES) and send a message to the orchestrator.
