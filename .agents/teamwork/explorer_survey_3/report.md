# Dataset & ML Architecture Survey Report
**Module:** `drywall_detection` | **Surveyor:** `survey_explorer_3`
**Date:** 2026-11-07T20:30:00Z | **Status:** Complete & Verified

---

## Executive Summary

This survey establishes the empirical foundations for Requirement **R2** (Dataset Audit & Multi-Dataset Preparation) and Requirement **R3** (Machine Learning Wall Segmentation) of the Drywall Detection pipeline. 

### Core Takeaways:
1. **Dataset Eligibility**:
   - **Top Recommended & Fully Eligible**: **Modified Swiss Dwellings (MSD)** (`philippds/modified-swiss-dwellings-enriched` on Hugging Face: 174 MB download, CC BY 4.0 permissive license, explicit `entity_subtype: WALL` WKT vector polygons, strict `site_id`/`building_id` hierarchical grouping).
   - **Fully Eligible Primary Benchmark**: **CubiCasa5K** (Zenodo Record `2613548`: 5.09 GB download, CC BY-NC-SA 4.0, explicit SVG wall polygons, 5,000 floor plans). Well under the 10 GB unannounced download threshold.
   - **Conditionally Eligible**: **FloorPlanCAD** (454 MB Hugging Face mirror; official Google Drive links active, but CAD drawing copyright disclaimer requires user risk acceptance) and **CVC-FP** (Figshare mirror: 353 MB; original university server timed out; small sample size of 122 plans).
   - **Ineligible for Direct Download**: **R2V (Raster-to-Vector)** (LIFULL raw images are gated behind an academic application and consent agreement with the National Institute of Informatics NII IDR; downloading bypasses access rules without user credentials).
   - **Ineligible for Wall Segmentation**: **SESYD Floorplans** (only contains annotations for 16 furniture/fixture symbols; zero ground-truth wall or partition labels exist in the dataset).

2. **Data Splitting Protocol**:
   - Zero project overlap must be strictly enforced: all sheets, levels, and crops originating from the same building or complex must be assigned atomically to either train, validation, or test. Splitting by image index causes fatal architectural data leakage (footprint geometry, wall line styles, and drafting conventions).

3. **Segmentation Architecture & Training Strategy**:
   - **U-Net with Pretrained Encoder** (ResNet34 / EfficientNet) and **SegFormer** (MiT-B0 / MiT-B1) are the optimal candidate architectures. Semantic segmentation is mathematically superior to instance segmentation (YOLOv8-seg) because architectural walls form continuous connected planar graphs rather than discrete bounding-box entities.
   - Loss function must use a compound **Dice + Focal Loss** (or Dice + Cross-Entropy) to overcome the severe 90:10 background-to-wall class imbalance.
   - The local environment is strictly CPU-based (`torch 2.1.0+cpu`, 0 CUDA VRAM, 7.88 GB RAM with ~0.9 GB free). Google Colab compatibility with automated hardware probing, dynamic batch sizing, and checkpoint saving to Google Drive is vital for scalable training.

4. **Weak Pseudo-Labeling Guardrails (99th Street PDF)**:
   - There is an acute domain gap between residential training datasets and the 99th Street MTA transit facility drawing (dense MEP, CMU/shaft assemblies, dimension strings, hatch patterns).
   - Vector-extracted wall masks may be used for fine-tuning only if explicitly tagged as `weak_pseudo_label`, visually spot-checked for error rate, and **strictly excluded from validation and test splits**.

---

## 1. Deep Audit of the 6 Candidate Datasets

