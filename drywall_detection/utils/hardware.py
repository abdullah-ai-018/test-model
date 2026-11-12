"""
Hardware environment detection and dynamic training configuration module.
Probes CPU, RAM, GPU, CUDA, disk space, and runtime libraries, and dynamically
configures training parameters tailored to local or cloud hardware constraints.
"""

from __future__ import annotations
import importlib.metadata
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil
import torch

from drywall_detection.config import (
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
    WORKSPACE_ROOT,
)


class AttrDict(dict):
    """Dictionary subclass supporting dot-notation attribute access."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"No attribute or key '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


@dataclass
class HardwareProfile:
    """Represents a comprehensive snapshot of the host execution environment."""
    cpu_physical_cores: int = 4
    cpu_logical_cores: int = 8
    cpu_model: str = "Host CPU"
    ram_total_gb: float = 16.0
    ram_available_gb: float = 8.0
    ram_used_gb: float = 8.0
    ram_percent: float = 50.0
    cuda_available: bool = False
    gpu_count: int = 0
    gpu_name: Optional[str] = None
    vram_total_gb: float = 0.0
    vram_free_gb: float = 0.0
    disk_path: str = ""
    disk_total_gb: float = 100.0
    disk_free_gb: float = 50.0
    python_version: str = "3.10"
    torch_version: str = "2.1.0"
    torch_cuda_version: Optional[str] = None
    platform_system: str = "Windows"
    platform_release: str = "10"
    cpu_cores_physical: Optional[int] = None
    cpu_cores_logical: Optional[int] = None
    has_cuda: Optional[bool] = None
    gpu_vram_gb: Optional[float] = None

    def __post_init__(self) -> None:
        if self.cpu_cores_physical is not None:
            self.cpu_physical_cores = self.cpu_cores_physical
        else:
            self.cpu_cores_physical = self.cpu_physical_cores

        if self.cpu_cores_logical is not None:
            self.cpu_logical_cores = self.cpu_cores_logical
        else:
            self.cpu_cores_logical = self.cpu_logical_cores

        if self.has_cuda is not None:
            self.cuda_available = self.has_cuda
        else:
            self.has_cuda = self.cuda_available

        if self.gpu_vram_gb is not None:
            self.vram_total_gb = self.gpu_vram_gb
        else:
            self.gpu_vram_gb = self.vram_total_gb

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown_table(self) -> str:
        gpu_desc = (
            f"{self.gpu_name} ({self.vram_total_gb:.2f} GB)"
            if self.cuda_available and self.gpu_name
            else "None (CPU only)"
        )
        return (
            "| Resource | Detected Specification |\n"
            "|---|---|\n"
            f"| Host OS | {self.platform_system} {self.platform_release} ({platform.machine()}) |\n"
            f"| CPU Processor | {self.cpu_model} ({self.cpu_physical_cores}P / {self.cpu_logical_cores}L cores) |\n"
            f"| System RAM | Total: {self.ram_total_gb:.2f} GB, Available: {self.ram_available_gb:.2f} GB ({self.ram_percent}% used) |\n"
            f"| GPU / Acceleration | {gpu_desc} |\n"
            f"| CUDA Support | {'Available' if self.cuda_available else 'Unavailable'} |\n"
            f"| Primary Disk Space | Path: {self.disk_path}, Free: {self.disk_free_gb:.2f} GB / Total: {self.disk_total_gb:.2f} GB |\n"
            f"| Python Runtime | {self.python_version} ({sys.executable}) |\n"
            f"| PyTorch Runtime | {self.torch_version} (CUDA build: {self.torch_cuda_version or 'None'}) |\n"
        )


@dataclass
class TrainingConfig:
    """Auto-configured hyperparameters for segmentation model training."""
    device: str
    batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    image_height: int
    image_width: int
    img_size: int
    num_workers: int
    pin_memory: bool
    mixed_precision: bool
    use_amp: bool
    amp_dtype: str
    encoder_backbone: str
    max_epochs: int
    early_stopping_patience: int
    is_local_constrained: bool
    colab_recommended: bool
    recommendation_message: str
    hardware_tier: int
    tier_description: str
    notes: str
    recommended_architecture: str = "SegFormer-B0"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


# ==============================================================================
# INDIVIDUAL HARDWARE PROBING FUNCTIONS
# ==============================================================================

def probe_cpu() -> AttrDict:
    """Probes host CPU cores, model name, and architecture."""
    phys = psutil.cpu_count(logical=False) or 1
    log = psutil.cpu_count(logical=True) or 1
    return AttrDict({
        "physical_cores": phys,
        "logical_cores": log,
        "processor": platform.processor() or "Unknown CPU",
        "architecture": platform.machine() or "x86_64",
    })


def probe_ram() -> AttrDict:
    """Probes system memory (RAM)."""
    vmem = psutil.virtual_memory()
    return AttrDict({
        "total_gb": round(vmem.total / (1024.0 ** 3), 2),
        "available_gb": round(vmem.available / (1024.0 ** 3), 2),
        "used_gb": round(vmem.used / (1024.0 ** 3), 2),
        "percent_used": float(vmem.percent),
    })


def probe_gpu() -> Dict[str, Any]:
    """Probes GPU accelerator availability, device names, and VRAM."""
    cuda_avail = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if cuda_avail else 0
    devices: List[Dict[str, Any]] = []
    total_vram_gb = 0.0

    if cuda_avail and device_count > 0:
        for i in range(device_count):
            props = torch.cuda.get_device_properties(i)
            vram_gb = round(props.total_memory / (1024.0 ** 3), 2)
            total_vram_gb += vram_gb
            devices.append({
                "index": i,
                "name": props.name,
                "total_memory_gb": vram_gb,
            })

    return {
        "cuda_available": cuda_avail,
        "device_count": device_count,
        "vram_total_gb": round(total_vram_gb, 2),
        "devices": devices,
    }


def probe_disk(path: Union[str, Path] = WORKSPACE_ROOT) -> Dict[str, Any]:
    """Probes total, used, and free disk space on the specified path or drive."""
    resolved = Path(path).resolve()
    drive_root = resolved.anchor or str(resolved)
    try:
        usage = shutil.disk_usage(drive_root)
        total_gb = round(usage.total / (1024.0 ** 3), 2)
        used_gb = round(usage.used / (1024.0 ** 3), 2)
        free_gb = round(usage.free / (1024.0 ** 3), 2)
        percent_free = round((usage.free / usage.total) * 100.0, 2) if usage.total > 0 else 0.0
    except Exception:
        total_gb = 0.0
        used_gb = 0.0
        free_gb = 0.0
        percent_free = 0.0

    return {
        "drive": drive_root,
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "percent_free": percent_free,
    }


def probe_software_environment() -> Dict[str, Any]:
    """Probes Python, PyTorch, and installed core packages."""
    package_names = [
        "pymupdf",
        "fitz",
        "pdfplumber",
        "shapely",
        "opencv-python",
        "cv2",
        "torch",
        "numpy",
        "pandas",
    ]
    installed: Dict[str, str] = {}

    for pkg_name in package_names:
        # Try importlib metadata first
        try:
            installed[pkg_name] = importlib.metadata.version(pkg_name)
            continue
        except Exception:
            pass

        # Try direct module import
        try:
            mod = __import__(pkg_name)
            if hasattr(mod, "__version__"):
                installed[pkg_name] = str(mod.__version__)
            elif hasattr(mod, "version"):
                v = mod.version
                installed[pkg_name] = str(v[0] if isinstance(v, (tuple, list)) else v)
            else:
                installed[pkg_name] = "installed"
        except ImportError:
            pass

    return {
        "python_version": sys.version.split()[0],
        "torch_version": str(torch.__version__),
        "torch_cuda_version": getattr(torch.version, "cuda", None),
        "installed_packages": installed,
    }


def probe_all_hardware(disk_path: Union[str, Path] = WORKSPACE_ROOT) -> AttrDict:
    """Combines CPU, RAM, GPU, disk, and software environment probes."""
    gpu = probe_gpu()
    cuda_avail = bool(gpu.get("cuda_available", False))
    return AttrDict({
        "cpu": probe_cpu(),
        "ram": probe_ram(),
        "gpu": gpu,
        "disk": probe_disk(disk_path),
        "software": probe_software_environment(),
        "has_cuda": cuda_avail,
    })


def probe_hardware(disk_path: Union[str, Path] = WORKSPACE_ROOT) -> HardwareProfile:
    """
    Probes the host system and returns a complete HardwareProfile.
    """
    cpu_info = probe_cpu()
    ram_info = probe_ram()
    gpu_info = probe_gpu()
    disk_info = probe_disk(disk_path)
    soft_info = probe_software_environment()

    vmem = psutil.virtual_memory()
    cuda_avail = gpu_info["cuda_available"]
    gpu_nm = gpu_info["devices"][0]["name"] if gpu_info["devices"] else None
    vram_tot = gpu_info["vram_total_gb"]
    vram_fr = 0.0

    if cuda_avail and gpu_info["device_count"] > 0:
        try:
            mem_info = torch.cuda.mem_get_info()
            vram_fr = round(mem_info[0] / (1024.0 ** 3), 2)
        except Exception:
            vram_fr = vram_tot

    return HardwareProfile(
        cpu_physical_cores=cpu_info["physical_cores"],
        cpu_logical_cores=cpu_info["logical_cores"],
        cpu_model=cpu_info["processor"],
        ram_total_gb=ram_info["total_gb"],
        ram_available_gb=ram_info["available_gb"],
        ram_used_gb=ram_info["used_gb"],
        ram_percent=float(vmem.percent),
        cuda_available=cuda_avail,
        gpu_count=gpu_info["device_count"],
        gpu_name=gpu_nm,
        vram_total_gb=vram_tot,
        vram_free_gb=vram_fr,
        disk_path=disk_info["drive"],
        disk_total_gb=disk_info["total_gb"],
        disk_free_gb=disk_info["free_gb"],
        python_version=soft_info["python_version"],
        torch_version=soft_info["torch_version"],
        torch_cuda_version=soft_info["torch_cuda_version"],
        platform_system=platform.system(),
        platform_release=platform.release(),
    )


# ==============================================================================
# DYNAMIC TRAINING CONFIGURATION (5 TIERS)
# ==============================================================================

def _safe_float(val: Any, default: float) -> float:
    """Safely coalesces None to default before float conversion."""
    return float(val if val is not None else default)


def _safe_int(val: Any, default: int) -> int:
    """Safely coalesces None to default before int conversion."""
    return int(val if val is not None else default)


def _safe_bool(val: Any, default: bool) -> bool:
    """Safely coalesces None to default before bool conversion."""
    return bool(val if val is not None else default)


def auto_configure_training(
    profile: Optional[Union[HardwareProfile, Dict[str, Any]]] = None,
    task: str = "segmentation",
) -> TrainingConfig:
    """
    Dynamically configures training parameters based on detected or provided hardware profile.
    Implements a 5-tier memory and accelerator classification hierarchy.
    """
    if profile is None:
        profile = probe_hardware()

    # Extract values whether profile is HardwareProfile or Dict
    if isinstance(profile, dict):
        cuda_available = _safe_bool(profile.get("cuda_available"), False)
        vram_total_gb = _safe_float(profile.get("vram_total_gb"), 0.0)

        # Coalesce ram_available_gb -> ram_total_gb -> default 8.0
        raw_ram = profile.get("ram_available_gb")
        if raw_ram is None:
            raw_ram = profile.get("ram_total_gb")
        ram_available_gb = _safe_float(raw_ram, 8.0)

        cpu_logical_cores = _safe_int(profile.get("cpu_logical_cores"), 4)
    else:
        cuda_available = _safe_bool(profile.cuda_available, False)
        vram_total_gb = _safe_float(profile.vram_total_gb, 0.0)
        ram_available_gb = _safe_float(profile.ram_available_gb, 8.0)
        cpu_logical_cores = _safe_int(profile.cpu_logical_cores, 4)

    # Tier 1: High-End Dedicated GPU (VRAM >= 14 GB)
    if cuda_available and vram_total_gb >= 14.0:
        return TrainingConfig(
            device="cuda",
            batch_size=16,
            gradient_accumulation_steps=1,
            effective_batch_size=16,
            image_height=512,
            image_width=512,
            img_size=512,
            num_workers=min(4, max(2, cpu_logical_cores)),
            pin_memory=True,
            mixed_precision=True,
            use_amp=True,
            amp_dtype="float16",
            encoder_backbone="resnet34",
            max_epochs=30,
            early_stopping_patience=7,
            is_local_constrained=False,
            colab_recommended=False,
            recommendation_message="Local high-end GPU is sufficient for full resolution 512x512 training.",
            hardware_tier=1,
            tier_description="High-End Dedicated GPU (VRAM >= 14 GB)",
            notes="Full resolution 512x512 training with batch size 16 and fp16 AMP.",
        )

    # Tier 2: Mid-Range GPU (6 GB <= VRAM < 14 GB, e.g. T4, RTX 3060)
    elif cuda_available and vram_total_gb >= 6.0:
        return TrainingConfig(
            device="cuda",
            batch_size=8,
            gradient_accumulation_steps=2,
            effective_batch_size=16,
            image_height=512,
            image_width=512,
            img_size=512,
            num_workers=2,
            pin_memory=True,
            mixed_precision=True,
            use_amp=True,
            amp_dtype="float16",
            encoder_backbone="resnet34",
            max_epochs=25,
            early_stopping_patience=5,
            is_local_constrained=False,
            colab_recommended=False,
            recommendation_message="Local mid-range GPU is sufficient with gradient accumulation.",
            hardware_tier=2,
            tier_description="Mid-Range GPU (6 GB <= VRAM < 14 GB)",
            notes="512x512 resolution with batch size 8 and gradient accumulation step 2.",
        )

    # Tier 3: Low-End GPU (VRAM < 6 GB)
    elif cuda_available and vram_total_gb < 6.0:
        is_very_low = vram_total_gb < 3.0
        bs = 2 if is_very_low else 4
        res = 256 if is_very_low else 384
        amp = not is_very_low
        return TrainingConfig(
            device="cuda",
            batch_size=bs,
            gradient_accumulation_steps=16 // bs,
            effective_batch_size=16,
            image_height=res,
            image_width=res,
            img_size=res,
            num_workers=0,
            pin_memory=False,
            mixed_precision=amp,
            use_amp=amp,
            amp_dtype="float16" if amp else "float32",
            encoder_backbone="resnet18",
            max_epochs=20,
            early_stopping_patience=5,
            is_local_constrained=True,
            colab_recommended=True,
            recommendation_message="Low VRAM GPU detected. Training scaled down; Google Colab recommended for full runs.",
            hardware_tier=3,
            tier_description="Low-End GPU (VRAM < 6 GB)",
            notes=f"Scaled to {res}x{res} with batch size {bs}; Google Colab recommended for full runs.",
        )

    # Tier 4: CPU with Ample RAM (RAM available >= 4.0 GB)
    elif not cuda_available and ram_available_gb >= 4.0:
        return TrainingConfig(
            device="cpu",
            batch_size=4,
            gradient_accumulation_steps=4,
            effective_batch_size=16,
            image_height=256,
            image_width=256,
            img_size=256,
            num_workers=0,
            pin_memory=False,
            mixed_precision=False,
            use_amp=False,
            amp_dtype="float32",
            encoder_backbone="resnet18",
            max_epochs=10,
            early_stopping_patience=3,
            is_local_constrained=False,
            colab_recommended=True,
            recommendation_message="CPU training with ample RAM. Google Colab recommended for GPU acceleration.",
            hardware_tier=4,
            tier_description="CPU Execution with Ample RAM (Available >= 4.0 GB)",
            notes="CPU training at 256x256 resolution. Google Colab recommended for GPU acceleration.",
        )

    # Tier 5: Constrained Host (CPU only, Available RAM < 4.0 GB, specifically ~0.7-2.0 GB)
    else:
        bs = 1 if (ram_available_gb < 1.0 or cpu_logical_cores <= 1) else 2
        return TrainingConfig(
            device="cpu",
            batch_size=bs,
            gradient_accumulation_steps=8,
            effective_batch_size=16,
            image_height=256,
            image_width=256,
            img_size=256,
            num_workers=0,
            pin_memory=False,
            mixed_precision=False,
            use_amp=False,
            amp_dtype="float32",
            encoder_backbone="resnet18",
            max_epochs=5,
            early_stopping_patience=2,
            is_local_constrained=True,
            colab_recommended=True,
            recommendation_message="Severe RAM constraint detected. Local execution bounded to batch size 2, 256x256 resolution. Google Colab recommended for full model training.",
            hardware_tier=5,
            tier_description="Constrained Host (CPU only, Available RAM < 2.0 GB)",
            notes=(
                f"Severe RAM constraint detected ({ram_available_gb:.2f} GB free). "
                "Local execution strictly bounded to batch_size=2, resolution 256x256, and num_workers=0 "
                "to prevent OOM termination. Production training should be executed on Google Colab."
            ),
        )


def get_training_auto_config(
    hardware_profile: Optional[Union[HardwareProfile, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper returning configuration dictionary for training."""
    cfg = auto_configure_training(hardware_profile)
    return cfg.to_dict()


