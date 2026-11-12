"""
drywall_detection/cli.py
========================
Unified Production Command-Line Interface for the drywall_detection package.
Executable via:
    python -m drywall_detection <subcommand> [options]
"""

from __future__ import annotations
import argparse
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import fitz  # PyMuPDF

from drywall_detection import __version__
from drywall_detection.audit.dataset_auditor import DatasetAuditor
from drywall_detection.classification.classifier import (
    DrywallClassifier,
    IntegrityViolationError,
    ScheduleValidationError,
    ClassifiedWallPolygon,
)
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
from drywall_detection.pipeline.annotate import VisualOverlayConfig, WallAnnotator
from drywall_detection.pipeline.fusion import HybridFusionPipeline
from drywall_detection.pipeline.infer import DrywallInferencePipeline
from drywall_detection.pipeline.router import PipelineModality
from drywall_detection.utils.hardware import probe_hardware
from drywall_detection.vector.extractor import VectorExtractor
from drywall_detection.vector.schedule_parser import PartitionScheduleParser

logger = logging.getLogger("drywall_detection.cli")

# Strict POSIX Exit Codes
EXIT_SUCCESS: int = 0
EXIT_ERROR: int = 1
EXIT_REVIEW_REQUIRED: int = 2
EXIT_CMU_VETO_VIOLATION: int = 3


def _parse_page_list(page_str: Optional[Union[str, int]], total_pages: int = 999999) -> List[int]:
    """Parses page specification string into a sorted list of zero-based integer indices."""
    if page_str is None or str(page_str).strip().lower() == "all":
        return list(range(total_pages))
    if isinstance(page_str, int):
        return [page_str]
    pages: List[int] = []
    for part in str(page_str).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s.strip()), int(end_s.strip())
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return sorted(list(set(pages)))


def build_cli_parser() -> argparse.ArgumentParser:
    """Constructs the unified command-line parser with all 7 subcommands."""
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
    p_audit.add_argument(
        "--dataset-id",
        type=str,
        default=None,
        choices=["msd", "cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd"],
        help="Audit single dataset.",
    )
    p_audit.add_argument("--check-network", action="store_true", default=False, help="Probe live HTTP endpoints.")
    p_audit.add_argument("--max-unannounced-gb", type=float, default=10.0, help="Maximum unannounced download limit in GB.")
    p_audit.add_argument(
        "--format",
        choices=["table", "markdown", "json", "both"],
        default="table",
        help="Output display format.",
    )
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
    p_run.add_argument(
        "--force-modality",
        choices=["VECTOR_FIRST", "RASTER_ML", "HYBRID"],
        default=None,
        help="Manually override modality routing.",
    )
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


def cmd_info(args: argparse.Namespace) -> int:
    """Executes the 'info' / 'version' subcommand."""
    profile = probe_hardware()
    model_path = BEST_MODEL_DIR / "best_model.pt"
    config_path = BEST_MODEL_DIR / "config.json"
    metrics_path = BEST_MODEL_DIR / "metrics.json"
    class_mapping_path = BEST_MODEL_DIR / "class_mapping.json"

    ckpt_info: Dict[str, Any] = {
        "champion_model_found": model_path.is_file(),
        "directory": str(BEST_MODEL_DIR),
        "weights_size_bytes": model_path.stat().st_size if model_path.is_file() else 0,
        "config": json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {},
        "metrics": json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {},
        "class_mapping": json.loads(class_mapping_path.read_text(encoding="utf-8")) if class_mapping_path.is_file() else {},
    }

    if getattr(args, "json", False):
        payload = {
            "version": __version__,
            "hardware": profile.to_dict(),
            "checkpoints": ckpt_info,
        }
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 70)
        print("Drywall Detection & Takeoff Engine")
        print(f"Version: {__version__}")
        print("=" * 70)
        print("\n--- Hardware Environment Profile ---")
        print(profile.to_markdown_table())
        print("\n--- Champion Model Status ---")
        print(f"Champion Model Found: {ckpt_info['champion_model_found']}")
        print(f"Directory: {ckpt_info['directory']}")
        print(f"Weights Size: {ckpt_info['weights_size_bytes'] / (1024 * 1024):.2f} MB")
        if ckpt_info.get("metrics"):
            m = ckpt_info["metrics"]
            print(f"Validation Wall IoU: {m.get('val_wall_iou', 'N/A')}")
            print(f"Validation mIoU: {m.get('val_miou', 'N/A')}")

    return EXIT_SUCCESS


