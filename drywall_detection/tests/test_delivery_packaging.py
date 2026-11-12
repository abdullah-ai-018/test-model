"""
drywall_detection/tests/test_delivery_packaging.py
=================================================
Delivery packaging, reports audit, codebase cleanliness, and documentation
completeness verification test suite (Milestone M6).
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest

from drywall_detection import __version__
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    PACKAGE_ROOT,
    REPORTS_DIR,
    WORKSPACE_ROOT,
)


class TestMilestoneReports:
    """Verifies that all required milestone reports exist, exceed 10 KB, and contain the mandatory notice."""

    REQUIRED_REPORTS = [
        "M1_audit_report.md",
        "M2_dataset_report.md",
        "M3_vector_schedule_report.md",
        "M4_model_training_report.md",
        "M5_classification_report.md",
        "M6_final_limitations_report.md",
    ]

    def test_all_milestone_reports_exist_and_non_empty(self):
        for rep_name in self.REQUIRED_REPORTS:
            rep_path = REPORTS_DIR / rep_name
            assert rep_path.is_file(), f"Missing required milestone report: {rep_name}"
            size_bytes = rep_path.stat().st_size
            assert size_bytes >= 10_000, (
                f"Report {rep_name} is too small ({size_bytes} bytes < 10,000 bytes target)"
            )

    def test_mandatory_notice_present_in_all_reports(self):
        mandatory_pattern = "PROGRESS SET 95% CDs"
        for rep_name in self.REQUIRED_REPORTS:
            rep_path = REPORTS_DIR / rep_name
            content = rep_path.read_text(encoding="utf-8")
            assert mandatory_pattern in content, (
                f"Mandatory progress set citation ('{mandatory_pattern}') missing in report: {rep_name}"
            )


class TestCheckpointBundlePackaging:
    """Verifies that the deliverable model bundle satisfies interface contracts."""

    BUNDLE_ARTIFACTS = [
        "best_model.pt",
        "config.json",
        "class_mapping.json",
        "training_log.json",
        "metrics.json",
        "infer.py",
        "README.md",
        "sample_overlays",
    ]

    def test_checkpoint_best_model_bundle_integrity(self):
        for art_name in self.BUNDLE_ARTIFACTS:
            art_path = BEST_MODEL_DIR / art_name
            assert art_path.exists(), f"Missing checkpoint artifact: {art_name}"
            if art_path.is_file():
                assert art_path.stat().st_size > 0

        # Validate config.json
        cfg = json.loads((BEST_MODEL_DIR / "config.json").read_text(encoding="utf-8"))
        assert cfg.get("num_classes") == 4
        assert cfg.get("total_parameters") == 3715172

        # Validate class_mapping.json
        cm = json.loads((BEST_MODEL_DIR / "class_mapping.json").read_text(encoding="utf-8"))
        assert len(cm.get("classes", [])) == 4

        # Validate metrics.json
        met = json.loads((BEST_MODEL_DIR / "metrics.json").read_text(encoding="utf-8"))
        assert "confusion_matrix" in met


class TestApprovedScheduleMappingIntegrity:
    """Verifies approved partition schedule CSV schema, 24 rows, and Detail 1A CMU veto."""

    def test_approved_partition_schedule_csv_integrity(self):
        assert APPROVED_SCHEDULE_CSV_PATH.is_file(), (
            f"Approved schedule CSV missing at: {APPROVED_SCHEDULE_CSV_PATH}"
        )

        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.lstrip("\ufeff").strip().lower() for fn in (reader.fieldnames or [])]
            assert "tag" in fieldnames
            assert "proposed_class" in fieldnames

            rows = list(reader)

        assert len(rows) == 24, f"Expected exactly 24 assembly details, found {len(rows)}"

        # Verify Detail 1A is Non-Drywall
        tag_1a_row = None
        for r in rows:
            clean_tag = r.get("tag", "").strip().upper()
            if clean_tag == "1A":
                tag_1a_row = r
                break

        assert tag_1a_row is not None, "Detail 1A missing from approved schedule CSV"
        assert tag_1a_row.get("proposed_class", "").strip() == "Non-Drywall"


class TestCodebaseLayoutCleanliness:
    """Verifies layout compliance: package source code and tests in drywall_detection/, and metadata only in worker state."""

    def test_codebase_layout_cleanliness(self):
        # 1. Verify package structure and essential entry points exist in drywall_detection/
        assert (PACKAGE_ROOT / "__init__.py").is_file()
        assert (PACKAGE_ROOT / "__main__.py").is_file()
        assert (PACKAGE_ROOT / "cli.py").is_file()
        assert (PACKAGE_ROOT / "app.py").is_file()
        assert (PACKAGE_ROOT / "config.py").is_file()

        # 2. Verify submodules have proper __init__.py files
        for subpkg in ["audit", "data", "vector", "models", "classification", "pipeline", "utils", "tests"]:
            init_file = PACKAGE_ROOT / subpkg / "__init__.py"
            assert init_file.is_file(), f"Subpackage missing __init__.py: {subpkg}"

        # 3. Verify that current milestone worker folder contains only metadata (no code or test files)
        worker_dir = WORKSPACE_ROOT / ".agents" / "teamwork" / "worker_m6_1"
        if worker_dir.is_dir():
            py_files = list(worker_dir.glob("*.py"))
            assert len(py_files) == 0, (
                f"Worker state folder contains python code/test files: {py_files}"
            )

        # 4. Verify no package directory or production modules are inside .agents/teamwork/
        teamwork_dir = WORKSPACE_ROOT / ".agents" / "teamwork"
        assert not (teamwork_dir / "drywall_detection").exists()


class TestDocumentationCompleteness:
    """Verifies that drywall_detection/README.md is comprehensive and contains all required sections."""

    def test_readme_documentation_completeness(self):
        readme_path = PACKAGE_ROOT / "README.md"
        assert readme_path.is_file(), "Root README.md missing"
        content = readme_path.read_text(encoding="utf-8")

        required_keywords = [
            "PROGRESS SET 95% CDs",
            "MTA Contract C-48526",
            "Quick Start",
            "run_app.bat",
            "streamlit run",
            "Unified Production CLI",
            "python -m drywall_detection",
            "audit-datasets",
            "extract-vector",
            "parse-schedule",
            "classify",
            "infer-segmentation",
            "run-pipeline",
            "4-Class Material Taxonomy",
            "Detail 1A",
            "Non-Drywall",
            "pytest",
            "Limitations & Disclaimers",
        ]
        for kw in required_keywords:
            assert kw in content, f"Missing required keyword/section '{kw}' in README.md"


class TestCLIEntryPointsSubprocess:
    """Verifies that top-level module and standalone scripts are executable via subprocess."""

    def test_cli_entry_points_help_flag(self):
        cmd1 = [sys.executable, "-m", "drywall_detection", "--help"]
        res1 = subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res1.returncode == 0
        assert "Drywall Detection & Takeoff Engine" in res1.stdout

        infer_script = BEST_MODEL_DIR / "infer.py"
        cmd2 = [sys.executable, str(infer_script), "--help"]
        res2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res2.returncode == 0
        assert "Standalone offline inference CLI" in res2.stdout
