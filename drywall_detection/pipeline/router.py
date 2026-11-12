"""
drywall_detection/pipeline/router.py

Modality Router for Architectural Drawings.
Inspects incoming PDF pages and dynamically routes processing to the optimal track:
  - VECTOR_FIRST: High-speed, high-precision CAD vector line extraction and schedule classification.
  - RASTER_ML: Deep learning (SegFormer-B0) segmentation for scanned blueprints / pure raster pages.
  - HYBRID: Mixed vector and raster fusion for complex, partially annotated drawings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import fitz


class PipelineModality(str, Enum):
    VECTOR_FIRST = "VECTOR_FIRST"
    RASTER_ML = "RASTER_ML"
    HYBRID = "HYBRID"


@dataclass
class PageModalityDecision:
    page_number: int
    modality: PipelineModality
    confidence: float
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class ModalityRouter:
    """
    Inspects PDF pages and dynamically routes processing to the optimal pipeline track.
    """

    def __init__(
        self,
        min_vector_paths: int = 100,
        max_image_coverage_vector: float = 0.50,
        min_text_words_vector: int = 20,
        scanned_path_ceiling: int = 50,
        scanned_image_coverage_floor: float = 0.70,
    ) -> None:
        self.min_vector_paths = min_vector_paths
        self.max_image_coverage_vector = max_image_coverage_vector
        self.min_text_words_vector = min_text_words_vector
        self.scanned_path_ceiling = scanned_path_ceiling
        self.scanned_image_coverage_floor = scanned_image_coverage_floor

    def evaluate_page(self, page: fitz.Page) -> PageModalityDecision:
        drawings = page.get_drawings() or []
        path_count = len(drawings)
        words = page.get_text("words") or []
        word_count = len(words)
        images = page.get_images() or []

        page_area = max(page.rect.width * page.rect.height, 1.0)
        image_coverage = 0.0
        if hasattr(page, "get_image_rects"):
            for img in images:
                try:
                    for r in page.get_image_rects(img[0]):
                        image_coverage += (r.width * r.height) / page_area
                except Exception:
                    pass

        reasons: List[str] = []
        metrics = {
            "path_count": path_count,
            "word_count": word_count,
            "image_count": len(images),
            "image_coverage": round(image_coverage, 4),
        }

        # Check pure scanned raster condition
        if path_count < self.scanned_path_ceiling and (image_coverage >= self.scanned_image_coverage_floor or word_count == 0):
            modality = PipelineModality.RASTER_ML
            reasons.append(f"Scanned page profile: low path count ({path_count}) and high image coverage ({image_coverage:.2%})")
            confidence = 0.98

        # Check pure CAD vector condition
        elif path_count >= self.min_vector_paths and image_coverage < self.max_image_coverage_vector and word_count >= self.min_text_words_vector:
            modality = PipelineModality.VECTOR_FIRST
            reasons.append(f"Pure vector CAD profile: {path_count} paths, {word_count} text words, low image coverage ({image_coverage:.2%})")
            confidence = 0.95

        # Hybrid fallback condition
        else:
            modality = PipelineModality.HYBRID
            reasons.append("Mixed vector and raster content detected; hybrid fusion recommended")
            confidence = 0.85

        return PageModalityDecision(
            page_number=page.number,
            modality=modality,
            confidence=confidence,
            reasons=reasons,
            metrics=metrics,
        )
