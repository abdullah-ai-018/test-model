# Dispatch: Milestone M4 Implementation Worker (`worker_m4_1`)

You are `worker_m4_1`, the Implementation Worker for Milestone M4 (Wall Segmentation Training).

Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m4_1`
Your parent orchestrator is: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Notice — Progress Set & Single-Project Bounds
> The reference PDF represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped "PROGRESS SET 95% CDs 10/02/2026" and constitutes an interim construction design progress set, not an approved final as-built construction document. All 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results on this drawing set cannot prove cross-domain generalization. Include this notice in all generated reports.

## MANDATORY FIRST STEP
Read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1\handoff.md` (Architecture benchmarks, SegFormer-B0 champion selection, checkpoint bundle contract)
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_2\handoff.md` (Compound Loss blueprint, multi-metric evaluation suite, anti-leakage verification)
5. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3\handoff.md` (Hardware Tier 5 training engine, Colab runner specification, weak pseudo-label quarantine)

## File Ownership Boundaries
You have exclusive write access to:
- `drywall_detection/models/__init__.py`
- `drywall_detection/models/unet.py`
- `drywall_detection/models/segformer.py`
- `drywall_detection/models/losses.py`
- `drywall_detection/models/metrics.py`
- `drywall_detection/models/trainer.py`
- `drywall_detection/models/evaluate.py`
- `train_colab.py`
- `drywall_detection/checkpoints/best_model/*`
- `drywall_detection/reports/M4_model_training_report.md`
- `drywall_detection/tests/test_models.py`
- `drywall_detection/tests/test_training.py`
Do NOT modify unrelated QTO Engine files or prior milestone files.

## Detailed Objectives

### 1. Implement Model Architectures (`drywall_detection/models/`)
- `drywall_detection/models/segformer.py`:
  - Implement `SegFormerB0` model using `transformers.SegformerConfig` and `SegformerForSemanticSegmentation`.
  - Provide 100% offline fallback initialization (`from_config`) and graceful loading of local or pretrained weights.
  - Number of classes: 4 (`Background: 0, Drywall: 1, Non-Drywall: 2, Uncertain: 3`).
- `drywall_detection/models/unet.py`:
  - Implement `ResNet34UNet` using native `torchvision.models.resnet34` backbone with transposed convolution decoder blocks and skip connections (do NOT rely on `segmentation_models_pytorch` since it is not installed).
  - Also provide `LightweightUNet` as an ultra-fast CPU fallback option.
- `drywall_detection/models/__init__.py`:
  - Clean exports of model classes and model factory `create_segmentation_model(arch_name, num_classes=4, in_channels=3)`.

### 2. Implement Compound Loss Functions (`drywall_detection/models/losses.py`)
- Implement `SoftDiceLoss`:
  - Squared denominator ($\sum p^2 + \sum y^2$) for stronger gradients on thin wall linework.
  - Multi-class batch spatial aggregation.
- Implement `FocalLoss`:
  - Numerically stabilized with `log_softmax` and tensor `gather`.
  - Dynamic modulating factor $(1 - p_t)^\gamma$ with $\gamma = 2.0$ to suppress easy background gradients.
- Implement `CompoundLoss`:
  - $\mathcal{L} = \alpha \mathcal{L}_{\text{Dice}} + \beta \mathcal{L}_{\text{Focal}}$ with default $\alpha = 1.0, \beta = 1.0$.
  - Follow drop-in blueprint from `explorer_m4_2/handoff.md`.

### 3. Implement Multi-Metric Evaluation Suite (`drywall_detection/models/metrics.py`)
- Implement `SegmentationMetricTracker`:
  - Overall mIoU across all classes.
  - Foreground Wall IoU (averaging classes 1, 2, 3, omitting background class 0 to prevent artificial inflation).
  - Per-class IoU for Drywall (Class 1), Non-Drywall (Class 2), and Uncertain (Class 3).
  - Dice score / F1, Precision, Recall per class and macro-averaged.
  - Confusion Matrix: $4 \times 4$ contingency table supporting raw counts, row-normalized (recall), and col-normalized (precision).
- Implement `compute_boundary_iou`:
  - Cheng et al. (CVPR 2021) Boundary IoU at dilation distances $d=2$ and $d=4$ pixels.
  - Implement via PyTorch morphological pooling (`MaxPool2d`) for device-independent tensor execution.
- Implement `assert_zero_leakage_manifests(train_json, val_json)`:
  - Runtime verification ensuring zero project, drawing, or file path overlap between train and validation splits before evaluation.

