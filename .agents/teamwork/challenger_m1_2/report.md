# Adversarial Challenge Report: Milestone M1 (Dataset Auditor & Hardware Utilities)

**Agent ID:** `challenger_m1_2`  
**Role:** M1 Dataset & Hardware Challenger (Critic / Specialist)  
**Date:** 2026-11-08  
**Target Code:** `drywall_detection/audit/dataset_auditor.py`, `drywall_detection/utils/hardware.py`  
**Test Suite:** `drywall_detection/tests/test_adversarial_m1.py` (19 tests, 100% pass)  
**Empirical Verdict:** **REQUEST_CHANGES**

---

## 1. Challenge Summary

**Overall Risk Assessment:** **MEDIUM**  
The coordinate transformation geometry and core zero-tolerance licensing rules (R2V access block, SESYD wall label exclusion) are implemented with high fidelity and strict immutability. However, adversarial stress testing revealed four concrete edge-case vulnerabilities in disk safety validation, threshold calculations, and hardware profile dictionary parsing that allow safety bypasses or uncaught exceptions.

| # | Challenge Area | Severity | Finding | Status |
|---|---|---|---|---|
| **C1** | Negative Required Space Bypass | **HIGH** | `check_disk_space()` and `check_disk_safety()` allow negative `required_gb`, producing `sufficient=True` on non-existent drives (`Z:\`) with 0 free GB. | **VULNERABILITY REPRODUCED** |
| **C2** | `NoneType` Crash in Auto-Config | **MEDIUM** | Passing dictionary with explicit `None` values (e.g. `vram_total_gb: None`) raises uncaught `TypeError` in `auto_configure_training()`. | **VULNERABILITY REPRODUCED** |
| **C3** | Extraction Size Threshold Omission | **MEDIUM** | `audit_candidate("cubicasa5k")` fails to check the 21.47 GB extracted payload against the 10 GB threshold, emitting no warning despite `config.py` rule. | **VULNERABILITY REPRODUCED** |
| **C4** | R2V 10.00 GB Boundary Mismatch | **LOW** | R2V catalog spec declares `raw_size_bytes = 10_737_418_240` (exactly 10.000000 GB). Strict `> 10.0` check produces `exceeds_10gb_threshold = False` despite `# >10 GB` comment. | **DEFECT REPRODUCED** |
| **C5** | R2V & SESYD Guardrails | **PASS** | R2V is permanently blocked with `PermissionError`; SESYD is permanently classified ineligible for wall segmentation. Immutability verified. | **ROBUST** |
| **C6** | URL & Network Fault Tolerance | **PASS** | HTTP 403, 404, 500, timeouts, invalid schemes, and empty URLs are handled safely without uncaught exceptions. | **ROBUST** |

---

## 2. Detailed Findings & Reproductions

### Challenge 1 (HIGH): Negative Required Disk Space Bypasses Safety & Headroom Checks
- **Assumption Challenged**: Disk safety functions assume callers will only provide non-negative byte or GB allocations.
- **Attack Scenario**: An adversary, malformed candidate metadata, or integer overflow delivers a negative download size (e.g. `required_gb = -5.0`).
- **Blast Radius**: Disk safety checks return `sufficient = True` ("OK: Sufficient disk space") even on a non-existent drive `Z:\` or a 100% full volume with 0 bytes free.
- **Empirical Evidence**:
  ```python
  from drywall_detection.audit.dataset_auditor import DatasetAuditor
  from drywall_detection.utils.hardware import check_disk_safety

  auditor = DatasetAuditor()
  res = auditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")
  # res.free_gb == 0.0, yet res.is_sufficient is True!
  # Message: "OK: Sufficient disk space (0.00 GB free, 5.00 GB post-download headroom)."

  safe, free, msg = check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
  # safe is True! Message: "OK: Sufficient disk space (0.00 GB free)."
  ```
- **Root Cause**:
  In `dataset_auditor.py` line 578:
  ```python
  elif (free_gb - req_dl_gb) < min_headroom_gb:
  ```
  When `req_dl_gb = -5.0`, `0.0 - (-5.0) = +5.0 GB >= 2.0 GB`, satisfying the headroom condition.
  In `hardware.py` line 498:
  ```python
  if free_gb < (required_gb + DISK_FREE_MIN_GB):
  ```
  `0.0 < (-6.0 + 5.0)` evaluates to `0.0 < -1.0`, which is `False`, allowing execution to proceed.
- **Recommended Mitigation**:
  Add explicit non-negative guard in both functions:
  ```python
  if required_gb < 0.0:
      return DiskAuditResult(..., sufficient_space=False, warning_message="REJECTED: Required download size cannot be negative.")
  ```

---

### Challenge 2 (MEDIUM): `NoneType` Dictionary Values Cause Uncaught `TypeError` in `auto_configure_training`
- **Assumption Challenged**: Input hardware dictionaries will only contain non-None numeric/boolean values for present keys.
- **Attack Scenario**: Hardware probing from an uninstrumented environment or upstream API returns `{"vram_total_gb": None}` or `{"ram_available_gb": None}`.
- **Blast Radius**: Uncaught exception halts training startup.
- **Empirical Evidence**:
  ```python
  from drywall_detection.utils.hardware import auto_configure_training
  auto_configure_training({"cuda_available": True, "vram_total_gb": None})
  # TypeError: float() argument must be a string or a real number, not 'NoneType'

  auto_configure_training({"cuda_available": False, "ram_available_gb": None})
  # TypeError: float() argument must be a string or a real number, not 'NoneType'

  auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
  # TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
  ```
- **Root Cause**:
  In `hardware.py` lines 308–312:
  `profile.get("vram_total_gb", 0.0)` returns `None` because the key exists in the dict with value `None`. Subsequent `float(None)` raises `TypeError`.
- **Recommended Mitigation**:
  Use `or` fallback or `is not None` guard:
  ```python
  raw_vram = profile.get("vram_total_gb")
  vram_total_gb = float(raw_vram) if raw_vram is not None else 0.0
  raw_ram = profile.get("ram_available_gb")
  ram_available_gb = float(raw_ram) if raw_ram is not None else 8.0
  raw_cores = profile.get("cpu_logical_cores")
  cpu_logical_cores = int(raw_cores) if raw_cores is not None else 4
  ```

---

### Challenge 3 (MEDIUM): CubiCasa5K Extracted Payload (>10 GB) Omits Mandatory Warning
- **Assumption Challenged**: `audit_candidate()` evaluates total dataset storage impact against the 10 GB ceiling.
- **Attack Scenario**: A user runs `python -m drywall_detection.audit.dataset_auditor` or automated pipeline to audit candidate datasets.
- **Blast Radius**: CubiCasa5K requires 21.47 GB of uncompressed disk space (up to 105 GB if LMDB format), but `audit_candidate("cubicasa5k")` produces `exceeds_10gb_threshold = False` and outputs zero warnings about the extraction footprint, violating `config.py` rule: *"Downloads or dataset extractions > 10 GB require explicit user notification / prompt before downloading."*
- **Empirical Evidence**:
  ```python
  res = auditor.audit_candidate("cubicasa5k")
  assert res.dataset_spec.extracted_size_gb == 20.0
  assert res.disk_audit.exceeds_10gb_threshold is False
  assert not any("10" in w for w in res.warnings)
  ```
- **Root Cause**:
  In `dataset_auditor.py` line 703:
  ```python
  disk_res = self.check_disk_space(spec.dataset_id)
  ```
  `check_disk_space()` defaults `include_extracted = False`. Furthermore, `exceeds_10gb = req_dl_gb > self.max_unannounced_gb` only evaluates archive download size, never extracted size.
- **Recommended Mitigation**:
  Evaluate both download size and extracted size against `max_unannounced_gb` during candidate audits:
  ```python
  if (spec.raw_size_gb > self.max_unannounced_gb) or (spec.extracted_size_gb > self.max_unannounced_gb):
      warnings.append(f"LARGE PAYLOAD: Extracted size ({spec.extracted_size_gb:.2f} GB) exceeds 10 GB notification threshold.")
  ```

---

### Challenge 4 (LOW): R2V 10.00 GB Boundary Mismatch Fails Notification Threshold
- **Assumption Challenged**: R2V download specification is >10 GB and triggers the warning threshold.
- **Attack Scenario**: R2V is audited with expected large download warning.
- **Blast Radius**: R2V's raw download size is defined as `10_737_418_240` bytes. Because $10,737,418,240 / 1024^3 = 10.000000$ GB, and the comparison is `req_dl_gb > 10.0`, `exceeds_10gb_threshold` evaluates to `False`. The code comment `# >10 GB` is mathematically false.
- **Empirical Evidence**:
  ```python
  res = auditor.audit_candidate("r2v")
  assert res.dataset_spec.raw_size_gb == 10.0
  assert res.disk_audit.exceeds_10gb_threshold is False
  ```
- **Recommended Mitigation**:
  Update R2V spec to reflect its true external size (e.g. `11_000_000_000` bytes) or change threshold comparison to `size_gb >= threshold_gb`.

---

## 3. Verified Robust Areas (Zero-Tolerance Invariants)

The following core security and integrity mechanisms were rigorously attacked and confirmed robust:

1. **R2V Zero-License Automated Download Block**:
   - `DatasetSpec` is frozen (`@dataclass(frozen=True)`). Runtime attribute assignment raises `FrozenInstanceError`.
   - `res.eligibility_verdict` is permanently `INELIGIBLE_FOR_AUTOMATED_DOWNLOAD`.
   - `res.is_downloadable_now` is permanently `False`.
   - `prepare_dataset("r2v")` unconditionally raises `PermissionError: AUTOMATED ACCESS FORBIDDEN`.
2. **SESYD Wall Segmentation Disqualification**:
   - `spec.has_wall_segmentation_labels` is strictly `False`.
   - `res.eligibility_verdict` is permanently `INELIGIBLE_FOR_WALL_SEGMENTATION`.
   - `res.is_downloadable_now` is permanently `False`.
   - Clear blocker documents that annotations exclusively cover 16 furniture/fixture symbols with zero wall labels.
3. **URL & Network Probing Fault Tolerance**:
   - Probing handles HTTP 403 (with GET range retry), HTTP 404, HTTP 500, socket timeouts, invalid schemes (`not_a_valid_url`, `ftp://`), and empty strings `""` without crashing.
4. **Dynamic Hardware Auto-Configuration Tiers**:
   - Zero available RAM, negative RAM, and NaN VRAM fall safely into Tier 5 (`device="cpu"`, `bs=2`, `num_workers=0`, 256x256 resolution).
   - Extreme GPU VRAM (80 GB, 1000 GB) correctly maps to Tier 1 (`device="cuda"`, `bs=16`, `num_workers=4`, 512x512 resolution).
5. **Exact Coordinate Bijection**:
   - Verified determinants $\det(M) = S^2 > 0$ with roundtrip bijection error $< 10^{-14}$ pt across all quadrants.

---

## 4. Verification Harness Summary

All 19 adversarial tests are preserved in the test suite:
- File: `drywall_detection/tests/test_adversarial_m1.py`
- Test command:
  ```powershell
  python -m pytest drywall_detection/tests/test_adversarial_m1.py -v
  ```
- Outcome: 19 passed in 14.5s.

## 5. Recommendation & Verdict

**Verdict: REQUEST_CHANGES**  
Worker `worker_m1_1` should apply the 4 targeted hardening fixes (C1: negative disk space guard, C2: NoneType dict handling, C3: extraction size check in candidate audit, C4: R2V size calibration) before advancing to Milestone M2.
