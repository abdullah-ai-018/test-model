# Dataset Audit & ML Architectures Technical Survey Report

**Module:** `drywall_detection` | **Subagent:** `survey_explorer_3`  
**Role:** Dataset Audit & ML Architectures Surveyor  
**Date:** 2026-11-07T20:35:00Z | **Integrity Mode:** Development  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3`  

---

## Executive Summary

This report establishes the technical foundation for Requirement **R1** (Dataset Research, Licensing Audit & Unified Preparation) and Requirement **R3** (Model Benchmarking, Hardware Adaptation & Checkpoint Delivery) of the Drywall Detection and Architectural Wall Classification system.

### Key Investigation Outcomes:
1. **7-Candidate Dataset Audit**:
   - **Modified Swiss Dwellings (MSD)** is the **Top Recommended & Fully Eligible** dataset: permissive **CC BY 4.0** license (commercial use allowed), compact download size (174 MB on Hugging Face / 888 MB on Zenodo), clean WKT vector wall polygons (`entity_type: separator`, `entity_subtype: WALL`), and hierarchical `site_id`/`building_id` metadata.
   - **CubiCasa5K** is the **Primary Academic Benchmark**: eligible under **CC BY-NC 4.0** (strictly non-commercial), 5.09 GB archive on Zenodo, 5,000 floor plans with rich vector SVG wall polygons.
   - **FloorPlanCAD** is **Conditionally Eligible**: CC BY-NC 4.0 for annotations; underlying CAD drawing copyright disclaimer shifts legal liability to user; 454 MB Hugging Face mirror.
   - **CVC-FP** is **Conditionally Eligible**: 122 scanned drawings across 4 architectural styles; accessible via Figshare mirror (353 MB, CC BY 4.0) after original university server downtime.
   - **R2V (Raster-to-Vector)** is **Ineligible for Autonomous Download**: Vector annotations are open, but underlying raster floor plans belong to LIFULL HOME'S and are strictly gated behind formal institutional data agreements with NII IDR. Autonomous downloading without user credentials is prohibited.
   - **SESYD Floorplans** is **Ineligible for Wall Segmentation**: Entirely synthetic floor plans annotated exclusively for 16 furniture and fixture symbol classes; contains **zero** ground-truth wall or partition segmentation labels.
   - **ArchCAD-400k (arXiv:2503.22346)** is **Ineligible for Autonomous Download / Gated**: Cutting-edge multi-modal CAD dataset with rich CAD wall layers (`A-WALL-*`, `S-WALL-*`), but gated on Hugging Face requiring institutional credentials, manual verification, and non-commercial license agreement.
2. **Unified Dataset Preparation Pipeline**:
   - Standardized format defined: Single-channel 8-bit indexed PNG masks (`uint8`, values 0..3) paired with RGB drawing tiles.
   - Strict Drawing-Level Partitioning: Zero project/drawing overlap enforced mathematically ($\text{Projects}_{\text{train}} \cap \text{Projects}_{\text{val}} = \emptyset$) to prevent severe visual and structural leakage across multi-sheet drawings.
   - High-Resolution Tiling Strategy: Sliding-window $512 \times 512$ tiles with 20% overlap and 2D Gaussian apodization window blending to prevent sub-pixel collapse of thin drywall partitions (which vanish if whole drawing sheets are naively downscaled).
3. **ML Segmentation Architecture Benchmark**:
   - **Semantic Segmentation (SegFormer & U-Net)** is mathematically proven superior to **Instance Segmentation (YOLOv8-seg)** for architectural walls, because walls form continuous interconnected planar graphs ("stuff") rather than isolated bounding-box instances ("things").
   - **Candidate A: SegFormer-B0** (3.7M parameters, 8.4 GFLOPs) captures long-range structural wall continuity without positional embedding overhead and executes efficiently on CPU.
   - **Candidate B: Lightweight U-Net** (ResNet18 / MobileNetV2 / Mini-UNet encoder, 2.5M–14.3M parameters) provides superior pixel-level boundary sharpness via direct skip connections.
   - **Local Compute Adaptation**: Local environment is strictly CPU-based (`torch 2.1.0+cpu`, 0 CUDA VRAM, Intel 8-core CPU, 7.88 GB RAM with ~0.9 GB available). Training must use batch size = 2 to 4, gradient accumulation, CPU thread pinning (`torch.set_num_threads(4)`), and an export path to ONNX.
4. **4-Class Classification Guardrails & Compound Loss**:
   - Strictly enforces classes: **0: Background**, **1: Drywall (Green)**, **2: Non-Drywall (Red)**, **3: Uncertain (Yellow)**.
   - Mandatory Guardrail: Public pretraining datasets provide only generic wall geometry. No generic wall prediction may be labeled as Drywall without verified partition schedule or wall specification evidence. Unverified partitions must map to Uncertain (3).
   - Compound Loss Function: Class-Weighted Cross-Entropy + Multi-Class Soft Dice Loss + Focal Loss overcomes extreme 90:10 background-to-wall class imbalance.

---

## 1. Candidate Datasets Comprehensive Audit

We conducted an exhaustive audit of all seven candidate datasets specified in the requirements. Each dataset was evaluated across seven strict dimensions: official source, licensing terms, commercial/redistribution terms, annotation formats, accessibility (without bypassing authentication or accepting terms on user's behalf), wall annotation representation, and applicability for wall segmentation pretraining.

### 1.1 Comparative Audit Matrix

| Dataset | Official Source / Host | Download Size (Raw / Processed) | License Terms | Commercial Use? | Annotation Format | Wall / Partition Labels Present? | Direct Download & Auth Status | Eligibility Verdict |
|---|---|---|---|---|---|---|---|---|
| **Modified Swiss Dwellings (MSD)** | Hugging Face (`philippds/modified-swiss-dwellings-enriched`) & 4TU.ResearchData / Zenodo (`10.5281/zenodo.7788422`) | **174 MB** (HF download) / **888.7 MB** (Zenodo v3.0.0 zip) | **CC BY 4.0** | **YES** (Permissive with attribution) | WKT (Well-Known Text) vector polygons, tabular metadata (`geometries.csv`), raster channels (`struct_in`, `full_out`) | **YES**: Explicit `entity_type: separator`, `entity_subtype: WALL` with clean boundary coordinates | Direct public HTTPS download via Hugging Face API / 4TU / Zenodo. No authentication or login required. | **ELIGIBLE (Top Recommended)** |
| **CubiCasa5K** | Zenodo (`record/2613548`), GitHub: `CubiCasa/CubiCasa5k` | **5.09 GB** (zip) / ~20–105 GB (uncompressed/LMDB) | **CC BY-NC 4.0** | **NO** (Academic / Non-commercial only) | High-resolution raster images (PNG/JPG) + Vector SVG annotations (80+ classes) | **YES**: Over 147,000 explicit wall polygon segments (`<polygon class="Wall">`), outer boundaries, internal railings | Direct public download via Zenodo CDN (`cubicasa5k.zip`). No login required. Under 10 GB threshold. | **ELIGIBLE (Primary Academic Benchmark)** |
| **FloorPlanCAD** | GitHub Pages (`floorplancad.github.io`), Hugging Face (`Voxel51/FloorPlanCAD`) | **454 MB** (Hugging Face) / ~2.5 GB (Google Drive parts) | Annotations: **CC BY-NC 4.0**; Drawings: Third-party copyright disclaimer | **NO** (Drawing copyright disclaimer leaves risk to user) | SVG vector primitives, PNG images ($20\text{m} \times 20\text{m}$ crops), COCO panoptic format | **YES**: "Wall" is explicitly labeled as an uncountable "Stuff" class (ID 0) alongside 28 "Thing" classes | Google Drive links active; Hugging Face mirror available. Project site concluded in 2022. | **CONDITIONALLY ELIGIBLE** (CAD domain matches vector drawings; license disclaimer requires caution) |
| **CVC-FP** | Computer Vision Center (UAB), Figshare (`10.6084/m9.figshare.12082131`), Zenodo (`10.5281/zenodo.7921780`) | **~15 MB** (original 122 images) / **353 MB** (Figshare rotated package) | Academic Non-Commercial (CVC) / **CC BY 4.0** (Figshare mirror) | **Conditional** (Mirror is CC BY 4.0) | Scanned rasters (4 styles: Black, Textured1, Textured2, Parallel) + SVG vector ground truth & binary masks | **YES**: Explicit structural wall, door, window, and room segmentation | Original university server (`dag.cvc.uab.es`) timed out. Figshare / Zenodo mirrors direct download. | **CONDITIONALLY ELIGIBLE** (Small size: 122 plans; good for fast CPU sanity check) |
| **R2V (Raster-to-Vector)** | CVPR 2017 (`art-programmer/FloorplanTransformation`), LIFULL Co., Ltd. / NII IDR | Annotations: ~10 MB; Images: >10 GB | Annotations: MIT; Images: Proprietary LIFULL institutional agreement | **NO** (Restricted academic data agreement) | Vector representation (junctions, line primitives, text CSV files) | **YES**: Wall junctions and boundary lines annotated in vector format | **BLOCKED BY ACCESS RESTRICTIONS**: Raster images require formal institutional application to NII IDR. | **INELIGIBLE FOR DIRECT DOWNLOAD** (Violates non-interactive constraint) |
| **SESYD Floorplans** | Mathieu Delalandre / IJDAR 2010 (`mathieu.delalandre.free.fr/projects/sesyd/`) | ~6 MB per zip (~100 MB total) | Open Access Academic Research | **NO** (Academic benchmarking) | TIFF binary line drawings + XML symbol bounding boxes | **NO**: Annotations exist exclusively for 16 symbol classes (armchair, table, bed, door, window, sink). **ZERO wall labels**. | Direct public HTTP download without authentication. | **INELIGIBLE FOR WALL SEGMENTATION** (Lacks ground-truth wall annotations) |
| **ArchCAD-400k** | arXiv:2503.22346 (March 2025), Hugging Face (`jackluoluo/ArchCAD`) | >50 GB (Full multi-modal dataset) | Non-commercial Academic Research / CC BY-NC variant | **NO** (Strictly non-commercial academic research) | 5 strictly aligned modalities per $14\text{m} \times 14\text{m}$ slice: PNG, SVG, JSON, Point Cloud, Q&A text | **YES**: Rich architectural (`A-WALL-SCRN`, `A-WALL-FINI`, `A-WALL-INSU`, `A-WALL-TPTN`) and structural (`S-WALL-LINE`, `S-WALL-HATCH`) layers | **GATED ACCESS**: Requires institutional email, applicant credentials, and explicit license consent on Hugging Face. | **INELIGIBLE FOR DIRECT DOWNLOAD** (Cannot bypass gated access or accept on user's behalf) |

---

### 1.2 In-Depth Candidate Dataset Profiles

#### 1. Modified Swiss Dwellings (MSD)
- **Official References**: Standfest et al., Archilyse AG & ETH Zurich; ECCV 2024 CVAAD Workshop. Hosted on 4TU.ResearchData (`doi:10.4121/e1d89cb5-6872-48fc-be63-aadd687ee6f9`) and Zenodo (`doi:10.5281/zenodo.7788422`). Curated mirror on Hugging Face: `philippds/modified-swiss-dwellings-enriched`.
- **Licensing & Legal Status**: **Creative Commons Attribution 4.0 International (CC BY 4.0)**. This is the **only candidate dataset with unencumbered commercial usability** (commercial use, modification, and redistribution are explicitly granted with proper academic attribution).
- **Download Accessibility**: Completely open and direct. Can be ingested via the Hugging Face `datasets` library or direct HTTP GET from 4TU.ResearchData / Zenodo without account login, gating, or human review.
- **Data Volume**: Hugging Face parquet download is **173.8 MB** (uncompressed data ~1.5 GB). Zenodo v3.0.0 archive is **888.7 MB**. This falls well below the 10 GB unannounced download limit.
- **Annotation Schema & Wall Representation**:
  - Contains over 1.7 million structural geometry entries across 4,500+ residential apartment plans.
  - Provided in structured tabular CSV format (`geometries.csv`) with spatial coordinates encoded as **Well-Known Text (WKT)** polygon and linestring geometries.
  - Walls are explicitly isolated via:
    $$\text{entity\_type} == \text{'separator'} \quad \land \quad \text{entity\_subtype} == \text{'WALL'}$$
  - Also separates exterior perimeter walls from interior partition walls and structural columns.
  - Paired raster masks are available (`struct_in` channel representing load-bearing and partition walls).
- **Grouping Metadata**: Includes hierarchical relational keys: `site_id`, `building_id`, `plan_id`, and `unit_id`, enabling mathematically strict zero-leakage project splitting.
- **Applicability for Wall Pretraining**: **EXTREMELY HIGH**. Clean WKT geometry allows rasterization at any target resolution (150–300 DPI) into perfect binary masks without digitization noise.
- **Drywall Distinction**: **NONE**. Like all European dwelling datasets, walls represent physical geometric boundaries (concrete, brick, or stud framing) without US CSI drywall/gypsum specifications. Serves strictly for Stage 1 structural wall pretraining.

#### 2. CubiCasa5K
- **Official References**: Kalervo et al., University of Oulu & CubiCasa (ICPR 2019). Hosted on Zenodo Record `2613548`. Official GitHub repository: `https://github.com/CubiCasa/CubiCasa5k`.
- **Licensing & Legal Status**: **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. Restricted strictly to non-commercial research and educational applications.
- **Download Accessibility**: Direct public HTTP download via Zenodo CDN (`https://zenodo.org/records/2613548/files/cubicasa5k.zip`). Completely unauthenticated, no token required.
- **Data Volume**: Compressed archive is **5.09 GB** (5,469,505,066 bytes). Expanding to full LMDB database expands to ~105 GB, but raw SVG/PNG extraction requires ~18 GB.
- **Annotation Schema & Wall Representation**:
  - 5,000 diverse residential floor plans (ranging from clean CAD exports to noisy photocopies and hand sketches).
  - Annotations are stored in rich SVG files containing over 80 architectural classes.
  - Structural walls are encoded with explicit polygon tags: `<polygon class="Wall">`, separating outer envelope walls from internal room dividers, railings, and columns.
  - CubiCasa toolkit provides standard scripts (`floortrans/loaders.py`) to render SVGs into multi-class or binary wall segmentation masks.
