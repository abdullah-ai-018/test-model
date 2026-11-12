## 2026-11-07T20:42:11Z
You are explorer_m1_3 (role: M1 Test Suite & Report Architect).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your private state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_3

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. Read the master project scope at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Read the survey reports for reference:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\report.md
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_2\report.md
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3\report.md

Milestone M1 Objective: Workspace and Dataset Audit.
Your Task:
Investigate and design the technical plan for:
1. Verification and unit test suites implemented from scratch inside `drywall_detection/tests/`:
   - `drywall_detection/tests/test_coords.py`: unit tests verifying coordinate bijection forward and backward transforms, rotation handling, Shapely polygon transforms, and identity invariants.
   - `drywall_detection/tests/test_hardware.py`: unit tests verifying hardware probing functions (CPU, RAM, disk, CUDA check, auto-config recommendations).
   - `drywall_detection/tests/test_audit.py`: unit tests verifying dataset auditor functionality (mocking API responses, checking disk space thresholds, verifying 10GB warning trigger, testing license and label validation).
2. Report structure for Milestone M1 in `drywall_detection/reports/M1_audit_report.md`:
   - Must cover workspace cleanliness and isolation verification.
   - Must document reference PDF properties (71 pages, 90° rotation, 1728x2592 pt MediaBox, sheet catalog, sheets A-900/A-901).
   - Mandatory notice: record that 99th Street PDF is a 95% CDs progress set and a single-project calibration sample that cannot prove generalization.
   - Must document hardware specifications and constraints (CPU, RAM 0.9GB free, CPU-only PyTorch, disk headroom).
   - Must document complete audit of the 6 candidate datasets (CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, MSD) with sources, licenses, formats, and wall segmentation eligibility.

Do NOT implement the code files directly in `drywall_detection/` (that is the Worker's responsibility).
Formulate a concrete, step-by-step implementation strategy with test case specifications, assertion criteria, and report outline.
Create your state folder `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_3` if needed, write your findings to `report.md` and `handoff.md` in your state folder, and send a completion message to the orchestrator.
