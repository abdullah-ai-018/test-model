# Task Assignment: Milestone M2 Spec Miner 2 (Partition Schedule & Taxonomy Mining)

- **Assigned Agent**: `m2_spec_miner_2` (`teamwork_spec_miner`)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_spec_miner_2`
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Milestone**: M2 (Drywall Ground Truth, Vector Engine & Ground Truth Verification)
- **Date**: 2026-11-08

---

## 1. Scope & Mining Objectives

Mine authoritative partition schedules and construction specifications from the reference drawing set to formulate the drywall classification taxonomy and review mechanism:
1. **Target Sheets**:
   - Reference PDF: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
   - Sheet A-900: `PARTITION TYPES & DETAILS` (Page 63)
   - Sheet A-901: `PARTITION TYPES & DETAILS` (Page 64)
   - Sheet A-902: `WALL DETAILS` (Page 65)
2. **Specification Mining**:
   - Extract all 24 assembly details (stud gauge/size, gypsum board layers, GWB thickness, acoustic insulation, fire ratings, finishes).
   - Establish strict 4-class mapping:
     - **Class 0: Background** (White, `#FFFFFF`)
     - **Class 1: Drywall** (Green, `#00FF00`): Gypsum wallboard assemblies (Tags 1B, 1C, 1D, 1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A, 7B, 7C, 7E, 7F, 7G, 8A, Col 10).
     - **Class 2: Non-Drywall** (Red, `#FF0000`): Concrete masonry unit (Tag 1A: 6" CMU), glass officefronts (GL1, GL2), privacy walls (PW), operable partitions (FWP-2), concrete encasements (Col 11, Key Notes 1, 18).
     - **Class 3: Uncertain** (Yellow, `#FFFF00`): Untagged walls, ambiguous callouts, academic generic walls.
   - Specify the CSV export schema (`partition_schedule_mapping.csv`) and human-in-the-loop review stopping protocol (`REVIEW_REQUIRED.lock` / exit code 2).
3. **Architecture Deliverable**:
   - Deliver full transcription table, schema contracts, and implementation blueprint for `drywall_detection/vector/schedule_parser.py` in `analysis.md` and `handoff.md`.


## 2026-11-08T05:00:19Z
You are assigned as m2_spec_miner_2 (Partition Schedule & Taxonomy Spec Miner).
Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_spec_miner_2

Read your task assignment in:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m2_spec_miner_2\DISPATCH.md

Also read:
1. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md

Investigate Sheets A-900 (p.63) and A-901 (p.64) partition schedules in C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf:
- Transcribe all 24 assembly details (studs, GWB thickness, fire rating, STC, finish)
- Map to 4-class taxonomy: Drywall (1, Green), Non-Drywall (2, Red: 1A CMU, GL1/2 glass, PW, FWP-2), Uncertain (3, Yellow)
- Specify CSV schema (partition_schedule_mapping.csv) and review stopping lockfile (REVIEW_REQUIRED.lock / exit code 2)
- Design architecture for drywall_detection/vector/schedule_parser.py
- Deliver findings in analysis.md and handoff.md.
