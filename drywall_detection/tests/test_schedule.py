"""
drywall_detection/tests/test_schedule.py

Test Suite: Partition Schedule Parsing, 24 Assembly Details & CSV Review Lock Protocol.
Target: drywall_detection/vector/schedule_parser.py
"""

from __future__ import annotations
import csv
from pathlib import Path
import pytest
from shapely.geometry import box, LineString, Point, Polygon

from drywall_detection.config import (
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
    EXIT_CODE_AWAITING_REVIEW,
)
from drywall_detection.vector.schedule_parser import (
    SCHEDULE_14_COLUMNS,
    PartitionScheduleParser,
    PartitionTagInstance,
    ScheduleDetailRecord,
)


class TestPartitionSchedule24Details:
    """Verifies complete parsing and cataloging of all 24 assembly details from Sheets A-900 & A-901."""

    EXPECTED_TAGS_A900 = {
        "1A", "1B", "1C", "1D", "1E", "2B", "2C", "3A", "3D", "5B", "5D", "5E"
    }
    EXPECTED_TAGS_A901 = {
        "7A", "7B", "7C", "7E", "7F", "7G", "8A", "GL1", "GL2", "09", "10", "11"
    }

    def test_total_assembly_count_is_24(self) -> None:
        """The authoritative schedule dictionary must contain exactly 24 assembly details."""
        parser = PartitionScheduleParser()
        all_tags = parser.EXPECTED_TAGS_A900 if hasattr(parser, "EXPECTED_TAGS_A900") else (
            self.EXPECTED_TAGS_A900 | self.EXPECTED_TAGS_A901
        )
        assert len(self.EXPECTED_TAGS_A900) == 12
        assert len(self.EXPECTED_TAGS_A901) == 12
        assert len(all_tags) == 24

        records = [parser.get_detail(t) for t in all_tags]
        assert all(r is not None for r in records), "All 24 tags must be present in schedule parser"
        assert len(records) == 24

    def test_detail_1a_cmu_masonry_attributes(self) -> None:
        """
        MANDATORY SAFETY INVARIANT: Detail 1A is explicitly 6" CMU masonry block.
        Must be Non-Drywall (Red), NEVER Drywall.
        """
        parser = PartitionScheduleParser()
        rec_1a = parser.get_detail("1A")
        assert rec_1a is not None
        assert rec_1a.proposed_class == "Non-Drywall"
        assert rec_1a.proposed_class != "Drywall"
        assert "CMU" in rec_1a.description.upper()
        assert rec_1a.material_trade.lower() == "masonry"
        assert rec_1a.confidence == 1.0

    def test_material_distribution_breakdown(self) -> None:
        """Verifies correct class assignment across all 24 details."""
        parser = PartitionScheduleParser()
        non_drywall_tags = {"1A", "11", "GL1", "GL2"}
        uncertain_tags = {"09"}
        drywall_tags = (self.EXPECTED_TAGS_A900 | self.EXPECTED_TAGS_A901) - non_drywall_tags - uncertain_tags

        for tag in drywall_tags:
            rec = parser.get_detail(tag)
            assert rec is not None
            assert rec.proposed_class == "Drywall", f"Tag {tag} expected Drywall, got {rec.proposed_class}"

        for tag in non_drywall_tags:
            rec = parser.get_detail(tag)
            assert rec is not None
            assert rec.proposed_class == "Non-Drywall", f"Tag {tag} expected Non-Drywall, got {rec.proposed_class}"

        for tag in uncertain_tags:
            rec = parser.get_detail(tag)
            assert rec is not None
            assert rec.proposed_class == "Uncertain", f"Tag {tag} expected Uncertain, got {rec.proposed_class}"


