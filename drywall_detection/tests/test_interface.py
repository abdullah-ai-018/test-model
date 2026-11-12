#!/usr/bin/env python3
"""
drywall_detection/tests/test_interface.py
========================================
Test Suite for Streamlit Local Testing Interface & Takeoff Dashboard (Milestone M4).

Covers:
1. Python Syntax & CLI Smoke
2. Headless AppTest Session Execution
3. Takeoff Arithmetic & Zero-Division Safety
4. Error Handling for 0-byte and Corrupt Drawing Uploads
"""

from __future__ import annotations

import ast
import csv
import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from drywall_detection.app import (
    build_annotated_pdf_bytes,
    build_takeoff_csv_str,
    compute_takeoff_stats,
)
from drywall_detection.config import (
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
)

APP_FILE_PATH = Path(__file__).resolve().parent.parent / "app" / "app.py"
ROOT_APP_FILE_PATH = Path(__file__).resolve().parent.parent / "app.py"


# ==============================================================================
# TEST CLASS 1: Syntax & CLI Smoke
# ==============================================================================

class TestStreamlitSyntaxAndSmoke:
    """Verifies that the interface code is free of syntax errors and passes CLI smoke tests."""

    def test_app_syntax_and_importability(self) -> None:
        """Parses app scripts using Python's AST compiler to verify syntax validity."""
        for path in (APP_FILE_PATH, ROOT_APP_FILE_PATH):
            assert path.exists(), f"App file does not exist: {path}"
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code, filename=str(path))
            assert tree is not None

    def test_streamlit_cli_smoke(self) -> None:
        """Executes streamlit CLI help to verify environment integrity."""
        cmd = [sys.executable, "-m", "streamlit", "run", str(APP_FILE_PATH), "--help"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        assert proc.returncode == 0
        assert "Usage: streamlit run" in proc.stdout or "Usage: streamlit run" in proc.stderr


# ==============================================================================
# TEST CLASS 2: Headless AppTest Session
# ==============================================================================

class TestStreamlitAppTestMockSession:
    """Runs Streamlit headless tests using streamlit.testing.v1.AppTest without browser drivers."""

    def test_apptest_initial_render(self) -> None:
        at = AppTest.from_file(str(APP_FILE_PATH), default_timeout=30)
        at.run()

        # Assert no unhandled exceptions thrown during initial render
        assert len(at.exception) == 0, f"AppTest raised exceptions: {at.exception}"

        # Assert title and sidebar controls are discovered
        assert len(at.title) >= 1
        assert "Drywall Detection & Wall Classification" in at.title[0].value

        # Check select_slider exists (DPI)
        assert len(at.select_slider) >= 1

        # Check slider exists (Alpha)
        assert len(at.slider) >= 1

    def test_apptest_parameter_reconfiguration(self) -> None:
        at = AppTest.from_file(str(APP_FILE_PATH), default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Adjust DPI select_slider to 72
        at.select_slider[0].set_value(72)
        at.run()
        assert len(at.exception) == 0
        assert at.select_slider[0].value == 72

        # Adjust Alpha slider to 0.60
        at.slider[0].set_value(0.60)
        at.run()
        assert len(at.exception) == 0
        assert abs(at.slider[0].value - 0.60) < 1e-4

    def test_apptest_sample_drawing_selection(self) -> None:
        at = AppTest.from_file(str(APP_FILE_PATH), default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Select pre-loaded radio option: "Load Sample Drawing from Workspace"
        radio = at.radio[0]
        radio.set_value("Load Sample Drawing from Workspace")
        at.run()
        assert len(at.exception) == 0

        # Select A-104 held-out set if available in dropdown
        select = at.selectbox[1]  # Selectbox for samples
        a104_option = [opt for opt in select.options if "A-104" in opt]
        if a104_option:
            select.set_value(a104_option[0])
            at.run()
            assert len(at.exception) == 0


# ==============================================================================
# TEST CLASS 3: Takeoff Arithmetic & Zero-Division Safety
# ==============================================================================

class TestTakeoffArithmeticAndSafety:
    """Validates takeoff calculations and zero-division defenses."""

    def test_takeoff_zero_division_guard(self) -> None:
        """Asserts that 100% background mask returns clean 0.0% without ZeroDivisionError."""
        empty_mask = np.zeros((500, 500), dtype=np.uint8)
        stats = compute_takeoff_stats(empty_mask, latency_sec=0.1)

        assert stats["total_pixels"] == 250000
        assert stats["background_pixels"] == 250000
        assert stats["wall_total_pixels"] == 0
        assert stats["wall_pct_canvas"] == 0.0
        assert stats["drywall_pct_walls"] == 0.0
        assert stats["non_drywall_pct_walls"] == 0.0
        assert stats["uncertain_pct_walls"] == 0.0
        assert stats["latency_sec"] == 0.1

    def test_takeoff_arithmetic_precision(self) -> None:
        """Asserts exact arithmetic breakdown with known synthetic distribution."""
        mask = np.zeros((100, 100), dtype=np.uint8)  # 10,000 total pixels
        # 500 Drywall pixels (50% of walls, 5% of canvas)
        mask[:5, :] = CLASS_DRYWALL
        # 300 Non-Drywall pixels (30% of walls, 3% of canvas)
        mask[5:8, :] = CLASS_NON_DRYWALL
        # 200 Uncertain pixels (20% of walls, 2% of canvas)
        mask[8:10, :] = CLASS_UNCERTAIN
        # Remaining 9,000 pixels are Background (0)

        stats = compute_takeoff_stats(mask, latency_sec=0.5)

        assert stats["total_pixels"] == 10000
        assert stats["wall_total_pixels"] == 1000
        assert stats["background_pixels"] == 9000
        assert stats["drywall_pixels"] == 500
        assert stats["non_drywall_pixels"] == 300
        assert stats["uncertain_pixels"] == 200

        assert stats["wall_pct_canvas"] == 10.0
        assert stats["drywall_pct_walls"] == 50.0
        assert stats["non_drywall_pct_walls"] == 30.0
        assert stats["uncertain_pct_walls"] == 20.0

    def test_csv_serialization(self) -> None:
        sample_stats = [
            {
                "page_index": 1,
                "sheet_name": "Sheet A-101",
                "total_pixels": 100000,
                "wall_total_pixels": 20000,
                "wall_pct_canvas": 20.0,
                "drywall_pixels": 15000,
                "drywall_pct_walls": 75.0,
                "non_drywall_pixels": 3000,
                "non_drywall_pct_walls": 15.0,
                "uncertain_pixels": 2000,
                "uncertain_pct_walls": 10.0,
                "latency_sec": 1.25,
            }
        ]
        csv_str = build_takeoff_csv_str(sample_stats)
        reader = list(csv.reader(io.StringIO(csv_str)))
        assert len(reader) == 2  # Header + 1 data row
        assert reader[0][0] == "page_index"
        assert reader[1][1] == "Sheet A-101"
        assert reader[1][6] == "75.0"


# ==============================================================================
# TEST CLASS 4: Error Handling for 0-byte and Corrupt PDF Uploads
# ==============================================================================

class TestEdgeCasesAndCorruptInputs:
    """Verifies graceful error handling for malformed or empty PDF streams."""

    def test_empty_and_corrupt_pdf_upload(self) -> None:
        import fitz

        # 0-byte input
        empty_bytes = b""
        with pytest.raises(Exception):
            fitz.open(stream=empty_bytes, filetype="pdf")

        # Corrupted stream
        corrupt_bytes = b"%PDF-1.4 CORRUPTED STREAM DATA NOT VALID"
        with pytest.raises(Exception):
            doc = fitz.open(stream=corrupt_bytes, filetype="pdf")
            doc.load_page(0)
