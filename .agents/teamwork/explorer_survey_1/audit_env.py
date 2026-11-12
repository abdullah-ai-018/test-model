import sys
import os
import platform
import psutil
import shutil
import json

def inspect_environment():
    env_info = {}
    
    # Python & OS
    env_info["python_version"] = sys.version
    env_info["python_executable"] = sys.executable
    env_info["os"] = platform.platform()
    env_info["os_release"] = platform.release()
    env_info["machine"] = platform.machine()
    env_info["processor"] = platform.processor()
    
    # CPU
    env_info["cpu_count_logical"] = psutil.cpu_count(logical=True)
    env_info["cpu_count_physical"] = psutil.cpu_count(logical=False)
    
    # RAM
    mem = psutil.virtual_memory()
    env_info["ram_total_gb"] = round(mem.total / (1024**3), 2)
    env_info["ram_available_gb"] = round(mem.available / (1024**3), 2)
    env_info["ram_used_gb"] = round(mem.used / (1024**3), 2)
    env_info["ram_percent"] = mem.percent

    # Disk
    disks = {}
    for d in ['C:\\', 'E:\\']:
        if os.path.exists(d):
            usage = shutil.disk_usage(d)
            disks[d] = {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2)
            }
    env_info["disks"] = disks

    # PyTorch & GPU
    try:
        import torch
        env_info["torch_version"] = torch.__version__
        env_info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env_info["cuda_version"] = torch.version.cuda
            env_info["cudnn_version"] = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
            env_info["device_count"] = torch.cuda.device_count()
            env_info["device_name"] = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory
            env_info["vram_total_gb"] = round(vram / (1024**3), 2)
        else:
            env_info["cuda_version"] = None
            env_info["device_name"] = None
            env_info["vram_total_gb"] = 0
    except ImportError as e:
        env_info["torch_version"] = None
        env_info["torch_error"] = str(e)
        env_info["cuda_available"] = False

    # Package audits
    pkgs = [
        "fitz", "pdfplumber", "shapely", "cv2", "albumentations", "timm",
        "transformers", "ultralytics", "segmentation_models_pytorch",
        "scipy", "sklearn", "PIL", "numpy", "pandas", "matplotlib"
    ]
    pkg_status = {}
    for pkg in pkgs:
        try:
            m = __import__(pkg)
            ver = getattr(m, "__version__", "installed (no __version__)")
            pkg_status[pkg] = {"installed": True, "version": ver}
        except ImportError:
            pkg_status[pkg] = {"installed": False, "version": None}
    env_info["packages"] = pkg_status

    return env_info

if __name__ == "__main__":
    info = inspect_environment()
    print(json.dumps(info, indent=2))
    with open(r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\env_audit.json", "w") as f:
        json.dump(info, f, indent=2)
