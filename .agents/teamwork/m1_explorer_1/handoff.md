# Handoff Report: Dataset Research, Licensing Audit & Module Architecture

**Subagent:** `m1_explorer_1` (Dataset Licensing & Research Explorer)  
**Milestone:** M1 (Dataset Research, Licensing Audit & Unified Preparation)  
**Recipient:** Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1`  
**Timestamp:** 2026-11-07T20:48:00Z  
**Type:** Hard (Task Complete)  

---

## 1. Observation

1. **Candidate Datasets Verified via Official APIs and Repositories**:
   - **Modified Swiss Dwellings (MSD)**:
     * Command: Python script querying Zenodo API (`https://zenodo.org/api/records/7788422`) and Hugging Face API (`https://huggingface.co/api/datasets/philippds/modified-swiss-dwellings-enriched`).
     * Direct Output:
       - Zenodo Title: `"Swiss Dwellings: A large dataset of apartment models including aggregated geolocation-based simulation results..."`
       - Zenodo License: `{'id': 'cc-by-4.0'}`
       - Zenodo DOI: `10.5281/zenodo.7788422`
       - Zenodo File: `swiss-dwellings-v3.0.0.zip` (931,868,205 bytes, MD5 `3b7915ecd5bf8e492a3e78c598b74123`)
       - Hugging Face License: `'license': 'cc-by-4.0'`
       - Hugging Face Download Size: `173,829,500` bytes (~173.8 MB).
       - Features: Tabular WKT polygons in `geometries` split (`entity_type: separator`, `entity_subtype: WALL`) and raster channel `struct_in` for structural/partition walls.

   - **CubiCasa5K**:
     * Command: Python script querying Zenodo API (`https://zenodo.org/api/records/2613548`) and GitHub raw LICENSE (`https://raw.githubusercontent.com/CubiCasa/CubiCasa5k/master/LICENSE`).
     * Direct Output:
       - Zenodo Title: `"CubiCasa5k"`
       - Zenodo License: `{'id': 'cc-by-nc-sa-4.0'}`
       - Zenodo DOI: `10.5281/zenodo.2613548`
       - Zenodo File: `cubicasa5k.zip` (5,469,495,706 bytes ~5.09 GB, MD5 `0ce0b203d1e3c125b51087b219bd23b9`)
       - GitHub LICENSE: `"CubiCasa5K is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)."`
       - Wall representation: High-resolution SVG files with `<polygon class="Wall">` tags.

   - **FloorPlanCAD**:
     * Command: Python script querying `https://floorplancad.github.io/` and Hugging Face API (`https://huggingface.co/api/datasets/Voxel51/FloorPlanCAD`).
     * Direct Output:
       - Official Website Verbatim Disclaimer:
         `"The annotations in this dataset along with this website belong to us and are licensed under a Creative Commons Attribution-NonCommercial 4.0 License. We do not own the copyright of the drawings. By downloading the dataset you agree to the following terms: The authors give no warranties regarding the dataset. The users of the dataset accept full responsibility for the use of the dataset, including but not limited to the use of any copies of copyrighted dataset that they may create from the dataset."`
       - Hugging Face test split: 454 MB download. Full Google Drive set: ~3.5 GB.
       - Vector SVG primitives in $20\text{m} \times 20\text{m}$ sub-drawing crops; Wall is Stuff Class 0.

   - **CVC-FP**:
     * Command: Python script querying Figshare API (`https://api.figshare.com/v2/articles/12082131`) and Zenodo API (`https://zenodo.org/api/records/7921780`).
     * Direct Output:
       - Figshare Title: `"Data and codes of Indoor mapping and modeling by parsing floor plan images"`
       - Figshare License: `{'value': 1, 'name': 'CC BY 4.0', 'url': 'https://creativecommons.org/licenses/by/4.0/'}`
       - Figshare DOI: `10.6084/m9.figshare.12082131.v1`
       - Archive File: `1-WID512_ROTATE.tar.gz` (370,815,867 bytes ~353.6 MB).
       - Volume: 122 scanned floor plans in 4 graphic styles with vector SVG and binary PNG masks for walls.

   - **R2V (Raster-to-Vector)**:
     * Command: Python script inspecting `https://raw.githubusercontent.com/art-programmer/FloorplanTransformation/master/README.md`.
     * Direct Output:
       - Verbatim Author Disclosure:
         `"## Data"`
         `"We don't have the permission to share the rasterized images, which are from the LIFULL dataset. Here we only share our vector-graphics annotations which might be helpful for other tasks... Note that, since we cannot share the image data, you might need to change the code..."`
       - Access Barrier: Requires formal institutional application to National Institute of Informatics (NII) IDR in Japan and execution of a legal contract with LIFULL Co., Ltd.

   - **SESYD Floorplans**:
     * Command: Python script inspecting `http://mathieu.delalandre.free.fr/projects/sesyd/symbols/floorplans.html`.
     * Direct Output:
       - Annotations schema: Ground truth XML files contain bounding boxes exclusively for 16 symbol models (armchair, bed, chair, door1, door2, table, sink, tub, window1, window2).
       - Verbatim Table Columns: `dataset, name, images, format, type, size, symbols, models, bounding, width, background, download`.
       - Wall ground truth: **ZERO**. The walls in SESYD are merely static background raster noise; no wall annotations exist.

   - **ArchCAD-400k**:
     * Command: Python script querying Hugging Face API (`https://huggingface.co/api/datasets/jackluoluo/ArchCAD`).
     * Direct Output:
       - Hugging Face API parameters: `'gated': 'manual'`, `'private': False`.
       - Verbatim Gated Fields: `'full_name'`, `'affiliation'`, `'email': {'label': 'Institutional Email (preferred)'}`, `'country'`, `'intended_use'`, `'non_commercial_use': {'type': 'checkbox'}`, `'data_protection_ack': {'type': 'checkbox'}`.
       - Gated Prompt: `"To request access to the ArchCAD dataset, please complete the following form... approval may take up to 3 business days."`

