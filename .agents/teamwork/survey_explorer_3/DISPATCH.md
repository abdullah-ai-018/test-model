# Dispatch: survey_explorer_3

- **Role**: Dataset Audit & ML Architectures Surveyor
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md

## Objective
Read ORIGINAL_REQUEST.md. Survey candidate datasets and segmentation model architectures.
1. Audit candidate datasets: FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, Modified Swiss Dwellings (MSD), ArchCAD-400k. Verify official sources, licensing terms, commercial/redistribution terms, annotation formats, accessibility (without bypassing access restrictions or accepting licenses on user's behalf), and applicability for wall segmentation pretraining.
2. Formulate dataset preparation pipeline: conversion of eligible datasets into a unified segmentation format, sample filtering, drawing-level train/val/test split strategy (zero leakage across drawings).
3. Benchmark and evaluate segmentation architectures: SegFormer (e.g. B0/B1), U-Net, YOLOv8-seg, etc., considering floor plan resolution, compute efficiency, and 4-class segmentation (Background, Drywall, Non-Drywall, Uncertain).
4. Propose loss functions, metrics (mIoU, Dice, F1, per-class IoU, confusion matrix), and training/fine-tuning workflow adapted to local compute.
5. Record findings in analysis.md and provide a detailed handoff.md.


## 2026-11-07T20:27:59Z
[Message] timestamp=2026-11-07T20:27:59Z sender=3c1a82ae-9b50-494e-b173-0369a8d4a486 priority=MESSAGE_PRIORITY_HIGH content=You are survey_explorer_3. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md

Your role: Dataset Audit & ML Architectures Surveyor
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3

Your tasks:
1. Audit candidate datasets: FloorPlanCAD, CubiCasa5K, CVC-FP, R2V, SESYD, Modified Swiss Dwellings (MSD), ArchCAD-400k. Verify official sources, licensing terms, commercial/redistribution terms, annotation formats, accessibility (without bypassing access restrictions or accepting licenses on user's behalf), and applicability for wall segmentation pretraining.
2. Formulate dataset preparation pipeline: conversion of eligible datasets into a unified segmentation format, sample filtering, drawing-level train/val/test split strategy (zero leakage across drawings).
3. Benchmark and evaluate segmentation architectures: SegFormer (e.g. B0/B1), U-Net, YOLOv8-seg, etc., considering floor plan resolution, compute efficiency, and 4-class segmentation (Background, Drywall, Non-Drywall, Uncertain).
4. Propose loss functions, metrics (mIoU, Dice, F1, per-class IoU, confusion matrix), and training/fine-tuning workflow adapted to local compute.
5. Maintain your liveness in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\progress.md with timestamps.
6. Write your comprehensive technical investigation in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\analysis.md and write a complete handoff in c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_3\handoff.md.
7. Notify the orchestrator via send_message when done with the path to your handoff.md.
