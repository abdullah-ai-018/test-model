"""
Unit tests for DatasetAuditor, licensing compliance, disk safety, and report generation.
Verifies audit criteria for all 6 candidate datasets (MSD, CubiCasa5K, FloorPlanCAD,
CVC-FP, R2V, SESYD) without network dependencies or unauthorized license acceptance.
"""

from __future__ import annotations
import io
import json
import math
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from drywall_detection.audit.dataset_auditor import (
    DatasetAuditor,
    DatasetAuditResult,
    main,
)


@pytest.fixture
def auditor():
    """Provides an offline-mode DatasetAuditor fixture."""
    return DatasetAuditor(offline_mode=True)


class TestDatasetAuditorCatalog:
    """Test suite for dataset catalog registry and schema coverage."""

    def test_audit_all_catalogs_exact_six_candidates(self, auditor):
        """auditor.audit_all() must catalog exactly the 6 authoritative candidates."""
        report = auditor.audit_all()
        expected_keys = {"cubicasa5k", "floorplancad", "cvc_fp", "r2v", "sesyd", "msd"}
        actual_keys = set(report.keys())
        assert actual_keys == expected_keys
        assert len(report) == 6

    def test_dataset_metadata_schema_fields(self, auditor):
        """Every dataset record must expose complete schema properties."""
        report = auditor.audit_all()
        for did, record in report.items():
            assert isinstance(record.name, str) and len(record.name) > 0
            assert record.official_source_url.startswith("http")
            assert isinstance(record.download_size_gb, float) and record.download_size_gb > 0
            assert isinstance(record.license_name, str) and len(record.license_name) > 0
            assert isinstance(record.is_commercial_allowed, bool)
            assert isinstance(record.has_wall_annotations, bool)
            assert isinstance(record.annotation_format, str) and len(record.annotation_format) > 0
            assert isinstance(record.eligibility_verdict, str) and len(record.eligibility_verdict) > 0
            assert isinstance(record.access_type, str) and len(record.access_type) > 0


class TestDatasetEligibilityVerdicts:
    """Test suite for individual dataset eligibility verdicts and licensing."""

    def test_msd_audit_verdict(self, auditor):
        """Modified Swiss Dwellings must be ELIGIBLE, commercial, and compact (<1 GB)."""
        record = auditor.audit_candidate("msd")
        assert record.eligibility_verdict == "ELIGIBLE"
        assert record.is_commercial_allowed is True
        assert record.has_wall_annotations is True
        assert record.download_size_gb <= 1.0
        assert record.access_type == "PUBLIC_DIRECT"

    def test_cubicasa5k_audit_verdict(self, auditor):
        """CubiCasa5K must be ELIGIBLE, non-commercial, with walls, and ~5.09 GB archive."""
        record = auditor.audit_candidate("cubicasa5k")
        assert record.eligibility_verdict == "ELIGIBLE"
        assert record.is_commercial_allowed is False
        assert record.has_wall_annotations is True
        assert math.isclose(record.download_size_gb, 5.09, rel_tol=0.1)
        assert record.download_size_gb < 10.0
        # Hardened check: CubiCasa5K extracted payload (> 10 GB) triggers warning
        assert record.extracted_size_gb > 10.0
        assert record.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w and "extract" in w.lower() for w in record.warnings)

    def test_floorplancad_audit_verdict(self, auditor):
        """FloorPlanCAD is CONDITIONALLY_ELIGIBLE due to third-party CAD copyright disclaimer."""
        record = auditor.audit_candidate("floorplancad")
        assert record.eligibility_verdict == "CONDITIONALLY_ELIGIBLE"
        assert record.has_wall_annotations is True
        assert "disclaimer" in record.notes.lower() or "disclaimer" in record.license_name.lower()

    def test_cvc_fp_audit_verdict(self, auditor):
        """CVC-FP is CONDITIONALLY_ELIGIBLE due to small size and offline original host with active mirror."""
        record = auditor.audit_candidate("cvc_fp")
        assert record.eligibility_verdict == "CONDITIONALLY_ELIGIBLE"
        assert record.has_wall_annotations is True
        assert "mirror" in record.notes.lower() or "figshare" in record.official_source_url.lower()

    def test_r2v_audit_verdict_ineligible_gated(self, auditor):
        """R2V is INELIGIBLE_FOR_AUTOMATED_DOWNLOAD due to required institutional NII IDR agreement."""
        record = auditor.audit_candidate("r2v")
        assert record.eligibility_verdict == "INELIGIBLE_FOR_AUTOMATED_DOWNLOAD"
        assert record.requires_user_agreement is True
        assert record.access_type == "RESTRICTED_APPLICATION"
        # Hardened check: R2V footprint (>= 10 GB) triggers threshold
        assert record.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in record.warnings)

    def test_sesyd_audit_verdict_ineligible_no_walls(self, auditor):
        """SESYD is INELIGIBLE_FOR_WALL_SEGMENTATION because it contains zero wall labels."""
        record = auditor.audit_candidate("sesyd")
        assert record.eligibility_verdict == "INELIGIBLE_FOR_WALL_SEGMENTATION"
        assert record.has_wall_annotations is False


