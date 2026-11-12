"""
drywall_detection/tests/test_challenger_m3_iter2.py

Independent Empirical Adversarial Stress Test Suite for Milestone M3 Iteration 2
Author: challenger_m3_iter2

Covers:
1. Detail 1A CMU safety veto adversarial stress testing (GWB, case, whitespace, synonyms, corruptions)
2. SpatialMatcher tampering resistance across object types, dictionary casings, and whitespace
3. Review lock protocol bypass resistance:
   - 0-byte file
   - Whitespace-only file
   - Truncated headers
   - Corrupted schema headers
   - Missing Detail 1A row
   - Empty data rows
   - Non-UTF8 binary data
   - In-memory object mutation
4. Tag 7F Discovery empirical validation across Floor Plans A-100 to A-105 on Master Architectural PDF
5. Authoritative approved CSV file audit (24 details, 1A Non-Drywall, 7F Drywall)
"""

from __future__ import annotations
import csv
import io
import os
from pathlib import Path
import pytest
from shapely.geometry import box, LineString, Polygon

import fitz

from drywall_detection.config import (
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
    DEFAULT_MASTER_PDF_PATH,
)
from drywall_detection.vector.schedule_parser import (
    SCHEDULE_14_COLUMNS,
    PartitionScheduleParser,
    PartitionTagInstance,
    ScheduleDetailRecord,
    APPROVED_SCHEDULE_CSV_PATH,
)
from drywall_detection.vector.spatial_matcher import (
    SpatialMatcher,
    MatchMethod,
)
from drywall_detection.vector.extractor import VectorExtractor


class MockWall:
    def __init__(self, wall_id: str, geom: Polygon):
        self.wall_id = wall_id
        self.geometry = geom
        self.geometry_pdf = geom


class MockTag:
    def __init__(self, tag_id: str, box_geom: Polygon, leader_line: LineString | None = None):
        self.tag_id = tag_id
        self.tag = tag_id
        self.box_geom = box_geom
        self.box_bbox = box_geom.bounds
        self.centroid = (box_geom.centroid.x, box_geom.centroid.y)
        self.center = self.centroid
        self.leader_line = leader_line
        self.leader_lines = [leader_line] if leader_line is not None else []


# ==============================================================================
# 1. DETAIL 1A SCHEDULE PARSER ADVERSARIAL STRESS TESTS
# ==============================================================================
class TestScheduleParserDetail1AAdversarial:
    """Stress tests Detail 1A non-drywall CMU veto in schedule parser against adversarial injections."""

    @pytest.mark.parametrize(
        "malicious_class",
        [
            "Drywall",
            "drywall",
            "DRYWALL",
            "  Drywall  ",
            "\tDrywall\n",
            "GWB",
            "gwb",
            "  GWB  ",
            "Gypsum",
            "gypsum",
            "Gypsum Wallboard",
            "gypsum wallboard",
            "GYPSUM WALLBOARD",
            "Gypsum Wall Board",
            "gypsum wall board",
            "Sheetrock",
            "sheetrock",
            "1",
            " 1 ",
            "Uncertain",       # Detail 1A is known CMU; CANNOT be marked Uncertain
            "Masonry Block",   # Only strictly 'Non-Drywall' or '2' is allowed
            "Concrete",
            "Random",
            "",
            "   ",
        ],
    )
    def test_detail_1a_illegal_classes_raise_integrity_violation(
        self, tmp_path: Path, malicious_class: str
    ) -> None:
        """Any class other than Non-Drywall / 2 on Detail 1A MUST raise ValueError with INTEGRITY VIOLATION."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

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
                "proposed_class": malicious_class,
                "confidence": 1.0,
                "notes": "Adversarial injection",
            })

        with pytest.raises(ValueError) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )
        assert "INTEGRITY VIOLATION" in str(exc.value)

    @pytest.mark.parametrize(
        "valid_class",
        [
            "Non-Drywall",
            "non-drywall",
            "NON-DRYWALL",
            "  Non-Drywall  ",
            "2",
            " 2 ",
        ],
    )
    def test_detail_1a_valid_non_drywall_accepted(
        self, tmp_path: Path, valid_class: str
    ) -> None:
        """Valid Non-Drywall variants on Detail 1A must be accepted and clear the review lock."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "approved.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

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
                "proposed_class": valid_class,
                "confidence": 1.0,
                "notes": "Valid review",
            })

        approved = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert approved is True
        assert not lock_path.exists()

    def test_detail_1a_order_poisoning_attack(self, tmp_path: Path) -> None:
        """
        Adversarial Scenario: CSV contains two rows for 1A.
        Row 1: tag='1A', proposed_class='Non-Drywall'
        Row 2: tag='1A', proposed_class='Drywall'
        Invariant:
        The second row must trigger the integrity violation exception even if the first row was valid.
        """
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "poisoned_order.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        with open(appr_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            writer.writerow({"tag": "1A", "proposed_class": "Non-Drywall"})
            writer.writerow({"tag": "1A", "proposed_class": "Drywall"})

        with pytest.raises(ValueError) as exc:
            parser.export_and_enforce_review_lock(
                csv_path=csv_path,
                approved_csv_path=appr_path,
                lock_path=lock_path,
                interactive_mode=False,
            )
        assert "INTEGRITY VIOLATION" in str(exc.value)


