# Milestone M1 Test Suite & Report Architecture Plan
**Document ID:** ARCH-EXP3-M1-001  
**Author:** explorer_m1_3 (M1 Test Suite & Report Architect)  
**Date:** 2026-11-08  
**Project:** Isolated Drywall Detection Module (`drywall_detection/`)  
**Integrity Mode:** Development  
**Reference Document:** MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728 x 2592 pt unrotated / 2592 x 1728 pt visual, Rotation 90° CW, "PROGRESS SET 95% CDs 10/02/2026")  
**Notice:** This reference PDF represents a 95% CDs progress set, not an approved final construction document. Pages represent a single project and calibration sample that cannot prove cross-domain generalization.

---

## Executive Summary

This architecture document delivers the complete, concrete engineering design for:
1. **The Milestone M1 Unit Test Suites** to be implemented from scratch inside `drywall_detection/tests/`:
   - `test_coords.py`: Unit tests verifying forward and backward coordinate bijection, 90° rotation handling, multi-quadrant rotation (0°, 90°, 180°, 270°), Shapely polygon transformations, area scaling invariance, and boundary conditions.
   - `test_hardware.py`: Unit tests verifying hardware detection probes (CPU, RAM, disk, CUDA/GPU, software environment) and hardware-aware training auto-configuration logic (Colab vs local CPU auto-tuning).
   - `test_audit.py`: Unit tests verifying dataset auditor capabilities across all 6 candidate datasets (CubiCasa5K, FloorPlanCAD, CVC-FP, R2V, SESYD, MSD), including mock HTTP probing, disk space headroom validation, the mandatory 10 GB user notification threshold, and license/annotation validation.
2. **The Milestone M1 Audit Report Structure** to be authored at `drywall_detection/reports/M1_audit_report.md`:
   - Comprehensive multi-section report covering workspace cleanliness and isolation verification, authoritative reference PDF properties, the mandatory single-project 95% CDs limitation notice, local hardware constraints (~0.9 GB free RAM, CPU-only PyTorch), and the full audit of the 6 candidate datasets.
3. **Step-by-Step Implementation Instructions** for the downstream Worker agent.

---

## 1. Unit Test Suite Architecture & Conventions

### 1.1 Testing Philosophy & Framework
- **Test Runner:** `pytest` (verified installed: version 9.1.1).
- **Execution Target:** `pytest drywall_detection/tests/ -v`.
- **Zero-Tolerance Quality Invariant:** No mocks of test assertions, no hardcoded dummy pass returns, no empty test stubs. Tests must verify true logic, boundary invariants, mathematical bijection, and realistic failure states.
- **Isolation:** Tests must not depend on external live internet connectivity or download large gigabyte archives during execution. External network probes and disk checks must use deterministic mocking fixtures (`unittest.mock.patch`), while local geometric and mathematical transforms execute against live real calculations.
- **Directory Layout:**
  ```
  drywall_detection/tests/
  ├── __init__.py
  ├── test_coords.py      # Mathematical coordinate bijection & Shapely geometry tests
  ├── test_hardware.py    # Hardware detection & auto-configuration tests
  └── test_audit.py       # Dataset auditor, licensing, & disk safety tests
  ```

---

## 2. Specification for `drywall_detection/tests/test_coords.py`

### 2.1 Target Module Contracts
The tests verify `drywall_detection.utils.coords` which interfaces with `drywall_detection.config`:
- `pdf_to_pixel(x: float, y: float, dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> Tuple[float, float]`
- `pixel_to_pdf(px: float, py: float, dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> Tuple[float, float]`
- `transform_bbox_to_pixel(bbox: Tuple[float, float, float, float], dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> Tuple[float, float, float, float]`
- `transform_bbox_to_pdf(pixel_bbox: Tuple[float, float, float, float], dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> Tuple[float, float, float, float]`
- `transform_polygon_to_pixel(polygon: shapely.geometry.Polygon, dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> shapely.geometry.Polygon`
- `transform_polygon_to_pdf(pixel_polygon: shapely.geometry.Polygon, dpi: int = 150, page_width: float = 1728.0, page_height: float = 2592.0, rotation: int = 90) -> shapely.geometry.Polygon`

### 2.2 Test Classes and Test Cases

#### Class `TestPointCoordinateTransforms`
1. **`test_pdf_to_pixel_forward_90deg_72dpi`**:
   - Inputs: Point $(x=500.0, y=1200.0)$, $DPI=72$, $W=1728.0, H=2592.0, \text{rotation}=90$.
   - Assertions:
     - $S = 72 / 72 = 1.0$.
     - Expected: $px = 1.0 \cdot (2592.0 - 1200.0) = 1392.0$, $py = 1.0 \cdot 500.0 = 500.0$.
     - `assert px == 1392.0 and py == 500.0`
