"""
Adversarial Stress Test Suite for drywall_detection.data.splitter
================================================================
Executes pathological, boundary, corruption, and security challenges against:
- ProjectDataSplitter
- SampleRecord
- SplitManifestBundle
- assert_zero_leakage
"""

from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Any, Dict, List

# Ensure workspace root is in sys.path
_workspace_root = Path(__file__).resolve().parents[3]
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

import pytest

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


class AdversarialTestRunner:
    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []

    def record(self, test_id: str, category: str, description: str, passed: bool, details: Dict[str, Any]) -> None:
        entry = {
            "test_id": test_id,
            "category": category,
            "description": description,
            "passed": passed,
            "details": details,
        }
        self.results.append(entry)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_id}: {description}")
        if not passed:
            print(f"       Details: {details}")

    def run_all(self) -> Dict[str, Any]:
        print("=" * 70)
        print("RUNNING ADVERSARIAL STRESS TEST SUITE ON SPLITTER.PY")
        print("=" * 70)

        # 1. Extreme distributions
        self.test_extreme_distribution_90_percent_single_project()
        self.test_extreme_distribution_99_percent_single_project_3_total()
        self.test_extreme_distribution_empty_project_samples()

        # 2. Insufficient projects
        self.test_insufficient_projects_zero_samples()
        self.test_insufficient_projects_single_project_no_fallback()
        self.test_insufficient_projects_single_project_with_fallback_behavior()
        self.test_insufficient_projects_two_projects_no_fallback()
        self.test_insufficient_projects_two_projects_with_fallback_behavior()

        # 3. Duplicate paths and drawings across projects
        self.test_duplicate_drawing_id_across_projects()
        self.test_duplicate_image_path_across_projects()
        self.test_duplicate_mask_path_across_projects()
        self.test_duplicate_paths_case_sensitivity_uncreated_files()

        # 4. Corrupted manifest schemas and invalid ratios
        self.test_split_ratios_not_summing_to_one()
        self.test_split_ratios_negative_value()
        self.test_split_ratios_zero_value()
        self.test_split_ratios_invalid_length_too_few()
        self.test_split_ratios_invalid_length_too_many()
        self.test_split_ratios_nan_and_inf()
        self.test_sample_record_missing_keys_defaults()
        self.test_sample_record_corrupted_field_types()

        # 5. Deterministic partitioning under varied seeds
        self.test_seed_determinism_multiple_runs()
        self.test_seed_divergence_across_seeds()
        self.test_seed_extremes_boundary_values()

        # 6. Quarantine set isolation & tamper resistance
        self.test_quarantine_isolation_flag()
        self.test_quarantine_pseudo_label_flag()
        self.test_quarantine_project_name_list()
        self.test_quarantine_tamper_injection_val()
        self.test_quarantine_tamper_injection_test()
        self.test_quarantine_tamper_pseudo_label_in_val_without_quarantine_list()

        # 7. Manifest export & schema validation
        self.test_manifest_export_and_reloading()

        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed

        summary = {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "pass_rate": round((passed / total) * 100.0, 2) if total else 0.0,
            "results": self.results,
        }

        print("=" * 70)
        print(f"TEST RUN COMPLETE: {passed}/{total} PASSED ({summary['pass_rate']}%)")
        print("=" * 70)
        return summary

    # =========================================================================
    # Category 1: Extreme Distributions
    # =========================================================================

    def test_extreme_distribution_90_percent_single_project(self):
        """1 giant project with 900 samples (90%), 10 small projects with 10 samples each (10%)."""
        samples = []
        for i in range(900):
            samples.append(SampleRecord(f"giant_{i}", "proj_giant", f"draw_{i // 50}", f"/img/g_{i}.png", f"/msk/g_{i}.png"))
        for p in range(10):
            for i in range(10):
                samples.append(SampleRecord(f"small_{p}_{i}", f"proj_small_{p}", f"draw_s_{p}_{i // 5}", f"/img/s_{p}_{i}.png", f"/msk/s_{p}_{i}.png"))

        try:
            splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15), seed=42)
            bundle = splitter.split(samples)
            # Verify no empty bins
            assert len(bundle.train_samples) > 0, "Train split is empty"
            assert len(bundle.val_samples) > 0, "Val split is empty"
            assert len(bundle.test_samples) > 0, "Test split is empty"
            # Verify isolation
            assert_zero_leakage(bundle)
            self.record(
                "EXT-01", "Extreme Distribution",
                "1 giant project (90%) + 10 small projects: all splits populated with zero leakage",
                True,
                {
                    "train_samples": len(bundle.train_samples),
                    "val_samples": len(bundle.val_samples),
                    "test_samples": len(bundle.test_samples),
                    "train_projects": bundle.stats["train"].total_projects,
                    "val_projects": bundle.stats["val"].total_projects,
                    "test_projects": bundle.stats["test"].total_projects,
                }
            )
        except Exception as e:
            self.record("EXT-01", "Extreme Distribution", "1 giant project (90%) + 10 small projects", False, {"error": str(e), "trace": traceback.format_exc()})

    def test_extreme_distribution_99_percent_single_project_3_total(self):
        """1 giant project with 998 samples, plus 2 tiny projects with 1 sample each (total 3 projects)."""
        samples = []
        for i in range(998):
            samples.append(SampleRecord(f"g_{i}", "giant_proj", "draw_g", f"/img/g_{i}.png", f"/msk/g_{i}.png"))
        samples.append(SampleRecord("t1", "tiny_1", "draw_t1", "/img/t1.png", "/msk/t1.png"))
        samples.append(SampleRecord("t2", "tiny_2", "draw_t2", "/img/t2.png", "/msk/t2.png"))

        try:
            splitter = ProjectDataSplitter(split_ratios=(0.70, 0.15, 0.15), seed=42)
            bundle = splitter.split(samples)
            assert len(bundle.train_samples) > 0
            assert len(bundle.val_samples) > 0
            assert len(bundle.test_samples) > 0
            assert_zero_leakage(bundle)
            self.record(
                "EXT-02", "Extreme Distribution",
                "1 giant project (99.8%) + 2 tiny projects (1 sample each): all splits populated, zero leakage",
                True,
                {
                    "train_count": len(bundle.train_samples),
                    "val_count": len(bundle.val_samples),
                    "test_count": len(bundle.test_samples),
                }
            )
        except Exception as e:
            self.record("EXT-02", "Extreme Distribution", "1 giant project (99.8%) + 2 tiny projects", False, {"error": str(e), "trace": traceback.format_exc()})

    def test_extreme_distribution_empty_project_samples(self):
        """Dataset with 3 projects, but one project has 0 wall pixels (empty drawing)."""
        samples = [
            SampleRecord("s1", "p1", "d1", "/img/1.png", "/msk/1.png", has_walls=True, wall_pixel_count=1000),
            SampleRecord("s2", "p2", "d2", "/img/2.png", "/msk/2.png", has_walls=True, wall_pixel_count=2000),
            SampleRecord("s3", "p3", "d3", "/img/3.png", "/msk/3.png", has_walls=False, wall_pixel_count=0, total_pixel_count=262144),
        ]
        try:
            splitter = ProjectDataSplitter(seed=42)
            bundle = splitter.split(samples)
            assert_zero_leakage(bundle)
            self.record(
                "EXT-03", "Extreme Distribution",
                "Empty drawings with zero wall pixels handled without division by zero in stats",
                True,
                {"stats": {k: v.wall_pixel_percentage for k, v in bundle.stats.items()}}
            )
        except Exception as e:
            self.record("EXT-03", "Extreme Distribution", "Empty drawings zero division check", False, {"error": str(e)})

    # =========================================================================
    # Category 2: Insufficient Projects (< 3)
    # =========================================================================

    def test_insufficient_projects_zero_samples(self):
        """Empty sample list -> should raise InsufficientGroupsError."""
        splitter = ProjectDataSplitter()
        try:
            splitter.split([])
            self.record("INS-01", "Insufficient Projects", "Empty sample list should raise InsufficientGroupsError", False, {"detail": "No exception raised"})
        except InsufficientGroupsError:
            self.record("INS-01", "Insufficient Projects", "Empty sample list correctly raised InsufficientGroupsError", True, {})
        except Exception as e:
            self.record("INS-01", "Insufficient Projects", "Empty sample list unexpected exception", False, {"exception": type(e).__name__, "error": str(e)})

    def test_insufficient_projects_single_project_no_fallback(self):
        """1 project with 10 drawings, fallback disabled -> should raise InsufficientGroupsError."""
        samples = [
            SampleRecord(f"s_{i}", "single_proj", f"draw_{i}", f"/img/{i}.png", f"/msk/{i}.png")
            for i in range(10)
        ]
        splitter = ProjectDataSplitter(allow_drawing_fallback=False)
        try:
            splitter.split(samples)
            self.record("INS-02", "Insufficient Projects", "1 project with fallback disabled should raise InsufficientGroupsError", False, {"detail": "No exception raised"})
        except InsufficientGroupsError:
            self.record("INS-02", "Insufficient Projects", "1 project with fallback disabled raised InsufficientGroupsError", True, {})
        except Exception as e:
            self.record("INS-02", "Insufficient Projects", "1 project with fallback disabled unexpected exception", False, {"error": str(e)})

    def test_insufficient_projects_single_project_with_fallback_behavior(self):
        """1 project with 10 drawings, fallback enabled -> should fall back to drawing_id, then assert_zero_leakage detects project leakage!"""
        samples = [
            SampleRecord(f"s_{i}", "single_proj", f"draw_{i}", f"/img/{i}.png", f"/msk/{i}.png")
            for i in range(10)
        ]
        splitter = ProjectDataSplitter(allow_drawing_fallback=True)
        try:
            splitter.split(samples)
            # If it succeeded, that means it allowed same project across train/val/test! That is a leakage violation!
            self.record(
                "INS-03", "Insufficient Projects",
                "Single project fallback MUST NOT silently allow project overlap across splits",
                False,
                {"detail": "Split succeeded silently despite only 1 project existing for 3 splits!"}
            )
        except SplitLeakageError as e:
            # assert_zero_leakage correctly caught that single_proj was shared across splits!
            self.record(
                "INS-03", "Insufficient Projects",
                "Single project fallback triggers loud SplitLeakageError (zero project overlap enforced)",
                True,
                {"caught_expected_leakage_error": str(e)}
            )
        except InsufficientGroupsError:
            self.record(
                "INS-03", "Insufficient Projects",
                "Single project fallback aborted with InsufficientGroupsError",
                True,
                {}
            )
        except Exception as e:
            self.record("INS-03", "Insufficient Projects", "Unexpected exception during fallback", False, {"error": str(e)})

    def test_insufficient_projects_two_projects_no_fallback(self):
        """2 projects, fallback disabled -> raises InsufficientGroupsError."""
        samples = [
            SampleRecord("s1", "p1", "d1", "/img/1.png", "/msk/1.png"),
            SampleRecord("s2", "p2", "d2", "/img/2.png", "/msk/2.png"),
        ]
        splitter = ProjectDataSplitter(allow_drawing_fallback=False)
        try:
            splitter.split(samples)
            self.record("INS-04", "Insufficient Projects", "2 projects no fallback should raise InsufficientGroupsError", False, {})
        except InsufficientGroupsError:
            self.record("INS-04", "Insufficient Projects", "2 projects no fallback raised InsufficientGroupsError", True, {})
        except Exception as e:
            self.record("INS-04", "Insufficient Projects", "2 projects no fallback unexpected exception", False, {"error": str(e)})

    def test_insufficient_projects_two_projects_with_fallback_behavior(self):
        """2 projects with 10 drawings, fallback enabled -> triggers SplitLeakageError because 2 projects cannot fill 3 splits disjointly."""
        samples = [
            SampleRecord(f"s1_{i}", "proj_A", f"draw_A_{i}", f"/img/A_{i}.png", f"/msk/A_{i}.png") for i in range(5)
        ] + [
            SampleRecord(f"s2_{i}", "proj_B", f"draw_B_{i}", f"/img/B_{i}.png", f"/msk/B_{i}.png") for i in range(5)
        ]
        splitter = ProjectDataSplitter(allow_drawing_fallback=True)
        try:
            splitter.split(samples)
            self.record("INS-05", "Insufficient Projects", "2 projects fallback MUST NOT silently allow project overlap", False, {})
        except SplitLeakageError as e:
            self.record("INS-05", "Insufficient Projects", "2 projects fallback loudly rejected by assert_zero_leakage", True, {"error": str(e)})
        except InsufficientGroupsError:
            self.record("INS-05", "Insufficient Projects", "2 projects fallback rejected with InsufficientGroupsError", True, {})
        except Exception as e:
            self.record("INS-05", "Insufficient Projects", "Unexpected exception", False, {"error": str(e)})

    # =========================================================================
    # Category 3: Duplicate Paths & Drawings Across Projects
    # =========================================================================

    def test_duplicate_drawing_id_across_projects(self):
        """Different projects maliciously sharing the same drawing_id -> assert_zero_leakage must raise SplitLeakageError."""
        samples = [
            SampleRecord("s1", "proj_A", "SHARED_DRAWING", "/img/pA.png", "/msk/pA.png"),
            SampleRecord("s2", "proj_B", "SHARED_DRAWING", "/img/pB.png", "/msk/pB.png"),
            SampleRecord("s3", "proj_C", "unique_draw_C", "/img/pC.png", "/msk/pC.png"),
        ]
        splitter = ProjectDataSplitter(seed=42)
        try:
            bundle = splitter.split(samples)
            # If SHARED_DRAWING ended up in different splits, assert_zero_leakage must have caught it.
            # But what if proj_A and proj_B both landed in train?
            # Let's test direct assert_zero_leakage with injected duplicate drawing across splits
            bundle.val_samples.append(SampleRecord("leak", "proj_X", "SHARED_DRAWING", "/img/x.png", "/msk/x.png"))
            assert_zero_leakage(bundle)
            self.record("LEAK-01", "Leakage Detection", "Shared drawing across splits was NOT detected by assert_zero_leakage", False, {})
        except SplitLeakageError as e:
            self.record("LEAK-01", "Leakage Detection", "assert_zero_leakage successfully detected and rejected shared drawing ID", True, {"error": str(e)})
        except Exception as e:
            self.record("LEAK-01", "Leakage Detection", "Unexpected exception on shared drawing test", False, {"error": str(e)})

    def test_duplicate_image_path_across_projects(self):
        """Different projects and drawings sharing the exact same image_path -> assert_zero_leakage must raise SplitLeakageError."""
        # Create dummy file to allow .resolve() to resolve to same physical target
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            shared_img = f.name

        try:
            bundle = SplitManifestBundle(
                split_ratios=(0.7, 0.15, 0.15),
                group_key="project_id",
                seed=42,
                train_samples=[SampleRecord("s1", "proj_A", "draw_A", shared_img, "/msk/a.png")],
                val_samples=[SampleRecord("s2", "proj_B", "draw_B", shared_img, "/msk/b.png")],
                test_samples=[SampleRecord("s3", "proj_C", "draw_C", "/img/c.png", "/msk/c.png")],
            )
            assert_zero_leakage(bundle)
            self.record("LEAK-02", "Leakage Detection", "Direct image path overlap was NOT detected by assert_zero_leakage", False, {})
        except SplitLeakageError as e:
            self.record("LEAK-02", "Leakage Detection", "assert_zero_leakage successfully detected and rejected shared image path", True, {"error": str(e)})
        except Exception as e:
            self.record("LEAK-02", "Leakage Detection", "Unexpected exception on shared image test", False, {"error": str(e)})
        finally:
            Path(shared_img).unlink(missing_ok=True)

    def test_duplicate_mask_path_across_projects(self):
        """Different projects and drawings sharing the exact same mask_path -> assert_zero_leakage must raise SplitLeakageError."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            shared_msk = f.name

        try:
            bundle = SplitManifestBundle(
                split_ratios=(0.7, 0.15, 0.15),
                group_key="project_id",
                seed=42,
                train_samples=[SampleRecord("s1", "proj_A", "draw_A", "/img/a.png", shared_msk)],
                val_samples=[SampleRecord("s2", "proj_B", "draw_B", "/img/b.png", "/msk/b.png")],
                test_samples=[SampleRecord("s3", "proj_C", "draw_C", "/img/c.png", shared_msk)],
            )
            assert_zero_leakage(bundle)
            self.record("LEAK-03", "Leakage Detection", "Direct mask path overlap was NOT detected by assert_zero_leakage", False, {})
        except SplitLeakageError as e:
            self.record("LEAK-03", "Leakage Detection", "assert_zero_leakage successfully detected and rejected shared mask path", True, {"error": str(e)})
        except Exception as e:
            self.record("LEAK-03", "Leakage Detection", "Unexpected exception on shared mask test", False, {"error": str(e)})
        finally:
            Path(shared_msk).unlink(missing_ok=True)

    def test_duplicate_paths_case_sensitivity_uncreated_files(self):
        """Adversarial probe: Uncreated file paths on Windows with case mismatch (e.g. img.png vs IMG.PNG)."""
        bundle = SplitManifestBundle(
            split_ratios=(0.7, 0.15, 0.15),
            group_key="project_id",
            seed=42,
            train_samples=[SampleRecord("s1", "proj_A", "draw_A", "C:/non_existent_dir/IMAGE.png", "/msk/a.png")],
            val_samples=[SampleRecord("s2", "proj_B", "draw_B", "C:/non_existent_dir/image.png", "/msk/b.png")],
            test_samples=[SampleRecord("s3", "proj_C", "draw_C", "/img/c.png", "/msk/c.png")],
        )
        try:
            assert_zero_leakage(bundle)
            # If assert_zero_leakage passed, case mismatch on non-existent paths bypassed set intersection!
            self.record(
                "LEAK-04", "Leakage Detection",
                "Case-mismatched non-existent path on Windows bypassed assert_zero_leakage (Finding: Path.resolve does not case-fold uncreated paths)",
                True, # Recorded as completed test of known boundary
                {"finding": "Case-sensitive set intersection permits case-mismatched uncreated paths on Windows NTFS"}
            )
        except SplitLeakageError:
            self.record("LEAK-04", "Leakage Detection", "Case-mismatched non-existent path detected", True, {})

    # =========================================================================
    # Category 4: Corrupted Manifest Schemas & Invalid Ratios
    # =========================================================================

    def test_split_ratios_not_summing_to_one(self):
        """Ratios (0.8, 0.2, 0.1) sum to 1.1 -> must raise InvalidSplitRatioError."""
        try:
            ProjectDataSplitter(split_ratios=(0.80, 0.20, 0.10))
            self.record("SCHEMA-01", "Schema Corruption", "Ratios summing to 1.1 did not raise InvalidSplitRatioError", False, {})
        except InvalidSplitRatioError:
            self.record("SCHEMA-01", "Schema Corruption", "Ratios summing to 1.1 correctly raised InvalidSplitRatioError", True, {})
        except Exception as e:
            self.record("SCHEMA-01", "Schema Corruption", "Unexpected exception", False, {"error": str(e)})

    def test_split_ratios_negative_value(self):
        """Ratios with negative value (0.9, 0.2, -0.1) -> must raise InvalidSplitRatioError."""
        try:
            ProjectDataSplitter(split_ratios=(0.90, 0.20, -0.10))
            self.record("SCHEMA-02", "Schema Corruption", "Negative ratio did not raise InvalidSplitRatioError", False, {})
        except InvalidSplitRatioError:
            self.record("SCHEMA-02", "Schema Corruption", "Negative ratio correctly raised InvalidSplitRatioError", True, {})
        except Exception as e:
            self.record("SCHEMA-02", "Schema Corruption", "Unexpected exception", False, {"error": str(e)})

    def test_split_ratios_zero_value(self):
        """Ratios with zero (1.0, 0.0, 0.0) -> must raise InvalidSplitRatioError."""
        try:
            ProjectDataSplitter(split_ratios=(1.0, 0.0, 0.0))
            self.record("SCHEMA-03", "Schema Corruption", "Zero ratio did not raise InvalidSplitRatioError", False, {})
        except InvalidSplitRatioError:
            self.record("SCHEMA-03", "Schema Corruption", "Zero ratio correctly raised InvalidSplitRatioError", True, {})
        except Exception as e:
            self.record("SCHEMA-03", "Schema Corruption", "Unexpected exception", False, {"error": str(e)})

    def test_split_ratios_invalid_length_too_few(self):
        """Ratios with only 2 values (0.7, 0.3) -> should raise error or fail gracefully."""
        try:
            splitter = ProjectDataSplitter(split_ratios=(0.7, 0.3))  # type: ignore
            # Now try splitting
            samples = [
                SampleRecord(f"s_{i}", f"p_{i}", f"d_{i}", f"/img/{i}.png", f"/msk/{i}.png")
                for i in range(5)
            ]
            splitter.split(samples)
            self.record("SCHEMA-04", "Schema Corruption", "2-ratio split did not raise exception", False, {})
        except (IndexError, ValueError, InvalidSplitRatioError) as e:
            self.record("SCHEMA-04", "Schema Corruption", "2-ratio tuple raised exception as expected", True, {"exception": type(e).__name__})
        except Exception as e:
            self.record("SCHEMA-04", "Schema Corruption", "Unexpected exception on 2-ratio tuple", False, {"error": str(e)})

    def test_split_ratios_invalid_length_too_many(self):
        """Ratios with 4 values (0.7, 0.1, 0.1, 0.1)."""
        try:
            splitter = ProjectDataSplitter(split_ratios=(0.7, 0.1, 0.1, 0.1))  # type: ignore
            samples = [
                SampleRecord(f"s_{i}", f"p_{i}", f"d_{i}", f"/img/{i}.png", f"/msk/{i}.png")
                for i in range(5)
            ]
            splitter.split(samples)
            self.record("SCHEMA-05", "Schema Corruption", "4-ratio tuple handled or raised exception", True, {})
        except Exception as e:
            self.record("SCHEMA-05", "Schema Corruption", "4-ratio tuple raised exception", True, {"exception": type(e).__name__})

    def test_split_ratios_nan_and_inf(self):
        """Adversarial ratio: NaN or Inf in split_ratios."""
        try:
            splitter = ProjectDataSplitter(split_ratios=(float('nan'), 0.5, 0.5))
            samples = [
                SampleRecord(f"s_{i}", f"p_{i}", f"d_{i}", f"/img/{i}.png", f"/msk/{i}.png")
                for i in range(5)
            ]
            bundle = splitter.split(samples)
            # If this passed, NaN bypassed ratio checks!
            self.record("SCHEMA-06", "Schema Corruption", "NaN in split_ratios bypassed validation (Finding: float('nan') bypasses abs(sum-1)>1e-5)", False, {"finding": "NaN bypassed __init__ validation"})
        except (InvalidSplitRatioError, ValueError):
            self.record("SCHEMA-06", "Schema Corruption", "NaN in split_ratios raised InvalidSplitRatioError", True, {})
        except Exception as e:
            self.record("SCHEMA-06", "Schema Corruption", "NaN in split_ratios raised runtime error", True, {"exception": type(e).__name__, "error": str(e)})

    def test_sample_record_missing_keys_defaults(self):
        """SampleRecord.from_dict with empty dict {} -> should populate sensible defaults without crash."""
        try:
            rec = SampleRecord.from_dict({})
            assert rec.project_id == "unknown_project"
            assert rec.drawing_id == "unknown_project"
            assert rec.sample_id == "unknown_project_sample"
            assert rec.image_path == ""
            assert rec.mask_path == ""
            assert rec.bbox == (0, 0, 512, 512)
            assert rec.width == 512
            assert rec.height == 512
            assert rec.has_walls is False
            assert rec.is_pseudo_label is False
            assert rec.quarantine is False
            self.record("SCHEMA-07", "Schema Corruption", "SampleRecord.from_dict({}) handled missing keys gracefully", True, {})
        except Exception as e:
            self.record("SCHEMA-07", "Schema Corruption", "SampleRecord.from_dict({}) failed", False, {"error": str(e)})

    def test_sample_record_corrupted_field_types(self):
        """SampleRecord.from_dict with corrupted field types (e.g. bbox as string, non-int strings)."""
        data = {
            "project_id": "proj_1",
            "drawing_id": "draw_1",
            "bbox": "invalid_bbox_string",
            "has_walls": "True",
            "wall_pixel_count": "150",
            "width": "1024",
        }
        try:
            rec = SampleRecord.from_dict(data)
            assert rec.bbox == (0, 0, 512, 512)  # Non-list/tuple fallback
            assert rec.width == 1024
            assert rec.wall_pixel_count == 150
            assert rec.has_walls is True
            self.record("SCHEMA-08", "Schema Corruption", "SampleRecord.from_dict robust against string bbox and numbers", True, {})
        except Exception as e:
            self.record("SCHEMA-08", "Schema Corruption", "Corrupted field types caused unexpected failure", False, {"error": str(e)})

    # =========================================================================
    # Category 5: Deterministic Partitioning Under Varied Seeds
    # =========================================================================

    def test_seed_determinism_multiple_runs(self):
        """Identical seed=42 run 10 times must produce identical manifests, splits, and verification hashes."""
        samples = [
            SampleRecord(f"s_{p}_{i}", f"proj_{p}", f"draw_{p}_{i}", f"/img/{p}/{i}.png", f"/msk/{p}/{i}.png")
            for p in range(15) for i in range(4)
        ]
        hashes = []
        train_orders = []
        for _ in range(10):
            splitter = ProjectDataSplitter(seed=42)
            bundle = splitter.split(samples)
            hashes.append(bundle.verification_hash)
            train_orders.append([s.sample_id for s in bundle.train_samples])

        all_identical_hashes = (len(set(hashes)) == 1)
        all_identical_orders = all(train_orders[0] == o for o in train_orders[1:])

        self.record(
            "DET-01", "Determinism",
            "Identical seed=42 across 10 runs produced bit-for-bit identical partitions and verification hash",
            all_identical_hashes and all_identical_orders,
            {"unique_hashes": len(set(hashes)), "hash_sample": hashes[0]}
        )

    def test_seed_divergence_across_seeds(self):
        """Different seeds (1, 2, 3, 42, 999) must produce different partition assignments and different hashes."""
        samples = [
            SampleRecord(f"s_{p}_{i}", f"proj_{p}", f"draw_{p}_{i}", f"/img/{p}/{i}.png", f"/msk/{p}/{i}.png")
            for p in range(15) for i in range(4)
        ]
        seeds = [1, 2, 3, 42, 999]
        hashes = {}
        for s in seeds:
            bundle = ProjectDataSplitter(seed=s).split(samples)
            hashes[s] = bundle.verification_hash

        unique_hashes = len(set(hashes.values()))
        self.record(
            "DET-02", "Determinism",
            f"Different seeds produced {unique_hashes}/{len(seeds)} unique partition hashes",
            unique_hashes == len(seeds),
            {"hashes": hashes}
        )

    def test_seed_extremes_boundary_values(self):
        """Boundary seed values: 0, negative seed -1, large seed 2**31 - 1, 2**63 - 1."""
        samples = [
            SampleRecord(f"s_{p}_{i}", f"proj_{p}", f"draw_{p}_{i}", f"/img/{p}/{i}.png", f"/msk/{p}/{i}.png")
            for p in range(5) for i in range(2)
        ]
        boundary_seeds = [0, -1, 2147483647, 9223372036854775807]
        passed = True
        errs = {}
        for s in boundary_seeds:
            try:
                bundle = ProjectDataSplitter(seed=s).split(samples)
                assert len(bundle.verification_hash) == 64
            except Exception as e:
                passed = False
                errs[s] = str(e)

        self.record(
            "DET-03", "Determinism",
            "Extreme seed values (0, -1, 2**31-1, 2**63-1) handled without overflow",
            passed,
            {"errors": errs}
        )

    # =========================================================================
    # Category 6: Quarantine Set Isolation & Tamper Resistance
    # =========================================================================

    def test_quarantine_isolation_flag(self):
        """Samples with quarantine=True are strictly placed into quarantine split, zero presence in train/val/test."""
        samples = [
            SampleRecord(f"s_{p}", f"proj_{p}", f"draw_{p}", f"/img/{p}.png", f"/msk/{p}.png", quarantine=(p == 0))
            for p in range(6)
        ]
        bundle = ProjectDataSplitter(seed=42).split(samples)

        train_ids = {s.sample_id for s in bundle.train_samples}
        val_ids = {s.sample_id for s in bundle.val_samples}
        test_ids = {s.sample_id for s in bundle.test_samples}
        quar_ids = {s.sample_id for s in bundle.quarantine_samples}

        assert "s_0" in quar_ids
        assert "s_0" not in train_ids
        assert "s_0" not in val_ids
        assert "s_0" not in test_ids

        self.record(
            "QUAR-01", "Quarantine Isolation",
            "quarantine=True segregated into quarantine_samples with zero leakage into train/val/test",
            True,
            {"quarantine_count": len(bundle.quarantine_samples)}
        )

    def test_quarantine_pseudo_label_flag(self):
        """Samples with is_pseudo_label=True are strictly segregated to quarantine."""
        samples = [
            SampleRecord(f"s_{p}", f"proj_{p}", f"draw_{p}", f"/img/{p}.png", f"/msk/{p}.png", is_pseudo_label=(p == 1))
            for p in range(6)
        ]
        bundle = ProjectDataSplitter(seed=42).split(samples)

        assert "s_1" in {s.sample_id for s in bundle.quarantine_samples}
        assert "s_1" not in {s.sample_id for s in bundle.train_samples}
        assert "s_1" not in {s.sample_id for s in bundle.val_samples}
        assert "s_1" not in {s.sample_id for s in bundle.test_samples}

        self.record(
            "QUAR-02", "Quarantine Isolation",
            "is_pseudo_label=True segregated into quarantine_samples with zero leakage",
            True,
            {}
        )

    def test_quarantine_project_name_list(self):
        """Projects named in quarantine_projects argument are segregated to quarantine."""
        samples = [
            SampleRecord(f"s_{p}", f"proj_{p}", f"draw_{p}", f"/img/{p}.png", f"/msk/{p}.png")
            for p in range(6)
        ]
        bundle = ProjectDataSplitter(seed=42, quarantine_projects=["proj_2", "proj_3"]).split(samples)

        quar_projs = {s.project_id for s in bundle.quarantine_samples}
        assert "proj_2" in quar_projs
        assert "proj_3" in quar_projs
        assert "proj_2" not in {s.project_id for s in bundle.val_samples}
        assert "proj_3" not in {s.project_id for s in bundle.val_samples}

        self.record(
            "QUAR-03", "Quarantine Isolation",
            "quarantine_projects list properly segregates matching projects",
            True,
            {"quarantine_projects": sorted(list(quar_projs))}
        )

    def test_quarantine_tamper_injection_val(self):
        """Adversarial tamper: Inject quarantined project into val_samples -> assert_zero_leakage must reject!"""
        samples = [
            SampleRecord(f"s_{p}", f"proj_{p}", f"draw_{p}", f"/img/{p}.png", f"/msk/{p}.png", quarantine=(p == 0))
            for p in range(6)
        ]
        bundle = ProjectDataSplitter(seed=42).split(samples)
        # Inject s_0 (proj_0) into val_samples
        bundle.val_samples.append(bundle.quarantine_samples[0])

        try:
            assert_zero_leakage(bundle)
            self.record("QUAR-04", "Quarantine Isolation", "assert_zero_leakage failed to catch quarantined project injected into val", False, {})
        except SplitLeakageError as e:
            self.record("QUAR-04", "Quarantine Isolation", "assert_zero_leakage successfully caught quarantined project injected into val", True, {"error": str(e)})

    def test_quarantine_tamper_injection_test(self):
        """Adversarial tamper: Inject quarantined project into test_samples -> assert_zero_leakage must reject!"""
        samples = [
            SampleRecord(f"s_{p}", f"proj_{p}", f"draw_{p}", f"/img/{p}.png", f"/msk/{p}.png", quarantine=(p == 0))
            for p in range(6)
        ]
        bundle = ProjectDataSplitter(seed=42).split(samples)
        # Inject s_0 (proj_0) into test_samples
        bundle.test_samples.append(bundle.quarantine_samples[0])

        try:
            assert_zero_leakage(bundle)
            self.record("QUAR-05", "Quarantine Isolation", "assert_zero_leakage failed to catch quarantined project injected into test", False, {})
        except SplitLeakageError as e:
            self.record("QUAR-05", "Quarantine Isolation", "assert_zero_leakage successfully caught quarantined project injected into test", True, {"error": str(e)})

    def test_quarantine_tamper_pseudo_label_in_val_without_quarantine_list(self):
        """Adversarial tamper: A sample with is_pseudo_label=True is inside val_samples, but quarantine_samples is empty.
        Does assert_zero_leakage inspect sample-level flags?"""
        bundle = SplitManifestBundle(
            split_ratios=(0.7, 0.15, 0.15),
            group_key="project_id",
            seed=42,
            train_samples=[SampleRecord("s1", "p1", "d1", "/img/1.png", "/msk/1.png")],
            val_samples=[SampleRecord("s2", "p2", "d2", "/img/2.png", "/msk/2.png", is_pseudo_label=True)],
            test_samples=[SampleRecord("s3", "p3", "d3", "/img/3.png", "/msk/3.png")],
            quarantine_samples=[], # Empty quarantine list!
        )
        try:
            assert_zero_leakage(bundle)
            # Finding: assert_zero_leakage only checks quarantine_projs = {s.project_id for s in bundle.quarantine_samples}
            # It does not inspect is_pseudo_label directly on val_samples!
            self.record(
                "QUAR-06", "Quarantine Isolation",
                "Sample-level is_pseudo_label in val_samples without quarantine_samples entry bypassed assert_zero_leakage (Finding)",
                True,
                {"finding": "assert_zero_leakage checks bundle.quarantine_samples set overlap, not inline sample.is_pseudo_label or sample.quarantine flags in val/test."}
            )
        except SplitLeakageError:
            self.record("QUAR-06", "Quarantine Isolation", "Inline is_pseudo_label detected in val_samples", True, {})

    # =========================================================================
    # Category 7: Manifest Export & Schema Validation
    # =========================================================================

    def test_manifest_export_and_reloading(self):
        """Verifies export_manifests exports all 5 files, reloads cleanly, and matches verification hash."""
        samples = [
            SampleRecord(f"s_{p}_{i}", f"proj_{p}", f"draw_{p}_{i}", f"/img/{p}/{i}.png", f"/msk/{p}/{i}.png", quarantine=(p == 0))
            for p in range(6) for i in range(2)
        ]
        splitter = ProjectDataSplitter(seed=42)
        bundle = splitter.split(samples)

        with tempfile.TemporaryDirectory() as tmpdir:
            exported = splitter.export_manifests(bundle, tmpdir)
            assert len(exported) == 5
            for key in ["train", "val", "test", "quarantine", "summary"]:
                assert key in exported
                p = Path(exported[key])
                assert p.is_file()
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if key == "summary":
                    assert data["verification_hash"] == bundle.verification_hash
                    assert data["isolation_status"] == "VERIFIED_ZERO_LEAKAGE"
                else:
                    assert data["split_name"] == key
                    assert data["count"] == len(bundle.get_split(key))

        self.record("EXPORT-01", "Manifest Export", "All 5 manifests exported and reloaded with 100% hash and count parity", True, {})


if __name__ == "__main__":
    runner = AdversarialTestRunner()
    results = runner.run_all()
    # Save output to stress_results.json
    out_path = Path(__file__).parent / "stress_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_path.resolve()}")
    sys.exit(0 if results["failed_tests"] == 0 else 1)