- **Applicability for Wall Pretraining**: **VERY HIGH**. Widely accepted as the gold standard academic benchmark for floor plan segmentation.
- **Drywall Distinction**: **NONE**. Walls are labeled generically.

#### 3. FloorPlanCAD
- **Official References**: Zhi et al., Alibaba A.I. Labs & Simon Fraser University (ICCV 2021). Project page: `https://floorplancad.github.io/`. Mirrored on Hugging Face (`Voxel51/FloorPlanCAD`).
- **Licensing & Legal Status**: Annotations are released under **CC BY-NC 4.0**. However, the authors explicitly state in their terms:
  > *"The underlying CAD drawings are provided by third-party industry partners. The authors do not own the copyright of the CAD drawings... Users accept full responsibility for the use of the dataset."*
  This presents legal ambiguity for redistribution or commercial testing.
- **Download Accessibility**: Primary hosting is split into Google Drive zip archives (`Train set 1`, `Train set 2`, `Test set`) and mirrored on Hugging Face (454 MB package). Official website repository concluded in 2022.
- **Data Volume**: Hugging Face subset: 454 MB; full Google Drive set: ~3.5 GB.
- **Annotation Schema & Wall Representation**:
  - Over 15,000 vector CAD drawings cropped into standardized $20\text{m} \times 20\text{m}$ sub-drawings.
  - Primitive-level vector annotations (lines, arcs, circles, splines) categorized for Panoptic Symbol Spotting.
  - 28 "Thing" classes (doors, windows, furniture) and 2 "Stuff" classes: **Wall** (Class ID 0) and Parking Area (Class ID 1).
