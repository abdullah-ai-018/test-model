# Handoff Report — Dataset & ML Architecture Surveyor (`survey_explorer_3`)

**Recipient:** Orchestrator (`3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`)  
**Workspace:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3`  
**Date:** 2026-11-07T20:31:00Z  
**Status:** Task Complete (Hard Handoff)

---

## 1. Observation

1. **Zenodo API Query for CubiCasa5K** (`record/2613548`):
   - Command: `python -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('https://zenodo.org/api/records/2613548').read().decode()); print([(f['key'], f['size']/(1024*1024*1024)) for f in data['files']]); print('license:', data['metadata'].get('license'))"`
   - Result: `[('cubicasa5k.zip', 5.093864822760224)]`, `license: {'id': 'cc-by-nc-sa-4.0'}`.
   - Exact size: 5.09 GB (under 10 GB limit), direct public download, CC BY-NC-SA 4.0 license.

2. **FloorPlanCAD Official Website Audit** (`https://floorplancad.github.io/`):
   - Project site fetched via Python HTTP request.
   - Text extracted:
     - License: *"The annotations in this dataset along with this website belong to us and are licensed under a Creative Commons Attribution-NonCommercial 4.0 License. We do not own the copyright of the drawings."*
     - Download: Direct links to Google Drive (`1HcyKt6qWeXog-tRfvEjdO3O3TN91PXGL`, `1kSS7OB_EEu7VJzb0W8DK9_nu1EvshioV`, `1jxpYgxnLUbXEzMOsjaMPQFSuvmvHimiZ`).
     - Mirror on Hugging Face: `Voxel51/FloorPlanCAD` (454 MB).

3. **CVC-FP Server Audit & Figshare Mirror**:
   - Primary server `http://dag.cvc.uab.es/resources/floorplans/` timed out (`urllib.error.URLError: <urlopen error timed out>`).
   - Figshare API (`https://api.figshare.com/v2/articles/12082131`):
     - Title: *"Data and codes of Indoor mapping and modeling by parsing floor plan images"*
     - License: `CC BY 4.0`
     - Files: `1-WID512_ROTATE.tar.gz` (353.6 MB), direct public download.

4. **R2V (Raster-to-Vector) Official Host & Access Restriction**:
   - Official repository: `https://github.com/art-programmer/FloorplanTransformation`.
   - Observation: Repository only contains vector geometry files. Raw raster images originate from LIFULL Co., Ltd. and require a formal application and signed institutional agreement with the National Institute of Informatics (NII) IDR (`https://www.nii.ac.jp/dsc/idr/en/lifull/1.html`).

5. **SESYD Floorplans Official Host & Annotation Content**:
   - Official URL: `http://mathieu.delalandre.free.fr/projects/sesyd/symbols/floorplans.html`.
   - Table inspection of 16 floorplan sets (`floorplans16-01` to `floorplans16-16`): each zip is ~6 MB.
   - Observation: Annotations exist solely for 16 symbol models (doors, windows, armchairs, tables, sinks, beds). Zero wall segmentation annotations or wall polygons exist in SESYD.

6. **Modified Swiss Dwellings (MSD) Hugging Face & Zenodo Audit**:
   - Hugging Face API (`https://huggingface.co/api/datasets/philippds/modified-swiss-dwellings-enriched`):
     - License: `cc-by-4.0`.
     - Download size: `173,829,500` bytes (173.8 MB). Dataset size: `1.52 GB`.
     - Splits: train (4,572 examples), test (800 examples).
     - Features: `site_id`, `building_id`, `plan_id`, `struct_in` (wall image), `full_out` (full image), and `geometries` config with `entity_type: separator`, `entity_subtype: WALL`.
   - Zenodo API (`record/7788422`):
     - Archive: `swiss-dwellings-v3.0.0.zip` (888.7 MB), license: `cc-by-4.0`.

