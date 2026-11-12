#!/usr/bin/env python3
"""
drywall_detection.pipeline.infer
================================
Unified Architectural PDF & Image Inference Pipeline.

Satisfies Requirement R4:
  - Vector & Scanned Architectural PDF processing at configurable DPI (default 150).
  - Extracts page metadata: dimensions in points (MediaBox/CropBox), rotation, page count.
  - 512x512 sliding-window tiling with configurable overlap (default 20%, stride 410)
    and 2D Hann apodization window stitching.
  - Small-canvas bounds guard (handling canvases smaller than 512x512 without broadcast errors).
  - 4-Class material taxonomy:
      0: Background (Canvas/Structure)
      1: Drywall (Green #00FF00 / #00C853)
      2: Non-Drywall (Red #FF0000 / #D50000)
      3: Uncertain / Generic Wall (Yellow #FFFF00 / #FFD600)
  - Vector-linework-preserving annotated PDF export.
  - Clean CLI invocation supporting single-file, batch, and directory processing.
  - Emits structured JSON summary with per-page and aggregate statistics.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

# Ensure workspace root is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer
from drywall_detection.config import (
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    DEFAULT_OVERLAY_ALPHA,
)
from drywall_detection.pipeline.annotate import (
    PALETTE_STANDARD,
    PALETTE_VIBRANT,
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
    render_blended_image,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline.infer")

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


class DrywallInferencePipeline:
    """
    End-to-end inference and annotation pipeline for architectural drawings.
    """

    def __init__(
        self,
        checkpoint_dir: Union[str, Path] = BEST_MODEL_DIR,
        device: Optional[str] = None,
        dpi: int = DEFAULT_DPI,
        tile_size: int = 512,
        overlap: float = 0.20,
        alpha: float = DEFAULT_OVERLAY_ALPHA,
        annotation_method: str = "overlay",
        palette_name: str = "standard",
    ) -> None:
        if dpi <= 0:
            raise ValueError(f"DPI must be strictly positive, got {dpi}")
        if tile_size <= 0:
            raise ValueError(f"tile_size must be strictly positive, got {tile_size}")

        self.dpi = dpi
        self.tile_size = tile_size
        self.overlap = overlap
        self.alpha = alpha
        self.annotation_method = annotation_method
        self.palette = PALETTE_VIBRANT if palette_name == "vibrant" else PALETTE_STANDARD

        logger.info("Initializing StandaloneInferencer from %s...", checkpoint_dir)
        self.inferencer = StandaloneInferencer(checkpoint_dir=checkpoint_dir, device=device)
        self.annotator = PDFAnnotator(
            alpha=self.alpha,
            palette=self.palette,
            annotation_method=self.annotation_method,
        )

    def process_pdf_page(
        self,
        doc: fitz.Document,
        page_idx: int,
    ) -> Tuple[np.ndarray, Image.Image, Dict[str, Any]]:
        """
        Renders and segments a single PDF page at configured DPI.

        Returns:
            mask_uint8: [H, W] predicted class mask.
            rendered_image: PIL RGB visual page image.
            page_metrics: Structured metrics dictionary.
        """
        page = doc[page_idx]
        t0 = time.time()

        # Render visual page to high-res pixmap
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Run sliding-window inference with Hann apodization window
        mask, norm_probs = self.inferencer.predict_image_sliding_window(
            img,
            tile_size=self.tile_size,
            overlap=self.overlap,
        )
        t_elapsed = time.time() - t0

        dim_pt = (float(page.mediabox.width), float(page.mediabox.height))
        metrics = compute_mask_metrics(
            mask_uint8=mask,
            page_num=page_idx + 1,
            dimensions_px=(img.height, img.width),
            dimensions_pt=dim_pt,
            rotation_deg=page.rotation,
            elapsed_sec=t_elapsed,
        )

        return mask, img, metrics

    def process_pdf(
        self,
        input_pdf_path: Union[str, Path],
        output_pdf_path: Union[str, Path],
        pages: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Processes multi-page architectural PDF, annotates pages preserving vector
        quality, dimensions, and rotation, and exports annotated PDF.
        """
        in_path = Path(input_pdf_path)
        out_path = Path(output_pdf_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(in_path)
        total_doc_pages = len(doc)
        pages_to_process = pages if pages is not None else list(range(total_doc_pages))

        logger.info(
            "Processing %d of %d pages from %s at %d DPI...",
            len(pages_to_process),
            total_doc_pages,
            in_path.name,
            self.dpi,
        )

        t_start = time.time()
        page_metrics_list: List[Dict[str, Any]] = []

        for step_idx, p_idx in enumerate(pages_to_process):
            if p_idx < 0 or p_idx >= total_doc_pages:
                logger.warning("Skipping out-of-range page index %d", p_idx)
                continue

            if progress_callback:
                progress_callback(step_idx, len(pages_to_process), f"Processing Page {p_idx+1}/{total_doc_pages}")

            page = doc[p_idx]
            logger.info("Segmenting Page %d (%s, rotation=%d°)...", p_idx + 1, page.rect, page.rotation)
            mask, _, metrics = self.process_pdf_page(doc, p_idx)
            page_metrics_list.append(metrics)

            # Apply annotation directly onto PDF page
            if self.annotation_method == "polygon":
                self.annotator.annotate_pdf_page_polygons(page, mask, dpi=self.dpi)
            else:
                self.annotator.annotate_pdf_page_overlay(page, mask)

        # Save annotated PDF preserving vector linework and original geometry
        doc.save(str(out_path), deflate=True, garbage=4)
        doc.close()

        total_elapsed = time.time() - t_start
        file_size_kb = out_path.stat().st_size / 1024.0

        # Calculate aggregate statistics
        total_pixels = sum(m["total_pixels"] for m in page_metrics_list)
        total_c0 = sum(m["class_pixel_counts"]["background"] for m in page_metrics_list)
        total_c1 = sum(m["class_pixel_counts"]["drywall"] for m in page_metrics_list)
        total_c2 = sum(m["class_pixel_counts"]["non_drywall"] for m in page_metrics_list)
        total_c3 = sum(m["class_pixel_counts"]["uncertain"] for m in page_metrics_list)
        total_walls = total_c1 + total_c2 + total_c3

        summary: Dict[str, Any] = {
            "status": "success",
            "type": "pdf",
            "input_path": str(in_path),
            "output_path": str(out_path),
            "output_file_size_kb": round(file_size_kb, 1),
            "model": {
                "architecture": self.inferencer.config.get("model_architecture") or self.inferencer.config.get("architecture"),
                "device": str(self.inferencer.device),
            },
            "parameters": {
                "dpi": self.dpi,
                "tile_size": self.tile_size,
                "overlap": self.overlap,
                "alpha": self.alpha,
                "annotation_method": self.annotation_method,
            },
            "total_pages_in_doc": total_doc_pages,
            "pages_processed_count": len(page_metrics_list),
            "pages": page_metrics_list,
            "aggregate_statistics": {
                "total_pixels": total_pixels,
                "total_background_pixels": total_c0,
                "total_drywall_pixels": total_c1,
                "total_non_drywall_pixels": total_c2,
                "total_uncertain_pixels": total_c3,
                "total_wall_pixels": total_walls,
                "overall_drywall_pct": round((total_c1 / total_pixels) * 100.0, 4) if total_pixels else 0.0,
                "overall_wall_density_pct": round((total_walls / total_pixels) * 100.0, 4) if total_pixels else 0.0,
                "total_elapsed_sec": round(total_elapsed, 3),
            },
        }

        return summary

    def process_image(
        self,
        input_image_path: Union[str, Path],
        output_image_path: Union[str, Path],
        mode: str = "overlay",
    ) -> Dict[str, Any]:
        """
        Processes single floor plan image (.png, .jpg, .tif).
        """
        in_path = Path(input_image_path)
        out_path = Path(output_image_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        image = Image.open(in_path).convert("RGB")
        mask, norm_probs = self.inferencer.predict_image_sliding_window(
            image,
            tile_size=self.tile_size,
            overlap=self.overlap,
        )
        elapsed = time.time() - t0

        metrics = compute_mask_metrics(
            mask_uint8=mask,
            page_num=1,
            dimensions_px=(image.height, image.width),
            dimensions_pt=None,
            rotation_deg=0,
            elapsed_sec=elapsed,
        )

        # Output rendering
        if str(out_path).lower().endswith(".pdf"):
            # If user requested PDF output from image
            blended = render_blended_image(np.array(image), mask, alpha=self.alpha, palette=self.palette)
            Image.fromarray(blended).save(out_path, format="PDF", resolution=self.dpi)
        elif mode == "mask":
            Image.fromarray(mask, mode="L").save(out_path)
        else:
            blended = render_blended_image(np.array(image), mask, alpha=self.alpha, palette=self.palette)
            Image.fromarray(blended).save(out_path)

        file_size_kb = out_path.stat().st_size / 1024.0

        return {
            "status": "success",
            "type": "image",
            "input_path": str(in_path),
            "output_path": str(out_path),
            "output_file_size_kb": round(file_size_kb, 1),
            "model": {
                "architecture": self.inferencer.config.get("model_architecture") or self.inferencer.config.get("architecture"),
                "device": str(self.inferencer.device),
            },
            "parameters": {
                "tile_size": self.tile_size,
                "overlap": self.overlap,
                "alpha": self.alpha,
                "mode": mode,
            },
            "pages": [metrics],
            "aggregate_statistics": {
                "total_pixels": metrics["total_pixels"],
                "total_drywall_pixels": metrics["class_pixel_counts"]["drywall"],
                "total_non_drywall_pixels": metrics["class_pixel_counts"]["non_drywall"],
                "total_uncertain_pixels": metrics["class_pixel_counts"]["uncertain"],
                "overall_drywall_pct": metrics["drywall_percentage"],
                "total_elapsed_sec": round(elapsed, 3),
            },
        }

    def process(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        pages: Optional[List[int]] = None,
        mode: str = "overlay",
    ) -> Dict[str, Any]:
        """
        Universal dispatch entry point for single file, multi-page PDF, or directory.
        """
        in_p = Path(input_path)
        if not in_p.exists():
            raise FileNotFoundError(f"Input path does not exist: {in_p}")

        if in_p.is_file():
            suffix = in_p.suffix.lower()
            if suffix == ".pdf":
                out_p = Path(output_path) if output_path else in_p.parent / f"{in_p.stem}_annotated.pdf"
                return self.process_pdf(in_p, out_p, pages=pages)
            elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
                out_p = Path(output_path) if output_path else in_p.parent / f"{in_p.stem}_annotated.png"
                return self.process_image(in_p, out_p, mode=mode)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
        elif in_p.is_dir():
            # Batch directory processing
            out_dir = Path(output_path) if output_path else in_p / "annotated"
            out_dir.mkdir(parents=True, exist_ok=True)

            batch_results: List[Dict[str, Any]] = []
            files_to_run = [
                f for f in in_p.iterdir()
                if f.is_file() and (f.suffix.lower() == ".pdf" or f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS)
            ]

            logger.info("Found %d supported files in directory %s", len(files_to_run), in_p)
            for file_path in files_to_run:
                target_out = out_dir / f"{file_path.stem}_annotated{file_path.suffix}"
                try:
                    res = self.process(file_path, target_out, pages=pages, mode=mode)
                    batch_results.append(res)
                except Exception as exc:
                    logger.error("Failed processing %s: %s", file_path.name, exc)
                    batch_results.append({
                        "status": "error",
                        "input_path": str(file_path),
                        "error": str(exc),
                    })

            return {
                "status": "batch_completed",
                "input_directory": str(in_p),
                "output_directory": str(out_dir),
                "total_files": len(files_to_run),
                "successful": sum(1 for r in batch_results if r.get("status") == "success"),
                "results": batch_results,
            }
        else:
            raise ValueError(f"Invalid path type: {in_p}")


def parse_page_arg(page_str: Optional[Union[str, int]]) -> Optional[List[int]]:
    """Parses page CLI argument into a list of 0-based page indices."""
    if page_str is None:
        return None
    if isinstance(page_str, int):
        return [page_str]
    pages: List[int] = []
    for part in str(page_str).split(","):
        part = part.strip()
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages.extend(range(start, end + 1))
        elif part:
            pages.append(int(part))
    return sorted(list(set(pages)))


def build_cli_parser() -> argparse.ArgumentParser:
    """Constructs command-line argument parser satisfying Requirement R4."""
    parser = argparse.ArgumentParser(
        prog="python -m drywall_detection.pipeline.infer",
        description="Unified Architectural PDF & Floor Plan Inference and Annotation Pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to input architectural PDF (.pdf), floor plan image (.png/.jpg), or directory",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Path to output annotated PDF or image (defaults to <input_stem>_annotated.<ext>)",
    )
    parser.add_argument(
        "--checkpoint", "-c",
        type=str,
        default=str(BEST_MODEL_DIR),
        help="Path to model checkpoint directory or best_model.pt",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help="Rendering resolution in DPI for PDF pages (e.g. 150 for balanced, 300 for high-res)",
    )
    parser.add_argument(
        "--page", "-p",
        type=str,
        default=None,
        help="Page index or range to process (e.g. '17' for Sheet A-104, '0,1,2', or '13-18')",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=0.20,
        help="Sliding-window overlap fraction for Hann apodization stitching (e.g. 0.20 for 20%% overlap)",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=512,
        help="Tile dimension square (512x512)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_OVERLAY_ALPHA,
        help="Alpha transparency for wall annotation overlays (0.0 to 1.0)",
    )
    parser.add_argument(
        "--annotation-method",
        type=str,
        choices=["overlay", "polygon"],
        default="overlay",
        help="Annotation mechanism: 'overlay' (translucent pixmap) or 'polygon' (vector paths)",
    )
    parser.add_argument(
        "--palette",
        type=str,
        choices=["standard", "vibrant"],
        default="standard",
        help="Color taxonomy palette ('standard' pure Green/Red/Yellow or 'vibrant' Material Design)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["overlay", "mask"],
        default="overlay",
        help="Output mode for images",
    )
    parser.add_argument(
        "--device", "-d",
        type=str,
        default=None,
        help="Execution device: 'cpu' or 'cuda' (defaults to CUDA if available else CPU)",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Optional path to write formatted summary JSON report",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode: suppress standard info logs and print only final JSON summary to stdout",
    )

    return parser


def main() -> None:
    parser = build_cli_parser()
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    pages = parse_page_arg(args.page)

    pipeline = DrywallInferencePipeline(
        checkpoint_dir=args.checkpoint,
        device=args.device,
        dpi=args.dpi,
        tile_size=args.tile_size,
        overlap=args.overlap,
        alpha=args.alpha,
        annotation_method=args.annotation_method,
        palette_name=args.palette,
    )

    summary = pipeline.process(
        input_path=args.input,
        output_path=args.output,
        pages=pages,
        mode=args.mode,
    )

    json_str = json.dumps(summary, indent=2)

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        logger.info("Saved structured summary JSON to %s", json_path)

    print(json_str)


if __name__ == "__main__":
    main()