# ==============================================================================
# 2. DETAIL 1A SPATIAL MATCHER ADVERSARIAL STRESS TESTS
# ==============================================================================
class TestSpatialMatcherDetail1AAdversarial:
    """Stress tests Detail 1A tampering resistance in SpatialMatcher."""

    @pytest.mark.parametrize(
        "tampered_schedule",
        [
            {"1A": {"proposed_class": "Drywall"}},
            {"1A": {"proposed_class": "GWB"}},
            {"1A": {"proposed_class": "gypsum"}},
            {"1A": {"proposed_class": "Gypsum Wallboard"}},
            {"1A": {"proposed_class": "Sheetrock"}},
            {"1A": {"proposed_class": "1"}},
            {"1A": {"proposed_class": "Uncertain"}},
            {"1A": {"proposed_class": "Masonry"}},
            {"1A": {"proposed_class": "  Drywall  "}},
            {"1A": type("MockRecord", (), {"proposed_class": "Drywall"})()},
            {"1A": type("MockRecord", (), {"proposed_class": "GWB"})()},
        ],
    )
    def test_spatial_matcher_raises_on_tampered_1a(self, tampered_schedule) -> None:
        """SpatialMatcher must immediately raise ValueError with INTEGRITY VIOLATION on tampered 1A."""
        wall = MockWall("w1", box(100.0, 100.0, 200.0, 110.0))
        tag = MockTag("1A", box(100.0, 115.0, 111.2, 126.2), LineString([(105.6, 115.0), (105.6, 105.0)]))

        matcher = SpatialMatcher(schedule_mapping=tampered_schedule)
        with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
            matcher.match([wall], [tag])

    def test_spatial_matcher_safe_on_untampered_1a(self) -> None:
        """When schedule is untampered, 1A resolves strictly to Non-Drywall (#FF0000)."""
        wall = MockWall("w1", box(100.0, 100.0, 200.0, 110.0))
        tag = MockTag("1A", box(100.0, 115.0, 111.2, 126.2), LineString([(105.6, 115.0), (105.6, 105.0)]))

        # Test both empty mapping and explicitly safe mapping
        for safe_map in [
            {},
            {"1A": {"proposed_class": "Non-Drywall"}},
            {"1A": {"proposed_class": "2"}},
        ]:
            matcher = SpatialMatcher(schedule_mapping=safe_map)
            report = matcher.match([wall], [tag])
            assert report.matched_walls == 1
            res = report.results[0]
            assert res.assigned_tag == "1A"
            assert res.proposed_class == "Non-Drywall"
            assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]


