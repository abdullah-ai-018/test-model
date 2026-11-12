# Task Assignment: Milestone M1 Iteration 2 Challenger 1 Replacement (Quota Stress)

- **Assigned Agent**: `m1_r2_challenger_1_rep` (`teamwork_challenger`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1_rep`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Challenger Replacement)
- **Date**: 2026-11-08

---

## 1. Context & Scope

Predecessor challenger `m1_r2_challenger_1` authored an exhaustive empirical adversarial stress suite in `drywall_detection/tests/test_quota_adversarial_stress.py` (610 lines) covering:
1. Reproduction of the 2000x2000 canvas with 1 wall tile and 24 linework tiles (verifying hard negatives $\le 1$ and ratio $\le 50.0\%$, eliminating the 96% ratio defect).
2. Multi-wall drawings with dense linework across varying quotas (0.0 to 1.0) and monotonicity.
3. Zero-wall drawings with pure linework (0 tiles retained for multi-tile sheet, 1 tile for single crop).
4. Extreme aspect ratios (512x4000 ribbon, 4000x512 column, 1000x4000 banner, 1234x2345 irregular).
5. Deterministic linework variance ranking (std descending) and canonical raster tie-breaking.
6. Multiclass mask wall detection and micro-walls.

Your tasks:
1. Inspect `drywall_detection/tests/test_quota_adversarial_stress.py`.
2. Run pytest on `drywall_detection/tests/test_quota_adversarial_stress.py` and the full regression test suite `python -m pytest drywall_detection/tests/ -v`.
3. Verify that 100% of stress tests pass with zero failures.
4. Author your empirical handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1_rep\handoff.md` with explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-08T04:21:35Z
You are assigned as m1_r2_challenger_1_rep (M1 R2 Quota Challenger Replacement).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1_rep

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_1_rep\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_quota_adversarial_stress.py

Predecessor m1_r2_challenger_1 authored the empirical stress test file in drywall_detection/tests/test_quota_adversarial_stress.py (610 lines).
Your tasks:
1. Run pytest on drywall_detection/tests/test_quota_adversarial_stress.py -v.
2. Run full regression test suite python -m pytest drywall_detection/tests/ -v.
3. Verify that the 2000x2000 adversarial reproduction passes (hard negatives <= 1, ratio <= 50%, 96% defect eliminated), zero-wall sheets retain 0 tiles, and all extreme aspect ratios pass.
4. Record your progress in progress.md and author your empirical handoff report in handoff.md with verdict APPROVE or REQUEST_CHANGES.
