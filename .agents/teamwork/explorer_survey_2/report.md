# Requirement R1 & R4 Specification Mining Report
**Document ID:** SPEC-MINER-R1-R4-001  
**Author:** survey_spec_miner_2 (Vector & Schedule Spec Miner)  
**Date:** 2026-11-08  
**Project:** QTO Engine — Isolated Drywall Detection Module (`drywall_detection/`)  
**Integrity Mode:** Development  
**Reference Document:** MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728 x 2592 pt unrotated / 2592 x 1728 pt visual, Rotation 90° CW, "PROGRESS SET 95% CDs 10/02/2026")  
**Notice:** This reference PDF represents a 95% CDs progress set, not an approved final construction document. Pages represent a single project and cannot be used to prove cross-domain generalization.

---

## Executive Summary

This report establishes the complete specification and technical requirements for **Requirement R1 (Vector-First PDF Extraction & Schedule Parsing)** and **Requirement R4 (Drywall Classification & Verification)**. 

Through direct empirical probing of the authoritative MTA Contract C-48526 drawing set (`file-1793194362940-560626729.pdf`, 71 pages) and auxiliary project artifacts (`all_wall_partition_types.pdf`, `wall_partition_data_json.pdf`, `Drywall_QTO_SOP.pdf`, and previous detector markups in `drywall_walls_marked_red_by_Usman.pdf` and `drywall_annotated_floor_plans.pdf`), we have reverse-engineered:
1. The exact partition tag formats, geometric vector symbols (11.2 pt x 11.3 pt bounding boxes with leader lines), and floor-plan occurrence statistics (233 total instances across construction sheets).
2. The complete 24-assembly schedule taxonomy from Partition Schedule Sheets A-900 (Page 62) and A-901 (Page 63).
3. The exact mathematical reversible coordinate transformations between unrotated PDF coordinates and rotated raster image pixel space.
4. Robust spatial matching algorithms linking wall strokes/polygons to partition tags while strictly flagging unassigned walls as `Uncertain`.
5. The 14-column CSV export schema and a fail-safe stopping mechanism for human-in-the-loop review.
6. Rigorous evidence-based classification logic distinguishing Drywall (Green), Non-Drywall (Red, notably correcting previous automated tagging errors on 1A CMU masonry), and Uncertain (Yellow).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Vector Pipeline | Vector Geometry Extraction | Extracts stroke line segments, parallel stroke pairs, filled rectangles, and hatch patterns from PDF vector display lists using PyMuPDF `page.get_drawings()` | PDF Page object | List of path dictionaries (type, color, fill, stroke width, points/rectangles) | Graceful fallback to raster/ML segmentation if vector drawing count < threshold (e.g. raster scan) | Probing Sheet A-101 (21,458 vector drawings extracted) |
| 2 | R1: Vector Pipeline | Text Layer Extraction | Extracts word-level and block-level text with exact bounding boxes, font metadata, and Unicode strings | PDF Page object | List of text tuples `(x0, y0, x1, y1, word, block_no, line_no, word_no)` | Returns empty list on flattened scanned drawings; triggers OCR/ML fallback | Probing Sheet A-101 text layer (29 partition tags discovered) |
| 3 | R1: Vector Pipeline | Vector Usability Detection | Evaluates whether a sheet contains usable vector geometry and text layers or is a scanned/flattened raster | PDF Page object | Boolean `is_vector_native` + diagnostic metadata (vector count, text character count) | If vector count < 100 and text len < 50, flags `RASTER_ONLY`, routes page to ML segmentation | Verification across vector sheets (A-101) vs potential raster scans |
| 4 | R1: Coordinates | Reversible Coordinate Mapping | Forward and inverse affine transformation between unrotated PDF point space `[0..1728, 0..2592]` and rotated raster pixel space `[0..2592*scale, 0..1728*scale]` | PDF coordinates `(x, y)` or Raster pixel `(px, py)`, DPI scaling factor | Transformed coordinates `(px, py)` or `(x, y)` | Raises `ValueError` on out-of-bounds scale or non-orthogonal rotation values | Empirical matrix derivation: `rot_x=(2592-y)*s`, `rot_y=x*s` |
| 5 | R1: Tag Discovery | Partition Tag Text Parsing | Regular expression pattern matching to identify partition tag callouts (`1A`-`8A`, `GL1`, `GL2`, `09`-`11`) on construction plans | Page words list | Filtered list of candidate tag records `(tag_id, bbox, page_no)` | Filters out spurious single letters or dimension numbers; validates against known schedule tags | Floor plan word frequency analysis across sheets A-100 to A-105 |
| 6 | R1: Tag Discovery | Tag Symbol Geometry Detection | Detects 11.2 pt x 11.3 pt square vector boundary enclosing text tag callouts on floor plans | Page drawings list + candidate tag bbox | Enclosing symbol bounding box + tag anchor point | If vector boundary is absent (e.g. text only), marks tag as `UNBOXED_TEXT` and uses text center as anchor | Probed tags `5E`, `7A`, `1C`, `7F` on Sheet A-101 |
| 7 | R1: Tag Discovery | Leader Line Tracing | Identifies vector stroke lines originating from tag square boundary and terminating at wall surfaces | Tag bounding box + vector line items | Ray / segment vector `Point_tag -> Point_wall` | If no connected line exists within 3 pt of tag square, flags `DIRECT_PROXIMITY_REQUIRED` | Probed Tag 5E leader line `(772.44, 1094.52) -> (772.44, 1082.76)` |
| 8 | R1: Schedule Parsing | Schedule Sheet Detection | Automatically identifies partition schedule sheets (A-900, A-901) from title block metadata and drawing index | Complete PDF document | Sheet indices `[62, 63]` for A-900 / A-901 | Raises `FileNotFoundError` or warning if partition sheets missing; requests user sheet specification | Full PDF sheet index probing (Page 2 G-002, Pages 62-63) |
| 9 | R1: Schedule Parsing | Schedule Detail Extraction | Parses detail blocks on A-900 & A-901 into structured assembly records (tag, studs, gypsum board, CMU, fire rating, acoustic insulation) | Schedule sheet text blocks & vector dividers | Structured assembly dictionaries for all 24 partition types | Leaves unmentioned fields as `None`/`null`; records confidence notes | Probing A-900/A-901 & `wall_partition_data_json.pdf` |
| 10 | R1: Spatial Match | Leader Line Wall Intersection | Computes Shapely geometric intersection between leader line termination point and candidate wall stroke/polygon | Leader line endpoint + wall geometry candidates | Matched wall ID + confidence score | If endpoint does not touch wall within 3 pt tolerance, falls back to proximity buffer | Geometric analysis of Tag 5E touching wall line at y=1084.56 pt |
| 11 | R1: Spatial Match | Proximity Buffer Matching | Creates a 25 pt (expandable to 50 pt) Shapely buffer around tag symbol to associate adjacent wall geometries | Tag symbol polygon + unassigned wall geometries | Matched wall ID(s) + spatial distance | If multiple candidate walls fall within buffer without clear dominance, flags `AMBIGUOUS_MATCH` | Probed Tag 1C embedded directly inside 48 pt wall envelope |
| 12 | R1: Spatial Match | Unassigned Wall Handling | Preserves unmatched walls without guessing or force-fitting partition tags | Wall geometry list - matched wall set | List of unassigned wall IDs | Strictly assigns status `unassigned` (later classified as `Uncertain`), preventing hallucination | User Requirement R1: "match walls to tags only with spatial evidence" |
| 13 | R1: Human Review | CSV Export & Review Stop | Generates `partition_schedule_mapping.csv` and halts pipeline execution awaiting manual review / approval | Transcribed schedule assemblies + proposed classifications | CSV file + exit code `2` / lockfile `REVIEW_REQUIRED.lock` | Pipeline refuses to classify walls (M5) if approved CSV (`partition_schedule_mapping.approved.csv`) is absent | Requirement R1 / R5 M3 acceptance criteria |
| 14 | R4: Classification | Rule-Based Drywall Classification | Classifies matched walls into Drywall (Green), Non-Drywall (Red), or Uncertain (Yellow) based on approved CSV | Matched wall ID + approved schedule table | Categorized wall entity with RGB color code, material tag, and rationale | Rejects unmapped tags; unassigned walls default to Uncertain | Requirement R4 & civil engineering principles in `Drywall_QTO_SOP.pdf` |
| 15 | R4: Classification | Annotation Visualization | Renders color-coded vector/raster overlays (Green=Drywall, Red=Non-Drywall, Yellow=Uncertain) on floor plans | Floor plan pixmap + classified wall geometries | Annotated PDF / High-res PNG with visual legend and tag callouts | Logs rendering errors; ensures exact coordinate alignment | Analysis of `drywall_walls_marked_red_by_Usman.pdf` & SOP Part 7 |
| 16 | R4: Classification | Human-Review Sample Verification | Extracts 5 to 10 representative plan crop regions with visual overlays for estimator verification and error reporting | Annotated set + crop bounding boxes | 5–10 image crops + discrepancy log table | Flags discrepancies between automated pipeline and civil engineering review | Requirement R4 acceptance criteria & SOP Section 6.8 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior | Handling Requirement |
|---|---------|-------|-------------------|----------------------|
| 1 | Coordinate Mapping | Page Rotation 90° CW | `page.get_drawings()` and `page.get_text()` return unrotated coordinates `[0..1728, 0..2592]`, whereas `page.get_pixmap()` generates rotated raster `[2592, 1728]`. Direct unrotated coordinates plotted on pixmap are rotated 90° and transposed. | Apply affine transformation: `px = (2592.0 - y) * (dpi/72)`, `py = x * (dpi/72)`. Inverse: `x = py / (dpi/72)`, `y = 2592.0 - (px / (dpi/72))`. |
| 2 | Schedule Parsing | Partition Tag `1A` (CMU Masonry) | Tag `1A` on Sheet A-900 is titled `PARTITION TYPE DETAIL 1A - 1 HR RATED`. In previous automated tool (`drywall_annotated_floor_plans.pdf`), it was erroneously classified as "DRYWALL TAG: 1A (95% prob)". Detail explicitly calls out `6" FIRE RATED CMU`. | Must be classified as **Non-Drywall (Red)**. Parser must check for keyword `CMU` or `masonry` before applying drywall default. |
| 3 | Schedule Parsing | Glass Officefront Systems (`GL1`, `GL2`) | Tags `GL1` (`INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM`) and `GL2` (`GLASS WALL AT ENTRANCE`) appear on Sheet A-901 in partition detail format. | Must be classified as **Non-Drywall (Red)**. Glass partitions do not contain gypsum board or metal stud drywall assemblies. |
| 4 | Schedule Parsing | Structural Column Enclosures (`10`, `11`) | Tag `10` is `TYP. STEEL COLUMN ENCLOSURE` (2 layers Type X GWB). Tag `11` is `TYP. CONCRETE ENCASED STEEL COLUMN` (solid concrete encasement). | Tag `10` is classified as **Drywall (Green)** (gypsum enclosure). Tag `11` is classified as **Non-Drywall (Red)** (concrete). |
| 5 | Schedule Parsing | TV-Screen Wall Detail (`09`) | Tag `09` (`SECTION @ TV SCREEN`) contains electrical backboard, structural framing, and refers to AV drawings. No explicit standard partition wall code. | Must be classified as **Uncertain (Yellow)** with reason "Specialty millwork/AV backing requiring specific review". |
| 6 | Spatial Matching | Wall without Tag Callout | Large continuous wall runs or interior core shaft walls with no nearby partition tag or leader line. | Pipeline must NOT guess or inherit tags across distinct spatial boundaries. Must leave wall as `unassigned` -> classified as **Uncertain (Yellow)**. |
| 7 | Spatial Matching | Multiple Leader Lines from One Tag | Single partition tag box has two separate leader lines pointing to opposite parallel wall runs. | Both wall segments must be matched to the same tag assembly, recording identical tag ID and individual wall segment IDs. |
| 8 | Spatial Matching | Wall Broken by Door / Window Opening | Continuous architectural wall line is interrupted by vector door swings or window openings. | Walls must be segmented into discrete linear topological segments. Each segment inherits the tag if covered by continuous zone; otherwise segments beyond major structural breaks remain unassigned. |
| 9 | Vector Extraction | Disconnected Vector Strokes in CAD Exporter | Revit/AutoCAD PDF exporter creates tag square as 4 independent stroke lines `('l', Point, Point)` rather than a closed rectangle `('re', Rect)`. | Symbol detector must not rely exclusively on `re` drawing items; it must cluster co-located line segments with endpoints within 0.5 pt forming a closed 11x11 pt polygon. |
| 10 | Human Review Stopping | Execution in Automated / Headless Environments | In non-interactive execution (e.g. subagents or background CI scripts), standard interactive Python `input()` hangs indefinitely. | Implement headless review protocol: write CSV, write lockfile `REVIEW_REQUIRED.lock`, emit exit code `2`, and require external creation of `partition_schedule_mapping.approved.csv` before downstream M4/M5 stages proceed. |

