# Technical Blueprint: Hardening `drywall_detection.audit` (Milestone M1 Iteration 2)

**Author:** `explorer_m1_iter2_2` (M1 Auditor Hardening Explorer)  
**Date:** 2026-11-08  
**Scope:** `drywall_detection/audit/dataset_auditor.py` and `drywall_detection/audit/__init__.py`  
**Target Files:**
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\audit\dataset_auditor.py`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\audit\__init__.py`

---

## 1. Executive Summary

Adversarial testing by `challenger_m1_2` and code review by `reviewer_m1_2` identified four concrete edge cases in the dataset auditing module:
1. **Negative Required Disk Space Bypass**: Supplying a negative allocation (e.g. `required_gb = -5.0`) produces artificial headroom, causing `check_disk_space()` to return `sufficient=True` even on non-existent or 100% full drives.
2. **CubiCasa5K Extracted Payload Threshold Omission**: CubiCasa5K uncompressed payload is 21.47 GB (~20.0 GB), yet `audit_candidate("cubicasa5k")` only compared archive download size (5.09 GB), omitting the mandatory 10 GB notification warning required by `config.py`.
3. **R2V 10.00 GB Boundary Mismatch**: R2V archive size is exactly $10 \times 1024^3 = 10,737,418,240$ bytes ($10.000000$ GB). Strict inequality (`> 10.0`) failed to trigger the threshold check despite the `# >10 GB` specification intent.
4. **Python `runpy` `RuntimeWarning` on CLI Invocation**: Eager imports inside `drywall_detection/audit/__init__.py` pre-populate `sys.modules['drywall_detection.audit.dataset_auditor']`, causing Python `runpy` to emit a benign but noisy `RuntimeWarning` when executing `python -m drywall_detection.audit.dataset_auditor`.

This document provides the exact code modifications, unified diffs, and test assertions to completely harden `dataset_auditor.py` and `audit/__init__.py`.

---

## 2. Root Cause Analysis & Architectural Design

### Fix 1: Negative Required Space Guard in `check_disk_space`
- **Location**: `drywall_detection/audit/dataset_auditor.py`, `check_disk_space()` (lines 528-565).
- **Vulnerability**: In `dataset_auditor.py`:
  ```python
  elif (free_gb - req_dl_gb) < min_headroom_gb:
  ```
  When `required_gb_or_id = -5.0`, `req_dl_gb = -5.0`. Then `0.0 - (-5.0) = +5.0 GB >= 2.0 GB headroom`, returning `sufficient_space = True` on full or non-existent volumes.
- **Architectural Fix**: Add an explicit validation guard at the entry of `check_disk_space()`. If `required_gb_or_id` is numeric (or numeric string) and $< 0.0$, immediately raise:
  ```python
  raise ValueError("required_gb must be non-negative")
  ```
  Additionally, validate that if a dataset ID is passed, `spec.raw_size_bytes >= 0` and `spec.extracted_size_bytes >= 0`.

### Fix 2: Dual Threshold Evaluation (Archive & Extracted) in `audit_candidate` and `check_disk_space`
- **Location**: `drywall_detection/audit/dataset_auditor.py`, `check_disk_space()` and `audit_candidate()` (lines 555-602, 703-740).
- **Vulnerability**: `check_disk_space()` previously set `req_ext_b = 0` when `include_extracted=False`, and only checked `req_dl_gb > self.max_unannounced_gb`. `audit_candidate()` evaluated only `disk_res.exceeds_10gb_threshold` based on raw download size. CubiCasa5K has `raw_size_gb = 5.09 GB` and `extracted_size_gb = 20.00 GB` ($21,474,836,480$ bytes). Because only raw size was evaluated, no warning was emitted.
- **Architectural Fix**:
  1. In `check_disk_space()`, always populate `req_ext_b = spec.extracted_size_bytes` when called with a dataset ID so that `DiskAuditResult.required_extracted_bytes` accurately reflects the payload.
  2. Set `exceeds_10gb = (req_dl_gb >= self.max_unannounced_gb) or (req_ext_gb >= self.max_unannounced_gb)`.
  3. In `audit_candidate()`, evaluate both `spec.raw_size_gb` and `spec.extracted_size_gb` against `self.max_unannounced_gb`:
     ```python
     if spec.raw_size_gb >= self.max_unannounced_gb:
         warnings.append(
             f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB user notification threshold."
         )
     if spec.extracted_size_gb >= self.max_unannounced_gb:
         warnings.append(
             f"LARGE PAYLOAD: Extracted size ({spec.extracted_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB notification threshold."
         )
     ```
  4. In `DiskAuditResult.warning_message`, generate descriptive threshold alert text if `exceeds_10gb` is triggered by download size, extracted payload, or both.