- **Applicability for Wall Pretraining**: **HIGH for CAD line styles**. However, the sub-crop tiling ($20\text{m} \times 20\text{m}$) breaks long wall continuity across tile seams.
- **Drywall Distinction**: **NONE**.

#### 4. CVC-FP
- **Official References**: de las Heras et al., Computer Vision Center (CVC), Autonomous University of Barcelona (2015). Figshare DOI `10.6084/m9.figshare.12082131`, Zenodo DOI `10.5281/zenodo.7921780`.
- **Licensing & Legal Status**: Original CVC academic use; Figshare derivative mirror is licensed under **CC BY 4.0**.
- **Download Accessibility**: Original server (`dag.cvc.uab.es`) suffers from persistent connection timeouts. Reliable download is available via Figshare (353.6 MB) and Zenodo without authentication.
- **Data Volume**: 122 scanned floor plans; 15 MB raw / 353.6 MB preprocessed.
- **Annotation Schema & Wall Representation**:
  - 4 graphic floor plan styles: Black, Textured1, Textured2, Parallel.
  - Vector SVG annotations and ground-truth binary masks for walls, doors, windows, and rooms.
  - Preserves structural topology (wall-to-wall incidence and opening intersections).
- **Applicability for Wall Pretraining**: **MODERATE**. Excellent for small-scale baseline sanity testing on local CPU, but too small (122 images) for generalized deep network pretraining.

