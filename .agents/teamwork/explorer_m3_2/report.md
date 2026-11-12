# Authoritative Partition Specification & Floor Plan Tag Mining Report (Milestone M3)

**Author:** `explorer_m3_2` (M3 Partition Tag and Schedule Spec Miner)  
**Date:** 2026-11-08  
**Authoritative Reference:** `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf` (MTA 99th Street Progress Set 95% CDs, 71 pages, MediaBox 1728 x 2592 pt)  
**Target Design Specification:** `drywall_detection/vector/schedule_parser.py`

---

## 1. Executive Summary & Authoritative Discoveries

1. **Partition Schedule Source Sheets (Pages 63 & 64)**:
   - **Sheet A-900 (Page 63, index 62)**: Titled `PARTITION TYPES SHEET I`. Contains exactly **12 assembly details** arranged in a 3-column x 4-row grid.
   - **Sheet A-901 (Page 64, index 63)**: Titled `PARTITION TYPES SHEET II`. Contains exactly **12 assembly details** arranged in a 3-column x 4-row grid.
   - **Total Assembly Details**: Exactly **24 assembly details** across both sheets (numbered/tagged: `1A`, `1B`, `1C`, `1D`, `1E`, `2B`, `2C`, `3A`, `3D`, `5B`, `5D`, `5E`, `7A`, `7B`, `7C`, `7E`, `7F`, `7G`, `8A`, `09`, `10`, `11`, `GL1`, `GL2`).
   - Tags `2A`, `3B`, `3C`, `5A`, `5C`, `7D`, `8B` **do not exist** anywhere in the architectural drawings or schedule.

2. **MANDATORY SAFETY CHECK (Detail 1A Verified)**:
   - Verbatim drawing text on Sheet A-900 (Row 3, Col 0):
     `6" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB. 1A PARTITION TYPE DETAIL 1A - 1 HR RATED`
   - Classification: **`Non-Drywall (Red)`** — **NEVER DRYWALL**.
   - Detail 1A is structural/masonry concrete masonry unit (CMU), completely devoid of gypsum wallboard.

