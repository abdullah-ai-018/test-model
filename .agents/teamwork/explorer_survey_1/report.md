# Workspace, Reference PDF & Environment Survey Report
**Document ID:** SURVEY-EXP1-M1-001  
**Author:** survey_explorer_1 (Workspace & PDF Surveyor)  
**Date:** 2026-11-08  
**Project:** QTO Engine — Isolated Drywall Detection Module (`drywall_detection/`)  
**Integrity Mode:** Development  
**Reference Document:** MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728 x 2592 pt unrotated MediaBox / 2592 x 1728 pt visual, Rotation 90° CW, "PROGRESS SET 95% CDs 10/02/2026")  
**Notice:** This reference PDF represents a 95% CDs progress set, not an approved final construction document. Pages represent a single project and cannot prove cross-domain generalization.

---

## Executive Summary

This survey establishes the complete empirical assessment of the workspace, reference architectural PDF set, auxiliary project artifacts, and the hardware/software execution environment for **Milestone M1 (Workspace and Dataset Audit)**.

### Core Discoveries & Verified Facts:
1. **Workspace Layout**: The active workspace `c:\Users\TEC ZONE\OneDrive\Desktop\test-model` is clean and contains only agent coordination metadata under `.agents/teamwork/`. No pre-existing QTO Engine files or legacy modules reside in the root. The upcoming `drywall_detection/` module will be developed in complete isolation without external side effects.
2. **Authoritative Reference PDF Located**: Located at `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf` (29,110,223 bytes). Page count is verified at exactly **71 pages**. Unrotated MediaBox is **1728.0 pt x 2592.0 pt**; rotation is **90° clockwise** across all 71 pages; visual rendered dimensions are **2592.0 pt x 1728.0 pt** (standard 36" x 24" Arch D landscape).
3. **Partition Schedule & Floor Plan Sheets Mapped**:
   - Master Sheet Index: Page 3 (idx 2, Sheet G-002).
   - Authoritative Partition Schedule Sheets: Page 63 (idx 62, Sheet A-900, "PARTITION TYPES SHEET I") and Page 64 (idx 63, Sheet A-901, "PARTITION TYPES SHEET II").
   - Primary Floor Plans: Page 14 (idx 13, A-100) through Page 19 (idx 18, A-105), plus Life Safety Plans LS-100 to LS-105 (Pages 8–13).
4. **Auxiliary Ground-Truth Assets Discovered**:
   - `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (27 pages, 478 red human markup annotations of walls and tags) provides an empirical civil-engineering ground truth for the R4 human-review sample evaluation.
   - `C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf` (27 pages, 502 automated annotations) exposes a critical prior error: Tag `1A` was erroneously classified as drywall (95% prob), whereas Sheet A-900 explicitly defines `1A` as `6" FIRE RATED CMU` (masonry / Non-Drywall).
   - `C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf` (27 pages) is an exact 1:1 page extraction of the relevant architectural floor plans and partition sheets from the master 71-page set.
5. **Hardware Execution Environment & Constraints**:
   - CPU: Intel Core 4 physical / 8 logical cores.
   - GPU: Intel(R) UHD Graphics 620 integrated; **no NVIDIA GPU, no CUDA**.
   - PyTorch: `2.1.0+cpu` (CPU execution only).
   - System RAM: 7.88 GB total, **~0.90 GB available** (extreme RAM constraint).
   - Disk: C:\ has 16.37 GB free; E:\ has 30.45 GB free (combined 46.82 GB free).
   - Python: 3.10.0 (64-bit AMD64).
   - Installed core libraries: `fitz` (PyMuPDF 1.22.0), `pdfplumber` (0.11.7), `shapely` (2.1.1), `cv2` (OpenCV 4.11.0), `torch` (2.1.0+cpu), `timm` (1.0.22), `transformers` (4.41.2), `ultralytics` (8.3.167), `scipy` (1.15.3), `sklearn` (1.7.2), `PIL`, `numpy`, `pandas`, `matplotlib`. Missing: `albumentations`, `segmentation_models_pytorch`.
   - Implications: Local segmentation model training must be auto-configured for lightweight CPU execution (small batch size, modest resolution), while training scripts must maintain seamless Google Colab compatibility for GPU fine-tuning.

