"""
drywall_detection.pipeline
==========================
Inference and Annotation Pipeline for Architectural Drawings.
"""

from drywall_detection.pipeline.annotate import (
    PALETTE_STANDARD,
    PALETTE_VIBRANT,
    PDFAnnotator,
    compute_mask_metrics,
    mask_to_rgba_overlay,
    render_blended_image,
)
from drywall_detection.pipeline.infer import (
    DrywallInferencePipeline,
    build_cli_parser,
    parse_page_arg,
)

__all__ = [
    "PALETTE_STANDARD",
    "PALETTE_VIBRANT",
    "PDFAnnotator",
    "compute_mask_metrics",
    "mask_to_rgba_overlay",
    "render_blended_image",
    "DrywallInferencePipeline",
    "build_cli_parser",
    "parse_page_arg",
]
