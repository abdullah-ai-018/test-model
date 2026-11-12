"""
drywall_detection.data.qc
========================
Visual Quality Control (QC) module for architectural floor plan datasets.
Generates horizontal inspection triplets: [Original Drawing | Color Mask | Translucent Overlay]
and writes artifacts to drywall_detection/reports/qc_samples/.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_BGR,
    DEFAULT_OVERLAY_ALPHA,
    REPORTS_DIR,
    QC_SAMPLES_DIR,
)

logger = logging.getLogger(__name__)


@dataclass
class QCInspectionRecord:
    """Diagnostic audit record for a single QC sample."""
    sample_id: str
    project_id: str
    split_name: str
    image_path: str
    mask_path: str
    qc_image_path: str
    height: int
    width: int
    drywall_pct: float
    non_drywall_pct: float
    uncertain_pct: float
    status: str  # WALL_SAMPLE, HARD_NEGATIVE, EMPTY, CORRUPT
    error_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisualQCGenerator:
    """
    Renders visual Quality Control sample triplets with header diagnostic banners.
    """

    def __init__(self, alpha: float = DEFAULT_OVERLAY_ALPHA) -> None:
        self.alpha = float(alpha)

    def render_color_mask(self, mask: np.ndarray) -> np.ndarray:
        """Converts (H, W) uint8 mask into (H, W, 3) BGR color image."""
        h, w = mask.shape[:2]
        vis = np.full((h, w, 3), 255, dtype=np.uint8)  # Default white background

        for cls_val in (CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN):
            m = (mask == cls_val)
            if np.any(m):
                vis[m] = CLASS_COLORS_BGR[cls_val]
        return vis

    def render_overlay(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Blends color mask onto drawing linework at specified alpha."""
        h, w = mask.shape[:2]
        if image_bgr.shape[:2] != (h, w):
            image_bgr = cv2.resize(image_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

        overlay = image_bgr.copy()
        for cls_val in (CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN):
            m = (mask == cls_val)
            if np.any(m):
                color_layer = np.zeros_like(image_bgr)
                color_layer[m] = CLASS_COLORS_BGR[cls_val]
                blended = cv2.addWeighted(image_bgr, 1.0 - self.alpha, color_layer, self.alpha, 0)
                overlay[m] = blended[m]
        return overlay

    def create_triplet(
        self,
        image_bgr: np.ndarray,
        mask: np.ndarray,
        meta: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        Creates composite: [Original Drawing | Color Mask | Translucent Overlay]
        with diagnostic header banner.
        """
        h, w = mask.shape[:2]
        if image_bgr.shape[:2] != (h, w):
            image_bgr = cv2.resize(image_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

        color_mask = self.render_color_mask(mask)
        overlay = self.render_overlay(image_bgr, mask)

        # Horizontally stack panels
        triplet = np.hstack([image_bgr, color_mask, overlay])
        trip_h, trip_w, _ = triplet.shape

        # Render top diagnostic banner (40 px height)
        banner_h = 40
        banner = np.full((banner_h, trip_w, 3), 34, dtype=np.uint8)  # Charcoal #222222

        if meta:
            sample_id = meta.get("sample_id", "sample")
            proj_id = meta.get("project_id", "project")
            split = str(meta.get("split_name", "train")).upper()
            dw_pct = float(meta.get("drywall_pct", 0.0))
            non_dw_pct = float(meta.get("non_drywall_pct", 0.0))
            unc_pct = float(meta.get("uncertain_pct", 0.0))
            status = meta.get("status", "VALID")

            line1 = f"ID: {sample_id} | PROJ: {proj_id} | SPLIT: {split} | STATUS: {status}"
            line2 = f"DW: {dw_pct:.1f}% | NON-DW: {non_dw_pct:.1f}% | UNC: {unc_pct:.1f}% | ALPHA: {self.alpha:.2f}"

            cv2.putText(banner, line1, (16, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(banner, line2, (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 220, 255), 1, cv2.LINE_AA)

        return np.vstack([banner, triplet])


class VisualQCPipeline:
    """
    Automates sampling from split manifests and generates QC sample triplets.
    """

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        alpha: float = DEFAULT_OVERLAY_ALPHA,
    ) -> None:
        self.output_dir = Path(output_dir or (REPORTS_DIR / "qc_samples")).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = VisualQCGenerator(alpha=alpha)

    def generate_qc_for_sample(
        self,
        image_path: Union[str, Path],
        mask_path: Union[str, Path],
        sample_meta: Dict[str, Any],
    ) -> QCInspectionRecord:
        """Processes a single image/mask pair into a saved QC triplet image."""
        img_p = Path(image_path)
        msk_p = Path(mask_path)

        if not img_p.is_file():
            raise FileNotFoundError(f"Image not found: {img_p}")
        if not msk_p.is_file():
            raise FileNotFoundError(f"Mask not found: {msk_p}")

        image_bgr = cv2.imread(str(img_p))
        if image_bgr is None:
            raise IOError(f"Failed to read image at {img_p}")

        # Mask loading as uint8
        with Image.open(msk_p) as m_pil:
            mask = np.array(m_pil, dtype=np.uint8)
        if mask.ndim == 3:
            mask = mask[:, :, 0]

        h, w = mask.shape[:2]
        tot = max(h * w, 1)
        dw_cnt = int(np.sum(mask == CLASS_DRYWALL))
        non_dw_cnt = int(np.sum(mask == CLASS_NON_DRYWALL))
        unc_cnt = int(np.sum(mask == CLASS_UNCERTAIN))
        has_walls = (dw_cnt + non_dw_cnt + unc_cnt) > 0

        # Heuristic determination of status
        std_val = float(np.std(image_bgr))
        if has_walls:
            status = "WALL_SAMPLE"
        elif std_val > 5.0:
            status = "HARD_NEGATIVE"
        else:
            status = "EMPTY"

        meta_dict = {
            "sample_id": sample_meta.get("sample_id") or sample_meta.get("tile_id") or img_p.stem,
            "project_id": sample_meta.get("project_id", "unknown"),
            "split_name": sample_meta.get("split_name", "train"),
            "drywall_pct": (dw_cnt / tot) * 100.0,
            "non_drywall_pct": (non_dw_cnt / tot) * 100.0,
            "uncertain_pct": (unc_cnt / tot) * 100.0,
            "status": status,
        }

        triplet = self.generator.create_triplet(image_bgr, mask, meta_dict)

        clean_sample_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in str(meta_dict["sample_id"]))
        clean_proj_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in str(meta_dict["project_id"]))
        out_name = f"qc_{meta_dict['split_name']}_{clean_proj_id}_{clean_sample_id}.png"
        out_path = self.output_dir / out_name
        cv2.imwrite(str(out_path), triplet)

        return QCInspectionRecord(
            sample_id=meta_dict["sample_id"],
            project_id=meta_dict["project_id"],
            split_name=meta_dict["split_name"],
            image_path=str(img_p),
            mask_path=str(msk_p),
            qc_image_path=str(out_path),
            height=h,
            width=w,
            drywall_pct=round(meta_dict["drywall_pct"], 3),
            non_drywall_pct=round(meta_dict["non_drywall_pct"], 3),
            uncertain_pct=round(meta_dict["uncertain_pct"], 3),
            status=status,
        )

    def run_qc_on_splits(
        self,
        splits_dir: Union[str, Path],
        samples_per_split: int = 5,
    ) -> List[QCInspectionRecord]:
        """Runs stratified QC generation across all split manifests."""
        splits_path = Path(splits_dir)
        records: List[QCInspectionRecord] = []

        for split_name in ["train", "val", "test", "quarantine"]:
            s_file = splits_path / f"{split_name}.json"
            if not s_file.is_file():
                continue

            with open(s_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                samples = data
            else:
                samples = data.get("samples") or data.get("tiles") or data.get("drawings") or []
            if not samples:
                continue

            # Stratify: select samples with walls first, then hard negatives
            wall_samples = [s for s in samples if s.get("has_walls", True)]
            empty_samples = [s for s in samples if not s.get("has_walls", True)]

            selected = []
            if wall_samples:
                n_walls = min(len(wall_samples), int(samples_per_split * 0.8) or 1)
                selected.extend(wall_samples[:n_walls])
            if empty_samples:
                n_empty = min(len(empty_samples), samples_per_split - len(selected))
                selected.extend(empty_samples[:n_empty])

            # Fill remainder if still short
            if len(selected) < samples_per_split and len(samples) > len(selected):
                remainder = [s for s in samples if s not in selected]
                selected.extend(remainder[:samples_per_split - len(selected)])

            for s_info in selected:
                s_info["split_name"] = split_name
                try:
                    rec = self.generate_qc_for_sample(
                        image_path=s_info["image_path"],
                        mask_path=s_info["mask_path"],
                        sample_meta=s_info,
                    )
                    records.append(rec)
                except Exception as e:
                    logger.warning(f"QC generation failed for {s_info.get('sample_id')}: {e}")

        # Export QC manifest index
        manifest_file = self.output_dir / "qc_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records], f, indent=2)

        return records


def main(args: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Drywall Detection Visual Quality Control Generator")
    parser.add_argument("--splits-dir", type=str, default="drywall_detection/data/splits", help="Directory containing split JSON manifests")
    parser.add_argument("--output", type=str, default="drywall_detection/reports/qc_samples", help="Output directory for QC images")
    parser.add_argument("--samples-per-split", type=int, default=5, help="Number of representative samples per split")
    parser.add_argument("--alpha", type=float, default=0.40, help="Translucent overlay alpha blending factor")
    parsed = parser.parse_args(args)

    pipeline = VisualQCPipeline(output_dir=parsed.output, alpha=parsed.alpha)
    records = pipeline.run_qc_on_splits(parsed.splits_dir, samples_per_split=parsed.samples_per_split)
    print(f"Generated {len(records)} visual QC sample triplets in {parsed.output}")
    return 0


__all__ = [
    "QCInspectionRecord",
    "VisualQCGenerator",
    "VisualQCPipeline",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
