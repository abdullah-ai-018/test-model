# Milestone M3 Architecture & Interface Review Report

**Agent**: `m3_reviewer_1` (Model Architecture & Interface Reviewer / Adversarial Critic)  
**Recipient**: `parent` (Milestone M3 Orchestrator / Project Team)  
**Date**: 2026-11-09T01:22:00Z  
**Type**: Hard Handoff (Milestone M3 Review Complete)  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct empirical observations, tool commands, verbatim outputs, and code references:

1. **Standalone Inference CLI Execution Failure (`drywall_detection/checkpoints/best_model/infer.py`)**:
   - Tool Command Executed:
     ```powershell
     python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
     ```
   - Verbatim Tool Output (Exit Code 1):
     ```text
     Traceback (most recent call last):
       File "C:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\checkpoints\best_model\infer.py", line 412, in <module>
         main()
       File "C:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\checkpoints\best_model\infer.py", line 354, in main
         t0 = time.time()
     NameError: name 'time' is not defined
     ```
   - Inspection of `drywall_detection/checkpoints/best_model/infer.py` lines 20–36:
     ```python
     import argparse
     import json
     import logging
     import os
     import sys
     from pathlib import Path
     from typing import Any, Dict, List, Optional, Tuple, Union

     import numpy as np
     from PIL import Image
     import torch
     import torch.nn.functional as F
     import torchvision.transforms.functional as TF
     ```
     `import time` is completely missing from top-level imports.
   - Lines 354, 374, and 406 invoke `time.time()`, causing an unhandled fatal `NameError` whenever `main()` processes an image or PDF.
   - Command `python drywall_detection/checkpoints/best_model/infer.py --help` exited with code 0 only because `argparse.parse_args()` exits prior to line 354.

2. **Model Architecture Inspection**:
   - `drywall_detection/models/segformer.py`:
     - Class `SegFormerWallDetector` (alias `SegFormerB0`) wraps `transformers.SegformerForSemanticSegmentation` with `SegformerConfig`.
     - Parameter count: `model.count_parameters()` = **3,715,172 (~3.72M)** parameters.
     - Upsampling logic: Line 130–135 applies `F.interpolate(raw_logits, size=(H, W), mode="bilinear", align_corners=False)` restoring input resolution from $[B, 4, H/4, W/4]$ to $[B, 4, H, W]$.
     - Offline fallback: Lines 85–108 safely fall back to local offline random initialization when `offline=True` or Hugging Face Hub download fails.
   - `drywall_detection/models/unet.py`:
     - Class `UNetWallDetector` implements native TorchVision `resnet18` encoder + 4-stage convolutional decoder (`dec4`, `dec3`, `dec2`, `dec1`, `dec0`) with skip connections.
     - Parameter count: `model.count_parameters()` = **14,343,524 (~14.34M)** parameters.
     - Offline fallback: Defaults to `weights=None` when offline or download fails.

3. **Checkpoint Packaging Contract (`PROJECT.md` Section 4.4)**:
   - Evaluated `drywall_detection/checkpoints/best_model/`:
     - `best_model.pt` (44,836,021 bytes) — Present.
     - `config.json` (751 bytes) — Present.
     - `class_mapping.json` (88 bytes) — Present.
     - `training_log.json` (838 bytes) — Present.
     - `metrics.json` (1,532 bytes) — Present.
     - `infer.py` (13,780 bytes) — Present, but crashes at runtime as observed in Observation 1.
     - `README.md` (6,421 bytes) — Present.
     - `sample_overlays/` (`tile_0_comparison.png`, `tile_0_overlay.png`, `sample_01_original.png`, `sample_01_mask.png`, `sample_01_overlay.png`) — Present.

4. **Resolution Metadata Discrepancy**:
   - `drywall_detection/checkpoints/best_model/config.json` specifies:
     - `"input_size": [256, 256]`
     - `"input_resolution": [256, 256]`
     - `"tile_size": 256`
   - In contrast, `infer.py` lines 63, 96, 151 hardcode:
     - `def create_hann_window(tile_size: int = 512)`
     - `self.hann_window = create_hann_window(512)`
     - `if tile_img.size != (512, 512): tile_img = tile_img.resize((512, 512), Image.BILINEAR)`

5. **Test Suite Execution**:
   - Command: `python -m pytest drywall_detection/tests/test_models.py -v`
     - Result: `17 passed in 337.10s (0:05:37)`.
     - Finding: `test_models.py` tests `StandaloneInferencer` directly via Python API (`predict_tile`, `predict_image_sliding_window`), but contains zero test cases invoking `infer.py` as a CLI subprocess (`python infer.py ...`). Consequently, the `NameError` in `main()` went undetected by the automated test suite.
   - Command: `python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_data.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py -v`
     - Result: `115 passed in 61.18s (0:01:01)`. Full regression passing across M1 and M2 test targets.

