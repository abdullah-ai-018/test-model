# Challenger Report & Handoff: Milestone M5 Safety Veto & Schema Hardening

**Document ID:** HANDOFF-M5-CHALLENGER-01  
**Author:** `challenger_m5_1` (Milestone M5 Safety Veto & Schema Challenger)  
**Date:** 2026-11-09T18:10:00Z  
**Recipient Parent Agent:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Working Directory:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\`  
**Target Milestone:** M5 (Drywall Classification & Verification)  
**Verdict:** **REQUEST_CHANGES**  

---

## Challenge Summary

**Overall risk assessment**: **HIGH**  
While the Layer 1 Ingestion Gate and basic schedule lookups are solidly defended against CSV tampering and whitespace/case variations, empirical probing exposed 5 distinct vulnerabilities and failure modes:
1. **Detail 1A Runtime Invariant Bypass via Incomplete Synonym Whitelist** (Detail 1A accepted as drywall under unregistered synonyms like `"gyp bd"`, `"gyp board"`, `"gypsum board"`, `"dry wall"`).
2. **Detail 1A Runtime Invariant Bypass via Post-Init Attribute Mutation** (mutating `poly.classification = "Drywall"` succeeds silently without `__setattr__` protection, allowing downstream serialization to GeoJSON as Drywall).
3. **Tier 3 Unassigned Fallback Bypass via Whitespace Tags** (`tag="   "` assigned `confidence=0.30` and `matched_tag=""` instead of strict unassigned fallback `confidence=0.0` and `matched_tag=None`).
4. **Spatial Matcher Unhandled Exception Crash on `tag_id = None`** (`SpatialMatcher._resolve_classification` crashes with `AttributeError: 'NoneType' object has no attribute 'upper'`).
5. **Material Takeoff Summary Count Accounting Discrepancy** (`HybridFusionPipeline.compute_summary_statistics` counts empty geometries in `total_walls` but skips them in class breakdown, causing `total_walls != sum(class_counts)`).

---

## 1. Observation

### 1.1 Test Suite Creation & Empirical Execution
- **Delivered Test Suite**: `drywall_detection/tests/test_challenger_m5_safety.py` (770 lines, 62 distinct test cases).
- **Execution Command**:
  ```powershell
  pytest drywall_detection/tests/test_challenger_m5_safety.py -v
  ```
- **Execution Result**:
  `5 failed, 57 passed in 10.84s`

### 1.2 Verbatim Observations of Passing Defenses (57 Tests Passed)
1. **Ingestion Gate Tampering Defenses (23 passed)**:
   - Case variations (`"drywall"`, `"DRYWALL"`, `"DrYwAlL"`, `"  drywall  "`, `"\tDRYWALL\n"`): All raised `IntegrityViolationError("INTEGRITY VIOLATION")`.
   - Drywall synonyms in CSV (`"GWB"`, `"gwb"`, `"Gypsum Wallboard"`, `"gypsum wallboard"`, `"sheetrock"`, `"1"`, `"gyp bd"`, `"gypsum board"`, `"dry wall"`): All raised `IntegrityViolationError`.
   - Downgrading 1A to `"Uncertain"`: Raised `IntegrityViolationError`.
   - Zero-byte CSV (`0 bytes`): Raised `ScheduleValidationError`.
   - Corrupted headers (missing mandatory `"tag"` or `"proposed_class"`): Raised `ScheduleValidationError`.
   - Omitted Detail 1A row (23 rows): Raised `ScheduleValidationError`.
   - Replaced Detail 1A row (24 rows with `"1X"` instead of `"1A"`): Raised `IntegrityViolationError`.
   - UTF-8 BOM CSV (`\ufeff`): Cleanly parsed 24 details with canonical 1A Non-Drywall.
   - Tag whitespace/case in CSV (`" 1A "`, `"1a"`, `"1A\t"`): Successfully normalized to canonical 1A Non-Drywall.
2. **Runtime Invariant Direct Instantiation Standard Defenses (13 passed)**:
   - Instantiation with `matched_tag="1A"` and `classification` in `{"Drywall", "drywall", "DRYWALL", "  Drywall  ", "GWB", "Gypsum Wallboard", "sheetrock", "1"}` raised `IntegrityViolationError`.
   - Tag variations (`"1a"`, `" 1A "`, `"1A\t"`) triggered `IntegrityViolationError`.
   - `DrywallClassifier.classify_walls()` unconditionally classified Detail 1A as `Non-Drywall` (`#D50000`).
