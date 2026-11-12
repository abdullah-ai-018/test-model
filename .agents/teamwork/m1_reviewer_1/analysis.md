# Dataset Licensing & Legal Compliance Review & Adversarial Analysis

- **Reviewer / Subagent**: `m1_reviewer_1`
- **Roles**: Reviewer, Critic (Dataset Licensing & Legal Compliance Reviewer)
- **Target Subagent**: `m1_worker_1`
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Date**: 2026-11-08T02:11:30Z
- **Verdict**: **APPROVE**

---

## 1. Quality Review Summary

### 1.1 Executive Verdict
**VERDICT: APPROVE**

The dataset licensing audit engine implemented in `drywall_detection/datasets/licensing_audit.py`, along with its deliverable artifacts (`DATASET_LICENSING_REPORT.md`, `dataset_licensing_audit.json`, `M1_audit_report.md`, and `tests/test_licensing_audit.py`), meets all legal, architectural, and integrity standards outlined in `ORIGINAL_REQUEST.md` and `PROJECT.md`.

### 1.2 Review Dimensions

#### 1. Correctness & Legal Accuracy
- **Candidate Dataset Coverage**: Exactly 7 candidate datasets are cataloged and audited:
  1. *Modified Swiss Dwellings (MSD)*: DOI `10.5281/zenodo.7788422`, License `CC-BY-4.0`, Commercial Permitted, Verdict `ELIGIBLE_PRIMARY`.
  2. *CubiCasa5K*: DOI `10.5281/zenodo.2613548`, License `CC-BY-NC-4.0`, Non-Commercial Only, Verdict `ELIGIBLE_BENCHMARK`.
  3. *FloorPlanCAD*: ICCV 2021, License `CC-BY-NC-4.0` (Annotations only, CAD drawings disclaimed), Verdict `CONDITIONALLY_ELIGIBLE`.
  4. *CVC-FP*: Figshare DOI `10.6084/m9.figshare.12082131.v1`, Zenodo `10.5281/zenodo.7921780`, License `CC-BY-4.0`, Commercial Permitted, Verdict `ELIGIBLE_SMOKE_TEST`.
  5. *R2V (Raster-to-Vector)*: Code MIT, images proprietary to LIFULL Co., Ltd., access gated via NII IDR legal agreement in Japan, Verdict `DISQUALIFIED_GATED`.
  6. *SESYD Floorplans*: Open Academic Research, fatal defect: zero wall annotations (ground truth contains only 16 furniture/sanitary symbols), Verdict `DISQUALIFIED_NO_ANNOTATIONS`.
  7. *ArchCAD-400k*: arXiv:2503.22346 (March 2025), CC-BY-NC-4.0, gated behind manual Hugging Face web application form with 3 business days institutional review, Verdict `DISQUALIFIED_GATED`.
- **System Rule Compliance**:
  - Zero license acceptance on user's behalf is strictly respected. Gated datasets (`r2v`, `archcad_400k`) are disqualified and excluded from automated download.
  - Zero wall annotations in SESYD are detected, preventing severe model corruption.
  - Distinction between generic structural walls and CSI drywall is strictly enforced: external datasets are mapped exclusively to `Class 3 (Uncertain / Generic Wall)` to eliminate ungrounded drywall hallucinations.
- **Storage Safeguards**:
  - Large archives (>10 GB unannounced threshold or exceeding free disk capacity on C:) are accounted for. CubiCasa5K's 5.09 GB archive (~18 GB uncompressed) is flagged with explicit instructions for selective extraction (200–500 sample slice) or secondary drive E: staging (30.4 GB free).

#### 2. Logical Completeness & Code Quality
- Clean, idiomatic Python with type annotations, `@dataclass`, and strict string/int `Enum` definitions (`AuditStatus`, `CommercialStatus`, `AccessModel`).
- Robust exception handling in `verify_connectivity(timeout_seconds=5)` to prevent air-gapped CI or proxy timeouts from throwing unhandled exceptions.
- CLI arguments support `--json`, `--markdown`, `--verify-urls`, and `--stdout`.
- Backwards compatibility facade in `drywall_detection/audit/dataset_auditor.py` and `drywall_detection/audit/__init__.py` ensures seamless interoperability.

#### 3. Integrity Verification (Anti-Cheat / Anti-Facade Check)
- **Hardcoded test outputs**: None detected. Production code contains genuine data structures and real logic.
- **Dummy / facade implementations**: None detected. Serialization, CLI generation, Markdown rendering, and network reachability functions execute live operations.
- **Shortcuts / task bypass**: None detected. The audit covers all 7 required datasets with complete legal citations, DOIs, and rationales.
- **Self-certifying claims**: Indepedently validated by running full test executions and inspecting generated files.

---

## 2. Adversarial Review & Challenge Report

### 2.1 Challenge Summary
- **Overall Risk Assessment**: LOW (all major risks mitigated by design)

### 2.2 Adversarial Challenges

