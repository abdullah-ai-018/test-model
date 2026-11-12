# Milestone M1 Adversarial Stress Test Analysis: Tiling, Stitching & Unified Format

- **Subagent**: `m1_challenger_2`
- **Role**: Tiling, Stitching & Conversion Stress Challenger (critic, specialist)
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Target Components**: `drywall_detection/datasets/unified_format.py`, `drywall_detection/datasets/loader.py`
- **Test File**: `drywall_detection/tests/test_tiling_stitching_stress.py` (58 test cases)
- **Timestamp**: 2026-11-08T02:25:00Z

---

## 1. Executive Summary

An adversarial empirical stress testing campaign was executed against the unified segmentation format, sliding-window tiling engine, 2D Hann apodization reverse stitcher, mask validation subsystem, and visual QC generator. 

Key empirical findings:
1. **100% Canvas Surface Coverage**: Sliding-window tiling with boundary clamping was tested across 10 diverse dimensions, including irregular dimensions not multiples of 512 (`700x900`, `1234x5678`), full-scale MTA 99th Street floor plans (`2592x1728`), high-resolution raster plans (`5400x3600`), boundary off-by-one dimensions (`513x513`, `1025x769`), and extreme ribbon aspect ratios (`512x3000`, `4000x512`). In all cases, 100% canvas coverage was achieved with zero uncovered margin pixels (`uncovered_pixels = 0`), and exact boundary clamping (`y_steps[-1] + 512 == H` and `x_steps[-1] + 512 == W`).
2. **Sub-Tile Behavior**: Images smaller than tile size (e.g., `300x400`) are rejected gracefully by `tile_drawing()` as shape mismatches (returning `[]` empty list), preventing malformed patches from entering training pipelines.
3. **Zero Discrete Reconstruction Error**: Reconstructing discrete ground truth segmentation masks across arbitrary dimensions using 2D Hann window apodization reverse stitching yielded **0 mismatched pixels** (error rate `0.000000%`).
4. **Sub-Microscopic Continuous Probability Error**: Reconstructing continuous soft probability distributions $[H, W, 4]$ across overlap ratios (10%, 20%, 30%, 50%) yielded Mean Absolute Error (MAE) $< 7.7 \times 10^{-9}$, Root Mean Square Error (RMSE) $< 1.7 \times 10^{-8}$, and Max Error $< 3.0 \times 10^{-7}$, with **100.0000% argmax classification agreement**.
5. **Hann Boundary Safety**: The 2D Hann window clipping to $10^{-4}$ prevents zero-division singularity at tile corners and edges where raw $\text{outer}(w_y, w_x) = 0.0$.
6. **Mask Validation & Corrupt Input Rejection**: Masks with out-of-bounds values ($>3$), signed negative values, non-uint8 dtypes, non-2D shapes, non-array inputs, and NaNs were rejected with `MaskValidationError`. Corrupted tile data injected into `SlidingWindowTiler` were filtered with `rejection_reason="INVALID_MASK_VALUE"`.
7. **Visual QC Triplet Verification**: Generated QC triplets match dimensions `(H + 36, 3W, 3)` with banner and `(H, 3W, 3)` without banner. Diagnostic header banner text and status formatting (`WALL_SAMPLE`, `HARD_NEG`, `EMPTY`) were verified. Alpha blending transparency on floor plan drawings achieved exact numerical agreement with the theoretical blending equation ($\text{max\_pixel\_diff} = 0$).

---

## 2. Empirical Verification Logs & Quantitative Results

### 2.1 Tiling Canvas Coverage Audit

Tested using `UnifiedDatasetConfig(tile_size=512, overlap_ratio=0.20, stride=410)`:

| Dimension $(H \times W)$ | Description | Grid Steps $(R \times C)$ | Total Tiles | Uncovered Pixels | Coverage Depth $[\min, \max]$ | Clamped Boundary | Coverage % |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `700 x 900` | Non-multiple small plan | $2 \times 2$ | 4 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `1234 x 5678` | Large irregular plan | $3 \times 14$ | 42 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `2592 x 1728` | MTA 99th St (72 dpi) | $7 \times 4$ | 28 | 0 | $[1, 6]$ | Y: Yes, X: Yes | 100.0% |
| `5400 x 3600` | High-res raster (150 dpi) | $13 \times 9$ | 117 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `512 x 512` | Single exact tile | $1 \times 1$ | 1 | 0 | $[1, 1]$ | Y: Yes, X: Yes | 100.0% |
| `513 x 513` | Boundary off-by-one | $2 \times 2$ | 4 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `1024 x 1024` | Exact multiple of 512 | $3 \times 3$ | 9 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `1025 x 769` | Dual off-by-one | $3 \times 2$ | 6 | 0 | $[1, 4]$ | Y: Yes, X: Yes | 100.0% |
| `512 x 3000` | Extreme horizontal ribbon | $1 \times 8$ | 8 | 0 | $[1, 3]$ | Y: Yes, X: Yes | 100.0% |
| `4000 x 512` | Extreme vertical ribbon | $10 \times 1$ | 10 | 0 | $[1, 2]$ | Y: Yes, X: Yes | 100.0% |

