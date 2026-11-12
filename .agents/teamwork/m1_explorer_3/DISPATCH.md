# Dispatch: m1_explorer_3

- **Role**: Split Strategy & Dataset Loader Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

## Objective
Read ORIGINAL_REQUEST.md and PROJECT.md. Formulate the drawing-level split integrity manager and PyTorch dataset loader interface.
1. Design the drawing-level split manager (`drywall_detection/datasets/split_manager.py`) enforcing zero project/drawing overlap between train, validation, and test splits (grouped by drawing or project ID, e.g. 70% train, 15% val, 15% test).
2. Design the PyTorch `Dataset` and `DataLoader` classes that ingest unified tiles, apply data augmentations (flips, 90-degree rotations, contrast), and return normalized image tensors `[3, 512, 512]` and segmentation masks `[512, 512]`.
3. Design unit test specifications for `drywall_detection/tests/unit/test_datasets.py` to verify licensing audit, conversion, QC generation, split isolation, and DataLoader batching.
4. Recommend concrete implementation steps for the Worker.
5. Record findings in analysis.md and write a complete handoff.md.


## 2026-11-07T20:41:48Z
You are m1_explorer_3. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

Role: Split Strategy & Dataset Loader Explorer
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3

Your tasks for Milestone M1 (Dataset Research, Licensing Audit & Unified Preparation):
1. Design drawing-level split integrity manager `drywall_detection/datasets/split_manager.py` ensuring zero project/drawing overlap across train/val/test splits.
2. Design PyTorch `Dataset` and `DataLoader` classes that stream unified tiles and yield normalized `[3, 512, 512]` images and `[512, 512]` long masks.
3. Formulate unit testing specifications for `drywall_detection/tests/unit/test_datasets.py`.
4. Maintain liveness in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\progress.md.
5. Write your comprehensive analysis in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\analysis.md and handoff in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\handoff.md.
6. Notify the orchestrator via send_message when done with the path to your handoff.md.
