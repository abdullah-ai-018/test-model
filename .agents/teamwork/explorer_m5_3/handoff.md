# Handoff Report: Milestone M5 Ground Truth Validation & Human-Review Benchmark Architecture

**Document ID:** HANDOFF-M5-EXPLORER-GT-BENCHMARK  
**Role:** `explorer_m5_3` (M5 Ground Truth Validation & Human-Review Benchmark Architect)  
**Workspace:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_3\`  
**Target Milestone:** M5 (Drywall Classification & Verification)  
**Parent Orchestrator:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Date:** 2026-11-09  

---

## 1. Observation

### 1.1 Direct File System & Reference Document Observations
Live inspection of local storage and environment configuration confirmed the presence, integrity, and exact byte counts of all core architectural documents and ground truth files:

1. **Master Architectural Reference PDF**:
   - Path: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
   - Size: 29,110,223 bytes (29.11 MB).
   - Document Structure: 71 pages, unrotated portrait MediaBox $[0.0, 0.0, 1728.0, 2592.0]$ pt ($24" \times 36"$), rendered with a $90^\circ$ clockwise page rotation (`page.rotation == 90`), yielding landscape visual dimensions of $[0.0, 0.0, 2592.0, 1728.0]$ pt ($36" \times 24"$).
   - Prominent Title Block Stamp: `"PROGRESS SET 95% CDs 10/02/2026"`, MTA Contract C-48526, 99th Street Phase 2 Interior Set.
   - Sheet Index Mapping:
     - `A-100` (Cellar Construction Plan): Page Index 13
     - `A-101` (First Floor Construction Plan): Page Index 14
     - `A-102` (Second Floor Construction Plan): Page Index 15
     - `A-103` (Third Floor Construction Plan): Page Index 16
     - `A-104` (Fourth Floor Construction Plan): Page Index 17
     - `A-105` (Roof Construction Plan): Page Index 18
     - `A-900` (Partition Types Sheet I, Details 1A–5E): Page Index 62
     - `A-901` (Partition Types Sheet II, Details 7A–11, GL1, GL2): Page Index 63

2. **Auxiliary Ground Truth Markup PDF**:
   - Path: `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf`
   - Size: 8,445,633 bytes (8.45 MB).
   - Document Structure: 27 pages, all with `rect = Rect(0.0, 0.0, 2592.0, 1728.0)` and `rotation = 90`.
   - Sheet Page Correspondence in Usman PDF:
     - Page Index 0 $\to$ Sheet `A-100` (Cellar Plan)
     - Page Index 1 $\to$ Sheet `A-101` (First Floor Plan)
     - Page Index 2 $\to$ Sheet `A-102` (Second Floor Plan)
     - Page Index 3 $\to$ Sheet `A-103` (Third Floor Plan)
     - Page Index 4 $\to$ Sheet `A-104` (Fourth Floor Plan)
     - Page Index 5 $\to$ Sheet `A-105` (Roof Plan)
     - Page Indices 6–10 $\to$ Reflected Ceiling Plans (A-200 to A-204)
     - Page Indices 11–15 $\to$ Finish Plans (A-401 to A-406)
     - Page Indices 21–22 $\to$ Partition Schedules (A-900 and A-901)

3. **Approved Partition Schedule Mapping CSV**:
   - Path: `drywall_detection/data/partition_schedule_mapping.approved.csv`
   - Size: 6,432 bytes; 25 lines (Header + 24 assembly details).
   - Class Breakdown:
     - **Drywall (Green)**: 19 Details (1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, 10).
     - **Non-Drywall (Red)**: 4 Details (1A CMU masonry mandatory safety veto, 11 Concrete pier, GL1 Infinium glass, GL2 Tubelite entrance glass).
     - **Uncertain (Yellow)**: 1 Detail (09 TV screen architectural niche).
   - Review sentinel lockfile: `drywall_detection/data/REVIEW_REQUIRED.lock` has been cleared.

---

### 1.2 Quantitative Analysis of `drywall_walls_marked_red_by_Usman.pdf`
Inspection via PyMuPDF (`fitz`) revealed the exact mathematical structure of human expert annotations on construction plans A-100 to A-104:

```powershell
python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf'); ..."
```

#### Exact Annotation Inventory Across Sheets A-100 to A-104:
| Sheet | Master PDF Page | Usman PDF Page | Total Annots | 'Line' Annots (Centerlines) | 'Square' Annots (Tag Enclosures) | Red Color Spec | Line Stroke Width |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **A-100** | 13 | 0 | **8** | 4 | 4 | `(1.0, 0.0, 0.0)` | $5.0$ pt |
| **A-101** | 14 | 1 | **56** | 28 | 28 | `(1.0, 0.0, 0.0)` | $5.0$ pt |
| **A-102** | 15 | 2 | **142** | 71 | 71 | `(1.0, 0.0, 0.0)` | $5.0$ pt |
| **A-103** | 16 | 3 | **134** | 67 | 67 | `(1.0, 0.0, 0.0)` | $5.0$ pt |
| **A-104** | 17 | 4 | **138** | 69 | 69 | `(1.0, 0.0, 0.0)` | $5.0$ pt |
| **TOTAL** | — | — | **478** | **239** | **239** | — | — |

**Empirical Invariants Directly Observed:**
1. **Strict 1:1 Pairing**: For every single marked drywall wall on sheets A-100 through A-104, there exists exactly **one Line annotation** (tracing the wall cavity centerline) and **one Square annotation** (enclosing the associated partition tag). $239 + 239 = 478$ total human annotations.
2. **Annotation Color & Stroke**:
   - Line annotations: Stroke color `(1.0, 0.0, 0.0)` (pure RGB red), stroke width $5.0$ pt, no fill, line ends `(0, 0)`.
   - Square annotations: Stroke color `(0.850, 0.0, 0.0)`, width $1.0\text{--}1.5$ pt, tightly bounding the partition tag symbol box ($11.2 \times 11.3$ pt).
3. **Partition Tags Enclosed by Usman Squares**:
   - Sheet A-100 (4 walls): `5E` (4).
   - Sheet A-101 (28 walls): `7A` (8), `5E` (6), `5B` (3), `1C` (2), `8A` (2), `3A` (1), `1E` (1), `1D` (1), `7F` (1), + 3 compound tags.
   - Sheet A-102 (71 walls): `1C` (15), `7A` (10), `8A` (10), `7B` (7), `7F` (5), `5E` (4), `3D` (2), `2B` (2), `3A` (1), + compound callouts.
   - Sheet A-103 (67 walls): `2C` (17), `7A` (13), `1C` (8), `7F` (7), `7B` (5), `5E` (5), `3D` (2), `3A` (1), `7G` (1), `5D` (1), + compound callouts.
   - Sheet A-104 (69 walls): `7A` (16), `2C` (11), `3D` (4), `1C` (4), `5E` (4), `7F` (4), `3A` (4), `7B` (3), `8A` (2), `7G` (1), `7E` (1), + compound callouts.
4. **Selective Ground Truth Precedence**:
   - Usman **exclusively** marked verified Gypsum Wallboard (GWB) drywall assemblies in red.
   - Non-drywall assemblies—such as Detail 1A CMU masonry, Detail 11 concrete column piers, GL1 butt-glazed glass office fronts, and GL2 entrance glass storefronts—were **strictly left unannotated** by the human estimator.
   - This proves that in human expert practice, "red markup" in `drywall_walls_marked_red_by_Usman.pdf` specifically designated *drywall scope of work*, creating a high-fidelity ground truth for Drywall True Positives.

---

### 1.3 Material and Detail Spatial Cluster Observations
Direct text and vector scans on the floor plan sheets revealed specific architectural locations where drywall, non-drywall, and uncertain elements co-occur:

1. **Detail 1A (`6" FIRE RATED CMU MASONRY BLOCK`)**:
   - Located on Sheet A-900 (Page 62) at unrotated PDF coordinates $[415.6, 2259.6, 437.3, 2278.6]$ pt.
   - Text specification: `"6\" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB."`
   - Studs: `None (CMU block)`. GWB layers: `0`. Fire rating: `1-HR`. Trade: `Masonry`.
   - Classification in Approved Schedule: `Non-Drywall` (Red, `#D50000`).

