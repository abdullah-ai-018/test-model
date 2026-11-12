# Handoff Report: Dataset Audit & ML Architectures Surveyor

**Subagent:** `survey_explorer_3`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3`  
**Date:** 2026-11-07T20:37:00Z  
**Type:** Hard (Task Complete)  

---

## 1. Observation

1. **Local Hardware & Deep Learning Environment**:
   - Python Environment & Libraries (Command: `python -c "import sys; print('Python:', sys.version); ..."`):
     * Python: `3.10.0 (tags/v3.10.0:b494f59, Oct 4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]`
     * PyTorch: `torch == 2.1.0+cpu`
     * TorchVision: `torchvision == 0.16.0+cpu`
     * Hugging Face Transformers: `transformers == 4.41.2`
     * Ultralytics: `ultralytics == 8.3.167`
     * PyMuPDF: `fitz (PyMuPDF)` installed
     * OpenCV: `cv2 == 4.11.0`
     * Pillow: `PIL == 10.2.0`
     * Scikit-Learn: `sklearn == 1.7.2`
     * PyTorch Image Models: `timm == 1.0.22`
     * Shapely: `shapely == 2.1.1`
     * Missing Libraries: `segmentation_models_pytorch` (Not installed), `albumentations` (Not installed).
   - Compute Constraints (Command: `python -c "import torch, psutil, platform; ..."` and `nvidia-smi`):
     * OS: `Windows-10-10.0.26100-SP0` (Windows 11 AMD64)
     * CPU: 4 physical cores, 8 logical cores
     * System RAM: 7.88 GB total, **~0.9 GB to 1.5 GB available RAM** (over 88% utilized)
     * CUDA Availability: `CUDA Available: False`
     * `nvidia-smi`: Term not recognized (`CommandNotFoundException`). Strictly CPU execution environment.

2. **Candidate Datasets Licensing, Formats & Accessibility Audit**:
   - **Modified Swiss Dwellings (MSD)**:
     * Source: 4TU.ResearchData (`doi:10.4121/e1d89cb5-6872-48fc-be63-aadd687ee6f9`), Zenodo (`10.5281/zenodo.7788422`), Hugging Face `philippds/modified-swiss-dwellings-enriched`.
     * License: **CC BY 4.0** (Permissive; commercial use allowed with attribution).
     * Download Size: 173.8 MB (Hugging Face) / 888.7 MB (Zenodo zip).
     * Format: WKT (Well-Known Text) vector polygons in CSV + raster channels (`struct_in`). Explicit `entity_type: separator`, `entity_subtype: WALL`.
     * Accessibility: Direct HTTP/API download without authentication or gating.
   - **CubiCasa5K**:
     * Source: Zenodo Record `2613548`, GitHub `CubiCasa/CubiCasa5k`.
     * License: **CC BY-NC 4.0** (Non-commercial research only).
     * Download Size: 5.09 GB compressed zip (`cubicasa5k.zip`).
     * Format: High-resolution raster images + Vector SVG polygons (`<polygon class="Wall">`).
     * Accessibility: Direct public HTTP download from Zenodo CDN; no credentials required.
   - **FloorPlanCAD**:
     * Source: GitHub Pages (`floorplancad.github.io`), Hugging Face `Voxel51/FloorPlanCAD`.
     * License: Annotations CC BY-NC 4.0; CAD drawings have third-party copyright disclaimer ("Users accept full responsibility for use of copyrighted dataset").
     * Download Size: 454 MB (Hugging Face mirror) / ~3.5 GB (Google Drive).
     * Format: Vector SVG primitives and PNG crops ($20\text{m} \times 20\text{m}$). Wall is Stuff class (ID 0).
     * Accessibility: Active mirrors on Hugging Face and Google Drive.
   - **CVC-FP**:
     * Source: CVC UAB, Figshare (`10.6084/m9.figshare.12082131`), Zenodo (`10.5281/zenodo.7921780`).
     * License: CC BY 4.0 (Figshare mirror) / Academic Non-commercial (CVC).
     * Download Size: 353.6 MB (Figshare).
     * Format: 122 scanned floor plans in 4 styles + SVG vector ground truth / binary PNG masks.
     * Accessibility: University host timed out; fully accessible via Figshare / Zenodo mirrors.
   - **R2V (Raster-to-Vector)**:
     * Source: Liu et al., ICCV 2017 (`art-programmer/FloorplanTransformation`).
     * License / Access Restriction: Gated behind National Institute of Informatics (NII) IDR institutional agreement with LIFULL HOME'S Co., Ltd. Only text vector annotations are public; raster images cannot be downloaded autonomously.
   - **SESYD Floorplans**:
     * Source: Delalandre et al., IJDAR 2010 (`mathieu.delalandre.free.fr/projects/sesyd/`).
     * License: Open access academic research.
     * Annotation Defect: Synthetically generated for symbol recognition (16 furniture/fixture symbols). **Zero ground-truth wall or partition annotations exist**.
   - **ArchCAD-400k**:
     * Source: Luo et al., March 2025 (`arXiv:2503.22346v3`), Hugging Face `jackluoluo/ArchCAD`.
     * License / Access Restriction: Gated repository requiring institutional email verification, credential submission, and manual license agreement on Hugging Face. Cannot be accessed autonomously without user credentials.

3. **Existing Analysis Files and Project Artifacts**:
   - `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\analysis.md`: Contains the complete technical survey report (6 sections, 530+ lines) detailing the 7 dataset profiles, unified dataset specification, resolution/tiling mechanics, SegFormer/U-Net/YOLOv8-seg benchmarks, compound loss formulation, evaluation metrics, and local CPU adaptation workflows.

---

## 2. Logic Chain

1. **Eligibility Logic for Candidate Datasets**:
   - *Premise*: Requirement R1 and system constraints dictate: (a) verify licenses and commercial/redistribution terms, (b) never bypass access controls or accept terms on the user's behalf, (c) verify ground-truth wall availability.
   - *Step 1*: R2V requires an institutional data agreement with NII IDR for raster images $\implies$ Autonomous download is impossible without bypassing access restrictions $\implies$ **R2V is disqualified**.
   - *Step 2*: SESYD contains only 16 symbol categories (armchair, sink, table, etc.) and lacks wall annotations $\implies$ Cannot provide wall supervision $\implies$ **SESYD is disqualified for wall segmentation**.
   - *Step 3*: ArchCAD-400k is gated on Hugging Face requiring institutional credentials and manual license agreement $\implies$ Autonomous agent cannot accept terms on user's behalf $\implies$ **ArchCAD-400k is disqualified for autonomous ingestion**.
   - *Step 4*: Modified Swiss Dwellings (MSD) has a permissive CC BY 4.0 license, explicit WKT wall polygons, compact 174 MB download, and direct public API access $\implies$ **MSD is the Top Recommended & Fully Eligible dataset**.
   - *Step 5*: CubiCasa5K has 5,000 floor plans and explicit SVG wall polygons under CC BY-NC 4.0 with direct Zenodo download $\implies$ **CubiCasa5K is the Primary Academic Benchmark dataset**.

2. **Resolution & Tiling Logic**:
   - *Premise*: Architectural drawings rendered at $200\text{ DPI}$ produce $4,800 \times 7,200\text{ to }10,800 \times 14,400$ pixel canvases. Physical $4.5''\text{ to }6''$ drywall partitions occupy 8 to 12 pixels across their width.
   - *Step 1*: Naively downsampling a $4,800 \times 7,200$ drawing to $512 \times 512$ reduces an 8-pixel wall to $\sim 0.57$ pixels.
   - *Step 2*: Sub-pixel collapse destroys partition lines into anti-aliasing blur, preventing convolutional or attention filters from identifying walls.
   - *Conclusion*: High-resolution sliding-window tiling ($512 \times 512$ patches with 20–25% overlap) paired with 2D Gaussian apodization window blending during reconstruction is mathematically mandatory.

3. **Architecture Selection Logic**:
   - *Premise*: Architectural walls form interconnected, continuous planar graphs ("stuff" category with T-junctions and perimeter loops), not isolated countable "things" (doors, chairs).
   - *Step 1*: YOLOv8-seg relies on bounding-box proposals. Bounding boxes around intersecting corridor walls overlap extensively, causing Non-Maximum Suppression (NMS) to clip or suppress connected wall intersections and fragmenting continuous partitions.
   - *Step 2*: Semantic segmentation models (SegFormer, U-Net) predict per-pixel categorical distributions without bounding boxes or NMS suppression, naturally preserving continuous graph topology.
   - *Step 3*: Local compute is strictly CPU with $< 1.5\text{ GB}$ available RAM. SegFormer-B0 has 3.71M parameters (8.4 GFLOPs) and Lightweight U-Net has 2.5M–14.3M parameters, both easily fitting into CPU memory, while heavier transformers (SegFormer-B4/B5) or DeepLabV3+ with ResNet-101 cause severe memory paging.
   - *Conclusion*: SegFormer-B0 and Lightweight U-Net are selected as the two comparative benchmark architectures.

4. **Classification Guardrail & Ground Truth Logic**:
   - *Premise*: Public datasets (MSD, CubiCasa5K, FloorPlanCAD) label walls generically as structural boundaries without material specifications (drywall/gypsum vs CMU vs concrete).
   - *Step 1*: Generic wall annotations can only be used for Stage 1 binary wall vs background pretraining.
   - *Step 2*: In Stage 2 fine-tuning, only walls with verified partition schedule callouts (e.g., Partition Type P1 gypsum board on metal studs) can be labeled as Drywall (Class 1, Green). Walls with confirmed masonry/concrete specifications must be labeled as Non-Drywall (Class 2, Red).
   - *Conclusion*: Any wall lacking verified partition schedule ground truth MUST be mapped to Uncertain (Class 3, Yellow). Generic wall detections must never be claimed as confirmed drywall without verified ground truth.

---

## 3. Caveats

1. **Pretraining Domain Shift**:
   - Public datasets (MSD, CubiCasa5K) represent European and Nordic residential layouts. Commercial architectural drawings (such as the MTA 99th Street transit facility set) contain much denser MEP infrastructure, structural columns, diagonal masonry hatching, and multi-hour fire-rated shaft assemblies. Fine-tuning on actual architectural sheets is essential to bridge this domain shift.
2. **Local CPU Training Speed**:
   - While SegFormer-B0 and Lightweight U-Net fit within the 7.88 GB system RAM (< 1.5 GB free), training on CPU without CUDA acceleration will require approximately 3–5 minutes per epoch on a 500-tile dataset. Training runs should be constrained to 15–20 epochs with early stopping (patience = 5).
3. **Third-Party CAD Copyright in FloorPlanCAD**:
   - While FloorPlanCAD annotations are CC BY-NC 4.0, the authors disclaim CAD drawing copyright ownership. If commercial redistribution is required downstream, Modified Swiss Dwellings (CC BY 4.0) must remain the primary source.

---

## 4. Conclusion

1. **Dataset Selection**:
   - Adopt **Modified Swiss Dwellings (MSD)** as the primary pretraining dataset (CC BY 4.0, 174 MB Hugging Face download, clean WKT vector wall polygons).
   - Adopt **CubiCasa5K** as the secondary reference benchmark (CC BY-NC 4.0, Zenodo Record 2613548).
   - Disqualify R2V (gated LIFULL images), SESYD (no wall ground truth), and ArchCAD-400k (gated license agreement).
2. **Dataset Preparation**:
   - Convert all training data into the unified format: single-channel 8-bit indexed PNG masks (`uint8`, values 0..3) paired with RGB image tiles.
   - Enforce strict drawing-level splitting ($\text{Projects}_{\text{train}} \cap \text{Projects}_{\text{val}} = \emptyset$) using hierarchical grouping keys (`site_id` / drawing sheet ID) to eliminate architectural data leakage.
   - Implement sliding-window $512 \times 512$ tiling with 20% overlap and 2D Gaussian apodization blending.
3. **Model Architecture & Training**:
   - Benchmark **SegFormer-B0** (Mix-Transformer, 3.7M params) and **Lightweight U-Net** (ResNet18 / Mini-UNet encoder, 2.5M–14.3M params) using compound Class-Weighted Cross-Entropy + Soft Dice + Focal Loss.
   - Configure local CPU execution with batch size = 2 to 4, gradient accumulation (accum_steps = 4), and CPU thread allocation (`torch.set_num_threads(4)`).
   - Deliver trained champion checkpoint bundle to `drywall_detection/checkpoints/best_model/` with verified `infer.py` reloading interface and ONNX export.
4. **Guardrails**:
   - Maintain strict 4-class taxonomy: 0: Background, 1: Drywall (Green), 2: Non-Drywall (Red), 3: Uncertain (Yellow). Any wall lacking verified partition schedule material evidence must remain Uncertain.

---

## 5. Verification Method

To independently verify the facts, hardware metrics, and dataset properties reported:

1. **Verify Local Compute Environment**:
   ```powershell
   python -c "import torch, psutil; print('Torch:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('RAM Free GB:', round(psutil.virtual_memory().available / (1024**3), 2)); print('CPU Cores:', psutil.cpu_count(logical=True))"
   ```
   *Expected Output*: Torch `2.1.0+cpu`, CUDA `False`, RAM Free `< 1.5 GB`, CPU Cores `8`.

2. **Verify Installed Computer Vision & Transformer Libraries**:
   ```powershell
   python -c "import transformers, ultralytics, fitz, cv2, PIL, shapely; print('transformers:', transformers.__version__); print('ultralytics:', ultralytics.__version__); print('fitz:', fitz.__doc__.split('\n')[0]); print('cv2:', cv2.__version__)"
   ```
   *Expected Output*: `transformers 4.41.2`, `ultralytics 8.3.167`, `fitz` PyMuPDF bindings, `cv2 4.11.0`.

3. **Verify Modified Swiss Dwellings (MSD) Open Access via Hugging Face API**:
   ```powershell
   python -c "import urllib.request, json; res = urllib.request.urlopen('https://huggingface.co/api/datasets/philippds/modified-swiss-dwellings-enriched'); print('Status:', res.status); data = json.loads(res.read()); print('Dataset ID:', data.get('id')); print('Tags:', data.get('tags')[:5])"
   ```
   *Expected Output*: Status `200`, Dataset ID `philippds/modified-swiss-dwellings-enriched`.

4. **Verify CubiCasa5K Zenodo Record Metadata & Download Size**:
   ```powershell
   python -c "import urllib.request, json; res = urllib.request.urlopen('https://zenodo.org/api/records/2613548'); data = json.loads(res.read()); print('Title:', data['metadata']['title']); print('License:', data['metadata']['license']); print('File:', data['files'][0]['key'], 'Size GB:', round(data['files'][0]['size'] / (1024**3), 2))"
   ```
   *Expected Output*: Title `CubiCasa5k`, License `cc-by-nc-4.0`, File `cubicasa5k.zip`, Size `5.09 GB`.

5. **Verify ArchCAD-400k Gated Status on Hugging Face**:
   ```powershell
   python -c "import urllib.request, json; res = urllib.request.urlopen('https://huggingface.co/api/datasets/jackluoluo/ArchCAD'); data = json.loads(res.read()); print('Gated:', data.get('gated', False))"
   ```
   *Expected Output*: `Gated: True` (Confirms gated access restriction).

6. **Inspect Full Technical Survey Report**:
   - Inspect `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\analysis.md` for full technical sections, formulas, matrices, and training workflows.
