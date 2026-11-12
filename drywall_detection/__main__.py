"""
drywall_detection/__main__.py
=============================
Package entrypoint enabling execution via:
    python -m drywall_detection <command> [options]
"""

import sys
from drywall_detection.cli import main

if __name__ == "__main__":
    sys.exit(main())
