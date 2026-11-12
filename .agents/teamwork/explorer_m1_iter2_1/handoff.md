# Handoff Report: M1 Hardware Hardening Blueprint

**Agent ID:** `explorer_m1_iter2_1`  
**Role:** M1 Hardware Hardening Explorer  
**Date:** 2026-11-08  
**Recipient:** Orchestrator (`3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`) / Implementer (`worker_m1_1`)  
**Type:** Hard Handoff (Investigation Complete)  

---

## 1. Observation

Direct observations and reproductions conducted in the local workspace:

1. **Negative Disk Space Bypass in `check_disk_safety`**:
   - Location: `drywall_detection/utils/hardware.py`, lines 470–506.
   - Command executed:
     ```powershell
     python -c "from drywall_detection.utils.hardware import check_disk_safety; print(check_disk_safety(-5.0))"
     ```
   - Verbatim Output:
     ```
     (True, 10.71, 'OK: Sufficient disk space (10.71 GB free).')
     ```
   - Reproduction on non-existent volume (`Z:\nonexistent`):
     ```python
     safe, free, msg = check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
     # safe == True, free == 0.0, msg == "OK: Sufficient disk space (0.00 GB free)."
     ```
   - Observation: At line 498 (`if free_gb < (required_gb + DISK_FREE_MIN_GB):`), when `required_gb = -6.0` and `DISK_FREE_MIN_GB = 5.0`, `required_gb + DISK_FREE_MIN_GB = -1.0`. The condition `0.0 < -1.0` is `False`. The code falls through to line 505 and reports `(True, 0.0, "OK: Sufficient disk space (0.00 GB free).")`, bypassing safety checks.

2. **Uncaught `TypeError` on Explicit `None` Values in `auto_configure_training`**:
   - Location: `drywall_detection/utils/hardware.py`, lines 294–318.
   - Command executed:
     ```powershell
     python -c "from drywall_detection.utils.hardware import auto_configure_training; auto_configure_training({'cuda_available': True, 'vram_total_gb': None})"
     ```
   - Verbatim Error:
     ```
     Traceback (most recent call last):
       File "<string>", line 1, in <module>
       File "C:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\hardware.py", line 308, in auto_configure_training
         vram_total_gb = float(profile.get("vram_total_gb", 0.0))
     TypeError: float() argument must be a string or a real number, not 'NoneType'
     ```
   - Also verified for:
     - `{"cuda_available": False, "ram_available_gb": None}` -> `TypeError: float() argument must be a string or a real number, not 'NoneType'`
     - `{"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None}` -> `TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'`

3. **Current Test Baseline**:
   - Running `pytest drywall_detection/tests/test_hardware.py -v`: 18 passed in 11.64s.
   - Running `pytest drywall_detection/tests/test_adversarial_m1.py -v`: 19 passed in 14.5s (where tests lines 111-124 and 242-254 currently assert that the buggy behavior is reproduced).

---

## 2. Logic Chain