2. **`test_pdf_to_pixel_forward_90deg_150dpi`**:
   - Inputs: Point $(x=500.0, y=1200.0)$, $DPI=150$, $\text{rotation}=90$.
   - Assertions:
     - $S = 150 / 72.0 = 2.0833333333333335$.
     - Expected: $px = 1392.0 \cdot \frac{150}{72} = 2900.0$, $py = 500.0 \cdot \frac{150}{72} = 1041.6666666666667$.
     - `assert math.isclose(px, 2900.0, rel_tol=1e-5)`
     - `assert math.isclose(py, 1041.666667, rel_tol=1e-5)`
3. **`test_pixel_to_pdf_inverse_90deg`**:
   - Inputs: Point $(px=2900.0, py=1041.666667)$, $DPI=150$, $\text{rotation}=90$.
   - Assertions:
     - Inverse: $x = py / S = 1041.666667 / (150/72) = 500.0$.
     - Inverse: $y = 2592.0 - px / S = 2592.0 - 2900.0 / (150/72) = 1200.0$.
     - `assert math.isclose(x, 500.0, abs_tol=1e-4)`
     - `assert math.isclose(y, 1200.0, abs_tol=1e-4)`
4. **`test_roundtrip_bijection_identity_all_corners`**:
   - Inputs: 4 corners of unrotated page: $(0.0, 0.0)$, $(1728.0, 0.0)$, $(0.0, 2592.0)$, $(1728.0, 2592.0)$, plus center $(864.0, 1296.0)$.
   - Procedure: Forward `pdf_to_pixel` then inverse `pixel_to_pdf`.
   - Assertions: For every point, $|x_{roundtrip} - x| < 10^{-4}$ and $|y_{roundtrip} - y| < 10^{-4}$.
5. **`test_roundtrip_bijection_random_samples`**:
   - Inputs: 100 random uniform points $x \in [0, 1728]$, $y \in [0, 2592]$ using fixed seed `random.seed(42)`.
   - Tested DPI values: `[72, 100, 150, 200, 300]`.
   - Assertions: Error for all samples strictly $< 10^{-4}$ pt.
6. **`test_multi_quadrant_rotations`**:
   - Test rotations $\theta \in \{0, 90, 180, 270\}$:
     - $\theta = 0$: $px = x \cdot S, py = y \cdot S$; inverse: $x = px / S, y = py / S$.
     - $\theta = 90$: $px = (H - y) \cdot S, py = x \cdot S$; inverse: $x = py / S, y = H - px / S$.
     - $\theta = 180$: $px = (W - x) \cdot S, py = (H - y) \cdot S$; inverse: $x = W - px / S, y = H - py / S$.
     - $\theta = 270$: $px = y \cdot S, py = (W - x) \cdot S$; inverse: $x = W - py / S, y = px / S$.
   - Assertions: All 4 rotations pass exact roundtrip bijection identity within $10^{-4}$ pt.
7. **`test_invalid_rotation_raises_value_error`**:
   - Inputs: `rotation=45`, `rotation=-90`, `rotation=360`, `rotation=15`.
   - Assertions: `pytest.raises(ValueError, match="[Uu]nsupported rotation")`.
8. **`test_invalid_dpi_raises_value_error`**:
   - Inputs: `dpi=0`, `dpi=-150`.
   - Assertions: `pytest.raises(ValueError, match="[Dd][Pp][Ii]")`.

#### Class `TestBoundingBoxTransforms`
1. **`test_bbox_forward_normalization_90deg`**:
   - Inputs: Axis-aligned PDF bounding box $B = (100.0, 200.0, 300.0, 500.0)$ in $[x_0, y_0, x_1, y_1]$.
   - Assertions:
     - Resulting pixel bounding box $(px_0, py_0, px_1, py_1)$ has $px_0 < px_1$ and $py_0 < py_1$ (normalized coordinate ordering guaranteed).
2. **`test_bbox_full_page_coverage`**:
   - Inputs: Entire page MediaBox $(0.0, 0.0, 1728.0, 2592.0)$ at 150 DPI under 90° rotation.
   - Assertions:
     - Visual landscape dimensions are $2592.0 \cdot \frac{150}{72} = 5400.0$ px wide, $1728.0 \cdot \frac{150}{72} = 3600.0$ px high.
     - Pixel bounding box equals exactly $(0.0, 0.0, 5400.0, 3600.0)$.
3. **`test_bbox_roundtrip_bijection`**:
   - Inputs: Multiple arbitrary bounding boxes, e.g. partition tag symbol box of size $11.2 \times 11.3$ pt at $(770.0, 1080.0, 781.2, 1091.3)$.
   - Assertions: Roundtrip $B \to B_{pixel} \to B_{roundtrip}$ matches original $B$ within $10^{-4}$ pt across all 4 coordinates.

#### Class `TestShapelyPolygonTransforms`
1. **`test_shapely_polygon_transform_validity`**:
   - Inputs: Shapely `Polygon([(100, 200), (300, 200), (300, 400), (100, 400)])`.
   - Assertions:
     - Transformed pixel polygon satisfies `poly_pixel.is_valid`.
     - Roundtrip polygon satisfies `poly_roundtrip.is_valid`.
     - `poly.equals_exact(poly_roundtrip, tolerance=1e-4)`.
