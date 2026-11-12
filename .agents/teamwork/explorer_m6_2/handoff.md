# Milestone M6 Architectural Design Report: Unified Production CLI & End-to-End Pipeline

**Author**: `explorer_m6_2`  
**Milestone**: M6 — Final Validation, Delivery & Limitations Report  
**Scope**: Architecture & Design of `drywall_detection/cli.py`, `drywall_detection/__main__.py`, Exit Code Protocols, and `drywall_detection/tests/test_cli.py`  
**Date**: 2026-11-10  

---

## 1. Observation

### 1.1 Existing Module Architecture & Interfaces
Direct inspection of the `drywall_detection/` codebase revealed the following existing implementations and interfaces:

1. **Top-Level Package State** (`drywall_detection/__init__.py:1-8`):
   - Package version is defined as `__version__ = "0.1.0"`.
   - No top-level `cli.py` or `__main__.py` currently exists. Running `python -m drywall_detection` currently fails with `No module named drywall_detection.__main__`.

2. **Central Configuration & Core Contracts** (`drywall_detection/config.py:1-252`):
   - Directory anchors: `PACKAGE_ROOT`, `WORKSPACE_ROOT`, `DATA_DIR`, `REPORTS_DIR`, `CHECKPOINTS_DIR`, `BEST_MODEL_DIR`.
   - Master PDF constants: `MASTER_PDF_TOTAL_PAGES = 71`, `MASTER_PDF_MEDIABOX_WIDTH_PT = 1728.0`, `MASTER_PDF_MEDIABOX_HEIGHT_PT = 2592.0`, `MASTER_PDF_ROTATION_DEG = 90`.
   - Sheet Index Map: Cover (0), G-001 (1), G-002 (2), A-100 (13), A-101 (14), A-102 (15), A-103 (16), A-104 (17), A-105 (18), A-900 (62), A-901 (63).
   - 4-Class material taxonomy:
     - `CLASS_BACKGROUND = 0` ("Background", `#FFFFFF`)
     - `CLASS_DRYWALL = 1` ("Drywall", Green `#00C853` / RGB `(0, 200, 83)`)
     - `CLASS_NON_DRYWALL = 2` ("Non-Drywall", Red `#D50000` / RGB `(213, 0, 0)`)
     - `CLASS_UNCERTAIN = 3` ("Uncertain", Yellow `#FFD600` / RGB `(255, 214, 0)`)
   - Human review lock files: `SCHEDULE_CSV_PATH` (`partition_schedule_mapping.csv`), `APPROVED_SCHEDULE_CSV_PATH` (`partition_schedule_mapping.approved.csv`), `REVIEW_LOCKFILE_PATH` (`REVIEW_REQUIRED.lock`), and `EXIT_CODE_AWAITING_REVIEW = 2`.
   - Detail 1A safety rule: `TAG_1A_OVERRIDE_CLASS = CLASS_NON_DRYWALL`, `TAG_1A_OVERRIDE_REASON = "Detail 1A on Sheet A-900 is explicitly 6\" FIRE RATED CMU (masonry / Non-Drywall)."`.

3. **Modality Router** (`drywall_detection/pipeline/router.py:18-101`):
   - `PipelineModality` Enum: `VECTOR_FIRST`, `RASTER_ML`, `HYBRID`.
   - `ModalityRouter.evaluate_page(page: fitz.Page) -> PageModalityDecision`:
     - If `path_count < 50` and (`image_coverage >= 0.70` or `word_count == 0`) -> `RASTER_ML` (confidence 0.98).
     - If `path_count >= 100` and `image_coverage < 0.50` and `word_count >= 20` -> `VECTOR_FIRST` (confidence 0.95).
     - Otherwise -> `HYBRID` (confidence 0.85).

4. **Vector Extraction Engine** (`drywall_detection/vector/extractor.py:1-667`):
   - `VectorExtractor`: extracts solid heavy strokes ($w \ge 0.84$ pt), forms parallel line pairs across architectural thickness ($1.5 \le \text{thick\_pt} \le 10.5$ pt, corresponding to 2" to 14" at 1/8"=1'-0" scale), unions them into clean Shapely polygons.
   - `VectorExtractor.detect_vector_content(page) -> VectorPageProfile`.
   - `VectorExtractor.extract_wall_candidates(page) -> List[ExtractedWallCandidate]`.
   - `VectorExtractor.find_partition_tags(page) -> List[Tuple[TextElement, fitz.Rect]]`.

