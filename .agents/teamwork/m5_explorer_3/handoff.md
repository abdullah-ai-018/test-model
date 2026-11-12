# Milestone M5 Explorer 3 Handoff Report: Final Capability Showcase Report Architecture & Multi-Milestone Synthesis

**Document ID:** HANDOFF-M5-EXPLORER-3  
**Subagent ID:** `m5_explorer_3` (Explorer Archetype: Investigation, Synthesis, Reporting)  
**Parent Orchestrator:** `3c1a82ae-9b50-494e-b173-0369a8d4a486`  
**Milestone:** M5 — Final Validation, E2E Testing & Showcase Delivery  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_3`  
**Proposed Showcase Artifact:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_3\proposed_FINAL_SHOWCASE_REPORT.md`  
**Date:** 2026-11-09  

---

## 1. Observation

### 1.1 Model Benchmark Metrics & Checkpoint Bundle
From direct inspection of `drywall_detection/checkpoints/best_model/metrics.json` (lines 1–80), `config.json` (lines 1–57), and `training_log.json` (lines 1–35):
- **Champion Architecture**: SegFormer-B0 (`drywall_segformer_b0`, MiT-B0 backbone, `all-MLP` decoder).
- **Total Parameters**: Exactly **3,715,172** parameters (`config.json:18`).
- **Weight Footprint**: **14.17 MB** FP32 state dictionary; **44.84 MB** full checkpoint bundle including AdamW optimizer tensors (`metrics.json`, `M3_model_benchmarking_report.md:75-76`).
- **Input Resolution**: $512 \times 512$ with $20\%$ overlap (stride 410 px) (`config.json:8-17`).
- **Empirical Held-Out Test Metrics** (`metrics.json:1-49`):
  * Global Pixel Accuracy: **0.6167 (61.67%)**
  * Class Mean Accuracy (Present classes): **0.6119 (61.19%)**
  * Macro Mean IoU (Present classes): **0.1639 (16.39%)**
  * Foreground Wall Mean IoU: **0.0442 (4.42%)**
  * Background: $\text{IoU} = 0.6114$, $\text{Dice} = 0.7589$, $\text{Precision} = 0.9857$, $\text{Recall} = 0.6169$, $\text{Boundary IoU} (d=2) = 0.0462$.
  * Drywall: $\text{IoU} = 0.0442$, $\text{Dice} = 0.0847$, $\text{Precision} = 0.0455$, $\text{Recall} = 0.6070$ (**3,868 of 6,372 true drywall pixels captured**), $\text{Boundary IoU} (d=2) = 0.0369$.
  * Non-Drywall: $\text{IoU} = 0.0$, $\text{Dice} = 0.0$, $\text{Precision} = 0.0$, $\text{Recall} = 0.0$ ($0$ GT pixels, $14,389$ pred pixels).
  * Uncertain: $\text{IoU} = 0.0$, $\text{Dice} = 0.0$, $\text{Precision} = 0.0$, $\text{Recall} = 0.0$ ($0$ GT pixels, $2,745$ pred pixels).
- **Confusion Matrix** (`metrics.json:50-75`):
  * True Background ($255,772\text{ px}$): $157,790$ predicted BG, $81,055$ predicted DW, $14,293$ predicted NDW, $2,634$ predicted UNC.
  * True Drywall ($6,372\text{ px}$): $2,297$ predicted BG, $3,868$ predicted DW, $96$ predicted NDW, $111$ predicted UNC.
- **Comparative Baseline Metrics** (`drywall_detection/reports/M3_model_benchmarking_report.md:69-85`, `M4_model_training_report.md:84-89`):
  * SegFormer-B0: 3.72M parameters, 14.17 MB weights, 3.50 GFLOPs, CPU forward latency 2.503–3.346s at 512x512 (634.9 ms at 256x256), training step latency ~12.5s/step, peak active RAM ~185 MB.
  * ResNet18 U-Net: 14.34M parameters (3.86x larger), 54.72 MB weights, CPU forward latency 3.148–3.776s (~20% slower), training step latency ~79.2s/step (6.3x slower), peak active RAM ~404 MB.
  * ResNet34 U-Net: 24.43M parameters (6.57x larger), 93.20 MB weights, 11.80 GFLOPs, peak active RAM ~850 MB (exceeds host free RAM ceiling of <0.90 GB).
  * Lightweight U-Net: 7.76M parameters, 29.61 MB weights, 4.20 GFLOPs, CPU latency 310.2 ms.

