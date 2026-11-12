# Investigation Report: Review Lock Protocol & CSV Schema Hardening (Failures 3, 4, 5)

**Author:** `explorer_m3_iter2_2` (Review Lock & CSV Validation Explorer)  
**Date:** 2026-11-08  
**Scope:** `drywall_detection/vector/schedule_parser.py` (`export_and_enforce_review_lock`)  
**Target Vulnerabilities:** Failures 3, 4, and 5 from `drywall_detection/tests/test_adversarial_m3.py`

---

## 1. Executive Summary

Milestone M3 Iteration 1 adversarial testing revealed 5 security and safety vulnerabilities. This investigation focuses on **Failures 3, 4, and 5**, which reside in the human-in-the-loop review lock protocol within `drywall_detection/vector/schedule_parser.py`:

| Vulnerability | Test Name | Mechanism | Security Impact |
|---|---|---|---|
| **Failure 3: Empty (0-byte) CSV Bypass** | `test_empty_approved_csv_must_not_bypass_lock` | `appr_csv.exists()` was evaluated without checking `stat().st_size == 0`. An empty file iterated 0 times, unlinked the lockfile, and returned `True`. | Critical review bypass: An empty file unblocks downstream execution without human approval. |
| **Failure 4: Invalid/Corrupted Header Bypass** | `test_invalid_header_approved_csv_must_not_bypass_lock` | Lack of header schema validation allowed arbitrary column names (e.g. `random_col1,random_col2`). Missing `"tag"` column resulted in 0 inspections, unlinking the lockfile and returning `True`. | Arbitrary or corrupted files unblock downstream pipeline execution. |
| **Failure 5: Omitted Detail 1A Row Bypass** | `test_missing_detail_1a_row_must_not_bypass_lock` | Iteration loop did not enforce mandatory presence of Detail 1A. A CSV omitting row `1A` bypassed the CMU safety inspection completely. | Safety veto circumvented: Downstream code executes without verified CMU block veto. |
| **Critical Regression Discovered** | `test_valid_approved_csv_removes_existing_lockfile` & `test_schedule.py` | Attempted fix used substring search `any(kw in cls_val for kw in ("drywall", ...))`. Since `"drywall"` is a substring of `"non-drywall"`, legitimate `"Non-Drywall"` approved CSVs failed with `ValueError`. | Pipeline deadlocked: Valid approved files could never be consumed. |

---

## 2. Root Cause Analysis

### 2.1 Failure 3: 0-Byte Approved CSV Bypass
In `drywall_detection/vector/schedule_parser.py`:
```python
if appr_csv.exists():
    with open(appr_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ...
    if lock_file.exists():
        lock_file.unlink()
    return True
```
- When `appr_csv` is an empty (0-byte) file, `appr_csv.exists()` evaluates to `True`.
- `csv.DictReader` encounters EOF immediately.
- The `for row in reader:` loop executes 0 times.
- Execution reaches `if lock_file.exists(): lock_file.unlink()`, deleting the lockfile and returning `True`.
- **Requirement:** Must check `if not appr_csv.is_file() or appr_csv.stat().st_size == 0:` and treat it as unapproved (write/enforce lockfile and return `False`).

### 2.2 Failure 4: Corrupted / Invalid CSV Header Schema
When an approved CSV contains invalid headers:
```
random_col1,random_col2
foo,bar
```
- `reader.fieldnames` does not contain `"tag"` or `"proposed_class"`.
- In `row.get("tag", "")`, `tag` defaults to `""`.
- `clean_tag == "1A"` evaluates to `False`.
- The safety inspection never runs.
- Lock is cleared and `True` is returned.
- **Requirement:** Must inspect `reader.fieldnames`. Strip whitespace, convert to lowercase, and strip optional UTF-8 BOM (`\ufeff`). If `"tag"` or `"proposed_class"` is missing, treat the CSV as invalid (enforce lockfile and return `False`).

### 2.3 Failure 5: Approved CSV Omitting Detail 1A Row
When an approved CSV contains valid headers and rows for other tags (e.g., Detail 1B) but intentionally or accidentally omits Detail 1A:
```csv
tag,sheet,detail_title,...,proposed_class,...
1B,A-900,1B Drywall,...,Drywall,...
```
- `reader` processes the rows, but `tag == "1A"` is never seen.
- Since there was no tracking boolean `found_1a = False`, the loop completes normally without error.
- Lock is unlinked and `True` is returned without Detail 1A ever being validated.
- **Requirement:** Must track `found_1a = False`. If all rows are parsed and `found_1a` is still `False`, approval is invalid (enforce lockfile and return `False`).

### 2.4 Critical Regression Discovery: Substring Keyword Matching
An attempted fix contained:
```python
cls_val = row.get("proposed_class", "").strip().lower()
if any(kw in cls_val for kw in ("drywall", "gwb", "gypsum", "sheetrock")) or (cls_val != "non-drywall" and cls_val != "2"):
    raise ValueError(...)
```
Because `"drywall"` is a literal substring of `"non-drywall"`:
```python
"drywall" in "non-drywall" == True
```
This caused any valid approved CSV where Detail 1A is `"Non-Drywall"` to immediately raise `ValueError: INTEGRITY VIOLATION`, breaking:
- `drywall_detection/tests/test_adversarial_m3.py::test_valid_approved_csv_removes_existing_lockfile`
- `drywall_detection/tests/test_schedule.py::test_csv_columns_match_contract`
- `drywall_detection/tests/test_schedule.py::test_approved_csv_bypasses_lock`

