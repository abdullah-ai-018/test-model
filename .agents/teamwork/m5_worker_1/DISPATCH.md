# Milestone M5 Implementation Worker Dispatch: E2E Test Suite & Showcase Delivery

## 1. Workspace & State Folder
- **Working Directory**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
- **Your State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_worker_1`
- **Parent Conversation ID**: `3c1a82ae-9b50-494e-b173-0369a8d4a486`

---

## 2. Mandatory Integrity Warning
> **DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.**

---

## 3. Mandatory Reading List
Before writing any code or tests, you MUST read the following authoritative state files:
1. `ORIGINAL_REQUEST.md`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `PROJECT.md`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`
3. `TEST_INFRA.md`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\TEST_INFRA.md`
4. `ORCHESTRATOR ANALYSIS`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\orchestrator\analysis.md`
5. `EXPLORER 1 REP HANDOFF`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_1_rep\handoff.md`
6. `PROPOSED TEST READY`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_1_rep\proposed_TEST_READY.md`
7. `EXPLORER 3 HANDOFF`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_3\handoff.md`
8. `PROPOSED FINAL SHOWCASE REPORT`: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_3\proposed_FINAL_SHOWCASE_REPORT.md`

---

## 4. Exclusive Write Ownership
You own and may modify ONLY the following files:
1. `drywall_detection/pipeline/infer.py` (Line 435: escape `%` to `%%` in argparse help string).
2. `drywall_detection/reports/FINAL_SHOWCASE_REPORT.md` (Deploy authoritative final showcase report based on `m5_explorer_3/proposed_FINAL_SHOWCASE_REPORT.md`).
3. `drywall_detection/tests/e2e/__init__.py` (Package marker).
4. `drywall_detection/tests/e2e/test_tier1_feature_coverage.py` (75 tests across F1–F15, 5 per feature).
5. `drywall_detection/tests/e2e/test_tier2_boundaries.py` (75 boundary tests across F1–F15, 5 per feature).
6. `drywall_detection/tests/e2e/test_tier3_pairwise.py` (15 pairwise interaction tests).
7. `drywall_detection/tests/e2e/test_tier4_realworld.py` (5 end-to-end real-world workload scenarios).
8. `TEST_READY.md` (Deploy authoritative test readiness certificate at project root based on `m5_explorer_1_rep/proposed_TEST_READY.md`).

Do NOT modify any files outside this exclusive list.

---

## 5. Implementation Tasks & Acceptance Criteria

### Task 1: Fix Argparse Formatting Defect in `drywall_detection/pipeline/infer.py`
- Line 435: Change `help="Sliding-window overlap fraction for Hann apodization stitching (e.g. 0.20 for 20% overlap)"` to `... (e.g. 0.20 for 20%% overlap)`.
- Verify: `python -m drywall_detection.pipeline.infer --help` executes cleanly with exit code 0.

### Task 2: Implement the 4-Tier Opaque-Box E2E Test Suite under `drywall_detection/tests/e2e/`
Implement test files matching the exact specification in `proposed_TEST_READY.md`:
- `test_tier1_feature_coverage.py`:
  - 15 test classes (`TestTier1Feature01` through `TestTier1Feature15`), each with exactly 5 tests (Total 75 tests).
  - Exercises public entry points across all 15 features (F1 to F15).
- `test_tier2_boundaries.py`:
  - 15 test classes (`TestTier2Boundary01` through `TestTier2Boundary15`), each with exactly 5 tests (Total 75 tests).
  - Exercises boundary conditions, edge cases, zero-dimension inputs, OOM safety guards, and corrupted inputs.
- `test_tier3_pairwise.py`:
  - 15 tests (`test_tier3_f01_f02` through `test_tier3_f13_f15`) testing cross-feature interactions.
- `test_tier4_realworld.py`:
  - 5 tests (`test_tier4_scenario1` through `test_tier4_scenario5`) exercising end-to-end multi-feature workflows on Sheet A-101, Sheet A-104, Spark Lake Grove, model reload, and Streamlit export.
- Acceptance criteria:
  - All 170 E2E tests MUST pass with exit code 0.
  - Execution runtime must complete within $\le 180$ seconds on host Windows CPU (use representative pages/fixtures where appropriate).

### Task 3: Deploy Final Showcase Report
- Copy/deploy `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_3\proposed_FINAL_SHOWCASE_REPORT.md` to `drywall_detection/reports/FINAL_SHOWCASE_REPORT.md`.
- Verify it is complete, properly formatted, contains all benchmark tables, 4-class taxonomy, 2-layer Detail 1A CMU safety veto, mandatory 95% CDs notice, and 3-phase strategic roadmap.

### Task 4: Execute Full Test Suite & Publish `TEST_READY.md`
- Run: `pytest drywall_detection/tests/e2e/ -v`
- Run: `pytest drywall_detection/tests/ -v`
- Verify that 100% of tests pass (170 E2E tests + 977 existing regression tests = 1,147 total tests).
- Copy `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_explorer_1_rep\proposed_TEST_READY.md` to `TEST_READY.md` at workspace root.

### Task 5: Deliver Hard Handoff
- Deliver self-contained Hard Handoff report in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_worker_1\handoff.md`.
- Send completion message to parent orchestrator (`3c1a82ae-9b50-494e-b173-0369a8d4a486`) via `send_message`.


## 2026-11-09T17:56:30Z
Resume work at c:\Users\TEC ZONE\OneDrive\Desktop\test-model.
Your state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_worker_1
Your task instructions and mandatory reading list are located in: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m5_worker_1\DISPATCH.md