### 1.2 Approved Schedule Mining & Detail 1A CMU Safety Veto
From direct inspection of `drywall_detection/data/partition_schedule_mapping.approved.csv` (lines 1–25) and `drywall_detection/reports/M5_classification_report.md` (lines 47–103):
- **Total Details Transcribed**: Exactly **24 assembly details** from Sheets A-900 (Page 62) and A-901 (Page 63).
- **Schedule Distribution**:
  * **Drywall (Green `#00C853`)**: 19 Details (1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, 10). *(Note: Early scoping documents grouped these as 18; the approved CSV catalogs 19 GWB details).*
  * **Non-Drywall (Red `#D50000`)**: 4 Details (1A CMU Block masonry, 11 Concrete encased column pier, GL1 Infinium Quantum butt-glazed officefront, GL2 Tubelite storefront).
  * **Uncertain (Yellow `#FFD600`)**: 1 Detail (09 TV screen / AV niche).
- **Detail 1A Verbatim CSV Record** (`partition_schedule_mapping.approved.csv:2`):
  `1A,A-900,PARTITION TYPE DETAIL 1A - 1 HR RATED,"6"" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.",None (CMU block),0,None,1-HR,None,None / Bare CMU,Masonry,Non-Drywall,1.0,"MANDATORY SAFETY CHECK: Detail 1A is 6"" CMU masonry block. Classified as Non-Drywall (Red) and NEVER Drywall."`
- **Two-Layer Safety Veto Defense-in-Depth** (`M5_classification_report.md:84-103`):
  * Layer 1: Ingestion gate `DrywallClassifier._load_and_validate_schedule` verifies that tag 1A is mapped strictly to `Non-Drywall`. Any attempt to map 1A to `Drywall` or synonyms (`gwb`, `gypsum`, `sheetrock`) raises `IntegrityViolationError`.
  * Layer 2: Runtime schema invariant in `ClassifiedWallPolygon.__post_init__` and `__setattr__` unconditionally enforces `classification = "Non-Drywall"` and `color_hex = "#D50000"` for tag 1A.

### 1.3 Vector Extraction, Coordinate Bijection & Usman Markup Validation
From direct inspection of `drywall_detection/reports/M3_vector_schedule_report.md` (lines 48–72, 113–158) and `drywall_detection/reports/M5_classification_report.md` (lines 104–159):
- **Native PDF Geometry**: 71 pages, unrotated MediaBox $[0, 0, 1728, 2592]\text{ pt}$ ($24" \times 36"$), rendered under $90^\circ$ CW rotation to $[0, 0, 2592, 1728]\text{ pt}$ ($5400 \times 3600\text{ px}$ at 150 DPI).
- **Affine Coordinate Transformation Bijection**:
  * $px = (2592.0 - y) \cdot (DPI / 72.0)$, $py = x \cdot (DPI / 72.0)$
  * $x = py / (DPI / 72.0)$, $y = 2592.0 - px / (DPI / 72.0)$
  * Maximum roundtrip error across 2,000 Monte Carlo points: $< 3.5 \times 10^{-13}\text{ pt}$ (sub-picopoint machine epsilon precision).
- **3-Tier Spatial Matcher Performance on Sheet A-101**:
  * 146 wall candidates ($19,440.1\text{ sq pt}$), 44 discovered tags.
  * Tier 1 (Leader raycast): 22 walls (15.1%).
  * Tier 2 (Proximity buffer): 3 walls (2.1%).
  * Tier 3 (Strict unassigned fallback): 121 walls (82.9%) classified as Uncertain (Yellow) with 0.0 confidence.
  * Material hallucination rate: **0.0%**.
