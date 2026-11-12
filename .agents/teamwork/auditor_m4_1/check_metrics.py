import json
import re

with open(r'drywall_detection/checkpoints/best_model/metrics.json', 'r', encoding='utf-8') as f:
    metrics = json.load(f)

with open(r'drywall_detection/reports/M4_model_training_report.md', 'r', encoding='utf-8') as f:
    report_text = f.read()

# Extract Section 5.1
sec_5_1_match = re.search(r'### 5\.1 Empirical Local CPU Calibration Run.*?(?=### 5\.2)', report_text, re.DOTALL)
assert sec_5_1_match is not None, 'Section 5.1 not found in report!'
sec_5_1 = sec_5_1_match.group(0)

# Check top level metrics
checks = [
    ('pixel_accuracy', str(metrics['pixel_accuracy'])),
    ('mean_accuracy', str(metrics['mean_accuracy'])),
    ('mean_iou_present', str(metrics['mean_iou_present'])),
    ('mean_iou_all', str(metrics['mean_iou_all'])),
    ('wall_mean_iou_present', str(metrics['wall_mean_iou_present'])),
    ('wall_mean_iou_all', str(metrics['wall_mean_iou_all'])),
    ('test_samples', str(metrics['test_samples'])),
    ('evaluated_tiles', str(metrics['evaluated_tiles'])),
]

for name, val in checks:
    found = val in sec_5_1
    print(f'{name} ({val}) in Sec 5.1: {found}')
    assert found, f'Mismatch for {name} ({val})!'

# Check per-class metrics
for cls_name, cls_data in metrics['per_class'].items():
    iou = str(cls_data['iou'])
    dice = str(cls_data['dice'])
    prec = str(cls_data['precision'])
    rec = str(cls_data['recall'])
    gt_px = str(cls_data['gt_pixels'])
    pred_px = str(cls_data['pred_pixels'])
    gt_px_comma = f"{cls_data['gt_pixels']:,}"
    pred_px_comma = f"{cls_data['pred_pixels']:,}"
    
    assert iou in sec_5_1 or f"{float(iou):.4f}" in sec_5_1, f"IoU {iou} not found for {cls_name}"
    assert dice in sec_5_1 or f"{float(dice):.4f}" in sec_5_1, f"Dice {dice} not found for {cls_name}"
    assert prec in sec_5_1 or f"{float(prec):.4f}" in sec_5_1, f"Prec {prec} not found for {cls_name}"
    assert rec in sec_5_1 or f"{float(rec):.4f}" in sec_5_1, f"Rec {rec} not found for {cls_name}"
    assert gt_px in sec_5_1 or gt_px_comma in sec_5_1, f"GT pixels not found for {cls_name}"
    assert pred_px in sec_5_1 or pred_px_comma in sec_5_1, f"Pred pixels not found for {cls_name}"
    print(f"Class {cls_name} verified: IoU={iou}, Dice={dice}, Prec={prec}, Rec={rec}, GT={gt_px_comma}, Pred={pred_px_comma}")

cm = metrics['confusion_matrix']
for r_idx, row in enumerate(cm):
    for c_idx, val in enumerate(row):
        val_comma = f"{val:,}"
        assert str(val) in sec_5_1 or val_comma in sec_5_1, f"CM[{r_idx}][{c_idx}] = {val} not found"

print("\nCONFIRMED: ALL metrics.json values perfectly match Section 5.1!")

# Also check framing of Section 3.1 and Section 5.2
sec_3_1_match = re.search(r'### 3\.1 Architecture Capacity & Benchmark Profiling.*?(?=### 3\.2)', report_text, re.DOTALL)
assert sec_3_1_match is not None, 'Section 3.1 not found!'
sec_3_1 = sec_3_1_match.group(0)

print('\nChecking Section 3.1 framing:')
assert 'Comparative Architecture Analysis' in sec_3_1, 'Missing Comparative Architecture Analysis qualifier in Sec 3.1'
assert 'theoretical capacity targets under full GPU convergence' in sec_3_1 or 'high-epoch GPU convergence capacity benchmarks' in sec_3_1, 'Missing theoretical GPU qualifier in Sec 3.1'
print('Section 3.1 framing explicitly qualified as comparative benchmarks / theoretical GPU targets: PASS')

sec_5_2_match = re.search(r'### 5\.2 Comparative Architecture Benchmarks & Full GPU Convergence Projections.*?(?=## 6)', report_text, re.DOTALL)
assert sec_5_2_match is not None, 'Section 5.2 not found!'
sec_5_2 = sec_5_2_match.group(0)

print('\nChecking Section 5.2 framing:')
assert 'Comparative Architecture Benchmarks & Full GPU Convergence Projections' in sec_5_2, 'Missing header qualification in Sec 5.2'
assert 'Full GPU Convergence Projections' in sec_5_2, 'Missing GPU Convergence qualifier in Sec 5.2'
assert 'theoretical convergence profiles' in sec_5_2 or 'GPU convergence' in sec_5_2, 'Missing theoretical convergence note in Sec 5.2'
print('Section 5.2 framing explicitly qualified as comparative benchmarks / theoretical GPU targets: PASS')
