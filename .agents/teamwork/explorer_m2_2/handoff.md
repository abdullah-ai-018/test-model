# Milestone M2 Handoff Report: Dataset Unifier & Mask Generation Architecture

**Document ID:** HANDOFF-M2-PREPARER-001  
**Author:** explorer_m2_2 (M2 Mask Unifier Explorer)  
**Date:** 2026-11-07  
**State Folder:** `.agents/teamwork/explorer_m2_2/`  
**Working Directory:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation

1. **Existing Preparer Stub and Split Manager Facade**:
   - Inspected `drywall_detection/data/preparer.py` (lines 1–28). It currently contains only a 28-line facade importing and re-exporting split integrity symbols from `drywall_detection.datasets.split_manager`:
     ```python
     from drywall_detection.datasets.split_manager import (
         DrawingSplitManager, SplitManifest, TileRecord, SplitStats,
         SplitLeakageError, InsufficientGroupsError, InvalidSplitRatioError,
         verify_split_isolation,
     )
     ```
   - No direct imports of `preparer` exist in the test suite yet (confirmed via search for `"preparer"`), but `PROJECT.md` section 4.3 specifically cites `drywall_detection.data.preparer` as the canonical entry point for the data split protocol.

2. **Full Baseline Test Suite Passing**:
   - Executed `pytest drywall_detection/tests/ -v`.
   - Result: Exactly **261 passed, 1 warning in 82.16s** across all unit and stress test files:
     ```
     ================== 261 passed, 1 warning in 82.16s (0:01:22) ==================
     ```
   - Zero test failures exist in the workspace. Any implementation of `preparer.py` must retain re-exports to preserve 100% test pass rates.

3. **Modified Swiss Dwellings (MSD) Annotation Schema**:
   - Inspected `drywall_detection/data/dataset_licensing_audit.json` (lines 35–65):
     `official_sources`: `https://doi.org/10.5281/zenodo.7788422`, `https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched`.
     `wall_annotation_format`: `"WKT Polygons (entity_type='separator', entity_subtype='WALL') and struct_in raster masks"`.
     `drywall_labels_available`: `false`.
     `archive_size_mb`: `173.8` (compact Parquet format).
   - Confirmed via official schema documentation and paper (Standfest et al., ECCV 2024, arXiv:2407.10121):
     MSD entity records are stored in columnar Apache Parquet format with columns `site_id`, `building_id`, `floor_id` / `drawing_id`, `entity_type`, `entity_subtype`, and `geometry` (WKT string in metric Cartesian coordinates).

4. **Coordinate System Discrepancy & Mathematical Transformations**:
   - Inspected `drywall_detection/utils/coords.py` (lines 38–195):
     The project handles coordinate transformations between CAD vector points and visual pixels.
     In WKT geometries, coordinates are in meters with Cartesian convention ($+Y$ pointing upwards).
     In image rasters, pixel row index 0 is at the top ($+Y$ pointing downwards).
     Without Y-reflection and aspect-ratio preserving scaling, geometries will rasterize inverted or distorted.

5. **Python Environment & Library Availability**:
   - Executed probe commands in the local Python 3.10 environment:
     `pyarrow` 20.0.0, `pandas` 2.2.2, `shapely` 2.1.1, `opencv-python` (cv2) 4.11.0, and `torch` 2.1.0+cpu are installed and fully operational.
   - Verified that `shapely.make_valid()` correctly converts self-intersecting bowtie polygons into valid `MultiPolygon` collections.
   - Verified that `cv2.fillPoly` correctly evacuates interior holes when rasterizing with background color `0`.

---

## 2. Logic Chain

1. **From Observation 1 & 2 (Clean Baseline & Split Contract)**:
   - `preparer.py` must become the comprehensive dataset unifier, vector parser, and mask rasterizer while continuing to re-export `DrawingSplitManager`, `SplitManifest`, `TileRecord`, `verify_split_isolation`, etc.
   - This ensures full backward compatibility with the 261 existing tests while providing all required unifier functionalities.

2. **From Observation 3 (MSD Format & Guardrail R2)**:
   - In MSD Parquet tables, entities must be filtered using:
     `entity_type.lower() == "separator"` AND `"wall" in entity_subtype.lower()`.
   - Because MSD annotations lack US CSI drywall material specifications, Rule R2 mandates that all generic MSD walls must be rasterized as `Class 3 (Uncertain)` in semantic multiclass masks, and `Class 1 (Wall)` in binary masks.
   - Grouping entities by `site_id` (or `building_id`) directly provides the project key needed by `DrawingSplitManager` for zero-leakage 70/15/15 partitioning.

3. **From Observation 4 & 5 (Coordinate Geometry & Rasterization)**:
   - For an arbitrary floor plan with bounding box $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$, the scaling factor must be uniform:
     $$s = \min\left(\frac{W_{\text{px}} - 1}{\text{span}_x}, \frac{H_{\text{px}} - 1}{\text{span}_y}\right)$$
     with symmetric letterboxing offsets $\text{pad}_x$ and $\text{pad}_y$.
   - Cartesian-to-raster inversion ($py = (H - 1) - [\text{pad}_y + (y - y_{\min}) \cdot s]$) correctly aligns North-up vector drawings with standard image coordinates.
   - Using `cv2.fillPoly` on exterior rings followed by interior hole evacuation guarantees that wall cavity boundaries and courtyard cutouts are geometrically exact.

