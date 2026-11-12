# Milestone M4 Exploration Handoff Report
**Subagent**: `m4_explorer_1` (PDF Rendering & Annotation Pipeline Explorer)  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Target Modules**: `drywall_detection/pipeline/annotate.py` and `drywall_detection/pipeline/infer.py`  
**Date**: 2026-11-09  

---

## 1. Observation

### 1.1 Existing Implementations & Codebase Audit
1. **Pipeline Directory Status**:
   - Command: `dir "drywall_detection\pipeline"`
   - Result: `Cannot find path '...\drywall_detection\pipeline' because it does not exist.` (Exit code 1).
   - Finding: The pipeline package has not yet been implemented. All pipeline logic was temporarily placed in `drywall_detection/checkpoints/best_model/infer.py` and `drywall_detection/app.py`.

2. **Existing PDF Generation Deficiency in `app.py` and `infer.py`**:
   - File: `drywall_detection/app.py` lines 78-93 and `drywall_detection/checkpoints/best_model/infer.py` lines 326-337:
     ```python
     def create_annotated_pdf(annotated_images: List[Image.Image], dpi: int = 150) -> bytes:
         ...
         annotated_images[0].save(
             buf,
             format="PDF",
             resolution=dpi,
             save_all=True,
             append_images=annotated_images[1:],
         )
         return buf.getvalue()
     ```
   - Direct Observation: Both existing scripts rasterize the entire PDF page into an RGB image, blend the mask into the image pixels, and re-encode the raster image as a new PDF via Pillow (`Image.save(..., "PDF")`).
   - Deficiency: This completely destroys the original vector linework, text layer, CAD paths, and bookmarks. When zoomed into in a PDF viewer, line geometry appears blurry/pixelated at 150 DPI rather than maintaining infinite vector crispness. Furthermore, file size balloons to ~2.0 MB per page (~142 MB for the 71-page MTA contract set).