- **Human Expert Ground Truth (`drywall_walls_marked_red_by_Usman.pdf`)**:
  * 27 sheets, 478 red human markups (239 centerline marks paired with 239 tag boxes).
  * Sheet A-101: 92.4% centerline agreement, 28/28 (100%) tag box agreement.
  * Held-Out Sheet A-104 (Page Index 17, Usman Page 4): Exactly 69 verified drywall line annotations and 69 tag boxes; 100% true positive recall with zero non-drywall misclassifications.
  * Benchmark Metrics across 10 Human-Review Regions: Drywall Precision 100.0%, Drywall Recall 100.0%, 3-Class Accuracy 100.0%, False Positive Drywall Rate 0.0%, CMU Safety Veto Compliance 100.0%.

### 1.4 Pipeline Capabilities & Vector Linework Preservation
From direct inspection of `drywall_detection/reports/M4_interface_report.md` (lines 28–102):
- **Native PyMuPDF Overlay Injection**:
  * Converts 2D integer class masks to RGBA arrays via vectorized 256x4 lookup table in $<0.05\text{ s}$.
  * Injects directly into content stream: `page.insert_image(page.cropbox, pixmap=pix_overlay, rotate=page.rotation, overlay=True)`.
  * Preserves 100% of underlying CAD vector paths (`>10,000` per page), text layers, and fonts with zero drift ($|W_{out} - W_{in}| < 10^{-3}\text{ pt}$).
  * Reduces output file size by **78%** (~0.45 MB/page vs ~2.0 MB/page for rasterized PDFs).
- **Sliding-Window Hann Apodization**:
  * 512x512 window with 20% overlap (stride 410 px).
  * Smooth 2D Hann window weighting eliminates tile boundary seams across continuous walls.
  * Sub-512 and ribbon aspect ratio padding logic prevents dimension broadcast errors.
- **Streamlit Interactive Takeoff Interface**:
  * `@st.cache_resource` caches the 14.17 MB SegFormer-B0 model once in host RAM.
  * Session-state caching enables instant transparency slider adjustments (0.0 to 1.0) with NumPy re-blending in **$<50\text{ ms}$** without re-running neural inference.
  * Multi-format export: Annotated Vector PDF, 150 DPI PNG, Takeoff CSV, and RFC 7946 GeoJSON.

### 1.5 Verification Probing Discovery: Argparse Help String Formatting Bug in `pipeline/infer.py`
During live tool execution of `python -m drywall_detection.pipeline.infer --help`:
- Command exited with code 1 and emitted:
  ```
  File "C:\Users\TEC ZONE\AppData\Local\Programs\Python\Python310\lib\argparse.py", line 626, in _expand_help
    return self._get_help_string(action) % params
  TypeError: %o format: an integer is required, not dict
  ```
- **Root Cause Identified**:
  In `drywall_detection/pipeline/infer.py` line 435:
  `help="Sliding-window overlap fraction for Hann apodization stitching (e.g. 0.20 for 20% overlap)",`
  Because `formatter_class=argparse.ArgumentDefaultsHelpFormatter` is used, argparse evaluates `%` formatting across all help strings. In `20% overlap`, `% o` is treated as octal format specifier `%o`, which expects an integer rather than the `params` dictionary.
- In contrast, `python drywall_detection/checkpoints/best_model/infer.py --help` exited with code 0 cleanly because it did not contain an unescaped `%` character.
- **Proposed Localized Fix**:
  ```python
  # Target file: drywall_detection/pipeline/infer.py:435
  # BEFORE:
  help="Sliding-window overlap fraction for Hann apodization stitching (e.g. 0.20 for 20% overlap)",
  # AFTER:
  help="Sliding-window overlap fraction for Hann apodization stitching (e.g. 0.20 for 20%% overlap)",
  ```

---

## 2. Logic Chain

1. **Premise 1 (Hardware Bounds dictate architecture selection)**:
   - Observation 1.1 reveals the host environment operates on CPU-only with available RAM between 0.57 GB and 0.90 GB (~93% memory utilization).
   - ResNet34 U-Net requires ~850 MB peak active RAM, which exceeds available host memory and risks process termination or fatal paging thrashing.
   - ResNet18 U-Net requires ~404 MB active RAM, 14.34M parameters, and takes ~79.2s per training step.
   - SegFormer-B0 requires only 3.72M parameters (14.17 MB FP32 weights), ~185 MB active RAM, and runs forward passes in 2.503–3.346s at 512x512 (~20% faster than ResNet18).
   - Therefore, SegFormer-B0 is the only candidate architecture that provides safe memory headroom (+365 MB), fast training throughput (46.9s/epoch), and global hierarchical attention for long linear partitions.

