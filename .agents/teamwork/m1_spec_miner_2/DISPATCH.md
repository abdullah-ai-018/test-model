# Dispatch: m1_spec_miner_2

- **Role**: Dataset Format & Conversion Spec Miner
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

## Objective
Read ORIGINAL_REQUEST.md and PROJECT.md. Mine and specify the unified dataset conversion pipeline and visual QC reporting.
1. Formulate the technical specifications for converting eligible candidate datasets (MSD WKT polygons, CubiCasa5K SVG, and raster floor plan masks) into a unified segmentation format: single-channel 8-bit indexed PNG masks (`uint8`, values 0: Background, 1: Drywall, 2: Non-Drywall, 3: Uncertain).
2. Detail the sliding-window tiling engine ($512 \times 512$ tiles with 20% overlap), coordinate scaling, corrupted/empty tile filtering, and visual QC sample generator (rendering translucent color masks overlaid on floor plans).
3. Specify the interface, functions, and classes for `drywall_detection/datasets/unified_format.py` and QC generation.
4. Recommend implementation guidelines for the Worker.
5. Record findings in analysis.md and write a complete handoff.md.


## 2026-11-07T20:41:40Z
You are m1_spec_miner_2. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

Role: Dataset Format & Conversion Spec Miner
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2

Your tasks for Milestone M1 (Dataset Research, Licensing Audit & Unified Preparation):
1. Specify the unified dataset format: single-channel 8-bit indexed PNG masks (`uint8`, values 0: Background, 1: Drywall, 2: Non-Drywall, 3: Uncertain).
2. Specify the conversion pipeline from eligible datasets (MSD WKT, CubiCasa5K SVG, and raster masks) into this unified representation.
3. Specify the sliding-window tiling engine (512x512 patches with 20% overlap), coordinate scaling, filtering corrupt/empty tiles, and visual QC sample generator (overlaying translucent masks onto drawing tiles).
4. Detail the classes, methods, and error handling for `drywall_detection/datasets/unified_format.py`.
5. Maintain liveness in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\progress.md.
6. Write your comprehensive analysis in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\analysis.md and handoff in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2\handoff.md.
7. Notify the orchestrator via send_message when done with the path to your handoff.md.
