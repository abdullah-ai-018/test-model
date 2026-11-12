## 2026-11-09T09:51:11Z
You are m4_explorer_3 (Held-Out Drawing Validation & Test Suite Explorer) for Milestone M4: Local PDF Testing Interface & Inference Pipeline.

## Workspace & Context
- Working Directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- Your State Folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_3
- Parent Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486

## Mandatory Initial Reading
Before performing any analysis, you MUST read:
1. ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. TEST_INFRA.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\TEST_INFRA.md
4. Existing test suites:
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_models.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_vector.py
   - c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_schedule.py

## Mission & Objectives
Investigate held-out architectural test drawings and design a comprehensive test suite for Milestone M4 (`drywall_detection/tests/test_interface.py` and `drywall_detection/tests/test_pipeline.py`):
1. Held-Out Architectural Drawing Inventory:
   - Search the workspace for available held-out architectural PDF drawings not used in training:
     * MTA 99th Street Sheet A-104 (Page 4 of master PDF, 69 verified drywall partitions, strictly reserved for held-out testing).
     * Any other sheets or mock permit sets (e.g. Spark Lake Grove or synthetic multi-page test PDFs).
   - Characterize physical dimensions, vector vs scanned properties, rotation, resolution, and memory footprint when rasterized at 72, 150, and 300 DPI.
2. Pipeline & Interface Test Architecture:
   - Design test cases for `drywall_detection/tests/test_pipeline.py`:
     * Loading single-page and multi-page PDFs.
     * Coordinate preservation: MediaBox / CropBox dimensions preserved bit-for-bit in output PDF.
     * Page rotation preservation: 90° CW, 180°, 270°, and 0° unrotated pages.
     * Small-canvas guard: canvases smaller than 512x512 handled without broadcast mismatch.
     * Color mapping correctness: Drywall (Green `#00FF00`), Non-Drywall (Red `#FF0000`), Uncertain (Yellow `#FFFF00`), Background (Transparent).
     * Detail 1A CMU safety veto: Non-Drywall tags correctly mapped to Class 2.
     * End-to-end PDF annotation: re-opening generated PDF with PyMuPDF and asserting page count == input page count, dimensions match, overlay visual presence verified.
     * CLI execution test: invoking `python -m drywall_detection.pipeline.infer --input ... --output ...` via `subprocess.run` and asserting exit code 0 and valid JSON output.
3. Streamlit Interface Test Architecture:
   - Design test cases for `drywall_detection/tests/test_interface.py`:
     * Module importability and syntax validation.
     * CLI invocation smoke test (`streamlit run drywall_detection/app/app.py --help` or `--server.headless true`).
     * Mock session execution (using `streamlit.testing.v1.AppTest` or mock request runner) verifying file upload, configuration change, and page navigation without unhandled exceptions.
4. Edge Case & Stress Testing:
   - Empty/corrupted PDFs (raises clean `ValueError` or user-friendly error, no crash).
   - High-aspect-ratio drawings (e.g. 10:1 banner drawings).
   - High-resolution memory footprint guards (in-process garbage collection, avoiding RAM spikes above host 550MB available headroom).

## Constraints & Requirements
- Read-only exploration agent: DO NOT write or modify source code files directly.
- Document all findings, test case specifications, assertion formulas, and drawing paths in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m4_explorer_3\handoff.md`.
- Follow the 5-component handoff protocol: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
- Send a completion message to parent when done via send_message.
