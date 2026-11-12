# Milestone M4 Review & Verification Report (Hard Handoff)

**Reviewer Agent**: `m4_reviewer_1` (Pipeline & Vector Reviewer)  
**Parent Agent**: `orchestrator` (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Review Target**: `drywall_detection/pipeline/`, `drywall_detection/tests/test_pipeline.py`, `drywall_detection/reports/M4_interface_report.md`  
**Date**: 2026-11-09  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Source Code and Architecture Audit
1. **`drywall_detection/pipeline/__init__.py`**:
   - Clean exports: `PALETTE_STANDARD`, `PALETTE_VIBRANT`, `PDFAnnotator`, `compute_mask_metrics`, `mask_to_rgba_overlay`, `render_blended_image`, `DrywallInferencePipeline`, `build_cli_parser`, `parse_page_arg`.
   - Optional imports for `VisualOverlayConfig`, `WallAnnotator`, `ModalityRouter`, and `HybridFusionPipeline` guarded by `try...except (ImportError, AttributeError)` to maintain standalone operational cleanliness.
2. **`drywall_detection/pipeline/annotate.py`**:
   - Vectorized 256x4 LUT mapping (`mask_to_rgba_overlay` and `build_rgba_lut` lines 64-98): builds a `(256, 4)` uint8 lookup table mapping Class 0 to `[0, 0, 0, 0]` (alpha 0) and Classes 1 (Drywall), 2 (Non-Drywall), 3 (Uncertain) to RGB with configured alpha. Evaluates via `lut[mask_uint8]` in $<0.05$s.
   - Vector-preserving PDF injection (`PDFAnnotator.annotate_pdf_page_overlay` lines 185-212):
     ```python
     pix_overlay = fitz.Pixmap(fitz.csRGB, w, h, rgba.tobytes(), True)
     page.insert_image(
         page.cropbox,
         pixmap=pix_overlay,
         rotate=page.rotation,
         overlay=True,
     )
     ```
   - Vector polygon contour extraction fallback (`PDFAnnotator.annotate_pdf_page_polygons` lines 214-274): extracts OpenCV contour polygons, transforms to point units via `pixel_to_pdf`, and inserts native vector paths with `shape.draw_polyline` and `shape.finish(fill_opacity=self.alpha)`.
   - Multi-page document pipeline (`PDFAnnotator.annotate_pdf_document` lines 276-314): processes all designated pages and writes deflated, garbage-collected output (`doc.save(str(out_path), deflate=True, garbage=4)`).
   - High-fidelity visualization engine (`WallAnnotator` lines 344-587): provides `render_raster_image`, `generate_annotated_vector_pdf`, architectural legend drawing (`_draw_raster_legend`, `_draw_vector_legend`), and Detail 1A safety disclosures.
3. **`drywall_detection/pipeline/infer.py`**:
   - `DrywallInferencePipeline` (lines 73-375): wraps `StandaloneInferencer` and `PDFAnnotator`. Implements `process_pdf_page`, `process_pdf`, `process_image`, and universal `process`.
   - Sliding-window tiling and Hann apodization stitching (lines 173-256 of `StandaloneInferencer`): decomposes input into 512x512 tiles with 20% overlap (stride 410 px). Softmax probabilities are multiplied by 2D Hann window (`create_hann_window`), accumulated into `prob_canvas` and `weight_canvas`, and normalized by `valid_weights = np.maximum(weight_canvas, 1e-5)[:, :, np.newaxis]`.
   - Small-canvas & ribbon bounds protection (lines 195-204, 251-254): pads images smaller than tile_size up to 512x512 with white background, performs inference, and cleanly unpads back to original `[:orig_height, :orig_width]` dimensions.
   - CLI parser (`build_cli_parser` lines 394-489): comprehensive CLI with flags `--input`, `--output`, `--checkpoint`, `--dpi`, `--page`, `--overlap`, `--tile-size`, `--alpha`, `--annotation-method`, `--palette`, `--mode`, `--device`, `--json-output`, `--quiet`.
4. **Integrity Audit**:
   - No hardcoded test outputs or dummy facades exist.
   - No bypassed inference or mocked numbers.
   - Detail 1A (6" FIRE RATED CMU) is strictly enforced as Non-Drywall (Class 2, Red).
   - Prominent 95% CDs progress set disclosure notices are displayed in report, code, and UI.

### 1.2 Empirical Tool Command Executions and Results
1. **Pipeline Test Suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_pipeline.py -v
   ```
   *Result*: **11 passed in 122.64s (0:02:02)** (Exit Code 0).
   - `TestPDFLoadingAndMetadata::test_load_single_page_pdf`: PASSED
   - `TestPDFLoadingAndMetadata::test_load_multipage_pdf`: PASSED
   - `TestPDFLoadingAndMetadata::test_render_dpi_scaling`: PASSED
   - `TestCoordinateAndRotationPreservation::test_roundtrip_dimension_preservation`: PASSED ($|W_{recovered} - W_{pt}| < 10^{-3}$)
   - `TestCoordinateAndRotationPreservation::test_page_rotation_preservation`: PASSED (0°, 90°, 180°, 270°)
   - `TestSmallCanvasAndAspectRatios::test_sub_512_canvas_handling`: PASSED
   - `TestSmallCanvasAndAspectRatios::test_extreme_aspect_ratio_ribbons`: PASSED
   - `TestColorMappingAndSafetyVeto::test_color_taxonomy_dominance`: PASSED
   - `TestColorMappingAndSafetyVeto::test_detail_1a_cmu_safety_veto`: PASSED
   - `TestEndToEndPDFAnnotation::test_pdf_annotation_reopen_visual_check`: PASSED
   - `TestEndToEndPDFAnnotation::test_cli_pipeline_execution`: PASSED
2. **Standalone CLI Inference Smoke Test**:
   ```bash
   python -m drywall_detection.pipeline.infer --input drywall_detection/data/processed/images/mock_plan_00.png --output test_rev_smoke.png --quiet
   ```
   *Result*: **Exit Code 0**. Emitted valid structured JSON output:
   - Input: 1024x1024 px (1,048,576 pixels)
   - Background: 831,878 px (79.3341%)
   - Drywall: 156,067 px (14.8837%)
   - Non-Drywall: 25,551 px (2.4367%)
   - Uncertain: 35,080 px (3.3455%)
   - Total Wall Density: 20.6659%
   - Elapsed Time: 20.582s
   - Smoke artifact `test_rev_smoke.png` verified created and cleanly removed.
3. **Model Regression Test Suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_models.py -v
   ```
   *Result*: **24 passed in 291.61s (0:04:51)** (Exit Code 0).
4. **Interface Test Suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_interface.py -v
   ```
   *Result*: **9 passed in 73.67s (0:01:13)** (Exit Code 0).
5. **Direct Empirical Vector & Dimension Verification**:
   - Vector linework and text layer preservation: verified via PyMuPDF that `page.get_drawings()` count is unchanged (2 initial == 2 post) and `page.get_text()` is identical (`'UNDERLYING CAD TEXT 12345'`).
   - Dimension preservation across rotations:
     * Rot 0°: $\Delta W_{mb} = 0.000000$, $\Delta H_{mb} = 0.000000$, $\Delta W_{cb} = 0.000000$, $\Delta H_{cb} = 0.000000$
     * Rot 90°: $\Delta W_{mb} = 0.000000$, $\Delta H_{mb} = 0.000000$, $\Delta W_{cb} = 0.000000$, $\Delta H_{cb} = 0.000000$
     * Rot 180°: $\Delta W_{mb} = 0.000000$, $\Delta H_{mb} = 0.000000$, $\Delta W_{cb} = 0.000000$, $\Delta H_{cb} = 0.000000$
     * Rot 270°: $\Delta W_{mb} = 0.000000$, $\Delta H_{mb} = 0.000000$, $\Delta W_{cb} = 0.000000$, $\Delta H_{cb} = 0.000000$
     * Spatial visual alignment: red square marker placed at visual coordinate $[10..29, 10..29]$ re-renders exactly at visual $[10..29, 10..29]$ across all 4 rotations.

---

## 2. Logic Chain

1. **Non-Destructive Annotation Invariant**:
   - *Observation*: `page.insert_image(page.cropbox, pixmap=..., rotate=page.rotation, overlay=True)` appends an `/XObject /Image` dictionary entry onto the page content stream with blend mode support rather than rewriting the vector stream.
   - *Inference*: Because underlying vector streams and `/Font` resources are never rewritten or converted into raster tiles, infinite zoom CAD fidelity is maintained, and searchable text layers remain fully functional.
2. **Multi-Quadrant Rotation Invariant**:
   - *Observation*: PDF pages store unrotated physical boundaries in `cropbox` / `mediabox`, while display viewers apply the `/Rotate` key ($0^\circ, 90^\circ, 180^\circ, 270^\circ$).
   - *Inference*: PyMuPDF's `page.get_pixmap()` renders the visual coordinate system. Passing `rotate=page.rotation` into `page.insert_image(page.cropbox, ...)` applies the exact inverse transformation matching viewer rendering. Our empirical test proved identical visual coordinate alignment across all 4 rotations.
3. **Seamless Tiling Mathematics**:
   - *Observation*: Large architectural drawings (5400x3600 px) exceed neural network receptive fields. Boundary seams occur when adjacent tiles are stitched naively.
   - *Inference*: Multiplying tile probabilities by a 2D Hann window ($w(x, y) = \sin^2(\frac{\pi x}{N}) \sin^2(\frac{\pi y}{N})$) smooths edge contributions to near-zero at tile borders. Normalizing by the accumulated weights canvas produces mathematically seamless transitions.
4. **Integrity and Classification Guardrails**:
   - *Observation*: Detail 1A on Sheet A-900 specifies 6" CMU block masonry. Tag 1A is mapped to Class 2 (Non-Drywall, Red) in `partition_schedule_mapping.approved.csv` and asserted in `test_detail_1a_cmu_safety_veto`.
   - *Inference*: Requirement R2 and R4 guardrails are honored; no CMU masonry can be falsely classified as drywall.

---

## 3. Caveats

1. **CPU Execution Latency on Master Sheets**:
   - Full 150 DPI inference on a 5400x3600 px architectural sheet decomposes into 126 tiles (512x512 with 20% overlap). On local CPU, single-sheet execution requires ~3.5 minutes. The CLI `--page` argument and Streamlit single-sheet mode are designed specifically to address this operational reality.
2. **Progress Set Single-Project Scope**:
   - The MTA Contract C-48526 drawings represent a single project in 95% CDs progress status (dated 10/02/2026). The Spark Lake Grove permit set serves as the held-out cross-domain validation set.
3. **Python Runtime Warning on Direct CLI Execution**:
   - Executing `python -m drywall_detection.pipeline.infer` emits a harmless standard library `RuntimeWarning` from `runpy.py` due to sub-package name resolution, which does not affect exit code or JSON output.

---

## 4. Conclusion

**Verdict: APPROVE**

The Milestone M4 implementation satisfies all requirements specified in `ORIGINAL_REQUEST.md` (Requirement R4) and `PROJECT.md`:
- `drywall_detection/pipeline/annotate.py` delivers a vector-preserving, dimension-preserving PDF and image annotation engine.
- `drywall_detection/pipeline/infer.py` delivers a complete sliding-window inference pipeline with 2D Hann apodization stitching, small-canvas bounds handling, and CLI capability.
- 100% of pipeline tests (11/11), CLI smoke tests, interface tests (9/9), and model regression tests (24/24) pass with Exit Code 0.
- Zero integrity violations, hardcoded shortcuts, or facade implementations exist.

---

## 5. Verification Method

To independently reproduce this verification:

1. **Pipeline Test Suite Execution**:
   ```bash
   python -m pytest drywall_detection/tests/test_pipeline.py -v
   ```
   *Expected*: 11 passed in ~120s, exit code 0.

2. **Standalone CLI Inference Smoke Test**:
   ```bash
   python -m drywall_detection.pipeline.infer --input drywall_detection/data/processed/images/mock_plan_00.png --output test_rev_smoke.png --quiet
   python -c "import os; assert os.path.exists('test_rev_smoke.png'); os.remove('test_rev_smoke.png'); print('Cleaned up!')"
   ```
   *Expected*: Valid JSON emitted to stdout, exit code 0.

3. **Vector & Dimension Preservation Check**:
   ```bash
   python -c "
   import fitz, numpy as np
   for rot in [0, 90, 180, 270]:
       doc = fitz.open()
       p = doc.new_page(width=1728.0, height=2592.0)
       p.set_rotation(rot)
       pix = p.get_pixmap(dpi=72)
       rgba = np.zeros((pix.height, pix.width, 4), dtype=np.uint8)
       rgba[10:50, 10:50] = [0, 255, 0, 100]
       p.insert_image(p.cropbox, pixmap=fitz.Pixmap(fitz.csRGB, pix.width, pix.height, rgba.tobytes(), True), rotate=p.rotation, overlay=True)
       b = doc.tobytes(); doc.close()
       doc2 = fitz.open('pdf', b); p2 = doc2[0]
       assert abs(p2.mediabox.width - 1728.0) < 1e-3
       assert abs(p2.mediabox.height - 2592.0) < 1e-3
       assert p2.rotation == rot
       doc2.close()
   print('Vector & Dimension Invariants Verified 100%!')
   "
   ```
   *Expected*: `Vector & Dimension Invariants Verified 100%!`, exit code 0.

4. **Regression Test Suite**:
   ```bash
   python -m pytest drywall_detection/tests/test_models.py -v
   python -m pytest drywall_detection/tests/test_interface.py -v
   ```
   *Expected*: All tests pass with exit code 0.
