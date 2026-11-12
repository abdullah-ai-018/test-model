"""
Adversarial stress-test suite for Milestone M1 (Dataset Auditor and Hardware Utilities).
Written by challenger_m1_2 to empirically stress-test boundary conditions, threshold
bypasses, non-existent drives, full disks, negative allocations, and extreme hardware profiles.
"""

from __future__ import annotations
from dataclasses import FrozenInstanceError
import math
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from drywall_detection.audit.dataset_auditor import (
    CANDIDATE_DATASETS,
    DatasetAuditor,
    DatasetEligibility,
    DatasetSpec,
    LicenseCategory,
)
from drywall_detection.utils.hardware import (
    HardwareProfile,
    TrainingConfig,
    auto_configure_training,
    check_disk_safety,
    probe_disk,
)


@pytest.fixture
def auditor():
    return DatasetAuditor(offline_mode=True)


class Test10GBThresholdAdversarialBypass:
    """Stress tests probing the 10 GB unannounced download ceiling."""

    def test_9_9999_vs_10_0000_vs_10_0001_gb(self, auditor):
        """Precision test on 10 GB threshold boundary."""
        res_below = auditor.check_download_threshold(9.9999)
        assert res_below.warning_triggered is False
        assert res_below.requires_user_confirmation is False

        res_exact = auditor.check_download_threshold(10.0000)
        assert res_exact.warning_triggered is False
        assert res_exact.requires_user_confirmation is False

        res_above = auditor.check_download_threshold(10.0001)
        assert res_above.warning_triggered is True
        assert res_above.requires_user_confirmation is True
        assert "ALERT" in res_above.warning_message

    def test_r2v_triggers_10gb_warning(self, auditor):
        """
        Hardened: R2V download specification (10.000 GB raw, 20.000 GB extracted)
        must trigger the >= 10 GB notification threshold.
        """
        r2v_spec = auditor.get_spec("r2v")
        assert r2v_spec.raw_size_gb >= 10.0 or r2v_spec.extracted_size_gb > 10.0

        disk_res = auditor.check_disk_space("r2v")
        assert disk_res.exceeds_10gb_threshold is True

        res = auditor.audit_candidate("r2v")
        assert res.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in res.warnings)

    def test_cubicasa5k_large_extraction_triggers_warning(self, auditor):
        """
        Hardened: CubiCasa5K extracted size is 20.0 GB (or 21.47 GB, > 10 GB threshold).
        audit_candidate('cubicasa5k') must check extraction footprint, set
        exceeds_10gb_threshold = True, and emit a LARGE EXTRACTION warning.
        """
        res = auditor.audit_candidate("cubicasa5k")
        assert res.dataset_spec.extracted_size_gb > 10.0
        assert res.disk_audit.exceeds_10gb_threshold is True
        assert any("10" in w for w in res.warnings)
        assert any("extract" in w.lower() for w in res.warnings)


