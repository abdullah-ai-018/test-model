# Dispatch: Milestone M4 Training Pipeline & Hardware Explorer

You are `explorer_m4_3`, the Training Pipeline & Hardware Explorer for Milestone M4 (Wall Segmentation Training).

Working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
State folder: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3`
Your parent orchestrator is: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`

## MANDATORY FIRST STEP
Read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\hardware.py`
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M1_audit_report.md`

## Objectives
1. **Profile Local Hardware & Adapt Training Configuration**:
   - Inspect CPU cores, RAM, disk space, and CUDA availability via `hardware.py`.
   - Auto-configure training loop parameters:
     - `batch_size`: 2 or 4 (auto-scaled to RAM/VRAM).
     - `num_workers`: 0 (mandatory Windows multiprocessing safety).
     - `torch.set_num_threads()`: tailored to CPU cores.
     - Gradient accumulation steps (to simulate effective batch size of 8 or 16).
     - Early stopping with patience = 5 epochs based on validation mIoU.
2. **Google Colab Compatibility Guarantee**:
   - Design a standalone, reproducible training notebook or runnable script that runs seamlessly on Google Colab with free T4 GPU.
   - Specify dependency installation and mount paths.
3. **Weak Pseudo-Labeling Guardrail for 99th Street PDF**:
   - Vector-extracted geometry from the reference PDF may be used as weak pseudo-labels for fine-tuning ONLY if:
     - Explicitly tagged in metadata as `weak_pseudo_label`.
     - Visually spot-checked for error rate across 5–10 plan regions.
     - Strictly quarantined from validation and test sets (zero leakage).
4. **Deliver Report**:
   - Deliver training loop architecture, Colab runner specification, hardware profiling guidelines, and pseudo-labeling guardrails in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3\handoff.md`.
   - Message parent orchestrator upon completion.


## 2026-11-08T19:08:18Z
You are explorer_m4_3, the Training Pipeline & Hardware Explorer for Milestone M4 (Wall Segmentation Training).

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3
Your parent orchestrator is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

Read instructions in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3\DISPATCH.md`.
Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, `drywall_detection/utils/hardware.py`, and `M1_audit_report.md`.

Investigate:
1. Profile local compute environment (CPU, RAM, disk, Python 3.10) and auto-adapt training configuration (batch size, num_workers=0, gradient accumulation, early stopping).
2. Design 100% Google Colab compatible standalone training workflow with GPU acceleration.
3. Weak pseudo-labeling guardrails for 99th Street PDF extractions (tagging as weak_pseudo_label, spot-checking 5-10 plan regions, strict quarantine from val/test splits).
4. Deliver report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m4_3\handoff.md` and message parent orchestrator.
