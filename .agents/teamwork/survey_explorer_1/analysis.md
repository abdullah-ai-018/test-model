# Technical Analysis: Workspace Inventory & Environment Audit

- **Agent**: `survey_explorer_1`
- **Role**: Workspace & Environment Surveyor
- **Timestamp**: 2026-11-07T20:37:00Z
- **Workspace Path**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Integrity Level**: Complete forensic audit & verification

---

## 1. Executive Summary

This report delivers the foundational technical findings regarding the local compute environment and the inventory of architectural PDF drawings available for the drywall detection project. 

Key discoveries:
1. **Local Compute Profile**: Windows 10 (AMD64), Intel Core 4-core/8-thread CPU, **strictly CPU-bound** (`torch 2.1.0+cpu`, no NVIDIA GPU / 0 CUDA VRAM), and **critical RAM scarcity** (7.88 GB total, only ~1.0 GB available; ~87% utilized). Local model training must use lightweight architectures (SegFormer-B0, compact U-Net, YOLOv8n-seg), tile/patch-based sampling (512x512), low batch sizes ($B=2$), or GPU workflows.
2. **Software Stack**: Python 3.10.0 with core vision/ML packages pre-installed: `torch` (2.1.0+cpu), `torchvision` (0.16.0+cpu), `ultralytics` (8.3.167), `transformers` (4.41.2), `timm` (1.0.22), `opencv-python` (4.11.0), `PyMuPDF/fitz` (installed), `pdfplumber` (0.11.7), `shapely` (2.1.1), `streamlit` (1.48.1), and `fastapi` (0.116.0).
3. **Primary Reference Drawing Set**: Located at `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf` (71 pages, 75.8 MB, 2592 x 1728 pt / ANSI D 36" x 24"). Contains MTA Contract C-48526 (99th Street Phase 2 Interior). It is a pure digital vector PDF with searchable text and 10,000 to 135,000 vector primitives per sheet.
4. **Target Sheets Located**:
   - Sheet **A-101** (Page 15): First Floor Construction Plan
   - Sheet **A-102** (Page 16): Second Floor Construction Plan
   - Sheet **A-103** (Page 17): Third Floor Construction Plan
   - Sheet **A-104** (Page 18): Fourth Floor Construction Plan
   - Sheet **A-900** (Page 63): Partition Types Sheet I (Details 1A, 1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E)
   - Sheet **A-901** (Page 64): Partition Types Sheet II (Details 7A, 7B, 7C, 7E, 7F, 7G, 8A, GL1/GL2, Column Enclosures)
   - Sheet **A-902** (Page 65): Wall Details I
   - Sheet **A-910** (Page 71): Firestopping Details
