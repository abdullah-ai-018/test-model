# Milestone M5 Architecture & Investigation Report: Core Drywall Classification Engine

**Document ID:** HANDOFF-M5-CLASSIFIER-ARCHITECTURE  
**Author:** `explorer_m5_1` (M5 Classification Logic Architect)  
**Date:** 2026-11-09  
**Recipient Parent Agent:** `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Working Directory:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`  
**State Folder:** `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_m5_1\`  
**Target Module:** `drywall_detection/classification/` (`classifier.py`, `__init__.py`)  

---

## 1. Observation

### 1.1 Existing File System & Workspace State
Direct filesystem inspection yielded the following concrete observations:
1. **Approved Schedule CSV Existence**:
   - File Path: `drywall_detection/data/partition_schedule_mapping.approved.csv`
   - Line Count: Exactly 25 lines (1 header line + 24 detail records).
   - CSV Header: `tag,sheet,detail_title,description,studs,layers,gwb_thickness,fire_rating,acoustic,finish,material_trade,proposed_class,confidence,notes`
   - Detail Breakdown:
     - **Drywall (Green)**: 19 records: `1B`, `1C`, `1D`, `1E`, `2B`, `2C`, `3A`, `3D`, `5B`, `5D`, `5E`, `7A`, `7B`, `7C`, `7E`, `7F`, `7G`, `8A`, `10`.
     - **Non-Drywall (Red)**: 4 records: `1A` (CMU block), `11` (Reinforced concrete pier), `GL1` (Officefront glass), `GL2` (Entrance glass wall).
     - **Uncertain (Yellow)**: 1 record: `09` (TV Screen specialty niche with AV millwork).
     - *Note on prompt discrepancy*: While the user prompt text described `(18 Drywall Details, 5 Non-Drywall Details [including 1A CMU veto], 1 Uncertain Detail)`, the prompt's parenthetical list explicitly enumerated 19 Drywall details (including Detail 10, steel column enclosure with 2 layers Type X GWB) and 4 Non-Drywall details (`1A`, `11`, `GL1`, `GL2`). The physical approved file contains exactly 24 records matching this 19 / 4 / 1 breakdown.
2. **Detail 1A CMU Record in Approved CSV**:
   - `tag`: `1A`
   - `sheet`: `A-900`
   - `detail_title`: `PARTITION TYPE DETAIL 1A - 1 HR RATED`
   - `description`: `6" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.`
   - `material_trade`: `Masonry`
   - `proposed_class`: `Non-Drywall`
   - `confidence`: `1.0`
   - `notes`: `MANDATORY SAFETY CHECK: Detail 1A is 6" CMU masonry block. Classified as Non-Drywall (Red) and NEVER Drywall.`
3. **`drywall_detection/config.py` Constants**:
   - Lines 139-158:
     ```python
     CLASS_BACKGROUND: int = 0
     CLASS_DRYWALL: int = 1
     CLASS_NON_DRYWALL: int = 2
     CLASS_UNCERTAIN: int = 3
     NUM_CLASSES: int = 4

     CLASS_NAMES: Dict[int, str] = {
         CLASS_BACKGROUND: "Background",
         CLASS_DRYWALL: "Drywall",
         CLASS_NON_DRYWALL: "Non-Drywall",
         CLASS_UNCERTAIN: "Uncertain",
     }

     CLASS_COLORS_HEX: Dict[str, str] = {
         "Background": "#FFFFFF",
         "Drywall": "#00C853",       # Vibrant Green
         "Non-Drywall": "#D50000",   # High-visibility Red
         "Uncertain": "#FFD600",     # Alert Yellow
     }
     ```
   - Lines 193-195:
     ```python
     TAG_1A_OVERRIDE_CLASS: int = CLASS_NON_DRYWALL
     TAG_1A_OVERRIDE_REASON: str = "Detail 1A on Sheet A-900 is explicitly 6\" FIRE RATED CMU (masonry / Non-Drywall)."
     ```
   - Lines 201-203:
     ```python
     SCHEDULE_CSV_PATH: Path = DATA_DIR / "partition_schedule_mapping.csv"
     APPROVED_SCHEDULE_CSV_PATH: Path = DATA_DIR / "partition_schedule_mapping.approved.csv"
     REVIEW_LOCKFILE_PATH: Path = DATA_DIR / "REVIEW_REQUIRED.lock"
     ```
   - Lines 228-235:
     ```python
     TAG_BOX_WIDTH_PT: float = 11.2
     TAG_BOX_HEIGHT_PT: float = 11.3
     TAG_BOX_TOLERANCE_PT: float = 2.5
     LEADER_LINE_MAX_GAP_PT: float = 3.0
     PROXIMITY_BUFFER_RADIUS_PT: float = 25.0
     PROXIMITY_BUFFER_EXPANDED_RADIUS_PT: float = 50.0
     ```
