# TEST_READY: 4-Tier Opaque-Box E2E Test Suite Specification
## Milestone M5: Drywall Detection & Classification Pipeline

**Status:** CERTIFIED TEST-READY  
**Version:** 1.0.0  
**Test Framework:** Pytest (v9.x)  
**Target Execution Environment:** Local Windows 11 CPU / PyTorch 2.x  
**Specification Reference:** `TEST_INFRA.md`, `PROJECT.md`, `ORIGINAL_REQUEST.md`  
**Total E2E Test Target:** **170 Test Cases** (Tiers 1–4)  
**Total Project Suite:** **1,147 Test Cases** (including 977 unit/stress regression tests)

---

## 1. Executive Summary & Test Readiness Certification

This document formally certifies that the opaque-box end-to-end (E2E) testing suite for the `drywall_detection` module is fully specified, architected, and ready for execution under Milestone M5.

The test suite satisfies all requirements set forth in `ORIGINAL_REQUEST.md` (R1 through R4) and the testing contracts in `PROJECT.md` and `TEST_INFRA.md`. Testing strictly follows an **opaque-box requirement-driven philosophy**: all tests exercise public CLI commands, high-level API entry points, and interface contracts without coupling to internal module private methods.

```
================================================================================
                           4-TIER TEST SUITE SUMMARY
================================================================================
Tier 1: Feature Coverage (15 Features x 5 Tests/Feature) ............. 75 Tests
Tier 2: Boundary & Corner Cases (15 Features x 5 Tests/Feature) ...... 75 Tests
Tier 3: Cross-Feature Pairwise Interactions (15 Pairwise Flows) ...... 15 Tests
Tier 4: Real-World Workload Scenarios (5 Full Workflows) .............  5 Tests
--------------------------------------------------------------------------------
TOTAL OPAQUE-BOX E2E TEST TARGET: ................................... 170 Tests
EXISTING UNIT, REGRESSION & ADVERSARIAL TESTS: ...................... 977 Tests
================================================================================
TOTAL COMBINED TEST SUITE: ......................................... 1,147 Tests
================================================================================
```

---

## 2. Feature Inventory & Coverage Mapping Matrix

All 15 features (F1 through F15) mapped across requirements R1–R4, Milestones M1–M5, and testing tiers:

| # | Feature ID | Feature Name | Requirement | Primary Public Interface | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---|---|:---:|---|:---:|:---:|:---:|:---:|
| **F1** | `F-DATASET-AUDIT` | Dataset Licensing Audit | R1 | `DatasetAuditor`, `CANDIDATE_DATASETS` | 5 | 5 | ✓ | ✓ |
| **F2** | `F-DATA-UNIFY` | Unified Dataset Preparation | R1 | `DatasetPreparer`, `GeometryRasterizer` | 5 | 5 | ✓ | ✓ |
| **F3** | `F-DATA-SPLIT` | Drawing-Level Split Integrity | R1 | `ProjectDataSplitter`, `SplitManifestBundle` | 5 | 5 | ✓ | ✓ |
| **F4** | `F-SCHED-PARSE` | Drawing Inventory & Schedule Mining | R2 | `VectorExtractor`, `PartitionScheduleParser` | 5 | 5 | ✓ | ✓ |
| **F5** | `F-CLASS-RULE` | 4-Class Classification Guardrails | R2 | `DrywallClassifier`, `ClassifiedWallPolygon` | 5 | 5 | ✓ | ✓ |
| **F6** | `F-VEC-TRANSFORM`| Ground Truth & Coordinate Alignment | R2 | `CoordinateTransformer`, `pdf_to_pixel` | 5 | 5 | ✓ | ✓ |
| **F7** | `F-ENV-AUDIT` | Model Benchmarking on CPU | R3 | `HardwareProfile`, `probe_all_hardware` | 5 | 5 | ✓ | ✓ |
| **F8** | `F-MODEL-TRAIN` | Model Training & Fine-Tuning | R3 | `SegmentationTrainer`, `CompoundLoss` | 5 | 5 | ✓ | ✓ |
| **F9** | `F-LOSS-METRICS` | Comprehensive Evaluation Suite | R3 | `SegmentationMetricTracker`, `evaluate` | 5 | 5 | ✓ | ✓ |
| **F10** | `F-CHECKPOINT-SAVE`| Checkpoint Delivery & Reload | R3 | `StandaloneInferencer`, `infer.py` CLI | 5 | 5 | ✓ | ✓ |
| **F11** | `F-INFER-PIPE` | Multi-Page PDF Inference Pipeline | R4 | `run_pipeline`, `PDFAnnotator`, `router` | 5 | 5 | ✓ | ✓ |
| **F12** | `F-STREAMLIT-UI`| Local Streamlit PDF Interface | R4 | `app.py`, Takeoff Analytics Export | 5 | 5 | ✓ | ✓ |
| **F13** | `F-HELDOUT-VAL` | Held-Out Drawing Validation | R4 | Sheet A-104 (Page 17), Spark Lake Grove | 5 | 5 | ✓ | ✓ |
| **F14** | `F-ERROR-ROBUST`| Robustness & Defensive Guards | R4 | Small-canvas guard, Corrupted PDF guard | 5 | 5 | ✓ | ✓ |
| **F15** | `F-REPORT-DOCS` | Capability Showcase Documentation | R1-R4 | `drywall_detection/reports/*.md` | 5 | 5 | ✓ | ✓ |
| **TOTAL**| | | | | **75** | **75** | **15** | **5** |

---

## 3. Test Suite Architecture & Directory Layout

The 170-test opaque-box suite is structured into dedicated test files under `drywall_detection/tests/e2e/`:

```
drywall_detection/tests/
├── conftest.py                             # Shared fixtures (temp dirs, mock hardware, reference paths)
├── stress_harness.py                       # Resource stress generators and memory monitors
├── unit/                                   # Unit tests per individual module (977 existing tests)
│   └── test_datasets.py
└── e2e/                                    # 4-Tier Opaque-Box End-to-End Test Suite (170 tests)
    ├── __init__.py
    ├── test_tier1_feature_coverage.py      # Tier 1: 75 Feature Coverage Tests (F1–F15 x 5)
    ├── test_tier2_boundaries.py            # Tier 2: 75 Boundary & Corner Case Tests (F1–F15 x 5)
    ├── test_tier3_pairwise.py              # Tier 3: 15 Cross-Feature Pairwise Interaction Tests
    └── test_tier4_realworld.py             # Tier 4: 5 Real-World Workload Scenarios
```

