## 2026-11-07T21:45:01Z
You are explorer_m2_2 (M2 Mask Unifier Explorer).
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m2_2
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model

Read these files first:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read before starting work)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M1_audit_report.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\config.py
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\utils\coords.py

Your Mission:
Architect the dataset unifier and mask generation module for Milestone M2, located at `drywall_detection/data/preparer.py`.
1. Standardize floor plan inputs into a unified representation:
   - Floor plan image (RGB/grayscale, normalized resolution).
   - Binary wall mask (uint8 array, 0=Background, 1=Wall) and semantic multiclass mask.
2. Investigate annotation formats for MSD: MSD provides vector polygons in WKT format (Well-Known Text) with labels such as `separator` / `WALL`.
3. Design robust rasterization using `shapely.wkt` and `cv2.fillPoly` / `PIL.ImageDraw` preserving exact geometric boundaries and coordinate systems.
4. Formulate filtering and sanitization: reject degenerate/empty drawings, handle missing polygons, validate polygon coordinate bounds, and filter duplicate or corrupted entries.
5. Provide complete, exact code blueprints for `preparer.py` and its CLI (`python -m drywall_detection.data.preparer`).
6. Write your findings to `.agents/teamwork/explorer_m2_2/analysis.md` and summarize in `.agents/teamwork/explorer_m2_2/handoff.md`.
7. Send a message to the orchestrator when complete. Do NOT write source code to drywall_detection/ (you are a read-only Explorer).