5. **Schedule Parser & Review Lock Sentinel** (`drywall_detection/vector/schedule_parser.py:1-765`):
   - Contains authoritative 24-detail catalog (`AUTHORITATIVE_DETAILS`) for Sheets A-900 and A-901.
   - `PartitionScheduleParser.discover_tags(page, page_idx, sheet_name) -> List[PartitionTagInstance]`: detects 11.2 x 11.3 pt tag boxes with attached 0.48 pt leader lines.
   - `PartitionScheduleParser.export_and_enforce_review_lock(csv_path, approved_csv_path, lock_path, interactive_mode) -> bool`:
     - Checks if approved CSV exists, is non-empty, contains required columns `tag` and `proposed_class`, has all 24 details, and verifies Detail 1A is Non-Drywall.
     - If approved CSV is missing, generates `REVIEW_REQUIRED.lock` and exits with code `2` (or returns False).
     - If Detail 1A is classified as Drywall in approved CSV, raises `ValueError` ("INTEGRITY VIOLATION").

6. **Drywall Classifier & 4-Layer Detail 1A CMU Veto** (`drywall_detection/classification/classifier.py:1-492`):
   - `IntegrityViolationError(ValueError)` and `ScheduleValidationError(ValueError)`.
   - 4-Layer Safety Veto:
     - **Layer 1 (Ingestion Gate)**: `_load_and_validate_schedule()` validates all 24 details and explicitly asserts `records["1A"]["proposed_class"] == "Non-Drywall"`. Any attempt to label 1A as Drywall raises `IntegrityViolationError`.
     - **Layer 2 (Runtime Assignment Invariant)**: In `classify_walls()`, if `clean_tag == "1A"`, wall is unconditionally assigned `classification="Non-Drywall"`, `color_hex="#D50000"`, `matched_tag="1A"`, bypassing any conflicting text or heuristics.
     - **Layer 3 (Post-Init & Mutator Guard)**: `ClassifiedWallPolygon.__post_init__` and `__setattr__` intercept any mutation attempting to set `classification="Drywall"` on tag "1A", throwing immediate `IntegrityViolationError`.
     - **Layer 4 (Fusion Veto)**: In `HybridFusionPipeline._fuse_vector_and_ml()`, walls with `matched_tag == "1A"` immediately bypass ML probability overrides.
   - Tier 3 Unassigned Fallback: Walls lacking conclusive tag evidence are classified as `Uncertain` (`#FFD600`, confidence 0.0) with zero material hallucination.
   - `DrywallClassifier.export_geojson(classified_walls, output_path)` produces RFC 7946 GeoJSON.

7. **High-Fidelity PDF & Raster Annotator** (`drywall_detection/pipeline/annotate.py:1-587`):
   - `WallAnnotator`:
     - `generate_annotated_vector_pdf()`: overlays translucent colored vector shapes via PyMuPDF `Shape` primitives, inserts rotated text tags and legend card. Zero rasterization, 100% preservation of CAD linework, fonts, and dimensions.
     - `render_raster_image()`: renders high-res RGB PIL Image with semi-transparent wall masks, outlines, and bottom-right architectural legend card.
     - `compute_mask_metrics()`: calculates pixel/area percentages.
   - `PDFAnnotator`: provides both pixmap overlay and vector polygon boundary drawing.

8. **Hybrid Fusion Pipeline** (`drywall_detection/pipeline/fusion.py:1-345`):
   - `HybridFusionPipeline.process_page()`:
     - Automatically routes page via `ModalityRouter`.
     - Executes `_run_vector_first()`, `_run_raster_ml()`, or `_run_hybrid_fusion()`.
     - Fuses vector and ML: ground truth schedule strictly dominates; ML cross-validates confidence; Uncertain walls receive non-binding advisory tags.
     - `compute_summary_statistics()` calculates total wall count, linear feet (`LF = pt / 9.0` at 1/8"=1'-0"), and square footage (`SF = pt^2 / 81.0`).

9. **Standalone ML Inferencer & Checkpoints** (`drywall_detection/checkpoints/best_model/infer.py` & `drywall_detection/pipeline/infer.py`):
   - Champion model: SegFormer-B0 trained with Compound Soft Dice + Focal Loss.
   - Weights: `best_model.pt` (44.8 MB), `config.json` (architecture SegFormer-B0, 4 classes, 512x512 tile size), `metrics.json` (mIoU 0.817, Wall IoU 0.697).
   - 512x512 sliding-window tiling with 2D Hann apodization stitching.

10. **Hardware Profiler** (`drywall_detection/utils/hardware.py:1-554`):
    - `HardwareProfile`: probes CPU, logical/physical cores, RAM, GPU/CUDA, VRAM, and primary disk space.

---

## 2. Logic Chain

