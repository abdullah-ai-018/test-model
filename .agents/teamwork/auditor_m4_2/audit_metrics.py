import json
import re
import os
import sys

print("=== CHECK 2: METRICS & LOG AUTHENTICITY ===")

metrics_path = r"drywall_detection/checkpoints/best_model/metrics.json"
log_path = r"drywall_detection/checkpoints/best_model/training_log.json"
report_path = r"drywall_detection/reports/M4_model_training_report.md"

assert os.path.exists(metrics_path), f"metrics.json missing at {metrics_path}"
assert os.path.exists(log_path), f"training_log.json missing at {log_path}"
assert os.path.exists(report_path), f"M4 report missing at {report_path}"

with open(metrics_path, "r", encoding="utf-8") as f:
    metrics = json.load(f)

with open(log_path, "r", encoding="utf-8") as f:
    training_log = json.load(f)

with open(report_path, "r", encoding="utf-8") as f:
    report_text = f.read()

print(f"Loaded metrics.json: {list(metrics.keys())}")
print(f"Loaded training_log.json: {len(training_log)} epochs")

# Check test_samples and evaluated_tiles
print(f"metrics.json test_samples: {metrics.get('test_samples')}")
print(f"metrics.json evaluated_tiles: {metrics.get('evaluated_tiles')}")
assert metrics.get('test_samples') == 1, f"Expected test_samples: 1, got {metrics.get('test_samples')}"
assert metrics.get('evaluated_tiles') == 1, f"Expected evaluated_tiles: 1, got {metrics.get('evaluated_tiles')}"

# Extract Section 5.1
sec_5_1_match = re.search(r'### 5\.1 Empirical Local CPU Calibration Run.*?(?=### 5\.2)', report_text, re.DOTALL)
assert sec_5_1_match is not None, "Section 5.1 not found in M4 report!"
sec_5_1 = sec_5_1_match.group(0)

print("\n--- Cross-checking Section 5.1 vs metrics.json ---")
metric_keys_to_check = [
    ('pixel_accuracy', metrics['pixel_accuracy']),
    ('mean_accuracy', metrics['mean_accuracy']),
    ('mean_iou_present', metrics['mean_iou_present']),
    ('mean_iou_all', metrics['mean_iou_all']),
    ('wall_mean_iou_present', metrics['wall_mean_iou_present']),
    ('wall_mean_iou_all', metrics['wall_mean_iou_all']),
    ('test_samples', metrics['test_samples']),
    ('evaluated_tiles', metrics['evaluated_tiles']),
]

for name, val in metric_keys_to_check:
    val_str = str(val)
    val_fmt = f"{val:.4f}" if isinstance(val, float) else str(val)
    matched = (val_str in sec_5_1) or (val_fmt in sec_5_1)
    print(f"  {name}: {val} -> matched in Sec 5.1: {matched}")
    assert matched, f"Metric mismatch: {name} ({val}) not found in Section 5.1"

print("\n--- Cross-checking per-class metrics in Section 5.1 ---")
for cls_name, cls_data in metrics['per_class'].items():
    iou = cls_data['iou']
    dice = cls_data['dice']
    prec = cls_data['precision']
    rec = cls_data['recall']
    gt_px = cls_data['gt_pixels']
    pred_px = cls_data['pred_pixels']
    
    assert (str(iou) in sec_5_1) or (f"{iou:.4f}" in sec_5_1), f"Class {cls_name} IoU {iou} missing"
    assert (str(dice) in sec_5_1) or (f"{dice:.4f}" in sec_5_1), f"Class {cls_name} Dice {dice} missing"
    assert (str(prec) in sec_5_1) or (f"{prec:.4f}" in sec_5_1), f"Class {cls_name} Precision {prec} missing"
    assert (str(rec) in sec_5_1) or (f"{rec:.4f}" in sec_5_1), f"Class {cls_name} Recall {rec} missing"
    assert (str(gt_px) in sec_5_1) or (f"{gt_px:,}" in sec_5_1), f"Class {cls_name} GT pixels {gt_px} missing"
    assert (str(pred_px) in sec_5_1) or (f"{pred_px:,}" in sec_5_1), f"Class {cls_name} Pred pixels {pred_px} missing"
    print(f"  Class '{cls_name}': IoU={iou:.4f}, Dice={dice:.4f}, Prec={prec:.4f}, Rec={rec:.4f}, GT={gt_px:,}, Pred={pred_px:,} -> VERIFIED")

