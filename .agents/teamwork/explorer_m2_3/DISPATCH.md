## 2026-11-07T21:45:01Z
You are explorer_m2_3 (M2 Data Splitter & QC Explorer).
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_3
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model

Read these files first:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read before starting work)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M1_audit_report.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py

Your Mission:
Architect the project-isolated data partitioning module (`drywall_detection/data/splitter.py`), visual QC module (`drywall_detection/data/qc.py`), test suite (`drywall_detection/tests/test_data.py`), and report template (`drywall_detection/reports/M2_dataset_report.md`).
1. Data Splitter Architecture:
   - Strict project/building isolation: group drawings by `site_id` / `building_id`.
   - Ratios: 70% Train, 15% Validation, 15% Independent Test.
   - Zero-overlap guarantee: assert `set(train_projects) & set(val_projects) == empty`, `set(train_projects) & set(test_projects) == empty`, `set(val_projects) & set(test_projects) == empty`.
   - Output format: split manifests in `drywall_detection/data/splits/{train,val,test}.json`.
2. Visual QC Architecture:
   - Generate visual quality control sample triplets (original drawing, ground-truth mask, semi-transparent color overlay) for a representative sample across splits.
   - Output QC images to `drywall_detection/reports/qc_samples/`.
3. Design comprehensive test suite in `drywall_detection/tests/test_data.py`:
   - Test project-isolated splitting invariants (0% leakage).
   - Test mask dimensions, class values, and coordinate bounds.
   - Test disk safety and threshold checks.
4. Outline the complete structure for `drywall_detection/reports/M2_dataset_report.md` (mandatory 95% CDs notice, dataset statistics, split sizes, visual QC observations).
5. Write your findings to `.agents/teamwork/explorer_m2_3/analysis.md` and summarize in `.agents/teamwork/explorer_m2_3/handoff.md`.
6. Send a message to the orchestrator when complete. Do NOT write source code to drywall_detection/ (you are a read-only Explorer).
