# Milestone M1 Test Suite Hardening Strategy Report

**Agent ID:** `explorer_m1_iter2_3`  
**Role:** M1 Test Suite Hardening Explorer  
**Date:** 2026-11-08  
**Scope:** Hardening test suite assertions across `drywall_detection/tests/test_adversarial_m1.py`, `drywall_detection/tests/test_audit.py`, and `drywall_detection/tests/test_hardware.py` for the 4 identified fixes (C1, C2, C3, C4).  
**Mode:** Read-only Investigation & Blueprint Design (No production/test file modifications).

---

## 1. Executive Summary

During Milestone M1 verification, `challenger_m1_2` formulated 19 adversarial stress tests in `drywall_detection/tests/test_adversarial_m1.py`. However, four of these tests were authored to **reproduce and assert the defective behavior** (i.e. verifying that negative disk allocations bypass checks, `NoneType` crashes auto-configuration, CubiCasa5K omits the extraction warning, and R2V fails the 10 GB threshold).

When workers implement the hardening fixes:
1. `check_disk_safety` and `check_disk_space` will raise `ValueError` on negative values.
2. `auto_configure_training` will gracefully coalesce `NoneType` values to safe defaults without crashing.
3. `audit_candidate("cubicasa5k")` will evaluate both archive download and extracted size, triggering the 10 GB warning.
4. `audit_candidate("r2v")` and `check_disk_space("r2v")` will evaluate `>= 10.0` GB, triggering the 10 GB threshold warning.

If the test suite is not updated, the tests asserting the vulnerable behaviors will fail once the fixes are applied. This report specifies the exact test refactoring in `test_adversarial_m1.py`, new unit-level test additions in `test_audit.py` and `test_hardware.py`, and the verification protocol to ensure a 100% pass rate across all 258+ tests in the M1 test suite.

---

## 2. Detailed Review of the 4 Target Fixes & Test Impact

