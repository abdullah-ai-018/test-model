# Milestone M3 Adversarial Stress Challenge Report

**Author:** `challenger_m3_2` (M3 Spatial Matcher and Safety Stress Challenger)  
**Recipient:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a` (Parent Orchestrator)  
**Date:** 2026-11-08  
**Working Directory:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `.agents/teamwork/challenger_m3_2`  
**Verdict:** **REQUEST_CHANGES**

---

## 1. Observation

1. **Test Suite Execution**:
   - Implemented 21 adversarial stress tests in `drywall_detection/tests/test_adversarial_m3.py` targeting:
     - 3-tier spatial matcher pathological geometries
     - Detail 1A Non-Drywall CMU safety tampering
     - Review lock protocol edge cases and schema validation
   - Executed: `python -m pytest drywall_detection/tests/test_adversarial_m3.py -v`
   - Result: **16 passed, 5 failed in 3.80s**.

2. **3-Tier Spatial Matcher Pathological Scenarios (ALL 9 PASSED)**:
   - `test_dense_tag_cluster_pointing_to_same_wall`: PASSED. 5 tags with leaders targeting the same wall geometry assign exactly 1 tag (`1B`) via Tier 1; 4 remaining tags are cleanly segregated into `unmatched_tags`. Zero double-assignments or crashes.
   - `test_dense_tag_cluster_adjacent_parallel_walls`: PASSED. 5 parallel walls spaced 15 pt apart matched 1-to-1 to 5 clustered tags with zero cross-talk.
   - `test_ambiguous_equidistant_proximity_buffers`: PASSED. A leaderless tag placed at exact geometric midpoint (distance 5.0 pt to both north and south walls, delta = 0.0 pt < 8.0 pt) rejected both walls. Both walls strictly defaulted to Tier 3 Uncertain (confidence 0.0, color `#FFD600`).
   - `test_proximity_buffer_delta_boundary_conditions`: PASSED. Distance delta = 7.9 pt rejected; distance delta = 8.0 pt accepted close wall.
   - `test_crossing_orthogonal_leader_lines`: PASSED. Crossing leader lines in an 'X' pattern correctly resolved to endpoints without geometric interference.
   - `test_long_leader_crossing_multiple_walls`: PASSED. 300 pt leader intersecting 3 walls matched the wall closest to the leader endpoint, ignoring intermediate traversed walls.
   - `test_leader_terminating_far_outside_geometry`: PASSED. Leader terminating 40 pt outside wall (exceeding 12 pt raycast and 50 pt buffer) defaulted to Tier 3 Uncertain.
   - `test_degenerate_zero_length_and_multisegment_leaders`: PASSED. Zero-length leader handled safely (norm check prevents zero division); multi-segment zigzag leader matched.
   - `test_massive_empty_drawing_stress_1000_walls`: PASSED. 1,000 synthetic wall candidates on empty drawing with 0 tags evaluated in 0.08s; 100% (1,000/1,000) assigned to Tier 3 Uncertain (`#FFD600`, confidence 0.0).