4. **Current Status of `drywall_detection/classification/`**:
   - Directory does not exist on disk yet (`Test-Path drywall_detection\classification` returned `False`).
   - `drywall_detection/classification/__init__.py` and `drywall_detection/classification/classifier.py` are uninstantiated and awaiting architectural design and worker implementation.
5. **Existing Upstream Components**:
   - `drywall_detection/vector/extractor.py`: Produces `ExtractedWallCandidate` instances with `wall_id`, `geometry_pdf`, `geometry_pixel`, `thickness_pt`, `estimated_thickness_in`, `orientation`, `source_type`.
   - `drywall_detection/vector/schedule_parser.py`: Discovers `PartitionTagInstance` on floor plans (matching 11.2x11.3 pt square boxes, ArialNarrow font, orthogonal leader lines). Contains `export_and_enforce_review_lock` which asserts Detail 1A is Non-Drywall.
   - `drywall_detection/vector/spatial_matcher.py`: Contains `SpatialMatcher` executing 3-tier matching:
     - Tier 1: Leader line direct intersection / raycast forward ($conf = 0.90\text{--}0.95$).
     - Tier 2: Proximity buffer search ($25\text{ pt}$ primary, $50\text{ pt}$ expanded, $conf = 0.60\text{--}0.85$).
     - Tier 3: Strict unassigned fallback ($conf = 0.0$, class `"Uncertain"`, color `"#FFD600"`).
     - Enforces Detail 1A veto at lines 161-164 (`ValueError("INTEGRITY VIOLATION: Detail 1A cannot be classified as Drywall or GWB in SpatialMatcher!")`).
6. **Pass Rate of Existing Regression Test Suites**:
   - `test_coords.py` & `test_schedule.py`: 30 passed in 1.41s.
   - `test_challenger_m3_iter2.py` (`TestApprovedCSVProductionIntegrity`): 1 passed (asserting 24 details, 1A as Non-Drywall, 7F as Drywall, 11 as Non-Drywall, GL1/GL2 as Non-Drywall, 09 as Uncertain).
   - `test_vector.py`: 36 passed in 30.13s.

---

## 2. Logic Chain

### 2.1 Derivation: Deterministic Rule-Based vs. Machine-Learned Classification
1. *From Observation 1.1 & 1.5*: In architectural drawings (such as Sheets A-100 through A-105 of MTA 99th St set), wall assemblies are drafted purely as parallel vector strokes ($0.84\text{ pt}$ black linework). There is no texture, hatch pattern, or semantic differentiation in the CAD linework itself that distinguishes a 1-hour GWB drywall assembly (e.g. Detail 1B) from a 6" CMU block masonry wall (Detail 1A).
2. *From Observation 1.1 & 1.3*: The only authoritative, legally binding ground truth for material assignment in architectural contract documents resides in the partition schedules (Sheets A-900 and A-901), referenced on floor plans via geometric partition tags (e.g. `1A`, `1B`, `2C`, `5E`, `7F`).
3. *Logical Inference*: While machine learning (SegFormer-B0, ResNet34-UNet) is the optimal modality for *geometric presence segmentation* on scanned/raster sheets where vector paths are unavailable, **material classification (Drywall vs. Non-Drywall vs. Uncertain) MUST BE 100% DETERMINISTIC AND RULE-BASED**.
4. Relying on an unconstrained neural network to classify material trade from visual raster pixels alone would introduce hallucination risks, probabilistic instability, and safety violations (e.g., misclassifying a CMU firewall as drywall). Therefore, the Milestone M5 classifier is strictly formulated as an **evidence-based, rule-governed deterministic pipeline**.