4. **From Observation 5 (Defensive Sanitization & Deduplication)**:
   - Real-world CAD/GIS vector data contains degenerate lines, NaN coordinates, zero-area slivers, and duplicate overlapping segments.
   - Applying `shapely.make_valid()`, filtering by minimum area ($\ge 10^{-4} \text{ m}^2$), deduplicating via 3-decimal coordinate hashing, and enforcing a 50-pixel density threshold eliminates corrupted drawings.
   - Pure blank white drawings ($\text{std} < 2.0$, $\text{mean} > 250$) are rejected, while drawings containing linework but zero walls are retained as hard negatives up to a $15\%$ ceiling.

---

## 3. Caveats

1. **Single-Project Progress Set Boundary**:
   - The reference PDF (`file-1793194362940-560626729.pdf`) represents MTA Contract C-48526 (99th Street Phase 2 Interior Set), stamped `"PROGRESS SET 95% CDs 10/02/2026"`. It is an interim progress set from a single facility and cannot prove cross-domain generalization.
2. **Download Separation**:
   - This handoff architects the unification and mask generation module (`preparer.py`). Automated downloading and network fetching are architected by peer agent `explorer_m2_1` (`downloader.py`).
3. **No Direct Source Modification**:
   - As an explorer agent with read-only permissions, no files in `drywall_detection/` have been modified. The complete, exact code blueprint is documented in `.agents/teamwork/explorer_m2_2/analysis.md` and summarized below.

---

## 4. Conclusion

The dataset unifier and mask generation architecture for Milestone M2 is fully specified, mathematically verified, and documented.

### Deliverables Produced:
1. **Analysis Report**: `.agents/teamwork/explorer_m2_2/analysis.md` (complete architectural analysis, mathematical formulations, 6 sanitization gates, and exact code blueprint).
2. **Standardized Representation**:
   - Input floor plan image: RGB uint8 $(H, W, 3)$ with aspect-ratio preserving letterboxing.
   - Binary mask: uint8 $(H, W)$ with $\{0, 1\}$.
   - Semantic multiclass mask: uint8 $(H, W)$ with $\{0, 1, 2, 3\}$ in PIL Mode `'P'` 256-color indexed PNG.
3. **MSD Ingestion Engine**: Complete Parquet/CSV parser extracting `site_id`, `building_id`, `floor_id`, filtering `separator` / `WALL`, and mapping to `Class 3 (Uncertain)`.
4. **Geometric Rasterizer**: Exact aspect-ratio preserving affine mapping with hole evacuation via `cv2.fillPoly` and fallback synthetic CAD linework generation.
5. **Filtering & Deduplication**: 6 defensive gates rejecting degenerates, invalid topologies, and uninformative blanks while capping hard negatives at $15\%$.
6. **CLI Specification**: Standalone entry point `python -m drywall_detection.data.preparer` with comprehensive argument parsing.

---

## 5. Verification Method

To independently verify the architecture and prepare for implementation:

1. **Verify Baseline Test Suite Passes**:
   ```powershell
   pytest drywall_detection/tests/ -v
   ```
   *Expected Result*: All 261 tests pass.

2. **Verify Python Dependencies**:
   ```powershell
   python -c "import pyarrow, pandas, shapely, cv2, torch; print('Dependencies OK')"
   ```
   *Expected Result*: `Dependencies OK`.

3. **Verify WKT Rasterization & Hole Evacuation Invariant**:
   ```powershell
   python -c "import shapely.wkt, cv2, numpy as np; poly = shapely.wkt.loads('POLYGON ((0 0, 100 0, 100 100, 0 100, 0 0), (20 20, 80 20, 80 80, 20 80, 20 20))'); img = np.zeros((100, 100), dtype=np.uint8); cv2.fillPoly(img, [np.array(poly.exterior.coords, dtype=np.int32)], 3); [cv2.fillPoly(img, [np.array(h.coords, dtype=np.int32)], 0) for h in poly.interiors]; assert np.all(np.unique(img) == [0, 3]); assert img[50, 50] == 0; assert img[10, 10] == 3; print('Rasterization Invariant PASSED')"
   ```
   *Expected Result*: `Rasterization Invariant PASSED`.

4. **Verify Analysis and Blueprint Artifact**:
   - Inspect `.agents/teamwork/explorer_m2_2/analysis.md` for complete class implementations of `GeometryRasterizer`, `DrawingSanitizer`, `MSDAnnotationParser`, `DatasetPreparer`, and CLI `main()`.

5. **Invalidation Conditions**:
   - Any modification that breaks existing re-exports of `DrawingSplitManager` or `verify_split_isolation` from `drywall_detection.data.preparer`.
   - Any rasterization mapping generic MSD walls directly to `Class 1 (Drywall)` without verified partition schedules.