2. **`test_shapely_polygon_area_scaling_invariant`**:
   - Inputs: Arbitrary polygon, $DPI=150$, scale $S = 150 / 72.0$.
   - Assertions:
     - Area ratio $\frac{\text{Area}(poly_{pixel})}{\text{Area}(poly_{pdf})}$ equals $S^2 = (150/72)^2 \approx 4.340277$ within $10^{-4}$.
3. **`test_shapely_polygon_with_interior_holes`**:
   - Inputs: Exterior rectangle $[(50, 50), (500, 50), (500, 500), (50, 500)]$ with interior hole $[(150, 150), (350, 150), (350, 350), (150, 350)]$.
   - Assertions:
     - Transformed polygon has `len(poly_pixel.interiors) == 1`.
     - Both exterior and interior rings maintain topological validity.
     - Roundtrip equals original geometry within $10^{-4}$.
4. **`test_shapely_linestring_transform`**:
   - Inputs: Leader line `LineString([(772.44, 1094.52), (772.44, 1082.76)])`.
   - Assertions:
     - Forward transformed pixel line length equals PDF line length $\times S$.
     - Inverse transformed line matches original vertices within $10^{-4}$ pt.
5. **`test_shapely_multipolygon_support`**:
   - Inputs: `MultiPolygon` representing disjoint wall segments.
   - Assertions:
     - All constituent polygons transformed preserving disjointness and validity.

---

## 3. Specification for `drywall_detection/tests/test_hardware.py`

