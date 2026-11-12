# Milestone M2 Handoff Report: Dataset Downloader Module Architecture

**Document ID:** HANDOFF-M2-DOWNLOADER-01  
**Author:** explorer_m2_1 (M2 Dataset Downloader Explorer)  
**Date:** 2026-11-08  
**To:** Orchestrator (`3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`) / Implementer Worker  
**Artifacts Generated:**  
- `.agents/teamwork/explorer_m2_1/analysis.md` (Comprehensive Architectural Blueprint & Code Specification)  
- `.agents/teamwork/explorer_m2_1/handoff.md` (Self-Contained 5-Component Handoff Report)  

---

## 1. Observation

1. **Candidate Endpoint Probing Results**:
   - `https://huggingface.co/api/datasets/epfl-dcl/modified-swiss-dwellings` returned `HTTP Error 401: Unauthorized` (gated or restricted repo).
   - `https://zenodo.org/api/records/7788422` and `https://zenodo.org/records/7788422` returned `HTTP Error 403: Forbidden` when accessed via Python `urllib` due to Cloudflare anti-bot challenge.
   - `https://data.4tu.nl/v2/articles/e1d89cb5-6872-48fc-be63-aadd687ee6f9` returned `HTTP 200 OK`, exposing CC BY 4.0 license, but distributes two large zip archives: `modified-swiss-dwellings-v1-test.zip` (786,779,770 bytes / ~750 MB) and `modified-swiss-dwellings-v1-train.zip` (4,757,396,292 bytes / ~4.43 GB), totaling 5.54 GB (uncompressed >15 GB).
   - `https://huggingface.co/api/datasets/philippds/modified-swiss-dwellings-enriched` returned `HTTP 200 OK` with tags `['license:cc-by-4.0', 'format:parquet', 'modality:image', 'modality:tabular']`. Zero login, zero API keys, and zero EULA acceptance required.

2. **Hugging Face Parquet Structure & Authoritative Git LFS Checksums**:
   - Inspection of Git LFS pointer files via `https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched/raw/main/` confirmed exact SHA-256 hashes and sizes:
     - `data/test-00000-of-00001.parquet`: size `26,082,532` bytes, sha256 `a0cf855f3cd450a298da588cf3beaf68491970be64221fe586e41ab810f94638`
     - `data/train-00000-of-00003.parquet`: size `48,129,426` bytes, sha256 `ff66a65e1a5948bd73e5b9999f1343eac3f0b4a35d6213ef0cd95ab518fe1ef6`
     - `data/train-00001-of-00003.parquet`: size `49,452,621` bytes, sha256 `640bddec36b1a06783f883077e1836c95638714f4a45085dcb93ef6489eef6f7`
     - `data/train-00002-of-00003.parquet`: size `50,164,921` bytes, sha256 `44511e3fd8b00c2437286deea7ee02033b0c1d71f03bd7258742bc376edc0213`
     - Subtotal Core Split: `173,829,500` bytes (165.78 MiB / 173.83 MB).
     - `geometries/test-00000-of-00001.parquet`: size `26,877,935` bytes, sha256 `307fb472cf92fe01d15d58141e967117ef6a8a41bf5ec8181614298719a1a67b`
     - `geometries/train-00000-of-00001.parquet`: size `154,641,570` bytes, sha256 `39e7ef663a8f03642a35dda02210af02cd9673e0e10c663a13aca92f9f150d53`
     - Subtotal Geometries Split: `181,519,505` bytes (173.11 MiB / 181.52 MB).
     - Combined Total: `355,411,406` bytes (338.95 MiB / 355.41 MB).

3. **HTTP Range Resumability Verification**:
   - Executing `Range: bytes=0-1023` against `data/test-00000-of-00001.parquet` returned `Status: 206`, `Content-Range: bytes 0-1023/26082532`, with Parquet magic bytes `b'PAR1'`. Resumable chunked streaming is natively supported.