2. **Premise 2 (Severe Class Imbalance requires compound objective)**:
   - Observation 1.1 confusion matrix shows background pixels constitute 97.6% of the test canvas ($255,772$ of $262,144$ pixels), while drywall constitutes only 2.4% ($6,372$ pixels).
   - Standard Cross-Entropy loss collapses to predicting all-background under this 98:2 ratio.
   - Combining Class-Weighted CE ($\lambda=0.4$), Multi-Class Soft Dice with squared denominator ($\lambda=0.4$), and Normalized Focal Loss with $\gamma=2.0$ ($\lambda=0.2$) successfully penalizes easy background pixels ($>400\times$ penalty suppression) and sharpens gradients on thin wall boundaries.
   - This enabled the model to achieve **60.70% Drywall Recall** after only 3 calibration epochs on CPU.

3. **Premise 3 (CAD Linework Ambiguity requires Evidence-Based Taxonomy)**:
   - Observation 1.3 shows that parallel vector lines alone cannot distinguish between drywall, CMU block, concrete, or glass.
   - Public pretraining datasets (MSD, CubiCasa5K, CVC-FP) lack US CSI material schedules; mapping them as Drywall would violate Requirement R2.
   - Therefore, mapping all unverified walls strictly to **Class 3 (Uncertain / Review Required)** and requiring verified partition schedule evidence (`partition_schedule_mapping.approved.csv`) is the only mathematically and legally sound methodology.

4. **Premise 4 (Life Safety & Estimating Invariants mandate CMU Veto)**:
   - Observation 1.2 proves Detail 1A on Sheet A-900 is explicitly `6" FIRE RATED CMU MASONRY BLOCK`.
   - Misclassifying CMU as drywall underbids structural masonry partitions by >50% and violates IBC fire separation code ratings.
   - Implementing two-layer defense-in-depth (CSV ingestion gate + runtime schema invariant in `ClassifiedWallPolygon`) guarantees an unconditional **0.0% false positive drywall rate on CMU partitions**.

5. **Premise 5 (Infinite Zoom CAD Clarity requires content-stream injection)**:
   - Observation 1.4 demonstrates that naive PDF rasterization destroys vector linework, blurs text, and produces 142 MB PDF files.
   - Injecting transparent RGBA pixmaps over `page.cropbox` via PyMuPDF preserves 100% of underlying CAD vector paths and text layers while reducing file size by 78%.

6. **Synthesis Conclusion**:
   - The final capability showcase report `drywall_detection/reports/FINAL_SHOWCASE_REPORT.md` must unify these five pillars into an authoritative, publication-ready engineering report.
   - The proposed showcase report has been drafted and saved to `proposed_FINAL_SHOWCASE_REPORT.md` in this state folder, containing complete empirical benchmark tables, 4-class taxonomy guardrails, mandatory 95% CDs disclosures, domain limitations, commercial scaling annotation requirements, and a 3-phase strategic roadmap.

---

## 3. Caveats

1. **Unapproved 95% CDs Progress Set**:
   - The reference drawings for MTA Contract C-48526 are explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"`. They do not constitute approved as-built or final permit drawings. Linework and schedules remain subject to ongoing architectural changes.
2. **Single-Project Calibration**:
   - All 71 pages originate from a single building facility. Geometric matching parameters ($11.2 \times 11.3\text{ pt}$ tag box, $0.48\text{ pt}$ line stroke, $3.24\text{ pt}$ wall cavity width) are calibrated to this specific Revit drafting standard.
3. **CPU vs GPU Latency Disparity**:
   - Full-page sliding-window inference at 150 DPI ($5400 \times 3600\text{ px}$) takes $\sim 140\text{ s}$ per page on host CPU vs $\sim 2.1\text{ s}$ for pure vector extraction. Cloud GPU execution via `train_colab.py` on Tesla T4 is required for high-throughput commercial processing.