### 3.1 Target Module Contracts
The tests verify `drywall_detection.utils.hardware`:
- `probe_cpu() -> Dict[str, Any]`
- `probe_ram() -> Dict[str, Any]`
- `probe_gpu() -> Dict[str, Any]`
- `probe_disk(path: str = ".") -> Dict[str, Any]`
- `probe_software_environment() -> Dict[str, Any]`
- `probe_all_hardware(disk_path: str = ".") -> Dict[str, Any]`
- `get_training_auto_config(hardware_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

### 3.2 Test Classes and Test Cases

#### Class `TestHardwareProbingUnits`
1. **`test_probe_cpu_live`**:
   - Call live `probe_cpu()`.
   - Assertions:
     - Returns dictionary containing keys `physical_cores`, `logical_cores`, `processor`, `architecture`.
     - `physical_cores >= 1` and `logical_cores >= physical_cores`.
     - `isinstance(architecture, str)` and len > 0.
2. **`test_probe_ram_live`**:
   - Call live `probe_ram()`.
   - Assertions:
     - Keys: `total_gb`, `available_gb`, `used_gb`, `percent_used`.
     - `total_gb > 0`, `available_gb > 0`, `used_gb > 0`.
     - $0.0 \le \text{percent\_used} \le 100.0$.
     - `total_gb` is within $\pm 0.1$ GB of `available_gb + used_gb` (or matches psutil total).
3. **`test_probe_disk_live`**:
   - Call live `probe_disk(".")`.
   - Assertions:
     - Keys: `drive`, `total_gb`, `used_gb`, `free_gb`, `percent_free`.
     - `total_gb > 0` and `free_gb > 0`.
4. **`test_probe_gpu_cpu_only_mock`**:
   - Mock: `@patch("torch.cuda.is_available", return_value=False)`
   - Call `probe_gpu()`.
   - Assertions:
     - `result["cuda_available"] is False`
     - `result["device_count"] == 0`
     - `result["vram_total_gb"] == 0.0`
     - `result["devices"] == []`
5. **`test_probe_gpu_cuda_available_mock`**:
   - Mock: `@patch("torch.cuda.is_available", return_value=True)`, `@patch("torch.cuda.device_count", return_value=1)`, `@patch("torch.cuda.get_device_properties")`. Mock device properties object: `name="Tesla T4"`, `total_memory=16106127360` (15.0 GB).
   - Call `probe_gpu()`.
   - Assertions:
     - `result["cuda_available"] is True`
     - `result["device_count"] == 1`
     - `math.isclose(result["vram_total_gb"], 15.0, rel_tol=1e-2)`
     - `result["devices"][0]["name"] == "Tesla T4"`
6. **`test_probe_software_environment_live`**:
   - Call `probe_software_environment()`.
   - Assertions:
     - `python_version` starts with `3.10`.
     - `torch_version` is present and matches `torch.__version__`.
     - `installed_packages` dict includes `fitz`, `pdfplumber`, `shapely`, `cv2`, `torch`, `numpy`, `pandas`.

#### Class `TestTrainingAutoConfiguration`
1. **`test_auto_config_constrained_cpu_local_profile`**:
   - Input mock profile: CPU-only (`cuda_available: False`), RAM total 7.88 GB, RAM available 0.90 GB.
   - Call `get_training_auto_config(mock_profile)`.
   - Assertions:
     - `config["device"] == "cpu"`
     - `config["batch_size"] <= 2`
     - `config["img_size"] == 256`
     - `config["use_amp"] is False`
     - `config["num_workers"] == 0`
     - `config["is_local_constrained"] is True`
     - `config["colab_recommended"] is True`
     - `"Google Colab" in config["recommendation_message"]`
2. **`test_auto_config_unconstrained_cpu_profile`**:
   - Input mock profile: CPU-only, RAM total 32.0 GB, RAM available 16.0 GB.
   - Call `get_training_auto_config(mock_profile)`.
   - Assertions:
     - `config["device"] == "cpu"`
     - `config["batch_size"] >= 4`
     - `config["img_size"] in [256, 384, 512]`
     - `config["use_amp"] is False`
3. **`test_auto_config_colab_t4_gpu_profile`**:
   - Input mock profile: `cuda_available: True`, `vram_total_gb: 15.0`, RAM available 12.0 GB.
   - Call `get_training_auto_config(mock_profile)`.
   - Assertions:
     - `config["device"] == "cuda"`
     - `config["batch_size"] == 16`
     - `config["img_size"] == 512`
     - `config["use_amp"] is True`
     - `config["num_workers"] >= 2`
     - `config["colab_recommended"] is False`
4. **`test_auto_config_mid_tier_gpu_profile`**:
   - Input mock profile: `cuda_available: True`, `vram_total_gb: 6.0`.
   - Call `get_training_auto_config(mock_profile)`.
   - Assertions:
     - `config["device"] == "cuda"`
     - `config["batch_size"] in [4, 8]`
     - `config["img_size"] == 512`
     - `config["use_amp"] is True`
5. **`test_auto_config_low_vram_gpu_profile`**:
   - Input mock profile: `cuda_available: True`, `vram_total_gb: 2.0`.
   - Call `get_training_auto_config(mock_profile)`.
   - Assertions:
     - `config["device"] == "cuda"`
     - `config["batch_size"] == 2`
     - `config["img_size"] == 256`
     - `config["use_amp"] is False`

---

## 4. Specification for `drywall_detection/tests/test_audit.py`

### 4.1 Target Module Contracts
The tests verify `drywall_detection.audit.dataset_auditor`:
- Class `DatasetAuditor`:
  - `audit_candidate(dataset_name: str) -> DatasetAuditRecord`
  - `audit_all() -> Dict[str, DatasetAuditRecord]`
  - `check_disk_space(required_gb: float, target_path: str = ".") -> DiskCheckResult`
  - `check_download_threshold(size_gb: float, threshold_gb: float = 10.0) -> DownloadThresholdResult`
  - `validate_license_and_access(dataset_name: str) -> LicenseValidationResult`
  - `generate_markdown_report() -> str`
  - `generate_json_report() -> str`
- CLI Entry Point: `drywall_detection.audit.dataset_auditor:main(args=None)`

### 4.2 Test Classes and Test Cases

#### Class `TestDatasetAuditorCatalog`
1. **`test_audit_all_catalogs_exact_six_candidates`**:
   - Call `auditor.audit_all()`.
   - Assertions:
     - Result contains exactly 6 candidate keys: `{"cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd", "msd"}` (case-insensitive keys).
2. **`test_dataset_metadata_schema_fields`**:
   - For every dataset audited:
   - Assertions:
     - Record contains `name`, `official_source_url`, `download_size_gb`, `license_name`, `is_commercial_allowed`, `has_wall_annotations`, `annotation_format`, `eligibility_verdict`, `access_type`.

#### Class `TestDatasetEligibilityVerdicts`
1. **`test_msd_audit_verdict`**:
   - Call `auditor.audit_candidate("msd")`.
   - Assertions:
     - `record.eligibility_verdict == "ELIGIBLE"`
     - `record.is_commercial_allowed is True` (CC BY 4.0)
     - `record.has_wall_annotations is True` (WKT separator / WALL polygons)
     - `record.download_size_gb <= 1.0` (174 MB HF / 888 MB Zenodo)
     - `record.access_type == "PUBLIC_DIRECT"`
2. **`test_cubicasa5k_audit_verdict`**:
   - Call `auditor.audit_candidate("cubicasa5k")`.
   - Assertions:
     - `record.eligibility_verdict == "ELIGIBLE"`
     - `record.is_commercial_allowed is False` (CC BY-NC-SA 4.0)
     - `record.has_wall_annotations is True` (SVG polygon class "Wall")
     - `math.isclose(record.download_size_gb, 5.09, rel_tol=0.1)`
     - `record.download_size_gb < 10.0` (Under 10 GB unannounced threshold)
3. **`test_floorplancad_audit_verdict`**:
   - Call `auditor.audit_candidate("floorplancad")`.
   - Assertions:
     - `record.eligibility_verdict == "CONDITIONALLY_ELIGIBLE"`
     - `"copyright disclaimer" in record.notes.lower() or "disclaimer" in record.notes.lower()`
     - `record.has_wall_annotations is True` (COCO panoptic stuff class "Wall")
4. **`test_cvc_fp_audit_verdict`**:
   - Call `auditor.audit_candidate("cvc_fp")`.
   - Assertions:
     - `record.eligibility_verdict == "CONDITIONALLY_ELIGIBLE"`
     - `record.has_wall_annotations is True`
     - `"mirror" in record.notes.lower() or "figshare" in record.official_source_url.lower()`
5. **`test_r2v_audit_verdict_ineligible_gated`**:
   - Call `auditor.audit_candidate("r2v")`.
   - Assertions:
     - `record.eligibility_verdict == "INELIGIBLE_FOR_AUTOMATED_DOWNLOAD"`
     - `record.requires_user_agreement is True` (LIFULL / NII IDR agreement)
     - `record.access_type == "RESTRICTED_APPLICATION"`
6. **`test_sesyd_audit_verdict_ineligible_no_walls`**:
   - Call `auditor.audit_candidate("sesyd")`.
   - Assertions:
     - `record.eligibility_verdict == "INELIGIBLE_FOR_WALL_SEGMENTATION"`
     - `record.has_wall_annotations is False` (Zero wall labels; only 16 symbol categories)

#### Class `TestDiskSafetyAndThresholdGuards`
1. **`test_disk_space_check_sufficient`**:
   - Mock: `@patch("shutil.disk_usage", return_value=(150*1024**3, 130*1024**3, 20*1024**3))` (20 GB free).
   - Call `auditor.check_disk_space(required_gb=5.09, min_headroom_gb=2.0)`.
   - Assertions:
     - `result.is_sufficient is True`
     - `result.free_gb == 20.0`
     - `result.post_download_headroom_gb == 14.91`
2. **`test_disk_space_check_insufficient`**:
   - Mock: `@patch("shutil.disk_usage", return_value=(150*1024**3, 147*1024**3, 3*1024**3))` (3 GB free).
   - Call `auditor.check_disk_space(required_gb=5.09, min_headroom_gb=2.0)`.
   - Assertions:
     - `result.is_sufficient is False`
     - `"insufficient" in result.message.lower()`
3. **`test_disk_space_check_headroom_violation`**:
   - Mock: `@patch("shutil.disk_usage", return_value=(150*1024**3, 144*1024**3, 6*1024**3))` (6 GB free).
   - Call `auditor.check_disk_space(required_gb=5.0, min_headroom_gb=2.0)`.
   - Required + Headroom = 7.0 GB > 6.0 GB available.
   - Assertions:
     - `result.is_sufficient is False`
     - `"headroom" in result.message.lower()`
4. **`test_10gb_warning_threshold_not_triggered_below_limit`**:
   - Inputs: `0.174` (MSD), `5.09` (CubiCasa5K), `9.99`.
   - Call `auditor.check_download_threshold(size_gb)`.
   - Assertions:
     - `result.warning_triggered is False`
     - `result.requires_user_confirmation is False`
5. **`test_10gb_warning_threshold_triggered_above_limit`**:
   - Inputs: `10.01`, `15.0`, `25.0`.
   - Call `auditor.check_download_threshold(size_gb)`.
   - Assertions:
     - `result.warning_triggered is True`
     - `result.requires_user_confirmation is True`
     - `"10 gb" in result.warning_message.lower() or "10gb" in result.warning_message.lower()`
6. **`test_10gb_warning_threshold_exact_boundary`**:
   - Boundary tests at `threshold_gb = 10.0`:
     - `size_gb = 10.0`: `warning_triggered is False` (at threshold).
     - `size_gb = 10.001`: `warning_triggered is True` (exceeds threshold).

#### Class `TestNetworkAndLicenseMocking`
1. **`test_mock_url_probe_success`**:
   - Mock `urllib.request.urlopen` returning HTTP 200 with headers `{'Content-Length': '182452224'}`.
   - Call `auditor.probe_url("https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched")`.
   - Assertions:
     - `result["is_reachable"] is True`
     - `result["http_status"] == 200`
2. **`test_mock_url_probe_timeout_handling`**:
   - Mock `urllib.request.urlopen` raising `urllib.error.URLError("Connection timed out")` (simulating `dag.cvc.uab.es`).
   - Call `auditor.probe_url("http://dag.cvc.uab.es/dataset/cvc-fp")`.
   - Assertions:
     - `result["is_reachable"] is False`
     - `"timed out" in result["error_message"].lower()`
     - Auditor does not crash; records fallback status gracefully.
3. **`test_zero_license_acceptance_guard`**:
   - Verify that calling `auditor.prepare_dataset("r2v")` raises a `PermissionError` or returns `requires_manual_user_action=True` rather than auto-submitting terms of service.

#### Class `TestReportSerializationAndCLI`
1. **`test_generate_markdown_report_structure`**:
   - Call `auditor.generate_markdown_report()`.
   - Assertions:
     - Output is string.
     - Contains Markdown table header `| Dataset | Official Source | Size | License | Wall Labels | Eligibility |`.
     - Contains all 6 dataset names.
2. **`test_generate_json_report_structure`**:
   - Call `auditor.generate_json_report()`.
   - Assertions:
     - String parses into valid JSON via `json.loads()`.
     - Root object contains `"datasets"` key with 6 child entries.
3. **`test_cli_runner_json_output`**:
   - Mock `sys.argv = ["dataset_auditor", "--format", "json"]`.
   - Capture stdout using `capsys`.
   - Call `main()`.
   - Assertions:
     - Exit code 0.
     - Captured stdout parses as valid JSON containing dataset audit data.

---

## 5. Milestone M1 Audit Report Structure (`reports/M1_audit_report.md`)

The worker must implement the official Milestone M1 report at:
`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\drywall_detection\reports\M1_audit_report.md`

### 5.1 Mandatory Notice (Section 1)
The report must lead with this verbatim notice:
```markdown
> **MANDATORY NOTICE — PROGRESS SET & SINGLE-PROJECT BOUNDS**  
> The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
> Furthermore, all 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, and vector extractions on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards.
```

### 5.2 Section 2: Workspace Layout & Cleanliness Verification
- **Verification of Clean Workspace**:
  - Root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`
  - Workspace inspection: verify only `.agents/teamwork/` metadata exists at initialization.
  - Zero pre-existing code, legacy QTO packages, or temporary test dumps in root.