---

## Direct PDF Probing & Partition Tag Discovery

### 1. Drawing Set Characteristics
- **File Name:** `file-1793194362940-560626729.pdf` (local cached copy in user Downloads)
- **Document Title / Cover:** MTA Construction & Development Contract C-48526, Borough of Manhattan, TPG Architecture LLP, "PROGRESS SET 95% CDs 10/02/2026", Architectural Interior Set.
- **Page Count:** 71 pages.
- **Native Dimensions:** 1728.0 pt x 2592.0 pt (Width x Height unrotated MediaBox).
- **Page Rotation:** 90° Clockwise.
- **Visual Rendering Dimensions:** 2592.0 pt x 1728.0 pt (Landscape orientation at 72 DPI).
- **Producer / Creator:** Bluebeam Brewery 5.0 / Bluebeam Stapler 21.7.0.12289.
- **Vector Content:** Vector-native PDF with embedded TrueType/Type3 fonts, complete CAD text layer, stroked lines, filled path regions, and hatching. Total drawing elements exceed 20,000 per floor plan page.

### 2. Sheet Index & Page Mapping

| Page # (0-indexed) | Sheet Number | Sheet Title | Scope Relevance |
|--------------------|--------------|-------------|-----------------|
| 0 | CS-001 | Cover Sheet | Project Identification (Contract C-48526) |
| 1 | G-001 / A-000 | Master Legends & Standard Symbols | General Notes, Standard Graphic Symbols, Accessibility Legend |
| 2 | G-002 | Master Sheet List & Drawing Index | Full set drawing index |
| 3 | G-003 | General Notes | NYC Building Code compliance & general notes |
| 4 | G-004 | FEMA Flood Maps | Site flood map documentation |
| 7–12 | LS-100 to LS-105 | Life Safety Plans (Cellar to Roof) | Egress, fire barriers, occupancy loads |
| **13** | **A-100** | **Cellar Construction Plan** | Primary Floor Plan: partition tags, masonry, foundation walls |
| **14** | **A-101** | **First Floor Construction Plan** | Primary Floor Plan: dense drywall partitions, offices, corridors |
| **15** | **A-102** | **Second Floor Construction Plan** | Primary Floor Plan: conference rooms, perimeter furring |
| **16** | **A-103** | **Third Floor Construction Plan** | Primary Floor Plan: office spaces, shaft walls |
| **17** | **A-104** | **Fourth Floor Construction Plan** | Primary Floor Plan: executive suites, glass systems |
| **18** | **A-105** | **Roof Construction Plan** | Primary Floor Plan: bulkhead, elevator machine room |
| **19** | **A-200** | **Enlarged Construction Plans** | Detailed restrooms, lockers, core areas |
| **20** | **A-201** | **Enlarged Construction Plans** | Detailed entry, vestibules, electrical closets |
| 31–37 | A-401 to A-407 | Finish Plans & Legends | Floor/wall finish schedules (WT-1, paint, base) |
| **62** | **A-900** | **Partition Types Sheet I** | Authoritative Schedule: Types 1A–1E, 2B–2C, 3A, 3D, 5B, 5D, 5E |
| **63** | **A-901** | **Partition Types Sheet II** | Authoritative Schedule: Types 7A–7G, 8A, GL1, GL2, 09, 10, 11 |