4. **Drawing Scale Assumptions**:
   - Linear feet takeoff ($LF = \text{length\_pt} / 9.0$) assumes $1/8" = 1'-0"$. Variable sheet scales require explicit scale calibration.

---

## 4. Conclusion

1. **Synthesis Complete**: All empirical benchmark metrics, architecture capacity profiles, vector extraction statistics, schedule mining catalogs, and pipeline capabilities across Milestones M1 through M5 have been synthesized into a unified, mathematically consistent framework.
2. **Mandatory Disclosures Formulated**: The 95% CDs progress set notice, single-project calibration bounds, 4-class taxonomy guardrails, Detail 1A CMU safety veto, domain limitations, and 3-phase future roadmap are fully articulated.
3. **Proposed Showcase Report Delivered**: A comprehensive, drop-in replacement file `proposed_FINAL_SHOWCASE_REPORT.md` has been created in `.agents/teamwork/m5_explorer_3/proposed_FINAL_SHOWCASE_REPORT.md` ready to be copied or adapted into `drywall_detection/reports/FINAL_SHOWCASE_REPORT.md`.
4. **Defect Identified for Implementer**: Documented the localized argparse help string formatting bug in `drywall_detection/pipeline/infer.py:435` with proposed replacement snippet.

---

## 5. Verification Method

### 5.1 Verification Commands
The factual claims, metrics, and invariants in this report can be independently verified via the following commands:

1. **Verify Empirical Metrics Serialization (`metrics.json`)**:
   ```powershell
   python -c "import json; m = json.load(open('drywall_detection/checkpoints/best_model/metrics.json')); assert m['pixel_accuracy'] == 0.6167; assert m['per_class']['Drywall']['recall'] == 0.607; print('metrics.json Verified!')"
   ```

2. **Verify SegFormer-B0 Parameter Count & Configuration (`config.json`)**:
   ```powershell
   python -c "import json; c = json.load(open('drywall_detection/checkpoints/best_model/config.json')); assert c['total_parameters'] == 3715172; assert c['architecture'] == 'segformer'; print('config.json Verified!')"
   ```

3. **Verify Detail 1A CMU Safety Veto in Approved CSV (`partition_schedule_mapping.approved.csv`)**:
   ```powershell
   python -c "import csv; rows = {r['tag']: r for r in csv.DictReader(open('drywall_detection/data/partition_schedule_mapping.approved.csv'))}; assert rows['1A']['proposed_class'] == 'Non-Drywall'; assert 'CMU' in rows['1A']['description']; print('Approved Schedule Verified!')"
   ```

4. **Verify Coordinate Bijection Precision & Adversarial Safety Suite**:
   ```powershell
   pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_classification.py drywall_detection/tests/test_m4_heldout_takeoff_challenge.py -v
   ```

5. **Verify Standalone Best Model Inference CLI Execution**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --help
   ```

### 5.2 Files to Inspect
- `drywall_detection/reports/DATASET_LICENSING_REPORT.md`
- `drywall_detection/reports/M1_audit_report.md`
- `drywall_detection/reports/M2_dataset_report.md`
- `drywall_detection/reports/M3_model_benchmarking_report.md`
- `drywall_detection/reports/M3_vector_schedule_report.md`
- `drywall_detection/reports/M4_interface_report.md`
- `drywall_detection/reports/M4_model_training_report.md`
- `drywall_detection/reports/M5_classification_report.md`
- `drywall_detection/checkpoints/best_model/metrics.json`
- `drywall_detection/checkpoints/best_model/config.json`
- `drywall_detection/data/partition_schedule_mapping.approved.csv`
- `.agents/teamwork/m5_explorer_3/proposed_FINAL_SHOWCASE_REPORT.md`

### 5.3 Invalidation Conditions
This report's conclusions are invalidated if:
- Any CMU partition (Detail 1A) is classified as Drywall.
- The 95% CDs progress set disclosure is omitted from the final showcase report.
- Empirical local CPU metrics and theoretical cloud GPU projections are conflated without explicit distinction.
- Vector linework or searchable text layers are degraded or rasterized in exported PDFs.
