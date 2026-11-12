# Dispatch: Milestone M3 Loss & Metrics Explorer (`m3_explorer_2`)

## Mission
Design and specify the compound loss function (Class-Weighted Cross-Entropy + Soft Dice + Focal Loss) tailored to the severe 90:10 background-to-wall class imbalance, along with the complete semantic segmentation evaluation metrics suite (mIoU, per-class IoU, Dice/F1, Precision, Recall, Confusion Matrix) adhering to the strict 4-class classification guardrails.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (Workspace root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - specifically Section 1 Track 3, Section 2 Feature Inventory (F-LOSS-METRICS), Section 4.4 Model Checkpoint Contract, and Section 6 Zero-Tolerance Integrity Rules.
3. `drywall_detection/datasets/unified_format.py` (Strict 4-Class Taxonomy: 0=Background, 1=Drywall, 2=Non-Drywall, 3=Uncertain).
4. `drywall_detection/data/processed/splits/splits_summary.json` (Ground truth distributions across train/val/test splits).

## Tasks & Scope
1. **Severe Imbalance & Compound Loss Formulation**:
   - Analyze pixel class distributions in architectural drawing tiles (~90% Background, ~8% Drywall, ~1.5% Non-Drywall, ~0.5% Uncertain).
   - Formulate Compound Loss:
     $$\mathcal{L}_{total} = \lambda_{ce} \mathcal{L}_{ce\_weighted} + \lambda_{dice} \mathcal{L}_{soft\_dice} + \lambda_{focal} \mathcal{L}_{focal}$$
   - Calculate exact class inverse frequency weights: $w_c = \frac{1}{\log(1.02 + p_c)}$ or median frequency balancing to prevent background domination without destabilizing small classes (Non-Drywall, Uncertain).
   - Formulate multi-class Soft Dice Loss:
     $$\mathcal{L}_{dice} = 1 - \frac{1}{C} \sum_{c=0}^{C-1} \frac{2 \sum_i p_{i,c} g_{i,c} + \epsilon}{\sum_i p_{i,c}^2 + \sum_i g_{i,c}^2 + \epsilon}$$
     (handling empty ground truth classes safely with $\epsilon=1e-6$).
   - Formulate multi-class Focal Loss with $\gamma=2.0$ to focus learning on hard boundary pixels and linework.
   - Design default weighting coefficients (e.g. $\lambda_{ce}=0.4, \lambda_{dice}=0.4, \lambda_{focal}=0.2$).
2. **Evaluation Metrics Specification**:
   - Design `drywall_detection/models/metrics.py` class `SegmentationMetrics`:
     - Multi-class Confusion Matrix ($4 \times 4$ accumulator).
     - Per-class IoU: $IoU_c = \frac{TP_c}{TP_c + FP_c + FN_c}$.
     - Mean IoU (mIoU): Macro-average across classes present, and Wall mIoU (average over classes 1, 2, 3).
     - Per-class Dice / F1 Score, Precision, Recall.
     - Pixel Accuracy and Mean Accuracy.
     - Boundary IoU (evaluating edge sharpness of thin wall linework).
   - Ensure numerical stability: zero division protection when classes have zero ground truth and zero predictions ($IoU=1.0$ if $TP=FP=FN=0$, or exclude from macro-average with explicit reporting).
3. **Module Interface Contracts**:
   - Specify `drywall_detection/models/losses.py`:
     - `CompoundSegmentationLoss(weights=None, ce_weight=0.4, dice_weight=0.4, focal_weight=0.2, gamma=2.0, smooth=1e-6)`
   - Specify `drywall_detection/models/metrics.py`:
     - `SegmentationMetrics(num_classes=4, class_names=["Background", "Drywall", "Non-Drywall", "Uncertain"])`
     - Methods: `update(preds, targets)`, `compute() -> Dict[str, Any]`, `reset()`, `confusion_matrix() -> np.ndarray`.
4. **Guardrail Invariants**:
   - Non-Drywall (Class 2) and Uncertain (Class 3) must never be collapsed into Drywall (Class 1).
   - Verify that loss and metrics handle batch inputs `[B, 4, H, W]` logits and `[B, H, W]` integer class labels correctly.

## Deliverables
- Write mathematical formulations, implementation details, and verification test cases to `.agents/teamwork/m3_explorer_2/analysis.md`.
- Write self-contained handoff report to `.agents/teamwork/m3_explorer_2/handoff.md` following the Handoff Protocol.
- Notify orchestrator with summary upon completion.


## 2026-11-08T18:43:45Z
You are `m3_explorer_2`, the Loss & Metrics Explorer for Milestone M3 ("Model Benchmarking, Hardware Adaptation & Checkpoint Delivery").

Your mission is to design and specify the compound loss function (Class-Weighted Cross-Entropy + Soft Dice + Focal Loss) tailored to the severe 90:10 background-to-wall class imbalance, along with the complete semantic segmentation evaluation metrics suite (mIoU, per-class IoU, Dice/F1, Precision, Recall, Confusion Matrix) adhering to the strict 4-class classification guardrails.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_explorer_2\

Read your dispatch file first:
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_explorer_2\DISPATCH.md`

Also read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\datasets\unified_format.py`
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\processed\splits\splits_summary.json`

Deliverables:
- Author `analysis.md` in your state folder.
- Author `handoff.md` in your state folder following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send a completion message to parent orchestrator via `send_message`.