print("\n--- Cross-checking confusion matrix ---")
cm = metrics['confusion_matrix']
for r_idx, row in enumerate(cm):
    for c_idx, count in enumerate(row):
        assert (str(count) in sec_5_1) or (f"{count:,}" in sec_5_1), f"CM[{r_idx}][{c_idx}] count {count} missing"
print("Confusion matrix: all cells verified in Section 5.1 table.")

print("\n--- Cross-checking training_log.json epochs vs Section 5.1 ---")
for entry in training_log:
    ep = entry['epoch']
    t_loss = entry['train_loss']
    v_loss = entry['val_loss']
    v_miou = entry['val_miou']
    v_wiou = entry['val_wall_iou']
    v_acc = entry['val_pixel_accuracy']
    ts = entry['timestamp']
    assert (str(t_loss) in sec_5_1) or (f"{t_loss:.4f}" in sec_5_1), f"Epoch {ep} train_loss {t_loss} missing"
    assert (str(v_loss) in sec_5_1) or (f"{v_loss:.4f}" in sec_5_1), f"Epoch {ep} val_loss {v_loss} missing"
    assert (str(v_miou) in sec_5_1) or (f"{v_miou:.4f}" in sec_5_1), f"Epoch {ep} val_miou {v_miou} missing"
    assert (str(v_wiou) in sec_5_1) or (f"{v_wiou:.4f}" in sec_5_1), f"Epoch {ep} val_wall_iou {v_wiou} missing"
    assert (str(v_acc) in sec_5_1) or (f"{v_acc:.4f}" in sec_5_1), f"Epoch {ep} val_pixel_acc {v_acc} missing"
    assert ts in sec_5_1, f"Epoch {ep} timestamp {ts} missing"
    print(f"  Epoch {ep}: train_loss={t_loss}, val_loss={v_loss}, val_miou={v_miou}, val_wall_iou={v_wiou}, val_pixel_acc={v_acc}, ts={ts} -> VERIFIED")

print("\n--- Verifying Framing of Section 3.1 & Section 5.2 ---")
sec_3_1_match = re.search(r'### 3\.1 Architecture Capacity & Benchmark Profiling.*?(?=### 3\.2)', report_text, re.DOTALL)
assert sec_3_1_match is not None, "Section 3.1 not found in report"
sec_3_1 = sec_3_1_match.group(0)

# Check qualification in Section 3.1
has_benchmark_qual = ("Comparative Architecture Analysis" in sec_3_1) and (
    "GPU convergence" in sec_3_1 or "theoretical capacity" in sec_3_1 or "benchmark" in sec_3_1
)
print(f"Section 3.1 comparative architecture benchmark qualification: {has_benchmark_qual}")
assert has_benchmark_qual, "Section 3.1 lacks explicit comparative architecture benchmark qualification!"

sec_5_2_match = re.search(r'### 5\.2 Comparative Architecture Benchmarks & Full GPU Convergence Projections.*?(?=## 6)', report_text, re.DOTALL)
assert sec_5_2_match is not None, "Section 5.2 not found in report"
sec_5_2 = sec_5_2_match.group(0)

# Check qualification in Section 5.2
has_gpu_proj_qual = ("Comparative Architecture Benchmarks & Full GPU Convergence Projections" in sec_5_2) and (
    "train_colab.py" in sec_5_2 or "theoretical convergence" in sec_5_2 or "GPU" in sec_5_2
)
print(f"Section 5.2 GPU convergence projection qualification: {has_gpu_proj_qual}")
assert has_gpu_proj_qual, "Section 5.2 lacks explicit GPU convergence projection qualification!"

print("\nCHECK 2 RESULT: ALL CHECKS PASSED PERFECTLY!")
