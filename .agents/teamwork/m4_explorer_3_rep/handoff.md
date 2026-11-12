# Handoff Report: Held-Out Drawing Validation & Test Suite Architecture (Milestone M4)

**Agent**: `m4_explorer_3_rep`  
**State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_3_rep`  
**Parent Conversation ID**: `3c1a82ae-9b50-494e-b173-0369a8d4a486`  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Handoff Type**: Hard (Investigation & Test Suite Architecture Complete)

---

## 1. Observation

### 1.1 Available Held-Out Architectural Drawings Inventory
Through filesystem queries and PyMuPDF programmatic auditing, the following held-out drawing assets were identified and profiled in the local environment:

1. **MTA Contract C-48526, 99th Street Sheet A-104 (Page 18 / Page Index 17 of Master PDF)**
   - **File Path**: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
   - **Corroborating Ground Truth**: `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (Page index 4)
   - **Total Pages in Master PDF**: 71 pages
   - **Sheet Identity**: Sheet A-104, "FOURTH FLOOR CONSTRUCTION PLAN" (MTA 95% CDs Progress Set, dated 10/02/2026).
   - **Native Dimensions**: Unrotated MediaBox: `width = 1728.0 pt` (24"), `height = 2592.0 pt` (36"). Rendered visual rectangle: `2592.0 x 1728.0 pt` (Landscape, aspect ratio: `1.500`).
   - **Page Rotation**: `90° CW` (`page.rotation = 90`).
   - **Vector vs. Scanned Profile**: Strictly vector-based CAD drawing.
     * Vector drawing paths (`page.get_drawings()`): **50,419 paths**.
     * Text layer characters (`page.get_text()`): **12,903 characters**.
     * Embedded raster images (`page.get_images()`): **3 images** (small title block logos).
   - **Verified Ground Truth**: Exactly **69 verified drywall wall centerlines** annotated by Usman on Page 4 of `drywall_walls_marked_red_by_Usman.pdf` (confirmed via line annotation extraction in `drywall_detection/data/ground_truth_builder.py:131, 549-564` and `drywall_detection/tests/test_vector.py:543`).
   - **Split Quarantine Status**: Strictly quarantined from training and validation sets; reserved 100% for held-out evaluation (`drywall_detection/data/splits/quarantine.json`).

2. **Spark Lake Grove Permit Set (`test Spark Lake Grove - Permit Set.pdf`)**
   - **File Path**: `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf`
   - **File Size**: **35,661,630 bytes (~35.6 MB)**
   - **Total Pages**: **54 pages**
   - **Native Dimensions**: `2592.0 x 1728.0 pt` (Landscape ARCH D, 36" x 24", aspect ratio: `1.500`).
   - **Heterogeneous Page Rotations**:
     * `270° CW`: Pages 0, 2–11, 16–25 (22 pages)
     * `180° CW`: Page 1 (1 page)
     * `90° CW`: Pages 12–15 (4 pages)
     * `0°` (Unrotated): Pages 26–53 (27 pages)
   - **Vector vs. Scanned Profile**: Highly complex multi-page vector permit drawing set.
     * Page 0 (270°): 53,576 vector paths, 10,352 text characters, 2 raster images.
     * Page 1 (180°): 43,438 vector paths, 798 text characters, 6 raster images.
     * Page 26 (0°): 108,609 vector paths, 1,420 text characters, 0 raster images.
   - **Suitability**: Ideal real-world multi-page benchmark for heterogeneous orientation handling, multi-page streaming, and cross-domain generalization.

---

### 1.2 Rasterization Resolution & Memory Footprint Characterization
Empirical benchmarking was executed using PyMuPDF (`fitz.Page.get_pixmap`) and Python garbage collection profiling on Sheet A-104 and Spark Lake Grove:

