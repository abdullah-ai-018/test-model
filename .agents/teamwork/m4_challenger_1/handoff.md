# Adversarial Challenge Handoff Report — Milestone M4

**Agent**: `m4_challenger_1` (Milestone M4 Empirical Pipeline Challenger)  
**Parent Agent**: `orchestrator` (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Date**: 2026-11-09  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Test Execution Commands and Verbatim Outputs

#### Observation 1: Baseline Pipeline Test Suite Execution
- **Command**: `python -m pytest drywall_detection/tests/test_pipeline.py -v`
- **Result**: `11 passed in 150.29s (0:02:30)` (Exit code 0).
- **Verbatim log**:
  ```text
  drywall_detection/tests/test_pipeline.py::TestPDFLoadingAndMetadata::test_load_single_page_pdf PASSED [  9%]
  drywall_detection/tests/test_pipeline.py::TestPDFLoadingAndMetadata::test_load_multipage_pdf PASSED [ 18%]
  drywall_detection/tests/test_pipeline.py::TestPDFLoadingAndMetadata::test_render_dpi_scaling PASSED [ 27%]
  drywall_detection/tests/test_pipeline.py::TestCoordinateAndRotationPreservation::test_roundtrip_dimension_preservation PASSED [ 36%]
  drywall_detection/tests/test_pipeline.py::TestCoordinateAndRotationPreservation::test_page_rotation_preservation PASSED [ 45%]
  drywall_detection/tests/test_pipeline.py::TestSmallCanvasAndAspectRatios::test_sub_512_canvas_handling PASSED [ 54%]
  drywall_detection/tests/test_pipeline.py::TestSmallCanvasAndAspectRatios::test_extreme_aspect_ratio_ribbons PASSED [ 63%]
  drywall_detection/tests/test_pipeline.py::TestColorMappingAndSafetyVeto::test_color_taxonomy_dominance PASSED [ 72%]
  drywall_detection/tests/test_pipeline.py::TestColorMappingAndSafetyVeto::test_detail_1a_cmu_safety_veto PASSED [ 81%]
  drywall_detection/tests/test_pipeline.py::TestEndToEndPDFAnnotation::test_pdf_annotation_reopen_visual_check PASSED [ 90%]
  drywall_detection/tests/test_pipeline.py::TestEndToEndPDFAnnotation::test_cli_pipeline_execution PASSED [100%]
  ======================= 11 passed in 150.29s (0:02:30) ========================
  ```

#### Observation 2: Adversarial Stress Test Suite Authoring & Execution
- **File Created**: `drywall_detection/tests/test_m4_adversarial_stress.py` (260 lines, 60 distinct test invocations across 4 test classes).
- **Command**: `python -m pytest drywall_detection/tests/test_m4_adversarial_stress.py -v`
- **Result**: `60 passed in 212.74s (0:03:32)` (Exit code 0).
- **Verbatim log summary**:
  - `TestCoordinateAndRotationAdversarial::test_all_rotations_dimension_preservation` across 16 combinations (rotations 0°, 90°, 180°, 270° x sizes 1728x2592, 2592x1728, 1000x1000, 3000x500): 16 PASSED.
  - `TestCoordinateAndRotationAdversarial::test_pixel_drift_zero_across_rotations` across 0°, 90°, 180°, 270°: 4 PASSED.
  - `TestCoordinateAndRotationAdversarial::test_affine_transformation_bijective_precision` across 4 rotations x 3 DPIs (72, 150, 300): 12 PASSED.
  - `TestPathologicalAspectRatiosAndSmallCanvases::test_extreme_aspect_ratio_tiling` (512x5120, 5120x512, 300x3000, 3000x300): 4 PASSED.
  - `TestPathologicalAspectRatiosAndSmallCanvases::test_sub_512_small_canvases` ((1,1), (64,64), (128,256), (256,128), (511,511)): 5 PASSED.
  - `TestPathologicalAspectRatiosAndSmallCanvases::test_compute_mask_metrics_pathological_bounds`: 1 PASSED.
  - `TestCorruptAndPathologicalFiles::test_zero_byte_pdf_handling`: 1 PASSED.
  - `TestCorruptAndPathologicalFiles::test_truncated_corrupt_pdf_handling`: 1 PASSED.
  - `TestCorruptAndPathologicalFiles::test_non_pdf_binary_file_handling`: 1 PASSED.
  - `TestCorruptAndPathologicalFiles::test_unsupported_extension_rejection`: 1 PASSED.
  - `TestCorruptAndPathologicalFiles::test_batch_directory_resilience_to_corrupt_files`: 1 PASSED.
  - `TestColorBlendingAndAlphaBounds::test_alpha_boundary_values` across alpha in {0.0, 0.45, 1.0} and palettes {"standard", "vibrant"}: 6 PASSED.
  - `TestColorBlendingAndAlphaBounds::test_out_of_range_alpha_clamping` across alpha in {-1.0, -0.01, 1.01, 5.0, 100.0}: 5 PASSED.
  - `TestColorBlendingAndAlphaBounds::test_high_contrast_background_blending`: 1 PASSED.
  - `TestColorBlendingAndAlphaBounds::test_mask_to_rgba_overlay_properties`: 1 PASSED.

#### Observation 3: Combined Full Pipeline Suite Execution
- **Command**: `python -m pytest drywall_detection/tests/test_pipeline.py drywall_detection/tests/test_m4_adversarial_stress.py -v`
- **Result**: `71 passed in 165.48s (0:02:45)` (Exit code 0).

#### Observation 4: Coordinate Rotation Overlay Empirical Verification
- **Command**:
  ```python
  # Rotated visual coordinate test placing marker at visual pixels y in [20, 39], x in [50, 99]
  ```
- **Verbatim output across orientations**:
  ```text
  Rot 0:   y range [20, 39], x range [50, 99]. Expected y in [20, 39], x in [50, 99]
  Rot 90:  y range [20, 39], x range [50, 99]. Expected y in [20, 39], x in [50, 99]
  Rot 180: y range [20, 39], x range [50, 99]. Expected y in [20, 39], x in [50, 99]
  Rot 270: y range [20, 39], x range [50, 99]. Expected y in [20, 39], x in [50, 99]
  ```
  Result: **Exact 0 pixel drift** across every orientation.

#### Observation 5: Sub-512 Canvas and Extreme Ribbon Output Verification
- **Verbatim log**:
  ```text
  Sub-512 (1, 1) PASSED!
  Sub-512 (64, 64) PASSED!
  Sub-512 (128, 256) PASSED!
  Sub-512 (511, 511) PASSED!
  Aspect ratio (512, 5120) PASSED!
  Aspect ratio (5120, 512) PASSED!
  ```

#### Observation 6: Exception Types on Pathological Inputs
- 0-byte file: `fitz.open()` raises `<class 'fitz.fitz.EmptyFileError'>`, which inherits from `fitz.FileDataError` and `RuntimeError`.
- Truncated corrupt file: raises `<class 'fitz.fitz.FileDataError'>` (`RuntimeError`).
- Non-PDF binary stream: raises `<class 'fitz.fitz.FileDataError'>` (`RuntimeError`).
- Unsupported file extension passed to `pipeline.process()`: raises `ValueError("Unsupported file format: .docx")`.

---

## 2. Logic Chain

1. **Coordinate Roundtrip & Rotation Invariants (Observation 2 & 4)**:
   - PyMuPDF content streams are stored in unrotated CropBox coordinates (`page.cropbox`), whereas raster pixmaps are rendered in rotated visual space (`page.rect`).
   - In `PDFAnnotator.annotate_pdf_page_overlay`, calling `page.insert_image(page.cropbox, pixmap=pix_overlay, rotate=page.rotation, overlay=True)` rotates the visual pixmap into the unrotated cropbox geometry.
   - When the annotated document is re-opened and re-rendered at identical DPI, the overlay pixels map directly to the initial visual coordinates.
   - Empirical re-rendering confirmed that a green marker placed at `[20..39, 50..99]` in visual space reappears at precisely `[20..39, 50..99]` across all rotations: 0°, 90°, 180°, and 270°.
   - Across all 16 page geometry and orientation combinations, physical dimensions satisfied $|W_{out} - W_{in}| < 10^{-3}$ pt, $|H_{out} - H_{in}| < 10^{-3}$ pt, and vector linework streams remained intact (`len(page.get_drawings()) > 0`).

2. **Sliding-Window and Apodization Window Stitching (Observation 2 & 5)**:
   - For ribbons with extreme aspect ratios (10:1 horizontal banner 5120x512, 1:10 vertical column 512x5120, and non-tile-divisible ribbons 300x3000 and 3000x300), sliding-window tiling generates coordinates that fully cover the canvas.
   - The Hann window weighting `prob_canvas += weighted_probs` and `weight_canvas += hann` followed by `prob_canvas / np.maximum(weight_canvas, 1e-5)` normalizes stitched probabilities, ensuring probabilities sum to $\approx 1.0$ per pixel with zero NaNs or Infs.
   - For sub-512 canvases ((1,1), (64,64), (128,256), (511,511)), the small-canvas bounds guard pads the input to at least $512 \times 512$ with white background, performs inference, and unpads the output back to $(H_{orig}, W_{orig})$ with exact dimensional alignment.

3. **Exception and Pathological File Handling (Observation 2 & 6)**:
   - 0-byte, truncated, and random binary files passed as PDFs trigger `fitz.EmptyFileError` or `fitz.FileDataError`, both conforming to `RuntimeError`.
   - Passing unsupported extensions to `pipeline.process()` cleanly raises `ValueError("Unsupported file format")`.
   - In batch directory execution, exceptions from corrupted files are caught and isolated in `results` with `"status": "error"`, enabling the batch to complete successfully (`status: batch_completed`) while processing all valid files.

4. **Color Blending Clamping and Alpha Bounds (Observation 2)**:
   - In `render_blended_image`, `alpha_val = float(np.clip(alpha, 0.0, 1.0))` clamps all alpha inputs into $[0.0, 1.0]$.
   - At $\alpha = 0.0$, the returned array is bitwise identical to the input image.
   - At $\alpha = 1.0$, masked pixels are replaced with the exact RGB tuple from the chosen palette.
   - Output arrays are clipped using `np.clip(overlay, 0, 255).astype(np.uint8)`, ensuring no 8-bit integer overflow under high-contrast pure black (0) or pure white (255) backgrounds.

---

## 3. Caveats

1. **Hardware Host Throughput**: All sliding-window inference stress tests were executed on the local Windows CPU host using the SegFormer-B0 model. While fast for synthetic and small test images ($<1$s per sub-512 image, $\sim 8$s per 5120x512 ribbon), production multi-page 150 DPI architectural sheets require 3–4 minutes per sheet on CPU.
2. **PyMuPDF DPI Floating Precision**: When rendering at fractional zoom levels (e.g., $150 / 72 = 2.0833\dots$), pixmap dimensions may vary by $\pm 1$ pixel due to integer rounding (`round(rect.width * zoom)`). The pipeline handles this consistently by querying `pix.width` and `pix.height` directly.

---

## 4. Conclusion

The Milestone M4 PDF annotation and neural inference pipeline (`drywall_detection/pipeline/annotate.py`, `infer.py`) is **empirically robust, mathematically sound, and fully verified**.

- Rotation and coordinate preservation across 0°, 90°, 180°, and 270° exhibits **0 pixel drift**.
- Page width, height, and CropBox boundaries are preserved within $|W_{out} - W_{in}| < 10^{-3}$ pt.
- Extreme aspect ratios (10:1, 1:10) and sub-512 canvases (down to 1x1) execute with zero shape broadcast errors.
- Corrupt, truncated, and 0-byte files raise standard exceptions (`RuntimeError`, `ValueError`) cleanly and are resilient in batch runs.
- Alpha blending maintains strict $[0, 255]$ `uint8` limits across extreme alpha and background values.
- All 11 baseline tests and all 60 adversarial stress tests passed ($71/71$ total).

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce and verify these findings:

1. **Run full baseline pipeline test suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_pipeline.py -v
   ```
2. **Run newly authored adversarial stress test suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_m4_adversarial_stress.py -v
   ```
3. **Run combined suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_pipeline.py drywall_detection/tests/test_m4_adversarial_stress.py -v
   ```
4. **Invalidation Conditions**:
   - Any pixel drift $>0$ pixels when re-rendering rotated annotated PDF pages.
   - Any shape broadcast or mismatch crash when tiling 10:1 (5120x512) or sub-512 (1x1) canvases.
   - Any unhandled crash or non-standard exception when loading 0-byte or corrupt PDFs.
   - Any pixel value exceeding $[0, 255]$ or non-uint8 dtype in `render_blended_image`.
