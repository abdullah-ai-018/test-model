# Dispatch: Milestone M3 Implementation Worker (`m3_worker_1`)

## Mission
Implement candidate semantic segmentation models (SegFormer-B0 and Lightweight U-Net), compound loss function, evaluation metrics suite, CPU-adapted training and validation loop, evaluate on drawing-level splits, package the champion model checkpoint bundle into `drywall_detection/checkpoints/best_model/`, verify standalone inference reload, and provide a portable Google Colab GPU training workflow.

## MANDATORY INTEGRITY WARNING (VERBATIM)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - Sections 1 (Track 3), 2 (Features 18-24), 4.4 (Model Checkpoint Contract), 5 (Code Layout), and 6 (Zero-Tolerance Integrity Rules).
3. `m3_explorer_1` Analysis & Handoff (`.agents/teamwork/m3_explorer_1/analysis.md` and `handoff.md`) - SegFormer-B0 and ResNet18 U-Net architectural specifications, parameter counts, and offline fallback.
4. `m3_explorer_2` Analysis & Handoff (`.agents/teamwork/m3_explorer_2/analysis.md` and `handoff.md`) - Compound Loss ($\mathcal{L}_{CE} + \mathcal{L}_{Dice} + \mathcal{L}_{Focal}$) and `SegmentationMetrics` suite.
5. `m3_explorer_3` Analysis & Handoff (`.agents/teamwork/m3_explorer_3/analysis.md` and `handoff.md`) - CPU hardware adaptation, training loop, early stopping, drawing-level validation, checkpoint packaging, and Colab fallback.
6. `drywall_detection/datasets/loader.py` - Streaming DataLoader and tile dataset.
7. `drywall_detection/data/processed/splits/splits_summary.json` - Ground truth splits (`train.json`, `val.json`, `test.json`, `quarantine.json`).

## Files to Create & Own
You have exclusive write ownership of the following files:
1. `drywall_detection/models/__init__.py`
2. `drywall_detection/models/segformer.py` - `SegFormerWallDetector` (MiT-B0 encoder + all-MLP decoder, 3.72M params, bilinear upsample to input dimensions, offline initialization fallback).
3. `drywall_detection/models/unet.py` - `UNetWallDetector` (native `torchvision.models.resnet18` backbone with 4-stage convolutional decoder with skip connections, 14.34M params).
4. `drywall_detection/models/losses.py` - `CompoundSegmentationLoss` (Class-Weighted CE + Multi-Class Soft Dice + Focal Loss with normalized $\alpha$, class weights `[1.0, 5.0, 15.0, 20.0]`).
5. `drywall_detection/models/metrics.py` - `SegmentationMetrics` (streaming $4 \times 4$ confusion matrix, per-class IoU, Wall mIoU, Dice/F1, Precision, Recall, native PyTorch Boundary IoU).
6. `drywall_detection/models/trainer.py` - `Trainer` class (CPU-adapted training loop, `num_workers=0`, `torch.set_num_threads(4)`, $B=2$, $N_{accum}=4$, AdamW, Cosine Annealing LR, drawing-level validation on `val.json`, early stopping with patience $P=3$ on `val_miou`).
7. `drywall_detection/models/evaluate.py` - Standalone evaluation script on `test.json` computing metrics, confusion matrix, and saving sample visual overlays.
8. `drywall_detection/models/train_colab.py` & `notebooks/train_colab.ipynb` - 100% portable Colab GPU training script/notebook (Tesla T4, FP16 AMP, $B=16$).
9. `drywall_detection/checkpoints/best_model/` packaging:
   - `best_model.pt`
   - `config.json`
   - `class_mapping.json` (`{"0": "Background", "1": "Drywall", "2": "Non-Drywall", "3": "Uncertain"}`)
   - `training_log.json`
   - `metrics.json`
   - `infer.py` (standalone offline inference CLI supporting tile and multi-page PDF input)
   - `README.md`
   - `sample_overlays/`
10. `drywall_detection/tests/test_models.py` - Comprehensive unit and integration test suite covering architectures, forward passes, losses, metrics, trainer, and standalone reload.
11. `drywall_detection/reports/M3_model_benchmarking_report.md` - Formal Milestone M3 Report.

## Mandatory Verification Commands
Run build/test verification and report exact outputs:
1. `python -m pytest drywall_detection/tests/test_models.py -v` (All unit tests must pass).
2. `python drywall_detection/checkpoints/best_model/infer.py --help` (Verify standalone inference CLI loads clean).
3. Full regression run: `python -m pytest drywall_detection/tests/ -v` (All 545 existing tests + new test suite must pass 100%).

## Deliverables
- Author all source, test, checkpoint, and report files.
- Author `.agents/teamwork/m3_worker_1/handoff.md` following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send completion message to parent orchestrator.
