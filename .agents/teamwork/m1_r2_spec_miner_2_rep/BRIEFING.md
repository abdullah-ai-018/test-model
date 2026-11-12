# BRIEFING — 2026-11-08T02:45:00Z

## Mission
Mine and specify functional contracts and deterministic selection algorithms for hard negative quota enforcement in SlidingWindowTiler, quarantine validation in verify_split_isolation(), and validate_mask_array().

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Tiling & Filtering Specification Miner
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2_rep
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)

## 🔒 Key Constraints
- Do NOT implement code — read-only specification role
- Mine and specify functional contracts and deterministic selection algorithms
- Address Reviewer failure report (m1_reviewer_2/handoff.md) and Challenger recommendations (m1_challenger_1)
- Write analysis.md and handoff.md in state folder
- Notify orchestrator via send_message when done

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: 2026-11-08T02:45:00Z

## Task Summary
- **What to build**: Specification for SlidingWindowTiler hard negative quota capping (max_hard_negative_ratio = 0.15), quarantine validation in verify_split_isolation(), and export of validate_mask_array() in unified_format.py.
- **Success criteria**: Detailed functional/API contracts, deterministic selection algorithm (ranking by linework variance descending, tie-breaking by coordinates), edge cases, complete tables.
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md, codebase sources.
- **Code layout**: drywall_detection/datasets/unified_format.py, drywall_detection/datasets/split_manager.py, drywall_detection/datasets/__init__.py, drywall_detection/tests/.

## Key Decisions Made
- Derived mathematical quota formula $K_{bound} = \frac{R}{1 - R} N_{wall}$, specifying both ceil (reviewer recommendation, $\le 1/2$ on $N_{wall}=1$) and floor (strict $\le R$ on multi-tile drawings).
- Zero-wall drawings policy: retain 1 tile when $N_{cand} == 1$ to preserve single-tile test compatibility (`test_tile_filtering_blank_and_hard_neg`), while retaining 0 on multi-tile unannotated sheets to prevent dataset flooding.
- 4-tier deterministic ranking key $(-\sigma, \text{row\_idx}, \text{col\_idx}, \text{tile\_id})$ prioritizes high-variance linework, schedules, and text with canonical spatial tie-breaking.
- Standalone quarantine validation: enforced disjointness between `quarantine_tiles` and `val_tiles ∪ test_tiles` across projects, drawings, tile IDs, and canonical file paths with Windows case-folding, plus flag assertions (`not t.quarantine and not t.is_pseudo_label`).
- Standalone `validate_mask_array()` signature, typing, docstrings, and export declarations specified.

## Artifact Index
- analysis.md — Full technical specifications, mathematical derivations, contracts, and test plans
- handoff.md — 5-component hard handoff report for orchestrator and workers
- progress.md — Liveness heartbeat and execution log