2. **Glass Officefront Assemblies (GL1 & GL2)**:
   - Tag `GL2` (Entrance Storefront): Discovered on Sheet A-101 at $[732.4, 936.9, 743.4, 948.1]$ pt, adjacent to door D101.
   - Tag `GL1` (Infinium Quantum demountable glass office fronts): Discovered on:
     - Sheet A-102 at $[621.2, 988.0, 632.1, 999.2]$ pt.
     - Sheet A-103 at 8 distinct office fronts along the corridor: $[578.2, 981.4]$, $[578.2, 1065.9]$, $[669.7, 1150.5]$, $[578.2, 1234.8]$, $[577.9, 1319.8]$, $[669.7, 1386.8]$, $[690.1, 1759.0]$, $[729.9, 1891.9]$.
     - Sheet A-104 at 9 distinct office fronts: $[620.0, 958.3]$, $[706.9, 986.0]$, $[706.9, 1052.0]$, $[673.5, 1205.7]$, $[489.8, 1266.8]$, $[673.5, 1287.0]$, $[673.5, 1377.8]$, $[673.5, 1461.1]$, $[488.5, 1600.9]$.

3. **Concrete Piers & Columns (Detail 11)**:
   - Discovered on Sheet A-101 at $[757.7, 1006.2]$, $[652.3, 1843.8]$, $[533.2, 1896.9]$, $[538.1, 1182.3]$, $[538.7, 1354.2]$, $[539.1, 1535.1]$.
   - Discovered on Sheet A-102 at $[750.8, 1809.7]$, $[733.3, 1840.0]$, $[733.3, 1893.4]$, $[650.2, 1893.4]$, $[620.7, 1704.8]$.
   - Discovered on Sheet A-103 at $[655.7, 1877.1]$, $[695.3, 1890.4]$.

