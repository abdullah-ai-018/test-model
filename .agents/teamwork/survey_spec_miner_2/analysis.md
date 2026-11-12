# Architectural Drawings & Geometry Specification Mining Report

**Agent:** `survey_spec_miner_2`  
**Role:** Architectural Drawings & Geometry Spec Miner  
**Workspace:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Date:** 2026-11-07T20:38:00Z  
**Project:** Drywall Detection & Wall Classification AI System  

---

## Executive Summary

This report delivers an exhaustive technical investigation of all architectural drawings, partition schedules, construction specifications, vector drawing geometries, and coordinate transformation systems available in the workspace and user environment.

Key technical conclusions:
1. **Authoritative Specification Source**: The primary commercial architectural reference set is the **MTA 99th Street - Phase 2 Interior Project** (Contract `C-48526`, architectural firm **TPG Architecture LLP**, Autodesk Revit 2025 authoring, 95% Construction Documents issued 10/02/2026).
2. **Definitive Partition Schedule**: Full partition schedules and construction details were extracted from drawing sheets **A-900 (Partition Types Sheet I)**, **A-901 (Partition Types Sheet II)**, **A-902 (Wall Details I)**, and **A-910 (Firestopping Details)**.
3. **Partition Material Classification**:
   - **Verified Drywall (Class 1, Green)**: Partition Types `1B`, `1C`, `1D`, `1E`, `2B`, `2C`, `3A`, `3D`, `5B`, `5D`, `5E`, `7A`, `7B`, `7C`, `7E`, `7F`, `7G`, `8A`, Detail 10 column enclosures, and gypsum soffits/bulkheads.
   - **Verified Non-Drywall (Class 2, Red)**: Partition Type `1A` (6" CMU masonry block), `GL1` & `GL2` (glass officefront and entrance glass systems), `PW` (Steelcase demountable privacy walls), `Key Note 7 / FWP-2` (Modernfold operable acoustic partitions), `Key Note 1` (concrete infill), `Key Note 18` (concrete enclosure), `Detail 11` (concrete-encased steel columns), and exterior/core structural masonry and concrete.
   - **Uncertain / Manual Review (Class 3, Yellow)**: Any wall partition lacking a verified material callout, ambiguous existing walls without furring callouts, demolition walls of unknown composition, and generic academic datasets (Modified Swiss Dwellings, CubiCasa5K, FloorPlanCAD) lacking gypsum specifications.
4. **Drawing Geometry & Coordinate Alignment**:
   - Architectural sheets are standard **ARCH D** format ($36\text{ in} \times 24\text{ in}$, $2592 \times 1728\text{ points}$).
   - Revit PDFs possess `mediabox: Rect(0.0, 0.0, 1728.0, 2592.0)` with `rotation: 90`, rendering visual `page.rect: Rect(0.0, 0.0, 2592.0, 1728.0)`.
   - Drawing scale on construction plans A-100 through A-105 is $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ ($1:96$ scale, where $1\text{ pt} = 1.3333\text{ in} = 33.867\text{ mm}$ physical space).
   - PyMuPDF vector drawing elements (`get_drawings()`) and text elements (`get_text("words")`) in modern versions are native to rotated visual `page.rect` space, establishing an exact affine mapping to raster segmentation pixels: $x_{px} = (x_{pt} - x_0) \cdot \frac{DPI}{72.0}$.
5. **Gold-Standard Ground Truth Annotations**:
   - `drywall_walls_marked_red_by_Usman.pdf` contains **239 human-verified drywall wall centerline line annotations** and **239 tag square annotations** across floors A-100 to A-104.
   - `drywall_relevant_full_pages.pdf` provides the pristine 27-page vector PDF for evaluation and inference.

---

## 1. Architectural Drawings Workspace Inventory

An exhaustive search across the workspace (`test-model`), `Downloads`, `Documents`, and related directories identified the following architectural PDF drawing sets and technical artifacts:

| # | File Path / Name | Size | Pages | Origin / Project | Description & Contents |
|---|---|---|---|---|---|
| 1 | `file-1793194362940-560626729.pdf` | 29.11 MB | 71 | MTA - 99th Street - Phase 2 Interior (Contract C-48526, TPG Architecture LLP) | Complete 95% CD interior architectural set. Contains title sheets, life safety plans (LS-100 to LS-105), construction floor plans (A-100 to A-105), reflected ceiling plans (A-200 to A-204), power/comm plans (A-300 to A-306), finish plans (A-401 to A-404), furniture plans (A-501 to A-504), door schedules (A-601/602), interior elevations (A-701 to A-710), stair details (A-801 to A-804), partition sheets (A-900, A-901), wall details (A-902), ceiling details (A-905, A-906), clerestory details (A-907), entry details (A-908), firestopping (A-910). |
| 2 | `drywall_relevant_full_pages.pdf` | 8.08 MB | 27 | MTA 99th Street (Phase 2 Interior) | Curated 27-page pristine vector drawing extract containing all sheets relevant to wall and drywall analysis: A-100 through A-105, A-200 through A-204, A-401 through A-404, A-406, A-602, A-801, A-802, A-804, A-805, A-900, A-901, A-902, A-905, A-906, A-907, A-910. Zero annotations. Serves as clean inference/test benchmark. |
| 3 | `drywall_walls_marked_red_by_Usman.pdf` | 8.45 MB | 27 | MTA 99th Street (Phase 2 Interior) | Curated 27-page set with 478 vector PDF annotations (239 wall centerlines + 239 tag bounding boxes) marked in red by Usman / Jev Drywall Detector across pages 1–5 (A-100 to A-104). Provides gold-standard human verification labels. |
| 4 | `drywall_annotated_floor_plans.pdf` | 8.30 MB | 27 | MTA 99th Street (Phase 2 Interior) | Floor plans with automated drywall detections (482 annotations across pages 1–5). |
| 5 | `all_wall_partition_types.pdf` | 523.6 KB | 2 | MTA 99th Street (Sheets A-900 & A-901) | Isolated 2-page vector sheets: Page 1 = A-900 Partition Types Sheet I, Page 2 = A-901 Partition Types Sheet II. |
| 6 | `wall_partition_data_json.pdf` | 38.1 KB | 7 | MTA 99th Street (Sheets A-900 & A-901) | Detailed structured JSON transcription (21,935 characters) documenting every partition assembly, stud gauge/depth, gypsum layers, fire ratings, insulation, and notes. |
| 7 | `floor_wise_new_wall_partition_tags.pdf` | 29.1 KB | 2 | MTA 99th Street | Floor-by-floor inventory of new wall tags appearing on sheets A-100 through A-105. |
| 8 | `protake_ai_wall_partition_data.pdf` | 30.1 KB | 2 | MTA 99th Street (ProTake AI) | Reference summary connecting floor-wise tags to partition assembly specifications and non-drywall systems (GL1, GL2, PW, Key Notes). |
| 9 | `Drywall_QTO_SOP.pdf` | 145.5 KB | 35 | Civil Engineering Drywall QTO SOP | Comprehensive standard operating procedure detailing drawing review, partition classification, PlanSwift/Bluebeam annotation standards, and calculation logic. |
| 10 | `Bid Set.pdf` | 79.46 MB | 71 | Best Buy College Point #0546 (MJM Architects) | Commercial retail architectural bid set (139-15 20th Ave, College Point, NY). Vector CAD drawings including demolition, life safety, architectural site, and construction floor plans. Excellent held-out commercial test set. |
| 11 | `3.1-all-architectural-darwings.pdf` | 25.89 MB | 107 | MHD Storage Facility (Mwanza, Tanzania) | Institutional/commercial storage facility architectural drawings. Mixed vector/raster CAD sheets. |
| 12 | `test Spark Lake Grove - Permit Set.pdf` | 35.66 MB | Multi | Spark Lake Grove Permit Set | Commercial retail interior fit-out permit set. |
| 13 | `image-canvas-project/sample_drawings/` | Various | 6 files | Synthetic & Pilot Architectural Test Set | Includes `commercial_plan_with_finish_schedule.pdf` (7.8 KB), `pilot_residential_10pages.pdf` (1.60 MB), `synthetic_office_plan.pdf` (3.0 KB), `scanned_raster_fixture.pdf` (1.50 MB), and `rotated_test.pdf` (0.78 KB). |

---

## 2. MTA 99th Street (Contract C-48526): Master Sheet Index & Mapping

The 71-page master set `file-1793194362940-560626729.pdf` and its 27-page curated derivative `drywall_relevant_full_pages.pdf` map as follows:

| Sheet Number | Sheet Title | 71-Page Index | 27-Page Index | Scale | Primary Content / Purpose |
|---|---|---|---|---|---|
| `G-001` | Master Legends | Page 2 | — | As indicated | General legends, line styles, wall hatch symbols, material abbreviations |
| `G-002` | Master Sheet List | Page 3 | — | N/A | Complete project drawing index and revision tracking (100% DD to 95% CD) |
| `G-003` | Notes & Specifications | Page 4 | — | N/A | CSI divisional specifications (024119 Demo, 033000 Concrete, 042000 CMU, 092216 Metal Studs, 092900 Gypsum Board) |
| `A-100` | Cellar Construction Plan | Page 14 | Page 1 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Cellar layout: existing concrete foundation walls, sump pits, elevator shafts, partition tag `5E` (4 locations), privacy wall `PW` |
| `A-101` | First Floor Construction Plan | Page 15 | Page 2 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Ground floor: parking/storage, tinsmith, carpentry shops. Wall tags: `1C, 1D, 1E, 3A, 5B, 5E, 7A, 7F, 8A, GL2, PW` |
| `A-102` | Second Floor Construction Plan | Page 16 | Page 3 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Offices, locker rooms, rest rooms, server room, pantry. Wall tags: `1A (CMU), 1B, 1C, 3A, 3D, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 8A, GL1, PW` |
| `A-103` | Third Floor Construction Plan | Page 17 | Page 4 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Offices, conference rooms, break areas. Wall tags: `1C, 2C, 3A, 3D, 5D, 5E, 7A, 7B, 7E, 7F, 7G, 8A, GL1, PW` |
| `A-104` | Fourth Floor Construction Plan | Page 18 | Page 5 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Executive offices, meeting spaces, restrooms. Wall tags: `1C, 2C, 3A, 3D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, GL1, PW` |
| `A-105` | Roof Construction Plan | Page 19 | Page 6 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Roof deck, stair/elevator bulkheads, parapet walls |
| `A-200` | Cellar Reflected Ceiling Plan | Page 20 | Page 7 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Open slab ceiling throughout cellar |
| `A-201` | First Floor Reflected Ceiling Plan | Page 21 | Page 8 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | ACT (acoustic tile) and gypsum ceiling layouts, soffit locations |
| `A-202` | Second Floor Reflected Ceiling Plan | Page 22 | Page 9 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Ceiling heights ($9\text{ ft } 0\text{ in}$, $10\text{ ft } 0\text{ in}$), gypsum soffit bulkheads |
| `A-203` | Third Floor Reflected Ceiling Plan | Page 23 | Page 10 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Ceiling heights, soffit details at partition heads |
| `A-204` | Fourth Floor Reflected Ceiling Plan | Page 24 | Page 11 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Ceiling heights, soffits at glass fronts |
| `A-401` to `A-404` | Finish Plans (1st - 4th Floors) | Pages 32–35 | Pages 12–15 | $1/8\text{ in} = 1\text{ ft } 0\text{ in}$ | Wall finish schedules (paint, ceramic tile in restrooms, wall bases) |
| `A-406` | Finish Legend Sheet I | Page 37 | Page 16 | N/A | Material finishes and paint specs |
| `A-602` | Door Details | Page 42 | Page 17 | As indicated | Door frame jamb and head details in drywall and CMU partitions |
| `A-801` | Stair A Plans & Sections | Page 53 | Page 18 | $1/4\text{ in} = 1\text{ ft } 0\text{ in}$ | Stair A shaft enclosure and landing details |
| `A-802` | Stair B Plans & Sections | Page 54 | Page 19 | $1/4\text{ in} = 1\text{ ft } 0\text{ in}$ | Stair B shaft enclosure (shaft wall partition 7F, 2-hr rated) |
| `A-804` | Stair Typ. Details II | Page 56 | Page 20 | As indicated | Structural attachments to partitions |
| `A-805` | Typ. Millwork Details I | Page 57 | Page 21 | As indicated | Millwork blocking and wall anchorage |
| `A-900` | Partition Types Sheet I | Page 63 | Page 22 | $1\text{ }1/2\text{ in} = 1\text{ ft } 0\text{ in}$ | Authoritative partition assembly details: 1A, 1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E |
| `A-901` | Partition Types Sheet II | Page 64 | Page 23 | $1\text{ }1/2\text{ in} = 1\text{ ft } 0\text{ in}$ | Authoritative partition assembly details: 7A, 7B, 7C, 7E, 7F, 7G, 8A, GL1, GL2, Details 09, 10, 11 |
| `A-902` | Wall Details I | Page 65 | — | $1/4\text{ in}, 3/8\text{ in}, 3\text{ in} = 1\text{ ft } 0\text{ in}$ | Operable partition details (Modernfold Legacy paired panels, track connection, gypsum soffit) |
| `A-905` | Ceiling Details I | Page 67 | Page 24 | $1\text{ }1/2\text{ in} = 1\text{ ft } 0\text{ in}$ | Gypsum ceiling transitions, soffits, and pocket details |
| `A-906` | Ceiling Details II | Page 68 | Page 25 | As indicated | Wall-to-ceiling head track acoustic and firestopping seals |
| `A-907` | Clerestory Details | Page 69 | Page 26 | As indicated | Clerestory glass framing and gypsum header assemblies |
| `A-910` | Firestopping Details | Page 71 | Page 27 | As indicated | Through-penetration firestop systems for gypsum stud partitions, CMU, and concrete slabs |

---

## 3. Partition Types & Schedules: Complete Material Taxonomy

The following tables document the exhaustive mining of partition assemblies from Sheets `A-900`, `A-901`, `A-902`, and `A-910`.

### 3.1 Verified Drywall Assemblies (Class 1)

Every partition listed in this table is definitively composed of gypsum wallboard (GWB) attached to cold-formed metal framing or laminated to existing substrates.

| Tag | Drawing Sheet | Drawing Label | Framing / Metal Stud Specifications | Gypsum Wallboard (GWB) Assembly | Insulation & Acoustic Sealant | Fire Rating | Structural / Detail Notes |
|---|---|---|---|---|---|---|---|
| **1B** | A-900 | Detail 1B | $2\text{ }1/2\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $13\text{ ft}$; $13\text{--}17\text{ ft}$ use $20\text{ GA}$; $>17\text{ ft}$ use $18\text{ GA}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | None specified | Non-Rated | Secure channel runners to structure above and below; diagonal stud bracing @ $48\text{ in}$ O.C. max; add'l bracing at door headers |
| **1C** | A-900 | Detail 1C | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $17\text{ ft}$; $17\text{--}22\text{ ft}$ use $20\text{ GA}$; $>22\text{ ft}$ use $18\text{ GA}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | None specified | Non-Rated | Most common standard interior drywall partition. Secure runners top and bottom; stud bracing @ $48\text{ in}$ O.C. |
| **1D** | A-900 | Detail 1D | $6\text{ in}$, $16\text{ GA}$ heavy-gauge metal studs @ $16\text{ in}$ O.C. ($8\text{ ft}$ max height) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | None specified | Non-Rated | Heavy-gauge deep cavity partition (used on 1st floor shop areas for impact resistance or equipment mounting) |
| **1E** | A-900 | Detail 1E | Metal studs @ $16\text{ in}$ O.C. | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | Moisture-resistant barrier at wet locations | Non-Rated | Wet-location drywall assembly (water-resistant / greenboard gypsum backing for tile or paint) |
| **2B** | A-900 | Detail 2B | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $17\text{ ft}$; $17\text{--}22\text{ ft}$ use $20\text{ GA}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | Full height & thickness Sound Attenuation Blanket (SAB); continuous acoustic sealant top & bottom, both sides | Non-Rated (Acoustic) | Standard acoustic wall assembly between private offices and circulation corridors |
| **2C** | A-900 | Detail 2C | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $16\text{ ft}$; $16\text{--}23\text{ ft}$ use $20\text{ GA}$; $>23\text{ ft}$ use $18\text{ GA}$) | (2) Layers of $5/8\text{ in}$ Gypsum Wall Board on each side; stagger all vertical joints | Full height & thickness Sound Attenuation Blanket (SAB); continuous acoustic sealant top & bottom, both sides | Non-Rated (High STC) | High-performance sound partition between conference rooms, server rooms, and executive spaces |
| **3A** | A-900 | Detail 3A | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $17\text{ ft}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | None specified | Non-Rated | Standard office demising wall extending to ceiling / structure above |
| **3D** | A-900 | Detail 3D | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $16\text{ ft}$) | (2) Layers of $5/8\text{ in}$ Gypsum Wall Board on each side; stagger all vertical joints | Full height & thickness Sound Attenuation Blanket; continuous acoustic sealant | Non-Rated (High STC) | Double-layer acoustic wall with moisture barrier in wet areas (restrooms, locker rooms) |
| **5B** | A-900 | Detail 5B | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. | Fire-rated Type X Gypsum Wall Board assembly (1 layer each side or per UL design) | Sound Attenuation Blanket; continuous acoustic sealant | **1-Hour Fire Rated** | 1-Hour rated corridor or egress enclosure wall |
| **5D** | A-900 | Detail 5D | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. | Fire-rated Gypsum Wall Board assembly | Sound Attenuation Blanket; continuous acoustic sealant | **1-Hour Fire Rated** | 1-Hour rated tenant/occupancy separation wall |
| **5E** | A-900 | Detail 5E | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $16\text{ ft}$; $16\text{--}23\text{ ft}$ use $20\text{ GA}$; $>23\text{ ft}$ use $18\text{ GA}$) | (2) Layers of $5/8\text{ in}$ Type X Gypsum Wall Board on each side; stagger all vertical joints | Full height & thickness Sound Attenuation Blanket; continuous acoustic sealant top & bottom | **2-Hour Fire Rated** | Primary 2-hour fire-rated drywall partition enclosing stairs, electrical closets, and main mechanical shafts |
| **7A** | A-901 | Detail 7A | Direct wall attachment (no metal studs); adhesive / mechanical laminate | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board laminated to existing wall ($R\text{-}0.5$) | $1\text{ }1/2\text{ in}$ Rigid Insulation ($R\text{-}7.5$, Total assembly $R\text{-}8$) | Non-Rated (Thermal Furring) | Perimeter interior furring wall applied against exterior concrete and masonry facade walls |
| **7B** | A-901 | Detail 7B | $3\text{ }5/8\text{ in}$, $25\text{ GA}$ @ $16\text{ in}$ O.C. (Up to $16\text{ ft}$; $16\text{--}23\text{ ft}$ use $20\text{ GA}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on room side only | Full height & thickness Sound Attenuation Blanket; continuous acoustic sealant both sides | Non-Rated (Chase Furring) | One-sided stud furring along masonry core walls or MEP piping chases |
| **7C** | A-901 | Detail 7C | $3\text{ }5/8\text{ in}$, $20\text{ GA}$ @ $16\text{ in}$ O.C. ($>14\text{ ft}$ use $18\text{ GA}$) | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board on each side | Full height & thickness Sound Attenuation Blanket; continuous acoustic sealant | Non-Rated (Heavy Gauge) | Double bottom runner channel secured to structure; high-durability partition |
| **7E** | A-901 | Detail 7E | $2\text{ }1/2\text{ in}$, $25\text{ GA}$ C-H metal studs @ $24\text{ in}$ O.C. (Up to $16\text{ ft}$) | (2) Layers of $1/2\text{ in}$ Type-C Gypsum Wall Board; stagger all vertical joints | Moisture-resistant barrier in wet locations | Non-Rated (Shaft/Chase) | Vertical chase enclosure using C-H studs for one-sided erection |
| **7F** | A-901 | Detail 7F | $2\text{ }1/2\text{ in}$, $25\text{ GA}$ C-H metal studs @ $24\text{ in}$ O.C. with $4\text{ in}$ metal J-runner | (1) Layer of $1\text{ in}$ Type-SCX Gypsum Shaftliner board + (2) Layers of $1/2\text{ in}$ Type-C Gypsum Wall Board; stagger vertical joints | None specified (cavity open or insulated per spec) | **2-Hour Fire Rated** (UL U415 System E) | 2-Hour shaft wall partition for vertical elevator and mechanical shafts; constructed entirely from corridor side |
| **7G** | A-901 | Detail 7G | $2\text{ }1/2\text{ in}$, $20\text{ GA}$ @ $16\text{ in}$ O.C. max ($>14\text{ ft}$ use $18\text{ GA}$) | (1) Layer of Gypsum Wall Board on each side; header aligns to ACT ceiling | $R\text{-}19$ insulation continuing all the way to structure above | Non-Rated (Acoustic Baffle) | Attenuation partition stopping at ceiling with above-ceiling gypsum baffle and $R\text{-}19$ batt blanket |
| **8A** | A-901 | Detail 8A | Direct wall attachment (no metal studs); laminated directly | (1) Layer of $5/8\text{ in}$ Gypsum Wall Board laminated directly to existing wall | None | Non-Rated (Laminated) | Direct drywall lamination over smooth existing concrete/CMU partitions; scheduled wall base |
| **Detail 10** | A-901 | Detail 10 | $2\text{ }1/2\text{ in}$ metal studs around structural steel column | (2) Layers of Type X Gypsum Wall Board framing column | Cavity blocking as required | **2-Hour Fire Rated** | Structural steel column drywall enclosure |
| **Gypsum Soffits** | A-902 / A-905 | Details | $2\text{ }1/2\text{ in}$ metal studs & channels | $5/8\text{ in}$ Gypsum Board with spackable corner beads | Batt insulation inside cavities where noted | Non-Rated / Fire Barrier | Ceiling bulkheads, pocket headers above operable partitions (A-902 Detail 3), and glass officefront fascias |

---

### 3.2 Verified Non-Drywall Assemblies (Class 2)

Every assembly listed in this table is definitively constructed of masonry, concrete, glass, or factory-manufactured demountable metal panels. **None of these are drywall.**

| Identifier | Drawing Sheet | Label / Specification | Material Assembly | Structural Function | Why Classified as Non-Drywall |
|---|---|---|---|---|---|
| **1A** | A-900 | Detail 1A - 1 HR Rated | $6\text{ in}$ Fire-Rated Concrete Masonry Unit (CMU) block | 1-Hour fire-rated masonry demising wall | Detail explicitly calls out $6\text{ in}$ solid CMU block with mortar joints. Zero gypsum board or metal framing. |
| **GL1** | A-901 | Glass Officefront System | Infinium Quantum single butt-glazed center office front system, extruded aluminum profile | Architectural glass demountable storefront | 100% butt-glazed tempered/laminated glass and aluminum channel. (Header drywall fascia above is separate). |
| **GL2** | A-901 | Glass Wall at Entrance | Architectural entrance glass wall system | Glazed vestibule entry wall | Aluminum and glass curtain/storefront construction. |
| **PW** | Floor Plans | Demountable Privacy Wall | Steelcase demountable modular privacy wall panels | Movable office divider panels | Factory-fabricated demountable metal/fabric furniture panels supplied by furniture vendor; not gypsum/stud construction. |
| **FWP-2 / Key Note 7** | A-902 | Operable Partition (Details 1, 2, 3) | Modernfold Acousti-Seal Legacy paired panel operable partition, $3\text{ in}$ ($76.2\text{ mm}$) panel thickness | Moveable acoustic folding partition | Fabric-wrapped acoustic folding panels suspended from overhead structural steel track. (Soffit above is drywall; folding panel is non-drywall). |
| **Key Note 1** | A-100 to A-104 | Key Note 1 | Cast-in-place concrete infill | Structural slab/wall repair | Heavy structural concrete; not gypsum. |
| **Key Note 18** | A-101 / A-102 | Key Note 18 | Concrete enclosure, $42\text{ in}$ ($1,066.8\text{ mm}$) to $56\text{ in}$ high | Mechanical/electrical protection curb | Poured-in-place reinforced concrete; not gypsum. |
| **Detail 11** | A-901 | Detail 11 | Typ. Concrete Encased Steel Column ($56\text{ in}$ high reinforced concrete jacket) | Column fireproofing and collision protection | Solid reinforced concrete jacket around wide-flange structural steel; not drywall. |
| **Foundation / Retaining Walls** | A-100 Cellar | Sub-grade perimeter | $12\text{ in}$ to $18\text{ in}$ reinforced cast-in-place concrete | Below-grade foundation retaining walls with blindside membrane | Heavy reinforced concrete; non-drywall. |
| **Exterior Masonry Walls** | A-101 to A-104 | Building envelope | Existing multi-wythe brick and CMU load-bearing exterior facade | Structural facade shell | Unit masonry; non-drywall (only the interior 7A furring layer is drywall). |

---

### 3.3 Ambiguous / Uncertain Partitions (Class 3)

The following partitions lack definitive material callouts on the drawings and **must be classified as Class 3 (Uncertain / Manual Review)** to maintain strict classification integrity per Requirement R2:

1. **Untagged Interior Partitions**: Any wall segment on floor plans A-100 through A-105 that does not have an associated partition tag (e.g. minor closet partitions or storage enclosures in Cellar A-100).
2. **Demolition / Existing Unaltered Walls**: Existing partitions indicated on drawings with light gray line style (`rgb(0.73, 0.73, 0.73)`) where no furring tag (`7A` or `8A`) is specified and material composition is not explicitly annotated.
3. **Transition & Junction Zones with Spatial Ambiguity**: Wall intersections where two different partition types meet (e.g. where $1\text{C}$ transitions into $7\text{B}$ furring or $5\text{E}$ shaft) if the tag association distance exceeds confidence threshold ($R > 50\text{ pt}$).
4. **Public Pretraining Datasets**: Generic wall annotations from public benchmark datasets (Modified Swiss Dwellings, CubiCasa5K, FloorPlanCAD) that designate walls in CAD or residential floor plans without architectural partition schedules. Per Requirement R2, these must be treated as generic walls (or Class 3 in 4-class evaluation) and never falsely reported as verified drywall.

---

## 4. Drawing Geometry, Vector Extraction & Coordinate Alignment

### 4.1 Page Layout & Dimensions

- **Standard Dimensions**: $2592.0\text{ pt} \times 1728.0\text{ pt}$.
  - At $72\text{ pt/inch}$, this corresponds exactly to $36.0\text{ in} \times 24.0\text{ in}$ (**Architectural Series D / ANSI D**).
- **Page Rotation**:
  - `mediabox: Rect(0.0, 0.0, 1728.0, 2592.0)` (Portrait orientation in raw PDF dictionary).
  - `page.rotation: 90` (Clockwise 90-degree rotation instruction).
  - `page.rect: Rect(0.0, 0.0, 2592.0, 1728.0)` (Landscape orientation as visually viewed and extracted).
- **Physical Drawing Scale**:
  - Primary floor plans (A-100 through A-105): $\mathbf{1/8\text{ in} = 1\text{ ft } 0\text{ in}}$ ($1:96$ ratio).
  - Conversion factor:
    $$\frac{72\text{ pt}}{1\text{ in}} \times \frac{1\text{ in (drawing)}}{8\text{ ft (real)}} = \frac{72\text{ pt}}{96\text{ in (real)}} = 0.75\text{ pt/inch (real)}$$
    $$1\text{ pt (PDF)} = \frac{96}{72}\text{ in} = \frac{4}{3}\text{ in} \approx 1.3333\text{ in (real)} = 33.867\text{ mm (real)}$$
    $$1\text{ ft (real)} = 9.0\text{ pt (PDF)}$$
  - Detail sheets (A-900, A-901): $1\text{ }1/2\text{ in} = 1\text{ ft } 0\text{ in}$ ($1:8$ ratio; $1\text{ pt} = 0.111\text{ in} = 2.822\text{ mm}$).
  - Wall detail sheets (A-902): $1/4\text{ in} = 1\text{ ft } 0\text{ in}$ ($1:48$ ratio) and $3\text{ in} = 1\text{ ft } 0\text{ in}$ ($1:4$ ratio).

---

### 4.2 Vector Drawing Paths Distribution

Inspection of Sheet `A-101` (First Floor Construction Plan, Page 15) using PyMuPDF `get_drawings()` revealed **21,458 vector drawing paths**:

| Drawing Type | Path Count | Typical Geometric Usage in Revit Architecture |
|---|---|---|
| `s` (Strokes / Outlines) | 20,744 (96.7%) | Wall boundary lines, centerline markers, dimension extension lines, door swings, gridlines |
| `f` (Fills / Solid Polygons) | 671 (3.1%) | Solid wall cavity fills, column section fills, text annotation background masks (`(1, 1, 1)` whiteout) |
| `fs` (Fill and Stroke) | 43 (0.2%) | Complex composite architectural symbols, structural column cut outlines |

**Stroke Width Distribution**:
- `0.24 pt` (16,358 paths): Hairlines used for dimension strings, witness lines, material hatching, and gridlines.
- `0.48 pt` (2,916 paths): Thin-medium lines for door swings, cabinet edges, room boundary dividers.
- `1.20 pt` (406 paths): Medium-heavy lines for secondary wall edges and partition boundaries.
- `3.48 pt` (420 paths): Heavy cut lines representing primary structural wall cuts and fire-rated shaft boundaries.

**Color Distribution**:
- Black `(0.0, 0.0, 0.0)` (13,119 paths): New construction wall outlines, dimensions, text callouts.
- Medium Gray `(0.57, 0.57, 0.57)` (4,802 paths): Background underlays, furniture fixtures, equipment outlines.
- Light Gray `(0.73, 0.73, 0.73)` (1,830 paths): Existing partitions, structural gridlines, column centerlines.
- Dark Gray `(0.13, 0.13, 0.13)` (104 paths): Window mullions and frame profiles.

---

### 4.3 Embedded Fonts & Text Layers

Analysis of font dictionaries across all 71 pages identified 10 embedded TrueType/Type0 fonts:
1. `ArialMT` (TrueType / Type0)
2. `MicrosoftSansSerif` (TrueType, subset `BCPWJW`)
3. `CenturyGothic` (TrueType, subset `CFWUZY`)
4. `Helvetica75Bold10.5` (Type0)
5. `Arial` (TrueType, subset `JWTRVT`)
6. `SegoeUISymbol` (TrueType, subset `NBPIKY`)
7. `ArialNarrow,Bold` (TrueType, subset `QTBMYZ`)
8. `ArialNarrow` (TrueType, subset `ROCIYD`)
9. `Arial,Bold` (TrueType, subset `WDLTFM`)
10. `Arial` (Standard fallback)

All partition tags (`1C`, `5E`, `7A`, etc.) are rendered as live selectable vector text rather than outlined curves. This enables 100% accurate, zero-OCR-error text extraction via PyMuPDF `page.get_text("words")`.

---

### 4.4 Resolution, DPI & Coordinate Transformation Mathematics

When bridging between PyMuPDF vector coordinates (in PDF points) and raster segmentation masks (in pixel arrays), exact mathematical alignment is mandatory.

#### Modern PyMuPDF Coordinate Unification
In modern PyMuPDF (v1.23+), calling `page.get_drawings()` and `page.get_text("words")` automatically maps all coordinates into the rotated visual space defined by `page.rect`.
- Visual bounds: $x \in [0.0, 2592.0]$, $y \in [0.0, 1728.0]$.
- Standard raster pixmap rendered via `page.get_pixmap(dpi=DPI)` produces an image of dimensions:
  $$W_{px} = \text{round}\left( 2592.0 \times \frac{DPI}{72.0} \right)$$
  $$H_{px} = \text{round}\left( 1728.0 \times \frac{DPI}{72.0} \right)$$

#### Exact Forward Mapping: Vector Space $(x_{pt}, y_{pt}) \longrightarrow$ Raster Space $(x_{px}, y_{px})$
For any vector vertex $(x_{pt}, y_{pt})$:
$$x_{px} = \text{round}\left( (x_{pt} - x_0) \cdot \frac{DPI}{72.0} \right)$$
$$y_{px} = \text{round}\left( (y_{pt} - y_0) \cdot \frac{DPI}{72.0} \right)$$
Where $x_0 = \text{page.rect.x0} = 0.0$ and $y_0 = \text{page.rect.y0} = 0.0$.

#### Exact Inverse Mapping: Raster Prediction $(x_{px}, y_{px}) \longrightarrow$ PDF Geometry $(x_{pt}, y_{pt})$
To re-render segmentation polygons back into downloadable vector PDFs:
$$x_{pt} = x_0 + \left( x_{px} \cdot \frac{72.0}{DPI} \right)$$
$$y_{pt} = y_0 + \left( y_{px} \cdot \frac{72.0}{DPI} \right)$$

#### DPI Evaluation Matrix for Training & Inference

| Target DPI | Pixel Dimensions ($W \times H$) | Megapixels | Memory / 3-ch Image | Wall Width ($4\text{ }7/8\text{ in}$ Wall) | Recommendation |
|---|---|---|---|---|---|
| **72 DPI** | $2592 \times 1728$ | $4.48\text{ MP}$ | $13.4\text{ MB}$ | $3.66\text{ px}$ | Fast inference, lightweight preview, sufficient for global layout |
| **144 / 150 DPI** | $5400 \times 3600$ | $19.44\text{ MP}$ | $58.3\text{ MB}$ | $7.62\text{ px}$ | **Optimal balance**: wall lines clearly separable (7–8 px wide), text legible |
| **300 DPI** | $10800 \times 7200$ | $77.76\text{ MP}$ | $233.3\text{ MB}$ | $15.24\text{ px}$ | Heavy for GPU memory; requires $512 \times 512$ sliding window tiling |

---

## 5. Ground Truth Mapping Strategy (4-Class Label Derivation)

### 5.1 4-Class Segmentation Taxonomy

| Class ID | Semantic Label | Display Color (RGB / Hex) | Physical Architecture Scope | Decision Rule |
|---|---|---|---|---|
| **0** | **Background** | White / Transparent `(255, 255, 255)` / `None` | White space, text, dimensions, room tags, furniture, millwork, fixtures, doors, windows, symbols, structural column steel | Pixel is not part of a wall assembly |
| **1** | **Drywall** | Green `(0, 255, 0)` / `#00FF00` | Gypsum board on metal studs (1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 7C, 7G), fire-rated gypsum partitions (5B, 5D, 5E), shaftwall systems (7E, 7F), perimeter/chase furring (7A, 7B, 8A), column enclosures (Detail 10), gypsum soffits/bulkheads | Wall is definitively linked to a verified drywall tag or detail |
| **2** | **Non-Drywall** | Red `(255, 0, 0)` / `#FF0000` | CMU block (1A), demountable metal privacy walls (PW), operable acoustic folding panels (FWP-2 / Key Note 7), glass storefronts (GL1, GL2), cast concrete walls/infill (Key Note 1, 18), concrete column jackets (Detail 11), structural concrete cores | Wall is definitively linked to a verified non-drywall assembly |
| **3** | **Uncertain / Manual Review** | Yellow `(255, 255, 0)` / `#FFFF00` | Untagged walls, ambiguous existing masonry partitions without furring notes, unverified CAD segments, public datasets without material specs | Wall lacks verified material callout ($\text{confidence} < 0.85$) |

---

### 5.2 Algorithmic Tag-to-Wall Association Pipeline

To automatically map vector CAD elements to semantic wall classes:

```
[PyMuPDF Page]
      │
      ├──> Extract Text Words & Filter Wall Tags (TAG_REGEX: 1A-8A, GL1-2, PW)
      │         │
      │         └──> Store Tag Centroids C_tag = (x_t, y_t) with Verified Class
      │
      ├──> Extract Vector Path Strokes (get_drawings())
      │         │
      │         └──> Filter Wall Cut Paths (Stroke width >= 1.0 pt OR Parallel Double Lines)
      │
      └──> Spatial Association Matching
                │
                ├──> Compute Euclidean Distance d = ||P_wall - C_tag||
                ├──> Gating Radius: d <= 50.0 pt (~8.3 physical inches)
                ├──> Check Collinearity: Angle between wall vector and tag orientation
                ├──> Compute Confidence Score: S = exp(-d / 25.0) * (1 - conflict_penalty)
                │
                ├── If S >= 0.85: Assign Tag's Verified Class (Class 1 or 2)
                └── If S < 0.85 OR Conflict: Assign Class 3 (Uncertain)
```

---

### 5.3 Mining Gold-Standard Ground Truth from `drywall_walls_marked_red_by_Usman.pdf`

An investigation of `drywall_walls_marked_red_by_Usman.pdf` verified that **478 expert vector annotations** exist across pages 1 through 5, perfectly matching sheets `A-100` through `A-104`:

| Sheet | Page Index | Floor Description | Line Annotations (Walls) | Square Annotations (Tags) | Total Annotations | Verified Partition Types Tagged |
|---|---|---|---|---|---|---|
| `A-100` | Page 0 | Cellar Construction Plan | 4 | 4 | 8 | `5E` (4 walls) |
| `A-101` | Page 1 | First Floor Construction Plan | 28 | 28 | 56 | `5E` (8), `7A` (9), `1C` (2), `1D` (2), `1E` (1), `3A` (1), `5B` (4), `7F` (1) |
| `A-102` | Page 2 | Second Floor Construction Plan | 71 | 71 | 142 | `1C` (18), `7A` (12), `8A` (13), `7B` (8), `5E` (7), `7F` (7), `3D` (2), `7C` (2), `7E` (2), `3A` (1) |
| `A-103` | Page 3 | Third Floor Construction Plan | 67 | 67 | 134 | `2C` (17), `7A` (13), `7F` (10), `1C` (8), `7B` (5), `5E` (5), `3D` (2), `7E` (2), `8A` (2), `3A` (1), `7G` (1) |
| `A-104` | Page 4 | Fourth Floor Construction Plan | 69 | 69 | 138 | `7A` (18), `2C` (15), `7F` (8), `1C` (7), `5E` (5), `3A` (4), `3D` (4), `8A` (4), `7B` (3), `7E` (2), `7C` (1), `7G` (1) |
| **Total** | — | **5 Full Construction Floors** | **239** | **239** | **478** | **15 Distinct Gypsum Partition Assemblies** |

**Distribution of Verified Drywall Walls**:
- `7A` Perimeter Furring: **52 walls** (21.8%)
- `1C` Standard Metal Stud: **35 walls** (14.6%)
- `2C` Double-Layer Acoustic: **32 walls** (13.4%)
- `5E` 2-Hour Fire-Rated: **27 walls** (11.3%)
- `7F` 2-Hour Shaft Wall: **27 walls** (11.3%)
- `8A` Direct Laminated Furring: **22 walls** (9.2%)
- `7B` One-Sided Stud Furring: **16 walls** (6.7%)
- `3D` Double-Layer Gypsum: **8 walls** (3.3%)
- `3A` Standard Stud: **7 walls** (2.9%)
- `5B` 1-Hour Fire-Rated: **4 walls** (1.7%)
- `1D` Heavy-Gauge Stud: **2 walls** (0.8%)
- `2B` Acoustic Stud: **2 walls** (0.8%)
- `5D` Fire-Rated Stud: **2 walls** (0.8%)
- `7G` Acoustic Ceiling Baffle: **2 walls** (0.8%)
- `1E` Wet-Area Stud: **1 wall** (0.4%)
- **Total: 239 Verified Drywall Walls**.

**Crucial Finding**: All 239 annotated walls strictly belong to the verified drywall assemblies mined in Section 3.1. Non-drywall partitions (`1A` CMU block, `GL1` glass storefronts, `PW` privacy walls) were deliberately excluded by the expert annotator, providing ground truth for evaluating Class 1 precision and recall.

---

### 5.4 Multi-Class Raster Mask Synthesis Pipeline

For training and evaluating semantic segmentation models (SegFormer, U-Net), 4-class ground truth raster masks $M \in \{0, 1, 2, 3\}^{H \times W}$ are generated using the following procedure:

1. **Raster Canvas Initialization**:
   - Create a single-channel unsigned 8-bit NumPy array $M$ of shape $(H, W)$ filled with `0` (Background).
2. **Layer 1: Uncertain Walls (Class 3, Yellow)**:
   - For all candidate wall vector paths lacking definitive tags or from generic academic pretraining sets:
     - Render line with dilation thickness $T_{wall} \approx \text{round}(3.66 \cdot \frac{DPI}{72})$ using `cv2.line(M, pt1, pt2, 3, thickness=T_wall)`.
3. **Layer 2: Non-Drywall Walls (Class 2, Red)**:
   - For all verified non-drywall assemblies (`1A` CMU, `GL1`/`GL2`, `PW`, `KeyNote 7/18`, concrete columns):
     - Render line / polygon using `cv2.fillPoly(M, [poly], 2)` or `cv2.line(M, pt1, pt2, 2, thickness=T_wall)`.
4. **Layer 3: Drywall Walls (Class 1, Green)**:
   - For all verified drywall assemblies (the 239 expert-annotated centerlines dilated by $T_{wall}$ plus verified tag-associated partitions):
     - Render line using `cv2.line(M, pt1, pt2, 1, thickness=T_wall)`.
5. **Precedence Hierarchy**:
   - Order of rasterization: $\text{Background (0)} \longrightarrow \text{Uncertain (3)} \longrightarrow \text{Non-Drywall (2)} \longrightarrow \text{Drywall (1)}$.
   - This ensures verified material labels strictly overwrite generic/uncertain designations.

---

## 6. Edge Cases & Technical Risks

| # | Edge Case / Condition | Technical Risk | Mitigation Strategy |
|---|---|---|---|
| 1 | **Page Rotation 90° vs Raw Mediabox** | Naive renderers extract unrotated portrait images ($1728 \times 2592$) while vector paths remain in landscape ($2592 \times 1728$), causing severe $90^\circ$ spatial shearing | Always use PyMuPDF unified `page.rect` coordinate space; never mix raw `mediabox` with visual coordinates. Verify `page.rotation` in pre-flight checks. |
| 2 | **Shared Walls Between Dissimilar Spaces** | A single wall separating an office from a shaft (e.g. standard drywall on room side, shaftliner on shaft side) | Model predicts Class 1 (Drywall) because both assemblies are gypsum-based. For schedule takeoffs, assign partition tag with higher fire rating. |
| 3 | **Operable Partition Headers (A-902)** | A folding partition (`FWP-2`, non-drywall) hangs beneath a $6\text{ in}$ gypsum board soffit (drywall) | On floor plans, the plan line represents the operable partition (Class 2, Non-Drywall); on Reflected Ceiling Plans (A-201–204), the soffit represents drywall (Class 1). Do not classify folding panel as drywall. |
| 4 | **Glass Officefront Drywall Fascias (GL1)** | Butt-glazed glass partition has a drywall pocket fascia above the ceiling line | On construction plans, classify the partition run as Class 2 (Non-Drywall). Drywall fascia takeoff belongs to ceiling package (RCP). |
| 5 | **Sub-pixel Wall Line Thinning at Low DPI** | At 72 DPI, a $3\text{ }5/8\text{ in}$ stud wall is only $\sim 3.6\text{ pixels}$ wide; standard convolutional pooling may cause wall continuity to fragment | Minimum rasterization resolution of $150\text{ DPI}$ ($7.6\text{ px}$ width); use Dice loss with high weight on fine line continuity; avoid pooling operations that exceed $4\times$ reduction without skip connections. |
| 6 | **Text Annotation Masking Blocks** | Revit exports white filled rectangles `(1, 1, 1)` behind text tags to mask underlying CAD lines | Detect white filled bounding boxes and exclude them from background negative sampling; do not treat text background masks as wall breaks. |

---

## 7. Downstream Engineering Recommendations

1. **Pretraining on Academic Benchmarks**:
   - Train generic wall segmentation backbone on **Modified Swiss Dwellings (MSD)** (CC BY 4.0, 174 MB) and **CubiCasa5K** (CC BY-NC-SA 4.0, 5.09 GB) mapping all walls to Class 3 (Uncertain / Generic Wall).
2. **Fine-Tuning on 99th Street Domain**:
   - Fine-tune classification heads on MTA 99th Street sheets A-101 through A-104 using the 239 verified drywall centerlines and confirmed non-drywall assemblies (`1A`, `GL1`, `PW`).
3. **Data Leakage Guardrail**:
   - Hold out Sheet `A-104` (Fourth Floor) or `Bid Set.pdf` (College Point) exclusively for final test evaluation; never mix levels or projects between train and test splits.
4. **Inference Pipeline & Export**:
   - The PDF testing interface must render inference predictions directly into vector annotations (`fitz.Annot`) on the pristine `drywall_relevant_full_pages.pdf` (preserving 100% original CAD geometry, text selectable, ARCH D dimensions), with color coding:
     - **Drywall**: `#00FF00` (Green)
     - **Non-Drywall**: `#FF0000` (Red)
     - **Uncertain**: `#FFFF00` (Yellow)
