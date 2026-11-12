# Handoff Report — survey_spec_miner_2

**Date:** 2026-11-08  
**Sender:** survey_spec_miner_2 (Vector & Schedule Spec Miner)  
**Recipient:** 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a (orchestrator)  
**Role:** Specification Miner for Requirements R1 & R4  
**Integrity Mode:** Development  
**Artifact Generated:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_2\report.md`  

---

## 1. Observation

1. **Reference PDF Properties:**
   - File Path: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
   - Page Count: 71 pages.
   - Dimensions & Rotation: Unrotated MediaBox `Rect(0.0, 0.0, 1728.0, 2592.0)`, rotation: `90` degrees clockwise, rendering to landscape pixmap `2592.0 x 1728.0` pt at 72 DPI (5400 x 3600 at 150 DPI).
   - Document Title / Stamp: Cover Page 0 contains verbatim:
     ```text
     CONTRACT C - 48526
     99TH STREET PROJECT LOCATION
     PROGRESS SET 95% CDs 10/02/2026
     ARCHITECTURAL INTERIOR SET
     ```
   - Producer / Creator: `Bluebeam Brewery 5.0` / `Bluebeam Stapler 21.7.0.12289`.

2. **Partition Schedule Sheets A-900 & A-901:**
   - Located on Page 62 (Sheet A-900: `PARTITION TYPES SHEET I`) and Page 63 (Sheet A-901: `PARTITION TYPES SHEET II`).
   - All 24 assembly details discovered verbatim:
     - Sheet A-900: `1A` (1 HR RATED), `1B`, `1C`, `1D`, `1E`, `2B`, `2C`, `3A`, `3D`, `5B` (1 HR RATED), `5D`, `5E` (2 HR RATED).
     - Sheet A-901: `7A`, `7B`, `7C`, `7E`, `7F` (2 HR RATED), `7G`, `8A`, `GL1`, `GL2`, `09`, `10`, `11`.
   - Verbatim Callout for Detail 1A on Sheet A-900 (Page 62 block text):
     ```text
     6" FIRE RATED CMU
     ```
   - Verbatim Callout for Detail 5E on Sheet A-900:
     ```text
     (2) LAYER OF 5/8" GYPSUM WALL
     3 5/8" 20 GA. METAL STUDS @ 16"
     ```
   - Verbatim Callout for Detail GL1 on Sheet A-901 (Page 63 block text):
     ```text
     INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM
     ```

3. **Partition Tags on Floor Plans:**
   - Extracted 233 tag occurrences across floor plan sheets (A-100 to A-105, A-200, A-201).
   - Tag frequencies: 7A (52), 1C (35), 5E (27), 7F (26), 8A (21), GL1 (18), 7B (16), 3D (8), 3A (7), 7E (6), 5B (4), 7C (3), 1D (2), 2B (2), 5D (2), 7G (2), 1E (1), GL2 (1).
   - Geometric symbol: 11.2 pt x 11.3 pt square / box vector outline surrounding text.
   - Leader line: 0.48 pt stroked line segments connecting box edge to wall centerline/face (e.g. Tag 5E leader line from `(772.44, 1094.52)` to `(772.44, 1082.76)`).

4. **Coordinate Discrepancy & Mapping:**
   - `page.get_drawings()` and `page.get_text()` return unrotated coordinates in `[0..1728, 0..2592]`.
   - `page.get_pixmap()` renders rotated raster `[0..2592*scale, 0..1728*scale]`.
   - Forward transformation matrix: $M = \begin{bmatrix} 0 & -S & 2592 \cdot S \\ S & 0 & 0 \\ 0 & 0 & 1 \end{bmatrix}$.
   - Inverse transformation matrix: $M^{-1} = \begin{bmatrix} 0 & 1/S & 0 \\ -1/S & 0 & 2592 \\ 0 & 0 & 1 \end{bmatrix}$.
   - Numerical roundtrip verified: point $(500.0, 1200.0) \to (1392.0, 500.0) \to (500.0, 1200.0)$ with zero error.

5. **Existing Detectors & Prior Errors:**
   - In `C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf` (Page 1, Annotation 1), Tag 1A was tagged as:
     `DRYWALL TAG: 1A\nProbability: 95.0%`.
   - In `Drywall_QTO_SOP.pdf` (Page 34, Part 7) and `wall_partition_data_json.pdf`:
     "The visible detail explicitly identifies 6 inch fire-rated CMU masonry block; do not classify this as a standard gypsum-stud partition!"

---

## 2. Logic Chain

1. From Observation 1, the reference PDF has 71 pages, 90° rotation, and 1728x2592 pt dimensions. PyMuPDF extracts vectors in native unrotated space, while images are rendered rotated. Therefore, a strict reversible affine transformation ($M$ and $M^{-1}$) is mathematically mandatory for any alignment between vector geometries and raster segmentation masks (Observation 4).
2. From Observation 2, Sheet A-900 and A-901 contain 24 distinct assembly details. Detail 1A explicitly specifies `6" FIRE RATED CMU` (Concrete Masonry Unit), Detail GL1/GL2 specifies glass systems, and Detail 11 specifies concrete encasement.
3. From Observation 5, previous automated detectors erroneously classified Tag 1A as Drywall with 95% confidence. Because CMU, glass, and concrete are non-drywall trades, classifying them as drywall produces massive takeoff and material ordering errors.
4. Therefore, classification MUST follow verified material evidence: Drywall (Green) for gypsum/GWB, Non-Drywall (Red) for CMU/glass/concrete, and Uncertain (Yellow) for ambiguous or unassigned elements.
5. From Observation 3, 233 tag instances appear on floor plans enclosed in 11.2x11.3 pt squares with leader lines or direct proximity. Walls without leader lines or proximity must not be guessed, per Requirement R1.
6. Therefore, unmatched walls must remain `unassigned` and be classified as `Uncertain` (Yellow).
7. To enforce human oversight, the pipeline must export the 14-column schedule CSV and halt execution with a lockfile/exit code, allowing downstream classification (M5) to proceed only with an approved CSV file.

