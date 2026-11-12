import os
import subprocess
import re

print("=== CHECK 5 & 6: PROGRESS SET NOTICE & REPOSITORY BOUNDARY ===")

# --- CHECK 5: Progress Set Notice ---
print("\n--- Auditing 95% CDs Progress Set Notice ---")
report_path = r"drywall_detection/reports/M4_model_training_report.md"
readme_path = r"drywall_detection/README.md"

assert os.path.exists(report_path), f"Report not found at {report_path}"
assert os.path.exists(readme_path), f"README not found at {readme_path}"

with open(report_path, "r", encoding="utf-8") as f:
    report_content = f.read()

with open(readme_path, "r", encoding="utf-8") as f:
    readme_content = f.read()

# Check key terms of the mandatory notice
terms = [
    "95% CD",
    "PROGRESS SET",
    "C-48526",
    "as-built",
    "interim"
]

print("Checking M4_model_training_report.md:")
for t in terms:
    found = t.lower() in report_content.lower()
    print(f"  Term '{t}': {found}")
    assert found, f"Term '{t}' missing from M4_model_training_report.md!"

print("\nChecking README.md:")
for t in terms:
    found = t.lower() in readme_content.lower()
    print(f"  Term '{t}': {found}")
    assert found, f"Term '{t}' missing from README.md!"

print("\nCHECK 5 RESULT: MANDATORY 95% CDs NOTICE PROMINENTLY VERIFIED IN BOTH FILES!")


# --- CHECK 6: Repository Boundary Integrity ---
print("\n--- Auditing Workspace Boundary Integrity ---")
git_cmd = ["git", "status", "--porcelain"]
git_res = subprocess.run(git_cmd, capture_output=True, text=True)

print(f"git status returncode: {git_res.returncode}")
lines = git_res.stdout.strip().splitlines()

external_modifications = []
allowed_prefixes = (
    "drywall_detection/",
    ".agents/teamwork/",
    "?? drywall_detection/",
    "?? .agents/teamwork/",
    " M drywall_detection/",
    " M .agents/teamwork/",
    "M  drywall_detection/",
    "M  .agents/teamwork/",
    "A  drywall_detection/",
    "A  .agents/teamwork/",
    "D  drywall_detection/",
    "D  .agents/teamwork/"
)

for line in lines:
    line_clean = line.strip()
    if not line_clean:
        continue
    
    # Extract path
    parts = line_clean.split(maxsplit=1)
    if len(parts) == 2:
        file_path = parts[1].replace("\\", "/")
        if not (file_path.startswith("drywall_detection/") or file_path.startswith(".agents/teamwork/")):
            external_modifications.append(file_path)

print(f"Total modified/untracked files: {len(lines)}")
print(f"External modifications outside drywall_detection/ & .agents/teamwork/: {len(external_modifications)}")
if external_modifications:
    print("Violating files:")
    for f in external_modifications:
        print(f"  {f}")
    assert False, f"INTEGRITY VIOLATION: Files modified outside drywall_detection/: {external_modifications}"
else:
    print("CHECK 6 RESULT: PASS - ZERO EXTERNAL MODIFICATIONS OUTSIDE drywall_detection/!")