4. **Architectural Millwork / TV Niches (Detail 09 - Uncertain)**:
   - Discovered on Sheet A-101 at $[732.3, 1031.6]$ pt.
   - Discovered on Sheet A-102 at $[476.8, 864.8]$ pt.
   - Discovered on Sheet A-103 at $[452.3, 1581.4]$ pt.
   - Discovered on Sheet A-104 at $[514.9, 857.1]$ pt and $[567.9, 1081.4]$ pt.

---

### 1.4 Codebase State
- `drywall_detection/vector/extractor.py`: Implements vector linework filtering, parallel wall pairing, and reversible affine transformation.
- `drywall_detection/vector/schedule_parser.py`: Catalogues all 24 details, enforces Detail 1A safety veto, and manages the approved CSV review gate.
- `drywall_detection/vector/spatial_matcher.py`: Implements 3-tier matching (leader line raycast, buffer proximity, and strict unassigned fallback).
- Missing files to be designed/implemented for Milestone M5:
  - `drywall_detection/classification/classifier.py` (Core classification module)
  - `drywall_detection/classification/__init__.py` (Package exports)
  - `drywall_detection/tests/test_classification.py` (Verification test suite)
  - `drywall_detection/reports/M5_classification_report.md` (Formal milestone report)

---

## 2. Logic Chain

### Step 1: Verification of Auxiliary Ground Truth Semantics
- From Observation 1.2, Usman's markup in `drywall_walls_marked_red_by_Usman.pdf` contains exactly 239 centerline walls across Sheets A-100 to A-104.
- Every single marked wall corresponds to a verified Drywall assembly tag (e.g. `5E`, `7A`, `1C`, `2C`, `3A`, `3D`, `5B`, `7B`, `7F`, `8A`).
- Non-drywall assemblies (Detail 1A CMU block, Detail 11 concrete piers, GL1/GL2 glass office fronts) were intentionally unannotated by the human expert estimator.
- Therefore, Usman's markups provide an exact, authoritative ground truth for evaluating Drywall True Positives ($TP$) and Drywall False Negatives ($FN$).
- However, because Usman did not mark non-drywall or uncertain walls, evaluating the complete 3-class taxonomy requires dedicated human-review benchmark plan regions where Non-Drywall (Red), Drywall (Green), and Uncertain (Yellow) co-exist.

