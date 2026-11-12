# Task Assignment: Milestone M1 Iteration 2 Reviewer 2 (Split & Loader)

- **Assigned Agent**: `m1_r2_reviewer_2` (`teamwork_reviewer`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_reviewer_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Gate Review)
- **Date**: 2026-11-08

---

## 1. Scope & Review Objectives

Review the updated code and tests for Milestone M1 Iteration 2:
1. `drywall_detection/datasets/split_manager.py`:
   - Inspect `verify_split_isolation()` to confirm that quarantine isolation is exhaustively enforced against `val_tiles` and `test_tiles` across project IDs, drawing IDs, tile IDs, and canonical file paths.
   - Confirm that any tile record in `val_tiles` or `test_tiles` flagged with `quarantine=True` or `is_pseudo_label=True` raises `SplitLeakageError`.
   - Confirm Windows path comparisons use `_canonical_path()` with `os.path.normcase(os.path.abspath(str(p)))`.
2. `drywall_detection/datasets/loader.py`:
   - Confirm streaming dataset and dataloader contracts remain intact.
3. `drywall_detection/tests/unit/test_datasets.py`:
   - Inspect `TestQuarantineIsolationValidation` and related tests.
4. Run test verification:
   - `python -m pytest drywall_detection/tests/ -v`

---

## 2. Input References

- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\handoff.md`

---

## 3. Deliverables

1. Maintain `progress.md` with timestamps.
2. Deliver `handoff.md` with explicit verdict: **APPROVE** or **REQUEST_CHANGES**.