7. **Local Hardware and Package Environment** (from `.agents/teamwork/explorer_survey_1/env_audit.json`):
   - CPU: Intel Core (4 physical / 8 logical cores).
   - RAM: 7.88 GB total, 0.90 GB available (88.5% used).
   - Disk: C: has 16.37 GB free; E: has 30.45 GB free.
   - PyTorch: `2.1.0+cpu`, CUDA available: `false`, VRAM: 0 GB.
   - Installed: `fitz` (PyMuPDF), `pdfplumber` 0.11.7, `shapely` 2.1.1, `cv2` 4.11.0, `transformers` 4.41.2, `ultralytics` 8.3.167, `timm` 1.0.22.
   - Uninstalled: `albumentations`, `segmentation_models_pytorch`.

---

## 2. Logic Chain

1. **Dataset Selection Reasoning**:
   - *Premise 1*: The project requires training a wall segmentation model using public datasets without bypassing access restrictions, accepting licenses on the user's behalf, or downloading >10 GB unannounced (Requirement R2).
   - *Observation 4*: R2V requires an institutional agreement and credentials from NII IDR $\implies$ R2V cannot be downloaded autonomously.
   - *Observation 5*: SESYD contains only symbol bounding boxes and lacks wall segmentation labels entirely $\implies$ SESYD cannot train a wall segmentation model.
   - *Observation 1 & 6*: Modified Swiss Dwellings (MSD) has CC BY 4.0 license, 174 MB download size, and explicit WKT wall polygons. CubiCasa5K has 5.09 GB download size, CC BY-NC-SA 4.0 license, and explicit SVG wall polygons.
   - *Conclusion*: **MSD is the top recommended primary dataset** (lightweight, permissive CC BY 4.0, structured hierarchical IDs), and **CubiCasa5K is the primary academic benchmark** (5.09 GB < 10 GB). FloorPlanCAD and CVC-FP are secondary/conditional options.

2. **Data Splitting Reasoning**:
   - *Premise 2*: Multiple sheets or levels of the same building share footprints, structural column grids, and firm-specific CAD drafting conventions.
   - *Inference*: Splitting drawings by image index causes severe data leakage, artificially inflating validation metrics while destroying generalization to new buildings.
   - *Conclusion*: Data splitting must be strictly enforced at the source project level (`site_id` / building folder), ensuring zero project overlap between train, validation, and test sets.

3. **ML Architecture & Loss Formulation Reasoning**:
   - *Premise 3*: Architectural walls form an interconnected continuous planar graph (connected loops, T-junctions, cross-junctions).
   - *Inference*: Instance segmentation (YOLOv8-seg) is fundamentally mismatched because continuous walls cannot be cleanly bounded into non-overlapping boxes without heavy NMS clipping.
   - *Inference*: Semantic segmentation (U-Net with pretrained encoder, SegFormer-B0/B1) natively predicts continuous pixel-wise wall probability maps.
   - *Premise 4*: Walls occupy only 5%–15% of pixels, creating extreme class imbalance.
   - *Conclusion*: A compound **Dice + Focal Loss** (or Dice + Cross-Entropy) is mandatory to prevent the network from collapsing to all-background predictions.

4. **Hardware & Google Colab Reasoning**:
   - *Observation 7*: The local execution environment has no CUDA GPU, `torch 2.1.0+cpu`, and only ~0.9 GB available RAM.
   - *Inference*: Full-scale model training locally on CPU will suffer from severe memory throttling and slow convergence.
   - *Conclusion*: Training scripts must be strictly Google Colab compatible (auto-detecting GPU vs CPU, auto-scaling batch size and resolution, headless logging, Google Drive persistence), while lightweight CPU sanity runs are provided locally.

5. **Weak Pseudo-Labeling Guardrail Reasoning**:
   - *Premise 5*: The 99th Street PDF is a single commercial transit facility progress set (95% CDs), fundamentally different from residential academic floor plans.
   - *Inference*: Vector-extracted wall masks from 99th Street can help adapt the model to commercial CAD styles, but contain automated extraction noise.
   - *Conclusion*: Vector-derived masks must be tagged as `weak_pseudo_label`, visually spot-checked for error rate (5–10 regions), and **strictly isolated from validation and test sets** to avoid invalid, circular evaluation metrics.

