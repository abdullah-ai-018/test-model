# Dispatch: m1_r2_explorer_3

- **Role**: Test Design & Validation Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation - Iteration 2)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Reviewer Failure Report to Fix**:
  `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md`

## Problem to Investigate & Plan Fix Strategy
Reviewer `m1_reviewer_2` identified that existing unit tests in `drywall_detection/tests/unit/test_datasets.py` tested hard negative filtering on only a single tile in isolation, which masked the lack of quota enforcement across multi-tile drawings.

Your tasks:
1. Formulate comprehensive unit test specifications for `drywall_detection/tests/unit/test_datasets.py`:
   - Test a multi-tile drawing (e.g. 2000x2000) with 1 wall tile and 24 hard negative tiles, asserting that retained hard negatives strictly do not exceed `max_hard_negative_ratio` (15%).
   - Test drawings with 0 wall tiles, verifying hard negative capping behavior.
   - Test varying `max_hard_negative_ratio` values (0.05, 0.15, 0.30, 0.0) and verify that retained ratios match expectations.
   - Test quarantine isolation validation in `verify_split_isolation()`.
   - Test `validate_mask_array()` standalone function.
2. Do NOT implement the code yourself (Explorer archetype). Formulate the test design and verification assertions in `analysis.md` and `handoff.md`.
3. Notify orchestrator via send_message when done.


## 2026-11-07T21:27:25Z
You are m1_r2_explorer_3. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
And the Reviewer failure report: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_reviewer_2\handoff.md

Role: Test Design & Validation Explorer
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_r2_explorer_3

Your task:
Design comprehensive unit tests for multi-tile hard negative quota verification, zero wall drawings, varying quota ratios, quarantine validation, and validate_mask_array().
Write analysis.md and handoff.md in your state folder.
Notify the orchestrator via send_message when done.
