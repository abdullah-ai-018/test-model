# Dispatch Assignment: reviewer_m5_2

## Role
M5 Pipeline & Visualization Reviewer (`teamwork_reviewer`)

## Working Directory
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model`

## State Folder
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\reviewer_m5_2\`

## Mandatory Inputs (MUST READ FIRST)
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m5_2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\coords.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\router.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\fusion.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\annotate.py`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M5_classification_report.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\sample_overlays\`

## Scope of Review
1. Review `coords.py` (`AffineTransformManager`):
   - Verify coordinate bijection under 90° CW rotation from portrait MediaBox [1728 x 2592] pt to visual landscape [5400 x 3600] px at 150 DPI.
   - Verify forward and inverse transforms for points, bboxes, coordinate arrays, and Shapely geometries with $< 10^{-12}$ pt roundtrip drift.
2. Review `pipeline/router.py` (`ModalityRouter`):
   - Verify page profiling logic into `VECTOR_FIRST`, `RASTER_ML`, or `HYBRID`.
3. Review `pipeline/fusion.py` (`HybridFusionPipeline`):
   - Verify schedule authority invariant: vector schedule tags dominate ML predictions.
   - Verify Detail 1A CMU veto is preserved during fusion.
   - Verify ML confidence boosting when vector and ML agree; advisory metadata for unassigned walls.
4. Review `pipeline/annotate.py` (`WallAnnotator`):
   - Verify high-resolution 150 DPI raster PNG overlay generation with legend card and linear feet takeoff.
   - Verify vector PDF overlay generation via PyMuPDF Shape primitives (`page.new_shape()`, `fill_opacity=0.40`), preserving 100% searchable text, fonts, and native CAD linework without rasterization.
5. Review `drywall_detection/reports/M5_classification_report.md`:
   - Verify mandatory 95% CDs progress set notice is prominently included.
   - Verify all 24 details, 10 human review benchmark regions (R01-R10), and 5 verification metrics are documented accurately.
6. Execute the test suite:
   - Run `pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_schedule.py drywall_detection/tests/test_classification.py -v`
7. Deliver a formal Review Report and `handoff.md` in your state folder with an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.
