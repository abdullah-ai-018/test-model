import re
import sys
from pathlib import Path

files_to_check = [
    'drywall_detection/classification/classifier.py',
    'drywall_detection/pipeline/fusion.py',
    'drywall_detection/pipeline/router.py',
    'drywall_detection/pipeline/annotate.py',
    'drywall_detection/vector/spatial_matcher.py',
    'drywall_detection/vector/extractor.py',
    'drywall_detection/vector/schedule_parser.py'
]

test_tokens = ['test', 'dummy', 'mock', 'r01', 'r02', 'r03', 'r04', 'r05', 'r06', 'r07', 'r08', 'r09', 'r10', 'usman', 'fake', 'fixture']

print("=== STATIC AUDIT: CHECKING PRODUCTION CODE FOR TEST SHORTCUTS ===")
findings = []
for fpath in files_to_check:
    p = Path(fpath)
    if not p.exists():
        print(f"File missing: {fpath}")
        continue
    lines = p.read_text(encoding='utf-8').splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith("*"):
            continue
        line_lower = stripped.lower()
        for token in test_tokens:
            if re.search(r'\b' + re.escape(token) + r'\b', line_lower):
                findings.append((fpath, idx, token, stripped))

print(f"Total occurrences of test-related tokens in non-comment code: {len(findings)}")
for fpath, idx, token, code in findings:
    print(f"{fpath}:{idx} (matched '{token}'): {code}")
