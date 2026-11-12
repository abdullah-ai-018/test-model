# BRIEFING — 2026-11-07T20:36:00Z

## Mission
Conduct a rigorous audit of candidate floor plan datasets and benchmark ML architectures for wall/drywall segmentation to support model training and architecture selection.

## 🔒 My Identity
- Archetype: explorer
- Roles: Dataset Audit & ML Architectures Surveyor
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: Survey & Audit

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code or modify workspace outside state folder
- Audit candidate datasets (FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, MSD, ArchCAD-400k) verifying official sources, licensing, commercial/redistribution terms, annotation formats, accessibility without bypassing access restrictions or accepting licenses on user's behalf
- Generic wall annotations must not be assumed to be drywall; distinguish generic wall pretraining from drywall-specific classification
- Model benchmarking must evaluate SegFormer (B0/B1), U-Net, YOLOv8-seg, considering resolution, compute efficiency, and 4-class segmentation (Background, Drywall, Non-Drywall, Uncertain)
- Save all analyses and handoff in state folder (.agents/teamwork/survey_explorer_3)

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\DISPATCH.md`
  - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\env_audit.json`
  - FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, MSD, ArchCAD-400k official papers, licenses, repositories
- **Key findings**:
  - **MSD**: Fully eligible, top recommendation. CC BY 4.0 (commercial allowed), 174 MB HF download, explicit WKT wall polygons.
  - **CubiCasa5K**: Primary academic benchmark, CC BY-NC 4.0, 5.09 GB archive, rich vector SVG wall polygons.
  - **FloorPlanCAD**: Conditionally eligible (CC BY-NC 4.0 annotations, drawing copyright disclaimer).
  - **CVC-FP**: Conditionally eligible via Figshare mirror (353 MB, CC BY 4.0).
  - **R2V**: Ineligible for autonomous download (LIFULL raster images gated behind NII IDR agreement).
  - **SESYD**: Ineligible for wall segmentation (zero wall annotations; symbol spotting only).
  - **ArchCAD-400k**: Ineligible for autonomous download (gated access requiring manual credential submission and agreement).
  - **Architecture Benchmarking**: Semantic segmentation (SegFormer-B0 & Lightweight U-Net) is mathematically superior to instance segmentation (YOLOv8-seg) for continuous wall planar graphs.
  - **Hardware Adaptation**: Host is strictly CPU (Intel 8 cores, 7.88 GB RAM with ~0.9 GB free, CUDA=False). Training requires batch size = 2 to 4, gradient accumulation, CPU thread pinning (`torch.set_num_threads(4)`), and sliding-window 512x512 tiles with Gaussian apodization blending to prevent sub-pixel collapse of thin walls.
  - **Compound Loss & 4-Class Guardrails**: Class-Weighted CE + Soft Dice + Focal Loss resolves 90:10 background imbalance. Output strictly enforces 0:Background, 1:Drywall (Green), 2:Non-Drywall (Red), 3:Uncertain (Yellow). Generic wall pretraining must never be labeled as Drywall without verified partition schedule ground truth.
- **Unexplored areas**: None for survey scope. Training execution and dataset download scheduled for subsequent milestones.

## Key Decisions Made
- Confirmed MSD as primary pretraining dataset and CubiCasa5K as secondary benchmark.
- Disqualified R2V (auth block), SESYD (no wall labels), and ArchCAD-400k (gated license agreement).
- Selected SegFormer-B0 and Lightweight U-Net as the comparative benchmark candidates.
- Specified compound loss formulation (Weighted CE + Soft Dice + Focal Loss) and comprehensive metric suite (mIoU, per-class IoU, Dice, Precision/Recall, 4x4 Confusion Matrix, Boundary IoU).

## Artifact Index
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\analysis.md` — Comprehensive technical survey report
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\handoff.md` — 5-component handoff report
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\progress.md` — Liveness heartbeat & task tracking
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\DISPATCH.md` — Received dispatch instructions
