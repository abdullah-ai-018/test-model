# M1 Hardware Hardening Analysis & Blueprint Report

**Author:** `explorer_m1_iter2_1` (M1 Hardware Hardening Explorer)  
**Date:** 2026-11-08  
**Target Module:** `drywall_detection/utils/hardware.py`  
**Referenced Challenger Findings:** Challenger 2 Report (`.agents/teamwork/challenger_m1_2/report.md`), Challenges C1 & C2  
**Status:** COMPLETE (Blueprint Prepared for Implementation by `worker_m1_1`)

---

## 1. Executive Summary

Adversarial stress testing conducted in Milestone M1 identified two critical vulnerabilities in `drywall_detection/utils/hardware.py`:
1. **Challenge C1 (Negative Disk Space Allocation)**: `check_disk_safety()` lacked input validation for non-negative required storage. A negative value (e.g. `-5.0` or `-6.0` GB) artificially inflated mathematical headroom (`0.0 - (-6.0) > 0.0`), reporting `sufficient = True` even on non-existent drives (`Z:\`) or 100% full volumes with 0 bytes free.
2. **Challenge C2 (`NoneType` Dictionary Values)**: `auto_configure_training()` extracted dictionary values using `.get(key, default)`. When upstream APIs or probes supply keys explicitly set to `None` (e.g. `{"vram_total_gb": None}`), Python's `dict.get` returns `None` instead of the fallback default, triggering unhandled `TypeError: float() argument must be a string or a real number, not 'NoneType'`.

This report provides the exact blueprint, safe helper functions, unified diff patch, and comprehensive test suite extensions for `worker_m1_1` to implement without modifying any unrelated modules.

---

## 2. Empirical Root Cause Analysis

### 2.1 Challenge C1: Negative Required Free Disk Space
- **Target File & Function**: `drywall_detection/utils/hardware.py:470`, `check_disk_safety`
- **Observed Behavior**:
  ```python
  from drywall_detection.utils.hardware import check_disk_safety
  check_disk_safety(-5.0)
  # Output: (True, 10.71, 'OK: Sufficient disk space (10.71 GB free).')
  check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
  # Output: (True, 0.0, 'OK: Sufficient disk space (0.00 GB free).')
  ```
- **Code Trace**:
  ```python
  # Line 498 in hardware.py:
  if free_gb < (required_gb + DISK_FREE_MIN_GB):
  ```
  When `required_gb = -6.0` and `DISK_FREE_MIN_GB = 5.0`:
  `required_gb + DISK_FREE_MIN_GB = -6.0 + 5.0 = -1.0 GB`.
  On an empty or non-existent volume where `free_gb = 0.0`, the condition `0.0 < -1.0` evaluates to `False`. The check bypasses failure handling and falls through to line 505:
  `return (True, free_gb, f"OK: Sufficient disk space ({free_gb:.2f} GB free).")`
- **Resolution**:
  Validate `required_free_gb >= 0.0` at function entry. If negative, immediately raise `ValueError("required_free_gb must be non-negative")`. To maintain seamless backward compatibility with existing tests invoking keyword argument `required_gb=...`, support both `required_free_gb` and `required_gb`.

### 2.2 Challenge C2: `NoneType` Dictionary Values in `auto_configure_training`
- **Target File & Function**: `drywall_detection/utils/hardware.py:294`, `auto_configure_training`
- **Observed Behavior**:
  ```python
  from drywall_detection.utils.hardware import auto_configure_training
  auto_configure_training({"cuda_available": True, "vram_total_gb": None})
  # Traceback:
  #   File "hardware.py", line 308, in auto_configure_training
  #     vram_total_gb = float(profile.get("vram_total_gb", 0.0))
  # TypeError: float() argument must be a string or a real number, not 'NoneType'
  ```
- **Code Trace**:
  Lines 306–312:
  ```python
  if isinstance(profile, dict):
      cuda_available = bool(profile.get("cuda_available", False))
      vram_total_gb = float(profile.get("vram_total_gb", 0.0))
      ram_available_gb = float(
          profile.get("ram_available_gb", profile.get("ram_total_gb", 8.0))
      )
      cpu_logical_cores = int(profile.get("cpu_logical_cores", 4))
  ```
  In standard Python dictionary semantics, `dict.get(key, default)` returns `default` **only** if `key not in dict`. If `key in dict` with value `None`, `dict.get` returns `None`. Subsequent `float(None)` and `int(None)` calls fail with `TypeError`.
- **Resolution**:
  Introduce typed, safe `None`-coalescing helper functions (`_safe_float`, `_safe_int`, `_safe_bool`) that explicitly evaluate `val if val is not None else default` prior to type casting. Apply coalescing to both dictionary profiles and dataclass profiles.

---

## 3. Exact Code Blueprint & Modification Details

### 3.1 Addition of Safe Coalescing Helpers (Lines 290–305)

Insert the following helpers immediately preceding `auto_configure_training`:

```python
# ==============================================================================
# SAFE COALESCING HELPERS
# ==============================================================================

def _safe_float(val: Any, default: float) -> float:
    """Safely coalesces None to default before float conversion."""
    return float(val if val is not None else default)


def _safe_int(val: Any, default: int) -> int:
    """Safely coalesces None to default before int conversion."""
    return int(val if val is not None else default)


def _safe_bool(val: Any, default: bool) -> bool:
    """Safely coalesces None to default before bool conversion."""
    return bool(val if val is not None else default)
```

### 3.2 Hardening `auto_configure_training`

Replace lines 306–318 with:

```python
    # Extract values whether profile is HardwareProfile or Dict
    if isinstance(profile, dict):
        cuda_available = _safe_bool(profile.get("cuda_available"), False)
        vram_total_gb = _safe_float(profile.get("vram_total_gb"), 0.0)

        # Coalesce ram_available_gb -> ram_total_gb -> default 8.0
        raw_ram = profile.get("ram_available_gb")
        if raw_ram is None:
            raw_ram = profile.get("ram_total_gb")
        ram_available_gb = _safe_float(raw_ram, 8.0)

        cpu_logical_cores = _safe_int(profile.get("cpu_logical_cores"), 4)
    else:
        cuda_available = _safe_bool(profile.cuda_available, False)
        vram_total_gb = _safe_float(profile.vram_total_gb, 0.0)
        ram_available_gb = _safe_float(profile.ram_available_gb, 8.0)
        cpu_logical_cores = _safe_int(profile.cpu_logical_cores, 4)
```

### 3.3 Hardening `check_disk_safety`

Replace lines 470–506 with:

```python
def check_disk_safety(
    required_free_gb: float = 0.0,
    disk_path: Union[str, Path] = WORKSPACE_ROOT,
    *,
    required_gb: Optional[float] = None,
) -> Tuple[bool, float, str]:
    """
    Checks if sufficient disk space is available for an operation and enforces
    the mandatory notification threshold for operations exceeding 10 GB.

    Args:
        required_free_gb: Required free disk space in gigabytes (must be non-negative).
        disk_path: Path or drive anchor to evaluate.
        required_gb: Backward-compatible keyword alias for required_free_gb.

    Returns:
        (is_safe, free_gb, message)

    Raises:
        ValueError: If required_free_gb (or required_gb) is negative.
    """
    effective_req_gb = (
        float(required_gb) if required_gb is not None else float(required_free_gb)
    )

    if effective_req_gb < 0.0:
        raise ValueError("required_free_gb must be non-negative")

    resolved_disk = Path(disk_path).resolve()
    drive_root = resolved_disk.anchor or str(resolved_disk)
    try:
        usage = shutil.disk_usage(drive_root)
        free_gb = round(usage.free / (1024.0 ** 3), 2)
    except Exception:
        free_gb = 0.0

    if effective_req_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB:
        msg = (
            f"WARNING: Operation requires {effective_req_gb:.2f} GB, which exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
            f"mandatory user notification threshold. Current free space: {free_gb:.2f} GB."
        )
        if free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
            return (False, free_gb, f"REJECTED: {msg} (Insufficient headroom under 5.0 GB safety margin).")
        return (True, free_gb, f"PROCEED_WITH_NOTICE: {msg}")

    if free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
        return (
            False,
            free_gb,
            f"REJECTED: Insufficient disk space ({free_gb:.2f} GB free, requires {effective_req_gb:.2f} GB + {DISK_FREE_MIN_GB:.1f} GB safety margin).",
        )

    return (True, free_gb, f"OK: Sufficient disk space ({free_gb:.2f} GB free).")
```

---

## 4. Machine-Applicable Unified Diff Patch

```diff
--- a/drywall_detection/utils/hardware.py
+++ b/drywall_detection/utils/hardware.py
@@ -290,6 +290,24 @@
 # ==============================================================================
 # DYNAMIC TRAINING CONFIGURATION (5 TIERS)
 # ==============================================================================
+
+def _safe_float(val: Any, default: float) -> float:
+    """Safely coalesces None to default before float conversion."""
+    return float(val if val is not None else default)
+
+
+def _safe_int(val: Any, default: int) -> int:
+    """Safely coalesces None to default before int conversion."""
+    return int(val if val is not None else default)
+
+
+def _safe_bool(val: Any, default: bool) -> bool:
+    """Safely coalesces None to default before bool conversion."""
+    return bool(val if val is not None else default)
+
 
 def auto_configure_training(
     profile: Optional[Union[HardwareProfile, Dict[str, Any]]] = None,
@@ -306,15 +324,19 @@
     # Extract values whether profile is HardwareProfile or Dict
     if isinstance(profile, dict):
-        cuda_available = bool(profile.get("cuda_available", False))
-        vram_total_gb = float(profile.get("vram_total_gb", 0.0))
-        ram_available_gb = float(
-            profile.get("ram_available_gb", profile.get("ram_total_gb", 8.0))
-        )
-        cpu_logical_cores = int(profile.get("cpu_logical_cores", 4))
+        cuda_available = _safe_bool(profile.get("cuda_available"), False)
+        vram_total_gb = _safe_float(profile.get("vram_total_gb"), 0.0)
+
+        raw_ram = profile.get("ram_available_gb")
+        if raw_ram is None:
+            raw_ram = profile.get("ram_total_gb")
+        ram_available_gb = _safe_float(raw_ram, 8.0)
+
+        cpu_logical_cores = _safe_int(profile.get("cpu_logical_cores"), 4)
     else:
-        cuda_available = profile.cuda_available
-        vram_total_gb = profile.vram_total_gb
-        ram_available_gb = profile.ram_available_gb
-        cpu_logical_cores = profile.cpu_logical_cores
+        cuda_available = _safe_bool(profile.cuda_available, False)
+        vram_total_gb = _safe_float(profile.vram_total_gb, 0.0)
+        ram_available_gb = _safe_float(profile.ram_available_gb, 8.0)
+        cpu_logical_cores = _safe_int(profile.cpu_logical_cores, 4)
 
     # Tier 1: High-End Dedicated GPU (VRAM >= 14 GB)
@@ -470,7 +492,8 @@
 # ==============================================================================
 # DISK SPACE SAFETY CHECK
 # ==============================================================================
 
 def check_disk_safety(
-    required_gb: float,
+    required_free_gb: float = 0.0,
     disk_path: Union[str, Path] = WORKSPACE_ROOT,
+    *,
+    required_gb: Optional[float] = None,
 ) -> Tuple[bool, float, str]:
     """
     Checks if sufficient disk space is available for an operation and enforces
     the mandatory notification threshold for operations exceeding 10 GB.
 
+    Args:
+        required_free_gb: Required free disk space in gigabytes (must be non-negative).
+        disk_path: Target path or drive anchor to evaluate.
+        required_gb: Backward-compatible keyword alias for required_free_gb.
+
     Returns:
         (is_safe, free_gb, message)
+
+    Raises:
+        ValueError: If required_free_gb (or required_gb) is negative.
     """
+    effective_req_gb = (
+        float(required_gb) if required_gb is not None else float(required_free_gb)
+    )
+
+    if effective_req_gb < 0.0:
+        raise ValueError("required_free_gb must be non-negative")
+
     resolved_disk = Path(disk_path).resolve()
     drive_root = resolved_disk.anchor or str(resolved_disk)
     try:
@@ -488,19 +514,19 @@
         free_gb = 0.0
 
-    if required_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB:
+    if effective_req_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB:
         msg = (
-            f"WARNING: Operation requires {required_gb:.2f} GB, which exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
+            f"WARNING: Operation requires {effective_req_gb:.2f} GB, which exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
             f"mandatory user notification threshold. Current free space: {free_gb:.2f} GB."
         )
-        if free_gb < (required_gb + DISK_FREE_MIN_GB):
+        if free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
             return (False, free_gb, f"REJECTED: {msg} (Insufficient headroom under 5.0 GB safety margin).")
         return (True, free_gb, f"PROCEED_WITH_NOTICE: {msg}")
 
-    if free_gb < (required_gb + DISK_FREE_MIN_GB):
+    if free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
         return (
             False,
             free_gb,
-            f"REJECTED: Insufficient disk space ({free_gb:.2f} GB free, requires {required_gb:.2f} GB + {DISK_FREE_MIN_GB:.1f} GB safety margin).",
+            f"REJECTED: Insufficient disk space ({free_gb:.2f} GB free, requires {effective_req_gb:.2f} GB + {DISK_FREE_MIN_GB:.1f} GB safety margin).",
         )
 
     return (True, free_gb, f"OK: Sufficient disk space ({free_gb:.2f} GB free).")
```

---

## 5. Test Suite Extensions & Assertions

### 5.1 Unit Tests for `drywall_detection/tests/test_hardware.py`

Append the following test methods to `TestDiskSafetyGuards` and `TestTrainingAutoConfiguration`:

```python
    def test_check_disk_safety_negative_raises_value_error(self):
        """Negative required space must raise ValueError."""
        for neg_val in [-0.0001, -1.0, -10.0, -999.0]:
            with pytest.raises(ValueError, match="required_free_gb must be non-negative"):
                check_disk_safety(neg_val)
            with pytest.raises(ValueError, match="required_free_gb must be non-negative"):
                check_disk_safety(required_free_gb=neg_val)
            with pytest.raises(ValueError, match="required_free_gb must be non-negative"):
                check_disk_safety(required_gb=neg_val)

    def test_check_disk_safety_zero_is_valid(self):
        """Zero required space is valid non-negative boundary condition."""
        is_safe, free_gb, msg = check_disk_safety(0.0)
        assert isinstance(is_safe, bool)
        assert free_gb >= 0.0

    def test_auto_configure_training_none_coalescing(self):
        """Explicit None values in hardware dictionary coalesce safely to defaults."""
        # 1. VRAM None -> defaults to 0.0 (Tier 3 low GPU if cuda True)
        cfg1 = auto_configure_training({"cuda_available": True, "vram_total_gb": None})
        assert cfg1.hardware_tier == 3
        assert cfg1.batch_size == 2
        assert cfg1.img_size == 256

        # 2. RAM available None -> falls back to 8.0 default (Tier 4 CPU)
        cfg2 = auto_configure_training({"cuda_available": False, "ram_available_gb": None})
        assert cfg2.hardware_tier == 4
        assert cfg2.device == "cpu"
        assert cfg2.batch_size == 4

        # 3. RAM available None falls back to specified ram_total_gb (1.5 GB -> Tier 5)
        cfg3 = auto_configure_training({
            "cuda_available": False,
            "ram_available_gb": None,
            "ram_total_gb": 1.5,
        })
        assert cfg3.hardware_tier == 5
        assert cfg3.device == "cpu"
        assert cfg3.batch_size == 2

        # 4. CPU logical cores None -> defaults to 4
        cfg4 = auto_configure_training({
            "cuda_available": True,
            "vram_total_gb": 16.0,
            "cpu_logical_cores": None,
        })
        assert cfg4.hardware_tier == 1
        assert cfg4.num_workers == 4

        # 5. Empty dictionary
        cfg5 = auto_configure_training({})
        assert cfg5.hardware_tier == 4
        assert cfg5.device == "cpu"

        # 6. All keys explicitly None
        cfg6 = auto_configure_training({
            "cuda_available": None,
            "vram_total_gb": None,
            "ram_available_gb": None,
            "ram_total_gb": None,
            "cpu_logical_cores": None,
        })
        assert cfg6.hardware_tier == 4
        assert cfg6.device == "cpu"
```

### 5.2 Transition in `drywall_detection/tests/test_adversarial_m1.py`

When the fix is applied, Challenger 2's vulnerability assertion tests will be updated as follows:
- In `test_negative_required_gb_bypasses_headroom_check`:
  Change `safe, free, msg = check_disk_safety(-6.0, ...)` to:
  ```python
  with pytest.raises(ValueError, match="required_free_gb must be non-negative"):
      check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")
  ```
- In `test_explicit_none_dictionary_crash`:
  Change `with pytest.raises(TypeError):` to asserting success:
  ```python
  cfg1 = auto_configure_training({"cuda_available": True, "vram_total_gb": None})
  assert cfg1.hardware_tier == 3
  cfg2 = auto_configure_training({"cuda_available": False, "ram_available_gb": None})
  assert cfg2.hardware_tier == 4
  cfg3 = auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
  assert cfg3.hardware_tier == 1
  ```

---

## 6. Implementation & Verification Command

To independently verify the blueprint once implemented by `worker_m1_1`:
```powershell
python -m pytest drywall_detection/tests/test_hardware.py -v
python -m pytest drywall_detection/tests/test_adversarial_m1.py -v
```
Expected output: All hardware tests pass cleanly with zero uncaught exceptions and 100% boundary guard coverage.
