"""
Empirical Adversarial Stress Test Suite for Milestone M2
Target Modules:
- drywall_detection.data.downloader
- drywall_detection.data.preparer
- drywall_detection.data.qc
- drywall_detection.datasets.unified_format
"""

from __future__ import annotations
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch
import urllib.error
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from PIL import Image
import shapely
import shapely.wkt
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, Point, LineString

# Target imports
from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
)
from drywall_detection.data.downloader import (
    MSDDownloader,
    DatasetFileSpec,
    ChecksumMismatchError,
    DiskSpaceSafetyError,
    compute_file_sha256,
    EXIT_CODE_SUCCESS,
    EXIT_CODE_DISK_SAFETY_VIOLATION,
    EXIT_CODE_CHECKSUM_MISMATCH,
)
from drywall_detection.utils.hardware import check_disk_safety
from drywall_detection.data.preparer import (
    PreparationConfig,
    GeometryRasterizer,
    DrawingSanitizer,
    ParsedDrawing,
    UnifiedFloorPlan,
    DatasetPreparer,
    PALETTE_256,
)
from drywall_detection.datasets.unified_format import (
    UnifiedDatasetConfig,
    SlidingWindowTiler,
    UnifiedMask,
)
from drywall_detection.data.qc import (
    VisualQCGenerator,
    VisualQCPipeline,
)


def json_sanitize(val: Any) -> Any:
    """Converts numpy and non-standard types to pure python primitives."""
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    elif isinstance(val, (np.integer, int)):
        return int(val)
    elif isinstance(val, (np.floating, float)):
        return float(val)
    elif isinstance(val, np.ndarray):
        return val.tolist()
    elif isinstance(val, dict):
        return {str(k): json_sanitize(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple, set)):
        return [json_sanitize(x) for x in val]
    return str(val) if val is not None else None


class TestResultCollector:
    """Collects individual stress test case results for audit reporting."""
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def record(self, category: str, name: str, passed: bool, details: Dict[str, Any], notes: str = ""):
        self.results.append({
            "category": category,
            "test_name": name,
            "passed": bool(passed),
            "details": json_sanitize(details),
            "notes": str(notes),
        })
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {category} :: {name} - {notes}", flush=True)


collector = TestResultCollector()


# ==============================================================================
# SECTION 1: DOWNLOADER ADVERSARIAL STRESS TESTS
# ==============================================================================

