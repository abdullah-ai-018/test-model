# Milestone M1 Iteration 2 Challenger Report: Split Leakage Stress

- **Author**: `m1_r2_challenger_2` (M1 R2 Split Leakage Stress Challenger)
- **Role**: critic, specialist
- **Date**: 2026-11-08T04:02:00Z
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_challenger_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Handoff Type**: Hard (Task Complete)
- **Verdict**: **APPROVE**

---

## Challenge Summary

- **Target Under Test**: `verify_split_isolation()` and `DrawingSplitManager` in `drywall_detection/datasets/split_manager.py`.
- **Target Test File**: `drywall_detection/tests/test_split_leakage_adversarial.py` (64 test cases).
- **Overall Risk Assessment**: **LOW** (Zero regressions, 100% adversarial detection rate, zero data leakage under extreme skew).

---

## 1. Observation

### 1.1 Code Inspection of `drywall_detection/datasets/split_manager.py`
Direct observation of `drywall_detection/datasets/split_manager.py`:
1. **Canonicalization**:
   Lines 100–102:
   ```python
   def _canonical_path(p: Union[str, Path]) -> str:
       """Returns canonical case-folded absolute path string for cross-platform isolation checks."""
       return os.path.normcase(os.path.abspath(str(p)))
   ```
2. **Flag Invariant Checking**:
   Lines 111–120:
   ```python
   for split_name, tiles in [("Val", manifest.val_tiles), ("Test", manifest.test_tiles)]:
       for t in tiles:
           is_quar = getattr(t, "quarantine", False)
           is_pseudo = getattr(t, "is_pseudo_label", False)
           if is_quar or is_pseudo:
               raise SplitLeakageError(
                   f"Quarantined or pseudo-labeled tile record leakage detected in {split_name} split! Tile ID: {t.tile_id}"
               )
   ```
3. **Quarantine Cross-Split Isolation**:
   Lines 196–231:
   ```python
   # 5. Quarantine isolation against Val and Test evaluation splits
   qv_tile = quar_tile_ids.intersection(val_tile_ids)
   if qv_tile:
       raise SplitLeakageError(f"Quarantined tile ID leaked into Val split: {qv_tile}")
   qt_tile = quar_tile_ids.intersection(test_tile_ids)
   if qt_tile:
       raise SplitLeakageError(f"Quarantined tile ID leaked into Test split: {qt_tile}")

   qv_proj = quar_proj.intersection(val_proj)
   if qv_proj:
       raise SplitLeakageError(f"Quarantined project leaked into Val split: {qv_proj}")
   qt_proj = quar_proj.intersection(test_proj)
   if qt_proj:
       raise SplitLeakageError(f"Quarantined project leaked into Test split: {qt_proj}")

   qv_draw = quar_draw.intersection(val_draw)
   if qv_draw:
       raise SplitLeakageError(f"Quarantined drawing leaked into Val split: {qv_draw}")
   qt_draw = quar_draw.intersection(test_draw)
   if qt_draw:
       raise SplitLeakageError(f"Quarantined drawing leaked into Test split: {qt_draw}")

   qv_img = quar_img_paths.intersection(val_img_paths)
   if qv_img:
       raise SplitLeakageError(f"Quarantined image path overlap with Val split: {qv_img}")
   qt_img = quar_img_paths.intersection(test_img_paths)
   if qt_img:
       raise SplitLeakageError(f"Quarantined image path overlap with Test split: {qt_img}")

   qv_msk = quar_msk_paths.intersection(val_msk_paths)
   if qv_msk:
       raise SplitLeakageError(f"Quarantined mask path overlap with Val split: {qv_msk}")
   qt_msk = quar_msk_paths.intersection(test_msk_paths)
   if qt_msk:
       raise SplitLeakageError(f"Quarantined mask path overlap with Test split: {qt_msk}")
   ```

