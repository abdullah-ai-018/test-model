## 2026-11-09T11:19:52Z
You are m4_worker_1_rep (Milestone M4 Implementation Worker) for Milestone M4: Local PDF Testing Interface & Inference Pipeline.

## Workspace & Context
- Working Directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- Your State Folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_worker_1_rep
- Parent Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Initial Reading
Before writing any code, you MUST read:
1. ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Synthesis analysis at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\orchestrator\analysis.md
4. Explorer reports and reference implementations:
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\handoff.md
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_annotate.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_infer.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_1\proposed_init.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_2_rep\handoff.md
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_2_rep\proposed_app.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_3_rep\handoff.md

## Exclusive Write Ownership
You exclusively own and may create/modify the following files under `drywall_detection/`:
1. `drywall_detection/pipeline/__init__.py`
2. `drywall_detection/pipeline/annotate.py`
3. `drywall_detection/pipeline/infer.py`
4. `drywall_detection/app/app.py` (and root `drywall_detection/app.py` to keep them synchronized)
5. `drywall_detection/tests/test_pipeline.py`
6. `drywall_detection/tests/test_interface.py`
7. `drywall_detection/reports/M4_interface_report.md`
DO NOT modify files outside your write ownership without explicit orchestrator permission.

## Implementation Tasks

### Task 1: Pipeline Module (`drywall_detection/pipeline/`)
1. Create directory `drywall_detection/pipeline/` and `__init__.py` (incorporate `m4_explorer_1/proposed_init.py`).
2. Implement `drywall_detection/pipeline/annotate.py` (incorporate `m4_explorer_1/proposed_annotate.py`):
   - Fast vectorized 256x4 LUT mapping (`mask_to_rgba_overlay`).
   - `PDFAnnotator` class:
     * `annotate_pdf_page_overlay`: PyMuPDF `page.insert_image(page.cropbox, pixmap=..., rotate=page.rotation, overlay=True)` preserving 100% of underlying CAD vector linework, dimensions, and orientation.
     * `annotate_pdf_page_polygons`: vector polygon extraction fallback using PyMuPDF Shape and `pixel_to_pdf`.
     * `annotate_pdf_document`: multi-page PDF processing with deflated save (`garbage=4`).
     * `render_blended_image`: composite image blending for PNG/UI export.
     * `compute_mask_metrics`: rigorous per-page pixel counts, class percentages, drywall %, and timing.
3. Implement `drywall_detection/pipeline/infer.py` (incorporate `m4_explorer_1/proposed_infer.py`):
   - `DrywallInferencePipeline` wrapping `StandaloneInferencer` and `PDFAnnotator`.
   - Sliding-window tiling (512x512, 20% overlap, stride 410, 2D Hann window apodization stitching).
   - Small-canvas bounds guard (handling canvases smaller than 512x512 and extreme aspect ratios).
   - CLI interface supporting `--input`, `--output`, `--dpi 150`, `--checkpoint`, `--page`, `--overlap`, `--alpha`, `--annotation-method`, `--json-output`. Emits structured JSON summary.

### Task 2: Streamlit Interactive Interface (`drywall_detection/app/app.py` and root `drywall_detection/app.py`)
1. Deploy `drywall_detection/app/app.py` and update root `drywall_detection/app.py` incorporating `m4_explorer_2_rep/proposed_app.py`:
   - Model caching via `@st.cache_resource`.
   - Fast session state decoupling: raw prediction masks stored in `st.session_state["cache"]`. Opacity slider changes re-blend in NumPy in <50ms without re-running neural network inference.
   - Multi-page navigation: previous/next buttons, dropdown selector, sheet info banner.
   - On-demand sheet inference (`⚡ Run Inference on Active Sheet`) and batch mode (`🚀 Batch Run All Sheets`).
   - 3 Visual inspection tabs: "Annotated Overlay", "Side-by-Side Comparison", "Raw Prediction Mask".
   - 4-Class Color Legend: Green Drywall (`#00C853`), Red Non-Drywall (`#D50000`), Yellow Uncertain (`#FFD600`), Background Transparent.
   - Takeoff Statistics Dashboard with zero-division protection.
   - One-click sample selectors for MTA Sheet A-101, A-102, held-out A-104 (69 verified walls), sample tile 01, and Spark Permit Set.
   - Downloads: Annotated PDF (vector-preserving), PNG composite, Takeoff CSV, Summary JSON.
   - Prominent 95% CDs progress set disclosure notice banner.

### Task 3: Comprehensive Test Suites
1. Implement `drywall_detection/tests/test_pipeline.py` per `m4_explorer_3_rep` specifications:
   - PDF loading and dimension metadata extraction.
   - Coordinate & rotation preservation roundtrip ($|W_{recovered} - W_{pt}| < 10^{-3}$, 0°, 90°, 180°, 270°).
   - Small-canvas bounds and extreme aspect ratio ribbons ((64, 64), (256, 256), (5000, 500), (500, 5000)).
   - 4-Class color mapping & Detail 1A CMU safety veto.
   - End-to-end PDF annotation & CLI JSON execution.
2. Implement `drywall_detection/tests/test_interface.py` per `m4_explorer_3_rep` specifications:
   - Python syntax compilation & CLI smoke (`streamlit run ... --help`).
   - Headless `AppTest` session (`from streamlit.testing.v1 import AppTest`).
   - Takeoff arithmetic unit tests & zero-division safety.
   - Error handling for 0-byte and corrupt PDF uploads.

### Task 4: Verification Execution
Run all verification suites and document results:
1. `python -m pytest drywall_detection/tests/test_pipeline.py -v`
2. `python -m pytest drywall_detection/tests/test_interface.py -v`
3. Standalone CLI test: `python -m drywall_detection.pipeline.infer --input drywall_detection/data/processed/images/mock_plan_00.png --output test_pipeline_smoke.png` (clean up temporary overlay after verifying).
4. Streamlit AppTest verification command:
   `python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('drywall_detection/app/app.py', default_timeout=30); at.run(); assert len(at.exception) == 0; print('AppTest Passed!')"`
5. Regression test suite:
   `python -m pytest drywall_detection/tests/test_models.py drywall_detection/tests/test_m3_adversarial_loss_splits.py -v`
6. Author formal Milestone M4 report: `drywall_detection/reports/M4_interface_report.md`.