2. **Hardware & Disk Storage Constraints**:
   - Direct measurement from `survey_explorer_1/handoff.md`:
     * Total System RAM: 7.88 GB, with only **~1.00 GB available**.
     * Local Disk Storage:
       - `C:\`: Total 149.64 GB, Used 133.29 GB, Free **16.35 GB** (89.1% full).
       - `E:\`: Total 88.12 GB, Used 57.66 GB, Free **30.45 GB** (65.4% full).
     * GPU: 0 CUDA VRAM (CPU-only execution environment).

3. **Analysis Deliverable Completed**:
   - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1\analysis.md` (written and saved, containing detailed 7-dataset dossiers, compliance rationale, module design, schema, and Worker instructions).

---

## 2. Logic Chain

1. **Autonomous Eligibility Assessment**:
   - *Premise 1*: System Integrity Rules and Requirement R1 dictate: (a) verify licenses, (b) never accept terms or bypass access controls on user's behalf, (c) verify wall annotation presence.
   - *Observation 1 (R2V)*: R2V only distributes coordinate text files, not raster images. Access to raster images requires signing an institutional contract with LIFULL Co. via NII IDR. Autonomous agents cannot sign legal agreements $\implies$ **R2V is disqualified**.
   - *Observation 1 (SESYD)*: SESYD contains zero wall annotations, only 16 symbol categories. Wall segmentation requires wall ground truth $\implies$ **SESYD is disqualified**.
   - *Observation 1 (ArchCAD-400k)*: Hugging Face API confirms `gated: manual`, requiring submission of personal name, affiliation, institutional email, and manual approval taking up to 3 business days. Autonomous agents cannot submit personal information or sign affidavits $\implies$ **ArchCAD-400k is disqualified for autonomous ingestion**.
   - *Observation 1 (MSD)*: MSD is open access under CC BY 4.0 (commercial use permitted), provides explicit WKT wall polygons (`entity_type == 'separator' & entity_subtype == 'WALL'`), has pre-tiled Hugging Face parquet download of 173.8 MB, and requires zero credentials $\implies$ **MSD is the Top Recommended Primary Ingestion Dataset**.
   - *Observation 1 (CVC-FP)*: Figshare distribution is open access under CC BY 4.0, archive size 353.6 MB, contains 122 scanned floor plans with pixel-accurate SVG/PNG wall masks $\implies$ **CVC-FP is eligible for fast CPU smoke testing**.
   - *Observation 1 (CubiCasa5K)*: Zenodo distribution is direct HTTP under CC BY-NC 4.0 / CC BY-NC-SA 4.0, archive size 5.09 GB, provides 5,000 real-world floor plans with SVG wall polygons $\implies$ **CubiCasa5K is eligible as the non-commercial academic validation benchmark**.

