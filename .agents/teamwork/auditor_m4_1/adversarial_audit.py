import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import torch
import numpy as np
from PIL import Image
from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer

def run_adversarial_audit():
    print("=== ADVERSARIAL INTEGRITY AUDIT ===")
    
    # 1. Load StandaloneInferencer
    inferencer = StandaloneInferencer(device="cpu")
    model = inferencer.model
    print("Model successfully loaded on CPU.")

    # 2. Check layer-by-layer matching
    total_weights = 0
    for name, p in model.named_parameters():
        total_weights += p.numel()
    print(f"Total model parameter count: {total_weights} (expected 3,715,172)")
    assert total_weights == 3715172, f"Param count mismatch: {total_weights}"

    # 3. Test Sensitivity to Input (Proof of Genuine Computation)
    # Generate 3 distinct inputs: all-zeros (black), all-255 (white), and random noise
    img_black = Image.fromarray(np.zeros((512, 512, 3), dtype=np.uint8))
    img_white = Image.fromarray(np.full((512, 512, 3), 255, dtype=np.uint8))
    np.random.seed(12345)
    img_noise = Image.fromarray(np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8))

    mask_black = inferencer.predict_tile(img_black)
    mask_white = inferencer.predict_tile(img_white)
    mask_noise = inferencer.predict_tile(img_noise)

    diff_bw = (mask_black != mask_white).sum()
    diff_bn = (mask_black != mask_noise).sum()
    diff_wn = (mask_white != mask_noise).sum()

    print(f"Prediction difference Black vs White: {diff_bw} / {mask_black.size} pixels ({diff_bw / mask_black.size * 100:.2f}%)")
    print(f"Prediction difference Black vs Noise: {diff_bn} / {mask_black.size} pixels ({diff_bn / mask_black.size * 100:.2f}%)")
    print(f"Prediction difference White vs Noise: {diff_wn} / {mask_white.size} pixels ({diff_wn / mask_white.size * 100:.2f}%)")

    assert diff_bw > 0 or diff_bn > 0, "FATAL: Model produces identical predictions regardless of input! Facade suspected!"
    print("PASS: Predictions dynamically respond to input variations (genuine neural inference).")

    # 4. Weight Dependence Check (Ablation)
    # Forward pass on normal weights
    x_test = torch.randn(1, 3, 256, 256)
    with torch.no_grad():
        out_normal = model(x_test)
        if hasattr(out_normal, 'logits'):
            out_normal = out_normal.logits
        elif isinstance(out_normal, dict):
            out_normal = out_normal['logits']

    # Now alter a layer weight slightly
    first_weight = next(model.parameters())
    original_data = first_weight.data.clone()
    first_weight.data.fill_(0.0)

    with torch.no_grad():
        out_ablated = model(x_test)
        if hasattr(out_ablated, 'logits'):
            out_ablated = out_ablated.logits
        elif isinstance(out_ablated, dict):
            out_ablated = out_ablated['logits']

    logits_diff = (out_normal - out_ablated).abs().max().item()
    print(f"Max absolute change in logits upon weight zeroing: {logits_diff:.6f}")
    assert logits_diff > 1e-4, "FATAL: Zeroing layer weights had no effect on logits! Model is a mock!"
    print("PASS: Output logits directly depend on network weights.")

    # Restore weights
    first_weight.data.copy_(original_data)

    print("\nALL ADVERSARIAL STRESS CHECKS PASSED: Clean, authentic deep learning pipeline.")

if __name__ == '__main__':
    run_adversarial_audit()