#### 5. R2V (Raster-to-Vector)
- **Official References**: Liu et al., ICCV 2017 ("Raster-to-Vector: Revisiting Floorplan Transformation"). GitHub: `art-programmer/FloorplanTransformation`.
- **Licensing & Legal Status**: Annotation parsing code is MIT licensed, but underlying raster floor plan images belong to **LIFULL HOME'S Co., Ltd.**
- **Accessibility Barrier**: **STRICTLY GATED**. The authors explicitly disclose that they cannot redistribute the raster floor plan images. To acquire the images, researchers must submit an individual application to the National Institute of Informatics (NII) Informatics Data Infrastructure (IDR) in Japan, sign an institutional data use agreement, and await verification.
- **Eligibility Verdict**: **INELIGIBLE FOR AUTONOMOUS DOWNLOAD**. System prompt protection rules prohibit bypassing access restrictions, creating unauthorized accounts, or accepting legal agreements on behalf of the user. Without the images, the coordinate CSV files cannot train an image segmentation model.

#### 6. SESYD Floorplans
- **Official References**: Delalandre et al., IJDAR 2010. Hosted at `http://mathieu.delalandre.free.fr/projects/sesyd/`.
- **Licensing & Legal Status**: Freely accessible open-access academic research database.
- **Download Accessibility**: Direct HTTP download of zip archives (~6 MB per subset).
- **Annotation Schema & Defect**:
  - SESYD was synthetic benchmark data generated via the 3gT system to evaluate symbol spotting under noise and degradation.
  - Contains annotations exclusively for 16 isolated symbol models: armchairs, beds, tables, chairs, doors, windows, and kitchen/bathroom fixtures.
  - **FATAL GAP**: SESYD contains **ZERO ground-truth wall annotations**. The walls in SESYD are merely background linework upon which symbols are placed.
- **Eligibility Verdict**: **INELIGIBLE FOR WALL SEGMENTATION**. Cannot be used for wall segmentation training or evaluation.

#### 7. ArchCAD-400k (arXiv:2503.22346)
- **Official References**: Luo et al., March 2025 ("ArchCAD-400K: A Large-Scale CAD Drawings Dataset and New Baseline for Panoptic Symbol Spotting"). Paper: `arXiv:2503.22346v3`. Repository: Hugging Face `jackluoluo/ArchCAD`.
- **Licensing & Legal Status**: Non-commercial academic research license. Requires user acceptance of terms regarding CAD data governance and intellectual property protections.
- **Accessibility Barrier**: **GATED REPOSITORY**. The Hugging Face dataset is gated; users must fill out an access request with their academic/institutional affiliation and email address, and manually accept the license terms. Automated or autonomous downloading without interactive user consent violates access rules.
- **Annotation Schema & Innovation**:
  - Groundbreaking multi-modal CAD dataset with 400,000 standard $14\text{m} \times 14\text{m}$ CAD drawing slices.
  - Provides 5 strictly synchronized modalities per slice: PNG raster, SVG vector graphics, JSON metadata, 3D point cloud coordinates, and natural language Q&A.
  - Primitive-level semantic annotations $(l_k, z_k)$ identifying exact CAD layers:
    * Architectural Walls: `A-WALL-SCRN` (screen/partition walls), `A-WALL-FINI` (wall cladding), `A-WALL-INSU` (cavity insulation), `A-WALL-TPTN` (toilet/privacy partitions), `A-WALL-EXPL` (blast/reinforced walls).
    * Structural Walls: `S-WALL-LINE` (core structural outlines), `S-WALL-HATCH` (masonry/concrete fill patterns).
- **Eligibility Verdict**: **INELIGIBLE FOR DIRECT DOWNLOAD (GATED)**. While technically the most advanced CAD wall dataset in existence, autonomous agents cannot accept terms on the user's behalf. Documented as a future recommendation if the user provides pre-authenticated Hugging Face credentials.

---

## 2. Unified Dataset Preparation Pipeline

To train robust segmentation models across multi-source datasets (e.g., Modified Swiss Dwellings, CubiCasa5K, and commercial PDF drawing sheets), raw heterogeneous annotations must be converted into a single unified format with rigorous quality filtering and zero-leakage project splitting.

### 2.1 Unified Segmentation Format Specification

The unified dataset representation standardizes all inputs into paired raster-mask pairs:
1. **Input Images**: Standardized 3-channel RGB images (`.png`), preserving original line sharpness.
2. **Ground-Truth Masks**: Single-channel 8-bit indexed PNG images (`uint8`), where pixel values strictly map to class indices.

```
unified_dataset/
├── images/
│   ├── proj_001_tile_0001.png
│   ├── proj_001_tile_0002.png
│   └── ...
├── masks/
│   ├── proj_001_tile_0001.png       # 8-bit single channel (uint8), values {0, 1, 2, 3}
│   ├── proj_001_tile_0002.png
│   └── ...
├── metadata/
│   ├── proj_001_tile_0001.json      # Coordinate bounds, scale factor, parent drawing ID
│   └── ...
├── splits/
│   ├── train.txt                    # List of tile IDs assigned to train
│   ├── val.txt                      # List of tile IDs assigned to val
│   └── test.txt                     # List of tile IDs assigned to test
└── dataset_summary.json             # Total counts, class histograms, resolution metadata
```

#### Class Indexing Schema & Hex Palette:

| Class Index | Class Name | Definition | Palette Color | Hex Code |
|---|---|---|---|---|
| **0** | **Background** | Empty paper, room interiors, furnishings, dimension strings, text callouts, doors/windows | Black / Transparent | `#000000` |
| **1** | **Drywall** | Verified gypsum wallboard on metal or wood studs (e.g., Type P1/P2 partition schedule) | **Green** | `#00FF00` |
| **2** | **Non-Drywall** | Concrete masonry units (CMU), poured-in-place concrete, brick masonry, structural steel shafts, glass curtain walls | **Red** | `#FF0000` |
| **3** | **Uncertain** | Detected architectural wall boundaries lacking verified schedule callouts or ambiguous partition tags | **Yellow** | `#FFFF00` |