- **Strict Boundary Isolation**:
  - All source code, configs, pipeline scripts, tests, and reports reside exclusively within `drywall_detection/`.
  - `.agents/teamwork/` contains only agent state and communication files (`BRIEFING.md`, `progress.md`, `handoff.md`, `report.md`). No source code, tests, or project data are placed inside `.agents/`.

### 5.3 Section 3: Authoritative Reference PDF Properties & Sheet Catalog
- **Document Identification**:
  - File Path: `C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf`
  - File Size: `29,110,223 bytes` (~27.76 MB)
  - Client / Project: Metropolitan Transportation Authority (MTA C&D), Contract C-48526, 99th Street Phase 2 Interior Set.
  - Architect: TPG Architecture LLP.
  - Stamp: `"PROGRESS SET 95% CDs 10/02/2026"`.
  - Page Count: Exactly **71 pages**.
- **Page Geometry & Rotations**:
  - MediaBox (Unrotated): `Rect(0.0, 0.0, 1728.0, 2592.0)` pt ($W=1728, H=2592$).
  - CropBox: `Rect(0.0, 0.0, 1728.0, 2592.0)` pt.
  - Rotation: **90° clockwise** on 100% of pages (all 71 pages).
  - Rendered Visual Landscape Dimensions: $2592.0 \times 1728.0$ pt (standard 36" x 24" Arch D format).
  - Scale Factor $S = DPI / 72.0$: at 150 DPI, visual image size is $5400 \times 3600$ pixels.