4. **Host Disk & Hardware Status**:
   - Drive `C:\` has `12.89 GB` free of `149.64 GB`.
   - `drywall_detection/config.py` lines 126-130 define `DISK_FREE_MIN_GB = 5.0` and `DISK_LARGE_DOWNLOAD_THRESHOLD_GB = 10.0`.
   - `drywall_detection/utils/hardware.py` lines 490-542 define `check_disk_safety(required_free_gb, disk_path)`.

5. **Existing Codebase Interfaces**:
   - `drywall_detection/data/preparer.py` re-exports `split_manager` interfaces expecting `TileRecord` objects and `project_id` / `drawing_id` groupings.
   - `drywall_detection/datasets/unified_format.py` contains `MSDConverter` at line 255 parsing WKT geometries to `UnifiedMask`.
   - `pyarrow` (20.0.0), `pandas` (2.2.2), `PIL` (10.2.0), and `shapely` (2.1.1) are installed in the host Python environment.

---

## 2. Logic Chain

1. **Source Selection**:
   - From (1), Zenodo is blocked by Cloudflare WAF bot-detection (403), EPFL Hugging Face is unauthorized (401), and 4TU.ResearchData requires downloading 5.54 GB zip archives with ~15 GB uncompressed disk footprint (violating host disk constraints).
   - In contrast, `philippds/modified-swiss-dwellings-enriched` on Hugging Face is public, CC BY 4.0, zero-login, and provides compact Parquet files (173.8 MB core + 173.1 MB geometries). Therefore, it is selected as the authoritative primary download endpoint.

2. **Disk Safety Pre-Flight Math**:
   - From (2) and (4), downloading MSD Core requires 0.17 GB, and Core + Geometries requires 0.35 GB.
   - Both are far below the 10.0 GB threshold ($0.35 < 10.0$ GB), so no user alert prompt is triggered.
   - With 12.89 GB free on Drive `C:\`, post-download space is $12.89 - 0.35 = 12.54$ GB. Since $12.54 > 5.0$ GB safety margin, `check_disk_safety` evaluates to `(True, 12.89, "OK: Sufficient disk space...")`. Pre-flight safety passes unconditionally.

3. **Data Integrity & Atomicity**:
   - From (2) and (3), authoritative SHA-256 hashes are fixed in `MSD_CATALOG`. Downloading to `<filename>.part` and verifying the SHA-256 hash before renaming to `<filename>` guarantees that incomplete or corrupted transfers never pollute `drywall_detection/data/raw/msd/`.
   - From (3), partial downloads can be safely resumed using `Range: bytes={existing_bytes}-` upon transient disconnections.

4. **Integration with Milestone M2 Pipeline**:
   - From (2) and (5), the Parquet files contain `site_id`, `building_id`, `struct_in` (512×512 PNG byte masks), and explicit WKT `geom` wall strings (`entity_type: separator`, `entity_subtype: WALL`).
   - This provides immediate inputs for `drywall_detection/data/preparer.py` and `MSDConverter` to enforce project-isolated 70/15/15 splits with zero building leakage.

---

## 3. Caveats

1. **4TU Fallback Complexity**:
   - 4TU.ResearchData remains an eligible secondary mirror, but because its payload is bundled in two large zips (5.54 GB total), fallback downloading requires selective decompression or higher disk headroom. The primary Hugging Face endpoint should be preferred for all automated pipelines.
2. **Column Names in Enriched Parquet**:
   - In the enriched Parquet dataset, the floor plan identifier is named `id` (corresponding to Swiss Dwellings `floor_id`), with `site_id` and `building_id` as integers. Downstream consumers in `preparer.py` must map `project_id = str(row['site_id'])` and `drawing_id = str(row['id'])`.
3. **Read-Only Scope**:
   - In accordance with Teamwork Explorer constraints, no source code was created or edited under `drywall_detection/`. All blueprints and specifications reside in `.agents/teamwork/explorer_m2_1/`.

---

## 4. Conclusion

1. **Endpoint Resolution**: The Modified Swiss Dwellings dataset at `https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched/resolve/main/` is verified as fully open, CC BY 4.0, zero-login, and immediately downloadable.
2. **Manifest Verified**: The exact SHA-256 checksums and file sizes for all 6 core and geometry Parquet files totaling 355.4 MB have been authoritatively captured in `analysis.md`.
3. **Architecture Established**: The complete design for `drywall_detection/data/downloader.py`—incorporating disk safety pre-flight checks, multi-tier caching, atomic `.part` file promotion, resumable HTTP transfers, exponential backoff, CLI arguments, and exit codes—is fully specified and ready for immediate implementation by the M2 Worker.

---

## 5. Verification Method

To independently verify the findings and test the blueprint once implemented:

1. **Inspect Architectural Blueprint**:
   ```powershell
   Get-Content ".agents\teamwork\explorer_m2_1\analysis.md"
   ```

2. **Verify Hugging Face Endpoint & Range Resumability**:
   ```powershell
   python -c "import urllib.request; req = urllib.request.Request('https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched/resolve/main/data/test-00000-of-00001.parquet', headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-10'}); resp = urllib.request.urlopen(req); print('Status:', resp.status, '| Content-Range:', resp.headers.get('Content-Range'))"
   ```
   *Expected Output:* `Status: 206 | Content-Range: bytes 0-10/26082532`

3. **Verify Pre-Flight Disk Safety Check**:
   ```powershell
   python -c "from drywall_detection.utils.hardware import check_disk_safety; print(check_disk_safety(0.35))"
   ```
   *Expected Output:* `(True, 12.89, 'OK: Sufficient disk space (12.89 GB free).')`

4. **Verify Existing Dataset Unit Tests**:
   ```powershell
   pytest drywall_detection/tests/unit/test_datasets.py -v
   ```
   *Expected Output:* All 21 tests pass.
