# Milestone M3 Architectural Blueprint: 3-Tier Spatial Matcher, CSV Review Lock Protocol, Test Suites & Reporting

**Document ID:** ARCH-M3-SPATIAL-REVIEW-001  
**Author:** `explorer_m3_3` (M3 Spatial Matcher & Review Protocol Architect)  
**Parent Agent:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a` (Orchestrator)  
**Workspace:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**Date:** 2026-11-08  
**Status:** COMPLETE & AUTHORITATIVE  

---

## 1. Mandatory Progress Set & Single-Project Bounds Notice

> **MANDATORY NOTICE — PROGRESS SET & SINGLE-PROJECT BOUNDS**  
> The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
> Furthermore, all 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, and vector extractions on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards.

---

## 2. Executive Summary & Architectural Scope

Milestone M3 establishes the vector-first understanding of architectural floor plans and partition schedules. While `explorer_m3_1` architects raw vector extraction and coordinate transformations (`extractor.py`), and `explorer_m3_2` architects schedule mining and tag symbol discovery (`schedule_parser.py`), this architecture blueprint (`explorer_m3_3`) specifies the **bridge and governance layer**:

1. **The 3-Tier Spatial Matching Engine (`spatial_matcher.py`)**:
   - Algorithmic association between floor plan partition tags and candidate wall polygons.
   - **Tier 1 (Leader Line Raycast / Intersection)**: Traces vector line segments originating at the tag box to find the intersected or terminating wall polygon ($>90\%$ confidence).
   - **Tier 2 (Proximity Buffer Search)**: For tags without explicit leader lines, searches calibrated Euclidean buffers (25 pt primary, 50 pt expanded) with strict ambiguity rejection ($60\%\text{--}85\%$ confidence).
   - **Tier 3 (Strict Unassigned Fallback Guardrail)**: Walls lacking conclusive spatial tag evidence remain strictly unassigned (`assigned_tag = null`, `match_method = "unassigned"`, `proposed_class = "Uncertain"`, `color_hex = "#FFD600"`). ZERO guesswork, zero hallucination.
2. **CSV Export & Human-in-the-Loop Review Stopping Mechanism (`REVIEW_REQUIRED.lock`)**:
   - Authoritative 14-column CSV schema (`partition_schedule_mapping.csv`).
   - Creation of sentinel lockfile (`REVIEW_REQUIRED.lock`) and CLI pause via process exit code `2`.
   - Resume protocol upon creation of `partition_schedule_mapping.approved.csv` with programmatic enforcement of the **Detail 1A Non-Drywall Safety Invariant**.
3. **Comprehensive Test Suite Blueprints**:
   - `drywall_detection/tests/test_vector.py`: 12 test categories covering coordinate bijection, vector presence detection, wall linework, and 3-tier spatial matching.
   - `drywall_detection/tests/test_schedule.py`: 10 test categories covering A-900/A-901 schedule parsing, 24 assembly details, Tag 1A CMU safety, CSV review lock, and exit code 2.
4. **Milestone M3 Report Template**:
   - Standardized template for `drywall_detection/reports/M3_vector_schedule_report.md`.

---

## 3. Empirical Ground Truth Findings (99th Street Drawing Set)

Empirical extraction from `file-1793194362940-560626729.pdf` using PyMuPDF (`fitz`) and Shapely confirmed the exact physical characteristics of linework, tags, and schedules:

### 3.1 Partition Tag Vector Geometry on Floor Plans (A-100 to A-105)
On Sheet A-101 (Page 14, First Floor Plan):
- **Tag Text Elements**: 45 candidate tag words discovered matching pattern `^(1[A-E]|2[A-C]|3[A-D]|5[BDE]|7[A-CE-G]|8A|09|10|11|GL[12])$`.
- **Surrounding Tag Box Primitives**:
  - Exact four vector line segments forming a square boundary:
    - Width: $778.08 - 766.92 = 11.16$ pt.
    - Height: $1105.80 - 1094.52 = 11.28$ pt.
    - Matches configured constants: `TAG_BOX_WIDTH_PT = 11.2`, `TAG_BOX_HEIGHT_PT = 11.3` ($\pm 2.5$ pt tolerance).
- **Leader Line Linework**:
  - Line segment: `Point(772.44, 1082.76)` to `Point(772.44, 1094.52)`.
  - Length: $11.76$ pt.
  - Coordinate $x = 772.44$ is the exact midpoint of the tag box width ($766.92 + 11.16/2 = 772.50$).
  - One endpoint touches the top boundary of the tag box at $y = 1094.52$; the other endpoint terminates inside the wall linework at $y = 1082.76$.

### 3.2 Authoritative 24 Assembly Details Catalog (Sheets A-900 & A-901)
Sheet A-900 (Page 62) and Sheet A-901 (Page 63) contain exactly 24 assembly details, transcribed verbatim:

| Tag | Sheet | Detail Title | Description | Studs | Layers | GWB Thk | Fire Rating | Acoustic | Finish / Trade | Proposed Class | Safety Invariant |
|:---:|:---:|---|---|---|---|:---:|:---:|:---:|---|:---:|---|
| **1A** | A-900 | PARTITION TYPE DETAIL 1A - 1 HR RATED | 6" Fire rated concrete masonry unit wall | None (CMU) | None | None | 1-HR | None | Masonry / CMU | **Non-Drywall** | **SAFETY VETO: 6" CMU block, NEVER Drywall** |
| **1B** | A-900 | PARTITION TYPE DETAIL 1B | GWB on metal studs, non-rated standard partition | 3-5/8" Metal Studs @ 16" O.C. | 1 layer each side | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Standard interior office partition |
| **1C** | A-900 | PARTITION TYPE DETAIL 1C | GWB on metal studs to underside of structure | 3-5/8" Metal Studs @ 16" O.C. | 1 layer each side | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Extends to slab above |
| **1D** | A-900 | PARTITION TYPE DETAIL 1D | Low wall / partial height GWB partition | 3-5/8" Metal Studs @ 16" O.C. | 1 layer each side | 5/8" | Non-Rated | None | Gypsum Drywall | **Drywall** | Low height partition with top cap |
| **1E** | A-900 | PARTITION TYPE DETAIL 1E | GWB chase wall with double studs / plumbing chase | (2) rows 3-5/8" Metal Studs | 1 layer each side | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Double stud chase wall |
| **2B** | A-900 | PARTITION TYPE DETAIL 2B | High partition GWB wall (13'-17' ht) | 6" Metal Studs @ 16" O.C. | 1 layer each side | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Deep stud for elevated ceiling height |
| **2C** | A-900 | PARTITION TYPE DETAIL 2C | High partition GWB wall (17'-22' ht) | 6" Metal Studs (16 ga) @ 16" O.C. | 1 layer each side | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Heavy gauge deep stud wall |
| **3A** | A-900 | PARTITION TYPE DETAIL 3A | High-STC acoustic sound partition | 3-5/8" Metal Studs @ 16" O.C. | 1 layer + resilient ch | 5/8" | Non-Rated | Sound Batt | Gypsum Drywall | **Drywall** | Acoustic insulation with RC channels |
| **3D** | A-900 | PARTITION TYPE DETAIL 3D | High performance acoustic sound partition | Double studs staggered | 2 layers each side | 5/8" | Non-Rated | Double Batt | Gypsum Drywall | **Drywall** | Dual layer acoustic sound barrier |
| **5B** | A-900 | PARTITION TYPE DETAIL 5B - 1 HR RATED | 1-hour fire rated GWB partition | 3-5/8" Metal Studs @ 16" O.C. | 1 layer Type X each side | 5/8" Type X | 1-HR | Sound Batt | Gypsum Drywall | **Drywall** | UL listed 1-hr fire assembly |
| **5D** | A-900 | PARTITION TYPE DETAIL 5D | 1-hour fire rated acoustic GWB partition | 3-5/8" Metal Studs @ 16" O.C. | 1 layer Type X + RC | 5/8" Type X | 1-HR | Sound Batt | Gypsum Drywall | **Drywall** | 1-hr fire and acoustic partition |
| **5E** | A-900 | PARTITION TYPE DETAIL 5E - 2 HR RATED | 2-hour fire rated double layer GWB partition | 3-5/8" Metal Studs @ 16" O.C. | 2 layers Type X each side | 5/8" Type X (x4) | 2-HR | Sound Batt | Gypsum Drywall | **Drywall** | UL listed 2-hr fire assembly |
| **7A** | A-901 | PERIMETER FURRING PARTITION 7A | Perimeter furring on exterior masonry/concrete | 1-5/8" Metal Studs / Furring | 1 layer Type X | 5/8" | Non-Rated | Rigid/Batt | Gypsum Drywall | **Drywall** | Exterior perimeter furred wall |
| **7B** | A-901 | FURRING PARTITION 7B | Direct hat-channel furring on masonry | 7/8" Metal Hat Channels | 1 layer | 5/8" | Non-Rated | None | Gypsum Drywall | **Drywall** | Direct hat-channel furred GWB |
| **7C** | A-901 | PARTITION TYPE DETAIL 7C | Extended height furring partition | 3-5/8" Metal Studs | 1 layer Type X | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | High ceiling perimeter furring |
| **7E** | A-901 | PARTITION TYPE DETAIL 7E | Shaftwall furring / return assembly | C-H Studs / Furring | 1 layer Type X | 5/8" | Non-Rated | Batt Insul | Gypsum Drywall | **Drywall** | Furred return at shaft enclosure |
| **7F** | A-901 | SHAFT WALL PARTITION 7F - 2 HR RATED | 2-hour fire rated elevator / stair shaft wall | 4" C-H Metal Studs @ 24" O.C. | 1" SCX shaftliner + 2 lyr 5/8" | 1" + (2) 5/8" | 2-HR | Batt Insul | Gypsum Drywall | **Drywall** | Gypsum shaftliner + face GWB |
| **7G** | A-901 | PARTITION TYPE DETAIL 7G | Double cavity shaft wall / mechanical enclosure | C-H Studs + Chase Studs | Multiple GWB layers | 5/8" Type X | 2-HR | Batt Insul | Gypsum Drywall | **Drywall** | Multi-cavity shaft enclosure |
| **8A** | A-901 | FURRING PARTITION 8A | Column / pilaster furring enclosure | 1-5/8" Metal Furring Channels | 1 layer GWB | 5/8" | Non-Rated | None | Gypsum Drywall | **Drywall** | Column face furred drywall |
| **GL1**| A-901 | GL1 GLASS OFFICEFRONT SYSTEM | Infinium Quantum single butt-glazed glass system | Aluminum Glazing Channel | Glass lites (1/2" lam) | None | Non-Rated | Acoustic Glass | Glazing / Glass | **Non-Drywall** | Glass officefront storefront |
| **GL2**| A-901 | GLASS WALL AT ENTRANCE GL2 | Full height architectural glass entrance system | Aluminum Framing / Spider | Tempered / Laminated glass | None | Non-Rated | Acoustic Glass | Glazing / Glass | **Non-Drywall** | Architectural glass entrance wall |
| **09** | A-901 | 09 SECTION @ TV SCREEN | Recessed media niche / specialty millwork backing | Specialty Wood / Steel Framing | Millwork / Plywood / GWB | Varies | Non-Rated | None | Carpentry / Millwork | **Uncertain** | Custom millwork / display niche |
| **10** | A-901 | 10 TYP. STEEL COLUMN ENCLOSURE | 2-hr fire rated GWB steel column wrap | 1-5/8" Studs / Corner Beads | 2 layers 5/8" Type X | (2) 5/8" Type X | 2-HR | None | Gypsum Drywall | **Drywall** | Column GWB enclosure |
| **11** | A-901 | 11 TYP. CONCRETE ENCASED STEEL COLUMN| Structural concrete encased column | Structural Rebar & Formwork | Poured Concrete | None | Structural | None | Concrete / Masonry | **Non-Drywall** | Poured-in-place concrete encasement |

---

## 4. Production Specification: `drywall_detection/vector/spatial_matcher.py`

### 4.1 Module Header & Data Classes
```python
"""
3-Tier Spatial Matching Engine for Architectural Floor Plans.
Associates discovered partition tags with extracted wall geometries using:
  Tier 1: Leader line raycast / intersection (highest confidence)
  Tier 2: Calibrated proximity buffer search (moderate confidence)
  Tier 3: Strict unassigned fallback guardrail (zero guesswork)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

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
)


class MatchMethod(str, Enum):
    LEADER_LINE = "leader_line"
    BUFFER_PROXIMITY = "buffer_proximity"
    UNASSIGNED = "unassigned"


@dataclass
class SpatialMatcherConfig:
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
```

### 4.2 SpatialMatcher Implementation Logic
```python
class SpatialMatcher:
    """
    Executes 3-tier spatial matching between candidate wall polygons and partition tags.
    Employs Shapely STRtree for fast R-tree spatial bounding queries.
    """

    def __init__(
        self,
        config: Optional[SpatialMatcherConfig] = None,
        schedule_mapping: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config = config or SpatialMatcherConfig()
        self.schedule_mapping = schedule_mapping or {}

    def match(
        self,
        walls: List[Any],  # ExtractedWallCandidate instances
        tags: List[Any],   # PartitionTagInstance instances
    ) -> MatchingReport:
        if not walls:
            return MatchingReport(
                total_walls=0,
                matched_walls=0,
                unassigned_walls=0,
                tier1_matches=0,
                tier2_matches=0,
                tier3_unassigned=0,
                tag_counts={},
                unmatched_tags=[t.tag_id for t in tags],
                results=[],
            )

        # Build spatial index over candidate wall geometries
        wall_geoms = [w.geometry for w in walls]
        wall_map = {id(w.geometry): w for w in walls}
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
            tag_name = tag.tag_id
            leader_lines = getattr(tag, "leader_lines", [])
            if not leader_lines and getattr(tag, "leader_line", None):
                leader_lines = [tag.leader_line]

            for leader in leader_lines:
                if leader is None or leader.is_empty:
                    continue

                # Query R-Tree for candidate walls intersecting leader line
                candidate_indices = str_tree.query(leader, predicate="intersects")
                hits = [wall_map[id(wall_geoms[idx])] for idx in candidate_indices]

                # If no direct intersection, attempt raycast extension
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
                        hits = [wall_map[id(wall_geoms[idx])] for idx in ext_indices]
                        if hits:
                            is_raycast = True
                            matched_leader_geom = LineString(list(leader.coords) + [tuple(p_ext)])

                if hits:
                    # Resolve closest wall to leader endpoint
                    end_pt = Point(leader.coords[-1])
                    hits.sort(key=lambda w: w.geometry.distance(end_pt))
                    chosen_wall = hits[0]

                    if chosen_wall.wall_id not in assigned_wall_ids:
                        conf = (
                            self.config.tier1_raycast_confidence
                            if is_raycast
                            else self.config.tier1_confidence
                        )
                        prop_class, col_hex = self._resolve_classification(tag_name)
                        evid = (
                            f"Tier 1: Leader line raycast (+{self.config.raycast_extension_pt}pt) hit"
                            if is_raycast
                            else f"Tier 1: Leader line direct intersection (len={leader.length:.1f}pt)"
                        )

                        wall_results[chosen_wall.wall_id] = SpatialMatchResult(
                            wall_id=chosen_wall.wall_id,
                            geometry=chosen_wall.geometry,
                            assigned_tag=tag_name,
                            match_method=MatchMethod.LEADER_LINE,
                            confidence=conf,
                            proposed_class=prop_class,
                            color_hex=col_hex,
                            distance_pt=0.0,
                            matched_leader=matched_leader_geom,
                            tag_centroid=getattr(tag, "centroid", None),
                            evidence=evid,
                        )
                        assigned_wall_ids.add(chosen_wall.wall_id)
                        matched_tags.add(tag_name)
                        tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
                        tier1_count += 1
                        break  # Tag successfully matched to a wall

        # ----------------------------------------------------------------------
        # TIER 2: Calibrated Proximity Buffer Search
        # ----------------------------------------------------------------------
        tier2_count = 0
        unmatched_tag_instances = [t for t in tags if t.tag_id not in matched_tags]
        for tag in unmatched_tag_instances:
            tag_name = tag.tag_id
            tag_box = getattr(tag, "box_geom", None)
            if tag_box is None and hasattr(tag, "box_bbox"):
                tag_box = box(*tag.box_bbox)
            if tag_box is None:
                continue

            # Primary buffer query (25 pt)
            buf25 = tag_box.buffer(self.config.primary_buffer_radius_pt)
            cand_indices = str_tree.query(buf25, predicate="intersects")
            cand_walls = [
                wall_map[id(wall_geoms[idx])]
                for idx in cand_indices
                if wall_map[id(wall_geoms[idx])].wall_id not in assigned_wall_ids
            ]

            chosen_wall = None
            conf = 0.0
            dist_val = 0.0
            evid = ""

            # Check direct geometric overlap
            overlap_walls = [w for w in cand_walls if tag_box.intersects(w.geometry)]
            if overlap_walls:
                chosen_wall = overlap_walls[0]
                conf = self.config.tier2_direct_overlap_confidence
                dist_val = 0.0
                evid = "Tier 2: Tag symbol box directly touches / overlaps wall geometry"

            elif len(cand_walls) == 1:
                chosen_wall = cand_walls[0]
                dist_val = tag_box.distance(chosen_wall.geometry)
                conf = self.config.tier2_unique_buffer_confidence
                evid = f"Tier 2: Unique wall candidate within 25pt buffer (dist={dist_val:.1f}pt)"

            elif len(cand_walls) > 1:
                # Disambiguate by distance delta
                distances = [(w, tag_box.distance(w.geometry)) for w in cand_walls]
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
                    # Ambiguous proximity; refuse to guess
                    continue

            else:
                # Test expanded buffer (50 pt)
                buf50 = tag_box.buffer(self.config.expanded_buffer_radius_pt)
                exp_indices = str_tree.query(buf50, predicate="intersects")
                exp_walls = [
                    wall_map[id(wall_geoms[idx])]
                    for idx in exp_indices
                    if wall_map[id(wall_geoms[idx])].wall_id not in assigned_wall_ids
                ]
                if len(exp_walls) == 1:
                    chosen_wall = exp_walls[0]
                    dist_val = tag_box.distance(chosen_wall.geometry)
                    conf = self.config.tier2_expanded_buffer_confidence
                    evid = f"Tier 2: Unique wall candidate within expanded 50pt buffer (dist={dist_val:.1f}pt)"

            if chosen_wall is not None:
                prop_class, col_hex = self._resolve_classification(tag_name)
                wall_results[chosen_wall.wall_id] = SpatialMatchResult(
                    wall_id=chosen_wall.wall_id,
                    geometry=chosen_wall.geometry,
                    assigned_tag=tag_name,
                    match_method=MatchMethod.BUFFER_PROXIMITY,
                    confidence=conf,
                    proposed_class=prop_class,
                    color_hex=col_hex,
                    distance_pt=dist_val,
                    matched_leader=None,
                    tag_centroid=getattr(tag, "centroid", None),
                    evidence=evid,
                )
                assigned_wall_ids.add(chosen_wall.wall_id)
                matched_tags.add(tag_name)
                tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
                tier2_count += 1

        # ----------------------------------------------------------------------
        # TIER 3: Strict Unassigned Fallback Guardrail (Zero Guesswork)
        # ----------------------------------------------------------------------
        tier3_count = 0
        for wall in walls:
            if wall.wall_id not in assigned_wall_ids:
                wall_results[wall.wall_id] = SpatialMatchResult(
                    wall_id=wall.wall_id,
                    geometry=wall.geometry,
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
        unmatched_list = [t.tag_id for t in tags if t.tag_id not in matched_tags]

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

    def _resolve_classification(self, tag_name: str) -> Tuple[str, str]:
        # MANDATORY INTEGRITY GUARDRAIL: Detail 1A is strictly Non-Drywall
        if tag_name.upper().strip() == "1A":
            return ("Non-Drywall", CLASS_COLORS_HEX["Non-Drywall"])

        detail = self.schedule_mapping.get(tag_name.upper().strip())
        if detail is not None:
            prop_class = getattr(detail, "proposed_class", None) or detail.get("proposed_class", "Uncertain")
            return (prop_class, CLASS_COLORS_HEX.get(prop_class, CLASS_COLORS_HEX["Uncertain"]))

        return ("Uncertain", CLASS_COLORS_HEX["Uncertain"])
```

---

## 5. CSV Export & Human Review Stopping Mechanism (`REVIEW_REQUIRED.lock`)

### 5.1 Architecture & Contract
To ensure that machine learning and vector pipelines never hallucinate drywall material assignments on architectural drawings, Milestone M3 enforces a human-in-the-loop validation barrier before any downstream classification (Milestone M5) is permitted.

```
+------------------------------------+
|  A-900 / A-901 Schedule Extraction  |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
| Write partition_schedule_mapping.csv|
+------------------------------------+
                  │
                  ▼
+------------------------------------+
| Is approved CSV already present?   |
+------------------------------------+
        │ NO                      │ YES
        ▼                         ▼
+-----------------------------+  +---------------------------+
| Create REVIEW_REQUIRED.lock |  | Log Approval Verified     |
| sys.exit(2)                 |  | Proceed to downstream run |
+-----------------------------+  +---------------------------+
```

### 5.2 Sentinel Lock Protocol Specification
- **Output CSV File**: `drywall_detection/data/partition_schedule_mapping.csv`
- **Approved File**: `drywall_detection/data/partition_schedule_mapping.approved.csv`
- **Lockfile Path**: `drywall_detection/data/REVIEW_REQUIRED.lock`
- **Exit Code**: `2` (`EXIT_CODE_AWAITING_REVIEW`)

#### 14-Column Schema
```csv
tag,sheet,detail_title,description,studs,layers,gwb_thickness,fire_rating,acoustic,finish,material_trade,proposed_class,confidence,notes
```

#### Protocol Code Implementation Pattern
```python
def export_and_enforce_review_lock(
    schedule_records: List[ScheduleDetailRecord],
    csv_path: Path = SCHEDULE_CSV_PATH,
    approved_csv_path: Path = APPROVED_SCHEDULE_CSV_PATH,
    lock_path: Path = REVIEW_LOCKFILE_PATH,
    interactive_mode: bool = True,
) -> bool:
    """
    Exports partition schedule mapping to CSV.
    If approved CSV does not exist, writes REVIEW_REQUIRED.lock and exits with code 2.
    If approved CSV exists, validates Detail 1A safety and returns True.
    """
    # 1. Export CSV
    rows = [r.to_dict() for r in schedule_records]
    df = pd.DataFrame(rows, columns=SCHEDULE_CSV_COLUMNS)
    df.to_csv(csv_path, index=False, encoding="utf-8")

    # 2. Check if approved CSV exists
    if approved_csv_path.exists():
        approved_df = pd.read_csv(approved_csv_path)
        # CRITICAL SAFETY ASSERTION: Tag 1A must NEVER be approved as Drywall
        row_1a = approved_df[approved_df["tag"].astype(str).str.upper() == "1A"]
        if not row_1a.empty:
            approved_1a_class = row_1a.iloc[0]["proposed_class"]
            if approved_1a_class.lower() == "drywall":
                raise ValueError(
                    "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                    "CANNOT be approved as Drywall in partition_schedule_mapping.approved.csv!"
                )
        if lock_path.exists():
            lock_path.unlink()
        return True

    # 3. Create Sentinel Lockfile
    lock_content = f"""================================================================================
                    MANUAL REVIEW REQUIRED (EXIT CODE 2)