**Verbatim test log output**:
```text
=== 1. TILING CANVAS COVERAGE AUDIT ===
Shape 700x900: tiles=2x2=4, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 1234x5678: tiles=3x14=42, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 2592x1728: tiles=7x4=28, uncovered=0, depth=[1, 6], clamped_y=True, clamped_x=True
Shape 5400x3600: tiles=13x9=117, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 512x512: tiles=1x1=1, uncovered=0, depth=[1, 1], clamped_y=True, clamped_x=True
Shape 513x513: tiles=2x2=4, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 1024x1024: tiles=3x3=9, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 1025x769: tiles=3x2=6, uncovered=0, depth=[1, 4], clamped_y=True, clamped_x=True
Shape 512x3000: tiles=1x8=8, uncovered=0, depth=[1, 3], clamped_y=True, clamped_x=True
Shape 4000x512: tiles=10x1=10, uncovered=0, depth=[1, 2], clamped_y=True, clamped_x=True
```

---

### 2.2 2D Hann Apodization Reverse Stitcher Numerical Precision

#### Continuous Soft Probability Fields ($[800 \times 1000 \times 4]$):

Apodization weight accumulation evaluated with:
$$\hat{P}(y, x) = \frac{\sum_i W_i(y, x) P_i(y, x)}{\sum_i W_i(y, x)}$$

| Overlap Ratio | Stride (px) | Mean Absolute Error (MAE) | Max Absolute Error | Root Mean Square Error (RMSE) | Argmax Classification Accuracy |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 10% | 461 | $5.77 \times 10^{-9}$ | $2.98 \times 10^{-7}$ | $1.41 \times 10^{-8}$ | **100.0000%** |
| 20% | 410 | $5.69 \times 10^{-9}$ | $2.38 \times 10^{-7}$ | $1.40 \times 10^{-8}$ | **100.0000%** |
| 30% | 358 | $5.70 \times 10^{-9}$ | $2.38 \times 10^{-7}$ | $1.40 \times 10^{-8}$ | **100.0000%** |
| 50% | 256 | $7.66 \times 10^{-9}$ | $1.79 \times 10^{-7}$ | $1.67 \times 10^{-8}$ | **100.0000%** |

#### Discrete Segmentation Labels:

Ground truth synthesized with Background (0), Drywall (1), Non-Drywall (2), and Uncertain (3):

| Canvas Dimension | Total Pixels | Reconstructed Mismatches | Classification Error Rate | Reconstruction Status |
|:---:|:---:|:---:|:---:|:---:|
| `700 x 900` | 630,000 | 0 | 0.000000% | **PERFECT** |
| `1234 x 1500` | 1,851,000 | 0 | 0.000000% | **PERFECT** |
| `2592 x 1728` | 4,478,976 | 0 | 0.000000% | **PERFECT** |

---

### 2.3 Mask Invariant Enforcement & Corrupt Input Rejection

Tested against malformed inputs to `UnifiedMask`:

| Malformed Input Case | Test Array Specification | Result / Rejection Behavior | Exception Raised |
|:---|:---|:---|:---|
| Out of bounds ($>3$) | `uint8` array containing value `4` | REJECTED | `MaskValidationError: Invalid mask values found: [4]. Allowed values are {0, 1, 2, 3}.` |
| Large pixel value | `uint8` array containing value `255` | REJECTED | `MaskValidationError: Invalid mask values found: [255]. Allowed values are {0, 1, 2, 3}.` |
| Negative integer (int8) | `int8` array containing `-1` | REJECTED | `MaskValidationError: Expected dtype uint8, got int8` |
| Negative integer wrapped | `int8` `-1` cast to `uint8` ($= 255$) | REJECTED | `MaskValidationError: Invalid mask values found: [255]. Allowed values are {0, 1, 2, 3}.` |
| Negative integer (int32)| `int32` array containing `-10` | REJECTED | `MaskValidationError: Expected dtype uint8, got int32` |
| Floating point values | `float32` array `[[0.0, 1.0]]` | REJECTED | `MaskValidationError: Expected dtype uint8, got float32` |
| NaN floating point | `float32` array containing `np.nan` | REJECTED | `MaskValidationError: Expected dtype uint8, got float32` |
| Inf floating point | `float32` array containing `np.inf` | REJECTED | `MaskValidationError: Expected dtype uint8, got float32` |
| 1D array | Shape `(64,)` | REJECTED | `MaskValidationError: Expected 2D array (H, W), got shape (64,)` |
| 3D singleton channel | Shape `(64, 64, 1)` | REJECTED | `MaskValidationError: Expected 2D array (H, W), got shape (64, 64, 1)` |
| 3D RGB array | Shape `(64, 64, 3)` | REJECTED | `MaskValidationError: Expected 2D array (H, W), got shape (64, 64, 3)` |
| Non-array object | Python string `"mask.png"` | REJECTED | `MaskValidationError: Expected numpy ndarray, got <class 'str'>` |
| Tiler corrupt tile | Corrupt pixel injected into tile | DISCARDED | Discarded by tiler (`rejection_reason="INVALID_MASK_VALUE"`) |

