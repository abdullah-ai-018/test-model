## 2026-11-08T03:52:13Z
You are challenger_m2_2 (M2 Mask and Downloader Challenger).
Your state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m2_2
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model

Read these files first:
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read before starting work)
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\downloader.py
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\preparer.py
- c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\data\qc.py

Your Mission:
Adversarially challenge and stress-test `drywall_detection/data/downloader.py` and `preparer.py`:
1. Write adversarial stress tests in your state folder and execute them:
   - Downloader: test disk safety headroom boundaries (e.g. required_free_gb exceeding available disk, negative required_gb), simulated SHA-256 checksum mismatches (verify corrupt `.part` files are deleted and never promoted), simulated network disconnects / HTTP 500 / 403 errors (verify exponential backoff retry halts gracefully).
   - Preparer & Rasterizer: test pathological WKT inputs (self-intersecting bowtie polygons, zero-area slivers, inverted coordinate polygons, NaN / Inf coordinates, nested donut holes, empty geometries, pure blank white floor plans).
   - Verify that invalid topologies are either repaired with `shapely.make_valid` or rejected cleanly without crashing.
   - Verify that hard negatives with zero walls are capped at <= 15% and never flood the dataset.
2. Execute stress tests and document results.
3. Issue a clear verdict: `APPROVE` or `REQUEST_CHANGES`. Write report to `.agents/teamwork/challenger_m2_2/report.md` and summarize in `.agents/teamwork/challenger_m2_2/handoff.md`. Notify the orchestrator when complete.