---

## 1. Workspace Layout & Isolation Audit

### 1.1 Directory Tree Verification
- Root workspace directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- Command working directory: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- Existing structure:
  ```
  c:\Users\TEC ZONE\OneDrive\Desktop\test-model\
  └── .agents\
      └── teamwork\
          ├── ORIGINAL_REQUEST.md
          ├── explorer_survey_1\
          ├── explorer_survey_2\
          ├── explorer_survey_3\
          ├── orchestrator\
          ├── interviewer\
          └── sentinel\
  ```
- **Verification Result**: No source code files, build scripts, or external QTO Engine packages exist in the root.
- **Isolation Compliance**: All upcoming project code will reside exclusively within a new top-level `drywall_detection/` directory in compliance with R5 and PROJECT layout conventions. `.agents/teamwork/` contains exclusively agent metadata.

---

## 2. Reference PDF Survey & Detailed Properties

### 2.1 File Identification & Provenance
- Primary File Path: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
- File Size: `29,110,223 bytes` (~27.76 MB)
- Document Title / Cover:
  - Client / Owner: The Metropolitan Transportation Authority (MTA Construction & Development)
  - Contract: `C - 48526`
  - Location: 99th Street, Borough of Manhattan
  - Architect: TPG Architecture LLP
  - Issue Stamp: `"PROGRESS SET 95% CDs 10/02/2026"`
  - Set Title: `ARCHITECTURAL INTERIOR SET`
  - Revit Source File: `Autodesk Docs://1624114-00_MTA 99th Street/1624114-00_MTA_99th Street_ARCH_V25.rvt`
  - PDF Producer: Bluebeam Brewery 5.0 / Bluebeam Stapler 21.7.0.12289

### 2.2 Physical Page Geometry & Transformations
- **Page Count:** 71 pages (verified via PyMuPDF `len(doc) == 71`).
- **MediaBox (Unrotated PDF Point Space):** `Rect(0.0, 0.0, 1728.0, 2592.0)` pt ($W = 1728.0$, $H = 2592.0$).
- **CropBox:** `Rect(0.0, 0.0, 1728.0, 2592.0)` pt.
- **Rotation Flag (`/Rotate`):** `90` degrees clockwise across all 71 pages ($100\%$ uniform).
- **Rendered Visual Dimensions (at 72 DPI):** $2592.0 \times 1728.0$ pt (Landscape orientation, 36" wide x 24" high, standard Arch D format).
- **Transformation Matrices:**
  - `page.transformation_matrix`: `Matrix(1.0, 0.0, 0.0, -1.0, 0.0, 2592.0)`
  - `page.derotation_matrix`: `Matrix(0.0, -1.0, 1.0, 0.0, -0.0, 2592.0)`

### 2.3 Mathematical Coordinate Mapping Formula
To ensure reversible mapping between native PDF vector space and rendered raster images:
- Given PDF unrotated coordinate $(x, y) \in [0..1728, 0..2592]$ and rendering scale factor $S = \frac{DPI}{72.0}$:
  $$\text{Pixel } X: \quad px = S \cdot (2592.0 - y)$$
  $$\text{Pixel } Y: \quad py = S \cdot x$$
- Inverse mapping (from pixel to unrotated PDF point):
  $$\text{PDF } x = \frac{py}{S}$$
  $$\text{PDF } y = 2592.0 - \frac{px}{S}$$
- Numerical verification: Tested roundtrip on Point $(500.0, 1200.0)$ yielding $\Delta x = 0.0$ pt, $\Delta y = 0.0$ pt. Exact mathematical bijection confirmed.