def run_downloader_stress_tests() -> None:
    print("\n" + "=" * 70)
    print("RUNNING SECTION 1: DOWNLOADER ADVERSARIAL STRESS TESTS")
    print("=" * 70)

    # Test 1.1: Negative required_free_gb
    try:
        check_disk_safety(required_free_gb=-5.0)
        passed = False
        notes = "Failed: Expected ValueError for negative required_free_gb"
    except ValueError as e:
        passed = True
        notes = f"Correctly raised ValueError: {e}"
    except Exception as e:
        passed = False
        notes = f"Unexpected exception: {type(e).__name__}: {e}"
    collector.record("Downloader", "test_disk_safety_negative_required_gb", passed, {}, notes)

    # Test 1.2: Negative required_gb keyword alias
    try:
        check_disk_safety(required_gb=-0.001)
        passed = False
        notes = "Failed: Expected ValueError for negative required_gb alias"
    except ValueError as e:
        passed = True
        notes = f"Correctly raised ValueError: {e}"
    collector.record("Downloader", "test_disk_safety_negative_required_gb_alias", passed, {}, notes)

    # Test 1.3: required_free_gb exceeding available disk (e.g., 50 million GB)
    is_safe, free_gb, msg = check_disk_safety(required_free_gb=50_000_000.0)
    passed = (not is_safe) and ("REJECTED" in msg) and (free_gb >= 0)
    collector.record(
        "Downloader",
        "test_disk_safety_exceeding_available",
        passed,
        {"is_safe": is_safe, "free_gb": free_gb, "msg": msg},
        f"Headroom rejection verified: is_safe={is_safe}, msg='{msg[:60]}...'",
    )

    # Test 1.4: Large download threshold (> 10 GB) pre-flight enforcement
    with tempfile.TemporaryDirectory() as tmp_dir:
        spec_11gb = DatasetFileSpec(
            relative_path="huge.parquet",
            download_url="https://example.com/huge.parquet",
            size_bytes=11 * (1024 ** 3),  # 11 GB
            sha256="0" * 64,
        )
        # Without allow_large_downloads
        dl_strict = MSDDownloader(target_dir=tmp_dir, allow_large_downloads=False)
        is_safe, free_gb, msg = dl_strict.preflight_disk_check([spec_11gb])
        passed_strict = (not is_safe) and ("exceeds the 10.0 GB mandatory notification limit" in msg)

        # With allow_large_downloads
        dl_allow = MSDDownloader(target_dir=tmp_dir, allow_large_downloads=True)
        is_safe_allow, free_gb_allow, msg_allow = dl_allow.preflight_disk_check([spec_11gb])
        # It should pass preflight check if disk has at least 11 + 5 = 16 GB free
        passed_allow = (is_safe_allow if free_gb_allow >= 16.0 else not is_safe_allow)

        passed = passed_strict and (is_safe_allow == (free_gb_allow >= 16.0))
        collector.record(
            "Downloader",
            "test_large_download_10gb_threshold",
            passed,
            {"passed_strict": passed_strict, "passed_allow": passed_allow, "free_gb": free_gb_allow},
            f"10 GB threshold enforced: strict rejected={not is_safe}, allow_passed={is_safe_allow}",
        )

    # Test 1.5: SHA-256 Checksum Mismatch: corrupt .part file deleted and never promoted
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        fake_content = b"Corrupt payload bytes that do not match expected hash"
        expected_sha = "a" * 64  # deliberate mismatch
        spec = DatasetFileSpec(
            relative_path="test_file.parquet",
            download_url="https://example.com/test_file.parquet",
            size_bytes=len(fake_content),
            sha256=expected_sha,
        )
        dl = MSDDownloader(target_dir=dest_dir, max_retries=1)

        # Mock urllib.request.urlopen returning fake_content
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read = MagicMock(side_effect=[fake_content, b""])
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            try:
                dl.download_file(spec)
                passed = False
                notes = "Failed: Expected ChecksumMismatchError but download succeeded without error"
            except ChecksumMismatchError as e:
                dest_file = dest_dir / spec.relative_path
                part_file = dest_file.with_name(dest_file.name + ".part")
                passed = (not dest_file.exists()) and (not part_file.exists())
                notes = f"Verified: ChecksumMismatchError raised, dest.exists={dest_file.exists()}, part.exists={part_file.exists()}"
            except RuntimeError as e:
                # Swallowed exception finding
                dest_file = dest_dir / spec.relative_path
                part_file = dest_file.with_name(dest_file.name + ".part")
                # Even though .part was deleted and dest was not created, ChecksumMismatchError was swallowed into RuntimeError
                passed = False
                notes = (
                    f"BUG DETECTED: ChecksumMismatchError swallowed by generic 'except Exception' and raised as RuntimeError. "
                    f"Corrupt .part was deleted={not part_file.exists()}, dest not promoted={not dest_file.exists()}."
                )
            except Exception as e:
                passed = False
                notes = f"Unexpected exception: {type(e).__name__}: {e}"

        collector.record("Downloader", "test_sha256_mismatch_corrupt_part_deleted", passed, {}, notes)

    # Test 1.6: Pre-existing corrupt file in destination detected by is_cached_valid
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        spec = DatasetFileSpec(
            relative_path="file.parquet",
            download_url="https://example.com/file.parquet",
            size_bytes=100,
            sha256=hashlib.sha256(b"correct data" * 10).hexdigest(),
        )
        dest_path = dest_dir / spec.relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Write corrupted file (wrong length)
        dest_path.write_bytes(b"corrupt")
        dl = MSDDownloader(target_dir=dest_dir)
        valid_size_mismatch = dl.is_cached_valid(spec)

        # Write wrong content with exact length (100 bytes)
        dest_path.write_bytes(b"x" * 100)
        valid_hash_mismatch = dl.is_cached_valid(spec)

        passed = (not valid_size_mismatch) and (not valid_hash_mismatch)
        collector.record(
            "Downloader",
            "test_pre_existing_corrupt_file_cache_rejection",
            passed,
            {"valid_size_mismatch": valid_size_mismatch, "valid_hash_mismatch": valid_hash_mismatch},
            f"Pre-existing corrupt file rejected on size ({valid_size_mismatch}) and hash ({valid_hash_mismatch})",
        )

    # Test 1.7: HTTP Fatal Error (403 Forbidden / 404 Not Found): halts immediately, cleans up .part, no retry loop
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        spec = DatasetFileSpec(
            relative_path="forbidden.parquet",
            download_url="https://example.com/forbidden.parquet",
            size_bytes=1024,
            sha256="b" * 64,
        )
        dl = MSDDownloader(target_dir=dest_dir, max_retries=5)
        http_403 = urllib.error.HTTPError(spec.download_url, 403, "Forbidden", {}, None)

        attempt_count = 0
        def mock_urlopen_403(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise http_403

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_403):
            try:
                dl.download_file(spec)
                passed = False
                notes = "Failed: Expected HTTPError 403"
            except urllib.error.HTTPError as e:
                dest_file = dest_dir / spec.relative_path
                part_file = dest_file.with_name(dest_file.name + ".part")
                # Attempt count must be exactly 1: fatal error halts immediately!
                passed = (e.code == 403) and (attempt_count == 1) and (not part_file.exists())
                notes = f"HTTP 403 halted immediately: attempts={attempt_count}, part_exists={part_file.exists()}"
            except Exception as e:
                passed = False
                notes = f"Unexpected exception: {type(e).__name__}: {e}"

        collector.record("Downloader", "test_http_fatal_403_immediate_halt", passed, {}, notes)

    # Test 1.8: HTTP Transient Error (500 Internal Server Error): exponential backoff up to max_retries, clean halt
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        spec = DatasetFileSpec(
            relative_path="transient.parquet",
            download_url="https://example.com/transient.parquet",
            size_bytes=1024,
            sha256="c" * 64,
        )
        dl = MSDDownloader(target_dir=dest_dir, max_retries=3)
        http_500 = urllib.error.HTTPError(spec.download_url, 500, "Internal Server Error", {}, None)

        attempts = 0
        def mock_urlopen_500(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            raise http_500

        sleep_calls: List[float] = []
        def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_500):
            with patch("time.sleep", side_effect=mock_sleep):
                try:
                    dl.download_file(spec)
                    passed = False
                    notes = "Failed: Expected RuntimeError after max_retries"
                except RuntimeError as e:
                    dest_file = dest_dir / spec.relative_path
                    part_file = dest_file.with_name(dest_file.name + ".part")
                    # Should attempt 3 times, sleep 2 times (after attempt 1 and attempt 2)
                    passed = (
                        (attempts == 3)
                        and (len(sleep_calls) == 2)
                        and (sleep_calls[1] > sleep_calls[0])  # exponential growth
                        and (not part_file.exists())
                        and (not dest_file.exists())
                    )
                    notes = f"Retried {attempts} times with backoffs {[round(s, 2) for s in sleep_calls]}, .part deleted={not part_file.exists()}"
                except Exception as e:
                    passed = False
                    notes = f"Unexpected exception: {type(e).__name__}: {e}"

        collector.record("Downloader", "test_http_transient_500_exponential_backoff", passed, {}, notes)

    # Test 1.9: Simulated Network Disconnect / Socket Timeout
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        spec = DatasetFileSpec(
            relative_path="timeout.parquet",
            download_url="https://example.com/timeout.parquet",
            size_bytes=512,
            sha256="d" * 64,
        )
        dl = MSDDownloader(target_dir=dest_dir, max_retries=2)
        timeout_err = urllib.error.URLError("Connection timed out")

        t_attempts = 0
        def mock_urlopen_timeout(*args, **kwargs):
            nonlocal t_attempts
            t_attempts += 1
            raise timeout_err

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_timeout):
            with patch("time.sleep", return_value=None):
                try:
                    dl.download_file(spec)
                    passed = False
                    notes = "Failed: Expected RuntimeError on network timeout"
                except RuntimeError as e:
                    part_file = (dest_dir / spec.relative_path).with_suffix(".parquet.part")
                    passed = (t_attempts == 2) and (not part_file.exists())
                    notes = f"Handled socket timeout after {t_attempts} attempts, part cleaned up={not part_file.exists()}"
                except Exception as e:
                    passed = False
                    notes = f"Unexpected exception: {e}"

        collector.record("Downloader", "test_network_disconnect_socket_timeout", passed, {}, notes)

    # Test 1.10: Resumable Transfers with HTTP Range (Partial Download Recovery)
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_dir = Path(tmp_dir)
        full_content = b"The quick brown fox jumps over the lazy dog. Architectural Wall Segmentation Data."
        expected_sha = hashlib.sha256(full_content).hexdigest()
        spec = DatasetFileSpec(
            relative_path="resumable.parquet",
            download_url="https://example.com/resumable.parquet",
            size_bytes=len(full_content),
            sha256=expected_sha,
        )
        dl = MSDDownloader(target_dir=dest_dir, max_retries=3)

        # Pre-stage a partial .part file with first 20 bytes
        dest_file = dest_dir / spec.relative_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        part_file = dest_file.with_name(dest_file.name + ".part")
        part_file.write_bytes(full_content[:20])

        # Server returns remaining bytes with HTTP 206
        mock_resp_206 = MagicMock()
        mock_resp_206.status = 206
        mock_resp_206.read = MagicMock(side_effect=[full_content[20:], b""])
        mock_resp_206.__enter__.return_value = mock_resp_206

        def mock_urlopen_range(req, *args, **kwargs):
            range_hdr = req.get_header("Range")
            assert range_hdr == "bytes=20-", f"Expected Range: bytes=20-, got {range_hdr}"
            return mock_resp_206

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_range):
            dest_res, was_cached, transferred = dl.download_file(spec)
            passed = (
                (dest_res.is_file())
                and (dest_res.stat().st_size == len(full_content))
                and (dest_res.read_bytes() == full_content)
                and (not part_file.exists())
                and (transferred == len(full_content) - 20)
            )
            notes = f"Resumed from byte 20, transferred={transferred} bytes, verified SHA-256 match"

        collector.record("Downloader", "test_resumable_transfer_http_range_206", passed, {}, notes)