### Fix 1: Negative Required Disk Space Protection (`ValueError`)
- **Vulnerability**: Callers passing `required_gb = -5.0` to `DatasetAuditor.check_disk_space()` or `check_disk_safety(-6.0)` produced `is_sufficient = True` on full disks or non-existent drives (`Z:\`), because negative numbers satisfied the headroom inequality (`0.0 - (-5.0) = +5.0 >= 2.0`).
- **Target Implementation**:
  - `drywall_detection/audit/dataset_auditor.py`: If `isinstance(required_gb_or_id, (int, float))` and `required_gb_or_id < 0.0`, raise `ValueError("required_gb must be non-negative: got ...")`.
  - `drywall_detection/utils/hardware.py`: In `check_disk_safety(required_gb, disk_path)`, if `required_gb < 0.0`, raise `ValueError("required_gb must be non-negative: got ...")`.
- **Existing Defective Assertion**:
  `test_adversarial_m1.py::test_negative_required_gb_bypasses_headroom_check` asserts `res.is_sufficient is True` and `safe is True`.
- **Test Hardening Strategy**:
  Convert `test_negative_required_gb_bypasses_headroom_check` to `test_negative_required_gb_raises_value_error`, asserting `pytest.raises(ValueError, match=r"(?i)non-negative")` for both functions across edge cases (`-5.0`, `-0.001`, `-100.0`). Add dedicated unit tests in `test_audit.py` and `test_hardware.py`.

---

### Fix 2: `NoneType` Dictionary Handling in `auto_configure_training`
- **Vulnerability**: Calling `auto_configure_training({"cuda_available": True, "vram_total_gb": None})` or `{"ram_available_gb": None}` or `{"cpu_logical_cores": None}` crashes with `TypeError: float() argument must be a string or a real number, not 'NoneType'` because `.get(key, default)` returns `None` if the key exists in the dictionary.
- **Target Implementation**:
  - `drywall_detection/utils/hardware.py`: Use safe `None`-coalescing helper functions `_safe_float` and `_safe_int`, falling back to safe defaults (`0.0` for VRAM, `8.0` for RAM, `4` for CPU logical cores, `False` for CUDA) when the value is `None`.
- **Existing Defective Assertion**:
  `test_adversarial_m1.py::test_explicit_none_dictionary_crash` asserts `with pytest.raises(TypeError, match="float.*NoneType"): ...`.
- **Test Hardening Strategy**:
  Convert `test_explicit_none_dictionary_crash` to `test_explicit_none_dictionary_safe_fallback`, asserting that passing dictionaries with `None` values does NOT raise `TypeError`, but returns a valid `TrainingConfig` adhering to hardware tier constraints. Add unit tests in `test_hardware.py`.

---

### Fix 3: CubiCasa5K Extracted Payload (>10 GB) Warning
- **Vulnerability**: CubiCasa5K has an archive download size of ~5.09 GB, but an uncompressed extraction footprint of ~20.0 GB (up to 21.47 GB or 105 GB in LMDB). Project specifications require explicit warning on any download or extraction > 10 GB. `audit_candidate("cubicasa5k")` only checked archive size against the threshold, producing `exceeds_10gb_threshold = False` and omitting any warning.
- **Target Implementation**:
  - `drywall_detection/audit/dataset_auditor.py`: In `audit_candidate()` and `check_disk_space()`, evaluate both `spec.raw_size_gb` and `spec.extracted_size_gb` against `max_unannounced_gb`. If either exceeds `10.0`, set `exceeds_10gb_threshold = True` and append a `LARGE EXTRACTION` warning to `warnings`.
- **Existing Defective Assertion**:
  `test_adversarial_m1.py::test_cubicasa5k_large_extraction_omission` asserts:
  ```python
  assert res.dataset_spec.extracted_size_gb > 10.0
  assert res.disk_audit.exceeds_10gb_threshold is False
  ```
- **Test Hardening Strategy**:
  Update `test_adversarial_m1.py::test_cubicasa5k_large_extraction_triggers_warning` to assert `res.disk_audit.exceeds_10gb_threshold is True`, `any("10" in w for w in res.warnings)`, and `any("extract" in w.lower() for w in res.warnings)`. Add unit test in `test_audit.py`.

---

### Fix 4: R2V 10.00 GB Boundary Mismatch
- **Vulnerability**: R2V catalog spec defines `raw_size_bytes = 10_737_418_240`, which equals exactly `10.000000` GB ($10,737,418,240 / 1024^3$). `check_disk_space` evaluated strict inequality `req_dl_gb > 10.0`, resulting in `exceeds_10gb_threshold = False` despite the comment `# >10 GB`. Furthermore, R2V extracted size is 20.0 GB.
- **Target Implementation**:
  - `drywall_detection/audit/dataset_auditor.py`: Check `req_dl_gb >= self.max_unannounced_gb` (or evaluate extraction size `20.0 GB > 10.0 GB`), ensuring `exceeds_10gb_threshold = True` and emitting a large dataset warning.
- **Existing Defective Assertion**:
  `test_adversarial_m1.py::test_r2v_exact_boundary_fails_to_trigger_10gb_warning` asserts `disk_res.exceeds_10gb_threshold is False`.
- **Test Hardening Strategy**:
  Update `test_adversarial_m1.py::test_r2v_triggers_10gb_warning` to assert `disk_res.exceeds_10gb_threshold is True`, `res.disk_audit.exceeds_10gb_threshold is True`, and `any("10" in w for w in res.warnings)`. Update `test_audit.py::test_r2v_audit_verdict_ineligible_gated`.

---

## 3. Exact Code Updates Required in `drywall_detection/tests/test_adversarial_m1.py`

Below are the exact replacement test methods for `drywall_detection/tests/test_adversarial_m1.py`:

```python
<<<<
    def test_r2v_exact_boundary_fails_to_trigger_10gb_warning(self, auditor):
        """
        Adversarial Finding: R2V catalog spec has raw_size_bytes = 10_737_418_240.
        Although code comment claims '# >10 GB', 10_737_418_240 bytes == 10.000000 GB exact.
        Because check_disk_space uses strict inequality (> 10.0), exceeds_10gb_threshold is False.
        """
        r2v_spec = auditor.get_spec("r2v")
        assert r2v_spec.raw_size_bytes == 10_737_418_240
        assert math.isclose(r2v_spec.raw_size_gb, 10.0, abs_tol=1e-9)

        disk_res = auditor.check_disk_space("r2v")
        assert disk_res.exceeds_10gb_threshold is False

    def test_cubicasa5k_large_extraction_omission(self, auditor):
        """
        Adversarial Finding: CubiCasa5K extracted size is 21.47 GB (> 10 GB threshold).
        audit_candidate('cubicasa5k') does not check extraction size against the 10 GB threshold,
        producing exceeds_10gb_threshold = False.
        """
        res = auditor.audit_candidate("cubicasa5k")
        assert res.dataset_spec.extracted_size_gb > 10.0
        assert res.disk_audit.exceeds_10gb_threshold is False
====
    def test_r2v_triggers_10gb_warning(self, auditor):
        """
        Hardened: R2V download specification (10.000 GB raw, 20.000 GB extracted)
        must trigger the >= 10 GB notification threshold.
        """
        r2v_spec = auditor.get_spec("r2v")
        assert r2v_spec.raw_size_gb >= 10.0 or r2v_spec.extracted_size_gb > 10.0

        disk_res = auditor.check_disk_space("r2v")
        assert disk_res.exceeds_10gb_threshold is True

        res = auditor.audit_candidate("r2v")
        assert res.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in res.warnings)

    def test_cubicasa5k_large_extraction_triggers_warning(self, auditor):
        """
        Hardened: CubiCasa5K extracted size is 20.0 GB (or 21.47 GB, > 10 GB threshold).
        audit_candidate('cubicasa5k') must check extraction footprint, set
        exceeds_10gb_threshold = True, and emit a LARGE EXTRACTION warning.
        """
        res = auditor.audit_candidate("cubicasa5k")
        assert res.dataset_spec.extracted_size_gb > 10.0
        assert res.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in res.warnings)
        assert any("extract" in w.lower() for w in res.warnings)
>>>>
```

And in `TestDiskHeadroomAdversarialStress`:

```python
<<<<
    def test_negative_required_gb_bypasses_headroom_check(self, auditor):
        r"""
        Adversarial Finding: Passing negative required_gb creates artificial headroom.
        On non-existent drive Z:\ with 0 free GB, required_gb = -5.0 returns sufficient = True!
        """
        res = auditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")
        # 0.0 - (-5.0) = 5.0 >= 2.0 headroom
        assert res.free_gb == 0.0
        assert res.is_sufficient is True  # Demonstrates bypass vulnerability

        safe, free, msg = check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
        assert free == 0.0
        assert safe is True  # Demonstrates bypass vulnerability
====
    def test_negative_required_gb_raises_value_error(self, auditor):
        r"""
        Hardened: Passing negative required_gb to check_disk_space or check_disk_safety
        must raise ValueError rather than fabricating artificial headroom.
        """
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-0.0001)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(-0.001)
>>>>
```

And in `TestHardwareAutoConfigStress`:

```python
<<<<
    def test_explicit_none_dictionary_crash(self):
        """
        Adversarial Finding: Passing explicit None in profile dictionary crashes with TypeError
        because .get(key, default) returns None instead of the fallback default.
        """
        with pytest.raises(TypeError, match="float.*NoneType"):
            auto_configure_training({"cuda_available": True, "vram_total_gb": None})

        with pytest.raises(TypeError, match="float.*NoneType"):
            auto_configure_training({"cuda_available": False, "ram_available_gb": None})

        with pytest.raises(TypeError, match="int.*NoneType"):
            auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
====
    def test_explicit_none_dictionary_safe_fallback(self):
        """
        Hardened: Passing explicit None in profile dictionary safely falls back to defaults
        without raising TypeError.
        """
        # None VRAM with CUDA True safely falls back to 0.0 VRAM (CPU or safe low Tier)
        cfg1 = auto_configure_training({"cuda_available": True, "vram_total_gb": None})
        assert isinstance(cfg1, TrainingConfig)
        assert cfg1.device in ("cpu", "cuda")

        # None RAM safely falls back to default RAM
        cfg2 = auto_configure_training({"cuda_available": False, "ram_available_gb": None})
        assert isinstance(cfg2, TrainingConfig)
        assert cfg2.device == "cpu"
        assert cfg2.hardware_tier == 4

        # None cpu_logical_cores safely falls back to default cores
        cfg3 = auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
        assert isinstance(cfg3, TrainingConfig)
        assert cfg3.hardware_tier == 1
        assert cfg3.num_workers >= 2

        # All None profile safely yields Tier 5 or Tier 4 default config
        all_none = {
            "cuda_available": None,
            "vram_total_gb": None,
            "ram_available_gb": None,
            "ram_total_gb": None,
            "cpu_logical_cores": None,
        }
        cfg4 = auto_configure_training(all_none)
        assert isinstance(cfg4, TrainingConfig)
        assert cfg4.device == "cpu"
        assert cfg4.batch_size in (2, 4)
>>>>
```

---

## 4. Exact Test Additions Required in `drywall_detection/tests/test_audit.py`

In `drywall_detection/tests/test_audit.py`, append the following hardened regression assertions:

### 4.1 Under `TestDatasetEligibilityVerdicts`:

Update `test_cubicasa5k_audit_verdict`:
```python
    def test_cubicasa5k_audit_verdict(self, auditor):
        """CubiCasa5K must be ELIGIBLE, non-commercial, with walls, and ~5.09 GB archive."""
        record = auditor.audit_candidate("cubicasa5k")
        assert record.eligibility_verdict == "ELIGIBLE"
        assert record.is_commercial_allowed is False
        assert record.has_wall_annotations is True
        assert math.isclose(record.download_size_gb, 5.09, rel_tol=0.1)
        assert record.download_size_gb < 10.0
        # Hardened check: CubiCasa5K extracted payload (> 10 GB) triggers warning
        assert record.extracted_size_gb > 10.0
        assert record.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w and "extract" in w.lower() for w in record.warnings)
```

Update `test_r2v_audit_verdict_ineligible_gated`:
```python
    def test_r2v_audit_verdict_ineligible_gated(self, auditor):
        """R2V is INELIGIBLE_FOR_AUTOMATED_DOWNLOAD due to required institutional NII IDR agreement."""
        record = auditor.audit_candidate("r2v")
        assert record.eligibility_verdict == "INELIGIBLE_FOR_AUTOMATED_DOWNLOAD"
        assert record.requires_user_agreement is True
        assert record.access_type == "RESTRICTED_APPLICATION"
        # Hardened check: R2V footprint (>= 10 GB) triggers threshold
        assert record.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in record.warnings)
```

### 4.2 Under `TestDiskSafetyAndThresholdGuards`:

Add:
```python
    def test_check_disk_space_negative_required_raises_value_error(self, auditor):
        """check_disk_space must strictly raise ValueError on negative allocations."""
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-1.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-100.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-0.0001)

    def test_10gb_warning_threshold_exact_boundary_hardened(self, auditor):
        """10.0 GB exact boundary triggers user notification under >= comparison."""
        res_exact = auditor.check_download_threshold(size_gb=10.0)
        assert res_exact.warning_triggered is True
        assert res_exact.requires_user_confirmation is True
```

---

## 5. Exact Test Additions Required in `drywall_detection/tests/test_hardware.py`

In `drywall_detection/tests/test_hardware.py`, add unit tests:

### 5.1 Under `TestDiskSafetyGuards`:
```python
    def test_check_disk_safety_negative_required_raises_value_error(self):
        """check_disk_safety rejects negative required space with ValueError."""
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(required_gb=-5.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(required_gb=-0.01)
```

### 5.2 Under `TestTrainingAutoConfiguration`:
```python
    def test_auto_configure_training_none_values_resilience(self):
        """auto_configure_training must withstand dictionary keys containing explicit None values."""
        profiles = [
            {"cuda_available": None, "vram_total_gb": None},
            {"ram_available_gb": None, "ram_total_gb": None},
            {"cpu_logical_cores": None},
            {"cuda_available": None, "vram_total_gb": None, "ram_available_gb": None, "cpu_logical_cores": None},
        ]
        for p in profiles:
            cfg = auto_configure_training(p)
            assert isinstance(cfg, TrainingConfig)
            assert cfg.batch_size in (2, 4, 8, 16)
            assert cfg.img_size in (256, 384, 512)
```

---

## 6. Verification Protocol & Execution Commands

### Verification Command Matrix

| Target | Command | Expected Outcome |
|---|---|---|
| **Auditor & Hardware Suites** | `python -m pytest drywall_detection/tests/test_adversarial_m1.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_hardware.py drywall_detection/tests/test_licensing_audit.py -v` | **100% Pass** (~58 tests, 0 failures) |
| **Coordinate Transformation Suites** | `python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_coords_stress.py -v` | **100% Pass** (~36 tests, 0 failures) |
| **Dataset & Tiling Stress Suites** | `python -m pytest drywall_detection/tests/test_m1_adversarial_stress.py drywall_detection/tests/test_tiling_stitching_stress.py -v` | **100% Pass** (~90 tests, 0 failures) |
| **Unit Suites** | `python -m pytest drywall_detection/tests/unit/ -v` | **100% Pass** (~75 tests, 0 failures) |
| **Comprehensive M1 Regression** | `python -m pytest drywall_detection/tests/ -v` | **100% Pass** (258+ tests, 0 failures) |

### CLI Sanity Checks
```powershell
# 1. Dataset Auditor CLI runner (ensuring zero runtime import warnings)
python -m drywall_detection.audit.dataset_auditor --format json

# 2. Hardware Profiling CLI runner
python -m drywall_detection.utils.hardware
```

---

## 7. Zero-Tolerance Integrity & Regression Checks

1. **Negative Disk Rejection**: Neither `check_disk_safety` nor `check_disk_space` shall ever return `sufficient = True` or `is_safe = True` when passed negative values. `ValueError` must be raised unconditionally.
2. **Crash-Free Hardware Probing**: Passing dictionaries with missing or `None` values shall never raise unhandled exceptions (`TypeError`, `AttributeError`, `ZeroDivisionError`).
3. **Extraction Visibility**: Any dataset whose uncompressed extracted payload exceeds 10 GB (e.g. CubiCasa5K at 20 GB) must trigger explicit notification warnings.
4. **License Immutability**: R2V must remain blocked (`PermissionError: AUTOMATED ACCESS FORBIDDEN`), and SESYD must remain disqualified from wall segmentation (`has_wall_annotations = False`).
