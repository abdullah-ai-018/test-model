# Milestone M1 Independent Review & Adversarial Challenge Report

**Reviewer:** reviewer_m1_2 (M1 Auditor & Hardware Reviewer)  
**Date:** 2026-11-08  
**Scope:** Milestone M1 Implementation (`drywall_detection/utils/hardware.py`, `drywall_detection/audit/dataset_auditor.py`, `drywall_detection/tests/test_hardware.py`, `drywall_detection/tests/test_audit.py`, `drywall_detection/reports/M1_audit_report.md`)  
**Verdict:** **APPROVE**  

---

## 1. Review Summary

**Verdict**: **APPROVE**

An independent, evidence-based quality audit and adversarial challenge was conducted on the Milestone M1 deliverable package. The implementation demonstrates exceptional technical rigor, zero-tolerance integrity compliance, and sound software engineering principles.

Key findings:
1. **Integrity & Authenticity**: Zero hardcoded shortcuts, facade implementations, or fabricated outputs were detected. All hardware profiling functions invoke native OS and PyTorch primitives (`psutil`, `shutil.disk_usage`, `torch.cuda`). Dataset records reflect true upstream repository states, license terms, and ground-truth schemas.
2. **5-Tier Dynamic Hardware Auto-Configuration**: Properly classifies execution environments across 5 tiers (High GPU, Mid GPU / Colab T4, Low GPU, CPU Ample RAM, Constrained Host). On the current host (Windows 10, Intel 4P/8L cores, ~1.45 GB available RAM, CPU PyTorch), the profiler dynamically selects **Tier 5 (Constrained Host)** with safe defensive bounds (`batch_size=2`, `num_workers=0`, `gradient_accumulation_steps=8`, `effective_batch_size=16`, resolution `256x256`), preventing Out-Of-Memory terminations and process deadlocks.
3. **6-Candidate Dataset Auditor**: Evaluates all 6 datasets specified in `PROJECT.md` (MSD, CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD). Correctly disqualifies R2V (gated behind institutional NII IDR agreement, violating zero license acceptance) and SESYD (zero wall annotations; 16 furniture symbols only). Top recommendation (MSD, CC BY 4.0, 165.7 MB) and primary academic benchmark (CubiCasa5K, CC BY-NC-SA 4.0, 5.09 GB) are verified.
4. **Safety Guardrails**: Disk headroom verification and the mandatory 10 GB download warning ceiling are mathematically enforced in both runtime code and test suites.
5. **Mandatory Disclosures**: `drywall_detection/reports/M1_audit_report.md` prominently includes the mandatory notice disclosing the 95% CDs progress set status (`file-1793194362940-560626729.pdf`, MTA Contract C-48526) and single-project calibration bounds in Section 1.
6. **Test Suite & CLI Validation**: The targeted test suite (`test_hardware.py` and `test_audit.py`) executed 38 tests with 100% pass rate. Standalone CLIs for `hardware.py` and `dataset_auditor.py` executed cleanly with zero unhandled exceptions.

---

## 2. Findings & Recommendations

### [Minor] Finding 1: Eager Module Import in `drywall_detection/audit/__init__.py` Causes CLI `RuntimeWarning`

- **What**: Executing `python -m drywall_detection.audit.dataset_auditor` emits a standard Python `RuntimeWarning`:
  `RuntimeWarning: 'drywall_detection.audit.dataset_auditor' found in sys.modules after import of package 'drywall_detection.audit', but prior to execution of 'drywall_detection.audit.dataset_auditor'; this may result in unpredictable behaviour`
- **Where**: `drywall_detection/audit/__init__.py:5-20`
- **Why**: When Python executes a module inside a package with `-m`, it imports the parent package first. Because `audit/__init__.py` performs an eager import (`from drywall_detection.audit.dataset_auditor import ...`), `dataset_auditor` is placed into `sys.modules` before `runpy` finishes executing it as `__main__`. (Note that `drywall_detection/utils/__init__.py` already solved this identically using `__getattr__` lazy attribute loading).
- **Suggestion**: Replace eager imports in `drywall_detection/audit/__init__.py` with lazy loading via `__getattr__` or `importlib`, mirroring `drywall_detection/utils/__init__.py`. This eliminates the benign runtime warning during CLI invocation.

### [Minor] Finding 2: Parameter Discrepancy Between Global Safety Margin and Pre-Download Headroom