| Dataset | Official Source / Host | Download Size (Raw / Processed) | License Terms | Commercial Use? | Annotation Format | Wall / Partition Labels Present? | Direct Download & Auth Status | Eligibility Verdict |
|---|---|---|---|---|---|---|---|---|
| **Modified Swiss Dwellings (MSD)** | Hugging Face (`philippds/modified-swiss-dwellings-enriched`) & Zenodo (`10.5281/zenodo.7788422`) | **174 MB** (HF download) / **888.7 MB** (Zenodo v3.0.0 zip) | **CC BY 4.0** | **YES** (with attribution) | WKT (Well-Known Text) vector polygons, structured tabular metadata, raster images (`struct_in`, `full_out`) | **YES**: Explicit `entity_type: separator`, `entity_subtype: WALL` with exact polygon boundary coordinates. Multi-apartment complexes. | Direct public HTTPS download via Hugging Face API / Zenodo. No login required. | **ELIGIBLE (Top Recommended)** |
| **CubiCasa5K** | Zenodo (`record/2613548`), GitHub: `CubiCasa/CubiCasa5k` | **5.09 GB** (zip) / ~20-105 GB (uncompressed/LMDB) | **CC BY-NC-SA 4.0** | **NO** (Academic / Non-commercial only) | High-resolution raster images (PNG/JPG) + Vector SVG annotations | **YES**: Over 147,000 explicit wall polygon segments (`<g id="Wall">`), external walls, internal railings. | Direct public download via Zenodo CDN (`cubicasa5k.zip`). No login required. Under 10 GB limit. | **ELIGIBLE (Primary Academic Benchmark)** |
| **FloorPlanCAD** | GitHub Pages (`floorplancad.github.io`), Hugging Face (`Voxel51/FloorPlanCAD`) | **454 MB** (Hugging Face) / ~2.5 GB (Google Drive parts) | Annotations: **CC BY-NC 4.0**; Drawings: Third-party copyright disclaimer | **NO** (Drawing copyright disclaimer leaves risk to user) | SVG vector primitives, PNG images ($20\text{m} \times 20\text{m}$ crops), COCO panoptic format | **YES**: "Wall" is explicitly labeled as an uncountable "Stuff" class alongside 28 "Thing" classes. | Google Drive links active (`1HcyKt...`, `1kSS7...`, `1jxpYg...`); Hugging Face mirror available. | **CONDITIONALLY ELIGIBLE** (CAD domain matches vector drawings; license disclaimer requires caution) |
| **CVC-FP** | Computer Vision Center (UAB), Figshare (`10.6084/m9.figshare.12082131`), Zenodo (`10.5281/zenodo.7921780`) | **~15 MB** (original 122 images) / **353 MB** (Figshare rotated package) | Academic Non-Commercial (CVC) / **CC BY 4.0** (Figshare mirror) | **Conditional** (Mirror is CC BY 4.0) | Scanned rasters (4 styles: Black, Textured1, Textured2, Parallel) + SVG vector ground truth & binary masks | **YES**: Explicit structural wall, door, window, and room segmentation. | Original university server (`dag.cvc.uab.es`) timed out / offline. Figshare / Zenodo mirrors direct download. | **CONDITIONALLY ELIGIBLE** (Small size: 122 plans; good for quick sanity checks) |
| **R2V (Raster-to-Vector)** | CVPR 2017 (`art-programmer/FloorplanTransformation`), LIFULL Co., Ltd. / NII IDR | Annotations: ~10 MB; Images: >10 GB | Annotations: MIT; Images: Proprietary LIFULL institutional agreement | **NO** (Restricted academic data agreement) | Vector representation (junctions, line primitives, text files) | **YES**: Wall junctions and boundary lines annotated in vector format. | **BLOCKED BY ACCESS RESTRICTIONS**: Raster images require formal institutional application to NII IDR. | **INELIGIBLE FOR AUTOMATED DOWNLOAD** (Violates non-interactive constraint) |
| **SESYD Floorplans** | Mathieu Delalandre / IJDAR 2010 (`mathieu.delalandre.free.fr/projects/sesyd/`) | ~6 MB per zip (~100 MB total) | Open Access Academic Research | **NO** (Academic benchmarking) | TIFF binary line drawings + XML symbol bounding boxes | **NO**: Annotations exist exclusively for 16 symbol classes (armchair, table, bed, door, window, sink). **ZERO wall labels**. | Direct public HTTP download without authentication. | **INELIGIBLE FOR WALL SEGMENTATION** (Lacks ground-truth wall annotations) |

