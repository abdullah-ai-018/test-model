# BRIEFING — 2026-11-08T02:30:00Z

## Mission
Mine and author authoritative technical specifications, API contracts, mathematical selection algorithms, and edge cases for hard negative quota enforcement in SlidingWindowTiler, quarantine validation in verify_split_isolation, and the standalone validate_mask_array convenience function.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Tiling & Filtering Specification Miner
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)

## 🔒 Key Constraints
- Read-only: Do NOT implement or modify project code (reserved for workers).
- Do NOT skip any feature or edge case, no matter how obscure.
- Prioritize authoritative sources over LLM prior knowledge; verify behavior directly against codebase and tests.
- Produce fully specified functional contracts, signatures, mathematical formulas, and deterministic selection algorithms.
- Deliver findings in analysis.md and hard handoff in handoff.md; notify orchestrator via send_message.

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: not yet

## Task Summary
- **What to build**: Comprehensive functional contracts and deterministic selection specifications for:
  1. `SlidingWindowTiler.tile_drawing()` hard negative quota enforcement ($\le 15\%$).
  2. `verify_split_isolation()` standalone quarantine validation against val/test sets.
  3. `validate_mask_array()` standalone convenience function exported in `unified_format.py` and `datasets/__init__.py`.
- **Success criteria**:
  - Full API signatures, types, docstrings, mathematical formulas, invariants, and edge cases specified.
  - Deterministic selection algorithm specified (sorting by linework variance descending to prioritize informative text/linework tiles, deterministic tie-breaking by coordinates/tile_id).
  - Quarantined tile isolation verified to eliminate pseudo-label leakage into val/test.
  - Complete error conditions and validation invariants documented.
- **Interface contracts**: `PROJECT.md`, `m1_reviewer_2/handoff.md`, `m1_challenger_1/handoff.md`.
- **Code layout**: `drywall_detection/datasets/unified_format.py`, `drywall_detection/datasets/split_manager.py`.

## Key Decisions Made
- Mathematical quota formula: For drawing with $N_{wall}$ wall tiles and quota ratio $r = \text{max\_hard\_negative\_ratio}$, the maximum hard negatives allowed is $N_{hn} = \lfloor \frac{r}{1 - r} \cdot N_{wall} \rfloor$ (or ceiling depending on minimum policy). We will rigorously specify both floor/ceil trade-offs and define the exact bound such that $\frac{N_{hn}}{N_{wall} + N_{hn}} \le r$.
- Zero wall drawings ($N_{wall} = 0$): When a drawing contains zero wall tiles, if it is a pure hard negative crop / detail sheet, retaining hard negatives must be specified with deterministic handling (e.g., if $N_{wall} == 0$, if drawing has no walls, retain 0 if strict quota is applied, or if drawing is tested as a single tile or explicitly negative sheet, define behavior clearly to maintain consistency with `test_tile_filtering_blank_and_hard_neg`).
- Deterministic selection: Candidate hard negatives sorted by `(img_std, tile_id)` descending. Higher `std` indicates higher density of lines, schedules, or text — the most informative negatives.
- Quarantine isolation: `verify_split_isolation()` must check that `manifest.quarantine_tiles` does not intersect `val_tiles` or `test_tiles` by `drawing_id`, `project_id`, `image_path`, and `mask_path`.
- Standalone `validate_mask_array`: Validates arbitrary ndarrays (dtype uint8, 2D, values in {0,1,2,3}) and raises `MaskValidationError`.

## Artifact Index
- `.agents/teamwork/m1_r2_spec_miner_2/DISPATCH.md` — Dispatch prompt and assignment
- `.agents/teamwork/m1_r2_spec_miner_2/BRIEFING.md` — Persistent situational memory
- `.agents/teamwork/m1_r2_spec_miner_2/progress.md` — Heartbeat and execution log
- `.agents/teamwork/m1_r2_spec_miner_2/analysis.md` — Deep technical specifications and contract mining
- `.agents/teamwork/m1_r2_spec_miner_2/handoff.md` — Hard handoff report for orchestrator and workers