def cmd_audit_datasets(args: argparse.Namespace) -> int:
    """Executes dataset licensing, disk safety, and wall label audit."""
    auditor = DatasetAuditor(
        target_download_dir=args.target_dir,
        max_unannounced_gb=args.max_unannounced_gb,
        offline_mode=not args.check_network,
    )
    if args.dataset_id:
        res = auditor.audit_candidate(args.dataset_id, check_network=args.check_network)
        if args.format == "json":
            d = res.to_dict()
            d["dataset_id"] = res.dataset_spec.dataset_id
            print(json.dumps(d, indent=2))
        else:
            print(f"Dataset: {res.name}")
            print(f"Eligibility: {res.eligibility_verdict}")
            print(f"Size: {res.download_size_gb:.2f} GB")
            print(f"Wall Labels: {res.has_wall_annotations}")
            print(f"Commercial Allowed: {res.is_commercial_allowed}")
            if res.blockers:
                print("Blockers:")
                for b in res.blockers:
                    print(f"  - {b}")
    else:
        report = auditor.audit_all(check_network=args.check_network)
        if args.save:
            saved = auditor.save_reports(output_dir=args.output_dir)
            print(f"Saved reports to {saved['markdown']} and {saved['json']}")

        if args.format == "json":
            print(auditor.generate_json_report(report))
        elif args.format in ("table", "markdown", "both"):
            print(auditor.generate_markdown_report(report))

    return EXIT_SUCCESS


def cmd_extract_vector(args: argparse.Namespace) -> int:
    """Executes vector CAD linework, wall candidates, and partition tag extraction."""
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF drawing set not found at: {pdf_path}")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    page_indices = _parse_page_list(args.pages, total_pages)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    extractor = VectorExtractor(dpi=args.dpi)
    for p_idx in page_indices:
        if p_idx < 0 or p_idx >= total_pages:
            raise ValueError(f"Page index {p_idx} out of range [0, {total_pages - 1}]")
        page = doc[p_idx]
        profile = extractor.detect_vector_content(page)
        print(f"\n--- Page {p_idx + 1} (Index {p_idx}) Vector Profile ---")
        print(f"Recommended Modality: {profile.recommended_pipeline}")
        print(f"Linework: {profile.line_count} lines, {profile.rect_count} rects, {profile.word_count} words")

        if args.detect_only:
            continue

        walls = extractor.extract_wall_candidates(page)
        tags = extractor.find_partition_tags(page)
        print(f"Extracted {len(walls)} wall candidates, {len(tags)} partition tags.")

        if args.format == "geojson":
            fc = {
                "type": "FeatureCollection",
                "page": p_idx,
                "features": [w.to_geojson_feature() for w in walls],
            }
            out_file = out_dir / f"extracted_walls_p{p_idx}.geojson"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(fc, f, indent=2)
            print(f"Saved GeoJSON candidates to: {out_file}")

    return EXIT_SUCCESS


def cmd_parse_schedule(args: argparse.Namespace) -> int:
    """Executes partition schedule parsing and human review lock verification."""
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF not found at: {pdf_path}")

    parser = PartitionScheduleParser()
    parser.parse_pdf(pdf_path)

    out_csv = Path(args.output_csv)
    appr_csv = Path(args.approved_csv)
    lock_file = out_csv.parent / "REVIEW_REQUIRED.lock"

    # Enforce review lock logic
    if not appr_csv.is_file():
        parser.export_and_enforce_review_lock(
            csv_path=out_csv,
            approved_csv_path=appr_csv,
            lock_path=lock_file,
            interactive_mode=False,
        )
        if args.enforce_review_lock:
            sys.stderr.write(
                f"\n[AWAITING REVIEW (EXIT CODE 2)] Draft schedule exported to: {out_csv}\n"
                f"Lockfile created at: {lock_file}\n"
                f"Human review required before downstream classification.\n"
            )
            return EXIT_REVIEW_REQUIRED
        return EXIT_SUCCESS

    # If approved CSV exists, verify it
    # Note: export_and_enforce_review_lock validates Detail 1A and raises ValueError if 1A is Drywall
    is_valid = parser.export_and_enforce_review_lock(
        csv_path=out_csv,
        approved_csv_path=appr_csv,
        lock_path=lock_file,
        interactive_mode=False,
    )
    if not is_valid:
        if args.enforce_review_lock:
            return EXIT_REVIEW_REQUIRED

    if args.verify_detail_1a:
        # Check approved CSV content directly
        classifier = DrywallClassifier(schedule_csv=appr_csv)
        if classifier.schedule_mapping["1A"]["proposed_class"] != "Non-Drywall":
            raise IntegrityViolationError("Detail 1A must NOT be classified as Drywall!")
        print("Detail 1A CMU safety invariant verified: Non-Drywall (Red #D50000).")

    print(f"Schedule parsed successfully. 24 details exported to: {out_csv}. Approved CSV validated.")
    return EXIT_SUCCESS