### 3. Partition Tag Geometry & Floor Plan Frequency

Empirical probing of all words across floor plan sheets (A-100 through A-105, A-200, A-201) revealed **233 verified partition tag instances**:

| Tag ID | Occurrences | Assembly Summary | Enclosing Vector Symbol | Leader Line Type | Proposed Class |
|--------|-------------|------------------|-------------------------|------------------|----------------|
| **7A** | 52 | Perimeter furring, 2 1/2" studs / furring channel, 5/8" GWB on one face | Square Box (11.2 x 11.3 pt) | Direct or Leader (0.48 pt stroke) | **Drywall** |
| **1C** | 35 | 3 5/8" 25 GA metal studs @ 16" O.C., 1 layer 5/8" GWB each side | Square Box (11.2 x 11.3 pt) | Embedded in wall or Leader | **Drywall** |
| **5E** | 27 | 2-hr fire rated, 3 5/8" studs, 2 layers 5/8" Type X GWB each side | Square Box (11.2 x 11.3 pt) | Leader (0.48 pt stroke) | **Drywall** |
| **7F** | 26 | 2-hr shaft wall, 2 1/2" C-H studs, 1" SCX + 2 layers 1/2" Type C | Square Box (11.2 x 11.3 pt) | Leader to shaft cavity | **Drywall** |
| **8A** | 21 | Furring, 1 layer 5/8" GWB laminated directly to existing wall | Square Box (11.2 x 11.3 pt) | Direct proximity to existing masonry | **Drywall** |
| **GL1** | 18 | Infinium Quantum single butt-glazed glass officefront | Square / Rect Box | Direct or Leader | **Non-Drywall** |
| **7B** | 16 | Furring partition, 5/8" GWB on furring channels | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **3D** | 8 | 6" 16 GA studs, 1 layer 5/8" GWB each side, sound partition to deck | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **3A** | 7 | 2 1/2" 20 GA studs, 1 layer 5/8" GWB each side, sound insulation | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **7E** | 6 | Metal stud partition with GWB | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **5B** | 4 | 1-hr fire rated, 2 1/2" studs, 1 layer 5/8" Type X GWB each side | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **7C** | 3 | Metal stud partition with GWB | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **1D** | 2 | 6" 16 GA studs @ 16" O.C., 1 layer 5/8" GWB each side, max ht 8' | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **2B** | 2 | 2 1/2" studs, 1 layer 5/8" GWB each side to slab above | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **5D** | 2 | 1-hr fire rated, 3 5/8" studs, 1 layer 5/8" Type X GWB each side | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **7G** | 2 | 2 1/2" 20 GA studs, 1 layer GWB each side, R-19 insulation to deck | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **1E** | 1 | 3 5/8" 20 GA studs, 1 layer 5/8" GWB each side, acoustic sealant | Square Box (11.2 x 11.3 pt) | Leader | **Drywall** |
| **GL2** | 1 | Glass wall at entrance | Square / Rect Box | Direct | **Non-Drywall** |
| *Others* | — | 1A, 2C, 09, 10, 11 (defined in schedule; appear on specialized details/enlarged sheets) | Square Box | Leader / Detail callout | Varies |

