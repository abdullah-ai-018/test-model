# Task Assignment: Milestone M2 Reviewer 2 (Schedule Parser & Ground Truth Pipeline)

- **Assigned Agent**: `m2_r2_reviewer_2` (`teamwork_reviewer`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_reviewer_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Date**: 2026-11-08

## 1. Required Reading
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Verbatim user requirements)
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Architecture, contracts, zero-tolerance rules)
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md` (Worker implementation report)

## 2. Review Scope & Files to Inspect
- `drywall_detection/vector/schedule_parser.py` (24 assembly details, 4-class taxonomy, Detail 1A 6" CMU Non-Drywall safety veto, review lock protocol verifying non-zero size, required headers, and 1A presence).
- `drywall_detection/data/ground_truth_builder.py` (Usman 239 red wall centerlines rasterization into 150 DPI Mode 'P' 8-bit indexed PNG masks with 8.35 pt buffer, `validate_mask_array()` compliance, zero-leakage split manifests).
- `drywall_detection/data/partition_schedule_mapping.csv` and `drywall_detection/data/partition_schedule_mapping.approved.csv`.
- `drywall_detection/data/processed/masks_ground_truth/` and `drywall_detection/data/processed/splits/`.
- `drywall_detection/tests/test_schedule.py` and `drywall_detection/tests/test_adversarial_m3.py`.

## 3. Review Responsibilities
1. Run the test commands:
   `python -m pytest drywall_detection/tests/test_schedule.py drywall_detection/tests/test_adversarial_m3.py -v`
2. Objectively review AND adversarially challenge the code for:
   - Absolute enforcement of Detail 1A Non-Drywall CMU safety veto (cannot be bypassed by GWB synonyms, whitespace, or tampering).
   - Human review lock protocol robustness (rejection of empty CSV, bad headers, missing 1A row).
   - Ground truth rasterization fidelity (Mode 'P', 256 palette, physical thickness, validated array shape).
   - Zero project/drawing leakage across train, val, and test splits.
3. Write `handoff.md` in your state folder with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`. Include detailed evidence and test execution outputs.
4. Send a message to the orchestrator with your verdict.


## 2026-11-08T11:36:21Z
You are m2_r2_reviewer_2 (Milestone M2 Schedule Parser & Ground Truth Pipeline Reviewer).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_reviewer_2

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_reviewer_2\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md

Review drywall_detection/vector/schedule_parser.py and drywall_detection/data/ground_truth_builder.py.
Run the test commands:
python -m pytest drywall_detection/tests/test_schedule.py drywall_detection/tests/test_adversarial_m3.py -v
Verify 24 details, 4-class taxonomy, Detail 1A 6" CMU Non-Drywall veto, review lock protocol, Usman 239 red lines rasterization into 150 DPI Mode 'P' 8-bit indexed PNG masks with 8.35 pt buffer, validate_mask_array, and zero-leakage split manifests.
Author handoff.md with an explicit verdict (APPROVE or REQUEST_CHANGES) and send a message to the orchestrator.
