"""
Empirical stress harness for drywall_detection.utils.coords.
Runs intensive statistical stress tests, chained roundtrips, degenerate geometries,
and logs empirical metrics.
"""

from __future__ import annotations
import json
import math
import sys
import time
import numpy as np
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.validation import explain_validity

from drywall_detection.config import (
    BASE_DPI,
    DEFAULT_DPI,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_ROTATION_DEG,
)
from drywall_detection.utils.coords import (
    get_forward_matrix,
    get_inverse_matrix,
    pdf_bbox_to_pixel,
    pdf_geom_to_pixel,
    pdf_points_to_pixel,
    pdf_to_pixel,
    pixel_bbox_to_pdf,
    pixel_geom_to_pdf,
    pixel_points_to_pdf,
    pixel_to_pdf,
)


def run_10000_chained_roundtrips() -> dict:
    """Measures drift over 10,000 continuous chained roundtrips."""
    print("--- Running 10,000 Chained Roundtrips ---")
    test_points = [
        ("partition_tag_coord", 772.44, 1094.52),
        ("origin", 0.0, 0.0),
        ("page_max", 1728.0, 2592.0),
        ("center", 864.0, 1296.0),
        ("arbitrary_float", 123.45678901234, 987.65432109876),
        ("extreme_coord", 10_000_000.5, 25_000_000.25),
        ("negative_coord", -500_000.75, -1_200_000.125),
    ]

    results = {}
    dpis = [72, 150, 200, 300]
    rotations = [0, 90, 180, 270]

    for pt_name, orig_x, orig_y in test_points:
        pt_results = {}
        for rot in rotations:
            for dpi in dpis:
                cur_x, cur_y = orig_x, orig_y
                max_drift_x = 0.0
                max_drift_y = 0.0

                start_t = time.perf_counter()
                for _ in range(10_000):
                    px, py = pdf_to_pixel(cur_x, cur_y, dpi=dpi, rotation=rot)
                    cur_x, cur_y = pixel_to_pdf(px, py, dpi=dpi, rotation=rot)
                    dx = abs(cur_x - orig_x)
                    dy = abs(cur_y - orig_y)
                    if dx > max_drift_x:
                        max_drift_x = dx
                    if dy > max_drift_y:
                        max_drift_y = dy
                elapsed = time.perf_counter() - start_t

                final_dx = abs(cur_x - orig_x)
                final_dy = abs(cur_y - orig_y)

                key = f"rot{rot}_dpi{dpi}"
                pt_results[key] = {
                    "max_drift_x": max_drift_x,
                    "max_drift_y": max_drift_y,
                    "final_drift_x": final_dx,
                    "final_drift_y": final_dy,
                    "elapsed_sec": round(elapsed, 4),
                    "passed_tolerance_1e_4": (max_drift_x < 1e-4 and max_drift_y < 1e-4),
                }
        results[pt_name] = pt_results

    return results


def run_large_scale_vectorized_test() -> dict:
    """Tests 100,000 points vectorized roundtrip error distribution."""
    print("--- Running 100,000 Vectorized Random Points ---")
    np.random.seed(42)
    pts = np.random.uniform(
        low=[-10_000.0, -10_000.0],
        high=[20_000.0, 30_000.0],
        size=(100_000, 2),
    )

    results = {}
    for rot in [0, 90, 180, 270]:
        t0 = time.perf_counter()
        pxs = pdf_points_to_pixel(pts, dpi=150, rotation=rot)
        rpts = pixel_points_to_pdf(pxs, dpi=150, rotation=rot)
        elapsed = time.perf_counter() - t0

        diffs = np.abs(pts - rpts)
        max_err = float(np.max(diffs))
        mean_err = float(np.mean(diffs))
        std_err = float(np.std(diffs))
        p99_err = float(np.percentile(diffs, 99))

        results[f"rot_{rot}"] = {
            "max_err_pt": max_err,
            "mean_err_pt": mean_err,
            "std_err_pt": std_err,
            "p99_err_pt": p99_err,
            "throughput_pts_per_sec": round(100_000 / elapsed, 1),
            "passed": max_err < 1e-4,
        }
    return results


