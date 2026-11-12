# Milestone M1 Dataset Architecture & Pipeline Review Report

- **Reviewer**: `m1_reviewer_2` (Dataset Architecture & Pipeline Reviewer)
- **Roles**: Reviewer, Adversarial Critic
- **Date**: 2026-11-08T02:15:00Z
- **Target Files**:
  - `drywall_detection/datasets/unified_format.py`
  - `drywall_detection/datasets/split_manager.py`
  - `drywall_detection/datasets/loader.py`
  - `drywall_detection/tests/unit/test_datasets.py`
  - `drywall_detection/data/qc_samples/sample_triplet_qc.png`
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Executive Summary

A comprehensive quality review and adversarial challenge was conducted on the Milestone M1 dataset preparation, tiling, split manager, and DataLoader modules. 

The implementation demonstrates high architectural maturity, excellent documentation, and rigorous mathematical invariants in most components:
- The single-channel 8-bit indexed PNG standard (Mode `'P'`, `PALETTE_256`) provides an elegant dual-capability solution: human visual inspection in standard image viewers (White, Green, Red, Yellow) and zero-overhead integer loading (`torch.int64`, values `0..3`) directly in PyTorch.
- Multi-dataset converters (`MSDConverter`, `CubiCasaConverter`, `RasterMaskConverter`) correctly enforce Acceptance Criteria R2 by mapping generic external wall annotations strictly to **Class 3 (Uncertain / Generic Wall)**, preventing generic walls from being falsely assumed as drywall.
- The drawing-level and project-level split integrity manager (`DrawingSplitManager`, `verify_split_isolation`) provides mathematically proven zero data leakage with greedy multi-way group partitioning, fallback drawing grouping, and quarantined pseudo-label isolation.
- The streaming PyTorch DataLoader (`DrywallTileDataset`, `get_tile_dataloader`) ensures CPU and Windows RAM stability (`num_workers=0`, `pin_memory=False`, `batch_size=2`), with native `torchvision.transforms.functional` synchronized augmentations.
- All 28 unit tests in `test_datasets.py` and all 174 tests across the full project test suite pass cleanly without regressions.

**However, an adversarial stress test revealed a functional requirement omission:**
Requirement 3 of the dispatch directives mandates: *"Blank tile filtering and hard negative retention within 15% quota."*
While `UnifiedDatasetConfig` defines `max_hard_negative_ratio: float = 0.15`, **the quota is completely unenforced in `SlidingWindowTiler.tile_drawing`**. In an adversarial stress test with linework-heavy floor plans, 24 hard negative tiles and 1 wall tile were generated, and all 24 hard negatives were retained (yielding an actual hard negative ratio of **96.00%**). Because the existing unit test only evaluated a single hard negative tile in isolation, this omission went undetected.

Therefore, the verdict is **REQUEST_CHANGES** to address this Major requirement defect before Milestone M2.

---

## 2. Review Checklist & Verification Matrix

| # | Item to Verify | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|:---:|
| 1 | **Mode 'P' Indexed PNG Standard** | uint8, values $\{0, 1, 2, 3\}$, 256-color palette (0: White, 1: Green, 2: Red, 3: Yellow) | Strict validation in `UnifiedMask`, `PALETTE_256` verified, direct PyTorch int64 tensor load verified | **PASS** |
| 2 | **WKT / SVG / Raster Converters** | Converts MSD WKT, CubiCasa SVG, and raster masks to UnifiedMask; generic walls map to Class 3 | Implemented in `MSDConverter`, `CubiCasaConverter`, and `RasterMaskConverter`. Walls map to Class 3 | **PASS** |
| 3 | **512x512 Tiling & Apodization Stitcher** | 512x512 patches, 20% overlap (stride 410 px), boundary clamping, 2D Hann reverse stitcher | `compute_tile_grid` covers 100% canvas with stride 410. 2D Hann apodization stitching reconstructs global mask with 100% exact match | **PASS** |
| 4 | **Blank Tile Filtering & Hard Negative Quota** | Pure blank white tiles discarded; hard negatives with linework retained within 15% quota | Pure blank white tiles are discarded. Hard negatives are retained, but **15% quota is NOT enforced** (actual ratio reached 96% in stress test) | **FAIL** |
| 5 | **Split Integrity & Zero Leakage** | Drawing/project isolated splits (70/15/15), quarantine support, `verify_split_isolation` validator | Greedy multi-way partitioning, fallback drawing grouping, zero project/drawing/path overlap, SHA-256 hash | **PASS** |
| 6 | **Streaming PyTorch DataLoader** | Lazy disk loading, synchronized transforms (flips, discrete 90° rotations, image-only jitter), Windows CPU safe defaults | `DrywallTileDataset` streams lazily, `SynchronizedTransform` maintains discrete labels, DataLoader defaults to CPU safe values | **PASS** |
| 7 | **Visual QC Artifacts** | Composite triplet `[Drawing \| Color Mask \| Translucent Overlay]` with diagnostic banner | Generated and saved to `drywall_detection/data/qc_samples/sample_triplet_qc.png` (548, 1536, 3) | **PASS** |
| 8 | **Unit Test Suite Execution** | All tests pass with zero errors | `pytest drywall_detection/tests/unit/test_datasets.py -v`: 28 passed. Full suite: 174 passed | **PASS** |

