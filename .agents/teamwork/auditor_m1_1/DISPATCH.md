## 2026-11-07T20:59:38Z
You are auditor_m1_1 (role: M1 Forensic Auditor).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your private state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\auditor_m1_1

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. Read the master project scope at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Read the Worker handoff at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m1_1\handoff.md

Forensic Integrity Audit Task:
You are the independent Forensic Auditor with BINARY VETO POWER.
Perform comprehensive static and runtime integrity verification on the Milestone M1 work product in `drywall_detection/`:
1. Static Analysis for Cheating:
   - Check all code files under `drywall_detection/` for hardcoded test inputs, dummy/stub implementations, short-circuited logic, fabricated metrics, or mock bypasses in production code.
   - Verify that test assertions in `tests/test_coords.py`, `tests/test_hardware.py`, and `tests/test_audit.py` test real logic rather than self-asserting trivial constants.
2. Domain & Integrity Check:
   - Verify Tag 1A classification rule: check that Tag 1A (6" Fire-Rated CMU) is strictly classified as Non-Drywall, NOT Drywall.
   - Check workspace boundary: verify that NO files outside `drywall_detection/` (and `.agents/teamwork/`) were modified or created.
   - Verify that reference PDF data (71 pages, 90° rotation, MediaBox 1728x2592 pt) and candidate dataset audit facts are genuine and derived from empirical truth rather than hallucinated.
   - Verify that `reports/M1_audit_report.md` contains the mandatory disclosure that the 99th Street PDF is a 95% CDs progress set and single-project calibration sample.
3. Execution Validation:
   - Run the full test suite independently: `python -m pytest drywall_detection/tests/ -v`.
   - Verify that tests actually execute real code and pass cleanly.
4. Binary Verdict:
   - If ANY cheating, hardcoding, facade implementation, or unauthorized modification is found: issue **INTEGRITY VIOLATION** (with full evidence).
   - If all implementations are genuine, authentic, and compliant: issue **CLEAN**.
5. Write your forensic audit report to `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\auditor_m1_1\report.md` and `handoff.md`, and send a completion message with your verdict to the orchestrator.