### Detailed Breakdown by Candidate

#### 1. Modified Swiss Dwellings (MSD)
- **Official References**: Standfest et al., Archilyse AG & CVAAD Workshop (ECCV 2024). Zenodo DOI `10.5281/zenodo.7788422` (v3.0.0); Hugging Face `philippds/modified-swiss-dwellings-enriched`.
- **Accessibility & Method**: Hugging Face dataset API (`load_dataset('philippds/modified-swiss-dwellings-enriched')`) or Zenodo direct HTTP GET. No credentials or forms required.
- **Data Volume**: The Hugging Face download size is **173.8 MB** (uncompressed ~1.52 GB). Zenodo archive is **888.7 MB**. Both are well below the 10 GB user notification threshold.
- **Labels & Ground Truth**: Features multi-apartment complex floor plans with 1.7 million wall and railing separators encoded in WKT (Well-Known Text) polygons. Wall lines are categorized as `entity_type: separator` and `entity_subtype: WALL`.
- **Project Structure**: Clean hierarchical identifiers: `site_id`, `building_id`, `plan_id`, and `unit_id`.
- **License**: **CC BY 4.0** — fully permissible for research, derivation, and commercial testing with attribution.

#### 2. CubiCasa5K
- **Official References**: Kalervo et al., University of Oulu / CubiCasa. GitHub: `https://github.com/CubiCasa/CubiCasa5k`. Zenodo Record: `2613548`.
- **Accessibility & Method**: Direct HTTP download from Zenodo CDN (`https://zenodo.org/record/2613548/files/cubicasa5k.zip?download=1`).
- **Data Volume**: Compressed archive is **5.09 GB** (5,469,505,066 bytes). (Note: Expanding to an LMDB database generates ~105 GB; therefore, the pipeline should stream or extract only raw PNG/SVG files or a compact subset).
- **Labels & Ground Truth**: 5,000 residential floor plans with rich SVG annotations: walls (`<polygon class="Wall">`), doors, windows, and room types. Over 147,000 wall segments.
- **License**: **CC BY-NC-SA 4.0** — strictly non-commercial research use.

#### 3. FloorPlanCAD
- **Official References**: Fan et al., Alibaba A.I. Labs & Simon Fraser University (ICCV 2021). `https://floorplancad.github.io/`.
- **Accessibility & Method**: Hosted on Google Drive (`Train set 1`, `Train set 2`, `Test set`) and mirrored on Hugging Face (`Voxel51/FloorPlanCAD`, 454 MB).
- **Data Volume**: ~454 MB (HF subset) to ~3.5 GB (full Google Drive CAD drawings).
- **Labels & Ground Truth**: Over 15,000 CAD drawings. Annotations are line-grained SVG primitives with panoptic symbol classes: 28 "Thing" classes and 2 "Stuff" classes (Walls and Parking Areas).
- **License**: Annotations are CC BY-NC 4.0. Crucially, the authors explicitly disclaim copyright ownership of the CAD drawings: *"The users of the dataset accept full responsibility for the use of the dataset, including but not limited to the use of any copies of copyrighted dataset that they may create."*

#### 4. CVC-FP
- **Official References**: de las Heras et al., Computer Vision Center (CVC), UAB. Figshare DOI `10.6084/m9.figshare.12082131`. Zenodo DOI `10.5281/zenodo.7921780`.
- **Accessibility & Method**: Original university server `http://dag.cvc.uab.es/` is currently down (connection timeout). Fully accessible via Figshare mirror (353.6 MB) and Zenodo FP-TXT mirror (1.2 MB).
- **Data Volume**: ~15 MB raw / 353.6 MB preprocessed.
- **Labels & Ground Truth**: 122 scanned floor plans in 4 styles. Vector SVG and raster masks for structural walls, openings, and rooms.
- **License**: CC BY 4.0 (Figshare mirror) / Academic Non-commercial (CVC).

