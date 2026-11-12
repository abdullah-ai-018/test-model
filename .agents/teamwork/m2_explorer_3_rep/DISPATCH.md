# Task Assignment: Milestone M2 Explorer 3 Replacement (Usman Ground Truth & Mask Rasterizer)

- **Assigned Agent**: `m2_explorer_3_rep` (`teamwork_explorer`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_explorer_3_rep`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Role**: Replacement Explorer taking over from `m2_explorer_3` (connection interrupted).
- **Date**: 2026-11-08

---

## 1. Scope & Investigation Objectives

Investigate the human expert markup ground truth and design the ground truth rasterization and dataset splitting architecture:
1. **Target Artifacts**:
   - `C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf` (27 pages, human expert estimator annotations).
   - Pristine extract: `C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf` (27 pages).
   - Held-Out Permit Set: `C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf` (54 pages).
2. **Technical Probing**:
   - Probe the red markup layer in Usman's PDF (239 red wall centerlines across Sheets A-100 to A-104).
   - Extract stroke properties (RGB red color `(1, 0, 0)` or `(255, 0, 0)`, line widths, coordinate bounds).
   - Verify alignment between red marked walls and architectural vector partitions.
   - Design rasterization engine (`ground_truth_builder.py`): rasterize red wall centerlines into 4-class Mode 'P' indexed PNG masks matching 150 DPI resolution ($5400 \times 3600$ px for ARCH D) with proper wall thickness buffering.
   - Design Drawing-Level Split Strategy:
     - Training Split: MSD tiles + Sheets A-101, A-102, A-103.
     - Validation Split: CubiCasa5K benchmark slice.
     - Held-Out Test Split: Sheet A-104 (69 verified drywall walls) + `test Spark Lake Grove - Permit Set.pdf`.
     - Quarantined: MTA 99th Street weak pseudo-labels.
3. **Architecture Deliverable**:
   - Deliver detailed analysis, coordinate alignment proofs, rasterizer algorithms, and split specifications in `analysis.md` and `handoff.md`.


## 2026-11-08T05:08:21Z
You are assigned as m2_explorer_3_rep (Usman Ground Truth & Mask Rasterizer Explorer Replacement).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_explorer_3_rep

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_explorer_3_rep\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
3. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\datasets\unified_format.py

Investigate C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf (27 pages):
- Extract red markup stroke layer (239 red wall centerlines across A-100..A-104)
- Verify alignment with architectural vector walls
- Design rasterization engine (ground_truth_builder.py) to convert red centerlines into 4-class Mode 'P' indexed PNG masks at 150 DPI
- Design drawing-level splits: Train (MSD + A-101..103), Val (CubiCasa5K), Test (A-104 + Spark Lake Grove Permit Set), Quarantine (99th St weak pseudo-labels)
- Deliver findings in analysis.md and handoff.md.
