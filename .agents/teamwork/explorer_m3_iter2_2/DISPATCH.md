# Dispatch: M3 Iteration 2 Explorer 2 (Review Lock & CSV Validation)

You are explorer_m3_iter2_2, the Review Lock & CSV Validation Explorer for Milestone M3 Iteration 2.

Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m3_iter2_2
Your parent is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the project architecture at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
and the adversarial challenge report from challenger_m3_2 at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m3_2\handoff.md

## Background & Objective
In Milestone M3 Iteration 1, the gate failed due to 5 edge-case vulnerabilities reported by `challenger_m3_2` in `drywall_detection/tests/test_adversarial_m3.py`.
Your focus is **Review Lock Protocol & CSV Schema Hardening** in `drywall_detection/vector/schedule_parser.py`:
1. Empty (0-byte) approved CSV bypass:
   - Line 624-636: Currently `if appr_csv.exists():` does not check file size. An empty file unlinks the lockfile and returns True.
   - Test `test_empty_approved_csv_must_not_bypass_lock` failed.
2. Invalid/corrupted headers in approved CSV:
   - If headers do not contain `"tag"` and `"proposed_class"`, it silently unlinks lockfile and returns True.
   - Test `test_invalid_header_approved_csv_must_not_bypass_lock` failed.
3. Approved CSV omitting Detail 1A row:
   - If approved CSV omits row for `1A`, it silently unlinks lockfile.
   - Test `test_missing_detail_1a_row_must_not_bypass_lock` failed. Detail 1A mandatory presence must be validated.

DO NOT modify source code. Produce concrete analysis and recommended code diffs.
Write your report to `report.md` and handoff to `handoff.md`, then send a message to parent orchestrator.


## 2026-11-08T11:09:46Z
You are explorer_m3_iter2_2, the Review Lock & CSV Validation Explorer for Milestone M3 Iteration 2.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m3_iter2_2
Your parent is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

Read instructions in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m3_iter2_2\DISPATCH.md`.
Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m3_2\handoff.md`.

Investigate Failures 3, 4, 5 from `test_adversarial_m3.py`:
1. Empty (0-byte) approved CSV bypass.
2. Invalid/corrupted headers in approved CSV.
3. Approved CSV omitting Detail 1A row.

Formulate exact diffs for `drywall_detection/vector/schedule_parser.py` (`export_and_enforce_review_lock`) to resolve all 3 failures. Do NOT edit source code files. Write your report to `report.md` and handoff report to `handoff.md`.
Send a completion message to the parent orchestrator.