class TestDiskHeadroomAdversarialStress:
    """Stress tests on non-existent drives, full disk, negative space, and boundary margins."""

    def test_nonexistent_drive_handling(self, auditor):
        r"""Non-existent drive Z:\ gracefully reports 0 GB free and insufficient space for downloads."""
        res = auditor.check_disk_space(required_gb_or_id=1.0, target_path=r"Z:\nonexistent\store")
        assert res.free_gb == 0.0
        assert res.is_sufficient is False
        assert "insufficient" in res.message.lower()

        safe, free, msg = check_disk_safety(1.0, disk_path=r"Z:\nonexistent\store")
        assert free == 0.0
        assert safe is False
        assert "insufficient" in msg.lower()

    def test_simulated_completely_full_disk(self, auditor):
        """A completely full disk (free = 0) rejects any download attempt."""
        with patch("shutil.disk_usage", return_value=MagicMock(total=100 * 1024**3, used=100 * 1024**3, free=0)):
            res = auditor.check_disk_space(required_gb_or_id=0.1)
            assert res.is_sufficient is False
            assert res.free_gb == 0.0

            safe, free, msg = check_disk_safety(0.1)
            assert safe is False
            assert free == 0.0

    def test_simulated_negative_free_space(self, auditor):
        """Negative free space (e.g. -10 GB from corrupted disk API) is rejected."""
        with patch("shutil.disk_usage", return_value=MagicMock(total=100 * 1024**3, used=110 * 1024**3, free=-10 * 1024**3)):
            res = auditor.check_disk_space(required_gb_or_id=1.0)
            assert res.is_sufficient is False

            safe, free, msg = check_disk_safety(1.0)
            assert safe is False

    def test_negative_required_gb_raises_value_error(self, auditor):
        r"""
        Hardened: Passing negative required_gb to check_disk_space or check_disk_safety
        must raise ValueError rather than fabricating artificial headroom.
        """
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-5.0, target_path=r"Z:\nonexistent")

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            auditor.check_disk_space(required_gb_or_id=-0.0001)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(-6.0, disk_path=r"Z:\nonexistent")

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(-0.001)

    def test_exact_headroom_boundary_and_single_byte_drop(self, auditor):
        """Exact headroom boundary (free - required == headroom) passes; 1 byte less fails."""
        # 5.0 GB free, 3.0 GB required, 2.0 GB headroom -> exactly 2.0 GB remaining
        with patch("shutil.disk_usage", return_value=MagicMock(total=100 * 1024**3, used=95 * 1024**3, free=5 * 1024**3)):
            res_pass = auditor.check_disk_space(required_gb_or_id=3.0, min_headroom_gb=2.0)
            assert res_pass.is_sufficient is True

        # 1 byte less free space fails headroom
        with patch("shutil.disk_usage", return_value=MagicMock(total=100 * 1024**3, used=95 * 1024**3 + 1, free=5 * 1024**3 - 1)):
            res_fail = auditor.check_disk_space(required_gb_or_id=3.0, min_headroom_gb=2.0)
            assert res_fail.is_sufficient is False
            assert "headroom" in res_fail.message.lower()


class TestAuditorInputsAndNetworkFaults:
    """Stress tests on malformed inputs, corrupted metadata, and HTTP errors."""

    def test_probe_url_http_404_and_500(self, auditor):
        """probe_url handles 404 and 500 without crashing."""
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://u.rl/404", 404, "Not Found", {}, None)):
            res = auditor.probe_url("http://u.rl/404")
            assert res["is_reachable"] is False
            assert res["http_status"] == 404

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://u.rl/500", 500, "Server Error", {}, None)):
            res = auditor.probe_url("http://u.rl/500")
            assert res["is_reachable"] is False
            assert res["http_status"] == 500

    def test_probe_url_double_403_failure(self, auditor):
        """When HEAD fails 403 and fallback GET also fails 403, returns is_reachable False."""
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://u.rl/403", 403, "Forbidden", {}, None)):
            res = auditor.probe_url("http://u.rl/403")
            assert res["is_reachable"] is False
            assert res["http_status"] == 403

    def test_probe_url_invalid_schemes_and_empty(self, auditor):
        """probe_url safely handles completely invalid URL schemes and empty strings."""
        for bad_url in ["", "not_a_valid_url", "ftp://test.com", "file:///invalid"]:
            res = auditor.probe_url(bad_url)
            assert res["is_reachable"] is False

    def test_audit_candidate_invalid_types_raise(self, auditor):
        """audit_candidate raises clean KeyError on unknown IDs and AttributeError on None."""
        with pytest.raises(KeyError):
            auditor.audit_candidate("non_existent_dataset_12345")

        with pytest.raises(AttributeError):
            auditor.audit_candidate(None)