| Parameter / Metric | 72 DPI (Base / Thumbnail) | 150 DPI (Production Standard) | 300 DPI (High-Resolution) |
|---|---|---|---|
| **Rendered Pixel Dimensions** | `2,592 x 1,728 px` | `5,400 x 3,600 px` | `10,800 x 7,200 px` |
| **Total Pixels per Page** | 4,478,976 px (~4.48 MP) | 19,440,000 px (~19.44 MP) | 77,760,000 px (~77.76 MP) |
| **Uncompressed Pixmap Buffer** | **12.81 MB** (13,437,016 B) | **55.62 MB** (58,320,088 B) | **222.47 MB** (233,280,088 B) |
| **Render Latency (A-104)** | 1.558 s | 3.293 s | 1.979 s |
| **Render Latency (Spark P1)** | 2.438 s | 6.162 s | 39.589 s |
| **Tile Grid (512x512, 20% overlap)** | 6 x 4 = **24 tiles** | 13 x 9 = **117 tiles** | 26 x 17 = **442 tiles** |
| **Float32 Probability Canvas (`H x W x 4`)** | `2592 x 1728 x 4 x 4` = **71.66 MB** | `3600 x 5400 x 4 x 4` = **296.63 MB** | `7200 x 10800 x 4 x 4` = **1,244.16 MB (~1.24 GB)** |
| **Float32 Weight Canvas (`H x W x 1`)** | 17.92 MB | 74.16 MB | 311.04 MB |
| **Estimated Peak Working Set** | ~110 MB | **~435 MB** | **~1,840 MB (~1.84 GB)** |
| **Host 550MB Headroom Safety** | **SAFE** (<20% headroom) | **SAFE** (within ~550MB limit) | **UNSAFE / CRITICAL OOM HAZARD** |

**Critical Memory Finding**:
At 300 DPI, full-canvas float32 probability accumulation requires **1.24 GB RAM for the probability tensor alone**, which unconditionally crashes with Out-Of-Memory on systems constrained to ~550MB available headroom. Therefore:
1. `150 DPI` is confirmed as the optimal production default.
2. In-process garbage collection (`gc.collect()`) and explicit pixmap buffer deletion are mandatory between pages.
3. 300 DPI mode must use streaming tile-based accumulation or downsampled accumulation grids.

---

### 1.3 Local Streamlit Environment Verification
1. **Streamlit Installation**: Version `1.48.1` is installed and verified.
2. **AppTest Support**: `from streamlit.testing.v1 import AppTest` imported successfully.
3. **Execution on `drywall_detection/app.py`**:
   - `AppTest.from_file('drywall_detection/app.py', default_timeout=30).run()` completed with **0 exceptions** (`len(at.exception) == 0`).
   - Sidebar components: 14 elements discovered.
   - Identified widget accessors:
     * `at.select_slider[0]`: "Rendering Resolution (DPI)" (default: 150)
     * `at.slider[0]`: "Overlay Transparency (Alpha)" (default: 0.45)
     * `at.slider[1]`: "Tile Overlap Fraction" (default: 0.2)
     * `at.selectbox[0]`: "Or choose a pre-loaded drawing"
     * `at.get("file_uploader")`: File uploader widget

---

### 1.4 Inference Boundary & Small-Canvas Verification
Empirically executed sliding-window inference on irregular and boundary shapes using `StandaloneInferencer`:
- `(256, 256)`: output mask `(256, 256)`, probs `(256, 256, 4)` — PASS (zero broadcast error)
- `(64, 64)`: output mask `(64, 64)`, probs `(64, 64, 4)` — PASS
- `(5000, 500)` (10:1 horizontal banner): output mask `(5000, 500)`, probs `(5000, 500, 4)` — PASS
- `(500, 5000)` (1:10 vertical column): output mask `(500, 5000)`, probs `(500, 5000, 4)` — PASS

---

## 2. Logic Chain

1. **Held-Out Independence**: Sheet A-104 represents the 4th Floor of the MTA 99th St set. Historical training manifests (`drywall_detection/data/splits/quarantine.json` and `test.json`) confirm that Sheet A-104 was quarantined with 69 verified centerlines. Testing the inference pipeline and interface against Sheet A-104 and Spark Lake Grove guarantees 100% un-leaked evaluation against unseen geometries.
2. **Dimension Preservation Mathematics**: When rendering a PDF page at resolution $D$ (DPI) where base PDF points are $72 \text{ pt/inch}$, the pixel dimensions are:
   $$W_{\text{px}} = \text{round}\left(W_{\text{pt}} \cdot \frac{D}{72}\right), \quad H_{\text{px}} = \text{round}\left(H_{\text{pt}} \cdot \frac{D}{72}\right)$$
   When exporting the annotated image back to PDF with resolution metadata $D$, the recovered PDF points are:
   $$W_{\text{recovered}} = \frac{W_{\text{px}}}{D} \cdot 72 = W_{\text{pt}}, \quad H_{\text{recovered}} = \frac{H_{\text{px}}}{D} \cdot 72 = H_{\text{pt}}$$
   Empirical verification confirmed $W_{\text{recovered}} = 2592.0 \text{ pt}$ and $H_{\text{recovered}} = 1728.0 \text{ pt}$ with zero numerical drift ($\Delta = 0.0 \text{ pt}$).