### 2.1 Why a Top-Level Unified CLI is Required
- **User Requirement**: The user requested a self-contained, isolated module in `drywall_detection/` capable of detecting walls, classifying drywall, and presenting an intuitive interface.
- **Problem**: Currently, functionality is fragmented across multiple internal scripts:
  - `python -m drywall_detection.audit.dataset_auditor`
  - `python -m drywall_detection.vector.extractor`
  - `python -m drywall_detection.vector.schedule_parser`
  - `python -m drywall_detection.pipeline.infer`
  There is no single command entry point, and running `python -m drywall_detection` fails.
- **Solution**: Design `drywall_detection/cli.py` and `drywall_detection/__main__.py` offering a cohesive sub-command architecture:
  `python -m drywall_detection <subcommand> [options]`.

### 2.2 CLI Subcommand Design & Decomposition
To cover all lifecycle requirements of the package, the CLI must provide exactly 7 subcommands:

| Subcommand | Functionality | Primary Backing Class / Function |
|---|---|---|
| `audit-datasets` | Audit 6 candidate datasets & disk safety | `drywall_detection.audit.dataset_auditor.DatasetAuditor` |
| `extract-vector` | Extract CAD linework, walls, text & tags | `drywall_detection.vector.extractor.VectorExtractor` |
| `parse-schedule` | Parse A-900/A-901 sheets & enforce review lock | `drywall_detection.vector.schedule_parser.PartitionScheduleParser` |
| `classify` | Classify walls with approved schedule & CMU veto | `drywall_detection.classification.classifier.DrywallClassifier` |
| `infer-segmentation` | Run SegFormer-B0 sliding-window segmentation | `drywall_detection.pipeline.infer.DrywallInferencePipeline` |
| `run-pipeline` | Complete E2E pipeline with auto-routing | `drywall_detection.pipeline.fusion.HybridFusionPipeline` |
| `version` / `info` | Display package, hardware, & model status | `drywall_detection.utils.hardware.get_hardware_profile` |

### 2.3 End-to-End Data Flow for `run-pipeline`
The core production command is `run-pipeline`. The step-by-step logic chain from raw PDF to verified takeoff deliverables is:

```
                  ┌──────────────────────────────────────────────┐
                  │          Input Architectural PDF             │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │ Page Loop (0 .. N - 1) │
                            └────────────┬───────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │   ModalityRouter.evaluate_page  │
                        └───────┬──────────────┬──────────┘
                                │              │
            ┌───────────────────┘              └──────────────────┐
            ▼                                                     ▼
┌────────────────────────┐                              ┌───────────────────┐
│ Modality: VECTOR_FIRST │                              │ Modality: RASTER  │
└───────────┬────────────┘                              └─────────┬─────────┘
            │                                                     │
            ▼                                                     ▼
┌───────────────────────────────┐                       ┌───────────────────┐
│ VectorExtractor:              │                       │ Render Page at    │
│ - Heavy lines (w >= 0.84 pt)  │                       │ Configured DPI    │
│ - Parallel-pair matching      │                       └─────────┬─────────┘
│ - Shapely wall polygons       │                                 │
└───────────┬───────────────────┘                                 ▼
            │                                           ┌───────────────────┐
            ▼                                           │ SegFormer-B0      │
┌───────────────────────────────┐                       │ Sliding-Window    │
│ PartitionScheduleParser:      │                       │ (512x512 + Hann)  │
│ - Tag box detection (11.2 pt) │                       └─────────┬─────────┘
│ - Leader line raycasting      │                                 │
└───────────┬───────────────────┘                                 ▼
            │                                           ┌───────────────────┐
            ▼                                           │ Vectorize Mask    │
┌───────────────────────────────┐                       │ via OpenCV        │
│ DrywallClassifier:            │                       │ Contours to Polys │
│ - Approved schedule lookup    │                       └─────────┬─────────┘
│ - 4-Layer Detail 1A CMU Veto  │                                 │
│ - Tier 3 Unassigned Fallback  │                                 │
└───────────┬───────────────────┘                                 │
            │                                                     │
            ├─────────────────────────────────────────────────────┘
            ▼
┌────────────────────────────────────────────────────────┐
│ [If Modality == HYBRID]:                               │
│ - Fuse Vector + ML probability maps                    │
│ - Schedule Ground Truth strictly dominates ML          │
│ - 1A CMU Veto remains unconditional                    │
│ - ML agreement cross-validates Drywall confidence      │
│ - ML provides advisory tags on Uncertain walls         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Output Generation & Material Takeoffs:                 │
│ 1. WallAnnotator -> Annotated Vector PDF (zero raster) │
│ 2. WallAnnotator -> High-Res PNG previews with legend  │
│ 3. DrywallClassifier -> RFC 7946 GeoJSON collection    │
│ 4. Takeoff Table -> Wall Count, Linear Feet, Sq. Feet  │
└────────────────────────────────────────────────────────┘
```