3. **Critical Security & Safety Failures (5 CONFIRMED FAILURES)**:

   - **Failure 1 — Detail 1A GWB Synonym Bypass in Approved CSV**:
     - *Test*: `TestDetail1ASafetyTampering::test_tampered_detail_1a_gwb_raises_integrity_violation`
     - *Observed Code*: `drywall_detection/vector/schedule_parser.py:628-633`:
       ```python
       if row.get("tag", "").strip().upper() == "1A":
           if row.get("proposed_class", "").strip().lower() == "drywall":
               raise ValueError(...)
       ```
     - *Observation*: When an approved CSV sets `tag="1A"` and `proposed_class="GWB"` (or `"Gypsum Wallboard"`), line 629 evaluates `False`. The integrity violation check is bypassed, `export_and_enforce_review_lock` returns `True`, and `REVIEW_REQUIRED.lock` is deleted.
     - *Verbatim Error*: `Failed: DID NOT RAISE <class 'ValueError'>`.

   - **Failure 2 — SpatialMatcher Silent Veto without Exception on Tampered Schedule**:
     - *Test*: `TestDetail1ASafetyTampering::test_spatial_matcher_raises_exception_on_tampered_1a`
     - *Observed Code*: `drywall_detection/vector/spatial_matcher.py:146-149`:
       ```python
       clean_tag = tag_name.upper().strip()
       if clean_tag == "1A":
           return ("Non-Drywall", CLASS_COLORS_HEX["Non-Drywall"])
       ```
     - *Observation*: When `SpatialMatcher` is provided a tampered schedule dictionary `{"1A": {"proposed_class": "Drywall"}}` or `{"1A": {"proposed_class": "GWB"}}`, it overrides the classification to `Non-Drywall` but fails to raise an immediate fatal exception as required by the zero-tolerance safety specification.
     - *Verbatim Error*: `Failed: DID NOT RAISE <class 'ValueError'>`.

   - **Failure 3 — Empty (0-Byte) Approved CSV Bypasses Review Lock**:
     - *Test*: `TestReviewLockProtocolEdgeCases::test_empty_approved_csv_must_not_bypass_lock`
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
     - *Observation*: An empty (0-byte) `partition_schedule_mapping.approved.csv` satisfies `appr_csv.exists()`. `csv.DictReader` iterates 0 times, the safety loop never runs, `lock_file.unlink()` deletes `REVIEW_REQUIRED.lock`, and the function returns `True`.
     - *Verbatim Error*: `AssertionError: SECURITY FLAW: 0-byte approved CSV bypassed the review lock! assert True is False`.

   - **Failure 4 — Approved CSV with Invalid/Corrupted Headers Bypasses Review Lock**:
     - *Test*: `TestReviewLockProtocolEdgeCases::test_invalid_header_approved_csv_must_not_bypass_lock`
     - *Observed Code*: `drywall_detection/vector/schedule_parser.py:624-636`.
     - *Observation*: When an approved CSV contains invalid headers (e.g. `col1,col2`), `row.get("tag")` is `None` / `""`. The validation loop performs 0 inspections, silently clears `REVIEW_REQUIRED.lock`, and returns `True`.
     - *Verbatim Error*: `AssertionError: SECURITY FLAW: Approved CSV with invalid headers bypassed the review lock! assert True is False`.

   - **Failure 5 — Approved CSV Omitting Detail 1A Row Bypasses Review**:
     - *Test*: `TestReviewLockProtocolEdgeCases::test_missing_detail_1a_row_must_not_bypass_lock`
     - *Observed Code*: `drywall_detection/vector/schedule_parser.py:624-636`.
     - *Observation*: If an approved CSV provides rows for other details but deliberately omits `1A`, `tag == "1A"` is never encountered. The lockfile is unlinked and approval is granted without Detail 1A ever being validated.
     - *Verbatim Error*: `AssertionError: SECURITY FLAW: Approved CSV omitting Detail 1A bypassed review! assert True is False`.

---

## 2. Logic Chain

1. **Spatial Matcher Robustness**:
   - Observations in Section 1.2 demonstrate that the R-tree spatial indexing (`STRtree`), Tier 1 raycast sorting, Tier 2 distance delta margin ($\Delta \ge 8.0$ pt), and Tier 3 unassigned fallback guardrail are mathematically and geometrically sound.
   - All 9 pathological geometric scenarios passed cleanly.

2. **Detail 1A Non-Drywall CMU Safety Invariant**:
   - MTA Sheet A-900 cell Detail 1A explicitly specifies `6" FIRE RATED CMU MASONRY BLOCK`.
   - The contract in `PROJECT.md` Section 6 Rule 3 and DISPATCH Section 2 dictates: "Never classify Tag 1A as Drywall... Deliberately craft corrupted/tampered inputs attempting to assign Detail 1A to 'Drywall' or 'GWB'. Verify that the programmatic safety veto in `schedule_parser.py` and `spatial_matcher.py` intercepts this and raises an immediate exception."
   - Because `schedule_parser.py:629` only checks `== "drywall"`, an injection of `"GWB"` or `"Gypsum Wallboard"` succeeds without raising an exception (Observation Section 1.3, Failure 1).
   - In `spatial_matcher.py:146-149`, receiving a tampered schedule with `1A` mapped to Drywall/GWB silently resets the class rather than raising an immediate fatal exception (Observation Section 1.3, Failure 2).