- **Vector Usability & CAD Text Layer**:
  - 100% native vector drawing content across all pages (from 190 paths on survey sheet to 618,536 paths on A-204).
  - Searchable text layer with 9 embedded fonts (`ArialMT`, `CenturyGothic`, `Helvetica75Bold`, `ArialNarrow`, etc.). No OCR required for baseline extraction.
- **Master Sheet Index Catalog (from Sheet G-002, Page 3)**:
  - Complete inventory table of all 71 pages mapping Page #, Sheet Number, Title, Vector Path Count, Text Character Count, and Pipeline Role.
- **Partition Schedule Sheets (Page 63, A-900 & Page 64, A-901)**:
  - Full catalog of all **24 assembly details**:
    - Tag 1A: `6" FIRE RATED CMU` (masonry / Non-Drywall).
    - Tags 1B, 1C, 1D, 1E: Metal stud partitions with single 5/8" GWB each side (Drywall).
    - Tags 2B, 2C: Slab-to-slab metal stud partitions with 5/8" GWB (Drywall).
    - Tags 3A, 3D: Acoustically insulated metal stud partitions with 5/8" GWB (Drywall).
    - Tags 5B, 5D: 1-hr fire-rated partitions with Type X GWB (Drywall).
    - Tag 5E: 2-hr fire-rated partition with 2 layers Type X GWB each side (Drywall).
    - Tags 7A, 7B: Furring partitions with 5/8" GWB (Drywall).
    - Tags 7C, 7E, 7G: Interior partitions with GWB and batt insulation (Drywall).
    - Tag 7F: 2-hr shaft wall with C-H studs, 1" SCX liner + 2 layers 1/2" Type C GWB (Drywall).
    - Tag 8A: Direct wall furring with 5/8" GWB (Drywall).
    - Tag GL1, GL2: Infinium Quantum butt-glazed glass office front systems (Non-Drywall).
    - Tag 09: Section @ TV Screen / millwork AV backing (Uncertain).
    - Tag 10: Steel column enclosure with 2 layers Type X GWB (Drywall).
    - Tag 11: Concrete encased steel column (Non-Drywall).
