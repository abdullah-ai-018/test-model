# DISPATCH — Milestone M3 Iteration 2 Implementation Worker (m3_worker_2)

## Mission
Apply targeted remediation fixes for Milestone M3 based on verified findings from Explorers `m3_iter2_explorer_1`, `m3_iter2_explorer_2`, and `m3_iter2_explorer_3`:
1. Synchronize `config.json` resolution and tile metadata to 512x512.
2. Update `trainer.py` defaults to 512x512 and confirm drawing-level test split isolation assertions.
3. Ensure `metrics.py` has test split manifest drawing checks and test split quarantine assertions.
4. Harden `infer.py` with `import time`, dynamic `tile_size` reading from config, and small-canvas sliding-window padding guard.
5. Add automated regression tests `test_infer_cli_invocation` and `test_standalone_inferencer_small_canvas_guard` to `test_models.py`.
6. Run full verification suites and author `handoff.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Input Artifacts
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_1\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_2\handoff.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_3\analysis.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_3\handoff.md`

## File Ownership
- `drywall_detection/checkpoints/best_model/config.json`
- `drywall_detection/models/trainer.py`
- `drywall_detection/models/metrics.py`
- `drywall_detection/checkpoints/best_model/infer.py`
- `drywall_detection/tests/test_models.py`

## Deliverables
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_worker_2\analysis.md`
- `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_worker_2\handoff.md`


## 2026-11-09T07:27:36Z
You are m3_worker_2, the Milestone M3 Iteration 2 Implementation Worker.
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_worker_2
Parent conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP:
Read these specification documents before starting work:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_1\handoff.md
4. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_2\handoff.md
5. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_3\analysis.md
6. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_iter2_explorer_3\handoff.md

FILE OWNERSHIP (Exclusive write access):
- drywall_detection/checkpoints/best_model/config.json
- drywall_detection/models/trainer.py
- drywall_detection/models/metrics.py
- drywall_detection/checkpoints/best_model/infer.py
- drywall_detection/tests/test_models.py

OBJECTIVE & REQUIRED IMPLEMENTATION TASKS:
1. In drywall_detection/checkpoints/best_model/config.json:
   - Synchronize resolution and tile metadata (lines 8–17):
     "input_size": [512, 512],
     "input_resolution": [512, 512],
     "tile_size": 512,
     "tile_overlap": 102
2. In drywall_detection/models/trainer.py:
   - In Trainer.save_checkpoint (line 422 and lines 438–441), update default metadata to:
     "input_size": [512, 512],
     "input_resolution": [512, 512],
     "tile_size": 512,
     "tile_overlap": 102
   - Ensure lines 98–108 in verify_split_isolation contain the drawing-level train/test and val/test intersection checks:
     if test_drawings:
         draw_train_test = train_drawings.intersection(test_drawings)
         if draw_train_test:
             raise ValueError(f"Drawing leakage detected between Train and Test: {draw_train_test}")
         draw_val_test = val_drawings.intersection(test_drawings)
         if draw_val_test:
             raise ValueError(f"Drawing leakage detected between Val and Test: {draw_val_test}")
3. In drywall_detection/models/metrics.py:
   - Ensure assert_zero_leakage_manifests extracts te_draws, checks t_draws & te_draws and v_draws & te_draws, checks t_imgs & te_imgs and v_imgs & te_imgs, and checks quarantine/pseudo-label flags on ("test", te_tiles) as well as ("validation", v_tiles).
4. In drywall_detection/checkpoints/best_model/infer.py:
   - Confirm line 28 has "import time".
   - In StandaloneInferencer.__init__, dynamically read tile_size:
     self.tile_size = int(self.config.get("tile_size") or 512)
     self.hann_window = create_hann_window(self.tile_size)
   - In predict_tile, resize tile_img to (self.tile_size, self.tile_size) if size differs.
   - Confirm small-canvas bounds guard is present in predict_image_sliding_window (padding images smaller than tile_size with white background and slicing back to original dimensions upon exit).
5. In drywall_detection/tests/test_models.py:
   - Append test_infer_cli_invocation(tmp_path) and test_standalone_inferencer_small_canvas_guard() at the end of Test Group 6 (see exact code in m3_iter2_explorer_3/analysis.md Section 5).

VERIFICATION COMMANDS TO RUN:
Execute and document all results in your handoff report:
1. python -m pytest drywall_detection/tests/test_models.py -k "test_infer_cli_invocation or test_standalone_inferencer" -v
2. python -m pytest drywall_detection/tests/test_m3_adversarial_loss_splits.py -v (18/18 must pass)
3. python drywall_detection/checkpoints/best_model/infer.py --help (exit code 0)
4. python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
   Verify valid JSON summary with "status": "success", dimensions [1024, 1024], and clean up test_overlay.png.
5. python -c "from drywall_detection.models.metrics import assert_zero_leakage_manifests; from pathlib import Path; p = Path('drywall_detection/data/processed/splits'); assert_zero_leakage_manifests(p/'train.json', p/'val.json', p/'test.json'); print('PASS CLEAN')"
6. Fast regression suite:
   python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_data.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py -v (115/115 must pass)

DELIVERABLES:
- Write progress.md in your state folder at each step with "Last visited" timestamp.
- Write analysis.md with detailed implementation notes.
- Write handoff.md following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Notify caller via send_message when complete.
