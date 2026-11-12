# Task Assignment: Milestone M1 Iteration 2 Reviewer 1 (Licensing & Format)

- **Assigned Agent**: `m1_r2_reviewer_1` (`teamwork_reviewer`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_reviewer_1`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Gate Review)
- **Date**: 2026-11-08

---

## 1. Scope & Review Objectives

Review the updated code and tests for Milestone M1 Iteration 2:
1. `drywall_detection/datasets/unified_format.py`:
   - Inspect `SlidingWindowTiler.tile_drawing()` to confirm that hard negative tiles are capped using `int(np.ceil(num_walls * ratio / (1.0 - ratio)))`.
   - Confirm candidate hard negatives are sorted deterministically by linework standard deviation descending `(-std, row_idx, col_idx, tile_id)` to prioritize the most informative linework/text/schedules.
   - Confirm zero-wall sheets with multiple tiles cap hard negatives at 0 (or nominal minimum), preventing background flooding.
   - Confirm `validate_mask_array()` validates array instance, uint8 dtype, 2D ndim, non-zero dimensions, expected shape, and value membership strictly in `{0, 1, 2, 3}`.
   - Confirm `validate_mask_array` is exported in `drywall_detection/datasets/__init__.py`.
2. `drywall_detection/tests/unit/test_datasets.py`:
   - Inspect the new test suites for quota capping, variance ranking, zero-wall handling, and `validate_mask_array`.
3. Run test verification:
   - `python -m pytest drywall_detection/tests/unit/test_datasets.py -v`
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


## 2026-11-08T03:47:57Z
You are assigned as m1_r2_reviewer_1 (M1 R2 Licensing & Format Reviewer).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_reviewer_1

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_reviewer_1\DISPATCH.md

Also read the authoritative inputs:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\handoff.md

Review drywall_detection/datasets/unified_format.py and test_datasets.py:
- Verify hard negative quota capping in SlidingWindowTiler.tile_drawing
- Verify deterministic variance ranking
- Verify zero-wall and single-crop handling
- Verify standalone validate_mask_array export and contract
- Run tests: python -m pytest drywall_detection/tests/unit/test_datasets.py -v and python -m pytest drywall_detection/tests/ -v
- Deliver your verdict (APPROVE or REQUEST_CHANGES) in handoff.md.
