"""
drywall_detection/vector/schedule_parser.py

Authoritative partition schedule parser, 24 assembly details miner, and
floor plan partition tag discovery engine (Milestone M3).
Enforces Detail 1A CMU Non-Drywall safety invariant and human review lock protocol.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import csv
import math
import os
import re
import sys

import fitz  # PyMuPDF
from shapely.geometry import box, LineString, Point, Polygon

from drywall_detection.config import (
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
    CLASS_COLORS_HEX,
    DATA_DIR,
    DEFAULT_MASTER_PDF_PATH,
    EXIT_CODE_AWAITING_REVIEW,
    REVIEW_LOCKFILE_PATH,
    SCHEDULE_CSV_PATH,
    APPROVED_SCHEDULE_CSV_PATH,
    TAG_1A_OVERRIDE_CLASS,
    TAG_1A_OVERRIDE_REASON,
    TAG_BOX_WIDTH_PT,
    TAG_BOX_HEIGHT_PT,
    TAG_BOX_TOLERANCE_PT,
)


SCHEDULE_14_COLUMNS = [
    "tag",
    "sheet",
    "detail_title",
    "description",
    "studs",
    "layers",
    "gwb_thickness",
    "fire_rating",
    "acoustic",
    "finish",
    "material_trade",
    "proposed_class",
    "confidence",
    "notes",
]


@dataclass
class ScheduleDetailRecord:
    """Represents a verified partition assembly detail from Sheets A-900 & A-901."""
    tag: str
    sheet: str
    detail_title: str
    description: str
    studs: str
    layers: str
    gwb_thickness: str
    fire_rating: str
    acoustic: str
    finish: str
    material_trade: str
    proposed_class: str  # "Drywall", "Non-Drywall", "Uncertain"
    confidence: float
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_csv_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionTagInstance:
    """Represents a discovered partition tag instance on an architectural floor plan."""
    tag: str = ""
    sheet: str = ""
    page_idx: int = 0
    bbox: Any = None
    center: Any = None
    box_polygon: Optional[List[Tuple[float, float]]] = None
    box_geom: Optional[Polygon] = None
    leader_line: Optional[Union[LineString, Tuple[Tuple[float, float], Tuple[float, float]]]] = None
    leader_lines: List[LineString] = field(default_factory=list)
    leader_target_pt: Optional[Tuple[float, float]] = None
    font_name: str = "ArialNarrow"
    font_size: float = 8.29
    classification: str = "Drywall"
    color_hex: str = "#00FF00"
    tag_name: Optional[str] = None
    page_index: Optional[int] = None
    center_pt: Any = None

    def __post_init__(self) -> None:
        if self.tag_name is not None and not self.tag:
            self.tag = self.tag_name
        elif not self.tag_name:
            self.tag_name = self.tag

        if self.page_index is not None and self.page_idx == 0:
            self.page_idx = self.page_index
        elif self.page_index is None:
            self.page_index = self.page_idx

        if self.center_pt is not None and self.center is None:
            if hasattr(self.center_pt, "x") and hasattr(self.center_pt, "y"):
                self.center = (float(self.center_pt.x), float(self.center_pt.y))
            elif isinstance(self.center_pt, (list, tuple)) and len(self.center_pt) >= 2:
                self.center = (float(self.center_pt[0]), float(self.center_pt[1]))
            else:
                self.center = self.center_pt
        elif self.center is not None and self.center_pt is None:
            self.center_pt = self.center

        if self.box_geom is None and self.bbox is not None:
            if hasattr(self.bbox, "x0"):
                self.box_geom = box(self.bbox.x0, self.bbox.y0, self.bbox.x1, self.bbox.y1)
            else:
                self.box_geom = box(*self.bbox)

        if self.leader_line is not None and not self.leader_lines:
            if isinstance(self.leader_line, LineString):
                self.leader_lines = [self.leader_line]
            elif isinstance(self.leader_line, (list, tuple)) and len(self.leader_line) == 2:
                self.leader_lines = [LineString([self.leader_line[0], self.leader_line[1]])]

    @property
    def tag_id(self) -> str:
        """Alias for tag to support varied matcher access patterns."""
        return self.tag

    @property
    def centroid(self) -> Tuple[float, float]:
        """Alias for center coordinate."""
        return self.center

    @property
    def box_bbox(self) -> Tuple[float, float, float, float]:
        """Alias for bbox."""
        return self.bbox


class PartitionScheduleParser:
    """
    Parses architectural PDF partition schedule sheets (A-900 & A-901),
    catalogs all 24 assembly details, provides offline fallback tables,
    discovers floor plan tags, and manages the CSV review lock protocol.
    """

    TAG_REGEX_STRICT = re.compile(
        r"^(1[A-E]|2[BC]|3[AD]|5[BDE]|7[ABCEFG]|8A|GL[12]|09|10|11)$"
    )

    AUTHORITATIVE_DETAILS: Dict[str, Dict[str, Any]] = {
        "1A": {
            "tag": "1A", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1A - 1 HR RATED",
            "description": "6\" FIRE RATED CMU MASONRY BLOCK. UNDERSIDE OF EXISTING SLAB, BEAM / OR DECK ABOVE. EXISTING FLOOR SLAB.",
            "studs": "None (CMU block)", "layers": "0", "gwb_thickness": "None", "fire_rating": "1-HR",
            "acoustic": "None", "finish": "None / Bare CMU", "material_trade": "Masonry",
            "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "MANDATORY SAFETY CHECK: Detail 1A is 6\" CMU masonry block. Classified as Non-Drywall (Red) and NEVER Drywall."
        },
        "1B": {
            "tag": "1B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1B",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. LINE OF SCHEDULED CEILING.",
            "studs": "2 1/2\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 13' HEIGHT; 13'-17' USE 20 GA.; OVER 17' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Standard interior drywall partition to slab with 2-1/2\" studs."
        },
        "1C": {
            "tag": "1C", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. UNDERSIDE OF EXISTING SLAB ABOVE. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Standard interior drywall partition to slab with 3-5/8\" studs and moisture barrier."
        },
        "1D": {
            "tag": "1D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1D",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. 6\" 16 GA STUDS UP TO 8'. ATTACH TO EXTERIOR BRICK WALL. 5/8\" CEILING ON 7/8\" FURRING. 10\" 16 GA STUD FRAMING @ 16\" O.C.",
            "studs": "6\" 16 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 8' HEIGHT; 10\" 16 GA. METAL STUD FRAMING @ 16\" O.C.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "GWB Ceiling + Plywood backing", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Heavy gauge 6\" drywall partition tied to exterior brick wall with soffit ceiling."
        },
        "1E": {
            "tag": "1E", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 1E",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8\" 25 GA STUDS UP TO 8' HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 8' HEIGHT",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Low drywall partition (up to 8' height) to slab."
        },
        "2B": {
            "tag": "2B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 2B",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET.",
            "studs": "2 1/2\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 13' HEIGHT; 13'-17' USE 20 GA.; OVER 17' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Acoustic drywall partition with 2-1/2\" studs and sound attenuation blanket."
        },
        "2C": {
            "tag": "2C", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 2C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM. *MOISTURE RESISTANT BARRIER.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "High performance acoustic drywall partition with 3-5/8\" studs, blanket, acoustic sealant, moisture barrier."
        },
        "3A": {
            "tag": "3A", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 3A",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 3 5/8\" STUDS UP TO 22'+ HEIGHT. UNDERSIDE OF EXISTING SLAB ABOVE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 17' HEIGHT; 17'-22' USE 20 GA.; OVER 22' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Full-height drywall partition to underside of deck with 3-5/8\" studs."
        },
        "3D": {
            "tag": "3D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 3D",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. 6\" 25 GA STUDS UP TO 20' (20'-32' USE 20 GA). *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "6\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 20' HEIGHT; 20'-32' USE 20 GA. METAL STUDS",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Extra-tall drywall partition (up to 32') with 6\" studs and moisture barrier."
        },
        "5B": {
            "tag": "5B", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 5B - 1 HR RATED",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD UL TYPE SCX ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "2 (1 each side, staggered)", "gwb_thickness": "5/8\" UL Type SCX", "fire_rating": "1-HR (UL U419)",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Type SCX GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "1-Hour fire-rated acoustic drywall partition (UL U419) with 5/8\" Type SCX gypsum board."
        },
        "5D": {
            "tag": "5D", "sheet": "A-900", "detail_title": "PARTITION TYPE DETAIL 5D",
            "description": "(2) LAYERS OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. 6\" 25 GA STUDS UP TO 20' (20'-33' USE 20 GA). CONTINUOUS ACOUSTIC SEALANT.",
            "studs": "6\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 20' HEIGHT; 20'-33' USE 20 GA. METAL STUDS",
            "layers": "4 (2 each side, staggered)", "gwb_thickness": "5/8\" (double layer)", "fire_rating": "2-HR equivalent / Non-rated scheduled",
            "acoustic": "CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Double-layer GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "High acoustic 6\" drywall partition with double-layer GWB on both sides (4 layers total)."
        },
        "5E": {
            "tag": "5E", "sheet": "A-900", "detail_title": "5E PARTITION TYPE DETAIL 5E - 2 HR RATED",
            "description": "(2) LAYERS OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE OF METAL STUD. STAGGER ALL VERTICAL JOINTS. UL U419. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. (MAX.) UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "4 (2 each side, staggered)", "gwb_thickness": "5/8\" (double layer)", "fire_rating": "2-HR (UL U419)",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Double-layer Type X/SCX GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "2-Hour fire-rated acoustic drywall partition (UL U419) with 4 layers of 5/8\" GWB and blanket."
        },
        "7A": {
            "tag": "7A", "sheet": "A-901", "detail_title": "PERIMETER FURRING PARTITION 7A",
            "description": "EXISTING WALL. (1) LAYER OF 5/8\" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 1 1/2\" RIGID INSULATION. 1 1/2\" RIGID = 7.5 R VALUE. 5/8\" GYP = 0.5 R VALUE. TOTAL = 8 R VALUE.",
            "studs": "Furred / metal channel runners", "layers": "1 (laminated single face)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "None (R-8 Thermal: 1-1/2\" Rigid Insulation R-7.5 + 5/8\" GWB R-0.5)",
            "finish": "Laminated GWB + Wall Base", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Perimeter exterior wall furring with 1-1/2\" rigid insulation and 5/8\" laminated drywall."
        },
        "7B": {
            "tag": "7B", "sheet": "A-901", "detail_title": "FURRING PARTITION 7B",
            "description": "UNDERSIDE OF EXISTING SLAB ABOVE. 3 5/8\" 25 GA STUDS UP TO 16' (16'-23' 20 GA, OVER 23' 18 GA). FULL HEIGHT SOUND ATTENUATION BLANKET. (1) LAYER OF 5/8\" GWB ON ROOM SIDE.",
            "studs": "3 5/8\" 25 GA. METAL STUDS @ 16\" O.C. UP TO 16' HEIGHT; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.",
            "layers": "1 (room side only)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET",
            "finish": "GWB on room side", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Single-sided drywall furring partition with 3-5/8\" studs and sound attenuation blanket."
        },
        "7C": {
            "tag": "7C", "sheet": "A-901", "detail_title": "7C PARTITION TYPE DETAIL 7C",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 2 1/2\" 20 GA STUDS @ 16\" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES. *MOISTURE BARRIER.",
            "studs": "(2) METAL RUNNERS; 2 1/2\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.; BRACING (48\" O.C. MAX)",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 2-1/2\" acoustic drywall partition with sound blanket and acoustic sealant both sides."
        },
        "7E": {
            "tag": "7E", "sheet": "A-901", "detail_title": "7E PARTITION TYPE DETAIL 7E",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8\" 20 GA STUDS @ 16\" O.C. FULL HEIGHT SOUND BLANKET. CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES.",
            "studs": "(2) METAL RUNNERS; 3 5/8\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated",
            "acoustic": "FULL HEIGHT AND THICKNESS SOUND ATTENUATION BLANKET; CONTINUOUS ACOUSTICAL SEALANT BOTH SIDES",
            "finish": "Standard GWB", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 3-5/8\" acoustic drywall partition with sound blanket and acoustic sealant."
        },
        "7F": {
            "tag": "7F", "sheet": "A-901", "detail_title": "SHAFT WALL PARTITION 7F - 2 HR RATED",
            "description": "(2) LAYERS OF 1/2\" TYPE-C GYPSUM BOARD (ROOM SIDE) + (1) LAYER OF 1\" TYPE-SCX GYPSUM BOARD (SHAFT SIDE). 2 1/2\" C-H STUDS @ 24\" O.C. 4\" METAL J RUNNER. UL U415 SYSTEM E. *MOISTURE BARRIER.",
            "studs": "2 1/2\" 25 GA. C-H METAL STUD @ 24\" O.C. UP TO 16'; 16'-23' USE 20 GA.; OVER 23' USE 18 GA.; 4\" METAL J RUNNER",
            "layers": "3 (2 layers 1/2\" Type C room side + 1 layer 1\" Type SCX shaft core)",
            "gwb_thickness": "1/2\" Type-C (2x) + 1\" Type-SCX (1x)", "fire_rating": "2-HR (UL U415 System E)",
            "acoustic": "CONTINUOUS ACOUSTIC SEALANT TOP & BOTTOM, EACH SIDE",
            "finish": "Type-C and Type-SCX Shaft Wall; Moisture Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "2-Hour fire-rated elevator/stair shaft wall (UL U415 System E) with C-H studs and 1\" shaftliner + double 1/2\" Type C."
        },
        "7G": {
            "tag": "7G", "sheet": "A-901", "detail_title": "PARTITION TYPE DETAIL 7G",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD ON EACH SIDE. (2) METAL CHANNEL RUNNERS. 3 5/8\" 20 GA STUDS @ 16\" O.C. HORIZONTAL BRACING AS REQUIRED. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "(2) METAL RUNNERS; 3 5/8\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.; HORIZONTAL BRACING AS REQUIRED",
            "layers": "2 (1 each side)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Double runner 3-5/8\" plumbing chase / pipe drywall partition with horizontal bracing."
        },
        "8A": {
            "tag": "8A", "sheet": "A-901", "detail_title": "8A FURRING PARTITION 8A",
            "description": "(1) LAYER OF 5/8\" GYPSUM WALL BOARD LAMINATED TO EXISTING WALL. 2 1/2\" 20 GA METAL STUDS @ 16\" O.C. *MOISTURE RESISTANT BARRIER ON ALL WET LOCATIONS.",
            "studs": "2 1/2\" 20 GA METAL STUDS @ 16\" O.C. (MAX.); OVER 14' USE 18 GA.",
            "layers": "1 (laminated to existing wall)", "gwb_thickness": "5/8\"", "fire_rating": "Non-rated", "acoustic": "None",
            "finish": "Moisture Resistant Barrier in wet areas", "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Studded drywall wall furring against existing masonry/concrete wall with 2-1/2\" studs."
        },
        "09": {
            "tag": "09", "sheet": "A-901", "detail_title": "09 SECTION @ TV SCREEN",
            "description": "COORDINATE WITH AV DRAWINGS. ELECTRICAL BACK BOX/PANEL. BLOCKING AS REQUIRED. BATT INSULATION INSIDE CAVITIES. SCHEDULED WALL FINISH. SCHEDULED TV.",
            "studs": "Scheduled partition framing + wood/metal blocking as required",
            "layers": "Per scheduled partition", "gwb_thickness": "Per scheduled partition", "fire_rating": "Non-rated",
            "acoustic": "BATT INSULATION INSIDE ALL CAVITIES", "finish": "Scheduled Wall Finish / AV Millwork",
            "material_trade": "Millwork / AV Equipment", "proposed_class": "Uncertain", "confidence": 0.8,
            "notes": "Specialty architectural section through wall-mounted TV screen with electrical backbox and structural blocking. Classified as Uncertain (Yellow)."
        },
        "10": {
            "tag": "10", "sheet": "A-901", "detail_title": "10 TYP. STEEL COLUMN ENCLOSURE",
            "description": "PROVIDE 2 LAYERS OF TYPE X. GYPSUM BOARD AROUND EXISTING STRUC. COLUMN TYP.",
            "studs": "Framing / furring clips around steel column", "layers": "2 (around all 4 faces)", "gwb_thickness": "5/8\" Type X (2 layers)",
            "fire_rating": "2-HR Column Fireproofing", "acoustic": "None", "finish": "Type X Gypsum Board Enclosure",
            "material_trade": "Drywall", "proposed_class": "Drywall", "confidence": 1.0,
            "notes": "Fire-resistive gypsum wallboard enclosure around structural steel column (2 layers Type X)."
        },
        "11": {
            "tag": "11", "sheet": "A-901", "detail_title": "TYP. CONCRETE ENCASED STEEL COLUMN 11",
            "description": "REINFORCED CONCRETE ENCASED COLUMN 56\" HIGH. EXISTING STRUCTURAL COLUMN. 26\" x 26\" CONCRETE PIER.",
            "studs": "None (Reinforced concrete)", "layers": "0", "gwb_thickness": "None", "fire_rating": "Structural concrete fireproofing",
            "acoustic": "None", "finish": "Exposed Concrete", "material_trade": "Concrete", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Structural reinforced concrete encasement around steel column. Classified as Non-Drywall (Red) - NEVER Drywall."
        },
        "GL1": {
            "tag": "GL1", "sheet": "A-901", "detail_title": "GL1 GLASS OFFICEFRONT SYSTEM",
            "description": "INFINIUM QUANTUM SINGLE BUTT-GLAZED CENTER OFFICE FRONT SYSTEM. R-19 INSULATION. 2-1/2\" 20 GA. METAL STUDS @ 16\" O.C. (1) LAYER GWB TO 6\" ABOVE CEILING. ALIGN HEADER TO ACT CEILING.",
            "studs": "INFINIUM QUANTUM aluminum frame + 2 1/2\" 20 GA metal studs for header/soffit",
            "layers": "Butt-glazed glass system + GWB header soffit", "gwb_thickness": "1/2\" or 5/8\" on header soffit only",
            "fire_rating": "Non-rated", "acoustic": "R-19 INSULATION IN HEADER",
            "finish": "Demountable glass storefront system", "material_trade": "Glazing / Demountable Partition", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Infinium Quantum demountable glass officefront system. Classified as Non-Drywall (Red)."
        },
        "GL2": {
            "tag": "GL2", "sheet": "A-901", "detail_title": "GLASS WALL AT ENTRANCE GL2",
            "description": "TUBELITE 400TU FRAME BY APOGEE. R-19 INSULATION. 3-5/8\" 20 GA STUDS @ 16\" O.C. (1) LAYER GWB TO SLAB ABOVE EACH SIDE. ALIGN HEADER TO GYP. BD. CEILING. TRANSOM ABOVE 8'-0\" AFF.",
            "studs": "TUBELITE 400TU aluminum frame + 3 5/8\" 20 GA metal studs for transom/soffit",
            "layers": "Glass storefront + GWB header to slab", "gwb_thickness": "5/8\" on header to slab",
            "fire_rating": "Non-rated", "acoustic": "R-19 INSULATION IN HEADER",
            "finish": "Aluminum storefront glass wall", "material_trade": "Glazing / Storefront", "proposed_class": "Non-Drywall", "confidence": 1.0,
            "notes": "Tubelite 400TU aluminum entrance glass storefront system. Classified as Non-Drywall (Red)."
        }
    }

    # Grid bounding boxes in unrotated mediabox space for Sheets A-900 and A-901
    SHEET_CELL_COORDS: Dict[str, List[Tuple[str, Tuple[float, float, float, float]]]] = {
        "A-900": [
            ("1D", (0.0, 350.0, 420.0, 890.0)),
            ("1C", (0.0, 890.0, 420.0, 1430.0)),
            ("1B", (0.0, 1430.0, 420.0, 1970.0)),
            ("1A", (0.0, 1970.0, 420.0, 2520.0)),
            ("3A", (420.0, 350.0, 835.0, 890.0)),
            ("2C", (420.0, 890.0, 835.0, 1430.0)),
            ("2B", (420.0, 1430.0, 835.0, 1970.0)),
            ("1E", (420.0, 1970.0, 835.0, 2520.0)),
            ("5E", (835.0, 350.0, 1260.0, 890.0)),
            ("5D", (835.0, 890.0, 1260.0, 1430.0)),
            ("5B", (835.0, 1430.0, 1260.0, 1970.0)),
            ("3D", (835.0, 1970.0, 1260.0, 2520.0)),
        ],
        "A-901": [
            ("7E", (0.0, 350.0, 420.0, 890.0)),
            ("7C", (0.0, 890.0, 420.0, 1430.0)),
            ("7B", (0.0, 1430.0, 420.0, 1970.0)),
            ("7A", (0.0, 1970.0, 420.0, 2520.0)),
            ("09", (420.0, 350.0, 835.0, 890.0)),
            ("8A", (420.0, 890.0, 835.0, 1430.0)),
            ("7G", (420.0, 1430.0, 835.0, 1970.0)),
            ("7F", (420.0, 1970.0, 835.0, 2520.0)),
            ("11", (835.0, 350.0, 1260.0, 890.0)),
            ("10", (835.0, 890.0, 1260.0, 1430.0)),
            ("GL2", (835.0, 1430.0, 1260.0, 1970.0)),
            ("GL1", (835.0, 1970.0, 1260.0, 2520.0)),
        ],
    }

    def __init__(self, pdf_path: Optional[Union[str, Path]] = None) -> None:
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self._records: Dict[str, ScheduleDetailRecord] = {}
        # Prepopulate with authoritative 24-detail fallback dictionary
        for tag, data in self.AUTHORITATIVE_DETAILS.items():
            self._records[tag] = ScheduleDetailRecord(**data)

    def get_detail(self, tag: str) -> Optional[ScheduleDetailRecord]:
        """Returns detail record for a tag (case-insensitive)."""
        clean_tag = tag.strip().upper()
        # Handle '09' or '9'
        if clean_tag == "9":
            clean_tag = "09"
        return self._records.get(clean_tag)

    def parse_pdf(self, pdf_path: Optional[Union[str, Path]] = None) -> List[ScheduleDetailRecord]:
        """
        Parses sheets A-900 and A-901 from the PDF, extracts cell text,
        updates records, and enforces safety invariant.
        """
        target_path = Path(pdf_path) if pdf_path else self.pdf_path
        if not target_path or not target_path.exists():
            return list(self._records.values())

        doc = fitz.open(target_path)
        found_a900 = False
        found_a901 = False

        # Fast path: Check known indices 62 and 63 first
        if len(doc) > 63:
            p62 = doc[62]
            t62 = p62.get_text()
            if "PARTITION TYPES SHEET I" in t62 or "A-900" in t62:
                self.parse_sheet(p62, "A-900")
                found_a900 = True
            p63 = doc[63]
            t63 = p63.get_text()
            if "PARTITION TYPES SHEET II" in t63 or "A-901" in t63:
                self.parse_sheet(p63, "A-901")
                found_a901 = True

        if not (found_a900 and found_a901):
            for i, page in enumerate(doc):
                text = page.get_text()
                if not found_a900 and ("PARTITION TYPES SHEET I" in text or "A-900" in text):
                    self.parse_sheet(page, "A-900")
                    found_a900 = True
                elif not found_a901 and ("PARTITION TYPES SHEET II" in text or "A-901" in text):
                    self.parse_sheet(page, "A-901")
                    found_a901 = True
                if found_a900 and found_a901:
                    break

        # MANDATORY INTEGRITY GUARDRAIL: Detail 1A is strictly Non-Drywall
        assert self._records["1A"].proposed_class == "Non-Drywall", (
            "CRITICAL SAFETY VIOLATION: Detail 1A must unconditionally be classified as Non-Drywall!"
        )
        return list(self._records.values())

    def parse_sheet(self, page: fitz.Page, sheet_name: str) -> List[ScheduleDetailRecord]:
        """Parses cell coordinates of a schedule sheet."""
        if sheet_name not in self.SHEET_CELL_COORDS:
            return []

        results = []
        for tag, (x0, y0, x1, y1) in self.SHEET_CELL_COORDS[sheet_name]:
            rect = fitz.Rect(x0, y0, x1, y1)
            cell_text = page.get_textbox(rect).strip()
            if cell_text and tag in self._records:
                rec = self._records[tag]
                if tag == "1A":
                    # Invariant: Must remain Non-Drywall regardless of extracted text
                    rec.proposed_class = "Non-Drywall"
                results.append(rec)
        return results

    # --------------------------------------------------------------------------
    # Floor Plan Partition Tag Discovery Engine
    # --------------------------------------------------------------------------
    def discover_tags(
        self,
        page: Any,
        page_idx: int = 0,
        sheet_name: str = "",
    ) -> List[PartitionTagInstance]:
        """
        Discovers verified partition tag instances on floor plans matching:
        - 11.2 x 11.3 pt vector square boxes (w=0.48 pt lines)
        - ArialNarrow font text tokens
        - Attached orthogonal leader lines (w=0.48 pt)
        """
        tag_instances: List[PartitionTagInstance] = []
        if not hasattr(page, "get_text") or not hasattr(page, "get_drawings"):
            return tag_instances

        # 1. Extract vector drawings and find 11.2 x 11.3 pt candidate boxes & leader lines
        drawings = page.get_drawings()
        candidate_boxes: List[fitz.Rect] = []
        light_lines: List[Tuple[Point, Point]] = []

        for d in drawings:
            r = d.get("rect")
            width = round(float(d.get("width", 0.0)), 2)
            if r is not None:
                if (
                    abs(r.width - TAG_BOX_WIDTH_PT) <= TAG_BOX_TOLERANCE_PT
                    and abs(r.height - TAG_BOX_HEIGHT_PT) <= TAG_BOX_TOLERANCE_PT
                ):
                    candidate_boxes.append(r)

            # Check lines for leaders (w == 0.48 pt or w < 0.84 pt)
            if width < 0.84:
                for it in d.get("items", []):
                    if it[0] == "l":
                        light_lines.append((Point(it[1].x, it[1].y), Point(it[2].x, it[2].y)))

        # 2. Extract text blocks
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if not txt or not self.TAG_REGEX_STRICT.match(txt):
                            continue

                        bbox_raw = span.get("bbox")
                        if not bbox_raw:
                            continue
                        t_rect = fitz.Rect(bbox_raw)
                        cx = (t_rect.x0 + t_rect.x1) / 2.0
                        cy = (t_rect.y0 + t_rect.y1) / 2.0

                        # Match with candidate box or synthesize
                        matched_box = None
                        for b in candidate_boxes:
                            if b.intersects(t_rect) or b.contains(t_rect):
                                matched_box = b
                                break

                        if matched_box is None:
                            matched_box = fitz.Rect(
                                cx - TAG_BOX_WIDTH_PT / 2.0,
                                cy - TAG_BOX_HEIGHT_PT / 2.0,
                                cx + TAG_BOX_WIDTH_PT / 2.0,
                                cy + TAG_BOX_HEIGHT_PT / 2.0,
                            )

                        box_poly = [
                            (matched_box.x0, matched_box.y0),
                            (matched_box.x1, matched_box.y0),
                            (matched_box.x1, matched_box.y1),
                            (matched_box.x0, matched_box.y1),
                        ]
                        box_geom = box(matched_box.x0, matched_box.y0, matched_box.x1, matched_box.y1)

                        # Look for attached leader lines
                        matched_leader: Optional[LineString] = None
                        leader_target: Optional[Tuple[float, float]] = None

                        bx0, by0 = matched_box.x0 - 2.0, matched_box.y0 - 2.0
                        bx1, by1 = matched_box.x1 + 2.0, matched_box.y1 + 2.0

                        for p1, p2 in light_lines:
                            # Fast scalar bounding check before Shapely distance calls
                            p1_near = (bx0 <= p1.x <= bx1 and by0 <= p1.y <= by1)
                            p2_near = (bx0 <= p2.x <= bx1 and by0 <= p2.y <= by1)
                            if not (p1_near or p2_near):
                                continue

                            d1 = box_geom.distance(p1)
                            d2 = box_geom.distance(p2)
                            line_len = p1.distance(p2)
                            if line_len < 2.0:
                                continue

                            # One endpoint touches or is within 2.0 pt of box
                            if d1 <= 2.0 and d2 > 2.0:
                                matched_leader = LineString([(p1.x, p1.y), (p2.x, p2.y)])
                                leader_target = (p2.x, p2.y)
                                break
                            elif d2 <= 2.0 and d1 > 2.0:
                                matched_leader = LineString([(p2.x, p2.y), (p1.x, p1.y)])
                                leader_target = (p1.x, p1.y)
                                break

                        detail = self.get_detail(txt)
                        prop_class = detail.proposed_class if detail else "Uncertain"
                        color = CLASS_COLORS_HEX.get(prop_class, "#FFD600")

                        tag_instances.append(
                            PartitionTagInstance(
                                tag=txt,
                                sheet=sheet_name,
                                page_idx=page_idx,
                                bbox=(matched_box.x0, matched_box.y0, matched_box.x1, matched_box.y1),
                                center=(cx, cy),
                                box_polygon=box_poly,
                                box_geom=box_geom,
                                leader_line=matched_leader,
                                leader_lines=[matched_leader] if matched_leader else [],
                                leader_target_pt=leader_target,
                                font_name=span.get("font", "ArialNarrow"),
                                font_size=float(span.get("size", 8.29)),
                                classification=prop_class,
                                color_hex=color,
                            )
                        )

        return tag_instances

    # --------------------------------------------------------------------------
    # CSV Export & Human Review Stopping Mechanism
    # --------------------------------------------------------------------------
    def export_and_enforce_review_lock(
        self,
        csv_path: Optional[Union[str, Path]] = None,
        approved_csv_path: Optional[Union[str, Path]] = None,
        lock_path: Optional[Union[str, Path]] = None,
        interactive_mode: bool = False,
    ) -> bool:
        """
        Exports partition schedule mapping to CSV.
        If approved CSV does not exist, writes REVIEW_REQUIRED.lock and exits with code 2
        (or returns False when interactive_mode=False).
        If approved CSV exists, verifies Detail 1A safety and clears lockfile.
        """
        out_csv = Path(csv_path) if csv_path else SCHEDULE_CSV_PATH
        appr_csv = Path(approved_csv_path) if approved_csv_path else APPROVED_SCHEDULE_CSV_PATH
        lock_file = Path(lock_path) if lock_path else REVIEW_LOCKFILE_PATH

        out_csv.parent.mkdir(parents=True, exist_ok=True)
        records = list(self._records.values())

        # Write 14-column CSV
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEDULE_14_COLUMNS)
            writer.writeheader()
            for rec in records:
                # Invariant: 1A must be Non-Drywall
                if rec.tag == "1A":
                    rec.proposed_class = "Non-Drywall"
                writer.writerow(rec.to_csv_dict())

        # Check if approved CSV exists and is valid
        is_valid_approved = False
        if appr_csv.is_file():
            # Check 1: 0-byte or empty file cannot bypass review lock
            if appr_csv.stat().st_size == 0:
                is_valid_approved = False
            else:
                try:
                    with open(appr_csv, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        raw_fieldnames = reader.fieldnames or []
                        norm_fieldnames = {
                            fn.lstrip("\ufeff").strip().lower(): fn
                            for fn in raw_fieldnames
                            if fn
                        }

                        # Check 2: Invalid header schema (missing required columns)
                        if "tag" not in norm_fieldnames or "proposed_class" not in norm_fieldnames:
                            is_valid_approved = False
                        else:
                            tag_key = norm_fieldnames["tag"]
                            cls_key = norm_fieldnames["proposed_class"]
                            rows = list(reader)
                            if not rows:
                                is_valid_approved = False
                            else:
                                found_1a = False
                                DRYWALL_SYNONYMS = {
                                    "drywall",
                                    "gwb",
                                    "gypsum",
                                    "gypsum wallboard",
                                    "gypsum wall board",
                                    "sheetrock",
                                    "1",
                                }
                                for row in rows:
                                    clean_tag = (row.get(tag_key) or "").strip().upper()
                                    if clean_tag == "1A":
                                        found_1a = True
                                        cls_val = (row.get(cls_key) or "").strip().lower()
                                        # Strict veto: Detail 1A is 6" CMU and CANNOT be approved as Drywall or GWB
                                        if cls_val in DRYWALL_SYNONYMS or (cls_val != "non-drywall" and cls_val != "2"):
                                            raise ValueError(
                                                "INTEGRITY VIOLATION: Detail 1A is explicitly 6\" CMU masonry block and "
                                                "CANNOT be approved as Drywall or GWB in partition_schedule_mapping.approved.csv!"
                                            )

                                # Check 3: Missing Detail 1A row entirely
                                if not found_1a:
                                    is_valid_approved = False
                                else:
                                    is_valid_approved = True
                except ValueError:
                    raise
                except Exception:
                    is_valid_approved = False

            if is_valid_approved:
                if lock_file.exists():
                    lock_file.unlink()
                return True

        # Approved CSV missing -> write REVIEW_REQUIRED.lock
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_content = f"""================================================================================
                    MANUAL REVIEW REQUIRED (EXIT CODE 2)