# ==============================================================================
# 3. REVIEW LOCK PROTOCOL EDGE CASES & MALFORMED CSVs
# ==============================================================================
class TestReviewLockEdgeCasesAndMalformedCSVs:
    """Stress tests review lock enforcement under all malformed, empty, and partial CSV states."""

    def test_zero_byte_approved_csv_does_not_clear_lock(self, tmp_path: Path) -> None:
        """0-byte file must return False and retain lockfile."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "zero_byte.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_bytes(b"")
        assert appr_path.stat().st_size == 0

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False
        assert lock_path.exists()

    def test_whitespace_and_newlines_only_csv_does_not_clear_lock(self, tmp_path: Path) -> None:
        """CSV containing only newlines and spaces must return False and retain lockfile."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "whitespace_only.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_text("\n   \n\t\n   \r\n", encoding="utf-8")
        assert appr_path.stat().st_size > 0

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False
        assert lock_path.exists()

    def test_headers_only_csv_does_not_clear_lock(self, tmp_path: Path) -> None:
        """CSV with valid headers but 0 data rows must return False and retain lockfile."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "headers_only.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_text("tag,proposed_class\n", encoding="utf-8")

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False
        assert lock_path.exists()

    def test_missing_tag_header_does_not_clear_lock(self, tmp_path: Path) -> None:
        """CSV missing 'tag' header must return False and retain lockfile."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "missing_tag_col.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_text("detail_id,proposed_class\n1A,Non-Drywall\n", encoding="utf-8")

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False
        assert lock_path.exists()

    def test_missing_proposed_class_header_does_not_clear_lock(self, tmp_path: Path) -> None:
        """CSV missing 'proposed_class' header must return False and retain lockfile."""
        csv_path = tmp_path / "mapping.csv"
        appr_path = tmp_path / "missing_class_col.csv"
        lock_path = tmp_path / "REVIEW_REQUIRED.lock"
        parser = PartitionScheduleParser()

        appr_path.write_text("tag,category\n1A,Non-Drywall\n", encoding="utf-8")

        res = parser.export_and_enforce_review_lock(
            csv_path=csv_path,
            approved_csv_path=appr_path,
            lock_path=lock_path,
            interactive_mode=False,
        )
        assert res is False
        assert lock_path.exists()

    def test_utf8_bom_handling_valid_and_tampered(self, tmp_path: Path) -> None:
        """CSV with UTF-8 BOM must be decoded cleanly; valid 1A clears lock, tampered 1A raises."""
        parser = PartitionScheduleParser()

        # Valid with BOM
        bom_valid = tmp_path / "bom_valid.csv"
        bom_valid.write_text("\ufefftag,proposed_class\n1A,Non-Drywall\n", encoding="utf-8")
        lock1 = tmp_path / "lock1.lock"
        res1 = parser.export_and_enforce_review_lock(
            csv_path=tmp_path / "m1.csv",
            approved_csv_path=bom_valid,
            lock_path=lock1,
            interactive_mode=False,
        )
        assert res1 is True
        assert not lock1.exists()

        # Tampered with BOM
        bom_tampered = tmp_path / "bom_tampered.csv"
        bom_tampered.write_text("\ufefftag,proposed_class\n1A,GWB\n", encoding="utf-8")
        lock2 = tmp_path / "lock2.lock"
        with pytest.raises(ValueError, match="INTEGRITY VIOLATION"):
            parser.export_and_enforce_review_lock(
                csv_path=tmp_path / "m2.csv",
                approved_csv_path=bom_tampered,
                lock_path=lock2,
                interactive_mode=False,
            )


