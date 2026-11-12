"""
drywall_detection/tests/test_challenger_m5_safety.py

Milestone M5 Empirical Challenger Adversarial Stress Suite:
1. Detail 1A CMU Safety Veto Attacks:
   - Tampered CSV ingestion attempts: case variations ("drywall", "DRYWALL"), whitespace padding,
     drywall synonyms ("GWB", "Gypsum Wallboard", "sheetrock", "1", "gyp bd", "gypsum board"),
     downgrade attempts to "Uncertain", UTF-8 BOM, zero-byte CSV, corrupted headers,
     omitted Detail 1A row, replaced 1A row.
   - Runtime Invariant attacks: direct instantiation of ClassifiedWallPolygon with 1A and Drywall,
     standard drywall synonyms, unregistered drywall synonyms ("gyp bd", "gypsum board"),
     post-initialization attribute mutation (tampering poly.classification or poly.matched_tag).
   - Pipeline classification invariant: unconditional Non-Drywall assignment in classify_walls.

2. Tier 3 Unassigned Fallback Attacks:
   - Candidate walls with missing tags, distant tags, empty string tags, whitespace-only tags ("   "),
     None tags (tag_id=None), unknown tags ("UNKNOWN_TAG"), and missing wall_id.
   - Verification of zero material hallucination: strictly Uncertain, confidence=0.0, matched_tag=None.

3. GeoJSON Schema & Takeoff Stress:
   - RFC 7946 compliance with degenerate Shapely geometries (empty Polygon, 0-area Polygon,
     self-intersecting bowtie Polygon, MultiPolygon, None geometry).
   - End-to-end GeoJSON file export and roundtrip disk serialization.
   - Material takeoff stress: negative coordinate bounds, large numbers (> 10^6), and
     takeoff accounting count consistency with degenerate geometries.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import pytest
from shapely.geometry import box, LineString, mapping, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from drywall_detection.classification import (
    ClassificationClass,
    ClassificationFeatureCollection,
    ClassificationSummary,
    ClassifiedWallPolygon,
    DrywallClassifier,
    IntegrityViolationError,
    ScheduleValidationError,
)
from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
)
from drywall_detection.pipeline import HybridFusionPipeline
from drywall_detection.vector.spatial_matcher import MatchMethod


# ==============================================================================
# Helper Fixtures & Synthetic Dummies
# ==============================================================================
class DummyCandidate:
    """Synthetic wall geometry candidate for spatial matching and classification."""
    def __init__(
        self,
        wall_id: str,
        geom_pdf: Optional[BaseGeometry] = None,
        thickness_pt: float = 8.35,
        estimated_thickness_in: float = 6.0,
        orientation: str = "HORIZONTAL",
    ):
        self.wall_id = wall_id
        self.geometry = geom_pdf if geom_pdf is not None else box(100.0, 100.0, 200.0, 108.35)
        self.geometry_pdf = self.geometry
        self.thickness_pt = thickness_pt
        self.estimated_thickness_in = estimated_thickness_in
        self.orientation = orientation


class DummyTag:
    """Synthetic partition tag symbol candidate with optional leader line."""
    def __init__(
        self,
        tag: Optional[str],
        box_geom: Optional[Polygon] = None,
        leader_line: Optional[LineString] = None,
    ):
        self.tag = tag
        self.tag_id = tag
        self.box_geom = box_geom if box_geom is not None else box(140.0, 120.0, 151.2, 131.3)
        self.bbox = self.box_geom.bounds
        self.center = (
            (self.box_geom.bounds[0] + self.box_geom.bounds[2]) / 2.0,
            (self.box_geom.bounds[1] + self.box_geom.bounds[3]) / 2.0,
        )
        self.centroid = self.center
        self.leader_line = leader_line
        self.leader_lines = [leader_line] if leader_line else []


@pytest.fixture
def classifier() -> DrywallClassifier:
    return DrywallClassifier()


@pytest.fixture
def valid_csv_rows() -> List[List[str]]:
    with open(APPROVED_SCHEDULE_CSV_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    return reader


# ==============================================================================
# Suite 1: Detail 1A CMU Safety Veto Adversarial Attacks
# ==============================================================================
class TestDetail1ACMUSafetyVetoIngestionGate:
    """
    Adversarially probe Layer 1 (Ingestion Gate) of Detail 1A CMU safety veto:
    Attempts to inject tampered CSVs must raise IntegrityViolationError or ScheduleValidationError.
    """

    @pytest.mark.parametrize("bad_val", [
        "drywall",
        "DRYWALL",
        "DrYwAlL",
        "  drywall  ",
        "\tDRYWALL\n",
        "Drywall",
    ])
    def test_tampered_csv_case_and_whitespace_raise_integrity_violation(
        self, valid_csv_rows: List[List[str]], tmp_path: Path, bad_val: str
    ) -> None:
        """Any case or whitespace variation of 'drywall' on Detail 1A must fail immediately."""
        header = valid_csv_rows[0]
        class_idx = header.index("proposed_class")
        rows = [list(r) for r in valid_csv_rows]
        for r in rows:
            if r[0] == "1A":
                r[class_idx] = bad_val

        csv_file = tmp_path / f"tampered_{bad_val.strip().lower()}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        with pytest.raises(IntegrityViolationError, match="INTEGRITY VIOLATION"):
            DrywallClassifier(approved_schedule_path=csv_file)

    @pytest.mark.parametrize("synonym", [
        "GWB",
        "gwb",
        "Gypsum Wallboard",
        "gypsum wallboard",
        "gypsum wall board",
        "sheetrock",
        "SHEETROCK",
        "1",
        "gyp bd",
        "gypsum board",
        "dry wall",
    ])
    def test_tampered_csv_drywall_synonyms_raise_integrity_violation(
        self, valid_csv_rows: List[List[str]], tmp_path: Path, synonym: str
    ) -> None:
        """Drywall synonyms and abbreviations on Detail 1A must fail immediately at ingestion."""
        header = valid_csv_rows[0]
        class_idx = header.index("proposed_class")
        rows = [list(r) for r in valid_csv_rows]
        for r in rows:
            if r[0] == "1A":
                r[class_idx] = synonym

        csv_file = tmp_path / f"syn_{synonym.replace(' ', '_')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        with pytest.raises(IntegrityViolationError, match="INTEGRITY VIOLATION"):
            DrywallClassifier(approved_schedule_path=csv_file)

    def test_tampered_csv_downgrade_to_uncertain_raises_integrity_violation(
        self, valid_csv_rows: List[List[str]], tmp_path: Path
    ) -> None:
        """Attempting to downgrade Detail 1A to 'Uncertain' must fail with IntegrityViolationError."""
        header = valid_csv_rows[0]
        class_idx = header.index("proposed_class")
        rows = [list(r) for r in valid_csv_rows]
        for r in rows:
            if r[0] == "1A":
                r[class_idx] = "Uncertain"

        csv_file = tmp_path / "downgrade_1a_uncertain.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        with pytest.raises(IntegrityViolationError, match="INTEGRITY VIOLATION"):
            DrywallClassifier(approved_schedule_path=csv_file)

    def test_zero_byte_csv_raises_schedule_validation_error(self, tmp_path: Path) -> None:
        """A 0-byte approved schedule CSV must raise ScheduleValidationError."""
        empty_csv = tmp_path / "zero_bytes.csv"
        empty_csv.write_bytes(b"")
        with pytest.raises(ScheduleValidationError, match="empty"):
            DrywallClassifier(approved_schedule_path=empty_csv)

    def test_corrupted_headers_raises_schedule_validation_error(self, tmp_path: Path) -> None:
        """CSV with corrupted or missing mandatory headers must raise ScheduleValidationError."""
        bad_csv = tmp_path / "bad_headers.csv"
        bad_csv.write_text("random_col1,random_col2\n1A,Non-Drywall\n", encoding="utf-8")
        with pytest.raises(ScheduleValidationError, match="missing mandatory"):
            DrywallClassifier(approved_schedule_path=bad_csv)

    def test_omitted_detail_1a_row_raises_error(
        self, valid_csv_rows: List[List[str]], tmp_path: Path
    ) -> None:
        """Omitting Detail 1A row entirely (23 rows) must raise an error."""
        rows = [r for r in valid_csv_rows if r[0] != "1A"]
        csv_file = tmp_path / "omitted_1a.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        with pytest.raises((IntegrityViolationError, ScheduleValidationError)):
            DrywallClassifier(approved_schedule_path=csv_file)

    def test_detail_1a_replaced_by_other_tag_raises_integrity_violation(
        self, valid_csv_rows: List[List[str]], tmp_path: Path
    ) -> None:
        """24-row CSV where 1A is replaced with '1X' must raise IntegrityViolationError."""
        rows = [list(r) for r in valid_csv_rows]
        for r in rows:
            if r[0] == "1A":
                r[0] = "1X"
        csv_file = tmp_path / "replaced_1a.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        with pytest.raises(IntegrityViolationError, match="Mandatory Detail 1A is missing"):
            DrywallClassifier(approved_schedule_path=csv_file)

    def test_utf8_bom_csv_loaded_successfully_with_canonical_1a(
        self, valid_csv_rows: List[List[str]], tmp_path: Path
    ) -> None:
        """CSV with UTF-8 BOM must load cleanly with Detail 1A as Non-Drywall."""
        csv_file = tmp_path / "bom_schedule.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(valid_csv_rows)

        c = DrywallClassifier(approved_schedule_path=csv_file)
        assert len(c.schedule_mapping) == 24
        assert c.schedule_mapping["1A"]["proposed_class"] == "Non-Drywall"

    @pytest.mark.parametrize("tag_variation", [" 1A ", "1a", "1A\t", "\t1a\n"])
    def test_detail_1a_tag_whitespace_and_case_normalized_to_canonical(
        self, valid_csv_rows: List[List[str]], tmp_path: Path, tag_variation: str
    ) -> None:
        """Detail 1A tag whitespace and lowercase variations in CSV must resolve to canonical 1A Non-Drywall."""
        rows = [list(r) for r in valid_csv_rows]
        for r in rows:
            if r[0] == "1A":
                r[0] = tag_variation
        csv_file = tmp_path / f"tag_var_{abs(hash(tag_variation))}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        c = DrywallClassifier(approved_schedule_path=csv_file)
        assert "1A" in c.schedule_mapping
        assert c.schedule_mapping["1A"]["proposed_class"] == "Non-Drywall"


class TestDetail1ACMURuntimeInvariant:
    """
    Adversarially probe Layer 2 (Runtime Invariant) of Detail 1A CMU safety veto:
    Direct instantiation, synonym injection, and post-init mutation attacks.
    """

    @pytest.mark.parametrize("drywall_class", [
        "Drywall",
        "drywall",
        "DRYWALL",
        "  Drywall  ",
        "GWB",
        "Gypsum Wallboard",
        "sheetrock",
        "1",
    ])
    def test_classified_wall_polygon_direct_instantiation_raises_on_standard_synonyms(
        self, drywall_class: str
    ) -> None:
        """Instantiating ClassifiedWallPolygon with tag='1A' and drywall classification must raise IntegrityViolationError."""
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU"):
            ClassifiedWallPolygon(
                wall_id="w_atk_01",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag="1A",
                detail_number="1A",
                material_description="6\" CMU Block",
                classification=drywall_class,
                confidence=1.0,
                color_hex="#00C853",
                reason="Adversarial direct instantiation attack",
            )

    @pytest.mark.parametrize("tag_var", ["1a", " 1A ", "1A\t", "\t1a\n"])
    def test_classified_wall_polygon_tag_case_and_whitespace_checked(self, tag_var: str) -> None:
        """Tag variations like '1a' or ' 1A ' must still trigger the runtime veto."""
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU"):
            ClassifiedWallPolygon(
                wall_id="w_atk_02",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag=tag_var,
                detail_number=tag_var,
                material_description="6\" CMU Block",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Case/whitespace bypass attempt",
            )

    def test_classified_wall_polygon_blocks_unregistered_drywall_synonyms(self) -> None:
        """
        Adversarial Probe: Detail 1A MUST NOT be classifiable under unregistered drywall
        synonyms ('gyp bd', 'gyp board', 'gypsum board', 'dry wall', 'gyp').
        Any non-Non-Drywall assignment on Detail 1A is an integrity violation.
        """
        unregistered_synonyms = ["gyp bd", "gyp board", "gypsum board", "dry wall", "gyp"]
        vulnerable_synonyms = []
        for syn in unregistered_synonyms:
            try:
                poly = ClassifiedWallPolygon(
                    wall_id=f"w_syn_{syn}",
                    page_idx=0,
                    sheet="A-101",
                    geometry_pdf=box(0, 0, 10, 10),
                    geometry_pixel=box(0, 0, 20, 20),
                    matched_tag="1A",
                    detail_number="1A",
                    material_description="6\" CMU Block",
                    classification=syn,
                    confidence=1.0,
                    color_hex="#00C853",
                    reason="Synonym injection attempt",
                )
                vulnerable_synonyms.append(syn)
            except IntegrityViolationError:
                pass

        assert not vulnerable_synonyms, (
            f"VULNERABILITY: Detail 1A runtime invariant bypassed with unregistered drywall synonyms: "
            f"{vulnerable_synonyms}. Detail 1A must ONLY be classifiable as Non-Drywall."
        )

    def test_classified_wall_polygon_prevents_post_init_mutation_to_drywall(self) -> None:
        """
        Adversarial Probe: Post-initialization attribute mutation attack.
        If a wall is created as 'Non-Drywall', mutating `poly.classification = 'Drywall'`
        must either be blocked by immutability (__setattr__) or raise IntegrityViolationError.
        """
        poly = ClassifiedWallPolygon(
            wall_id="w_mut_01",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1A",
            detail_number="1A",
            material_description="6\" CMU Block",
            classification="Non-Drywall",
            confidence=1.0,
            color_hex="#D50000",
            reason="Initial safe veto",
        )

        try:
            poly.classification = "Drywall"
        except (IntegrityViolationError, AttributeError, TypeError):
            # Immutability guard worked
            return

        # If mutation succeeded without error, test if downstream GeoJSON allows Drywall 1A
        feat = poly.to_geojson_feature()
        assert feat["properties"]["classification"] != "Drywall", (
            "VULNERABILITY: Detail 1A runtime invariant bypassed via post-init attribute mutation! "
            "ClassifiedWallPolygon allows field reassignment resulting in Drywall classification on Detail 1A."
        )

    @pytest.mark.parametrize("tag_val", ["1A", "1a", " 1A ", "1A\n", "\t1a\t"])
    def test_classify_walls_unconditionally_enforces_1a_non_drywall(
        self, classifier: DrywallClassifier, tag_val: str
    ) -> None:
        """DrywallClassifier.classify_walls must unconditionally produce Non-Drywall (#D50000) for Detail 1A."""
        wall = DummyCandidate("w_1a_pipe", box(100, 100, 200, 108.35))
        tag = DummyTag(tag_val, box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=14, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Non-Drywall"
        assert w.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
        assert w.matched_tag == "1A"
        assert "MANDATORY SAFETY VETO" in w.reason
        assert "CMU" in w.material_description.upper()


# ==============================================================================
# Suite 2: Tier 3 Unassigned Fallback Adversarial Attacks
# ==============================================================================
class TestTier3UnassignedFallbackAdversarial:
    """
    Adversarially probe Tier 3 Unassigned Fallback:
    Zero material hallucination invariant.
    Untagged, distant, empty, whitespace, unknown, and malformed tags must produce
    strictly Uncertain with confidence=0.0 and zero drywall hallucination.
    """

    def test_unassigned_candidate_wall_strict_uncertain_zero_confidence(
        self, classifier: DrywallClassifier
    ) -> None:
        """Candidate wall with no tags must produce Uncertain, confidence=0.0, matched_tag=None."""
        wall = DummyCandidate("w_untagged_01", box(300, 300, 500, 308.35))
        results = classifier.classify_walls([wall], [], page_idx=0, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.color_hex == CLASS_COLORS_HEX["Uncertain"]
        assert w.confidence == 0.0
        assert w.matched_tag is None
        assert w.detail_number is None
        assert w.match_method == "unassigned"
        assert "Tier 3" in w.reason

    def test_distant_tag_candidate_strict_uncertain_zero_confidence(
        self, classifier: DrywallClassifier
    ) -> None:
        """Candidate wall with tag placed far outside proximity buffer (> 50pt) must fall back to Tier 3."""
        wall = DummyCandidate("w_distant", box(100, 100, 200, 108.35))
        # Tag is at distance > 100 pt with no leader
        tag = DummyTag("1B", box(500, 500, 511.2, 511.3), leader_line=None)

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.confidence == 0.0
        assert w.matched_tag is None
        assert w.match_method == "unassigned"

    def test_empty_string_tag_candidate_strict_uncertain_zero_confidence(
        self, classifier: DrywallClassifier
    ) -> None:
        """Candidate wall associated with an empty string tag must fall back to Tier 3 unassigned."""
        wall = DummyCandidate("w_empty_tag", box(100, 100, 200, 108.35))
        tag = DummyTag("", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.confidence == 0.0
        assert w.matched_tag is None
        assert w.match_method == "unassigned"

    def test_unknown_tag_candidate_strictly_uncertain_zero_hallucination(
        self, classifier: DrywallClassifier
    ) -> None:
        """Candidate wall associated with unknown tag ('UNKNOWN_99') must NEVER be classified as Drywall."""
        wall = DummyCandidate("w_unk_tag", box(100, 100, 200, 108.35))
        tag = DummyTag("UNKNOWN_99", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.color_hex == CLASS_COLORS_HEX["Uncertain"]
        assert w.classification != "Drywall"
        assert w.classification != "Non-Drywall"

    def test_whitespace_only_tag_candidate_falls_back_to_unassigned_zero_confidence(
        self, classifier: DrywallClassifier
    ) -> None:
        """
        Adversarial Probe: Whitespace-only tag ('   ') has no semantic content.
        It must fall back to Tier 3 unassigned with confidence=0.0 and matched_tag=None.
        Assigning confidence > 0.0 or treating it as a matched tag violates zero-hallucination.
        """
        wall = DummyCandidate("w_ws_tag", box(100, 100, 200, 108.35))
        tag = DummyTag("   ", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        w = results[0]
        assert w.classification == "Uncertain"
        assert w.confidence == 0.0, (
            f"VULNERABILITY: Whitespace tag '   ' was assigned confidence={w.confidence} and matched_tag='{w.matched_tag}'. "
            f"Whitespace tags must fall back to Tier 3 unassigned with confidence=0.0 and matched_tag=None."
        )
        assert w.matched_tag is None

    def test_none_tag_candidate_does_not_crash_attribute_error(
        self, classifier: DrywallClassifier
    ) -> None:
        """
        Adversarial Probe: Candidate tag with tag_id=None or tag=None must not crash
        SpatialMatcher._resolve_classification with AttributeError: 'NoneType' object has no attribute 'upper'.
        It must safely resolve to Uncertain or Tier 3 unassigned fallback.
        """
        wall = DummyCandidate("w_none_tag", box(100, 100, 200, 108.35))
        tag = DummyTag(None, box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        try:
            results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        except AttributeError as e:
            pytest.fail(f"VULNERABILITY / BUG: SpatialMatcher crashed on None tag with AttributeError: {e}")

        assert len(results) == 1
        assert results[0].classification == "Uncertain"

    def test_missing_wall_id_fallback_generates_valid_id(
        self, classifier: DrywallClassifier
    ) -> None:
        """Wall dicts without 'wall_id' or with empty wall_id must not crash and receive unique IDs."""
        w_dict = {"geometry_pdf": box(100, 100, 200, 108.35)}
        results = classifier.classify_walls([w_dict], [], page_idx=0, sheet="A-101")
        assert len(results) == 1
        assert results[0].wall_id != ""
        assert results[0].classification == "Uncertain"


# ==============================================================================
# Suite 3: GeoJSON Schema & Takeoff Stress
# ==============================================================================
class TestGeoJSONSchemaAndTakeoffStress:
    """
    Adversarially probe RFC 7946 GeoJSON schema boundaries and takeoff calculations:
    Degenerate Shapely geometries, negative bounds, large coordinates, and count accounting.
    """

    def test_geojson_export_empty_polygon_rfc7946_compliance(
        self, classifier: DrywallClassifier, tmp_path: Path
    ) -> None:
        """Empty Polygon (Polygon()) must serialize to valid RFC 7946 GeoJSON without crashing."""
        empty_poly = Polygon()
        wall = ClassifiedWallPolygon(
            wall_id="w_deg_empty",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=empty_poly,
            geometry_pixel=empty_poly,
            matched_tag="1B",
            detail_number="1B",
            material_description="Standard Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Degenerate empty geometry test",
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["id"] == "w_deg_empty"
        # In GeoJSON RFC 7946, empty polygon coordinates map to []
        assert feat["geometry"]["type"] == "Polygon"
        dumped = json.dumps(feat)
        assert len(dumped) > 0

    def test_geojson_export_zero_area_polygon_rfc7946_compliance(
        self, classifier: DrywallClassifier
    ) -> None:
        """Zero-area collapsed Polygon must serialize to valid GeoJSON."""
        zero_poly = Polygon([(0.0, 0.0), (10.0, 0.0), (0.0, 0.0)])
        wall = ClassifiedWallPolygon(
            wall_id="w_deg_zero",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=zero_poly,
            geometry_pixel=zero_poly,
            matched_tag="1B",
            detail_number="1B",
            material_description="Standard Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Degenerate zero-area test",
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Polygon"

    def test_geojson_export_self_intersecting_polygon_rfc7946_compliance(
        self, classifier: DrywallClassifier
    ) -> None:
        """Self-intersecting bowtie polygon must serialize without error."""
        bowtie = Polygon([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0), (0.0, 0.0)])
        assert not bowtie.is_valid
        wall = ClassifiedWallPolygon(
            wall_id="w_deg_bowtie",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=bowtie,
            geometry_pixel=bowtie,
            matched_tag="1B",
            detail_number="1B",
            material_description="Standard Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="Degenerate invalid geometry test",
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Polygon"

    def test_geojson_export_multipolygon_rfc7946_compliance(
        self, classifier: DrywallClassifier
    ) -> None:
        """MultiPolygon wall assembly must serialize to MultiPolygon geometry in GeoJSON."""
        multi = MultiPolygon([box(0, 0, 10, 10), box(20, 20, 30, 30)])
        wall = ClassifiedWallPolygon(
            wall_id="w_deg_multi",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=multi,
            geometry_pixel=multi,
            matched_tag="1B",
            detail_number="1B",
            material_description="Standard Drywall",
            classification="Drywall",
            confidence=0.95,
            color_hex="#00C853",
            reason="MultiPolygon geometry test",
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "MultiPolygon"
        assert len(feat["geometry"]["coordinates"]) == 2

    def test_geojson_export_none_geometry_rfc7946_compliance(
        self, classifier: DrywallClassifier
    ) -> None:
        """None geometry must serialize to geometry: null per RFC 7946 Section 3.2."""
        wall = ClassifiedWallPolygon(
            wall_id="w_deg_none",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=None,
            geometry_pixel=None,
            matched_tag=None,
            detail_number=None,
            material_description="Unassigned",
            classification="Uncertain",
            confidence=0.0,
            color_hex="#FFD600",
            reason="None geometry test",
        )

        feat = wall.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["geometry"] is None

    def test_geojson_export_roundtrip_disk_serialization(
        self, classifier: DrywallClassifier, tmp_path: Path
    ) -> None:
        """Full GeoJSON FeatureCollection roundtrip write and load from disk."""
        poly1 = box(100, 100, 200, 108.35)
        poly2 = box(300, 300, 400, 308.35)
        w1 = DummyCandidate("w1", poly1)
        w2 = DummyCandidate("w2", poly2)
        tag1 = DummyTag("1C", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        classified = classifier.classify_walls([w1, w2], [tag1], page_idx=0, sheet="A-101")
        out_file = tmp_path / "roundtrip.geojson"
        classifier.export_geojson(classified, out_file, extra_metadata={"run_id": "test_m5"})

        assert out_file.is_file()
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2
        assert data["metadata"]["run_id"] == "test_m5"
        assert "summary" in data
        assert data["summary"]["drywall_count"] == 1
        assert data["summary"]["uncertain_count"] == 1

    def test_takeoff_classifier_summary_with_degenerate_geometries(
        self, classifier: DrywallClassifier
    ) -> None:
        """DrywallClassifier.compute_summary handles degenerate geometries without division by zero or NaN."""
        empty_poly = Polygon()
        multi = MultiPolygon([box(0, 0, 10, 10), box(20, 20, 30, 30)])
        w_empty = DummyCandidate("w_emp", empty_poly)
        w_multi = DummyCandidate("w_mul", multi)

        classified = classifier.classify_walls([w_empty, w_multi], [])
        summary = classifier.compute_summary(classified)
        assert summary.total_walls == 2
        assert summary.total_area_sq_pt == 200.0  # 100 + 100
        assert summary.uncertain_pct == 100.0

    def test_takeoff_fusion_summary_negative_bounds_and_large_numbers(self) -> None:
        """HybridFusionPipeline.compute_summary_statistics handles negative bounds and large numbers without error."""
        pipeline = HybridFusionPipeline()
        # Wall with negative coordinates (e.g. CAD origin offset)
        neg_poly = box(-1000.0, -500.0, -100.0, -490.0)  # length = 900 pt, area = 9000 sq pt
        # Wall with large coordinates
        big_poly = box(1_000_000.0, 1_000_000.0, 1_000_900.0, 1_000_010.0)  # length = 900 pt, area = 9000 sq pt

        w1 = ClassifiedWallPolygon(
            wall_id="w_neg", page_idx=0, sheet="A", geometry_pdf=neg_poly, geometry_pixel=neg_poly,
            matched_tag="1B", detail_number="1B", material_description="DW", classification="Drywall",
            confidence=1.0, color_hex="#00C853", reason="neg"
        )
        w2 = ClassifiedWallPolygon(
            wall_id="w_big", page_idx=0, sheet="A", geometry_pdf=big_poly, geometry_pixel=big_poly,
            matched_tag="1A", detail_number="1A", material_description="CMU", classification="Non-Drywall",
            confidence=1.0, color_hex="#D50000", reason="big"
        )

        summary = pipeline.compute_summary_statistics([w1, w2])
        assert summary["drywall_count"] == 1
        assert summary["nondrywall_count"] == 1
        # 900 pt / 9.0 = 100.0 LF
        assert summary["drywall_lf"] == 100.0
        assert summary["nondrywall_lf"] == 100.0
        # 9000 / 81 = 111.1 SqFt
        assert summary["drywall_sqft"] == 111.1
        assert summary["nondrywall_sqft"] == 111.1

    def test_takeoff_fusion_summary_accounting_consistency_with_empty_geometries(self) -> None:
        """
        Adversarial Probe: Takeoff summary accounting invariant:
        `total_walls` must equal `drywall_count + nondrywall_count + uncertain_count`.
        Empty or degenerate geometries must not create an accounting discrepancy.
        """
        pipeline = HybridFusionPipeline()
        w_valid = ClassifiedWallPolygon(
            wall_id="w_val", page_idx=0, sheet="A", geometry_pdf=box(0, 0, 90, 10), geometry_pixel=box(0, 0, 90, 10),
            matched_tag="1B", detail_number="1B", material_description="DW", classification="Drywall",
            confidence=1.0, color_hex="#00C853", reason="valid"
        )
        w_empty = ClassifiedWallPolygon(
            wall_id="w_emp", page_idx=0, sheet="A", geometry_pdf=Polygon(), geometry_pixel=Polygon(),
            matched_tag="1B", detail_number="1B", material_description="DW", classification="Drywall",
            confidence=1.0, color_hex="#00C853", reason="empty"
        )

        summary = pipeline.compute_summary_statistics([w_valid, w_empty])
        class_sum = summary["drywall_count"] + summary["nondrywall_count"] + summary["uncertain_count"]
        assert summary["total_walls"] == class_sum, (
            f"DISCREPANCY: Takeoff summary total_walls ({summary['total_walls']}) does not equal "
            f"the sum of class counts ({class_sum})! Empty geometries were skipped in class counts "
            f"but tallied in total_walls."
        )