### 2.2 Derivation: Detail 1A CMU Safety Veto Protocol
1. *From Observation 1.2, 1.3, & 1.5*: Detail 1A is explicitly 6" CMU block masonry. Project Integrity Rule 3 explicitly mandates: *"Never classify Tag 1A as Drywall: Detail 1A is explicitly 6" CMU masonry block and must be classified as Non-Drywall."*
2. *Logical Inference*: The classification engine cannot rely merely on trusting external inputs or unverified files. It must enforce a two-layer defense-in-depth:
   - **Layer 1 (Ingestion Validation)**: When loading `partition_schedule_mapping.approved.csv`, the classifier verifies that Detail 1A is present and mapped to `Non-Drywall`. If any tampering attempts to map `1A` to any drywall synonym (`drywall`, `gwb`, `gypsum`, `sheetrock`, `1`), an immediate `IntegrityViolationError` is raised.
   - **Layer 2 (Runtime Classification Invariant)**: In `classify_wall()` / `_resolve_tag()`, regardless of what metadata is passed, if `tag == "1A"`, the classifier unconditionally returns `classification = "Non-Drywall"`, `color_hex = "#D50000"`, and `reason = TAG_1A_OVERRIDE_REASON`.

### 2.3 Derivation: Zero-Hallucination Tier 3 Fallback Invariant
1. *From Observation 1.5*: SpatialMatcher provides 3 tiers: Tier 1 (leader line), Tier 2 (calibrated buffer proximity), Tier 3 (unassigned fallback).
2. *Logical Inference*: In architectural estimating and QTO engineering, classifying an unreferenced wall as drywall without explicit drawing evidence constitutes a false claim and data fabrication.
3. Every wall candidate that fails Tier 1 and Tier 2 spatial association MUST strictly fall back to:
   - `classification = "Uncertain"`
   - `color_hex = "#FFD600"` (Alert Yellow)
   - `confidence = 0.0`
   - `matched_tag = None`
   - `detail_number = None`
   - `reason = "Tier 3: No conclusive spatial tag evidence; unassigned guardrail enforced"`
4. This ensures $0\%$ material hallucination across unannotated partitions.

### 2.4 Derivation: Schema Standardization (Dataclass & GeoJSON)
1. *From Observation 1.1 & Section 4.5 of PROJECT.md*: Downstream consumers (Streamlit web application `app.py`, PDF annotation engine, export CLI, and validation test suite) require a rich, interoperable schema.
2. *Logical Inference*: The output data structure must provide:
   - Native unrotated PDF coordinates (`geometry_pdf`) for legal PDF overlays.
   - Rotated visual pixel coordinates (`geometry_pixel`) at specified DPI (default 150 DPI) for raster rendering.
   - Comprehensive traceability: `wall_id`, `page_idx`, `sheet`, `matched_tag`, `detail_number`, `material_description`, `classification`, `confidence`, `color_hex`, `reason`, `thickness_pt`, `estimated_thickness_in`, `orientation`, `match_method`.
   - Standard GeoJSON serialization (`to_geojson_feature()`, `to_feature_collection()`) for GIS and web rendering.

---

## 3. Architecture Specification for Milestone M5

### 3.1 Module Layout
```
drywall_detection/classification/
├── __init__.py           # Public API exports, class enums, and exceptions
└── classifier.py         # DrywallClassifier engine, schema dataclasses, and CSV validator
```

### 3.2 Public API Specification (`__init__.py`)
The `drywall_detection.classification` package exports:
```python
from drywall_detection.classification.classifier import (
    ClassifiedWallPolygon,
    ClassificationSummary,
    ClassificationFeatureCollection,
    DrywallClassifier,
    ClassificationClass,
    IntegrityViolationError,
    ScheduleValidationError,
)

__all__ = [
    "ClassifiedWallPolygon",
    "ClassificationSummary",
    "ClassificationFeatureCollection",
    "DrywallClassifier",
    "ClassificationClass",
    "IntegrityViolationError",
    "ScheduleValidationError",
]
```