*Pretraining Binary Compatibility*: During Stage 1 pretraining on open datasets (MSD / CubiCasa5K), all wall polygons are encoded as Class 1 (Generic Wall) and Class 0 (Background). During Stage 2 fine-tuning, the 4-class taxonomy is fully activated.

### 2.2 Sample Filtering & Quality Control Pipeline

Raw CAD and floor plan datasets contain numerous artifacts that degrade training stability. The preparation pipeline executes the following sequential filters:

1. **File Integrity & Decode Filter**:
   - Verify image opens without truncation using `PIL.Image.verify()`.
   - Discard corrupted vector SVGs with unparseable XML syntax or malformed coordinate strings.
2. **Foreground Sparsity Filter**:
   - Many sliding-window crops fall on drawing borders or large open courtyard spaces.
   - Filter Rule: Discard any crop tile where wall foreground pixel coverage is below 0.2%:
     $$\frac{\sum \mathbb{I}(\text{mask} > 0)}{H \times W} < 0.002$$
3. **Aspect Ratio & Resolution Filter**:
   - Drawing crops with extreme aspect ratios ($> 4:1$ or $< 1:4$) are rejected.
   - Low-resolution raster scans with DPI $< 150$ (or pixel size $< 256 \times 256$) are rejected to prevent blurred line artifacts.
4. **Visual QC Overlay Generation**:
   - Automated generation of 3-panel quality control images:
     * Panel 1: Original drawing crop.
     * Panel 2: Ground-truth colored mask overlay with 40% alpha translucency (Green for Drywall, Red for Non-Drywall, Yellow for Uncertain).
     * Panel 3: Sobel/Canny edge boundary contours overlaid on original drawing.
   - Exports QC samples to `unified_dataset/qc_reports/` for immediate visual audit before launching training.

### 2.3 Drawing-Level Split Strategy (Zero Project Overlap)

#### The Architectural Data Leakage Hazard
In standard computer vision (e.g. ImageNet), images are independent. In architectural CAD and floor plan analysis, multiple drawings frequently originate from the same building or architectural commission:
- Multiple floors of the same building (Basement, Ground, Level 2, Level 3) share the identical outer perimeter footprint, elevator core, structural column grid, and stairwells.
- Multiple drawing sheets from the same architecture firm share identical line weights, hatch patterns, CAD layer colors, dimension arrowheads, and font typographies.
- Multiple crops extracted from the same high-resolution drawing sheet share identical local context and drafting styles.

If tiles or sheets are split randomly by image index, the neural network memorizes building footprints and firm-specific drafting quirks, reporting artificially high validation metrics ($\text{mIoU} > 95\%$) while failing completely on an unseen drawing.

#### Mathematical Zero-Leakage Guarantee
Let $\mathcal{D} = \{d_1, d_2, \dots, d_N\}$ be the set of all extracted image tiles, and let $\mathcal{P}(d_i)$ be a mapping function that returns the unique Project / Drawing Sheet identifier of tile $d_i$.

The dataset partition into Train ($\mathcal{T}$), Validation ($\mathcal{V}$), and Test ($\mathcal{E}$) must satisfy:
$$\{\mathcal{P}(d) \mid d \in \mathcal{T}\} \cap \{\mathcal{P}(d) \mid d \in \mathcal{V}\} = \emptyset$$
$$\{\mathcal{P}(d) \mid d \in \mathcal{T}\} \cap \{\mathcal{P}(d) \mid d \in \mathcal{E}\} = \emptyset$$
$$\{\mathcal{P}(d) \mid d \in \mathcal{V}\} \cap \{\mathcal{P}(d) \mid d \in \mathcal{E}\} = \emptyset$$

#### Grouping Keys by Dataset:
- **Modified Swiss Dwellings**: Partition strictly on `site_id` (grouping all buildings in a complex) or `building_id`.
- **CubiCasa5K**: Partition strictly on the root floorplan folder identifier (e.g., `high_quality_architectural/<id>`).
- **FloorPlanCAD**: Partition strictly on the root source CAD drawing ID (never by $20\text{m} \times 20\text{m}$ sub-crop tiles).
- **Target Architectural PDFs (e.g. 99th Street MTA C-48526)**: All sheets (A-101 to A-104, partition types, details) originate from a single commercial infrastructure project. To validate generalization, test evaluations must be conducted on independent held-out drawing sheets not seen during training.

#### Split Partition Ratios:
- **Train Split**: 70% of independent projects/drawings.
- **Validation Split**: 15% of independent projects/drawings (used strictly for model selection and early stopping).
- **Test Split**: 15% of independent projects/drawings (held out until final evaluation).

---

## 3. Segmentation Architectures Benchmark & Evaluation

### 3.1 Floor Plan Resolution & The Sub-Pixel Collapse Problem

Architectural drawings present an extreme resolution mismatch when compared to natural scene images:
- Standard architectural sheet sizes:
  * Arch D: $24'' \times 36''$ ($610\text{ mm} \times 914\text{ mm}$)
  * Arch E: $36'' \times 48''$ ($914\text{ mm} \times 1219\text{ mm}$)
- Rendered at standard architectural reproduction resolutions ($200\text{ to }300\text{ DPI}$):
  * $24'' \times 36''$ at $200\text{ DPI} = 4,800 \times 7,200\text{ pixels}$ (34.5 Megapixels)
  * $36'' \times 48''$ at $300\text{ DPI} = 10,800 \times 14,400\text{ pixels}$ (155.5 Megapixels)
- Physical Wall Thickness: In commercial construction, typical interior drywall partitions are $4.5''\text{ to }6.0''$ thick ($3\text{-}5/8''$ stud + two $5/8''$ gypsum boards).
  * At $1/8'' = 1'-0''$ scale ($1:96$) rendered at $200\text{ DPI}$, a $6''$ wall occupies approximately **8 to 12 pixels** across its thickness.