5. **Human Ground-Truth & Annotated Drawings Discovered**:
   - `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (27 pages): Contains human estimator red vector line and polygon markups identifying verified drywall partitions.
   - `C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf` (27 pages): Contains green square and text annotations identifying drywall partitions.
   - `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf` (54 pages): Fully independent commercial permit drawing set suitable for held-out cross-domain validation.

---

## 2. Local Compute Environment Audit

### 2.1 Hardware Metrics

| Subsystem | Metric | Verified Value | Impact / Constraint |
|---|---|---|---|
| **Operating System** | Platform | Windows 10 (10.0.26100-SP0) | Shell is PowerShell; Windows path separators |
| **Architecture** | Machine Type | AMD64 (x86_64) | 64-bit binaries supported |
| **Processor** | Model / Stepping | Intel64 Family 6 Model 142 Stepping 10 | 4 physical cores, 8 logical threads (~1.7 GHz) |
| **System RAM** | Total Memory | 7.88 GB (8,069 MB) | Constrained |
| **System RAM** | Currently Used | 6.88 GB (~87.3%) | Background processes consume most RAM |
| **System RAM** | Available Memory | **~1.00 GB (1,024 MB)** | **CRITICAL**: High risk of OOM on large tensors |
| **GPU / Acceleration** | Discrete GPU | None (`nvidia-smi` failed / not installed) | No CUDA hardware present |
| **VRAM** | Dedicated Video RAM | 0 GB | Pure CPU processing |
| **Storage (C:)** | Capacity / Free | 149.64 GB total / 16.35 GB free (89.1% full) | Disk headroom is limited (<17 GB free) |
| **Storage (E:)** | Capacity / Free | 88.12 GB total / 30.45 GB free (65.4% full) | Usable secondary volume |

### 2.2 Deep Learning & Vision Package Manifest

The Python interpreter is located at `C:\Users\TEC ZONE\AppData\Local\Programs\Python\Python310\python.exe` (Version 3.10.0).

| Package | Status | Version | Capability Supported |
|---|---|---|---|
| `torch` | Installed | `2.1.0+cpu` | Neural network forward/backward pass (CPU only) |
| `torchvision` | Installed | `0.16.0+cpu` | Image transforms, vision backbones |
| `ultralytics` | Installed | `8.3.167` | YOLOv8 instance segmentation & object detection |
| `transformers` | Installed | `4.41.2` | Hugging Face SegFormer (`nvidia/mit-b0`, `mit-b1`) |
| `timm` | Installed | `1.0.22` | Pretrained vision encoders (ResNet, EfficientNet) |
| `huggingface_hub` | Installed | `0.36.0` | Model and dataset downloading |
| `opencv-python` (`cv2`) | Installed | `4.11.0` | Image processing, morphological filtering, contours |
| `PyMuPDF` (`fitz`) | Installed | Present | High-speed PDF rendering, vector path extraction |
| `pdfplumber` | Installed | `0.11.7` | Text and table extraction from PDFs |
| `pypdf` | Installed | `6.1.0` | PDF page manipulation, merging, splitting |
| `pypdfium2` | Installed | Present | PDFium rendering backend |
| `shapely` | Installed | `2.1.1` | Planar geometric operations, polygon IoU, intersection |
| `pyclipper` | Installed | `1.3.0.post6` | Polygon clipping and offsetting |
| `scipy` | Installed | `1.15.3` | Spatial algorithms, distance transforms, optimization |
| `scikit-learn` (`sklearn`) | Installed | `1.7.2` | Confusion matrices, metrics (precision, recall, F1) |
| `scikit-image` (`skimage`) | Installed | `0.25.2` | Skeletonization, boundary analysis, thin line extraction |
| `numpy` | Installed | `1.26.4` | Numerical array computing |
| `pandas` | Installed | `2.2.2` | Tabular data analysis, schedule parsing |
| `pillow` (`PIL`) | Installed | `10.2.0` | Image loading, rendering, and palette conversions |
| `matplotlib` | Installed | `3.10.3` | Visual plotting and QC figure rendering |
| `seaborn` | Installed | `0.13.2` | Statistical heatmaps, confusion matrix plots |
| `onnxruntime` | Installed | `1.23.0` | Optimized ONNX inference |
| `streamlit` | Installed | `1.48.1` | Interactive local web interface for testing & preview |
| `fastapi` & `uvicorn` | Installed | `0.116.0` / `0.35.0` | REST API for inference pipelines |
| `flask` | Installed | `2.3.3` | Lightweight web backend |
| `albumentations` | Missing | Not installed | Augmentation can be done via `torchvision` or `cv2` |
| `segmentation_models_pytorch` | Missing | Not installed | U-Net can be loaded via custom PyTorch or `timm` |
| `gradio` | Missing | Not installed | Not needed: `streamlit` is available and superior for PDFs |

---

## 3. Comprehensive Inventory of Architectural Drawings

### 3.1 Primary Drawing Sets & Derivatives

| File Name | File Path | Pages | Size (MB) | Vector / Scanned | Key Content & Sheet Coverage |
|---|---|---|---|---|---|
| **file-1793194362940-560626729.pdf** | `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf` | **71** | **75.77 MB** | Pure Vector (10k-135k paths/page) | **Master Set: MTA Contract C-48526 (99th St Phase 2 Interior)**. Contains Cover, Legends (G-001), Life Safety (LS-100 to LS-105), Construction Plans (**A-101 to A-104**), Reflected Ceiling Plans (A-200 to A-204), Partition Types (**A-900, A-901**), Wall Details (**A-902**), Firestopping (**A-910**). Dimensions: 2592 x 1728 pt. |
| **Bid Set.pdf** | `C:\Users\TEC ZONE\Downloads\Bid Set.pdf` | 71 | 75.77 MB | Vector | Full set, 3024 x 2160 pt. Pages 3-4 feature Wall Types Legend; Page 5 features Finish Floor Plan. |
| **drywall_walls_marked_red_by_Usman.pdf** | `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (and copy in `Documents`) | 27 | 62.48 MB | Vector + PDF Markup | **Human-marked ground truth**: 27 selected floor plan and detail pages. Human estimator marked verified drywall walls with explicit red vector strokes (`stroke=(1.0, 0.0, 0.0)`) and bounding squares. |
| **drywall_annotated_floor_plans.pdf** | `C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf` | 27 | 62.46 MB | Vector + Green Annotations | 27 floor plan pages with Green square and text annotations (`stroke=(0.0, 0.7, 0.2), fill=(0.85, 1.0, 0.85)`). Corresponds to user prompt convention: Drywall in Green. |
| **3.1-all-architectural-darwings.pdf** | `C:\Users\TEC ZONE\Downloads\3.1-all-architectural-darwings.pdf` | 107 | 8.44 MB | Vector | Comprehensive 107-page architectural drawings binder. |
| **all_wall_partition_types.pdf** | `C:\Users\TEC ZONE\Downloads\all_wall_partition_types.pdf` | 2 | 4.88 MB | Vector | Standalone 2-page extraction containing exactly Sheet A-900 (Partition Types Sheet I) and Sheet A-901 (Partition Types Sheet II). |
| **floor_wise_new_wall_partition_tags.pdf** | `C:\Users\TEC ZONE\Downloads\floor_wise_new_wall_partition_tags.pdf` | 2 | 2.15 MB | Vector | Floor-wise breakdown linking partition tags to floors 1–4. |
| **protake_ai_wall_partition_data.pdf** | `C:\Users\TEC ZONE\Downloads\protake_ai_wall_partition_data.pdf` | 2 | 1.80 MB | Vector / Text | Structured table mapping partition tags to material schedules. |
| **wall_partition_data_json.pdf** | `C:\Users\TEC ZONE\Downloads\wall_partition_data_json.pdf` | 7 | 0.85 MB | Text / Code | JSON transcriptions of partition assemblies. |
| **Drywall_QTO_SOP.pdf** | `C:\Users\TEC ZONE\Downloads\Drywall_QTO_SOP.pdf` | 35 | 1.48 MB | Text & Diagrams | Standard Operating Procedure manual for Drywall QTO. |
| **test Spark Lake Grove - Permit Set.pdf** | `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf` | 54 | 10.35 MB | Vector | **Held-Out External Test Set**: 54 pages of commercial permit drawings with Partition Key, Partition Types, and Floor Plans. |

