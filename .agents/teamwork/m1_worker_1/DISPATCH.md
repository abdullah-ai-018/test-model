# Dispatch: m1_worker_1

- **Role**: Dataset & Pipeline Worker
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Explorer Reports to Read**:
  * `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1\handoff.md`
  * `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\handoff.md`
  * `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own and may create files inside:
- `drywall_detection/datasets/`
- `drywall_detection/audit/`
- `drywall_detection/data/`
- `drywall_detection/reports/`
- `drywall_detection/tests/`
- `drywall_detection/__init__.py`
Do NOT modify any files outside `drywall_detection/` or outside your state folder.

## Implementation Tasks
1. **Licensing Audit Module & Report** (`drywall_detection/datasets/licensing_audit.py` + facade `drywall_detection/audit/dataset_auditor.py`):
   - Implement audit of candidate datasets (MSD, CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, ArchCAD-400k) verifying official sources, DOIs, licenses, commercial/redistribution terms, and access restrictions.
   - Generate deliverable reports: `drywall_detection/datasets/DATASET_LICENSING_REPORT.md` and `drywall_detection/data/dataset_licensing_audit.json`.
2. **Unified Dataset Preparation & QC Engine** (`drywall_detection/datasets/unified_format.py`):
   - Implement single-channel 8-bit indexed PNG mask standard (`uint8`, Mode 'P', palette: 0=White, 1=Green, 2=Red, 3=Yellow).
   - Implement WKT (MSD), SVG (CubiCasa5K), and raster mask conversion into unified format.
   - Implement sliding-window tiling ($512 \times 512$, 20% overlap, stride 410 px) and 2D Hann apodization reverse stitcher.
   - Implement tile filtering (dropping blank white tiles while retaining hard negative linework within 15% quota).
   - Implement visual QC generator creating composite triplet PNGs `[Drawing Tile | Color Mask | Translucent Overlay]`.
3. **Drawing-Level Split Integrity Manager** (`drywall_detection/datasets/split_manager.py`):
   - Implement greedy multi-way group partitioning enforcing zero project/drawing overlap between train/val/test splits.
   - Implement `verify_split_isolation()` validator that raises `SplitLeakageError` on any overlap.
   - Implement project quarantine support for weak pseudo-labeled sets (e.g. 99th Street).
   - Export `train.json`, `val.json`, `test.json`, and `splits_summary.json` with SHA-256 integrity hashes.
4. **PyTorch Dataset & DataLoader Interface** (`drywall_detection/datasets/loader.py`):
   - Implement low-RAM streaming `DrywallTileDataset` yielding normalized `[3, 512, 512]` float32 image tensors and `[512, 512]` int64 masks.
   - Support 4-class multi-class and binary pretraining modes.
   - Implement synchronized orthographic augmentations via `torchvision.transforms.functional` (no albumentations dependency).
   - Implement `get_tile_dataloader()` with Windows CPU safe defaults (`num_workers=0`, `pin_memory=False`, `batch_size=2`).
5. **Unit Tests & Verification**:
   - Write comprehensive unit tests in `drywall_detection/tests/test_licensing_audit.py` and `drywall_detection/tests/unit/test_datasets.py`.
   - Run `pytest drywall_detection/tests/ -v` and ensure all tests pass.
   - Document commands executed and test outputs in your handoff report.
6. Write your handoff in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1\handoff.md` and notify orchestrator when done.


## 2026-11-07T20:49:59Z
[Message] timestamp=2026-11-07T20:49:59Z sender=3c1a82ae-9b50-494e-b173-0369a8d4a486 priority=MESSAGE_PRIORITY_HIGH content=You are m1_worker_1. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
And the Explorer handoff reports:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1\handoff.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\handoff.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\handoff.md

Role: Dataset & Pipeline Worker
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your implementation tasks for Milestone M1:
1. Implement dataset licensing audit engine in drywall_detection/datasets/licensing_audit.py (and facade in drywall_detection/audit/dataset_auditor.py), and generate deliverable reports: drywall_detection/datasets/DATASET_LICENSING_REPORT.md and drywall_detection/data/dataset_licensing_audit.json.
2. Implement unified dataset format, multi-source conversion (WKT, SVG, raster), 512x512 sliding-window tiling (20% overlap, stride 410 px), 2D Hann apodization reverse stitcher, blank tile filtering with hard-negative retention, and visual QC sample generator in drywall_detection/datasets/unified_format.py.
3. Implement drawing-level split integrity manager in drywall_detection/datasets/split_manager.py with greedy multi-way group partitioning, standalone verify_split_isolation() validator, quarantine support, and JSON manifest exports.
4. Implement low-RAM streaming PyTorch Dataset and DataLoader in drywall_detection/datasets/loader.py with native torchvision synchronized augmentations.
5. Implement and run comprehensive unit tests in drywall_detection/tests/test_licensing_audit.py and drywall_detection/tests/unit/test_datasets.py using pytest.
6. Verify all tests pass, document execution outputs, and write your handoff report in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1\handoff.md.
7. Notify the orchestrator via send_message when complete.