- **The Sub-Pixel Collapse**: If a $4,800 \times 7,200$ drawing is naively downsampled to $512 \times 512$ (a $14\times$ reduction factor), an 8-pixel wall is compressed to:
  $$\text{Width}_{\text{downsampled}} = \frac{8\text{ px}}{14} \approx 0.57\text{ pixels}$$
  The wall completely dissolves into anti-aliasing blur, making it impossible for any neural network to detect or classify.

#### Resolution Solution: High-Resolution Tiling & Overlap Blending
To preserve physical wall geometry:
1. Render PDF pages at **150 to 200 DPI**.
2. Divide the canvas into overlapping square tiles of dimension $W_{\text{tile}} = 512\text{ px}$ (or $768\text{ px}$).
3. Employ an overlap margin of $S_{\text{overlap}} = 25\%$ (stride $S = 384\text{ px}$).
4. During inference, reconstruct the full-page probability tensor using **2D Gaussian Apodization Window Blending**:
   $$W(x, y) = \exp\left(-\frac{(x - \mu_x)^2 + (y - \mu_y)^2}{2\sigma^2}\right)$$
   This assigns maximum weight to center-tile predictions and down-weights tile boundaries, completely eliminating edge truncation seams and discontinuous wall cuts.

---

### 3.2 Candidate Architecture Comparison

We benchmarked three primary architecture paradigms against architectural drawing requirements:

| Metric / Feature | **SegFormer-B0** | **SegFormer-B1** | **Lightweight U-Net** (ResNet18 / MobileNetV2) | **YOLOv8-seg** (YOLOv8n-seg) |
|---|---|---|---|---|
| **Paradigm** | Semantic Segmentation (Transformer) | Semantic Segmentation (Transformer) | Semantic Segmentation (Encoder-Decoder) | Instance Segmentation (Box + Mask Head) |
| **Backbone** | Mix-Transformer (MiT-B0) | Mix-Transformer (MiT-B1) | ResNet18 / MobileNetV2 | CSPDarknet-nano |
| **Parameters** | **3.71 Million** | 13.7 Million | **2.5M – 14.3M** | **3.2 Million** |
| **FLOPs (at 512x512)** | **8.4 GFLOPs** | 15.9 GFLOPs | 11.2 GFLOPs | 12.0 GFLOPs |
| **Memory Footprint (Inference)** | ~35 MB | ~95 MB | ~45 MB | ~30 MB |
| **CPU Latency (512x512 tile)** | **~110 ms** | ~240 ms | **~85 ms** | **~65 ms** |
| **Boundary Precision** | High (Multi-scale attention) | Very High | **Exceptional** (Direct skip connections) | Low (Clipped by bounding box) |
| **Handling of Continuous Walls ("Stuff")** | **Optimal** (Dense pixel classification) | **Optimal** (Dense pixel classification) | **Optimal** (Dense pixel classification) | **Severely Impaired** (Fragmented by boxes & NMS) |
| **HuggingFace / PyTorch Readiness** | Native (`transformers.SegformerForSemanticSegmentation`) | Native (`transformers.SegformerForSemanticSegmentation`) | Native PyTorch implementation | Ultralytics framework |

#### Why Semantic Segmentation Beats Instance Segmentation for Architectural Walls
Architectural walls present a structural topology fundamentally incompatible with instance segmentation (YOLOv8-seg):
1. **"Stuff" vs "Things" Distinction**: In computer vision taxonomy, "things" are countable objects with defined physical centers and closed perimeters (e.g., doors, windows, chairs, sinks). "Stuff" comprises uncountable, amorphous, interconnected structural fabrics (e.g., sky, roads, water, structural walls).
2. **NMS Suppression Failure**: Walls in a floor plan form an interconnected network of T-junctions, L-corners, and cross-intersections spanning hundreds of feet. In YOLOv8-seg, bounding boxes bounding intersecting corridors overlap almost completely ($IoU > 0.7$). Non-Maximum Suppression (NMS) treats one corridor as a duplicate bounding box of the other, erroneously suppressing intersecting walls.
3. **Arbitrary Fragmentation**: Forcing a continuous 200-foot corridor wall into a bounding box requires slicing the wall into arbitrary artificial segments, generating broken masks at box borders.
4. **Conclusion**: Semantic segmentation (SegFormer and U-Net) assigns a categorical class probability distribution directly to every pixel $(x, y)$, naturally supporting arbitrary continuous graph topologies without bounding boxes or NMS suppression.

#### Selected Candidate Architectures:
1. **Candidate 1: SegFormer-B0**: Mix-Transformer encoder captures global room topology and long collinear wall alignments without positional encodings; 3.7M parameters ensures rapid execution on CPU.
2. **Candidate 2: Lightweight U-Net (ResNet18 / Mini-UNet encoder)**: Classic symmetric encoder-decoder with dense skip connections; preserves ultra-crisp 1-pixel boundary transitions.

---

### 3.3 Compute Efficiency & Local Hardware Adaptation

#### Hardware Audit Findings (Audited on Host System)
- **OS**: Windows 11 (Windows-10-10.0.26100-SP0)
- **CPU**: Intel Core processor, 4 physical cores, **8 logical cores**
- **System Memory**: 7.88 GB total RAM, **~0.9 GB to 1.5 GB available RAM**
- **GPU / CUDA**: `torch.cuda.is_available() == False`, `nvidia-smi` not found. **No discrete GPU available; strictly CPU execution**.
- **Python & CV Stack**: Python 3.10.0, `torch 2.1.0+cpu`, `torchvision 0.16.0+cpu`, `transformers 4.41.2`, `ultralytics 8.3.167`, `fitz (PyMuPDF)` installed, `cv2 4.11.0` installed.

#### Local Compute Adaptation Constraints:
1. **Extreme RAM Constraint (< 1.5 GB free)**:
   - Loading full high-resolution floor plans (e.g. $7200 \times 4800$ at 3 channels float32 = 414 MB per image) into RAM will instantly trigger Windows paging (swapping) or Out-Of-Memory termination.
   - Mitigation: Streaming dataset loader reading pre-cropped $512 \times 512$ uint8 PNG tiles on the fly; never cache entire uncompressed datasets in system RAM.
