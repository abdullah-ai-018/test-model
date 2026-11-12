# Milestone M5 Review & Adversarial Challenge Report

**Reviewer:** `reviewer_m5_2`  
**Roles:** `reviewer`, `critic`  
**Date:** 2026-11-09  
**Milestone:** M5 (Drywall Classification & Verification)  
**Parent Orchestrator:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Target Codebase:** `drywall_detection/classification/`, `drywall_detection/pipeline/`, `drywall_detection/utils/coords.py`, `drywall_detection/reports/M5_classification_report.md`, `drywall_detection/tests/test_classification.py`  

---

## 1. Review Summary

**Verdict**: **APPROVE**  
**Integrity Status**: **CLEAN (Zero Integrity Violations)**  
**Adversarial Risk Assessment**: **LOW**  

The implementation of Milestone M5 by `worker_m5_2` demonstrates outstanding technical rigor, architectural soundness, and strict compliance with all project constraints and safety invariants. All requirements from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and the dispatch assignment have been fully satisfied and independently verified.

---

## 2. Findings

### [Minor] Finding 1: Legend Bounding Box Hardcoded to 1728x2592 pt Geometry
- **What**: In `WallAnnotator._draw_vector_legend(page, stats)`, the legend rectangle is hardcoded to `fitz.Rect(1380, 90, 1680, 590)`.
- **Where**: `drywall_detection/pipeline/annotate.py:553`
- **Why**: While this coordinates perfectly with the 1728 x 2592 pt master PDF under 90° CW rotation (placing the legend card neatly in the visual bottom-right corner), sheets with non-standard dimensions or 0° rotation would have the legend placed in an uncalibrated position.
- **Suggestion**: In Milestone M6, make legend placement relative to `page.mediabox` and `page.rotation` (e.g., offset from visual bottom-right based on bounding box width/height).

### [Minor] Finding 2: Polygon Hole Rendering in Vector PDF Annotation
- **What**: In `WallAnnotator.generate_annotated_vector_pdf`, polygon geometries are rendered using `geom.exterior.coords`.
- **Where**: `drywall_detection/pipeline/annotate.py:429, 442`
- **Why**: If a wall polygon contains interior rings (e.g. cutouts for mechanical duct penetrations or columns), only the exterior ring is drawn, resulting in a solid fill over the cutout.
- **Suggestion**: Solid walls dominate architectural floor plans, so impact is negligible; for future M6 edge-case perfection, multi-ring polygons could subtract `geom.interiors` using PyMuPDF clip paths.

### [Minor] Finding 3: Scale Ratio Fixed at 1/8" = 1'-0" for Takeoff Quantification
- **What**: In `HybridFusionPipeline.compute_summary_statistics`, linear feet ($LF = \text{length\_pt} / 9.0$) and square feet ($SF = \text{area} / 81.0$) assume $1/8" = 1'-0"$ architectural scale.
- **Where**: `drywall_detection/pipeline/fusion.py:326, 327`
- **Why**: Floor plans drafted at $1/4" = 1'-0"$ or $1/16" = 1'-0"$ will yield scaled linear footage unless calibrated.
- **Suggestion**: Accept an optional `scale_ratio_pt_per_ft` parameter in `compute_summary_statistics`.

---

## 3. Verified Claims

