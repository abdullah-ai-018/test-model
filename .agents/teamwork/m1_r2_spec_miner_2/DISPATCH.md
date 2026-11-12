# Dispatch: m1_r2_spec_miner_2

- **Role**: Tiling & Filtering Specification Miner
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Reviewer Failure Report to Fix**:
  `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md`

## Problem to Investigate & Plan Fix Strategy
Reviewer `m1_reviewer_2` flagged that `SlidingWindowTiler.tile_drawing()` does not cap hard negative tiles at 15% quota (`max_hard_negative_ratio = 0.15`).
Additionally, `m1_challenger_1` recommended:
- Standalone `verify_split_isolation()` should explicitly validate that `manifest.quarantine_tiles` does not overlap with `val_tiles` or `test_tiles`.
- `validate_mask_array()` convenience function should be exported in `unified_format.py`.

Your tasks:
1. Mine the exact functional and API contracts for `SlidingWindowTiler.tile_drawing()`, `verify_split_isolation()`, and `validate_mask_array()`.
2. Detail the exact method signatures, docstrings, typing, and deterministic tile selection algorithm for hard negatives (e.g. sorting candidate hard negatives by linework variance descending to retain the most informative hard negatives, then capping at quota).
3. Do NOT implement the code yourself (Spec Miner archetype). Formulate the technical specification in `analysis.md` and `handoff.md`.
4. Notify orchestrator via send_message when done.


## 2026-11-07T21:27:15Z
[Message] timestamp=2026-11-07T21:27:15Z sender=3c1a82ae-9b50-494e-b173-0369a8d4a486 priority=MESSAGE_PRIORITY_HIGH content=You are m1_r2_spec_miner_2. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
And the Reviewer failure report: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md

Role: Tiling & Filtering Specification Miner
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2

Your task:
Mine and specify the functional contracts and deterministic selection algorithms for hard negative quota enforcement in SlidingWindowTiler, quarantine validation in verify_split_isolation(), and validate_mask_array().
Write analysis.md and handoff.md in your state folder.
Notify the orchestrator via send_message when done.