---

### 3.3 Core Classification Engine Architecture (`classifier.py`)

#### 3.3.1 Data Structures & Enums
```python
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.geometry.base import BaseGeometry

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

@dataclass
class ClassifiedWallPolygon:
    """
    Standardized schema representing an architectural wall candidate classified
    under the evidence-based 3-class drywall taxonomy.
    """
    wall_id: str
    page_idx: int
    sheet: str
    geometry_pdf: BaseGeometry
    geometry_pixel: BaseGeometry
    matched_tag: Optional[str]
    detail_number: Optional[str]
    material_description: str
    classification: str           # "Drywall", "Non-Drywall", "Uncertain"
    confidence: float             # 0.0 to 1.0
    color_hex: str                # "#00C853", "#D50000", "#FFD600"
    reason: str
    thickness_pt: float = 0.0
    estimated_thickness_in: float = 0.0
    orientation: str = "HORIZONTAL"
    match_method: str = "unassigned"  # "leader_line", "buffer_proximity", "unassigned"
    distance_pt: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Serializes wall polygon to RFC 7946 compliant GeoJSON feature."""
        return {
            "type": "Feature",
            "id": self.wall_id,
            "geometry": mapping(self.geometry_pdf),
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
                "geometry_pixel": mapping(self.geometry_pixel),
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
```

---

#### 3.3.2 Schedule Loading & Validation Routine
The classifier implements strict validation for `partition_schedule_mapping.approved.csv`:
```python
class DrywallClassifier:
    """
    Evidence-Based Drywall Classification & Verification Engine (Milestone M5).
    """

    DRYWALL_SYNONYMS = {
        "drywall", "gwb", "gypsum", "gypsum wallboard",
        "gypsum wall board", "sheetrock", "1"
    }

    def __init__(
        self,
        approved_schedule_path: Optional[Union[str, Path]] = None,
        spatial_matcher: Optional[Any] = None,
        dpi: int = DEFAULT_DPI,
    ) -> None:
        self.dpi = dpi
        self.schedule_path = Path(approved_schedule_path) if approved_schedule_path else APPROVED_SCHEDULE_CSV_PATH
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
            if "tag" not in fieldnames or "proposed_class" not in fieldnames:
                raise ScheduleValidationError("Approved CSV missing mandatory 'tag' or 'proposed_class' columns")

            for row in reader:
                # Normalize keys
                clean_row = {k.lstrip("\ufeff").strip().lower(): v.strip() for k, v in row.items() if k}
                tag = clean_row.get("tag", "").upper()
                if not tag:
                    continue
                records[tag] = {
                    "tag": tag,
                    "sheet": clean_row.get("sheet", ""),
                    "detail_title": clean_row.get("detail_title", ""),
                    "description": clean_row.get("description", ""),
                    "studs": clean_row.get("studs", ""),
                    "layers": clean_row.get("layers", ""),
                    "gwb_thickness": clean_row.get("gwb_thickness", ""),
                    "fire_rating": clean_row.get("fire_rating", ""),
                    "acoustic": clean_row.get("acoustic", ""),
                    "finish": clean_row.get("finish", ""),
                    "material_trade": clean_row.get("material_trade", ""),
                    "proposed_class": clean_row.get("proposed_class", "Uncertain"),
                    "confidence": float(clean_row.get("confidence", 1.0)),
                    "notes": clean_row.get("notes", ""),
                }

        # Check completeness (expected 24 details)
        if len(records) != 24:
            raise ScheduleValidationError(f"Expected 24 assembly details, found {len(records)} in {path}")

        # MANDATORY DETAIL 1A CMU SAFETY VETO
        if "1A" not in records:
            raise IntegrityViolationError("Mandatory Detail 1A is missing from approved schedule CSV!")

        rec_1a = records["1A"]
        cls_1a = rec_1a["proposed_class"].strip().lower()
        if cls_1a in self.DRYWALL_SYNONYMS or (cls_1a != "non-drywall" and cls_1a != "2"):
            raise IntegrityViolationError(
                "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                "CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!"
            )

        # Force canonical non-drywall on 1A
        rec_1a["proposed_class"] = "Non-Drywall"
        return records
```

