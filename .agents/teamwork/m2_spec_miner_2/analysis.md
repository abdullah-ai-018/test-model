# Partition Schedule & Taxonomy Specification Mining Report

- **Author**: `m2_spec_miner_2` (Specification Miner)
- **Role**: Partition Schedule & Taxonomy Specialist
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_spec_miner_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Authoritative Reference**: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
- **Target Sheets**: Sheet A-900 (p.63 / index 62), Sheet A-901 (p.64 / index 63), Sheet A-902 (p.65 / index 64)

---

## 1. Executive Summary & Objectives

The primary mission of `m2_spec_miner_2` is to probe the authoritative reference drawings from the MTA 99th Street - Phase 2 Interior Project (Contract `C-48526`, TPG Architecture LLP, Autodesk Revit 2025, 95% Construction Documents) to establish the architectural ground truth for drywall detection and wall classification.

This investigation delivers:
1. **Authoritative Sheet & Coordinate Mining**: Direct extraction of Sheets A-900 (Page 63), A-901 (Page 64), and A-902 (Page 65), verifying the ARCH D dimensions ($36\text{ in} \times 24\text{ in}$, $2592 \times 1728\text{ pt}$), clockwise $90^\circ$ page rotation, and vertical text flow.
2. **Exhaustive Assembly Transcription**: Verbatim transcription of all **24 partition assembly details** across Sheets A-900 and A-901, detailing stud sizes, steel gauges, on-center spacing, maximum height limits, gypsum wallboard (GWB) layers and thickness, UL fire-resistance ratings, sound attenuation blankets (SAB), acoustic sealant, moisture barriers, and trade CSI divisions.
3. **Rigorous 4-Class Taxonomy Mapping**: Unambiguous mapping of every assembly into the 4-class taxonomy:
   - **Class 0: Background** (White `#FFFFFF`)
   - **Class 1: Drywall** (Green `#00FF00`): 18 verified gypsum assemblies (1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, Col 10, gypsum soffits)
   - **Class 2: Non-Drywall** (Red `#FF0000`): Masonry block (Tag 1A: 6" CMU - **Mandatory Zero-Tolerance Drywall Veto**), glass officefront systems (GL1, GL2), modular demountable privacy walls (PW), operable acoustic folding partitions (FWP-2 / Modernfold), and reinforced concrete encasements/infill (Col 11, Key Note 1, Key Note 18)
   - **Class 3: Uncertain / Manual Review** (Yellow `#FFFF00`): Tag 09 (specialty TV screen recessed millwork/blocking), untagged wall runs, ambiguous junctions, and generic CAD walls lacking partition schedules
4. **CSV Export Specification & Review Stopping Protocol**: Strict contract definition for `drywall_detection/data/partition_schedule_mapping.csv`, accompanied by a human-in-the-loop review stopping mechanism using sentinel file `drywall_detection/data/REVIEW_REQUIRED.lock` and CLI exit code `2`.
5. **Architectural Blueprint for `drywall_detection/vector/schedule_parser.py`**: Production-ready software design featuring coordinate-aware grid partitioning ($3 \times 4$ cells per sheet), word-level line grouping, regular expression field parsers, safety validation rules, and export/lock orchestration.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Drawing Spec | Rotated Sheet Coordinate Resolution | Resolves visual landscape coordinates ($2592 \times 1728\text{ pt}$) vs unrotated mediabox ($1728 \times 2592\text{ pt}$) with $90^\circ$ clockwise page rotation. | `fitz.Page` | Normalization transform $(x_{vis}, y_{vis}) = (2592 - y_{raw}, x_{raw})$ | Raises `CoordinateShearError` if unrotated mediabox is mixed with visual space. | A-900 / A-901 `page.rect` & `page.rotation` inspection |
| 2 | Drawing Spec | Partition Sheet Grid Partitioning | Partitions drawing sheets A-900 and A-901 into a deterministic $3 \times 4$ cell spatial bounding box grid (12 details per sheet). | `page: fitz.Page` | 12 `ScheduleCellBBox` rectangles per sheet | Clamps out-of-bound coordinates to sheet margins. | Empirical cell analysis on A-900 & A-901 |
| 3 | Text Extraction | Coordinate-Aware Line Reconstruction | Reconstructs natural line reading order by clustering PyMuPDF word tokens by common $x_0$ coordinates and ordering by $y_0$ descending (accommodating $90^\circ$ text rotation). | `List[fitz_word]` within cell bbox | `List[str]` clean textual lines in natural reading order | Fallback to PyMuPDF block order if clustering variance exceeds tolerance. | Empirical word-coordinate profiling on A-901 Cell 7F |
| 4 | Schedule Parsing | Partition Tag & Header Extraction | Identifies primary assembly tag (e.g. `1A`, `1C`, `5E`, `7F`, `GL1`, `10`) and view title via regex matching against detail headers. | Cell text lines | `tag: str`, `detail_title: str`, `scale: str` | Raises `AssemblyHeaderNotFoundError` if tag cannot be parsed from detail title. | Header inspection across all 24 cells |
| 5 | Schedule Parsing | Metal Stud & Framing Specification Extraction | Extracts stud depth ($2\text{ }1/2\text{ in}$, $3\text{ }5/8\text{ in}$, $6\text{ in}$, $10\text{ in}$), gauge ($25\text{ GA}$, $20\text{ GA}$, $18\text{ GA}$, $16\text{ GA}$), on-center spacing ($16\text{ in}$, $24\text{ in}$), and height-gauge step rules. | Cell text lines | `stud_size`, `gauge`, `spacing_oc`, `max_height`, `step_rules` | Returns `None` for solid masonry (1A) or direct laminate (7A, 8A). | Regex parsing of stud callouts across A-900/A-901 |
| 6 | Schedule Parsing | Gypsum Board Layers & Thickness Extraction | Extracts GWB thickness ($5/8\text{ in}$, $1/2\text{ in}$, $1\text{ in}$), layer count per face, board types (Type X, Type C, Type SCX shaftliner), and lamination methods. | Cell text lines | `layers_per_face`, `total_layers`, `gwb_thickness`, `gwb_type` | Returns `layers=0` and `thickness=None` for non-gypsum assemblies (1A CMU, GL1 glass). | Line parsing of gypsum callouts |
| 7 | Schedule Parsing | Fire Resistance Rating Extraction | Identifies explicit UL fire-resistance ratings (`1-Hour`, `2-Hour`) and specific UL design numbers (`UL U419`, `UL U415 System E`). | Cell text lines | `fire_rating: Optional[str]`, `ul_design: Optional[str]` | Defaults to `"Non-Rated"` if no fire rating callout is present. | Regex matching on `HR RATED`, `UL U419`, `UL U415` |
| 8 | Schedule Parsing | Acoustic & STC Specification Extraction | Detects presence of Sound Attenuation Blankets (SAB), full height/thickness requirements, and continuous acoustic sealant top/bottom both sides. | Cell text lines | `has_sab: bool`, `acoustic_sealant: bool`, `stc_estimate: Optional[str]` | Defaults to `has_sab=False`, `acoustic_sealant=False`. | Text matching on `SOUND ATTENUATION BLANKET` & `ACOUSTIC SEALANT` |
| 9 | Schedule Parsing | Finish & Moisture Barrier Extraction | Detects moisture-resistant barrier requirements in wet locations, wall base specifications, and paint/drywall finishes. | Cell text lines | `moisture_resistant: bool`, `finish_notes: str` | Defaults to standard drywall finish. | Text matching on `*MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS` |
| 10 | Taxonomy | 4-Class Semantic Label Assignment | Maps parsed assembly into strictly one of 4 classes: Background (0), Drywall (1), Non-Drywall (2), Uncertain (3) based on verified material trade. | `PartitionAssembly` | `proposed_class: int`, `confidence: float`, `color_hex: str` | Unmatched or contradictory assemblies assigned Class 3 (Uncertain). | Material classification rules |
| 11 | Taxonomy Safety | Tag 1A CMU Non-Drywall Safety Veto | Hardcoded safety override that unconditionally forces Tag 1A (6" CMU Masonry Block) to Class 2 (Non-Drywall, Red), preventing catastrophic misclassification. | `assembly.tag == "1A"` | `proposed_class = 2`, `confidence = 1.0` | Throws `DrywallIntegrityViolation` if any rule attempts to map Tag 1A to Class 1. | Project Integrity Rule 3 |
| 12 | Export & Review | CSV Tabular Export | Serializes all 24 parsed assemblies into standardized CSV format (`partition_schedule_mapping.csv`) with 14 mandatory columns. | `List[PartitionAssembly]` | Written CSV file with exact headers | Raises `CSVExportError` if write fails or required columns are omitted. | PROJECT.md § 4.2 |
| 13 | Export & Review | Review Stopping Sentinel Protocol | Generates `REVIEW_REQUIRED.lock` sentinel file containing review metadata and terminates execution with exit code `2`. | Parsed assemblies, output CSV path | `drywall_detection/data/REVIEW_REQUIRED.lock`, exit code `2` | Prevents automated execution from continuing without human review. | PROJECT.md § 4.2 / Milestone M3 |
| 14 | Export & Review | Approved CSV Handshake Verification | Verifies existence and integrity of `partition_schedule_mapping.approved.csv` before allowing downstream M5 drywall classification. | `approved_csv_path: Path` | Validated approval status | Raises `ReviewRequiredError` if approved CSV is absent or lockfile remains present. | Pipeline safety contract |
| 15 | Supplementary | Operable Partition (FWP-2) Extraction | Probes Sheet A-902 (Wall Details I) to extract Modernfold Acousti-Seal Legacy paired panel operable partition specifications. | Sheet A-902 (p.65) | `FWP-2` assembly record (Class 2 Non-Drywall) | Classified as Class 2; RCP gypsum soffit noted separately. | Sheet A-902 inspection |
| 16 | Supplementary | Demountable Privacy Wall (PW) Extraction | Extracts Steelcase demountable modular privacy wall specifications from construction floor plans A-100 through A-104. | Floor Plans A-100 to A-104 | `PW` assembly record (Class 2 Non-Drywall) | Classified as Class 2; demountable furniture system. | Floor plan text layer inspection |
| 17 | Supplementary | Concrete Column Jacket & Infill Extraction | Extracts reinforced concrete column jackets ($56\text{ in}$ high curb, Col 11) and concrete infill (Key Notes 1, 18). | A-901 Col 11, Floor Plan Key Notes | Non-drywall structural concrete records (Class 2) | Classified as Class 2; heavy structural concrete. | A-901 Cell 11 & Key Note inspection |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| E-01 | Coordinate Resolution | Raw PDF Mediabox vs visual Page Rect | Mediabox is $(0, 0, 1728, 2592)$, `rotation: 90`. Direct use of mediabox coordinates causes $90^\circ$ shearing and inverted coordinates. Native PyMuPDF visual space $(0, 0, 2592, 1728)$ correctly aligns visual elements. |
| E-02 | Line Grouping | Words spanning vertical columns on rotated page | Words on the same text line have identical $x_0$ (within $\pm 3.0\text{ pt}$) and decreasing $y_0$ coordinates ($2113 \to 2013$). Clustering by $x$ and sorting by $-y$ perfectly reconstructs multi-line text strings. |
| E-03 | Tag 1A Safety | Partition Type 1A with masonry callout | Text states: `6" FIRE RATED CMU MASONRY BLOCK`. Must NEVER be assigned Class 1 (Drywall). Parser enforces hardcoded check: `if tag == '1A': assert class == 2`. |
| E-04 | Hybrid Assembly | Tag GL1 / GL2 glass storefront with drywall pocket header | Detail calls out butt-glazed glass storefront below ACT ceiling, but has 2-1/2" metal studs with 5/8" GWB extending 6" above ceiling into plenum. On floor plans, the wall line represents the glass partition (Class 2, Red). Drywall pocket is an RCP ceiling bulkhead. |
| E-05 | Hybrid Assembly | Modernfold Operable Partition FWP-2 beneath gypsum soffit (A-902) | Movable folding acoustic partition suspended beneath overhead track and 6" gypsum board soffit. Floor plan partition is Class 2 (Non-Drywall); ceiling soffit is Class 1 (Drywall). |
| E-06 | Multi-Layer Gypsum | Detail 5D & 5E double-layer callouts | Text notes: `(2) LAYER OF 5/8" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS`. Total layers = 4 (2 per side). Total gypsum thickness = $2 \times 5/8\text{ in} = 1\text{ }1/4\text{ in}$ per face, $2\text{ }1/2\text{ in}$ total. |
| E-07 | Shaftwall Assembly | Detail 7F C-H stud asymmetric assembly | Text notes: `(1) LAYER OF 1" TYPE-SCX GYPSUM WALL BOARD + (2) LAYERS OF 1/2" TYPE-C GYPSUM WALL BOARD`. Shaft side has 1" shaftliner in C-H cavity; room side has 2 layers 1/2" Type-C. Total gypsum thickness = $2.0\text{ in}$. |
| E-08 | Direct Lamination | Detail 7A & 8A direct wall attachments | Details 7A and 8A specify `LAMINATED TO EXISTING WALL` with no metal framing. 7A adds 1-1/2" rigid insulation ($R\text{-}7.5$, Total $R\text{-}8$); 8A is direct lamination. Both classified as Class 1 (Drywall). |
| E-09 | TV Screen Section | Detail 09 on Sheet A-901 | Detail 09 is a section cut through a scheduled partition showing electrical backbox, AV blocking, and TV mounting. Not an independent partition type on floor plans. Classified as Class 3 (Uncertain / Specialty Millwork). |
| E-10 | Review Lock State | Parser run without pre-existing approval | Script generates `partition_schedule_mapping.csv`, writes `REVIEW_REQUIRED.lock`, and terminates with `sys.exit(2)`. Downstream processes check for lockfile and halt if present. |
| E-11 | Review Approval | User renames/approves CSV to `partition_schedule_mapping.approved.csv` | Downstream classification verifies approved CSV exists, checks that `REVIEW_REQUIRED.lock` has been removed, and proceeds with classification without exiting. |

---

## 4. Authoritative Specification Source

The primary specification source is the official 95% Construction Document drawing set for the MTA 99th Street - Phase 2 Interior fit-out:
- **File Name**: `file-1793194362940-560626729.pdf`
- **Architect of Record**: TPG Architecture LLP, New York, NY
- **Project Title**: MTA - 99th Street - Phase 2 Interior (Contract `C-48526`)
- **Authoring Software**: Autodesk Revit 2025 (Doc URI: `Autodesk Docs://1624114-00_MTA 99th Street/1624114-00_MTA_99th Street_ARCH_V25.rvt`)
- **Issue Status**: 95% Construction Documents (IN PROGRESS - NOT FOR CONSTRUCTION), dated 10/02/2026
- **Sheet Geometry**:
  - Raw Mediabox: `Rect(0.0, 0.0, 1728.0, 2592.0)` (Portrait ARCH D, 72 pt/in)
  - Rotation Instruction: `90` (Clockwise)
  - Visual Page Rect: `Rect(0.0, 0.0, 2592.0, 1728.0)` (Landscape ARCH D, $36\text{ in} \times 24\text{ in}$)
- **Target Sheets**:
  - `A-900` (Page 63, 0-indexed 62): `PARTITION TYPES SHEET I`
  - `A-901` (Page 64, 0-indexed 63): `PARTITION TYPES SHEET II`
  - `A-902` (Page 65, 0-indexed 64): `WALL DETAILS I`

---

## 5. Exhaustive Transcription Table (All 24 Assembly Details)

Below is the complete, verbatim transcription of all 24 assembly details from Sheets A-900 and A-901, along with the 4-class taxonomy classification.

| # | Tag | Sheet | Detail Title | Framing / Studs | GWB Layers & Thickness | Fire Rating | Acoustic / STC / SAB | Finish / Moisture | Trade CSI Division | Class | Conf | Structural / Specific Detail Notes |
|---|---|---|---|---|---|---|---|---|---|:---:|:---:|---|
| 1 | **1A** | A-900 | Detail 1A - 1 HR Rated | None (Solid masonry block) | None ($0$ layers, $0\text{"}$) | **1 Hour** | None called out | Exposed masonry / paint | Div 04 Masonry | **2** | 1.00 | **CRITICAL SAFETY OVERRIDE**: Explicitly calls out 6" FIRE RATED CMU MASONRY BLOCK. ZERO gypsum board. Must NEVER be classified as Drywall. |
| 2 | **1B** | A-900 | Detail 1B | $2\text{ }1/2\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $13\text{'}$; $13\text{'--}17\text{'}$ use $20\text{ GA}$; $>17\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side ($1\text{ }1/4\text{"}$ total) | Non-Rated | Diagonal stud bracing @ $48\text{"}$ O.C. max; add'l bracing at door headers | Standard drywall finish | Div 09 Gypsum | **1** | 1.00 | Standard interior demising wall. Secure runner channels to structure above and slab below. |
| 3 | **1C** | A-900 | Detail 1C | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $17\text{'}$; $17\text{'--}22\text{'}$ use $20\text{ GA}$; $>22\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side ($1\text{ }1/4\text{"}$ total) | Non-Rated | Stud bracing @ $48\text{"}$ O.C. max; add'l bracing at door headers | Moisture resistant barrier on all wet locations | Div 09 Gypsum | **1** | 1.00 | Most prevalent general interior partition across all office floors (Sheets A-101 to A-104). |
| 4 | **1D** | A-900 | Detail 1D | $6\text{"}$, $16\text{ GA}$ heavy-gauge @ $16\text{"}$ O.C. (Up to $8\text{'}$; $10\text{"}$ $16\text{ GA}$ studs @ $16\text{"}$ O.C. above) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated | None specified | $5/8\text{"}$ gyp bd ceiling on $7/8\text{"}$ furring channel @ $8\text{'}-0\text{"}$ AFF; $3/4\text{"}$ plywood, $1\text{ }5/8\text{"}$ metal decking | Div 09 Gypsum / Framing | **1** | 1.00 | Heavy-gauge deep cavity partition attached to existing exterior brick wall; used in 1st floor shop areas. |
| 5 | **1E** | A-900 | Detail 1E | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $8\text{'}$ height max) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated | None specified | Refer to Wall Type 1D for construction | Div 09 Gypsum | **1** | 1.00 | Low-height interior drywall partition terminating at $8\text{'}-0\text{"}$ AFF ceiling line. |
| 6 | **2B** | A-900 | Detail 2B | $2\text{ }1/2\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $13\text{'}$; $13\text{'--}17\text{'}$ use $20\text{ GA}$; $>17\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated (Acoustic) | Full height & thickness Sound Attenuation Blanket (SAB); continuous acoustic sealant top & bottom each side (STC ~45) | Paint / Scheduled finish | Div 09 Gypsum / Acoustic | **1** | 1.00 | Acoustic demising partition between private offices and corridors. |
| 7 | **2C** | A-900 | Detail 2C | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $17\text{'}$; $17\text{'--}22\text{'}$ use $20\text{ GA}$; $>22\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated (High STC) | Full height & thickness SAB; continuous acoustic sealant top & bottom each side (STC ~48--50) | Moisture resistant barrier on all wet locations | Div 09 Gypsum / Acoustic | **1** | 1.00 | High-performance sound wall demising conference rooms and executive offices. |
| 8 | **3A** | A-900 | Detail 3A | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $17\text{'}$; $17\text{'--}22\text{'}$ use $20\text{ GA}$; $>22\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated | Stud bracing @ $48\text{"}$ O.C. max; add'l bracing at door headers | Paint / Scheduled finish | Div 09 Gypsum | **1** | 1.00 | Full-height demising partition extending past ceiling to underside of structural slab above. |
| 9 | **3D** | A-900 | Detail 3D | $6\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $20\text{'}$; $20\text{'--}32\text{'}$ use $20\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated | Bracing as required | Moisture resistant barrier on all wet locations | Div 09 Gypsum | **1** | 1.00 | Deep 6" stud cavity allows vertical MEP distribution, plumbing risers, and conduit banks. |
| 10 | **5B** | A-900 | Detail 5B - 1 HR Rated | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $16\text{'}$; $16\text{'--}23\text{'}$ use $20\text{ GA}$; $>23\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB UL Type SCX on each side, stagger vertical joints | **1-Hour** (UL U419) | Full height & thickness SAB; continuous acoustic sealant top & bottom each side | UL listed taped and spackled fire-rated joints | Div 09 Fire Assemblies | **1** | 1.00 | 1-Hour fire-rated egress and occupancy separation partition. |
| 11 | **5D** | A-900 | Detail 5D | $6\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $20\text{'}$; $20\text{'--}33\text{'}$ use $20\text{ GA}$) | (2) Layers $5/8\text{"}$ GWB each side ($4$ layers total, $2\text{ }1/2\text{"}$ total GWB), stagger joints | 1--2 Hour equiv. | Continuous acoustic sealant top & bottom each side | Paint / Scheduled finish | Div 09 Gypsum | **1** | 1.00 | Double-layer 6" stud partition providing high fire resistance and high sound isolation. |
| 12 | **5E** | A-900 | Detail 5E - 2 HR Rated | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $16\text{'}$; $16\text{'--}23\text{'}$ use $20\text{ GA}$; $>23\text{'}$ use $18\text{ GA}$) | (2) Layers $5/8\text{"}$ Type X GWB each side ($4$ layers total), stagger joints | **2-Hour** (UL U419) | Full height & thickness SAB; continuous acoustic sealant top & bottom each side | UL listed fire-rated taped and spackled joints | Div 09 Fire Assemblies | **1** | 1.00 | Primary 2-hour fire-rated drywall partition enclosing stairs, electrical closets, and main mechanical shafts. |
| 13 | **7A** | A-901 | Perimeter Furring Partition 7A | None (Direct adhesive/mechanical lamination to wall) | (1) Layer $5/8\text{"}$ GWB laminated to existing wall ($R\text{-}0.5$) | Thermal Furring (Non-Rated) | Thermal assembly: $1\text{ }1/2\text{"}$ rigid insulation ($R\text{-}7.5$) + $5/8\text{"}$ GWB ($R\text{-}0.5$) = Total $R\text{-}8$ | Scheduled wall base, paint | Div 09 Gypsum Furring / Insulation | **1** | 1.00 | Perimeter interior insulated furring applied against exterior concrete and masonry facade walls. |
| 14 | **7B** | A-901 | Furring Partition 7B | $3\text{ }5/8\text{"}$, $25\text{ GA}$ @ $16\text{"}$ O.C. (Up to $16\text{'}$; $16\text{'--}23\text{'}$ use $20\text{ GA}$; $>23\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB on room side only | Non-Rated | Full height and thickness Sound Attenuation Blanket | Room side finished; secure metal channel runner above and below | Div 09 Gypsum Furring | **1** | 1.00 | One-sided stud chase furring along existing masonry core walls and MEP piping shafts. |
| 15 | **7C** | A-901 | Detail 7C | $2\text{ }1/2\text{"}$, $20\text{ GA}$ @ $16\text{"}$ O.C. ($>14\text{'}$ use $18\text{ GA}$; secure (2) runners below) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated (Heavy Gauge) | Full height & thickness SAB; continuous acoustic sealant both sides; bracing @ $48\text{"}$ O.C. | Moisture resistant barrier on all wet locations | Div 09 Gypsum / Framing | **1** | 1.00 | High-durability double-bottom runner channel partition for high-traffic areas. |
| 16 | **7E** | A-901 | Detail 7E | $3\text{ }5/8\text{"}$, $20\text{ GA}$ @ $16\text{"}$ O.C. ($>14\text{'}$ use $18\text{ GA}$; secure (2) runners below) | (1) Layer $5/8\text{"}$ GWB each side | Non-Rated | Full height & thickness SAB; continuous acoustic sealant both sides | Scheduled finish; double metal runners below | Div 09 Gypsum / Framing | **1** | 1.00 | Heavy-gauge acoustic stud partition with double floor runner channels. |
| 17 | **7F** | A-901 | Shaft Wall Partition 7F - 2 HR Rated | $2\text{ }1/2\text{"}$, $25\text{ GA}$ C-H metal studs @ $24\text{"}$ O.C. ($16\text{'--}23\text{'}$ use $20\text{ GA}$; $>23\text{'}$ use $18\text{ GA}$) | (1) Layer $1\text{"}$ Type-SCX shaftliner + (2) Layers $1/2\text{"}$ Type-C GWB room side ($2.0\text{"}$ total GWB) | **2-Hour** (UL U415 System E) | Continuous acoustic sealant top & bottom each side; 4" J-runner below | Moisture resistant barrier on all wet locations | Div 09 Shaft Wall Assemblies | **1** | 1.00 | 2-Hour fire-rated shaftwall constructed entirely from one side (corridor side) for elevator and mechanical shafts. |
| 18 | **7G** | A-901 | Detail 7G | $3\text{ }5/8\text{"}$, $20\text{ GA}$ @ $16\text{"}$ O.C. ($>14\text{'}$ use $18\text{ GA}$) | (1) Layer $5/8\text{"}$ GWB each side; header aligns to ACT ceiling | Non-Rated (Plenum Baffle) | Horizontal bracing as required; acoustic baffle above ceiling line | Moisture resistant barrier on all wet locations | Div 09 Gypsum | **1** | 1.00 | Office partition stopping at ACT ceiling line with plenum sound baffle. |
| 19 | **8A** | A-901 | Furring Partition 8A | None (Laminated directly to existing wall; note mentions $2\text{ }1/2\text{"}$ $20\text{ GA}$ where indicated) | (1) Layer $5/8\text{"}$ GWB laminated directly to existing wall | Non-Rated | None | Scheduled wall base, moisture resistant barrier on all wet locations | Div 09 Gypsum Furring | **1** | 1.00 | Direct adhesive/mechanical drywall lamination over smooth existing masonry/concrete walls. |
| 20 | **09** | A-901 | 09 Section @ TV Screen | $2\text{ }1/2\text{"}$ framing inside partition with $4\text{"}$ AV blocking per AV drawings | Scheduled wall finish on parent partition | Non-Rated | Batt insulation inside all cavities | Scheduled wall finish, scheduled wall base, finished floor | Div 09 / Div 27 AV Millwork | **3** | 0.75 | Specialty AV millwork/electrical backbox insert detail within a partition. Not an independent wall type on floor plans. |
| 21 | **GL1** | A-901 | GL1 Glass Officefront System | Framing above ceiling: $2\text{ }1/2\text{"}$ $20\text{ GA}$ @ $16\text{"}$ O.C.; butt-glazed glass below | 100% butt-glazed glass below; (1) layer $5/8\text{"}$ GWB header continuing $6\text{"}$ above ceiling | Non-Rated | $R\text{-}19$ insulation continuing all the way to structure above | Infinium Quantum single butt-glazed center office front system | Div 08 Glazing & Storefronts | **2** | 1.00 | Architectural glass officefront storefront system. Plan line is non-drywall glass. (Header fascia belongs to RCP). |
| 22 | **GL2** | A-901 | Glass Wall at Entrance | Framing above: $3\text{ }5/8\text{"}$ $20\text{ GA}$ @ $16\text{"}$ O.C.; aluminum storefront below | Glazed storefront; (1) layer GWB to slab above | Non-Rated | $R\text{-}19$ insulation continuing to structure above | Tubelite 400TU frame by Apogee; transom above $8\text{'}-0\text{"}$ AFF | Div 08 Glazing / Entrances | **2** | 1.00 | Commercial entrance storefront glazing system. Non-drywall architectural glass. |
| 23 | **10** | A-901 | 10 Typ. Steel Column Enclosure | Framed around structural steel column ($2\text{ }1/2\text{"}$ studs & runners) | (2) Layers Type X Gypsum Board ($1\text{ }1/4\text{"}$ total GWB) | **2-Hour** fire enclosure | None | Corner beads, spackling, paint | Div 09 Gypsum Fire Enclosure | **1** | 1.00 | Gypsum drywall fire enclosure encasing structural steel columns. |
| 24 | **11** | A-901 | 11 Typ. Concrete Encased Steel Column | None (Poured reinforced concrete jacket $26\text{"} \times 26\text{"}$, $56\text{"}$ high) | None ($0$ layers) | Heavy industrial impact / 4-Hr | None | Smooth formed reinforced concrete | Div 03 Concrete | **2** | 1.00 | Solid poured-in-place reinforced concrete jacket around structural column. Non-drywall. |

---

## 6. Supplementary Non-Schedule Drawing Elements

Beyond the 24 details on Sheets A-900 and A-901, the following assemblies are explicitly called out on floor plans and detail sheets:

| Element | Sheet Origin | Description | Material Assembly | Proposed Class | Confidence |
|---|---|---|---|:---:|:---:|
| **PW** | Floor Plans A-100 to A-104 | Demountable Privacy Wall | Steelcase demountable modular furniture panels (metal/fabric). Movable divider partitions. | **2** (Non-Drywall) | 1.00 |
| **FWP-2 / Key Note 7** | A-902 Details 1, 2, 3 | Modernfold Operable Partition | Modernfold Acousti-Seal Legacy paired panel movable acoustic partition with single pass door. Suspended from overhead steel track. | **2** (Non-Drywall) | 1.00 |
| **Key Note 1** | A-100 to A-104 | Structural Slab/Wall Infill | Cast-in-place reinforced structural concrete infill. | **2** (Non-Drywall) | 1.00 |
| **Key Note 18** | A-101, A-102 | Concrete Equipment Curb | Poured concrete enclosure curb, $42\text{ in}$ to $56\text{ in}$ high. | **2** (Non-Drywall) | 1.00 |
| **Gypsum Soffits** | A-902 Detail 3, A-905 | Ceiling Soffits & Bulkheads | Metal studs/furring with 5/8" gypsum board enclosing overhead tracks or ceiling transitions. | **1** (Drywall) | 1.00 |

---

## 7. Strict 4-Class Taxonomy Mapping & Precedence Rules

### 7.1 Class Definitions & Color Standards
- **Class 0: Background** (White, `#FFFFFF` / `0`):
  - Blank paper, general linework, text notes, dimensions, door swings, room identifiers, electrical/mechanical symbols, structural steel columns.
- **Class 1: Drywall** (Green, `#00FF00` / `1`):
  - All verified gypsum wallboard assemblies: Tags `1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, 10`, and gypsum soffits/bulkheads.
- **Class 2: Non-Drywall** (Red, `#FF0000` / `2`):
  - Masonry block (`1A` 6" CMU), architectural glass storefronts (`GL1, GL2`), modular privacy walls (`PW`), operable folding partitions (`FWP-2 / Key Note 7`), concrete column encasements (`11`), and concrete curbs/infill (`Key Notes 1, 18`).
- **Class 3: Uncertain / Manual Review** (Yellow, `#FFFF00` / `3`):
  - Tag `09` (specialty millwork/AV insert), untagged wall lines, ambiguous wall transitions where distance $> 50\text{ pt}$, and generic CAD walls from academic benchmark datasets (MSD, CubiCasa5K, FloorPlanCAD) lacking material schedules.

### 7.2 Precedence Hierarchy & Safety Overrides
1. **Mandatory Safety Rule (Tag 1A Veto)**:
   $$\text{Tag } 1\text{A} \implies \text{Class } 2 \text{ (Non-Drywall, Red, } \text{confidence} = 1.00\text{)}$$
   Under no circumstances shall Detail 1A be mapped to Class 1. Any code path assigning Class 1 to Tag 1A must trigger an immediate fatal assertion error.
2. **Layering / Rasterization Precedence**:
   $$\text{Class 0 (Background)} < \text{Class 3 (Uncertain)} < \text{Class 2 (Non-Drywall)} < \text{Class 1 (Drywall)}$$
   Verified material evidence strictly overwrites generic or uncertain designations.

---

## 8. CSV Export Specification & Schema Contract

The partition schedule parser serializes the transcribed ground truth into `drywall_detection/data/partition_schedule_mapping.csv`.

### 8.1 14-Column CSV Schema Specification

| Column # | Column Name | Data Type | Nullable | Description & Allowed Values |
|---|---|---|:---:|---|
| 1 | `tag` | `string` | No | Partition tag identifier (`"1A"`, `"1B"`, ..., `"GL1"`, `"10"`, `"11"`). |
| 2 | `sheet` | `string` | No | Source drawing sheet number (`"A-900"` or `"A-901"`). |
| 3 | `detail_title` | `string` | No | Verbatim detail title from drawing sheet. |
| 4 | `description` | `string` | No | High-level engineering description of the partition assembly. |
| 5 | `studs` | `string` | Yes | Metal stud size, gauge, spacing, and height limits (e.g. `"3 5/8\" 25 GA @ 16\" O.C."`). `null` for masonry/laminates. |
| 6 | `layers` | `string` | No | Gypsum board layer description (e.g. `"(1) layer each side"`, `"(2) layers each side"`, `"0"`). |
| 7 | `gwb_thickness` | `string` | Yes | Nominal GWB thickness (e.g. `"5/8\""`, `"1/2\""`, `"1\""`). `null` for non-drywall. |
| 8 | `fire_rating` | `string` | No | Fire resistance rating (`"Non-Rated"`, `"1-Hour (UL U419)"`, `"2-Hour (UL U419)"`, `"2-Hour (UL U415)"`). |
| 9 | `acoustic` | `string` | Yes | Acoustic specifications (`"Sound Attenuation Blanket (SAB)"`, `"Continuous Acoustic Sealant"`, `"R-19"`). |
| 10 | `finish` | `string` | Yes | Finish notes (`"Moisture resistant barrier in wet locations"`, `"Wall base"`, `"Paint"`). |
| 11 | `material_trade` | `string` | No | CSI MasterFormat Division (`"Division 09 - Gypsum Board"`, `"Division 04 - Masonry"`, `"Division 08 - Glazing"`). |
| 12 | `proposed_class` | `integer` | No | 4-class taxonomy integer: `0` (Background), `1` (Drywall), `2` (Non-Drywall), `3` (Uncertain). |
| 13 | `confidence` | `float` | No | Parsing and mapping confidence score $\in [0.0, 1.0]$. |
| 14 | `notes` | `string` | Yes | Specific architectural, structural, or safety notes. |

### 8.2 Sample CSV Rows
```csv
tag,sheet,detail_title,description,studs,layers,gwb_thickness,fire_rating,acoustic,finish,material_trade,proposed_class,confidence,notes
1A,A-900,PARTITION TYPE DETAIL 1A - 1 HR RATED,6" Fire-rated concrete masonry unit block wall,,0,,1-Hour,,,Division 04 - Masonry,2,1.0,CRITICAL SAFETY: 6" CMU block. ZERO drywall. Never classify as drywall.
1C,A-900,PARTITION TYPE DETAIL 1C,Standard interior drywall partition,3 5/8" 25 GA @ 16" O.C.,(1) layer each side,5/8",Non-Rated,Bracing @ 48" O.C.,Moisture barrier in wet locations,Division 09 - Gypsum Board,1,1.0,Standard office demising partition.
5E,A-900,PARTITION TYPE DETAIL 5E - 2 HR RATED,2-Hour fire-rated drywall partition,3 5/8" 25 GA @ 16" O.C.,(2) layers each side,5/8" Type X,2-Hour (UL U419),Full SAB and continuous sealant,UL listed taped finish,Division 09 - Fire Assemblies,1,1.0,Primary shaft and stair enclosure.
GL1,A-901,GL1 GLASS OFFICEFRONT SYSTEM,Infinium Quantum butt-glazed glass storefront,2 1/2" 20 GA header,Pocket header only,None,Non-Rated,R-19 to structure,Anodized aluminum / glass,Division 08 - Glazing,2,1.0,Architectural glass officefront. Plan line is non-drywall.
09,A-901,09 SECTION @ TV SCREEN,Specialty AV screen wall section with blocking,2 1/2" internal framing,Parent wall finish,5/8",Non-Rated,Batt insulation,Scheduled wall finish,Division 09 / 27 - AV Millwork,3,0.75,Specialty AV insert; not a standalone floor plan tag.
```

---

## 9. Human-in-the-Loop Review Stopping Protocol

To prevent unreviewed partition classifications from propagating into downstream training or takeoff pipelines, a strict review stopping lockfile protocol is mandated.

### 9.1 Protocol Mechanics
1. **Parser Execution**:
   - `PartitionScheduleParser.parse_and_export()` parses Sheets A-900 and A-901.
   - It writes `drywall_detection/data/partition_schedule_mapping.csv`.
2. **Lockfile Creation**:
   - If `drywall_detection/data/partition_schedule_mapping.approved.csv` does NOT exist:
     - The parser creates sentinel lockfile `drywall_detection/data/REVIEW_REQUIRED.lock`.
     - The parser logs a structured warning and terminates execution with exit code `2` (`EXIT_REVIEW_REQUIRED`).
3. **Lockfile Payload**:
   `REVIEW_REQUIRED.lock` contains a formatted JSON document:
   ```json
   {
     "status": "REVIEW_REQUIRED",
     "timestamp": "2026-11-08T05:15:00Z",
     "source_sheets": ["A-900", "A-901"],
     "generated_csv": "drywall_detection/data/partition_schedule_mapping.csv",
     "expected_approved_csv": "drywall_detection/data/partition_schedule_mapping.approved.csv",
     "total_assemblies": 24,
     "class_summary": {
       "drywall_class_1": 19,
       "non_drywall_class_2": 4,
       "uncertain_class_3": 1
     },
     "instructions": "Human architectural estimator must review partition_schedule_mapping.csv, verify drywall vs non-drywall classifications (especially Tag 1A CMU), and save the reviewed file as partition_schedule_mapping.approved.csv before deleting this lockfile."
   }
   ```
4. **Approval Handshake**:
   - To resume downstream execution (Milestone M5 drywall classification), the human reviewer verifies the CSV and saves it as `partition_schedule_mapping.approved.csv`.
   - The lockfile is removed.
   - Any attempt by downstream classification modules to execute while `REVIEW_REQUIRED.lock` exists or `partition_schedule_mapping.approved.csv` is missing raises `ReviewRequiredError`.

---

## 10. Architectural Blueprint for `drywall_detection/vector/schedule_parser.py`

### 10.1 Class & Data Structure Hierarchy

```python
"""
drywall_detection/vector/schedule_parser.py
Architecture Blueprint
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF
import json
import csv
import sys
import re

EXIT_SUCCESS = 0
EXIT_REVIEW_REQUIRED = 2
EXIT_ERROR = 1

@dataclass
class ScheduleCellBBox:
    col_idx: int
    row_idx: int
    x0: float
    x1: float
    y0: float
    y1: float

@dataclass
class PartitionAssembly:
    tag: str
    sheet: str
    detail_title: str
    description: str
    studs: Optional[str]
    layers: str
    gwb_thickness: Optional[str]
    fire_rating: str
    acoustic: Optional[str]
    finish: Optional[str]
    material_trade: str
    proposed_class: int
    confidence: float
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "sheet": self.sheet,
            "detail_title": self.detail_title,
            "description": self.description,
            "studs": self.studs or "",
            "layers": self.layers,
            "gwb_thickness": self.gwb_thickness or "",
            "fire_rating": self.fire_rating,
            "acoustic": self.acoustic or "",
            "finish": self.finish or "",
            "material_trade": self.material_trade,
            "proposed_class": self.proposed_class,
            "confidence": round(self.confidence, 2),
            "notes": self.notes or ""
        }

@dataclass
class ScheduleParserConfig:
    pdf_path: Path
    output_csv_path: Path = Path("drywall_detection/data/partition_schedule_mapping.csv")
    approved_csv_path: Path = Path("drywall_detection/data/partition_schedule_mapping.approved.csv")
    lockfile_path: Path = Path("drywall_detection/data/REVIEW_REQUIRED.lock")
    a900_page_idx: int = 62  # 0-indexed (Page 63)
    a901_page_idx: int = 63  # 0-indexed (Page 64)
    a902_page_idx: int = 64  # 0-indexed (Page 65)
    enforce_lock: bool = True
```

### 10.2 Core Parsing Engine Methods

1. **`detect_partition_sheets(doc: fitz.Document) -> Dict[str, fitz.Page]`**:
   - Searches for sheet numbers `A-900`, `A-901`, `A-902` in title blocks.
   - Validates dimensions: ARCH D ($2592 \times 1728\text{ pt}$) with `rotation == 90`.
2. **`partition_sheet_into_cells(page: fitz.Page) -> List[ScheduleCellBBox]`**:
   - Generates the $3 \times 4$ bounding box layout:
     - X-bands: $[0, 445]$, $[445, 860]$, $[860, 1300]$
     - Y-bands: $[1980, 2550]$, $[1440, 1980]$, $[900, 1440]$, $[350, 900]$
3. **`extract_cell_lines(page: fitz.Page, cell: ScheduleCellBBox) -> List[str]`**:
   - Retrieves word tokens inside `cell` bounding box.
   - Clusters words having $|w_{0} - k| < 3.0\text{ pt}$.
   - Sorts words within each cluster by $y_0$ descending (accommodating clockwise rotated text).
   - Returns clean, natural reading lines.
4. **`parse_assembly_from_lines(lines: List[str], sheet_name: str) -> PartitionAssembly`**:
   - Matches tag regex: `r'^(1[A-E]|2[B-C]|3[A-D]|5[B-E]|7[A-G]|8A|GL[1-2]|09|10|11)'`.
   - Extracts framing callouts (`r'\d+/\d+"|\d+"\s+\d+\s+GA'`).
   - Extracts GWB layers (`r'\(\d+\)\s+LAYER'`).
   - Extracts fire ratings (`r'(\d+)\s*-\s*HR\s+RATED|UL\s+U\d+'`).
   - Extracts acoustic blankets (`r'SOUND\s+ATTENUATION\s+BLANKET|ACOUSTIC\s+SEALANT'`).
   - Applies strict Tag 1A safety override.
5. **`export_csv(assemblies: List[PartitionAssembly], path: Path) -> Path`**:
   - Writes standard CSV with 14 columns.
6. **`enforce_review_lock(assemblies: List[PartitionAssembly], config: ScheduleParserConfig) -> int`**:
   - Checks if `config.approved_csv_path.exists()`.
   - If not, writes `config.lockfile_path` with JSON summary and calls `sys.exit(EXIT_REVIEW_REQUIRED)`.

### 10.3 Exception Hierarchy
```python
class ScheduleParsingError(Exception):
    """Base exception for partition schedule parsing failures."""

class AssemblyHeaderNotFoundError(ScheduleParsingError):
    """Raised when an assembly tag or title cannot be identified in a cell."""

class DrywallIntegrityViolation(ScheduleParsingError):
    """Fatal error raised if Tag 1A CMU is classified as Drywall."""

class ReviewRequiredError(ScheduleParsingError):
    """Raised when downstream processing attempts to proceed while review is locked."""
```

---

## 11. Verification Method & Test Suite Specification

The implementation of `drywall_detection/vector/schedule_parser.py` must be verified by `drywall_detection/tests/test_schedule_parser.py` with the following test cases:

1. **`test_transcribe_all_24_assemblies()`**:
   - Verifies that all 24 assembly details (12 on A-900, 12 on A-901) are successfully discovered and transcribed without missing tags.
2. **`test_tag_1a_cmu_safety_veto()`**:
   - Explicitly asserts `assembly["1A"].proposed_class == 2` (Non-Drywall) and `assembly["1A"].confidence == 1.0`.
   - Asserts that attempting to set `proposed_class = 1` on Tag 1A raises `DrywallIntegrityViolation`.
3. **`test_drywall_assemblies_classification()`**:
   - Verifies that Tags 1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, and 10 are classified as Class 1 (Drywall).
4. **`test_non_drywall_assemblies_classification()`**:
   - Verifies that Tags 1A, GL1, GL2, and 11 are classified as Class 2 (Non-Drywall).
5. **`test_uncertain_assembly_classification()`**:
   - Verifies that Detail 09 is classified as Class 3 (Uncertain).
6. **`test_csv_export_schema_integrity()`**:
   - Verifies that exported CSV matches the 14-column contract exactly.
7. **`test_review_stopping_lockfile_and_exit_code()`**:
   - Asserts that running the CLI without an approved CSV produces `REVIEW_REQUIRED.lock` and exits with code `2`.
8. **`test_approved_csv_resumes_execution()`**:
   - Asserts that when `partition_schedule_mapping.approved.csv` is present, the parser exits with code `0` and does not recreate the lockfile.
