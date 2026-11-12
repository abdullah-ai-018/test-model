# Dispatch: Milestone M3 Loss, Boundary IoU & Split Isolation Challenger (`m3_challenger_2`)

## Mission
Empirically stress-test the compound loss function (`losses.py`), evaluation metrics suite (`metrics.py`), Boundary IoU mathematical equivalence, split isolation anti-leakage invariants, and quarantine enforcement.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (Workspace root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - Sections 1, 4.3, 4.4, 5, and 6.
3. `drywall_detection/models/losses.py`, `metrics.py`, `trainer.py`.
4. `drywall_detection/data/processed/splits/splits_summary.json`.

## Adversarial Stress Tasks
Write and execute an adversarial stress test script (e.g. `drywall_detection/tests/test_m3_adversarial_loss_splits.py`) evaluating:
1. **Adversarial Loss Stress**:
   - Zero-frequency classes (p_c = 0) in `calculate_class_weights` -> verify weights strictly <= 50.5, no NaNs/Infs.
   - Empty targets (e.g. all pixels are Class 0) -> verify Soft Dice and Focal loss produce finite scalar without NaNs.
   - Inverse predictions (predicting 100% Class 0 when target is 100% Class 1) -> verify loss increases monotonically and gradients remain non-zero and finite.
   - Extreme logits (e.g. +/- 1000.0) -> verify numerical stability via log-sum-exp stabilization.
2. **Boundary IoU Empirical Rigor**:
   - Compare native PyTorch MaxPool2D morphological erosion against OpenCV `cv2.erode` across 100 synthetic random binary masks of varying radii (1, 2, 3, 5).
   - Assert zero pixel difference ($\sum |cv2 - torch| == 0$).
3. **Split Isolation & Quarantine Adversarial Attacks**:
   - Construct hostile split dictionaries with deliberate leakage:
     - Project ID overlap between train and val.
     - Drawing ID overlap between train and test.
     - Quarantined tile (`quarantine=True`) injected into val split.
     - Pseudo-labeled tile (`is_pseudo_label=True`) injected into test split.
   - Assert that `verify_split_isolation` intercepts every attack with an immediate `ValueError`.
4. **Verdict**:
   - Deliver an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.

## Deliverables
- Author `.agents/teamwork/m3_challenger_2/handoff.md` following the Handoff Protocol.
- Send completion message to parent orchestrator.


## 2026-11-08T20:09:10Z
You are `m3_challenger_2`, the Loss & Split Isolation Challenger for Milestone M3 ("Model Benchmarking, Hardware Adaptation & Checkpoint Delivery").

Your mission is to empirically stress-test the compound loss function (`losses.py`), evaluation metrics suite (`metrics.py`), Boundary IoU mathematical equivalence, split isolation anti-leakage invariants, and quarantine enforcement.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_challenger_2\

Read your dispatch file first:
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_challenger_2\DISPATCH.md`

Also read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_worker_1\handoff.md`

Deliverables:
- Author `handoff.md` in your state folder with an explicit verdict: APPROVE or REQUEST_CHANGES.
- Send completion message to parent orchestrator via `send_message`.