---

## 4. Detailed Specification of Test Cases (Tiers 1–4)

### 4.1 Tier 1: Feature Coverage (75 Tests — 5 per Feature)

#### F1: Dataset Licensing Audit (`test_tier1_feature_coverage.py::TestTier1Feature01DatasetAudit`)
1. `test_tier1_f01_audit_catalog_completeness`: Verifies `CANDIDATE_DATASETS` catalogs all 6 authoritative datasets (`msd`, `cubicasa5k`, `floorplancad`, `cvc_fp`, `r2v`, `sesyd`) with complete metadata, license names, and URLs.
2. `test_tier1_f01_licensing_compliance_categorization`: Verifies licensing classification rules (MSD permissive CC BY 4.0, CubiCasa5K non-commercial research, R2V non-commercial restricted).
3. `test_tier1_f01_disk_headroom_verification`: Verifies `DatasetAuditor.check_disk_safety()` enforces `DISK_FREE_MIN_GB` (5.0 GB) headroom before downloading.
4. `test_tier1_f01_download_threshold_guard`: Verifies `check_download_threshold()` flags downloads exceeding `DISK_LARGE_DOWNLOAD_THRESHOLD_GB` (10.0 GB).
5. `test_tier1_f01_audit_report_generation`: Verifies `DatasetAuditor.generate_audit_report()` produces structured markdown and JSON audit records.

#### F2: Unified Dataset Preparation (`test_tier1_feature_coverage.py::TestTier1Feature02DataPreparation`)
6. `test_tier1_f02_dataset_preparer_initialization`: Verifies `DatasetPreparer` instantiates with valid input/output directories and configuration parameters.
7. `test_tier1_f02_geometry_rasterizer_binary_mask`: Verifies `GeometryRasterizer` converts Shapely polygons into 2D uint8 binary numpy masks.
8. `test_tier1_f02_multiclass_mask_generation`: Verifies `GeometryRasterizer` renders 4-class Mode 'P' indexed PNG masks with values strictly in $\{0, 1, 2, 3\}$.
9. `test_tier1_f02_drawing_sanitizer_validation`: Verifies `DrawingSanitizer` cleans invalid, self-intersecting, or degenerate polygon geometries.
10. `test_tier1_f02_visual_qc_triplet_generation`: Verifies `VisualQCGenerator` generates synchronized original image, mask, and overlay triplets.

#### F3: Drawing-Level Split Integrity (`test_tier1_feature_coverage.py::TestTier1Feature03SplitIntegrity`)
11. `test_tier1_f03_project_splitter_partitioning`: Verifies `ProjectDataSplitter` partitions drawing samples according to 70/15/15 target ratios.
12. `test_tier1_f03_zero_leakage_invariant`: Verifies $\text{Projects}(train) \cap \text{Projects}(val) = \emptyset$ and $\text{Projects}(train) \cap \text{Projects}(test) = \emptyset$.
13. `test_tier1_f03_split_manifest_bundle_schema`: Verifies `SplitManifestBundle` serializes and reloads from JSON with valid sample counts and paths.
14. `test_tier1_f03_quarantine_manifest_isolation`: Verifies weak pseudo-label manifests and single-project calibration drawings are strictly quarantined from validation and test sets.
15. `test_tier1_f03_deterministic_split_seeding`: Verifies identical random seeds yield identical project assignments across repeated runs.

#### F4: Drawing Inventory & Schedule Mining (`test_tier1_feature_coverage.py::TestTier1Feature04ScheduleMining`)
16. `test_tier1_f04_vector_extractor_page_profile`: Verifies `VectorExtractor.analyze_page()` returns valid `VectorPageProfile` (path count, text blocks, rotation).
17. `test_tier1_f04_wall_candidate_extraction`: Verifies `VectorExtractor.extract_walls()` detects linear and filled wall geometry elements.
18. `test_tier1_f04_partition_tag_discovery`: Verifies `VectorExtractor.extract_tags()` identifies ~11.2x11.3 pt square partition tag boxes and text labels.
19. `test_tier1_f04_schedule_parser_parsing`: Verifies `PartitionScheduleParser.parse_schedule()` extracts all 24 assembly details from Sheets A-900 and A-901.
20. `test_tier1_f04_3tier_spatial_matching`: Verifies `SpatialMatcher.match()` assigns wall polygons via leader line, proximity buffer, or unassigned fallback.

#### F5: 4-Class Classification Guardrails (`test_tier1_feature_coverage.py::TestTier1Feature05ClassificationGuardrails`)
21. `test_tier1_f05_taxonomy_strict_4classes`: Verifies `ClassificationClass` enum defines exactly BACKGROUND (0), DRYWALL (1), NON_DRYWALL (2), UNCERTAIN (3).
22. `test_tier1_f05_approved_csv_loading`: Verifies `DrywallClassifier` successfully loads and parses `partition_schedule_mapping.approved.csv`.
23. `test_tier1_f05_detail_1a_cmu_veto_enforcement`: Verifies Detail 1A (`6" FIRE RATED CMU`) is unconditionally classified as `Non-Drywall` (Red `#D50000`).
24. `test_tier1_f05_unassigned_walls_uncertain`: Verifies unassigned walls default to `Uncertain` (Yellow `#FFD600`) with zero hallucinated drywall labels.
25. `test_tier1_f05_classified_polygon_geojson_export`: Verifies `DrywallClassifier.to_geojson()` emits valid GeoJSON FeatureCollection with required properties.