3. **Safety Veto Invariant**: Tag 1A (6" FIRE RATED CMU) represents concrete masonry block. In accordance with the approved schedule mapping (`drywall_detection/data/partition_schedule_mapping.approved.csv`), Tag 1A must map to Class 2 (`Non-Drywall`, Red), never Class 1 (`Drywall`, Green). Test suites must explicitly probe Tag 1A classification.
4. **Memory Guardrail Invariant**: Because a single 300 DPI float32 probability canvas requires 1.24 GB RAM, running multi-page batch inference or high-resolution full-canvas stitching without memory bounds will exhaust the host's 550MB-850MB headroom. Test suites must mandate in-process garbage collection, verify page-by-page memory reclamation, and assert that 150 DPI is the safe default.

---

## 3. Caveats

1. **Master PDF Single-Project Progress Limitation**: In strict compliance with zero-tolerance rule #5, all tests and reports must note that MTA Contract C-48526 is a 95% CDs progress set representing a single project. Spark Lake Grove serves as the cross-domain external validation set.
2. **File Paths in Downloads Directory**: The held-out drawings currently reside in `C:\Users\TEC ZONE\Downloads\`. Test fixtures should check for the presence of these files and provide self-contained synthetic PDF generation fallbacks if external files are temporarily missing.
3. **CLI Entry Point Consistency**: PROJECT.md specifies `drywall_detection/pipeline/infer.py`, while currently `drywall_detection/checkpoints/best_model/infer.py` exists. The test suite must test both the new `drywall_detection.pipeline.infer` CLI module and the programmatic `StandaloneInferencer` API.

---

## 4. Conclusion & Test Suite Specifications

A comprehensive 2-file test suite architecture has been designed to validate Milestone M4 deliverables:
1. `drywall_detection/tests/test_pipeline.py` (Pipeline, coordinates, rotation, color mapping, CLI)
2. `drywall_detection/tests/test_interface.py` (Streamlit syntax, CLI smoke, AppTest headless session, widget state)

### 4.1 Detailed Specification: `drywall_detection/tests/test_pipeline.py`

```python
"""
drywall_detection/tests/test_pipeline.py
Test Architecture Specification for Inference & Annotation Pipeline
"""

# Test Class 1: PDF Ingestion & Dimension Preservation
class TestPDFLoadingAndMetadata:
    - test_load_single_page_pdf():
        Creates synthetic 1-page PDF (MediaBox 2592x1728 pt).
        Asserts page count == 1, dimensions match bit-for-bit.
    - test_load_multipage_pdf():
        Creates synthetic 3-page PDF with mixed rotations (0°, 90°, 270°).
        Asserts page count == 3, per-page rotations extracted accurately.
    - test_render_dpi_scaling():
        Renders at 72, 150, 300 DPI.
        Asserts width_px == round(rect.width * dpi / 72.0).

# Test Class 2: Coordinate & Rotation Preservation
class TestCoordinateAndRotationPreservation:
    - test_roundtrip_dimension_preservation():
        Runs inference on 2592x1728 pt PDF, exports annotated PDF.
        Re-opens with PyMuPDF; asserts abs(out_page.rect.width - 2592.0) < 1e-3.
        Asserts abs(out_page.rect.height - 1728.0) < 1e-3.
    - test_page_rotation_preservation():
        Feeds pages with 0°, 90°, 180°, 270° rotations.
        Asserts out_page.rotation == in_page.rotation across all 4 orientations.

# Test Class 3: Small-Canvas & Extreme Aspect Ratio Bounds
class TestSmallCanvasAndAspectRatios:
    - test_sub_512_canvas_handling():
        Feeds (64, 64), (128, 256), (256, 256), and (511, 511) images.
        Asserts zero broadcast errors; returned mask shape exactly matches input.
    - test_extreme_aspect_ratio_ribbons():
        Feeds 10:1 horizontal banner (5000 x 500 px) and 1:10 column (500 x 5000 px).
        Asserts seamless tiling and exact shape recovery.

# Test Class 4: Color Mapping & Detail 1A Safety Veto
class TestColorMappingAndSafetyVeto:
    - test_color_taxonomy_dominance():
        Asserts Drywall (1) has G > R and G > B.
        Asserts Non-Drywall (2) has R > G and R > B.
        Asserts Uncertain (3) has R > 180, G > 180, B < 80.
        Asserts Background (0) is transparent / unaltered.
    - test_detail_1a_cmu_safety_veto():
        Queries approved schedule mapping for Tag 1A.
        Asserts proposed_class == "Non-Drywall" (Class 2).
        Asserts proposed_class != "Drywall" (Class 1).

# Test Class 5: End-to-End PDF Annotation & CLI Invocations
class TestEndToEndPDFAnnotation:
    - test_pdf_annotation_reopen_visual_check():
        Generates annotated PDF for held-out Sheet A-104 or synthetic test plan.
        Re-opens with PyMuPDF; asserts page count preserved and overlay present.
    - test_cli_pipeline_execution():
        Executes `python -m drywall_detection.pipeline.infer --input <test.pdf> --output <out.pdf> --dpi 72`.
        Asserts exit code == 0, stdout parses as valid JSON with keys:
        ['input_path', 'output_path', 'status', 'device', 'type', 'elapsed_sec'].
```

---

### 4.2 Detailed Specification: `drywall_detection/tests/test_interface.py`

```python
"""
drywall_detection/tests/test_interface.py
Test Architecture Specification for Streamlit Local Testing Interface
"""

# Test Class 1: Syntax & CLI Smoke
class TestStreamlitSyntaxAndSmoke:
    - test_app_syntax_and_importability():
        Parses `drywall_detection/app.py` via `ast.parse`.
        Asserts zero syntax errors.
    - test_streamlit_cli_smoke():
        Executes `streamlit run drywall_detection/app.py --help` via subprocess.
        Asserts exit code == 0.

# Test Class 2: Headless AppTest Session
class TestStreamlitAppTestMockSession:
    - test_apptest_initial_render():
        Initializes `AppTest.from_file("drywall_detection/app.py", default_timeout=30).run()`.
        Asserts len(at.exception) == 0.
        Asserts sidebar controls exist (DPI slider, alpha slider, overlap slider).
    - test_apptest_parameter_reconfiguration():
        Sets `at.select_slider[0].set_value(150).run()`.
        Sets `at.slider[0].set_value(0.60).run()`.
        Asserts len(at.exception) == 0; parameters persist.
    - test_apptest_sample_drawing_selection():
        Selects pre-loaded sample from `at.selectbox[0]`:
        "Held-Out Test Set: MTA 99th St Set (Sheet A-104 / Page 18)".
        Runs `at.run()`; asserts no unhandled crash.

# Test Class 3: Edge Cases & Memory Safeguards
class TestEdgeCasesAndMemoryGuard:
    - test_empty_and_corrupt_pdf_upload():
        Uploads 0-byte file and malformed string `b"INVALID_PDF_STREAM"`.
        Asserts app displays clean user-facing error message without traceback crash.
    - test_in_process_memory_reclamation():
        Runs inference across multi-page test PDF; asserts gc.collect() reclaims
        buffers and memory does not monotonically expand beyond host headroom.
```

---

## 5. Verification Method

To independently verify the findings and validate the forthcoming test suites:

1. **Verify Held-Out Drawing Inventory & Centerline Counts**:
   ```bash
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf'); print('Page 4 line annots:', len([a for a in doc[4].annots() if a.type[1]=='Line']))"
   # Output: Page 4 line annots: 69
   ```

2. **Verify DPI Rasterization Latency and Buffer Size**:
   ```bash
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); pix=doc[17].get_pixmap(dpi=150); print('150 DPI dimensions:', pix.width, pix.height, 'Buffer MB:', pix.size / 1048576)"
   # Output: 150 DPI dimensions: 5400 3600 Buffer MB: 55.62
   ```

3. **Verify Headless AppTest Session**:
   ```bash
   python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('drywall_detection/app.py', default_timeout=30); at.run(); assert len(at.exception) == 0; print('AppTest passed with 0 exceptions!')"
   ```

4. **Execute Full Test Suite (Post-Implementation)**:
   ```bash
   pytest drywall_detection/tests/test_pipeline.py drywall_detection/tests/test_interface.py -v
   ```

5. **Invalidation Conditions**:
   - Master PDF Sheet A-104 having any other count than 69 verified drywall partitions.
   - Tag 1A mapped to Class 1 (Drywall).
   - Inability to roundtrip PDF dimensions within 0.001 pt.
   - Host memory consumption exceeding 550MB available RAM at 150 DPI.
