# BRIEFING — 2026-11-07T20:31:00Z

## Mission
Survey 6 candidate floor plan datasets (CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, MSD) and ML segmentation architectures/loss/metrics/Colab compatibility, split requirements, and weak pseudo-labeling rules for drywall detection.

## 🔒 My Identity
- Archetype: explorer
- Roles: Dataset & ML Architecture Surveyor
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3
- Original parent: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a
- Milestone: M1 (Workspace and Dataset Audit)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement project source code
- Only write metadata inside `.agents/teamwork/explorer_survey_3/`
- Never bypass access restrictions or accept licenses on user's behalf
- Audit datasets without downloading >10 GB unannounced
- Strict project/drawing splitting (zero project overlap)
- Produce evidence-based findings, no fabricated URLs or metrics

## Current Parent
- Conversation ID: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a
- Updated: 2026-11-07T20:31:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`
  - `.agents/teamwork/explorer_survey_1/env_audit.json`
  - Zenodo API (`record/2613548`, `record/7788422`, `record/7921780`)
  - Hugging Face Datasets API (`philippds/modified-swiss-dwellings-enriched`, `Voxel51/FloorPlanCAD`)
  - FloorPlanCAD project site (`floorplancad.github.io`)
  - SESYD project site (`mathieu.delalandre.free.fr/projects/sesyd/`)
  - Figshare API (`articles/12082131`)
- **Key findings**:
  - **Modified Swiss Dwellings (MSD)**: Top eligible dataset. 174 MB download, CC BY 4.0 permissive license, explicit WKT wall polygons (`entity_subtype: WALL`), hierarchical IDs (`site_id`, `building_id`, `plan_id`).
  - **CubiCasa5K**: Primary academic benchmark. Zenodo download size 5.09 GB (< 10 GB limit), CC BY-NC-SA 4.0, explicit SVG wall polygons.
  - **FloorPlanCAD**: Conditionally eligible. Annotations CC BY-NC 4.0, but drawings copyright disclaimer. 454 MB HuggingFace mirror / Google Drive parts.
  - **CVC-FP**: Conditionally eligible via Figshare (353.6 MB) / Zenodo. Original university server timed out. Small sample (122 drawings).
  - **R2V**: Ineligible for autonomous download. LIFULL raw images require formal institutional application to NII IDR.
  - **SESYD**: Ineligible for wall segmentation. Lacks wall labels completely (only 16 furniture/fixture symbol classes).
  - **Data Splitting**: Strict project/drawing level grouping (`site_id` / building folder) to prevent building footprint and drafting style leakage; zero project overlap.
  - **Architectures**: U-Net with pretrained encoder (ResNet34) and SegFormer (MiT-B0/B1) outperform YOLOv8-seg (semantic segmentation matches continuous planar wall graphs).
  - **Loss Function**: Compound Soft Dice + Focal Loss (or Dice + Cross-Entropy) to solve 90:10 background-to-wall class imbalance.
  - **Hardware & Colab**: Local environment has `torch 2.1.0+cpu`, no CUDA GPU, and ~0.9 GB free RAM. Colab-compatible training scripts with automated hardware probing and Google Drive persistence are critical.
  - **Weak Pseudo-Labeling**: Vector-extracted masks from 99th Street must be explicitly tagged as weak, visually spot-checked for error rate, and strictly kept out of validation/test splits.
- **Unexplored areas**: None for M1 survey scope. Downstream download and training execution occur in M2 and M4.

## Key Decisions Made
- Confirmed MSD as top recommended dataset for M2, followed by CubiCasa5K.
- Disqualified R2V (auth wall) and SESYD (no wall annotations).
- Selected U-Net and SegFormer as the two comparative candidate architectures for M4.
- Mandated compound Dice + Focal loss and Boundary IoU evaluation.
- Formulated strict weak pseudo-label isolation protocol.

## Artifact Index
- `DISPATCH.md` — Received dispatch instructions
- `BRIEFING.md` — Working memory and identity index
- `progress.md` — Heartbeat and activity log
- `report.md` — Comprehensive survey report on 6 candidate datasets, data splitting, ML architectures, and weak pseudo-labeling rules
- `handoff.md` — 5-component handoff report for the orchestrator