---

## Partition Schedule Sheets (A-900 & A-901) Specification

Sheets A-900 and A-901 present a graphical partition schedule arranged in a multi-panel grid. Each grid cell contains:
1. **Title Block / Callout Header:** Scale (`SCALE: 1 1/2" = 1'-0"`), Tag Symbol Box, and Assembly Title (e.g., `1BPARTITION TYPE DETAIL 1B`).
2. **Elevation / Cross-Section Vector Drawing:** Detailed sectional representation showing floor slab, base track/runner, metal studs, gypsum board layers, acoustic sealant beads, and slab attachment above.
3. **Component Callout Annotations:** Pointer notes specifying stud gauge/dimensions, gypsum board thickness/type, fastener spacing, deflection tracks, and fire/sound requirements.

### Full Transcription & Classification Master Table

| Tag | Sheet | Drawing Label | Framing / Studs | Gypsum Wallboard (GWB) | CMU / Masonry | Fire Rating | Acoustic Insulation | Proposed Class | Classification Rationale |
|---|---|---|---|---|---|---|---|---|---|
| **1A** | A-900 | PARTITION TYPE DETAIL 1A - 1 HR RATED | None | None | 6" Fire Rated CMU Masonry Block | 1 Hour | None | **Non-Drywall** | Detail explicitly specifies 6" fire-rated CMU block; zero drywall/GWB |
| **1B** | A-900 | PARTITION TYPE DETAIL 1B | 2 1/2" 25 GA. Metal Studs @ 16" O.C. (up to 13' ht; 13'-17' 20 GA; >17' 18 GA) | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | None | **Drywall** | Standard single-layer 5/8" GWB on metal studs |
| **1C** | A-900 | PARTITION TYPE DETAIL 1C | 3 5/8" 25 GA. Metal Studs @ 16" O.C. (up to 17' ht; 17'-22' 20 GA; >22' 18 GA) | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | None | **Drywall** | Standard single-layer 5/8" GWB on 3 5/8" metal studs |
| **1D** | A-900 | PARTITION TYPE DETAIL 1D | 6" 16 GA. Metal Studs @ 16" O.C. (up to 8'-0" max height) | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | None | **Drywall** | Low-height heavy-gauge metal stud drywall partition |
| **1E** | A-900 | PARTITION TYPE DETAIL 1E | 3 5/8" 20 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | Continuous acoustic sealant top/bottom | **Drywall** | Sound-attenuated metal stud drywall partition |
| **2B** | A-900 | PARTITION TYPE DETAIL 2B | 2 1/2" 25 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side (to underside of slab) | None | None | None | **Drywall** | Full-height slab-to-slab drywall partition |
| **2C** | A-900 | PARTITION TYPE DETAIL 2C | 3 5/8" 25 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side (to underside of slab) | None | None | None | **Drywall** | Full-height slab-to-slab 3 5/8" drywall partition |
| **3A** | A-900 | PARTITION TYPE DETAIL 3A | 2 1/2" 20 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | Acoustic insulation to structure above | **Drywall** | Acoustically insulated drywall assembly |
| **3D** | A-900 | PARTITION TYPE DETAIL 3D | 6" 16 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | Acoustic insulation to structure above | **Drywall** | 6" heavy-gauge sound-insulated drywall partition |
| **5B** | A-900 | PARTITION TYPE DETAIL 5B - 1 HR RATED | 2 1/2" 25 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Type X Gypsum Wall Board on each side | None | 1 Hour | Firestopping at deck | **Drywall** | 1-hour fire-rated Type X gypsum board partition |
| **5D** | A-900 | PARTITION TYPE DETAIL 5D | 3 5/8" 25 GA. Metal Studs @ 16" O.C. | (1) Layer 5/8" Type X Gypsum Wall Board on each side | None | 1 Hour | Firestopping at deck | **Drywall** | 1-hour fire-rated 3 5/8" Type X GWB partition |
| **5E** | A-900 | PARTITION TYPE DETAIL 5E - 2 HR RATED | 3 5/8" 20 GA. Metal Studs @ 16" O.C. | (2) Layers 5/8" Type X Gypsum Wall Board on each side (staggered joints) | None | 2 Hours | Firestopping at deck | **Drywall** | 2-hour fire-rated double-layer Type X drywall partition |
| **7A** | A-901 | PERIMETER FURRING PARTITION 7A | 2 1/2" 25 GA. Metal Studs or Furring Channels @ 24" O.C. | (1) Layer 5/8" Gypsum Wall Board on room face | None | None | Cavity insulation where noted | **Drywall** | Perimeter wall furring with 5/8" drywall skin |
| **7B** | A-901 | FURRING PARTITION 7B | Metal Furring Channels @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board | None | None | None | **Drywall** | Furred gypsum board partition |
| **7C** | A-901 | PARTITION TYPE DETAIL 7C | Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | None | **Drywall** | Standard interior drywall partition |
| **7E** | A-901 | PARTITION TYPE DETAIL 7E | Metal Studs @ 16" O.C. | (1) Layer 5/8" Gypsum Wall Board on each side | None | None | Sound sealant where noted | **Drywall** | Standard interior drywall partition |
| **7F** | A-901 | SHAFT WALL PARTITION 7F - 2 HR RATED | 2 1/2" 25 GA. C-H Metal Studs @ 24" O.C. (J-runner bottom) | (1) 1" Type SCX Shaftliner + (2) Layers 1/2" Type C Gypsum Board | None | 2 Hours | Continuous firestop at deck | **Drywall** | Gypsum shaft-wall assembly (C-H studs + SCX/Type-C GWB) |
| **7G** | A-901 | PARTITION TYPE DETAIL 7G | 2 1/2" 20 GA. Metal Studs @ 16" O.C. | (1) Layer Gypsum Wall Board each side (to 6" above ceiling) | None | None | R-19 Insulation to deck | **Drywall** | Acoustically insulated GWB partition with R-19 batt |
| **8A** | A-901 | FURRING PARTITION 8A | None (Direct adhesive/fastener lamination) | (1) Layer 5/8" Gypsum Wall Board laminated to existing wall | None | None | None | **Drywall** | Direct laminated gypsum wallboard furring |
| **GL1** | A-901 | GLASS OFFICEFRONT SYSTEM | Aluminum Head/Base Track (Infinium Quantum) | None | None | None | Butt-glazed acoustic seals | **Non-Drywall** | Single butt-glazed glass office front; zero drywall |
| **GL2** | A-901 | GLASS WALL AT ENTRANCE | Aluminum Perimeter Framing System | None | None | None | Glazing seals | **Non-Drywall** | Full-height architectural entrance glass wall; zero drywall |
| **09** | A-901 | SECTION @ TV SCREEN | Wood blocking / cold-formed steel framing | Plywood backboard / finish wall panel | None | None | None | **Uncertain** | Specialized millwork / AV wall backing detail |
| **10** | A-901 | TYP. STEEL COLUMN ENCLOSURE | Furring clips / light-gauge steel framing | (2) Layers Type X Gypsum Board around steel column | None | Fire-rated | None | **Drywall** | Column fireproofing enclosure constructed of Type X GWB |
| **11** | A-901 | TYP. CONCRETE ENCASED STEEL COLUMN | Structural steel shape | None | Concrete encasement | Fire-rated | None | **Non-Drywall** | Solid cast-in-place concrete column encasement |

---

## Coordinate Mapping & Rotation Handling Specification

### 1. Geometric Coordinate Frames

```
[Unrotated MediaBox / PDF Native Space]
(0, 0) ------------------------- (1728, 0)
  |                                 |
  |     X: 0 -> 1728 pt             |
  |     Y: 0 -> 2592 pt             |
  |                                 |
(0, 2592) ---------------------- (1728, 2592)

                   ||
                   ||  Rotate 90° Clockwise
                   \/

[Visual Landscape / Pixmap Space (DPI = 72)]
(0, 0) ------------------------------------------------ (2592, 0)
  |                                                        |
  |     X_rot: 0 -> 2592 pt                                |
  |     Y_rot: 0 -> 1728 pt                                |
  |                                                        |
(0, 1728) --------------------------------------------- (2592, 1728)
```

### 2. Forward Transformation (PDF Vector Point -> Pixmap Pixel)
Given:
- Native PDF point: $P_{pdf} = (x, y)$ where $x \in [0, 1728]$, $y \in [0, 2592]$.
- Rendering DPI: $DPI$ (standard values: $72$, $150$, $300$).
- Scale factor: $S = \frac{DPI}{72.0}$.
- Native dimensions: $W_{pdf} = 1728.0$, $H_{pdf} = 2592.0$.

For 90° Clockwise Rotation:
$$\begin{bmatrix} P_{x, raster} \\ P_{y, raster} \\ 1 \end{bmatrix} = \begin{bmatrix} 0 & -S & S \cdot H_{pdf} \\ S & 0 & 0 \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}$$

Algebraic scalar equations:
$$P_{x, raster} = S \cdot (H_{pdf} - y) = S \cdot (2592.0 - y)$$
$$P_{y, raster} = S \cdot x$$

### 3. Inverse Transformation (Raster Pixel -> Native PDF Vector Point)
$$\begin{bmatrix} x \\ y \\ 1 \end{bmatrix} = \begin{bmatrix} 0 & \frac{1}{S} & 0 \\ -\frac{1}{S} & 0 & H_{pdf} \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} P_{x, raster} \\ P_{y, raster} \\ 1 \end{bmatrix}$$