def cmd_classify(args: argparse.Namespace) -> int:
    """Executes wall classification using approved schedule mapping and Detail 1A CMU veto."""
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF not found at: {pdf_path}")

    sched_csv = Path(args.schedule_csv)
    if not sched_csv.is_file():
        sys.stderr.write(f"\n[EXIT CODE 2] Approved schedule CSV not found at: {sched_csv}\n")
        return EXIT_REVIEW_REQUIRED

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # DrywallClassifier validates schedule on init (and raises IntegrityViolationError if 1A is Drywall)
    classifier = DrywallClassifier(schedule_csv=sched_csv, dpi=args.dpi)
    extractor = VectorExtractor(dpi=args.dpi)
    schedule_parser = PartitionScheduleParser()

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    page_indices = _parse_page_list(args.pages, total_pages)

    annotated_pages: Dict[int, List[ClassifiedWallPolygon]] = {}

    for p_idx in page_indices:
        page = doc[p_idx]
        walls = extractor.extract_wall_candidates(page)
        tags = schedule_parser.discover_tags(page, page_idx=p_idx)
        classified = classifier.classify_walls(walls=walls, tags=tags, page_idx=p_idx, sheet=f"Sheet_{p_idx + 1}")
        annotated_pages[p_idx] = classified

        geojson_path = out_dir / f"classified_walls_p{p_idx}.geojson"
        classifier.export_geojson(classified, geojson_path)
        print(f"Page {p_idx + 1}: Classified {len(classified)} walls -> {geojson_path}")

        if args.export_raster_overlays:
            annotator = WallAnnotator(VisualOverlayConfig(dpi=args.dpi))
            summary_stats = classifier.compute_summary(classified).to_dict()
            raster_img = annotator.render_raster_image(page, classified, summary_stats)
            img_out = out_dir / f"overlay_p{p_idx}.png"
            raster_img.save(img_out)
            print(f"Page {p_idx + 1}: Saved overlay image to: {img_out}")

    if args.export_annotated_pdf:
        annotator = WallAnnotator(VisualOverlayConfig(dpi=args.dpi))
        out_pdf = out_dir / "annotated_classified_drawings.pdf"
        annotator.generate_annotated_vector_pdf(pdf_path, annotated_pages, out_pdf)
        print(f"Generated annotated vector PDF: {out_pdf}")

    return EXIT_SUCCESS