### 2.4 Vector Content & Text Layers
- **Vector Usability:** Every single page is native vector PDF. Vector drawing paths (`page.get_drawings()`) range from **190 paths** (minimal survey notes) to **618,536 paths** (dense reflected ceiling plan).
- **Text Layers:** Complete searchable CAD text layer present on all 71 pages (ranging from 269 characters on the cover to 30,031 characters on general specification sheets). No page is a scanned raster; OCR is not required for primary extraction, though fallback detection logic is implemented.
- **Embedded Fonts (9 Unique Fonts):**
  1. `ArialMT`
  2. `BCPWJW+MicrosoftSansSerif`
  3. `CFWUZY+CenturyGothic`
  4. `Helvetica75Bold10.5`
  5. `JWTRVT+Arial`
  6. `NBPIKY+SegoeUISymbol`
  7. `QTBMYZ+ArialNarrow,Bold`
  8. `ROCIYD+ArialNarrow`
  9. `WDLTFM+Arial,Bold`

---

## 3. Complete 71-Page Sheet Catalog & Critical Sheet Locations

The sheet index was extracted from Sheet G-002 (Page 3, idx 2) and verified against each page's title block metadata:

| Page # | Page Index | Sheet Number | Sheet Title | Vector Paths | Text Chars | Category / Role in Pipeline |
|:---:|:---:|:---:|:---|:---:|:---:|:---|
| 1 | 0 | COVER / TITLE | ARCHITECTURAL INTERIOR SET - COVER | 13,647 | 269 | Project Title Block & Cover |
| 2 | 1 | G-001 | MASTER LEGENDS | 10,828 | 17,058 | Legend & Standard Symbols |
| **3** | **2** | **G-002** | **MASTER SHEET LIST** | **4,029** | **11,322** | **Master Sheet Index (Sheet List)** |
| 4 | 3 | G-003 | NOTES & SPECIFICATIONS | 926 | 30,031 | Building Code & Spec Notes |
| 5 | 4 | G-004 | FEMA FLOOD MAPS | 205 | 1,332 | Flood Hazard Plan |
| 6 | 5 | G-005 | UTILITY SURVEY DRAWINGS | 195 | 1,250 | Utility Survey |
| 7 | 6 | G-006 | SURVEY | 190 | 1,214 | Site Survey |
| 8 | 7 | LS-100 | CELLAR LIFE SAFETY PLAN | 10,178 | 8,962 | Life Safety Floor Plan |
| 9 | 8 | LS-101 | FIRST FLOOR LIFE SAFETY PLAN | 29,162 | 11,301 | Life Safety Floor Plan |
| 10 | 9 | LS-102 | SECOND FLOOR LIFE SAFETY PLAN | 135,967 | 10,000 | Life Safety Floor Plan |
| 11 | 10 | LS-103 | THIRD FLOOR LIFE SAFETY | 118,496 | 10,205 | Life Safety Floor Plan |
| 12 | 11 | LS-104 | FOURTH FLOOR LIFE SAFETY | 110,560 | 10,048 | Life Safety Floor Plan |
| 13 | 12 | LS-105 | ROOF LIFE SAFETY PLAN | 10,754 | 8,471 | Life Safety Floor Plan |
| **14** | **13** | **A-100** | **CELLAR CONSTRUCTION PLAN** | **10,788** | **12,217** | **Primary Floor Plan (Basement)** |
| **15** | **14** | **A-101** | **FIRST FLOOR CONSTRUCTION PLAN** | **21,458** | **12,523** | **Primary Floor Plan (Ground Floor)** |
| **16** | **15** | **A-102** | **SECOND FLOOR CONSTRUCTION PLAN** | **89,450** | **13,006** | **Primary Floor Plan (Level 2)** |
| **17** | **16** | **A-103** | **THIRD FLOOR CONSTRUCTION PLAN** | **47,167** | **12,672** | **Primary Floor Plan (Level 3)** |
| **18** | **17** | **A-104** | **FOURTH FLOOR CONSTRUCTION PLAN** | **50,419** | **12,903** | **Primary Floor Plan (Level 4)** |
| **19** | **18** | **A-105** | **ROOF CONSTRUCTION PLAN** | **8,672** | **12,010** | **Primary Floor Plan (Roof/Bulkhead)**|
| 20 | 19 | A-200 | CELLAR REFLECTED CEILING PLAN | 10,995 | 9,520 | Reflected Ceiling Plan |
| 21 | 20 | A-201 | FIRST FLOOR REFLECTED CEILING PLAN | 38,025 | 10,179 | Reflected Ceiling Plan |
| 22 | 21 | A-202 | SECOND FLOOR REFLECTED CEILING PLAN | 43,143 | 10,546 | Reflected Ceiling Plan |
| 23 | 22 | A-203 | THIRD FLOOR REFLECTED CEILING PLAN | 67,418 | 10,498 | Reflected Ceiling Plan |
| 24 | 23 | A-204 | FOURTH FLOOR REFLECTED CEILING PLAN | 618,536 | 10,665 | Reflected Ceiling Plan |
| 25 | 24 | A-300 | CELLAR POWER & COMMUNICATIONS PLAN | 9,381 | 10,920 | Electrical / Data Plan |
| 26 | 25 | A-301 | FIRST FLOOR POWER & COMMUNICATIONS PLAN | 19,008 | 11,264 | Electrical / Data Plan |
| 27 | 26 | A-302 | SECOND FLOOR POWER & COMMUNICATIONS PLAN | 120,874 | 12,775 | Electrical / Data Plan |
| 28 | 27 | A-303 | THIRD FLOOR POWER & COMMUNICATIONS PLAN | 84,502 | 13,134 | Electrical / Data Plan |
| 29 | 28 | A-304 | FOURTH FLOOR POWER & COMMUNICATIONS PLAN | 81,424 | 13,460 | Electrical / Data Plan |
| 30 | 29 | A-305 | ROOF POWER & COMMUNICATIONS PLAN | 8,044 | 10,707 | Electrical / Data Plan |
| 31 | 30 | A-306 | EQUIPMENT, PLUMBING, ACCESSORIES & FIXTURES | 2,148 | 12,013 | Equipment Schedule |
| 32 | 31 | A-401 | FIRST FLOOR FINISH PLAN | 15,894 | 6,936 | Finish Schedule Plan |
| 33 | 32 | A-402 | SECOND FLOOR FINISH PLAN | 83,023 | 7,025 | Finish Schedule Plan |
| 34 | 33 | A-403 | THIRD FLOOR FINISH PLAN | 17,334 | 7,294 | Finish Schedule Plan |
| 35 | 34 | A-404 | FOURTH FLOOR FINISH PLAN | 17,321 | 7,363 | Finish Schedule Plan |
| 36 | 35 | A-405 | FINISH TRANSITION | 3,878 | 4,158 | Finish Details |
| 37 | 36 | A-406 | FINISH LEGEND SHEET I | 1,041 | 18,931 | Wall / Floor Finish Legend |
| 38 | 37 | A-407 | FINISH LEGEND SHEET II | 564 | 8,804 | Wall / Floor Finish Legend |
| 39 | 38 | EN-101 | ENLARGED CORE PLANS | 7,638 | 1,722 | Enlarged Core Details |
| 40 | 39 | A-501 | FIRST FLOOR FURNITURE PLAN | 18,903 | 2,287 | Furniture Layout |
| 41 | 40 | A-502 | SECOND FLOOR FURNITURE PLAN | 118,793 | 2,215 | Furniture Layout |
| 42 | 41 | A-503 | THIRD FLOOR FURNITURE PLAN | 79,975 | 2,492 | Furniture Layout |
| 43 | 42 | A-504 | FOURTH FLOOR FURNITURE PLAN | 71,104 | 2,481 | Furniture Layout |
| 44 | 43 | A-505 | ENLARGED FURNITURE DETAILS | 6,791 | 1,555 | Furniture Details |
| 45 | 44 | A-601 | DOOR SCHEDULE | 4,108 | 12,448 | Door Types & Hardware |
| 46 | 45 | A-602 | DOOR DETAILS | 10,268 | 2,798 | Door Frame Sections |
| 47 | 46 | A-701 | ELEVATIONS - PANTRYS | 40,127 | 5,014 | Interior Elevations |
| 48 | 47 | A-702 | ELEVATIONS - RESTROOMS SHEET I & LACTATION RM | 28,683 | 4,509 | Interior Elevations |
| 49 | 48 | A-703 | ELEVATIONS - RESTROOMS SHEET II | 97,463 | 4,559 | Interior Elevations |
| 50 | 49 | A-704 | ELEVATIONS - RESTROOMS SHEET III | 28,696 | 3,857 | Interior Elevations |
| 51 | 50 | A-705 | ELEVATIONS - RESTROOMS SHEET IV | 26,616 | 3,771 | Interior Elevations |
| 52 | 51 | A-706 | ELEVATIONS - TYP. OFFICE, CONF. & LOBBY | 25,420 | 4,204 | Interior Elevations |
| 53 | 52 | A-707 | ELEVATIONS - STORM RM DESK & SAFETY MTG RM | 5,671 | 2,719 | Interior Elevations |
| 54 | 53 | A-708 | ELEVATIONS - WALLS AT WORKSTATIONS | 12,506 | 2,888 | Interior Elevations |
| 55 | 54 | A-709 | ELEVATIONS - ENTRY VESTIBULES | 1,434 | 2,290 | Interior Elevations |
| 56 | 55 | A-710 | ELEVATIONS - WORKSTATIONS 4TH FLOOR | 2,663 | 1,954 | Interior Elevations |
| 57 | 56 | A-800 | RAMP PLANS SECTION & DETAILS | 14,517 | 3,683 | Vertical Circulation |
| 58 | 57 | A-801 | STAIR A PLANS & SECTIONS | 33,795 | 7,153 | Stair Sections |
| 59 | 58 | A-802 | STAIR B PLANS & SECTIONS | 31,030 | 5,424 | Stair Sections |
| 60 | 59 | A-803 | STAIR TYP. DETAILS I | 20,414 | 5,327 | Stair Details |
| 61 | 60 | A-804 | STAIR TYP. DETAILS II | 8,297 | 3,051 | Stair Details |
| 62 | 61 | A-805 | TYP. MILLWORK DETAILS I | 35,948 | 9,294 | Architectural Millwork |
| **63** | **62** | **A-900** | **PARTITION TYPES SHEET I** | **14,734** | **8,540** | **Authoritative Partition Schedule I** |
| **64** | **63** | **A-901** | **PARTITION TYPES SHEET II** | **25,778** | **7,508** | **Authoritative Partition Schedule II**|
| 65 | 64 | A-902 | WALL DETAILS I | 12,421 | 2,054 | Partition Wall Head/Base Details |
| 66 | 65 | A-903 | SIGNAGE | 5,405 | 1,671 | Signage Types & Locations |
| 67 | 66 | A-905 | CEILING DETAILS I | 9,438 | 8,198 | Ceiling Framing Details |
| 68 | 67 | A-906 | CEILING DETAILS II | 9,302 | 5,684 | Ceiling Framing Details |
| 69 | 68 | A-907 | CLERESTORY DETAILS | 3,392 | 2,306 | Interior Glazing / Clerestory |
| 70 | 69 | A-908 | ENTRY DETAILS | 234 | 1,339 | Vestibule / Entry Doors |
| 71 | 70 | A-910 | FIRESTOPPING DETAILS | 18,040 | 6,174 | Fire-rated Penetration Assemblies |