6. **Workspace Layout Compliance**:
   - Inspected `.agents/teamwork/`: Contains exclusively agent metadata markdown files (`BRIEFING.md`, `DISPATCH.md`, `handoff.md`, `progress.md`, `report.md`).
   - Zero source code, tests, or data files present in `.agents/teamwork/`. Fully compliant with `PROJECT.md` Section 5.

---

## 2. Logic Chain

1. **Premise 1 (`PROJECT.md` Section 4.4 & DISPATCH.md Task 2)**: The model checkpoint deliverable contract requires a working standalone `infer.py` script that can reload the champion model and execute inference on an image. DISPATCH Task 2 explicitly specifies: *"Test standalone inference reload on a tile image"*.
2. **Premise 2 (Observation 1)**: Executing `python drywall_detection/checkpoints/best_model/infer.py --input <image> --output <output>` unconditionally raises `NameError: name 'time' is not defined` at line 354 and exits with code 1.
3. **Inference 1**: The delivered `infer.py` script cannot execute image or PDF inference via its command-line interface. The checkpoint packaging deliverable does not satisfy the operational requirement of Milestone M3.
4. **Premise 3 (Observation 5)**: `test_models.py` passed all 17 tests because `test_standalone_inferencer_tile_and_sliding_window` tested only the in-memory class methods, omitting a subprocess execution test of the CLI script itself.
5. **Inference 2**: The test suite has an automated coverage gap for CLI invocation, allowing a breaking entrypoint bug to escape into the delivery bundle.
6. **Premise 4 (Observation 4)**: `config.json` advertises tile size 256, while `infer.py` hardcodes tile size 512.
7. **Inference 3**: Inconsistent metadata creates configuration confusion for downstream integration in Milestone M4.
8. **Synthesis Conclusion**: Because a core deliverable contract (`infer.py` standalone execution) is broken, the review verdict must be **REQUEST_CHANGES**.

---

## 3. Caveats

1. **No Implementation Changes Made**: In accordance with the Reviewer constraint (*"Review-only — do NOT modify implementation code"*), `m3_reviewer_1` did not modify `infer.py`, `config.json`, or any other source files. All fixes must be implemented by the implementation worker.
2. **In-Memory Core Logic Is Sound**: When imported programmatically in Python, `StandaloneInferencer` and the model architectures (`SegFormerB0`, `UNetWallDetector`) function properly and pass all 17 unit and integration tests. The defect is confined to the CLI entrypoint `main()`, configuration parameter alignment, and test coverage.
3. **Host Hardware Timing**: Running `test_models.py` on the constrained Windows CPU takes ~5.5 minutes due to the single-epoch training integration test.

---

## 4. Conclusion & Actionable Recommendations

### Verdict: **REQUEST_CHANGES**

Milestone M3 is close to completion, but cannot be approved until the following actionable items are resolved by the implementation team:

### Actionable Required Fixes:
1. **Fix Missing Import in `infer.py` (Critical)**:
   - Add `import time` to top-level imports in `drywall_detection/checkpoints/best_model/infer.py`.
   - Verify that running:
     ```powershell
     python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
     ```
     executes cleanly, generates `test_overlay.png`, and outputs JSON summary statistics without error.
2. **Add CLI Subprocess Test to `test_models.py` (Major)**:
   - Add a unit test (e.g. `test_infer_cli_invocation`) using `subprocess.run([sys.executable, str(infer_script), "--input", ...], capture_output=True)` to ensure any future entrypoint regressions are caught automatically in CI.
3. **Reconcile Resolution Metadata (Major)**:
   - Reconcile `tile_size` / `input_size` across `config.json` and `infer.py` (use 512 consistently, or allow `infer.py` to dynamically read `tile_size` from `config.json`).
4. **Guard Sliding Window for Small Images (Minor)**:
   - In `predict_image_sliding_window`, add a guard when `image.width < tile_size` or `image.height < tile_size` to resize/pad the canvas before slicing, preventing array shape broadcasting errors.

---

## 5. Verification Method

To verify the required fixes once implemented:

1. **Verify Standalone CLI Inference**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
   ```
   *Pass Condition*: Exits with code 0, prints JSON summary stats with `"status": "success"`, and generates `test_overlay.png`.

2. **Verify CLI Help**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --help
   ```
   *Pass Condition*: Exits with code 0.

3. **Verify Model Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -v
   ```
   *Pass Condition*: 18 passed (including the new CLI subprocess test), 0 failed.

4. **Verify Regression Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_data.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py -v
   ```
   *Pass Condition*: 115 passed.