---

## 3. Findings & Defect Analysis

### [Major] Finding 1: Hard Negative Retention 15% Quota is Unenforced in `SlidingWindowTiler`
- **Location**: `drywall_detection/datasets/unified_format.py`, line 94 and lines 508–534 (`tile_drawing()`).
- **What**: `UnifiedDatasetConfig` defines `max_hard_negative_ratio: float = 0.15`. However, in `SlidingWindowTiler.tile_drawing()`, every tile that is not pure blank and lacks walls (`is_hard_negative = True`) is unconditionally appended to `results`. There is no subsampling, filtering, or quota enforcement.
- **Why**: On architectural permit drawings with extensive schedules, notes, legends, and empty structural spans, hard negative tiles vastly outnumber wall tiles. In our adversarial stress test, a 2000x2000 canvas with line grid and a single wall patch produced 1 wall tile and 24 hard negative tiles. All 24 hard negatives were retained, resulting in a **96.00% hard negative ratio**, blowing past the 15% quota ceiling. If passed unconstrained into training, this extreme class imbalance will suppress wall recall and degrade convergence.
- **Suggestion**: In `SlidingWindowTiler.tile_drawing()` (or via a dedicated helper method `filter_hard_negatives()`), calculate the maximum allowed hard negatives based on the number of wall tiles:
  ```python
  wall_tiles = [r for r in results if r[2].has_walls]
  hn_tiles = [r for r in results if r[2].is_hard_negative]
  other_tiles = [r for r in results if not r[2].has_walls and not r[2].is_hard_negative]

  if self.config.max_hard_negative_ratio is not None and 0.0 < self.config.max_hard_negative_ratio < 1.0:
      if wall_tiles:
          max_hn = int(np.ceil(len(wall_tiles) * self.config.max_hard_negative_ratio / (1.0 - self.config.max_hard_negative_ratio)))
          hn_retained = hn_tiles[:max_hn]
      else:
          hn_retained = []
  else:
      hn_retained = hn_tiles

  results = wall_tiles + hn_retained + other_tiles
  ```
  Add a unit test in `test_datasets.py` verifying that when a drawing produces many hard negatives, the retained ratio does not exceed `max_hard_negative_ratio`.

---

### [Minor] Finding 2: Canvas Smaller Than Tile Size Discarded as Corrupt Instead of Padded
- **Location**: `drywall_detection/datasets/unified_format.py`, lines 489–497.
- **What**: In `compute_tile_grid`, if `height < 512` or `width < 512`, `get_steps` returns `[0]`. Slicing `image[0:512, 0:512]` yields shape `(height, width) != (512, 512)`. Line 491 flags this as `is_corrupt = True, rejection_reason = "SHAPE_MISMATCH"`, discarding the tile entirely.
- **Why**: While full architectural sheets are large (e.g. MTA sheets are ~3600x5400 px), small detail callouts or cropped permit figures with dimensions under 512 px will produce 0 tiles and be dropped as "corrupt".
- **Suggestion**: Pad small images to `(512, 512)` with white background (255) for image and background (0) for mask before slicing, or clearly document the minimum input dimension requirement.

---

### [Minor] Finding 3: RGB Mask Fallback in DataLoader Destroys Class Labels via Luminance Greyscale Conversion
- **Location**: `drywall_detection/datasets/loader.py`, lines 166–168.
- **What**: `DrywallTileDataset.__getitem__` executes:
  ```python
  if msk.mode not in ('P', 'L'):
      msk = msk.convert('L')
  ```
  When converting an RGB mask to `'L'`, PIL computes luminance: $0.299R + 0.587G + 0.114B$. Drywall (Green `#00FF00`) becomes 150, Non-Drywall (Red `#FF0000`) becomes 76, and Uncertain (Yellow `#FFFF00`) becomes 226. Subsequently, `torch.clamp(mask_tensor, 0, 3)` clamps 150, 76, and 226 all to 3 (Uncertain), destroying all drywall and non-drywall labels.
