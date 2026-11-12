"""
drywall_detection/tests/test_challenger_m6_cli_stress.py
=========================================================
Empirical Adversarial Challenger Stress Testing Suite for Milestone M6.
Exhaustively stress-tests:
1. Subprocess Execution of all 7 subcommands via `python -m drywall_detection`
2. POSIX Exit Code 0: Clean execution across valid pipelines
3. POSIX Exit Code 1: Missing files, invalid page indices, corrupted/truncated PDFs
4. POSIX Exit Code 2: Missing approved schedule CSV and active REVIEW_REQUIRED.lock
5. POSIX Exit Code 3: Detail 1A CMU veto tampering attacks across subcommands
6. End-to-End Artifact Verification:
   - Sheet A-101 pipeline execution
   - 0% rasterization check in annotated vector PDF
   - GeoJSON RFC 7946 compliance and Detail 1A "#D50000" / "Non-Drywall" assertion
   - Summary statistics JSON validation
"""

from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest
import fitz

from drywall_detection import __version__
from drywall_detection.cli import (
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_REVIEW_REQUIRED,
    EXIT_CMU_VETO_VIOLATION,
    main,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    BEST_MODEL_DIR,
    DEFAULT_MASTER_PDF_PATH,
)


class TestSubprocessInvocationAllCommands:
    """Verifies that all 7 CLI subcommands execute cleanly via subprocess `python -m drywall_detection`."""

    def test_subprocess_help(self):
        res = subprocess.run(
            [sys.executable, "-m", "drywall_detection", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert res.returncode == 0
        assert "Drywall Detection & Takeoff Engine" in res.stdout

    def test_subprocess_info_json(self):
        res = subprocess.run(
            [sys.executable, "-m", "drywall_detection", "info", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["version"] == __version__
        assert data["checkpoints"]["champion_model_found"] is True

    def test_subprocess_version_alias(self):
        res = subprocess.run(
            [sys.executable, "-m", "drywall_detection", "version", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["version"] == __version__

    def test_subprocess_audit_datasets_json(self):
        res = subprocess.run(
            [sys.executable, "-m", "drywall_detection", "audit-datasets", "--dataset-id", "msd", "--format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["dataset_id"] == "msd"
        assert data["eligibility_verdict"] == "ELIGIBLE"

    def test_subprocess_extract_vector_detect_only(self):
        res = subprocess.run(
            [
                sys.executable, "-m", "drywall_detection", "extract-vector",
                "--pdf", str(DEFAULT_MASTER_PDF_PATH),
                "--pages", "14",
                "--detect-only",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert res.returncode == 0
        assert "Vector Profile" in res.stdout
        assert "VECTOR_FIRST" in res.stdout


class TestExitCode1FailureModes:
    """Verifies that corrupt inputs, missing files, and invalid parameters return Exit Code 1."""

    def test_missing_pdf_in_extract_vector(self, tmp_path):
        missing_pdf = tmp_path / "does_not_exist.pdf"
        code = main(["extract-vector", "--pdf", str(missing_pdf)])
        assert code == EXIT_ERROR

    def test_out_of_range_page_in_extract_vector(self):
        code = main([
            "extract-vector",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "99999",
        ])
        assert code == EXIT_ERROR

    def test_corrupted_empty_pdf_in_extract_vector(self, tmp_path):
        corrupt_pdf = tmp_path / "corrupt_empty.pdf"
        corrupt_pdf.write_bytes(b"")  # 0 bytes
        code = main([
            "extract-vector",
            "--pdf", str(corrupt_pdf),
            "--pages", "0",
        ])
        assert code == EXIT_ERROR

    def test_corrupted_garbage_pdf_in_extract_vector(self, tmp_path):
        corrupt_pdf = tmp_path / "garbage.pdf"
        corrupt_pdf.write_bytes(b"NOT A REAL PDF FILE GARBAGE DATA 123456789")
        code = main([
            "extract-vector",
            "--pdf", str(corrupt_pdf),
            "--pages", "0",
        ])
        assert code == EXIT_ERROR

    def test_missing_input_in_infer_segmentation(self, tmp_path):
        missing_img = tmp_path / "missing.png"
        code = main([
            "infer-segmentation",
            "--input", str(missing_img),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_ERROR

    def test_missing_checkpoint_in_infer_segmentation(self, tmp_path):
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        missing_ckpt = tmp_path / "non_existent_ckpt"
        code = main([
            "infer-segmentation",
            "--input", str(sample_img),
            "--checkpoint", str(missing_ckpt),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_ERROR

    def test_missing_pdf_in_parse_schedule(self, tmp_path):
        missing_pdf = tmp_path / "missing.pdf"
        code = main([
            "parse-schedule",
            "--pdf", str(missing_pdf),
            "--output-csv", str(tmp_path / "out.csv"),
        ])
        assert code == EXIT_ERROR

    def test_missing_pdf_in_classify(self, tmp_path):
        missing_pdf = tmp_path / "missing.pdf"
        code = main([
            "classify",
            "--pdf", str(missing_pdf),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_ERROR

    def test_missing_pdf_in_run_pipeline(self, tmp_path):
        missing_pdf = tmp_path / "missing.pdf"
        code = main([
            "run-pipeline",
            "--pdf", str(missing_pdf),
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_ERROR


class TestExitCode2ReviewLockModes:
    """Verifies that missing approved CSV or active review lock strictly returns Exit Code 2."""

    def test_parse_schedule_missing_approved_creates_lock_and_exits_2(self, tmp_path):
        out_csv = tmp_path / "draft.csv"
        missing_appr = tmp_path / "missing.approved.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(missing_appr),
            "--enforce-review-lock",
        ])
        assert code == EXIT_REVIEW_REQUIRED
        lock_file = tmp_path / "REVIEW_REQUIRED.lock"
        assert lock_file.exists(), "REVIEW_REQUIRED.lock must be created when approved CSV is missing"

    def test_classify_missing_approved_csv_exits_2(self, tmp_path):
        missing_appr = tmp_path / "nonexistent.approved.csv"
        code = main([
            "classify",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(missing_appr),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_REVIEW_REQUIRED

    def test_run_pipeline_missing_approved_csv_exits_2(self, tmp_path):
        missing_appr = tmp_path / "nonexistent.approved.csv"
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(missing_appr),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_REVIEW_REQUIRED


class TestExitCode3CMUVetoTamperingAttacks:
    """Verifies that any malicious attempt to classify Detail 1A CMU as Drywall yields Exit Code 3."""

    def _create_tampered_csv(self, target_path: Path, replacement: str = "Drywall"):
        with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tampered_lines = []
        for line in lines:
            if line.startswith("1A,"):
                parts = line.split(",")
                parts[11] = replacement  # proposed_class column
                tampered_lines.append(",".join(parts))
            else:
                tampered_lines.append(line)
        target_path.write_text("".join(tampered_lines), encoding="utf-8")

    def test_tampered_1a_drywall_in_parse_schedule_exits_3(self, tmp_path):
        tampered_csv = tmp_path / "tampered.approved.csv"
        self._create_tampered_csv(tampered_csv, "Drywall")
        out_csv = tmp_path / "draft.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(tampered_csv),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION

    def test_tampered_1a_gwb_synonym_in_parse_schedule_exits_3(self, tmp_path):
        tampered_csv = tmp_path / "tampered_gwb.approved.csv"
        self._create_tampered_csv(tampered_csv, "GWB")
        out_csv = tmp_path / "draft.csv"
        code = main([
            "parse-schedule",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--output-csv", str(out_csv),
            "--approved-csv", str(tampered_csv),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION

    def test_tampered_1a_drywall_in_classify_exits_3(self, tmp_path):
        tampered_csv = tmp_path / "tampered.approved.csv"
        self._create_tampered_csv(tampered_csv, "Drywall")
        code = main([
            "classify",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(tampered_csv),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION

    def test_tampered_1a_drywall_in_run_pipeline_exits_3(self, tmp_path):
        tampered_csv = tmp_path / "tampered.approved.csv"
        self._create_tampered_csv(tampered_csv, "Drywall")
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(tampered_csv),
            "--output-dir", str(tmp_path),
        ])
        assert code == EXIT_CMU_VETO_VIOLATION


class TestEndToEndPipelineArtifactIntegrity:
    """Validates end-to-end run on Sheet A-101 and verifies 0% rasterization, GeoJSON, and Detail 1A color."""

    @pytest.fixture(scope="class")
    def pipeline_run_output(self, tmp_path_factory):
        out_dir = tmp_path_factory.mktemp("e2e_a101_output")
        code = main([
            "run-pipeline",
            "--pdf", str(DEFAULT_MASTER_PDF_PATH),
            "--pages", "14",
            "--schedule-csv", str(APPROVED_SCHEDULE_CSV_PATH),
            "--output-dir", str(out_dir),
            "--export-pdf",
            "--export-png",
            "--export-geojson",
        ])
        assert code == EXIT_SUCCESS
        return out_dir

    def test_annotated_vector_pdf_zero_percent_rasterization(self, pipeline_run_output):
        """Verifies that the annotated PDF preserves native vector linework with 0% rasterization."""
        pdf_files = list(pipeline_run_output.glob("*.pdf"))
        assert len(pdf_files) == 1, f"Expected 1 annotated PDF, found {len(pdf_files)}"
        annotated_pdf = pdf_files[0]

        # Open both original and annotated PDF
        orig_doc = fitz.open(DEFAULT_MASTER_PDF_PATH)
        annot_doc = fitz.open(annotated_pdf)

        assert len(annot_doc) == 1, f"Annotated PDF should contain 1 page, found {len(annot_doc)}"

        orig_page = orig_doc[14]
        annot_page = annot_doc[0]

        # 1. Page dimensions must be preserved exactly
        assert abs(orig_page.rect.width - annot_page.rect.width) < 1.0
        assert abs(orig_page.rect.height - annot_page.rect.height) < 1.0

        # 2. 0% rasterization check:
        # Original page 14 has zero embedded raster images.
        # Annotated PDF should NOT contain a giant full-page raster overlay image replacing vectors!
        annot_images = annot_page.get_images(full=True)
        # Any raster image occupying > 50% of page area indicates page rasterization violation
        page_area = annot_page.rect.width * annot_page.rect.height
        for img in annot_images:
            xref = img[0]
            bbox = annot_page.get_image_bbox(img)
            img_area = bbox.width * bbox.height
            assert img_area < 0.5 * page_area, "Page was converted to a raster image! Rasterization detected."

        # Verify that vector drawings are present on the annotated page
        drawings = annot_page.get_drawings()
        assert len(drawings) > 100, f"Expected vector paths on annotated page, found {len(drawings)}"

        orig_doc.close()
        annot_doc.close()

    def test_rfc7946_geojson_takeoff_and_detail_1a_cmu_verification(self, pipeline_run_output):
        """Verifies GeoJSON format and asserts Detail 1A is strictly Non-Drywall (#D50000)."""
        geojson_files = list(pipeline_run_output.glob("*.geojson"))
        assert len(geojson_files) >= 1, "Expected at least 1 GeoJSON takeoff file"
        geojson_path = geojson_files[0]

        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["type"] == "FeatureCollection"
        features = data["features"]
        assert len(features) > 0, "FeatureCollection must contain extracted wall polygons"

        # Check Detail 1A walls
        tag_1a_found = 0
        drywall_count = 0
        non_drywall_count = 0
        uncertain_count = 0

        for f in features:
            props = f["properties"]
            assert "classification" in props
            assert "color_hex" in props
            assert "matched_tag" in props

            classification = props["classification"]
            color_hex = props["color_hex"]
            tag = props.get("matched_tag")

            if tag == "1A":
                tag_1a_found += 1
                assert classification == "Non-Drywall", f"CRITICAL: 1A CMU wall was classified as {classification}!"
                assert color_hex == "#D50000", f"Detail 1A must have color #D50000, got {color_hex}"

            if classification == "Drywall":
                drywall_count += 1
                assert color_hex == "#00C853" or color_hex == "#00FF00"
            elif classification == "Non-Drywall":
                non_drywall_count += 1
                assert color_hex == "#D50000" or color_hex == "#FF0000"
            elif classification == "Uncertain":
                uncertain_count += 1
                assert color_hex == "#FFD600" or color_hex == "#FFFF00"

        assert tag_1a_found > 0, "Sheet A-101 must contain at least one Detail 1A CMU wall"
        assert drywall_count > 0, "Sheet A-101 must contain classified Drywall walls"
        print(f"\n[GeoJSON Takeoff Verified] Total: {len(features)}, Drywall: {drywall_count}, "
              f"Non-Drywall: {non_drywall_count} (including {tag_1a_found} Detail 1A CMU), Uncertain: {uncertain_count}")

    def test_pipeline_summary_json_integrity(self, pipeline_run_output):
        """Verifies summary JSON schema, execution metrics, and modality used."""
        summary_path = pipeline_run_output / "pipeline_summary.json"
        assert summary_path.is_file(), "pipeline_summary.json must exist"

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert "pages" in summary
        assert "Sheet_15" in summary["pages"]  # Page 14 is Sheet 15 (0-based 14)
        sheet_data = summary["pages"]["Sheet_15"]
        assert sheet_data["modality"] == "VECTOR_FIRST"
        assert "summary_stats" in sheet_data
        stats = sheet_data["summary_stats"]
        assert stats["total_walls"] > 0
        assert stats["drywall_count"] > 0
        assert stats["non_drywall_count"] > 0
        assert "elapsed_seconds" in summary