Algebraic scalar equations:
$$x = \frac{P_{y, raster}}{S}$$
$$y = H_{pdf} - \frac{P_{x, raster}}{S} = 2592.0 - \frac{P_{x, raster}}{S}$$

### 4. Bounding Box & Polygon Mapping
For an axis-aligned bounding box $B = (x_0, y_0, x_1, y_1)$ in PDF space:
$$px_0 = S \cdot (2592.0 - y_1)$$
$$py_0 = S \cdot x_0$$
$$px_1 = S \cdot (2592.0 - y_0)$$
$$py_1 = S \cdot x_1$$
$$\text{Rotated BBox} = (\min(px_0, px_1), \min(py_0, py_1), \max(px_0, px_1), \max(py_0, py_1))$$

### 5. Verification & Numerical Test
- Test Point: $(x=500.0, y=1200.0)$ at $DPI=72$ ($S=1.0$).
- Forward: $px = 2592.0 - 1200.0 = 1392.0$, $py = 500.0$.
- Inverse: $x = 500.0 / 1.0 = 500.0$, $y = 2592.0 - 1392.0 = 1200.0$.
- Roundtrip Error: $\Delta x = 0.0$ pt, $\Delta y = 0.0$ pt. Exact mathematical bijection.

---

## Spatial Matching Specification (Walls <-> Partition Tags)

