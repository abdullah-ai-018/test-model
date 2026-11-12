# Handoff Report: Milestone M1 Dataset Architecture & Pipeline Review

- **Subagent**: `m1_reviewer_2`
- **Role**: Dataset Architecture & Pipeline Reviewer (reviewer, critic)
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Handoff Type**: Hard (Review Complete)
- **Recipient**: Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2`
- **Timestamp**: 2026-11-08T02:16:00Z
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

1. **Test Suite Execution Results**:
   - Executed: `python -m pytest drywall_detection/tests/unit/test_datasets.py -v`
     Verbatim summary:
     `============================= 28 passed in 22.49s =============================`
   - Executed full project test suite: `python -m pytest drywall_detection/tests/ -v`
     Verbatim summary:
     `============================ 174 passed in 28.42s =============================`
   - All 174 unit and integration tests passed cleanly with 0 failures and 0 errors.

2. **QC Triplet Artifact Inspection**:
   - Inspected `drywall_detection/data/qc_samples/sample_triplet_qc.png`:
     Verbatim check:
     `python -c "import cv2; img = cv2.imread('drywall_detection/data/qc_samples/sample_triplet_qc.png'); print('Loaded QC Triplet shape:', img.shape if img is not None else None)"`
     Output:
     `Loaded QC Triplet shape: (548, 1536, 3)`
   - Dimensions conform exactly to 512 + 36 banner height, 512 * 3 = 1536 width, 3 color channels.

3. **Adversarial Stress Test on Hard Negative Retention Quota**:
   - Script executed:
     ```python
     from drywall_detection.datasets.unified_format import SlidingWindowTiler, UnifiedDatasetConfig, UnifiedMask, DatasetClass
     config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15)
     tiler = SlidingWindowTiler(config)
     img = np.full((2000, 2000, 3), 255, dtype=np.uint8)
     for i in range(100, 1900, 100): cv2.line(img, (0, i), (2000, i), (0, 0, 0), 2)
     mask_data = np.zeros((2000, 2000), dtype=np.uint8)
     mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value
     tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), 'test_draw', 'test_src')
     wall_tiles = [t for t in tiles if t[2].has_walls]
     hn_tiles = [t for t in tiles if t[2].is_hard_negative]
     print(f'Total tiles generated: {len(tiles)}')
     print(f'Wall tiles: {len(wall_tiles)}')
     print(f'Hard negative tiles: {len(hn_tiles)}')
     print(f'Actual hard negative ratio: {len(hn_tiles) / len(tiles):.2%}')
     print(f'Config max_hard_negative_ratio: {config.max_hard_negative_ratio:.2%}')
     ```
   - Verbatim output:
     `Total tiles generated: 25`
     `Wall tiles: 1`
     `Hard negative tiles: 24`
     `Actual hard negative ratio: 96.00%`
     `Config max_hard_negative_ratio: 15.00%`
   - Observation: Despite configuring `max_hard_negative_ratio = 0.15`, 100% of hard negative tiles (24 out of 24) were retained, yielding an actual ratio of **96.00%**.

4. **Code Inspection of `unified_format.py`**:
   - `UnifiedDatasetConfig` declares `max_hard_negative_ratio: float = 0.15` at line 94.
   - Searching the entire repository revealed that `max_hard_negative_ratio` appears only at line 94 of `unified_format.py` and is never read, referenced, or applied anywhere in `SlidingWindowTiler.tile_drawing` or any subsequent filter.
   - Lines 511–533 of `unified_format.py` calculate `is_pure_blank` and `is_hard_negative`, discarding only pure blank tiles (`if is_pure_blank and not has_walls: continue`), and unconditionally appends every hard negative to `results`.

5. **Code Inspection of `split_manager.py` and `loader.py`**:
   - `split_manager.py`: Implements greedy multi-way group partitioning, fallback drawing grouping, SHA-256 hash calculation, and strict zero-leakage validator `verify_split_isolation`. Quarantined tiles (`is_pseudo_label=True`, `quarantine=True`) are strictly isolated from validation and test sets.
   - `loader.py`: Implements streaming `DrywallTileDataset`, native `torchvision.transforms.functional` synchronized flips, discrete 90° rotations (90°, 180°, 270°) with `NEAREST` mask interpolation, and image-only photometric jitter. Safe CPU/Windows DataLoader defaults (`num_workers=0`, `pin_memory=False`, `batch_size=2`).

6. **Anti-Cheat Audit**:
   - No hardcoded test outputs or dummy return statements detected.
   - No fabricated verification outputs found.
   - No unauthorized dependencies used (native `torchvision`, `cv2`, `PIL`, `numpy`).

---

## 2. Logic Chain

1. *Premise*: Dispatch Requirement 3 explicitly mandates: *"Blank tile filtering and hard negative retention within 15% quota."*
2. *Observation*: Observation 4 confirms that `max_hard_negative_ratio = 0.15` is declared as a dataclass attribute in `UnifiedDatasetConfig`, but `tile_drawing()` contains no logic enforcing this cap.
3. *Observation*: Observation 3 empirically demonstrates that an architectural floor plan with 1 wall tile and 24 non-blank linework tiles produces a 96.00% hard negative ratio instead of being capped at $\le 15.00\%$.
4. *Inference*: On real architectural floor plans (which are dense with notes, legends, grid lines, schedules, and structural margins), unconstrained retention of hard negatives will severely distort the training distribution, drastically worsening the 90:10 background-to-wall class imbalance during Milestone M4 model training.
5. *Observation*: Observation 1 shows that `test_tile_filtering_blank_and_hard_neg` only tested 1 tile per test case in isolation, leaving this omission undetected.
6. *Conclusion*: Because one of the core milestone verification requirements is functionally omitted and poses material training risk, the review verdict must be **REQUEST_CHANGES**.

---

## 3. Caveats

1. **Full-Sized Floor Plans**: Architectural drawings in MTA Contract C-48526 are large (MediaBox 1728x2592 pt, rendered at 150 DPI to ~3600x5400 px), meaning drawings will typically generate 50–100+ tiles. The lack of a hard negative quota will have a substantial impact on dataset size and class balance.
2. **Detail Sheets < 512px**: Images smaller than 512x512 are currently classified as corrupt (`SHAPE_MISMATCH`) and dropped. This is safe for master floor plans, but detail callouts may need padding in future milestones.
3. **RGB Mask Non-Standard Ingestion**: While the pipeline standardizes on Mode `'P'` indexed PNGs, ingesting RGB masks via `DrywallTileDataset` using `.convert('L')` causes luminance degradation (mapping Green, Red, and Yellow to 3). This is an edge-case caveat since all upstream tools produce Mode `'P'`.

---

## 4. Conclusion

The Milestone M1 dataset architecture and pipeline implementation is of high quality, structurally sound, and clean of integrity violations. However, it fails on Requirement 3 due to the complete lack of enforcement of the 15% hard negative retention quota in `SlidingWindowTiler`.

**Verdict**: **REQUEST_CHANGES**

### Required Modifications for `m1_worker_1`:
1. Modify `SlidingWindowTiler.tile_drawing()` (or add a companion filter method) to enforce `self.config.max_hard_negative_ratio`:
   - Calculate `max_hn = int(np.ceil(len(wall_tiles) * ratio / (1.0 - ratio)))` when `wall_tiles > 0`.
   - If `wall_tiles == 0`, retain at most 0 (or a configured nominal minimum) hard negatives.
   - Retain only up to `max_hn` hard negative tiles.
2. Add a unit test to `drywall_detection/tests/unit/test_datasets.py` verifying that when a drawing produces multiple hard negative tiles alongside wall tiles, the retained ratio strictly adheres to `max_hard_negative_ratio`.
3. Verify that `pytest drywall_detection/tests/unit/test_datasets.py -v` passes.

---

## 5. Verification Method

To independently verify the defect and validate the subsequent fix:

1. **Verify the Defect**:
   Run the adversarial stress test command:
   ```powershell
   python -c "import numpy as np, cv2; from drywall_detection.datasets.unified_format import SlidingWindowTiler, UnifiedDatasetConfig, UnifiedMask, DatasetClass; config = UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, max_hard_negative_ratio=0.15); tiler = SlidingWindowTiler(config); img = np.full((2000, 2000, 3), 255, dtype=np.uint8); [cv2.line(img, (0, i), (2000, i), (0, 0, 0), 2) for i in range(100, 1900, 100)]; mask_data = np.zeros((2000, 2000), dtype=np.uint8); mask_data[50:100, 50:100] = DatasetClass.DRYWALL.value; tiles = tiler.tile_drawing(img, UnifiedMask(mask_data), 'test', 'src'); hn = [t for t in tiles if t[2].is_hard_negative]; print(f'Hard Negatives: {len(hn)}/{len(tiles)} ({len(hn)/len(tiles):.1%})')"
   ```
   *Current behavior*: Outputs `Hard Negatives: 24/25 (96.0%)`.
   *Expected behavior after fix*: Outputs `Hard Negatives: <= 1 / 2 (<= 15.0%)` or similar quota compliance.

2. **Verify Full Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/unit/test_datasets.py -v
   ```
   *Expected output*: All tests pass including the new quota enforcement test.

3. **Invalidation Conditions**:
   - Hard negative ratio exceeding `max_hard_negative_ratio` on any multi-tile drawing.
   - Any pytest failure across `drywall_detection/tests/`.