---

## 4. In-Depth Mapping of Target Sheets (99th Street MTA Set)

In `file-1793194362940-560626729.pdf`, the exact page indices and characteristics of target sheets are:

| Sheet Number | PDF Page | Sheet Title | Dimensions (pt) | Drawing Primitives | Text Chars | Architectural Function |
|---|---|---|---|---|---|---|
| **A-101** | **Page 15** | First Floor Construction Plan | 2592 x 1728 (ANSI D) | 21,458 | 12,523 | Primary floor plan: shows interior rooms, partition tags (1B, 1C, 2B, 3A, etc.), column grids, door openings, corridor walls. |
| **A-102** | **Page 16** | Second Floor Construction Plan | 2592 x 1728 (ANSI D) | 89,450 | 13,006 | Dense floor plan with high-volume interior partitions, office layouts, mechanical shafts. |
| **A-103** | **Page 17** | Third Floor Construction Plan | 2592 x 1728 (ANSI D) | 47,167 | 12,672 | Floor plan detailing office partitions, restroom cores, acoustic walls. |
| **A-104** | **Page 18** | Fourth Floor Construction Plan | 2592 x 1728 (ANSI D) | 50,419 | 12,903 | Top floor plan with perimeter furring, executive suites, conference partitions. |
| **A-900** | **Page 63** | Partition Types Sheet I | 2592 x 1728 (ANSI D) | 14,734 | 8,540 | **Ground Truth Authority I**: 12 partition assembly details (1A, 1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E). |
| **A-901** | **Page 64** | Partition Types Sheet II | 2592 x 1728 (ANSI D) | 25,778 | 7,508 | **Ground Truth Authority II**: 11 assembly details (7A, 7B, 7C, 7E, 7F shaft wall, 7G, 8A, GL1/GL2 glass, Col 10/11). |
| **A-902** | **Page 65** | Wall Details I | 2592 x 1728 (ANSI D) | 12,421 | 2,054 | Wall head, base, deflection track, and junction details. |
| **A-910** | **Page 71** | Firestopping Details | 2592 x 1728 (ANSI D) | 18,040 | 6,174 | Fire-rated penetrations, acoustic sealant callouts, joint seals. |

