import os
import sys
import torch
import json

checkpoint_path = r"drywall_detection/checkpoints/best_model/best_model.pt"
config_path = r"drywall_detection/checkpoints/best_model/config.json"
mapping_path = r"drywall_detection/checkpoints/best_model/class_mapping.json"

print(f"=== CHECK 1: MODEL WEIGHTS AUTHENTICITY ===")
print(f"Checking checkpoint existence: {checkpoint_path}")
assert os.path.exists(checkpoint_path), f"Checkpoint not found at {checkpoint_path}"
file_size = os.path.getsize(checkpoint_path)
print(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")

# Load state dict
try:
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
except Exception as e:
    print(f"Failed to load checkpoint: {e}")
    sys.exit(1)

print(f"Checkpoint object type: {type(state_dict)}")
if isinstance(state_dict, dict) and "state_dict" in state_dict:
    print("Found 'state_dict' key in checkpoint dict.")
    model_weights = state_dict["state_dict"]
elif isinstance(state_dict, dict) and "model_state_dict" in state_dict:
    print("Found 'model_state_dict' key in checkpoint dict.")
    model_weights = state_dict["model_state_dict"]
else:
    model_weights = state_dict

print(f"Number of parameter tensors: {len(model_weights)}")

total_params = 0
trainable_params = 0
zero_tensors = []
constant_tensors = []
nan_tensors = []
inf_tensors = []
tensor_stats = []

for k, v in model_weights.items():
    if not isinstance(v, torch.Tensor):
        print(f"Non-tensor entry: {k} -> {type(v)}")
        continue
    
    num_el = v.numel()
    total_params += num_el
    
    v_float = v.float()
    v_min = v_float.min().item()
    v_max = v_float.max().item()
    v_mean = v_float.mean().item()
    v_std = v_float.std().item() if num_el > 1 else 0.0
    
    if torch.isnan(v_float).any():
        nan_tensors.append(k)
    if torch.isinf(v_float).any():
        inf_tensors.append(k)
    if torch.all(v_float == 0):
        zero_tensors.append(k)
    if v_min == v_max and num_el > 1:
        constant_tensors.append(k)
        
    tensor_stats.append({
        "name": k,
        "shape": list(v.shape),
        "numel": num_el,
        "min": v_min,
        "max": v_max,
        "mean": v_mean,
        "std": v_std
    })

print(f"Total parameter count: {total_params:,}")
print(f"NaN tensors: {len(nan_tensors)}")
print(f"Inf tensors: {len(inf_tensors)}")
print(f"All-zero tensors: {len(zero_tensors)} ({zero_tensors})")
print(f"Constant tensors: {len(constant_tensors)} ({constant_tensors})")

print("\nFirst 10 tensor summaries:")
for s in tensor_stats[:10]:
    print(f"  {s['name']} - shape: {s['shape']}, min: {s['min']:.4f}, max: {s['max']:.4f}, mean: {s['mean']:.4f}, std: {s['std']:.4f}")

print("\nLast 5 tensor summaries:")
for s in tensor_stats[-5:]:
    print(f"  {s['name']} - shape: {s['shape']}, min: {s['min']:.4f}, max: {s['max']:.4f}, mean: {s['mean']:.4f}, std: {s['std']:.4f}")

# Check model architecture instantiation using drywall_detection.models
sys.path.insert(0, os.path.abspath("."))
from drywall_detection.models.segformer import SegFormerB0

model = SegFormerB0(num_classes=4)
model_total_params = sum(p.numel() for p in model.parameters())
print(f"\nSegFormerB0 model definition total params: {model_total_params:,}")

# Load state dict into model
missing_keys, unexpected_keys = model.load_state_dict(model_weights, strict=False)
print(f"Missing keys: {len(missing_keys)} {missing_keys}")
print(f"Unexpected keys: {len(unexpected_keys)} {unexpected_keys}")

# Check config.json and class_mapping.json
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
print(f"\nconfig.json: {cfg}")

with open(mapping_path, "r", encoding="utf-8") as f:
    cls_map = json.load(f)
print(f"\nclass_mapping.json: {cls_map}")