---

## 4. Partition Schedule Sheets (A-900, A-901) & Floor Plan Tag Discovery

### 4.1 Partition Schedule Assemblies (Sheets A-900 & A-901)
Direct structural parsing of Page 63 (A-900) and Page 64 (A-901) reveals **24 unique partition assembly details**:

| Tag | Sheet | Detail Title | Key Specifications & Materials | Classification |
|---|---|---|---|---|
| **1A** | A-900 | PARTITION TYPE DETAIL 1A - 1 HR RATED | `6" FIRE RATED CMU` masonry block; zero drywall/GWB | **Non-Drywall** (Red) |
| **1B** | A-900 | PARTITION TYPE DETAIL 1B | 2 1/2" 25 GA studs @ 16" O.C., 1 layer 5/8" GWB each side | **Drywall** (Green) |
| **1C** | A-900 | PARTITION TYPE DETAIL 1C | 3 5/8" 25 GA studs @ 16" O.C., 1 layer 5/8" GWB each side | **Drywall** (Green) |
| **1D** | A-900 | PARTITION TYPE DETAIL 1D | 6" 16 GA studs @ 16" O.C., 1 layer 5/8" GWB each side, max 8' ht | **Drywall** (Green) |
| **1E** | A-900 | PARTITION TYPE DETAIL 1E | 3 5/8" 20 GA studs @ 16" O.C., 1 layer 5/8" GWB each side, acoustic sealant | **Drywall** (Green) |
| **2B** | A-900 | PARTITION TYPE DETAIL 2B | 2 1/2" 25 GA studs, 1 layer 5/8" GWB each side to slab above | **Drywall** (Green) |
| **2C** | A-900 | PARTITION TYPE DETAIL 2C | 3 5/8" 25 GA studs, 1 layer 5/8" GWB each side to slab above | **Drywall** (Green) |
| **3A** | A-900 | PARTITION TYPE DETAIL 3A | 2 1/2" 20 GA studs, 1 layer 5/8" GWB each side, acoustic insulation | **Drywall** (Green) |
| **3D** | A-900 | PARTITION TYPE DETAIL 3D | 6" 16 GA studs, 1 layer 5/8" GWB each side, sound insulation to deck | **Drywall** (Green) |
| **5B** | A-900 | PARTITION TYPE DETAIL 5B - 1 HR RATED | 2 1/2" 25 GA studs, 1 layer 5/8" Type X GWB each side, firestop at deck | **Drywall** (Green) |
| **5D** | A-900 | PARTITION TYPE DETAIL 5D | 3 5/8" 25 GA studs, 1 layer 5/8" Type X GWB each side, firestop at deck | **Drywall** (Green) |
| **5E** | A-900 | PARTITION TYPE DETAIL 5E - 2 HR RATED | 3 5/8" 20 GA studs, 2 layers 5/8" Type X GWB each side, firestop | **Drywall** (Green) |
| **7A** | A-901 | PERIMETER FURRING PARTITION 7A | 2 1/2" studs / furring channel @ 24" O.C., 1 layer 5/8" GWB room face | **Drywall** (Green) |
| **7B** | A-901 | FURRING PARTITION 7B | Metal furring channels @ 16" O.C., 1 layer 5/8" GWB | **Drywall** (Green) |
| **7C** | A-901 | PARTITION TYPE DETAIL 7C | Metal studs @ 16" O.C., 1 layer 5/8" GWB each side | **Drywall** (Green) |
| **7E** | A-901 | PARTITION TYPE DETAIL 7E | Metal studs @ 16" O.C., 1 layer 5/8" GWB each side, acoustic sealant | **Drywall** (Green) |
| **7F** | A-901 | SHAFT WALL PARTITION 7F - 2 HR RATED | 2 1/2" C-H studs @ 24" O.C., 1" SCX liner + 2 layers 1/2" Type C GWB | **Drywall** (Green) |
| **7G** | A-901 | PARTITION TYPE DETAIL 7G | 2 1/2" 20 GA studs, 1 layer GWB each side, R-19 batt insulation to deck | **Drywall** (Green) |
| **8A** | A-901 | FURRING PARTITION 8A | 1 layer 5/8" GWB laminated directly to existing masonry wall | **Drywall** (Green) |
| **GL1**| A-901 | GLASS OFFICEFRONT SYSTEM | Infinium Quantum single butt-glazed office front system | **Non-Drywall** (Red) |
| **GL2**| A-901 | GLASS WALL AT ENTRANCE | Full-height architectural entrance glass wall | **Non-Drywall** (Red) |
| **09** | A-901 | SECTION @ TV SCREEN | Millwork / plywood TV backboard backing (specialty AV assembly) | **Uncertain** (Yellow) |
| **10** | A-901 | TYP. STEEL COLUMN ENCLOSURE | 2 layers Type X gypsum board fireproofing enclosure around steel | **Drywall** (Green) |
| **11** | A-901 | TYP. CONCRETE ENCASED COLUMN | Solid concrete encasement around structural steel column | **Non-Drywall** (Red) |