---

## 5. Drywall vs. Non-Drywall Classification Evidence Matrix

In strict compliance with Requirement **R2** (Classification Guardrails), generic wall detections must never be assumed to be drywall. Every wall category must be validated by construction specifications:

| Partition Tag | Drawing Sheet | Assembly Description | Structural Core | Facing Material | Fire Rating | Classification Verdict | Color Code |
|---|---|---|---|---|---|---|---|
| **1A** | A-900 | 6" Fire-rated CMU masonry block | 6" CMU Block | Masonry / None | 1-Hour | **Non-Drywall** | **Red (2)** |
| **1B** | A-900 | Metal stud partition (2-1/2" 25 GA @ 16" OC) | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **1C** | A-900 | Metal stud partition (3-5/8" 25 GA @ 16" OC) | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **1D** | A-900 | Metal stud partition (6" 16 GA @ 16" OC, max 8' ht) | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **1E** | A-900 | Metal stud with moisture barrier at wet areas | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **2B** | A-900 | Sound partition with acoustic blanket & sealant | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **2C** | A-900 | Sound partition, staggered joints | Metal Stud | 2 layers 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **3A** | A-900 | Metal stud partition (3-5/8" 25 GA) | Metal Stud | 1 layer 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **3D** | A-900 | Sound partition, 2 layers gyp bd each side | Metal Stud | 2 layers 5/8" Gypsum Wallboard each side | None | **Drywall** | **Green (1)** |
| **5B** | A-900 | 1-HR Fire-rated metal stud partition | Metal Stud | Gypsum Wallboard assembly | 1-Hour | **Drywall** | **Green (1)** |
| **5D** | A-900 | Metal stud partition + sound blanket | Metal Stud | Gypsum Wallboard assembly | None | **Drywall** | **Green (1)** |
| **5E** | A-900 | 2-HR Fire-rated metal stud partition | Metal Stud | 2 layers 5/8" Gypsum Wallboard each side | 2-Hour | **Drywall** | **Green (1)** |
| **7A** | A-901 | Perimeter furring with 1-1/2" rigid insulation | Existing Wall | 1 layer 5/8" Gypsum Board laminated | None | **Drywall** | **Green (1)** |
| **7B** | A-901 | Furring partition on room side | Metal Stud | 1 layer 5/8" Gypsum Board room side | None | **Drywall** | **Green (1)** |
| **7C** | A-901 | Metal stud 3-5/8" 20 GA with acoustic blanket | Metal Stud | 1 layer 5/8" Gypsum Board each side | None | **Drywall** | **Green (1)** |
| **7E** | A-901 | Metal stud 2-1/2" C-H stud (24" OC) | C-H Stud | 2 layers 1/2" Type-C Gypsum Board | None | **Drywall** | **Green (1)** |
| **7F** | A-901 | 2-HR Fire-rated Shaft Wall | C-H Stud | 1 layer 1" Type-SCX + 2 layers 1/2" Type-C | 2-Hour | **Drywall** | **Green (1)** |
| **7G** | A-901 | Metal stud 2-1/2" 20 GA with R-19 insulation | Metal Stud | 1 layer Gypsum Board each side | None | **Drywall** | **Green (1)** |
| **8A** | A-901 | Furring partition laminated to wall | Existing Wall | 1 layer 5/8" Gypsum Board | None | **Drywall** | **Green (1)** |
| **GL1 / GL2** | A-901 | Glass officefront system / entrance glass | Aluminum Frame | Glass Panes | None | **Non-Drywall** | **Red (2)** |
| **10** | A-901 | Steel column enclosure | Steel Column | 2 layers Type X Gypsum Board | 2-Hour | **Drywall** | **Green (1)** |
| **11** | A-901 | Concrete-encased steel column | Concrete / Steel | Poured Concrete | None | **Non-Drywall** | **Red (2)** |
| **09** | A-901 | Section @ TV Screen | Wood/Metal | Electrical Backboard / AV Panel | None | **Uncertain** | **Yellow (3)** |
| **Structural / Perimeter** | Floor Plans | Concrete elevator cores, exterior masonry | Concrete / CMU | Masonry / Concrete | Multi-Hour | **Non-Drywall** | **Red (2)** |
| **Untagged / Ambiguous** | Floor Plans | Partitions lacking legible tag or schedule match | Unverified | Unverified | Unknown | **Uncertain** | **Yellow (3)** |