#### Challenge 1: Unannounced Commercial Contamination via Pretraining Weights
- **Assumption Challenged**: Using academic datasets (CubiCasa5K or FloorPlanCAD) for pretraining is safe for commercial deployment.
- **Attack Scenario**: If downstream pipelines combine CubiCasa5K (CC BY-NC 4.0) into the primary pretraining dataset for a commercial deliverable, the resulting weights may be legally encumbered by non-commercial restrictions.
- **Blast Radius**: High legal risk for commercial production release.
- **Mitigation Implemented**: `licensing_audit.py` segregates commercial vs non-commercial datasets (`get_eligible(commercial_only=True)`), explicitly recommending `modified_swiss_dwellings` (CC BY 4.0) as `ELIGIBLE_PRIMARY` and restricting `cubicasa5k` to `ELIGIBLE_BENCHMARK`.

#### Challenge 2: Host Disk Exhaustion via Full CubiCasa5K Decompression
- **Assumption Challenged**: The host machine has sufficient capacity to download and unpack all candidate datasets.
- **Attack Scenario**: Host C: drive has ~16.3 GB free. Downloading (5.09 GB) and uncompressing CubiCasa5K (~18 GB) would exceed C: drive capacity, triggering out-of-disk crashes and corrupting OS caches.
- **Blast Radius**: High infrastructure disruption.
- **Mitigation Implemented**: Both `licensing_audit.py` and `DATASET_LICENSING_REPORT.md` document this constraint, designating CubiCasa5K for selective extraction of a 200–500 drawing evaluation slice or routing to drive E: (30.4 GB free).

#### Challenge 3: Network Timeout / Air-Gap Failure during URL Verification
- **Assumption Challenged**: `verify_connectivity` requires active Internet reachability to external repositories (Zenodo, Figshare, Hugging Face).
- **Attack Scenario**: Running tests in an air-gapped CI or behind an enterprise firewall with socket blocking could cause indefinite hangs or unhandled socket exceptions.
- **Blast Radius**: Build and test pipeline failure.
- **Mitigation Implemented**: `verify_connectivity()` implements explicit timeout parameter (`timeout_seconds=5`) and broad exception handling (`except Exception as e: reachable = False`), and unit test `test_connectivity_safe_offline` confirms safe degradation.

#### Challenge 4: False Positive Wall Attribution (SESYD Floorplans)
- **Assumption Challenged**: Datasets named "Floorplans" contain floor plan wall masks.
- **Attack Scenario**: An engineer ingests SESYD expecting floor plan linework. Since SESYD annotates only 16 furniture symbols, all structural walls would be treated as background (class 0), training the model to actively ignore real walls.
- **Blast Radius**: Severe ML model regression.
- **Mitigation Implemented**: Authoritative schema inspection confirmed zero wall annotations. Disqualified unconditionally as `DISQUALIFIED_NO_ANNOTATIONS`.

---

## 3. Verified Claims

| Claim | Upstream Source | Verification Method | Status |
|---|---|---|:---:|
| 7 candidate datasets audited | Worker Handoff §1.1 | `python -c "from drywall_detection.datasets.licensing_audit import DatasetLicensingAuditor; assert len(DatasetLicensingAuditor().list_all()) == 7"` | **PASS** |
| 4 eligible, 3 disqualified, 2 commercial | Worker Handoff §1.1 | Direct inspection of `dataset_licensing_audit.json` & runtime query | **PASS** |
| `test_licensing_audit.py` passes 12/12 tests | Worker Handoff §1.5 | `pytest drywall_detection/tests/test_licensing_audit.py -v` (exited 0 in 23.54s) | **PASS** |
| Full test suite passes 174/174 tests | Worker Handoff §1.5 | `pytest drywall_detection/tests/ -v` (exited 0 in 23.60s) | **PASS** |
| CLI exports match markdown deliverable | Code & deliverables | Runtime comparison of `generate_markdown_report()` with disk file | **PASS** |
| Zero license acceptance on user's behalf | Worker Handoff §2.1 | Verified `r2v` and `archcad_400k` are disqualified (`DISQUALIFIED_GATED`) | **PASS** |
| Generic walls mapped to Class 3 Uncertain | Worker Handoff §2.2 | Inspected `unified_format.py` default target class for MSD, CubiCasa, Raster | **PASS** |

---

## 4. Coverage Gaps & Unverified Items
- **Gaps**: None. All 7 candidate datasets from `ORIGINAL_REQUEST.md` have been fully investigated and cataloged.
- **Unverified Items**: None.

---

## 5. Final Verdict & Recommendation
- **Verdict**: **APPROVE**
- **Recommendation**: Advance to Milestone M2 (Dataset Preparation) using Modified Swiss Dwellings (MSD) as primary pretraining dataset, CVC-FP for CPU smoke tests, CubiCasa5K (selective slice) for held-out benchmark evaluation, and MTA 99th Street drawing set under strict quarantine from validation/test splits.