- **Floor Plan Tag Occurrences**:
  - 233 verified tag instances on construction sheets A-100 to A-105 enclosed in $11.2 \times 11.3$ pt vector boxes with leader lines.
- **Auxiliary Project Files Discovered**:
  - `drywall_relevant_full_pages.pdf`: 27-sheet subset (8.08 MB).
  - `drywall_walls_marked_red_by_Usman.pdf`: 27 sheets, 478 red human markup annotations for R4 review.
  - `drywall_annotated_floor_plans.pdf`: 27 sheets, 502 annotations, uncovering the critical prior error where Tag 1A was falsely classified as drywall (95% prob).

### 5.4 Section 4: Hardware Specifications & Execution Bounds
- **Audited Host Specifications**:
  - CPU: Intel Core (Family 6 Model 142 Stepping 10), 4 physical cores, 8 logical threads.
  - RAM: 7.88 GB total, **~0.90 GB available** (88.5% utilization).
  - GPU: Intel(R) UHD Graphics 620 integrated; No dedicated GPU; No CUDA support.
  - PyTorch: `2.1.0+cpu` (CPU execution only).
  - Storage: C:\ 16.37 GB free; E:\ 30.45 GB free (combined 46.82 GB free).
  - Python: 3.10.0 64-bit AMD64.
- **Hardware-Aware Adaptation Strategy**:
  - Local CPU execution strictly bounded to sanity checks and lightweight crops ($256 \times 256$, batch size 1–2).
  - Full segmentation model training scripts designed with 100% Google Colab compatibility (T4 GPU, 15.3 GB VRAM, batch size 16, $512 \times 512$ resolution, FP16 mixed precision).

### 5.5 Section 5: Empirical Audit of 6 Candidate Datasets
- **Complete Comparative Audit Table**:

| Dataset | Official Source / Host | Download Size (Raw / Processed) | License Terms | Commercial Use? | Annotation Format | Wall / Partition Labels Present? | Direct Download & Auth Status | Eligibility Verdict |
|---|---|---|---|---|---|---|---|---|
| **Modified Swiss Dwellings (MSD)** | Hugging Face (`philippds/modified-swiss-dwellings-enriched`) & Zenodo (`10.5281/zenodo.7788422`) | **174 MB** (HF) / **888.7 MB** (Zenodo v3.0.0 zip) | **CC BY 4.0** | **YES** (with attribution) | WKT vector polygons, structured tabular metadata, raster images | **YES**: Explicit `entity_type: separator`, `entity_subtype: WALL` with exact polygon boundary coordinates. Multi-apartment complexes. | Direct public HTTPS download via Hugging Face API / Zenodo. No login required. | **ELIGIBLE (Top Recommended)** |
| **CubiCasa5K** | Zenodo (`record/2613548`), GitHub: `CubiCasa/CubiCasa5k` | **5.09 GB** (zip) / ~20-105 GB (uncompressed/LMDB) | **CC BY-NC-SA 4.0** | **NO** (Academic / Non-commercial only) | High-resolution raster images (PNG/JPG) + Vector SVG annotations | **YES**: Over 147,000 explicit wall polygon segments (`<g id="Wall">`), external walls, internal railings. | Direct public download via Zenodo CDN (`cubicasa5k.zip`). No login required. Under 10 GB limit. | **ELIGIBLE (Primary Academic Benchmark)** |
| **FloorPlanCAD** | GitHub Pages (`floorplancad.github.io`), Hugging Face (`Voxel51/FloorPlanCAD`) | **454 MB** (Hugging Face) / ~2.5 GB (Google Drive parts) | Annotations: **CC BY-NC 4.0**; Drawings: Third-party copyright disclaimer | **NO** (Drawing copyright disclaimer leaves risk to user) | SVG vector primitives, PNG images ($20\text{m} \times 20\text{m}$ crops), COCO panoptic format | **YES**: "Wall" is explicitly labeled as an uncountable "Stuff" class alongside 28 "Thing" classes. | Google Drive links active; Hugging Face mirror available. | **CONDITIONALLY ELIGIBLE** (CAD domain matches vector drawings; license disclaimer requires caution) |
| **CVC-FP** | Computer Vision Center (UAB), Figshare (`10.6084/m9.figshare.12082131`), Zenodo (`10.5281/zenodo.7921780`) | **~15 MB** (original 122 images) / **353 MB** (Figshare rotated package) | Academic Non-Commercial (CVC) / **CC BY 4.0** (Figshare mirror) | **Conditional** (Mirror is CC BY 4.0) | Scanned rasters (4 styles: Black, Textured1, Textured2, Parallel) + SVG vector ground truth & binary masks | **YES**: Explicit structural wall, door, window, and room segmentation. | Original university server (`dag.cvc.uab.es`) timed out / offline. Figshare / Zenodo mirrors direct download. | **CONDITIONALLY ELIGIBLE** (Small size: 122 plans; good for quick sanity checks) |
| **R2V (Raster-to-Vector)** | CVPR 2017 (`art-programmer/FloorplanTransformation`), LIFULL Co., Ltd. / NII IDR | Annotations: ~10 MB; Images: >10 GB | Annotations: MIT; Images: Proprietary LIFULL institutional agreement | **NO** (Restricted academic data agreement) | Vector representation (junctions, line primitives, text files) | **YES**: Wall junctions and boundary lines annotated in vector format. | **BLOCKED BY ACCESS RESTRICTIONS**: Raster images require formal institutional application to NII IDR. | **INELIGIBLE FOR AUTOMATED DOWNLOAD** (Violates non-interactive constraint) |
| **SESYD Floorplans** | Mathieu Delalandre / IJDAR 2010 (`mathieu.delalandre.free.fr/projects/sesyd/`) | ~6 MB per zip (~100 MB total) | Open Access Academic Research | **NO** (Academic benchmarking) | TIFF binary line drawings + XML symbol bounding boxes | **NO**: Annotations exist exclusively for 16 symbol classes (armchair, table, bed, door, window, sink). **ZERO wall labels**. | Direct public HTTP download without authentication. | **INELIGIBLE FOR WALL SEGMENTATION** (Lacks ground-truth wall annotations) |

