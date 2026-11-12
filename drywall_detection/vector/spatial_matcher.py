"""
drywall_detection/vector/spatial_matcher.py

3-Tier Spatial Matching Engine for Architectural Floor Plans (Milestone M3).
Associates discovered partition tags with extracted wall geometries using:
  Tier 1: Leader line direct intersection / raycast forward (highest confidence)
  Tier 2: Calibrated proximity buffer search (moderate confidence)
  Tier 3: Strict unassigned fallback guardrail (zero guesswork / zero hallucination)
Enforces Detail 1A Non-Drywall safety veto and human review lock protocol.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from drywall_detection.config import (
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    LEADER_LINE_MAX_GAP_PT,
    PROXIMITY_BUFFER_RADIUS_PT,
    PROXIMITY_BUFFER_EXPANDED_RADIUS_PT,
    TAG_1A_OVERRIDE_CLASS,
    TAG_1A_OVERRIDE_REASON,
    SCHEDULE_CSV_PATH,
    APPROVED_SCHEDULE_CSV_PATH,
    REVIEW_LOCKFILE_PATH,
)


class MatchMethod(str, Enum):
    LEADER_LINE = "leader_line"
    BUFFER_PROXIMITY = "buffer_proximity"
    UNASSIGNED = "unassigned"


@dataclass
class SpatialMatcherConfig:
    """Configuration thresholds and confidence scores for 3-tier matching."""
    leader_line_max_gap_pt: float = LEADER_LINE_MAX_GAP_PT  # 3.0 pt
    raycast_extension_pt: float = 12.0                      # Raycast forward projection
    primary_buffer_radius_pt: float = PROXIMITY_BUFFER_RADIUS_PT  # 25.0 pt
    expanded_buffer_radius_pt: float = PROXIMITY_BUFFER_EXPANDED_RADIUS_PT  # 50.0 pt
    min_distance_margin_pt: float = 8.0                    # Disambiguation distance delta
    tier1_confidence: float = 0.95
    tier1_raycast_confidence: float = 0.90
    tier2_direct_overlap_confidence: float = 0.85
    tier2_unique_buffer_confidence: float = 0.75
    tier2_expanded_buffer_confidence: float = 0.60
    tier3_unassigned_confidence: float = 0.00


@dataclass
class SpatialMatchResult:
    """Result of spatial association for an individual wall assembly."""
    wall_id: str
    geometry: BaseGeometry
    assigned_tag: Optional[str]
    match_method: MatchMethod
    confidence: float
    proposed_class: str
    color_hex: str
    distance_pt: float = 0.0
    matched_leader: Optional[LineString] = None
    tag_centroid: Optional[Tuple[float, float]] = None
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def matched_tag(self) -> Optional[str]:
        return self.assigned_tag

    @matched_tag.setter
    def matched_tag(self, val: Optional[str]) -> None:
        self.assigned_tag = val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wall_id": self.wall_id,
            "assigned_tag": self.assigned_tag,
            "match_method": self.match_method.value,
            "confidence": round(self.confidence, 4),
            "proposed_class": self.proposed_class,
            "color_hex": self.color_hex,
            "distance_pt": round(self.distance_pt, 2),
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass
class MatchingReport:
    """Aggregated statistics and results across all wall candidates on a sheet."""
    total_walls: int
    matched_walls: int
    unassigned_walls: int
    tier1_matches: int
    tier2_matches: int
    tier3_unassigned: int
    tag_counts: Dict[str, int]
    unmatched_tags: List[str]
    results: List[SpatialMatchResult]

    @property
    def match_rate(self) -> float:
        return self.matched_walls / self.total_walls if self.total_walls > 0 else 0.0

    @property
    def assignments(self) -> List[SpatialMatchResult]:
        return self.results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_walls": self.total_walls,
            "matched_walls": self.matched_walls,
            "unassigned_walls": self.unassigned_walls,
            "tier1_matches": self.tier1_matches,
            "tier2_matches": self.tier2_matches,
            "tier3_unassigned": self.tier3_unassigned,
            "match_rate": round(self.match_rate, 4),
            "tag_counts": self.tag_counts,
            "unmatched_tags": self.unmatched_tags,
            "results": [r.to_dict() for r in self.results],
        }


class SpatialMatcher:
    """
    Production 3-Tier Spatial Matcher for architectural drawings.
    Uses Shapely STRtree for spatial R-Tree acceleration.
    """

    def __init__(
        self,
        config: Optional[SpatialMatcherConfig] = None,
        schedule_mapping: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config = config or SpatialMatcherConfig()
        self.schedule_mapping = schedule_mapping or {}

    @staticmethod
    def _extract_tag_id(tag: Any) -> str:
        """Safely extracts tag string identifier from candidate tag object."""
        tag_val = getattr(tag, "tag_id", None)
        if tag_val is None:
            tag_val = getattr(tag, "tag_name", None)
        if tag_val is None:
            tag_val = getattr(tag, "tag", "")
        return str(tag_val or "")

    def _resolve_classification(self, tag_name: Any) -> Tuple[str, str]:
        """
        Resolves proposed class and color hex for a given tag.
        Enforces Detail 1A CMU safety veto unconditionally, raising an immediate
        fatal exception if a tampered schedule attempts to classify 1A as Drywall or GWB.
        """
        if not tag_name or not isinstance(tag_name, str) or not tag_name.strip():
            return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])
        clean_tag = tag_name.upper().strip()
        if clean_tag == "1A":
            detail = self.schedule_mapping.get("1A")
            if detail is not None:
                if hasattr(detail, "proposed_class"):
                    cls_raw = detail.proposed_class
                elif isinstance(detail, dict):
                    cls_raw = detail.get("proposed_class", "")
                else:
                    cls_raw = str(detail)
                cls_norm = (cls_raw or "").strip().lower()
                drywall_synonyms = {
                    "drywall", "gwb", "gypsum", "gypsum wallboard",
                    "gypsum wall board", "sheetrock", "1",
                }
                if cls_norm in drywall_synonyms or (cls_norm and cls_norm != "non-drywall" and cls_norm != "2"):
                    raise ValueError(
                        "INTEGRITY VIOLATION: Detail 1A cannot be classified as Drywall or GWB in SpatialMatcher!"
                    )
            return ("Non-Drywall", CLASS_COLORS_HEX["Non-Drywall"])

        detail = self.schedule_mapping.get(clean_tag)
        if detail is not None:
            if hasattr(detail, "proposed_class"):
                prop_class = detail.proposed_class
            elif isinstance(detail, dict):
                prop_class = detail.get("proposed_class", "Uncertain")
            else:
                prop_class = "Uncertain"
            return (prop_class, CLASS_COLORS_HEX.get(prop_class, CLASS_COLORS_HEX["Uncertain"]))

        return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])

    def match(
        self,
        walls: List[Any],
        tags: List[Any],
    ) -> MatchingReport:
        """
        Associates wall candidates with partition tags using 3-tier spatial matching.
        """
        if not walls:
            unmatched = [self._extract_tag_id(t) for t in tags]
            return MatchingReport(
                total_walls=0,
                matched_walls=0,
                unassigned_walls=0,
                tier1_matches=0,
                tier2_matches=0,
                tier3_unassigned=0,
                tag_counts={},
                unmatched_tags=unmatched,
                results=[],
            )

        # Build spatial index over candidate wall geometries
        wall_geoms: List[BaseGeometry] = []
        wall_map: Dict[int, Any] = {}
        for w in walls:
            geom = getattr(w, "geometry", getattr(w, "geometry_pdf", None))
            if geom is not None and not geom.is_empty:
                wall_geoms.append(geom)
                wall_map[id(geom)] = w

        if not wall_geoms:
            unmatched = [self._extract_tag_id(t) for t in tags]
            return MatchingReport(
                total_walls=len(walls),
                matched_walls=0,
                unassigned_walls=len(walls),
                tier1_matches=0,
                tier2_matches=0,
                tier3_unassigned=len(walls),
                tag_counts={},
                unmatched_tags=unmatched,
                results=[],
            )

        str_tree = STRtree(wall_geoms)

        assigned_wall_ids: Set[str] = set()
        wall_results: Dict[str, SpatialMatchResult] = {}
        matched_tags: Set[str] = set()
        tag_usage: Dict[str, int] = {}

        # ----------------------------------------------------------------------
        # TIER 1: Leader Line Raycast / Intersection
        # ----------------------------------------------------------------------
        tier1_count = 0
        for tag in tags:
            tag_name = self._extract_tag_id(tag)
            leader_lines = getattr(tag, "leader_lines", [])
            if not leader_lines:
                single_leader = getattr(tag, "leader_line", None)
                if single_leader is not None:
                    if isinstance(single_leader, LineString):
                        leader_lines = [single_leader]
                    elif isinstance(single_leader, (list, tuple)) and len(single_leader) == 2:
                        leader_lines = [LineString([single_leader[0], single_leader[1]])]

            for leader in leader_lines:
                if leader is None or leader.is_empty:
                    continue

                # Query R-Tree for candidate walls intersecting leader line
                candidate_indices = str_tree.query(leader, predicate="intersects")
                hits = [
                    wall_map[id(wall_geoms[idx])]
                    for idx in candidate_indices
                    if id(wall_geoms[idx]) in wall_map
                ]

                # Raycast extension if no direct intersection
                is_raycast = False
                matched_leader_geom = leader
                if not hits and len(leader.coords) >= 2:
                    p1 = np.array(leader.coords[-2])
                    p2 = np.array(leader.coords[-1])
                    vec = p2 - p1
                    norm = np.linalg.norm(vec)
                    if norm > 1e-4:
                        dir_unit = vec / norm
                        p_ext = p2 + dir_unit * self.config.raycast_extension_pt
                        extended_line = LineString([leader.coords[-1], tuple(p_ext)])
                        ext_indices = str_tree.query(extended_line, predicate="intersects")
                        hits = [
                            wall_map[id(wall_geoms[idx])]
                            for idx in ext_indices
                            if id(wall_geoms[idx]) in wall_map
                        ]
                        if hits:
                            is_raycast = True
                            matched_leader_geom = LineString(list(leader.coords) + [tuple(p_ext)])

                if hits:
                    end_pt = Point(leader.coords[-1])
                    # Sort by distance to leader endpoint
                    hits.sort(
                        key=lambda w: getattr(w, "geometry", getattr(w, "geometry_pdf", end_pt)).distance(end_pt)
                    )
                    chosen_wall = None
                    for candidate_w in hits:
                        if candidate_w.wall_id not in assigned_wall_ids:
                            chosen_wall = candidate_w
                            break

                    if chosen_wall is not None:
                        conf = (
                            self.config.tier1_raycast_confidence
                            if is_raycast
                            else self.config.tier1_confidence
                        )
                        prop_class, col_hex = self._resolve_classification(tag_name)
                        evid = (
                            f"Tier 1: Leader line raycast (+{self.config.raycast_extension_pt:.1f}pt) hit"
                            if is_raycast
                            else f"Tier 1: Leader line direct intersection (len={leader.length:.1f}pt)"
                        )

                        wall_geom = getattr(chosen_wall, "geometry", getattr(chosen_wall, "geometry_pdf"))
                        centroid_val = getattr(tag, "centroid", getattr(tag, "center", None))

                        wall_results[chosen_wall.wall_id] = SpatialMatchResult(
                            wall_id=chosen_wall.wall_id,
                            geometry=wall_geom,
                            assigned_tag=tag_name,
                            match_method=MatchMethod.LEADER_LINE,
                            confidence=conf,
                            proposed_class=prop_class,
                            color_hex=col_hex,
                            distance_pt=0.0,
                            matched_leader=matched_leader_geom,
                            tag_centroid=centroid_val,
                            evidence=evid,
                        )
                        assigned_wall_ids.add(chosen_wall.wall_id)
                        matched_tags.add(tag_name)
                        tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
                        tier1_count += 1
                        break

        # ----------------------------------------------------------------------
        # TIER 2: Calibrated Proximity Buffer Search
        # ----------------------------------------------------------------------
        tier2_count = 0
        unmatched_tag_instances = [
            t for t in tags
            if self._extract_tag_id(t) not in matched_tags
        ]

        for tag in unmatched_tag_instances:
            tag_name = self._extract_tag_id(tag)
            tag_box = getattr(tag, "box_geom", None)
            if tag_box is None:
                bbox_val = getattr(tag, "box_bbox", getattr(tag, "bbox", None))
                if bbox_val is not None:
                    tag_box = box(*bbox_val)
            if tag_box is None:
                continue

            # Primary buffer query (25 pt)
            buf25 = tag_box.buffer(self.config.primary_buffer_radius_pt)
            cand_indices = str_tree.query(buf25, predicate="intersects")
            cand_walls = [
                wall_map[id(wall_geoms[idx])]
                for idx in cand_indices
                if id(wall_geoms[idx]) in wall_map
                and wall_map[id(wall_geoms[idx])].wall_id not in assigned_wall_ids
            ]

            chosen_wall = None
            conf = 0.0
            dist_val = 0.0
            evid = ""

            # Check direct geometric overlap
            overlap_walls = [
                w for w in cand_walls
                if tag_box.intersects(getattr(w, "geometry", getattr(w, "geometry_pdf")))
            ]
            if overlap_walls:
                chosen_wall = overlap_walls[0]
                conf = self.config.tier2_direct_overlap_confidence
                dist_val = 0.0
                evid = "Tier 2: Tag symbol box directly touches / overlaps wall geometry"

            elif len(cand_walls) == 1:
                chosen_wall = cand_walls[0]
                dist_val = tag_box.distance(getattr(chosen_wall, "geometry", getattr(chosen_wall, "geometry_pdf")))
                conf = self.config.tier2_unique_buffer_confidence
                evid = f"Tier 2: Unique wall candidate within 25pt buffer (dist={dist_val:.1f}pt)"

            elif len(cand_walls) > 1:
                # Disambiguate by distance delta
                distances = [
                    (w, tag_box.distance(getattr(w, "geometry", getattr(w, "geometry_pdf"))))
                    for w in cand_walls
                ]
                distances.sort(key=lambda item: item[1])
                closest_w, d1 = distances[0]
                runner_up_w, d2 = distances[1]
                if (d2 - d1) >= self.config.min_distance_margin_pt:
                    chosen_wall = closest_w
                    dist_val = d1
                    conf = self.config.tier2_unique_buffer_confidence * 0.90
                    evid = (
                        f"Tier 2: Closest wall within 25pt (d1={d1:.1f}pt, d2={d2:.1f}pt, delta={d2-d1:.1f}pt)"
                    )
                else:
                    # Ambiguous proximity; do not guess
                    continue

            else:
                # Test expanded buffer (50 pt)
                buf50 = tag_box.buffer(self.config.expanded_buffer_radius_pt)
                exp_indices = str_tree.query(buf50, predicate="intersects")
                exp_walls = [
                    wall_map[id(wall_geoms[idx])]
                    for idx in exp_indices
                    if id(wall_geoms[idx]) in wall_map
                    and wall_map[id(wall_geoms[idx])].wall_id not in assigned_wall_ids
                ]
                if len(exp_walls) == 1:
                    chosen_wall = exp_walls[0]
                    dist_val = tag_box.distance(getattr(chosen_wall, "geometry", getattr(chosen_wall, "geometry_pdf")))
                    conf = self.config.tier2_expanded_buffer_confidence
                    evid = f"Tier 2: Unique wall candidate within expanded 50pt buffer (dist={dist_val:.1f}pt)"

            if chosen_wall is not None:
                prop_class, col_hex = self._resolve_classification(tag_name)
                wall_geom = getattr(chosen_wall, "geometry", getattr(chosen_wall, "geometry_pdf"))
                centroid_val = getattr(tag, "centroid", getattr(tag, "center", None))

                wall_results[chosen_wall.wall_id] = SpatialMatchResult(
                    wall_id=chosen_wall.wall_id,
                    geometry=wall_geom,
                    assigned_tag=tag_name,
                    match_method=MatchMethod.BUFFER_PROXIMITY,
                    confidence=conf,
                    proposed_class=prop_class,
                    color_hex=col_hex,
                    distance_pt=dist_val,
                    matched_leader=None,
                    tag_centroid=centroid_val,
                    evidence=evid,
                )
                assigned_wall_ids.add(chosen_wall.wall_id)
                matched_tags.add(tag_name)
                tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
                tier2_count += 1

        # ----------------------------------------------------------------------
        # TIER 3: Strict Unassigned Fallback Guardrail (Zero Hallucination)
        # ----------------------------------------------------------------------
        tier3_count = 0
        for wall in walls:
            if wall.wall_id not in assigned_wall_ids:
                wall_geom = getattr(wall, "geometry", getattr(wall, "geometry_pdf", None))
                wall_results[wall.wall_id] = SpatialMatchResult(
                    wall_id=wall.wall_id,
                    geometry=wall_geom,
                    assigned_tag=None,
                    match_method=MatchMethod.UNASSIGNED,
                    confidence=self.config.tier3_unassigned_confidence,
                    proposed_class="Uncertain",
                    color_hex=CLASS_COLORS_HEX["Uncertain"],
                    distance_pt=float("inf"),
                    matched_leader=None,
                    tag_centroid=None,
                    evidence="Tier 3: No conclusive spatial tag evidence; unassigned guardrail enforced",
                )
                tier3_count += 1

        ordered_results = [wall_results[w.wall_id] for w in walls]
        unmatched_list = [
            self._extract_tag_id(t)
            for t in tags
            if self._extract_tag_id(t) not in matched_tags
        ]

        return MatchingReport(
            total_walls=len(walls),
            matched_walls=tier1_count + tier2_count,
            unassigned_walls=tier3_count,
            tier1_matches=tier1_count,
            tier2_matches=tier2_count,
            tier3_unassigned=tier3_count,
            tag_counts=tag_usage,
            unmatched_tags=unmatched_list,
            results=ordered_results,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SpatialMatcher: 3-tier spatial tag-to-wall matcher."
    )
    parser.add_argument("--match", action="store_true", help="Run spatial matching demo on A-101")
    parser.add_argument("--pdf", type=str, default="", help="Path to input architectural PDF")
    parser.add_argument("--export-csv", type=str, default="", help="Export match results CSV")
    parser.add_argument("--check-lock", action="store_true", help="Check review lockfile")

    args = parser.parse_args()

    if args.check_lock:
        if REVIEW_LOCKFILE_PATH.exists():
            print(f"LOCKED: {REVIEW_LOCKFILE_PATH} is present. Awaiting human review (code 2).")
            return 2
        else:
            print("UNLOCKED: No lockfile found.")
            return 0

    print("SpatialMatcher CLI initialized.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