### 1.2 Adversarial Test Suite Construction
Created `drywall_detection/tests/test_split_leakage_adversarial.py` adhering to layout rules (co-located inside project tests directory). It implements:
- `TestQuarantineFlagInjectionAttack`: 9 test cases verifying direct and mutated flag injections (`quarantine=True`, `is_pseudo_label=True`, concurrent multi-tile flooding).
- `TestQuarantineEntityOverlapAttack`: 10 test cases verifying covert entity attribute leaks from `quarantine_tiles` into `val_tiles` and `test_tiles` (`tile_id`, `project_id`, `drawing_id`, `image_path`, `mask_path`).
- `TestWindowsPathCasingAttack`: 31 test cases verifying `_canonical_path` and 30 permutations across all 5 split pairs, testing drive casing (`C:\` vs `c:\`), lowercase, uppercase, mixed slash separators (`/` vs `\`), and dot segment traversals (`.` and `..`).
- `TestExtremeDistributionStress`: 10 stress tests testing:
  - 1000:1 group ratio (10,000 tiles vs 10 tiles vs 10 tiles).
  - 10,000:1 group ratio (10,000 tiles vs 1 tile vs 1 tile).
  - Zipf power-law distribution ($s_i = \max(1, \lfloor 1000 / (i+1)^{1.5} \rfloor)$) evaluated across 5 random seeds (7, 42, 99, 2026, 8888).
  - High group granularity (300 projects with 1 tile each).
  - Dominant quarantined group (5,000 tiles quarantined, 3 small active projects).
  - Drawing ID fallback under severe skew (2 projects, 7 drawings skewed 1000:10).
- `TestSplitManagerEdgeCases`: 4 tests verifying `InsufficientGroupsError`, `InvalidSplitRatioError`, deterministic SHA-256 manifest fingerprints, and `quarantine_tiles=[]` resilience.

### 1.3 Empirical Test Execution Results

1. **Targeted Adversarial Suite Execution**:
   - Command: `python -m pytest drywall_detection/tests/test_split_leakage_adversarial.py -v`
   - Result: `64 passed in 64.89s (0:01:04)` (Exit code 0).
   - Verbatim summary:
     ```
     ======================== 64 passed in 64.89s (0:01:04) ========================
     ```

2. **Full Project Regression Test Execution**:
   - Command: `python -m pytest drywall_detection/tests/ -v`
   - Result: `389 passed, 1 warning in 235.85s (0:03:55)` (Exit code 0).
   - Verbatim summary:
     ```
     ================= 389 passed, 1 warning in 235.85s (0:03:55) ==================
     ```
   - Previous baseline: 297 passed.
   - Delta: +92 newly passed tests (+64 adversarial split leakage stress tests, +28 other suite tests) with zero failures.

---

## 2. Logic Chain

1. **Quarantine and Pseudo-Label Flag Isolation (Observation 1.1, 1.2, 1.3)**:
   - Evaluation splits (`val_tiles` and `test_tiles`) must never contain weak pseudo-labels or quarantined tiles to ensure validation metrics reflect clean ground truth.
   - `verify_split_isolation()` scans every record in `manifest.val_tiles` and `manifest.test_tiles` for `getattr(t, "quarantine", False)` and `getattr(t, "is_pseudo_label", False)`.
   - In 9 out of 9 direct adversarial injection tests, `SplitLeakageError` was raised (100% detection rate).
   - In-place mutation of legitimate tiles and concurrent multi-tile flooding were detected unconditionally.

2. **Covert Quarantine Attribute Overlap (Observation 1.1, 1.2, 1.3)**:
   - Adversarial tiles with `quarantine=False` and `is_pseudo_label=False` were constructed sharing individual entity identifiers with `quarantine_tiles`:
     - `tile_id` collision: Caught by `quar_tile_ids.intersection(...)` $\implies$ `SplitLeakageError`.
     - `project_id` collision: Caught by `quar_proj.intersection(...)` $\implies$ `SplitLeakageError`.
     - `drawing_id` collision: Caught by `quar_draw.intersection(...)` $\implies$ `SplitLeakageError`.
     - `image_path` collision: Caught by `quar_img_paths.intersection(...)` $\implies$ `SplitLeakageError`.
     - `mask_path` collision: Caught by `quar_msk_paths.intersection(...)` $\implies$ `SplitLeakageError`.
   - In 10 out of 10 tests across Val and Test, 100% of covert leaks were detected and blocked.

3. **Windows Path Casing and Normalization Resilience (Observation 1.1, 1.2, 1.3)**:
   - On Windows, the filesystem treats `C:\Data\Tile.png`, `c:\data\tile.png`, and `c:/data/sub/../tile.png` as identical files. If comparison relied on raw strings, attackers could leak files across splits by altering casing or slashes.
   - `_canonical_path()` wraps `os.path.normcase(os.path.abspath(str(p)))`. On Windows, `normcase` folds uppercase drive letters and directories to lowercase and converts `/` to `\`. `abspath` normalizes relative traversals (`.` and `..`).
   - Testing 30 distinct permutations across `(train, val)`, `(train, test)`, `(val, test)`, `(quarantine, val)`, and `(quarantine, test)` proved that 100% of case-mismatched, slash-mismatched, and dot-traversed paths were equated to canonical form and raised `SplitLeakageError`.

4. **Extreme Group Distribution & Greedy Partitioning Stability (Observation 1.2, 1.3)**:
   - The greedy multi-way partitioning algorithm sorts groups descending by tile count and greedily assigns each group to the split bin maximizing relative shortfall $(T_i - S_i) / r_i$.
   - Under 1000:1 skew (10,000 tiles : 10 tiles : 10 tiles) and 10,000:1 skew (10,000 tiles : 1 tile : 1 tile):
     - Initial shortfalls are equal ($1.0 \cdot N_{total}$), tie-breaking allocates the giant group to bin 0 (Train).
     - Subsequent groups are allocated to bin 1 (Val) and bin 2 (Test), guaranteeing that all splits remain populated.
     - Projects and drawings in Train, Val, and Test remain 100% mutually disjoint.
     - `verify_split_isolation()` passes on the resulting manifest.
   - Under heavy-tailed Zipf power law ($s_i \propto i^{-1.5}$) across 5 random seeds, zero leakage occurred and all splits were populated.
   - Drawing fallback safely resolved 2-project severe skew without crash or leakage.

5. **Cryptographic Fingerprint Integrity (Observation 1.2, 1.3)**:
   - SHA-256 verification hashes were verified to be deterministic across identical seeds and sensitive to any single tile mutation.

---

## 3. Stress Test Results Matrix

| # | Stress Scenario | Attack Vector | Expected Behavior | Observed Result | Status |
|---|---|---|---|---|:---:|
| 1 | Flag Injection (Val) | `quarantine=True`, `is_pseudo_label=True` in `val_tiles` | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 2 | Flag Injection (Test) | `quarantine=True`, `is_pseudo_label=True` in `test_tiles` | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 3 | In-place Flag Mutation | Legitimate tile mutated in-place | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 4 | Covert Tile ID Overlap | Clean flags, shared `tile_id` with quarantine | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 5 | Covert Project ID Overlap | Clean flags, shared `project_id` with quarantine | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 6 | Covert Drawing ID Overlap | Clean flags, shared `drawing_id` with quarantine | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 7 | Covert Image Path Overlap | Clean flags, shared `image_path` with quarantine | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 8 | Covert Mask Path Overlap | Clean flags, shared `mask_path` with quarantine | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 9 | Windows Drive Casing | `C:\` vs `c:\` across split pairs | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 10 | Mixed Slashes & Casing | `C:/Data\sub/tile.png` vs `c:\data\SUB\tile.png` | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 11 | Redundant Dot Segments | `c:\data\.\sub\..\tile.png` vs `c:\data\tile.png` | `SplitLeakageError` | `SplitLeakageError` raised | **PASS** |
| 12 | 1000:1 Group Ratio | 10,000 : 10 : 10 tiles | Zero leakage, 3 populated splits | All splits > 0, 0 leakage | **PASS** |
| 13 | 10,000:1 Group Ratio | 10,000 : 1 : 1 tiles | Zero leakage, 3 populated splits | All splits > 0, 0 leakage | **PASS** |
| 14 | Zipf Power Law (5 seeds) | 30 groups, $\alpha=1.5$ | Deterministic, zero leakage | 5/5 seeds pass zero leakage | **PASS** |
| 15 | Granular Micro-Groups | 300 projects with 1 tile each | 70/15/15 ratio preservation | Exact 210/45/45 split | **PASS** |
| 16 | Quarantined Monolith | 5,000 tile group quarantined | Clean isolation from val/test | Zero leakage, 5000 quarantined | **PASS** |
| 17 | Severe Skew Fallback | 2 projects, 7 drawings | Fallback to drawing_id, 0 leakage | Fallback successful, 0 leakage | **PASS** |
| 18 | SHA-256 Sensitivity | Swapping 1 tile between splits | Hash alteration | Distinct 64-char hex hash | **PASS** |

---

## 4. Caveats

- **No Caveats**: All 64 adversarial challenge tests and all 389 repository unit and stress tests execute genuine algorithms against real state. No mocks or test facades were used. `verify_split_isolation()` and `DrawingSplitManager` conform strictly to Track 2 interface contracts in `PROJECT.md`.

---

## 5. Conclusion

**Final Verdict: APPROVE**

The data split integrity manager (`drywall_detection/datasets/split_manager.py`) is exceptionally robust:
1. `verify_split_isolation()` detected 100% of adversarial quarantine and pseudo-label injections across all test vectors (flags, tile IDs, project IDs, drawing IDs, image paths, mask paths).
2. `_canonical_path()` successfully neutralizes Windows filesystem variations (casing, slashes, relative traversals), preventing cross-split leakage.
3. `DrawingSplitManager` cleanly partitions extreme power-law distributions (up to 10,000:1 ratio) without crash, preserving zero project/drawing leakage and populating all required splits.
4. The full test suite passes with 100% success rate (389 passed, 0 failed).

---

## 6. Verification Method

To independently reproduce the empirical findings, execute the following commands from the project root:

1. **Run the Adversarial Split Leakage Stress Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_split_leakage_adversarial.py -v
   ```
   *Expected outcome*: 64 passed in ~65s.

2. **Run the Complete Repository Regression Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/ -v
   ```
   *Expected outcome*: 389 passed, 1 warning in ~235s (Exit code 0).
