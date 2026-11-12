"""
drywall_detection/classification/classifier.py

Evidence-Based Drywall Classification & Verification Engine (Milestone M5).
Associates extracted wall geometries with approved partition schedules, enforcing:
  1. Deterministic evidence-based 3-class assignment (Drywall, Non-Drywall, Uncertain)
  2. Mandatory Detail 1A CMU Non-Drywall safety veto (unconditional, fatal fail-fast)
  3. Tier 3 strict unassigned fallback guardrail (zero material hallucination)
  4. RFC 7946 compliant GeoJSON serialization and material takeoff summaries.
"""

from __future__ import annotations
import csv
from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from shapely.geometry import mapping, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from drywall_detection.config import (
    APPROVED_SCHEDULE_CSV_PATH,
    CLASS_COLORS_HEX,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    DEFAULT_DPI,
    TAG_1A_OVERRIDE_REASON,
)
from drywall_detection.utils.coords import pdf_geom_to_pixel
from drywall_detection.vector.spatial_matcher import MatchMethod, SpatialMatcher


class ClassificationClass(str, Enum):
    DRYWALL = "Drywall"
    NON_DRYWALL = "Non-Drywall"
    UNCERTAIN = "Uncertain"


class IntegrityViolationError(ValueError):
    """Raised when mandatory safety guardrails (e.g. Detail 1A CMU veto) are breached."""
    pass


class ScheduleValidationError(ValueError):
    """Raised when partition schedule mapping CSV fails schema or integrity checks."""
    pass


DRYWALL_SYNONYMS = {
    "drywall",
    "gwb",
    "gypsum",
    "gypsum wallboard",
    "gypsum wall board",
    "sheetrock",
    "1",
}