class TestDiskSafetyAndThresholdGuards:
    """Test suite for free disk space evaluation and 10 GB download thresholds."""

    @patch("shutil.disk_usage")
    def test_disk_space_check_sufficient(self, mock_usage, auditor):
        """20 GB free disk safely accommodates a 5.09 GB download with 2 GB headroom."""
        # usage: (total, used, free)
        mock_usage.return_value = MagicMock(
            total=150 * (1024 ** 3),
            used=130 * (1024 ** 3),
            free=20 * (1024 ** 3),
        )
        res = auditor.check_disk_space(required_gb_or_id=5.09, min_headroom_gb=2.0)
        assert res.is_sufficient is True
        assert math.isclose(res.free_gb, 20.0, rel_tol=1e-2)
        assert math.isclose(res.post_download_headroom_gb, 14.91, rel_tol=1e-2)

    @patch("shutil.disk_usage")
    def test_disk_space_check_insufficient(self, mock_usage, auditor):
        """3 GB free disk fails a 5.09 GB download requirement."""
        mock_usage.return_value = MagicMock(
            total=150 * (1024 ** 3),
            used=147 * (1024 ** 3),
            free=3 * (1024 ** 3),
        )
        res = auditor.check_disk_space(required_gb_or_id=5.09, min_headroom_gb=2.0)
        assert res.is_sufficient is False
        assert "insufficient" in res.message.lower()

    @patch("shutil.disk_usage")
    def test_disk_space_check_headroom_violation(self, mock_usage, auditor):
        """6 GB free disk fails a 5.0 GB download when 2.0 GB headroom is enforced."""
        mock_usage.return_value = MagicMock(
            total=150 * (1024 ** 3),
            used=144 * (1024 ** 3),
            free=6 * (1024 ** 3),
        )
        # Required (5.0) + Headroom (2.0) = 7.0 GB > 6.0 GB available
        res = auditor.check_disk_space(required_gb_or_id=5.0, min_headroom_gb=2.0)
        assert res.is_sufficient is False
        assert "headroom" in res.message.lower()

    def test_10gb_warning_threshold_not_triggered_below_limit(self, auditor):
        """Downloads below 10 GB do not trigger notification warnings."""
        for size in [0.174, 5.09, 9.99]:
            res = auditor.check_download_threshold(size_gb=size)
            assert res.warning_triggered is False
            assert res.requires_user_confirmation is False

    def test_10gb_warning_threshold_triggered_above_limit(self, auditor):
        """Downloads strictly exceeding 10 GB trigger mandatory user notification."""
        for size in [10.01, 15.0, 25.0]:
            res = auditor.check_download_threshold(size_gb=size)
            assert res.warning_triggered is True
            assert res.requires_user_confirmation is True
            assert "10" in res.warning_message.lower()

    def test_10gb_warning_threshold_exact_boundary(self, auditor):
        """Boundary test: 10.0 GB exact does not trigger warning; 10.001 GB does."""
        res_exact = auditor.check_download_threshold(size_gb=10.0)
        assert res_exact.warning_triggered is False

        res_over = auditor.check_download_threshold(size_gb=10.001)
        assert res_over.warning_triggered is True

    def test_check_disk_space_negative_required_raises_value_error(self, auditor):
        """check_disk_space must strictly raise ValueError on negative allocations."""
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-1.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-100.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-0.0001)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id="-10.0")


class TestNetworkAndLicenseMocking:
    """Test suite for URL probing and zero license acceptance guardrails."""

    @patch("urllib.request.urlopen")
    def test_mock_url_probe_success(self, mock_urlopen, auditor):
        """Successful HTTP HEAD probe returns is_reachable True and status 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Length": "182452224"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = auditor.probe_url("https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched")
        assert res["is_reachable"] is True
        assert res["http_status"] == 200

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out"))
    def test_mock_url_probe_timeout_handling(self, mock_urlopen, auditor):
        """Connection timeout is handled gracefully without crashing."""
        res = auditor.probe_url("http://dag.cvc.uab.es/dataset/cvc-fp")
        assert res["is_reachable"] is False
        assert "timed out" in res["error_message"].lower()

    def test_zero_license_acceptance_guard(self, auditor):
        """Attempting to prepare a gated dataset raises PermissionError."""
        with pytest.raises(PermissionError, match="AUTOMATED ACCESS FORBIDDEN"):
            auditor.prepare_dataset("r2v")


class TestReportSerializationAndCLI:
    """Test suite for Markdown/JSON report formatting and CLI execution."""

    def test_generate_markdown_report_structure(self, auditor):
        """Markdown report contains table header and all 6 candidate names."""
        md = auditor.generate_markdown_report()
        assert isinstance(md, str)
        assert "| Dataset | Official Source | Size | License | Wall Labels | Eligibility |" in md
        for name in [
            "Modified Swiss Dwellings",
            "CubiCasa5K",
            "FloorPlanCAD",
            "CVC-FP",
            "R2V",
            "SESYD",
        ]:
            assert name in md

    def test_generate_json_report_structure(self, auditor):
        """JSON report deserializes cleanly and contains 6 dataset records."""
        json_str = auditor.generate_json_report()
        data = json.loads(json_str)
        assert "datasets" in data
        assert len(data["datasets"]) == 6
        assert "msd" in data["datasets"]

    def test_cli_runner_json_output(self, capsys):
        """Running CLI with --format json exits 0 and prints valid JSON to stdout."""
        exit_code = main(["--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "datasets" in data
        assert "msd" in data["datasets"]
