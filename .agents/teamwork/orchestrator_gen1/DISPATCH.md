## 2026-11-07T20:19:40Z

Build an isolated `drywall_detection/` module within the QTO Engine project to detect architectural walls, parse partition schedules, and classify drywall using a vector-first pipeline combined with machine learning segmentation on architectural drawings.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Integrity mode: development

## Reference Material
- Reference PDF: 99th Street (MTA Contract C-48526) architectural set (71 pages, 1728 x 2592 pt, rotation 90, vector PDF with embedded fonts/text layer, "PROGRESS SET 95% CDs 10/02/2026").
- Target Datasets to audit: CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD Floorplans, Modified Swiss Dwellings (MSD).

## Requirements: R1, R2, R3, R4, R5
Milestones M1 through M6 in strict order.


## 2026-11-07T20:25:44Z

Build, train, fine-tune, evaluate, and deliver a practical AI model as a capability showcase for detecting architectural walls and classifying drywall on architectural PDF drawings and floor plans, supported by a simple local PDF testing interface for previewing and downloading annotated drawings.

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Integrity mode: development

## Reference Material
- Priority Dataset 1: FloorPlanCAD (https://floorplancad.github.io)
- Priority Dataset 2: CubiCasa5K (https://zenodo.org/records/2613548, https://github.com/CubiCasa/CubiCasa5k)
- Supporting / Audited Datasets: CVC-FP (https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/), R2V (https://art-programmer.github.io/floorplan-transformation/paper.pdf), SESYD (https://hyper.ai/en/datasets/34280), Modified Swiss Dwellings (MSD) (https://data.4tu.nl/datasets/e1d89cb5-6872-48fc-be63-aadd687ee6f9), ArchCAD-400k (https://arxiv.org/html/2503.22346v3)
- Architectural Drawings: The team searches the workspace for any supplied architectural PDF drawings (prioritizing floor plans A-101 to A-104, partition types sheets A-900 and A-901, wall details A-902, and firestopping details A-910).

## Requirements

### R1. Dataset Research, Licensing Audit & Unified Preparation
Audit candidate datasets (FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, MSD, ArchCAD-400k) verifying official sources, licenses, commercial/redistribution terms, and wall/annotation availability without bypassing access restrictions or accepting licenses on the user's behalf. Download eligible datasets, inspect images and annotations, convert useful annotations into a unified segmentation format, filter corrupted or duplicate samples, and generate visual quality-control reports.

### R2. Drywall-Specific Evidence & Ground Truth Verification
Use generic wall annotations for wall segmentation pretraining; do not assume generic wall labels indicate drywall. Investigate partition schedules, wall-type identifiers, legends, and construction specifications from available architectural drawings in the workspace to establish verified drywall and non-drywall labels. Any wall lacking verified material evidence must be classified as Uncertain / Manual Review. If sufficient verified drywall labels are unavailable, train the strongest possible wall segmentation model and document the required annotations.

### R3. Model Benchmarking, Hardware Adaptation & Checkpoint Delivery
Benchmark semantic segmentation (SegFormer, U-Net), instance segmentation (YOLOv8-seg), and vector-based drawing understanding (PyMuPDF path and coordinate extraction preserving original PDF geometry). Inspect local hardware (GPU, CUDA, VRAM, RAM, CPU) and auto-adapt training configuration, or prepare reproducible GPU workflows if local compute is constrained. Train and fine-tune models using drawing-level train/val/test splits to avoid data leakage, apply suitable loss functions, and evaluate mIoU, per-class IoU, Dice, precision, recall, and confusion matrix. Save the best checkpoint and model bundle to `drywall_detection/checkpoints/best_model/`. Do not implement complete QTO engine features (measurements, quantity calculations, costing, or estimating).

### R4. Local PDF Testing Interface & Inference Pipeline
Implement an inference script and a simple local PDF testing interface that accepts architectural PDFs (both vector-based and scanned), processes all pages, runs the trained model, and generates downloadable annotated PDFs preserving original page dimensions and drawing quality. Display processing status and interactive page previews. Render Drywall in Green, Non-Drywall in Red, and Uncertain in Yellow. Validate the interface and model on held-out architectural drawings not used during training.

## Acceptance Criteria

### Dataset Audit & Preparation
- [ ] Dataset licensing report is produced documenting terms, commercial restrictions, and official sources for all candidate datasets.
- [ ] Eligible datasets are converted to a unified segmentation format with visual QC samples generated.
- [ ] Train, validation, and test splits are strictly separated at drawing level with zero project overlap.

### Model Benchmarking & Checkpoint Delivery
- [ ] Local compute environment (GPU, CUDA, memory, CPU, Python) is audited and logged.
- [ ] At least two candidate segmentation architectures are trained and comparatively evaluated on unseen drawings.
- [ ] Best model checkpoint is saved under `drywall_detection/checkpoints/best_model/` alongside model configuration, class mapping, dependencies, and loading instructions.
- [ ] Saved checkpoint is verified to reload from disk and execute inference without error.

### Classification Guardrails & Reporting
- [ ] Model outputs classify regions strictly into Background (0), Drywall (1, Green), Non-Drywall (2, Red), and Uncertain (3, Yellow).
- [ ] Generic wall detections are not presented as confirmed drywall without verified ground truth; ambiguous partitions are classified as Uncertain.
- [ ] A final report documents evaluation metrics (mIoU, Dice, F1), domain limitations, and additional annotations needed for higher drywall accuracy.

### PDF Testing Interface & End-to-End Validation
- [ ] Local PDF testing interface allows uploading vector and scanned architectural PDFs, displays processing progress, and previews annotated pages.
- [ ] Annotated PDF export preserves original drawing dimensions and layout with color-coded masks.
- [ ] End-to-end inference is validated on held-out architectural drawings not seen during training.