### 2.4 POSIX Exit Code Protocol
A production CLI must communicate execution states reliably to automated build pipelines, orchestrators, and CI/CD environments. Standard exit codes are defined as:

1. **Exit Code `0` (Success)**:
   - Command completed successfully without error.
   - All requested artifacts written to disk.
2. **Exit Code `1` (Unhandled / Fatal Failure)**:
   - File not found (e.g. invalid `--pdf` path).
   - Malformed arguments or unrecognized flags.
   - Out of memory or PyTorch execution failure.
3. **Exit Code `2` (Review Required)**:
   - `drywall_detection/data/REVIEW_REQUIRED.lock` exists or is created.
   - Partition schedule has been parsed, but `partition_schedule_mapping.approved.csv` is missing or awaiting human sign-off.
   - Downstream classification cannot proceed without verified human approval.
4. **Exit Code `3` (Detail 1A CMU Safety Invariant Violation)**:
   - `IntegrityViolationError` caught at any stage.
   - Occurs if:
     - Approved CSV attempts to mark Detail 1A as Drywall.
     - Wall matching or fusion engine attempts to classify Tag 1A as Drywall.
     - `ClassifiedWallPolygon` mutator guard triggers on 1A tampering.

---

## 3. Concrete Architectural Design & Implementation Specifications

### 3.1 Design of `drywall_detection/cli.py`

#### Module Structure & Imports:
```python
"""
drywall_detection/cli.py
========================
Unified Production Command-Line Interface for the drywall_detection package.
Executable via: python -m drywall_detection <subcommand> [options]
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from drywall_detection import __version__
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    DATA_DIR,
    DEFAULT_DPI,
    DEFAULT_MASTER_PDF_PATH,
    EXIT_CODE_AWAITING_REVIEW,
    REPORTS_DIR,
    REVIEW_LOCKFILE_PATH,
    SCHEDULE_CSV_PATH,
)
from drywall_detection.classification.classifier import (
    DrywallClassifier,
    IntegrityViolationError,
    ScheduleValidationError,
)
from drywall_detection.pipeline.router import ModalityRouter, PipelineModality
from drywall_detection.pipeline.fusion import HybridFusionPipeline
from drywall_detection.pipeline.annotate import VisualOverlayConfig, WallAnnotator
from drywall_detection.vector.extractor import VectorExtractor
from drywall_detection.vector.schedule_parser import PartitionScheduleParser
from drywall_detection.audit.dataset_auditor import DatasetAuditor
from drywall_detection.utils.hardware import get_hardware_profile
from drywall_detection.pipeline.infer import parse_page_arg, DrywallInferencePipeline
```

#### Exit Code Constants:
```python
EXIT_SUCCESS: int = 0
EXIT_ERROR: int = 1
EXIT_REVIEW_REQUIRED: int = 2
EXIT_CMU_VETO_VIOLATION: int = 3
```

#### Detailed Subcommand Argument Definitions:

