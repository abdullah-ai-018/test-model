# DISPATCH: Milestone M4 Data Leakage & Inference Challenger (challenger_m4_2)

**Timestamp**: 2026-11-09T07:25:00Z  
**Role**: `teamwork_challenger` (M4 Data Leakage & Inference Challenger)  
**Parent Orchestrator**: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**State Folder**: `.agents/teamwork/challenger_m4_2/`  
**Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Original Request Path**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`  
**Project Path**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`  

---

## Mission & Scope
Adversarially challenge data split invariants, pseudo-label quarantine, and inference edge cases:
- Test `assert_zero_leakage_manifests`:
  - Craft intentionally leaked manifests (shared projects, shared image paths, shared drawing IDs) and verify that `assert_zero_leakage_manifests` raises `AssertionError` with zero bypass.
- Test pseudo-label discount:
  - Verify that pseudo-labeled loss scaling ($\lambda = 0.35$) genuinely downweights gradients compared to supervised tiles.
  - Verify that 99th Street CAD tiles are strictly quarantined from `val.json` and `test.json`.
- Test standalone inferencer `infer.py`:
  - Test tiny inputs ($32 \times 32$), non-divisible dimensions ($733 \times 521$), huge images, pure noise images.
  - Check memory consumption during sliding-window stitching.

## Instructions
1. Read `ORIGINAL_REQUEST.md` and `PROJECT.md`.
2. Initialize `BRIEFING.md` and `progress.md` in your state folder.
3. Write dedicated stress test script(s) in `drywall_detection/tests/` (e.g. `test_challenger_m4_leakage_stress.py`).
4. Execute tests and report empirical results.
5. Issue an explicit verdict: `APPROVE` or `REQUEST_CHANGES`.
6. Write `handoff.md` and message the parent orchestrator with your verdict.


## 2026-11-09T07:24:28Z
[Message] timestamp=2026-11-09T07:24:28Z sender=3cdc71fe-4915-41ee-8ce4-6e81878e6b7a priority=MESSAGE_PRIORITY_HIGH content=You are challenger_m4_2 (M4 Data Leakage & Inference Challenger).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your dedicated state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m4_2\
Your dispatch assignment is located at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m4_2\DISPATCH.md
Original user request path: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
Parent conversation ID: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

Your task:
1. Read ORIGINAL_REQUEST.md and DISPATCH.md.
2. Initialize BRIEFING.md and progress.md in your state folder.
3. Stress test assert_zero_leakage_manifests with intentionally leaked/overlapping manifests (shared project IDs, shared file paths, corrupted manifests) to verify zero bypass.
4. Stress test pseudo-label discount weighting (lambda=0.35) and verify CAD tiles are strictly quarantined from validation and test splits.
5. Stress test standalone infer.py with tiny images (32x32), odd resolutions (733x521), large images, and pure noise.
6. Write a dedicated stress test script in drywall_detection/tests/ (e.g. test_challenger_m4_leakage_stress.py), run pytest, and evaluate results.
7. Issue an explicit verdict: APPROVE or REQUEST_CHANGES.
8. Write handoff.md in your state folder and message the parent orchestrator with your verdict.
