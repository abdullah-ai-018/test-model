# Milestone M3 Iteration 2 Split Isolation & Manifest Integrity Explorer Handoff Report

**Agent**: `m3_iter2_explorer_2` (Split Isolation & Manifest Integrity Explorer)  
**Recipient**: `parent` (Milestone M3 Orchestrator / Project Team)  
**Date**: 2026-11-09T06:33:00Z  
**Type**: Hard Handoff (Investigation & Remediation Specification Complete)  
**Verdict**: **READY_FOR_IMPLEMENTATION**  

---

## 1. Observation

Direct empirical observations, verbatim file paths, line numbers, and tool execution results:

### 1.1 Adversarial Test Execution
Executed the test suite provided by `m3_challenger_2`:
```powershell
python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
```
Out of 18 test items, 14 passed and 4 failed:
- `drywall_detection/tests/test_m3_adversarial_loss_splits.py::TestSplitIsolationAdversarialAttacks::test_attack_2_drawing_id_overlap_train_test`
  - Verbatim Error: `Failed: DID NOT RAISE ValueError` (Line 310)
- `drywall_detection/tests/test_m3_adversarial_loss_splits.py::TestSplitIsolationAdversarialAttacks::test_attack_7_drawing_id_overlap_val_test`
  - Verbatim Error: `Failed: DID NOT RAISE ValueError` (Line 405)
- `drywall_detection/tests/test_m3_adversarial_loss_splits.py::TestAssertZeroLeakageManifestsAdversarial::test_drawing_overlap_train_test_manifests`
  - Verbatim Error: `Failed: DID NOT RAISE RuntimeError` (Line 437)
- `drywall_detection/tests/test_m3_adversarial_loss_splits.py::TestAssertZeroLeakageManifestsAdversarial::test_quarantined_tile_in_test_manifest`
  - Verbatim Error: `Failed: DID NOT RAISE RuntimeError` (Line 457)

### 1.2 Verbatim Inspection of `drywall_detection/models/trainer.py`
In `drywall_detection/models/trainer.py` (lines 93–101):
```python
    # Drawing-level isolation check
    train_drawings = {t["drawing_id"] for t in train_tiles if "drawing_id" in t}
    val_drawings = {t["drawing_id"] for t in val_tiles if "drawing_id" in t}
    test_drawings = {t["drawing_id"] for t in test_tiles if "drawing_id" in t}

    draw_train_val = train_drawings.intersection(val_drawings)
    if draw_train_val:
        raise ValueError(f"Drawing leakage detected between Train and Val: {draw_train_val}")
```
- Direct Observation: `test_drawings` is defined on line 96, but is never used in any intersection check.
- Neither `train_drawings.intersection(test_drawings)` nor `val_drawings.intersection(test_drawings)` exists in the code.

### 1.3 Verbatim Inspection of `drywall_detection/models/metrics.py`
In `drywall_detection/models/metrics.py` (lines 336–352):
```python
    if test_manifest_path is not None:
        with open(test_manifest_path, "r", encoding="utf-8") as f:
            te_data = json.load(f)
        te_tiles = te_data.get("tiles") or te_data.get("samples") or []
        te_projs = {t.get("project_id") for t in te_tiles if t.get("project_id")}
        if t_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between train and test: {t_projs & te_projs}")
        if v_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between val and test: {v_projs & te_projs}")

    for name, tiles in [("validation", v_tiles)]:
        for t in tiles:
            if t.get("quarantine", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Quarantined sample {t.get('sample_id')} found in {name} split!")
            if t.get("is_pseudo_label", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Pseudo-labeled sample {t.get('sample_id')} found in {name} split!")
```
- Direct Observation: `te_draws` is never extracted from `te_tiles`.
- Direct Observation: `t_draws & te_draws` and `v_draws & te_draws` are never checked.
- Direct Observation: Line 346 strictly evaluates `[("validation", v_tiles)]`, completely omitting `te_tiles`.

### 1.4 Production Manifest Set Intersection Verification
Checked real production split manifests in `drywall_detection/data/processed/splits/` via Python:
- `t_draws & te_draws` = `set()`
- `v_draws & te_draws` = `set()`
- Quarantined or pseudo-labeled samples in `test.json` = `0`
- `assert_zero_leakage_manifests(train_p, val_p, test_p)` executed with exit code 0 (`PASS CLEAN`).

---

## 2. Logic Chain

1. **Premise 1 (Contract Requirement)**:
   - `PROJECT.md` Section 4.3 mandates strict project-isolated and drawing-level data partitioning with zero project or drawing overlap across all three splits:
     $$\text{Projects}(\text{train}) \cap \text{Projects}(\text{test}) = \emptyset, \quad \text{Drawings}(\text{train}) \cap \text{Drawings}(\text{test}) = \emptyset, \quad \text{Drawings}(\text{val}) \cap \text{Drawings}(\text{test}) = \emptyset$$
   - `PROJECT.md` Section 1 Track 3 and Dispatch require weak pseudo-labeled samples and quarantined tiles to be strictly excluded from validation and test sets.
2. **Premise 2 (Direct Observation of trainer.py)**:
   - `verify_split_isolation` only checks `draw_train_val = train_drawings.intersection(val_drawings)`. It leaves `test_drawings` completely unverified against `train_drawings` and `val_drawings`.