#### 5. R2V (Raster-to-Vector)
- **Official References**: Liu et al., CVPR 2017. GitHub: `art-programmer/FloorplanTransformation`.
- **Accessibility & Method**: **Gated / Restricted**. The repository provides vector graph annotations (junctions, room labels), but the original raster images belong to the LIFULL HOME'S dataset. To obtain the images, users must apply to the National Institute of Informatics (NII) IDR, sign an institutional data use agreement, and await account credentials.
- **Status**: Cannot be downloaded autonomously without violating the constraint against accepting licenses or bypassing authentication on the user's behalf.

#### 6. SESYD Floorplans
- **Official References**: Delalandre et al., IJDAR 2010. `http://mathieu.delalandre.free.fr/projects/sesyd/`.
- **Accessibility & Method**: Directly accessible public HTTP download (~6 MB per zip archive).
- **Labels & Ground Truth**: Contains 16 base synthetic drawings with 1,600 variations stress-testing document degradation. Annotations cover 16 symbol models (doors, windows, armchairs, tables, sinks). **Critically, SESYD contains NO wall segmentation ground truth**.
- **Status**: Ineligible as a ground-truth dataset for wall segmentation.

---

## 2. Data Splitting Architecture & Zero Project Overlap

### The Architectural Data Leakage Vulnerability
In standard computer vision (e.g. ImageNet), images are independent. In architectural CAD and floor plan analysis, multiple drawings frequently originate from the same building or architectural commission:
- Multiple floors of the same building (Basement, Ground, Level 2, Level 3) share the identical outer perimeter footprint, elevator core, structural column grid, and stairwells.
- Multiple drawing sheets from the same architecture firm share identical line weights, hatch patterns, CAD layer colors, dimension arrowheads, and font typographies.

If drawings are split randomly by image index, the neural network memorizes building footprints and firm-specific drafting quirks, reporting artificially high validation metrics ($\text{mIoU} > 95\%$) while failing completely on an unseen drawing.

### Strict Project-Level Partitioning Protocol
1. **Mathematical Condition**:
   Let $\mathcal{P}$ denote the set of source projects/buildings.
   $$\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset, \quad \mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset, \quad \mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$$
   All floors, apartments, crops, and sheets belonging to project $P_k$ must reside exclusively within a single partition:
   $$\forall p \in \text{Sheets}(P_k), \quad \text{Split}(p) = \text{Split}(P_k)$$

2. **Grouping Keys by Dataset**:
   - **Modified Swiss Dwellings**: Partition strictly on `site_id` (or `building_id`). Grouping by `site_id` prevents multi-building campus style leakage.
   - **CubiCasa5K**: Partition strictly on the root floorplan folder identifier (e.g., `high_quality_architectural/<id>`).
   - **FloorPlanCAD**: Partition strictly on the source CAD drawing ID (never by $20\text{m} \times 20\text{m}$ sub-crop tiles!).
   - **99th Street Reference Set**: The entire 71-page PDF represents a single project (MTA Contract C-48526). All pages belong to the same project domain and cannot be split across train and test to prove generalization.

3. **Recommended Partition Ratios**:
   - **Train**: 70% of independent projects
   - **Validation**: 15% of independent projects (for hyperparameter tuning and model selection)
   - **Independent Test**: 15% of independent projects (held-out, evaluated once after training)
   - **Cross-Domain Test**: External evaluation on held-out commercial sheets to test domain transfer.

---

## 3. Machine Learning Segmentation Architecture & Training Strategy

### Architectural Comparison for Architectural Wall Segmentation

