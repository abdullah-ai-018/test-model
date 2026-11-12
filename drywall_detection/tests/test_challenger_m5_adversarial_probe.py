"""
drywall_detection/tests/test_challenger_m5_adversarial_probe.py

Adversarial Stress Harness & Empirical Verification Suite (Milestone M5 - Iteration 2).
Author: challenger_m5_iter2_1 (Empirical Challenger)
Focus:
  1. Adversarial probing of __setattr__ runtime mutation guards on ClassifiedWallPolygon
  2. Adversarial probing of Detail 1A CMU invariant against all synonym variants and tags
  3. Probing reflective bypass vectors (object.__setattr__, __dict__, subclassing)
  4. Exhaustive regression verification of VULN-M5-01 through VULN-M5-05
"""

import copy
from typing import Optional
import pytest
from shapely.geometry import box, LineString, Polygon

from drywall_detection.config import CLASS_COLORS_HEX
from drywall_detection.classification.classifier import (
    ClassifiedWallPolygon,
    ClassificationClass,
    DrywallClassifier,
    IntegrityViolationError,
)
from drywall_detection.vector.spatial_matcher import SpatialMatcher


class DummyCandidate:
    def __init__(self, wall_id: str, geometry: Polygon, thickness_pt: float = 6.0):
        self.wall_id = wall_id
        self.geometry_pdf = geometry
        self.geometry_pixel = geometry
        self.thickness_pt = thickness_pt
        self.estimated_thickness_in = 5.0
        self.orientation = "HORIZONTAL"


class DummyTag:
    def __init__(self, tag: Optional[str], box_geom: Optional[Polygon] = None, leader_line: Optional[LineString] = None):
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


# ==============================================================================
# 1. Adversarial Probing of __setattr__ Runtime Mutation Guard
# ==============================================================================
class TestSetattrRuntimeMutationAdversarial:
    """Stress tests on ClassifiedWallPolygon.__setattr__ mutation guards."""

    def test_mutation_to_drywall_blocked(self):
        poly = ClassifiedWallPolygon(
            wall_id="w_adv_01",
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
            reason="Detail 1A safe",
        )
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            poly.classification = "Drywall"

    @pytest.mark.parametrize(
        "bad_class",
        [
            "drywall",
            "DRYWALL",
            "DryWall",
            "gwb",
            "GWB",
            "Gypsum Wallboard",
            "gypsum board",
            "gyp bd",
            "sheetrock",
            "1",
            "Uncertain",
            "uncertain",
            "0",
            "3",
            "",
            "RandomString",
            ClassificationClass.DRYWALL,
            ClassificationClass.UNCERTAIN,
        ],
    )
    def test_mutation_to_any_non_nondrywall_blocked(self, bad_class):
        poly = ClassifiedWallPolygon(
            wall_id="w_adv_02",
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
            reason="Detail 1A safe",
        )
        with pytest.raises(IntegrityViolationError):
            poly.classification = bad_class

    def test_mutation_to_nondrywall_allowed(self):
        poly = ClassifiedWallPolygon(
            wall_id="w_adv_03",
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
            reason="Detail 1A safe",
        )
        # Re-assigning valid Non-Drywall values must not crash
        poly.classification = "Non-Drywall"
        poly.classification = "2"
        poly.classification = ClassificationClass.NON_DRYWALL
        assert poly.classification == ClassificationClass.NON_DRYWALL

    @pytest.mark.parametrize("tag_1a_val", ["1A", "1a", " 1A ", "1A\t", "\t1a\n"])
    def test_retroactive_tag_assignment_blocked_on_drywall(self, tag_1a_val):
        """A wall classified as Drywall cannot have its matched_tag or detail_number mutated to 1A."""
        poly = ClassifiedWallPolygon(
            wall_id="w_adv_04",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1B",
            detail_number="1B",
            material_description="GWB",
            classification="Drywall",
            confidence=1.0,
            color_hex="#00C853",
            reason="Detail 1B safe",
        )
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU"):
            poly.matched_tag = tag_1a_val

        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU"):
            poly.detail_number = tag_1a_val

    def test_normal_walls_allow_mutation(self):
        """Non-1A walls (e.g. 1B) must allow normal attribute mutation without raising IntegrityViolationError."""
        poly = ClassifiedWallPolygon(
            wall_id="w_adv_05",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1B",
            detail_number="1B",
            material_description="GWB",
            classification="Drywall",
            confidence=1.0,
            color_hex="#00C853",
            reason="Detail 1B",
        )
        poly.classification = "Uncertain"
        assert poly.classification == "Uncertain"
        poly.classification = "Drywall"
        assert poly.classification == "Drywall"