3. **Tier 3 Unassigned Zero-Hallucination Baselines (5 passed)**:
   - Candidate wall with empty tags (`[]`): Produced `Uncertain`, `confidence=0.0`, `matched_tag=None`, `match_method="unassigned"`.
   - Candidate wall with distant tag (> 50pt buffer): Produced `Uncertain`, `confidence=0.0`, `matched_tag=None`.
   - Candidate wall with empty string tag (`""`): Produced `Uncertain`, `confidence=0.0`, `matched_tag=None`.
   - Candidate wall with unknown tag (`"UNKNOWN_99"`): Produced `Uncertain`, `#FFD600`, zero drywall hallucination.
   - Candidate wall with missing `wall_id` dict: Received fallback ID without crash.
4. **GeoJSON Schema & Takeoff Robustness (16 passed)**:
   - Empty Polygon (`Polygon()`): Handled without crashing; serialized coordinates to `[]`.
   - Zero-area Polygon (`Polygon([(0,0), (10,0), (0,0)])`): Valid GeoJSON feature.
   - Self-intersecting bowtie Polygon: Valid GeoJSON feature.
   - MultiPolygon: Valid GeoJSON MultiPolygon feature.
   - None geometry: Valid GeoJSON feature with `geometry: null`.
   - Full roundtrip disk serialization: Wrote and loaded valid GeoJSON FeatureCollection.
   - Takeoff with negative bounds (`box(-1000, -500, -100, -490)`) and coordinates $> 10^6$: Calculated correct linear feet and square feet without numerical error.

### 1.3 Verbatim Observations of Confirmed Failures (5 Failures)