---

## 6. Architectural Constraints & Strategic Recommendations for Downstream Milestones

### 6.1 Hardware Adaptation (Milestone M3)
- **Local CPU Mode**: With only ~1.0 GB available RAM and no CUDA GPU, local training must:
  1. Patch drawings into $512 \times 512$ tiles with stride 256.
  2. Use batch size $B=2$ and accumulate gradients over 4 steps.
  3. Limit epochs to $E=5\text{--}10$ for baseline convergence demonstration.
  4. Train a compact model: **SegFormer-B0** (`nvidia/mit-b0`, 3.7M parameters) or **Lightweight U-Net** with MobileNetV3/ResNet18 backbone.
- **GPU Scaling Pathway**: Provide an automated, reproducible Google Colab script (`train_colab.ipynb` or standalone python script) capable of detecting T4/A100 GPUs, increasing batch size to 16, and accelerating full-dataset fine-tuning.

### 6.2 Ground-Truth Integration (Milestone M2)
- Exploit `drywall_walls_marked_red_by_Usman.pdf` and `drywall_annotated_floor_plans.pdf` as human-verified ground truth for the 99th Street floor plans.
- Pair these with partition tag spatial parsing from sheets A-900 and A-901 to establish high-confidence Drywall (Green) vs. Non-Drywall (Red) masks.
- Classify any ambiguous, untagged, or conflicting partition lines strictly as **Uncertain (Yellow)**.

### 6.3 Local PDF Testing Interface (Milestone M4)
- **Framework Choice**: `streamlit` (Version 1.48.1 is already installed and verified!). It provides native support for PDF rendering via PyMuPDF, file uploader widgets, interactive side-by-side mask inspection, and download buttons for annotated PDFs.
- **Rendering Pipeline**: Accept vector or scanned PDFs, render at 150 DPI with PyMuPDF, pass image tiles through the segmentation model, map predictions to RGB masks (Green=Drywall, Red=Non-Drywall, Yellow=Uncertain), and composite the colored masks onto the original PDF geometry using PyMuPDF overlay streams preserving exact scale and vector quality.

### 6.4 Independent Validation (Milestone M5)
- Use `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf` (54 pages) as a completely held-out cross-domain commercial evaluation set to validate that the pipeline generalizes to unseen architectural conventions.
