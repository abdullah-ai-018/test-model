# Handoff Report: Milestone M1 Test Suite Hardening Strategy

**Agent ID:** `explorer_m1_iter2_3`  
**Role:** M1 Test Suite Hardening Explorer  
**Date:** 2026-11-08  
**Working Directory:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_3`  

---

## 1. Observation

1. **Adversarial Tests Asserting Vulnerabilities in `drywall_detection/tests/test_adversarial_m1.py`**:
   - Lines 52–64: `test_r2v_exact_boundary_fails_to_trigger_10gb_warning` asserts:
     ```python
     disk_res = auditor.check_disk_space("r2v")
     assert disk_res.exceeds_10gb_threshold is False
     ```
   - Lines 65–74: `test_cubicasa5k_large_extraction_omission` asserts:
     ```python
     res = auditor.audit_candidate("cubicasa5k")
     assert res.dataset_spec.extracted_size_gb > 10.0
     assert res.disk_audit.exceeds_10gb_threshold is False
     ```
   - Lines 111–124: `test_negative_required_gb_bypasses_headroom_check` asserts:
     ```python
     res = auditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")
     assert res.free_gb == 0.0
     assert res.is_sufficient is True

     safe, free, msg = check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
     assert free == 0.0
     assert safe is True
     ```
   - Lines 242–254: `test_explicit_none_dictionary_crash` asserts:
     ```python
     with pytest.raises(TypeError, match="float.*NoneType"):
         auto_configure_training({"cuda_available": True, "vram_total_gb": None})
     with pytest.raises(TypeError, match="float.*NoneType"):
         auto_configure_training({"cuda_available": False, "ram_available_gb": None})
     with pytest.raises(TypeError, match="int.*NoneType"):
         auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
     ```

2. **Current Baseline Test Suite Execution**:
   - Command: `python -m pytest drywall_detection/tests/test_adversarial_m1.py drywall_detection/tests/test_audit.py -v`
   - Output: `39 passed in 6.83s` (100% pass, precisely because these 4 tests currently assert the pre-fix vulnerable behavior).
   - Entire suite run: `257 passed, 1 failed` (where the single failure in `test_tiling_stitching_stress.py` line 306 was an isolated float32 peak equality check that was subsequently resolved, passing with 100%).

3. **Target Code Logic for Fixes**:
   - `drywall_detection/audit/dataset_auditor.py` line 560: `req_dl_b = int(float(required_gb_or_id) * (1024.0 ** 3))` produces negative bytes without checking `required_gb_or_id >= 0.0`.
   - `drywall_detection/utils/hardware.py` line 498: `if free_gb < (required_gb + DISK_FREE_MIN_GB):` allows negative `required_gb` to pass.
   - `drywall_detection/utils/hardware.py` lines 308–312: `profile.get(key, default)` returns `None` when keys are explicitly provided with `None`, causing `float(None)` and `int(None)` to raise `TypeError`.
   - `drywall_detection/audit/dataset_auditor.py` lines 703 & 735: `check_disk_space()` omits extraction check, causing CubiCasa5K (20 GB extracted) to set `exceeds_10gb_threshold = False`.

---

## 2. Logic Chain

1. From Observation 1, four tests in `test_adversarial_m1.py` explicitly verify and demand the *broken / vulnerable* behaviors (bypassing disk space checks, crashing on NoneType, omitting CubiCasa5K warnings, and missing R2V threshold).
2. Sibling explorers (`explorer_m1_iter2_1` and `explorer_m1_iter2_2`) are designing fixes for `hardware.py` and `dataset_auditor.py`:
   - Enforcing `ValueError` on negative disk space allocations.
   - Safe `None`-coalescing in `auto_configure_training`.
   - Adding extraction size checks (> 10 GB) and `>=` boundary checks in `audit_candidate` and `check_disk_space`.
3. When worker agents implement these fixes, any test that asserts `res.is_sufficient is True` for negative space, `exceeds_10gb_threshold is False` for CubiCasa5K/R2V, or `pytest.raises(TypeError)` for `NoneType` dictionaries will **FAIL immediately**, breaking CI/CD and milestone verification.
4. Therefore, the test suite must be updated in tandem:
   - The 4 tests in `drywall_detection/tests/test_adversarial_m1.py` must be updated to assert the *hardened* behavior (`pytest.raises(ValueError)`, valid `TrainingConfig` on `NoneType`, `exceeds_10gb_threshold is True`, and warning generation).
   - In addition, unit tests asserting the hardened behavior must be added to `drywall_detection/tests/test_audit.py` and `drywall_detection/tests/test_hardware.py` to prevent future regressions.
5. With both code fixes and test suite updates in place, all 258+ tests across Milestone M1 will pass 100%.

---

## 3. Caveats

- **No Production Code Modification**: As an Explorer agent, no changes were written directly to `drywall_detection/` production or test code. The exact diffs and assertions are specified in `report.md` for execution by the implementer worker.
- **Dependency on Fix Diffs**: The exact test regexes (e.g. `match=r"(?i)non-negative"`) assume the worker uses clear error messages containing `"non-negative"`, matching the specifications provided by `explorer_m1_iter2_1` and `explorer_m1_iter2_2`.
- **R2V Boundary Interpretation**: The test specification asserts `exceeds_10gb_threshold is True` for R2V, which holds true whether the implementer updates R2V raw size to 11 GB or switches the threshold operator from `>` to `>=`.

---

## 4. Conclusion

The test hardening strategy for Milestone M1 is fully formulated:
1. `drywall_detection/tests/test_adversarial_m1.py` refactors:
   - `test_negative_required_gb_bypasses_headroom_check` -> `test_negative_required_gb_raises_value_error` (asserting `ValueError`).
   - `test_explicit_none_dictionary_crash` -> `test_explicit_none_dictionary_safe_fallback` (asserting crash-free `TrainingConfig`).
   - `test_cubicasa5k_large_extraction_omission` -> `test_cubicasa5k_large_extraction_triggers_warning` (asserting `exceeds_10gb_threshold is True` & warning).
   - `test_r2v_exact_boundary_fails_to_trigger_10gb_warning` -> `test_r2v_triggers_10gb_warning` (asserting `exceeds_10gb_threshold is True` & warning).
2. Regression additions to `test_audit.py` and `test_hardware.py` verify unit-level negative input rejection, NoneType resilience, and large footprint warnings.
3. Full documentation and code replacements are provided in `report.md`.

---

## 5. Verification Method

Once workers apply the code and test updates, verify independently via:

1. **Targeted M1 Suites Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m1.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_hardware.py drywall_detection/tests/test_licensing_audit.py -v
   ```
   *Expected outcome*: 100% pass across all tests (0 failures, 0 errors).

2. **Full Project Test Suite Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/ -v
   ```
   *Expected outcome*: 258+ tests passing with zero failures.

3. **CLI Runner Zero-Warning Sanity Check**:
   ```powershell
   python -m drywall_detection.audit.dataset_auditor --format json
   python -m drywall_detection.utils.hardware
   ```
   *Expected outcome*: Clean JSON output with 0 runtime warnings.

4. **Invalidation Conditions**:
   - Any test raising `TypeError` when `None` is passed in a hardware profile.
   - Any test returning `sufficient=True` for negative disk space.
   - `audit_candidate("cubicasa5k")` omitting warnings about its 20 GB extraction payload.