#### Failure 1: Detail 1A Runtime Invariant Bypassed by Unregistered Drywall Synonyms
- **Test**: `TestDetail1ACMURuntimeInvariant::test_classified_wall_polygon_blocks_unregistered_drywall_synonyms`
- **Observed Code**: `drywall_detection/classification/classifier.py:53-61, 90-96`
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
  ...
  def __post_init__(self) -> None:
      if self.matched_tag and self.matched_tag.upper().strip() == "1A":
          if self.classification.strip().lower() in DRYWALL_SYNONYMS or self.classification == ClassificationClass.DRYWALL.value:
              raise IntegrityViolationError(...)
  ```
- **Observed Output**:
  ```text
  AssertionError: VULNERABILITY: Detail 1A runtime invariant bypassed with unregistered drywall synonyms: ['gyp bd', 'gyp board', 'gypsum board', 'dry wall', 'gyp']. Detail 1A must ONLY be classifiable as Non-Drywall.
  assert not ['gyp bd', 'gyp board', 'gypsum board', 'dry wall', 'gyp']
  ```
- **Line**: `drywall_detection/tests/test_challenger_m5_safety.py:352`

#### Failure 2: Detail 1A Runtime Invariant Bypassed via Post-Init Attribute Mutation
- **Test**: `TestDetail1ACMURuntimeInvariant::test_classified_wall_polygon_prevents_post_init_mutation_to_drywall`
- **Observed Code**: `drywall_detection/classification/classifier.py:64-96`
  `ClassifiedWallPolygon` is a standard mutable `@dataclass` without `frozen=True` or `__setattr__` guardrails.
- **Observed Output**:
  ```text
  AssertionError: VULNERABILITY: Detail 1A runtime invariant bypassed via post-init attribute mutation! ClassifiedWallPolygon allows field reassignment resulting in Drywall classification on Detail 1A.
  assert 'Drywall' != 'Drywall'
  ```
- **Line**: `drywall_detection/tests/test_challenger_m5_safety.py:386`

#### Failure 3: Whitespace Tags Bypass Tier 3 Zero-Confidence Fallback
- **Test**: `TestTier3UnassignedFallbackAdversarial::test_whitespace_only_tag_candidate_falls_back_to_unassigned_zero_confidence`
- **Observed Code**: `drywall_detection/classification/classifier.py:294-374`
  ```python
  if match_res is not None and match_res.assigned_tag:
      clean_tag = match_res.assigned_tag.upper().strip()
      ...
      detail = self.schedule_mapping.get(clean_tag)
      if detail:
          ...
      else:
          # Unrecognized tag in schedule -> Uncertain
          classified_walls.append(
              ClassifiedWallPolygon(
                  wall_id=wall_id,
                  ...
                  matched_tag=clean_tag,  # becomes ""
                  detail_number=None,
                  material_description="Tag not found in approved schedule",
                  classification="Uncertain",
                  confidence=0.30,  # <--- Should be 0.0 unassigned fallback!
                  color_hex=CLASS_COLORS_HEX["Uncertain"],
                  reason=f"Unknown tag '{clean_tag}' not in approved schedule",
  ```
- **Observed Output**:
  ```text
  AssertionError: VULNERABILITY: Whitespace tag '   ' was assigned confidence=0.3 and matched_tag=''. Whitespace tags must fall back to Tier 3 unassigned with confidence=0.0 and matched_tag=None.
  assert 0.3 == 0.0
  ```
- **Line**: `drywall_detection/tests/test_challenger_m5_safety.py:497`

#### Failure 4: SpatialMatcher Crashes on `tag_id = None` with AttributeError
- **Test**: `TestTier3UnassignedFallbackAdversarial::test_none_tag_candidate_does_not_crash_attribute_error`
- **Observed Code**: `drywall_detection/vector/spatial_matcher.py:146` & `spatial_matcher.py:298`
  ```python
  tag_name = getattr(tag, "tag_id", getattr(tag, "tag", ""))  # evaluates to None when tag.tag_id is None
  ...
  prop_class, col_hex = self._resolve_classification(tag_name)
  ...
  def _resolve_classification(self, tag_name: str) -> Tuple[str, str]:
      clean_tag = tag_name.upper().strip()  # <--- CRASHES when tag_name is None
  ```
- **Observed Output**:
  ```text
  AttributeError: 'NoneType' object has no attribute 'upper'
  Failed: VULNERABILITY / BUG: SpatialMatcher crashed on None tag with AttributeError: 'NoneType' object has no attribute 'upper'
  ```
- **Line**: `drywall_detection/tests/test_challenger_m5_safety.py:517`

#### Failure 5: Takeoff Summary Accounting Discrepancy on Empty Geometries
- **Test**: `TestGeoJSONSchemaAndTakeoffStress::test_takeoff_fusion_summary_accounting_consistency_with_empty_geometries`
- **Observed Code**: `drywall_detection/pipeline/fusion.py:307-344`
  ```python
  summary = {
      "total_walls": len(walls),  # Counts 2 walls
      "drywall_count": 0,
      "nondrywall_count": 0,
      "uncertain_count": 0,
      ...
  }
  for w in walls:
      if w.geometry_pdf is None or w.geometry_pdf.is_empty:
          continue  # Skips incrementing class counts for empty geometries!
  ```
- **Observed Output**:
  ```text
  AssertionError: DISCREPANCY: Takeoff summary total_walls (2) does not equal the sum of class counts (1)! Empty geometries were skipped in class counts but tallied in total_walls.
  assert 2 == 1
  ```
- **Line**: `drywall_detection/tests/test_challenger_m5_safety.py:756`

---

## 2. Logic Chain

1. *From Observation 1.2*: The CSV Ingestion Gate (`DrywallClassifier._load_and_validate_schedule`) is robust against tampering: any value other than `"non-drywall"` or `"2"` for Detail 1A is rejected with `IntegrityViolationError`. Omissions, 0-byte files, and corrupted headers are rejected with `ScheduleValidationError`.
2. *From Observation 1.3 (Failure 1)*: In `ClassifiedWallPolygon.__post_init__`, the runtime check relies on an incomplete whitelist `DRYWALL_SYNONYMS`. Because common architectural synonyms like `"gyp bd"`, `"gyp board"`, `"gypsum board"`, `"dry wall"`, and `"gyp"` were omitted from this whitelist, `ClassifiedWallPolygon` can be instantiated with `matched_tag="1A"` and `classification="gypsum board"` without error. This creates a loophole where Detail 1A is labeled as a gypsum assembly. Invariant 3 of `PROJECT.md` Section 6 ("Never classify Tag 1A as Drywall: Detail 1A is explicitly 6\" CMU masonry block and must be classified as Non-Drywall") requires that Detail 1A MUST ONLY be classified as `"Non-Drywall"`.
3. *From Observation 1.3 (Failure 2)*: `ClassifiedWallPolygon` lacks mutability protection. Once created as `"Non-Drywall"`, setting `poly.classification = "Drywall"` succeeds silently. Serializing to GeoJSON via `poly.to_geojson_feature()` or passing the object to `DrywallClassifier.compute_summary()` results in Detail 1A being reported as Drywall. This directly violates the dispatch requirement: *"Attempt to bypass the Runtime Invariant by directly instantiating `ClassifiedWallPolygon` with `tag="1A"` and `classification="Drywall"` or modifying its fields. Verify fatal `IntegrityViolationError`."*
4. *From Observation 1.3 (Failure 3)*: Candidate walls with whitespace tags (`"   "`) are treated as matched to tag `""` with `confidence=0.30`, rather than falling back to Tier 3 unassigned (`confidence=0.0`, `matched_tag=None`). This violates the zero-hallucination requirement of `ORIGINAL_REQUEST.md` R2 and the dispatch contract: *"Candidate walls with missing tags, whitespace tags, unknown tags, empty strings, None, or invalid formats. Verify strictly `Uncertain`, `confidence=0.0`, `#FFD600` (zero material hallucination)."*
5. *From Observation 1.3 (Failure 4)*: `SpatialMatcher._resolve_classification` assumes `tag_name` is always a `str`. If a tag symbol has `tag_id = None`, `getattr` yields `None`, causing `tag_name.upper()` to throw an unhandled `AttributeError`, crashing the vector extraction pipeline.
6. *From Observation 1.3 (Failure 5)*: In `HybridFusionPipeline.compute_summary_statistics`, `total_walls` is computed from `len(walls)`, but walls with empty geometries are skipped by `continue`, resulting in `total_walls != sum(class_counts)`. This breaks internal accounting consistency for takeoff reports.
7. *Conclusion from Logic Chain*: Because these 5 vulnerabilities represent direct breaches of safety veto requirements, zero-hallucination fallback rules, unhandled runtime crashes, and accounting consistency, the milestone cannot be approved in its current state. A verdict of `REQUEST_CHANGES` is mandatory.

---

## 3. Caveats

1. **Review-Only Constraint**: In accordance with the Teamwork protocol, `challenger_m5_1` did NOT modify any implementation code in `drywall_detection/classification/`, `vector/`, or `pipeline/`. All findings are documented as test cases and formal recommendations for the remediation worker.
2. **Platform & Scale**: Verification tests were executed on Windows 10 under Python 3.10 with CPU execution. Memory and execution times are bounded ($10.84$s for 62 tests).
3. **Usman Markup Evaluation**: The vector extraction pipeline accuracy against the 239 verified Usman markups was verified by `worker_m5_2` in `test_classification.py` (20 passed); this challenge focused specifically on adversarial safety vetoes, fallback edge cases, and schema integrity.

---

## 4. Conclusion & Verdict

**Final Verdict**: **REQUEST_CHANGES**

The Milestone M5 implementation has strong foundational components (Ingestion Gate, RFC 7946 GeoJSON export, Affine coordinate management), but contains 5 confirmed vulnerabilities that require remediation:

| ID | Severity | Component | Finding Summary | Required Fix |
|---|---|---|---|---|
| **VULN-M5-01** | **CRITICAL** | `classification/classifier.py` | Incomplete synonym whitelist allows 1A to be classified as `"gyp bd"`, `"gypsum board"`, `"dry wall"`. | Enforce that if `matched_tag == "1A"` or `detail_number == "1A"`, classification MUST strictly equal `"Non-Drywall"` or `"2"`. |
| **VULN-M5-02** | **CRITICAL** | `classification/classifier.py` | `ClassifiedWallPolygon` lacks post-init mutation guard; field reassignment to `"Drywall"` bypasses runtime veto. | Implement `__setattr__` guard (or `frozen=True`) preventing modification of `classification` to Drywall when tag is 1A. |
| **VULN-M5-03** | **HIGH** | `classification/classifier.py` | Whitespace-only tag (`"   "`) assigned `confidence=0.30` and `matched_tag=""` instead of Tier 3 fallback. | Check `if match_res.assigned_tag and match_res.assigned_tag.strip():`; whitespace tags must fall back to `confidence=0.0`, `matched_tag=None`. |
| **VULN-M5-04** | **HIGH** | `vector/spatial_matcher.py` | `_resolve_classification` crashes with `AttributeError` when `tag_id = None`. | Sanitize input: `if not tag_name: return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])`. |
| **VULN-M5-05** | **MEDIUM** | `pipeline/fusion.py` | `compute_summary_statistics` accounting mismatch: `total_walls != sum(class_counts)` with empty geometries. | Ensure class counts tally empty geometries or reconcile `total_walls` with valid geometries. |

---

## 5. Verification Method

To independently reproduce all 5 failures and verify the 57 passing tests:

```powershell
# Run the complete M5 adversarial challenge suite:
pytest drywall_detection/tests/test_challenger_m5_safety.py -v

# Run the 5 specific failing tests individually:
pytest drywall_detection/tests/test_challenger_m5_safety.py::TestDetail1ACMURuntimeInvariant::test_classified_wall_polygon_blocks_unregistered_drywall_synonyms -v
pytest drywall_detection/tests/test_challenger_m5_safety.py::TestDetail1ACMURuntimeInvariant::test_classified_wall_polygon_prevents_post_init_mutation_to_drywall -v
pytest drywall_detection/tests/test_challenger_m5_safety.py::TestTier3UnassignedFallbackAdversarial::test_whitespace_only_tag_candidate_falls_back_to_unassigned_zero_confidence -v
pytest drywall_detection/tests/test_challenger_m5_safety.py::TestTier3UnassignedFallbackAdversarial::test_none_tag_candidate_does_not_crash_attribute_error -v
pytest drywall_detection/tests/test_challenger_m5_safety.py::TestGeoJSONSchemaAndTakeoffStress::test_takeoff_fusion_summary_accounting_consistency_with_empty_geometries -v
```

**Invalidation Conditions (When Remediation Is Complete)**:
- All 62 tests in `drywall_detection/tests/test_challenger_m5_safety.py` pass with `62 passed in < 15s`.
- All existing 123 tests across `test_coords.py`, `test_schedule.py`, `test_vector.py`, `test_models.py`, `test_training.py`, and `test_classification.py` continue to pass with 0 regressions.
- No bypass of Detail 1A CMU safety veto via synonyms or field mutation is possible.
- No unhandled exceptions occur on `None` or whitespace tags.
