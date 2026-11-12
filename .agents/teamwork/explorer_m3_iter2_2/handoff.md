# Handoff Report: Review Lock & CSV Validation Hardening (Failures 3, 4, 5)

**Agent:** `explorer_m3_iter2_2`  
**State Folder:** `.agents/teamwork/explorer_m3_iter2_2`  
**Recipient:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a` (Parent Orchestrator)  
**Task:** Formulate exact diffs for `drywall_detection/vector/schedule_parser.py` (`export_and_enforce_review_lock`) resolving Failures 3, 4, 5.

---

## 1. Observation

1. **Failure 3: Empty (0-byte) approved CSV bypass**
   - *Test*: `drywall_detection/tests/test_adversarial_m3.py::TestReviewLockProtocolEdgeCases::test_empty_approved_csv_must_not_bypass_lock`
   - *Observed Code*: `drywall_detection/vector/schedule_parser.py:624-636`:
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
   - *Verbatim Error*:
     ```
     AssertionError: SECURITY FLAW: 0-byte approved CSV bypassed the review lock!
     assert True is False
     drywall_detection\tests\test_adversarial_m3.py:621
     ```

2. **Failure 4: Invalid/corrupted headers in approved CSV**
   - *Test*: `drywall_detection/tests/test_adversarial_m3.py::TestReviewLockProtocolEdgeCases::test_invalid_header_approved_csv_must_not_bypass_lock`
   - *Observed Input*: `appr_path.write_text("random_col1,random_col2\nfoo,bar\n", encoding="utf-8")`
   - *Verbatim Error*:
     ```
     AssertionError: SECURITY FLAW: Approved CSV with invalid headers bypassed the review lock!
     assert True is False
     drywall_detection\tests\test_adversarial_m3.py:642
     ```

3. **Failure 5: Approved CSV omitting Detail 1A row**
   - *Test*: `drywall_detection/tests/test_adversarial_m3.py::TestReviewLockProtocolEdgeCases::test_missing_detail_1a_row_must_not_bypass_lock`
   - *Observed Input*: CSV containing only Detail 1B, with 1A completely omitted.
   - *Verbatim Error*:
     ```
     AssertionError: SECURITY FLAW: Approved CSV omitting Detail 1A bypassed review!
     assert True is False
     drywall_detection\tests\test_adversarial_m3.py:683
     ```

4. **Critical Regression Discovered in Recent Workspace Edit**:
   - An attempted edit in `schedule_parser.py:649` introduced:
     ```python
     cls_val = row.get("proposed_class", "").strip().lower()
     if any(kw in cls_val for kw in ("drywall", "gwb", "gypsum", "sheetrock")) or (cls_val != "non-drywall" and cls_val != "2"):
         raise ValueError(...)
     ```
   - When Detail 1A has legitimate `proposed_class = "Non-Drywall"`, `cls_val` is `"non-drywall"`.
   - In Python, `"drywall" in "non-drywall"` evaluates to `True` (substring match).
   - *Verbatim Errors on Valid CSV*:
     - `test_valid_approved_csv_removes_existing_lockfile`: `ValueError: INTEGRITY VIOLATION: Detail 1A is explicitly 6" CMU masonry block and CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!` (line 650).
     - `test_schedule.py::test_csv_columns_match_contract`: `ValueError: INTEGRITY VIOLATION...` (line 650).
     - `test_schedule.py::test_approved_csv_bypasses_lock`: `ValueError: INTEGRITY VIOLATION...` (line 650).

---

## 2. Logic Chain

1. **Failure 3 Mechanism**:
   - As observed in Observation 1, `appr_csv.exists()` evaluates to `True` for 0-byte files.
   - `csv.DictReader` on an empty file yields 0 iterations.
   - The method unlinks the lockfile and returns `True`, allowing an empty file to bypass human review.
   - **Remediation**: Check `appr_csv.is_file()` and `appr_csv.stat().st_size == 0`. If 0 bytes, flag as unapproved (`is_valid_approved = False`), write `REVIEW_REQUIRED.lock`, and return `False`.

2. **Failure 4 Mechanism**:
   - As observed in Observation 2, `DictReader` accepts arbitrary headers (`random_col1,random_col2`).
   - `row.get("tag")` is `None`/`""`. The loop completes without detecting 1A.
   - The method unlinks the lockfile and returns `True`.
   - **Remediation**: Check `norm_fieldnames` contains both `"tag"` and `"proposed_class"`. If either is missing, flag as unapproved (`is_valid_approved = False`), write `REVIEW_REQUIRED.lock`, and return `False`. Strip optional UTF-8 BOM (`\ufeff`) to support Excel exports.

3. **Failure 5 Mechanism**:
   - As observed in Observation 3, if a CSV provides valid headers but omits 1A, `clean_tag == "1A"` is never entered.
   - Without a presence flag, the method assumes valid approval, unlinks the lock, and returns `True`.
   - **Remediation**: Maintain `found_1a = False`. If after iterating all rows `found_1a` is still `False`, flag as unapproved (`is_valid_approved = False`), write `REVIEW_REQUIRED.lock`, and return `False`.

4. **Regression Prevention**:
   - As observed in Observation 4, using `any(kw in cls_val ...)` performs substring matching. Since `"drywall"` is inside `"non-drywall"`, legitimate approvals fail.
   - **Remediation**: Use exact normalized membership:
     `DRYWALL_SYNONYMS = {"drywall", "gwb", "gypsum", "gypsum wallboard", "gypsum wall board", "sheetrock", "1"}`
     `if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"): raise ValueError(...)`
     This strictly forbids Drywall/GWB while allowing valid `"non-drywall"` and `"2"`.

---

## 3. Caveats

- **Scope Constraint**: Under Teamwork Explorer rules, this agent does not modify source code directly. All changes are provided as diff specifications for `worker_m3_1` / implementer.
- **Peer Coordination**: Failure 2 (`SpatialMatcher` fatal exception on tampered schedule) is located in `drywall_detection/vector/spatial_matcher.py` and is covered by `explorer_m3_iter2_1`.

---

## 4. Conclusion

Failures 3, 4, and 5 in `schedule_parser.py` are fully analyzed and resolved by hardening `export_and_enforce_review_lock`:
1. Reject 0-byte approved CSVs (`st_size == 0`).
2. Reject approved CSVs missing mandatory `"tag"` or `"proposed_class"` headers.
3. Reject approved CSVs omitting Detail 1A.
4. Correct Detail 1A safety veto from substring matching to exact membership check, resolving the critical regression on valid CSVs.

### Actionable Code Diff for Implementer:

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

## 5. Verification Method

To independently verify after code application:

1. **Review Lock Protocol Edge Case Tests**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m3.py -k "TestReviewLockProtocolEdgeCases" -v
   ```
   *Expected*: 5 passed, 0 failed.

2. **Schedule Parser Baseline Tests**:
   ```powershell
   python -m pytest drywall_detection/tests/test_schedule.py -v
   ```
   *Expected*: 9 passed, 0 failed.

3. **Tampered Detail 1A Tests**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m3.py -k "TestDetail1ASafetyTampering" -v
   ```
   *Expected*: Passes all schedule parser tampering tests.

4. **Invalidation Condition**:
   Any test in `TestReviewLockProtocolEdgeCases` failing or raising unexpected exceptions, or any test in `test_schedule.py` failing, invalidates the fix.
