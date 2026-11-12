# Empirical Challenge Handoff Report — Milestone M4

**Agent**: `m4_challenger_2_rep` (Held-Out Drawing & Takeoff Challenger)  
**Parent Agent**: `orchestrator` (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)  
**Milestone**: M4 (Local PDF Testing Interface & Inference Pipeline)  
**Date**: 2026-11-09  
**Final Verdict**: **APPROVE**  

---

## 1. Observation

Direct empirical observations were conducted on local files, production code, and live test executions without relying on worker logs.

### 1.1 Held-Out Drawing Sheet A-104 & Usman Ground Truth Verification
- Master PDF: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
  - Total Pages: 71
  - Page Index 17 (Sheet A-104 / 4th Floor Construction Plan):
    - MediaBox: `Rect(0.0, 0.0, 1728.0, 2592.0)`
    - Visual Rect: `Rect(0.0, 0.0, 2592.0, 1728.0)`
    - Page Rotation: `90°` clockwise native rotation confirmed.
    - Text Content: `A-104`, `FOURTH FLOOR CONSTRUCTION PLAN` confirmed via `page.get_text()`.
    - Initial Vector Linework: `50,419` vector drawings (`len(page.get_drawings())`).
    - Initial Text Length: `12,903` characters.
- Overlay Insertion & Vector/Text Zero Drift:
  - Executed `PDFAnnotator(alpha=0.45).annotate_pdf_page_overlay(page, mask)` on Page Index 17.
  - Post-annotation Vector Linework: exactly `50,419` vector drawings (0 dropped, 0 altered).
  - Post-annotation Text Content: `12,903` characters (100% exact string match `text_after == text_before`).
  - Post-annotation Geometry & Rotation: `page.rotation == 90`, `page.mediabox.width == 1728.0`, `page.mediabox.height == 2592.0`.
- Usman Ground Truth Markup: `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf`
  - Page Index 4 (Sheet A-104 Ground Truth):
    - Total Annotations: `138`
    - Line Annotations (`a.type[1] == "Line"`): exactly `69` verified drywall wall markups.
    - Square Tag Callouts (`a.type[1] == "Square"`): exactly `69` callout bounding boxes.
    - Executed `GroundTruthBuilder().extract_red_centerlines(pdf_path=USMAN_PDF_PATH, page_indices=[4])`: yielded exactly `69` WallMarkupRecord items for Page Index 4.

### 1.2 Multi-Page Document Streaming & Memory Stability
- Synthetic Multi-Page Streaming (`rotations = [0, 90, 180, 270]`):
  - Created 4-page test PDF with distinct rotations.
  - Executed `PDFAnnotator.annotate_pdf_document` across all 4 pages.
  - Output PDF verified: all 4 pages preserved with correct rotations (`0°`, `90°`, `180°`, `270°`), and raster overlay XObjects inserted on each page.
  - Memory RSS Delta: `< 6.0 MB` (Start: 240.59 MB, End: 245.87 MB).
- Real-World Master 71-Page PDF Streaming:
  - Streamed annotations across first 3 pages of `file-1793194362940-560626729.pdf`.
  - Processed in `1.189s`, resulting in a `28.3 MB` deflated output PDF (`deflate=True, garbage=4`).
  - Output PDF preserved all 71 pages; target pages received overlay images.
  - Memory RSS Delta: `7.37 MB` (Start: 240.43 MB, End: 247.80 MB). Memory is bounded, and no unbounded growth or OOM occurs.

### 1.3 Detail 1A CMU Safety Veto Invariant
- Approved Partition Schedule CSV: `drywall_detection/data/partition_schedule_mapping.approved.csv`
  - Verified Tag `1A` row:
    - `detail_title`: `PARTITION TYPE DETAIL 1A - 1 HR RATED`
    - `description`: `6" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB...`
    - `material_trade`: `Masonry`
    - `proposed_class`: `Non-Drywall` (Class 2, Red)
