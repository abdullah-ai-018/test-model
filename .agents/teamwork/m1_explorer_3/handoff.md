# Handoff Report: Split Strategy & PyTorch Dataset Loader Architecture

- **Agent**: `m1_explorer_3`
- **Role**: Split Strategy & Dataset Loader Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Handoff Type**: Hard (Task Complete)
- **Path**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\handoff.md`
- **Recipient**: Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`) / Downstream Worker

---

## 1. Observation

1. **Host Environment & Resource Scarcity**:
   - `survey_explorer_1/analysis.md:46` documented: Available system memory is `~1.00 GB (1,024 MB)` out of 7.88 GB total (~87.3% utilized).
   - `survey_explorer_1/analysis.md:47` documented: `torch.cuda.is_available() == False`, `nvidia-smi` failed / not installed. Dedicated VRAM: 0 GB.
   - `survey_explorer_1/analysis.md:83` documented: `albumentations` package is missing / not installed. `torch 2.1.0+cpu`, `torchvision 0.16.0+cpu`, `opencv-python 4.11.0`, and `PIL` are installed.
2. **Acceptance Criteria & Split Integrity Contracts**:
   - `ORIGINAL_REQUEST.md:35` verbatim acceptance criterion: `"Train, validation, and test splits are strictly separated at drawing level with zero project overlap."`
   - `ORIGINAL_REQUEST.md:25` verbatim requirement: `"Train and fine-tune models using drawing-level train/val/test splits to avoid data leakage..."`
   - `PROJECT.md:115` formal interface invariant:
     $$\text{Projects}(\text{train}) \cap \text{Projects}(\text{val}) = \emptyset$$
     $$\text{Projects}(\text{train}) \cap \text{Projects}(\text{test}) = \emptyset$$
     $$\text{Projects}(\text{val}) \cap \text{Projects}(\text{test}) = \emptyset$$
   - `PROJECT.md:28` guardrail: Weak pseudo-labeling for 99th Street PDF requires strict quarantine from validation and test sets.
3. **Data Representation & Tiling Standards**:
   - `m1_spec_miner_2/BRIEFING.md:17` specifies: 4-class unified segmentation format: uint8 PNG (0: Background, 1: Drywall, 2: Non-Drywall, 3: Uncertain).
   - `m1_spec_miner_2/BRIEFING.md:19` specifies: Sliding-window tiling engine generating $512 \times 512$ patches with 20% overlap.
4. **Test Infrastructure Standards**:
   - `TEST_INFRA.md:13` specifies: Feature F3 Drawing-Level Split Integrity (Tier 1 & Tier 2 tests).
   - `TEST_INFRA.md:29` specifies: Test runner command `pytest drywall_detection/tests/ -v`.

---

## 2. Logic Chain

1. **Derivation of Split Integrity Manager (`split_manager.py`)**:
   - *From Observation 2*: Architectural drawings from the same project share identical perimeter layouts, column grids, line weights, drafting styles, and overlapping sliding-window tiles. Naive random partitioning creates structural data leakage and overfitted validation metrics.
   - *Inference*: The split manager must group tiles by `project_id` (or fallback to `drawing_id` for isolated multi-sheet permit sets) and apply greedy multi-way number partitioning to balance tile counts (70% train, 15% val, 15% test) without violating group boundaries.
   - *Inference*: A standalone validator `verify_split_isolation()` must perform pairwise set intersections on projects, drawings, and file paths. If any intersection is non-empty, it raises `SplitLeakageError` immediately.
   - *Inference*: Drawings tagged as weak pseudo-labels (e.g. 99th Street MTA) must be quarantined via `quarantine_projects` so they never enter validation or test sets.

