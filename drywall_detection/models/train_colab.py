"""
drywall_detection.models.train_colab
===================================
Google Colab / Cloud GPU Training Script for Drywall Semantic Segmentation.

Designed for high-throughput GPU training on NVIDIA Tesla T4 / A100 instances.
Features:
- Dynamic hardware auto-detection (CUDA / AMP float16 mixed precision).
- Scaled batch size (B=16) and multi-threaded data loading (num_workers=2, pin_memory=True).
- Full 30-epoch training schedule with Cosine Annealing learning rate.
- Automated package delivery to checkpoints/best_model/.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import torch

from drywall_detection.datasets.loader import get_tile_dataloader
from drywall_detection.models.losses import CompoundSegmentationLoss
from drywall_detection.models.segformer import build_segformer
from drywall_detection.models.trainer import Trainer
from drywall_detection.utils.hardware import probe_hardware, auto_configure_training

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_colab_training(
    train_manifest: str = "drywall_detection/data/processed/splits/train.json",
    val_manifest: str = "drywall_detection/data/processed/splits/val.json",
    checkpoint_dir: str = "drywall_detection/checkpoints/best_model",
    batch_size: int = 16,
    num_workers: int = 2,
    max_epochs: int = 30,
    learning_rate: float = 1e-4,
    early_stopping_patience: int = 7,
) -> None:
    """
    Executes cloud GPU accelerated training loop.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Initializing training on device: %s", device)

    # Hardware profile inspection
    try:
        profile = probe_hardware()
        train_cfg = auto_configure_training(profile)
        logger.info(
            "Hardware Profile: Tier %s (%s). Recommend Batch Size=%d, AMP=%s",
            train_cfg.hardware_tier,
            train_cfg.tier_description,
            train_cfg.batch_size,
            train_cfg.use_amp,
        )
    except Exception as exc:
        logger.warning("Hardware profiling fallback: %s", exc)

    # Setup DataLoaders
    # Note: On CPU fallback, keep workers safe
    effective_workers = num_workers if device.type == "cuda" else 0
    effective_batch = batch_size if device.type == "cuda" else min(2, batch_size)
    pin_mem = True if device.type == "cuda" else False

    logger.info("Building DataLoaders (batch_size=%d, num_workers=%d)...", effective_batch, effective_workers)
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

    logger.info("Instantiating SegFormer-B0 Champion Model...")
    model = build_segformer(num_classes=4, pretrained=False, offline=True)
    param_count = model.count_parameters()
    logger.info("Model parameters: %d (~%.2fM)", param_count, param_count / 1e6)

    criterion = CompoundSegmentationLoss(
        num_classes=4,
        ce_weight=0.4,
        dice_weight=0.4,
        focal_weight=0.2,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=1e-2,
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max_epochs,
        eta_min=1e-6,
    )

    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        gradient_accumulation_steps=1 if device.type == "cuda" else 4,
        max_epochs=max_epochs,
        early_stopping_patience=early_stopping_patience,
        checkpoint_dir=checkpoint_dir,
    )

    logger.info("Commencing fit loop...")
    results = trainer.fit()
    logger.info("Training finished. Champion epoch: %s", results.get("best_epoch"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Colab / Cloud GPU Training Runner.")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument("--checkpoint-dir", type=str, default="drywall_detection/checkpoints/best_model")
    args = parser.parse_args()

    run_colab_training(
        checkpoint_dir=args.checkpoint_dir,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        learning_rate=args.lr,
        early_stopping_patience=args.patience,
    )


if __name__ == "__main__":
    main()