#### F6: Ground Truth & Coordinate Alignment (`test_tier1_feature_coverage.py::TestTier1Feature06CoordinateAlignment`)
26. `test_tier1_f06_forward_matrix_affine`: Verifies `get_forward_matrix(rotation=90)` transforms PDF coordinates to 150 DPI pixel grid.
27. `test_tier1_f06_inverse_matrix_affine`: Verifies `get_inverse_matrix(rotation=90)` accurately inverts pixel coordinates back to PDF points.
28. `test_tier1_f06_bijective_roundtrip_precision`: Verifies roundtrip transformation error $|p - M^{-1}(M(p))| < 10^{-4}$ pt for arbitrary coordinates.
29. `test_tier1_f06_bbox_transformation`: Verifies `pdf_bbox_to_pixel()` and `pixel_bbox_to_pdf()` preserve bounding box area and orientation.
30. `test_tier1_f06_usman_ground_truth_parsing`: Verifies `GroundTruthBuilder` parses Usman red annotations and associates tags on Sheet A-101.

#### F7: Model Benchmarking on CPU (`test_tier1_feature_coverage.py::TestTier1Feature07ModelBenchmarking`)
31. `test_tier1_f07_hardware_profiler_cpu`: Verifies `probe_cpu()` captures core count, architecture, and instruction set extensions.
32. `test_tier1_f07_hardware_profiler_ram`: Verifies `probe_ram()` detects total and available host memory.
33. `test_tier1_f07_auto_configure_training`: Verifies `auto_configure_training()` adapts batch size, num_workers, and resolution for CPU Tier 5.
34. `test_tier1_f07_segformer_b0_instantiation`: Verifies `SegFormerWallDetector` initializes with 3.72M parameters and outputs 4-class logits.
35. `test_tier1_f07_model_cpu_forward_pass`: Verifies a 512x512 tensor forward pass executes on CPU without OOM or tensor dimension errors.

#### F8: Model Training & Fine-Tuning (`test_tier1_feature_coverage.py::TestTier1Feature08ModelTraining`)
36. `test_tier1_f08_multiclass_soft_dice_loss`: Verifies `MultiClassSoftDiceLoss` computes non-negative scalar loss and handles zero targets cleanly.
37. `test_tier1_f08_multiclass_focal_loss`: Verifies `MultiClassFocalLoss` computes focal weighted loss with gamma focusing parameter.
38. `test_tier1_f08_compound_loss_backward`: Verifies `CompoundSegmentationLoss` produces gradients for all trainable parameters on backward pass.
39. `test_tier1_f08_class_weight_enet_formulation`: Verifies `compute_enet_class_weights()` down-weights background (0.1x) and up-weights drywall (1.0x).
40. `test_tier1_f08_trainer_epoch_step`: Verifies `SegmentationTrainer` executes a synthetic training step and logs loss history.

#### F9: Comprehensive Evaluation Suite (`test_tier1_feature_coverage.py::TestTier1Feature09EvaluationSuite`)
41. `test_tier1_f09_metric_tracker_iou`: Verifies `SegmentationMetricTracker` computes exact intersection over union for multi-class predictions.
42. `test_tier1_f09_foreground_wall_iou`: Verifies foreground wall IoU correctly aggregates classes 1, 2, and 3 while excluding class 0.
43. `test_tier1_f09_boundary_iou_computation`: Verifies boundary IoU computes boundary-aware contour overlap at dilation radius $d=2$.
44. `test_tier1_f09_confusion_matrix_schema`: Verifies `SegmentationMetrics.get_confusion_matrix()` produces a 4x4 matrix matching total pixel count.
45. `test_tier1_f09_evaluation_report_formatting`: Verifies `SegmentationEvaluationReport.to_markdown_table()` emits valid markdown metric table.

#### F10: Checkpoint Delivery & Reload (`test_tier1_feature_coverage.py::TestTier1Feature10CheckpointDelivery`)
46. `test_tier1_f10_champion_checkpoint_files_exist`: Verifies all required files exist in `drywall_detection/checkpoints/best_model/` (`best_model.pt`, `config.json`, `class_mapping.json`, `metrics.json`, `infer.py`, `README.md`).
47. `test_tier1_f10_config_json_schema`: Verifies `config.json` specifies architecture `segformer_b0`, 4 `num_classes`, and 512 input size.
48. `test_tier1_f10_standalone_inferencer_reload`: Verifies `StandaloneInferencer.from_directory()` loads checkpoint weights onto CPU successfully.
49. `test_tier1_f10_infer_cli_help`: Verifies `drywall_detection/checkpoints/best_model/infer.py --help` executes cleanly with exit code 0.
50. `test_tier1_f10_metrics_json_integrity`: Verifies `metrics.json` records global accuracy (61.67%) and SegFormer parameter count (3,715,172).

#### F11: Multi-Page PDF Inference Pipeline (`test_tier1_feature_coverage.py::TestTier1Feature11InferencePipeline`)
51. `test_tier1_f11_modality_router_evaluation`: Verifies `ModalityRouter.evaluate_page()` correctly classifies vector vs scanned drawings.
52. `test_tier1_f11_sliding_window_tiling`: Verifies tiler splits large canvas into 512x512 tiles with 20% overlap without clipping edges.
53. `test_tier1_f11_hann_window_apodization`: Verifies 2D Hann window blending eliminates sharp boundary discontinuities between overlapping tiles.
54. `test_tier1_f11_pdf_annotator_layer_injection`: Verifies `PDFAnnotator.annotate_page()` inserts RGBA overlay into PDF content stream preserving vectors.
55. `test_tier1_f11_pipeline_cli_dry_run`: Verifies `drywall_detection/pipeline/infer.py` executes on sample PDF page and outputs summary JSON.

#### F12: Local Streamlit PDF Interface (`test_tier1_feature_coverage.py::TestTier1Feature12StreamlitInterface`)
56. `test_tier1_f12_streamlit_app_import`: Verifies `drywall_detection/app/app.py` imports without syntax or missing dependency errors.
57. `test_tier1_f12_color_palette_mapping`: Verifies UI palettes map Drywall to Green (`#00C853`), Non-Drywall to Red (`#D50000`), Uncertain to Yellow (`#FFD600`).
58. `test_tier1_f12_takeoff_analytics_calculation`: Verifies takeoff summary computes wall area, linear footage estimates, and percentage distributions.
59. `test_tier1_f12_pdf_export_generator`: Verifies annotator creates valid downloadable PDF preserving original page dimensions.
60. `test_tier1_f12_disclaimer_notice_presence`: Verifies UI displays the mandatory 95% CDs progress set limitation notice.

