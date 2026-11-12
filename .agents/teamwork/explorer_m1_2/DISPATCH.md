## 2026-11-07T20:42:03Z
You are explorer_m1_2 (role: M1 Dataset Auditor Architecture Explorer).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your private state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_2

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. Read the master project scope at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. Read the survey reports for reference:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3\report.md

Milestone M1 Objective: Workspace and Dataset Audit.
Your Task:
Investigate and design the technical implementation plan for:
1. `drywall_detection/audit/dataset_auditor.py`: A comprehensive DatasetAuditor class that:
   - Audits all 6 candidate datasets: CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD Floorplans, and Modified Swiss Dwellings (MSD).
   - Formulates structured verification checks: official source URLs, API endpoints, download mechanisms, license terms, image/annotation formats, presence of wall segmentation labels, eligibility verdict (Eligible / Conditional / Ineligible).
   - Enforces disk space checking before any download, flagging if available disk < download size, and enforcing the requirement to notify the user before any download over 10 GB.
   - Enforces zero license acceptance on user's behalf and flags datasets requiring login/agreements (e.g., R2V requiring NII IDR agreement).
   - Generates structured JSON and Markdown summary tables.
   - Provides a standalone CLI entry point (`python -m drywall_detection.audit.dataset_auditor`).

Do NOT implement the code files directly in `drywall_detection/` (that is the Worker's responsibility).
Formulate a concrete, step-by-step implementation strategy with exact class definitions, method signatures, data structures, and CLI interface.
Create your state folder `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m1_2` if needed, write your findings to `report.md` and `handoff.md` in your state folder, and send a completion message to the orchestrator.
