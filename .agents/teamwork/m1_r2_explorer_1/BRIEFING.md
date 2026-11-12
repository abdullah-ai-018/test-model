# BRIEFING — 2026-11-08T02:40:00Z

## Mission
Investigate the unenforced 15% hard negative quota in SlidingWindowTiler.tile_drawing() and formulate the exact fix strategy and algorithm.

## 🔒 My Identity
- Archetype: explorer
- Roles: Tiling & Hard Negative Quota Explorer
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Write only to own state folder (.agents/teamwork/m1_r2_explorer_1)
- Never place source code, tests, or data files in .agents/teamwork/
- Formulate fix strategy, algorithm, and mathematical formulation for worker agent
- Deliver findings in analysis.md and handoff.md, notify parent via send_message

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `DISPATCH.md`
  - `ORIGINAL_REQUEST.md`
  - `PROJECT.md`
  - `m1_reviewer_2/handoff.md`
  - `drywall_detection/datasets/unified_format.py` (lines 80-200, 395-655)
  - `drywall_detection/tests/unit/test_datasets.py` (lines 1-250)
  - `drywall_detection/tests/test_tiling_stitching_stress.py` (lines 105-140, 415-445)
- **Key findings**:
  - Confirmed root cause: `SlidingWindowTiler.tile_drawing()` immediately appends any non-blank tile to `results` without checking `max_hard_negative_ratio=0.15`.
  - Formulated two-phase partitioning algorithm: `wall_tiles` vs `candidate_hn` with `img_std`.
  - Mathematical cap formula: `max_hn = int(np.ceil(len(wall_tiles) * ratio / (1.0 - ratio)))` when `wall_tiles > 0`.
  - Addressed edge case `len(wall_tiles) == 0`: introduced `nominal_hard_negative_min: int = 0` in `UnifiedDatasetConfig`. Suppresses wall-less sheets by default while allowing callers/tests to set `nominal_hard_negative_min=1`.
  - Deterministic ranking: Sort candidates by `(-img_std, row_idx, col_idx)` to select highest information-density linework false positives with zero additional compute overhead.
  - Preserved canonical spatial raster-scan order in returned list.
- **Unexplored areas**:
  - None. Investigation complete.

## Key Decisions Made
- Completed technical analysis report: `analysis.md`.
- Completed formal 5-component handoff report: `handoff.md`.
- Ready to hand off to orchestrator and `m1_worker_1`.

## Artifact Index
- `BRIEFING.md` — persistent working memory
- `progress.md` — liveness heartbeat
- `analysis.md` — technical deep-dive and code specification
- `handoff.md` — 5-component hard handoff report
