# Task Assignment: Milestone M1 Iteration 2 Implementation Worker

- **Assigned Agent**: `m1_worker_2` (`teamwork_worker`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Remediation)
- **Date**: 2026-11-08

---

## 1. Objective & Scope

Implement, verify, and deliver the Milestone M1 Iteration 2 code and test fixes to address the defects flagged by Reviewer `m1_reviewer_2` and Challenger `m1_challenger_1`:
1. **Hard Negative Quota Enforcement in `SlidingWindowTiler.tile_drawing()`**:
   - Enforce `self.config.max_hard_negative_ratio` (default 0.15) to eliminate the 96% hard-negative ratio defect on linework drawings.
   - Deterministically rank candidate hard negatives by linework standard deviation descending `(-img_std, row_idx, col_idx, tile_id)` to prioritize the most informative background tiles.
   - Preserve single-tile test crop behavior (`len(tiles_hn) == 1`) when $N_{wall} == 0$ and $N_{cand} == 1$, while capping multi-tile zero-wall sheets at 0 (or `nominal_hard_negatives_zero_walls: int = 0`).
2. **Standalone Mask Array Validation (`validate_mask_array`)**:
   - Implement and export `validate_mask_array()` as a standalone convenience function in `unified_format.py` and `datasets/__init__.py`.
   - Validate numpy array type, uint8 dtype, 2D dimensionality, non-zero shape, optional expected shape, and categorical values in `{0, 1, 2, 3}`.
   - Wire `UnifiedMask.__init__` to delegate validation to `validate_mask_array(data, raise_on_error=True)`.
3. **Quarantine Isolation in `verify_split_isolation()`**:
   - Enhance `verify_split_isolation(manifest)` in `split_manager.py` to ensure that project IDs, drawing IDs, tile IDs, and canonical file paths in `manifest.quarantine_tiles` have ZERO intersection with `val_tiles` or `test_tiles`.
   - Assert that no tile record in `val_tiles` or `test_tiles` has `quarantine=True` or `is_pseudo_label=True`. Raise `SplitLeakageError` immediately if violated.
   - Use `os.path.normcase(os.path.abspath(p))` for case-insensitive canonical path comparisons on Windows.
4. **Unit & Adversarial Test Suites**:
   - Implement the 5 unit test suites designed in `m1_r2_explorer_3/analysis.md` in `drywall_detection/tests/unit/test_datasets.py`.
   - Run full pytest test suite and ensure 100% pass rate.

---

## 2. Input Specifications & Source Reports

You MUST read these authoritative specifications before implementing:
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Authoritative user request)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Global architecture & contracts)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2_rep\analysis.md` (Authoritative API signatures, docstrings, typing, contracts)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1\analysis.md` (Mathematical quota derivations & ranking algorithm)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3\analysis.md` (Concrete test suite designs and code)

---

## 3. Write Ownership & Boundaries

You have EXCLUSIVE write ownership of:
- `drywall_detection/datasets/unified_format.py`
- `drywall_detection/datasets/split_manager.py`
- `drywall_detection/datasets/__init__.py`
- `drywall_detection/tests/unit/test_datasets.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2/` (your own state folder)

DO NOT modify files outside these paths.

---

## 4. Mandatory Integrity Warning

> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

---

## 5. Output Requirements

1. Update `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2\progress.md` with timestamps and current action.
2. Run `python -m pytest drywall_detection/tests/ -v` and document commands and exact test counts in `handoff.md`.
3. Author a complete Hard Handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2\handoff.md` following the protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).


## 2026-11-07T21:47:14Z
Sender: 3c1a82ae-9b50-494e-b173-0369a8d4a486
Content: You are assigned as m1_worker_2 (M1 Iteration 2 Implementation Worker).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2