| Architecture | Backbone / Variant | Parameter Count | GPU Memory (512x512, BS=8) | Inference Speed (CPU / T4 GPU) | Boundary Sharpness | Suitability for Floor Plan Walls |
|---|---|---|---|---|---|---|
| **U-Net with Pretrained Encoder** | ResNet34 / ResNet50 / EfficientNet-B0 | 21.3M – 32.5M | ~2.4 GB – 3.2 GB | ~85 ms / ~12 ms | **Superior**: Skip connections preserve full spatial resolution for 2–8 px wall boundaries | **Primary Candidate**: Excellent boundary delineation, low memory, stable training |
| **SegFormer** | MiT-B0 / MiT-B1 / MiT-B2 | 3.7M (B0) / 13.7M (B1) / 24.7M (B2) | ~1.6 GB (B0) / ~2.8 GB (B1) | ~110 ms / ~14 ms | **Moderate to High**: Captures global room alignment; lightweight MLP decoder slightly softer at edges | **Primary Candidate**: Mix-Transformer captures long-range structural wall continuity without positional embeddings |
| **YOLOv8-seg** | YOLOv8n-seg / YOLOv8s-seg | 3.2M – 11.2M | ~2.0 GB | ~60 ms / ~10 ms | **Suboptimal**: Box-based mask proposals suffer on sprawling, interconnected walls | **Inferior for Walls**: Walls are continuous "Stuff", not discrete bounding-box "Things". Heavy mask clipping at box boundaries |

#### Why Semantic Segmentation Beats Instance Segmentation for Walls
Walls are not discrete objects like chairs or cars; they form continuous, interconnected planar graphs (T-junctions, cross-junctions, perimeter loops). In instance segmentation (YOLOv8-seg):
1. Bounding boxes for interconnected wall segments overlap almost completely, causing Non-Maximum Suppression (NMS) to erroneously suppress valid wall branches.
2. Slicing continuous corridors into arbitrary box instances creates artificial seams and boundary gaps.
3. Therefore, semantic segmentation (U-Net or SegFormer) outputting a binary wall probability mask $P(\text{wall}) \in [0, 1]$ is the mathematically rigorous choice.

### Loss Function Formulation: Addressing Extreme Class Imbalance
In architectural floor plans, walls typically occupy only **5% to 15%** of drawing pixels, while empty space and room interiors occupy **85% to 95%**. Standard Binary Cross-Entropy (BCE) loss allows the model to achieve 90% accuracy by predicting background everywhere.

To resolve this, training must employ a **Compound Loss Function**:
$$\mathcal{L}_{\text{total}} = \alpha \mathcal{L}_{\text{Dice}} + \beta \mathcal{L}_{\text{Focal}}$$
where:
1. **Soft Dice Loss** directly maximizes foreground intersection over union, invariant to background volume:
   $$\mathcal{L}_{\text{Dice}} = 1 - \frac{2 \sum_{i} p_i y_i + \epsilon}{\sum_{i} p_i^2 + \sum_{i} y_i^2 + \epsilon}$$
2. **Focal Loss** dynamically down-weights easy background pixels, focusing gradient updates on ambiguous wall boundaries, dimension lines, and hatch textures:
   $$\mathcal{L}_{\text{Focal}} = -\alpha_t (1 - p_t)^\gamma \log(p_t), \quad \gamma = 2.0, \; \alpha = 0.25$$
3. **Optional Boundary Loss (Surface Loss)**: Penalizes Hausdorff distance along the wall contour to ensure crisp, straight edges suitable for downstream vectorization.

### Evaluation Metrics Suite
Model evaluation must report the following comprehensive metrics on the independent validation split:
1. **mIoU (Mean Intersection over Union)**: Arithmetic mean of Wall IoU and Background IoU.
2. **Wall IoU (Foreground IoU)**:
   $$\text{IoU}_{\text{wall}} = \frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$$