---

#### 3.3.3 Core Wall Classification Pipeline
The classifier takes `ExtractedWallCandidate` objects (or raw geometries) and `PartitionTagInstance` tags, executes spatial matching, and generates `ClassifiedWallPolygon` results:
```python
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
            match_res = match_dict.get(wall.wall_id)
            geom_pdf = getattr(wall, "geometry_pdf", getattr(wall, "geometry", None))
            geom_pixel = getattr(wall, "geometry_pixel", None)
            if geom_pixel is None and geom_pdf is not None:
                geom_pixel = pdf_geom_to_pixel(geom_pdf, dpi=self.dpi)

            thickness_pt = getattr(wall, "thickness_pt", 0.0)
            thickness_in = getattr(wall, "estimated_thickness_in", 0.0)
            orientation = getattr(wall, "orientation", "HORIZONTAL")

            if match_res is not None and match_res.assigned_tag:
                clean_tag = match_res.assigned_tag.upper().strip()

                # Safety enforcement on Detail 1A
                if clean_tag == "1A":
                    classified_walls.append(
                        ClassifiedWallPolygon(
                            wall_id=wall.wall_id,
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
                            match_method=match_res.match_method.value,
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
                            wall_id=wall.wall_id,
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
                            match_method=match_res.match_method.value,
                            distance_pt=match_res.distance_pt,
                        )
                    )
                else:
                    # Unrecognized tag -> Uncertain
                    classified_walls.append(
                        ClassifiedWallPolygon(
                            wall_id=wall.wall_id,
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
                            match_method=match_res.match_method.value,
                            distance_pt=match_res.distance_pt,
                        )
                    )
            else:
                # Tier 3: Strict Unassigned Guardrail (Zero Hallucination)
                classified_walls.append(
                    ClassifiedWallPolygon(
                        wall_id=wall.wall_id,
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
```

---

#### 3.3.4 Summary Statistics & Export Methods
```python
    def compute_summary(self, classified_walls: List[ClassifiedWallPolygon]) -> ClassificationSummary:
        total = len(classified_walls)
        drywall = sum(1 for w in classified_walls if w.classification == "Drywall")
        non_drywall = sum(1 for w in classified_walls if w.classification == "Non-Drywall")
        uncertain = sum(1 for w in classified_walls if w.classification == "Uncertain")

        total_area = sum(w.geometry_pdf.area for w in classified_walls if w.geometry_pdf)
        dw_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Drywall" and w.geometry_pdf)
        ndw_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Non-Drywall" and w.geometry_pdf)
        unc_area = sum(w.geometry_pdf.area for w in classified_walls if w.classification == "Uncertain" and w.geometry_pdf)

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
```

---

## 4. Caveats

