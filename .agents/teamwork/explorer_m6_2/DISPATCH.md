## 2026-11-09T17:55:33Z
You are `explorer_m6_2`, an expert software architect and CLI interface designer for Milestone M6 (Final Validation, Delivery & Limitations Report) of the `drywall_detection/` module.

## MANDATORY INPUT FILES TO READ:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Read FIRST!)
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py`
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\router.py`
5. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\fusion.py`
6. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\pipeline\annotate.py`
7. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\classification\classifier.py`
8. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\vector\extractor.py`
9. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\vector\schedule_parser.py`
10. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\audit\dataset_auditor.py`

## YOUR MISSION:
Investigate and design the Unified Production CLI & End-to-End Pipeline architecture for Milestone M6:
1. **CLI Requirements Analysis**:
   - The user requested a self-contained, isolated module in `drywall_detection/`.
   - To make the entire module easily usable and verifiable as a production package, design a unified top-level CLI interface (`drywall_detection/cli.py` and entrypoint `drywall_detection/__main__.py`, executable via `python -m drywall_detection <command> [options]`).
   - Define exact subcommands and arguments:
     - `audit-datasets`: Run the dataset auditor across all 6 candidate datasets and output audit report.
     - `extract-vector`: Extract vector paths, walls, texts, and partition tags from a PDF (`--pdf`, `--pages`, `--output-dir`, `--format [json|geojson]`).
     - `parse-schedule`: Parse partition schedule sheets A-900 / A-901 into tabular CSV (`--pdf`, `--output-csv`, `--enforce-review-lock`).
     - `classify`: Classify walls using approved partition schedule mapping (`--pdf`, `--schedule-csv`, `--output-dir`, `--export-annotated-pdf`, `--export-raster-overlays`).
     - `infer-segmentation`: Run deep learning segmentation on floor plan image or PDF (`--input`, `--checkpoint`, `--output-dir`, `--tile-size`, `--stride`, `--device`).
     - `run-pipeline`: Complete end-to-end vector-first pipeline with automatic raster/ML fallback routing (`--pdf`, `--output-dir`, `--checkpoint`, `--schedule-csv`, `--dpi`).
     - `version` / `info`: Print version, hardware specs, installed dependencies, and checkpoint status.
2. **End-to-End Pipeline Flow Analysis**:
   - Trace the exact data flow for `run-pipeline`:
     Input PDF -> Page loop -> `ModalityRouter.route_page()`:
       - If `VECTOR_FIRST`: `VectorExtractor` extracts linework + tags -> `DrywallClassifier` applies approved schedule mapping (with 4-layer Detail 1A CMU veto) -> `WallAnnotator` generates native vector PDF overlays with zero rasterization + high-res PNG crops.
       - If `RASTER_ML`: Renders page via PyMuPDF -> `infer.py` executes SegFormer-B0 sliding-window segmentation -> `HybridFusionPipeline` vectorizes masks and generates class overlays.
       - If `HYBRID`: Fuses vector linework with ML probability heatmaps, where schedule ground truth strictly dominates ML predictions.
     Produces final GeoJSON feature collection, summary statistics table, and annotated drawing files.
3. **Packaging, Exit Codes & Robustness**:
   - Define standard UNIX/POSIX exit codes:
     - `0`: Success
     - `1`: Unhandled error / fatal failure
     - `2`: Review required (`REVIEW_REQUIRED.lock` active)
     - `3`: Detail 1A CMU safety invariant violation
   - Ensure clean `--help` documentation for all commands and arguments.
   - Design test specifications for `drywall_detection/tests/test_cli.py` covering all CLI subcommands, argument validation, error reporting, and end-to-end execution.

## CONSTRAINTS:
- READ-ONLY investigation: Do NOT modify source code or create source files.
- Deliver your findings in a comprehensive handoff report at:
  `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m6_2\handoff.md`
- Maintain `progress.md` and `BRIEFING.md` in your state folder (`.agents/teamwork/explorer_m6_2/`).
- Send a completion message via `send_message` to parent (`3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`) when done.
