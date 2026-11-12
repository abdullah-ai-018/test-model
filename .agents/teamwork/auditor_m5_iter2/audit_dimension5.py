from pathlib import Path
import re

report_path = Path("drywall_detection/reports/M5_classification_report.md")

print("=== FORENSIC DIMENSION 5: PROGRESS SET NOTICE COMPLIANCE AUDIT ===")
assert report_path.is_file(), f"Report file not found: {report_path}"

content = report_path.read_text(encoding="utf-8")

# Required tokens:
# 1. "PROGRESS SET 95% CDs 10/02/2026"
# 2. "MTA Contract C-48526"
# 3. "interim"
# 4. "single-project calibration sample"
# 5. "cannot prove cross-domain generalization" or "cannot prove cross-building generalization"

required_phrases = [
    "PROGRESS SET 95% CDs 10/02/2026",
    "MTA Contract C-48526",
    "interim",
    "single-project calibration sample",
]

for phrase in required_phrases:
    found = phrase.lower() in content.lower()
    print(f"Phrase '{phrase}' present: {found}")
    assert found, f"Mandatory phrase missing: '{phrase}'"

assert "cannot prove cross" in content.lower(), "Missing statement regarding cross-domain/building generalization!"

# Check that it appears in Section 1 (prominently at top of document)
first_50_lines = "\n".join(content.splitlines()[:50])
assert "PROGRESS SET 95% CDs 10/02/2026" in first_50_lines, "Notice is not prominently placed at the top (within first 50 lines)!"

print("VERDICT: Dimension 5 PASS — Mandatory Progress Set & Single-Project Bounds notice is prominently displayed in Section 1 of M5_classification_report.md.")