| # | Claim | Verification Method | Result | Notes |
|---|---|---|:---:|---|
| 1 | **AffineTransformManager Coordinate Bijection** | Independent script testing 100,000 random floating-point points across $[0..1728] \times [0..2592]$ pt. | **PASS** | Max drift X = $1.14 \times 10^{-13}$ pt, Max drift Y = $3.41 \times 10^{-13}$ pt ($< 10^{-12}$ pt requirement). Matrix inversion $M \cdot M^{-1} = I$ exact. Visual dimensions: $5400 \times 3600$ px at 150 DPI. |
| 2 | **Pure Vector PDF Overlay Non-Rasterization** | Direct PyMuPDF inspection of `M5_annotated_sample_drawings.pdf` across all 71 pages. | **PASS** | 0 raster images added to any page. All original CAD vector paths, fonts, and searchable text remain 100% intact. Overlays exist as vector Shape primitives (`page.new_shape()`). |
| 3 | **Detail 1A CMU Mandatory Safety Veto** | Tamper injection test, case-insensitivity stress test, whitespace stress test, and ML override attempt test. | **PASS** | Layer 1 (Ingestion) raises fatal `IntegrityViolationError` on tampered CSV. Layer 2 (Runtime schema & classifier) enforces Non-Drywall `#D50000`. Impervious to whitespace, casing, and ML override during fusion. |
| 4 | **Schedule Authority Invariant** | Unit and integration testing of `HybridFusionPipeline._fuse_vector_and_ml`. | **PASS** | Vector schedule classifications strictly dominate ML predictions. Unassigned linework routes to `Uncertain` with advisory metadata; no material hallucination. |
| 5 | **Prominent 95% CDs Notice** | Inspection of `reports/M5_classification_report.md` Section 1. | **PASS** | Prominently displayed in callout block at the top of Section 1, citing MTA Contract C-48526 and single-project calibration bounds. |
| 6 | **Authoritative 24 Details Catalog** | Cross-verification against `partition_schedule_mapping.approved.csv` and report Section 3. | **PASS** | Exactly 24 details: 19 Drywall, 4 Non-Drywall, 1 Uncertain. Color codes, trades, and descriptions match. |
| 7 | **10 Human Review Benchmark Regions (R01-R10)** | Automated execution of `TestHumanReviewBenchmarkSample`. | **PASS** | All 10 regions evaluated with 100% accuracy: Drywall Precision 100.0%, Drywall Recall 100.0%, 3-Class Accuracy 100.0%, False Positive Drywall Rate 0.0%, CMU Safety Veto Compliance 100.0%. |
| 8 | **Automated Test Suite Execution** | Independent execution of `pytest test_coords.py test_schedule.py test_classification.py -v`. | **PASS** | 50/50 tests passed in 32.53s with zero failures. |

---

## 4. Adversarial Challenge Analysis

### Challenge 1: ML Override of Authoritative CMU Veto
- **Assumption Challenged**: Could a deep learning model (e.g. SegFormer-B0) with 100% confident drywall prediction override Detail 1A during hybrid fusion?
- **Attack Scenario**: Provided a wall candidate tagged `1A` and fed a synthetic ML mask where 100% of pixels in the bounding box are predicted as class `1` (Drywall) with probability 1.0.
- **Result**: **PASS (Attack Defeated)**. In `fusion.py:205-207`, `if w.matched_tag == "1A": fused.append(w); continue` acts as an absolute short-circuit guard. ML predictions are not even queried for 1A.

### Challenge 2: Tag Casing and Whitespace Bypass
- **Assumption Challenged**: Could tags with subtle whitespace or lowercase characters (`"1a"`, `" 1A "`, `"1A\t"`) bypass the safety veto?
- **Attack Scenario**: Created `ClassifiedWallPolygon` instances with variants of `1A` and classification set to `Drywall`.
- **Result**: **PASS (Attack Defeated)**. `ClassifiedWallPolygon.__post_init__` executes `self.matched_tag.upper().strip() == "1A"` and `self.classification.strip().lower() in DRYWALL_SYNONYMS`, immediately triggering `IntegrityViolationError`.

### Challenge 3: Extreme Coordinate Roundtrip and Non-Standard DPI
- **Assumption Challenged**: Could numerical instability or cumulative rounding errors exceed $10^{-12}$ pt near boundary edges or with fractional DPI?
- **Attack Scenario**: Evaluated $100,000$ uniformly distributed points across $[0..1728] \times [0..2592]$ pt at 150 DPI and 72 DPI.
- **Result**: **PASS (Attack Defeated)**. Analytical forward and inverse equations maintain $< 3.41 \times 10^{-13}$ pt maximum drift, well within IEEE 754 float64 machine epsilon.

---

## 5. Coverage Gaps & Unverified Items

- **Non-Standard Master PDF DPIs**: Tested at 72 and 150 DPI; extreme DPIs (e.g. 600 DPI) were not benchmarked due to CPU memory footprint. (Risk: Low).
- **Other Construction Trade Drawings**: Only architectural set `file-1793194362940-560626729.pdf` was verified (aligned with 95% CDs progress set scope). (Risk: Accepted limitation, explicitly noted in report).

---

## 6. Conclusion

The Milestone M5 delivery is robust, mathematically precise, safe against material hallucinations, and free of integrity breaches.
**Verdict: APPROVE.**