def run_degenerate_geometries_test() -> dict:
    """Stress tests on complex, degenerate, and malformed geometries."""
    print("--- Running Degenerate Geometries Suite ---")
    results = {}

    # 1. 100-hole polygon
    ext = [(0.0, 0.0), (2000.0, 0.0), (2000.0, 2000.0), (0.0, 2000.0)]
    holes = []
    for r in range(10):
        for c in range(10):
            x0 = 50.0 + c * 180.0
            y0 = 50.0 + r * 180.0
            holes.append([(x0, y0), (x0 + 40.0, y0), (x0 + 40.0, y0 + 40.0), (x0, y0 + 40.0)])
    p_100_holes = Polygon(shell=ext, holes=holes)
    p_px = pdf_geom_to_pixel(p_100_holes, dpi=150, rotation=90)
    p_rt = pixel_geom_to_pdf(p_px, dpi=150, rotation=90)
    results["100_holes"] = {
        "valid": p_rt.is_valid,
        "interiors_count": len(p_rt.interiors),
        "equals_exact": p_100_holes.equals_exact(p_rt, tolerance=1e-4),
        "area_diff": abs(p_100_holes.area - p_rt.area),
    }

    # 2. Bowtie self-intersecting polygon
    bowtie = Polygon([(0.0, 0.0), (200.0, 200.0), (0.0, 200.0), (200.0, 0.0), (0.0, 0.0)])
    b_px = pdf_geom_to_pixel(bowtie, dpi=150, rotation=90)
    b_rt = pixel_geom_to_pdf(b_px, dpi=150, rotation=90)
    results["bowtie_invalid"] = {
        "is_valid_before": bowtie.is_valid,
        "is_valid_after": b_rt.is_valid,
        "equals_exact": bowtie.equals_exact(b_rt, tolerance=1e-4),
    }

    # 3. Collinear zero area polygon
    collinear = Polygon([(0.0, 0.0), (500.0, 0.0), (1000.0, 0.0), (0.0, 0.0)])
    c_px = pdf_geom_to_pixel(collinear, dpi=150, rotation=90)
    c_rt = pixel_geom_to_pdf(c_px, dpi=150, rotation=90)
    results["collinear_zero_area"] = {
        "area_before": collinear.area,
        "area_after": c_rt.area,
        "crash": False,
    }

    # 4. Deeply nested donut in donut in donut (3 levels)
    # Shell: 0..600, Hole1: 100..500. Inside Hole1: Island1 150..450 with Hole2 200..400. Inside Hole2: Island2 250..350
    poly1 = Polygon(
        shell=[(0.0, 0.0), (600.0, 0.0), (600.0, 600.0), (0.0, 600.0)],
        holes=[[(100.0, 100.0), (500.0, 100.0), (500.0, 500.0), (100.0, 500.0)]],
    )
    poly2 = Polygon(
        shell=[(150.0, 150.0), (450.0, 150.0), (450.0, 450.0), (150.0, 450.0)],
        holes=[[(200.0, 200.0), (400.0, 200.0), (400.0, 400.0), (200.0, 400.0)]],
    )
    poly3 = Polygon(shell=[(250.0, 250.0), (350.0, 250.0), (350.0, 350.0), (250.0, 350.0)])
    mp_nested = MultiPolygon([poly1, poly2, poly3])
    mp_px = pdf_geom_to_pixel(mp_nested, dpi=150, rotation=90)
    mp_rt = pixel_geom_to_pdf(mp_px, dpi=150, rotation=90)
    results["deeply_nested_donuts"] = {
        "valid": mp_rt.is_valid,
        "geoms_count": len(mp_rt.geoms),
        "equals_exact": mp_nested.equals_exact(mp_rt, tolerance=1e-4),
    }

    # 5. Mixed GeometryCollection
    gc = GeometryCollection([
        Point(10.0, 20.0),
        LineString([(30.0, 40.0), (50.0, 60.0)]),
        LinearRing([(70.0, 80.0), (90.0, 80.0), (90.0, 100.0), (70.0, 80.0)]),
        Polygon([(110.0, 120.0), (130.0, 120.0), (130.0, 140.0), (110.0, 120.0)]),
    ])
    gc_px = pdf_geom_to_pixel(gc, dpi=150, rotation=90)
    gc_rt = pixel_geom_to_pdf(gc_px, dpi=150, rotation=90)
    results["mixed_geometry_collection"] = {
        "geoms_count": len(gc_rt.geoms),
        "equals_exact": gc.equals_exact(gc_rt, tolerance=1e-4),
    }

    return results


def run_exception_and_boundary_checks() -> dict:
    """Stress tests exception boundaries and illegal inputs."""
    print("--- Running Exception and Parameter Boundaries ---")
    results = {}

    exceptions_caught = 0
    total_checks = 0

    illegal_rotations = [45, -90, 360, 180.1, 91, None, "90"]
    for r in illegal_rotations:
        total_checks += 1
        try:
            pdf_to_pixel(100.0, 100.0, rotation=r)
        except (ValueError, TypeError):
            exceptions_caught += 1

    illegal_dpis = [0, -100, -0.1, None, "150"]
    for d in illegal_dpis:
        total_checks += 1
        try:
            pdf_to_pixel(100.0, 100.0, dpi=d)
        except (ValueError, TypeError):
            exceptions_caught += 1

    non_finites = [float("nan"), float("inf"), float("-inf")]
    for nf in non_finites:
        total_checks += 1
        try:
            pdf_to_pixel(nf, 100.0)
        except ValueError:
            exceptions_caught += 1

        total_checks += 1
        try:
            pixel_to_pdf(100.0, nf)
        except ValueError:
            exceptions_caught += 1

    results["total_illegal_checks"] = total_checks
    results["exceptions_caught"] = exceptions_caught
    results["all_exceptions_handled_properly"] = (exceptions_caught == total_checks)

    return results


if __name__ == "__main__":
    t_start = time.perf_counter()
    summary = {
        "chained_10k": run_10000_chained_roundtrips(),
        "vectorized_100k": run_large_scale_vectorized_test(),
        "degenerate_geometries": run_degenerate_geometries_test(),
        "exceptions_and_boundaries": run_exception_and_boundary_checks(),
        "total_runtime_seconds": round(time.perf_counter() - t_start, 2),
    }

    out_path = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m1_1\stress_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Stress test suite completed successfully in {summary['total_runtime_seconds']}s")
    print(f"Results written to: {out_path}")