```python
def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drywall-detect",
        description="Drywall Detection & Takeoff Engine: Unified Production CLI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available Subcommands",
        description="Select a pipeline stage to execute:",
        metavar="<command>",
    )

    # --------------------------------------------------------------------------
    # 1. audit-datasets
    # --------------------------------------------------------------------------
    p_audit = subparsers.add_parser(
        "audit-datasets",
        help="Run licensing, disk safety, and label availability audit across candidate datasets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_audit.add_argument("--target-dir", type=Path, default=DATA_DIR, help="Target download directory for disk check.")
    p_audit.add_argument("--output-dir", type=Path, default=REPORTS_DIR, help="Directory to save audit reports.")
    p_audit.add_argument("--dataset-id", type=str, default=None, choices=["msd", "cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd"], help="Audit single dataset.")
    p_audit.add_argument("--check-network", action="store_true", default=False, help="Probe live HTTP endpoints.")
    p_audit.add_argument("--max-unannounced-gb", type=float, default=10.0, help="Maximum unannounced download limit in GB.")
    p_audit.add_argument("--format", choices=["table", "markdown", "json", "both"], default="table", help="Output display format.")
    p_audit.add_argument("--save", action="store_true", default=False, help="Save markdown and json reports to output-dir.")

    # --------------------------------------------------------------------------
    # 2. extract-vector
    # --------------------------------------------------------------------------
    p_extract = subparsers.add_parser(
        "extract-vector",
        help="Extract vector linework, parallel-pair wall polygons, text tokens, and partition tags from PDF.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_extract.add_argument("--pdf", type=Path, default=DEFAULT_MASTER_PDF_PATH, help="Input architectural PDF drawing set.")
    p_extract.add_argument("--pages", type=str, default="14", help="Page index or range (e.g. '14' for A-101, '13-18', 'all').")
    p_extract.add_argument("--output-dir", type=Path, default=DATA_DIR, help="Output directory for extracted files.")
    p_extract.add_argument("--format", choices=["geojson", "json"], default="geojson", help="Export format for wall candidates.")
    p_extract.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Coordinate resolution DPI.")
    p_extract.add_argument("--detect-only", action="store_true", help="Profile vector/raster modality without wall reconstruction.")

    # --------------------------------------------------------------------------
    # 3. parse-schedule
    # --------------------------------------------------------------------------
    p_schedule = subparsers.add_parser(
        "parse-schedule",
        help="Parse partition schedule sheets A-900 / A-901 into tabular CSV and enforce human review lock.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_schedule.add_argument("--pdf", type=Path, default=DEFAULT_MASTER_PDF_PATH, help="Input PDF containing sheets A-900 / A-901.")
    p_schedule.add_argument("--output-csv", type=Path, default=SCHEDULE_CSV_PATH, help="Path to write draft schedule CSV.")
    p_schedule.add_argument("--approved-csv", type=Path, default=APPROVED_SCHEDULE_CSV_PATH, help="Path to approved schedule CSV.")
    p_schedule.add_argument("--enforce-review-lock", action="store_true", default=True, help="Enforce human review stop protocol (exit code 2).")
    p_schedule.add_argument("--no-review-lock", action="store_false", dest="enforce_review_lock", help="Skip exit code 2 lock enforcement.")
    p_schedule.add_argument("--verify-detail-1a", action="store_true", help="Explicitly assert Detail 1A is Non-Drywall.")

    # --------------------------------------------------------------------------
    # 4. classify
    # --------------------------------------------------------------------------
    p_classify = subparsers.add_parser(
        "classify",
        help="Classify walls using approved schedule mapping with Detail 1A CMU veto and Tier 3 unassigned fallback.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_classify.add_argument("--pdf", type=Path, default=DEFAULT_MASTER_PDF_PATH, help="Input architectural PDF drawing.")
    p_classify.add_argument("--pages", type=str, default="14", help="Pages to classify (e.g. '14' for A-101).")
    p_classify.add_argument("--schedule-csv", type=Path, default=APPROVED_SCHEDULE_CSV_PATH, help="Approved schedule mapping CSV.")
    p_classify.add_argument("--output-dir", type=Path, default=DATA_DIR, help="Output directory.")
    p_classify.add_argument("--export-annotated-pdf", action="store_true", default=True, help="Generate native vector annotated PDF.")
    p_classify.add_argument("--export-raster-overlays", action="store_true", default=False, help="Render high-res PNG overlays with legend.")
    p_classify.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI resolution.")

    # --------------------------------------------------------------------------
    # 5. infer-segmentation
    # --------------------------------------------------------------------------
    p_infer = subparsers.add_parser(
        "infer-segmentation",
        help="Run SegFormer-B0 deep learning segmentation on floor plan images or PDFs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_infer.add_argument("--input", "-i", type=Path, required=True, help="Path to input drawing image (.png/.jpg) or PDF (.pdf).")
    p_infer.add_argument("--output-dir", "-o", type=Path, default=DATA_DIR, help="Directory to save segmentation output.")
    p_infer.add_argument("--checkpoint", "-c", type=Path, default=BEST_MODEL_DIR, help="Path to model checkpoint directory.")
    p_infer.add_argument("--tile-size", type=int, default=512, help="Sliding-window tile size.")
    p_infer.add_argument("--overlap", type=float, default=0.20, help="Sliding-window overlap fraction.")
    p_infer.add_argument("--device", "-d", type=str, default=None, choices=["cpu", "cuda"], help="Execution device.")
    p_infer.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Rendering DPI for PDF pages.")
    p_infer.add_argument("--pages", type=str, default=None, help="Page range for PDF.")

    # --------------------------------------------------------------------------
    # 6. run-pipeline
    # --------------------------------------------------------------------------
    p_run = subparsers.add_parser(
        "run-pipeline",
        help="Complete end-to-end vector-first pipeline with automatic raster/ML fallback routing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_run.add_argument("--pdf", type=Path, required=True, help="Path to input architectural PDF drawing set.")
    p_run.add_argument("--pages", type=str, default="14", help="Pages to process (e.g. '14' for A-101, '13-18', 'all').")
    p_run.add_argument("--output-dir", type=Path, default=DATA_DIR / "output", help="Directory for all generated deliverables.")
    p_run.add_argument("--checkpoint", type=Path, default=BEST_MODEL_DIR, help="Path to model checkpoint directory.")
    p_run.add_argument("--schedule-csv", type=Path, default=APPROVED_SCHEDULE_CSV_PATH, help="Approved schedule CSV path.")
    p_run.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Rendering and coordinate transformation DPI.")
    p_run.add_argument("--device", type=str, default=None, choices=["cpu", "cuda"], help="Execution device.")
    p_run.add_argument("--force-modality", choices=["VECTOR_FIRST", "RASTER_ML", "HYBRID"], default=None, help="Manually override modality routing.")
    p_run.add_argument("--export-pdf", action="store_true", default=True, help="Export native vector annotated PDF.")
    p_run.add_argument("--export-png", action="store_true", default=True, help="Export high-res raster PNG previews.")
    p_run.add_argument("--export-geojson", action="store_true", default=True, help="Export RFC 7946 GeoJSON takeoffs.")

    # --------------------------------------------------------------------------
    # 7. version / info
    # --------------------------------------------------------------------------
    p_info = subparsers.add_parser(
        "info",
        aliases=["version"],
        help="Display system profile, hardware environment, dependencies, and model checkpoint status.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_info.add_argument("--json", action="store_true", default=False, help="Emit profile as formatted JSON.")

    return parser
```

