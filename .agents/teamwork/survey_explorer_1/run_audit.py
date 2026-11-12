import os
import sys
import json
import platform
import subprocess
import shutil

print("=== STARTING AUDIT SCRIPT ===")

results = {}

# 1. OS & System Info
try:
    results["os"] = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
except Exception as e:
    results["os"] = {"error": str(e)}

# 2. CPU & Memory
try:
    import psutil
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()
    results["hardware"] = {
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_freq_mhz": cpu_freq.current if cpu_freq else None,
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "ram_available_gb": round(vm.available / (1024**3), 2),
        "ram_used_gb": round(vm.used / (1024**3), 2),
        "ram_percent": vm.percent
    }
except Exception as e:
    # fallback without psutil
    results["hardware"] = {"error": str(e)}

# Disks
try:
    import psutil
    disks = {}
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks[part.mountpoint] = {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            }
        except Exception:
            pass
    results["disks"] = disks
except Exception as e:
    results["disks"] = {"error": str(e)}

# 3. GPU / CUDA
nvidia_smi_out = None
try:
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
    nvidia_smi_out = smi.stdout if smi.returncode == 0 else smi.stderr
except Exception as e:
    nvidia_smi_out = f"nvidia-smi not available or failed: {e}"

results["nvidia_smi"] = nvidia_smi_out

# 4. Python & Packages
results["python"] = {
    "version": sys.version,
    "executable": sys.executable,
    "path": sys.path
}

packages_to_check = [
    "torch", "torchvision", "torchaudio",
    "ultralytics", "transformers", "timm", "huggingface_hub",
    "cv2", "fitz", "pdfplumber", "pypdf", "pypdfium2", "pdf2image",
    "shapely", "pyclipper", "albumentations", "imgaug",
    "segmentation_models_pytorch", "monai",
    "scipy", "sklearn", "skimage",
    "numpy", "pandas", "PIL", "matplotlib", "seaborn",
    "onnx", "onnxruntime",
    "gradio", "streamlit", "flask", "fastapi", "uvicorn"
]

installed_packages = {}
for pkg in packages_to_check:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, "__version__", "installed (no __version__)")
        installed_packages[pkg] = {"installed": True, "version": str(ver)}
    except ImportError:
        installed_packages[pkg] = {"installed": False, "version": None}
    except Exception as e:
        installed_packages[pkg] = {"installed": "error", "error": str(e)}

results["packages"] = installed_packages

# Torch specific deep inspection
try:
    import torch
    results["torch_details"] = {
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version() if torch.cuda.is_available() else None,
        "current_device": torch.cuda.current_device() if torch.cuda.is_available() else None,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else 0
    }
except Exception as e:
    results["torch_details"] = {"error": str(e)}

# Output audit JSON
out_path = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_1\env_hardware_audit.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"Environment and Hardware audit saved to {out_path}")
print("CUDA Available:", results.get("torch_details", {}).get("cuda_available"))
print("RAM Total:", results.get("hardware", {}).get("ram_total_gb"), "GB, Available:", results.get("hardware", {}).get("ram_available_gb"), "GB")
