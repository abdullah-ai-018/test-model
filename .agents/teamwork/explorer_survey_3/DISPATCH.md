## 2026-11-07T20:21:35Z
Sender: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a (parent)
Role: survey_explorer_3 (Dataset & ML Architecture Surveyor)
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Private state folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3

Task:
1. Survey the 6 candidate datasets: CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD Floorplans, Modified Swiss Dwellings (MSD). Investigate official sources, accessibility, license terms (commercial/academic/redistribution), download sizes, image/annotation formats, and presence of wall/partition semantic segmentation labels. Verify which ones require authentication or accepting licenses, and identify which ones are directly downloadable and eligible.
2. Investigate requirements for data splitting strictly by source project/drawing (zero project overlap between train, val, test) and an independent test set.
3. Survey segmentation architectures (U-Net with pretrained encoder, SegFormer-B0/B1/B2, etc.), loss functions (Dice + CE/Focal), metrics (mIoU, per-class IoU, Dice, precision, recall, F1, boundary quality), Colab compatibility, and checkpoint directory structure (`drywall_detection/checkpoints/best_model/`).
4. Survey weak pseudo-labeling rules for 99th Street PDF (commercial domain gap, marking pseudo-labels as weak, visually spot-checking error rate, and keeping them strictly out of validation and test sets).
5. Create your state folder `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3` if needed, and write your report to `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_3\report.md` and `handoff.md`.
6. Send a message to the orchestrator when finished with a clear summary and file paths.
