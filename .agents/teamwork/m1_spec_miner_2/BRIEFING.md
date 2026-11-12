# BRIEFING — 2026-11-08T01:49:00Z

## Mission
Specify the unified dataset format, conversion pipeline (MSD WKT, CubiCasa5K SVG, raster masks), sliding-window tiling engine, QC overlay generator, and interface definitions for `drywall_detection/datasets/unified_format.py` in Milestone M1.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Dataset Format & Conversion Spec Miner
- Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_spec_miner_2
- Original parent: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Milestone: M1 (Dataset Research, Licensing Audit & Unified Preparation)

## 🔒 Key Constraints
- Read-only miner: do NOT implement source code or tests, only technical specifications, interfaces, and architecture.
- Write only to `.agents/teamwork/m1_spec_miner_2/`.
- Specify 4-class unified segmentation format: uint8 PNG (0: Background, 1: Drywall, 2: Non-Drywall, 3: Uncertain).
- Specify conversion pipelines for MSD (WKT), CubiCasa5K (SVG), and raster masks.
- Specify sliding-window tiling engine: 512x512 patches with 20% overlap (step = 410px), coordinate scaling, empty/corrupt tile filtering.
- Specify visual QC sample generator overlaying translucent masks onto drawing tiles.
- Deliver findings in `analysis.md` and complete handoff in `handoff.md`. Notify parent when done.

## Current Parent
- Conversation ID: 3c1a82ae-9b50-494e-b173-0369a8d4a486
- Updated: 2026-11-08T01:49:00Z

## Task Summary
- **What to build**: Unified dataset specification, conversion pipeline spec, tiling & QC spec, and module design for `drywall_detection/datasets/unified_format.py`.
- **Success criteria**: Exhaustive interface contracts, data models, error handling, edge cases, tiling logic, and QC generator specs.
- **Interface contracts**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Code layout**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

## Key Decisions Made
- Format chosen: Single-channel 8-bit indexed PNG in Mode 'P' with standard 256-color palette (White 0, Green 1, Red 2, Yellow 3). Provides human-readable color in image viewers while loading directly as integer indices in PyTorch.
- Generic wall pretraining guardrail: All external academic dataset walls (MSD, CubiCasa5K) mapped strictly to Class 3 (Uncertain).
- Tiling parameters: 512x512 patches, 20% overlap, stride 410 px. Boundary clamping guarantees 100% surface coverage.
- Stitching algorithm: 2D Hann window apodization weighting eliminates boundary seam artifacts with < 1e-5 reconstruction error.
- Filtering rules: Discard 100% pure blank whitespace tiles; retain hard negatives (drawing linework without walls) up to 15% quota.
- Triplet QC format: [Drawing Tile | Color Mask | Translucent Overlay] (1536x512) plus 36 px diagnostic header banner.

## Artifact Index
- analysis.md — Full specification analysis, module contracts, features discovered, edge cases, and implementation guidelines
- handoff.md — 5-component handoff report (Observation, Logic Chain, Caveats, Conclusion, Verification Method)
- probe_tests.py — Empirical test suite verifying WKT, SVG, Mode P PNG, tiling math, 2D Hann stitching, and QC triplets
- progress.md — Liveness heartbeat and milestone tracking