3. **Dice Coefficient (F1 Score)**: Harmonic mean of precision and recall.
4. **Precision & Recall**:
   - $\text{Precision}$: Penalizes false positives (e.g. mistaking dimension lines or grid lines for walls).
   - $\text{Recall}$: Penalizes false negatives (e.g. broken or missed wall segments).
5. **Boundary IoU (B-IoU)**: Evaluates IoU strictly within a $d$-pixel boundary dilation band ($d = 3\text{ px}$) around the true and predicted wall contours, isolating edge precision from interior area bulk.
6. **Inference Latency & VRAM Footprint**: Documented per model.

### Hardware Environment & Google Colab Compatibility

#### Local Environment Findings (Audited)
- **OS**: Windows 10 (AMD64)
- **CPU**: Intel Core (4 physical / 8 logical cores)
- **System RAM**: 7.88 GB total, **~0.9 GB available** (extreme RAM constraint)
- **Disk Space**: C: has 16.37 GB free; E: has 30.45 GB free
- **PyTorch**: `2.1.0+cpu` (No CUDA GPU available locally)

#### Colab Compatibility Requirements
Because local training on CPU with <1 GB free RAM is strictly bounded, the training pipeline must support seamless, 1-click execution on Google Colab (Tesla T4 GPU with 15.3 GB VRAM):
1. **Hardware Auto-Configuration**:
   ```python
   device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
   if torch.cuda.is_available():
       vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
       batch_size = 16 if vram_gb >= 15 else (8 if vram_gb >= 8 else 4)
       img_size = 512
       use_amp = True
   else:
       batch_size = 2
       img_size = 512
       use_amp = False
   ```
2. **Self-Contained Dependencies**: Standalone `requirements.txt` with pinned versions (`torch`, `torchvision`, `transformers`, `opencv-python-headless`, `shapely`, `timm`).
3. **Headless Execution**: Zero GUI/display calls (`cv2.imshow()`); all visual outputs saved as PNG overlays.
4. **Drive Persistence**: Optional Google Drive mounting hook to save checkpoints across Colab session disconnections.

### Checkpoint Directory Structure
The acceptance criteria specify saving the top-performing model in `drywall_detection/checkpoints/best_model/`. The directory must be completely self-contained:
```
drywall_detection/checkpoints/best_model/
├── best_model.pt               # Trained PyTorch model weights (state_dict)
├── config.json                 # Architecture config (model_type, backbone, num_classes, in_channels, input_size)
├── class_mapping.json          # Index mapping: {"0": "background", "1": "wall"}
├── training_log.json           # Per-epoch loss, val_loss, val_mIoU, val_dice, learning_rate
├── metrics.json                # Final validation metrics (mIoU, wall_iou, dice, precision, recall, boundary_iou)
├── sample_overlays/            # Visual QC validation samples
│   ├── val_001_overlay.png     # Original drawing + GT mask (green) + Pred mask (blue/yellow)
│   ├── val_002_overlay.png
│   └── ...
├── infer.py                    # Standalone reload-and-infer script (loads best_model.pt from disk, runs inference)
├── README.md                   # Model card, training hyperparameters, instructions to reload & reproduce
└── LIMITATIONS.md              # Domain gap analysis, failure modes, resolution bounds
```

---

## 4. Weak Pseudo-Labeling Rules for 99th Street Reference PDF

### The Commercial Infrastructure Domain Gap
The reference PDF (99th Street, MTA Contract C-48526, 71 pages, 1728 x 2592 pt) is a **95% CDs progress set** of a high-complexity public transit facility. There is a profound domain shift between public academic datasets and this drawing:
1. **Structural Complexity**: Public datasets feature residential drywall partitions, single doors, and domestic furniture. The 99th Street drawing features structural steel columns, composite CMU and masonry walls, 2-hour fire-rated shaft walls, and acoustic drywall assemblies.
2. **Dense Annotation Noise**: 99th Street sheets are heavily covered with MEP conduit, structural grid callouts (numbered/lettered bubbles), section cut markers, dimension strings, and architectural hatch patterns (concrete aggregate, diagonal masonry crosshatch).
3. **Visual Density**: A residential-trained model will frequently mistake dimension lines, equipment racks, and grid lines for walls.