### Step 2: Formulation of the 10 Human-Review Benchmark Plan Regions
To satisfy Requirement R4 ("evaluate the vector pipeline separately using a small human-review sample (5 to 10 plan regions with overlays) for error verification"), we formulate exactly 10 representative plan regions spanning Sheets A-100, A-101, A-102, A-103, A-104, and Schedule Sheet A-900:

#### Authoritative Specification of the 10 Benchmark Regions:

| Region ID | Sheet | Page | PDF Bounding Box $[x_1, y_1, x_2, y_2]$ (pt) | 150 DPI Pixel BBox $[px_1, py_1, px_2, py_2]$ (px) | Key Partition Tags Present | Expected Material Classification | Architectural Description & Test Purpose |
|---|:---:|:---:|---|---|---|---|---|
| **R01** | A-100 | 13 | $[450.0, 900.0, 820.0, 1100.0]$ | $[3108.3, 937.5, 3525.0, 1708.3]$ | `5E` | **Drywall (Green)** | Cellar Stair D050 enclosure: 2-HR fire-rated GWB drywall partition matching Usman red markup. |
| **R02** | A-101 | 14 | $[650.0, 880.0, 780.0, 1000.0]$ | $[3316.7, 1354.2, 3566.7, 1625.0]$ | `GL2`, `10`, `1C` | **Non-Drywall (Red)** (`GL2`), **Drywall (Green)** (`10`, `1C`) | First Floor Main Entrance Vestibule: Tests discrimination between aluminum entrance glass storefront (`GL2`) and GWB wall/column wraps. |
| **R03** | A-101 | 14 | $[700.0, 980.0, 820.0, 1120.0]$ | $[3066.7, 1458.3, 3358.3, 1708.3]$ | `09`, `11`, `5E`, `7A` | **Uncertain (Yellow)** (`09`), **Non-Drywall (Red)** (`11`), **Drywall (Green)** (`5E`, `7A`) | First Floor TV Niche & Concrete Pier: Complex multi-class cluster testing co-existence of all 3 material classes in tight proximity. |
| **R04** | A-101 | 14 | $[640.0, 1600.0, 820.0, 1750.0]$ | $[1754.2, 1333.3, 2066.7, 1708.3]$ | `7F`, `5B`, `7A` | **Drywall (Green)** | First Floor Shaft & Tool Crib: High-density drywall cluster (2-HR shaft liner, 1-HR GWB, furring) matching Usman centerlines. |
| **R05** | A-102 | 15 | $[450.0, 840.0, 650.0, 1020.0]$ | $[3275.0, 937.5, 3650.0, 1354.2]$ | `GL1`, `2B`, `3D`, `09` | **Non-Drywall (Red)** (`GL1`), **Drywall (Green)** (`2B`, `3D`), **Uncertain (Yellow)** (`09`) | Second Floor Enclosed Office Suite: Butt-glazed demountable glass office front (`GL1`) abutting acoustic drywall and TV niche. |
| **R06** | A-102 | 15 | $[600.0, 1780.0, 780.0, 1920.0]$ | $[1400.0, 1250.0, 1691.7, 1625.0]$ | `11`, `7A`, `7B` | **Non-Drywall (Red)** (`11`), **Drywall (Green)** (`7A`, `7B`) | Second Floor Structural Column Piers: Structural 26"x26" concrete pier (`11`) surrounded by drywall perimeter furring (`7A`, `7B`). |
| **R07** | A-103 | 16 | $[550.0, 950.0, 700.0, 1400.0]$ | $[2483.3, 1145.8, 3420.8, 1458.3]$ | `GL1` (x6), `1C`, `2C` | **Non-Drywall (Red)** (`GL1`), **Drywall (Green)** (`1C`, `2C`) | Third Floor Corridor Glass Office Front Bank: 6 consecutive glass officefronts with GWB demising walls; tests repetitive glass detection. |
| **R08** | A-104 | 17 | $[470.0, 840.0, 720.0, 1100.0]$ | $[3108.3, 979.2, 3650.0, 1500.0]$ | `09` (x2), `GL1` (x3), `2C`, `7A` | **Uncertain (Yellow)** (`09`), **Non-Drywall (Red)** (`GL1`), **Drywall (Green)** (`2C`, `7A`) | Fourth Floor Executive Conference Suite: Multi-class stress test with double TV niche millwork blocking and demountable glass partitions. |
| **R09** | A-900 | 62 | $[350.0, 2200.0, 480.0, 2350.0]$ | $[504.2, 729.2, 816.7, 1000.0]$ | `1A` | **Non-Drywall (Red)** | Partition Schedule Detail 1A Assembly Box: Mandatory safety veto verification region confirming Detail 1A 6" CMU is classified as Non-Drywall. |
| **R10** | A-101 | 14 | $[300.0, 1100.0, 450.0, 1300.0]$ | $[2691.7, 625.0, 3108.3, 937.5]$ | *Untagged* | **Uncertain (Yellow)** | Exterior Wall Envelope / Untagged Linework: Tests Tier 3 unassigned fallback guardrail; ensures non-hallucination on untagged geometry. |

