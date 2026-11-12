# Milestone M1 Technical Handoff Report: Unified Dataset Format & Conversion Pipeline

**Module:** `drywall_detection.datasets`  
**Subagent:** `m1_spec_miner_2`  
**Role:** Dataset Format & Conversion Spec Miner  
**Date:** 2026-11-08  
**Project:** Isolated Drywall Detection Module (`drywall_detection/`)  
**Workspace:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Target Milestone:** M1 (Dataset Research, Licensing Audit & Unified Preparation)  
**Deliverable Document:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\analysis.md`  

---

## 1. Observation

1. **Python Environment & Installed Packages**:
   Command: `python -c "import sys; print('Python:', sys.version); [print(p, ':', getattr(__import__(p), '__version__', 'ok')) if p in sys.modules or __import__(p) else None for p in ['numpy', 'cv2', 'PIL', 'shapely', 'fitz', 'torch', 'torchvision', 'scipy', 'matplotlib']]"`  
   Verbatim output:
   ```
   Python: 3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
   numpy : 1.26.4
   cv2 : 4.11.0
   PIL : 10.2.0
   shapely : 2.1.1
   fitz : ok
   torch : 2.1.0+cpu
   torchvision : 0.16.0+cpu
   scipy : 1.15.3
   matplotlib : 3.10.3
   ```
   Furthermore, inspection of `env_hardware_audit.json` lines 112–126 established that `albumentations` and `segmentation_models_pytorch` are **not installed** (`"installed": false`). Local compute is strictly CPU-based (`torch.cuda.is_available() == False`, 0 VRAM, 7.88 GB RAM with ~1 GB available).

2. **Single-Channel 8-bit Indexed PNG Verification**:
   Empirical testing with `probe_tests.py` verified that an 8-bit array with values `[0, 1, 2, 3]` saved via `PIL.Image.fromarray(arr, mode='P')` with an embedded 256-color palette (`PALETTE_256`) achieves dual compatibility:
   - When opened in standard image viewers, it visually renders the colors: White for Background (0), Green for Drywall (1), Red for Non-Drywall (2), Yellow for Uncertain (3).
   - When loaded in Python using `Image.open(...)` and converted to NumPy `np.array(...)` or PyTorch `torch.from_numpy(...).long()`, it returns exact integer indices `[0, 1, 2, 3]` with zero color de-mapping overhead:
     ```
     Loaded mode: P
     Loaded np shape: (2, 2) dtype: uint8 values: [[0, 1], [2, 3]]
     Torch tensor shape: torch.Size([2, 2]) dtype: torch.int64
     Verified: Mode P loads directly as integer class indices in PyTorch!
     ```

3. **Candidate Dataset Schemas**:
   - **Modified Swiss Dwellings (MSD)**: Tabular WKT coordinates in `geometries.csv`. Filtering criterion: `entity_type == 'separator' and entity_subtype == 'WALL'`. Tested Shapely parsing and `cv2.fillPoly` rasterization:
     ```
     Parsed poly area: 607.4100000000001
     Unique values in mask: [0 3]
     Count of wall pixels: 656
     ```
   - **CubiCasa5K**: Vector SVG `model.svg` with `<polygon class="Wall">` and `viewBox`. Tested XML ElementTree parsing and scale factor mapping to target raster shape:
     ```
     SVG Mask unique values: [0 3]
     SVG Wall pixel count: 5901
     ```
   - **MTA 99th Street**: 239 expert-annotated drywall wall centerlines in `drywall_walls_marked_red_by_Usman.pdf` across pages 0–4 (A-100 to A-104), with verified schedule mappings from sheets A-900 and A-901.

4. **Sliding-Window Tiling & Seamless Apodization Stitching**:
   Empirical testing of ARCH D sheets ($2592 \times 1728$ at 72 DPI) with patch size $512 \times 512$ and 20% overlap ($S = 410\text{ px}$) yielded:
   - Tiling grid: 4 rows $\times$ 7 columns = 28 tiles.
   - Row offsets: `[0, 410, 820, 1216]`.
   - Col offsets: `[0, 410, 820, 1230, 1640, 2050, 2080]`.
   - Coverage: Min coverage = 1, Max coverage = 6, Coverage gaps = 0.
   - Reverse stitching with 2D Hann window weighting yielded a numerical reconstruction error of `0.0` ($< 10^{-5}$).

5. **Tile Filtering Heuristics**:
   Tested filtering criteria:
   - Corrupt tiles (shape mismatch, invalid mask values $> 3$) $\to$ 100% rejected.
   - Pure blank tiles (variance $< 2.0$, mean $> 250$, 0 walls) $\to$ 100% discarded.
   - Hard negative tiles (contains text/linework, 0 walls) $\to$ retained within 15% quota.
   - Positive tiles (contains walls) $\to$ 100% retained.
   - Result: `Tile filtering logic verified successfully!`.

6. **Visual QC Triplet Construction**:
   Synthesized 512x512 tiles with alpha blending ($\alpha = 0.40$) and built composite triplets `[Drawing Tile | Color Mask | Translucent Overlay]`:
   - Shape: $(512, 1536, 3)$ plus 36 px diagnostic header banner.
   - Result: `Visual QC triplet constructed successfully! Shape: (512, 1536, 3)`.

---

## 2. Logic Chain

1. **Format Unification Logic**:
   - Semantic segmentation models (U-Net, SegFormer) require integer-indexed ground truth target masks $Y \in \{0, \dots, C-1\}^{H \times W}$.
   - Multi-channel RGB masks require expensive color matching during training dataloading, introducing CPU bottlenecks on a CPU-constrained machine.
   - Conversely, saving raw 8-bit grayscale images produces almost invisible black tiles (pixel values 0, 1, 2, 3 appear virtually identical to the human eye on an 8-bit 0..255 scale).
   - Saving masks as Mode `P` indexed PNG with an explicit 256-color palette (White, Green, Red, Yellow) completely resolves both problems: standard viewers display intuitive vibrant colors for visual QC and manual auditing, while PIL and PyTorch load integer values `[0, 1, 2, 3]` directly as `torch.long` tensors.

2. **Generic Wall Pretraining Guardrail Logic**:
   - Candidate academic datasets (MSD, CubiCasa5K, FloorPlanCAD) contain only geometric wall outlines without material specifications (drywall vs masonry vs concrete).
   - Zero-tolerance integrity rules strictly forbid presenting generic wall detections as confirmed drywall without verified ground truth evidence.
   - Therefore, the conversion pipeline must map all external dataset wall polygons to **Class 3 (Uncertain / Generic Wall)**.
   - Class 1 (Drywall) and Class 2 (Non-Drywall) designations are reserved exclusively for partitions verified against architectural schedules (e.g. MTA 99th Street Sheets A-900, A-901).

3. **Tiling & Stitching Logic**:
   - Architectural sheets are large ($2592 \times 1728$ at 72 DPI; $5400 \times 3600$ at 150 DPI). Direct downsampling to $512 \times 512$ reduces wall stroke widths from 4–8 pixels to less than 1 pixel, causing thin walls to vanish.
   - A sliding-window tiling engine with $512 \times 512$ patches preserves native line resolution.
   - An overlap of 20% (stride 410 px) ensures every wall segment appears centrally in at least one tile.
   - During inference reassembly, boundary discontinuities and tile seams are eliminated by applying 2D Hann window apodization weighting, which smoothly attenuates edge predictions and favors central predictions.

4. **Empty Tile Filtering Logic**:
   - Floor plans have extensive margins and unbuilt areas.
   - Unfiltered tiling produces up to 70% pure white blank tiles, leading to extreme class imbalance (99% background) and wasted CPU cycles.
   - Discarding 100% of pure blank tiles ($\sigma < 2.0, \mu > 250$) while retaining up to 15% of hard negatives (linework without walls) balances the dataset, improves convergence speed, and trains the model to distinguish non-wall CAD symbols.

---

## 3. Caveats

1. **Local Machine Hardware Constraint**:
   - Local CPU compute (`torch 2.1.0+cpu`, ~1.0 GB free RAM) cannot support full-scale pretraining on tens of thousands of tiles simultaneously. Full-scale pretraining should run in Google Colab (GPU) or use a curated sub-sample (e.g., 500–1,000 tiles) on CPU for validation.
2. **External Dataset Download Guardrails**:
   - Neither CubiCasa5K (5.09 GB) nor MSD (174 MB HF / 888 MB Zenodo) have been downloaded into the workspace yet. Downloading will be initiated in Milestone M2 under the strict disk-space checks and safety constraints established in M1.
3. **Usman Ground Truth Coverage**:
   - Expert annotations in `drywall_walls_marked_red_by_Usman.pdf` cover sheets A-100 through A-104 (Floors Cellar to 4th). Other sheets (e.g. roof A-105 or enlarged plans) lack expert markups and must be treated as unannotated or test-only sets.

---

## 4. Conclusion

The technical specifications and architectural contracts for the unified dataset format, multi-source conversion pipelines (MSD WKT, CubiCasa5K SVG, raster masks, and vector CAD), sliding-window tiling engine ($512 \times 512$ with 20% overlap, stride 410 px), tile filtering heuristics, visual QC generator, and the target module `drywall_detection/datasets/unified_format.py` are fully defined and mathematically verified.

All requirements for Milestone M1 Task 2 have been satisfied in full without creating code files outside the specification boundary. The detailed report is saved at `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\analysis.md`.

---

## 5. Verification Method

To independently verify the empirical observations and mathematical findings in this handoff report:

1. **Verify Python Environment & Dependencies**:
   ```powershell
   python -c "import torch, numpy, cv2, PIL, shapely; print('Torch:', torch.__version__, 'CUDA:', torch.cuda.is_available())"
   ```
2. **Execute Empirical Verification Test Suite**:
   ```powershell
   python c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\probe_tests.py
   ```
   *Expected output:*
   - `SVG Mask unique values: [0 3]`
   - `SVG Wall pixel count: 5901`
   - `Tile size: 512, Stride: 410`
   - `Tiling grid: 4 rows x 7 cols = 28 tiles`
   - `Coverage verified! Min coverage: 1, Max coverage: 6`
   - `Reconstruction max error: 0.0`
   - `Seamless stitching with 2D Hann apodization verified successfully!`
   - `Visual QC triplet constructed successfully! Shape: (512, 1536, 3)`
   - `Tile filtering logic verified successfully!`
   - `All probe tests passed successfully!`

3. **Inspect Specification Analysis Document**:
   Examine `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\analysis.md` for class definitions, mathematical proofs, and authoritative tables.
