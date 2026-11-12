# Dispatch: Milestone M3 Iteration 2 Split Isolation & Manifest Integrity Explorer (`m3_iter2_explorer_2`)

## Mission
Analyze the data leakage vulnerabilities reported by `m3_challenger_2` and formulate the exact remediation strategy for `drywall_detection/models/trainer.py` and `drywall_detection/models/metrics.py` to ensure 100% pass on `test_m3_adversarial_loss_splits.py` without regressions.

## References (MUST READ FIRST)
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` - Section 4.3 (Data Split Protocol) & Section 6
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m3_challenger_2\handoff.md` (Challenger report)
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\tests\test_m3_adversarial_loss_splits.py`
5. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\models\trainer.py` (lines 90-120: `verify_split_isolation`)
6. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\models\metrics.py` (lines 330-360: `assert_zero_leakage_manifests`)

## Defects to Analyze
1. **`trainer.py:verify_split_isolation` Drawing Leakage Blindspot**:
   - `test_drawings` is defined, but never compared against `train_drawings` or `val_drawings`.
   - `test_attack_2_drawing_id_overlap_train_test` and `test_attack_7_drawing_id_overlap_val_test` failed because `ValueError` was not raised.
   - Formulate exact intersection checks:
     ```python
     if test_drawings:
         draw_train_test = train_drawings.intersection(test_drawings)
         if draw_train_test:
             raise ValueError(f"Drawing leakage detected between Train and Test: {draw_train_test}")
         draw_val_test = val_drawings.intersection(test_drawings)
         if draw_val_test:
             raise ValueError(f"Drawing leakage detected between Val and Test: {draw_val_test}")
     ```
2. **`metrics.py:assert_zero_leakage_manifests` Test Manifest Blindspot**:
   - `test_drawing_overlap_train_test_manifests` and `test_quarantined_tile_in_test_manifest` failed because drawing leakage and quarantine checks on test manifests were omitted.
   - Formulate exact checks for test drawing overlaps (`t_draws & te_draws`, `v_draws & te_draws`) and including `("test", te_tiles)` in the quarantine/pseudo-label assertion loop.

## Deliverables
- Author `analysis.md` and `handoff.md` in `.agents/teamwork/m3_iter2_explorer_2/`.
- Send completion message to parent orchestrator.