- **What**: `drywall_detection/utils/hardware.py:check_disk_safety` uses `DISK_FREE_MIN_GB = 5.0` (from `config.py`), while `drywall_detection/audit/dataset_auditor.py:check_disk_space` defaults to `min_headroom_gb = 2.0`.
- **Where**: `drywall_detection/utils/hardware.py:470-506` vs `drywall_detection/audit/dataset_auditor.py:532`
- **Why**: While logically justified (workspace runtime headroom during training requires more margin than post-download archive margin on disk), the coexistence of two headroom thresholds (5.0 GB vs 2.0 GB) could cause developer ambiguity.
- **Suggestion**: Define both constants explicitly in `drywall_detection/config.py` (e.g., `DISK_FREE_RUNTIME_MIN_GB = 5.0` and `DISK_FREE_DOWNLOAD_MIN_GB = 2.0`) to maintain a single source of truth for all storage parameters.

---

## 3. Verified Claims

| Claim | Method | Result | Notes |
|---|---|:---:|---|
| Host CPU detection | `python -m pytest drywall_detection/tests/test_hardware.py -k test_probe_cpu_live` | **PASS** | Detected Intel 4P/8L cores on AMD64 |
| Host RAM detection | `python -m pytest drywall_detection/tests/test_hardware.py -k test_probe_ram_live` | **PASS** | Detected 7.88 GB total, ~1.45 GB available |
| Host GPU/CUDA probe | `python -m pytest drywall_detection/tests/test_hardware.py -k test_probe_gpu` | **PASS** | Mocks verify CPU-only and CUDA enumerations |
| 5-Tier dynamic configuration | `python -m pytest drywall_detection/tests/test_hardware.py -k TestTrainingAutoConfiguration` | **PASS** | Tiers 1-5 correctly map profiles to parameters |
| Tier 5 Constrained Host resolution | `python -m drywall_detection.utils.hardware` | **PASS** | Resolves to Tier 5 (batch 2, accum 8, 256x256, 0 workers) |
| Disk safety headroom check | `python -m pytest drywall_detection/tests/test_hardware.py -k TestDiskSafetyGuards` | **PASS** | Rejects insufficient space and warns >10 GB |
| 6 candidate datasets catalog | `python -m pytest drywall_detection/tests/test_audit.py -k TestDatasetAuditorCatalog` | **PASS** | Exact 6 candidates cataloged with complete schemas |
| MSD eligibility & commercial terms | `python -m pytest drywall_detection/tests/test_audit.py -k test_msd_audit_verdict` | **PASS** | ELIGIBLE, CC BY 4.0, WKT wall polygons, <1 GB |
| CubiCasa5K eligibility & size | `python -m pytest drywall_detection/tests/test_audit.py -k test_cubicasa5k_audit_verdict` | **PASS** | ELIGIBLE, CC BY-NC-SA 4.0, SVG walls, 5.09 GB |
| FloorPlanCAD disclaimer condition | `python -m pytest drywall_detection/tests/test_audit.py -k test_floorplancad_audit_verdict` | **PASS** | CONDITIONALLY_ELIGIBLE due to 3rd-party CAD disclaimer |
| CVC-FP mirror condition | `python -m pytest drywall_detection/tests/test_audit.py -k test_cvc_fp_audit_verdict` | **PASS** | CONDITIONALLY_ELIGIBLE, Figshare mirror active |
| R2V institutional gating | `python -m pytest drywall_detection/tests/test_audit.py -k test_r2v_audit_verdict_ineligible_gated` | **PASS** | INELIGIBLE_FOR_AUTOMATED_DOWNLOAD, EULA required |
| SESYD zero wall annotation | `python -m pytest drywall_detection/tests/test_audit.py -k test_sesyd_audit_verdict_ineligible_no_walls` | **PASS** | INELIGIBLE_FOR_WALL_SEGMENTATION, 0 wall labels |
| Zero license acceptance guard | `python -m pytest drywall_detection/tests/test_audit.py -k test_zero_license_acceptance_guard` | **PASS** | Raises PermissionError on gated preparation |
| 10 GB warning boundary | `python -m pytest drywall_detection/tests/test_audit.py -k TestDiskSafetyAndThresholdGuards` | **PASS** | 10.0 GB passes without warning; 10.001 GB triggers |
| Report serialization & CLI | `python -m pytest drywall_detection/tests/test_audit.py -k TestReportSerializationAndCLI` | **PASS** | JSON deserialization and CLI formats pass cleanly |
| Report Section 1 Progress Notice | Inspection of `drywall_detection/reports/M1_audit_report.md` | **PASS** | Section 1 contains 95% CDs notice & single-project bounds |
| Combined hardware & audit tests | `python -m pytest drywall_detection/tests/test_hardware.py drywall_detection/tests/test_audit.py -v` | **PASS** | 38 passed in 16.24s |
| Hardware CLI execution | `python -m drywall_detection.utils.hardware` | **PASS** | Clean execution, Markdown table + JSON output |
| Dataset Auditor CLI execution | `python -m drywall_detection.audit.dataset_auditor --format markdown` | **PASS** | Clean execution, 6-candidate table output |
| Ineligible Dataset CLI exit code | `python -m drywall_detection.audit.dataset_auditor --dataset-id r2v` | **PASS** | Exits with status code 2 (review/gated) |