---

## 3. Caveats

1. The reference drawing set is explicitly stamped `PROGRESS SET 95% CDs 10/02/2026` rather than an approved construction set; dimensions, callouts, or notes may undergo revisions in 100% CD releases.
2. The 71 pages represent a single architectural project; all performance metrics measured on it reflect single-project calibration rather than cross-domain generalization.
3. Certain minor partition details (e.g., Detail 09 TV Screen) do not specify standard gypsum wallboard thickness or stud gauge and are correctly reserved as `Uncertain`.
4. No project source code was modified during this survey, adhering strictly to read-only integrity constraints.

---

## 4. Conclusion

The technical specifications and interface contracts for Requirements R1 and R4 are fully mined, verified with empirical code probes, and documented in `report.md`:
1. Vector extraction pipeline must use PyMuPDF `get_drawings()` and `get_text()` with the verified 90° CW affine matrix `rot_x = (2592 - y)*S, rot_y = x*S`.
2. Schedule parsing must extract all 24 partition types across A-900 and A-901 into the specified 14-column CSV schema.
3. Spatial matching must enforce strict leader-line ray casting and 25 pt buffer proximity, assigning unmatched walls to `unassigned` without guessing.
4. Classification must categorize gypsum assemblies as Drywall (Green), CMU/glass/concrete as Non-Drywall (Red), and unassigned/ambiguous walls as Uncertain (Yellow).
5. A mandatory execution stop with exit code 2 and lockfile `REVIEW_REQUIRED.lock` must pause processing until `partition_schedule_mapping.approved.csv` is reviewed and confirmed.

---

## 5. Verification Method

To independently verify all observations and conclusions, execute the following PowerShell commands:

```powershell
# 1. Verify PDF properties (71 pages, 90 deg rotation, 1728x2592 pt)
python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print(f'Pages: {len(doc)}, Rect: {doc[0].rect}, Rotation: {doc[0].rotation}')"

# 2. Verify Sheet A-900 (Page 62) and A-901 (Page 63) partition titles
python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print('A-900:', [b[4].strip()[:30] for b in doc[62].get_text('blocks') if 'PARTITION' in b[4]]); print('A-901:', [b[4].strip()[:30] for b in doc[63].get_text('blocks') if 'PARTITION' in b[4]])"

# 3. Verify Tag 1A is 6" CMU Masonry (Non-Drywall)
python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); print([l.strip() for l in doc[62].get_text().splitlines() if 'CMU' in l])"

# 4. Verify reversible coordinate roundtrip
python -c "import fitz; doc=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'); p=doc[14]; mat=fitz.Matrix(1,1).prerotate(90); M=mat*fitz.Matrix(1,0,0,1,-(p.mediabox*mat).x0,0); Minv=~M; pt=fitz.Point(500,1200); assert abs((pt*M*Minv).x - pt.x) < 1e-4; print('Coordinate bijection assertion passed!')"
```

Invalidation Condition:
If a future drawing revision alters the rotation angle from 90° or changes Detail 1A from CMU to drywall studs, the transformation matrix and classification rule for 1A must be updated accordingly.