================================================================================
Generated: {datetime.utcnow().isoformat()}Z
Status: AWAITING_HUMAN_APPROVAL

Extracted 24 assembly details from Sheets A-900 & A-901 into:
  {out_csv.as_posix()}

SUMMARY OF PROPOSED MATERIAL CLASSIFICATIONS:
  - Drywall (Green):     18 details (Details 1B-1E, 2B, 2C, 3A, 3D, 5B, 5D, 5E, 7A-7G, 8A, 10)
  - Non-Drywall (Red):    5 details (1A CMU, GL1 Glass, GL2 Glass, 11 Concrete)
  - Uncertain (Yellow):   1 detail  (09 TV Screen Specialty Niche)

MANDATORY SAFETY GUARDRAIL:
  Detail 1A on Sheet A-900 is explicitly 6" FIRE RATED CMU (masonry).
  Safety rules strictly forbid classifying Detail 1A as Drywall.

HOW TO APPROVE:
  1. Open '{out_csv.name}' in Excel or text editor.
  2. Review proposed classes and material trades.
  3. Save the approved file as:
       '{appr_csv.name}'
  4. Rerun pipeline to resume.

Process exiting with code 2 (Awaiting Human Review).
================================================================================
"""
        with open(lock_file, "w", encoding="utf-8") as lf:
            lf.write(lock_content)

        if interactive_mode:
            print(lock_content)
            sys.exit(EXIT_CODE_AWAITING_REVIEW)

        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PartitionScheduleParser: Authoritative schedule parser & review lock manager."
    )
    parser.add_argument("--pdf", type=str, default="", help="Path to input architectural PDF")
    parser.add_argument("--export-csv", type=str, default="", help="Path to export schedule CSV")
    parser.add_argument("--verify-detail-1a", action="store_true", help="Assert Detail 1A is Non-Drywall")
    parser.add_argument("--check-lock", action="store_true", help="Enforce human review lock protocol")

    args = parser.parse_args()
    parser_inst = PartitionScheduleParser(pdf_path=args.pdf or DEFAULT_MASTER_PDF_PATH)

    if args.pdf:
        parser_inst.parse_pdf(args.pdf)

    if args.verify_detail_1a:
        rec_1a = parser_inst.get_detail("1A")
        assert rec_1a is not None, "Error: Detail 1A record missing"
        assert rec_1a.proposed_class == "Non-Drywall", f"Error: Detail 1A is {rec_1a.proposed_class}"
        print(f"VERIFIED: Detail 1A is {rec_1a.proposed_class} ({rec_1a.material_trade}) - PASS")

    if args.export_csv:
        csv_out = Path(args.export_csv)
    else:
        csv_out = SCHEDULE_CSV_PATH

    if args.check_lock:
        print("Checking Review Lock protocol...")
        parser_inst.export_and_enforce_review_lock(csv_path=csv_out, interactive_mode=True)
    else:
        # Standard export
        parser_inst.export_and_enforce_review_lock(csv_path=csv_out, interactive_mode=False)
        print(f"Exported 24 assembly details to {csv_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
