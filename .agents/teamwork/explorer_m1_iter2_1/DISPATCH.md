## 2026-11-07T21:11:00Z
You are explorer_m1_iter2_1 (role: M1 Hardware Hardening Explorer).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your private state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_1

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. Read the master project scope at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Read the Challenger 2 findings report:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m1_2\report.md

Task:
Design the exact code modification and fix blueprint for `drywall_detection/utils/hardware.py`:
1. `check_disk_safety(required_free_gb, disk_path)`: add explicit guard validating `required_free_gb >= 0.0`. If negative, raise `ValueError("required_free_gb must be non-negative")`.
2. `auto_configure_training(profile)`: replace unsafe `float(profile.get(key, default))` and `int(profile.get(key, default))` with safe `None`-coalescing helper functions (e.g. `val = profile.get(key); float(val if val is not None else default)`), preventing `TypeError` when keys are explicitly set to `None`.
3. Provide exact code diffs and test assertions.
Do NOT modify production files yourself. Write your report to `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_iter2_1\report.md` and `handoff.md`, and message the orchestrator.
