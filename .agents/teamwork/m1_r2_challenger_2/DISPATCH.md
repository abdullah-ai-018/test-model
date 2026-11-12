# Task Assignment: Milestone M1 Iteration 2 Challenger 2 (Split Leakage Stress)

- **Assigned Agent**: `m1_r2_challenger_2` (`teamwork_challenger`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Challenger)
- **Date**: 2026-11-08

---

## 1. Scope & Adversarial Objectives

Empirically challenge and stress-test `verify_split_isolation()` in `drywall_detection/datasets/split_manager.py`:
1. **Quarantine Leakage Injection Attack**:
   - Create synthetic manifests with quarantined tiles and attempt to inject them into `val_tiles` and `test_tiles`.
   - Test injections by: tile ID overlap, project ID overlap, drawing ID overlap, image file path overlap, and mask file path overlap.
   - Test setting `quarantine=True` or `is_pseudo_label=True` on tiles inside `val_tiles` and `test_tiles`.
   - Verify that `verify_split_isolation()` raises `SplitLeakageError` in 100% of injection attempts.
2. **Windows Path Casing Attack**:
   - Test file path comparisons with differing casing (e.g. `C:\Data\Tile.png` vs `c:\data\tile.png`).
   - Verify `_canonical_path()` equates them and catches leakage.
3. **Extreme Distribution Stress**:
   - Test group partitioning under extreme power-law group distributions (e.g. 1000:1 tile counts) to ensure no crash or leakage.
4. Document empirical findings and deliver `handoff.md` with explicit verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-11-08T03:47:57Z
You are assigned as m1_r2_challenger_2 (M1 R2 Split Leakage Stress Challenger).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_2

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_2\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\handoff.md

Empirically stress-test verify_split_isolation in drywall_detection/datasets/split_manager.py:
- Inject synthetic quarantined tiles, pseudo-labeled tiles, and case-mismatched Windows paths into val_tiles and test_tiles.
- Verify SplitLeakageError is raised in 100% of adversarial injection attempts.
- Test extreme group distributions (power law, 1000:1 ratio).
- Deliver your empirical report and verdict (APPROVE or REQUEST_CHANGES) in handoff.md.