2. **Disk Safety & Storage Management**:
   - *Premise 2*: System rules mandate free disk space check prior to download and notification for downloads $> 10\text{ GB}$.
   - *Observation 2*: Local drive C: has 16.35 GB free.
   - *Step 1*: MSD (173.8 MB) and CVC-FP (353.6 MB) occupy $< 2.5\text{ GB}$ uncompressed, safely within C: limits.
   - *Step 2*: CubiCasa5K archive is 5.09 GB; extracting all 5,000 floor plans requires $\sim 18\text{ GB}$, which would exhaust C: drive space.
   - *Conclusion*: In Milestone M2, CubiCasa5K must be either: (a) streamed/extracted selectively (e.g. 200–500 sample evaluation slice), or (b) extracted to drive E: (30.45 GB free).

3. **Drywall Distinction vs Generic Wall Segmentation**:
   - *Premise 3*: Public datasets (MSD, CubiCasa5K, FloorPlanCAD, CVC-FP) label walls generically without CSI drywall material specifications.
   - *Step 1*: In accordance with Requirement R2, generic wall labels can only be used for Stage 1 wall segmentation pretraining.
   - *Step 2*: CSI drywall classification (Drywall / Green, Non-Drywall / Red, Uncertain / Yellow) must be established in Stage 2 using project drawings with partition schedules (Sheets A-900/A-901) and human ground truth (`drywall_walls_marked_red_by_Usman.pdf`).

4. **Module Layout & Compatibility Strategy**:
   - *Premise 4*: The Milestone prompt specifies `drywall_detection/datasets/licensing_audit.py`, while `PROJECT.md` specifies `drywall_detection/audit/dataset_auditor.py`.
   - *Conclusion*: Implement canonical logic in `drywall_detection/datasets/licensing_audit.py` and provide an identical re-export facade in `drywall_detection/audit/dataset_auditor.py`. This ensures zero import breakage regardless of caller path.

---

## 3. Caveats

1. **Air-Gapped Test Runner**: In offline CI/CD or restricted execution environments, live HTTP network checks to Zenodo or Hugging Face will fail. The `DatasetLicensingAuditor` class must bake all verified license terms into local memory, treating network connectivity checks as optional with non-fatal exception handling.
2. **FloorPlanCAD Third-Party IP**: Although FloorPlanCAD annotations are CC BY-NC 4.0, the authors expressly disclaim copyright ownership of the underlying CAD drawings. Commercial deployment should favor MSD over FloorPlanCAD to eliminate third-party copyright liability.
3. **99th Street MTA Progress Set Status**: Drawings are marked "PROGRESS SET 95% CDs 10/02/2026 - NOT FOR CONSTRUCTION". Any wall labels derived from this set must carry the `weak_pseudo_label` tag and be quarantined from the validation/test splits.

---

## 4. Conclusion