1. **Step 1 (Root Cause of C1)**: From Observation 1, `check_disk_safety` accepts any float value for `required_gb`. When `required_gb < 0.0`, the sum `(required_gb + DISK_FREE_MIN_GB)` decreases and can become negative, allowing a drive with `0.0` free space to evaluate `free_gb < (required_gb + DISK_FREE_MIN_GB)` as `False`. Therefore, a non-negative guard `required_free_gb >= 0.0` is strictly necessary at the function entrance.
2. **Step 2 (Signature Compatibility)**: The task specifies `check_disk_safety(required_free_gb, disk_path)` raising `ValueError("required_free_gb must be non-negative")`. Existing test suite `test_hardware.py:231,238,244` invokes keyword argument `required_gb=...`. By declaring `def check_disk_safety(required_free_gb: float = 0.0, disk_path: Union[str, Path] = WORKSPACE_ROOT, *, required_gb: Optional[float] = None)` and coalescing `effective_req = required_gb if required_gb is not None else required_free_gb`, the function strictly satisfies the requested signature and error string while maintaining 100% backward compatibility with all callers.
3. **Step 3 (Root Cause of C2)**: From Observation 2, Python's `dict.get(key, default)` returns `default` only when `key not in dict`. When the key is present with value `None`, `dict.get` returns `None`. Subsequent `float(None)` or `int(None)` calls inevitably raise `TypeError`.
4. **Step 4 (Safe Helper Architecture)**: By defining module-level helper functions `_safe_float(val, default)`, `_safe_int(val, default)`, and `_safe_bool(val, default)` that compute `val if val is not None else default` before casting, and resolving `ram_available_gb` -> `ram_total_gb` -> `8.0`, any profile containing explicit `None` values or missing keys safely falls back to standard defaults without exceptions.
5. **Step 5 (Synthesis & Test Alignment)**: Adding explicit unit tests to `test_hardware.py` guarantees coverage of the new guards, while preparing the transition for `test_adversarial_m1.py` turns adversarial repros into permanent regression defenses.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: In accordance with the explorer archetype rules, this agent did not modify production code in `drywall_detection/utils/hardware.py` or existing tests. Full implementation is assigned to `worker_m1_1`.
2. **Dataset Auditor Scope**: Challenger C3 (CubiCasa5K extraction threshold) and C4 (R2V 10.00 GB exact boundary) reside in `drywall_detection/audit/dataset_auditor.py`, which is being addressed by a parallel explorer/worker track (`explorer_m1_iter2_2` / `worker_m1_1`). This report focuses specifically on `drywall_detection/utils/hardware.py`.
3. **External Upstream APIs**: Future upstream hardware telemetry tools might theoretically pass non-numeric strings (e.g. `"unknown"`). The proposed helpers use `float(val if val is not None else default)` which handles `None` and numeric types; if non-numeric string inputs are anticipated, a `try/except (ValueError, TypeError)` wrapper could be considered, though standard profiles only provide numeric/None types.

---

## 4. Conclusion

The exact code blueprint, unified diff patch, and test specifications have been drafted and validated. The fix consists of:
1. Adding `_safe_float`, `_safe_int`, `_safe_bool` helper functions immediately before `auto_configure_training` in `drywall_detection/utils/hardware.py`.
2. Updating `auto_configure_training` to extract all dictionary and dataclass fields through these safe coalescing helpers, preventing `TypeError`.
3. Updating `check_disk_safety` to validate `required_free_gb >= 0.0` and raise `ValueError("required_free_gb must be non-negative")` on negative values, using `effective_req_gb` for all downstream threshold and headroom calculations.
4. Supplying comprehensive unit test assertions for `test_hardware.py` and regression updates for `test_adversarial_m1.py`.

The blueprint is ready for immediate application by `worker_m1_1`.

---

## 5. Verification Method

Once `worker_m1_1` applies the changes, the fix can be independently verified with the following steps:

1. **Verify `check_disk_safety` Guard**:
   ```powershell
   python -c "from drywall_detection.utils.hardware import check_disk_safety; check_disk_safety(-1.0)"
   # Must raise ValueError: required_free_gb must be non-negative
   ```

2. **Verify `auto_configure_training` None-Coalescing**:
   ```powershell
   python -c "from drywall_detection.utils.hardware import auto_configure_training; cfg = auto_configure_training({'cuda_available': True, 'vram_total_gb': None}); print('Tier:', cfg.hardware_tier)"
   # Must print: Tier: 3 (without raising TypeError)
   ```

3. **Execute Project Hardware Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_hardware.py -v
   ```
   All tests must pass.

4. **Execute Adversarial Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m1.py -v
   ```

5. **Invalidation Conditions**:
   - `check_disk_safety(-5.0)` does not raise `ValueError`.
   - `check_disk_safety(required_gb=0.1)` raises `TypeError` due to unexpected keyword argument.
   - `auto_configure_training({"vram_total_gb": None})` raises `TypeError`.
