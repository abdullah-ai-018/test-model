# Forensic Integrity Audit Report: Milestone M4 Deliverables

**Auditor**: `m4_auditor_1` (Forensic Integrity Auditor)  
**Parent Agent**: `orchestrator` (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Date**: 2026-11-09  
**Profile**: General Project (Integrity Mode: `development` / Ground Truth Precedence)  
**Verdict**: **CLEAN**

---

## 1. Observation

### 1.1 Scope of Forensic Investigation
The forensic audit independently inspected and executed all Milestone M4 deliverables across:
- `drywall_detection/pipeline/__init__.py`
- `drywall_detection/pipeline/annotate.py`
- `drywall_detection/pipeline/infer.py`
- `drywall_detection/app/app.py` & `drywall_detection/app.py`
- `drywall_detection/tests/test_pipeline.py`
- `drywall_detection/tests/test_interface.py`
- `drywall_detection/datasets/unified_format.py`
- `drywall_detection/vector/schedule_parser.py`
- `drywall_detection/classification/classifier.py`
- `drywall_detection/data/partition_schedule_mapping.approved.csv`

### 1.2 Static AST & Anti-Cheating Scan Results
An automated AST traversal scanning every function and class across all M4 pipeline and application scripts revealed:
- **0** functions with empty bodies or only `pass`.
- **0** functions raising `NotImplementedError`.
- **0** functions returning hardcoded constants or fake metric values.
- **0** instances of `mock`, `stub`, `fake`, `dummy`, `TODO`, or `FIXME` in implementation code.
- Pre-populated artifact scan confirmed zero pre-existing test outputs or fake verification logs in `drywall_detection/`.

### 1.3 Empirical Vector Linework Preservation & Geometry Check
An independent script dynamically constructed a vector PDF containing CAD paths, vector rectangles, and text annotations, and processed it via `PDFAnnotator.annotate_pdf_document` with a 4-class segmentation mask.
Direct before-and-after inspection of the PDF object model yielded:
```text
Drawings: 2 -> 2
Text match: True
Rotation: 90 -> 90
MediaBox Delta: 0.000000 pt, 0.000000 pt
CropBox Delta: 0.000000 pt, 0.000000 pt
Overlay images added: 1
ALL EMPIRICAL VECTOR PRESERVATION CHECKS PASSED!
```
Underlying CAD vector paths (`page.get_drawings()`) and text (`page.get_text()`) remained 100% intact with zero rasterization flattening.

### 1.4 Strict 4-Class Taxonomy & Detail 1A Safety Veto Inspection
- **4-Class Taxonomy Guardrail**:
  * Class 0: Background (Transparent overlay, `#FFFFFF` canvas)
  * Class 1: Drywall (Green `#00FF00` / `#00C853`)
  * Class 2: Non-Drywall (Red `#FF0000` / `#D50000`)
  * Class 3: Uncertain (Yellow `#FFFF00` / `#FFD600`)
  * In `drywall_detection/datasets/unified_format.py`, `MSDConverter`, `CubiCasaConverter`, and `RasterMaskConverter` default strictly to `target_class: DatasetClass = DatasetClass.UNCERTAIN` (Class 3), preventing untagged academic datasets from contaminating confirmed Drywall.
- **Detail 1A CMU Safety Veto**:
  * Multi-layer defense-in-depth verified:
    - `drywall_detection/vector/schedule_parser.py` (lines 665-670):
      ```python
      if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"):
          raise ValueError(
              "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
              "CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!"
          )
      ```
    - `drywall_detection/classification/classifier.py` (lines 90-96):
      ```python
      if self.matched_tag and self.matched_tag.upper().strip() == "1A":
          if self.classification.strip().lower() in DRYWALL_SYNONYMS or self.classification == ClassificationClass.DRYWALL.value:
              raise IntegrityViolationError(
                  "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                  "CANNOT be classified as Drywall!"
              )
      ```
    - `drywall_detection/data/partition_schedule_mapping.approved.csv` row 2 confirms Detail 1A is mapped to `Non-Drywall`.

### 1.5 Independent Verification Command Executions & Exact Outputs

#### Test Target 1: Pipeline Tests (`test_pipeline.py`)
```bash
python -m pytest drywall_detection/tests/test_pipeline.py -v
```
**Output**:
```text
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\TEC ZONE\OneDrive\Desktop\test-model
collected 11 items

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

======================= 11 passed in 127.05s (0:02:07) ========================
```
*Result*: Exit Code 0. 11/11 tests passed.

#### Test Target 2: Interface Tests (`test_interface.py`)
```bash
python -m pytest drywall_detection/tests/test_interface.py -v
```
**Output**:
```text
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\TEC ZONE\OneDrive\Desktop\test-model
collected 9 items

drywall_detection/tests/test_interface.py::TestStreamlitSyntaxAndSmoke::test_app_syntax_and_importability PASSED [ 11%]
drywall_detection/tests/test_interface.py::TestStreamlitSyntaxAndSmoke::test_streamlit_cli_smoke PASSED [ 22%]
drywall_detection/tests/test_interface.py::TestStreamlitAppTestMockSession::test_apptest_initial_render PASSED [ 33%]
drywall_detection/tests/test_interface.py::TestStreamlitAppTestMockSession::test_apptest_parameter_reconfiguration PASSED [ 44%]
drywall_detection/tests/test_interface.py::TestStreamlitAppTestMockSession::test_apptest_sample_drawing_selection PASSED [ 55%]
drywall_detection/tests/test_interface.py::TestTakeoffArithmeticAndSafety::test_takeoff_zero_division_guard PASSED [ 66%]
drywall_detection/tests/test_interface.py::TestTakeoffArithmeticAndSafety::test_takeoff_arithmetic_precision PASSED [ 77%]
drywall_detection/tests/test_interface.py::TestTakeoffArithmeticAndSafety::test_csv_serialization PASSED [ 88%]
drywall_detection/tests/test_interface.py::TestEdgeCasesAndCorruptInputs::test_empty_and_corrupt_pdf_upload PASSED [100%]

============================= 9 passed in 51.62s ==============================
```
*Result*: Exit Code 0. 9/9 tests passed.

#### Test Target 3: CLI Smoke Test
```bash
python -m drywall_detection.pipeline.infer --input drywall_detection/data/processed/images/mock_plan_00.png --output test_auditor_smoke.png --quiet
```
**Output**:
```json
{
  "status": "success",
  "type": "image",
  "input_path": "drywall_detection\\data\\processed\\images\\mock_plan_00.png",
  "output_path": "test_auditor_smoke.png",
  "output_file_size_kb": 8.7,
  "model": {
    "architecture": "segformer_b0",
    "device": "cpu"
  },
  "parameters": {
    "tile_size": 512,
    "overlap": 0.2,
    "alpha": 0.4,
    "mode": "overlay"
  },
  "pages": [
    {
      "page_num": 1,
      "dimensions_px": [
        1024,
        1024
      ],
      "dimensions_pt": null,
      "rotation_deg": 0,
      "total_pixels": 1048576,
      "class_pixel_counts": {
        "background": 831878,
        "drywall": 156067,
        "non_drywall": 25551,
        "uncertain": 35080,
        "total_walls": 216698
      },
      "class_percentages": {
        "background": 79.3341,
        "drywall": 14.8837,
        "non_drywall": 2.4367,
        "uncertain": 3.3455
      },
      "drywall_percentage": 14.8837,
      "wall_density_percentage": 20.6659,
      "elapsed_sec": 33.969
    }
  ],
  "aggregate_statistics": {
    "total_pixels": 1048576,
    "total_drywall_pixels": 156067,
    "total_non_drywall_pixels": 25551,
    "total_uncertain_pixels": 35080,
    "overall_drywall_pct": 14.8837,
    "total_elapsed_sec": 33.969
  }
}
```
*Result*: Exit Code 0. Temporary artifact `test_auditor_smoke.png` confirmed on disk and safely deleted.

#### Test Target 4: Headless Streamlit AppTest
```bash
python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('drywall_detection/app/app.py', default_timeout=30); at.run(); assert len(at.exception) == 0; print('AppTest Passed!')"
```
**Output**:
```text
AppTest Passed!
```
*Result*: Exit Code 0. 0 unhandled exceptions.

#### Test Target 5: Regression Suite (`test_models.py` + `test_m3_adversarial_loss_splits.py`)
```bash
python -m pytest drywall_detection/tests/test_models.py drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
```
**Output**:
```text
======================= 42 passed in 465.89s (0:07:45) ========================
```
*Result*: Exit Code 0. 42/42 tests passed. Zero regressions across SegFormer-B0 architecture, ResNet U-Net models, compound losses, boundary IoU, and split quarantine integrity checks.

---

## 2. Logic Chain

1. **Anti-Cheating Verification**:
   - The AST analysis examined all function and class definitions across `annotate.py`, `infer.py`, and `app.py`.
   - All modules execute genuine image processing (NumPy LUT indexing, OpenCV contour analysis, PyMuPDF Pixmap rendering, Hann apodization sliding-window tensor stitching).
   - No facades or mock returns exist.

2. **Vector Linework & Geometry Preservation**:
   - Standard PDF libraries that convert pages to raster images destroy vector sharpness, inflate file sizes, and strip searchable text.
   - The audited code uses native PyMuPDF `page.insert_image(page.cropbox, pixmap=pix_overlay, rotate=page.rotation, overlay=True)`.
   - In our empirical verification, the vector drawing count before (2) and after (2) was identical, text strings matched character-for-character, and page MediaBox/CropBox dimensions experienced zero numerical drift ($< 10^{-6}$ pt).

3. **Taxonomy & Detail 1A Safety Invariant**:
   - The strict 4-class taxonomy is maintained throughout: Background (0), Drywall (1, Green), Non-Drywall (2, Red), Uncertain (3, Yellow).
   - Untagged walls and academic datasets map strictly to Class 3 Uncertain.
   - Detail 1A (6" FIRE RATED CMU) masonry partition is guarded by fatal `ValueError` / `IntegrityViolationError` exceptions at both schedule parsing and spatial classification stages, preventing any accidental or malicious re-classification as Drywall.

4. **Empirical Independent Execution**:
   - 62 distinct automated tests (11 pipeline + 9 interface + 1 CLI smoke + 1 AppTest + 42 regression) executed independently in clean processes.
   - All 62 tests terminated with Exit Code 0.

---

## 3. Caveats

1. **Host CPU Throughput**:
   - In the absence of an NVIDIA CUDA GPU on the host environment, 512x512 neural sliding-window inference runs on Windows CPU threads. Full-sheet processing takes ~30–40s per megapixel. UI responsiveness is preserved via NumPy session-state opacity decoupling.
2. **Master PDF Progress Set Notice**:
   - The MTA Contract C-48526 drawing set represents a 95% CDs progress set from a single project. The mandatory disclosure notice is prominently displayed in the UI banner and report headers.

---

## 4. Conclusion

All forensic integrity checks passed unconditionally:
- Anti-cheating scan: **PASS** (Zero stubs, zero facades, zero mocks)
- Vector linework preservation: **PASS** (CAD paths and text 100% intact, $\Delta < 10^{-3}$ pt)
- 4-Class taxonomy guardrails: **PASS** (Academic datasets default strictly to Class 3 Uncertain)
- Detail 1A CMU safety veto: **PASS** (Multi-layer fatal fail-fast verified)
- Independent test execution: **PASS** (62/62 tests passed, Exit Code 0 across all targets)

**Binary Verdict**: **`CLEAN`**

Milestone M4 is unconditionally approved. The project is cleared to proceed to Milestone M5 (Final Validation, E2E Testing & Showcase Delivery).

---

## 5. Verification Method

To independently reproduce this forensic audit:
```bash
# 1. Pipeline Test Suite (11 tests)
python -m pytest drywall_detection/tests/test_pipeline.py -v

# 2. Interface Test Suite (9 tests)
python -m pytest drywall_detection/tests/test_interface.py -v

# 3. CLI Smoke Test
python -m drywall_detection.pipeline.infer --input drywall_detection/data/processed/images/mock_plan_00.png --output test_smoke.png --quiet
python -c "import os; assert os.path.exists('test_smoke.png'); os.remove('test_smoke.png'); print('Smoke Verified!')"

# 4. Streamlit Headless AppTest
python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('drywall_detection/app/app.py', default_timeout=30); at.run(); assert len(at.exception) == 0; print('AppTest Verified!')"

# 5. Full Regression Suite (42 tests)
python -m pytest drywall_detection/tests/test_models.py drywall_detection/tests/test_m3_adversarial_loss_splits.py -v
```