# ==============================================================================
# DISK SPACE SAFETY CHECK
# ==============================================================================

def check_disk_safety(
    required_free_gb: float = 0.0,
    disk_path: Union[str, Path] = WORKSPACE_ROOT,
    *,
    required_gb: Optional[float] = None,
    min_free_gb: Optional[float] = None,
) -> Union[Tuple[bool, float, str], bool]:
    """
    Checks if sufficient disk space is available for an operation and enforces
    the mandatory notification threshold for operations exceeding 10 GB.

    Args:
        required_free_gb: Required free disk space in gigabytes (must be non-negative).
        disk_path: Target path or drive anchor to evaluate.
        required_gb: Backward-compatible keyword alias for required_free_gb.
        min_free_gb: Keyword alias used by boundary tests; returns bool when used alone.

    Returns:
        (is_safe, free_gb, message) or bool if min_free_gb is passed alone.

    Raises:
        ValueError: If required_free_gb (or required_gb) is negative.
    """
    if min_free_gb is not None:
        effective_req_gb = float(min_free_gb)
    elif required_gb is not None:
        effective_req_gb = float(required_gb)
    else:
        effective_req_gb = float(required_free_gb)

    if effective_req_gb < 0.0:
        raise ValueError("required_free_gb must be non-negative")

    resolved_disk = Path(disk_path).resolve()
    drive_root = resolved_disk.anchor or str(resolved_disk)
    try:
        usage = shutil.disk_usage(drive_root)
        free_gb = round(usage.free / (1024.0 ** 3), 2)
    except Exception:
        free_gb = 0.0

    if effective_req_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB:
        msg = (
            f"WARNING: Operation requires {effective_req_gb:.2f} GB, which exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
            f"mandatory user notification threshold. Current free space: {free_gb:.2f} GB."
        )
        if free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
            res_tuple = (False, free_gb, f"REJECTED: {msg} (Insufficient headroom under 5.0 GB safety margin).")
        else:
            res_tuple = (True, free_gb, f"PROCEED_WITH_NOTICE: {msg}")
    elif free_gb < (effective_req_gb + DISK_FREE_MIN_GB):
        res_tuple = (
            False,
            free_gb,
            f"REJECTED: Insufficient disk space ({free_gb:.2f} GB free, requires {effective_req_gb:.2f} GB + {DISK_FREE_MIN_GB:.1f} GB safety margin).",
        )
    else:
        res_tuple = (True, free_gb, f"OK: Sufficient disk space ({free_gb:.2f} GB free).")

    if min_free_gb is not None and required_gb is None and required_free_gb == 0.0:
        return res_tuple[0]
    return res_tuple


if __name__ == "__main__":
    profile = probe_hardware()
    config = auto_configure_training(profile)
    print("\n" + "=" * 60)
    print("HOST HARDWARE AUDIT REPORT")
    print("=" * 60)
    print(profile.to_markdown_table())
    print("\n" + "=" * 60)
    print("AUTO-CONFIGURED TRAINING SPECIFICATION")
    print("=" * 60)
    print(json.dumps(config.to_dict(), indent=2))
