# Dispatch: m1_r2_explorer_1

- **Role**: Tiling & Hard Negative Quota Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Reviewer Failure Report to Fix**:
  `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md`

## Problem to Investigate & Plan Fix Strategy
Reviewer `m1_reviewer_2` issued REQUEST_CHANGES because `SlidingWindowTiler.tile_drawing()` does not enforce the 15% hard negative retention quota (`max_hard_negative_ratio = 0.15`).
Currently, pure blank tiles are discarded, but 100% of hard negative tiles (linework without walls) are retained unconditionally, causing drawings with linework to produce up to 96% hard negative tiles.

Your tasks:
1. Read the reviewer failure report and inspect `drywall_detection/datasets/unified_format.py`.
2. Formulate a precise, robust fix strategy for `SlidingWindowTiler.tile_drawing()`:
   - How to partition generated tiles into wall tiles vs candidate hard negatives.
   - Exact mathematical cap formula: `max_hn = int(np.ceil(len(wall_tiles) * ratio / (1.0 - ratio)))` where `ratio = config.max_hard_negative_ratio`.
   - Handling edge case when `len(wall_tiles) == 0`.
   - Sampling or ordering criteria for retaining the best hard negatives (e.g. highest linework variance).
3. Do NOT implement the code yourself (Explorer archetype). Formulate the fix design in `analysis.md` and `handoff.md`.
4. Notify orchestrator via send_message when done.


## 2026-11-07T21:27:07Z
You are m1_r2_explorer_1. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
And the Reviewer failure report: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md

Role: Tiling & Hard Negative Quota Explorer
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1

Your task:
Investigate the unenforced 15% hard negative quota in SlidingWindowTiler.tile_drawing() and formulate the exact fix strategy and algorithm.
Write analysis.md and handoff.md in your state folder.
Notify the orchestrator via send_message when done.