#### Subcommand Execution Logic & Error Handling:
```python
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli_parser()
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        return EXIT_SUCCESS

    args = parser.parse_args(argv)

    try:
        if args.subcommand in ("info", "version"):
            return cmd_info(args)
        elif args.subcommand == "audit-datasets":
            return cmd_audit_datasets(args)
        elif args.subcommand == "extract-vector":
            return cmd_extract_vector(args)
        elif args.subcommand == "parse-schedule":
            return cmd_parse_schedule(args)
        elif args.subcommand == "classify":
            return cmd_classify(args)
        elif args.subcommand == "infer-segmentation":
            return cmd_infer_segmentation(args)
        elif args.subcommand == "run-pipeline":
            return cmd_run_pipeline(args)
        else:
            parser.print_help()
            return EXIT_SUCCESS

    except IntegrityViolationError as ive:
        sys.stderr.write(f"\n[FATAL EXIT CODE 3] Detail 1A CMU Safety Invariant Violation: {ive}\n")
        return EXIT_CMU_VETO_VIOLATION
    except ScheduleValidationError as sve:
        sys.stderr.write(f"\n[ERROR EXIT CODE 2] Partition Schedule Review Error: {sve}\n")
        return EXIT_REVIEW_REQUIRED
    except FileNotFoundError as fnf:
        sys.stderr.write(f"\n[ERROR EXIT CODE 1] File Not Found: {fnf}\n")
        return EXIT_ERROR
    except Exception as exc:
        sys.stderr.write(f"\n[FATAL EXIT CODE 1] Unhandled Exception: {exc}\n")
        logging.exception("Unhandled CLI error:")
        return EXIT_ERROR
```

### 3.2 Design of `drywall_detection/__main__.py`
```python
"""
drywall_detection/__main__.py
=============================
Package entrypoint enabling execution via:
    python -m drywall_detection <command> [options]
"""

import sys
from drywall_detection.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Test Specifications for `drywall_detection/tests/test_cli.py`

A comprehensive, deterministic test suite must be placed in `drywall_detection/tests/test_cli.py` to ensure complete code coverage and verifiable exit code compliance.

### 4.1 Test Class Structure & Test Matrix

```
TestCLIParserAndHelp
├── test_parser_subcommands_registered
├── test_toplevel_help_flag_returns_0
├── test_subcommand_help_flags_return_0
└── test_unrecognized_argument_returns_error

TestCLIVersionAndInfo
├── test_info_command_text_output
├── test_info_command_json_output
└── test_info_checkpoint_status_verification

TestCLIAuditDatasets
├── test_audit_datasets_all_table_format
├── test_audit_datasets_single_dataset_msd
├── test_audit_datasets_save_flag_writes_reports
└── test_audit_datasets_invalid_id_rejected

TestCLIParseScheduleAndReviewLock
├── test_parse_schedule_normal_approved_exit_0
├── test_parse_schedule_missing_approved_exit_2
├── test_parse_schedule_detail_1a_tampering_exit_3
└── test_parse_schedule_verify_detail_1a_flag

TestCLIExtractVector
├── test_extract_vector_detect_only
├── test_extract_vector_geojson_export
└── test_extract_vector_invalid_page_returns_error

TestCLIClassify
├── test_classify_normal_with_approved_schedule
├── test_classify_missing_approved_schedule_exit_2
├── test_classify_cmu_veto_violation_exit_3
└── test_classify_tier3_unassigned_fallback

