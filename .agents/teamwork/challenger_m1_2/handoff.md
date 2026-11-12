# Handoff Report: Milestone M1 Adversarial Challenge
**Agent ID:** `challenger_m1_2`  
**Milestone:** M1 (Workspace, Hardware, Geometry & Dataset Audit Challenge)  
**Date:** 2026-11-08  
**Parent Conversation ID:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Handoff Type:** Hard (Task complete)  
**Verdict:** **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Test Execution Baseline
- Existing M1 test suite (`drywall_detection/tests/test_audit.py`, `test_coords.py`, `test_hardware.py`):
  - Command: `python -m pytest drywall_detection/tests/test_audit.py drywall_detection/tests/test_coords.py drywall_detection/tests/test_hardware.py -v`
  - Result: 59 passed in 25.46s.

### 1.2 Adversarial Test Suite Execution
- Adversarial test suite created at `drywall_detection/tests/test_adversarial_m1.py` containing 19 stress-testing units across 5 classes:
  - Command: `python -m pytest drywall_detection/tests/test_adversarial_m1.py -v`
  - Result: 19 passed in 14.46s.
- Combined M1 suite:
  - Command: `python -m pytest drywall_detection/tests/test_audit.py drywall_detection/tests/test_coords.py drywall_detection/tests/test_hardware.py drywall_detection/tests/test_adversarial_m1.py -v`
  - Result: 78 passed in 14.46s.

### 1.3 Key Empirical Findings
1. **Negative Required Disk Space Bypass**:
   - `DatasetAuditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")` returned:
     `free_bytes=0, sufficient_space=True, warning_message='OK: Sufficient disk space (0.00 GB free, 5.00 GB post-download headroom).'`
   - `hardware.check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")` returned:
     `(True, 0.0, 'OK: Sufficient disk space (0.00 GB free).')`
2. **`NoneType` Crash in `auto_configure_training`**:
   - `auto_configure_training({"cuda_available": True, "vram_total_gb": None})` raised:
     `TypeError: float() argument must be a string or a real number, not 'NoneType'`
   - `auto_configure_training({"cuda_available": False, "ram_available_gb": None})` raised:
     `TypeError: float() argument must be a string or a real number, not 'NoneType'`
   - `auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})` raised:
     `TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'`
3. **CubiCasa5K Unannounced 20 GB Extraction Omission**:
   - `auditor.audit_candidate("cubicasa5k")` returned `disk_audit.exceeds_10gb_threshold = False` and empty warnings regarding extraction, despite CubiCasa5K having `extracted_size_bytes = 21_474_836_480` (20.0 GB).
4. **R2V 10.00 GB Boundary Equality**:
   - In `dataset_auditor.py:215`, R2V `raw_size_bytes = 10_737_418_240`.
   - $10,737,418,240 / 1024^3 = 10.000000$ GB.
   - `auditor.check_disk_space("r2v")` evaluates `10.0 > 10.0` as `False`, producing `exceeds_10gb_threshold = False`.
5. **Verified Security Invariants**:
   - R2V spec mutation: `r2v_spec.eligibility = ELIGIBLE` raised `FrozenInstanceError`.
   - `prepare_dataset("r2v")` raised `PermissionError: AUTOMATED ACCESS FORBIDDEN...`
   - SESYD spec mutation: `sesyd_spec.has_wall_segmentation_labels = True` raised `FrozenInstanceError`.
   - SESYD verdict: strictly `INELIGIBLE_FOR_WALL_SEGMENTATION` with `is_downloadable_now = False`.

---

## 2. Logic Chain

1. **Premise**: Disk safety checks must protect user storage under all inputs, including negative numbers and non-existent mount points.
   - In `dataset_auditor.py:578`, headroom is evaluated as `(free_gb - req_dl_gb) < min_headroom_gb`.
   - When `req_dl_gb` is negative (e.g. `-5.0`), `0.0 - (-5.0) = +5.0 GB >= 2.0 GB`.
   - Therefore, passing negative required space bypasses both download capacity and headroom validation, reporting that 0.0 GB of free space on a non-existent drive is sufficient.
   - Inference: `required_gb` must be validated as non-negative (`required_gb >= 0.0`) in both `check_disk_space()` and `check_disk_safety()`.