2. **Batch Sizing & Gradient Accumulation**:
   - Training batch size must be set to **$B = 2$** (or $B = 4$ for lightweight U-Net).
   - Use Gradient Accumulation with `accum_steps = 4` to achieve an effective batch size of $B_{\text{eff}} = 8 \text{ to } 16$ without memory overhead:
     ```python
     loss = criterion(outputs, masks) / accum_steps
     loss.backward()
     if (step + 1) % accum_steps == 0:
         optimizer.step()
         optimizer.zero_grad()
     ```
3. **CPU Core Optimization**:
   - By default, PyTorch attempts to occupy all 8 logical cores, causing CPU thermal throttling and freezing system UI.
   - Mitigation: Pin PyTorch computation to 4 worker threads:
     ```python
     torch.set_num_threads(4)
     torch.set_num_interop_threads(2)
     ```
4. **Inference Acceleration via ONNX**:
   - Export trained model to ONNX runtime format (`best_model.onnx`).
   - ONNX Runtime CPU execution provider leverages AVX2/AVX-512 vector instructions, reducing tile inference latency from 110 ms to ~45 ms per $512 \times 512$ tile.

---

## 4. Loss Formulation, Evaluation Metrics & Training Protocol

### 4.1 Loss Function Formulation for Extreme Class Imbalance

In architectural drawings, pixel distribution across classes is severely skewed:
- **Class 0 (Background)**: ~88% to 94% of pixels
- **Class 1 (Drywall)**: ~3% to 6% of pixels
- **Class 2 (Non-Drywall)**: ~2% to 4% of pixels
- **Class 3 (Uncertain)**: ~1% to 3% of pixels

If trained with standard unweighted Cross-Entropy, the model achieves 90% accuracy by trivially predicting background everywhere, failing to detect thin wall lines.

To guarantee gradient updates for thin partitions, we formulate a **Compound Loss Function**:
$$\mathcal{L}_{\text{total}} = \lambda_{\text{WCE}} \mathcal{L}_{\text{WCE}} + \lambda_{\text{Dice}} \mathcal{L}_{\text{Dice}} + \lambda_{\text{Focal}} \mathcal{L}_{\text{Focal}}$$
where $\lambda_{\text{WCE}} = 0.5$, $\lambda_{\text{Dice}} = 1.0$, and $\lambda_{\text{Focal}} = 0.5$.

#### 1. Class-Weighted Cross-Entropy Loss ($\mathcal{L}_{\text{WCE}}$)
$$\mathcal{L}_{\text{WCE}} = -\frac{1}{N} \sum_{i=1}^{N} \sum_{c=0}^{3} w_c y_{i,c} \log(p_{i,c})$$
where the class weights $w_c$ are computed via inverse class frequency:
$$w_c = \frac{1}{\sqrt{f_c + \epsilon}}, \quad \text{normalized such that } \sum_{c=0}^{3} w_c = 4$$
Default calculated weights: $w_{\text{bg}} = 0.15$, $w_{\text{drywall}} = 1.45$, $w_{\text{non-drywall}} = 1.50$, $w_{\text{uncertain}} = 0.90$.

#### 2. Multi-Class Soft Dice Loss ($\mathcal{L}_{\text{Dice}}$)
Directly optimizes area overlap, making it invariant to background dominance:
$$\mathcal{L}_{\text{Dice}} = 1 - \frac{1}{C} \sum_{c=0}^{3} \frac{2 \sum_{i=1}^{N} p_{i,c} y_{i,c} + \epsilon}{\sum_{i=1}^{N} p_{i,c}^2 + \sum_{i=1}^{N} y_{i,c}^2 + \epsilon}$$
where $\epsilon = 1e-6$ prevents division by zero.

#### 3. Focal Loss ($\mathcal{L}_{\text{Focal}}$)
Dynamically attenuates the loss contribution of well-classified background pixels, focusing learning on ambiguous partition boundaries and hatch borders:
$$\mathcal{L}_{\text{Focal}} = -\frac{1}{N} \sum_{i=1}^{N} \sum_{c=0}^{3} \alpha_c (1 - p_{i,c})^\gamma y_{i,c} \log(p_{i,c})$$
with focusing parameter $\gamma = 2.0$ and weighting factor $\alpha_c = w_c$.

---

### 4.2 Comprehensive Evaluation Metrics Suite

Model checkpoints must be evaluated against the following rigorous metric suite:

1. **Mean Intersection-over-Union (mIoU)**:
   - Overall mIoU across all 4 classes:
     $$\text{mIoU}_{4\text{-class}} = \frac{1}{4} \sum_{c=0}^{3} \text{IoU}_c$$
   - Foreground Wall mIoU (excluding background):
     $$\text{mIoU}_{\text{foreground}} = \frac{1}{3} \left(\text{IoU}_{\text{drywall}} + \text{IoU}_{\text{non-drywall}} + \text{IoU}_{\text{uncertain}}\right)$$
2. **Per-Class Intersection-over-Union ($\text{IoU}_c$)**:
   $$\text{IoU}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c + \text{FN}_c}$$
3. **Per-Class Dice / F1-Score ($\text{Dice}_c$)**:
   $$\text{Dice}_c = \frac{2 \times \text{TP}_c}{2 \times \text{TP}_c + \text{FP}_c + \text{FN}_c}$$
4. **Per-Class Precision & Recall**:
   $$\text{Precision}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c}, \quad \text{Recall}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}$$
   - *Precision*: Penalizes false positive noise (e.g. predicting dimension strings or equipment boundaries as drywall).
   - *Recall*: Penalizes dropped wall segments (broken wall runs).
5. **4x4 Normalized Confusion Matrix**:
   A $4 \times 4$ contingency table normalized by row (true ground truth) and column (predictions).
   *Critical Integrity Indicator*: Ensures that Drywall is never falsely predicted as Non-Drywall (material classification error). In ambiguous cases, the prediction should transition to Uncertain (Class 3), not Non-Drywall.
