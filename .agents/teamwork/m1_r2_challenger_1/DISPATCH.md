# Task Assignment: Milestone M1 Iteration 2 Challenger 1 (Hard Negative Quota Stress)

- **Assigned Agent**: `m1_r2_challenger_1` (`teamwork_challenger`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Challenger)
- **Date**: 2026-11-08

---

## 1. Scope & Adversarial Objectives

Empirically challenge and stress-test `SlidingWindowTiler.tile_drawing()` in `drywall_detection/datasets/unified_format.py`:
1. **Adversarial Reproduction of Previous Failure**:
   - Construct a 2000x2000 image with 1 wall tile and 24 non-blank linework tiles (grid lines every 100 px).
   - Run `tile_drawing()` with `max_hard_negative_ratio=0.15`.
   - Verify that the retained hard negative count is $\le 1$ ($50.0\%$ ratio bound on 1-wall drawing), proving that the 96% ratio defect is permanently eliminated.
2. **Stress Scenarios**:
   - Multi-wall drawings with dense linework (e.g. 50 wall tiles, 200 linework tiles) across varying ratios (0.0, 0.05, 0.15, 0.30, 0.50).
   - Zero-wall drawings with pure linework (general notes, schedules) -> verify 0 hard negatives retained.
   - Extreme aspect ratios and boundary conditions (e.g. 512x4000, 4000x512).
   - Deterministic variance ranking: verify highest linework variance tiles are always selected first.
3. Document empirical findings and deliver `handoff.md` with explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-08T03:47:57Z
You are assigned as m1_r2_challenger_1 (M1 R2 Hard Negative Quota Stress Challenger).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\handoff.md

Empirically stress-test SlidingWindowTiler.tile_drawing in drywall_detection/datasets/unified_format.py:
- Adversarially reproduce the previous 2000x2000 test with 1 wall tile and 24 linework tiles. Verify hard negative count <= 1 and ratio <= 50%, proving the 96% ratio defect is permanently eliminated.
- Test zero-wall drawings with pure linework (verify 0 tiles retained).
- Test varying quotas and extreme aspect ratios.
- Deliver your empirical report and verdict (APPROVE or REQUEST_CHANGES) in handoff.md.