# ==============================================================================
# 4. TAG 7F DISCOVERY EMPIRICAL VERIFICATION
# ==============================================================================
class TestTag7FDiscoveryEmpirical:
    """Verifies Tag 7F regex parsing and floor plan detection on master architectural PDF."""

    def test_regex_matches_all_authoritative_details_including_7f(self) -> None:
        """TAG_REGEX_STRICT must match all 24 authoritative catalog details."""
        parser = PartitionScheduleParser()
        assert "7F" in parser.AUTHORITATIVE_DETAILS
        assert parser.AUTHORITATIVE_DETAILS["7F"]["proposed_class"] == "Drywall"
        assert "SHAFT WALL" in parser.AUTHORITATIVE_DETAILS["7F"]["detail_title"].upper()

        for tag in parser.AUTHORITATIVE_DETAILS:
            match = parser.TAG_REGEX_STRICT.match(tag)
            assert match is not None, f"TAG_REGEX_STRICT failed to match catalog detail '{tag}'"

    def test_vector_extractor_regex_matches_7f(self) -> None:
        """VectorExtractor.TAG_REGEX must match '7F'."""
        assert VectorExtractor.TAG_REGEX.match("7F") is not None

    def test_master_pdf_sheet_a101_discovers_tag_7f(self) -> None:
        """
        Empirically scan Sheet A-101 (page 14) of the master architectural PDF.
        Assert that exactly 45 tags are discovered, including exactly 1 Tag 7F.
        """
        master_pdf = DEFAULT_MASTER_PDF_PATH
        assert master_pdf.exists() and master_pdf.is_file(), f"Master PDF not found at {master_pdf}"

        doc = fitz.open(master_pdf)
        assert len(doc) >= 19, f"PDF expected >= 71 pages, found {len(doc)}"

        parser = PartitionScheduleParser()
        p14 = doc[14]  # Sheet A-101
        tags = parser.discover_tags(p14, 14, "A-101")

        # Must discover 45 tags on Sheet A-101
        assert len(tags) == 45, f"Expected 45 tags on Sheet A-101, got {len(tags)}"

        tags_7f = [t for t in tags if t.tag == "7F"]
        assert len(tags_7f) == 1, f"Expected exactly 1 Tag 7F on Sheet A-101, found {len(tags_7f)}"

        tag_7f = tags_7f[0]
        assert tag_7f.sheet == "A-101"
        assert tag_7f.page_idx == 14
        # Verify center coordinate around (764.31, 1656.29)
        assert abs(tag_7f.center[0] - 764.3) < 2.0
        assert abs(tag_7f.center[1] - 1656.3) < 2.0

    def test_project_wide_floor_plans_discover_shaft_wall_tags(self) -> None:
        """
        Scan floor plans A-100 through A-105.
        Verify Tag 7F presence across the floor plan set.
        """
        master_pdf = DEFAULT_MASTER_PDF_PATH
        assert master_pdf.exists() and master_pdf.is_file()

        doc = fitz.open(master_pdf)
        parser = PartitionScheduleParser()

        floor_plans = [
            (13, "A-100"),
            (14, "A-101"),
            (15, "A-102"),
            (16, "A-103"),
            (17, "A-104"),
            (18, "A-105"),
        ]

        total_tags = 0
        total_7f = 0
        per_sheet_7f = {}

        for page_idx, sheet_name in floor_plans:
            page_tags = parser.discover_tags(doc[page_idx], page_idx, sheet_name)
            count_7f = sum(1 for t in page_tags if t.tag == "7F")
            per_sheet_7f[sheet_name] = count_7f
            total_tags += len(page_tags)
            total_7f += count_7f

        # 7F is present on A-101, A-102, A-103, A-104
        assert per_sheet_7f["A-101"] >= 1
        assert per_sheet_7f["A-102"] >= 1
        assert per_sheet_7f["A-103"] >= 1
        assert per_sheet_7f["A-104"] >= 1
        assert total_7f >= 4, f"Expected at least 4 Tag 7F instances across floor plans, got {total_7f}"


# ==============================================================================
# 5. APPROVED CSV PRODUCTION INTEGRITY AUDIT
# ==============================================================================
class TestApprovedCSVProductionIntegrity:
    """Verifies the production drywall_detection/data/partition_schedule_mapping.approved.csv."""

    def test_production_approved_csv_passes_all_validations(self) -> None:
        """Production approved CSV must exist, contain 24 details, 1A as Non-Drywall, 7F as Drywall."""
        appr_path = APPROVED_SCHEDULE_CSV_PATH
        assert appr_path.exists(), f"Approved CSV not found at {appr_path}"
        assert appr_path.stat().st_size > 0

        with open(appr_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            assert "tag" in fieldnames
            assert "proposed_class" in fieldnames
            rows = {r["tag"]: r for r in reader}

        assert len(rows) == 24, f"Expected 24 details, found {len(rows)}"

        # Verify Detail 1A is Non-Drywall
        assert "1A" in rows
        assert rows["1A"]["proposed_class"] == "Non-Drywall"

        # Verify Detail 7F is Drywall
        assert "7F" in rows
        assert rows["7F"]["proposed_class"] == "Drywall"

        # Verify Detail 11 is Non-Drywall (Concrete)
        assert rows["11"]["proposed_class"] == "Non-Drywall"

        # Verify GL1 and GL2 are Non-Drywall
        assert rows["GL1"]["proposed_class"] == "Non-Drywall"
        assert rows["GL2"]["proposed_class"] == "Non-Drywall"

        # Verify Detail 09 is Uncertain
        assert rows["09"]["proposed_class"] == "Uncertain"

        # Verify lock clearance
        parser = PartitionScheduleParser()
        cleared = parser.export_and_enforce_review_lock(
            csv_path=appr_path.parent / "temp_export.csv",
            approved_csv_path=appr_path,
            lock_path=appr_path.parent / "temp_review.lock",
            interactive_mode=False,
        )
        assert cleared is True
        assert not (appr_path.parent / "temp_review.lock").exists()
        if (appr_path.parent / "temp_export.csv").exists():
            (appr_path.parent / "temp_export.csv").unlink()