**Fix:** Detail 1A proposed class must be checked using exact membership in normalized sets:
```python
DRYWALL_SYNONYMS = {
    "drywall",
    "gwb",
    "gypsum",
    "gypsum wallboard",
    "gypsum wall board",
    "sheetrock",
    "1",
}
if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"):
    raise ValueError(...)
```
When `cls_val == "non-drywall"`, `cls_val in DRYWALL_SYNONYMS` is `False`, and `cls_val != "non-drywall"` is `False`. The check passes smoothly.

---

## 3. Schema & Validation Specifications

### 3.1 Validation Matrix
| Condition in `appr_csv` | Expected Behavior | Lockfile Action | Return Value |
|---|---|---|---|
| Does not exist | Unapproved | Create/maintain lock | `False` (or exit code 2 if interactive) |
| 0 bytes (`st_size == 0`) | Invalid approval | Create/maintain lock | `False` (or exit code 2 if interactive) |
| Binary garbage (non-UTF8) | Syntax error | Propagate `UnicodeDecodeError` | Exception raised |
| Missing `"tag"` or `"proposed_class"` | Invalid schema | Create/maintain lock | `False` (or exit code 2 if interactive) |
| Valid headers, 0 data rows | Incomplete | Create/maintain lock | `False` (or exit code 2 if interactive) |
| Valid headers, rows omit Detail 1A | Safety check failed | Create/maintain lock | `False` (or exit code 2 if interactive) |
| Detail 1A has `proposed_class="Drywall"` or `"GWB"` | Security violation | Raise `ValueError` | `ValueError("INTEGRITY VIOLATION...")` |
| Detail 1A has `proposed_class="Non-Drywall"` + 1A present | Approved! | Unlink `REVIEW_REQUIRED.lock` | `True` |

---

## 4. Proposed Source Code Diff

The following diff modifies `drywall_detection/vector/schedule_parser.py`:

```diff
--- a/drywall_detection/vector/schedule_parser.py
+++ b/drywall_detection/vector/schedule_parser.py
@@ -623,39 +623,54 @@ class PartitionScheduleParser:
         # Check if approved CSV exists and is valid
-        if appr_csv.exists():
+        is_valid_approved = False
+        if appr_csv.is_file():
             # Check 1: 0-byte or empty file cannot bypass review lock
             if appr_csv.stat().st_size == 0:
                 is_valid_approved = False
             else:
                 try:
                     with open(appr_csv, "r", encoding="utf-8") as f:
                         reader = csv.DictReader(f)
-                        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
-                        
-                        # Check 2: Invalid header schema (missing required columns)
-                        if "tag" not in fieldnames or "proposed_class" not in fieldnames:
+                        raw_fieldnames = reader.fieldnames or []
+                        norm_fieldnames = {
+                            fn.lstrip("\ufeff").strip().lower(): fn
+                            for fn in raw_fieldnames
+                            if fn
+                        }
+
+                        # Check 2: Invalid header schema (missing required columns)
+                        if "tag" not in norm_fieldnames or "proposed_class" not in norm_fieldnames:
                             is_valid_approved = False
                         else:
+                            tag_key = norm_fieldnames["tag"]
+                            cls_key = norm_fieldnames["proposed_class"]
                             rows = list(reader)
                             if not rows:
                                 is_valid_approved = False
                             else:
                                 found_1a = False
+                                DRYWALL_SYNONYMS = {
+                                    "drywall",
+                                    "gwb",
+                                    "gypsum",
+                                    "gypsum wallboard",
+                                    "gypsum wall board",
+                                    "sheetrock",
+                                    "1",
+                                }
                                 for row in rows:
-                                    clean_tag = row.get("tag", "").strip().upper()
+                                    clean_tag = (row.get(tag_key) or "").strip().upper()
                                     if clean_tag == "1A":
                                         found_1a = True
-                                        cls_val = row.get("proposed_class", "").strip().lower()
-                                        # Strict veto: 1A must NOT be Drywall, GWB, or gypsum synonyms
-                                        if any(kw in cls_val for kw in ("drywall", "gwb", "gypsum", "sheetrock")) or (cls_val != "non-drywall" and cls_val != "2"):
+                                        cls_val = (row.get(cls_key) or "").strip().lower()
+                                        # Strict veto: Detail 1A is 6" CMU and CANNOT be approved as Drywall or GWB
+                                        if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"):
                                             raise ValueError(
                                                 "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                                                 "CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!"
                                             )
-                                
+
                                 # Check 3: Missing Detail 1A row entirely
                                 if not found_1a:
                                     is_valid_approved = False
                                 else:
                                     is_valid_approved = True
                 except ValueError:
                     raise
                 except Exception:
                     is_valid_approved = False
 
             if is_valid_approved:
                 if lock_file.exists():
                     lock_file.unlink()
                 return True
 
         # Approved CSV missing -> write REVIEW_REQUIRED.lock
```

---

## 5. Verification Commands & Regression Checklist

1. **Adversarial M3 Suite Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m3.py -k "TestReviewLockProtocolEdgeCases" -v
   ```
   *Expected Result*: All 5 edge case tests PASS (`test_empty_approved_csv_must_not_bypass_lock`, `test_invalid_header_approved_csv_must_not_bypass_lock`, `test_missing_detail_1a_row_must_not_bypass_lock`, `test_approved_csv_binary_corruption_raises_decode_error`, `test_valid_approved_csv_removes_existing_lockfile`).

2. **Schedule Parser Suite Verification**:
   ```powershell
   python -m pytest drywall_detection/tests/test_schedule.py -v
   ```
   *Expected Result*: 9 passed, 0 failed.

3. **Combined Adversarial Suite (including Detail 1A safety tests)**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m3.py -k "TestDetail1ASafetyTampering" -v
   ```
   *Expected Result*: All 1A safety veto tests pass when combined with `spatial_matcher.py` fix from Explorer 1.