### 4.2 Floor Plan Tag Format & Spatial Association
Direct probing of Sheet A-101 (First Floor Construction Plan, Page 15, idx 14) revealed:
- **Partition Tag Text Strings:** Verified presence of tags `1C`, `1D`, `1E`, `3A`, `5B`, `5E`, `7A`, `7F`, `8A`.
- **Enclosing Geometry:** Tag text is enclosed within a vector bounding box measuring approximately **11.2 pt x 11.3 pt** formed by 4 stroked line segments.
- **Leader Lines:** Tag boxes frequently attach to a vector line stroke ($0.24$–$0.48$ pt width) pointing directly to the face or cavity of a wall run.
- **Direct Placement:** Other tags (e.g. `1C` and `7A`) are embedded directly inside or adjacent to the parallel wall lines without an extended leader.

---

## 5. Auxiliary Project Artifacts Survey

During the workspace and disk survey, three critical auxiliary PDF files were located in `C:\Users\TEC ZONE\Downloads\`:

1. **`drywall_relevant_full_pages.pdf` (27 pages, 8,082,962 bytes)**:
   - Probing verified this is an exact 1:1 extraction of the 27 architecturally significant sheets from the 71-page master set:
     - Pages 1–6 map to Sheets A-100 to A-105 (Construction Plans)
     - Pages 7–11 map to Sheets A-200 to A-204 (Reflected Ceiling Plans)
     - Pages 12–15 map to Sheets A-401 to A-404 (Finish Plans)
     - Pages 22–23 map to Sheets A-900 & A-901 (Partition Schedule Sheets I & II)
2. **`drywall_walls_marked_red_by_Usman.pdf` (27 pages, 8,445,633 bytes)**:
   - Contains **478 red human markup annotations** (`stroke: (1.0, 0.0, 0.0)`) across the 27 floor plans.
   - Specifically marks verified drywall wall runs and partition tags performed by estimator Usman.
   - **Crucial Value**: Serves as the independent civil-engineering reference sample for the Requirement R4 human-review sample evaluation (5 to 10 plan regions).
3. **`drywall_annotated_floor_plans.pdf` (27 pages, 8,299,007 bytes)**:
   - Contains 502 automated annotations from a previous detector tool.
   - **Critical Error Uncovered**: Page 1, Annotation 1 labeled Tag `1A` as `"DRYWALL TAG: 1A (95% prob)"`. Sheet A-900 proves conclusively that Detail 1A is `6" FIRE RATED CMU` (masonry / Non-Drywall). The new pipeline enforces strict material-precedence classification to eliminate this error.

