# Dispatch: Milestone M3 Iteration 2 Remediation Worker

You are `worker_m3_iter2`, the Remediation Worker for Milestone M3 Iteration 2.

Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m3_iter2`
Your parent orchestrator is: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Objectives
In Milestone M3 Iteration 1, the implementation passed almost all reviews and stress tests, but `challenger_m3_2` identified 5 edge-case vulnerabilities in `drywall_detection/tests/test_adversarial_m3.py` and `reviewer_m3_2` identified a regex omission for tag `7F`.
An Explorer Triad (`explorer_m3_iter2_1`, `explorer_m3_iter2_2`, `explorer_m3_iter2_3`) has thoroughly investigated and formulated exact diffs with 100% consensus.

Your mission is to apply these exact remediation changes and verify that 100% of all tests pass (expected 195/195 tests passing).

## Concrete Tasks to Execute

### 1. Update `drywall_detection/vector/schedule_parser.py`
1. **Tag Regex (Line 137)**:
   Change `TAG_REGEX_STRICT` from:
   `r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEG]|8A|GL[12]|09|10|11)$"`
   to:
   `r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEFG]|8A|GL[12]|09|10|11)$"`
   (Adds 'F' to support Detail 7F shaft wall partition, recovering all 26 occurrences across floor plans A-101 to A-104).

2. **Harden `export_and_enforce_review_lock`**:
   - Check file size: `if appr_csv.stat().st_size == 0: is_valid_approved = False` (empty file must NOT bypass lock).
   - Normalize fieldnames (stripping UTF-8 BOM `\ufeff`) and ensure both `"tag"` and `"proposed_class"` exist in headers. If not, `is_valid_approved = False`.
   - Ensure rows exist: `rows = list(reader)`, if empty -> `is_valid_approved = False`.
   - Enforce Detail 1A presence and exact safety veto:
     ```python
     found_1a = False
     DRYWALL_SYNONYMS = {
         "drywall", "gwb", "gypsum", "gypsum wallboard",
         "gypsum wall board", "sheetrock", "1",
     }
     for row in rows:
         clean_tag = (row.get(tag_key) or "").strip().upper()
         if clean_tag == "1A":
             found_1a = True
             cls_val = (row.get(cls_key) or "").strip().lower()
             # CRITICAL: Use exact set comparison. NEVER use `"drywall" in cls_val` substring check!
             if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"):
                 raise ValueError(
                     'INTEGRITY VIOLATION: Detail 1A is explicitly 6" CMU masonry block and '
                     'CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!'
                 )
     if not found_1a:
         is_valid_approved = False
     else:
         is_valid_approved = True
     ```
   - If `is_valid_approved` is True:
     unlink `lock_file` if exists, and return `True`.
   - Else: write `REVIEW_REQUIRED.lock` and return `False`.

### 2. Update `drywall_detection/vector/extractor.py`
1. **Tag Regex (Line 158)**:
   Change `TAG_REGEX` from:
   `r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEG]|8A|GL[12]|09|10|11)$"`
   to:
   `r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEFG]|8A|GL[12]|09|10|11)$"`

### 3. Update `drywall_detection/vector/spatial_matcher.py`
1. **Fatal Exception on Tampered Detail 1A in `_resolve_classification`**:
   ```python
   clean_tag = tag_name.upper().strip()
   if clean_tag == "1A":
       detail = self.schedule_mapping.get("1A")
       if detail is not None:
           if hasattr(detail, "proposed_class"):
               cls_raw = detail.proposed_class
           elif isinstance(detail, dict):
               cls_raw = detail.get("proposed_class", "")
           else:
               cls_raw = str(detail)
           cls_norm = (cls_raw or "").strip().lower()
           drywall_synonyms = {
               "drywall", "gwb", "gypsum", "gypsum wallboard",
               "gypsum wall board", "sheetrock", "1",
           }
           if cls_norm in drywall_synonyms or (cls_norm and cls_norm != "non-drywall" and cls_norm != "2"):
               raise ValueError(
                   "INTEGRITY VIOLATION: Detail 1A cannot be classified as Drywall or GWB in SpatialMatcher!"
               )
       return ("Non-Drywall", CLASS_COLORS_HEX["Non-Drywall"])
   ```

### 4. Reconcile Test Assertions
1. **In `drywall_detection/tests/test_adversarial_m3.py`**:
   Update `test_spatial_matcher_detail_1a_immutable_veto`:
   ```python
   for tampered_map in tampered_variants:
       with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
           matcher = SpatialMatcher(schedule_mapping=tampered_map)
           matcher.match([wall], [tag])

   # Verify untampered / empty schedule defaults safely to Non-Drywall
   matcher_clean = SpatialMatcher(schedule_mapping={})
   report = matcher_clean.match([wall], [tag])
   assert report.matched_walls == 1
   res = report.results[0]
   assert res.assigned_tag == "1A"
   assert res.proposed_class == "Non-Drywall"
   assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
   ```

2. **In `drywall_detection/tests/test_vector.py`**:
   Update `test_detail_1a_cmu_safety_veto`:
   ```python
   tampered_schedule = {"1A": {"proposed_class": "Drywall"}}
   matcher = SpatialMatcher(schedule_mapping=tampered_schedule)
   with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
       matcher.match([wall], [tag])

   # Verify untampered schedule resolves 1A to Non-Drywall
   matcher_valid = SpatialMatcher(schedule_mapping=sample_schedule)
   report = matcher_valid.match([wall], [tag])
   res = report.results[0]
   assert res.assigned_tag == "1A"
   assert res.proposed_class == "Non-Drywall"
   ```

## Verification Steps
Execute the following commands and ensure all pass:
1. `python -m pytest drywall_detection/tests/test_adversarial_m3.py -v` (21 passed)
2. `python -m pytest drywall_detection/tests/test_schedule.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_vector_adversarial_stress.py -v` (112 passed)
3. Full regression:
   `python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_hardware.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py drywall_detection/tests/test_vector_adversarial_stress.py drywall_detection/tests/test_adversarial_m3.py -q` (195 passed)
4. Detail 1A CLI verification:
   `python -m drywall_detection.vector.schedule_parser --verify-detail-1a`
5. Tag 7F Discovery verification:
   `python -c "import fitz; from drywall_detection.vector.schedule_parser import PartitionScheduleParser; doc = fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); p14 = doc[14]; p = PartitionScheduleParser(); tags = p.discover_tags(p14, 14, 'A-101'); print(f'Discovered {len(tags)} tags; 7F count = {len([t for t in tags if t.tag == \"7F\"])}'); assert len(tags) == 45 and len([t for t in tags if t.tag == '7F']) == 1"`

Document all changes and test outputs in `handoff.md` and message the parent orchestrator upon completion.
