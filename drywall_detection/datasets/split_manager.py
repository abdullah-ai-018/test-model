"""
drywall_detection.datasets.split_manager
========================================
Drawing-level and project-level split integrity manager enforcing zero
leakage between train, validation, and test splits.
Implements:
- Greedy multi-way group partitioning
- Zero project/drawing overlap invariant enforcement
- Standalone verify_split_isolation validator
- Quarantine support for weakly pseudo-labeled drawings
- Cryptographic SHA-256 verification hash and JSON manifest exports
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import hashlib
import json
import logging
import os
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class SplitLeakageError(Exception):
    """Raised when data leakage or overlap is detected between dataset splits."""
    pass


class InsufficientGroupsError(Exception):
    """Raised when the dataset has too few projects/drawings to create valid isolated splits."""
    pass


class InvalidSplitRatioError(Exception):
    """Raised when split ratios do not sum to 1.0 or are out of bounds."""
    pass


@dataclass
class TileRecord:
    """Individual tile metadata record."""
    tile_id: str
    project_id: str
    drawing_id: str
    image_path: str
    mask_path: str
    bbox: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    has_walls: bool = True
    class_counts: Dict[str, int] = field(default_factory=dict)
    is_pseudo_label: bool = False
    quarantine: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SplitStats:
    """Statistical summary for a single split partition."""
    split_name: str
    total_projects: int
    total_drawings: int
    total_tiles: int
    wall_tiles_count: int
    empty_tiles_count: int
    class_pixel_counts: Dict[int, int] = field(default_factory=dict)
    class_pixel_percentages: Dict[str, float] = field(default_factory=dict)


@dataclass
class SplitManifest:
    """Complete dataset split bundle containing split lists and verification proofs."""
    split_ratios: Tuple[float, float, float]
    group_key: str
    seed: int
    train_tiles: List[TileRecord]
    val_tiles: List[TileRecord]
    test_tiles: List[TileRecord]
    quarantine_tiles: List[TileRecord] = field(default_factory=list)
    stats: Dict[str, SplitStats] = field(default_factory=dict)
    verification_hash: str = ""

    def get_split_tiles(self, split: str) -> List[TileRecord]:
        name = split.lower().strip()
        if name in ("train", "training"):
            return self.train_tiles
        elif name in ("val", "valid", "validation"):
            return self.val_tiles
        elif name in ("test", "testing"):
            return self.test_tiles
        elif name in ("quarantine", "quarantined"):
            return self.quarantine_tiles
        else:
            raise ValueError(f"Unknown split name: '{split}'. Valid: train, val, test, quarantine.")


def _canonical_path(p: Union[str, Path]) -> str:
    """Returns canonical case-folded absolute path string for cross-platform isolation checks."""
    return os.path.normcase(os.path.abspath(str(p)))


def verify_split_isolation(manifest: SplitManifest) -> Dict[str, Any]:
    """
    Exhaustively verifies zero-leakage invariants across train, val, and test,
    as well as strict quarantine isolation against evaluation splits (val/test).
    Raises SplitLeakageError immediately if any overlap or prohibited flag is discovered.
    """
    # 0. Flag invariants on evaluation splits (Val and Test must contain zero pseudo/quarantine tiles)
    for split_name, tiles in [("Val", manifest.val_tiles), ("Test", manifest.test_tiles)]:
        for t in tiles:
            is_quar = getattr(t, "quarantine", False)
            is_pseudo = getattr(t, "is_pseudo_label", False)
            if is_quar or is_pseudo:
                raise SplitLeakageError(
                    f"Quarantined or pseudo-labeled tile record leakage detected in {split_name} split! Tile ID: {t.tile_id}"
                )

    quar_list = manifest.quarantine_tiles or []

    train_proj = {t.project_id for t in manifest.train_tiles}
    val_proj = {t.project_id for t in manifest.val_tiles}
    test_proj = {t.project_id for t in manifest.test_tiles}
    quar_proj = {t.project_id for t in quar_list}

    train_draw = {t.drawing_id for t in manifest.train_tiles}
    val_draw = {t.drawing_id for t in manifest.val_tiles}
    test_draw = {t.drawing_id for t in manifest.test_tiles}
    quar_draw = {t.drawing_id for t in quar_list}

    train_tile_ids = {t.tile_id for t in manifest.train_tiles}
    val_tile_ids = {t.tile_id for t in manifest.val_tiles}
    test_tile_ids = {t.tile_id for t in manifest.test_tiles}
    quar_tile_ids = {t.tile_id for t in quar_list}

    train_img_paths = {_canonical_path(t.image_path) for t in manifest.train_tiles}
    val_img_paths = {_canonical_path(t.image_path) for t in manifest.val_tiles}
    test_img_paths = {_canonical_path(t.image_path) for t in manifest.test_tiles}
    quar_img_paths = {_canonical_path(t.image_path) for t in quar_list}

    train_msk_paths = {_canonical_path(t.mask_path) for t in manifest.train_tiles}
    val_msk_paths = {_canonical_path(t.mask_path) for t in manifest.val_tiles}
    test_msk_paths = {_canonical_path(t.mask_path) for t in manifest.test_tiles}
    quar_msk_paths = {_canonical_path(t.mask_path) for t in quar_list}

    # 1. Project overlap check (enforced when grouping by project_id)
    if manifest.group_key == "project_id":
        tv_proj = train_proj.intersection(val_proj)
        tt_proj = train_proj.intersection(test_proj)
        vt_proj = val_proj.intersection(test_proj)

        if tv_proj:
            raise SplitLeakageError(f"Train/Val project leakage detected: {tv_proj}")
        if tt_proj:
            raise SplitLeakageError(f"Train/Test project leakage detected: {tt_proj}")
        if vt_proj:
            raise SplitLeakageError(f"Val/Test project leakage detected: {vt_proj}")

    # 2. Drawing overlap check
    tv_draw = train_draw.intersection(val_draw)
    tt_draw = train_draw.intersection(test_draw)
    vt_draw = val_draw.intersection(test_draw)

    if tv_draw:
        raise SplitLeakageError(f"Train/Val drawing leakage detected: {tv_draw}")
    if tt_draw:
        raise SplitLeakageError(f"Train/Test drawing leakage detected: {tt_draw}")
    if vt_draw:
        raise SplitLeakageError(f"Val/Test drawing leakage detected: {vt_draw}")

    # 3. Path overlap check between standard splits
    tv_img = train_img_paths.intersection(val_img_paths)
    tt_img = train_img_paths.intersection(test_img_paths)
    vt_img = val_img_paths.intersection(test_img_paths)

    if tv_img or tt_img or vt_img:
        raise SplitLeakageError(f"Direct image file path overlap detected between splits: {tv_img or tt_img or vt_img}")

    tv_msk = train_msk_paths.intersection(val_msk_paths)
    tt_msk = train_msk_paths.intersection(test_msk_paths)
    vt_msk = val_msk_paths.intersection(test_msk_paths)

    if tv_msk or tt_msk or vt_msk:
        raise SplitLeakageError(f"Direct mask file path overlap detected between splits: {tv_msk or tt_msk or vt_msk}")

    # 4. Direct tile ID overlap check between standard splits
    tv_tile = train_tile_ids.intersection(val_tile_ids)
    tt_tile = train_tile_ids.intersection(test_tile_ids)
    vt_tile = val_tile_ids.intersection(test_tile_ids)

    if tv_tile or tt_tile or vt_tile:
        raise SplitLeakageError(f"Direct tile ID overlap detected between splits: {tv_tile or tt_tile or vt_tile}")

    # 5. Quarantine isolation against Val and Test evaluation splits
    qv_tile = quar_tile_ids.intersection(val_tile_ids)
    if qv_tile:
        raise SplitLeakageError(f"Quarantined tile ID leaked into Val split: {qv_tile}")
    qt_tile = quar_tile_ids.intersection(test_tile_ids)
    if qt_tile:
        raise SplitLeakageError(f"Quarantined tile ID leaked into Test split: {qt_tile}")

    qv_proj = quar_proj.intersection(val_proj)
    if qv_proj:
        raise SplitLeakageError(f"Quarantined project leaked into Val split: {qv_proj}")
    qt_proj = quar_proj.intersection(test_proj)
    if qt_proj:
        raise SplitLeakageError(f"Quarantined project leaked into Test split: {qt_proj}")

    qv_draw = quar_draw.intersection(val_draw)
    if qv_draw:
        raise SplitLeakageError(f"Quarantined drawing leaked into Val split: {qv_draw}")
    qt_draw = quar_draw.intersection(test_draw)
    if qt_draw:
        raise SplitLeakageError(f"Quarantined drawing leaked into Test split: {qt_draw}")

    qv_img = quar_img_paths.intersection(val_img_paths)
    if qv_img:
        raise SplitLeakageError(f"Quarantined image path overlap with Val split: {qv_img}")
    qt_img = quar_img_paths.intersection(test_img_paths)
    if qt_img:
        raise SplitLeakageError(f"Quarantined image path overlap with Test split: {qt_img}")

    qv_msk = quar_msk_paths.intersection(val_msk_paths)
    if qv_msk:
        raise SplitLeakageError(f"Quarantined mask path overlap with Val split: {qv_msk}")
    qt_msk = quar_msk_paths.intersection(test_msk_paths)
    if qt_msk:
        raise SplitLeakageError(f"Quarantined mask path overlap with Test split: {qt_msk}")

    report = {
        "status": "PASSED",
        "train_projects": len(train_proj),
        "val_projects": len(val_proj),
        "test_projects": len(test_proj),
        "quarantine_projects": len(quar_proj),
        "train_drawings": len(train_draw),
        "val_drawings": len(val_draw),
        "test_drawings": len(test_draw),
        "quarantine_drawings": len(quar_draw),
        "train_tiles": len(manifest.train_tiles),
        "val_tiles": len(manifest.val_tiles),
        "test_tiles": len(manifest.test_tiles),
        "quarantine_tiles": len(manifest.quarantine_tiles),
        "project_overlap_count": 0,
        "drawing_overlap_count": 0,
        "tile_overlap_count": 0,
        "quarantine_leakage_count": 0,
        "quarantine_val_overlap_count": 0,
        "quarantine_test_overlap_count": 0,
    }
    return report


class DrawingSplitManager:
    """
    Manages drawing-level and project-level partitioning of unified dataset tiles.
    Guarantees mathematically verified zero-leakage between train, val, and test.
    """

    def __init__(
        self,
        split_ratios: Tuple[float, float, float] = (0.70, 0.15, 0.15),
        group_key: str = "project_id",
        seed: int = 42,
        quarantine_projects: Optional[List[str]] = None,
        allow_drawing_fallback: bool = True,
    ) -> None:
        if abs(sum(split_ratios) - 1.0) > 1e-5:
            raise InvalidSplitRatioError(f"Split ratios {split_ratios} must sum to 1.0 (got {sum(split_ratios):.5f})")
        if any(r <= 0 for r in split_ratios):
            raise InvalidSplitRatioError(f"All split ratios must be > 0: {split_ratios}")

        self.split_ratios = split_ratios
        self.group_key = group_key
        self.seed = seed
        self.quarantine_projects: Set[str] = set(quarantine_projects or [])
        self.allow_drawing_fallback = allow_drawing_fallback

    def create_splits(self, tiles: List[Union[TileRecord, Dict[str, Any]]]) -> SplitManifest:
        """
        Executes greedy multi-way group partitioning on input tiles.
        Returns a verified SplitManifest with zero project/drawing leakage.
        """
        records: List[TileRecord] = []
        for t in tiles:
            if isinstance(t, TileRecord):
                records.append(t)
            else:
                bbox_raw = t.get("bbox", (0, 0, 512, 512))
                bbox = tuple(bbox_raw) if isinstance(bbox_raw, (list, tuple)) else (0, 0, 512, 512)
                records.append(
                    TileRecord(
                        tile_id=t["tile_id"],
                        project_id=t["project_id"],
                        drawing_id=t["drawing_id"],
                        image_path=str(t["image_path"]),
                        mask_path=str(t["mask_path"]),
                        bbox=bbox,  # type: ignore
                        has_walls=t.get("has_walls", True),
                        class_counts=t.get("class_counts", {}),
                        is_pseudo_label=t.get("is_pseudo_label", False),
                        quarantine=t.get("quarantine", False),
                    )
                )

        # 1. Separate quarantined tiles
        active_records: List[TileRecord] = []
        quarantine_records: List[TileRecord] = []

        for r in records:
            if r.quarantine or r.is_pseudo_label or (r.project_id in self.quarantine_projects):
                quarantine_records.append(r)
            else:
                active_records.append(r)

        # 2. Extract groups
        active_group_key = self.group_key
        groups: Dict[str, List[TileRecord]] = {}
        for r in active_records:
            k = getattr(r, active_group_key)
            groups.setdefault(k, []).append(r)

        if len(groups) < 3:
            if active_group_key == "project_id" and self.allow_drawing_fallback:
                logger.warning(
                    f"Only {len(groups)} projects detected. Falling back to 'drawing_id' grouping."
                )
                active_group_key = "drawing_id"
                groups = {}
                for r in active_records:
                    groups.setdefault(r.drawing_id, []).append(r)
                if len(groups) < 3:
                    raise InsufficientGroupsError(
                        f"Insufficient groups ({len(groups)}) even after drawing fallback. Minimum 3 required."
                    )
            else:
                raise InsufficientGroupsError(
                    f"Insufficient groups ({len(groups)}) for 3-way split with group_key='{active_group_key}'."
                )

        # 3. Greedy multi-way partitioning
        # Sort groups descending by tile weight
        rng = random.Random(self.seed)
        group_items = list(groups.items())
        # Shuffle with seed for deterministic tie-breaking
        rng.shuffle(group_items)
        # Re-sort descending by tile count (stable sort)
        group_items.sort(key=lambda kv: len(kv[1]), reverse=True)

        total_tiles = sum(len(tiles_in_group) for _, tiles_in_group in group_items)
        target_counts = [r * total_tiles for r in self.split_ratios]

        split_bins: Tuple[List[TileRecord], List[TileRecord], List[TileRecord]] = ([], [], [])
        split_counts = [0, 0, 0]

        for group_id, group_tiles in group_items:
            # Choose bin with largest relative shortfall: (target - current) / ratio
            shortfalls = [
                (target_counts[i] - split_counts[i]) / self.split_ratios[i]
                for i in range(3)
            ]
            best_idx = int(shortfalls.index(max(shortfalls)))
            split_bins[best_idx].extend(group_tiles)
            split_counts[best_idx] += len(group_tiles)

        manifest = SplitManifest(
            split_ratios=self.split_ratios,
            group_key=active_group_key,
            seed=self.seed,
            train_tiles=split_bins[0],
            val_tiles=split_bins[1],
            test_tiles=split_bins[2],
            quarantine_tiles=quarantine_records,
            stats=self._compute_all_stats(split_bins, quarantine_records),
        )

        # 4. Mandatory zero-leakage verification
        verify_split_isolation(manifest)

        # 5. Compute cryptographic verification hash
        manifest.verification_hash = self._compute_manifest_hash(manifest)
        return manifest

    def verify_split_isolation(self, manifest: SplitManifest) -> Dict[str, Any]:
        """Convenience method delegating to standalone verify_split_isolation."""
        return verify_split_isolation(manifest)

    def export_split_manifests(
        self,
        manifest: SplitManifest,
        output_dir: Union[str, Path],
    ) -> Dict[str, Path]:
        """
        Exports train.json, val.json, test.json, and splits_summary.json.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        files: Dict[str, Path] = {}
        for name in ["train", "val", "test", "quarantine"]:
            tiles = manifest.get_split_tiles(name)
            split_file = out_path / f"{name}.json"
            data = {
                "split_name": name,
                "version": "1.0",
                "count": len(tiles),
                "tiles": [t.to_dict() for t in tiles],
            }
            with open(split_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            files[name] = split_file

        summary_file = out_path / "splits_summary.json"
        summary_data = {
            "version": "1.0",
            "seed": manifest.seed,
            "group_key": manifest.group_key,
            "split_ratios": manifest.split_ratios,
            "verification_hash": manifest.verification_hash,
            "isolation_status": "VERIFIED_ZERO_LEAKAGE",
            "stats": {k: asdict(v) for k, v in manifest.stats.items()},
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        files["summary"] = summary_file

        return files

    def _compute_manifest_hash(self, manifest: SplitManifest) -> str:
        """Computes deterministic SHA-256 fingerprint over all tile IDs and splits."""
        hasher = hashlib.sha256()
        for name in ["train", "val", "test"]:
            tiles = sorted(t.tile_id for t in manifest.get_split_tiles(name))
            hasher.update(f"[{name}:{','.join(tiles)}]".encode("utf-8"))
        return hasher.hexdigest()

    def _compute_all_stats(
        self,
        split_bins: Tuple[List[TileRecord], List[TileRecord], List[TileRecord]],
        quarantine_records: List[TileRecord],
    ) -> Dict[str, SplitStats]:
        names = ["train", "val", "test"]
        stats_map: Dict[str, SplitStats] = {}
        for name, tiles in zip(names, split_bins):
            projects = {t.project_id for t in tiles}
            drawings = {t.drawing_id for t in tiles}
            wall_tiles = sum(1 for t in tiles if t.has_walls)
            stats_map[name] = SplitStats(
                split_name=name,
                total_projects=len(projects),
                total_drawings=len(drawings),
                total_tiles=len(tiles),
                wall_tiles_count=wall_tiles,
                empty_tiles_count=len(tiles) - wall_tiles,
            )
        if quarantine_records:
            stats_map["quarantine"] = SplitStats(
                split_name="quarantine",
                total_projects=len({t.project_id for t in quarantine_records}),
                total_drawings=len({t.drawing_id for t in quarantine_records}),
                total_tiles=len(quarantine_records),
                wall_tiles_count=sum(1 for t in quarantine_records if t.has_walls),
                empty_tiles_count=len(quarantine_records) - sum(1 for t in quarantine_records if t.has_walls),
            )
        return stats_map
