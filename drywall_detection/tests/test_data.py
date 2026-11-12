"""
drywall_detection/tests/test_data.py
===================================
Comprehensive unit test suite for Milestone M2:
- Project-isolated data splitting invariants (0% leakage, greedy partitioning, determinism)
- Mask dimensions, uint8 dtype, {0, 1, 2, 3} class values, and coordinate bounds
- Geometric affine mapping, polygon rasterization, hole evacuation, and sanitization
- Visual QC triplet generation, palette mapping, and alpha blending
- Disk safety pre-flight checks and 10 GB user notification threshold
- MSD downloader catalog, SHA-256 validation, and caching checks
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import List
import pytest
import numpy as np
from PIL import Image
import cv2
import torch
from shapely.geometry import Polygon, MultiPolygon

from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_RGB,
    CLASS_COLORS_BGR,
    DEFAULT_OVERLAY_ALPHA,
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
)
from drywall_detection.data.splitter import (
    SampleRecord,
    SplitPartitionStats,
    SplitManifestBundle,
    ProjectDataSplitter,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    assert_zero_leakage,
)
from drywall_detection.data.preparer import (
    PreparationConfig,
    GeometryRasterizer,
    DrawingSanitizer,
    PALETTE_256,
)
from drywall_detection.data.qc import (
    VisualQCGenerator,
    VisualQCPipeline,
    QCInspectionRecord,
)
from drywall_detection.data.downloader import (
    MSDDownloader,
    MSD_CATALOG,
    DatasetFileSpec,
    compute_file_sha256,
)
from drywall_detection.utils.hardware import check_disk_safety


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def synthetic_sample_records(tmp_path: Path) -> List[SampleRecord]:
    """Generates 120 synthetic samples across 12 distinct projects (2 drawings, 5 tiles each)."""
    samples = []
    img_dir = tmp_path / "images"
    msk_dir = tmp_path / "masks"
    img_dir.mkdir(parents=True, exist_ok=True)
    msk_dir.mkdir(parents=True, exist_ok=True)

    for p_idx in range(12):
        proj_id = f"site_{p_idx:03d}"
        for d_idx in range(2):
            draw_id = f"{proj_id}_drawing_{d_idx:02d}"
            for t_idx in range(5):
                s_id = f"{draw_id}_tile_{t_idx:02d}"
                img_path = img_dir / f"{s_id}.png"
                msk_path = msk_dir / f"{s_id}.png"

                # Create lightweight dummy files
                dummy_img = np.full((128, 128, 3), 240, dtype=np.uint8)
                dummy_msk = np.zeros((128, 128), dtype=np.uint8)
                if t_idx % 2 == 0:
                    dummy_msk[20:60, 20:60] = CLASS_DRYWALL
                cv2.imwrite(str(img_path), dummy_img)

                p_img = Image.fromarray(dummy_msk, mode='P')
                p_img.putpalette(PALETTE_256)
                p_img.save(msk_path)

                samples.append(
                    SampleRecord(
                        sample_id=s_id,
                        project_id=proj_id,
                        drawing_id=draw_id,
                        image_path=str(img_path),
                        mask_path=str(msk_path),
                        bbox=(0, 0, 128, 128),
                        width=128,
                        height=128,
                        has_walls=(t_idx % 2 == 0),
                        wall_pixel_count=1600 if (t_idx % 2 == 0) else 0,
                        total_pixel_count=128 * 128,
                        is_pseudo_label=(proj_id == "site_011"),
                        quarantine=(proj_id == "site_011"),
                    )
                )
    return samples


# ==============================================================================
# 1. Project-Isolated Data Splitting Tests
# ==============================================================================

class TestProjectIsolatedSplitting:
    """Tests strict 0% leakage, greedy multi-way partitioning, and isolation invariants."""

    def test_strict_project_isolation_disjoint_sets(self, synthetic_sample_records):
        """Verifies projects in Train, Val, and Test form completely disjoint sets."""
        splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15), seed=42)
        bundle = splitter.split(synthetic_sample_records)

        train_projs = {s.project_id for s in bundle.train_samples}
        val_projs = {s.project_id for s in bundle.val_samples}
        test_projs = {s.project_id for s in bundle.test_samples}

        assert len(train_projs & val_projs) == 0, f"Leakage Train/Val: {train_projs & val_projs}"
        assert len(train_projs & test_projs) == 0, f"Leakage Train/Test: {train_projs & test_projs}"
        assert len(val_projs & test_projs) == 0, f"Leakage Val/Test: {val_projs & test_projs}"

    def test_strict_drawing_isolation_disjoint_sets(self, synthetic_sample_records):
        """Verifies drawings in Train, Val, and Test form completely disjoint sets."""
        splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15), seed=42)
        bundle = splitter.split(synthetic_sample_records)

        train_draws = {s.drawing_id for s in bundle.train_samples}
        val_draws = {s.drawing_id for s in bundle.val_samples}
        test_draws = {s.drawing_id for s in bundle.test_samples}

        assert len(train_draws & val_draws) == 0
        assert len(train_draws & test_draws) == 0
        assert len(val_draws & test_draws) == 0

    def test_strict_filepath_isolation_disjoint_sets(self, synthetic_sample_records):
        """Verifies image and mask paths in Train, Val, and Test have zero overlap."""
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(synthetic_sample_records)

        train_imgs = {Path(s.image_path).resolve() for s in bundle.train_samples}
        val_imgs = {Path(s.image_path).resolve() for s in bundle.val_samples}
        test_imgs = {Path(s.image_path).resolve() for s in bundle.test_samples}

        assert len(train_imgs & val_imgs) == 0
        assert len(train_imgs & test_imgs) == 0
        assert len(val_imgs & test_imgs) == 0

    def test_leakage_injection_raises_split_leakage_error(self, synthetic_sample_records):
        """Verifies assert_zero_leakage immediately raises SplitLeakageError on injected overlap."""
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(synthetic_sample_records)

        # Inject deliberate leakage: copy train sample into val
        bundle.val_samples.append(bundle.train_samples[0])
        with pytest.raises(SplitLeakageError, match="Train/Val project leakage detected"):
            assert_zero_leakage(bundle)

    def test_deterministic_splits_with_seed(self, synthetic_sample_records):
        """Verifies identical seed produces identical manifests and identical SHA-256 hash."""
        s1 = ProjectDataSplitter(seed=42).split(synthetic_sample_records)
        s2 = ProjectDataSplitter(seed=42).split(synthetic_sample_records)
        s3 = ProjectDataSplitter(seed=999).split(synthetic_sample_records)

        assert [s.sample_id for s in s1.train_samples] == [s.sample_id for s in s2.train_samples]
        assert s1.verification_hash == s2.verification_hash
        assert s1.verification_hash != s3.verification_hash

    def test_quarantined_projects_excluded_from_val_and_test(self, synthetic_sample_records):
        """Verifies quarantined projects never enter validation or test splits."""
        splitter = ProjectDataSplitter(quarantine_projects=["site_001", "site_002"])
        bundle = splitter.split(synthetic_sample_records)

        val_projs = {s.project_id for s in bundle.val_samples}
        test_projs = {s.project_id for s in bundle.test_samples}

        assert "site_001" not in val_projs and "site_001" not in test_projs
        assert "site_002" not in val_projs and "site_002" not in test_projs
        # site_011 was flagged as is_pseudo_label in fixture
        assert "site_011" not in val_projs and "site_011" not in test_projs
        assert len(bundle.quarantine_samples) == 30  # 10 tiles each for site_001, site_002, site_011

    def test_insufficient_groups_error(self):
        """Verifies InsufficientGroupsError is raised when < 3 groups exist."""
        samples = [
            SampleRecord("s1", "p1", "d1", "/img/1.png", "/msk/1.png"),
            SampleRecord("s2", "p2", "d2", "/img/2.png", "/msk/2.png"),
        ]
        splitter = ProjectDataSplitter(allow_drawing_fallback=False)
        with pytest.raises(InsufficientGroupsError):
            splitter.split(samples)

    def test_invalid_split_ratios_error(self):
        """Verifies InvalidSplitRatioError is raised when ratios do not sum to 1.0 or are <= 0."""
        with pytest.raises(InvalidSplitRatioError):
            ProjectDataSplitter(split_ratios=(0.80, 0.20, 0.10))
        with pytest.raises(InvalidSplitRatioError):
            ProjectDataSplitter(split_ratios=(1.0, 0.0, 0.0))

    def test_manifest_export_and_json_schema(self, synthetic_sample_records, tmp_path: Path):
        """Verifies manifest export creates valid JSON files passing schema checks."""
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(synthetic_sample_records)
        exported = splitter.export_manifests(bundle, tmp_path)

        assert "train" in exported and exported["train"].is_file()
        assert "val" in exported and exported["val"].is_file()
        assert "test" in exported and exported["test"].is_file()
        assert "summary" in exported and exported["summary"].is_file()

        with open(exported["summary"], "r", encoding="utf-8") as f:
            summary = json.load(f)
        assert summary["isolation_status"] == "VERIFIED_ZERO_LEAKAGE"
        assert len(summary["verification_hash"]) == 64


# ==============================================================================
# 2. Mask Dimensions, Class Values, and Bounds Tests
# ==============================================================================

class TestMaskDimensionsClassValuesAndBounds:
    """Verifies mask shapes, uint8 dtype, discrete {0, 1, 2, 3} values, and spatial bounds."""

    def test_mask_dimensions_match_image(self, synthetic_sample_records):
        """Verifies image and mask dimensions match exactly."""
        for rec in synthetic_sample_records[:10]:
            img = cv2.imread(rec.image_path)
            msk = cv2.imread(rec.mask_path, cv2.IMREAD_UNCHANGED)
            assert img.shape[:2] == msk.shape[:2]

    def test_mask_class_values_strict_range(self):
        """Verifies mask values are strictly within {0, 1, 2, 3}."""
        valid_mask = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        assert set(np.unique(valid_mask)).issubset({0, 1, 2, 3})

        invalid_mask = np.array([[0, 1], [2, 4]], dtype=np.uint8)
        invalid_vals = [int(v) for v in np.unique(invalid_mask) if v not in (0, 1, 2, 3)]
        assert len(invalid_vals) > 0 and 4 in invalid_vals

    def test_mode_p_indexed_png_roundtrip(self, tmp_path: Path):
        """Verifies Mode 'P' indexed PNG preserves discrete values and loads into PyTorch int64."""
        arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        out_path = tmp_path / "test_p.png"
        img_p = Image.fromarray(arr, mode='P')
        img_p.putpalette(PALETTE_256)
        img_p.save(out_path)

        with Image.open(out_path) as loaded:
            assert loaded.mode == 'P'
            loaded_arr = np.array(loaded)
            np.testing.assert_array_equal(loaded_arr, arr)

        # PyTorch direct tensor loading without de-mapping
        tensor = torch.from_numpy(loaded_arr).long()
        assert tensor.dtype == torch.int64
        assert tensor.shape == (2, 2)
        assert set(tensor.unique().tolist()).issubset({0, 1, 2, 3})

    def test_bounding_box_coordinates_bounds(self, synthetic_sample_records):
        """Verifies bounding box coordinates satisfy 0 <= min < max <= dim."""
        for rec in synthetic_sample_records:
            x0, y0, x1, y1 = rec.bbox
            assert 0 <= x0 < x1 <= rec.width
            assert 0 <= y0 < y1 <= rec.height


# ==============================================================================
# 3. Geometric Rasterization and Sanitization Tests
# ==============================================================================

class TestGeometryRasterizerAndSanitizer:
    """Verifies affine mapping, polygon rasterization, hole evacuation, and sanitization."""

    def test_affine_transformation_bounds_clamping(self):
        """Verifies affine mapping maps metric coords into [0, target_width-1] and [0, target_height-1]."""
        cfg = PreparationConfig(target_width=512, target_height=512, margin_ratio=0.05)
        rasterizer = GeometryRasterizer(cfg)

        bounds = (100.0, 200.0, 150.0, 300.0)
        affine = rasterizer.compute_affine_parameters(bounds)

        test_pts = [(100.0, 200.0), (150.0, 300.0), (125.0, 250.0)]
        pixel_pts = rasterizer.transform_coords_to_pixel(test_pts, affine)

        assert pixel_pts.shape == (3, 1, 2)
        for pt in pixel_pts:
            px, py = pt[0]
            assert 0 <= px < 512
            assert 0 <= py < 512

    def test_polygon_hole_evacuation(self):
        """Verifies cv2.fillPoly correctly evacuates interior holes to background class 0."""
        cfg = PreparationConfig(target_width=200, target_height=200, margin_ratio=0.0)
        rasterizer = GeometryRasterizer(cfg)

        # Doughnut: outer 100x100, inner hole 40x40 centered
        outer = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0)]
        inner = [(30.0, 30.0), (70.0, 30.0), (70.0, 70.0), (30.0, 70.0), (30.0, 30.0)]
        poly = Polygon(shell=outer, holes=[inner])

        bin_mask, multi_mask = rasterizer.rasterize_polygons(
            polygons=[poly],
            bounds=(0.0, 0.0, 100.0, 100.0),
            target_class=CLASS_UNCERTAIN,
        )

        assert bin_mask.shape == (200, 200)
        assert multi_mask.shape == (200, 200)

        # Center point (50, 50 in metric -> 100, 100 in pixel) must be background (0)
        center_val_bin = bin_mask[100, 100]
        center_val_multi = multi_mask[100, 100]
        assert center_val_bin == 0, f"Hole center was not evacuated (got {center_val_bin})"
        assert center_val_multi == 0, f"Hole center was not evacuated (got {center_val_multi})"

        # Wall perimeter point (15, 50 in metric) must be wall
        edge_pts = rasterizer.transform_coords_to_pixel([(15.0, 50.0)], rasterizer.compute_affine_parameters((0.0, 0.0, 100.0, 100.0)))
        epx, epy = edge_pts[0, 0]
        assert bin_mask[epy, epx] == 1
        assert multi_mask[epy, epx] == CLASS_UNCERTAIN

    def test_topology_repair_self_intersection(self):
        """Verifies DrawingSanitizer repairs self-intersecting bowtie polygon into valid polygons."""
        sanitizer = DrawingSanitizer(PreparationConfig())

        # Self-intersecting bowtie: (0,0) -> (2,2) -> (2,0) -> (0,2) -> (0,0)
        bowtie_wkt = "POLYGON ((0 0, 2 2, 2 0, 0 2, 0 0))"
        repaired = sanitizer.sanitize_polygon(bowtie_wkt)

        assert len(repaired) >= 1
        for p in repaired:
            assert p.is_valid
            assert p.area > 0

    def test_degenerate_polygon_filtering(self):
        """Verifies sanitizer discards tiny or degenerate polygons."""
        cfg = PreparationConfig(min_polygon_area=1e-3)
        sanitizer = DrawingSanitizer(cfg)

        # Very tiny triangle
        tiny_wkt = "POLYGON ((0 0, 0.0001 0, 0 0.0001, 0 0))"
        result = sanitizer.sanitize_polygon(tiny_wkt)
        assert len(result) == 0

        # Empty WKT
        assert sanitizer.sanitize_polygon("") == []
        assert sanitizer.sanitize_polygon("GEOMETRYCOLLECTION EMPTY") == []

    def test_deduplication(self):
        """Verifies duplicate polygons are filtered out."""
        sanitizer = DrawingSanitizer()
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        p2 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        p3 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)])

        unique = sanitizer.deduplicate_polygons([p1, p2, p3])
        assert len(unique) == 2


# ==============================================================================
# 4. Visual QC Pipeline Tests
# ==============================================================================

class TestVisualQCPipeline:
    """Verifies visual QC triplet composite image rendering, dimensions, and alpha blending."""

    def test_qc_triplet_dimensions(self):
        """Verifies triplet has width 3 * W and height H + 40 (banner)."""
        gen = VisualQCGenerator(alpha=0.40)
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:40, 20:40] = CLASS_DRYWALL

        meta = {"sample_id": "test_01", "project_id": "proj_A", "split_name": "train"}
        triplet = gen.create_triplet(img, mask, meta)

        assert triplet.shape == (140, 300, 3)  # 100 + 40 banner, 100 * 3 width

    def test_qc_alpha_blending_numerical_accuracy(self):
        """Verifies blended overlay matches (1 - alpha) * I + alpha * C within 1 unit."""
        alpha = 0.40
        gen = VisualQCGenerator(alpha=alpha)
        img = np.full((10, 10, 3), 100, dtype=np.uint8)
        mask = np.full((10, 10), CLASS_DRYWALL, dtype=np.uint8)

        overlay = gen.render_overlay(img, mask)
        expected = np.round(100 * (1.0 - alpha) + np.array(CLASS_COLORS_BGR[CLASS_DRYWALL]) * alpha).astype(np.uint8)

        actual_pixel = overlay[5, 5]
        diff = np.abs(actual_pixel.astype(int) - expected.astype(int))
        assert np.all(diff <= 1)

    def test_qc_samples_generation_and_manifest(self, synthetic_sample_records, tmp_path: Path):
        """Verifies running QC pipeline generates image files and qc_manifest.json."""
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(synthetic_sample_records)
        splits_dir = tmp_path / "splits"
        splitter.export_manifests(bundle, splits_dir)

        qc_out = tmp_path / "qc_samples"
        pipeline = VisualQCPipeline(output_dir=qc_out, alpha=0.40)
        records = pipeline.run_qc_on_splits(splits_dir, samples_per_split=2)

        assert len(records) > 0
        assert (qc_out / "qc_manifest.json").is_file()
        for r in records:
            assert Path(r.qc_image_path).is_file()


# ==============================================================================
# 5. Disk Safety and Threshold Checks
# ==============================================================================

class TestDiskSafetyGuards:
    """Verifies disk headroom pre-flight checks and 10 GB limit enforcement."""

    def test_disk_safety_sufficient_headroom(self):
        """Verifies check_disk_safety passes on host workspace volume for small payloads."""
        is_safe, free_gb, msg = check_disk_safety(required_free_gb=0.174)
        assert isinstance(is_safe, bool)
        assert free_gb > 0.0
        assert "free" in msg

    def test_10gb_user_notification_limit_trigger(self):
        """Verifies operations exceeding 10.0 GB trigger warning in message."""
        _, _, msg_small = check_disk_safety(required_free_gb=5.0)
        assert "mandatory user notification" not in msg_small

        _, _, msg_large = check_disk_safety(required_free_gb=10.5)
        assert "mandatory user notification" in msg_large

    def test_negative_required_gb_raises_value_error(self):
        """Verifies negative required space raises ValueError."""
        with pytest.raises(ValueError):
            check_disk_safety(required_free_gb=-1.0)


# ==============================================================================
# 6. MSD Downloader Catalog & Caching Tests
# ==============================================================================

class TestMSDDownloaderCatalogAndCaching:
    """Verifies MSD downloader catalog integrity, SHA-256 calculation, and dry-run pre-flight checks."""

    def test_catalog_file_specs(self):
        """Verifies MSD_CATALOG has valid entries, sizes, and 64-char SHA-256 digests."""
        assert len(MSD_CATALOG) == 6
        for name, spec in MSD_CATALOG.items():
            assert spec.size_bytes > 0
            assert len(spec.sha256) == 64
            assert spec.sha256.lower() == spec.sha256  # must be lowercase hex
            assert spec.download_url.startswith("https://huggingface.co/")

    def test_compute_file_sha256(self, tmp_path: Path):
        """Verifies streaming SHA-256 computation on local sample file."""
        sample_file = tmp_path / "sample.txt"
        content = b"drywall_detection_sha256_test"
        sample_file.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()
        actual_hash = compute_file_sha256(sample_file)
        assert actual_hash == expected_hash

    def test_preflight_disk_check_blocks_over_10gb(self, tmp_path: Path):
        """Verifies downloader pre-flight blocks requested downloads > 10 GB unless permitted."""
        downloader = MSDDownloader(target_dir=tmp_path, allow_large_downloads=False)

        # Mock large file specs totaling 12 GB
        large_specs = [
            DatasetFileSpec(
                relative_path="large_file.dat",
                download_url="http://example.com/large",
                size_bytes=12 * 1024 * 1024 * 1024,
                sha256="0" * 64,
            )
        ]
        is_safe, _, msg = downloader.preflight_disk_check(large_specs)
        assert is_safe is False
        assert "exceeds" in msg and "mandatory notification limit" in msg

    def test_is_cached_valid(self, tmp_path: Path):
        """Verifies is_cached_valid correctly evaluates matching vs corrupt files."""
        downloader = MSDDownloader(target_dir=tmp_path)
        content = b"valid_dataset_content"
        valid_sha = hashlib.sha256(content).hexdigest()

        spec = DatasetFileSpec(
            relative_path="data/test_part.dat",
            download_url="http://example.com/test",
            size_bytes=len(content),
            sha256=valid_sha,
        )

        # Initially missing
        assert downloader.is_cached_valid(spec) is False

        # Create valid file
        dest = tmp_path / spec.relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        assert downloader.is_cached_valid(spec) is True

        # Corrupt file content
        dest.write_bytes(b"corrupted_content_diff_hash")
        assert downloader.is_cached_valid(spec) is False