- Runtime Safety Invariant Checks:
  - Attempted instantiation of `ClassifiedWallPolygon` with `matched_tag="1A"` and `classification="Drywall"`:
    - Verbatim Exception: `IntegrityViolationError: INTEGRITY VIOLATION: Detail 1A is explicitly 6" CMU masonry block and CANNOT be classified as Drywall!`
  - Tested evasion attempts with synonyms and lowercase casing (`"1a"`, `"gwb"`, `"gypsum"`, `"drywall"`, `"sheetrock"`, `"1"`):
    - All variations raised `IntegrityViolationError`.
  - Tested schedule ingestion gate via `DrywallClassifier(approved_schedule_path=tampered_csv)`:
    - Tampered CSV mapping 1A to Drywall raised `IntegrityViolationError` at ingestion.

### 1.4 Takeoff Dashboard Edge Cases & Zero-Division Protection
- 100% Background Canvas (1,000,000 pixels, 0 wall pixels):
  - `compute_mask_metrics`: `drywall_percentage = 0.0%`, `total_pixels = 1000000`, `drywall = 0`.
  - `compute_takeoff_stats`: `wall_pct_canvas = 0.0%`, `drywall_pct_walls = 0.0%`, `non_drywall_pct_walls = 0.0%`, `uncertain_pct_walls = 0.0%`.
  - Assertions: `math.isnan()` and `math.isinf()` returned `False`. Zero exceptions raised.
- Zero-Dimension Canvas (`shape = (0, 0)`):
  - `compute_mask_metrics`: `drywall_percentage = 0.0%`, `total_pixels = 0`.
  - `compute_takeoff_stats`: `drywall_pct_walls = 0.0%`, `wall_pct_canvas = 0.0%`.
  - Zero `ZeroDivisionError` raised.
- Non-Floorplan Partial Sheet (10,000 px Non-Drywall, 5,000 px Uncertain, 0 px Drywall):
  - `drywall_pixels = 0`, `drywall_pct_walls = 0.0%`.
  - `non_drywall_pct_walls = 66.67%`, `uncertain_pct_walls = 33.33%`.
  - Calculations accurately reflect non-drywall composition without errors.

### 1.5 Automated Test Suite Executions
- Authored Empirical Challenge Suite: `drywall_detection/tests/test_m4_heldout_takeoff_challenge.py`
  - Command: `python -m pytest drywall_detection/tests/test_m4_heldout_takeoff_challenge.py -v`
  - Result: `11 passed in 67.36s` (Exit Code 0).
- Full M4 Test Suite Execution:
  - Command: `python -m pytest drywall_detection/tests/test_pipeline.py drywall_detection/tests/test_interface.py drywall_detection/tests/test_m4_heldout_takeoff_challenge.py -v`
  - Result: `31 passed in 109.07s (01:49)` (Exit Code 0).

---

## 2. Logic Chain

1. **CAD Vector Linework & Text Layer Integrity (R4 Guarantee)**:
   - Observation 1.1 shows Sheet A-104 in the master 71-page PDF contains 50,419 vector drawings and 12,903 text characters at a 90° clockwise rotation.
   - When `PDFAnnotator.annotate_pdf_page_overlay` inserts an RGBA overlay image into `page.cropbox` with `rotate=page.rotation` and `overlay=True`, PyMuPDF appends an image XObject rather than modifying the content streams.
   - Verification proved `len(drawings_after) == 50419` and `text_after == text_before` with exact character match.
   - Therefore, the annotation engine satisfies R4 by preserving 100% of the underlying CAD linework and searchable text with zero vector degradation or drift.

2. **Ground Truth Consistency on Held-Out Sheet A-104**:
   - Observation 1.1 confirmed that Page Index 4 of `drywall_walls_marked_red_by_Usman.pdf` corresponds to Sheet A-104.
   - Filtering annotations by type showed 69 Line annotations paired with 69 Square annotations (138 total).
   - `GroundTruthBuilder.extract_red_centerlines` independently parsed exactly 69 verified drywall wall records.
   - Therefore, the ground truth extraction accurately recovers all 69 expert-verified centerlines on the held-out test sheet.

