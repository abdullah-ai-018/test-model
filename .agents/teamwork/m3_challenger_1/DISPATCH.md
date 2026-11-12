# Dispatch: Milestone M3 Model Architecture & Tensor Stress Challenger (`m3_challenger_1`)

## Mission
Empirically stress-test the model architectures (`segformer.py`, `unet.py`), standalone inference reload (`infer.py`), input dimension variations, multi-page PDF processing, and tensor memory footprints under hostile edge cases.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (Workspace root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - Sections 1, 4.4, 5, and 6.
3. `drywall_detection/models/segformer.py`, `unet.py`.
4. `drywall_detection/checkpoints/best_model/infer.py` and `best_model.pt`.

## Adversarial Stress Tasks
Write and execute an adversarial stress test script (e.g. `drywall_detection/tests/test_m3_adversarial_arch.py`) evaluating:
1. **Dynamic Resolution & Aspect Ratio Stress**:
   - Forward passes on non-square resolutions ($512 \times 256$, $256 \times 512$, $1024 \times 768$, $384 \times 384$).
   - Forward passes on odd/prime dimensions ($513 \times 513$, $511 \times 511$) ensuring decoder upsampling handles rounding.
2. **Extreme Batch Size & Memory Bounds**:
   - Batch size $B=1$, $B=4$, $B=8$.
   - Verify peak memory consumption on CPU remains $< 500$ MB.
3. **Corrupted & Extreme Tensor Inputs**:
   - All-zero input tensors, all-one input tensors, extreme values ($[-10^6, +10^6]$), NaN/Inf inputs (asserting graceful handling or exception interception).
4. **Standalone Inferencer Offline Reload Stress**:
   - Test reloading `best_model.pt` from disk in an isolated process.
   - Test sliding-window Hann apodization stitching on high-resolution canvas ($2048 \times 2048$) with varying overlap factors (0.1, 0.25, 0.5).
   - Test multi-page PDF processing pipeline via `infer.py` on workspace sample PDFs.
5. **Verdict**:
   - Deliver an explicit verdict: **APPROVE** or **REQUEST_CHANGES**.

## Deliverables
- Author `.agents/teamwork/m3_challenger_1/handoff.md` following the Handoff Protocol.
- Send completion message to parent orchestrator.


## 2026-11-08T20:09:09Z
You are `m3_challenger_1`, the Model Architecture & Reload Challenger for Milestone M3 ("Model Benchmarking, Hardware Adaptation & Checkpoint Delivery").

Your mission is to empirically stress-test the model architectures (`segformer.py`, `unet.py`), standalone inference reload (`infer.py`), input dimension variations, multi-page PDF processing, and tensor memory footprints under hostile edge cases.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_challenger_1\

Read your dispatch file first:
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_challenger_1\DISPATCH.md`

Also read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_worker_1\handoff.md`

Deliverables:
- Author `handoff.md` in your state folder with an explicit verdict: APPROVE or REQUEST_CHANGES.
- Send completion message to parent orchestrator via `send_message`.