# ==============================================================================
# 2. Adversarial Probing of Detail 1A Direct Instantiation & Synonyms
# ==============================================================================
class TestDetail1ADirectInstantiationSynonymsAdversarial:
    """Stress tests on ClassifiedWallPolygon.__post_init__ invariant against arbitrary synonyms."""

    @pytest.mark.parametrize(
        "synonym",
        [
            "Drywall",
            "drywall",
            "DRYWALL",
            "DrYwAlL",
            "gwb",
            "GWB",
            "gypsum",
            "gypsum wallboard",
            "gypsum wall board",
            "sheetrock",
            "SHEETROCK",
            "1",
            "gyp bd",
            "gyp board",
            "gypsum board",
            "dry wall",
            "gyp",
            "Uncertain",
            "cmu",
            "concrete",
            "wood",
            "glass",
            "",
            "   ",
        ],
    )
    def test_direct_instantiation_raises_on_any_non_nondrywall_synonym(self, synonym):
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            ClassifiedWallPolygon(
                wall_id="w_syn_adv",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag="1A",
                detail_number="1A",
                material_description="CMU",
                classification=synonym,
                confidence=1.0,
                color_hex="#00C853",
                reason="Adversarial synonym injection",
            )

    @pytest.mark.parametrize("tag_var", ["1a", " 1A ", "1A\t", "\t1a\n"])
    def test_direct_instantiation_raises_on_tag_variations_with_drywall(self, tag_var):
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            ClassifiedWallPolygon(
                wall_id="w_tag_adv",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag=tag_var,
                detail_number=None,
                material_description="CMU",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Adversarial tag variation",
            )

    def test_direct_instantiation_raises_when_detail_number_is_1a_even_if_tag_is_none(self):
        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            ClassifiedWallPolygon(
                wall_id="w_detail_adv",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag=None,
                detail_number="1A",
                material_description="CMU",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Detail number 1A without tag",
            )