---

## 4. Coverage Gaps & Unexplored Areas

- **ArchCAD-400k (7th Candidate)**: ArchCAD-400k was discussed in the narrative licensing report (`DATASET_LICENSING_REPORT.md:24,163-180`) and verified to be disqualified (`DISQUALIFIED_GATED`) due to manual Hugging Face application review requirements. However, it was not registered in `CANDIDATE_DATASETS` in `dataset_auditor.py` (which targets the 6 datasets defined in `PROJECT.md`).  
  *Risk Level:* **Low**.  
  *Recommendation:* Accept risk. ArchCAD-400k is confirmed gated and cannot be downloaded autonomously. In Milestone M2, if programmatic inspection of all 7 datasets is desired, an entry can be added to `CANDIDATE_DATASETS`.

---

## 5. Adversarial Challenge Analysis

### Overall Risk Assessment: **LOW**

### Challenge 1: Memory Exhaustion on Constrained Host during Multiprocessing DataLoader
- **Assumption Challenged**: System can train PyTorch models without crashing despite having only ~1.45 GB available RAM.
- **Attack Scenario**: Setting `num_workers > 0` on Windows triggers `spawn` multiprocessing, duplicating memory per worker process and causing immediate OOM page fault termination.
- **Blast Radius**: Python process killed by Windows memory manager; corrupted checkpoint or aborted training run.
- **Mitigation Implemented**: Tier 5 configuration explicitly sets `num_workers = 0`, `pin_memory = False`, and `batch_size = 2` with `gradient_accumulation_steps = 8`. This guarantees single-process execution and minimal tensor footprint, safely avoiding worker memory multiplication.

### Challenge 2: Accidental Download of Gated or Non-Compliant Datasets
- **Assumption Challenged**: Automated scripts might attempt to curl or scrape datasets with restricted access terms or click-through agreements.
- **Attack Scenario**: Calling download on R2V or ArchCAD-400k would attempt to bypass auth or sign agreements without user consent.
- **Blast Radius**: Legal violation of academic data agreements; broken download pipe.
- **Mitigation Implemented**: `prepare_dataset()` in `dataset_auditor.py` explicitly throws `PermissionError` whenever `requires_login_or_eula` is True. The CLI marks R2V as `INELIGIBLE_FOR_AUTOMATED_DOWNLOAD` and returns exit code 2.

### Challenge 3: Disk Exhaustion During Archive Extraction
- **Assumption Challenged**: Archive download fits on disk, but uncompressed extraction exceeds available drive space.
- **Attack Scenario**: Downloading CubiCasa5K (5.09 GB archive) onto a drive with 10 GB free space succeeds, but extracting the 20 GB contents exhausts all remaining disk space, locking the OS.
- **Blast Radius**: Disk full error; potential corruption of operating system paging file.
- **Mitigation Implemented**: `check_disk_space()` provides `include_extracted: bool = True` option that adds `required_extracted_bytes` to the calculation, enforcing post-extraction headroom before allowing decompression. In addition, the auditor recommends selective extraction or secondary drive deployment for CubiCasa5K.

---

## 6. Final Assessment

The Milestone M1 implementation satisfies all criteria set forth in `ORIGINAL_REQUEST.md` and `PROJECT.md`. The code is modular, robust, mathematically grounded, and strictly adheres to project integrity guardrails.

**Verdict: APPROVE** — Milestone M1 is accepted, and the project is cleared to advance to Milestone M2 (Dataset Preparation).