### 4. Implement Hardware-Aware Training Engine (`drywall_detection/models/trainer.py`)
- Consume `drywall_detection.utils.hardware.probe_hardware` and `auto_configure_training`.
- Auto-adapt parameters for Tier 5 local host:
  - `batch_size = 2`
  - `num_workers = 0` (prevent Windows spawn deadlock)
  - `torch.set_num_threads(4)` (pin to physical cores)
  - `gradient_accumulation_steps = 8` (effective batch size 16)
  - Input resolution $256 \times 256$
  - Early stopping with patience = 5 epochs on validation mIoU.
- Integrate weak pseudo-label quarantine discount:
  - Loss weight factor $\lambda = 0.35$ for pseudo-labeled tiles.
  - Strict exclusion of quarantined samples from validation/test evaluation.
- Train candidate models (SegFormer-B0 and ResNet34-UNet) on dataset splits (`drywall_detection/data/processed/splits/train.json` and `val.json`).

### 5. Implement Comparative Evaluation Script (`drywall_detection/models/evaluate.py`)
- Evaluate candidate models comparatively on `drywall_detection/data/processed/splits/val.json`.
- Output comparative table: parameters, model size, FLOPs, CPU inference latency, mIoU, Foreground Wall IoU, Dice, Boundary IoU ($d=2, 4$).
- Select SegFormer-B0 as the champion based on parameter efficiency, boundary quality, memory safety, and inference speed.

### 6. Create Google Colab Standalone Runner (`train_colab.py`)
- Standalone runnable script and notebook cell structure compatible with Google Colab Tesla T4 GPU.
- Installs dependencies, downloads/prepares MSD dataset, auto-configures Tier 2 (`device="cuda"`, `batch_size=8`, mixed precision AMP `torch.cuda.amp.autocast`), executes training, and exports checkpoint bundle.

### 7. Package Best Model Checkpoint Bundle (`drywall_detection/checkpoints/best_model/`)
Save the champion model in `drywall_detection/checkpoints/best_model/` containing ALL 8 required artifacts:
1. `best_model.pt`: Checkpoint state dict, architecture metadata, class count, resolution, best val mIoU.
2. `config.json`: Architecture, hyperparameters, preprocessing, normalization, inference settings.
3. `class_mapping.json`: Canonical 4-class taxonomy, colors, descriptions, `id2label`, `label2id`.
4. `training_log.json`: Epoch-by-epoch loss, val loss, mIoU, Dice history.
5. `metrics.json`: Final quantitative evaluation metrics summary on validation/test set.
6. `infer.py`: Standalone single-file CLI reload-and-infer runner (zero external dependencies beyond PyTorch/PIL/numpy).
   - Must support: `python infer.py --image <image_path> [--output <output_path>] [--checkpoint best_model.pt]`
   - Reloads model, runs inference, outputs color-coded overlay, and returns JSON summary.
7. `README.md`: Model card, specs, benchmarks, usage examples.
8. `sample_overlays/`: Visual inspection triplets (`sample_01_original.png`, `sample_01_mask.png`, `sample_01_overlay.png`).

### 8. Implement Unit Test Suites (`drywall_detection/tests/`)
- `drywall_detection/tests/test_models.py`:
  - Forward pass output shape check for SegFormer-B0 and ResNet34-UNet (`[B, 4, H, W]`).
  - Backward pass gradient flow verification.
  - Offline instantiation without internet check.
- `drywall_detection/tests/test_training.py`:
  - Loss function numerical stability (zero NaN/Inf, all-background mask, single-pixel wall).
  - Metric calculations (mIoU, Foreground Wall IoU, Confusion Matrix row/col normalization, Boundary IoU).
  - Runtime zero-leakage assertion gate.
  - Checkpoint save and reload verification: assert reload from disk reproduces identical predictions.
  - Standalone `infer.py` execution test.

### 9. Deliver Milestone Report
Write `drywall_detection/reports/M4_model_training_report.md` documenting:
- Hardware specifications and auto-configured tier.
- Comparative architecture evaluation table (SegFormer-B0 vs ResNet34-UNet).
- Empirical class imbalance analysis and compound loss convergence.
- Multi-metric evaluation results (mIoU, Foreground Wall IoU, Dice, Boundary IoU).
- Checkpoint bundle contents and standalone reload-and-infer verification.
- Google Colab GPU training instructions.
- Mandatory 95% CDs progress set notice and domain gap analysis.

Run all tests via `python -m pytest drywall_detection/tests/ -v` and ensure 100% pass with ZERO regressions.
Deliver your handoff report to `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m4_1\handoff.md` and message parent orchestrator upon completion.