**Architectural Finding on `validate_mask_array()`**:
The function `validate_mask_array()` was not exposed as a standalone top-level function in `drywall_detection.datasets.unified_format`. Instead, invariant validation is strictly encapsulated within the `UnifiedMask` class constructor. Any attempt to instantiate `UnifiedMask` with invalid data triggers `MaskValidationError`. To maintain full backward compatibility with any callers expecting a standalone function, adding a lightweight alias `validate_mask_array(arr: np.ndarray) -> np.ndarray` is recommended as an ergonomic enhancement.

---

### 2.4 Visual QC Generator Verification

1. **Triplet Dimensions**:
   - `create_triplet(img, mask, metadata=meta)`: Shape = `(548, 1536, 3)` (Height = $512 + 36 = 548$, Width = $512 \times 3 = 1536$, 3 BGR channels).
   - `create_triplet(img, mask, metadata=None)`: Shape = `(512, 1536, 3)`.
2. **Diagnostic Banner Text**:
   - Status formatting verified: `"WALL_SAMPLE"` (when `has_walls=True`), `"HARD_NEG"` (when `is_hard_negative=True`), `"EMPTY"` (otherwise).
   - Class percentages displayed with 1 decimal place (`DW: 0.0% | NON-DW: 0.0% | UNC: 0.0%`).
   - Background banner color: Dark gray `(35, 35, 35)`.
3. **Alpha Blending Numerical Fidelity**:
   - Model equation: $I_{\text{overlay}} = I_{\text{base}} \times (1 - \alpha) + C_{\text{class}} \times \alpha$ with $\alpha = 0.40$.
   - Tested on base gray image $(200, 200, 200)$:
     - Background: Overlay is identically $(200, 200, 200)$ ($\Delta = 0$).
     - Drywall (Green, BGR $(0, 255, 0)$): Theoretical $=(120, 222, 120)$, Actual $=(120, 222, 120)$ ($\Delta = 0$).
     - Non-Drywall (Red, BGR $(0, 0, 255)$): Theoretical $=(120, 120, 222)$, Actual $=(120, 120, 222)$ ($\Delta = 0$).
     - Uncertain (Yellow, BGR $(0, 255, 255)$): Theoretical $=(120, 222, 222)$, Actual $=(120, 222, 222)$ ($\Delta = 0$).
   - Maximum pixel difference across all classes: **$\Delta = 0$**.
4. **File Persistence & Reload**:
   - `save_qc_sample()` writes valid PNG files readable by OpenCV (`(548, 1536, 3) uint8`) and PIL (`(1536, 548) Mode 'RGB'`).

---

## 3. Full Test Suite Regression Check

Executed full test suite across the workspace:
```powershell
python -m pytest drywall_detection/tests/ -v
```
**Result**: `258 passed, 1 warning in 142.68s` (100% pass rate).
Breakdown:
- `drywall_detection/tests/test_tiling_stitching_stress.py`: **58 passed** (NEW)
- `drywall_detection/tests/test_adversarial_m1.py`: **19 passed**
- `drywall_detection/tests/test_m1_adversarial_stress.py`: **38 passed**
- `drywall_detection/tests/unit/test_datasets.py`: **28 passed**
- `drywall_detection/tests/test_licensing_audit.py`: **12 passed**
- `drywall_detection/tests/test_audit.py`: **20 passed**
- `drywall_detection/tests/test_coords.py`: **37 passed**
- `drywall_detection/tests/test_coords_stress.py`: **27 passed**
- `drywall_detection/tests/test_hardware.py`: **19 passed**
Total: **258 tests passing**.