#### F13: Held-Out Drawing Validation (`test_tier1_feature_coverage.py::TestTier1Feature13HeldOutValidation`)
61. `test_tier1_f13_sheet_a104_extraction`: Verifies Sheet A-104 (Page index 17) extracts vector walls and partition tags cleanly.
62. `test_tier1_f13_usman_markup_a104_alignment`: Verifies Sheet A-104 achieves alignment with the 69 human-annotated Usman drywall markups.
63. `test_tier1_f13_spark_lake_grove_ingestion`: Verifies external permit drawing (`annotated_spark_test.pdf`) loads and renders without exceptions.
64. `test_tier1_f13_zero_false_positive_drywall`: Verifies non-drywall structural elements in held-out sets are never misclassified as drywall.
65. `test_tier1_f13_heldout_takeoff_summary`: Verifies held-out evaluation produces complete takeoff summary table with verified class counts.

#### F14: Robustness & Error Handling (`test_tier1_feature_coverage.py::TestTier1Feature14RobustnessGuards`)
66. `test_tier1_f14_corrupted_pdf_handling`: Verifies pipeline catches corrupted PDF bytes and raises `ValueError` or returns error code instead of crashing.
67. `test_tier1_f14_missing_schedule_csv`: Verifies missing `partition_schedule_mapping.approved.csv` falls back to Uncertain or exits code 2.
68. `test_tier1_f14_small_canvas_protection`: Verifies canvas smaller than 512x512 is padded or resized gracefully without tensor broadcast failure.
69. `test_tier1_f14_nan_inf_logit_sanitization`: Verifies NaN or Inf logits are clamped or replaced with finite values during argmax.
70. `test_tier1_f14_memory_cleanup_after_inference`: Verifies garbage collection and PyMuPDF doc closing prevents memory leaks over multi-page runs.

#### F15: Capability Showcase Documentation (`test_tier1_feature_coverage.py::TestTier1Feature15DocumentationSuite`)
71. `test_tier1_f15_all_reports_present`: Verifies `drywall_detection/reports/` contains M1, M2, M3, M4, M5, and final showcase documentation.
72. `test_tier1_f15_progress_set_citation_invariant`: Verifies every report contains the verbatim 95% CDs progress set disclaimer.
73. `test_tier1_f15_metric_reporting_veracity`: Verifies reported mIoU, Dice, and parameter counts in reports match `metrics.json` exactly.
74. `test_tier1_f15_schedule_mapping_table_completeness`: Verifies reports document all 24 partition schedule details and class assignments.
75. `test_tier1_f15_commercial_licensing_disclaimer`: Verifies licensing documentation accurately reflects non-commercial status of research datasets.

---

### 4.2 Tier 2: Boundary & Corner Cases (75 Tests — 5 per Feature)

#### F1: Dataset Licensing Audit (`test_tier2_boundaries.py::TestTier2Boundary01DatasetAudit`)
76. `test_tier2_f01_exact_10gb_threshold_edge`: Tests dataset size boundary at 9.999 GB (no warning), 10.000 GB, and 10.001 GB (triggers mandatory large download warning).
77. `test_tier2_f01_disk_headroom_exact_zero_drop`: Tests disk headroom when available space is exactly at 5.000 GB vs 4.999 GB (fails safety check).
78. `test_tier2_f01_negative_free_space_handling`: Tests disk probe behavior when mock system reports negative or zero bytes free.
79. `test_tier2_f01_malformed_url_schemes`: Tests candidate auditor with malformed URL schemes (`ftp://`, `file:///`, empty strings, invalid ports).
80. `test_tier2_f01_http_timeout_and_500_handling`: Tests network probes against simulated HTTP 403, 404, 500, and socket timeouts.

#### F2: Unified Dataset Preparation (`test_tier2_boundaries.py::TestTier2Boundary02DataPreparation`)
81. `test_tier2_f02_zero_area_polygon_rasterization`: Tests rasterizer with degenerate 0-area polygons, colinear lines, and point geometries.
82. `test_tier2_f02_extreme_canvas_aspect_ratios`: Tests rasterization on 1x5000 px and 5000x1 px extreme aspect ratio canvases.
83. `test_tier2_f02_overlapping_opposing_class_polygons`: Tests conflict resolution when Drywall (1) and Non-Drywall (2) polygons directly overlap.
84. `test_tier2_f02_invalid_mask_dtype_rejection`: Tests `validate_mask_array` rejects float32, int32, bool, and int16 dtypes with ValueError.
85. `test_tier2_f02_out_of_range_mask_values`: Tests `validate_mask_array` rejects mask containing pixel values 4, 5, 100, 255.

#### F3: Drawing-Level Split Integrity (`test_tier2_boundaries.py::TestTier2Boundary03SplitIntegrity`)
86. `test_tier2_f03_single_project_dataset_split_rejection`: Tests splitter raises `InsufficientGroupsError` when dataset contains fewer projects than split groups.
87. `test_tier2_f03_extreme_split_ratios`: Tests splitter with boundary split ratios (e.g. 98/1/1 or 50/50/0) and invalid sums (e.g. 0.7 + 0.2 + 0.2 = 1.1).
88. `test_tier2_f03_empty_sample_manifest`: Tests splitter with empty list of samples raising appropriate exception without unhandled crash.
89. `test_tier2_f03_synthetic_leakage_detection`: Tests split verification auditor injects synthetic sample overlap and asserts `SplitLeakageError` is raised.
90. `test_tier2_f03_building_id_case_and_whitespace_leak`: Tests project isolation detects leakage across case variations (`"proj_01"` vs `"PROJ_01"`) and whitespace.

