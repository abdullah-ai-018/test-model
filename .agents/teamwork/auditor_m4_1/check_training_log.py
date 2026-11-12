import json
import re

with open(r'drywall_detection/checkpoints/best_model/training_log.json', 'r', encoding='utf-8') as f:
    training_log = json.load(f)

with open(r'drywall_detection/reports/M4_model_training_report.md', 'r', encoding='utf-8') as f:
    report_text = f.read()

sec_5_1_match = re.search(r'### 5\.1 Empirical Local CPU Calibration Run.*?(?=### 5\.2)', report_text, re.DOTALL)
assert sec_5_1_match is not None, 'Section 5.1 not found in report!'
sec_5_1 = sec_5_1_match.group(0)

for entry in training_log:
    epoch = entry['epoch']
    train_loss = str(entry['train_loss'])
    val_loss = str(entry['val_loss'])
    val_miou = str(entry['val_miou'])
    val_wall_iou = str(entry['val_wall_iou'])
    val_pixel_acc = str(entry['val_pixel_accuracy'])
    timestamp = entry['timestamp']
    
    print(f"Verifying Epoch {epoch}: train_loss={train_loss}, val_loss={val_loss}, val_miou={val_miou}, val_wall_iou={val_wall_iou}, timestamp={timestamp}")
    assert train_loss in sec_5_1, f"train_loss {train_loss} not found"
    assert val_loss in sec_5_1, f"val_loss {val_loss} not found"
    assert val_miou in sec_5_1, f"val_miou {val_miou} not found"
    assert val_wall_iou in sec_5_1, f"val_wall_iou {val_wall_iou} not found"
    assert val_pixel_acc in sec_5_1, f"val_pixel_acc {val_pixel_acc} not found"
    assert timestamp in sec_5_1, f"timestamp {timestamp} not found"

print("\nCONFIRMED: ALL training_log.json values perfectly match Section 5.1 table!")
