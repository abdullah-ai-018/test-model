"""
drywall_detection/pipeline/fusion.py

Hybrid Vector + ML Fusion Pipeline (Milestone M5).
Integrates:
  1. Modality routing (Vector-First vs Raster ML vs Hybrid)
  2. Authoritative schedule-driven vector extraction & classification
  3. Offline SegFormer-B0 ML segmentation cross-validation
  4. Multi-class material takeoff quantification (Counts, Linear Feet, Square Feet).
"""

from __future__ import annotations
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import fitz
import numpy as np
from PIL import Image
from shapely.geometry import box, MultiPolygon, Polygon
from shapely.ops import unary_union

from drywall_detection.classification.classifier import (
    ClassifiedWallPolygon,
    DrywallClassifier,
    ClassificationClass,
)
from drywall_detection.config import (
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    PACKAGE_ROOT,
)
try:
    from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer
except ImportError:
    try:
        from drywall_detection.pipeline.infer import StandaloneInferencer
    except ImportError:
        StandaloneInferencer = None  # type: ignore
from drywall_detection.pipeline.router import ModalityRouter, PipelineModality
from drywall_detection.utils.coords import AffineTransformManager
from drywall_detection.vector.extractor import VectorExtractor
from drywall_detection.vector.schedule_parser import PartitionScheduleParser


class PageInferenceResult:
    """Unified container for page-level drywall inference results."""

    def __init__(
        self,
        page_idx: int,
        sheet: str,
        modality_used: PipelineModality,
        classified_walls: List[ClassifiedWallPolygon],
        summary_stats: Dict[str, Any],
        processing_time_s: float,
        raw_mask: Optional[np.ndarray] = None,
        probability_map: Optional[np.ndarray] = None,
    ) -> None:
        self.page_idx = page_idx
        self.sheet = sheet
        self.modality_used = modality_used
        self.classified_walls = classified_walls
        self.summary_stats = summary_stats
        self.processing_time_s = processing_time_s
        self.raw_mask = raw_mask
        self.probability_map = probability_map

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_idx": self.page_idx,
            "sheet": self.sheet,
            "modality_used": self.modality_used.value if hasattr(self.modality_used, "value") else str(self.modality_used),
            "wall_count": len(self.classified_walls),
            "summary_stats": self.summary_stats,
            "processing_time_s": self.processing_time_s,
        }