---

## 3. Caveats

1. **FloorPlanCAD Drawing Copyright Disclaimer**:
   FloorPlanCAD annotations are CC BY-NC 4.0, but the authors explicitly do not own the copyright of the underlying CAD drawings and disclaim liability. Downloading the CAD drawings places copyright compliance on the user.
2. **CVC-FP Server Unavailability**:
   The official UAB server (`dag.cvc.uab.es`) is currently unresponsive. Anyone utilizing CVC-FP must rely on the Figshare or Zenodo mirrors.
3. **Local Hardware Constraints**:
   The host machine has ~0.9 GB available RAM. Training deep segmentation networks locally requires small image crops ($256 \times 256$ or $512 \times 512$ with batch size 1–2) or offloading to Google Colab.
4. **99th Street Document Status**:
   The reference PDF is explicitly a "PROGRESS SET 95% CDs" (dated 10/02/2026), not an approved as-built drawing. Any findings or extracted geometries represent an unapproved progress milestone and a single project that cannot prove generalizability.

---

## 4. Conclusion

1. **Dataset Selection for Milestone M2**:
   - **Primary**: **Modified Swiss Dwellings (MSD)** via Hugging Face (`philippds/modified-swiss-dwellings-enriched`): 174 MB download, CC BY 4.0, explicit wall polygons, zero authentication barriers.
   - **Secondary Benchmark**: **CubiCasa5K** via Zenodo: 5.09 GB download (< 10 GB limit), CC BY-NC-SA 4.0.
   - **Reject**: R2V (blocked by institutional login) and SESYD (lacks wall annotations).
2. **Splitting Protocol**:
   - Partition strictly by `site_id` / project ID (70% train, 15% val, 15% test) with mathematical zero project overlap.
3. **Model Selection for Milestone M4**:
   - Train and compare **U-Net (ResNet34 encoder)** and **SegFormer-B0/B1** using compound **Dice + Focal Loss**.
   - Save champion model in `drywall_detection/checkpoints/best_model/` with config, class mapping, logs, metrics, sample overlays, and standalone `infer.py`.
4. **Guardrails for 99th Street**:
   - Vector-extracted masks from 99th Street may serve as weak pseudo-labels for fine-tuning only if explicitly marked as weak, visually spot-checked, and completely barred from validation and test sets.

---

## 5. Verification Method

To independently verify the empirical claims in this report, execute the following commands in the workspace:

1. **Verify Zenodo CubiCasa5K File Size and License**:
   ```powershell
   python -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('https://zenodo.org/api/records/2613548').read().decode()); print([(f['key'], round(f['size']/(1024**3), 2)) for f in data['files']]); print('license:', data['metadata'].get('license'))"
   ```
   *Expected Output*: `[('cubicasa5k.zip', 5.09)]`, `license: {'id': 'cc-by-nc-sa-4.0'}`.

2. **Verify Modified Swiss Dwellings Hugging Face Metadata**:
   ```powershell
   python -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('https://huggingface.co/api/datasets/philippds/modified-swiss-dwellings-enriched').read().decode()); print('license:', data['cardData'].get('license')); print('download_size_mb:', round(data['cardData']['dataset_info'][0]['download_size']/(1024**2), 2))"
   ```
   *Expected Output*: `license: cc-by-4.0`, `download_size_mb: 165.78` (or ~174 MB total).

3. **Verify Local Environment Constraints (CPU / RAM)**:
   ```powershell
   python -c "import psutil, torch; print('PyTorch:', torch.__version__, '| CUDA:', torch.cuda.is_available(), '| Free RAM GB:', round(psutil.virtual_memory().available/(1024**3), 2))"
   ```
   *Expected Output*: `PyTorch: 2.1.0+cpu | CUDA: False | Free RAM GB: < 1.5`.

4. **Verify Detailed Survey Report Existence**:
   Inspect `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3\report.md`.
