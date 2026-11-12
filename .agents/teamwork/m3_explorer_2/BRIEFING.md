# BRIEFING — 2026-11-08T19:02:00Z

## Mission
Design and specify the compound loss function (Class-Weighted Cross-Entropy + Soft Dice + Focal Loss) tailored to the severe 90:10 background-to-wall class imbalance, along with the complete semantic segmentation evaluation metrics suite (mIoU, per-class IoU, Dice/F1, Precision, Recall, Confusion Matrix) adhering to the strict 4-class classification guardrails.

## 🔒 My Identity
- Archetype: explorer
- Roles: Loss & Metrics Explorer
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_explorer_2\
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: M3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in `drywall_detection/models/`
- Compound loss tailored to severe 90:10 background-to-wall class imbalance (Weighted Cross-Entropy + Soft Dice + Focal Loss)
- Multi-class evaluation metrics suite adhering to 4-class taxonomy (0: Background, 1: Drywall, 2: Non-Drywall, 3: Uncertain)
- Guardrails: Non-Drywall (Class 2) and Uncertain (Class 3) must never be collapsed into Drywall (Class 1)
- Zero-tolerance integrity: No synthetic or hardcoded metrics; proper numerical stability for zero-division cases
- Write only to state folder: `.agents\teamwork\m3_explorer_2\`

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: 2026-11-08T18:43:45Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md` (R1-R4, acceptance criteria)
  - `PROJECT.md` (Track 3, F-LOSS-METRICS, section 4.4, zero-tolerance rules)
  - `drywall_detection/datasets/unified_format.py` (DatasetClass 0..3, PALETTE_256, SlidingWindowTiler)
  - `drywall_detection/datasets/loader.py` (DrywallTileDataset, safe_collate_fn)
  - `drywall_detection/config.py` (taxonomy, colors, schedule guardrails)
  - `drywall_detection/utils/hardware.py` (hardware constraints, memory limits)
  - `drywall_detection/data/processed/splits/splits_summary.json` (ground truth split stats)
  - `drywall_detection/data/processed/masks_ground_truth/` (A-100 to A-104 pixel census)
  - `drywall_detection/data/processed/masks_multiclass/` (mock_plan_00 to mock_plan_05 pixel census)
- **Key findings**:
  - Empirical background prevalence is 83.68% to 99.90% (>95% on floor plans; 97.46% on combined train split).
  - Drywall represents ~1.71% in train set, Non-Drywall 0.00%, Uncertain 0.84%.
  - Smoothed ENet inverse frequency $w_c = \frac{1}{\log(1.02 + p_c)}$ bounds maximum weight to ~50.5, preventing gradient overflow on absent classes.
  - PyTorch's default `F.cross_entropy` computes weighted mean $\frac{\sum w \ell}{\sum w}$. Multi-class Focal Loss must be normalized by $\sum \alpha_{y_i}$ to prevent a 10x scale divergence against CE and Dice.
  - Native PyTorch boundary extraction via `1.0 - max_pool2d(1.0 - x)` matches OpenCV `cv2.erode` bit-for-bit with 0 difference, enabling fast, GPU/CPU boundary IoU computation.
  - Designed `SegmentationMetrics` accumulator maintaining a $4 \times 4$ confusion matrix in $O(1)$ RAM, reporting mIoU (present & all), Wall mIoU (present & all), per-class Dice, Precision, Recall, Boundary IoU, and confusion matrix.
- **Unexplored areas**: None within the scope of loss and metrics exploration. Implementation in `drywall_detection/models/losses.py` and `drywall_detection/models/metrics.py` is handed off to worker.

## Key Decisions Made
- Use inverse frequency weighting with smoothing $\log(1.02 + p_c)$ to prevent extreme weight explosions on rare classes.
- Formulate multi-class Soft Dice Loss over softmax probabilities with squared denominator and $\epsilon=1e-6$ for smooth gradients.
- Implement multi-class Focal Loss using focused Cross Entropy $-\alpha_c (1 - p_{i,c})^\gamma \log(p_{i,c})$ normalized by $\sum \alpha_{y_i}$.
- Design `SegmentationMetrics` accumulator using a $4 \times 4$ confusion matrix to maintain full state in $O(1)$ memory.
- Primary training KPI established as `wall_mean_iou_present` to eliminate background domination bias.

## Artifact Index
- `BRIEFING.md` — Agent state and working memory
- `DISPATCH.md` — Task dispatch instructions
- `progress.md` — Heartbeat and step tracking
- `analysis.md` — Full mathematical specification, interface designs, test cases
- `handoff.md` — 5-component handoff report
