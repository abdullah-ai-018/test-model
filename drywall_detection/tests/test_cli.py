"""
drywall_detection/tests/test_cli.py
==================================
Comprehensive verification test suite for the unified production CLI (cli.py).
Tests all 7 subcommands, POSIX exit codes (0, 1, 2, 3), Detail 1A CMU safety veto,
human review lock protocol, and end-to-end pipeline execution (Milestone M6).
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import pytest
import fitz

from drywall_detection import __version__
from drywall_detection.cli import (
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_REVIEW_REQUIRED,
    EXIT_CMU_VETO_VIOLATION,
    build_cli_parser,
    main,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    DEFAULT_MASTER_PDF_PATH,
)


class TestCLIParserAndHelp:
    """Verifies CLI argument parser registration, options, and help exit codes."""

    def test_parser_subcommands_registered(self):
        parser = build_cli_parser()
        subparser_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparser_actions) == 1
        subcommands = subparser_actions[0].choices
        expected = [
            "audit-datasets",
            "extract-vector",
            "parse-schedule",
            "classify",
            "infer-segmentation",
            "run-pipeline",
            "info",
            "version",
        ]
        for cmd in expected:
            assert cmd in subcommands, f"Missing registered subcommand: {cmd}"

    def test_toplevel_help_flag_returns_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "Drywall Detection & Takeoff Engine" in captured.out

    def test_subcommand_help_flags_return_0(self, capsys):
        subcmds = [
            "audit-datasets",
            "extract-vector",
            "parse-schedule",
            "classify",
            "infer-segmentation",
            "run-pipeline",
            "info",
        ]
        for subcmd in subcmds:
            with pytest.raises(SystemExit) as exc:
                main([subcmd, "--help"])
            assert exc.value.code == 0

    def test_unrecognized_argument_returns_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["--unrecognized-option-xyz"])
        assert exc.value.code == 2

    def test_no_arguments_displays_help_and_exits_0(self, capsys):
        code = main([])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Drywall Detection & Takeoff Engine" in captured.out


class TestCLIVersionAndInfo:
    """Verifies system profiling, versioning, and checkpoint inspection."""

    def test_info_command_text_output(self, capsys):
        code = main(["info"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert f"Version: {__version__}" in captured.out
        assert "Hardware Environment Profile" in captured.out
        assert "Champion Model Status" in captured.out

    def test_info_command_json_output(self, capsys):
        code = main(["info", "--json"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["version"] == __version__
        assert "hardware" in data
        assert "checkpoints" in data
        assert data["checkpoints"]["champion_model_found"] is True

    def test_version_alias_command(self, capsys):
        code = main(["version", "--json"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["version"] == __version__


class TestCLIAuditDatasets:
    """Verifies candidate dataset auditing and disk safety pre-flight checks."""

    def test_audit_datasets_all_table_format(self, capsys):
        code = main(["audit-datasets", "--format", "table"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Dataset Audit Report" in captured.out
        assert "MSD" in captured.out
        assert "CUBICASA5K" in captured.out

    def test_audit_datasets_single_dataset_msd(self, capsys):
        code = main(["audit-datasets", "--dataset-id", "msd", "--format", "json"])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["dataset_id"] == "msd"
        assert data["eligibility_verdict"] == "ELIGIBLE"

    def test_audit_datasets_save_flag_writes_reports(self, tmp_path):
        out_dir = tmp_path / "audit_reports"
        code = main(["audit-datasets", "--output-dir", str(out_dir), "--save"])
        assert code == EXIT_SUCCESS
        assert (out_dir / "dataset_audit_report.md").is_file()
        assert (out_dir / "dataset_audit_report.json").is_file()

    def test_audit_datasets_invalid_id_rejected(self):
        with pytest.raises(SystemExit) as exc:
            main(["audit-datasets", "--dataset-id", "invalid_id"])
        assert exc.value.code == 2


class TestCLIParseScheduleAndReviewLock:
    """Verifies schedule parsing, Detail 1A CMU veto enforcement, and review lock protocol."""

    def test_parse_schedule_normal_approved_exit_0(self, tmp_path):
        out_csv = tmp_path / "draft_schedule.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--verify-detail-1a",
        ])
        assert code == EXIT_SUCCESS
        assert out_csv.exists()

    def test_parse_schedule_missing_approved_exit_2(self, tmp_path):
        out_csv = tmp_path / "draft_schedule.csv"
        missing_approved = tmp_path / "missing.approved.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(missing_approved),
            "--enforce-review-lock",
        ])
        assert code == EXIT_REVIEW_REQUIRED
        lock_file = tmp_path / "REVIEW_REQUIRED.lock"
        assert lock_file.exists()

    def test_parse_schedule_detail_1a_tampering_exit_3(self, tmp_path):
        # Create a tampered approved CSV attempting to mark Detail 1A as Drywall
        bad_approved = tmp_path / "bad.approved.csv"
        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as fin:
            content = fin.read()

        tampered = content.replace(",Non-Drywall,1.0,", ",Drywall,1.0,")
        with open(bad_approved, "w", encoding="utf-8") as fout:
            fout.write(tampered)

        out_csv = tmp_path / "draft_schedule.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(bad_approved),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION


class TestCLIExtractVector:
    """Verifies vector CAD linework, wall reconstruction, and tag discovery."""

    def test_extract_vector_detect_only(self, capsys):
        code = main([
            "extract-vector",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--detect-only",
        ])
        assert code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Vector Profile" in captured.out
        assert "VECTOR_FIRST" in captured.out

    def test_extract_vector_geojson_export(self, tmp_path):
        out_dir = tmp_path / "vec_out"
        code = main([
            "extract-vector",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--format", "geojson",
        ])
        assert code == EXIT_SUCCESS
        geojson_file = out_dir / "extracted_walls_p14.geojson"
        assert geojson_file.is_file()
        with open(geojson_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) > 0

    def test_extract_vector_invalid_page_returns_error(self):
        code = main([
            "extract-vector",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "9999",
        ])
        assert code == EXIT_ERROR


class TestCLIClassify:
    """Verifies wall classification with schedule rules, CMU veto, and Tier 3 unassigned fallback."""

    def test_classify_normal_with_approved_schedule(self, tmp_path):
        out_dir = tmp_path / "classify_out"
        code = main([
            "classify",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--output-dir", str(out_dir),
            "--export-annotated-pdf",
        ])
        assert code == EXIT_SUCCESS
        geojson_file = out_dir / "classified_walls_p14.geojson"
        assert geojson_file.is_file()
        pdf_file = out_dir / "annotated_classified_drawings.pdf"
        assert pdf_file.is_file()

    def test_classify_missing_approved_schedule_exit_2(self, tmp_path):
        out_dir = tmp_path / "classify_out"
        missing_csv = tmp_path / "non_existent.csv"
        code = main([
            "classify",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(missing_csv),
            "--output-dir", str(out_dir),
        ])
        assert code == EXIT_REVIEW_REQUIRED

    def test_classify_cmu_veto_violation_exit_3(self, tmp_path):
        bad_approved = tmp_path / "bad.approved.csv"
        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as fin:
            content = fin.read()
        tampered = content.replace(",Non-Drywall,1.0,", ",Drywall,1.0,")
        with open(bad_approved, "w", encoding="utf-8") as fout:
            fout.write(tampered)

        out_dir = tmp_path / "classify_bad_out"
        code = main([
            "classify",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(bad_approved),
            "--output-dir", str(out_dir),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION


class TestCLIInferSegmentation:
    """Verifies deep learning semantic segmentation CLI invocation."""

    def test_infer_segmentation_sample_image(self, tmp_path):
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        out_dir = tmp_path / "infer_out"
        code = main([
            "infer-segmentation",
            "--input", str(sample_img),
            "--output-dir", str(out_dir),
            "--checkpoint", str(BEST_MODEL_DIR),
            "--device", "cpu",
        ])
        assert code == EXIT_SUCCESS
        summary_file = out_dir / f"{sample_img.stem}_summary.json"
        assert summary_file.is_file()
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "success"

    def test_infer_segmentation_missing_checkpoint_returns_1(self, tmp_path):
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        out_dir = tmp_path / "infer_out"
        fake_ckpt = tmp_path / "fake_ckpt"
        fake_ckpt.mkdir()
        code = main([
            "infer-segmentation",
            "--input", str(sample_img),
            "--output-dir", str(out_dir),
            "--checkpoint", str(fake_ckpt),
            "--device", "cpu",
        ])
        assert code == EXIT_ERROR


class TestCLIRunPipelineEndToEnd:
    """Verifies full end-to-end multi-modal pipeline execution and artifact delivery."""

    def test_run_pipeline_vector_first_sheet_a101(self, tmp_path):
        out_dir = tmp_path / "pipeline_out"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
        ])
        assert code == EXIT_SUCCESS
        # Check deliverables exist
        annotated_pdf = list(out_dir.glob("*.pdf"))
        assert len(annotated_pdf) > 0
        geojson = list(out_dir.glob("*.geojson"))
        assert len(geojson) > 0
        summary_json = out_dir / "pipeline_summary.json"
        assert summary_json.is_file()

    def test_run_pipeline_review_lock_active_exit_2(self, tmp_path):
        out_dir = tmp_path / "pipeline_lock_out"
        missing_csv = tmp_path / "missing_schedule.csv"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(missing_csv),
        ])
        assert code == EXIT_REVIEW_REQUIRED

    def test_run_pipeline_cmu_veto_enforced_in_geojson(self, tmp_path):
        out_dir = tmp_path / "pipeline_cmu_out"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
        ])
        assert code == EXIT_SUCCESS
        geojson_path = list(out_dir.glob("*takeoff.geojson"))[0]
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for feature in data["features"]:
            props = feature["properties"]
            if props.get("matched_tag") == "1A":
                assert props["classification"] == "Non-Drywall"
                assert props["color_hex"] == "#D50000"

    def test_run_pipeline_modality_override_raster_ml(self, tmp_path):
        # Create a small synthetic 1-page PDF for fast ML modality execution
        doc = fitz.open()
        page = doc.new_page(width=200.0, height=300.0)
        page.draw_rect(fitz.Rect(20, 20, 80, 150), fill=(0, 0, 0))
        syn_pdf = tmp_path / "syn_raster.pdf"
        doc.save(str(syn_pdf))
        doc.close()

        out_dir = tmp_path / "pipeline_raster_out"
        code = main([
            "run-pipeline",
            "--pdf", str(syn_pdf),
            "--pages", "0",
            "--output-dir", str(out_dir),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--force-modality", "RASTER_ML",
            "--device", "cpu",
            "--dpi", "72",
        ])
        assert code == EXIT_SUCCESS
        assert (out_dir / "pipeline_summary.json").is_file()


class TestCLIExecutionEntrypoint:
    """Verifies that the package is executable as a top-level module via python -m drywall_detection."""

    def test_python_module_execution_subprocess(self):
        cmd = [sys.executable, "-m", "drywall_detection", "info", "--json"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0, f"Module execution failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["version"] == __version__

    def test_help_execution_subprocess(self):
        cmd = [sys.executable, "-m", "drywall_detection", "--help"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0
        assert "Drywall Detection & Takeoff Engine" in result.stdout