2. **Derivation of PyTorch Dataset Streaming (`loader.py`)**:
   - *From Observation 1 & 3*: Available RAM is only ~1.0 GB and uncompressed full-page drawings consume 30–150 MB each. Loading full floorplans or pre-caching large tensor arrays in RAM triggers fatal Windows OOM crashes.
   - *Inference*: `DrywallTileDataset` must implement lazy on-demand tile streaming from disk. Only lightweight JSON metadata records (<15 MB for 50,000 tiles) are kept in memory.
   - *Inference*: In `__getitem__`, tiles are loaded as RGB, masks as uint8, and converted into normalized `[3, 512, 512]` float32 image tensors (ImageNet mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]`) and `[512, 512]` int64 (`torch.long`) segmentation masks.
   - *Inference*: The dataset must support `mode="4class"` ({0: bg, 1: drywall, 2: non-drywall, 3: uncertain}) and `mode="binary"` ({0: bg, 1: wall}) for Stage 1 generic wall pretraining on open datasets (MSD/CubiCasa5K).

3. **Derivation of Synchronized Augmentations without Albumentations**:
   - *From Observation 1*: `albumentations` is not installed, but `torchvision` and `torch` are available.
   - *Inference*: Augmentations must be implemented natively via `torchvision.transforms.functional`.
   - *Inference*: Architectural drawings are orthographic; continuous small-angle rotations blur CAD lines into anti-aliasing artifacts. Therefore, geometric transforms are restricted to horizontal flips, vertical flips, and discrete 90° rotations (90°, 180°, 270°).
   - *Inference*: Geometric transforms must be synchronized identically between image and mask using nearest-neighbor mask interpolation. Photometric jitter (brightness and contrast) is applied strictly to the image, never touching the mask labels.

4. **Derivation of Hardware-Adapted DataLoader Defaults**:
   - *From Observation 1*: Host is Windows CPU-only with constrained memory. Windows multiprocessing `spawn` duplicates memory by ~150 MB per worker, and pinned memory wastes locked RAM without CUDA acceleration.
   - *Inference*: `get_tile_dataloader` must default to `num_workers=0`, `pin_memory=False`, and `batch_size=2` (scalable to 4 on capable hardware or Colab GPU).

5. **Derivation of Unit Test Suite (`test_datasets.py`)**:
   - *From Observation 2, 4*: Unit tests must verify split disjointness, leakage detection, deterministic seeds, tensor dimensions, normalization, synchronized augmentations, and PyTorch model forward pass compatibility under `pytest`.

---

## 3. Caveats

1. **Single-Project Datasets**: If a user supplies only a single architectural drawing project (e.g. only MTA 99th Street), 3-way project-level isolation cannot be satisfied. In this scenario, `DrawingSplitManager` gracefully falls back to `drawing_id` (sheet-level isolation, e.g. Sheet A-101 Train, Sheet A-102 Val, Sheet A-103 Test). While sheet-level isolation prevents overlapping tile leakage, it does not prevent drafting-style leakage. True cross-project evaluation requires external drawings (such as `test Spark Lake Grove - Permit Set.pdf`).
2. **Class Imbalance in Small Splits**: Some drawing projects contain only generic walls without verified partition schedules. In small validation sets, positive drywall or non-drywall classes may have sparse representation. The split manager logs detailed class pixel percentages in `splits_summary.json` to flag sparse class distribution.
3. **No Code Implementation in M1 Explorer Phase**: In accordance with the Explorer archetype rules, no production source code has been committed to `drywall_detection/`. All code structures, function signatures, data models, error classes, and test specifications are fully documented in `analysis.md` for direct execution by the Worker.

---

## 4. Conclusion

The split integrity and dataset loader architecture for Milestone M1 is fully specified and ready for Worker implementation:
1. **Split Manager (`split_manager.py`)**: Enforces zero project/drawing overlap using greedy multi-way group partitioning, verifiable through `verify_split_isolation()`, and exports `train.json`, `val.json`, `test.json`, and `splits_summary.json` with cryptographic SHA-256 verification hashes.
2. **PyTorch Dataset & DataLoader (`loader.py`)**: Streams 512x512 tiles lazily from disk with a RAM footprint < 15 MB, applies synchronized orthographic augmentations, supports both 4-class multi-class and binary pretraining modes, and yields normalized `[3, 512, 512]` float32 images and `[512, 512]` long masks.
3. **Unit Test Suite (`test_datasets.py`)**: Formulates 20+ unit tests across 5 test classes covering split disjointness, leakage exception handling, deterministic seeds, tensor shapes, synchronized augmentations, and model forward pass execution.

---

## 5. Verification Method

To independently verify this specification and its subsequent Worker implementation:

### 5.1 Verification Commands
```bash
# 1. Run unit test suite for dataset splits and DataLoader
pytest drywall_detection/tests/unit/test_datasets.py -v

# 2. Run specific split integrity and leakage detection tests
pytest drywall_detection/tests/unit/test_datasets.py -k "TestDrawingSplitManager" -v

# 3. Run PyTorch Dataset tensor dimensions and normalization tests
pytest drywall_detection/tests/unit/test_datasets.py -k "TestDrywallTileDataset" -v

# 4. Verify memory stability during batch iteration (CPU safe)
pytest drywall_detection/tests/unit/test_datasets.py -k "test_dataloader_iteration_memory_stability" -v
```

### 5.2 Files to Inspect
- Technical Architecture: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3\analysis.md`
- Target Implementation Modules:
  * `drywall_detection/datasets/split_manager.py`
  * `drywall_detection/datasets/loader.py`
  * `drywall_detection/tests/unit/test_datasets.py`
  * `drywall_detection/data/preparer.py` (import wrapper / alias)

### 5.3 Invalidation Conditions
- Any occurrence of $\text{Projects}(\text{train}) \cap \text{Projects}(\text{val}) \neq \emptyset$ or $\text{Drawings}(\text{train}) \cap \text{Drawings}(\text{val}) \neq \emptyset$.
- Any execution where `verify_split_isolation()` fails to raise `SplitLeakageError` when a tile from train is duplicated into val.
- Any DataLoader batch output deviating from `[B, 3, 512, 512]` float32 image or `[B, 512, 512]` long mask with values outside $\{0, 1, 2, 3\}$.
- Any memory leak where DataLoader iteration causes Python process RAM to exceed host memory threshold.
