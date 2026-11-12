# Dispatch: Milestone M4 Loss and Metrics Explorer

You are `explorer_m4_2`, the Loss & Metrics Explorer for Milestone M4 (Wall Segmentation Training).

Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_2`
Your parent orchestrator is: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`

## MANDATORY FIRST STEP
Read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M2_dataset_report.md`
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\processed\splits\splits_summary.json`

## Objectives
1. **Formulate Compound Loss Function**:
   - Address the severe ~90:10 background-to-wall class imbalance characteristic of architectural floor plans.
   - Formulate and mathematical verify a compound loss:
     - Soft Dice Loss (smooth intersection over union for thin wall features).
     - Focal Loss or Class-Weighted Cross-Entropy (penalizing false negatives and focusing on hard boundaries).
   - Specify weighting formulation (e.g., $\mathcal{L} = \alpha \mathcal{L}_{\text{Dice}} + \beta \mathcal{L}_{\text{Focal}}$).
2. **Define Multi-Metric Evaluation Suite**:
   - Specify exact mathematical definitions and implementation algorithms for:
     - Mean Intersection over Union (mIoU) and per-class Wall IoU.
     - Dice Coefficient / F1-Score.
     - Precision and Recall.
     - Confusion Matrix (normalized and unnormalized).
     - Boundary IoU / Boundary Quality (evaluating wall border alignment quality).
3. **Data Split Verification & Anti-Leakage Protocol**:
   - Verify evaluation strictly against drawing-level project-isolated `val.json` from Milestone M2.
   - Confirm zero project/building overlap between training and validation sets.
4. **Deliver Report**:
   - Deliver formulas, loss modules, evaluation scripts, and validation criteria in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_2\handoff.md`.
   - Message parent orchestrator upon completion.


## 2026-11-08T19:08:17Z
[Message from 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a]
You are explorer_m4_2, the Loss and Metrics Explorer for Milestone M4 (Wall Segmentation Training).
Investigate:
1. Compound loss formulation addressing 90:10 background-to-wall class imbalance (Soft Dice Loss + Focal Loss / Class-Weighted Cross-Entropy).
2. Multi-metric evaluation suite (mIoU, per-class Wall IoU, Dice/F1, Precision, Recall, Confusion Matrix, Boundary IoU).
3. Anti-leakage protocol verifying evaluation strictly against drawing-level project-isolated val.json from Milestone M2.
4. Deliver report in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_2\handoff.md and message parent orchestrator.