#### F4: Drawing Inventory & Schedule Mining (`test_tier2_boundaries.py::TestTier2Boundary04ScheduleMining`)
91. `test_tier2_f04_dense_tag_cluster_single_wall`: Tests spatial matcher with 10 tags pointing to the same wall polygon (asserts no multiple assignment crash).
92. `test_tier2_f04_degenerate_zero_length_leader_line`: Tests spatial matcher with 0-length leader lines or multi-segment zig-zag leaders.
93. `test_tier2_f04_orthogonal_crossing_leaders`: Tests spatial matcher disambiguation when two leader lines intersect each other orthogonally.
94. `test_tier2_f04_leader_pointing_outside_mediabox`: Tests spatial matcher handling leader line terminating completely outside page boundaries.
95. `test_tier2_f04_empty_page_zero_walls_zero_tags`: Tests vector extractor and spatial matcher on completely blank drawing sheet.

#### F5: 4-Class Classification Guardrails (`test_tier2_boundaries.py::TestTier2Boundary05ClassificationGuardrails`)
96. `test_tier2_f05_tampered_detail_1a_drywall_rejection`: Tests `DrywallClassifier` raises `IntegrityViolationError` if schedule CSV maps 1A to "Drywall".
97. `test_tier2_f05_tampered_detail_1a_synonyms_rejection`: Tests classifier rejects synonyms for 1A: "GWB", "Gypsum Board", "Sheetrock", "drywall".
98. `test_tier2_f05_missing_detail_1a_row`: Tests classifier raises `ScheduleValidationError` if Detail 1A is missing completely from the schedule CSV.
99. `test_tier2_f05_empty_schedule_csv_lock_preservation`: Tests empty or corrupt CSV does not bypass the review lock protocol (`REVIEW_REQUIRED.lock`).
100. `test_tier2_f05_polygon_immutable_detail_1a_mutation`: Tests `ClassifiedWallPolygon` prevents post-init mutation of tag 1A classification to Drywall.

#### F6: Ground Truth & Coordinate Alignment (`test_tier2_boundaries.py::TestTier2Boundary06CoordinateAlignment`)
101. `test_tier2_f06_extreme_coordinate_limits`: Tests coordinate transformer with coordinate extremes: $(0, 0)$, $(1728, 2592)$, negative coordinates, and sub-pixel floats.
102. `test_tier2_f06_nonstandard_dpi_values`: Tests coordinate transformer with non-standard DPI values (72, 100, 150, 300, 600 DPI) maintaining bijection.
103. `test_tier2_f06_zero_size_bounding_box`: Tests `pdf_bbox_to_pixel` on degenerate $(x, y, x, y)$ zero-area bounding boxes.
104. `test_tier2_f06_nonstandard_rotation_angles`: Tests coordinate transformer rejects or handles rotations outside 90° CW ($0^\circ, 180^\circ, 270^\circ$).
105. `test_tier2_f06_sub_picopoint_floating_point_drift`: Tests roundtrip transformation over $10^5$ operations asserting accumulated drift $< 10^{-11}$ pt.

#### F7: Model Benchmarking on CPU (`test_tier2_boundaries.py::TestTier2Boundary07ModelBenchmarking`)
106. `test_tier2_f07_zero_free_ram_tier5_fallback`: Tests hardware auto-config when mock RAM available is 0 MB falls back safely to Tier 5 CPU minimal mode.
107. `test_tier2_f07_extreme_vram_clamping`: Tests hardware auto-config with simulated 128 GB VRAM clamps batch size to safe architectural maximums.
108. `test_tier2_f07_nan_inf_hardware_telemetry`: Tests hardware probe handles NaN or negative CPU/RAM values without unhandled exceptions.
109. `test_tier2_f07_single_core_cpu_adaptation`: Tests training auto-config with single CPU core sets `num_workers=0` and batch size 1.
110. `test_tier2_f07_missing_torch_cuda_module`: Tests hardware probe executes gracefully in environment where `torch.cuda.is_available()` returns False.

#### F8: Model Training & Fine-Tuning (`test_tier2_boundaries.py::TestTier2Boundary08ModelTraining`)
111. `test_tier2_f08_all_background_batch_loss`: Tests `CompoundSegmentationLoss` handles a batch containing 100% background (no walls present) without division by zero.
112. `test_tier2_f08_all_drywall_batch_loss`: Tests loss function handles a batch containing 100% drywall pixels without numerical overflow.
113. `test_tier2_f08_extreme_class_weight_ratios`: Tests loss computation with extreme class weight ratios ($10^4 : 1$) remains numerically stable.
114. `test_tier2_f08_zero_smooth_dice_epsilon`: Tests dice loss numerical behavior when smoothing epsilon is set to 0.0 or machine epsilon.
115. `test_tier2_f08_gradient_clipping_overflow_prevention`: Tests trainer step handles explosive gradients via `clip_grad_norm_` without NaN weight updates.

#### F9: Comprehensive Evaluation Suite (`test_tier2_boundaries.py::TestTier2Boundary09EvaluationSuite`)
116. `test_tier2_f09_empty_ground_truth_metrics`: Tests metric tracker evaluates classes with 0 ground truth pixels (IoU, Dice, Recall return 0.0 without crash).
117. `test_tier2_f09_perfect_prediction_metrics`: Tests metric tracker with identical prediction and ground truth masks returns IoU=1.0, Dice=1.0, F1=1.0.
118. `test_tier2_f09_completely_disjoint_predictions`: Tests metric tracker with 100% false positive / disjoint predictions returns IoU=0.0, Dice=0.0.
119. `test_tier2_f09_single_pixel_wall_boundary_iou`: Tests boundary IoU calculation on single isolated pixel walls without index out of bounds.
120. `test_tier2_f09_confusion_matrix_all_zeros_handling`: Tests confusion matrix formatting when all predicted and ground truth pixels are class 0.