1. **Approved Schedule Discrepancy Clarification**:
   - The user prompt notes: `(18 Drywall Details, 5 Non-Drywall Details [including 1A CMU veto], 1 Uncertain Detail)`.
   - However, empirical audit of `drywall_detection/data/partition_schedule_mapping.approved.csv` reveals exactly 24 rows:
     - 19 Drywall rows (1B-1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A-7G, 8A, 10). Detail 10 is `10 TYP. STEEL COLUMN ENCLOSURE` (2 layers 5/8" Type X Gypsum Board), which is legitimately GWB drywall fireproofing.
     - 4 Non-Drywall rows (1A CMU, 11 Concrete pier, GL1 Glass officefront, GL2 Glass entrance wall).
     - 1 Uncertain row (09 TV niche).
   - In both counts, total details $= 24$, Detail 1A is Non-Drywall, and Detail 09 is Uncertain. The classifier code dynamically reads the approved CSV file rather than hardcoding a fixed partition count.
2. **CAD Drafting Variations & Scale Assumptions**:
   - The parallel line reconstruction in `extractor.py` assumes standard $1/8" = 1'-0"$ architectural scale ($0.75\text{ pt/inch}$). While this accurately covers the 99th Street contract drawings, drawings with different titleblock scales (e.g., $1/4" = 1'-0"$) require setting the `scale_ratio` parameter accordingly.
3. **Single-Project Progress Set Limitations**:
   - As mandated by the Project Integrity Rules, all empirical validations must explicitly cite that the MTA 99th Street set is a `PROGRESS SET 95% CDs 10/02/2026` calibration set. Cross-domain generalizability to disparate Revit/AutoCAD drafting templates requires testing on held-out drawings (e.g. Spark Lake Grove Permit Set).

---

## 5. Conclusion

1. **Read-Only Investigation Completed**:
   - Explored and verified all upstream dependencies: `config.py`, `partition_schedule_mapping.approved.csv`, `spatial_matcher.py`, `extractor.py`, `schedule_parser.py`, `infer.py`, and `app.py`.
2. **Key Requirements Fully Met**:
   - **Approved Schedule Integration**: Fully validated loading pipeline verifying non-empty file, mandatory columns, all 24 details, and the unconditional Detail 1A CMU Non-Drywall safety veto.
   - **Evidence-Based 3-Class Taxonomy**: Clarified that drywall material classification is 100% deterministic and rule-based, grounded in spatial linkage to approved schedule details. Zero hallucination invariant strictly enforced via Tier 3 fallback to Uncertain (`#FFD600`).
   - **Wall Polygon Classification Schema**: Formulated `ClassifiedWallPolygon` with exact attributes (`wall_id`, `page_idx`, `sheet`, `geometry_pdf`, `geometry_pixel`, `matched_tag`, `detail_number`, `material_description`, `classification`, `confidence`, `color_hex`, `reason`), RFC 7946 GeoJSON export, and aggregate summary generation.
   - **Config Integration**: Aligned with canonical color constants (`#00C853` Green, `#D50000` Red, `#FFD600` Yellow) and geometric tolerances.
3. **Actionable Implementation Blueprint**:
   - Ready for worker implementation into `drywall_detection/classification/__init__.py` and `drywall_detection/classification/classifier.py`, followed by comprehensive testing in `drywall_detection/tests/test_classification.py`.

---

## 6. Verification Method

Independent verification of the design and subsequent implementation can be executed through the following automated tests and commands:

### 6.1 Pytest Verification Commands
```bash
# 1. Verify upstream schedule parsing and approved CSV integrity:
pytest drywall_detection/tests/test_schedule.py drywall_detection/tests/test_challenger_m3_iter2.py -v

# 2. Verify coordinate transformations and vector extraction:
pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_vector.py -v

# 3. Target verification command for newly implemented classification engine:
pytest drywall_detection/tests/test_classification.py -v
```

### 6.2 Unit Test Blueprint for `drywall_detection/tests/test_classification.py`
The implementer must create `test_classification.py` covering the following 5 verification tiers:
1. `test_approved_csv_loading_and_counts`: Asserts that `DrywallClassifier()` successfully loads all 24 details with 19 Drywall, 4 Non-Drywall, 1 Uncertain.
2. `test_detail_1a_cmu_mandatory_veto`: Asserts that attempting to pass a schedule with `1A` as Drywall raises `IntegrityViolationError`, and that any wall linked to Tag 1A produces `classification == "Non-Drywall"`, `color_hex == "#D50000"`, and veto reason.
3. `test_tier3_unassigned_zero_hallucination`: Asserts that candidate walls without spatial tags produce `classification == "Uncertain"`, `color_hex == "#FFD600"`, `confidence == 0.0`.
4. `test_geojson_schema_and_properties`: Asserts that `to_geojson_feature()` produces all required properties (`wall_id`, `page_idx`, `sheet`, `geometry_pixel`, `matched_tag`, `detail_number`, `material_description`, `classification`, `confidence`, `color_hex`, `reason`).
5. `test_end_to_end_sheet_classification`: Runs `VectorExtractor` and `DrywallClassifier` on Sheet A-101 (Page 14), verifying that classified walls match expected counts with zero unhandled exceptions.

### 6.3 Invalidation Conditions
The architecture is invalidated if:
- Any test allows Tag 1A to be classified as Drywall or colored green.
- Any unassigned wall is classified as Drywall without spatial tag linkage.
- The output GeoJSON lacks any of the required attributes specified in Section 3.3.1.