class HybridFusionPipeline:
    """
    Unified end-to-end inference engine integrating Vector Extraction,
    3-Tier Spatial Matching, Schedule Rule Classification, and SegFormer-B0 ML Segmentation.
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Union[str, Path]] = None,
        schedule_csv: Optional[Union[str, Path]] = None,
        dpi: int = DEFAULT_DPI,
        device: Optional[str] = None,
    ) -> None:
        self.dpi = dpi
        self.router = ModalityRouter()
        self.classifier = DrywallClassifier(schedule_csv=schedule_csv, dpi=self.dpi)
        self.extractor = VectorExtractor(dpi=self.dpi)
        self.schedule_parser = PartitionScheduleParser()
        self.checkpoint_dir = Path(checkpoint_dir or (PACKAGE_ROOT / "checkpoints" / "best_model"))
        self._inferencer: Optional[StandaloneInferencer] = None
        self.device = device
        self.transform = AffineTransformManager(dpi=self.dpi)

    @property
    def inferencer(self) -> StandaloneInferencer:
        if self._inferencer is None:
            self._inferencer = StandaloneInferencer(checkpoint_dir=self.checkpoint_dir, device=self.device)
        return self._inferencer

    def process_page(
        self,
        page: fitz.Page,
        sheet_name: str = "",
        force_modality: Optional[PipelineModality] = None,
    ) -> PageInferenceResult:
        """
        Executes end-to-end page processing according to routed or requested modality.
        """
        t0 = time.time()
        decision = self.router.evaluate_page(page)
        modality = force_modality or decision.modality
        sheet = sheet_name or f"Page_{page.number + 1}"

        if modality == PipelineModality.VECTOR_FIRST:
            classified_walls = self._run_vector_first(page, sheet)
            raw_mask, prob_map = None, None

        elif modality == PipelineModality.RASTER_ML:
            classified_walls, raw_mask, prob_map = self._run_raster_ml(page, sheet)

        else:  # HYBRID
            classified_walls, raw_mask, prob_map = self._run_hybrid_fusion(page, sheet)

        elapsed = time.time() - t0
        summary = self.compute_summary_statistics(classified_walls)

        return PageInferenceResult(
            page_idx=page.number,
            sheet=sheet,
            modality_used=modality,
            classified_walls=classified_walls,
            summary_stats=summary,
            processing_time_s=round(elapsed, 3),
            raw_mask=raw_mask,
            probability_map=prob_map,
        )

    def _run_vector_first(self, page: fitz.Page, sheet: str) -> List[ClassifiedWallPolygon]:
        """Runs vector wall reconstruction and 3-tier spatial schedule classification."""
        wall_candidates = self.extractor.extract_wall_candidates(page)
        tag_candidates = self.schedule_parser.discover_tags(page, page_idx=page.number, sheet_name=sheet)

        classified_walls = self.classifier.classify_walls(
            walls=wall_candidates,
            tags=tag_candidates,
            page_idx=page.number,
            sheet=sheet,
        )
        return classified_walls

    def _run_raster_ml(self, page: fitz.Page, sheet: str) -> Tuple[List[ClassifiedWallPolygon], np.ndarray, np.ndarray]:
        """Renders page to RGB pixmap, runs sliding-window SegFormer-B0 inference, and vectorizes mask."""
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        mask, probs = self.inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.2)
        classified_walls = self._vectorize_ml_mask(mask, probs, page.number, sheet)
        return classified_walls, mask, probs

    def _run_hybrid_fusion(self, page: fitz.Page, sheet: str) -> Tuple[List[ClassifiedWallPolygon], np.ndarray, np.ndarray]:
        """Executes vector-first pipeline plus ML segmentation for confidence cross-validation."""
        vec_walls = self._run_vector_first(page, sheet)

        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        mask, probs = self.inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.2)
        fused_walls = self._fuse_vector_and_ml(vec_walls, mask, probs, page.number, sheet)
        return fused_walls, mask, probs

    def _fuse_vector_and_ml(
        self,
        vec_walls: List[ClassifiedWallPolygon],
        mask: np.ndarray,
        probs: np.ndarray,
        page_idx: int,
        sheet: str,
    ) -> List[ClassifiedWallPolygon]:
        """
        Fuses vector candidates with ML segmentation predictions.
        Strict invariant: Schedule authority is absolute. Detail 1A CMU veto is unconditional.
        """
        fused: List[ClassifiedWallPolygon] = []

        for w in vec_walls:
            # Rule 1: Detail 1A CMU veto is unconditional and authoritative
            if w.matched_tag == "1A":
                fused.append(w)
                continue

            # Compute ML agreement in wall pixel footprint
            poly_px = self.transform.transform_geometry_to_pixel(w.geometry_pdf)
            minx, miny, maxx, maxy = [int(v) for v in poly_px.bounds]
            minx, miny = max(0, minx), max(0, miny)
            maxx, maxy = min(mask.shape[1], maxx), min(mask.shape[0], maxy)

            submask = mask[miny:maxy, minx:maxx]
            if submask.size > 0:
                ml_drywall_ratio = float(np.mean(submask == CLASS_DRYWALL))
                ml_nondrywall_ratio = float(np.mean(submask == CLASS_NON_DRYWALL))

                if w.classification == "Drywall":
                    if ml_drywall_ratio >= 0.50:
                        w.confidence = max(w.confidence, 0.95)
                        w.metadata["ml_cross_validated"] = True
                        w.metadata["ml_drywall_agreement"] = round(ml_drywall_ratio, 3)
                    elif ml_drywall_ratio < 0.20:
                        w.metadata["ml_discrepancy"] = True
                        w.metadata["ml_drywall_agreement"] = round(ml_drywall_ratio, 3)

                elif w.classification == "Uncertain":
                    if ml_drywall_ratio >= 0.75:
                        w.metadata["ml_advisory"] = "Drywall"
                        w.metadata["ml_advisory_confidence"] = round(ml_drywall_ratio, 3)
                    elif ml_nondrywall_ratio >= 0.75:
                        w.metadata["ml_advisory"] = "Non-Drywall"
                        w.metadata["ml_advisory_confidence"] = round(ml_nondrywall_ratio, 3)

            fused.append(w)

        return fused

    def _vectorize_ml_mask(
        self,
        mask: np.ndarray,
        probs: np.ndarray,
        page_idx: int,
        sheet: str,
    ) -> List[ClassifiedWallPolygon]:
        """Converts ML segmentation mask connected components to ClassifiedWallPolygon objects."""
        walls: List[ClassifiedWallPolygon] = []
        counter = 1

        for cls_id, cls_name, col_name in [
            (CLASS_DRYWALL, "Drywall", "Drywall"),
            (CLASS_NON_DRYWALL, "Non-Drywall", "Non-Drywall"),
            (CLASS_UNCERTAIN, "Uncertain", "Uncertain"),
        ]:
            cls_mask = (mask == cls_id).astype(np.uint8)
            contours, _ = cv2.findContours(cls_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 50.0:  # Noise threshold in pixel space
                    continue

                epsilon = 0.01 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) < 3:
                    continue

                poly_pts = approx.reshape(-1, 2)
                poly_px = Polygon(poly_pts)
                if not poly_px.is_valid:
                    poly_px = poly_px.buffer(0)
                if poly_px.is_empty:
                    continue

                poly_pdf = self.transform.transform_geometry_to_pdf(poly_px)
                b = poly_pdf.bounds
                thick_pt = min(b[2] - b[0], b[3] - b[1])
                thick_in = thick_pt / 0.75  # 1/8" = 1'-0" scale

                walls.append(
                    ClassifiedWallPolygon(
                        wall_id=f"ml_wall_p{page_idx}_{counter:04d}",
                        page_idx=page_idx,
                        sheet=sheet,
                        geometry_pdf=poly_pdf,
                        geometry_pixel=poly_px,
                        matched_tag=None,
                        detail_number=None,
                        material_description=f"Raster ML predicted {cls_name} assembly",
                        classification=cls_name,
                        confidence=0.80,
                        color_hex=CLASS_COLORS_HEX[col_name],
                        reason=f"SegFormer-B0 sliding-window segmentation component (area={area:.0f} px)",
                        thickness_pt=thick_pt,
                        estimated_thickness_in=thick_in,
                        orientation="HORIZONTAL" if (b[2] - b[0]) >= (b[3] - b[1]) else "VERTICAL",
                        match_method="raster_ml",
                        distance_pt=0.0,
                    )
                )
                counter += 1

        return walls

    def compute_summary_statistics(self, walls: List[ClassifiedWallPolygon]) -> Dict[str, Any]:
        """Calculates total counts, linear feet (LF), and square footage (SqFt) per class."""
        summary = {
            "total_walls": len(walls),
            "drywall_count": 0,
            "nondrywall_count": 0,
            "uncertain_count": 0,
            "drywall_lf": 0.0,
            "nondrywall_lf": 0.0,
            "uncertain_lf": 0.0,
            "drywall_sqft": 0.0,
            "nondrywall_sqft": 0.0,
            "uncertain_sqft": 0.0,
        }
        for w in walls:
            lf = 0.0
            sqft = 0.0
            if w.geometry_pdf is not None and not w.geometry_pdf.is_empty:
                b = w.geometry_pdf.bounds
                length_pt = max(b[2] - b[0], b[3] - b[1])
                lf = length_pt / 9.0  # 1/8" = 1'-0" scale (9 pt = 1 foot)
                sqft = w.geometry_pdf.area / 81.0

            if w.classification == "Drywall":
                summary["drywall_count"] += 1
                summary["drywall_lf"] += lf
                summary["drywall_sqft"] += sqft
            elif w.classification == "Non-Drywall":
                summary["nondrywall_count"] += 1
                summary["nondrywall_lf"] += lf
                summary["nondrywall_sqft"] += sqft
            else:
                summary["uncertain_count"] += 1
                summary["uncertain_lf"] += lf
                summary["uncertain_sqft"] += sqft

        for k in ["drywall_lf", "nondrywall_lf", "uncertain_lf", "drywall_sqft", "nondrywall_sqft", "uncertain_sqft"]:
            summary[k] = round(summary[k], 1)
        return summary
