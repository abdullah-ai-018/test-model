# Task Assignment: Milestone M2 Challenger 2 (Safety Veto, Review Lock & Split Isolation Adversarial Stress)

- **Assigned Agent**: `m2_r2_challenger_2` (`teamwork_challenger`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Date**: 2026-11-08

## 1. Required Reading
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Verbatim user requirements)
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Architecture, contracts, zero-tolerance rules)
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md` (Worker implementation report)

## 2. Adversarial Testing Mission
Empirically stress-test the security invariants, review lock protocol, and split isolation:
1. **Detail 1A Safety Veto Bypass Attacks**:
   - Test adversarial injections attempting to reclassify Detail 1A as Drywall, GWB, Gypsum, Sheetrock, or aliases.
   - Test case variations, whitespace padding (`"  DRYWALL  "`), and numeric mappings (`"1"`).
   - Verify that `schedule_parser.py` raises `ValueError("INTEGRITY VIOLATION...")` on unapproved/tampered inputs.
   - Verify that `spatial_matcher.py` raises `ValueError("INTEGRITY VIOLATION...")` when given a tampered schedule dictionary.
2. **Review Lock Security Edge Cases**:
   - Test 0-byte approved CSV file (must NOT bypass lock).
   - Test missing mandatory headers (`tag`, `proposed_class`).
   - Test empty row sets or missing Detail 1A row.
   - Test binary corruption / non-UTF-8 inputs.
3. **Split Manifest Zero-Leakage Invariants**:
   - Verify disjointness between `train.json`, `val.json`, and `test.json` at project and drawing levels.
   - Verify quarantine isolation of MTA 99th St weak pseudo-labels (Sheets A-105+).
4. Run:
   `python -m pytest drywall_detection/tests/test_adversarial_m3.py drywall_detection/tests/test_schedule.py -v`
5. Write `handoff.md` in your state folder with an explicit verdict: `APPROVE` or `REQUEST_CHANGES`. Include concrete empirical findings and test output.
6. Send a message to the orchestrator with your verdict.


## 2026-11-08T11:36:34Z
You are m2_r2_challenger_2 (Milestone M2 Safety Veto, Review Lock & Split Isolation Challenger).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_2

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_r2_challenger_2\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1\handoff.md

Adversarially challenge drywall_detection/vector/schedule_parser.py, spatial_matcher.py safety veto, and split manifests.
Run the test commands:
python -m pytest drywall_detection/tests/test_adversarial_m3.py drywall_detection/tests/test_schedule.py -v
Stress test Detail 1A safety veto bypass attacks (whitespace, synonym attacks, memory mutation), review lock protocol (0-byte CSV, bad headers, missing 1A row), and split manifest zero-leakage invariants.
Author handoff.md with an explicit verdict (APPROVE or REQUEST_CHANGES) and send a message to the orchestrator.