#### F10: Checkpoint Delivery & Reload (`test_tier2_boundaries.py::TestTier2Boundary10CheckpointDelivery`)
121. `test_tier2_f10_missing_checkpoint_weight_file`: Tests `StandaloneInferencer` raises `FileNotFoundError` when `best_model.pt` is missing from checkpoint directory.
122. `test_tier2_f10_corrupted_config_json`: Tests loader raises descriptive error when `config.json` has invalid JSON syntax or missing required keys.
123. `test_tier2_f10_checkpoint_state_dict_key_mismatch`: Tests checkpoint loader handles unexpected or missing model weights with strict error reporting.
124. `test_tier2_f10_infer_cli_missing_input_argument`: Tests standalone CLI exits with code 2 and informative usage message when called without arguments.
125. `test_tier2_f10_nonexistent_input_image_path`: Tests inference script raises `FileNotFoundError` when input image path does not exist.

#### F11: Multi-Page PDF Inference Pipeline (`test_tier2_boundaries.py::TestTier2Boundary11InferencePipeline`)
126. `test_tier2_f11_single_pixel_image_tiling`: Tests tiling engine handles 1x1 pixel image canvas without infinite loop or negative stride.
127. `test_tier2_f11_canvas_smaller_than_tile_size`: Tests tiling and Hann window stitching on 256x256 image (smaller than 512x512 tile size) with safe padding.
128. `test_tier2_f11_zero_overlap_tiling`: Tests sliding-window tiling with overlap fraction 0.0 (exact grid tiling) executes without coordinate gaps.
129. `test_tier2_f11_extreme_99percent_overlap`: Tests tiling engine with 0.90 overlap fraction handles dense tile stitching without weight explosion.
130. `test_tier2_f11_multipage_pdf_single_corrupt_page`: Tests pipeline encounters one corrupted page in multi-page PDF, logs error, and continues to remaining pages.

#### F12: Local Streamlit PDF Interface (`test_tier2_boundaries.py::TestTier2Boundary12StreamlitInterface`)
131. `test_tier2_f12_corrupted_pdf_upload_simulation`: Tests Streamlit file uploader logic with 0-byte uploaded file, returning user-friendly warning.
132. `test_tier2_f12_non_pdf_file_upload_rejection`: Tests interface rejects unsupported file formats (.exe, .zip, .docx) with validation error.
133. `test_tier2_f12_zero_wall_takeoff_analytics`: Tests takeoff summary handles sheets with 0 wall detections (div-by-zero protection, 0.0% metrics).
134. `test_tier2_f12_extreme_resolution_preview_render`: Tests image preview downsampling prevents browser memory exhaustion on 5400x3600 canvases.
135. `test_tier2_f12_export_to_read_only_directory`: Tests export routines gracefully handle filesystem write permission denial.

#### F13: Held-Out Drawing Validation (`test_tier2_boundaries.py::TestTier2Boundary13HeldOutValidation`)
136. `test_tier2_f13_spark_lake_grove_zero_vector_fallback`: Tests router and pipeline correctly route Spark Lake Grove scanned pages to ML segmentation track.
137. `test_tier2_f13_unseen_wall_schedule_symbols`: Tests classifier encountering partition tags not present in schedule assigns `Uncertain` (Class 3).
138. `test_tier2_f13_high_density_corridor_evaluation`: Tests held-out evaluation on high-density corridor partition zones on Sheet A-104.
139. `test_tier2_f13_external_drawing_aspect_ratios`: Tests held-out evaluation on non-standard architectural drawing sizes (e.g. Arch D, Arch E).
140. `test_tier2_f13_usman_markup_partial_overlap`: Tests alignment metrics when ground truth marks have partial spatial overlap with detected walls.

#### F14: Robustness & Error Handling (`test_tier2_boundaries.py::TestTier2Boundary14RobustnessGuards`)
141. `test_tier2_f14_truncated_pdf_header`: Tests PDF loader rejects truncated PDF header (`%PDF-` missing or interrupted bytes).
142. `test_tier2_f14_negative_dpi_rejection`: Tests pipeline raises `ValueError` when negative or zero DPI is requested.
143. `test_tier2_f14_overlay_alpha_clamping`: Tests PDFAnnotator clamps alpha outside [0.0, 1.0] (e.g. -0.5 or 1.5) without crash.
144. `test_tier2_f14_invalid_tile_size_rejection`: Tests pipeline rejects non-positive or non-multiple tile sizes (e.g. 0, -512, 13).
145. `test_tier2_f14_memory_ceiling_throttling`: Tests sliding-window worker limits simultaneous tile allocation when active RAM exceeds safe threshold.

#### F15: Capability Showcase Documentation (`test_tier2_boundaries.py::TestTier2Boundary15DocumentationSuite`)
146. `test_tier2_f15_empty_report_file_rejection`: Tests verification audit checks that no report in `reports/` is 0 bytes or whitespace-only.
147. `test_tier2_f15_broken_markdown_link_detection`: Tests report integrity checker validates that referenced file paths and images exist.
148. `test_tier2_f15_inconsistent_metric_detection`: Tests audit cross-checks reported metrics across multiple report files for discrepancies.
149. `test_tier2_f15_missing_disclaimer_failure`: Tests report validator fails if any published report omits the 95% CDs progress set disclosure.
150. `test_tier2_f15_tampered_model_parameters_detection`: Tests report validator detects discrepancy if report claims parameter count different from `metrics.json`.

---

### 4.3 Tier 3: Cross-Feature Interactions (15 Pairwise Tests)

#### File: `drywall_detection/tests/e2e/test_tier3_pairwise.py`

151. `test_tier3_f01_f02_licensing_to_data_ingestion`:
    - **Pair:** F1 (Audit) $\times$ F2 (Preparation)
    - **Verification:** DatasetAuditor determines eligibility; DatasetPreparer ingests eligible datasets (MSD) and rejects ineligible (R2V, SESYD).

152. `test_tier3_f02_f03_data_unification_to_split_integrity`:
    - **Pair:** F2 (Preparation) $\times$ F3 (Splitting)
    - **Verification:** Emitted samples grouped by building/project ID; ProjectDataSplitter splits samples with strictly $\text{Projects}(train) \cap \text{Projects}(val) = \emptyset$.

153. `test_tier3_f03_f08_split_integrity_to_model_training`:
    - **Pair:** F3 (Splitting) $\times$ F8 (Training)
    - **Verification:** DataLoader built from split manifests guarantees zero validation sample leakage into training batches during model optimization.