3. **Master PDF Geometry & Multi-Quadrant Rotation**:
   - Inspected test documents in workspace:
     * `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf` (MTA 99th Street 71-page contract set):
       - `page.mediabox`: `Rect(0.0, 0.0, 1728.0, 2592.0)` (unrotated: width=1728 pt, height=2592 pt)
       - `page.rotation`: `90` (clockwise)
       - `page.rect`: `Rect(0.0, 0.0, 2592.0, 1728.0)` (visual rotated viewport)
     * `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf` (Held-Out Test Set, 54 pages):
       - `page.mediabox`: `Rect(0.0, 0.0, 1728.0, 2592.0)`
       - `page.rotation`: `270` (clockwise / 90° counter-clockwise)
       - `page.rect`: `Rect(0.0, 0.0, 2592.0, 1728.0)`
     * `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (Verified Reference, 27 pages).

4. **PyMuPDF Rendering & Coordinate Space Invariants**:
   - When rendering via `page.get_pixmap(dpi=150)`:
     * Base resolution: 72 DPI. Zoom factor: $s = 150 / 72 = 2.083333$.
     * Effective visual dimensions: $2592 \times s = 5400$ px width, $1728 \times s = 3600$ px height.
     * Pixmap dimensions: exactly `(5400, 3600)`.
   - Insertion coordinate mechanics:
     * The PDF content stream geometry is defined in native unrotated `page.cropbox` space `[0, 0, 1728, 2592]`.
     * `page.insert_image(page.cropbox, pixmap=..., rotate=page.rotation, overlay=True)` instructs PyMuPDF's MuPDF engine to place the image into the page's unrotated bounding box while transforming the image pixels by `page.rotation`.
     * Empirical validation: Evaluated across all 4 quadrants ($0^\circ, 90^\circ, 180^\circ, 270^\circ$). Top-left and bottom-right corner markers aligned with 0 error across all rotations.

5. **Empirical Benchmark on Sheet A-104 (Page 18, 5400x3600 px, 19.44M Pixels)**:
   - Tool execution on SegFormer-B0 champion model:
     * Page rendering (150 DPI): 0.76s
     * Sliding-window tiling inference (512x512, 20% overlap, 126 tiles, CPU): 190.01s
     * Mask shape: `(3600, 5400)` (19,440,000 pixels)
     * Class pixel distribution:
       - Background (0): 12,417,519 px (63.88%)
       - Drywall (1): 5,054,715 px (26.00%)
       - Non-Drywall (2): 429,426 px (2.21%)
       - Uncertain (3): 1,538,340 px (7.91%)
   - LUT mapping to RGBA array: 1.05s (vectorized numpy 256x4 lookup)
   - PyMuPDF direct `fitz.Pixmap` construction: 0.28s
   - PyMuPDF `insert_image` execution: 0.67s
   - Final PDF save (deflated): 1.15s
   - Output PDF file size: 463.5 KB (0.45 MB) vs 2.00 MB (naive full-raster PDF) — **78% file size reduction**!

6. **Small-Canvas Bounds Guard Verification**:
   - Standalone test on non-standard and small dimensions:
     * Tiny canvas `(150, 200)`: PASSED without broadcast errors
     * Extreme ribbon `(300, 2000)`: PASSED without broadcast errors
     * Exact tile `(512, 512)`: PASSED

---

## 2. Logic Chain

1. **Premise 1 (R4 Requirement)**: The system must produce a downloadable annotated PDF that accepts both vector-based and scanned PDFs, preserves original physical page dimensions, original drawing linework quality (does NOT degrade vector resolution), and original page rotation.
2. **Premise 2 (Deficiency of Raster Approach)**: Re-encoding rendered page bitmaps into a new PDF via Pillow or OpenCV converts all vector drawing commands to raster pixels, permanently losing vector resolution, selectable text, and drawing sharpness, while inflating file size to ~2.0 MB/page.
3. **Premise 3 (PyMuPDF Native Overlay Mechanism)**: In PyMuPDF, `page.insert_image(rect, pixmap=..., rotate=..., overlay=True)` injects an image XObject into the existing PDF page tree. When `overlay=True`, the image is composited on top of existing vector graphics. Because the underlying vector streams are not rewritten or converted, 100% of the vector drawing linework, fonts, layers, and text are preserved intact.
4. **Premise 4 (Coordinate & Rotation Alignment)**:
   - PyMuPDF's `page.get_pixmap(dpi=150)` renders the visual orientation (e.g. $5400 \times 3600$ px for a 90° rotated drawing).
   - In the PDF file structure, the page geometry is oriented according to `page.cropbox` (unrotated, e.g. $1728 \times 2592$ pt).
   - By constructing an RGBA pixmap of the segmentation mask and passing `rect=page.cropbox` and `rotate=page.rotation` to `insert_image`, PyMuPDF computes the exact affine transformation mapping the visual pixel grid to the unrotated page geometry.
   - Empirical tests across $0^\circ, 90^\circ, 180^\circ, 270^\circ$ confirm that top-left $(0,0)$ and bottom-right $(W,H)$ match exactly with 0 pixel displacement.
5. **Premise 5 (Tradeoff Analysis: Overlay vs Vector Polygons)**:
   - *Transparent RGBA Pixmap Overlay*:
     * Pros: 100% fidelity to dense model logits/probabilities, O(1) rendering complexity, handles arbitrary topology/holes effortlessly, fast insertion (< 1s per sheet), small deflated PDF size (0.45 MB/page).
     * Cons: Mask edges have pixel resolution of the rendering DPI (150 DPI), though underlying CAD drawing remains vector sharp.
   - *Vector Polygon Extraction (`cv2.findContours` + `draw_polyline`)*:
     * Pros: Infinitely scalable mask boundaries.
     * Cons: High complexity on complex floor plans (hundreds of polygons), contour staircase artifacts along diagonal walls, difficulty rendering interior topological holes without winding defects, risk of PDF rendering lag in desktop viewers.
   - *Synthesis*: Direct transparent RGBA pixmap overlay must be the **primary default mechanism**, with vector polygon rendering supported as an **optional alternative** via `--annotation-method polygon`.
6. **Premise 6 (Color Taxonomy)**:
   - Standard palette:
     * Background (0): Transparent (`RGBA(0, 0, 0, 0)`)
     * Drywall (1): Green (`#00FF00` or `#00C853`, `RGBA(0, 255, 0, alpha=0.45)`)
     * Non-Drywall (2): Red (`#FF0000` or `#D50000`, `RGBA(255, 0, 0, alpha=0.45)`)
     * Uncertain (3): Yellow (`#FFFF00` or `#FFD600`, `RGBA(255, 255, 0, alpha=0.45)`)
   - LUT-based mapping achieves $O(1)$ pixel conversion in ~1.0s for 19.44 million pixels.
7. **Conclusion**: Modularize the pipeline into `drywall_detection/pipeline/annotate.py` (annotation primitives, LUT mapping, PDF overlay/polygon inserters, metrics) and `drywall_detection/pipeline/infer.py` (CLI, batch handling, sliding-window orchestration, structured JSON output).

---

## 3. Caveats

1. **CPU Inference Latency**: Full-resolution sliding-window inference on a $5400 \times 3600$ plan (126 tiles of 512x512) takes ~190 seconds on a standard 4-thread CPU. On GPU / CUDA, this drops to ~2–4 seconds. The pipeline supports `--device cuda` / `--device cpu` and accepts single-page targeting (`--page 17`) to enable fast interactive testing.
2. **PyMuPDF In-Place Document Modification**: PyMuPDF's `doc.save(..., deflate=True, garbage=4)` produces optimal file sizes, but cannot overwrite the input file if opened in-place. The pipeline automatically writes to a distinct output file (e.g. `<stem>_annotated.pdf`), avoiding write-lock conflicts.
3. **App.py Independence**: `drywall_detection/app.py` currently exists and uses the older raster PDF export. The implementer should update `app.py` to import `PDFAnnotator` from `drywall_detection.pipeline.annotate` to benefit from vector preservation and reduced export sizes.

