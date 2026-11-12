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

# Optional extensions if available
try:
    from drywall_detection.pipeline.annotate import VisualOverlayConfig, WallAnnotator  # type: ignore
    __all__.extend(["VisualOverlayConfig", "WallAnnotator"])
except (ImportError, AttributeError):
    pass

try:
    from drywall_detection.pipeline.router import (  # type: ignore
        ModalityRouter,
        PipelineModality,
        PageModalityDecision,
    )
    __all__.extend(["ModalityRouter", "PipelineModality", "PageModalityDecision"])
except (ImportError, AttributeError):
    pass

try:
    from drywall_detection.pipeline.fusion import (  # type: ignore
        HybridFusionPipeline,
        PageInferenceResult,
    )
    __all__.extend(["HybridFusionPipeline", "PageInferenceResult"])
except (ImportError, AttributeError):
    pass
