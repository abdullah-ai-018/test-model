# Task Assignment: Milestone M1 Iteration 2 Worker Replacement (m1_worker_2_rep)

- **Assigned Agent**: `m1_worker_2_rep` (`teamwork_worker`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2 Remediation)
- **Role**: Replacement Worker taking over from `m1_worker_2` (which encountered a 429 quota interrupt after updating implementation files).
- **Date**: 2026-11-08

---

## 1. Context & Interruption Point

Predecessor worker `m1_worker_2` completed:
1. `drywall_detection/datasets/unified_format.py`: Added `validate_mask_array()`, updated `UnifiedDatasetConfig`, and updated `SlidingWindowTiler.tile_drawing()` with hard negative quota capping and deterministic variance ranking.
2. `drywall_detection/datasets/__init__.py`: Exported `validate_mask_array`.
3. `drywall_detection/datasets/split_manager.py`: Added `_canonical_path()` and comprehensive quarantine isolation checks against `val_tiles` and `test_tiles` in `verify_split_isolation()`.

What remains to be completed:
1. Inspect the existing code in `drywall_detection/datasets/unified_format.py`, `drywall_detection/datasets/split_manager.py`, and `drywall_detection/datasets/__init__.py` to ensure all implementations are complete, syntax-error-free, and adhere strictly to specifications.
2. Add the 5 unit test suites designed in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3\analysis.md` and `m1_r2_spec_miner_2_rep\analysis.md` to `drywall_detection/tests/unit/test_datasets.py`:
   - Hard negative quota and variance ranking tests (`test_hard_negative_variance_ranking`, `test_zero_wall_drawing_hard_negative_capping`, `test_varying_hard_negative_quota_ratios`, `test_hard_negative_quota_monotonicity`).
   - Quarantine isolation test suite (`TestQuarantineIsolationValidation`).
   - Standalone mask array validation test suite (`TestValidateMaskArrayStandalone`).
3. Run targeted pytest on `drywall_detection/tests/unit/test_datasets.py` and run full regression suite `python -m pytest drywall_detection/tests/ -v`.
4. Ensure 100% test pass rate across all tests.
5. Author a complete Hard Handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\handoff.md`.

---

## 2. Input Specifications & References

- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Authoritative original user request)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Global project architecture)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_spec_miner_2_rep\analysis.md` (API contracts, docstrings, typing signatures)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_1\analysis.md` (Mathematical quota derivations & ranking algorithm)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3\analysis.md` (Drop-in test implementations and assertions)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2\progress.md` (Predecessor progress log)

---

## 3. Write Ownership & Boundaries

You have EXCLUSIVE write ownership of:
- `drywall_detection/tests/unit/test_datasets.py`
- `drywall_detection/datasets/unified_format.py` (if any adjustments are needed)
- `drywall_detection/datasets/split_manager.py` (if any adjustments are needed)
- `drywall_detection/datasets/__init__.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep/` (your own state folder)

DO NOT modify files outside these paths.

---

## 4. Mandatory Integrity Warning

> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

---

## 5. Output Requirements

1. Maintain `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep\progress.md` with timestamps.
2. Run `python -m pytest drywall_detection/tests/ -v` and document all test runs and outputs.
3. Write `handoff.md` with sections: Observation, Logic Chain, Caveats, Conclusion, Verification Method.


## 2026-11-08T03:38:01Z
You are assigned as m1_worker_2_rep (M1 Iteration 2 Worker Replacement).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_2_rep