### Step 3: Derivation of Exact Coordinate Transformations
From Observation 1.1, the master PDF is drafted in portrait MediaBox $[0.0, 0.0, 1728.0, 2592.0]$ pt and rendered with $90^\circ$ clockwise rotation:
- **Forward Mapping ($M: \text{PDF} \to \text{Pixel}$)**:
  $$px = (2592.0 - y) \cdot \frac{\text{DPI}}{72.0}$$
  $$py = x \cdot \frac{\text{DPI}}{72.0}$$
- **Bounding Box Mapping ($[x_1, y_1, x_2, y_2] \to [px_1, py_1, px_2, py_2]$)**:
  Under $90^\circ$ CW rotation, the minimum and maximum coordinates transform with inverted Y:
  $$px_1 = (2592.0 - y_2) \cdot \frac{\text{DPI}}{72.0}, \quad px_2 = (2592.0 - y_1) \cdot \frac{\text{DPI}}{72.0}$$
  $$py_1 = x_1 \cdot \frac{\text{DPI}}{72.0}, \quad py_2 = x_2 \cdot \frac{\text{DPI}}{72.0}$$
  All 10 pixel bounding boxes above are analytically computed at $\text{DPI} = 150$, guaranteeing exact zero-drift alignment with rendered image overlays.

### Step 4: Formulation of Quantitative Error Verification Metrics
To establish a rigorous, objective benchmark across the human-review regions and the entire drawing set, we formulate the following 5 verification metrics:

1. **Drywall Precision ($P_{\text{drywall}}$)**:
   $$P_{\text{drywall}} = \frac{TP_{\text{drywall}}}{TP_{\text{drywall}} + FP_{\text{drywall}}}$$
   - *Target*: $\ge 95.0\%$. Measures purity of drywall predictions (ensures non-drywall or ambiguous elements are not erroneously included in drywall takeoffs).