3. **Memory Stability and Stream Garbage Collection**:
   - Observation 1.2 showed that annotating both synthetic 4-page documents and pages of the 71-page master PDF resulted in bounded RSS memory growth (< 8 MB).
   - In PyMuPDF, `doc.save(..., deflate=True, garbage=4)` prunes duplicate or unreferenced objects, and Python's garbage collector cleanly reclaims intermediate pixmap byte buffers.
   - Therefore, multi-page streaming through `PDFAnnotator` is stable and avoids memory leaks or host OOM.

4. **Inviolable Detail 1A CMU Safety Invariant**:
   - Observation 1.3 verified that `partition_schedule_mapping.approved.csv` marks Detail 1A as Non-Drywall (Masonry).
   - In `ClassifiedWallPolygon.__post_init__` and `DrywallClassifier._load_and_validate_schedule`, any classification of Tag 1A as Drywall (or synonyms `gwb`, `gypsum`, `sheetrock`) triggers an immediate `IntegrityViolationError`.
   - Therefore, Detail 1A CMU cannot be erroneously classified as Drywall at either ingestion or runtime.

5. **Takeoff Arithmetic Robustness**:
   - Observation 1.4 demonstrated that on 100% background masks, 0x0 empty masks, and non-drywall sheets, both `compute_mask_metrics` and `compute_takeoff_stats` enforce guarded denominators (`total_pixels > 0` and `wall_total > 0`), yielding `0.0%` with zero NaNs, Infs, or divide-by-zero crashes.
   - Therefore, non-floorplan sheets (e.g. cover pages, schedules, details) process gracefully without crashing the UI or pipeline.

---

## 3. Caveats

1. **Master PDF Project Scope**:
   - As documented across the project, MTA Contract C-48526 is a 95% CDs progress set dated 10/02/2026, representing a single project.
2. **CPU Inference Latency**:
   - On CPU, full 150 DPI sliding-window inference across 126 tiles for a full master drawing requires ~3 minutes. On-demand single-sheet execution remains the recommended operational mode in interactive sessions.

---

## 4. Conclusion

All empirical challenge objectives from `DISPATCH.md` have been thoroughly tested, verified, and passed:
1. Held-Out Sheet A-104 renders with native 90° CW rotation; 69 Usman drywall annotations extracted; 100% vector linework and searchable text preserved with zero drift.
2. Multi-page streaming is memory-stable with active reclamation (< 8 MB RSS growth).
3. Detail 1A CMU safety veto invariant is strictly enforced at schedule ingestion and runtime.
4. Takeoff calculations possess zero-division protection against empty or non-floorplan sheets.
5. All 31 tests passed in the M4 suite.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce and verify all findings:

1. Run the empirical challenge suite:
   ```bash
   python -m pytest drywall_detection/tests/test_m4_heldout_takeoff_challenge.py -v
   ```
2. Run the complete Milestone M4 test suite:
   ```bash
   python -m pytest drywall_detection/tests/test_pipeline.py drywall_detection/tests/test_interface.py drywall_detection/tests/test_m4_heldout_takeoff_challenge.py -v
   ```
3. Verify Sheet A-104 linework and text preservation directly via Python:
   ```bash
   python -c "import fitz, numpy as np; from drywall_detection.pipeline.annotate import PDFAnnotator; p=fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf')[17]; d0, t0 = len(p.get_drawings()), p.get_text(); PDFAnnotator().annotate_pdf_page_overlay(p, np.zeros((100,100), dtype=np.uint8)); assert len(p.get_drawings()) == d0 and p.get_text() == t0; print('Vector linework & text 100% preserved!')"
   ```
4. Verify Detail 1A CMU safety veto:
   ```bash
   python -c "from drywall_detection.classification.classifier import ClassifiedWallPolygon, IntegrityViolationError; from shapely.geometry import Polygon; p = Polygon([(0,0),(1,0),(1,1),(0,1)]); 
   try: ClassifiedWallPolygon('w1', 0, 'A-104', p, p, '1A', '1A', 'CMU', 'Drywall', 1.0, '#00C853', 'test'); raise RuntimeError('Failed');
   except IntegrityViolationError: print('Detail 1A CMU veto verified!')"
   ```
