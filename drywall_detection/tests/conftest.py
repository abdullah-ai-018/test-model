"""
Pytest configuration and environment fixtures for drywall_detection.
Ensures workspace root is in sys.path for test discovery across all runners.
"""

import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))