@dataclass
class ClassifiedWallPolygon:
    """
    Standardized schema representing an architectural wall candidate classified
    under the evidence-based 3-class drywall taxonomy.
    """
    wall_id: str = "w0"
    page_idx: int = 0
    sheet: str = ""
    geometry_pdf: BaseGeometry = field(default_factory=Polygon)
    geometry_pixel: BaseGeometry = field(default_factory=Polygon)
    matched_tag: Optional[str] = None
    detail_number: Optional[str] = None
    material_description: str = ""
    classification: str = "Uncertain"  # "Drywall", "Non-Drywall", "Uncertain"
    confidence: float = 1.0  # 0.0 to 1.0
    color_hex: str = "#FFD600"  # "#00C853", "#D50000", "#FFD600"
    reason: str = ""
    thickness_pt: float = 0.0
    estimated_thickness_in: float = 0.0
    orientation: str = "HORIZONTAL"
    match_method: str = "unassigned"  # "leader_line", "buffer_proximity", "unassigned"
    distance_pt: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    polygon: Optional[BaseGeometry] = None

    def __post_init__(self) -> None:
        if self.polygon is not None:
            if getattr(self.geometry_pdf, "is_empty", True):
                self.geometry_pdf = self.polygon
            if getattr(self.geometry_pixel, "is_empty", True):
                self.geometry_pixel = self.polygon
        elif not getattr(self.geometry_pdf, "is_empty", True):
            self.polygon = self.geometry_pdf

        # Mandatory runtime safety check: Detail 1A cannot be classified as Drywall
        clean_tag = str(self.matched_tag or "").strip().upper()
        clean_detail = str(self.detail_number or "").strip().upper()
        if clean_tag == "1A" or clean_detail == "1A":
            cls_raw = self.classification.value if hasattr(self.classification, "value") else self.classification
            cls_str = str(cls_raw or "").strip().lower()
            if cls_str != "non-drywall" and cls_str != "2":
                raise IntegrityViolationError(
                    "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                    "must ONLY be classified as Non-Drywall."
                )
        self._initialized = True

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_initialized", False):
            if name == "classification" and (hasattr(self, "matched_tag") or hasattr(self, "detail_number")):
                clean_tag = str(getattr(self, "matched_tag", "") or "").strip().upper()
                clean_detail = str(getattr(self, "detail_number", "") or "").strip().upper()
                if clean_tag == "1A" or clean_detail == "1A":
                    val_raw = value.value if hasattr(value, "value") else value
                    val_str = str(val_raw or "").strip().lower()
                    if val_str != "non-drywall" and val_str != "2":
                        raise IntegrityViolationError(
                            "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block; "
                            "field mutation to Drywall is forbidden."
                        )
            elif name in ("matched_tag", "detail_number") and hasattr(self, "classification"):
                new_tag = str(value or "").strip().upper()
                if new_tag == "1A":
                    cls_raw = self.classification.value if hasattr(self.classification, "value") else self.classification
                    cls_str = str(cls_raw or "").strip().lower()
                    if cls_str != "non-drywall" and cls_str != "2":
                        raise IntegrityViolationError(
                            "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                            "cannot be classified as Drywall."
                        )
        super().__setattr__(name, value)

    @property
    def class_id(self) -> int:
        cls_str = str(self.classification).strip().lower()
        if "non" in cls_str:
            return CLASS_NON_DRYWALL
        elif "drywall" in cls_str:
            return CLASS_DRYWALL
        elif "uncertain" in cls_str:
            return CLASS_UNCERTAIN
        return CLASS_BACKGROUND

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Serializes wall polygon to RFC 7946 compliant GeoJSON feature."""
        geom_pixel_mapped = mapping(self.geometry_pixel) if self.geometry_pixel is not None else None
        return {
            "type": "Feature",
            "id": self.wall_id,
            "geometry": mapping(self.geometry_pdf) if self.geometry_pdf is not None else None,
            "properties": {
                "wall_id": self.wall_id,
                "page_idx": self.page_idx,
                "sheet": self.sheet,
                "matched_tag": self.matched_tag,
                "detail_number": self.detail_number,
                "material_description": self.material_description,
                "classification": self.classification,
                "confidence": round(self.confidence, 4),
                "color_hex": self.color_hex,
                "reason": self.reason,
                "thickness_pt": round(self.thickness_pt, 2),
                "estimated_thickness_in": round(self.estimated_thickness_in, 2),
                "orientation": self.orientation,
                "match_method": self.match_method,
                "distance_pt": round(self.distance_pt, 2),
                "geometry_pixel": geom_pixel_mapped,
                "metadata": self.metadata,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wall_id": self.wall_id,
            "page_idx": self.page_idx,
            "sheet": self.sheet,
            "matched_tag": self.matched_tag,
            "detail_number": self.detail_number,
            "material_description": self.material_description,
            "classification": self.classification,
            "confidence": round(self.confidence, 4),
            "color_hex": self.color_hex,
            "reason": self.reason,
            "thickness_pt": round(self.thickness_pt, 2),
            "estimated_thickness_in": round(self.estimated_thickness_in, 2),
            "orientation": self.orientation,
            "match_method": self.match_method,
            "distance_pt": round(self.distance_pt, 2),
            "metadata": self.metadata,
        }


@dataclass
class ClassificationSummary:
    """Aggregated material takeoff and classification statistics for a drawing or set."""
    total_walls: int
    drywall_count: int
    non_drywall_count: int
    uncertain_count: int
    drywall_pct: float
    non_drywall_pct: float
    uncertain_pct: float
    total_area_sq_pt: float
    drywall_area_sq_pt: float
    non_drywall_area_sq_pt: float
    uncertain_area_sq_pt: float
    tag_frequencies: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassificationFeatureCollection:
    """Complete collection of classified walls with metadata and summary."""
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DrywallClassifier:
    """
    Production Drywall Classification Engine (Milestone M5).
    Enforces deterministic schedule lookup, Detail 1A CMU Non-Drywall veto,
    and Tier 3 zero-hallucination unassigned fallback.
    """

    DRYWALL_SYNONYMS = DRYWALL_SYNONYMS

    def __init__(
        self,
        approved_schedule_path: Optional[Union[str, Path]] = None,
        spatial_matcher: Optional[Any] = None,
        dpi: int = DEFAULT_DPI,
        schedule_csv: Optional[Union[str, Path]] = None,
    ) -> None:
        self.dpi = dpi
        csv_path = approved_schedule_path or schedule_csv or APPROVED_SCHEDULE_CSV_PATH
        self.schedule_path = Path(csv_path)
        self.schedule_mapping: Dict[str, Dict[str, Any]] = self._load_and_validate_schedule(self.schedule_path)
        self.matcher = spatial_matcher or SpatialMatcher(schedule_mapping=self.schedule_mapping)

    def _load_and_validate_schedule(self, path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.is_file():
            raise FileNotFoundError(f"Approved partition schedule CSV not found at: {path}")
        if path.stat().st_size == 0:
            raise ScheduleValidationError(f"Approved schedule CSV is empty (0 bytes): {path}")

        records: Dict[str, Dict[str, Any]] = {}
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.lstrip("\ufeff").strip().lower() for fn in (reader.fieldnames or [])]

            tag_col = None
            class_col = None
            desc_col = None
            for fn in (reader.fieldnames or []):
                norm = fn.lstrip("\ufeff").strip().lower()
                if norm in ("tag", "detail tag", "tag_id", "detail"):
                    tag_col = fn
                elif norm in ("proposed_class", "approved class", "class", "classification"):
                    class_col = fn
                elif norm in ("description", "material description", "detail_title"):
                    desc_col = fn

            if not tag_col or not class_col:
                raise ScheduleValidationError("Approved CSV missing mandatory 'tag' or 'proposed_class' columns")

            for row in reader:
                clean_row = {k.lstrip("\ufeff").strip().lower(): v.strip() for k, v in row.items() if k}
                tag = str(row.get(tag_col, "")).strip().upper()
                if not tag:
                    continue
                prop_cls = str(row.get(class_col, "Uncertain")).strip()
                desc = str(row.get(desc_col, "") if desc_col else "").strip()
                records[tag] = {
                    "tag": tag,
                    "sheet": clean_row.get("sheet", ""),
                    "detail_title": clean_row.get("detail_title", desc),
                    "description": desc,
                    "studs": clean_row.get("studs", ""),
                    "layers": clean_row.get("layers", ""),
                    "gwb_thickness": clean_row.get("gwb_thickness", ""),
                    "fire_rating": clean_row.get("fire_rating", ""),
                    "acoustic": clean_row.get("acoustic", ""),
                    "finish": clean_row.get("finish", ""),
                    "material_trade": clean_row.get("material_trade", ""),
                    "proposed_class": prop_cls,
                    "confidence": float(clean_row.get("confidence", 1.0) or 1.0),
                    "notes": clean_row.get("notes", ""),
                }

        # 1. MANDATORY DETAIL 1A CMU SAFETY VETO (Fail-fast check)
        if "1A" in records:
            rec_1a = records["1A"]
            cls_1a = rec_1a["proposed_class"].strip().lower()
            if cls_1a in self.DRYWALL_SYNONYMS or (cls_1a != "non-drywall" and cls_1a != "2"):
                raise IntegrityViolationError(
                    "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                    "CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!"
                )
            rec_1a["proposed_class"] = "Non-Drywall"

        # 2. Schema completeness validation
        if len(records) != 24:
            raise ScheduleValidationError(f"Expected 24 assembly details, found {len(records)} in {path}")

        # 3. Mandatory Detail 1A must be present in full catalog
        if "1A" not in records:
            raise IntegrityViolationError("Mandatory Detail 1A is missing from approved schedule CSV!")

        return records

    def get_class(self, tag: str) -> str:
        """Returns the classified label for a tag name, defaulting to 'Uncertain'."""
        if not tag:
            return "Uncertain"
        clean_tag = str(tag).strip().upper()
        if clean_tag == "1A":
            return "Non-Drywall"
        rec = self.schedule_mapping.get(clean_tag)
        if rec:
            return rec.get("proposed_class", "Uncertain")
        return "Uncertain"

    def classify_walls(
        self,
        walls: List[Any],
        tags: List[Any],
        page_idx: int = 0,
        sheet: str = "",
    ) -> List[ClassifiedWallPolygon]:
        """
        Classifies candidate wall assemblies against discovered tags using
        3-tier spatial matching and the approved schedule database.
        """
        if not walls:
            return []

        # Run 3-tier spatial matcher
        report = self.matcher.match(walls, tags)
        match_dict: Dict[str, Any] = {r.wall_id: r for r in report.results}

        classified_walls: List[ClassifiedWallPolygon] = []

        for wall in walls:
            wall_id = getattr(wall, "wall_id", "") or (wall.get("wall_id") if isinstance(wall, dict) else str(id(wall)))
            match_res = match_dict.get(wall_id)

            geom_pdf = getattr(wall, "geometry_pdf", getattr(wall, "geometry", None))
            if geom_pdf is None and isinstance(wall, dict):
                geom_pdf = wall.get("geometry_pdf") or wall.get("geometry")

            geom_pixel = getattr(wall, "geometry_pixel", None)
            if geom_pixel is None and isinstance(wall, dict):
                geom_pixel = wall.get("geometry_pixel")

            if geom_pixel is None and geom_pdf is not None:
                geom_pixel = pdf_geom_to_pixel(geom_pdf, dpi=self.dpi)

            thickness_pt = getattr(wall, "thickness_pt", 0.0) if not isinstance(wall, dict) else wall.get("thickness_pt", 0.0)
            thickness_in = getattr(wall, "estimated_thickness_in", 0.0) if not isinstance(wall, dict) else wall.get("estimated_thickness_in", 0.0)
            orientation = getattr(wall, "orientation", "HORIZONTAL") if not isinstance(wall, dict) else wall.get("orientation", "HORIZONTAL")

            if match_res is not None and match_res.assigned_tag and match_res.assigned_tag.strip():
                clean_tag = match_res.assigned_tag.upper().strip()

                # MANDATORY DETAIL 1A CMU SAFETY VETO LAYER 2 (Runtime Invariant)
                if clean_tag == "1A":
                    classified_walls.append(
                        ClassifiedWallPolygon(
                            wall_id=wall_id,
                            page_idx=page_idx,
                            sheet=sheet,
                            geometry_pdf=geom_pdf,
                            geometry_pixel=geom_pixel,
                            matched_tag="1A",
                            detail_number="1A",
                            material_description='6" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF SLAB.',
                            classification="Non-Drywall",
                            confidence=match_res.confidence,
                            color_hex=CLASS_COLORS_HEX["Non-Drywall"],
                            reason=f"MANDATORY SAFETY VETO: Detail 1A is 6\" CMU masonry block. ({match_res.evidence})",
                            thickness_pt=thickness_pt,
                            estimated_thickness_in=thickness_in,
                            orientation=orientation,
                            match_method=match_res.match_method.value if hasattr(match_res.match_method, "value") else str(match_res.match_method),
                            distance_pt=match_res.distance_pt,
                        )
                    )
                    continue

                detail = self.schedule_mapping.get(clean_tag)
                if detail:
                    prop_class = detail["proposed_class"]
                    color = CLASS_COLORS_HEX.get(prop_class, CLASS_COLORS_HEX["Uncertain"])
                    desc = detail["description"]
                    mat_trade = detail["material_trade"]
                    evid = f"{match_res.evidence} -> Matched Detail {clean_tag} ({mat_trade})"

                    classified_walls.append(
                        ClassifiedWallPolygon(
                            wall_id=wall_id,
                            page_idx=page_idx,
                            sheet=sheet,
                            geometry_pdf=geom_pdf,
                            geometry_pixel=geom_pixel,
                            matched_tag=clean_tag,
                            detail_number=clean_tag,
                            material_description=desc,
                            classification=prop_class,
                            confidence=match_res.confidence,
                            color_hex=color,
                            reason=evid,
                            thickness_pt=thickness_pt,
                            estimated_thickness_in=thickness_in,
                            orientation=orientation,
                            match_method=match_res.match_method.value if hasattr(match_res.match_method, "value") else str(match_res.match_method),
                            distance_pt=match_res.distance_pt,
                        )
                    )
                else:
                    # Unrecognized tag in schedule -> Uncertain
                    classified_walls.append(
                        ClassifiedWallPolygon(
                            wall_id=wall_id,
                            page_idx=page_idx,
                            sheet=sheet,
                            geometry_pdf=geom_pdf,
                            geometry_pixel=geom_pixel,
                            matched_tag=clean_tag,
                            detail_number=None,
                            material_description="Tag not found in approved schedule",
                            classification="Uncertain",
                            confidence=0.30,
                            color_hex=CLASS_COLORS_HEX["Uncertain"],
                            reason=f"Unknown tag '{clean_tag}' not in approved schedule",
                            thickness_pt=thickness_pt,
                            estimated_thickness_in=thickness_in,
                            orientation=orientation,
                            match_method=match_res.match_method.value if hasattr(match_res.match_method, "value") else str(match_res.match_method),
                            distance_pt=match_res.distance_pt,
                        )
                    )
            else:
                # Tier 3: Strict Unassigned Guardrail (Zero Material Hallucination)
                classified_walls.append(
                    ClassifiedWallPolygon(
                        wall_id=wall_id,
                        page_idx=page_idx,
                        sheet=sheet,
                        geometry_pdf=geom_pdf,
                        geometry_pixel=geom_pixel,
                        matched_tag=None,
                        detail_number=None,
                        material_description="Unassigned wall linework (no spatial tag evidence)",
                        classification="Uncertain",
                        confidence=0.0,
                        color_hex=CLASS_COLORS_HEX["Uncertain"],
                        reason="Tier 3: No conclusive spatial tag evidence; unassigned guardrail enforced",
                        thickness_pt=thickness_pt,
                        estimated_thickness_in=thickness_in,
                        orientation=orientation,
                        match_method="unassigned",
                        distance_pt=float("inf"),
                    )
                )

        return classified_walls

    def classify_page(
        self,
        page_idx: int,
        sheet: str,
        walls: List[Any],
        tags: List[Any],
        page: Optional[Any] = None,
    ) -> List[ClassifiedWallPolygon]:
        """Convenience wrapper for single page classification."""
        return self.classify_walls(walls=walls, tags=tags, page_idx=page_idx, sheet=sheet)

    def compute_summary(self, classified_walls: List[ClassifiedWallPolygon]) -> ClassificationSummary:
        """Calculates material breakdown counts, percentages, area totals, and tag frequencies."""
        total = len(classified_walls)
        drywall = sum(1 for w in classified_walls if w.classification == "Drywall")
        non_drywall = sum(1 for w in classified_walls if w.classification == "Non-Drywall")
        uncertain = sum(1 for w in classified_walls if w.classification == "Uncertain")

        total_area = sum(w.geometry_pdf.area for w in classified_walls if w.geometry_pdf is not None)
        dw_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Drywall" and w.geometry_pdf is not None)
        ndw_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Non-Drywall" and w.geometry_pdf is not None)
        unc_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Uncertain" and w.geometry_pdf is not None)

        tag_counts: Dict[str, int] = {}
        for w in classified_walls:
            if w.matched_tag:
                tag_counts[w.matched_tag] = tag_counts.get(w.matched_tag, 0) + 1

        return ClassificationSummary(
            total_walls=total,
            drywall_count=drywall,
            non_drywall_count=non_drywall,
            uncertain_count=uncertain,
            drywall_pct=round((drywall / total) * 100.0, 2) if total else 0.0,
            non_drywall_pct=round((non_drywall / total) * 100.0, 2) if total else 0.0,
            uncertain_pct=round((uncertain / total) * 100.0, 2) if total else 0.0,
            total_area_sq_pt=round(total_area, 2),
            drywall_area_sq_pt=round(dw_area, 2),
            non_drywall_area_sq_pt=round(ndw_area, 2),
            uncertain_area_sq_pt=round(unc_area, 2),
            tag_frequencies=tag_counts,
        )

    def export_geojson(
        self,
        classified_walls: List[ClassifiedWallPolygon],
        output_path: Union[str, Path],
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Exports classified wall polygons to RFC 7946 compliant GeoJSON."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        summary = self.compute_summary(classified_walls)

        fc = ClassificationFeatureCollection(
            type="FeatureCollection",
            features=[w.to_geojson_feature() for w in classified_walls],
            summary=summary.to_dict(),
            metadata=extra_metadata or {},
        )

        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(fc.to_dict(), f, indent=2)

        return out_p