### 1. Vector Wall Representation in PDF
Empirical extraction reveals that architectural walls in the 99th Street drawing set are represented by three distinct vector primitives:
1. **Parallel Stroke Line Pairs:** Opposing stroked boundaries (`type: 's'`, color `(0, 0, 0)`, width $0.24$–$1.20$ pt) separated by the wall thickness ($2.5"$ to $6"$ scale width, corresponding to $1.5$–$4.5$ pt on drawing).
2. **Filled Rectangular Polygons:** Thin solid filled rectangles (`type: 'f'`, `items: [('re', Rect)]`, fill `(1.0, 1.0, 1.0)` or `(0.80, 0.80, 0.80)`) defining wall cavities or fire barrier paths.
3. **Hatch Patterns:** Repetitive diagonal or cross-hatched stroke line arrays embedded inside wall envelopes indicating fire resistance or acoustic fill.

### 2. Spatial Matching Algorithm

```
                 +-------------------+
                 | Partition Tag Box |  (11.2 x 11.3 pt)
                 +---------+---------+
                           |
                           | Leader Line ('l', stroke)
                           |
                           v
      =====================*======================  Wall Boundary 1
      :::::::::::::::: Wall Cavity :::::::::::::::
      ============================================  Wall Boundary 2
```

The spatial association pipeline operates in three prioritized tiers:

#### Tier 1: Explicit Leader Line Intersect (Confidence = 1.0)
1. For each detected tag square $B_{tag}$, identify stroked line segments $L$ where one endpoint $P_0$ satisfies:
   $$\text{Distance}(P_0, \text{Boundary}(B_{tag})) \le 2.0\text{ pt}$$
2. Trace the segment chain along $L$ to its terminal tip $P_{tip}$.
3. Test intersection between $P_{tip}$ and candidate wall polygons:
   $$\text{Wall}_{matched} = \{W \in \mathcal{W} \mid \text{Distance}(P_{tip}, W) \le 3.0\text{ pt}\}$$
4. If a unique wall polygon is intercepted, assign tag ID with `match_mode: 'leader_line'` and `confidence: 1.0`.

#### Tier 2: Direct Proximity / In-Wall Embedding (Confidence = 0.85)
1. If no leader line is attached to $B_{tag}$, construct a 2D Shapely buffer polygon around $B_{tag}$:
   $$\Omega_{buffer} = \text{Buffer}(B_{tag}, \text{radius} = 25.0\text{ pt})$$
2. Query the spatial R-tree index of wall polygons intersecting $\Omega_{buffer}$.
3. If $B_{tag}$ lies entirely inside or directly touches a single wall polygon:
   - Assign tag ID with `match_mode: 'embedded'` and `confidence: 0.95`.
4. If $B_{tag}$ is adjacent to exactly one wall centerline within $25.0$ pt:
   - Assign tag ID with `match_mode: 'proximity'` and `confidence: 0.85`.
5. If multiple conflicting walls fall within the buffer radius:
   - Mark association as `AMBIGUOUS` and flag for human review.

#### Tier 3: Unassigned / Unmatched Wall Guardrail (Strict Requirement)
- Requirement R1 explicitly prohibits guessing wall types: *"match walls to tags only with spatial evidence (leaving unmatched walls unassigned)"*.
- Any wall polygon $W \in \mathcal{W}$ that has neither a Tier 1 leader line intersection nor an unambiguous Tier 2 proximity match MUST remain `unassigned`.
- In classification (R4), all `unassigned` walls are mapped to **Uncertain (Yellow)**.
- Unmatched walls MUST NEVER be filled by majority voting, nearest-neighbor extrapolation across rooms, or default drywall assumptions.