1. **Dataset Verdicts**:
   - **Eligible for Primary Ingestion (Stage 1 Pretraining)**: **Modified Swiss Dwellings (MSD)** (CC BY 4.0, 173.8 MB, WKT polygons).
   - **Eligible for Fast CPU Smoke Testing**: **CVC-FP** (CC BY 4.0 via Figshare, 353.6 MB, 122 scanned drawings).
   - **Eligible for Academic Benchmark (Held-out Validation)**: **CubiCasa5K** (CC BY-NC 4.0 / CC BY-NC-SA 4.0, 5.09 GB zip, selective extraction).
   - **Conditionally Eligible (Secondary CAD Benchmark)**: **FloorPlanCAD** (CC BY-NC 4.0 annotations, third-party drawing disclaimer).
   - **Disqualified (Gated Institutional Agreement)**: **R2V** (Proprietary LIFULL raster images, NII IDR gate).
   - **Disqualified (Fatal Ground Truth Defect)**: **SESYD** (Zero wall annotations; symbol spotting only).
   - **Disqualified (Gated Manual Application)**: **ArchCAD-400k** (Hugging Face manual 3-day review gate).

2. **Module & Deliverables Architecture**:
   - Primary module: `drywall_detection/datasets/licensing_audit.py`.
   - Facade alias: `drywall_detection/audit/dataset_auditor.py`.
   - Deliverable Markdown report: `drywall_detection/datasets/DATASET_LICENSING_REPORT.md` (and mirrored to `drywall_detection/reports/M1_audit_report.md`).
   - Deliverable JSON catalog: `drywall_detection/data/dataset_licensing_audit.json`.
   - Unit test suite: `drywall_detection/tests/test_licensing_audit.py` (9 comprehensive test cases).

---

## 5. Verification Method

To independently verify this investigation and the upcoming Worker implementation:

1. **Inspect Analysis and Dispatch Files**:
   - Read `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1\analysis.md`.
   - Read `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_1\BRIEFING.md`.

2. **Verify Live Endpoint Status & License Data**:
   Run the following Python one-liner to verify Zenodo API and Hugging Face API live responses:
   ```powershell
   python -c "import urllib.request, json; [print(k, json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})).read().decode('utf-8')).get('metadata', {}).get('license')) for k, u in [('CubiCasa5K', 'https://zenodo.org/api/records/2613548'), ('MSD', 'https://zenodo.org/api/records/7788422')]]"
   ```
   *Expected Output*:
   - `CubiCasa5K {'id': 'cc-by-nc-sa-4.0'}`
   - `MSD {'id': 'cc-by-4.0'}`

3. **Verify ArchCAD-400k Gated Status**:
   ```powershell
   python -c "import urllib.request, json; r = json.loads(urllib.request.urlopen(urllib.request.Request('https://huggingface.co/api/datasets/jackluoluo/ArchCAD', headers={'User-Agent': 'Mozilla/5.0'})).read().decode('utf-8')); print('Gated status:', r.get('gated'))"
   ```
   *Expected Output*: `Gated status: manual`

4. **Verify R2V Author Disclosure**:
   ```powershell
   python -c "import urllib.request; t = urllib.request.urlopen(urllib.request.Request('https://raw.githubusercontent.com/art-programmer/FloorplanTransformation/master/README.md', headers={'User-Agent': 'Mozilla/5.0'})).read().decode('utf-8'); print('Found LIFULL disclosure:', 'We don\'t have the permission to share the rasterized images' in t)"
   ```
   *Expected Output*: `Found LIFULL disclosure: True`

5. **Execute Unit Tests (Post-Worker Implementation)**:
   ```powershell
   pytest drywall_detection/tests/test_licensing_audit.py -v
   ```
   *Invalidation Conditions*: Any unit test failure, any hardcoded dummy facade without proper data structures, or failure to export the required Markdown and JSON files.