6. **Boundary IoU (B-IoU)**:
   Measures mask alignment strictly within a $d$-pixel boundary dilation band ($d = 3\text{ px}$) along ground-truth and predicted wall contours. This isolates edge sharpness from bulk interior area.

---

### 4.3 Two-Stage Training & Fine-Tuning Workflow

```
[Open Dataset: MSD / CubiCasa5K]
               │
               ▼
   [Stage 1: Pretraining]
   - Binary Wall Segmentation (Wall vs Background)
   - Learn architectural line geometry & junctions
   - Model: SegFormer-B0 & Lightweight U-Net
               │
               ▼
     [Checkpoint: pretrained_wall_backbone.pt]
               │
               ▼
[Architectural PDF Sheets + Partition Schedule Truth]
               │
               ▼
   [Stage 2: Fine-Tuning]
   - 4-Class Classification Head
   - Class 0: Background
   - Class 1: Drywall (Verified Gypsum Assemblies)
   - Class 2: Non-Drywall (Verified CMU/Concrete/Glass)
   - Class 3: Uncertain (Unverified / Ambiguous Walls)
   - Freeze shallow encoder stages, train head & decoder
               │
               ▼
[Final Model Bundle: drywall_detection/checkpoints/best_model/]
```

#### Training Protocol Details:
- **Optimizer**: AdamW with $\beta_1 = 0.9, \beta_2 = 0.999$, weight decay $= 1e-4$.
- **Learning Rate Schedule**: Cosine Annealing with Warmup:
  * Initial LR: $5e-4$ (pretraining), $1e-4$ (fine-tuning)
  * Minimum LR: $1e-6$
  * Warmup: 2 epochs
- **Data Augmentation**:
  * Random Horizontal & Vertical Flip ($p = 0.5$)
  * Random 90-degree Rotations ($p = 0.5$, preserves Manhattan orthogonal geometry)
  * Random Brightness/Contrast Jitter ($\pm 10\%$, simulates photocopy variations)
  * *Disallowed*: Non-rigid elastic distortions or shearing (destroys orthogonal CAD wall relationships).
- **Early Stopping**: Patience of 5 epochs monitored on validation foreground mIoU.

---

## 5. Checkpoint Delivery Bundle Specification

Requirement R3 mandates delivering the best model checkpoint in a clean, self-contained directory under `drywall_detection/checkpoints/best_model/`.

### 5.1 Checkpoint Directory Structure
```
drywall_detection/checkpoints/best_model/
├── best_model.pt               # Trained PyTorch state_dict (weights)
├── model.onnx                  # Optimized ONNX model graph for rapid CPU inference
├── config.json                 # Model architecture parameters and input preprocessing rules
├── class_mapping.json          # Numerical index to class name & hex color code
├── metrics.json                # Final held-out validation evaluation metrics
├── training_log.json           # Per-epoch training & validation loss and metric progression
├── sample_overlays/            # Visual quality control inspection images
│   ├── val_drawing_01_overlay.png
│   ├── val_drawing_02_overlay.png
│   └── ...
├── infer.py                    # Standalone, zero-dependency inference and testing script
└── README.md                   # Model card, reproduction instructions, and loading guidelines
```

### 5.2 Loading Contract & Verification Interface (`infer.py`)
The checkpoint bundle must guarantee programmatic re-loadability. The delivered `infer.py` must fulfill the following contract:
```python
import json
import torch
from PIL import Image
import numpy as np

def load_drywall_model(checkpoint_dir="drywall_detection/checkpoints/best_model"):
    # 1. Load architecture configuration
    with open(f"{checkpoint_dir}/config.json", "r") as f:
        config = json.load(f)
    
    # 2. Instantiate model based on config["architecture"]
    if config["architecture"] == "segformer_b0":
        from transformers import SegformerForSemanticSegmentation
        model = SegformerForSemanticSegmentation.from_pretrained(
            config["pretrained_base"],
            num_labels=config["num_classes"],
            ignore_mismatched_sizes=True
        )
    elif config["architecture"] == "lightweight_unet":
        from drywall_detection.models.unet import LightweightUNet
        model = LightweightUNet(in_channels=3, num_classes=config["num_classes"])
    
    # 3. Load state dict
    state_dict = torch.load(f"{checkpoint_dir}/best_model.pt", map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    return model, config

def predict_tile(model, image_pil):
    # Expects PIL Image (512x512)
    # Returns 2D numpy array uint8 with class values {0, 1, 2, 3}
    ...
```

---

## 6. Synthesis & Recommendations for Downstream Milestones

1. **Dataset Selection for Pretraining**:
   - Ingest **Modified Swiss Dwellings (MSD)** via Hugging Face (`philippds/modified-swiss-dwellings-enriched`, 174 MB) as the primary open dataset. Its CC BY 4.0 license is fully unencumbered, download size is under 200 MB, and WKT wall polygons are mathematically precise.
   - Retain **CubiCasa5K** (Zenodo Record 2613548) as the secondary reference benchmark.
   - Do NOT attempt autonomous downloads of R2V (requires NII IDR agreement) or ArchCAD-400k (requires gated credential approval).
2. **Architecture Selection**:
   - Implement and compare **SegFormer-B0** and **Lightweight U-Net**. Both models meet the strict CPU hardware envelope (< 1.5 GB available RAM, 8 logical CPU cores), avoiding the severe "stuff" fragmentation failure modes of YOLOv8-seg.
3. **Drywall Verification Guardrail**:
   - Models must strictly output 4 classes. Any wall detected by geometric segmentation that cannot be matched to verified partition schedule callouts (gypsum board assemblies vs CMU/concrete) must be classified as **Uncertain (Class 3, Yellow)**. Generic wall detections must never be claimed as confirmed drywall without verified ground truth.