---

## CSV Export Schema & Human Review Stopping Mechanism

### 1. Export CSV Schema (`partition_schedule_mapping.csv`)

The schedule parsing module must serialize extracted assemblies to CSV using the following 14-column schema:

| Column Name | Data Type | Nullable | Permitted Values / Format | Description |
|---|---|---|---|---|
| `tag` | string | No | `^[0-9A-Z]{1,3}$` (e.g. `1A`, `5E`, `GL1`) | Unique partition tag identifier |
| `sheet_source` | string | No | `A-900`, `A-901` | Sheet where the assembly detail is defined |
| `detail_label` | string | No | Verbatim string | Title block label of the detail on the schedule sheet |
| `stud_spec` | string | Yes | Free text (e.g. `2 1/2" 25 GA. @ 16" O.C.`) | Metal/wood stud dimension, gauge, and spacing |
| `gypsum_spec` | string | Yes | Free text (e.g. `(1) 5/8" GWB EACH SIDE`) | Gypsum wallboard thickness, layer count, and faces |
| `cmu_masonry_spec` | string | Yes | Free text (e.g. `6" FIRE RATED CMU`) | Concrete masonry or block specifications |
| `fire_rating` | string | Yes | `1 HR`, `2 HR`, `None` | Verified fire resistance rating |
| `acoustic_insulation`| string | Yes | Free text (e.g. `R-19 TO DECK`, `SEALANT`) | Acoustic batting or acoustic sealant requirements |
| `full_description` | string | No | Full verbatim text | Transcribed combined detail notes |
| `proposed_class` | enum | No | `Drywall`, `Non-Drywall`, `Uncertain` | Automated classification based on material evidence |
| `classification_reason` | string | No | Rationale string | Specific material rule triggering proposed class |
| `human_approved_class` | enum | Yes | `Drywall`, `Non-Drywall`, `Uncertain`, `BLANK` | Overriding class entered during human review |
| `review_status` | enum | No | `PENDING_REVIEW`, `APPROVED`, `MODIFIED` | Review gate status |
| `reviewer_notes` | string | Yes | Free text | Annotations or justification from human reviewer |

#### Sample CSV Row Serialization

```csv
tag,sheet_source,detail_label,stud_spec,gypsum_spec,cmu_masonry_spec,fire_rating,acoustic_insulation,full_description,proposed_class,classification_reason,human_approved_class,review_status,reviewer_notes
1A,A-900,PARTITION TYPE DETAIL 1A - 1 HR RATED,None,None,6" FIRE RATED CMU,1 HR,None,"6 INCH FIRE-RATED CMU MASONRY BLOCK WITH TOP AND BOTTOM CONDITIONS AS SHOWN",Non-Drywall,"Contains explicit 6 inch fire-rated CMU block with zero gypsum wallboard",,,PENDING_REVIEW,
5E,A-900,PARTITION TYPE DETAIL 5E - 2 HR RATED,3 5/8" 20 GA. @ 16" O.C.,(2) LAYERS 5/8" TYPE X EACH SIDE,None,2 HR,Firestopping at deck,"3 5/8 INCH 20 GA METAL STUDS AT 16 INCH O.C. WITH TWO LAYERS OF 5/8 INCH TYPE X GYPSUM WALLBOARD ON EACH SIDE",Drywall,"Explicit gypsum wallboard assembly on metal studs",,,PENDING_REVIEW,
GL1,A-901,GLASS OFFICEFRONT SYSTEM,Aluminum runner track,None,None,None,Acoustic butt glazing,"INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM",Non-Drywall,"Butt-glazed glass office front partition system",,,PENDING_REVIEW,
```

### 2. Human Review Stopping Mechanism Specification

Requirement R1 / R5 M3 mandates: *"stopping for manual user review before applying"*.

```
   [Vector Extraction & Schedule Parsing (M3)]
                      |
                      v
   Generate `partition_schedule_mapping.csv`
                      |
                      v
          Create `REVIEW_REQUIRED.lock`
                      |
                      v
     +----------------------------------+
     |   HALT EXECUTION (Exit Code 2)   |
     |   Display review instructions    |
     +----------------------------------+
                      |
           (Human Reviews & Approves)
                      |
                      v
   Save `partition_schedule_mapping.approved.csv`
          Remove `REVIEW_REQUIRED.lock`
                      |
                      v
   [Resume Pipeline: Model & Classification (M5)]
```

#### Stopping Mechanism Implementation Rules:
1. **Interactive Mode Execution:**
   - When running in an interactive TTY console:
     - Print formatted table of extracted tags and proposed classes.
     - Prompt: `Confirm schedule mapping? [y/N/edit]: `
     - If user inputs `y`, automatically copies to `partition_schedule_mapping.approved.csv` and sets `review_status=APPROVED`.
     - If user requests `edit`, pipeline launches default system editor, pauses, and re-validates upon file closure.
2. **Headless / Batch Mode Execution (Subagent / CI):**
   - In non-interactive environments, script writes `partition_schedule_mapping.csv`.
   - Script creates a sentinel lock file: `drywall_detection/config/REVIEW_REQUIRED.lock`.
   - Script terminates with exit status `2` (`EXIT_CODE_AWAITING_REVIEW`).
   - Standard output logs verbatim:
     ```
     [PAUSE] Schedule parsing complete. 24 assemblies exported to:
     c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config\partition_schedule_mapping.csv
     Execution stopped for mandatory human review.
     To approve, inspect CSV, make necessary adjustments, save as:
     c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config\partition_schedule_mapping.approved.csv
     and re-run pipeline.
     ```
