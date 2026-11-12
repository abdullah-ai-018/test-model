#!/usr/bin/env python3
"""
train_colab.py
==============
Standalone Google Colab / Cloud GPU Training Runner for Drywall & Architectural Wall Segmentation.

Optimized for Google Colab Free Tier (Tesla T4 GPU, 16GB VRAM, Ubuntu 22.04 LTS).
Auto-engages Tier 2 GPU specifications:
- Device: CUDA
- Batch size: 8 (or 16), Gradient Accumulation: 2 (effective batch size: 16)
- Mixed Precision: PyTorch AMP (torch.cuda.amp.autocast + GradScaler)
- Native resolution: 512x512 (or 256x256 fallback)
- Symmetrical Cosine Annealing learning rate schedule
- Champion SegFormer-B0 architecture
- Automatic export to drywall_detection/checkpoints/best_model/

Can be executed in Colab via:
    !python train_colab.py --epochs 25 --batch-size 8
Or pasted cell-by-cell into a Jupyter/Colab notebook.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train_colab")


def verify_colab_environment() -> Dict[str, Any]:
    """
    Checks GPU availability, device name, VRAM headroom, and PyTorch CUDA build.
    """
    env_info = {
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else 0.0,
        "pytorch_version": torch.__version__,
        "python_version": sys.version.split()[0],
    }
    logger.info("Environment probe: %s", env_info)
    return env_info


def install_colab_dependencies() -> None:
    """
    Installs required headless packages in Colab environment if not installed.
    """
    required_packages = ["pymupdf", "shapely", "opencv-python-headless"]
    for pkg in required_packages:
        try:
            __import__(pkg if pkg != "opencv-python-headless" else "cv2")
        except ImportError:
            logger.info("Installing missing package: %s...", pkg)
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)


def run_colab_training(
    train_manifest: str = "drywall_detection/data/processed/splits/train.json",
    val_manifest: str = "drywall_detection/data/processed/splits/val.json",
    checkpoint_dir: str = "drywall_detection/checkpoints/best_model",
    batch_size: int = 8,
    num_workers: int = 2,
    gradient_accumulation_steps: int = 2,
    max_epochs: int = 25,
    learning_rate: float = 1e-4,
    early_stopping_patience: int = 5,
    use_amp: bool = True,
) -> Dict[str, Any]:
    """
    Executes Tier 2 Cloud GPU training loop for SegFormer-B0.
    """
    env_info = verify_colab_environment()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Import modules from drywall_detection
    from drywall_detection.datasets.loader import get_tile_dataloader
    from drywall_detection.models.losses import CompoundLoss
    from drywall_detection.models.segformer import SegFormerB0
    from drywall_detection.models.metrics import SegmentationMetricTracker, assert_zero_leakage_manifests

    # Zero leakage check
    if Path(train_manifest).exists() and Path(val_manifest).exists():
        assert_zero_leakage_manifests(train_manifest, val_manifest)
        logger.info("Zero-leakage verification passed between %s and %s.", train_manifest, val_manifest)

    # Resolve safe dataloader parameters based on device
    effective_workers = num_workers if device.type == "cuda" else 0
    effective_batch = batch_size if device.type == "cuda" else min(2, batch_size)
    pin_mem = True if device.type == "cuda" else False

    logger.info("Creating DataLoaders (batch_size=%d, num_workers=%d, pin_memory=%s)...", effective_batch, effective_workers, pin_mem)
    train_loader = get_tile_dataloader(
        manifest_or_tiles=train_manifest,
        is_train=True,
        batch_size=effective_batch,
        num_workers=effective_workers,
        pin_memory=pin_mem,
    )
    val_loader = get_tile_dataloader(
        manifest_or_tiles=val_manifest,
        is_train=False,
        batch_size=effective_batch,
        num_workers=effective_workers,
        pin_memory=pin_mem,
    )

    # Initialize champion SegFormer-B0 model
    logger.info("Initializing SegFormer-B0 champion model...")
    model = SegFormerB0(num_classes=4, offline=True).to(device)
    param_count = model.count_parameters()
    logger.info("SegFormer-B0 total parameters: %d (~%.2fM)", param_count, param_count / 1e6)

    criterion = CompoundLoss(num_classes=4, alpha=1.0, beta=1.0).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-6)

    # Setup AMP mixed precision if on CUDA
    enable_amp = use_amp and (device.type == "cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=enable_amp)
    logger.info("Mixed precision AMP enabled: %s", enable_amp)

    best_val_miou = 0.0
    patience_counter = 0
    history = []
    ckpt_path = Path(checkpoint_dir)
    ckpt_path.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, max_epochs + 1):
        t0 = time.time()
        model.train()
        optimizer.zero_grad()
        total_loss = 0.0
        steps = len(train_loader)

        for step, batch in enumerate(train_loader):
            images = batch[0].to(device)
            targets = batch[1].to(device)
            metas = batch[2] if len(batch) >= 3 else None

            with torch.cuda.amp.autocast(enabled=enable_amp):
                outputs = model(images)
                logits = outputs.logits if hasattr(outputs, "logits") else (outputs["logits"] if isinstance(outputs, dict) else outputs)
                loss, comps = criterion(logits, targets)

                # Weak pseudo-label discount (lambda = 0.35)
                if metas is not None:
                    is_pseudo = any(isinstance(m, dict) and (m.get("is_pseudo_label", False) or m.get("label_type") == "weak_pseudo_label") for m in metas)
                    if is_pseudo:
                        loss = loss * 0.35

                loss_scaled = loss / gradient_accumulation_steps

            scaler.scale(loss_scaled).backward()
            total_loss += float(loss.item())

            if (step + 1) % gradient_accumulation_steps == 0 or (step + 1) == steps:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()

        scheduler.step()
        train_loss = total_loss / max(1, steps)

        # Validation
        model.eval()
        val_tracker = SegmentationMetricTracker(num_classes=4)
        val_loss_total = 0.0
        val_steps = len(val_loader)

        with torch.no_grad():
            for batch in val_loader:
                v_images = batch[0].to(device)
                v_targets = batch[1].to(device)
                with torch.cuda.amp.autocast(enabled=enable_amp):
                    v_out = model(v_images)
                    v_logits = v_out.logits if hasattr(v_out, "logits") else (v_out["logits"] if isinstance(v_out, dict) else v_out)
                    v_loss, _ = criterion(v_logits, v_targets)
                val_loss_total += float(v_loss.item())
                val_tracker.update(v_logits, v_targets)

        report = val_tracker.compute()
        val_loss = val_loss_total / max(1, val_steps)
        val_miou = report.miou_all_classes
        wall_iou = report.foreground_wall_iou
        duration = round(time.time() - t0, 2)

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "val_miou": round(val_miou, 4),
            "val_wall_iou": round(wall_iou, 4),
            "duration_sec": duration,
        }
        history.append(epoch_record)

        logger.info(
            "Epoch %d/%d [%.1fs]: train_loss=%.4f | val_loss=%.4f | val_mIoU=%.4f | wall_IoU=%.4f",
            epoch, max_epochs, duration, train_loss, val_loss, val_miou, wall_iou,
        )

        # Check improvement
        if val_miou > best_val_miou + 1e-4:
            best_val_miou = val_miou
            patience_counter = 0
            logger.info("New best val mIoU (%.4f) achieved! Saving checkpoint bundle...", val_miou)

            # Save state dict
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_metric": val_miou,
                "metric_name": "val_mIoU",
                "wall_iou": wall_iou,
                "architecture": "SegFormerB0",
                "num_classes": 4,
            }, ckpt_path / "best_model.pt")

            # Save training log
            with open(ckpt_path / "training_log.json", "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)

            # Save metrics
            with open(ckpt_path / "metrics.json", "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        else:
            patience_counter += 1
            if patience_counter >= early_stopping_patience:
                logger.info("Early stopping triggered at epoch %d (patience limit %d reached).", epoch, early_stopping_patience)
                break

    logger.info("Training complete. Best val mIoU: %.4f", best_val_miou)
    return {
        "status": "completed",
        "best_val_miou": best_val_miou,
        "history": history,
        "checkpoint_dir": str(ckpt_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Google Colab / Cloud GPU Training Runner.")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience")
    parser.add_argument("--checkpoint-dir", type=str, default="drywall_detection/checkpoints/best_model", help="Checkpoint output directory")
    parser.add_argument("--no-amp", action="store_true", help="Disable mixed precision AMP")
    args = parser.parse_args()

    run_colab_training(
        checkpoint_dir=args.checkpoint_dir,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        learning_rate=args.lr,
        early_stopping_patience=args.patience,
        use_amp=not args.no_amp,
    )


if __name__ == "__main__":
    main()