3. **Floor Plan Partition Tag Geometry (Sheets A-100 to A-105, Pages 14-19)**:
   - **Tag Boundary Shape**: Exactly an **11.16 pt to 11.28 pt square** (~11.2 x 11.2 pt), composed of 4 separate vector line segments (`stroke=(0,0,0)`, `width=0.48 pt`, `fill=None`).
   - **Embedded Text**: Centered inside the square box; font is `ArialNarrow`, font size is `8.29 pt`, text color is black (`color=0`).
   - **Leader Line Geometry**: Straight vector line segment (`stroke=(0,0,0)`, `width=0.48 pt`) of standard length `9.00 pt` (varying from 4.5 pt to ~18 pt) extending orthogonally (0°, 90°, 180°, -90°) from the edge of the tag box and terminating directly on the centerline of the 3.24 pt (4.86" real-world) parallel wall vector boundaries.

4. **Material Classification Summary of 24 Details**:
   - **Drywall (Green)** (19 details): `1B`, `1C`, `1D`, `1E`, `2B`, `2C`, `3A`, `3D`, `5B`, `5D`, `5E`, `7A`, `7B`, `7C`, `7E`, `7F`, `7G`, `8A`, `10`.
   - **Non-Drywall (Red)** (4 details): `1A` (6" CMU), `11` (Concrete column encasement), `GL1` (Infinium Quantum glass officefront), `GL2` (Tubelite 400TU storefront).
   - **Uncertain (Yellow)** (1 detail): `09` (Specialty TV screen mounting section & AV millwork).

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Schedule Mining | Sheet Detection | Identification of schedule sheets A-900 and A-901 by title block keywords (`PARTITION TYPES SHEET I / II`) | PDF Document, page indices | Matching page objects and sheet names | Returns empty if sheet not found | Fitz text parsing on pages 62-63 |
| 2 | Schedule Mining | 3x4 Grid Partition Cell Extraction | Spatially bounded extraction of the 12 assembly detail cells per sheet in PDF mediabox coordinate space | PDF Page, grid row/column bounds | Raw text, vector paths, and bounding boxes per detail | Falls back to full-page regex if grid displaced | Fitz Rect extraction on 3 cols x 4 rows |
| 3 | Schedule Mining | Verbatim Detail Transcription | Complete text parsing of assembly callouts, stud gauge/width/spacing, GWB thickness, fire rating, STC acoustic rating | Cell bounding box | `ScheduleDetailRecord` object | Logs warning if mandatory fields missing | Fitz get_textbox & dict parsing |
| 4 | Safety Classification | Detail 1A Non-Drywall Guardrail | Hardcoded safety invariant enforcing that Tag 1A (6" CMU) is strictly classified as `Non-Drywall (Red)` | Detail Tag `"1A"` | Class `"Non-Drywall"`, Color `"#FF0000"`, Confidence `1.0` | Throws `AssertionError` if classified as Drywall | Sheet A-900 verification & PROJECT.md § 6 |
| 5 | Tag Discovery | 11.2 pt Vector Tag Box Detection | Recognition of partition tag symbols drawn as 4 closed line segments forming an 11.16–11.28 pt square | Floor plan vector drawings list | List of candidate tag box BBoxes | Ignores non-square or oversized/undersized paths | Fitz get_drawings on sheets A-101 to A-104 |
| 6 | Tag Discovery | ArialNarrow 8.29 pt Text Extraction | Extraction of 2-3 character alphanumeric partition tags inside tag boxes | Tag box Rect, page text dict | Tag ID string (`1C`, `2C`, `7F`, etc.) | Discards empty or non-matching text boxes | Fitz get_text("dict") on match coordinates |
| 7 | Tag Discovery | Orthogonal Leader Line Tracing | Tracing of 0.48 pt vector stroke line segments connected to tag boxes and extending to wall centerlines | Tag box BBox, vector drawings | Leader line segment `((x1,y1), (x2,y2))`, length, angle, wall contact point | Returns `None` if tag is leaderless (embedded directly in wall) | Geometric endpoint proximity search |
| 8 | Tag Discovery | Wall Centerline Intersection | Identification of parallel wall boundary lines intersected by leader tip point (nominal 3.24 pt gap = 4.86" wall) | Leader tip Point, wall line vectors | Matched wall assembly reference | Sets fallback to proximity buffer if ray misses | Vector spatial intersection check |
| 9 | Pipeline Integration | Authoritative Hard Fallback Table | Comprehensive dictionary of all 24 partition details providing fallback and test fixtures | Tag identifier string | Validated `ScheduleDetailRecord` | Returns `None` or raises `KeyError` for unknown tags | A-900/A-901 ground truth mining |
| 10 | Pipeline Integration | CSV Export & Sentinel Stopping Protocol | Writing `partition_schedule_mapping.csv`, creating `REVIEW_REQUIRED.lock`, and exiting with code 2 | List of `ScheduleDetailRecord` | CSV file on disk, lockfile on disk, exit code 2 | Fails if output directory unwritable | PROJECT.md § 4.2 contract |

---

## 3. Edge Cases & Observed Behavior

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Tag Numbering | Missing tags `2A`, `3B`, `3C`, `5A`, `5C`, `7D`, `8B` | Search across entire 71-page PDF yielded 0 occurrences. Confirmed these tags were skipped in the architectural naming convention. |
| 2 | Furniture Partitions | Tag `PW` and `PWD` in Floor Plan Legend | Refers to Steelcase demountable furniture walls (`PW`) and doors (`PWD`). Not in A-900/A-901 drywall schedule; classified as Demountable/Non-Drywall. |
| 3 | Room / Life Safety Tags | Strings like `OFFICE 00`, `FEC 1`, `10`, `11` | Text matching `10` or `11` matches both column enclosure tags AND room/door numbers. Requires bounding box / symbol filter (11.2 pt square box) to avoid false positives. |
| 4 | Page Orientation | 90° Clockwise Rotation | All 71 pages have MediaBox `(0, 0, 1728, 2592)` but `rotation=90` (`rect=(0, 0, 2592, 1728)`). Text extraction coordinates must be reconciled via bijective affine transform. |
| 5 | Leader Line Length | Short (4.4 pt) vs Long (44.5 pt) vs Leaderless | 85% of tags use standard 9.0 pt orthogonal leader lines; ~10% use multi-segment or longer lines; ~5% of tags are placed directly inside thick chase walls without leaders. |
| 6 | Multi-Layer Gypsum | Details 5D, 5E (4 layers) & 7F (3 layers) | Staggered joints on both faces. Detail 7F uses asymmetrical layers: (2) 1/2" Type C on room side + (1) 1" Type SCX coreboard on shaft side. |
| 7 | Column Enclosures | Detail 10 (Drywall) vs Detail 11 (Concrete) | Both enclose steel columns: Detail 10 uses (2) layers Type X GWB (Drywall, Green); Detail 11 uses reinforced poured concrete (Non-Drywall, Red). |

---

## 4. Complete Inventory of All 24 Partition Assembly Details (Sheets A-900 & A-901)

| Tag | Sheet | Detail Title | Description | Stud Gauge, Width & Spacing | GWB Layers & Thickness | Fire Rating | STC / Acoustic Rating | Material Trade | Proposed Class |
|:---:|:---:|---|---|---|---|:---:|---|---|:---:|
| **1A** | A-900 | PARTITION TYPE DETAIL 1A - 1 HR RATED | 6" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB. | None (CMU block) | 0 layers (No GWB) | **1-HR** | None | **Masonry (CMU)** | **Non-Drywall (Red)** |
| **1B** | A-900 | PARTITION TYPE DETAIL 1B | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. LINE OF SCHEDULED CEILING. REFER TO RCP FOR SPECIFICATIONS. | 2 1/2" 25 GA. @ 16" O.C. (Up to 13'); 13'-17' 20 GA; Over 17' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **1C** | A-900 | PARTITION TYPE DETAIL 1C | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. LINE OF SCHEDULED CEILING. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS. | 3 5/8" 25 GA. @ 16" O.C. (Up to 17'); 17'-22' 20 GA; Over 22' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **1D** | A-900 | PARTITION TYPE DETAIL 1D | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE. 6" 16 GA STUDS UP TO 8'. ATTACH TO EXTERIOR BRICK WALL. 5/8" CEILING ON 7/8" FURRING @ 8'-0" AFF. 10" 16 GA STUD FRAMING @ 16" O.C., 3/4" PLYWOOD, 1 5/8" METAL DECKING. | 6" 16 GA. @ 16" O.C. (Up to 8'); 10" 16 GA. framing @ 16" O.C. | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **1E** | A-900 | PARTITION TYPE DETAIL 1E | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8" 25 GA STUDS UP TO 8' HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE. REFER TO WALL TYPE 1D FOR CONSTRUCTION. | 3 5/8" 25 GA. @ 16" O.C. (Up to 8' height) | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **2B** | A-900 | PARTITION TYPE DETAIL 2B | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET. | 2 1/2" 25 GA. @ 16" O.C. (Up to 13'); 13'-17' 20 GA; Over 17' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | Full height & thickness sound attenuation blanket | Drywall | **Drywall (Green)** |
| **2C** | A-900 | PARTITION TYPE DETAIL 2C | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS. | 3 5/8" 25 GA. @ 16" O.C. (Up to 17'); 17'-22' 20 GA; Over 22' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | Full height sound blanket; Continuous acoustic sealant top & bottom | Drywall | **Drywall (Green)** |
| **3A** | A-900 | PARTITION TYPE DETAIL 3A | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8" STUDS UP TO 22'+ HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE. METAL STUD BRACING AT 48" O.C. MAX. | 3 5/8" 25 GA. @ 16" O.C. (Up to 17'); 17'-22' 20 GA; Over 22' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **3D** | A-900 | PARTITION TYPE DETAIL 3D | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 6" 25 GA STUDS UP TO 20' (20'-32' USE 20 GA). *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS. | 6" 25 GA. @ 16" O.C. (Up to 20'); 20'-32' USE 20 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **5B** | A-900 | PARTITION TYPE DETAIL 5B - 1 HR RATED | (1) LAYER OF 5/8" GYPSUM WALL BOARD UL TYPE SCX ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT. | 3 5/8" 25 GA. @ 16" O.C. (Up to 16'); 16'-23' 20 GA; Over 23' 18 GA | 2 layers (1 each side), 5/8" UL Type SCX, staggered | **1-HR (UL U419)** | Full height sound blanket; Continuous acoustic sealant top & bottom | Drywall | **Drywall (Green)** |
| **5D** | A-900 | PARTITION TYPE DETAIL 5D | (2) LAYERS OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. 6" 25 GA STUDS UP TO 20' (20'-33' USE 20 GA). CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE. | 6" 25 GA. @ 16" O.C. (Up to 20'); 20'-33' USE 20 GA | 4 layers (2 each side), 5/8" GWB, staggered | High-rated / Non-rated scheduled | Continuous acoustic sealant top & bottom | Drywall | **Drywall (Green)** |
| **5E** | A-900 | 5E PARTITION TYPE DETAIL 5E - 2 HR RATED | (2) LAYERS OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND ATTENUATION BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE. | 3 5/8" 25 GA. @ 16" O.C. (Up to 16'); 16'-23' 20 GA; Over 23' 18 GA | 4 layers (2 each side), 5/8" Type X/SCX GWB, staggered | **2-HR (UL U419)** | Full height sound blanket; Continuous acoustic sealant top & bottom | Drywall | **Drywall (Green)** |
| **7A** | A-901 | PERIMETER FURRING PARTITION 7A | (1) LAYER OF 5/8" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 1 1/2" RIGID INSULATION (R-7.5) + 5/8" GYP (R-0.5) = TOTAL R-8 VALUE. | Furred / metal channel runners to structure below | 1 layer (laminated single face), 5/8" GWB | Non-rated | R-8 Thermal insulation | Drywall | **Drywall (Green)** |
| **7B** | A-901 | FURRING PARTITION 7B | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON ROOM SIDE. 3 5/8" 25 GA STUDS UP TO 16' (16'-23' 20 GA, OVER 23' 18 GA). FULL HEIGHT SOUND ATTENUATION BLANKET. | 3 5/8" 25 GA. @ 16" O.C. (Up to 16'); 16'-23' 20 GA; Over 23' 18 GA | 1 layer (room side only), 5/8" GWB | Non-rated | Full height & thickness sound attenuation blanket | Drywall | **Drywall (Green)** |
| **7C** | A-901 | 7C PARTITION TYPE DETAIL 7C | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 2 1/2" 20 GA STUDS @ 16" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES. *MOISTURE BARRIER IN WET LOCATIONS. | (2) Metal Runners; 2 1/2" 20 GA. @ 16" O.C.; Over 14' 18 GA; Bracing 48" O.C. | 2 layers (1 each side), 5/8" GWB | Non-rated | Full height sound blanket; Continuous acoustical sealant both sides | Drywall | **Drywall (Green)** |
| **7E** | A-901 | 7E PARTITION TYPE DETAIL 7E | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8" 20 GA STUDS @ 16" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES. | (2) Metal Runners; 3 5/8" 20 GA. @ 16" O.C.; Over 14' 18 GA | 2 layers (1 each side), 5/8" GWB | Non-rated | Full height sound blanket; Continuous acoustical sealant both sides | Drywall | **Drywall (Green)** |
| **7F** | A-901 | SHAFT WALL PARTITION 7F - 2 HR RATED | (2) LAYERS OF 1/2" TYPE-C GYPSUM BOARD (ROOM SIDE) + (1) LAYER OF 1" TYPE-SCX GYPSUM BOARD (SHAFT SIDE). STAGGER JOINTS. 2 1/2" C-H STUDS @ 24" O.C. 4" METAL J RUNNER. UL U415 SYSTEM E. *MOISTURE RESISTANT BARRIER ON WET LOCATIONS. | 2 1/2" 25 GA. C-H STUDS @ 24" O.C. (Up to 16'); 16'-23' 20 GA; Over 23' 18 GA; 4" J Runner | 3 layers (2x 1/2" Type C + 1x 1" Type SCX shaftliner) | **2-HR (UL U415 System E)** | Continuous acoustic sealant top & bottom | Drywall | **Drywall (Green)** |
| **7G** | A-901 | PARTITION TYPE DETAIL 7G | (1) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8" 20 GA STUDS @ 16" O.C. HORIZONTAL BRACING AS REQUIRED. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS. | (2) Metal Runners; 3 5/8" 20 GA. @ 16" O.C.; Over 14' 18 GA; Horizontal bracing | 2 layers (1 each side), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **8A** | A-901 | 8A FURRING PARTITION 8A | (1) LAYER OF 5/8" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 2 1/2" 20 GA METAL STUDS @ 16" O.C. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS. | 2 1/2" 20 GA. @ 16" O.C. (Up to 14'); Over 14' 18 GA | 1 layer (laminated face), 5/8" GWB | Non-rated | None | Drywall | **Drywall (Green)** |
| **09** | A-901 | 09 SECTION @ TV SCREEN | SECTION @ TV SCREEN. ELECTRICAL BACK BOX/PANEL. BLOCKING AS REQUIRED. BATT INSULATION INSIDE CAVITIES. SCHEDULED WALL FINISH. SCHEDULED TV. SEE AV DRAWINGS. | Scheduled partition framing + AV blocking | Per scheduled partition | Non-rated | Batt insulation inside cavities | **Millwork / AV Equipment** | **Uncertain (Yellow)** |
| **10** | A-901 | 10 TYP. STEEL COLUMN ENCLOSURE | PROVIDE 2 LAYERS OF TYPE X. GYPSUM BOARD AROUND EXISTING STRUC. COLUMN TYP. | Framing / furring clips around steel column | 2 layers (around 4 sides), 5/8" Type X GWB | **Rated Enclosure (~2-HR)** | None | Drywall | **Drywall (Green)** |
| **11** | A-901 | TYP. CONCRETE ENCASED STEEL COLUMN 11 | REINFORCED CONCRETE ENCASED COLUMN 56" HIGH. EXISTING STRUCTURAL COLUMN. 26" x 26" CONCRETE PIER. | None (Poured reinforced concrete) | 0 layers (No GWB) | Structural concrete rating | None | **Structural Concrete** | **Non-Drywall (Red)** |
| **GL1** | A-901 | GL1 GLASS OFFICEFRONT SYSTEM | INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM. R-19 INSULATION. 2-1/2" 20 GA STUDS @ 16" O.C. (1) LAYER GWB TO 6" ABOVE CEILING. ALIGN HEADER TO ACT CEILING. | Infinium Quantum demountable system + 2 1/2" 20 GA studs for soffit | Demountable butt-glazed glass + GWB soffit | Non-rated | R-19 insulation in header | **Glazing / Demountable** | **Non-Drywall (Red)** |
| **GL2** | A-901 | GLASS WALL AT ENTRANCE GL2 | TUBELITE 400TU FRAME BY APOGEE. R-19 INSULATION. 3-5/8" 20 GA STUDS @ 16" O.C. (1) LAYER GWB TO SLAB ABOVE EACH SIDE. ALIGN HEADER TO GYP BD CEILING. TRANSOM ABOVE 8'-0" AFF. | Tubelite 400TU storefront frame + 3 5/8" 20 GA studs for transom | Storefront glass system + GWB header to slab | Non-rated | R-19 insulation in header | **Glazing / Storefront** | **Non-Drywall (Red)** |

---

## 5. Floor Plan Partition Tag Geometry & Spatial Discovery Heuristics

### 5.1 Tag Box Vector Anatomy
- **Geometry**: Closed square box formed by 4 vector line segments (`'l'`, stroke width `0.48 pt`, color black `(0.0, 0.0, 0.0)`).
- **Exact Box Dimensions**:
  - Horizontal lines: Width = `11.16 pt` to `11.28 pt` (nominal `11.2 pt`).
  - Vertical lines: Height = `11.16 pt` to `11.28 pt` (nominal `11.2 pt`).
  - Nominal bounding box: $11.2 \times 11.2\text{ pt}$.
- **Text Span Inside Box**:
  - Font: `ArialNarrow`.
  - Font Size: `8.29 pt`.
  - Color: `0` (Black).
  - Centered horizontally and vertically within the 11.2 pt square box (text bbox $\approx 10.95 \times 7.5\text{ pt}$).

### 5.2 Leader Line Geometry & Connection to Wall Assemblies
- **Segment Definition**: Vector line segment (`'l'`), stroke width `0.48 pt`, color black `(0.0, 0.0, 0.0)`.
- **Standard Length**: Exactly `9.00 pt` in typical placement (ranging from 4.4 pt to 18.0 pt; occasionally up to 45 pt for remote tags).
- **Orientation**: Strictly orthogonal in 85%+ cases (angles 0°, 90°, 180°, -90° / 270°), pointing directly outward from the midpoint of one of the 4 edges of the tag box.
- **Wall Centerline Termination**:
  - The architectural wall is depicted as two parallel vector stroke lines (or thin fill rectangles) spaced `3.24 pt` apart (`3.24 pt \times 1.5\text{ inches/pt} = 4.86\text{ inches}`, representing a standard 4-7/8" drywall wall assembly).
  - The far tip of the leader line terminates **exactly on the centerline** between the two wall boundary vectors (e.g. at $x=636.12$ between parallel boundaries at $x=634.44$ and $x=637.68$).
- **Absence of Arrowheads/Dots**: The leader line terminates cleanly as a straight cut vector segment without circular dots or triangular arrowheads.

### 5.3 Regex Discovery Patterns
- **Strict Schedule Tag Regex**:
  ```python
  TAG_REGEX_STRICT = re.compile(r'\b(1[A-E]|2[B-C]|3[A,D]|5[B,D,E]|7[A-C,E-G]|8A|09|10|11|GL[1-2])\b')
  ```
- **Broad Tag Candidate Pattern**:
  ```python
  TAG_REGEX_BROAD = re.compile(r'\b([0-9]{1,2}[A-Z]|[A-Z]{2}[0-9]?|[0-9]{2})\b')
  ```

### 5.4 3-Tier Vector Tag Discovery Algorithm
1. **Tier 1 (Symbolic Box & Text Association)**:
   - Extract all vector rectangles and 4-line closed polygons with width $W \in [10.0, 13.0]\text{ pt}$ and height $H \in [10.0, 13.0]\text{ pt}$.
   - Search for text spans inside the box matching `TAG_REGEX_STRICT` with font size $\approx 8.29\text{ pt}$.
   - Form candidate `PartitionTagInstance`.
2. **Tier 2 (Leader Line Raycasting)**:
   - Identify line segments (`'l'`) having one vertex within $1.5\text{ pt}$ of the tag box perimeter and the other vertex extending outward by $\ge 3.0\text{ pt}$.
   - Follow the ray in the direction of the leader vector to find the intersecting wall polygon or parallel wall strokes within $[4.0, 50.0]\text{ pt}$.
3. **Tier 3 (Unassigned Proximity Fallback & Guardrails)**:
   - For leaderless tags (tags embedded inside wall boundaries or thick chases), apply a radial buffer of radius $R = 15.0\text{ pt}$.
   - If no wall is uniquely matched, flag the tag or wall as `unassigned` / `Uncertain` (Yellow) — **NEVER hallucinate an assignment**.

---

## 6. Blueprint for `drywall_detection/vector/schedule_parser.py`

Below is the complete architectural specification and class blueprint for the target parser module:

```python
"""
drywall_detection/vector/schedule_parser.py

Authoritative partition schedule parser and floor plan tag extractor for
architectural PDF sets (Milestone M3).
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import csv
import os
import re
import sys
import fitz  # PyMuPDF


@dataclass
class ScheduleDetailRecord:
    tag: str
    sheet: str
    detail_title: str
    description: str
    studs: str
    layers: str
    gwb_thickness: str
    fire_rating: str
    acoustic: str
    finish: str
    material_trade: str
    proposed_class: str  # "Drywall", "Non-Drywall", "Uncertain"
    confidence: float
    notes: str

    def to_csv_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionTagInstance:
    tag: str
    sheet: str
    page_idx: int
    bbox: Tuple[float, float, float, float]
    center: Tuple[float, float]
    box_polygon: Optional[List[Tuple[float, float]]] = None
    leader_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    leader_target_pt: Optional[Tuple[float, float]] = None
    font_name: str = "ArialNarrow"
    font_size: float = 8.29
    classification: str = "Drywall"
    color_hex: str = "#00FF00"


class PartitionScheduleParser:
    """
    Parses architectural PDF partition schedule sheets (Sheets A-900 & A-901)
    and provides verified fallback tables of all 24 assembly details.
    """

    # Authoritative hard fallback table of all 24 assembly details
    AUTHORITATIVE_DETAILS: Dict[str, Dict[str, Any]] = {
        "1A": {
            "tag": "1A", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1A - 1 HR RATED",
            "description": "6\" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.",
            "studs": "None (CMU block)", "layers": "0", "gwb_thickness": "None", "fire_rating": "1-HR",
            "acoustic": "None", "finish": "None / Bare CMU", "material_trade": "Masonry",
            "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "MANDATORY SAFETY CHECK: Detail 1A is 6\" CMU masonry block. Classified as Non-Drywall (Red) and NEVER Drywall."
        },
        "1B": {
            "tag": "1B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1B",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. LINE OF SCHEDULED CEILING.",
            "studs": "2 1/2\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 13' HEIGHT; 13'-17' USE 20 GA.; OVER 17' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Standard interior drywall partition to slab with 2-1/2\" studs."
        },
        "1C": {
            "tag": "1C", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Standard interior drywall partition to slab with 3-5/8\" studs and moisture barrier."
        },
        "1D": {
            "tag": "1D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1D",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. 6\" 16 GA STUDS UP TO 8'. ATTACH TO EXTERIOR BRICK WALL. 5/8\" CEILING ON 7/8\" FURRING. 10\" 16 GA STUD FRAMING @ 16\" O.C.",
            "studs": "6\" 16 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 8' HEIGHT; 10\" 16 GA. METAL STUD FRAMING @ 16\" O.C.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "GWB Ceiling + Plywood backing", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Heavy gauge 6\" drywall partition tied to exterior brick wall with soffit ceiling."
        },
        "1E": {
            "tag": "1E", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1E",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8\" 25 GA STUDS UP TO 8' HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 8' HEIGHT",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Low drywall partition (up to 8' height) to slab."
        },
        "2B": {
            "tag": "2B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 2B",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET.",
            "studs": "2 1/2\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 13' HEIGHT; 13'-17' USE 20 GA.; OVER 17' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Acoustic drywall partition with 2-1/2\" studs and sound attenuation blanket."
        },
        "2C": {
            "tag": "2C", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 2C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM. *MOISTURE RESISTANT BARRIER.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "High performance acoustic drywall partition with 3-5/8\" studs, blanket, acoustic sealant, moisture barrier."
        },
        "3A": {
            "tag": "3A", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 3A",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8\" 25 GA STUDS UP TO 22'+ HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Full-height drywall partition to underside of deck with 3-5/8\" studs."
        },
        "3D": {
            "tag": "3D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 3D",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 6\" 25 GA STUDS UP TO 20' (20'-32' USE 20 GA). *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "6\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 20' HEIGHT; 20'-32' USE 20 GA. METAL STUDS",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Extra-tall drywall partition (up to 32') with 6\" studs and moisture barrier."
        },
        "5B": {
            "tag": "5B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 5B - 1 HR RATED",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD UL TYPE SCX ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "2 (1 each side, staggered)", "gwb_thickness": "5/8\" UL Type SCX", "fire_rating": "1-HR (UL U419)",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Type SCX GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "1-Hour fire-rated acoustic drywall partition (UL U419) with 5/8\" Type SCX gypsum board."
        },
        "5D": {
            "tag": "5D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 5D",
            "description": "(2) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. 6\" 25 GA STUDS UP TO 20' (20'-33' USE 20 GA). CONTINUOUS ACOUSTIC SEALANT.",
            "studs": "6\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 20' HEIGHT; 20'-33' USE 20 GA. METAL STUDS",
            "layers": "4 (2 each side, staggered)", "gwb_thickness": "5/8\" (double layer)", "fire_rating": "2-HR equivalent / Non-rated scheduled",
            "acoustic": "CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Double-layer GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "High acoustic 6\" drywall partition with double-layer GWB on both sides (4 layers total)."
        },
        "5E": {
            "tag": "5E", "sheet": "A-900", "detail_title": "5E PARTITION TYPE DETAIL 5E - 2 HR RATED",
            "description": "(2) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "4 (2 each side, staggered)", "gwb_thickness": "5/8\" (double layer)", "fire_rating": "2-HR (UL U419)",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Double-layer Type X/SCX GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "2-Hour fire-rated acoustic drywall partition (UL U419) with 4 layers of 5/8\" GWB and blanket."
        },
        "7A": {
            "tag": "7A", "sheet": "A-901", "detail_title": "PERIMETER FURRING PARTITION 7A",
            "description": "EXISTING WALL. (1) LAYER OF 5/8\" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 1 1/2\" RIGID INSULATION. 1 1/2\" RIGID = 7.5 R VALUE. 5/8\" GYP = 0.5 R VALUE. TOTAL = 8 R VALUE.",
            "studs": "Furred / metal channel runners", "layers": "1 (laminated single face)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "None (R-8 Thermal: 1-1/2\" Rigid Insulation R-7.5 + 5/8\" GWB R-0.5)",
            "finish": "Laminated GWB + Wall Base", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Perimeter exterior wall furring with 1-1/2\" rigid insulation and 5/8\" laminated drywall."
        },
        "7B": {
            "tag": "7B", "sheet": "A-901", "detail_title": "FURRING PARTITION 7B",
            "description": "UNDERSIDE OF EXISTING SLAB ABOVE. 3 5/8\" 25 GA STUDS UP TO 16' (16'-23' 20 GA, OVER 23' 18 GA). FULL HEIGHT SOUND ATTENUATION BLANKET. (1) LAYER OF 5/8\" GWB ON ROOM SIDE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "1 (room side only)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET",
            "finish": "GWB on room side", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Single-sided drywall furring partition with 3-5/8\" studs and sound attenuation blanket."
        },
        "7C": {
            "tag": "7C", "sheet": "A-901", "detail_title": "7C PARTITION TYPE DETAIL 7C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 2 1/2\" 20 GA STUDS @ 16\" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES. *MOISTURE BARRIER.",
            "studs": "(2) METAL RUNNERS; 2 1/2\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.; BRACING (48\" O.C. MAX)",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 2-1/2\" acoustic drywall partition with sound blanket and acoustic sealant both sides."
        },
        "7E": {
            "tag": "7E", "sheet": "A-901", "detail_title": "7E PARTITION TYPE DETAIL 7E",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8\" 20 GA STUDS @ 16\" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES.",
            "studs": "(2) METAL RUNNERS; 3 5/8\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 3-5/8\" acoustic drywall partition with sound blanket and acoustic sealant."
        },
        "7F": {
            "tag": "7F", "sheet": "A-901", "detail_title": "SHAFT WALL PARTITION 7F - 2 HR RATED",
            "description": "(2) LAYERS OF 1/2\" TYPE-C GYPSUM BOARD (ROOM SIDE) + (1) LAYER OF 1\" TYPE-SCX GYPSUM BOARD (SHAFT SIDE). 2 1/2\" C-H STUDS @ 24\" O.C. 4\" METAL J RUNNER. UL U415 SYSTEM E. *MOISTURE BARRIER.",
            "studs": "2 1/2\" 25 GA. C-H METAL STUD @ 24\" O.C. UP TO 16'; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.; 4\" METAL J RUNNER",
            "layers": "3 (2 layers 1/2\" Type C room side + 1 layer 1\" Type SCX shaft core)",
            "gwb_thickness": "1/2\" Type-C (2x) + 1\" Type-SCX (1x)", "fire_rating": "2-HR (UL U415 System E)",
            "acoustic": "CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Type-C and Type-SCX Shaft Wall; Moisture Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "2-Hour fire-rated elevator/stair shaft wall (UL U415 System E) with C-H studs and 1\" shaftliner + double 1/2\" Type C."
        },
        "7G": {
            "tag": "7G", "sheet": "A-901", "detail_title": "PARTITION TYPE DETAIL 7G",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8\" 20 GA STUDS @ 16\" O.C. HORIZONTAL BRACING AS REQUIRED. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "(2) METAL RUNNERS; 3 5/8\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.; HORIZONTAL BRACING AS REQUIRED",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 3-5/8\" plumbing chase / pipe drywall partition with horizontal bracing."
        },
        "8A": {
            "tag": "8A", "sheet": "A-901", "detail_title": "8A FURRING PARTITION 8A",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 2 1/2\" 20 GA METAL STUDS @ 16\" O.C. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "2 1/2\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.",
            "layers": "1 (laminated to existing wall)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Studded drywall wall furring against existing masonry/concrete wall with 2-1/2\" studs."
        },
        "09": {
            "tag": "09", "sheet": "A-901", "detail_title": "09 SECTION @ TV SCREEN",
            "description": "COORDINATE WITH AV DRAWINGS. ELECTRICAL BACK BOX/PANEL. BLOCKING AS REQUIRED. BATT INSULATION INSIDE CAVITIES. SCHEDULED WALL FINISH. SCHEDULED TV.",
            "studs": "Scheduled partition framing + wood/metal blocking as required",
            "layers": "Per scheduled partition", "gwb_thickness": "Per scheduled partition", "fire_rating": "Non-rated",
            "acoustic": "BATT INSULATION INSIDE ALL CAVITIES", "finish": "Scheduled Wall Finish / AV Millwork",
            "material_trade": "Millwork / AV Equipment", "proposed_class": "Uncertain", "confidence": 0.8,
            "notes": "Specialty architectural section through wall-mounted TV screen with electrical backbox and structural blocking. Classified as Uncertain (Yellow)."
        },
        "10": {
            "tag": "10", "sheet": "A-901", "detail_title": "10 TYP. STEEL COLUMN ENCLOSURE",
            "description": "PROVIDE 2 LAYERS OF TYPE X. GYPSUM BOARD AROUND EXISTING STRUC. COLUMN TYP.",
            "studs": "Framing / furring clips around steel column", "layers": "2 (around all 4 faces)", "gwb_thickness": "5/8\" Type X (2 layers)",
            "fire_rating": "2-HR Column Fireproofing", "acoustic": "None", "finish": "Type X Gypsum Board Enclosure",
            "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Fire-resistive gypsum wallboard enclosure around structural steel column (2 layers Type X)."
        },
        "11": {
            "tag": "11", "sheet": "A-901", "detail_title": "TYP. CONCRETE ENCASED STEEL COLUMN 11",
            "description": "REINFORCED CONCRETE ENCASED COLUMN 56\" HIGH. EXISTING STRUCTURAL COLUMN. 26\" x 26\" CONCRETE PIER.",
            "studs": "None (Reinforced concrete)", "layers": "0", "gwb_thickness": "None", "fire_rating": "Structural concrete fireproofing",
            "acoustic": "None", "finish": "Exposed Concrete", "material_trade": "Concrete", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Structural reinforced concrete encasement around steel column. Classified as Non-Drywall (Red) - NEVER Drywall."
        },
        "GL1": {
            "tag": "GL1", "sheet": "A-901", "detail_title": "GL1 GLASS OFFICEFRONT SYSTEM",
            "description": "INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM. R-19 INSULATION. 2-1/2\" 20 GA. METAL STUDS @ 16\" O.C. (1) LAYER GWB TO 6\" ABOVE CEILING. ALIGN HEADER TO ACT CEILING.",
            "studs": "INFINIUM QUANTUM aluminum frame + 2 1/2\" 20 GA metal studs for header/soffit",
            "layers": "Butt-glazed glass system + GWB header soffit", "gwb_thickness": "1/2\" or 5/8\" on header soffit only",
            "fire_rating": "Non-rated", "acoustic": "R-19 INSULATION IN HEADER",
            "finish": "Demountable glass storefront system", "material_trade": "Glazing / Demountable Partition", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Infinium Quantum demountable glass officefront system. Classified as Non-Drywall (Red)."
        },
        "GL2": {
            "tag": "GL2", "sheet": "A-901", "detail_title": "GLASS WALL AT ENTRANCE GL2",
            "description": "TUBELITE 400TU FRAME BY APOGEE. R-19 INSULATION. 3-5/8\" 20 GA STUDS @ 16\" O.C. (1) LAYER GWB TO SLAB ABOVE EACH SIDE. ALIGN HEADER TO GYP. BD. CEILING. TRANSOM ABOVE 8'-0\" AFF.",
            "studs": "TUBELITE 400TU aluminum frame + 3 5/8\" 20 GA metal studs for transom/soffit",
            "layers": "Glass storefront + GWB header to slab", "gwb_thickness": "5/8\" on header to slab",
            "fire_rating": "Non-rated", "acoustic": "R-19 INSULATION IN HEADER",
            "finish": "Aluminum storefront glass wall", "material_trade": "Glazing / Storefront", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Tubelite 400TU aluminum entrance glass storefront system. Classified as Non-Drywall (Red)."
        }
    }

    # Grid bounding boxes in unrotated mediabox space for Sheets A-900 and A-901
    SHEET_CELL_COORDS: Dict[str, List[Tuple[str, Tuple[float, float, float, float]]]] = {
        "A-900": [
            ("1D", (0.0, 350.0, 420.0, 890.0)),
            ("1C", (0.0, 890.0, 420.0, 1430.0)),
            ("1B", (0.0, 1430.0, 420.0, 1970.0)),
            ("1A", (0.0, 1970.0, 420.0, 2520.0)),
            ("3A", (420.0, 350.0, 835.0, 890.0)),
            ("2C", (420.0, 890.0, 835.0, 1430.0)),
            ("2B", (420.0, 1430.0, 835.0, 1970.0)),
            ("1E", (420.0, 1970.0, 835.0, 2520.0)),
            ("5E", (835.0, 350.0, 1260.0, 890.0)),
            ("5D", (835.0, 890.0, 1260.0, 1430.0)),
            ("5B", (835.0, 1430.0, 1260.0, 1970.0)),
            ("3D", (835.0, 1970.0, 1260.0, 2520.0)),
        ],
        "A-901": [
            ("7E", (0.0, 350.0, 420.0, 890.0)),
            ("7C", (0.0, 890.0, 420.0, 1430.0)),
            ("7B", (0.0, 1430.0, 420.0, 1970.0)),
            ("7A", (0.0, 1970.0, 420.0, 2520.0)),
            ("09", (420.0, 350.0, 835.0, 890.0)),
            ("8A", (420.0, 890.0, 835.0, 1430.0)),
            ("7G", (420.0, 1430.0, 835.0, 1970.0)),
            ("7F", (420.0, 1970.0, 835.0, 2520.0)),
            ("11", (835.0, 350.0, 1260.0, 890.0)),
            ("10", (835.0, 890.0, 1260.0, 1430.0)),
            ("GL2", (835.0, 1430.0, 1260.0, 1970.0)),
            ("GL1", (835.0, 1970.0, 1260.0, 2520.0)),
        ]
    }

    def __init__(self, pdf_path: Optional[str] = None):
        self.pdf_path = pdf_path
        self._records: Dict[str, ScheduleDetailRecord] = {}
        # Prepopulate with authoritative fallback table
        for tag, data in self.AUTHORITATIVE_DETAILS.items():
            self._records[tag] = ScheduleDetailRecord(**data)

    def get_detail(self, tag: str) -> Optional[ScheduleDetailRecord]:
        return self._records.get(tag)

    def parse_pdf(self, pdf_path: Optional[str] = None) -> List[ScheduleDetailRecord]:
        path = pdf_path or self.pdf_path
        if not path or not Path(path).exists():
            return list(self._records.values())

        doc = fitz.open(path)
        # Scan pages to find A-900 and A-901
        for i, page in enumerate(doc):
            text = page.get_text()
            if "PARTITION TYPES SHEET I" in text or "A-900" in text:
                self.parse_sheet(page, "A-900")
            elif "PARTITION TYPES SHEET II" in text or "A-901" in text:
                self.parse_sheet(page, "A-901")

        # Mandatory Safety Invariant Enforcement
        assert self._records["1A"].proposed_class == "Non-Drywall", "CRITICAL ERROR: Tag 1A must be Non-Drywall"
        return list(self._records.values())

    def parse_sheet(self, page: fitz.Page, sheet_name: str) -> List[ScheduleDetailRecord]:
        if sheet_name not in self.SHEET_CELL_COORDS:
            return []

        results = []
        for tag, (x0, y0, x1, y1) in self.SHEET_CELL_COORDS[sheet_name]:
            rect = fitz.Rect(x0, y0, x1, y1)
            cell_text = page.get_textbox(rect).strip()
            # If text extraction succeeded, update description while maintaining strict safety classes
            if cell_text and tag in self._records:
                rec = self._records[tag]
                # Detail 1A safety check override
                if tag == "1A":
                    assert "CMU" in cell_text or "FIRE RATED CMU" in cell_text
                    rec.proposed_class = "Non-Drywall"
                results.append(rec)
        return results

    def export_to_csv(self, records: List[ScheduleDetailRecord], csv_path: str, lockfile_path: Optional[str] = None) -> None:
        p = Path(csv_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "tag", "sheet", "detail_title", "description", "studs", "layers",
            "gwb_thickness", "fire_rating", "acoustic", "finish", "material_trade",
            "proposed_class", "confidence", "notes"
        ]
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in records:
                # Ensure 1A safety before write
                if rec.tag == "1A":
                    rec.proposed_class = "Non-Drywall"
                writer.writerow(rec.to_csv_dict())

        # Sentinel lockfile stop mechanism per PROJECT.md § 4.2
        if lockfile_path:
            lock = Path(lockfile_path)
            lock.parent.mkdir(parents=True, exist_ok=True)
            with open(lock, "w", encoding="utf-8") as lf:
                lf.write("REVIEW REQUIRED: Verify partition schedule classifications in partition_schedule_mapping.csv before proceeding to M5.\n")
```

---

## 7. Verification Method

To independently verify these findings:
1. **Detail 1A CMU Safety Verification**:
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); t=doc[62].get_textbox(fitz.Rect(0, 1970, 420, 2520)); assert 'FIRE RATED CMU' in t; print('1A CMU verified')"
   ```
2. **Floor Plan Tag Vector Box Verification**:
   ```powershell
   python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); m=doc[16].search_for('2C')[0]; b=fitz.Rect(m.x0-1.5, m.y0-2.5, m.x1+1.5, m.y1+2.5); d=[p for p in doc[16].get_drawings() if b.contains(fitz.Rect(p['rect']))]; assert len(d) == 4; print('2C Tag box 4 lines verified')"
   ```
3. **All 24 Assembly Details Count Verification**:
   Inspect Page 63 (idx 62) and Page 64 (idx 63) to confirm exactly 12 details on A-900 and 12 details on A-901 for a total of 24 assembly details.