3. **Review Lock Security Semantics**:
   - `export_and_enforce_review_lock` is designed as a human-in-the-loop gating mechanism protecting downstream Milestone M4/M5 execution.
   - Merely checking `if appr_csv.exists():` without validating non-zero file size, CSV schema headers, row counts, and mandatory presence of Detail 1A creates severe security bypass vulnerabilities (Observation Section 1.3, Failures 3, 4, 5).
   - A human reviewer or external system touching an empty file or uploading a malformed file instantly bypasses the review lock.

---

## 3. Caveats

- **Scope Boundary**: As a critic/challenger under strict review-only constraints, `challenger_m3_2` does not modify implementation code in `drywall_detection/vector/`.
- **Existing Baseline**: Existing unit tests (`test_vector.py`, `test_schedule.py`, 41 tests) pass because they only test the happy-path `1A = "Drywall"` and non-empty valid files. They do not test `"GWB"`, empty files, missing headers, or omitted rows.

---

## 4. Conclusion

**Verdict:** **REQUEST_CHANGES**

Milestone M3 vector geometry and spatial matching algorithms are high quality and robust. However, Milestone M3 cannot be approved until the following safety and security vulnerabilities in `drywall_detection/vector/schedule_parser.py` and `spatial_matcher.py` are resolved by `worker_m3_1`:

### Required Changes for `worker_m3_1`:

1. **Harden Detail 1A Safety Veto in `schedule_parser.py`**:
   - In `export_and_enforce_review_lock`, normalize proposed class and check against all drywall identifiers:
     ```python
     DRYWALL_SYNONYMS = {"drywall", "gwb", "gypsum", "gypsum wallboard", "gypsum wall board"}
     # Or require strictly: norm_class == "non-drywall"
     ```
   - If `tag == "1A"` and `norm_class in DRYWALL_SYNONYMS` (or `norm_class != "non-drywall"`), raise `ValueError("INTEGRITY VIOLATION: Detail 1A is 6\" CMU masonry block and CANNOT be approved as Drywall/GWB!")`.

2. **Harden Approved CSV Schema Validation in `schedule_parser.py`**:
   - In `export_and_enforce_review_lock`:
     a) Verify file size: `if appr_csv.stat().st_size == 0: return False` (and do not unlink lockfile).
     b) Verify headers: Check that `reader.fieldnames` contains at least `"tag"` and `"proposed_class"`. If not, do not unlink lockfile and return `False` or raise `ValueError`.
     c) Verify mandatory presence of Detail 1A: Track if `1A` was encountered in `reader`. If `1A` was not in the file, do not unlink lockfile and return `False`.

3. **Harden Detail 1A Tampering Interception in `spatial_matcher.py`**:
   - In `SpatialMatcher._resolve_classification(tag_name)`:
     ```python
     if clean_tag == "1A":
         detail = self.schedule_mapping.get("1A")
         if detail:
             mapped_class = getattr(detail, "proposed_class", detail.get("proposed_class", "") if isinstance(detail, dict) else "")
             if mapped_class.strip().lower() in {"drywall", "gwb", "gypsum", "gypsum wallboard"}:
                 raise ValueError("INTEGRITY VIOLATION: Detail 1A cannot be classified as Drywall or GWB in SpatialMatcher!")
         return ("Non-Drywall", CLASS_COLORS_HEX["Non-Drywall"])
     ```

---

## 5. Verification Method

To independently reproduce and verify the findings:

1. **Run the Adversarial Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_adversarial_m3.py -v
   ```
   *Current Result*: 16 passed, 5 failed (confirming the 5 documented vulnerabilities).

2. **Resolution Invalidation Condition**:
   Once `worker_m3_1` implements the fixes above, running the command must produce:
   `21 passed in < 5.0s, 0 failures`.