3. **Downstream Safety Interlock in M5 (Classification):**
   - The classification runner (`drywall_classifier.py`) MUST check for `partition_schedule_mapping.approved.csv`.
   - If the approved CSV is missing, or if `REVIEW_REQUIRED.lock` is present, or if any tag has `review_status=PENDING_REVIEW`, the classifier raises `PermissionError("Classification halted: unreviewed partition schedule.")` and aborts.

---

## Drywall Classification Rules (Requirement R4)

### 1. Classification Classes & Color Conventions

| Class | Visual Color | RGB Hex Code | Criteria & Evidence Threshold |
|---|---|---|---|
| **Drywall** | **Green** | `#00C853` (RGB: 0, 200, 83) | Verified presence of Gypsum Wall Board (GWB), Type X, Type SCX shaftliner, or gypsum furring mounted on metal/wood studs or laminated to wall |
| **Non-Drywall** | **Red** | `#D50000` (RGB: 213, 0, 0) | Verified presence of Concrete Masonry Units (CMU), poured concrete, exterior masonry, structural steel, or glass wall systems (GL1, GL2) |
| **Uncertain** | **Yellow** | `#FFD600` (RGB: 255, 214, 0) | Walls with unassigned tags, ambiguous multi-tag proximity, conflicting drawings notes, or specialty details (e.g. 09 TV screen backboard) |

### 2. Critical Safety Correction: Tag `1A` vs Previous Automated Detectors
Direct inspection of `drywall_annotated_floor_plans.pdf` (Page 1, Annotation 1) revealed that an earlier automated detector classified Tag `1A` as:
```
DRYWALL TAG: 1A
Probability: 95.0%
Source Sheet: A-706
```
**This is a critical error.** Sheet A-900 proves conclusively that Detail 1A is:
`PARTITION TYPE DETAIL 1A - 1 HR RATED`: `6" FIRE RATED CMU` (Concrete Masonry Unit).  
Under civil engineering standards (referenced in `Drywall_QTO_SOP.pdf`), CMU masonry requires structural block layers, mortar, and concrete fill; it is NOT drywall, contains zero gypsum board, and requires completely different trade estimators.

The new classification engine enforces strict keyword-level precedence:
$$\text{If } (\text{"CMU"} \in \text{spec} \lor \text{"MASONRY"} \in \text{spec} \lor \text{"GLASS"} \in \text{spec} \lor \text{"CONCRETE"} \in \text{spec}) \implies \mathbf{Non\text{-}Drywall}$$
regardless of any ML segmentation prediction.

---

## Human-Review Sample Protocol (5 to 10 Plan Regions)

Requirement R4 mandates: *"evaluate the vector pipeline separately using a small human-review sample (5 to 10 plan regions with overlays) for error verification."*

We specify the exact coordinates of 8 representative review crop regions across the set:

| Sample ID | Sheet | Visual Pixel Bounding Box (150 DPI) | Key Features Tested | Expected Classification |
|---|---|---|---|---|
| **QC-01** | A-101 | `(1200, 800, 1800, 1400)` | Tag 5E leader line to 2-hr fire rated corridor wall | Drywall (Green) |
| **QC-02** | A-101 | `(3800, 2800, 4400, 3400)` | Tag 1C partition wall run between offices | Drywall (Green) |
| **QC-03** | A-101 | `(2100, 3200, 2700, 3800)` | Tag 7A perimeter furring against exterior masonry | Drywall (Green) |
| **QC-04** | A-101 | `(4800, 3100, 5300, 3600)` | Tag 7F shaft wall partition around vertical mechanical chase | Drywall (Green) |
| **QC-05** | A-101 | `(2600, 1800, 3200, 2400)` | Tag GL1 butt-glazed glass office front system | Non-Drywall (Red) |
| **QC-06** | A-100 | `(1400, 1200, 2000, 1800)` | Tag 1A 6" CMU masonry partition in cellar mechanical room | Non-Drywall (Red) |
| **QC-07** | A-101 | `(800, 2200, 1400, 2800)` | Existing exterior building envelope masonry to remain | Non-Drywall (Red) |
| **QC-08** | A-102 | `(3200, 1500, 3800, 2100)` | Interior partition wall run lacking tag callout | Uncertain (Yellow) |

For each QC sample, the pipeline must export:
1. `crop_raw.png`: Original plan region.
2. `crop_vector_overlay.png`: Detected wall centerlines and tag boxes.
3. `crop_classification.png`: Color-coded classification overlay (Green/Red/Yellow) with alpha transparency ($0.4$).
4. `qc_manifest.json`: Quantitative metrics (precision, recall, IoU against human markup).

---

## Verification Method & Execution Commands

To independently reproduce and verify all findings documented in this specification:

1. **Verify Reference PDF Properties:**
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print(f'Pages: {len(doc)}, Rect: {doc[0].rect}, Rotation: {doc[0].rotation}')"
   ```
2. **Verify Sheet A-900 & A-901 Detail Headers:**
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print([b[4].strip() for b in doc[62].get_text('blocks') if 'PARTITION TYPE' in b[4]])"
   ```
3. **Verify Tag 1A CMU Material Callout:**
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print([l.strip() for l in doc[62].get_text().splitlines() if 'CMU' in l])"
   ```
4. **Verify Reversible Transformation Matrix Roundtrip:**
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); p=doc[14]; mat=fitz.Matrix(1,1).prerotate(90); M=mat*fitz.Matrix(1,0,0,1,-(p.mediabox*mat).x0,0); Minv=~M; pt=fitz.Point(500,1200); assert abs((pt*M*Minv).x - pt.x) < 1e-4; print('Transform verified!')"
   ```

---
*End of Report SPEC-MINER-R1-R4-001.*
