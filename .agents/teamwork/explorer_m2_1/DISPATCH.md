## 2026-11-07T21:45:00Z
Sender: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a
Priority: MESSAGE_PRIORITY_HIGH

You are explorer_m2_1 (M2 Dataset Downloader Explorer).
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_1
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model

Read these files first:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read before starting work)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M1_audit_report.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\hardware.py
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\audit\dataset_auditor.py

Your Mission:
Architect the dataset downloader module for Milestone M2 (Dataset Preparation), located at `drywall_detection/data/downloader.py`.
Primary target: Modified Swiss Dwellings (MSD) dataset (CC BY 4.0, ~174 MB parquet/tabular / 888 MB Zenodo archive, explicit wall WKT geometries, site_id project grouping).
1. Investigate official download endpoints and structure for MSD (Hugging Face `epfl-dcl/modified-swiss-dwellings`, Zenodo 10.5281/zenodo..., or 4TU.ResearchData). Verify that access requires zero login, zero API keys, and zero EULA acceptance.
2. Formulate disk safety pre-flight check using `drywall_detection.utils.hardware.check_disk_safety` before initiating download, honoring the 10 GB user notification limit.
3. Design SHA256 verification, download caching under `drywall_detection/data/raw/msd/`, resume/retry logic with exponential backoff, and progress reporting.
4. Provide complete, exact code blueprints and interface specifications for `downloader.py` and its CLI (`python -m drywall_detection.data.downloader`).
5. Write your findings to `.agents/teamwork/explorer_m2_1/analysis.md` and summarize in `.agents/teamwork/explorer_m2_1/handoff.md`.
6. Send a message to the orchestrator when complete. Do NOT write source code to drywall_detection/ (you are a read-only Explorer).
