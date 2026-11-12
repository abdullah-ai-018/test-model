# Task Assignment: Milestone M2 Implementation Worker (Vector Engine & Schedule Parser)

- **Assigned Agent**: `m2_worker_1` (`teamwork_worker`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_worker_1`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Date**: 2026-11-08

---

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

---

## 1. Required Reading (Authoritative Sources of Truth)
Before writing any code, thoroughly read:
1. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md` (Verbatim user requirements)
2. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md` (Project architecture, milestones, interface contracts, zero-tolerance rules)
3. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_spec_miner_2\analysis.md` & `handoff.md` (Schedule mining, 24 details, 4-class taxonomy, Tag 1A CMU veto, CSV schema, review lock protocol)
4. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_explorer_1\analysis.md` & `handoff.md` (Vector extraction, 90° rotation, bijection proofs, 296 tags, 3-tier spatial matcher)
5. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_explorer_3_rep\analysis.md` & `handoff.md` (Usman 239 red lines + 239 square tags, 100% collinear alignment, 8.35 pt / 17 px wall thickness, rasterizer engine, zero-leakage splits)
6. `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py` & `drywall_detection\utils\coords.py` & `drywall_detection\datasets\unified_format.py`

---

## 2. File Ownership & Scope Boundaries
You have exclusive write ownership of:
- `drywall_detection/vector/__init__.py`
- `drywall_detection/vector/extractor.py`
- `drywall_detection/vector/schedule_parser.py`
- `drywall_detection/vector/spatial_matcher.py`
- `drywall_detection/data/ground_truth_builder.py`
- `drywall_detection/data/partition_schedule_mapping.csv`
- `drywall_detection/data/REVIEW_REQUIRED.lock`
- Split manifests in `drywall_detection/data/processed/splits/` (`train.json`, `val.json`, `test.json`, `quarantine.json`)
- `drywall_detection/tests/test_vector.py`
- `drywall_detection/tests/test_schedule.py`
- Your state folder `.agents/teamwork/m2_worker_1/`

You MUST NOT modify files owned by other modules (`drywall_detection/datasets/`, `drywall_detection/utils/`, etc.).

---

## 3. Implementation Requirements

### 3.1 `drywall_detection/vector/extractor.py`
- Extract vector primitives from PDF pages using PyMuPDF (`fitz`): drawings (lines, rectangles, curves), fills, strokes, and text layer spans.
- Handle $90^\circ$ clockwise page rotation by integrating `drywall_detection.utils.coords.pdf_to_pixel` and `pixel_to_pdf`.
- Partition Tag Discovery:
  - Detect square tag boxes with size $11.2 \times 11.3$ pt ($\pm 2.5$ pt tolerance).
  - Extract enclosed tag text (e.g. `1C`, `2C`, `5E`, `7A`, `7F`, `8A`, `1A`, `GL1`).
  - Detect attached vector leader lines connecting callouts to wall linework.

### 3.2 `drywall_detection/vector/schedule_parser.py`
- Parse partition schedules on Sheet A-900 (Page 63 / idx 62) and Sheet A-901 (Page 64 / idx 63).
- Transcribe all 24 assembly details into structured dataclasses (`PartitionAssembly`).
- Apply the 4-class taxonomy:
  - Class 1: Drywall (Green, `#00FF00`) - 18 verified gypsum assemblies (1B..1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A..7C, 7E..7G, 8A, Detail 10).
  - Class 2: Non-Drywall (Red, `#FF0000`) - Detail 1A (`6" FIRE RATED CMU MASONRY BLOCK` - mandatory safety veto, ZERO gypsum), GL1 & GL2 glass systems, Detail 11 concrete encasement.
  - Class 3: Uncertain (Yellow, `#FFFF00`) - Detail 09 (TV Screen millwork insert), untagged walls.
- Write 14-column CSV: `drywall_detection/data/partition_schedule_mapping.csv`.
- Create sentinel lockfile `drywall_detection/data/REVIEW_REQUIRED.lock` and return exit code 2 when `partition_schedule_mapping.approved.csv` is not present.

### 3.3 `drywall_detection/vector/spatial_matcher.py`
- Implement 3-tier spatial matching:
  - Tier 1: Leader line raycasting from tag box to nearest wall segment.
  - Tier 2: Primary buffer proximity search within $25.0$ pt radius (covers 96.2% of ground truth).
  - Tier 3: Extended buffer proximity search within $50.0$ pt radius (covers 100.0% of ground truth).
  - Fallback: Any wall beyond $50.0$ pt without an explicit leader line remains Unassigned / Uncertain.

### 3.4 `drywall_detection/data/ground_truth_builder.py`
- Parse `drywall_walls_marked_red_by_Usman.pdf` (Pages 0..4, Sheets A-100..A-104) and extract the 239 red wall centerlines.
- Rasterize centerlines into 4-class Mode 'P' 8-bit indexed PNG masks matching 150 DPI canvas ($5400 \times 3600$ px) with physical wall thickness buffering (8.35 pt / 17 px).
- Enforce `validate_mask_array()` on all generated masks.
- Generate drawing-level split manifests:
  - `train.json`: MSD tiles + Sheets A-100, A-101, A-102, A-103 (170 verified walls).
  - `val.json`: CubiCasa5K benchmark slice.
  - `test.json`: Sheet A-104 (69 verified walls) + `test Spark Lake Grove - Permit Set.pdf` (54 pages).
  - `quarantine.json`: MTA 99th St weak pseudo-labels (Sheets A-105+).
  - Assert zero project and zero drawing overlap across splits.

### 3.5 Test Suites & Verification
- Author `drywall_detection/tests/test_vector.py` and `drywall_detection/tests/test_schedule.py`.
- Run the full test suite (`python -m pytest drywall_detection/tests/ -v`).
- Ensure 100% pass rate (all previous 412 tests + new tests must pass).
- Document all commands, execution outputs, and verification in `handoff.md`.


## 2026-11-08T08:20:42Z
**Context**: Milestone M2 Ground Truth Approval
**Content**: FYI from user/parent: The user has reviewed and approved the partition schedule mapping CSV (18 Drywall, 5 Non-Drywall including 1A CMU veto, 1 Uncertain). The approved file is saved at `drywall_detection/data/partition_schedule_mapping.approved.csv` and `REVIEW_REQUIRED.lock` has been cleared.
**Action**: Please copy/use `partition_schedule_mapping.approved.csv` as the approved mapping for `partition_schedule_mapping.csv` if needed, do not create or block on `REVIEW_REQUIRED.lock`, and proceed with downstream ground truth builder, 150 DPI Mode 'P' indexed mask generation, split manifests, unit tests, and full test suite verification.