2. **Premise**: Dynamic hardware auto-configuration must be resilient against partially populated or `None`-filled profiling dictionaries.
   - In `hardware.py:308-312`, values are extracted using `profile.get(key, default)`.
   - In Python, if `key` exists in `profile` with value `None`, `.get(key, default)` returns `None` (not `default`).
   - Passing `None` to `float()` or `int()` immediately raises `TypeError`.
   - Inference: Extraction must check `val is not None` before casting.

3. **Premise**: `config.py` mandates that downloads or extractions exceeding 10 GB require explicit notification.
   - CubiCasa5K has an extracted size of 21.47 GB.
   - `audit_candidate("cubicasa5k")` checks only `spec.raw_size_bytes` (5.09 GB), omitting extracted size.
   - Inference: `audit_candidate()` must evaluate both `raw_size_gb` and `extracted_size_gb` against `max_unannounced_gb`.

4. **Premise**: R2V was documented in comments as `# >10 GB`.
   - However, $10,737,418,240$ bytes equals $10 \times 1024^3$ bytes, exactly 10.000000 GB.
   - The boundary check `size_gb > 10.0` does not trigger on equality.
   - Inference: Threshold comparison should use `>=` or R2V raw size should reflect its true external payload.

---

## 3. Caveats

1. **Non-Regression in Core Functionality**:
   - The four identified findings are edge-case vulnerabilities and boundary mismatches. Under normal happy-path operations with positive numbers and valid HardwareProfiles, the existing implementation passes 100% of unit tests.
2. **Review-Only Role**:
   - In strict compliance with the Challenger role constraints, no production implementation files (`dataset_auditor.py` or `hardware.py`) were modified. Only the adversarial test suite (`test_adversarial_m1.py`) and reports were created.
3. **M2 Dataset Test File Not Part of M1**:
   - Earlier pytest execution across all `drywall_detection/tests/` revealed two failures in `drywall_detection/tests/unit/test_datasets.py` (`NameError: name 'cv2' is not defined` and `SplitLeakageError: Train/Val project leakage detected`). These belong to the Milestone M2 dataset preparer pipeline, not the M1 scope.

---

## 4. Conclusion

Empirical verdict: **REQUEST_CHANGES**

The M1 coordinate geometry and licensing guardrails are solid and unbypassable. However, Worker `worker_m1_1` must apply four targeted hardening fixes before Milestone M1 sign-off:
1. **Fix Negative Disk Space Bypass**: Reject `required_gb < 0.0` in `drywall_detection/audit/dataset_auditor.py:check_disk_space()` and `drywall_detection/utils/hardware.py:check_disk_safety()`.
2. **Fix `NoneType` Dictionary Handling**: Use `val if val is not None else default` in `drywall_detection/utils/hardware.py:auto_configure_training()`.
3. **Fix Extraction Size Threshold Check**: Evaluate `spec.extracted_size_gb > self.max_unannounced_gb` in `drywall_detection/audit/dataset_auditor.py:audit_candidate()`.
4. **Fix R2V Size Boundary**: Use `>=` or adjust R2V bytes to exceed 10.0 GB in `drywall_detection/audit/dataset_auditor.py`.

All 19 adversarial regression tests are committed in `drywall_detection/tests/test_adversarial_m1.py`.

---

## 5. Verification Method

To independently reproduce all empirical findings:
1. **Execute Complete M1 and Adversarial Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_audit.py drywall_detection/tests/test_coords.py drywall_detection/tests/test_hardware.py drywall_detection/tests/test_adversarial_m1.py -v
   ```
   *Expected outcome*: 78 passed in ~14 seconds.

2. **Verify Negative Disk Allocation Vulnerability Directly**:
   ```powershell
   python -c "from drywall_detection.audit.dataset_auditor import DatasetAuditor; a = DatasetAuditor(); res = a.check_disk_space(-5.0, target_path='Z:\\nonexistent'); print('Sufficient on Z:\\:', res.sufficient_space)"
   ```
   *Expected outcome*: Prints `Sufficient on Z:\: True` (reproducing the vulnerability).

3. **Verify NoneType Crash in Training Auto-Configuration**:
   ```powershell
   python -c "from drywall_detection.utils.hardware import auto_configure_training; auto_configure_training({'cuda_available': True, 'vram_total_gb': None})"
   ```
   *Expected outcome*: Raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