154. `test_tier3_f04_f05_schedule_mining_to_classification_guardrails`:
    - **Pair:** F4 (Mining) $\times$ F5 (Classification)
    - **Verification:** Schedule details parsed from Sheets A-900/A-901 drive 3-class assignment in DrywallClassifier; Detail 1A triggers CMU non-drywall rule.

155. `test_tier3_f04_f06_tag_discovery_to_coordinate_alignment`:
    - **Pair:** F4 (Mining) $\times$ F6 (Coordinates)
    - **Verification:** Discovered 11.2x11.3 pt tag boxes in PDF space are mapped via `pdf_to_pixel` to 150 DPI canvas; inverse transform recovers original point within $<10^{-4}$ pt.

156. `test_tier3_f05_f11_classification_to_multipage_inference`:
    - **Pair:** F5 (Classification) $\times$ F11 (Inference)
    - **Verification:** Multi-page inference pipeline output masks strictly conform to 4-class taxonomy; Detail 1A walls rendered Red (`#D50000`) and never Green (`#00C853`).

157. `test_tier3_f06_f11_coordinate_bijection_to_overlay_injection`:
    - **Pair:** F6 (Coordinates) $\times$ F11 (Inference)
    - **Verification:** Coordinate bijection allows stitched tile masks to inject into PDF content stream preserving original page CropBox ($90^\circ$ CW) and linework.

158. `test_tier3_f07_f08_hardware_profiling_to_training_adaptation`:
    - **Pair:** F7 (Benchmarking) $\times$ F8 (Training)
    - **Verification:** Detected CPU profile feeds into training auto-config, setting batch size 1, num_workers 0, and SegFormer-B0 architecture.

159. `test_tier3_f08_f09_model_training_to_evaluation_metrics`:
    - **Pair:** F8 (Training) $\times$ F9 (Evaluation)
    - **Verification:** Model checkpoint forward logits pass into `SegmentationMetricTracker`, correctly updating mIoU, Dice, and Confusion Matrix.

160. `test_tier3_f09_f10_evaluation_suite_to_checkpoint_metadata`:
    - **Pair:** F9 (Evaluation) $\times$ F10 (Checkpoint)
    - **Verification:** Evaluation report metrics serialize into `metrics.json` inside checkpoint bundle matching the evaluator schema.

161. `test_tier3_f10_f11_checkpoint_reload_to_pipeline_inference`:
    - **Pair:** F10 (Checkpoint) $\times$ F11 (Inference)
    - **Verification:** `StandaloneInferencer` reloads SegFormer-B0 from `checkpoints/best_model/` onto CPU; runs pipeline inference without weight mismatch.

162. `test_tier3_f11_f12_pipeline_to_streamlit_interface`:
    - **Pair:** F11 (Inference) $\times$ F12 (Streamlit)
    - **Verification:** Streamlit UI invokes pipeline, receives annotated previews and takeoff statistics, and provides valid annotated PDF download.

163. `test_tier3_f11_f13_pipeline_to_heldout_validation`:
    - **Pair:** F11 (Inference) $\times$ F13 (Held-Out)
    - **Verification:** Pipeline executes across both held-out Sheet A-104 (vector track) and Spark Lake Grove (ML fallback track) successfully.

164. `test_tier3_f12_f14_interface_to_robustness_handling`:
    - **Pair:** F12 (Streamlit) $\times$ F14 (Robustness)
    - **Verification:** Streamlit interface intercepts corrupted file upload, displays user-friendly error banner, and maintains responsive session state.

165. `test_tier3_f13_f15_heldout_validation_to_showcase_reporting`:
    - **Pair:** F13 (Held-Out) $\times$ F15 (Documentation)
    - **Verification:** Empirical held-out validation results transcribe accurately into `FINAL_SHOWCASE_REPORT.md` alongside progress set disclosures.

---

### 4.4 Tier 4: Real-World Workload Scenarios (5 Workflows)

#### File: `drywall_detection/tests/e2e/test_tier4_realworld.py`

166. `test_tier4_scenario1_mta_full_set_sheet_a101_ingestion`:
    - **Scenario:** Full 71-Page MTA Drawing Set Ingestion & Sheet A-101 Extraction
    - **Features Exercised:** F4 (Inventory & Mining), F6 (Coordinate Alignment), F11 (Inference Pipeline)
    - **Execution Flow:**
      1. Open master 71-page PDF (`file-1793194362940-560626729.pdf`).
      2. Verify page count (71), unrotated MediaBox ($1728 \times 2592$ pt), and clockwise rotation ($90^\circ$).
      3. Navigate to Sheet A-101 (Page index 14).
      4. Run `VectorExtractor`: extract 146 candidate walls and 44 partition tag instances.
      5. Run `SpatialMatcher`: assign 22 walls via leader line, 3 walls via proximity buffer, and 121 walls to unassigned fallback.
      6. Assert zero material hallucinations (unassigned walls strictly classified as Uncertain).

167. `test_tier4_scenario2_highres_tiling_hann_reassembly`:
    - **Scenario:** High-Res 150 DPI Sliding-Window Tiling & Hann Window Apodization Re-Assembly
    - **Features Exercised:** F2 (Dataset Preparation), F11 (Inference Pipeline)
    - **Execution Flow:**
      1. Render floor plan canvas at 150 DPI ($5400 \times 3600$ px).
      2. Partition canvas into $512 \times 512$ sliding windows with $20\%$ overlap (stride 410 px).
      3. Execute forward pass with SegFormer-B0 model weights.
      4. Re-assemble predictions using smooth 2D Hann window weighting.
      5. Verify zero boundary seams across continuous walls ($< 10^{-3}$ seam discontinuity).
      6. Assert assembled mask dimensions exactly match $5400 \times 3600$ px.

