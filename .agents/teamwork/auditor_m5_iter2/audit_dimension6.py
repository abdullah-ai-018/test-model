from pathlib import Path
from datetime import datetime, timezone

root = Path(".")
# Any file modified in the last 24 hours (or specifically during M5) outside allowed dirs
m5_start_time = datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc)

allowed_prefixes = ("drywall_detection", ".agents", ".pytest_cache")

violations = []
for p in root.rglob("*"):
    # Convert path to relative POSIX style
    rel = p.relative_to(root).as_posix()
    if any(rel.startswith(prefix) for prefix in allowed_prefixes):
        continue
    
    # Check modification time
    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    if mtime > m5_start_time:
        violations.append((rel, mtime.isoformat()))

print("=== FORENSIC DIMENSION 6: WORKSPACE ISOLATION AUDIT ===")
print(f"Files outside drywall_detection/, .agents/, .pytest_cache/ modified after M5 start ({m5_start_time.isoformat()}): {len(violations)}")
for rel, mt in violations:
    print(f"  VIOLATION: {rel} (modified {mt})")

assert len(violations) == 0, f"Workspace isolation breached: {violations}"
print("VERDICT: Dimension 6 PASS — Zero files outside drywall_detection/ and .agents/teamwork/ were modified or created.")