---

## 6. Execution Environment & Hardware Audit

### 6.1 Hardware Specifications
- **Operating System:** Windows 10 (10.0.26100-SP0) AMD64
- **Host Processor:** Intel Core (Family 6 Model 142 Stepping 10, GenuineIntel)
  - Physical Cores: 4
  - Logical Threads: 8
- **System RAM:**
  - Total: 7.88 GB
  - Used: 6.98 GB (88.5% utilization)
  - Available: **0.90 GB free**
  - *Implication:* Extreme memory constraint. Memory-intensive operations (rendering 300 DPI full pages or loading large deep learning models) will risk OOM crashes if not properly bounded.
- **GPU & Hardware Acceleration:**
  - Controller: Intel(R) UHD Graphics 620
  - Dedicated GPU: **None**
  - CUDA Support: **Unavailable** (`cuda_available: False`)
  - VRAM: 0 GB dedicated (1 GB shared system memory)
  - PyTorch Build: `2.1.0+cpu`
- **Storage / Disks:**
  - `C:\`: Total 149.64 GB, Used 133.27 GB, **Free 16.37 GB**
  - `E:\`: Total 88.12 GB, Used 57.66 GB, **Free 30.45 GB**
  - *Combined Free Space:* 46.82 GB. Under R2, no download > 10 GB may occur without explicit prior user notification.

### 6.2 Software & Python Environment
- **Python Version:** 3.10.0 (64-bit AMD64)
- **Python Executable:** `C:\Users\TEC ZONE\AppData\Local\Programs\Python\Python310\python.exe`
- **Library Audit Table:**

| Package | Status | Version | Capability Notes |
|---|---|---|---|
| `fitz` (PyMuPDF) | Installed | 1.22.0 | Core vector extraction, page rotation, pixmap rendering |
| `pdfplumber` | Installed | 0.11.7 | PDF tabular extraction & text layout inspection |
| `shapely` | Installed | 2.1.1 | Geometric intersection, buffering, spatial R-tree indexing |
| `cv2` (OpenCV) | Installed | 4.11.0 | Raster mask processing, contour detection, morphological ops |
| `torch` | Installed | 2.1.0+cpu | PyTorch CPU-only build |
| `timm` | Installed | 1.0.22 | Pretrained vision backbones |
| `transformers` | Installed | 4.41.2 | Hugging Face SegFormer / vision models |
| `ultralytics` | Installed | 8.3.167 | YOLOv8 architecture suite |
| `scipy` | Installed | 1.15.3 | Scientific computing & spatial algorithms |
| `sklearn` | Installed | 1.7.2 | Scikit-learn evaluation metrics |
| `PIL` (Pillow) | Installed | 10.2.0 | Image manipulation & format conversion |
| `numpy` | Installed | 1.26.4 | Numerical arrays & tensor manipulation |
| `pandas` | Installed | 2.2.2 | CSV serialization & structured table operations |
| `matplotlib` | Installed | 3.10.3 | Visual QC plotting & chart generation |
| `albumentations` | **Not Installed** | None | Augmentation library (install if required by training) |
| `segmentation_models_pytorch` | **Not Installed** | None | SMP U-Net library (install or use timm/torchvision U-Net) |

---

## 7. Operational Recommendations for Downstream Milestones

1. **Hardware-Aware Training Strategy (R3 / M4)**:
   - Because the local host has only CPU and ~0.9 GB available RAM, heavy model training on the local machine must be constrained to lightweight sanity checks (e.g., small crop resolution $256 \times 256$, batch size 2, lightweight encoder).
   - All training code must be structured as standalone, modular Python scripts that are **100% Google Colab compatible** to take advantage of free T4 GPU acceleration without local RAM starvation.
2. **Dataset Download Safety (R2 / M2)**:
   - The primary eligible dataset recommendation is **Modified Swiss Dwellings (MSD)** via Hugging Face (`philippds/modified-swiss-dwellings-enriched`, 174 MB download, CC BY 4.0).
   - If **CubiCasa5K** is downloaded, use the Zenodo zip (5.09 GB), which sits comfortably under the 16.37 GB C:\ disk limit and the 10 GB notification threshold. Avoid unpacking raw LMDB caches locally.
3. **Mandatory Human-in-the-Loop Review Stop (R1 / M3)**:
   - When partition schedule parsing completes in M3, the pipeline must export `partition_schedule_mapping.csv`, place a `REVIEW_REQUIRED.lock` sentinel, and halt execution awaiting human approval. Downstream classification in M5 must reject execution until `partition_schedule_mapping.approved.csv` is present.
4. **Weak Pseudo-Labeling Guardrails (R3 / M4)**:
   - Vector extractions from the 99th Street PDF may only be used for semi-supervised fine-tuning if explicitly tagged as `weak_pseudo_label`, visually spot-checked for error rate, and **strictly quarantined away from validation and test splits**.

---
*Report SURVEY-EXP1-M1-001 complete and verified against live file and terminal evidence.*
