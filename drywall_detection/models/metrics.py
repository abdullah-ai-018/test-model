"""
drywall_detection.models.metrics
================================
Evaluation metrics suite for multi-class architectural floor plan segmentation.

Implements:
- SegmentationMetricTracker: Evaluates mIoU, Foreground Wall IoU, per-class metrics,
  boundary IoU, and normalized confusion matrices.
- SegmentationMetrics: Streaming 4x4 confusion matrix and boundary accumulator.
- compute_boundary_iou: Cheng et al. (CVPR 2021) Boundary IoU at distances d=2 and d=4.
- compute_tensor_boundary_mask: MaxPool2d morphological erosion.
- assert_zero_leakage_manifests: Pre-evaluation runtime zero-leakage assertion gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F

from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_NAMES,
    NUM_CLASSES,
)

DEFAULT_CLASS_NAMES = ["Background", "Drywall", "Non-Drywall", "Uncertain"]


@dataclass
class ClassMetricResult:
    class_id: int
    class_name: str
    tp: int
    fp: int
    fn: int
    tn: int
    iou: float
    dice: float
    precision: float
    recall: float
    specificity: float
    boundary_iou_d2: float
    boundary_iou_d4: float


@dataclass
class SegmentationEvaluationReport:
    num_classes: int
    total_pixels: int
    global_accuracy: float
    miou_all_classes: float
    foreground_wall_iou: float
    mean_dice: float
    mean_precision: float
    mean_recall: float
    mean_boundary_iou_d2: float
    mean_boundary_iou_d4: float
    per_class_metrics: Dict[str, ClassMetricResult]
    confusion_matrix_raw: List[List[int]]
    confusion_matrix_row_norm: List[List[float]]
    confusion_matrix_col_norm: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def compute_tensor_boundary_mask(mask: torch.Tensor, d: int = 2) -> torch.Tensor:
    """
    Computes boundary mask of distance d using 2D MaxPool on inverted binary mask.
    Args:
        mask: [B, 1, H, W] or [B, H, W] binary tensor (0.0 or 1.0).
        d: Dilation/erosion distance in pixels.
    """
    if d <= 0:
        return mask
    if mask.ndim == 3:
        mask = mask.unsqueeze(1)
    elif mask.ndim == 2:
        mask = mask.unsqueeze(0).unsqueeze(0)
    inv = 1.0 - mask.float()
    eroded = 1.0 - F.max_pool2d(inv, kernel_size=2 * d + 1, stride=1, padding=d)
    boundary = (mask.float() - eroded).clamp(min=0.0)
    return boundary


def compute_boundary_iou(
    gt_binary: torch.Tensor,
    pred_binary: torch.Tensor,
    d: int = 2,
    eps: float = 1e-6,
    num_classes: Optional[int] = None,
    **kwargs: Any,
) -> Union[float, torch.Tensor]:
    """
    Computes Boundary IoU (Cheng et al., CVPR 2021).
    When num_classes is provided, returns 1D Tensor of per-class Boundary IoU scores.
    """
    if num_classes is not None:
        b_ious = []
        for c in range(num_classes):
            gt_c = (gt_binary == c).float()
            pred_c = (pred_binary == c).float()
            b_gt = compute_tensor_boundary_mask(gt_c, d=d)
            b_pred = compute_tensor_boundary_mask(pred_c, d=d)
            inter = (b_gt * b_pred).sum().item()
            union = ((b_gt + b_pred) > 0).float().sum().item()
            if union == 0:
                val = 1.0 if inter == 0 else 0.0
            else:
                val = float((inter + eps) / (union + eps))
            b_ious.append(val)
        return torch.tensor(b_ious, dtype=torch.float32)

    gt_t = (gt_binary > 0).float() if gt_binary.dtype in (torch.int64, torch.int32, torch.uint8) else gt_binary.float()
    pred_t = (pred_binary > 0).float() if pred_binary.dtype in (torch.int64, torch.int32, torch.uint8) else pred_binary.float()

    b_gt = compute_tensor_boundary_mask(gt_t, d=d)
    b_pred = compute_tensor_boundary_mask(pred_t, d=d)

    inter = (b_gt * b_pred).sum().item()
    union = ((b_gt + b_pred) > 0).float().sum().item()

    if union == 0:
        return 1.0 if inter == 0 else 0.0
    return float((inter + eps) / (union + eps))


class SegmentationMetricTracker:
    """
    Accumulates predictions across validation batches and computes full evaluation suite:
    - Overall mIoU across all classes
    - Foreground Wall IoU (classes 1, 2, 3 omitting background class 0)
    - Per-class IoU, Dice/F1, Precision, Recall, Specificity
    - Boundary IoU at d=2 and d=4 pixels
    - Confusion Matrix (raw, row-normalized recall, col-normalized precision)
    """

    def __init__(
        self,
        num_classes: int = NUM_CLASSES,
        class_names: Optional[Dict[int, str]] = None,
    ) -> None:
        self.num_classes = num_classes
        if class_names is not None:
            self.class_names = class_names
        else:
            self.class_names = dict(CLASS_NAMES)

        self.confusion_matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
        self.boundary_iou_sums_d2 = np.zeros(num_classes, dtype=np.float64)
        self.boundary_iou_sums_d4 = np.zeros(num_classes, dtype=np.float64)
        self.sample_counts = 0

    def reset(self) -> None:
        self.confusion_matrix.fill(0)
        self.boundary_iou_sums_d2.fill(0.0)
        self.boundary_iou_sums_d4.fill(0.0)
        self.sample_counts = 0

    @torch.no_grad()
    def update(
        self,
        pred_logits_or_labels: Union[torch.Tensor, np.ndarray],
        targets: Union[torch.Tensor, np.ndarray],
    ) -> None:
        """
        Args:
            pred_logits_or_labels: [B, C, H, W] logits OR [B, H, W] labels.
            targets: [B, H, W] ground truth class labels.
        """
        if isinstance(pred_logits_or_labels, np.ndarray):
            preds_t = torch.from_numpy(pred_logits_or_labels)
        else:
            preds_t = pred_logits_or_labels

        if isinstance(targets, np.ndarray):
            targets_t = torch.from_numpy(targets)
        else:
            targets_t = targets

        if preds_t.ndim == 4:
            preds = torch.argmax(preds_t, dim=1)
        elif preds_t.ndim == 2:
            preds = preds_t.unsqueeze(0)
        else:
            preds = preds_t

        if targets_t.ndim == 2:
            targets_t = targets_t.unsqueeze(0)

        preds_cpu = preds.long().cpu()
        targets_cpu = targets_t.long().cpu()

        p_flat = preds_cpu.flatten().numpy()
        t_flat = targets_cpu.flatten().numpy()

        # Update confusion matrix
        mask = (t_flat >= 0) & (t_flat < self.num_classes) & (p_flat >= 0) & (p_flat < self.num_classes)
        hist = np.bincount(
            self.num_classes * t_flat[mask] + p_flat[mask],
            minlength=self.num_classes ** 2,
        ).reshape(self.num_classes, self.num_classes)
        self.confusion_matrix += hist

        # Accumulate Boundary IoU per batch item
        b_size = preds_cpu.shape[0]
        self.sample_counts += b_size
        preds_bin = preds_cpu.unsqueeze(1).float()
        targets_bin = targets_cpu.unsqueeze(1).float()

        for c in range(self.num_classes):
            p_c = (preds_bin == c).float()
            t_c = (targets_bin == c).float()
            b2 = compute_boundary_iou(t_c, p_c, d=2)
            b4 = compute_boundary_iou(t_c, p_c, d=4)
            self.boundary_iou_sums_d2[c] += b2 * b_size
            self.boundary_iou_sums_d4[c] += b4 * b_size

    def compute_report(self) -> SegmentationEvaluationReport:
        """Alias for compute()."""
        return self.compute()

    def compute(self) -> SegmentationEvaluationReport:
        cm = self.confusion_matrix
        tot_pix = int(cm.sum())
        diag = np.diag(cm)

        glob_acc = float(diag.sum() / tot_pix) if tot_pix > 0 else 0.0

        row_sums = cm.sum(axis=1, keepdims=True)
        col_sums = cm.sum(axis=0, keepdims=True)

        cm_row_norm = np.divide(cm.astype(float), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums > 0)
        cm_col_norm = np.divide(cm.astype(float), col_sums, out=np.zeros_like(cm, dtype=float), where=col_sums > 0)

        per_class: Dict[str, ClassMetricResult] = {}
        ious = []
        dices = []
        precisions = []
        recalls = []
        b_ious_d2 = []
        b_ious_d4 = []

        n_samples = max(self.sample_counts, 1)

        for c in range(self.num_classes):
            cname = self.class_names.get(c, f"Class_{c}")
            tp = int(cm[c, c])
            fp = int(cm[:, c].sum() - tp)
            fn = int(cm[c, :].sum() - tp)
            tn = int(tot_pix - tp - fp - fn)

            denom_iou = tp + fp + fn
            iou = float(tp / denom_iou) if denom_iou > 0 else (1.0 if (tp + fp + fn == 0) else 0.0)

            denom_dice = 2 * tp + fp + fn
            dice = float((2.0 * tp) / denom_dice) if denom_dice > 0 else (1.0 if (tp + fp + fn == 0) else 0.0)

            prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

            mean_b2 = float(self.boundary_iou_sums_d2[c] / n_samples)
            mean_b4 = float(self.boundary_iou_sums_d4[c] / n_samples)

            ious.append(iou)
            dices.append(dice)
            precisions.append(prec)
            recalls.append(rec)
            b_ious_d2.append(mean_b2)
            b_ious_d4.append(mean_b4)

            per_class[cname] = ClassMetricResult(
                class_id=c,
                class_name=cname,
                tp=tp,
                fp=fp,
                fn=fn,
                tn=tn,
                iou=iou,
                dice=dice,
                precision=prec,
                recall=rec,
                specificity=spec,
                boundary_iou_d2=mean_b2,
                boundary_iou_d4=mean_b4,
            )

        miou_all = float(np.mean(ious))
        # Foreground Wall IoU: Average over foreground classes (c >= 1) present in ground truth
        fg_present_ious = [
            ious[c] for c in range(1, self.num_classes)
            if int(cm[c, :].sum()) > 0
        ]
        if fg_present_ious:
            fg_wall_iou = float(np.mean(fg_present_ious))
        else:
            # If no foreground classes in ground truth, check for false positive predictions
            fg_pred_ious = [
                ious[c] for c in range(1, self.num_classes)
                if int(cm[:, c].sum()) > 0
            ]
            fg_wall_iou = float(np.mean(fg_pred_ious)) if fg_pred_ious else 0.0

        return SegmentationEvaluationReport(
            num_classes=self.num_classes,
            total_pixels=tot_pix,
            global_accuracy=glob_acc,
            miou_all_classes=miou_all,
            foreground_wall_iou=fg_wall_iou,
            mean_dice=float(np.mean(dices)),
            mean_precision=float(np.mean(precisions)),
            mean_recall=float(np.mean(recalls)),
            mean_boundary_iou_d2=float(np.mean(b_ious_d2)),
            mean_boundary_iou_d4=float(np.mean(b_ious_d4)),
            per_class_metrics=per_class,
            confusion_matrix_raw=cm.tolist(),
            confusion_matrix_row_norm=np.round(cm_row_norm, 4).tolist(),
            confusion_matrix_col_norm=np.round(cm_col_norm, 4).tolist(),
        )


def assert_zero_leakage_manifests(
    train_manifest_path: Union[str, Path],
    val_manifest_path: Union[str, Path],
    test_manifest_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Runtime verification ensuring zero project, drawing, or file path overlap
    between train, validation, and test splits before evaluation.
    Also asserts strict exclusion of quarantined or pseudo-labeled samples from val/test.
    """
    with open(train_manifest_path, "r", encoding="utf-8") as f:
        t_data = json.load(f)
    with open(val_manifest_path, "r", encoding="utf-8") as f:
        v_data = json.load(f)

    t_tiles = t_data.get("tiles") or t_data.get("samples") or []
    v_tiles = v_data.get("tiles") or v_data.get("samples") or []

    t_projs = {t.get("project_id") for t in t_tiles if t.get("project_id")}
    v_projs = {v.get("project_id") for v in v_tiles if v.get("project_id")}

    overlap_projs = t_projs & v_projs
    if overlap_projs:
        raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between train and val: {overlap_projs}")

    t_draws = {t.get("drawing_id") for t in t_tiles if t.get("drawing_id")}
    v_draws = {v.get("drawing_id") for v in v_tiles if v.get("drawing_id")}

    overlap_draws = t_draws & v_draws
    if overlap_draws:
        raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Drawings leaked between train and val: {overlap_draws}")

    t_imgs = {t.get("image_path") or t.get("tile_path") for t in t_tiles if t.get("image_path") or t.get("tile_path")}
    v_imgs = {v.get("image_path") or v.get("tile_path") for v in v_tiles if v.get("image_path") or v.get("tile_path")}
    if t_imgs & v_imgs:
        raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Image paths leaked between train and val: {t_imgs & v_imgs}")

    if test_manifest_path is not None:
        with open(test_manifest_path, "r", encoding="utf-8") as f:
            te_data = json.load(f)
        te_tiles = te_data.get("tiles") or te_data.get("samples") or []
        te_projs = {t.get("project_id") for t in te_tiles if t.get("project_id")}
        if t_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between train and test: {t_projs & te_projs}")
        if v_projs & te_projs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Projects leaked between val and test: {v_projs & te_projs}")

        te_draws = {t.get("drawing_id") for t in te_tiles if t.get("drawing_id")}
        if t_draws & te_draws:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Drawings leaked between train and test: {t_draws & te_draws}")
        if v_draws & te_draws:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Drawings leaked between val and test: {v_draws & te_draws}")

        te_imgs = {t.get("image_path") or t.get("tile_path") for t in te_tiles if t.get("image_path") or t.get("tile_path")}
        if t_imgs & te_imgs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Image paths leaked between train and test: {t_imgs & te_imgs}")
        if v_imgs & te_imgs:
            raise RuntimeError(f"[DATA LEAKAGE VIOLATION] Image paths leaked between val and test: {v_imgs & te_imgs}")
    else:
        te_tiles = []

    for name, tiles in [("validation", v_tiles), ("test", te_tiles)]:
        for t in tiles:
            if t.get("quarantine", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Quarantined sample {t.get('sample_id')} found in {name} split!")
            if t.get("is_pseudo_label", False):
                raise RuntimeError(f"[QUARANTINE LEAKAGE] Pseudo-labeled sample {t.get('sample_id')} found in {name} split!")


class SegmentationMetrics:
    """
    Streaming multi-class segmentation metric accumulator.

    Memory-efficient O(1) space complexity tracking a 4x4 integer confusion matrix
    and boundary intersection/union counters across batches.
    Maintained for backward compatibility.
    """

    def __init__(
        self,
        num_classes: int = 4,
        class_names: Optional[List[str]] = None,
        boundary_radius: int = 2,
    ) -> None:
        self.num_classes = num_classes
        self.class_names = list(class_names) if class_names is not None else list(DEFAULT_CLASS_NAMES)
        if len(self.class_names) != self.num_classes:
            raise ValueError(
                f"Length of class_names ({len(self.class_names)}) must equal num_classes ({self.num_classes})"
            )
        self.boundary_radius = boundary_radius
        self.reset()

    def reset(self) -> None:
        """Resets all streaming counters to zero."""
        self.conf_matrix = np.zeros((self.num_classes, self.num_classes), dtype=np.int64)
        self.boundary_inter = np.zeros(self.num_classes, dtype=np.int64)
        self.boundary_union = np.zeros(self.num_classes, dtype=np.int64)

    def _extract_boundaries(self, mask_tensor: torch.Tensor) -> torch.Tensor:
        """
        Extracts 1-pixel boundary masks using native PyTorch morphological erosion via MaxPool.
        """
        B, H, W = mask_tensor.shape
        r = self.boundary_radius
        k = 2 * r + 1
        boundaries = torch.zeros(
            (B, self.num_classes, H, W),
            dtype=torch.float32,
            device=mask_tensor.device,
        )
        for c in range(self.num_classes):
            c_mask = (mask_tensor == c).float().unsqueeze(1)
            eroded = 1.0 - F.max_pool2d(1.0 - c_mask, kernel_size=k, stride=1, padding=r)
            boundaries[:, c, :, :] = (c_mask - eroded).squeeze(1)
        return boundaries

    def update(
        self,
        preds: Union[torch.Tensor, np.ndarray],
        targets: Union[torch.Tensor, np.ndarray],
    ) -> None:
        """
        Updates streaming accumulators with predictions and ground truth from a batch.
        """
        if isinstance(preds, np.ndarray):
            preds_t = torch.from_numpy(preds)
        else:
            preds_t = preds

        if isinstance(targets, np.ndarray):
            targets_t = torch.from_numpy(targets)
        else:
            targets_t = targets

        if preds_t.ndim == 4:
            preds_t = torch.argmax(preds_t, dim=1)
        elif preds_t.ndim == 2:
            preds_t = preds_t.unsqueeze(0)

        if targets_t.ndim == 2:
            targets_t = targets_t.unsqueeze(0)

        preds_cpu = preds_t.long().cpu()
        targets_cpu = targets_t.long().cpu()

        if preds_cpu.shape != targets_cpu.shape:
            raise ValueError(
                f"Shape mismatch: preds {preds_cpu.shape} vs targets {targets_cpu.shape}"
            )

        p_flat = preds_cpu.view(-1).numpy()
        t_flat = targets_cpu.view(-1).numpy()
        valid = (
            (t_flat >= 0)
            & (t_flat < self.num_classes)
            & (p_flat >= 0)
            & (p_flat < self.num_classes)
        )
        bins = self.num_classes * t_flat[valid] + p_flat[valid]
        counts = np.bincount(bins, minlength=self.num_classes**2)
        self.conf_matrix += counts.reshape((self.num_classes, self.num_classes))

        b_preds = self._extract_boundaries(preds_cpu)
        b_targets = self._extract_boundaries(targets_cpu)
        for c in range(self.num_classes):
            bp_c = b_preds[:, c, :, :] > 0.5
            bt_c = b_targets[:, c, :, :] > 0.5
            inter = int(torch.logical_and(bp_c, bt_c).sum().item())
            union = int(torch.logical_or(bp_c, bt_c).sum().item())
            self.boundary_inter[c] += inter
            self.boundary_union[c] += union

    def get_per_class_metrics(self) -> Dict[Any, Any]:
        """Returns per-class metric breakdown dictionary with int and str keys."""
        metrics_dict = self.compute().get("per_class", {})
        result: Dict[Any, Any] = dict(metrics_dict)
        for idx, name in enumerate(self.class_names):
            if name in metrics_dict:
                result[idx] = metrics_dict[name]
        return result

    def compute(self) -> Dict[str, Any]:
        """
        Computes all metrics from accumulated confusion matrix and boundary counters.
        """
        cm = self.conf_matrix
        num_classes = self.num_classes
        total_pixels = int(cm.sum())
        tp = np.diag(cm)
        gt_pixels = cm.sum(axis=1)
        pred_pixels = cm.sum(axis=0)

        per_class: Dict[str, Dict[str, Any]] = {}
        ious_all: List[float] = []
        ious_present: List[float] = []

        for c in range(num_classes):
            name = self.class_names[c]
            c_tp = float(tp[c])
            c_gt = float(gt_pixels[c])
            c_pred = float(pred_pixels[c])
            c_fn = c_gt - c_tp
            c_fp = c_pred - c_tp

            denom_iou = c_tp + c_fp + c_fn
            if denom_iou == 0:
                iou = 1.0
                iou_present = None
            else:
                iou = c_tp / denom_iou
                iou_present = iou

            denom_dice = 2.0 * c_tp + c_fp + c_fn
            dice = (2.0 * c_tp / denom_dice) if denom_dice > 0 else (1.0 if c_gt == 0 and c_pred == 0 else 0.0)
            prec = (c_tp / c_pred) if c_pred > 0 else (1.0 if c_gt == 0 else 0.0)
            rec = (c_tp / c_gt) if c_gt > 0 else (1.0 if c_pred == 0 else 0.0)

            b_union = self.boundary_union[c]
            b_inter = self.boundary_inter[c]
            b_iou = (float(b_inter) / float(b_union)) if b_union > 0 else (1.0 if c_gt == 0 and c_pred == 0 else 0.0)

            per_class[name] = {
                "iou": round(float(iou), 4),
                "dice": round(float(dice), 4),
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "boundary_iou": round(float(b_iou), 4),
                "gt_pixels": int(c_gt),
                "pred_pixels": int(c_pred),
                "present_in_gt": bool(c_gt > 0),
            }
            ious_all.append(float(iou))
            if iou_present is not None:
                ious_present.append(float(iou_present))

        pixel_acc = float(tp.sum()) / max(float(total_pixels), 1e-7)
        present_recalls = [
            per_class[name]["recall"]
            for name in self.class_names
            if per_class[name]["present_in_gt"]
        ]
        mean_acc = float(np.mean(present_recalls)) if present_recalls else 0.0

        wall_classes = [self.class_names[c] for c in range(1, num_classes)]
        wall_ious_present = [
            per_class[c]["iou"]
            for c in wall_classes
            if per_class[c]["present_in_gt"]
        ]
        wall_miou_present = (
            float(np.mean(wall_ious_present)) if wall_ious_present else 0.0
        )
        wall_miou_all = float(np.mean([per_class[c]["iou"] for c in wall_classes]))

        return {
            "pixel_accuracy": round(float(pixel_acc), 4),
            "mean_accuracy": round(float(mean_acc), 4),
            "mean_iou_present": round(float(np.mean(ious_present)), 4) if ious_present else 0.0,
            "mean_iou_all": round(float(np.mean(ious_all)), 4),
            "wall_mean_iou_present": round(float(wall_miou_present), 4),
            "wall_mean_iou_all": round(float(wall_miou_all), 4),
            "per_class": per_class,
            "confusion_matrix": cm.tolist(),
        }

    def get_confusion_matrix(self) -> np.ndarray:
        return self.conf_matrix.copy()

    def to_markdown_table(self) -> str:
        res = self.compute()
        lines = [
            "| Class | Present in GT | IoU | Dice / F1 | Precision | Recall | Boundary IoU | GT Pixels | Pred Pixels |",
            "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]
        for name in self.class_names:
            c_data = res["per_class"][name]
            pres_str = "Yes" if c_data["present_in_gt"] else "No"
            lines.append(
                f"| **{name}** | {pres_str} | {c_data['iou']:.4f} | {c_data['dice']:.4f} | "
                f"{c_data['precision']:.4f} | {c_data['recall']:.4f} | {c_data['boundary_iou']:.4f} | "
                f"{c_data['gt_pixels']:,} | {c_data['pred_pixels']:,} |"
            )
        return "\n".join(lines)