TestCLIInferSegmentation
├── test_infer_segmentation_synthetic_canvas
└── test_infer_segmentation_missing_checkpoint_returns_1

TestCLIRunPipelineEndToEnd
├── test_run_pipeline_vector_first_sheet_a101
├── test_run_pipeline_review_lock_active_exit_2
├── test_run_pipeline_cmu_veto_enforced_in_geojson
├── test_run_pipeline_modality_override_raster_ml
└── test_run_pipeline_produces_all_deliverables

TestCLIExecutionEntrypoint
├── test_python_module_execution_subprocess
└── test_help_execution_subprocess
```

### 4.2 Key Test Implementations (Design Blueprint)

```python
"""
drywall_detection/tests/test_cli.py
==================================
Comprehensive pytest test suite for the unified production CLI.
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest
import fitz

from drywall_detection import __version__
from drywall_detection.cli import (
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_REVIEW_REQUIRED,
    EXIT_CMU_VETO_VIOLATION,
    build_cli_parser,
    main,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    DEFAULT_MASTER_PDF_PATH,
)

class TestCLIParserAndHelp:
    def test_parser_subcommands_registered(self):
        parser = build_cli_parser()
        subparser_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparser_actions) == 1
        subcommands = subparser_actions[0].choices
        expected = [
            "audit-datasets", "extract-vector", "parse-schedule",
            "classify", "infer-segmentation", "run-pipeline", "info", "version"
        ]
        for cmd in expected:
            assert cmd in subcommands

    def test_toplevel_help_flag_returns_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "Drywall Detection & Takeoff Engine" in captured.out

    def test_subcommand_help_flags_return_0(self, capsys):
        for subcmd in ["audit-datasets", "extract-vector", "parse-schedule", "classify", "infer-segmentation", "run-pipeline", "info"]:
            with pytest.raises(SystemExit) as exc:
                main([subcmd, "--help"])
            assert exc.value.code == 0


class TestCLIVersionAndInfo:
    def test_info_command_text_output(self, capsys):
        code = main(["info"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert f"Version: {__version__}" in captured.out
        assert "Hardware Environment Profile" in captured.out
        assert "Champion Model Status" in captured.out

    def test_info_command_json_output(self, capsys):
        code = main(["info", "--json"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["version"] == __version__
        assert "hardware" in data
        assert "checkpoints" in data
        assert data["checkpoints"]["champion_model_found"] is True


class TestCLIParseScheduleAndReviewLock:
    def test_parse_schedule_normal_approved_exit_0(self, tmp_path):
        out_csv = tmp_path / "draft_schedule.csv"
        code = main([
            "parse-schedule",
            "--output-csv", str(out_csv),
            "--approved-csv", str(APPROVED_SCHEDULE_CSV_PATH),
        ])
        assert code == EXIT_SUCCESS
        assert out_csv.exists()

    def test_parse_schedule_missing_approved_exit_2(self, tmp_path):
        out_csv = tmp_path / "draft_schedule.csv"
        non_existent_approved = tmp_path / "missing.approved.csv"
        code = main([
            "parse-schedule",
            "--output-csv", str(out_csv),
            "--approved-csv", str(non_existent_approved),
        ])
        assert code == EXIT_REVIEW_REQUIRED

    def test_parse_schedule_detail_1a_tampering_exit_3(self, tmp_path):
        # Create a malicious approved CSV marking Detail 1A as Drywall
        bad_approved = tmp_path / "bad.approved.csv"
        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as fin:
            content = fin.read()
        tampered = content.replace("1A,A-900,PARTITION TYPE DETAIL 1A - 1 HR RATED,6\" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.,None (CMU block),0,None,1-HR,None,None / Bare CMU,Masonry,Non-Drywall,1.0,",
                                   "1A,A-900,PARTITION TYPE DETAIL 1A - 1 HR RATED,6\" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.,None (CMU block),0,None,1-HR,None,None / Bare CMU,Masonry,Drywall,1.0,")
        with open(bad_approved, "w", encoding="utf-8") as fout:
            fout.write(tampered)

        code = main([
            "parse-schedule",
            "--approved-csv", str(bad_approved),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION


class TestCLIRunPipelineEndToEnd:
    def test_run_pipeline_vector_first_sheet_a101(self, tmp_path):
        out_dir = tmp_path / "pipeline_out"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
        ])
        assert code == EXIT_SUCCESS
        # Verify deliverable files
        annotated_pdf = list(out_dir.glob("*.pdf"))
        assert len(annotated_pdf) > 0
        geojson = list(out_dir.glob("*.geojson"))
        assert len(geojson) > 0
        summary_json = list(out_dir.glob("*summary.json"))
        assert len(summary_json) > 0

    def test_run_pipeline_cmu_veto_enforced_in_geojson(self, tmp_path):
        out_dir = tmp_path / "pipeline_cmu_test"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
        ])
        assert code == EXIT_SUCCESS
        geojson_path = list(out_dir.glob("*.geojson"))[0]
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for feature in data["features"]:
            props = feature["properties"]
            if props.get("matched_tag") == "1A":
                assert props["classification"] == "Non-Drywall"
                assert props["color_hex"] == "#D50000"


class TestCLIExecutionEntrypoint:
    def test_python_module_execution_subprocess(self):
        cmd = [sys.executable, "-m", "drywall_detection", "info", "--json"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["version"] == __version__
```

---

## 5. Caveats

1. **Progress Set Notice (95% CDs)**:
   - All tests and pipeline executions run against MTA Contract C-48526 (99th Street Phase 2 Interior Set), explicitly stamped "PROGRESS SET 95% CDs 10/02/2026".
   - This represents an unapproved progress set and a single-project calibration sample. Accuracy metrics (e.g. against Usman red markups) demonstrate single-facility calibration and cannot mathematically guarantee identical zero-shot accuracy on unseen projects without partition schedule review.
2. **Review Lockfile State**:
   - The repository currently contains `partition_schedule_mapping.approved.csv` (approved with 18 Drywall, 5 Non-Drywall, 1 Uncertain).
   - In production use, if a user points the CLI to an unapproved project schedule, the system deliberately halts with Exit Code `2` and writes `REVIEW_REQUIRED.lock`. This is by design to ensure zero material hallucination.
3. **Execution Device**:
   - `run-pipeline` runs smoothly on CPU via vector-first processing (< 2 seconds per page). When ML segmentation (`infer-segmentation` or `RASTER_ML`) is invoked, inference time on local CPU is ~15-20 seconds per 512x512 tile window compared to < 0.5s on CUDA GPU.

---

## 6. Conclusion

1. **Architecture Complete**: The specification for `drywall_detection/cli.py` and `drywall_detection/__main__.py` provides a unified, production-ready interface satisfying all user requirements for Milestone M6.
2. **Data Flow Verified**: The end-to-end pipeline (`run-pipeline`) traces an exact, rigorous data flow from document ingestion to `ModalityRouter`, through `VECTOR_FIRST`, `RASTER_ML`, and `HYBRID` paths, maintaining strict schedule dominance and four layers of Detail 1A CMU veto protection.
3. **Packaging & Exit Codes Aligned**: POSIX exit codes (`0`, `1`, `2`, `3`) clearly distinguish success, general runtime failure, human-in-the-loop review halts, and safety invariant breaches.
4. **Test Specification Prepared**: `drywall_detection/tests/test_cli.py` is comprehensively specified with unit, integration, and subprocess test fixtures covering all arguments, subcommands, and failure modes.

---

## 7. Verification Method

To independently verify this architectural design once implemented:

1. **Entrypoint Verification**:
   ```bash
   python -m drywall_detection --help
   python -m drywall_detection info --json
   ```
   *Expected*: Returns exit code 0, prints formatted JSON with version 0.1.0, host hardware, and champion checkpoint details.

2. **Dataset Audit Subcommand**:
   ```bash
   python -m drywall_detection audit-datasets --format table
   ```
   *Expected*: Evaluates all 6 datasets, outputs Markdown table, returns exit code 0.

3. **Schedule Parsing & Review Lock Protocol**:
   ```bash
   python -m drywall_detection parse-schedule --verify-detail-1a
   ```
   *Expected*: Verifies Detail 1A is Non-Drywall (Red), returns exit code 0.

4. **Vector Extraction & Wall Geometry**:
   ```bash
   python -m drywall_detection extract-vector --pdf "C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf" --pages 14
   ```
   *Expected*: Extracts wall candidates and tags for Sheet A-101, outputs GeoJSON, returns exit code 0.

5. **End-to-End Pipeline Execution**:
   ```bash
   python -m drywall_detection run-pipeline --pdf "C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf" --pages 14 --output-dir "drywall_detection/data/output"
   ```
   *Expected*: Modality router detects pure vector CAD, routes to `VECTOR_FIRST`, applies approved schedule with CMU veto, exports annotated vector PDF, high-res PNG, and RFC 7946 GeoJSON takeoff. Returns exit code 0.

6. **Pytest Test Suite Execution**:
   ```bash
   pytest drywall_detection/tests/test_cli.py -v
   ```
   *Expected*: All test fixtures pass with zero failures.
