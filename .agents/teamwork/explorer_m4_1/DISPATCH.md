# Dispatch: Milestone M4 Model Architecture Explorer

You are `explorer_m4_1`, the Model Architecture Explorer for Milestone M4 (Wall Segmentation Training).

Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1`
Your parent orchestrator is: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`

## MANDATORY FIRST STEP
Read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py`
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M2_dataset_report.md`
5. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M3_vector_schedule_report.md`

## Objectives
1. **Audit ML Dependencies**:
   - Inspect local environment for installed ML libraries: `torch`, `torchvision`, `transformers`, `timm`, `albumentations`, `scikit-learn`, etc.
   - Verify versions and offline capabilities.
2. **Evaluate Candidate Architectures**:
   - Compare at least two segmentation architectures:
     - Lightweight U-Net with ResNet34 (or MobileNetV3 / EfficientNet) backbone.
     - SegFormer (B0 or B1) semantic segmentation transformer.
   - Analyze: parameter counts, FLOPs, memory footprint under local CPU constraints, inference speed, and offline fallback (if pretrained weights cannot be fetched dynamically).
3. **Design Checkpoint Bundle**:
   - Specify exact file formats and contracts for `drywall_detection/checkpoints/best_model/`:
     - `best_model.pt` (weights / state dict)
     - `config.json` (architecture type, backbone, resolution, normalization)
     - `class_mapping.json` (`{"0": "background", "1": "wall"}`)
     - `training_log.json` (epoch loss, val loss, mIoU curves)
     - `metrics.json` (validation metrics summary)
     - `infer.py` (standalone single-file reload-and-infer script)
     - `README.md` (usage, environment requirements, loading instructions)
     - `sample_overlays/` (visual predictions)
4. **Deliver Report**:
   - Deliver your findings, architecture diagrams, and recommendations in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1\handoff.md`.
   - Message parent orchestrator upon completion.


## 2026-11-08T19:08:17Z
You are explorer_m4_1, the Model Architecture Explorer for Milestone M4 (Wall Segmentation Training).

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1
Your parent orchestrator is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

Read instructions in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1\DISPATCH.md`.
Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `drywall_detection/config.py`, and Milestone M2/M3 reports.

Investigate:
1. ML dependencies installed locally (torch, torchvision, transformers, timm).
2. Compare U-Net (ResNet34 encoder) vs SegFormer (B0/B1) for wall segmentation (parameters, FLOPs, CPU inference latency, memory, offline fallback).
3. Design checkpoint package contract for `drywall_detection/checkpoints/best_model/` (best_model.pt, config.json, class_mapping.json, training_log.json, metrics.json, standalone infer.py, README.md, sample overlays).
4. Deliver report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_1\handoff.md` and message parent orchestrator.
