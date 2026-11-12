# Dispatch Assignment: worker_m5_iter2

## Role
Milestone M5 Remediation Worker (`teamwork_worker`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m5_1\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_challenger_m5_safety.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\vector\spatial_matcher.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\fusion.py`

## Exclusive Write Ownership
You have exclusive write ownership of:
- `drywall_detection/classification/classifier.py`
- `drywall_detection/vector/spatial_matcher.py`
- `drywall_detection/pipeline/fusion.py`
- `drywall_detection/reports/M5_classification_report.md`
- `drywall_detection/tests/test_challenger_m5_fusion.py` (if needed)

## Required Remediation Tasks (5 Confirmed Vulnerabilities)

### 1. VULN-M5-01 (CRITICAL): Detail 1A Runtime Invariant Synonym Bypass
- In `drywall_detection/classification/classifier.py`:
  - `ClassifiedWallPolygon.__post_init__`:
    If `matched_tag` or `detail_number` is `"1A"` (case-insensitive, stripped), the classification MUST strictly be `"Non-Drywall"` (or numerical `"2"`).
    Any other classification (including any drywall synonym like `"gyp bd"`, `"gyp board"`, `"gypsum board"`, `"dry wall"`, `"gyp"`, etc.) MUST raise `IntegrityViolationError("INTEGRITY VIOLATION: Detail 1A is 6\" CMU masonry block and must ONLY be classified as Non-Drywall.")`.
    Do NOT rely only on an incomplete whitelist; reject ANY attempt to classify 1A as anything other than Non-Drywall.

### 2. VULN-M5-02 (CRITICAL): Detail 1A Runtime Invariant Field Mutation Bypass
- In `drywall_detection/classification/classifier.py`:
  - In `ClassifiedWallPolygon`, implement a `__setattr__` guard:
    ```python
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "classification" and hasattr(self, "matched_tag"):
            clean_tag = str(getattr(self, "matched_tag", "") or "").strip().upper()
            clean_detail = str(getattr(self, "detail_number", "") or "").strip().upper()
            if clean_tag == "1A" or clean_detail == "1A":
                # Check if new value is drywall or anything other than Non-Drywall
                val_str = str(value).strip().lower()
                if val_str != "non-drywall" and val_str != "2":
                    raise IntegrityViolationError("INTEGRITY VIOLATION: Detail 1A field mutation to Drywall is forbidden.")
        super().__setattr__(name, value)
    ```
    This prevents post-init mutation of `classification` to Drywall when the wall is tagged Detail 1A.

### 3. VULN-M5-03 (HIGH): Whitespace Tag Bypass of Tier 3 Unassigned Fallback
- In `drywall_detection/classification/classifier.py`:
  - In `DrywallClassifier.classify_walls()`:
    When inspecting `match_res.assigned_tag`, verify that it is non-empty after stripping:
    ```python
    if match_res is not None and match_res.assigned_tag and match_res.assigned_tag.strip():
        clean_tag = match_res.assigned_tag.upper().strip()
        ...
    else:
        # Strict Tier 3 unassigned fallback:
        # confidence=0.0, matched_tag=None, detail_number=None, classification="Uncertain", color_hex="#FFD600"
    ```
    Ensure that whitespace tags (`"   "`, `"\t"`, `""`) strictly fall back to Tier 3 unassigned with `confidence=0.0` and `matched_tag=None`.

### 4. VULN-M5-04 (HIGH): SpatialMatcher AttributeError on `tag_id = None`
- In `drywall_detection/vector/spatial_matcher.py`:
  - In `_resolve_classification(self, tag_name: Any)`:
    Check `if not tag_name or not isinstance(tag_name, str) or not tag_name.strip(): return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])`.
  - In line 298 or wherever `getattr(tag, "tag_id", ...)` is called:
    Ensure `tag_name` is safely sanitized to empty string if `tag_id` is `None`.

### 5. VULN-M5-05 (MEDIUM): Takeoff Summary Accounting Discrepancy
- In `drywall_detection/pipeline/fusion.py`:
  - In `compute_summary_statistics(self, walls)`:
    Ensure that `total_walls == sum(class_counts)`:
    Tally class counts for all walls in `walls` (even if empty geometry), while setting linear feet and area contributions to 0.0 for empty geometries. That way, `total_walls == drywall_count + nondrywall_count + uncertain_count`.

## Verification Commands to Execute
Run the following commands and include full verbatim results in your handoff report:
1. `pytest drywall_detection/tests/test_challenger_m5_safety.py -v` (ALL 62 MUST PASS).
2. `pytest drywall_detection/tests/test_classification.py -v` (ALL 20 MUST PASS).
3. `pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_schedule.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_models.py drywall_detection/tests/test_training.py -v` (Full repo regression - ALL MUST PASS).

Deliver your handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\handoff.md`.


## 2026-11-09T13:42:09Z
[Message] timestamp=2026-11-09T13:42:09Z sender=3cdc71fe-4915-41ee-8ce4-6e81878e6b7a priority=MESSAGE_PRIORITY_HIGH content=You are worker_m5_iter2. Read your dispatch assignment at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\DISPATCH.md`.
Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\`
Mandatory: Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `challenger_m5_1/handoff.md`, and `test_challenger_m5_safety.py`.
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Remediate the 5 confirmed vulnerabilities (VULN-M5-01 through VULN-M5-05) across `classification/classifier.py`, `vector/spatial_matcher.py`, and `pipeline/fusion.py`.
Run verification tests:
1. `pytest drywall_detection/tests/test_challenger_m5_safety.py -v` (assert 62/62 pass)
2. `pytest drywall_detection/tests/test_classification.py -v` (assert 20/20 pass)
3. Full repository regression suite across all tests.
Deliver your handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_iter2\handoff.md`.