- **Why**: If a user or external tool provides RGB masks instead of Mode `'P'`, all class labels are silently degraded to Uncertain.
- **Suggestion**: Rather than falling back to `msk.convert('L')`, raise a `MaskValidationError` requiring Mode `'P'` or `'L'`, or implement explicit nearest-color palette de-mapping for RGB inputs.

---

### [Minor] Finding 4: Missing Size Assertion in `DrywallTileDataset` When `transform=None`
- **Location**: `drywall_detection/datasets/loader.py`, lines 173–178.
- **What**: When `transform` is None (e.g. during raw testing), `image` and `mask` are not resized to `(512, 512)`.
- **Why**: If any tile record points to an image with non-standard dimensions, `safe_collate_fn` will raise `RuntimeError: stack expects each tensor to be equal size`.
- **Suggestion**: Ensure `image.resize((512, 512))` and `mask.resize((512, 512))` are called even when `transform` is None.

---

## 4. Adversarial Challenge & Stress-Test Results

| Scenario | Attack Vector | Expected Defense | Observed Result | Status |
|---|---|---|---|:---:|
| **Adversarial Hard Negative Flooding** | Input floor plan with 1 wall tile and 24 non-blank linework tiles | Retain at most $\lceil 1 \times 0.15 / 0.85 \rceil = 1$ hard negative | Retained all 24 hard negatives (96.00% ratio) | **FAIL (Defect)** |
| **Small Image Canvas (<512px)** | Input image of size 300x300 | Pad to 512x512 or handle gracefully | Discarded as corrupt (`SHAPE_MISMATCH`), 0 tiles produced | **WARN (Caveat)** |
| **Discrete 90° Rotations** | Rotate mask with discrete labels $\{0, 1, 2, 3\}$ by 90°, 180°, 270° | Retain discrete integers without interpolation artifacts | Exactly preserved integers using `NEAREST` interpolation | **PASS** |
| **Photometric Jitter Isolation** | Apply brightness and contrast jitter | Mask values unchanged; only image altered | Mask pixels remained strictly identical to ground truth | **PASS** |
| **Split Leakage Detection** | Inject duplicate train tile into validation split | Validator raises `SplitLeakageError` | `verify_split_isolation` raised `SplitLeakageError` immediately | **PASS** |
| **Single-Project Drawing Fallback** | Dataset containing only 1 project with 6 drawings | Fall back to `drawing_id` grouping with zero drawing overlap | Fallback triggered; train/val/test drawings 100% disjoint | **PASS** |
| **Deterministic Seed Invariance** | Split generation with seed=42 twice vs seed=999 | Identical splits for seed=42; different for seed=999 | SHA-256 manifest hash matched identically for seed=42 | **PASS** |
| **Quarantine Isolation** | Tag drawing with `is_pseudo_label=True` or `quarantine=True` | Quarantine split isolated from val and test | Quarantined drawings 100% absent from val and test splits | **PASS** |

---

## 5. Anti-Cheat & Integrity Audit

- **Hardcoded test outputs**: Checked all test and implementation files. No hardcoded return values, mocks masking core logic, or dummy branch overrides found.
- **Dummy or facade logic**: `preparer.py` and `dataset_auditor.py` re-export genuine canonical implementations from `split_manager.py` and `licensing_audit.py`.
- **Shortcuts or task bypass**: Algorithms (2D Hann apodization stitching, greedy number partitioning, WKT polygon rasterization, SVG XML parsing) are fully implemented from scratch.
- **Fabricated verification outputs**: Re-ran the entire test suite independently (`174 passed in 28.42s`). Inspected QC triplet image shape (`548, 1536, 3`).

**Integrity Audit Verdict**: **PASSED (No integrity violations detected)**.

---

## 6. Verdict & Required Actions

**Verdict**: **REQUEST_CHANGES**

### Required Action Items for Worker (`m1_worker_1`):
1. **Implement Hard Negative Quota Cap in `SlidingWindowTiler.tile_drawing()`**:
   - Apply `self.config.max_hard_negative_ratio` (default 0.15) to cap the retained hard negative tiles relative to the wall tiles in that drawing.
   - When a drawing has 0 wall tiles, retain at most `0` (or a controlled minimum) hard negatives.
2. **Add Unit Test in `test_datasets.py`**:
   - Construct a drawing that yields multiple hard negatives and positive wall tiles.
   - Assert that the ratio of retained hard negative tiles to total retained tiles does not exceed `max_hard_negative_ratio`.
3. **Re-run Test Suite**:
   - Verify all tests pass cleanly: `pytest drywall_detection/tests/unit/test_datasets.py -v`.