---

## 4. Conclusion & Architectural Design

### 4.1 Component Architecture

```
drywall_detection/pipeline/
├── __init__.py           # Exports DrywallInferencePipeline, PDFAnnotator, build_cli_parser
├── annotate.py           # Vector-preserving PDF & image annotation engine
└── infer.py              # CLI & batch orchestration pipeline emitting structured JSON
```

### 4.2 Module Specifications

#### 1. `drywall_detection/pipeline/annotate.py`
- **Class `PDFAnnotator`**:
  * `annotate_pdf_page_overlay(page: fitz.Page, mask_uint8: np.ndarray) -> None`: Constructs `fitz.Pixmap` from LUT RGBA array and inserts into `page.cropbox` with `rotate=page.rotation`.
  * `annotate_pdf_page_polygons(page: fitz.Page, mask_uint8: np.ndarray, dpi: int = 150) -> int`: Extracts contours via OpenCV, converts coordinates via `pixel_to_pdf`, and renders translucent vector polylines via `shape.draw_polyline(..., closePath=True)`.
  * `annotate_pdf_document(...) -> Dict[str, Any]`: Multi-page coordinator.
- **Helper Functions**:
  * `build_rgba_lut(alpha, palette)`: Vectorized 256x4 lookup table.
  * `mask_to_rgba_overlay(mask, alpha, palette)`: Converts mask to RGBA array.
  * `render_blended_image(image, mask, alpha, palette)`: Blends mask onto RGB image for PNG/display export.
  * `compute_mask_metrics(...)`: Generates per-page pixel counts, class percentages, drywall percentage, and timing.

#### 2. `drywall_detection/pipeline/infer.py`
- **Class `DrywallInferencePipeline`**:
  * Encapsulates `StandaloneInferencer` and `PDFAnnotator`.
  * Methods: `process_pdf(...)`, `process_image(...)`, `process(...)` (handles single file or directories).
  * Sliding-window parameters: 512x512 tile size, 20% overlap (stride 410), 2D Hann apodization stitching.
- **CLI Interface**:
  * `python -m drywall_detection.pipeline.infer --input <path> --output <path> --dpi 150 --checkpoint <ckpt>`
  * Arguments: `--input`, `--output`, `--checkpoint`, `--dpi`, `--page`, `--overlap`, `--tile-size`, `--alpha`, `--annotation-method`, `--palette`, `--mode`, `--device`, `--json-output`, `--quiet`.
  * Structured JSON schema emitted to stdout and/or file.

### 4.3 Reference Implementations Available in State Folder
The complete, syntactically verified reference code has been generated and validated in the explorer state folder:
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_annotate.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_infer.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_init.py`

---

## 5. Verification Method

The implementer can independently verify the implementation with the following concrete tests:

### 5.1 Unit Tests (`drywall_detection/tests/test_pipeline.py`)
Run:
```powershell
python -m pytest drywall_detection/tests/test_pipeline.py -v
```

Verification assertions to include:
1. **Rotation Alignment Invariant**:
   - Create synthetic PDF pages with rotations 0°, 90°, 180°, 270°.
   - Insert an overlay with known corner markers.
   - Assert rendered pixmap has corner markers at exact expected coordinates.
2. **Vector Linework Preservation Invariant**:
   - Open a vector PDF (e.g. MTA contract set or synthetic PDF with vector paths).
   - Count vector drawings: `len(page.get_drawings())`.
   - Apply `annotator.annotate_pdf_page_overlay(page, mask)`.
   - Save and reload: assert `len(reloaded_page.get_drawings()) == len(page.get_drawings())`.
3. **Small-Canvas & Ribbon Bounds Guard**:
   - Test images with sizes (150, 200), (300, 2000), (512, 512).
   - Assert prediction output shapes match input shapes exactly without exceptions.
4. **4-Class Taxonomy & Metrics Verification**:
   - Create a mask with known pixel counts for classes 0, 1, 2, 3.
   - Assert `compute_mask_metrics` returns exact counts and percentages.
5. **CLI End-to-End Execution**:
   - Run CLI command on a test image/PDF:
     ```powershell
     python -m drywall_detection.pipeline.infer --input "drywall_detection/checkpoints/best_model/sample_overlays/sample_crop_01.png" --output "test_annotated.png" --quiet
     ```
   - Assert exit code 0 and valid JSON output with keys `status`, `pages`, `aggregate_statistics`.

### 5.2 Invalidation Conditions
The implementation shall be deemed INVALID if:
- Annotated PDF export converts original vector paths into a raster image (degrading vector resolution).
- Overlay mask does not align with drawing linework on 90° or 270° rotated architectural plans.
- Canvas smaller than 512x512 raises broadcasting or shape mismatch errors.
- CLI crashes on valid PDF or image input, or fails to emit structured JSON output.