168. `test_tier4_scenario3_model_reload_and_cpu_inference`:
    - **Scenario:** Checkpoint Reload from `checkpoints/best_model/` & Offline CPU Inference
    - **Features Exercised:** F10 (Checkpoint Delivery), F11 (Inference Pipeline)
    - **Execution Flow:**
      1. Initialize `StandaloneInferencer` targeting `drywall_detection/checkpoints/best_model/`.
      2. Inspect and verify `config.json` (SegFormer-B0, 3,715,172 params, 4 classes).
      3. Load weights onto Windows CPU (`torch.device('cpu')`).
      4. Execute offline inference on sample floor plan image.
      5. Verify predicted class mask values are strictly in $\{0, 1, 2, 3\}$.
      6. Verify CPU forward latency is under $5.0$ seconds and active memory is under $300$ MB.

169. `test_tier4_scenario4_streamlit_preview_and_annotated_export`:
    - **Scenario:** Streamlit PDF Processing, Preview Rendering & Vector-Preserving Export
    - **Features Exercised:** F11 (Inference Pipeline), F12 (Streamlit Local Interface)
    - **Execution Flow:**
      1. Simulate file upload of architectural PDF.
      2. Process page and compute multi-class predictions.
      3. Generate RGBA visual overlay with Green Drywall (`#00C853`), Red Non-Drywall (`#D50000`), Yellow Uncertain (`#FFD600`).
      4. Compute takeoff analytics (wall area sq ft, class percentages).
      5. Export annotated PDF using `PDFAnnotator`.
      6. Assert output PDF preserves original MediaBox, rotation, and vector text searchability.

170. `test_tier4_scenario5_heldout_a104_and_spark_permit_takeoff`:
    - **Scenario:** Held-Out Sheet A-104 & External Permit Drawing Takeoff Challenge
    - **Features Exercised:** F5 (Classification Guardrails), F13 (Held-Out Validation), F15 (Documentation)
    - **Execution Flow:**
      1. Process held-out Sheet A-104 (Page index 17) against 69 Usman drywall annotations.
      2. Ingest external permit drawing Spark Lake Grove (`annotated_spark_test.pdf`).
      3. Enforce strict 4-class taxonomy: background (0), drywall (1), non-drywall (2), uncertain (3).
      4. Verify Detail 1A CMU safety veto: 100% compliance, zero CMU walls classified as drywall.
      5. Generate takeoff summary report and verify consistency with `FINAL_SHOWCASE_REPORT.md`.

---

## 5. Test Runner Commands & Execution Guide

### 5.1 Full Opaque-Box E2E Suite Execution (Tiers 1–4, 170 Tests)
```bash
pytest drywall_detection/tests/e2e/ -v
```

### 5.2 Individual Tier Execution
```bash
# Tier 1: Feature Coverage (75 tests)
pytest drywall_detection/tests/e2e/test_tier1_feature_coverage.py -v

# Tier 2: Boundary & Corner Cases (75 tests)
pytest drywall_detection/tests/e2e/test_tier2_boundaries.py -v

# Tier 3: Cross-Feature Interactions (15 tests)
pytest drywall_detection/tests/e2e/test_tier3_pairwise.py -v

# Tier 4: Real-World Workload Scenarios (5 tests)
pytest drywall_detection/tests/e2e/test_tier4_realworld.py -v
```

### 5.3 Complete Project Test Suite Execution (1,147 Tests)
```bash
pytest drywall_detection/tests/ -v
```

### 5.4 Test Execution Options & Performance Settings
- **Quiet Mode (Rapid Pass/Fail):** `pytest drywall_detection/tests/e2e/ -q`
- **Stop on First Failure (Fail-Fast):** `pytest drywall_detection/tests/e2e/ -x`
- **Filtered Feature Run (e.g., F5 Classification):** `pytest drywall_detection/tests/e2e/ -k "Feature05 or Boundary05"`
- **Hardware Optimization:** All tests are designed to execute synchronously on host Windows CPU without GPU/CUDA requirement.

---

## 6. Pass/Fail Semantics & Acceptance Thresholds

| Criteria | Acceptance Threshold | Failure Condition | Action on Failure |
|---|---|---|---|
| **Test Suite Pass Rate** | **100% (170/170 passed)** | Even a single failure (`1 failed`) | Milestone Gate FAILS immediately |
| **Unhandled Errors** | **0 errors** | Uncaught exceptions during teardown/setup | Milestone Gate FAILS immediately |
| **Detail 1A CMU Safety** | **100% Non-Drywall** | Any classification of 1A as Drywall | UNCONDITIONAL FORENSIC VETO |
| **Split Data Leakage** | **0 leaked projects** | $\text{Projects}(train) \cap \text{Projects}(val) \neq \emptyset$ | UNCONDITIONAL FORENSIC VETO |
| **Execution Time (E2E)** | $\le 180\text{ seconds}$ on CPU | Timeout or infinite loop ($> 300\text{s}$) | Performance regression failure |
| **Peak Host RAM Usage** | $\le 850\text{ MB}$ active RAM | Process OOM crash | Hardware constraint failure |
| **Vector linework drift** | $< 10^{-3}\text{ pt}$ deviation | Vector paths altered/rasterized | Geometry contract failure |

---

## 7. Zero-Tolerance Integrity Rules Compliance

The test suite enforces the five inviolable zero-tolerance integrity rules defined in `PROJECT.md`:

1. **No Hardcoded Facades:** All tests compute real forward passes, real affine matrix multiplications, real vector path extractions, and real metric aggregations.
2. **No Fabricated Numbers:** Evaluation metrics tested are checked against real numbers recorded in `metrics.json` and `training_log.json`.
3. **Mandatory Detail 1A CMU Veto:** Any attempt to classify 6" CMU masonry block as drywall raises `IntegrityViolationError` and fails the test.
4. **Mandatory Forensic Auditor Veto:** The test suite architecture produces standardized test output parsable by `teamwork_auditor`.
5. **Mandatory 95% CDs Disclosure:** Tests assert that the progress set citation notice is present in all generated reports and UI views.

---

## 8. Verification & Sign-Off Record

- **Test Plan Architect:** `m5_explorer_1_rep` (Explorer Archetype: Investigation, Synthesis, Reporting)
- **Reviewer:** Orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`)
- **Implementer Target:** `m5_worker_1`
- **Execution Target:** Milestone M5 Verification Phase
- **Timestamp:** 2026-11-09T17:50:00Z
- **Certification:** **TEST_READY**