def cmd_infer_segmentation(args: argparse.Namespace) -> int:
    """Executes SegFormer-B0 sliding-window semantic segmentation."""
    input_path = Path(args.input)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found at: {input_path}")

    ckpt_dir = Path(args.checkpoint)
    if not ckpt_dir.is_dir() or not (ckpt_dir / "best_model.pt").is_file():
        raise FileNotFoundError(f"Champion checkpoint not found in directory: {ckpt_dir}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = _parse_page_list(args.pages, 999999) if args.pages else None

    pipeline = DrywallInferencePipeline(
        checkpoint_dir=ckpt_dir,
        device=args.device,
        dpi=args.dpi,
        tile_size=args.tile_size,
        overlap=args.overlap,
    )

    output_path = out_dir / f"{input_path.stem}_segmented{input_path.suffix}"
    summary = pipeline.process(
        input_path=input_path,
        output_path=output_path,
        pages=pages,
    )

    summary_path = out_dir / f"{input_path.stem}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return EXIT_SUCCESS


def cmd_run_pipeline(args: argparse.Namespace) -> int:
    """Executes full end-to-end vector-first pipeline with automatic modality fallback routing."""
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF not found at: {pdf_path}")

    sched_csv = Path(args.schedule_csv)
    if not sched_csv.is_file():
        sys.stderr.write(f"\n[EXIT CODE 2] Approved schedule CSV not found at: {sched_csv}\n")
        return EXIT_REVIEW_REQUIRED

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    force_mod = None
    if args.force_modality:
        force_mod = PipelineModality[args.force_modality]

    pipeline = HybridFusionPipeline(
        checkpoint_dir=args.checkpoint,
        schedule_csv=sched_csv,
        dpi=args.dpi,
        device=args.device,
    )

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    page_indices = _parse_page_list(args.pages, total_pages)

    annotated_pages: Dict[int, List[ClassifiedWallPolygon]] = {}
    all_summaries: Dict[str, Any] = {"pages": {}, "aggregate": {}}

    t0 = time.time()
    for p_idx in page_indices:
        if p_idx < 0 or p_idx >= total_pages:
            continue
        page = doc[p_idx]
        sheet_name = f"Sheet_{p_idx + 1}"
        res = pipeline.process_page(page, sheet_name=sheet_name, force_modality=force_mod)
        annotated_pages[p_idx] = res.classified_walls
        all_summaries["pages"][sheet_name] = res.to_dict()

        # Unconditional CMU Veto Verification
        for w in res.classified_walls:
            if w.matched_tag == "1A" and w.classification == "Drywall":
                raise IntegrityViolationError("INTEGRITY VIOLATION: Detail 1A CMU wall classified as Drywall!")

        if args.export_geojson:
            fc = {
                "type": "FeatureCollection",
                "page": p_idx,
                "sheet": sheet_name,
                "summary": res.summary_stats,
                "features": [w.to_geojson_feature() for w in res.classified_walls],
            }
            geo_path = out_dir / f"{sheet_name}_takeoff.geojson"
            with open(geo_path, "w", encoding="utf-8") as f:
                json.dump(fc, f, indent=2)

        if args.export_png:
            annotator = WallAnnotator(VisualOverlayConfig(dpi=args.dpi))
            img = annotator.render_raster_image(page, res.classified_walls, res.summary_stats)
            img_path = out_dir / f"{sheet_name}_preview.png"
            img.save(img_path)

    if args.export_pdf:
        annotator = WallAnnotator(VisualOverlayConfig(dpi=args.dpi))
        out_pdf = out_dir / f"{pdf_path.stem}_annotated.pdf"
        annotator.generate_annotated_vector_pdf(pdf_path, annotated_pages, out_pdf)
        all_summaries["annotated_pdf"] = str(out_pdf)

    all_summaries["elapsed_seconds"] = round(time.time() - t0, 3)
    summary_file = out_dir / "pipeline_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    print(f"Pipeline executed successfully. Deliverables generated in: {out_dir}")
    return EXIT_SUCCESS


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main execution entry point for unified CLI."""
    parser = build_cli_parser()

    # If invoked with no arguments, display help and return success
    if argv is None:
        if len(sys.argv) <= 1:
            parser.print_help()
            return EXIT_SUCCESS
        args = parser.parse_args()
    else:
        if len(argv) == 0:
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
    except ValueError as ve:
        msg = str(ve).upper()
        if "INTEGRITY VIOLATION" in msg or "DETAIL 1A" in msg:
            sys.stderr.write(f"\n[FATAL EXIT CODE 3] Detail 1A CMU Safety Invariant Violation: {ve}\n")
            return EXIT_CMU_VETO_VIOLATION
        sys.stderr.write(f"\n[ERROR EXIT CODE 1] Value Error: {ve}\n")
        return EXIT_ERROR
    except FileNotFoundError as fnf:
        sys.stderr.write(f"\n[ERROR EXIT CODE 1] File Not Found: {fnf}\n")
        return EXIT_ERROR
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"\n[FATAL EXIT CODE 1] Unhandled Exception: {exc}\n")
        logger.exception("Unhandled CLI exception:")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
