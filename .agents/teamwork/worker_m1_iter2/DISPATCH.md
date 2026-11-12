## 2026-11-07T21:26:37Z

You are worker_m1_iter2 (role: M1 Remediation Worker).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your private state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m1_iter2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. Read the master project scope at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Read the Challenger 2 findings report:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m1_2\report.md
4. Read the detailed remediation blueprints provided by the M1 Iteration 2 Explorer triad:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_1\report.md (Diffs for hardware.py)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_2\report.md (Diffs for dataset_auditor.py and audit/__init__.py)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_3\report.md (Test suite updates for test_adversarial_m1.py, test_audit.py, test_hardware.py)

WRITE OWNERSHIP:
You exclusively own and will modify:
- drywall_detection/utils/hardware.py
- drywall_detection/audit/dataset_auditor.py
- drywall_detection/audit/__init__.py
- drywall_detection/tests/test_adversarial_m1.py
- drywall_detection/tests/test_audit.py
- drywall_detection/tests/test_hardware.py

IMPLEMENTATION TASKS:
1. Apply the blueprint diffs to `drywall_detection/utils/hardware.py`:
   - Add negative required free space validation (`required_free_gb >= 0.0`) in `check_disk_safety()`.
   - Add safe `None`-coalescing helper functions in `auto_configure_training()` to handle dictionaries with explicit `None` values without raising `TypeError`.
2. Apply the blueprint diffs to `drywall_detection/audit/dataset_auditor.py` and `drywall_detection/audit/__init__.py`:
   - Add negative required disk space guard (`required_gb >= 0.0`) in `check_disk_space()`.
   - Update 10 GB threshold checks in `check_disk_space()` and `audit_candidate()` to evaluate both archive download and uncompressed extraction footprints against `max_unannounced_gb` using `>=` comparison (ensuring CubiCasa5K's 20 GB extraction and R2V's 10.00 GB trigger the threshold warning).
   - Convert eager imports in `drywall_detection/audit/__init__.py` to PEP 562 lazy attribute loading via `__getattr__` and `__dir__`.
3. Update test assertions in `drywall_detection/tests/test_adversarial_m1.py`, `drywall_detection/tests/test_audit.py`, and `drywall_detection/tests/test_hardware.py` per `explorer_m1_iter2_3`'s blueprint to assert the hardened behavior (raising `ValueError` on negative disk allocations, safe auto-config on `None` values, CubiCasa5K extraction warning, and R2V 10 GB threshold).
4. Run the full test suite: execute `python -m pytest drywall_detection/tests/ -v` and ensure 100% of all tests pass.
5. Run the CLIs: `python -m drywall_detection.audit.dataset_auditor --format json` and `python -m drywall_detection.utils.hardware` and verify clean execution with zero `RuntimeWarning`.
6. Write your handoff report to `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m1_iter2\handoff.md` and send a completion message with summary to the orchestrator.