### Fix 3: R2V 10.00 GB Boundary Precision Check
- **Location**: `drywall_detection/audit/dataset_auditor.py`, `check_disk_space()`, line 568.
- **Vulnerability**: R2V `raw_size_bytes = 10_737_418_240` ($10.000000$ GB). With strict `> 10.0`, `10.0 > 10.0` is `False`.
- **Architectural Fix**:
  Use `>= self.max_unannounced_gb` in both `check_disk_space()` and `audit_candidate()`.
  This guarantees that exact 10.000 GB boundaries (such as R2V's archive download and extracted payload) correctly evaluate to `exceeds_10gb_threshold = True` and emit the mandatory notification warning.
  *(Note: `check_download_threshold(size_gb, threshold_gb)` remains `size_gb > threshold_gb` to adhere to `test_10gb_warning_threshold_exact_boundary` where `10.0` is documented as the exact upper bound before triggering).*

### Fix 4: Lazy Loading via PEP 562 `__getattr__` in `audit/__init__.py`
- **Location**: `drywall_detection/audit/__init__.py`.
- **Vulnerability**:
  ```python
  from drywall_detection.audit.dataset_auditor import (DatasetAuditor, ...)
  ```
  When invoked via `python -m drywall_detection.audit.dataset_auditor`, Python loads the parent package `drywall_detection.audit`, which executes `__init__.py`. This eagerly imports `dataset_auditor.py` into `sys.modules`. Next, `runpy` detects that the module to be executed as `__main__` is already in `sys.modules`, emitting:
  ```
  RuntimeWarning: 'drywall_detection.audit.dataset_auditor' found in sys.modules after import of package 'drywall_detection.audit', but prior to execution of 'drywall_detection.audit.dataset_auditor'; this may result in unpredictable behaviour
  ```
- **Architectural Fix**: Mirror the pattern successfully employed in `drywall_detection/utils/__init__.py`. Replace eager imports with PEP 562 `__getattr__(name)` and `__dir__()`:
  ```python
  __all__ = [...]
  def __getattr__(name: str) -> Any:
      if name in __all__:
          import drywall_detection.audit.dataset_auditor as _mod
          return getattr(_mod, name)
      raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
  def __dir__() -> List[str]:
      return __all__
  ```
  When the module is run as CLI via `-m`, `drywall_detection.audit` initializes without importing `dataset_auditor`, eliminating the warning entirely while preserving 100% backward compatibility for all facade imports.

---

## 3. Exact Code Blueprints & Unified Diffs

### Target File 1: `drywall_detection/audit/__init__.py`

#### Complete Proposed Replacement Content
```python
"""
Dataset audit and licensing compliance module.
Exports are lazily loaded via __getattr__ to prevent runpy shadowing
and RuntimeWarnings during CLI execution (e.g. python -m drywall_detection.audit.dataset_auditor).
"""

from typing import Any, List

__all__: List[str] = [
    "DatasetAuditor",
    "DatasetEligibility",
    "LicenseCategory",
    "DownloadMechanism",
    "DatasetSpec",
    "DiskAuditResult",
    "DiskCheckResult",
    "DatasetAuditResult",
    "DatasetAuditRecord",
    "DownloadThresholdResult",
    "LicenseValidationResult",
    "AuditReport",
    "CANDIDATE_DATASETS",
    "AuditStatus",
    "CommercialStatus",
    "AccessModel",
    "DatasetLicenseInfo",
    "DatasetLicensingAuditor",
]


def __getattr__(name: str) -> Any:
    """Lazily load symbols from dataset_auditor upon attribute access."""
    if name in __all__:
        import drywall_detection.audit.dataset_auditor as _mod
        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    """Support dir() and autocompletion for lazily exported symbols."""
    return __all__
```

#### Unified Diff for `drywall_detection/audit/__init__.py`
```diff
--- a/drywall_detection/audit/__init__.py
+++ b/drywall_detection/audit/__init__.py
@@ -1,37 +1,41 @@
 """
 Dataset audit and licensing compliance module.
+Exports are lazily loaded via __getattr__ to prevent runpy shadowing
+and RuntimeWarnings during CLI execution (e.g. python -m drywall_detection.audit.dataset_auditor).
 """
 
-from drywall_detection.audit.dataset_auditor import (
-    DatasetAuditor,
-    DatasetEligibility,
-    LicenseCategory,
-    DownloadMechanism,
-    DatasetSpec,
-    DiskAuditResult,
-    DatasetAuditResult,
-    AuditReport,
-    CANDIDATE_DATASETS,
-    AuditStatus,
-    CommercialStatus,
-    AccessModel,
-    DatasetLicenseInfo,
-    DatasetLicensingAuditor,
-)
+from typing import Any, List
 
-__all__ = [
+__all__: List[str] = [
     "DatasetAuditor",
     "DatasetEligibility",
     "LicenseCategory",
     "DownloadMechanism",
     "DatasetSpec",
     "DiskAuditResult",
+    "DiskCheckResult",
     "DatasetAuditResult",
+    "DatasetAuditRecord",
+    "DownloadThresholdResult",
+    "LicenseValidationResult",
     "AuditReport",
     "CANDIDATE_DATASETS",
     "AuditStatus",
     "CommercialStatus",
     "AccessModel",
     "DatasetLicenseInfo",
     "DatasetLicensingAuditor",
 ]
+
+
+def __getattr__(name: str) -> Any:
+    """Lazily load symbols from dataset_auditor upon attribute access."""
+    if name in __all__:
+        import drywall_detection.audit.dataset_auditor as _mod
+        return getattr(_mod, name)
+    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
+
+
+def __dir__() -> List[str]:
+    """Support dir() and autocompletion for lazily exported symbols."""
+    return __all__
```

---

### Target File 2: `drywall_detection/audit/dataset_auditor.py`

#### Modification 1: `check_disk_space()` Hardening (Lines 528–615)
Add negative `required_gb` guard, retain `spec.extracted_size_bytes` in `req_ext_b`, and check `>= self.max_unannounced_gb` across download and extracted sizes.

```python
<<<< BEFORE
    def check_disk_space(
        self,
        required_gb_or_id: Union[float, int, str],
        target_path: Optional[Union[str, Path]] = None,
        min_headroom_gb: float = 2.0,
        include_extracted: bool = False,
    ) -> DiskAuditResult:
        """
        Inspects available disk storage against dataset download or specified byte requirements.
        Supports calling with dataset_id (str) or raw required_gb (float/int).
        """
        target_dir = Path(target_path or self.target_download_dir).resolve()
        check_path = target_dir
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        drive_root = check_path.anchor or str(check_path)
        try:
            usage = shutil.disk_usage(drive_root)
            total_b = usage.total
            free_b = usage.free
        except Exception:
            total_b = 0
            free_b = 0

        free_gb = free_b / (1024.0 ** 3)

        if isinstance(required_gb_or_id, str):
            spec = self.get_spec(required_gb_or_id)
            req_dl_b = spec.raw_size_bytes
            req_ext_b = spec.extracted_size_bytes if include_extracted else 0
        else:
            req_dl_b = int(float(required_gb_or_id) * (1024.0 ** 3))
            req_ext_b = 0

        req_dl_gb = req_dl_b / (1024.0 ** 3)
        req_ext_gb = req_ext_b / (1024.0 ** 3)
        total_req_gb = req_dl_gb + req_ext_gb

        # Check conditions
        exceeds_10gb = req_dl_gb > self.max_unannounced_gb

        # Condition 1: Can we even fit the download?
        if free_gb < req_dl_gb:
            is_sufficient = False
            msg = (
                f"CRITICAL: Insufficient disk space for download. "
                f"Free: {free_gb:.2f} GB, Required download: {req_dl_gb:.2f} GB."
            )
        # Condition 2: Does it violate the minimum headroom?
        elif (free_gb - req_dl_gb) < min_headroom_gb:
            is_sufficient = False
            msg = (
                f"REJECTED: Disk space headroom violation. "
                f"Free: {free_gb:.2f} GB, Required: {req_dl_gb:.2f} GB. "
                f"Post-download headroom ({free_gb - req_dl_gb:.2f} GB) is less than required {min_headroom_gb:.1f} GB safety margin."
            )
        # Condition 3: Can it fit extraction if requested?
        elif include_extracted and (free_gb - total_req_gb) < min_headroom_gb:
            is_sufficient = True
            msg = (
                f"WARNING: Disk space sufficient for archive download ({req_dl_gb:.2f} GB), "
                f"but insufficient headroom for full extraction ({req_ext_gb:.2f} GB). Free: {free_gb:.2f} GB."
            )
        else:
            is_sufficient = True
            msg = f"OK: Sufficient disk space ({free_gb:.2f} GB free, {free_gb - req_dl_gb:.2f} GB post-download headroom)."

        if exceeds_10gb:
            threshold_msg = (
                f" ALERT: Download size ({req_dl_gb:.2f} GB) exceeds 10 GB limit. "
                "Explicit user confirmation required."
            )
            msg += threshold_msg

        return DiskAuditResult(
==== AFTER
    def check_disk_space(
        self,
        required_gb_or_id: Union[float, int, str],
        target_path: Optional[Union[str, Path]] = None,
        min_headroom_gb: float = 2.0,
        include_extracted: bool = False,
    ) -> DiskAuditResult:
        """
        Inspects available disk storage against dataset download or specified byte requirements.
        Supports calling with dataset_id (str) or raw required_gb (float/int).
        """
        # Explicit guard against negative required disk space
        if isinstance(required_gb_or_id, (int, float)):
            if float(required_gb_or_id) < 0.0:
                raise ValueError("required_gb must be non-negative")
        elif isinstance(required_gb_or_id, str):
            try:
                numeric_val = float(required_gb_or_id)
                if numeric_val < 0.0:
                    raise ValueError("required_gb must be non-negative")
            except ValueError as e:
                if str(e) == "required_gb must be non-negative":
                    raise
                # Non-numeric string, handled below as candidate dataset_id
        else:
            try:
                numeric_val = float(required_gb_or_id)
                if numeric_val < 0.0:
                    raise ValueError("required_gb must be non-negative")
            except ValueError as e:
                if str(e) == "required_gb must be non-negative":
                    raise

        target_dir = Path(target_path or self.target_download_dir).resolve()
        check_path = target_dir
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        drive_root = check_path.anchor or str(check_path)
        try:
            usage = shutil.disk_usage(drive_root)
            total_b = usage.total
            free_b = usage.free
        except Exception:
            total_b = 0
            free_b = 0

        free_gb = free_b / (1024.0 ** 3)

        if isinstance(required_gb_or_id, str):
            spec = self.get_spec(required_gb_or_id)
            if spec.raw_size_bytes < 0 or spec.extracted_size_bytes < 0:
                raise ValueError("required_gb must be non-negative")
            req_dl_b = spec.raw_size_bytes
            req_ext_b = spec.extracted_size_bytes
        else:
            req_dl_b = int(float(required_gb_or_id) * (1024.0 ** 3))
            req_ext_b = 0

        req_dl_gb = req_dl_b / (1024.0 ** 3)
        req_ext_gb = req_ext_b / (1024.0 ** 3)
        effective_ext_gb = req_ext_gb if include_extracted else 0.0
        total_req_gb = req_dl_gb + effective_ext_gb

        # Check threshold conditions (>= ensures exact 10.00 GB triggers threshold)
        exceeds_10gb = (req_dl_gb >= self.max_unannounced_gb) or (req_ext_gb >= self.max_unannounced_gb)

        # Condition 1: Can we even fit the download?
        if free_gb < req_dl_gb:
            is_sufficient = False
            msg = (
                f"CRITICAL: Insufficient disk space for download. "
                f"Free: {free_gb:.2f} GB, Required download: {req_dl_gb:.2f} GB."
            )
        # Condition 2: Does it violate the minimum headroom?
        elif (free_gb - req_dl_gb) < min_headroom_gb:
            is_sufficient = False
            msg = (
                f"REJECTED: Disk space headroom violation. "
                f"Free: {free_gb:.2f} GB, Required: {req_dl_gb:.2f} GB. "
                f"Post-download headroom ({free_gb - req_dl_gb:.2f} GB) is less than required {min_headroom_gb:.1f} GB safety margin."
            )
        # Condition 3: Can it fit extraction if requested?
        elif include_extracted and (free_gb - total_req_gb) < min_headroom_gb:
            is_sufficient = True
            msg = (
                f"WARNING: Disk space sufficient for archive download ({req_dl_gb:.2f} GB), "
                f"but insufficient headroom for full extraction ({req_ext_gb:.2f} GB). Free: {free_gb:.2f} GB."
            )
        else:
            is_sufficient = True
            msg = f"OK: Sufficient disk space ({free_gb:.2f} GB free, {free_gb - req_dl_gb:.2f} GB post-download headroom)."

        if exceeds_10gb:
            threshold_reasons = []
            if req_dl_gb >= self.max_unannounced_gb:
                threshold_reasons.append(f"download size ({req_dl_gb:.2f} GB)")
            if req_ext_gb >= self.max_unannounced_gb:
                threshold_reasons.append(f"extracted payload size ({req_ext_gb:.2f} GB)")
            threshold_msg = (
                f" ALERT: Payload {' and '.join(threshold_reasons)} exceeds {self.max_unannounced_gb:.0f} GB limit. "
                "Explicit user confirmation required."
            )
            msg += threshold_msg

        return DiskAuditResult(
>>>>
```

#### Modification 2: `audit_candidate()` Hardening (Lines 731–740)
Update threshold evaluation in `audit_candidate` to check both `spec.raw_size_gb` and `spec.extracted_size_gb` using `>= self.max_unannounced_gb`.

```python
<<<< BEFORE
        # 3. Disk safety check
        if not disk_res.is_sufficient:
            blockers.append(f"DISK SAFETY: {disk_res.message}")

        if disk_res.exceeds_10gb_threshold:
            warnings.append(
                f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds 10 GB user notification threshold."
            )

        # 4. Optional network probing
==== AFTER
        # 3. Disk safety check
        if not disk_res.is_sufficient:
            blockers.append(f"DISK SAFETY: {disk_res.message}")

        # Evaluate both archive download and extracted payload size against 10 GB threshold
        if spec.raw_size_gb >= self.max_unannounced_gb:
            warnings.append(
                f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB user notification threshold."
            )
        if spec.extracted_size_gb >= self.max_unannounced_gb:
            warnings.append(
                f"LARGE PAYLOAD: Extracted size ({spec.extracted_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB notification threshold."
            )

        # 4. Optional network probing
>>>>
```

#### Complete Unified Diff for `drywall_detection/audit/dataset_auditor.py`
```diff
--- a/drywall_detection/audit/dataset_auditor.py
+++ b/drywall_detection/audit/dataset_auditor.py
@@ -537,6 +537,25 @@
         Inspects available disk storage against dataset download or specified byte requirements.
         Supports calling with dataset_id (str) or raw required_gb (float/int).
         """
+        # Explicit guard against negative required disk space
+        if isinstance(required_gb_or_id, (int, float)):
+            if float(required_gb_or_id) < 0.0:
+                raise ValueError("required_gb must be non-negative")
+        elif isinstance(required_gb_or_id, str):
+            try:
+                numeric_val = float(required_gb_or_id)
+                if numeric_val < 0.0:
+                    raise ValueError("required_gb must be non-negative")
+            except ValueError as e:
+                if str(e) == "required_gb must be non-negative":
+                    raise
+                # Non-numeric string, handled below as candidate dataset_id
+        else:
+            try:
+                numeric_val = float(required_gb_or_id)
+                if numeric_val < 0.0:
+                    raise ValueError("required_gb must be non-negative")
+            except ValueError as e:
+                if str(e) == "required_gb must be non-negative":
+                    raise
+
         target_dir = Path(target_path or self.target_download_dir).resolve()
         check_path = target_dir
         while not check_path.exists() and check_path.parent != check_path:
@@ -555,17 +574,20 @@
         if isinstance(required_gb_or_id, str):
             spec = self.get_spec(required_gb_or_id)
+            if spec.raw_size_bytes < 0 or spec.extracted_size_bytes < 0:
+                raise ValueError("required_gb must be non-negative")
             req_dl_b = spec.raw_size_bytes
-            req_ext_b = spec.extracted_size_bytes if include_extracted else 0
+            req_ext_b = spec.extracted_size_bytes
         else:
             req_dl_b = int(float(required_gb_or_id) * (1024.0 ** 3))
             req_ext_b = 0
 
         req_dl_gb = req_dl_b / (1024.0 ** 3)
         req_ext_gb = req_ext_b / (1024.0 ** 3)
-        total_req_gb = req_dl_gb + req_ext_gb
+        effective_ext_gb = req_ext_gb if include_extracted else 0.0
+        total_req_gb = req_dl_gb + effective_ext_gb
 
-        # Check conditions
-        exceeds_10gb = req_dl_gb > self.max_unannounced_gb
+        # Check threshold conditions (>= ensures exact 10.00 GB triggers threshold)
+        exceeds_10gb = (req_dl_gb >= self.max_unannounced_gb) or (req_ext_gb >= self.max_unannounced_gb)
 
         # Condition 1: Can we even fit the download?
         if free_gb < req_dl_gb:
@@ -594,8 +616,14 @@
             msg = f"OK: Sufficient disk space ({free_gb:.2f} GB free, {free_gb - req_dl_gb:.2f} GB post-download headroom)."
 
         if exceeds_10gb:
-            threshold_msg = (
-                f" ALERT: Download size ({req_dl_gb:.2f} GB) exceeds 10 GB limit. "
-                "Explicit user confirmation required."
-            )
+            threshold_reasons = []
+            if req_dl_gb >= self.max_unannounced_gb:
+                threshold_reasons.append(f"download size ({req_dl_gb:.2f} GB)")
+            if req_ext_gb >= self.max_unannounced_gb:
+                threshold_reasons.append(f"extracted payload size ({req_ext_gb:.2f} GB)")
+            threshold_msg = (
+                f" ALERT: Payload {' and '.join(threshold_reasons)} exceeds {self.max_unannounced_gb:.0f} GB limit. "
+                "Explicit user confirmation required."
+            )
             msg += threshold_msg
 
         return DiskAuditResult(
@@ -732,9 +760,14 @@
         if not disk_res.is_sufficient:
             blockers.append(f"DISK SAFETY: {disk_res.message}")
 
-        if disk_res.exceeds_10gb_threshold:
+        # Evaluate both archive download and extracted payload size against 10 GB threshold
+        if spec.raw_size_gb >= self.max_unannounced_gb:
             warnings.append(
-                f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds 10 GB user notification threshold."
+                f"LARGE DOWNLOAD: Archive size ({spec.raw_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB user notification threshold."
+            )
+        if spec.extracted_size_gb >= self.max_unannounced_gb:
+            warnings.append(
+                f"LARGE PAYLOAD: Extracted size ({spec.extracted_size_gb:.2f} GB) exceeds {self.max_unannounced_gb:.0f} GB notification threshold."
             )
 
         # 4. Optional network probing
```

---

## 4. Test Assertions & Regression Hardening

To independently verify all four fixes and ensure zero regression across M1, the following assertions should be verified:

### 1. Negative Required Disk Space Raises `ValueError`
```python
def test_negative_required_disk_space_raises_value_error(auditor):
    """Negative required GB must immediately raise ValueError('required_gb must be non-negative')."""
    import pytest
    with pytest.raises(ValueError, match="required_gb must be non-negative"):
        auditor.check_disk_space(-5.0)

    with pytest.raises(ValueError, match="required_gb must be non-negative"):
        auditor.check_disk_space(-0.001)

    with pytest.raises(ValueError, match="required_gb must be non-negative"):
        auditor.check_disk_space("-10.0")
```

### 2. CubiCasa5K Extracted Payload Triggers 10 GB Threshold Warning
```python
def test_cubicasa5k_triggers_extracted_payload_warning(auditor):
    """CubiCasa5K (20 GB extracted) must trigger threshold warning despite 5.09 GB archive."""
    res = auditor.audit_candidate("cubicasa5k")
    assert res.dataset_spec.extracted_size_gb >= 10.0
    assert res.disk_audit.exceeds_10gb_threshold is True
    assert any("LARGE PAYLOAD" in w and "20.00 GB" in w for w in res.warnings)
```

### 3. R2V Exact 10.00 GB Boundary Triggers Threshold
```python
def test_r2v_exact_boundary_triggers_threshold(auditor):
    """R2V (exactly 10.000 GB download) triggers threshold warning using >= check."""
    disk_res = auditor.check_disk_space("r2v")
    assert disk_res.exceeds_10gb_threshold is True

    res = auditor.audit_candidate("r2v")
    assert any("LARGE DOWNLOAD" in w and "10.00 GB" in w for w in res.warnings)
    assert any("LARGE PAYLOAD" in w and "20.00 GB" in w for w in res.warnings)
```

### 4. Zero `RuntimeWarning` from `drywall_detection/audit/__init__.py`
```python
def test_audit_module_lazy_import_no_runpy_warning():
    """Running dataset_auditor as CLI must emit zero RuntimeWarnings from runpy."""
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-m", "drywall_detection.audit.dataset_auditor", "--format", "table"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "RuntimeWarning" not in proc.stderr
```

### 5. Backward Compatibility of Facade Exports in `drywall_detection.audit`
```python
def test_audit_facade_lazy_exports():
    """All symbols in __all__ must remain accessible via attribute access."""
    import drywall_detection.audit as audit
    assert hasattr(audit, "DatasetAuditor")
    assert hasattr(audit, "DatasetEligibility")
    assert hasattr(audit, "DatasetLicensingAuditor")
    assert audit.DatasetAuditor is not None
```

---

## 5. Verification Commands

The implementer (`worker_m1_1`) can verify these fixes using the following commands:

```powershell
# 1. Run the audit test suite
python -m pytest drywall_detection/tests/test_audit.py -v

# 2. Run the adversarial test suite
python -m pytest drywall_detection/tests/test_adversarial_m1.py -v

# 3. Run the licensing audit test suite
python -m pytest drywall_detection/tests/test_licensing_audit.py -v

# 4. Verify CLI execution emits zero warnings
python -W error::RuntimeWarning -m drywall_detection.audit.dataset_auditor --format table
```

---

## 6. Implementation Risk & Impact Assessment

| Risk | Level | Mitigation |
|---|---|---|
| Breakage of existing `test_audit.py` boundary tests | None | `check_download_threshold(10.0)` is preserved as strictly `> 10.0` for scalar calls, while dataset spec evaluations use `>= 10.0` to capture exact 10 GB packages. |
| Facade breakage in `test_licensing_audit.py` | None | `__getattr__` and `__dir__` fully implement PEP 562, dynamically resolving all 17 registered classes and aliases. |
| Downstream M2 ingestion impact | Positive | Guarantees that download operations will never bypass disk headroom checks with negative numbers and that CubiCasa5K/R2V large footprints are properly flagged before download. |