class TestFloorPlanTagDiscovery:
    """Verifies detection of 11.2 x 11.3 pt tag boxes and leader lines."""

    class MockFloorPlanPage:
        def __init__(self, drawings, text_blocks):
            self._drawings = drawings
            self._text_dict = {"blocks": text_blocks}

        def get_drawings(self):
            return self._drawings

        def get_text(self, kind="text"):
            if kind == "dict":
                return self._text_dict
            return ""

    def test_tag_box_and_leader_discovery(self) -> None:
        """Discovers tag symbol box (11.2 x 11.3 pt), centered text '2C', and orthogonal leader line."""
        class FitzRect:
            def __init__(self, x0, y0, x1, y1):
                self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
                self.width = x1 - x0
                self.height = y1 - y0

            def intersects(self, other):
                return not (self.x1 < other.x0 or self.x0 > other.x1 or self.y1 < other.y0 or self.y0 > other.y1)

            def contains(self, other):
                return self.x0 <= other.x0 and self.y0 <= other.y0 and self.x1 >= other.x1 and self.y1 >= other.y1

        class FitzPoint:
            def __init__(self, x, y):
                self.x, self.y = x, y

        # Box rect: width=11.2, height=11.3 at (500.0, 500.0) -> (511.2, 511.3)
        box_drawing = {
            "rect": FitzRect(500.0, 500.0, 511.2, 511.3),
            "width": 0.48,
            "type": "s",
            "items": [],
        }
        # Leader line extending from (505.6, 500.0) to (505.6, 490.0) (upwards by 10 pt)
        leader_drawing = {
            "rect": FitzRect(505.6, 490.0, 505.6, 500.0),
            "width": 0.48,
            "type": "s",
            "items": [("l", FitzPoint(505.6, 500.0), FitzPoint(505.6, 490.0))],
        }

        # Text inside the box: "2C"
        text_blocks = [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "2C",
                                "bbox": (502.0, 502.0, 509.0, 509.0),
                                "font": "ArialNarrow",
                                "size": 8.29,
                            }
                        ]
                    }
                ],
            }
        ]

        page = self.MockFloorPlanPage([box_drawing, leader_drawing], text_blocks)
        parser = PartitionScheduleParser()

        tags = parser.discover_tags(page, page_idx=14, sheet_name="A-101")
        assert len(tags) == 1

        tag = tags[0]
        assert tag.tag == "2C"
        assert tag.sheet == "A-101"
        assert tag.classification == "Drywall"
        assert tag.leader_line is not None
        assert len(tag.leader_lines) == 1
        assert tag.leader_target_pt == (505.6, 490.0)


class TestCSVExportAndReviewLock:
    """Verifies 14-column CSV generation, REVIEW_REQUIRED.lock creation, and exit code 2."""

    def test_csv_columns_match_contract(self, tmp_path: Path) -> None:
        """The exported CSV must have exactly 14 columns matching the contract."""
        csv_path = tmp_path / "partition_schedule_mapping.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            lock_path=lock_path,
            interactive_mode=False,
        )

        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

        assert len(header) == 14
        assert header == SCHEDULE_14_COLUMNS

    def test_lockfile_generation_and_content(self, tmp_path: Path) -> None:
        """When approved CSV is missing, REVIEW_REQUIRED.lock is generated with instructions."""
        csv_path = tmp_path / "partition_schedule_mapping.csv"
        appr_path = tmp_path / "partition_schedule_mapping.approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )

        assert res is False
        assert lock_path.exists()

        content = lock_path.read_text(encoding="utf-8")
        assert "MANUAL REVIEW REQUIRED (EXIT CODE 2)" in content
        assert "AWAITING_HUMAN_APPROVAL" in content
        assert "Detail 1A" in content
        assert "Non-Drywall" in content

    def test_exit_code_2_on_unapproved_run(self, tmp_path: Path) -> None:
        """Interactive mode exits with code 2 when approved CSV is absent."""
        csv_path = tmp_path / "partition_schedule_mapping.csv"
        appr_path = tmp_path / "partition_schedule_mapping.approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        with pytest.raises(SystemExit) as excinfo:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=True,
            )

        assert excinfo.value.code == EXIT_CODE_AWAITING_REVIEW
        assert excinfo.value.code == 2

    def test_approved_csv_bypasses_lock(self, tmp_path: Path) -> None:
        """Presence of valid approved CSV bypasses lock and removes lockfile."""
        csv_path = tmp_path / "partition_schedule_mapping.csv"
        appr_path = tmp_path / "partition_schedule_mapping.approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        # Generate lock first
        parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert lock_path.exists()

        # Create valid approved CSV (copy generated CSV)
        appr_path.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")

        # Rerun
        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )

        assert res is True
        assert not lock_path.exists()

    def test_tampered_detail_1a_approved_csv_raises_error(self, tmp_path: Path) -> None:
        """If user or attacker attempts to approve Detail 1A as Drywall, raises ValueError."""
        csv_path = tmp_path / "partition_schedule_mapping.csv"
        appr_path = tmp_path / "partition_schedule_mapping.approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        # Write approved CSV with illegal 1A = Drywall
        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "tag": "1A",
                "sheet": "A-900",
                "detail_title": "1A CMU",
                "description": "6\" CMU",
                "studs": "None",
                "layers": "0",
                "gwb_thickness": "None",
                "fire_rating": "1-HR",
                "acoustic": "None",
                "finish": "None",
                "material_trade": "Masonry",
                "proposed_class": "Drywall",  # ILLEGAL TAMPERING!
                "confidence": 1.0,
                "notes": "Tampered",
            })

        with pytest.raises(ValueError) as excinfo:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )

        assert "INTEGRITY VIOLATION" in str(excinfo.value)
        assert "Detail 1A" in str(excinfo.value)