2. **Drywall Recall ($R_{\text{drywall}}$)**:
   $$R_{\text{drywall}} = \frac{TP_{\text{drywall}}}{TP_{\text{drywall}} + FN_{\text{drywall}}}$$
   - *Target*: $\ge 90.0\%$ (calibrated against Usman's 239 centerline markups).

3. **Overall 3-Class Accuracy ($Acc_{\text{overall}}$)**:
   $$Acc_{\text{overall}} = \frac{TP_{\text{drywall}} + TP_{\text{non-drywall}} + TP_{\text{uncertain}}}{N_{\text{total\_walls}}}$$
   - *Target*: $\ge 92.0\%$ across all 10 human-review benchmark regions.

4. **False Positive Drywall Rate ($FPR_{\text{drywall}}$)**:
   $$FPR_{\text{drywall}} = \frac{FP_{\text{drywall}}}{TN_{\text{drywall}} + FP_{\text{drywall}}}$$
   - Where $TN_{\text{drywall}}$ represents actual Non-Drywall (CMU, concrete, glass) and Uncertain walls.
   - *Safety Target*: **Strictly $0.0\%$** on Non-Drywall assemblies. Non-drywall materials (especially CMU Detail 1A and glass assemblies) must never be classified as Drywall.

5. **CMU Safety Veto Compliance ($Comp_{\text{CMU}}$)**:
   $$Comp_{\text{CMU}} = \begin{cases} 100\% & \text{if all Detail 1A instances are classified as Non-Drywall (Red)} \\ 0\% & \text{if any Detail 1A instance is classified as Drywall (Green)} \end{cases}$$
   - *Mandatory Invariant*: Strictly $100\%$. Any failure constitutes an unconditional milestone failure.

---

### Step 5: Test Suite Architecture Specification for `drywall_detection/tests/test_classification.py`
The test suite must provide comprehensive unit, safety, schema, and benchmark coverage:

```python
# Blueprint for drywall_detection/tests/test_classification.py

class TestDrywallRuleBasedClassification:
    """Verifies evidence-based 3-class assignment from approved CSV mapping."""
    def test_approved_csv_loading_and_row_count(self): ...
    def test_drywall_tags_classified_green(self): ...     # 19 tags -> Drywall (#00C853)
    def test_nondrywall_tags_classified_red(self): ...    # 4 tags (1A, 11, GL1, GL2) -> Non-Drywall (#D50000)
    def test_uncertain_tags_classified_yellow(self): ...  # 1 tag (09) -> Uncertain (#FFD600)
    def test_unassigned_walls_classified_uncertain(self): ... # Guardrail test

class TestDetail1ACMUSafetyVeto:
    """Verifies mandatory Detail 1A CMU safety override."""
    def test_detail_1a_unconditional_nondrywall(self): ...
    def test_detail_1a_tampered_csv_raises_integrity_violation(self): ...
    def test_detail_1a_spatial_match_veto(self): ...

class TestClassifierGeoJSONSchema:
    """Verifies dataclass attributes and GeoJSON export integrity."""
    def test_classified_wall_dataclass_fields(self): ...
    def test_to_geojson_feature_validity(self): ...
    def test_geojson_roundtrip_reconstruction(self): ...

class TestHybridPipelineAndRasterFallback:
    """Verifies vector-first routing and fallback to SegFormer-B0 ML model."""
    def test_vector_page_routes_to_vector_classifier(self): ...
    def test_scanned_raster_page_routes_to_ml_inferencer(self): ...
    def test_hybrid_mask_fusion_without_drift(self): ...

class TestHumanReviewBenchmarkSample:
    """Evaluates the 10 defined benchmark plan regions (R01-R10)."""
    def test_r01_to_r10_region_classifications(self): ...
    def test_precision_recall_accuracy_metrics(self): ...
    def test_zero_false_positive_drywall_on_glass_and_cmu(self): ...

class TestVisualOverlayGenerator:
    """Verifies generation of annotated images and PDFs."""
    def test_overlay_alpha_blending(self): ...
    def test_90deg_rotation_alignment(self): ...
    def test_legend_and_summary_banner(self): ...
```

---

### Step 6: Design Blueprint for Milestone Report `M5_classification_report.md`
The formal report `drywall_detection/reports/M5_classification_report.md` must be structured into 10 mandatory sections:

1. **Mandatory Notice — Progress Set & Single-Project Bounds**:
   - Explicit verbatim citation:
     > **MANDATORY NOTICE — PROGRESS SET & SINGLE-PROJECT BOUNDS**  
     > The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
     > Furthermore, all 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, vector extractions, and model classifications on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards.
2. **Executive Summary & Milestone M5 Objectives**:
   - Scope, taxonomy (Green, Red, Yellow), approved schedule integration, and key achievements.
3. **Approved Schedule Mapping Integration & 4-Class Taxonomy**:
   - Authoritative table of all 24 details with proposed class, trade, fire rating, and color hex.
4. **Detail 1A CMU Safety Veto & Forensic Guardrails**:
   - Forensic justification, veto mechanism, tampered CSV fail-fast validation.
5. **Auxiliary Ground Truth Inspection (`drywall_walls_marked_red_by_Usman.pdf`)**:
   - 478 red human markups (239 centerline lines + 239 tag squares), breakdown per sheet A-100 to A-104, intersection statistics.
6. **10 Human-Review Benchmark Plan Regions**:
   - Complete tables of regions R01–R10 with PDF/pixel bounding boxes, tags, and expected vs observed classes.
7. **Quantitative Error Verification Metrics**:
   - Precision ($P_{\text{drywall}}$), Recall ($R_{\text{drywall}}$), Accuracy ($Acc_{\text{overall}}$), False Positive Drywall Rate ($FPR_{\text{drywall}} = 0.0\%$), and CMU Safety Compliance ($100\%$).
8. **Test Suite Verification Results (`test_classification.py`)**:
   - Pytest execution logs, test pass counts, and execution latency.
9. **Visual Verification Artifacts Index**:
   - File listing and previews of generated visual overlays and annotated PDFs.
10. **Limitations, Domain Boundary & M6 Handoff Readiness**:
    - Remaining work for M6 final delivery (standalone reload, end-to-end CLI, final delivery package).

---

## 3. Caveats

1. **Progress Set Calibration Single-Project Bounds**:
   - The master drawing set is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"`. It does not represent an as-built final construction document.
   - All ground truth annotations from Usman originate from this single project facility. While invaluable for within-distribution calibration, metrics cannot prove out-of-domain generalization to other architectural drawing standards or BIM exports.
2. **Human Markup Vector Imprecision**:
   - In `drywall_walls_marked_red_by_Usman.pdf`, human annotations were placed manually using a PDF markup pen ($5.0$ pt width).
   - Some centerline lines do not terminate at exact CAD vertex snap points, exhibiting small offsets ($\pm 2\text{--}4$ pt) relative to the vector linework parallel pairs. Spatial intersection queries must therefore use a minimum buffer tolerance of $3.0\text{--}5.0$ pt.
3. **Absence of Detail 1A on Upper Floor Plans**:
   - The master drawing set contains Detail 1A on Sheet A-900 (Page 62). However, upper residential/office floor plans (A-101 to A-104) predominantly use gypsum metal stud partitions (Types 1C, 2C, 5E, 7A) and glass systems (GL1, GL2).
   - Detail 1A is verified on Sheet A-900 (Region R09) and in unit test fixtures (`test_detail_1a_tampered_csv_raises_integrity_violation`), ensuring zero-leakage safety enforcement regardless of drawing sheet.
4. **Compound and Overlapping Tag Callouts**:
   - On Sheets A-102 and A-104, several partition tags appear in compound or closely spaced callouts (e.g., `8A/7F`, `2C/GL1`). The spatial matcher and classifier must cleanly isolate the individual tag tokens to prevent misclassification.

---

## 4. Conclusion

1. **Auxiliary Ground Truth Decoded**:
   - `drywall_walls_marked_red_by_Usman.pdf` contains **exactly 478 human annotations** across Sheets A-100 to A-104, structured in **exactly 239 pairs of centerline lines and tag squares**.
   - Usman exclusively marked drywall assemblies in red, confirming that human red markups establish a definitive ground truth for Drywall True Positives.
2. **10 Human-Review Benchmark Plan Regions Established**:
   - Standardized 10 plan regions (R01 through R10) across Sheets A-100, A-101, A-102, A-103, A-104, and A-900.
   - Defined dual coordinate bounding boxes (unrotated PDF points and 150 DPI rotated pixels), partition tags, and expected classifications.
   - Designed coverage across all 3 material classes: Drywall (Green), Non-Drywall (Red: Detail 1A CMU, Detail 11 concrete piers, GL1/GL2 glass systems), and Uncertain (Yellow: Detail 09 TV niches, untagged perimeter).
3. **Verification Metrics & Test Architecture Finalized**:
   - Established 5 rigorous error verification metrics with strict zero-tolerance safety bounds ($FPR_{\text{drywall}} = 0.0\%$ on non-drywall, CMU safety compliance $= 100\%$).
   - Designed complete unit and regression test specifications for `drywall_detection/tests/test_classification.py`.
   - Structured the formal milestone report blueprint for `drywall_detection/reports/M5_classification_report.md` incorporating the mandatory 95% CDs notice.
4. **Implementer Readiness**:
   - The architectural design is complete and fully specified. Implementer `worker_m5_1` has exact contracts, coordinates, formulas, and test templates to proceed with implementation immediately.

---

## 5. Verification Method

To independently verify all observations and architectural designs presented in this report:

### 1. Verify Auxiliary Ground Truth Markup Counts:
Run the following Python command to verify the exact 478 annotations (239 lines + 239 squares):
```powershell
python -c "
import fitz
doc = fitz.open(r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf')
total_annots, total_lines, total_squares = 0, 0, 0
for i in range(5):
    annots = list(doc[i].annots()) if doc[i].annots() else []
    lines = len([a for a in annots if a.type[1] == 'Line'])
    squares = len([a for a in annots if a.type[1] == 'Square'])
    total_annots += len(annots)
    total_lines += lines
    total_squares += squares
    print(f'Sheet A-10{i}: {len(annots)} annots ({lines} lines, {squares} squares)')
print(f'TOTAL: {total_annots} annots ({total_lines} lines, {total_squares} squares)')
assert total_annots == 478
assert total_lines == 239
assert total_squares == 239
print('ALL INVARIANTS VERIFIED!')
"
```

### 2. Verify Coordinate Transformations for Benchmark Regions R01–R10:
Run the following script to confirm exact roundtrip bijection and pixel bounding box calculations:
```powershell
python -c "
from drywall_detection.utils.coords import pdf_to_pixel, pixel_to_pdf

regions = [
    ('R01', (450.0, 900.0, 820.0, 1100.0)),
    ('R02', (650.0, 880.0, 780.0, 1000.0)),
    ('R03', (700.0, 980.0, 820.0, 1120.0)),
    ('R04', (640.0, 1600.0, 820.0, 1750.0)),
    ('R05', (450.0, 840.0, 650.0, 1020.0)),
    ('R06', (600.0, 1780.0, 780.0, 1920.0)),
    ('R07', (550.0, 950.0, 700.0, 1400.0)),
    ('R08', (470.0, 840.0, 720.0, 1100.0)),
    ('R09', (350.0, 2200.0, 480.0, 2350.0)),
    ('R10', (300.0, 1100.0, 450.0, 1300.0)),
]

for rid, (x1, y1, x2, y2) in regions:
    px1, py1 = pdf_to_pixel(x1, y2, dpi=150, rotation=90)
    px2, py2 = pdf_to_pixel(x2, y1, dpi=150, rotation=90)
    rx1, ry2 = pixel_to_pdf(px1, py1, dpi=150, rotation=90)
    rx2, ry1 = pixel_to_pdf(px2, py2, dpi=150, rotation=90)
    assert abs(rx1 - x1) < 1e-4 and abs(ry1 - y1) < 1e-4
    assert abs(rx2 - x2) < 1e-4 and abs(ry2 - y2) < 1e-4
print('ALL 10 REGIONS ROUNDTRIP BIJECTION VERIFIED (Error < 1e-4 pt)!')
"
```

### 3. Verify Approved Schedule Material Precedence:
Inspect `drywall_detection/data/partition_schedule_mapping.approved.csv`:
```powershell
python -c "
import csv
with open('drywall_detection/data/partition_schedule_mapping.approved.csv') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 24
rec_1a = next(r for r in rows if r['tag'] == '1A')
assert rec_1a['proposed_class'] == 'Non-Drywall'
assert 'CMU' in rec_1a['description'].upper()
print('APPROVED CSV INTEGRITY AND DETAIL 1A SAFETY VETO CONFIRMED!')
"
```

### Invalidation Conditions:
This analysis and architectural specification shall be considered invalidated if:
1. `drywall_walls_marked_red_by_Usman.pdf` is found to contain markup semantics that conflict with the 1:1 line/square pairing or include non-drywall materials.
2. Any candidate algorithm classifies Detail 1A CMU masonry as Drywall (Green).
3. The coordinate transformation fails to maintain roundtrip bijection within $10^{-4}$ pt or induces overlay drift exceeding $1.0$ pixel at 150 DPI.