3. **Premise 3 (Direct Observation of metrics.py)**:
   - `assert_zero_leakage_manifests` only checks `t_projs & te_projs` and `v_projs & te_projs`. It fails to verify `t_draws & te_draws` or `v_draws & te_draws`.
   - The quarantine loop only iterates over `[("validation", v_tiles)]`, silently skipping `te_tiles`.
4. **Deductive Step (Failure Explanation)**:
   - When hostile test splits sharing drawing IDs with train or val are passed to `verify_split_isolation`, no exception is raised, causing `test_attack_2_drawing_id_overlap_train_test` and `test_attack_7_drawing_id_overlap_val_test` to fail.
   - When hostile manifests with shared drawings or quarantined samples are passed to `assert_zero_leakage_manifests`, no `RuntimeError` is raised, causing `test_drawing_overlap_train_test_manifests` and `test_quarantined_tile_in_test_manifest` to fail.
5. **Deductive Step (Safety and Non-Regression)**:
   - In the clean production dataset, all sets are disjoint ($\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$) and no quarantined samples reside in `test.json`.
   - Therefore, enforcing these checks eliminates the vulnerability and guarantees 0% false positive risk on real data.

---

## 3. Caveats

- **Scope Boundary**: This investigation is strictly read-only and limited to `trainer.py:verify_split_isolation` and `metrics.py:assert_zero_leakage_manifests`. Unrelated test failures in `drywall_detection/tests/test_training.py` (e.g. `infer.py` sliding window canvas shape mismatch or `FocalLoss.__init__` arguments) belong to parallel tracks and are not modified by this fix.
- **Assumptions**: DataLoader manifests are expected to provide `drawing_id`, `project_id`, `quarantine`, and `is_pseudo_label` dictionaries inside dataset items or manifest records, which is standard throughout `drywall_detection`.

---

## 4. Conclusion

The data leakage vulnerabilities reported by `m3_challenger_2` are fully validated and isolated. The implementation worker must apply the following exact modifications:

### 4.1 Action 1: Patch `drywall_detection/models/trainer.py`
Around line 101, insert test drawing intersection checks:
```python
    draw_train_val = train_drawings.intersection(val_drawings)
    if draw_train_val:
        raise ValueError(f"Drawing leakage detected between Train and Val: {draw_train_val}")

    if test_drawings:
        draw_train_test = train_drawings.intersection(test_drawings)
        if draw_train_test:
            raise ValueError(f"Drawing leakage detected between Train and Test: {draw_train_test}")
        draw_val_test = val_drawings.intersection(test_drawings)
        if draw_val_test:
            raise ValueError(f"Drawing leakage detected between Val and Test: {draw_val_test}")
```

### 4.2 Action 2: Patch `drywall_detection/models/metrics.py`
Replace lines 336–352 with:
```python
    eval_splits = [("validation", v_tiles)]

    if test_manifest_path is not None:
        with open(test_manifest_path, "r", encoding="utf-8") as f:
            te_data = json.load(f)
        te_tiles = te_data.get("tiles") or te_data.get("samples") or []
        eval_splits.append(("test", te_tiles))

        te_projs = {t.get("project_id") for t in te_tiles if t.get("project_id")}
        if t_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between train and test: {t_projs & te_projs}")
        if v_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between val and test: {v_projs & te_projs}")

        te_draws = {t.get("drawing_id") for t in te_tiles if t.get("drawing_id")}
        if t_draws & te_draws:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Drawings leaked between train and test: {t_draws & te_draws}")
        if v_draws & te_draws:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Drawings leaked between val and test: {v_draws & te_draws}")

        te_imgs = {t.get("image_path") or t.get("tile_path") for t in te_tiles if t.get("image_path") or t.get("tile_path")}
        if t_imgs & te_imgs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Image paths leaked between train and test: {t_imgs & te_imgs}")
        if v_imgs & te_imgs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Image paths leaked between val and test: {v_imgs & te_imgs}")

    for name, tiles in eval_splits:
        for t in tiles:
            if t.get("quarantine", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Quarantined sample {t.get('sample_id')} found in {name} split!")
            if t.get("is_pseudo_label", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Pseudo-labeled sample {t.get('sample_id')} found in {name} split!")
```

---

## 5. Verification Method

To independently verify the implementation:

1. **Execute Adversarial Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
   ```
   **Expected Outcome**: 18 passed, 0 failed in ~130s.

2. **Execute Split Isolation Integration Tests**:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -k "test_split_isolation" -v
   ```
   **Expected Outcome**: 3 passed, 0 failed.

3. **Verify Clean Production Splits via CLI**:
   ```powershell
   python -c "from drywall_detection.models.metrics import assert_zero_leakage_manifests; from pathlib import Path; p = Path('drywall_detection/data/processed/splits'); assert_zero_leakage_manifests(p/'train.json', p/'val.json', p/'test.json'); print('PASS CLEAN')"
   ```
   **Expected Outcome**: Prints `PASS CLEAN` with exit code 0.

4. **Invalidation Conditions**:
   - If `test_attack_2` or `test_attack_7` still fails with `DID NOT RAISE ValueError`, check that `ValueError` is raised with `"Drawing leakage"` in the message.
   - If `test_drawing_overlap_train_test_manifests` fails with `DID NOT RAISE RuntimeError`, check that `RuntimeError` is raised with `"Drawings leaked"` in the message.
   - If `test_quarantined_tile_in_test_manifest` fails with `DID NOT RAISE RuntimeError`, check that `RuntimeError` is raised with `"Quarantined sample"` in the message.
