"""
Unit tests for hardware probing, disk safety, and dynamic training configuration.
Verifies system resource detection across CPU, RAM, GPU, disk, and Python libraries,
as well as the 5-tier dynamic configuration engine.
"""

from __future__ import annotations
import math
from unittest.mock import MagicMock, patch
import pytest

from drywall_detection.utils.hardware import (
    HardwareProfile,
    TrainingConfig,
    auto_configure_training,
    check_disk_safety,
    get_training_auto_config,
    probe_all_hardware,
    probe_cpu,
    probe_disk,
    probe_gpu,
    probe_hardware,
    probe_ram,
    probe_software_environment,
)


class TestHardwareProbingUnits:
    """Test suite for individual hardware and software probing functions."""

    def test_probe_cpu_live(self):
        """CPU probe must return valid core counts, model string, and architecture."""
        cpu = probe_cpu()
        assert "physical_cores" in cpu
        assert "logical_cores" in cpu
        assert "processor" in cpu
        assert "architecture" in cpu
        assert cpu["physical_cores"] >= 1
        assert cpu["logical_cores"] >= cpu["physical_cores"]
        assert isinstance(cpu["architecture"], str) and len(cpu["architecture"]) > 0

    def test_probe_ram_live(self):
        """RAM probe must report total, available, used memory in GB and percent used."""
        ram = probe_ram()
        assert "total_gb" in ram
        assert "available_gb" in ram
        assert "used_gb" in ram
        assert "percent_used" in ram
        assert ram["total_gb"] > 0.0
        assert ram["available_gb"] >= 0.0
        assert ram["used_gb"] > 0.0
        assert 0.0 <= ram["percent_used"] <= 100.0

    def test_probe_disk_live(self):
        """Disk probe must report valid drive letter and positive storage metrics."""
        disk = probe_disk(".")
        assert "drive" in disk
        assert "total_gb" in disk
        assert "used_gb" in disk
        assert "free_gb" in disk
        assert "percent_free" in disk
        assert disk["total_gb"] > 0.0
        assert disk["free_gb"] > 0.0

    @patch("torch.cuda.is_available", return_value=False)
    def test_probe_gpu_cpu_only_mock(self, mock_cuda):
        """When CUDA is unavailable, GPU probe reports 0 devices and 0 VRAM."""
        gpu = probe_gpu()
        assert gpu["cuda_available"] is False
        assert gpu["device_count"] == 0
        assert gpu["vram_total_gb"] == 0.0
        assert gpu["devices"] == []

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.device_count", return_value=1)
    def test_probe_gpu_cuda_available_mock(self, mock_cnt, mock_avail):
        """When CUDA is available, GPU probe correctly enumerates devices and VRAM."""
        mock_props = MagicMock()
        mock_props.name = "Tesla T4"
        mock_props.total_memory = 16_106_127_360  # 15.0 GB

        with patch("torch.cuda.get_device_properties", return_value=mock_props):
            gpu = probe_gpu()
            assert gpu["cuda_available"] is True
            assert gpu["device_count"] == 1
            assert math.isclose(gpu["vram_total_gb"], 15.0, rel_tol=1e-2)
            assert len(gpu["devices"]) == 1
            assert gpu["devices"][0]["name"] == "Tesla T4"

    def test_probe_software_environment_live(self):
        """Software probe reports Python, PyTorch, and installed core packages."""
        soft = probe_software_environment()
        assert "python_version" in soft
        assert "torch_version" in soft
        assert "installed_packages" in soft
        assert soft["python_version"].startswith("3.10")
        packages = soft["installed_packages"]
        for required_pkg in ["shapely", "torch", "numpy"]:
            assert required_pkg in packages

    def test_probe_all_hardware_live(self):
        """Combined hardware probe returns all probe sections."""
        all_hw = probe_all_hardware()
        assert "cpu" in all_hw
        assert "ram" in all_hw
        assert "gpu" in all_hw
        assert "disk" in all_hw
        assert "software" in all_hw

    def test_probe_hardware_real_system(self):
        """probe_hardware returns a populated HardwareProfile dataclass."""
        profile = probe_hardware()
        assert isinstance(profile, HardwareProfile)
        assert profile.cpu_logical_cores >= 1
        assert profile.ram_total_gb > 0.0
        assert profile.disk_free_gb > 0.0
        assert isinstance(profile.to_dict(), dict)

    def test_hardware_profile_markdown_table(self):
        """HardwareProfile formats cleanly as a Markdown specification table."""
        profile = probe_hardware()
        table = profile.to_markdown_table()
        assert "| Resource | Detected Specification |" in table
        assert "| Host OS |" in table
        assert "| System RAM |" in table
        assert "| PyTorch Runtime |" in table


