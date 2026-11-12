import os
import sys
import numpy as np
import cv2
import json
import subprocess
import torch

print("=== CHECK 4: STANDALONE INFERENCER INTEGRITY ===")

infer_script = r"drywall_detection/checkpoints/best_model/infer.py"
checkpoint_dir = r"drywall_detection/checkpoints/best_model"
checkpoint_path = os.path.join(checkpoint_dir, "best_model.pt")

assert os.path.exists(infer_script), f"infer.py not found at {infer_script}"
assert os.path.exists(checkpoint_path), f"best_model.pt not found at {checkpoint_path}"

# 1. Code inspection for genuine PyTorch logic
with open(infer_script, "r", encoding="utf-8") as f:
    infer_code = f.read()

print(f"infer.py size: {len(infer_code)} characters")
assert "torch" in infer_code, "infer.py does not import torch"
assert "load_state_dict" in infer_code or "torch.load" in infer_code, "infer.py does not load model weights"
assert "hann_window" in infer_code, "infer.py does not implement Hann apodization"
assert "softmax" in infer_code.lower() or "argmax" in infer_code.lower(), "infer.py does not compute probabilities/argmax"

# 2. Test directory setup
test_dir = r".agents/teamwork/auditor_m4_2/test_infer"
os.makedirs(test_dir, exist_ok=True)

img_a_path = os.path.join(test_dir, "test_white.png")
img_b_path = os.path.join(test_dir, "test_pattern.png")

# Image A: Pure white architectural background (512x512)
img_a = np.ones((512, 512, 3), dtype=np.uint8) * 255
cv2.imwrite(img_a_path, img_a)

# Image B: Floor plan mock with high contrast walls (512x512)
img_b = np.ones((512, 512, 3), dtype=np.uint8) * 255
cv2.rectangle(img_b, (50, 50), (450, 80), (0, 0, 0), -1)
cv2.rectangle(img_b, (50, 50), (80, 450), (0, 0, 0), -1)
cv2.rectangle(img_b, (420, 50), (450, 450), (0, 0, 0), -1)
cv2.rectangle(img_b, (50, 420), (450, 450), (0, 0, 0), -1)
cv2.imwrite(img_b_path, img_b)

# Run infer.py CLI on Image A (mode: mask)
out_a_mask = os.path.join(test_dir, "out_a_mask.png")
cmd_a = [
    sys.executable,
    infer_script,
    "--image", img_a_path,
    "--output", out_a_mask,
    "--checkpoint", checkpoint_dir,
    "--mode", "mask",
    "--device", "cpu"
]
print(f"Running CLI Image A (mask mode): {' '.join(cmd_a)}")
res_a = subprocess.run(cmd_a, capture_output=True, text=True)
print(f"CLI Image A exit code: {res_a.returncode}")
print(f"CLI Image A stdout:\n{res_a.stdout}")
assert res_a.returncode == 0, f"infer.py failed on Image A: {res_a.stderr}"

# Run infer.py CLI on Image B (mode: mask)
out_b_mask = os.path.join(test_dir, "out_b_mask.png")
cmd_b = [
    sys.executable,
    infer_script,
    "--image", img_b_path,
    "--output", out_b_mask,
    "--checkpoint", checkpoint_dir,
    "--mode", "mask",
    "--device", "cpu"
]
print(f"Running CLI Image B (mask mode): {' '.join(cmd_b)}")
res_b = subprocess.run(cmd_b, capture_output=True, text=True)
print(f"CLI Image B exit code: {res_b.returncode}")
print(f"CLI Image B stdout:\n{res_b.stdout}")
assert res_b.returncode == 0, f"infer.py failed on Image B: {res_b.stderr}"

# Run infer.py CLI on Image B (mode: overlay)
out_b_overlay = os.path.join(test_dir, "out_b_overlay.png")
cmd_b_overlay = [
    sys.executable,
    infer_script,
    "--image", img_b_path,
    "--output", out_b_overlay,
    "--checkpoint", checkpoint_dir,
    "--mode", "overlay",
    "--device", "cpu"
]
print(f"Running CLI Image B (overlay mode): {' '.join(cmd_b_overlay)}")
res_b_overlay = subprocess.run(cmd_b_overlay, capture_output=True, text=True)
assert res_b_overlay.returncode == 0, f"infer.py failed on Image B overlay: {res_b_overlay.stderr}"

# 3. Verify outputs
assert os.path.exists(out_a_mask), f"Missing {out_a_mask}"
assert os.path.exists(out_b_mask), f"Missing {out_b_mask}"
assert os.path.exists(out_b_overlay), f"Missing {out_b_overlay}"

mask_a = cv2.imread(out_a_mask, cv2.IMREAD_UNCHANGED)
mask_b = cv2.imread(out_b_mask, cv2.IMREAD_UNCHANGED)
overlay_b = cv2.imread(out_b_overlay, cv2.IMREAD_COLOR)

print(f"Mask A shape: {mask_a.shape}, unique classes: {np.unique(mask_a)}")
print(f"Mask B shape: {mask_b.shape}, unique classes: {np.unique(mask_b)}")
print(f"Overlay B shape: {overlay_b.shape}")

# Verify responsiveness: masks must differ between blank image and image with walls
assert not np.array_equal(mask_a, mask_b), "INTEGRITY VIOLATION: Output mask is identical for completely different inputs (hardcoded output detected)!"

# Verify classes are valid
all_classes = np.union1d(np.unique(mask_a), np.unique(mask_b))
print(f"All observed classes: {all_classes}")
assert all(c in [0, 1, 2, 3] for c in all_classes), f"Invalid class IDs found: {all_classes}"

# 4. Direct Python API test: StandaloneInferencer
sys.path.insert(0, os.path.abspath("."))
from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer

inferencer = StandaloneInferencer(checkpoint_dir=checkpoint_dir, device="cpu")
print("\nStandaloneInferencer successfully instantiated.")
print(f"Model architecture loaded: {type(inferencer.model)}")
print(f"Config loaded: {inferencer.config.get('model_name')} ({inferencer.config.get('architecture')})")

# Test sliding window inference directly on non-standard resolution (256x256)
from PIL import Image as PILImage
small_pil = PILImage.new("RGB", (256, 256), color=(200, 200, 200))
pred_mask, class_counts = inferencer.predict_image_sliding_window(small_pil)
print(f"Small image (256x256) direct inference output shape: {pred_mask.shape}")
assert pred_mask.shape == (256, 256), f"Small image output shape mismatch: {pred_mask.shape} != (256, 256)"
print(f"Direct inference class counts: {class_counts}")

print("\nCHECK 4 RESULT: ALL STANDALONE INFERENCER INTEGRITY CHECKS PASSED PERFECTLY!")