- **Disk Safety Protocols**:
  - Free space verification before download.
  - Safety headroom threshold: $\ge 2.0$ GB free after download.
  - Strict notification rule: no download $> 10$ GB allowed without explicit user notification and confirmation.
  - Zero license acceptance: auditor will never accept terms of service or click-through agreements on the user's behalf.

### 5.6 Section 6: Data Partitioning Protocol & Zero Project Leakage
- **The Data Leakage Vulnerability**: Multi-floor and multi-sheet architectural drawings share building footprints, exterior perimeters, structural column grids, and firm-specific drafting line styles.
- **Project-Level Partitioning Requirement**:
  $$\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset, \quad \mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset, \quad \mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}} = \emptyset$$
  - MSD: Group by `site_id` or `building_id`.
  - CubiCasa5K: Group by top-level floorplan folder ID.
  - FloorPlanCAD: Group by CAD drawing ID (never by $20\text{m} \times 20\text{m}$ tiles).
- **Quarantine of 99th Street Weak Pseudo-Labels**:
  - Vector-extracted masks from 99th Street must be tagged with `"is_pseudo_label": true`.
  - Must undergo human visual error spot-checking (5–10 regions).
  - Strictly quarantined to training split only; never included in validation or test sets.

### 5.7 Section 7: Verification Artifacts & Milestone M1 Sign-Off
- Inventory of verification tests executed.
- Pytest command and expected output:
  `pytest drywall_detection/tests/ -v` (all tests passing).
- Sign-off criteria for advancing to Milestone M2 (Dataset Preparation).

---

## 6. Worker Implementation Plan & Concrete Action Steps

When the Worker agent executes Milestone M1, it must follow this exact step-by-step sequence:

### Step 1: Directory Tree & Module Setup
1. Create `drywall_detection/` and subpackages:
   - `drywall_detection/__init__.py`
   - `drywall_detection/config.py`
   - `drywall_detection/utils/__init__.py`
   - `drywall_detection/utils/coords.py`
   - `drywall_detection/utils/hardware.py`
   - `drywall_detection/audit/__init__.py`
   - `drywall_detection/audit/dataset_auditor.py`
   - `drywall_detection/tests/__init__.py`
   - `drywall_detection/tests/test_coords.py`
   - `drywall_detection/tests/test_hardware.py`
   - `drywall_detection/tests/test_audit.py`
   - `drywall_detection/reports/M1_audit_report.md`

### Step 2: Implement Test Files First (TDD Approach)
1. Author `drywall_detection/tests/test_coords.py` following Section 2 specifications.
2. Author `drywall_detection/tests/test_hardware.py` following Section 3 specifications.
3. Author `drywall_detection/tests/test_audit.py` following Section 4 specifications.

### Step 3: Implement Production Code
1. Implement `drywall_detection/config.py` with paths, dimensions, thresholds, and class maps.
2. Implement `drywall_detection/utils/coords.py` implementing exact mathematical affine transformations and Shapely geometry operations.
3. Implement `drywall_detection/utils/hardware.py` implementing psutil/torch hardware probes and auto-configuration recommendations.
4. Implement `drywall_detection/audit/dataset_auditor.py` implementing DatasetAuditor with candidate audit records, disk checking, 10GB threshold checks, and CLI interface.

### Step 4: Author the Official Report
1. Author `drywall_detection/reports/M1_audit_report.md` following the Section 5 template, including the mandatory 95% CDs notice, reference PDF survey, hardware specs, and 6-dataset audit.

### Step 5: Execute Pytest and Verify
1. Run `pytest drywall_detection/tests/ -v`.
2. Confirm 100% of test cases pass with zero errors and zero warnings.
3. Document exact pytest output in `drywall_detection/reports/M1_audit_report.md`.

---
*End of Architectural Plan ARCH-EXP3-M1-001.*