class TestTrainingAutoConfiguration:
    """Test suite for the 5-tier dynamic configuration engine."""

    def test_auto_config_tier1_high_gpu(self):
        """Tier 1: Dedicated GPU with >= 14 GB VRAM -> batch size 16, 512x512, FP16."""
        mock_profile = {
            "cuda_available": True,
            "vram_total_gb": 16.0,
            "ram_available_gb": 16.0,
            "cpu_logical_cores": 8,
        }
        cfg = auto_configure_training(mock_profile)
        assert cfg.device == "cuda"
        assert cfg.batch_size == 16
        assert cfg.img_size == 512
        assert cfg.use_amp is True
        assert cfg.num_workers >= 2
        assert cfg.colab_recommended is False
        assert cfg.hardware_tier == 1

    def test_auto_config_tier2_mid_gpu(self):
        """Tier 2: GPU with 6-14 GB VRAM (e.g. T4) -> batch size 8, grad accum 2, 512x512."""
        mock_profile = {
            "cuda_available": True,
            "vram_total_gb": 8.0,
            "ram_available_gb": 12.0,
            "cpu_logical_cores": 4,
        }
        cfg = auto_configure_training(mock_profile)
        assert cfg.device == "cuda"
        assert cfg.batch_size == 8
        assert cfg.gradient_accumulation_steps == 2
        assert cfg.effective_batch_size == 16
        assert cfg.img_size == 512
        assert cfg.use_amp is True
        assert cfg.hardware_tier == 2

    def test_auto_config_tier3_low_gpu(self):
        """Tier 3: Low VRAM GPU (< 6 GB) -> batch size 4, 384x384, Colab recommended."""
        mock_profile = {
            "cuda_available": True,
            "vram_total_gb": 4.0,
            "ram_available_gb": 8.0,
            "cpu_logical_cores": 4,
        }
        cfg = auto_configure_training(mock_profile)
        assert cfg.device == "cuda"
        assert cfg.batch_size == 4
        assert cfg.img_size == 384
        assert cfg.colab_recommended is True
        assert cfg.hardware_tier == 3

    def test_auto_config_tier4_cpu_high_ram(self):
        """Tier 4: CPU with >= 4 GB RAM -> batch size 4, 256x256, Colab recommended."""
        mock_profile = {
            "cuda_available": False,
            "vram_total_gb": 0.0,
            "ram_available_gb": 8.0,
            "cpu_logical_cores": 8,
        }
        cfg = auto_configure_training(mock_profile)
        assert cfg.device == "cpu"
        assert cfg.batch_size == 4
        assert cfg.img_size == 256
        assert cfg.use_amp is False
        assert cfg.hardware_tier == 4

    def test_auto_config_tier5_constrained_host(self):
        """Tier 5: Constrained Host (CPU, < 2.0 GB free RAM) -> batch size 2, 0 workers, 256x256."""
        mock_profile = {
            "cuda_available": False,
            "vram_total_gb": 0.0,
            "ram_available_gb": 0.85,
            "cpu_logical_cores": 8,
        }
        cfg = auto_configure_training(mock_profile)
        assert cfg.device == "cpu"
        assert cfg.batch_size == 2
        assert cfg.num_workers == 0
        assert cfg.img_size == 256
        assert cfg.gradient_accumulation_steps == 8
        assert cfg.effective_batch_size == 16
        assert cfg.is_local_constrained is True
        assert cfg.colab_recommended is True
        assert "Google Colab" in cfg.recommendation_message
        assert cfg.hardware_tier == 5

    def test_get_training_auto_config_dict_wrapper(self):
        """get_training_auto_config returns dictionary matching TrainingConfig fields."""
        cfg_dict = get_training_auto_config()
        assert isinstance(cfg_dict, dict)
        assert "device" in cfg_dict
        assert "batch_size" in cfg_dict
        assert "img_size" in cfg_dict
        assert "recommendation_message" in cfg_dict

    def test_auto_configure_training_none_values_resilience(self):
        """auto_configure_training must withstand dictionary keys containing explicit None values."""
        profiles = [
            {"cuda_available": None, "vram_total_gb": None},
            {"ram_available_gb": None, "ram_total_gb": None},
            {"cpu_logical_cores": None},
            {"cuda_available": None, "vram_total_gb": None, "ram_available_gb": None, "cpu_logical_cores": None},
        ]
        for p in profiles:
            cfg = auto_configure_training(p)
            assert isinstance(cfg, TrainingConfig)
            assert cfg.batch_size in (2, 4, 8, 16)
            assert cfg.img_size in (256, 384, 512)


class TestDiskSafetyGuards:
    """Test suite for disk space checking and 10 GB download warnings."""

    def test_check_disk_safety_sufficient(self):
        """Small download requirement on live disk returns safe OK."""
        is_safe, free_gb, msg = check_disk_safety(required_gb=0.1)
        assert is_safe is True
        assert free_gb > 0.0
        assert "OK" in msg

    def test_check_disk_safety_insufficient(self):
        """Astronomical download requirement returns safe=False and REJECTED."""
        is_safe, free_gb, msg = check_disk_safety(required_gb=999_999.0)
        assert is_safe is False
        assert "REJECTED" in msg

    def test_check_disk_safety_10gb_warning_threshold(self):
        """Download exceeding 10 GB triggers mandatory user notification warning."""
        _, _, msg = check_disk_safety(required_gb=12.5)
        assert "WARNING" in msg
        assert "10.0 GB" in msg

    def test_check_disk_safety_negative_required_raises_value_error(self):
        """check_disk_safety rejects negative required space with ValueError."""
        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(required_gb=-5.0)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(required_gb=-0.01)

        with pytest.raises(ValueError, match=r"(?i)non-negative"):
            check_disk_safety(-1.0)