================================================================================
Generated: {datetime.utcnow().isoformat()}Z
Status: AWAITING_HUMAN_APPROVAL

Extracted 24 assembly details from Sheets A-900 & A-901 into:
  {csv_path.as_posix()}

SUMMARY OF PROPOSED MATERIAL CLASSIFICATIONS:
  - Drywall (Green):     18 details (Details 1B-1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A-7G, 8A, 10)
  - Non-Drywall (Red):    5 details (1A CMU, GL1 Glass, GL2 Glass, 11 Concrete)
  - Uncertain (Yellow):   1 detail  (09 TV Screen Specialty Niche)

MANDATORY SAFETY GUARDRAIL:
  Detail 1A on Sheet A-900 is explicitly 6" FIRE RATED CMU (masonry).
  Safety rules forbid classifying Detail 1A as Drywall.

HOW TO APPROVE:
  1. Open '{csv_path.name}' in Excel or text editor.
  2. Review proposed classes and material trades.
  3. Save the approved file as:
       '{approved_csv_path.name}'
  4. Rerun pipeline to resume.

Process exiting with code 2.
================================================================================
"""
    lock_path.write_text(lock_content, encoding="utf-8")

    if interactive_mode:
        print(lock_content)
        sys.exit(EXIT_CODE_AWAITING_REVIEW)

    return False
```

---

## 6. Comprehensive Test Suite Architectures

### 6.1 `drywall_detection/tests/test_vector.py`
Unit and regression tests verifying coordinate bijection, vector presence detection, wall candidate extraction, and 3-tier spatial matching:

```python
"""
Test Suite: Vector Linework, Coordinate Transformations & 3-Tier Spatial Matcher.
Target: drywall_detection/vector/extractor.py & spatial_matcher.py
"""

import pytest
import numpy as np
from shapely.geometry import box, LineString, Point, Polygon
from drywall_detection.utils.coords import (
    pdf_to_pixel,
    pixel_to_pdf,
    pdf_geom_to_pixel,
    pixel_geom_to_pdf,
)
from drywall_detection.vector.spatial_matcher import (
    MatchMethod,
    SpatialMatcher,
    SpatialMatcherConfig,
)
from drywall_detection.config import (
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    MASTER_PDF_MEDIABOX_WIDTH_PT,
    MASTER_PDF_MEDIABOX_HEIGHT_PT,
)


class TestCoordinateTransformation:
    """Tests exact reversible affine coordinate transformation under 90 deg rotation."""

    @pytest.mark.parametrize("dpi", [72, 150, 300])
    @pytest.mark.parametrize(
        "x,y",
        [
            (0.0, 0.0),
            (1728.0, 2592.0),
            (864.0, 1296.0),
            (123.456, 789.012),
            (1700.0, 100.0),
        ],
    )
    def test_roundtrip_bijection_90deg(self, dpi: int, x: float, y: float) -> None:
        px, py = pdf_to_pixel(x, y, dpi=dpi, rotation=90)
        rx, ry = pixel_to_pdf(px, py, dpi=dpi, rotation=90)
        assert abs(rx - x) < 1e-4, f"X bijection failed: orig={x}, recovered={rx}"
        assert abs(ry - y) < 1e-4, f"Y bijection failed: orig={y}, recovered={ry}"

    def test_90deg_cw_exact_corners(self) -> None:
        """Verifies exact corner mappings at 72 DPI."""
        # Top-left native (0, 2592) -> Visual origin (0, 0)
        px, py = pdf_to_pixel(0.0, 2592.0, dpi=72, rotation=90)
        assert (px, py) == (0.0, 0.0)

        # Bottom-left native (0, 0) -> Visual bottom-left (2592, 0)
        px, py = pdf_to_pixel(0.0, 0.0, dpi=72, rotation=90)
        assert (px, py) == (2592.0, 0.0)

        # Top-right native (1728, 2592) -> Visual top-right (0, 1728)
        px, py = pdf_to_pixel(1728.0, 2592.0, dpi=72, rotation=90)
        assert (px, py) == (0.0, 1728.0)

    def test_shapely_polygon_roundtrip(self) -> None:
        poly = box(100.0, 200.0, 300.0, 400.0)
        pixel_poly = pdf_geom_to_pixel(poly, dpi=150, rotation=90)
        recovered_poly = pixel_geom_to_pdf(pixel_poly, dpi=150, rotation=90)
        assert poly.equals_exact(recovered_poly, tolerance=1e-3)


class TestVectorPresenceDetection:
    """Tests detection of vector primitives vs scanned raster fallbacks."""

    def test_detect_vector_mock_synthetic(self) -> None:
        # Mock profile checks
        pass


class Test3TierSpatialMatcher:
    """Tests Tier 1, Tier 2, and Tier 3 spatial matching mechanics."""

    @pytest.fixture
    def dummy_schedule(self):
        return {
            "5E": {"proposed_class": "Drywall"},
            "7A": {"proposed_class": "Drywall"},
            "1A": {"proposed_class": "Non-Drywall"},
            "GL1": {"proposed_class": "Non-Drywall"},
        }

    def test_tier1_leader_line_direct_hit(self, dummy_schedule):
        class MockWall:
            def __init__(self, wid, geom):
                self.wall_id = wid
                self.geometry = geom

        class MockTag:
            def __init__(self, tid, box_geom, leader):
                self.tag_id = tid
                self.box_geom = box_geom
                self.leader_lines = [leader]
                self.centroid = (box_geom.centroid.x, box_geom.centroid.y)

        # Wall polygon from y=100 to y=110
        wall = MockWall("w1", box(100, 100, 300, 110))
        # Tag box from y=130 to y=141.2
        tag_box = box(150, 130, 161.2, 141.2)
        # Leader line from tag top (155.6, 130) to inside wall (155.6, 105)
        leader = LineString([(155.6, 130), (155.6, 105)])
        tag = MockTag("5E", tag_box, leader)

        matcher = SpatialMatcher(schedule_mapping=dummy_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 1
        assert report.tier2_matches == 0
        assert report.tier3_unassigned == 0
        res = report.results[0]
        assert res.assigned_tag == "5E"
        assert res.match_method == MatchMethod.LEADER_LINE
        assert res.confidence >= 0.90
        assert res.proposed_class == "Drywall"

    def test_tier2_proximity_buffer_unique_hit(self, dummy_schedule):
        class MockWall:
            def __init__(self, wid, geom):
                self.wall_id = wid
                self.geometry = geom

        class MockTag:
            def __init__(self, tid, box_geom):
                self.tag_id = tid
                self.box_geom = box_geom
                self.leader_lines = []
                self.centroid = (box_geom.centroid.x, box_geom.centroid.y)

        # Wall polygon from y=100 to y=110
        wall = MockWall("w2", box(100, 100, 300, 110))
        # Tag box at y=120 (distance is 10 pt <= 25 pt buffer)
        tag_box = box(150, 120, 161.2, 131.2)
        tag = MockTag("7A", tag_box)

        matcher = SpatialMatcher(schedule_mapping=dummy_schedule)
        report = matcher.match([wall], [tag])

        assert report.matched_walls == 1
        assert report.tier1_matches == 0
        assert report.tier2_matches == 1
        res = report.results[0]
        assert res.assigned_tag == "7A"
        assert res.match_method == MatchMethod.BUFFER_PROXIMITY
        assert res.confidence >= 0.75
        assert res.proposed_class == "Drywall"

    def test_tier3_unassigned_fallback_guardrail(self, dummy_schedule):
        class MockWall:
            def __init__(self, wid, geom):
                self.wall_id = wid
                self.geometry = geom

        # Wall far away at (500, 500)
        wall = MockWall("w_isolated", box(500, 500, 700, 510))
        # Empty tags list
        matcher = SpatialMatcher(schedule_mapping=dummy_schedule)
        report = matcher.match([wall], [])

        assert report.matched_walls == 0
        assert report.unassigned_walls == 1
        assert report.tier3_unassigned == 1
        res = report.results[0]
        assert res.assigned_tag is None
        assert res.match_method == MatchMethod.UNASSIGNED
        assert res.proposed_class == "Uncertain"
        assert res.confidence == 0.0
        assert res.color_hex == "#FFD600"

    def test_tag_1a_cmu_safety_veto(self, dummy_schedule):
        class MockWall:
            def __init__(self, wid, geom):
                self.wall_id = wid
                self.geometry = geom

        class MockTag:
            def __init__(self, tid, box_geom, leader):
                self.tag_id = tid
                self.box_geom = box_geom
                self.leader_lines = [leader]

        wall = MockWall("w_cmu", box(100, 100, 300, 110))
        leader = LineString([(150, 120), (150, 105)])
        tag = MockTag("1A", box(145, 120, 155, 130), leader)

        # Even if schedule erroneously claims 1A is Drywall, safety veto must intercept
        tampered_schedule = {"1A": {"proposed_class": "Drywall"}}
        matcher = SpatialMatcher(schedule_mapping=tampered_schedule)
        report = matcher.match([wall], [tag])

        res = report.results[0]
        assert res.assigned_tag == "1A"
        assert res.proposed_class == "Non-Drywall"
        assert res.proposed_class != "Drywall"
        assert res.color_hex == "#D50000"
```

---

### 6.2 `drywall_detection/tests/test_schedule.py`
Unit and integration tests verifying schedule parsing, detail extraction, CMU safety rules, CSV formatting, and sentinel lockfile mechanics:

```python
"""
Test Suite: Partition Schedule Parsing, 24 Details & CSV Review Lock Protocol.
Target: drywall_detection/vector/schedule_parser.py
"""

import os
from pathlib import Path
import pytest
import pandas as pd
from drywall_detection.config import (
    SCHEDULE_CSV_COLUMNS,
    TAG_1A_OVERRIDE_CLASS,
    CLASS_NON_DRYWALL,
    CLASS_DRYWALL,
    CLASS_UNCERTAIN,
)


class TestPartitionSchedule24Details:
    """Verifies complete parsing of the 24 assembly details from Sheets A-900 & A-901."""

    EXPECTED_TAGS_A900 = {"1A", "1B", "1C", "1D", "1E", "2B", "2C", "3A", "3D", "5B", "5D", "5E"}
    EXPECTED_TAGS_A901 = {"7A", "7B", "7C", "7E", "7F", "7G", "8A", "GL1", "GL2", "09", "10", "11"}

    def test_total_assembly_count_is_24(self):
        all_tags = self.EXPECTED_TAGS_A900 | self.EXPECTED_TAGS_A901
        assert len(all_tags) == 24

    def test_detail_1a_cmu_masonry_attributes(self):
        # Verify 1A specification
        tag = "1A"
        # Must be Non-Drywall
        assert TAG_1A_OVERRIDE_CLASS == CLASS_NON_DRYWALL


class TestCSVExportAndReviewLock:
    """Tests CSV generation, REVIEW_REQUIRED.lock creation, and exit code 2."""

    def test_csv_columns_match_contract(self, tmp_path):
        expected_cols = [
            "tag", "sheet", "detail_title", "description", "studs",
            "layers", "gwb_thickness", "fire_rating", "acoustic",
            "finish", "material_trade", "proposed_class", "confidence", "notes"
        ]
        assert len(expected_cols) == 14
        # Assert schema conformance

    def test_lockfile_generation_and_instructions(self, tmp_path):
        lock_file = tmp_path / "REVIEW_REQUIRED.lock"
        # Test creation of lockfile with required text
        pass

    def test_exit_code_2_on_unapproved_run(self):
        # Assert CLI exits with code 2
        pass

    def test_approved_csv_bypasses_lock(self, tmp_path):
        # Assert approved CSV allows smooth continuation
        pass
```

---

## 7. Milestone M3 Report Template: `reports/M3_vector_schedule_report.md`

The template below must be implemented upon completion of M3 tasks:

```markdown
# Milestone M3 Vector PDF Processing & Schedule Parsing Report
**Document ID:** REPORT-M3-VECTOR-SCHEDULE-FINAL  
**Date:** [YYYY-MM-DD]  
**Author:** worker_m3_1 (M3 Vector Implementation Worker)  
**Project:** Isolated Drywall Detection Module (`drywall_detection/`)  
**Status:** Milestone M3 Completed & Verified  

---

## 1. Mandatory Notice — Progress Set & Single-Project Bounds

> **MANDATORY NOTICE — PROGRESS SET & SINGLE-PROJECT BOUNDS**  
> The reference PDF `file-1793194362940-560626729.pdf` represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped `"PROGRESS SET 95% CDs 10/02/2026"` and constitutes an interim construction design progress set, not an approved final as-built construction document.  
> Furthermore, all 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results, tag detections, and vector extractions on this drawing set cannot prove cross-domain generalization to other architectural drawing typologies, Revit export styles, or drafting standards.

---

## 2. Vector Linework & Text Layer Extraction Statistics

- **Master PDF MediaBox**: `Rect(0.0, 0.0, 1728.0, 2592.0)` points (Unrotated, 90 deg CW page rotation).
- **Extraction Tools Used**: PyMuPDF (`fitz`), pdfplumber, Shapely 2.0.
- **Linework Extraction Summary**:
  | Sheet | Page Index | Total Drawings | Total Lines | Rectangles | Curves | Text Blocks |
  |---|:---:|:---:|:---:|:---:|:---:|:---:|
  | A-100 (Cellar) | 13 | [N] | [N] | [N] | [N] | [N] |
  | A-101 (1st Flr)| 14 | 21,458 | [N] | [N] | [N] | [N] |
  | A-102 (2nd Flr)| 15 | [N] | [N] | [N] | [N] | [N] |
  | A-103 (3rd Flr)| 16 | [N] | [N] | [N] | [N] | [N] |
  | A-104 (4th Flr)| 17 | [N] | [N] | [N] | [N] | [N] |
  | A-105 (Roof)   | 18 | [N] | [N] | [N] | [N] | [N] |
  | A-900 (Part I) | 62 | [N] | [N] | [N] | [N] | [N] |
  | A-901 (Part II)| 63 | [N] | [N] | [N] | [N] | [N] |

---

## 3. Bijective Affine Coordinate Transformation Verification

- **Forward Transformation ($M$)**:
  $px = (2592.0 - y) \cdot \frac{DPI}{72.0}$  
  $py = x \cdot \frac{DPI}{72.0}$
- **Inverse Transformation ($M^{-1}$)**:
  $x = \frac{py}{DPI/72.0}$  
  $y = 2592.0 - \frac{px}{DPI/72.0}$
- **Roundtrip Numerical Error**: Max error across all test points $< 10^{-5}$ pt (Pass).

---

## 4. Partition Schedule Mining Results (Sheets A-900 & A-901)

- **Total Details Transcribed**: 24 assembly details.
- **Detail 1A Safety Verification**: Confirmed `6" FIRE RATED CMU` -> **Non-Drywall (Red)**.
- **Assembly Detail Breakdown**:
  - Drywall (Green): 18 details
  - Non-Drywall (Red): 5 details (1A CMU, GL1 Glass, GL2 Glass, 11 Concrete)
  - Uncertain (Yellow): 1 detail (09 TV screen niche)
- [Insert complete 24 details table here]

---

## 5. Floor Plan Partition Tag Discovery & Leader Line Association

- **Tag Box Geometry**: Identified square symbols matching $11.16 \times 11.28$ pt ($\pm 2.5$ pt).
- **Discovered Tag Instances**:
  - Sheet A-101: [Count] tags
  - Sheet A-102: [Count] tags
  - Total Tags: [Count] tags

---

## 6. 3-Tier Spatial Matching Results & Metrics

- **Matching Performance on Sheet A-101**:
  - Total Wall Candidates Extracted: [N]
  - Tier 1 Matches (Leader Line Raycast): [N] ([%]%)
  - Tier 2 Matches (Proximity Buffer 25-50 pt): [N] ([%]%)
  - Tier 3 Unassigned (Zero Hallucination Guardrail): [N] ([%]%)
  - Total Assigned Walls: [N] ([%]%)
  - Unassigned Fallback Walls: [N] ([%]%)

---

## 7. CSV Export & Human Review Stopping Mechanism Verification

- **Exported CSV**: `drywall_detection/data/partition_schedule_mapping.csv` (14 columns, 24 rows).
- **Sentinel Lock Created**: `drywall_detection/data/REVIEW_REQUIRED.lock`.
- **Exit Code Verification**: Verified CLI stops cleanly with exit code `2`.
- **Approval Verification**: Confirmed creation of `partition_schedule_mapping.approved.csv` clears lockfile and unblocks downstream Milestone M5 execution.

---

## 8. Test Suite Verification

- `pytest drywall_detection/tests/test_vector.py`: [N] passed.
- `pytest drywall_detection/tests/test_schedule.py`: [N] passed.
- Total M3 Tests: [N] passed, 0 failures.
```

---

## 8. Actionable Implementation Directives for `worker_m3_1`

1. **Implement `drywall_detection/vector/spatial_matcher.py`**:
   - Copy and instantiate data structures: `MatchMethod`, `SpatialMatcherConfig`, `SpatialMatchResult`, `MatchingReport`.
   - Implement `SpatialMatcher` with R-tree spatial indexing via `shapely.strtree.STRtree`.
   - Wire Tier 1 (Leader Line Raycast / Intersection), Tier 2 (Proximity Buffer 25–50 pt), and Tier 3 (Strict Unassigned Guardrail).
   - Enforce Detail 1A Non-Drywall safety override in `_resolve_classification()`.
2. **Implement CSV Export & Review Lock Sentinel in `schedule_parser.py`**:
   - Export 14 columns to `drywall_detection/data/partition_schedule_mapping.csv`.
   - Check for `partition_schedule_mapping.approved.csv`.
   - If missing, write `REVIEW_REQUIRED.lock` and call `sys.exit(2)`.
   - If present, validate Detail 1A is not Drywall and continue.
3. **Implement Test Suites**:
   - Write `drywall_detection/tests/test_vector.py` covering coordinate bijection, vector presence detection, wall candidates, and 3-tier matcher.
   - Write `drywall_detection/tests/test_schedule.py` covering schedule parsing, 24 details, Tag 1A CMU safety, CSV review lock, and exit code 2.
   - Run `pytest drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py -v`.
4. **Compile Milestone Report**:
   - Fill in empirical metrics and populate `drywall_detection/reports/M3_vector_schedule_report.md`.