# ==============================================================================
# SECTION 2: PREPARER & RASTERIZER ADVERSARIAL STRESS TESTS
# ==============================================================================

def run_preparer_stress_tests() -> None:
    print("\n" + "=" * 70)
    print("RUNNING SECTION 2: PREPARER & RASTERIZER ADVERSARIAL STRESS TESTS")
    print("=" * 70)

    cfg = PreparationConfig(target_width=512, target_height=512, default_wall_class=CLASS_UNCERTAIN)
    sanitizer = DrawingSanitizer(cfg)
    rasterizer = GeometryRasterizer(cfg)

    # Test 2.1: Self-intersecting bowtie polygon (make_valid repair)
    bowtie_wkt = "POLYGON((0 0, 10 10, 0 10, 10 0, 0 0))"
    polys = sanitizer.sanitize_polygon(bowtie_wkt)
    # Bowtie should be repaired via shapely.make_valid into 2 valid triangles
    passed_bowtie = (len(polys) == 2) and all(p.is_valid for p in polys) and all(p.area > 0 for p in polys)
    # Rasterize repaired triangles
    bin_m, mul_m = rasterizer.rasterize_polygons(polys, (0, 0, 10, 10), target_class=CLASS_DRYWALL)
    wall_px = int(np.sum(bin_m > 0))
    passed = passed_bowtie and (wall_px > 0) and np.array_equal(bin_m > 0, mul_m == CLASS_DRYWALL)
    collector.record(
        "Preparer",
        "test_pathological_bowtie_polygon_repair",
        passed,
        {"num_polygons": len(polys), "wall_pixels": wall_px},
        f"Self-intersecting bowtie repaired into {len(polys)} valid polygons, rasterized to {wall_px} px",
    )

    # Test 2.2: Zero-area slivers and degenerate lines (filtered out)
    collinear_wkt = "POLYGON((0 0, 10 0, 10 0, 0 0, 0 0))"
    micro_sliver_wkt = "POLYGON((0 0, 10 0, 10 1e-6, 0 1e-6, 0 0))"  # area = 1e-5 < 1e-4 min_polygon_area
    polys_collinear = sanitizer.sanitize_polygon(collinear_wkt)
    polys_sliver = sanitizer.sanitize_polygon(micro_sliver_wkt)
    passed = (len(polys_collinear) == 0) and (len(polys_sliver) == 0)
    collector.record(
        "Preparer",
        "test_zero_area_slivers_and_degenerate_lines",
        passed,
        {"collinear_count": len(polys_collinear), "sliver_count": len(polys_sliver)},
        f"Degenerate polygons cleanly filtered: collinear={len(polys_collinear)}, sliver={len(polys_sliver)}",
    )

    # Test 2.3: Inverted coordinate polygons (Clockwise winding)
    cw_polygon_wkt = "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"
    polys_cw = sanitizer.sanitize_polygon(cw_polygon_wkt)
    bin_cw, mul_cw = rasterizer.rasterize_polygons(polys_cw, (0, 0, 10, 10), target_class=CLASS_DRYWALL)
    px_cw = int(np.sum(bin_cw > 0))
    passed = (len(polys_cw) == 1) and (px_cw > 1000)
    collector.record(
        "Preparer",
        "test_inverted_clockwise_polygon",
        passed,
        {"num_polygons": len(polys_cw), "wall_pixels": px_cw},
        f"Clockwise polygon handled cleanly: {len(polys_cw)} poly, {px_cw} px",
    )

    # Test 2.4: NaN and Inf coordinates in WKT (rejected cleanly without crashing)
    nan_wkt = "POLYGON((NaN 0, 10 0, 10 10, 0 10, NaN 0))"
    inf_wkt = "POLYGON((Inf 0, 10 0, 10 10, 0 10, Inf 0))"
    neg_inf_wkt = "POLYGON((-Inf 0, 10 0, 10 10, 0 10, -Inf 0))"
    polys_nan = sanitizer.sanitize_polygon(nan_wkt)
    polys_inf = sanitizer.sanitize_polygon(inf_wkt)
    polys_neginf = sanitizer.sanitize_polygon(neg_inf_wkt)
    passed_sanitizer = (len(polys_nan) == 0) and (len(polys_inf) == 0) and (len(polys_neginf) == 0)

    # Also test transform_coords_to_pixel with NaN and Inf coordinates directly
    affine_params = rasterizer.compute_affine_parameters((0, 0, 100, 100))
    pts = rasterizer.transform_coords_to_pixel(
        [(float("nan"), 0.0), (float("inf"), 10.0), (float("-inf"), 20.0), (50.0, 50.0), (60.0, 60.0), (50.0, 60.0)],
        affine_params,
    )
    # The 3 non-finite points must be skipped, leaving 3 valid points
    passed_transform = (len(pts) == 3)
    passed = passed_sanitizer and passed_transform
    collector.record(
        "Preparer",
        "test_nan_inf_coordinates_rejection",
        passed,
        {"nan_polys": len(polys_nan), "inf_polys": len(polys_inf), "filtered_pts": len(pts)},
        f"NaN/Inf WKT inputs safely rejected without crash (polys=0, valid pts retained={len(pts)})",
    )

    # Test 2.5: Nested donut holes and interior evacuation
    # Exterior 0..100, Hole 1: 20..40, Hole 2: 60..80
    donut_wkt = "POLYGON((0 0, 100 0, 100 100, 0 100, 0 0), (20 20, 40 20, 40 40, 20 40, 20 20), (60 60, 80 60, 80 80, 60 80, 60 60))"
    polys_donut = sanitizer.sanitize_polygon(donut_wkt)
    passed_donut_san = (len(polys_donut) == 1) and (len(polys_donut[0].interiors) == 2)

    bin_donut, mul_donut = rasterizer.rasterize_polygons(polys_donut, (0, 0, 100, 100), target_class=CLASS_DRYWALL)
    # Check that hole locations are evacuated to 0 in both binary and multiclass masks
    # Compute center of Hole 1 and Hole 2 in pixel coordinates
    scale, pad_x, pad_y, min_x_pad, min_y_pad = affine_params
    h1_px = rasterizer.transform_coords_to_pixel([(30.0, 30.0)], affine_params)[0][0]
    h2_px = rasterizer.transform_coords_to_pixel([(70.0, 70.0)], affine_params)[0][0]
    ext_px = rasterizer.transform_coords_to_pixel([(10.0, 10.0)], affine_params)[0][0]

    hole1_val = bin_donut[h1_px[1], h1_px[0]]
    hole2_val = bin_donut[h2_px[1], h2_px[0]]
    ext_val = bin_donut[ext_px[1], ext_px[0]]

    passed_evac = (hole1_val == 0) and (hole2_val == 0) and (ext_val == 1)
    passed = passed_donut_san and passed_evac
    collector.record(
        "Preparer",
        "test_nested_donut_holes_evacuation",
        passed,
        {"interiors": len(polys_donut[0].interiors) if polys_donut else 0, "h1_val": int(hole1_val), "h2_val": int(hole2_val), "ext_val": int(ext_val)},
        f"2 interior donut holes evacuated to 0: hole1={hole1_val}, hole2={hole2_val}, exterior={ext_val}",
    )

    # Test 2.6: Empty geometries and malformed inputs
    malformed_inputs = [
        "GEOMETRYCOLLECTION EMPTY",
        "POLYGON EMPTY",
        "LINESTRING EMPTY",
        "POINT(10 10)",
        "LINESTRING(0 0, 10 10)",
        "NOT_A_WKT_STRING",
        "POLYGON((0 0, 10 0))",  # unclosed, 2 points
        "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0",  # unbalanced parentheses
        "",
        None,
        12345,
    ]
    all_empty_clean = True
    for item in malformed_inputs:
        res = sanitizer.sanitize_polygon(item)
        if len(res) != 0:
            all_empty_clean = False
            break

    collector.record(
        "Preparer",
        "test_empty_and_malformed_inputs",
        all_empty_clean,
        {"tested_count": len(malformed_inputs)},
        f"All {len(malformed_inputs)} empty/malformed inputs returned [] without crash",
    )

    # Test 2.7: Degenerate canvas bounds and extreme coordinates
    # Single point bounds (span_x = 0, span_y = 0)
    params_single_pt = rasterizer.compute_affine_parameters((5.0, 5.0, 5.0, 5.0))
    scale_sp = params_single_pt[0]
    no_div_zero = math.isfinite(scale_sp) and scale_sp > 0

    # Extreme astronomical coordinates (1e8 pt)
    params_extreme = rasterizer.compute_affine_parameters((1e8, 1e8, 1e8 + 100, 1e8 + 100))
    coords_extreme = rasterizer.transform_coords_to_pixel([(1e8 + 50, 1e8 + 50)], params_extreme)
    extreme_clamped = (
        len(coords_extreme) == 1
        and (0 <= coords_extreme[0][0][0] < 512)
        and (0 <= coords_extreme[0][0][1] < 512)
    )
    passed = no_div_zero and extreme_clamped
    collector.record(
        "Preparer",
        "test_extreme_bounds_and_no_zero_division",
        passed,
        {"scale_sp": scale_sp, "extreme_pt": coords_extreme[0][0].tolist() if extreme_clamped else []},
        f"Division-by-zero protected (scale={scale_sp:.2f}), extreme coords clamped into [0, 511]",
    )

    # Test 2.8: Blank floor plan filtering in DatasetPreparer
    # Create synthetic parsed drawings: 4 with walls, 4 blank drawings (empty polygons)
    with tempfile.TemporaryDirectory() as tmp_prep_dir:
        prep_dir = Path(tmp_prep_dir)
        raw_json = prep_dir / "drawings.json"
        test_drawings_data = {
            "drawings": [
                # 4 drawings with real walls
                {"drawing_id": f"wall_{i}", "site_id": f"site_{i}", "wall_wkts": ["POLYGON((1 1, 10 1, 10 10, 1 10, 1 1))"]}
                for i in range(4)
            ] + [
                # 4 blank drawings with NO walls
                {"drawing_id": f"blank_{j}", "site_id": f"site_{j+4}", "wall_wkts": []}
                for j in range(4)
            ]
        }
        with open(raw_json, "w") as f:
            json.dump(test_drawings_data, f)

        # Ingest with filter_blank_drawings=True
        prep_config = PreparationConfig(
            raw_dir=prep_dir,
            output_dir=prep_dir / "processed",
            target_width=256,
            target_height=256,
            min_wall_pixels=50,
            filter_blank_drawings=True,
            split_after_prep=False,
        )
        preparer = DatasetPreparer(prep_config)
        manifest = preparer.prepare_dataset()

        # Invariant: blank drawings must be 100% filtered out
        prep_ids = [d["drawing_id"] for d in manifest["drawings"]]
        has_blanks = any("blank" in d_id for d_id in prep_ids)
        passed_filter = (not has_blanks) and (len(prep_ids) == 4)

        collector.record(
            "Preparer",
            "test_filter_blank_drawings_density_threshold",
            passed_filter,
            {"total_prepared": len(prep_ids), "has_blanks": has_blanks},
            f"filter_blank_drawings eliminated 100% of blank plans: {len(prep_ids)} wall drawings kept, 0 blank kept",
        )

        # Test 2.8b: Adversarial test of max_hard_negative_ratio in DatasetPreparer when filter_blank_drawings=False
        prep_config_unfiltered = PreparationConfig(
            raw_dir=prep_dir,
            output_dir=prep_dir / "processed_unfiltered",
            target_width=256,
            target_height=256,
            min_wall_pixels=50,
            filter_blank_drawings=False,
            max_hard_negative_ratio=0.15,
            split_after_prep=False,
        )
        preparer_unfiltered = DatasetPreparer(prep_config_unfiltered)
        manifest_unfiltered = preparer_unfiltered.prepare_dataset()
        blank_drawings = [d for d in manifest_unfiltered["drawings"] if d["wall_pixel_count"] < 50]
        total_drawings = len(manifest_unfiltered["drawings"])
        drawing_hn_ratio = (len(blank_drawings) / total_drawings) if total_drawings > 0 else 0.0

        # Does DatasetPreparer cap hard negative drawings when filter_blank_drawings=False?
        # If drawing_hn_ratio > 0.15, it failed to enforce max_hard_negative_ratio!
        passed_prep_cap = (drawing_hn_ratio <= 0.15)
        collector.record(
            "Preparer",
            "test_preparer_drawing_level_hard_negative_capping",
            passed_prep_cap,
            {"total_drawings": total_drawings, "blank_drawings": len(blank_drawings), "drawing_hn_ratio": drawing_hn_ratio},
            f"DatasetPreparer drawing-level HN cap when filter_blank_drawings=False: blanks={len(blank_drawings)}/{total_drawings} ({drawing_hn_ratio:.1%}, cap=15%)",
        )

    # Test 2.9: Hard Negative Capping at <= 15% in UnifiedDatasetTiler
    # Adversarial attack: Flood tiler with 1 drawing containing 4 wall tiles and 100 candidate hard negative tiles
    tiler_cfg = UnifiedDatasetConfig(
        tile_size=128,
        overlap_ratio=0.0,
        max_hard_negative_ratio=0.15,
        min_variance_threshold=5.0,
        nominal_hard_negatives_zero_walls=0,
    )
    tiler = SlidingWindowTiler(tiler_cfg)

    # Construct an image of 10x10 grid of 128x128 tiles = 1280 x 1280 px
    # Put walls on 4 tiles, complex linework (hard negatives) on all other 96 tiles
    canvas_img = np.full((1280, 1280, 3), 255, dtype=np.uint8)
    # Add CAD lines across entire image so variance > min_variance_threshold (not pure blank)
    for y in range(0, 1280, 16):
        cv2.line(canvas_img, (0, y), (1280, y), (50, 50, 50), 1)

    # Put walls only in top-left 2x2 tiles (4 tiles total)
    mask_arr = np.zeros((1280, 1280), dtype=np.uint8)
    mask_arr[10:240, 10:240] = CLASS_DRYWALL
    u_mask = UnifiedMask(mask_arr)

    tiles = tiler.tile_drawing(
        image=canvas_img,
        mask=u_mask,
        drawing_id="adversarial_hn_flood",
        dataset_source="test",
        split="train",
    )

    n_wall_tiles = sum(1 for _, _, m in tiles if m.has_walls)
    n_hn_tiles = sum(1 for _, _, m in tiles if m.is_hard_negative)
    total_retained = len(tiles)
    hn_ratio = (n_hn_tiles / total_retained) if total_retained > 0 else 0.0

    # Quota formula: quota_float = num_walls * ratio / (1 - ratio) = 4 * 0.15 / 0.85 = 0.705 -> ceil = 1
    # Thus exactly 1 hard negative tile should be retained out of 96 candidates!
    # And hn_ratio = 1 / 5 = 20% max (due to discrete ceil on small numbers), but let's check ratio against quota cap:
    passed_hn = (n_hn_tiles <= 1) and (n_wall_tiles == 4)
    collector.record(
        "Preparer",
        "test_hard_negatives_capped_against_flooding",
        passed_hn,
        {"num_wall_tiles": n_wall_tiles, "num_hn_retained": n_hn_tiles, "total_retained": total_retained, "ratio": hn_ratio},
        f"From 96 candidate hard negatives, tiler strictly capped retention to {n_hn_tiles} tiles (ratio={hn_ratio:.1%})",
    )

    # Test 2.10: Pure blank white drawings (zero variance, high mean) 100% discarded
    pure_white_img = np.full((512, 512, 3), 255, dtype=np.uint8)
    pure_blank_mask = UnifiedMask(np.zeros((512, 512), dtype=np.uint8))
    white_tiles = tiler.tile_drawing(
        image=pure_white_img,
        mask=pure_blank_mask,
        drawing_id="pure_blank_drawing",
        dataset_source="test",
        split="train",
    )
    passed_white = (len(white_tiles) == 0)
    collector.record(
        "Preparer",
        "test_pure_blank_white_drawings_100pct_discarded",
        passed_white,
        {"retained_tiles": len(white_tiles)},
        f"Pure blank white floor plans are 100% discarded: retained={len(white_tiles)} tiles",
    )

    # Test 2.11: Multiclass mask indexed PNG palette conformity
    test_mask = np.zeros((100, 100), dtype=np.uint8)
    test_mask[10:30, 10:30] = CLASS_DRYWALL
    test_mask[40:60, 40:60] = CLASS_NON_DRYWALL
    test_mask[70:90, 70:90] = CLASS_UNCERTAIN

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf_path = Path(tf.name)
    try:
        p_img = Image.fromarray(test_mask, mode="P")
        p_img.putpalette(PALETTE_256)
        p_img.save(tf_path)

        with Image.open(tf_path) as reloaded:
            passed_mode = (reloaded.mode == "P")
            palette = reloaded.getpalette()[:12]
            # Verify palette matches PALETTE_256 first 12 ints
            passed_pal = (palette == PALETTE_256[:12])
            arr = np.array(reloaded)
            passed_vals = set(np.unique(arr)).issubset({0, 1, 2, 3})
            passed = passed_mode and passed_pal and passed_vals
    finally:
        tf_path.unlink(missing_ok=True)

    collector.record(
        "Preparer",
        "test_multiclass_mask_palette_conformity",
        passed,
        {"mode": reloaded.mode, "unique_vals": list(map(int, np.unique(arr)))},
        f"Mode 'P' indexed PNG validated: classes={list(np.unique(arr))}, palette matching={passed_pal}",
    )


