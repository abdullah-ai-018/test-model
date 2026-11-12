# Dispatch: Milestone M3 Hardware & Training Loop Explorer (`m3_explorer_3`)

## Mission
Profile the local hardware execution constraints, design a robust, low-memory CPU training and validation loop (with dynamic thread allocation, gradient accumulation, and early stopping), establish drawing-level validation protocols, design model checkpoint packaging (`best_model/`), and provide a 100% portable Google Colab fallback / GPU training workflow.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (Workspace root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - specifically Section 1 Track 3, Section 2 Feature Inventory (F-MODEL-TRAIN, F-CHECKPOINT-SAVE, F-CHECKPOINT-RELOAD, F-PSEUDO-GUARD), Section 4.4 Model Checkpoint Contract, and Section 5 Code Layout.
3. `drywall_detection/utils/hardware.py` (Local hardware profile and compute environment).
4. `drywall_detection/datasets/loader.py` (Streaming tile dataset & DataLoader).
5. `drywall_detection/data/processed/splits/splits_summary.json` (Dataset splits: `train.json`, `val.json`, `test.json`, `quarantine.json`).

## Tasks & Scope
1. **Hardware Profiling & Hyperparameter Adaptation**:
   - Local environment: Windows 11 AMD64, Intel 4 physical / 8 logical cores, strictly CPU execution (`torch 2.1.0+cpu`, no CUDA), ~1.0 GB RAM available.
   - Guard against Windows multiprocessing crash (`spawn` memory overhead): `num_workers=0` in PyTorch `DataLoader` is strictly mandatory.
   - Hyperparameter adaptation:
     - `batch_size = 2`
     - `gradient_accumulation_steps = 4` (effective batch size = 8)
     - `torch.set_num_threads(4)` (saturating physical cores without thrashing context switches)
     - Optimizer: `torch.optim.AdamW(lr=1e-4, weight_decay=1e-2)`
     - LR Scheduler: `torch.optim.lr_scheduler.CosineAnnealingLR` or `ReduceLROnPlateau`
     - Epoch budget: 5–10 epochs on local CPU (or early stopping with patience=3 on validation mIoU)
2. **Training Loop & Validation Architecture**:
   - Design `drywall_detection/models/trainer.py` (`Trainer` class):
     - Support both SegFormer-B0 and U-Net backbones.
     - Training step: forward, loss calculation, backward with accumulation, optimizer step, gradient clipping (`clip_grad_norm_(max_norm=1.0)`).
     - Validation step: evaluate on drawing-level `val.json` every epoch; compute mIoU, per-class IoU, Dice, loss.
     - Early stopping logic tracking validation mIoU (`best_val_miou`).
     - Progress logging: console progress and structured JSON history (`training_log.json`).
3. **Model Checkpoint Contract (`best_model/`)**:
   - Design `drywall_detection/checkpoints/best_model/` packaging:
     * `best_model.pt` (PyTorch state dict & model weights)
     * `config.json` (architecture name, backbone, input resolution 512, normalization mean/std, num_classes 4)
     * `class_mapping.json` (`{"0": "Background", "1": "Drywall", "2": "Non-Drywall", "3": "Uncertain"}`)
     * `training_log.json` (epoch losses, metrics history, timestamps)
     * `metrics.json` (final evaluation metrics on test.json: mIoU, Dice, Precision, Recall, confusion matrix)
     * `infer.py` (standalone offline inference CLI reloading `best_model.pt` without external dependencies)
     * `README.md` (invocation guide, model metadata, reproducible CLI commands)
     * `sample_overlays/` (visual predictions vs ground truth masks)
   - Ensure `infer.py` can be invoked independently: `python infer.py --input <path_to_tile_or_pdf> --output <path_to_output>`.
4. **Drawing-Level Split Integrity & Quarantine Guardrail**:
   - Ensure zero leakage: training must strictly use `train.json`, validation strictly `val.json`, test strictly `test.json`.
   - Ensure MTA Sheet A-105+ weak pseudo-labels in `quarantine.json` are strictly excluded from validation and test sets.
5. **Google Colab / Cloud GPU Fallback**:
   - Provide a complete, self-contained Google Colab script / Jupyter notebook (`notebooks/train_colab.ipynb` or CLI command) that can run on a free T4 GPU (batch size 16, mixed precision FP16, fast 30-epoch training).

## Deliverables
- Write complete training loop design, hardware profiling, and checkpoint contract to `.agents/teamwork/m3_explorer_3/analysis.md`.
- Write self-contained handoff report to `.agents/teamwork/m3_explorer_3/handoff.md` following the Handoff Protocol.
- Notify orchestrator with summary upon completion.


## 2026-11-08T18:43:46Z
You are `m3_explorer_3`, the Hardware & Training Loop Explorer for Milestone M3 ("Model Benchmarking, Hardware Adaptation & Checkpoint Delivery").

Your mission is to profile the local hardware execution constraints, design a robust, low-memory CPU training and validation loop (with dynamic thread allocation, gradient accumulation, and early stopping), establish drawing-level validation protocols, design model checkpoint packaging (`best_model/`), and provide a 100% portable Google Colab fallback / GPU training workflow.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_explorer_3\