# ==============================================================================
# 3. Probing Reflective Bypass Vectors (object.__setattr__, __dict__, Subclassing)
# ==============================================================================
class TestReflectiveBypassProbes:
    """
    Empirical probe of Python reflective bypass vectors.
    Evaluates whether internal circumventions are possible and whether the production
    pipeline is exposed to them.
    """

    def test_probe_object_setattr_reflection(self):
        poly = ClassifiedWallPolygon(
            wall_id="w_refl_01",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1A",
            detail_number="1A",
            material_description="CMU",
            classification="Non-Drywall",
            confidence=1.0,
            color_hex="#D50000",
            reason="Detail 1A safe",
        )
        # object.__setattr__ bypasses custom __setattr__ in Python
        object.__setattr__(poly, "classification", "Drywall")
        assert poly.classification == "Drywall"

    def test_probe_dict_manipulation(self):
        poly = ClassifiedWallPolygon(
            wall_id="w_refl_02",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1A",
            detail_number="1A",
            material_description="CMU",
            classification="Non-Drywall",
            confidence=1.0,
            color_hex="#D50000",
            reason="Detail 1A safe",
        )
        # Direct __dict__ write bypasses __setattr__ in Python
        poly.__dict__["classification"] = "Drywall"
        assert poly.classification == "Drywall"

    def test_subclass_cannot_bypass_post_init(self):
        """Even if a subclass overrides __setattr__, __post_init__ still blocks initialization as Drywall."""
        class SubclassedWall(ClassifiedWallPolygon):
            def __setattr__(self, name, value):
                object.__setattr__(self, name, value)

        with pytest.raises(IntegrityViolationError, match="Detail 1A is explicitly 6\" CMU masonry block"):
            SubclassedWall(
                wall_id="w_sub_01",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag="1A",
                detail_number="1A",
                material_description="CMU",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Subclass attack",
            )

    def test_production_pipeline_never_uses_subclasses_or_reflection(self, classifier):
        """Production DrywallClassifier instantiates ClassifiedWallPolygon directly with Non-Drywall."""
        wall = DummyCandidate("w_prod_01", box(100, 100, 200, 108.35))
        tag = DummyTag("1A", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        res = results[0]
        assert type(res) is ClassifiedWallPolygon
        assert res.classification == "Non-Drywall"
        assert res.color_hex == CLASS_COLORS_HEX["Non-Drywall"]
        # Normal mutation is blocked
        with pytest.raises(IntegrityViolationError):
            res.classification = "Drywall"


# ==============================================================================
# 4. Verification of Previous Vulnerabilities (VULN-M5-01 through VULN-M5-05)
# ==============================================================================
class TestPreviousVulnerabilitiesClosed:
    """Verifies that all 5 vulnerabilities reported in Iteration 1 are permanently closed."""

    def test_vuln_m5_01_unregistered_drywall_synonyms_permanently_closed(self):
        """VULN-M5-01: Detail 1A cannot be instantiated with unregistered synonyms."""
        for syn in ["gyp bd", "gyp board", "gypsum board", "dry wall", "gyp"]:
            with pytest.raises(IntegrityViolationError):
                ClassifiedWallPolygon(
                    wall_id=f"w_v1_{syn}",
                    page_idx=0,
                    sheet="A-101",
                    geometry_pdf=box(0, 0, 10, 10),
                    geometry_pixel=box(0, 0, 20, 20),
                    matched_tag="1A",
                    detail_number="1A",
                    material_description="CMU",
                    classification=syn,
                    confidence=1.0,
                    color_hex="#00C853",
                    reason="VULN-01 test",
                )

    def test_vuln_m5_02_post_init_mutation_permanently_closed(self):
        """VULN-M5-02: Mutating poly.classification = 'Drywall' is intercepted and blocked."""
        poly = ClassifiedWallPolygon(
            wall_id="w_v2",
            page_idx=0,
            sheet="A-101",
            geometry_pdf=box(0, 0, 10, 10),
            geometry_pixel=box(0, 0, 20, 20),
            matched_tag="1A",
            detail_number="1A",
            material_description="CMU",
            classification="Non-Drywall",
            confidence=1.0,
            color_hex="#D50000",
            reason="VULN-02 test",
        )
        with pytest.raises(IntegrityViolationError):
            poly.classification = "Drywall"

    def test_vuln_m5_03_whitespace_tag_falls_back_to_unassigned(self, classifier):
        """VULN-M5-03: Whitespace-only tag produces confidence=0.0 and matched_tag=None."""
        wall = DummyCandidate("w_v3", box(100, 100, 200, 108.35))
        tag = DummyTag("   ", box(140, 120, 151.2, 131.3), LineString([(145.6, 120), (145.6, 108.35)]))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        res = results[0]
        assert res.classification == "Uncertain"
        assert res.matched_tag is None
        assert res.confidence == 0.0

    def test_vuln_m5_04_none_tag_does_not_crash(self, classifier):
        """VULN-M5-04: None tag candidate does not raise AttributeError in spatial matcher or classifier."""
        wall = DummyCandidate("w_v4", box(100, 100, 200, 108.35))
        tag = DummyTag(None, box(140, 120, 151.2, 131.3))

        results = classifier.classify_walls([wall], [tag], page_idx=0, sheet="A-101")
        assert len(results) == 1
        assert results[0].classification == "Uncertain"
        assert results[0].confidence == 0.0

    def test_vuln_m5_05_takeoff_summary_accounting_consistent_with_empty_geometries(self):
        """VULN-M5-05: Takeoff fusion summary total_walls strictly equals sum of class counts."""
        from drywall_detection.pipeline.fusion import HybridFusionPipeline

        pipeline = HybridFusionPipeline()
        walls = [
            ClassifiedWallPolygon(
                wall_id="w_v5_dw",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=Polygon(),  # Empty geometry
                geometry_pixel=Polygon(),
                matched_tag="1B",
                detail_number="1B",
                material_description="GWB",
                classification="Drywall",
                confidence=1.0,
                color_hex="#00C853",
                reason="Normal",
            ),
            ClassifiedWallPolygon(
                wall_id="w_v5_ndw",
                page_idx=0,
                sheet="A-101",
                geometry_pdf=box(0, 0, 10, 10),
                geometry_pixel=box(0, 0, 20, 20),
                matched_tag="1A",
                detail_number="1A",
                material_description="CMU",
                classification="Non-Drywall",
                confidence=1.0,
                color_hex="#D50000",
                reason="CMU",
            ),
        ]
        summary = pipeline.compute_summary_statistics(walls)
        assert summary["total_walls"] == 2
        assert summary["drywall_count"] == 1
        assert summary["nondrywall_count"] == 1
        assert summary["uncertain_count"] == 0
        assert summary["total_walls"] == (summary["drywall_count"] + summary["nondrywall_count"] + summary["uncertain_count"])