### Vector-First Extraction as Weak Pseudo-Labels
Because the 99th Street PDF is a vector PDF with embedded paths, Requirement **R1** extracts geometric wall candidates (parallel line pairs, filled rectangular paths). These vector-extracted candidates can serve as **weak pseudo-labels** to adapt the segmentation model to the commercial CAD style.

### Strict Guardrail Protocol for Weak Pseudo-Labels
To maintain absolute scientific integrity and avoid circular metrics:

1. **Explicit Metadata Tagging**:
   Every vector-extracted mask generated from 99th Street must carry persistent metadata:
   ```json
   {
     "is_pseudo_label": true,
     "label_source": "vector_extraction_weak",
     "confidence": "unverified_automated",
     "drawing_id": "MTA_C48526_99th_Street"
   }
   ```
2. **Mandatory Human-Review Error Rate Spot-Checking**:
   Before any weak pseudo-labels are used for fine-tuning, a visual inspection of **5 to 10 plan regions** must be performed, recording:
   - **False Positive Rate**: Non-wall vector elements (dimension lines, door frames, equipment outlines) incorrectly extracted as walls.
   - **False Negative Rate**: Wall segments missed due to broken lines or hatch interferences.
   - The verified error rate must be explicitly documented in the training report.
3. **Strict Split Isolation (Zero Leakage into Validation or Test)**:
   - Weak pseudo-labels may **ONLY** be used in the training split for semi-supervised fine-tuning or domain adaptation.
   - Weak pseudo-labels are **STRICTLY PROHIBITED** from entering the validation set or the test set.
   - Validation and test metrics ($\text{mIoU}$, $\text{Dice}$, etc.) must **ONLY** be measured against verified ground truth. Evaluating a model on its own pseudo-labels creates invalid, artificially inflated metrics.
4. **Single-Project Progress Set Limitation**:
   - The 99th Street PDF is explicitly a single project progress set ("PROGRESS SET 95% CDs 10/02/2026"), not an approved final as-built drawing.
   - Performance on this drawing cannot prove generalizability to other commercial buildings. All milestone reports (M1 through M6) must document this limitation prominently.

---

## 5. Actionable Implementation Recommendations for Milestone M2 & M4

1. **Milestone M2 (Dataset Preparation)**:
   - Download the **Modified Swiss Dwellings** enriched dataset via Hugging Face (`philippds/modified-swiss-dwellings-enriched`, 174 MB). Its CC BY 4.0 license, clean tabular/WKT wall annotations, and lightweight size make it the optimal primary dataset.
   - If a broader academic benchmark is required, download the **CubiCasa5K** archive from Zenodo (5.09 GB), maintaining strict adherence to the non-commercial license.
   - Partition the datasets strictly by project (`site_id` / folder ID) into 70% Train, 15% Val, 15% Test.
   - Generate visual QC overlays (`original`, `mask`, `overlay`) to verify ground-truth integrity before training.

2. **Milestone M4 (Wall Segmentation Training)**:
   - Train and compare two candidate models:
     - **Candidate A**: U-Net with ResNet34 encoder (using compound Dice + Focal Loss).
     - **Candidate B**: SegFormer-B0 or SegFormer-B1 (using compound Dice + Cross-Entropy Loss).
   - Log hardware specifications dynamically (GPU model, CUDA version, RAM, CPU).
   - Evaluate both models on the held-out project validation split; select the champion model based on validation mIoU, Boundary IoU, memory footprint, and inference latency.
   - Save the best model, configs, class mappings, logs, overlays, and standalone `infer.py` in `drywall_detection/checkpoints/best_model/`.
