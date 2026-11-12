# E2E Test Infra: Drywall Detection Pipeline

## Test Philosophy
- Opaque-box, requirement-driven testing derived from `ORIGINAL_REQUEST.md` and user-facing specifications.
- Completely decoupled from internal module implementations; exercises public interfaces and CLI/script/UI entry points.
- Progressive testability: Tier 1 tests verify basic capabilities without requiring complete end-to-end integration.

## Feature Inventory
| # | Feature | Requirement | Tier 1 (Count) | Tier 2 (Count) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|-------------|:--------------:|:--------------:|:-----------------:|:-----------------:|
| F1 | Dataset Licensing Audit | R1 | 5 | 5 | ✓ | ✓ |
| F2 | Unified Dataset Preparation | R1 | 5 | 5 | ✓ | ✓ |
| F3 | Drawing-Level Split Integrity | R1 | 5 | 5 | ✓ | ✓ |
| F4 | Drawing Inventory & Schedule Mining | R2 | 5 | 5 | ✓ | ✓ |
| F5 | 4-Class Classification Guardrails | R2 | 5 | 5 | ✓ | ✓ |
| F6 | Ground Truth & Coordinate Alignment | R2 | 5 | 5 | ✓ | ✓ |
| F7 | Model Benchmarking on CPU | R3 | 5 | 5 | ✓ | ✓ |
| F8 | Model Training & Fine-Tuning | R3 | 5 | 5 | ✓ | ✓ |
| F9 | Comprehensive Evaluation Suite | R3 | 5 | 5 | ✓ | ✓ |
| F10 | Checkpoint Delivery & Reload | R3 | 5 | 5 | ✓ | ✓ |
| F11 | Multi-Page PDF Inference Pipeline | R4 | 5 | 5 | ✓ | ✓ |
| F12 | Local Streamlit PDF Interface | R4 | 5 | 5 | ✓ | ✓ |
| F13 | Held-Out Drawing Validation | R4 | 5 | 5 | ✓ | ✓ |
| F14 | Robustness & Error Handling | R4 | 5 | 5 | ✓ | ✓ |
| F15 | Capability Showcase Documentation | R1-R4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `pytest`
- Execution command: `pytest drywall_detection/tests/ -v`
- Directory layout:
  * `drywall_detection/tests/unit/`: Unit tests per module
  * `drywall_detection/tests/e2e/tier1_features/`: Tier 1 Feature coverage tests
  * `drywall_detection/tests/e2e/tier2_boundaries/`: Tier 2 Boundary & edge case tests
  * `drywall_detection/tests/e2e/tier3_pairwise/`: Tier 3 Cross-feature integration tests
  * `drywall_detection/tests/e2e/tier4_realworld/`: Tier 4 End-to-end full workflow tests
  * `drywall_detection/tests/e2e/tier5_adversarial/`: Tier 5 Adversarial stress and perturbation tests

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Full 71-page MTA drawing set ingestion & Sheet A-101 extraction | F4, F6, F11 | Accurate coordinate alignment and sheet isolation |
| 2 | High-res 150 DPI sliding-window tiling and re-assembly | F2, F11 | Zero boundary seams, accurate Gaussian blending |
| 3 | Model reload from `checkpoints/best_model/` and CPU inference | F10, F11 | Output tensor strictly in {0, 1, 2, 3} without crashes |
| 4 | Streamlit PDF upload, preview rendering, and annotated PDF download | F11, F12 | Valid annotated PDF preserving original dimensions |
| 5 | Held-out Sheet A-104 & external permit set evaluation | F5, F13, F15 | Ground truth evaluation with strict 4-class guardrails |

## Coverage Thresholds
- Tier 1: ≥5 per feature (75 tests across 15 features)
- Tier 2: ≥5 per feature (75 tests across 15 features)
- Tier 3: ≥15 cross-feature interaction tests
- Tier 4: ≥5 real-world end-to-end workflow scenarios
- Total Target: ≥170 test cases