# ==============================================================================
# SECTION 3: VISUAL QC ADVERSARIAL STRESS TESTS
# ==============================================================================

def run_qc_stress_tests() -> None:
    print("\n" + "=" * 70)
    print("RUNNING SECTION 3: VISUAL QC ADVERSARIAL STRESS TESTS")
    print("=" * 70)

    gen = VisualQCGenerator(alpha=0.4)

    # Test 3.1: Resolution mismatch between image and mask auto-resizes cleanly
    img_large = np.full((1024, 1024, 3), 240, dtype=np.uint8)
    mask_small = np.zeros((256, 256), dtype=np.uint8)
    mask_small[50:100, 50:100] = CLASS_DRYWALL

    triplet = gen.create_triplet(img_large, mask_small, {"sample_id": "test_mismatch"})
    # Result should have banner (40px) + mask height (256px) = 296px, and width = 3 * 256 = 768px
    expected_h = 256 + 40
    expected_w = 256 * 3
    passed = (triplet.shape == (expected_h, expected_w, 3))
    collector.record(
        "QC",
        "test_qc_resolution_mismatch_auto_resize",
        passed,
        {"shape": list(triplet.shape), "expected": [expected_h, expected_w, 3]},
        f"Resolution mismatch gracefully unified: resulting triplet shape={triplet.shape}",
    )

    # Test 3.2: Translucent overlay alpha blending range and values
    overlay = gen.render_overlay(img_large[:256, :256], mask_small)
    # The drywall region (50..100) must be blended with Green (BGR: 83, 200, 0)
    # Background (outside 50..100) should be untouched 240
    bg_sample = overlay[10, 10]
    wall_sample = overlay[60, 60]
    passed_alpha = np.all(bg_sample == 240) and not np.all(wall_sample == 240)
    collector.record(
        "QC",
        "test_qc_overlay_alpha_blending",
        passed_alpha,
        {"bg_sample": bg_sample.tolist(), "wall_sample": wall_sample.tolist()},
        f"Translucent overlay verified: background untouched={np.all(bg_sample == 240)}, wall blended={wall_sample.tolist()}",
    )


# ==============================================================================
# MAIN RUNNER & JSON EXPORT
# ==============================================================================

def main() -> int:
    start_time = time.time()
    print("=" * 70)
    print("M2 EMPIRICAL ADVERSARIAL STRESS HARNESS")
    print("=" * 70)

    run_downloader_stress_tests()
    run_preparer_stress_tests()
    run_qc_stress_tests()

    elapsed = time.time() - start_time
    total_tests = len(collector.results)
    passed_tests = sum(1 for r in collector.results if r["passed"])
    failed_tests = total_tests - passed_tests

    print("\n" + "=" * 70)
    print(f"M2 STRESS TEST SUITE EXECUTION SUMMARY: {passed_tests}/{total_tests} PASSED in {elapsed:.2f}s")
    print("=" * 70)

    # Export results JSON to state folder
    state_dir = Path(r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m2_2")
    state_dir.mkdir(parents=True, exist_ok=True)
    out_file = state_dir / "stress_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "all_passed": (failed_tests == 0),
            "elapsed_seconds": round(elapsed, 2),
            "results": collector.results,
        }, f, indent=2)

    print(f"Detailed results exported to: {out_file}")
    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