class TestR2VAndSESYDZeroToleranceGuards:
    """Rigorous verification that R2V is NEVER downloadable and SESYD is NEVER wall-approved."""

    def test_r2v_immutable_and_permanently_ineligible(self, auditor):
        """R2V spec is frozen and its verdict is permanently INELIGIBLE_FOR_AUTOMATED_DOWNLOAD."""
        spec = auditor.get_spec("r2v")
        with pytest.raises(FrozenInstanceError):
            spec.eligibility = DatasetEligibility.ELIGIBLE

        res = auditor.audit_candidate("r2v")
        assert res.eligibility_verdict == "INELIGIBLE_FOR_AUTOMATED_DOWNLOAD"
        assert res.is_downloadable_now is False
        assert any("restricted access" in b.lower() for b in res.blockers)

        with pytest.raises(PermissionError, match="AUTOMATED ACCESS FORBIDDEN"):
            auditor.prepare_dataset("r2v")

    def test_sesyd_immutable_and_permanently_ineligible_for_walls(self, auditor):
        """SESYD spec is frozen and its verdict is permanently INELIGIBLE_FOR_WALL_SEGMENTATION."""
        spec = auditor.get_spec("sesyd")
        with pytest.raises(FrozenInstanceError):
            spec.has_wall_segmentation_labels = True

        res = auditor.audit_candidate("sesyd")
        assert res.eligibility_verdict == "INELIGIBLE_FOR_WALL_SEGMENTATION"
        assert res.is_downloadable_now is False
        assert res.has_wall_annotations is False
        assert any("zero wall" in b.lower() for b in res.blockers)


class TestHardwareAutoConfigStress:
    """Stress tests on auto_configure_training with extreme hardware profiles."""

    def test_zero_ram_falls_into_tier5_safely(self):
        """Simulated 0 RAM falls into Tier 5 without division by zero."""
        cfg = auto_configure_training({"cuda_available": False, "ram_available_gb": 0.0})
        assert cfg.hardware_tier == 5
        assert cfg.batch_size == 2
        assert cfg.img_size == 256
        assert cfg.num_workers == 0

    def test_extreme_gpu_vram_tier1(self):
        """Simulated 80 GB / 1000 GB VRAM scales properly into Tier 1."""
        for vram in [80.0, 1000.0]:
            cfg = auto_configure_training({"cuda_available": True, "vram_total_gb": vram, "cpu_logical_cores": 32})
            assert cfg.hardware_tier == 1
            assert cfg.batch_size == 16
            assert cfg.img_size == 512
            assert cfg.num_workers == 4

    def test_single_core_cpu_behaviors(self):
        """CPU with 1 core produces 0 workers in Tier 4 and 2 workers in Tier 1."""
        cfg_cpu = auto_configure_training({"cuda_available": False, "ram_available_gb": 8.0, "cpu_logical_cores": 1})
        assert cfg_cpu.hardware_tier == 4
        assert cfg_cpu.num_workers == 0

        cfg_gpu = auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": 1})
        assert cfg_gpu.hardware_tier == 1
        assert cfg_gpu.num_workers == 2  # min(4, max(2, 1))

    def test_nan_vram_falls_to_tier5(self):
        """NaN VRAM falls through all float comparisons safely into Tier 5."""
        cfg = auto_configure_training({"cuda_available": True, "vram_total_gb": float("nan")})
        assert cfg.hardware_tier == 5
        assert cfg.device == "cpu"

    def test_explicit_none_dictionary_safe_fallback(self):
        """
        Hardened: Passing explicit None in profile dictionary safely falls back to defaults
        without raising TypeError.
        """
        # None VRAM with CUDA True safely falls back to 0.0 VRAM (CPU or safe low Tier)
        cfg1 = auto_configure_training({"cuda_available": True, "vram_total_gb": None})
        assert isinstance(cfg1, TrainingConfig)
        assert cfg1.device in ("cpu", "cuda")

        # None RAM safely falls back to default RAM
        cfg2 = auto_configure_training({"cuda_available": False, "ram_available_gb": None})
        assert isinstance(cfg2, TrainingConfig)
        assert cfg2.device == "cpu"
        assert cfg2.hardware_tier == 4

        # None cpu_logical_cores safely falls back to default cores
        cfg3 = auto_configure_training({"cuda_available": True, "vram_total_gb": 16.0, "cpu_logical_cores": None})
        assert isinstance(cfg3, TrainingConfig)
        assert cfg3.hardware_tier == 1
        assert cfg3.num_workers >= 2

        # All None profile safely yields Tier 5 or Tier 4 default config
        all_none = {
            "cuda_available": None,
            "vram_total_gb": None,
            "ram_available_gb": None,
            "ram_total_gb": None,
            "cpu_logical_cores": None,
        }
        cfg4 = auto_configure_training(all_none)
        assert isinstance(cfg4, TrainingConfig)
        assert cfg4.device == "cpu"
        assert cfg4.batch_size in (2, 4)
