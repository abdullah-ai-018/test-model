"""
drywall_detection.data.splitter
==============================
Project-isolated data partitioning module for architectural drawings and tiles.
Enforces strict project/building isolation with zero data leakage across splits.

Invariants:
- Projects(train) ∩ Projects(val) == ∅
- Projects(train) ∩ Projects(test) == ∅
- Projects(val) ∩ Projects(test) == ∅
- Drawings(train) ∩ Drawings(val) == ∅
- Drawings(train) ∩ Drawings(test) == ∅
- Drawings(val) ∩ Drawings(test) == ∅
- Quarantined / pseudo-labeled drawings are strictly segregated from val and test.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field, asdict
import hashlib
import json
import logging
from pathlib import Path
import random
import sys
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
class SampleRecord:
    """Canonical metadata for a single image/mask sample (tile or full drawing)."""
    sample_id: str
    project_id: str
    drawing_id: str
    image_path: str
    mask_path: str
    bbox: Tuple[int, int, int, int] = (0, 0, 512, 512)
    width: int = 512
    height: int = 512
    has_walls: bool = True
    wall_pixel_count: int = 0
    total_pixel_count: int = 262144
    class_counts: Dict[str, int] = field(default_factory=dict)
    is_pseudo_label: bool = False
    quarantine: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SampleRecord:
        # Resolve project identifier across naming variations
        proj_id = (
            data.get("project_id")
            or data.get("site_id")
            or data.get("building_id")
            or data.get("parent_project_id")
            or "unknown_project"
        )
        draw_id = data.get("drawing_id") or data.get("parent_drawing_id") or proj_id
        sample_id = data.get("sample_id") or data.get("tile_id") or f"{draw_id}_sample"

        mask_p = str(data.get("mask_path") or data.get("multiclass_mask_path") or data.get("binary_mask_path") or "")
        img_p = str(data.get("image_path") or "")

        bbox_raw = data.get("bbox", (0, 0, 512, 512))
        bbox = tuple(bbox_raw) if isinstance(bbox_raw, (list, tuple)) else (0, 0, 512, 512)

        has_walls_val = data.get("has_walls")
        if has_walls_val is None:
            has_walls = int(data.get("wall_pixel_count", 0)) > 0
        else:
            has_walls = bool(has_walls_val)

        return cls(
            sample_id=str(sample_id),
            project_id=str(proj_id),
            drawing_id=str(draw_id),
            image_path=img_p,
            mask_path=mask_p,
            bbox=bbox,  # type: ignore
            width=int(data.get("width", 512)),
            height=int(data.get("height", 512)),
            has_walls=has_walls,
            wall_pixel_count=int(data.get("wall_pixel_count", 0)),
            total_pixel_count=int(data.get("total_pixel_count", 512 * 512)),
            class_counts=data.get("class_counts", {}),
            is_pseudo_label=bool(data.get("is_pseudo_label", False)),
            quarantine=bool(data.get("quarantine", False)),
        )


@dataclass
class SplitPartitionStats:
    """Summary statistics for an isolated split partition."""
    split_name: str
    total_projects: int
    total_drawings: int
    total_samples: int
    wall_samples_count: int
    empty_samples_count: int
    wall_pixel_percentage: float = 0.0
    projects_list: List[str] = field(default_factory=list)


@dataclass
class SplitManifestBundle:
    """Complete bundle of partitioned dataset splits and verification proofs."""
    train_samples: List[SampleRecord] = field(default_factory=list)
    val_samples: List[SampleRecord] = field(default_factory=list)
    test_samples: List[SampleRecord] = field(default_factory=list)
    split_ratios: Tuple[float, float, float] = (0.70, 0.15, 0.15)
    group_key: str = "project_id"
    seed: int = 42
    quarantine_samples: List[SampleRecord] = field(default_factory=list)
    stats: Dict[str, SplitPartitionStats] = field(default_factory=dict)
    verification_hash: str = ""

    def get_split(self, name: str) -> List[SampleRecord]:
        s = name.lower().strip()
        if s in ("train", "training"):
            return self.train_samples
        elif s in ("val", "valid", "validation"):
            return self.val_samples
        elif s in ("test", "testing"):
            return self.test_samples
        elif s in ("quarantine", "quarantined"):
            return self.quarantine_samples
        else:
            raise ValueError(f"Unknown split name: '{name}'. Choose from train, val, test, quarantine.")


def assert_zero_leakage(
    bundle: SplitManifestBundle,
    case_sensitive: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Exhaustively verifies zero-leakage invariants across train, val, and test.
    Raises SplitLeakageError immediately if any overlap is discovered.
    """
    if case_sensitive:
        train_projs = {s.project_id for s in bundle.train_samples if s.project_id}
        val_projs = {s.project_id for s in bundle.val_samples if s.project_id}
        test_projs = {s.project_id for s in bundle.test_samples if s.project_id}

        train_draws = {s.drawing_id for s in bundle.train_samples if s.drawing_id}
        val_draws = {s.drawing_id for s in bundle.val_samples if s.drawing_id}
        test_draws = {s.drawing_id for s in bundle.test_samples if s.drawing_id}
    else:
        train_projs = {s.project_id.strip().lower() for s in bundle.train_samples if s.project_id}
        val_projs = {s.project_id.strip().lower() for s in bundle.val_samples if s.project_id}
        test_projs = {s.project_id.strip().lower() for s in bundle.test_samples if s.project_id}

        train_draws = {s.drawing_id.strip().lower() for s in bundle.train_samples if s.drawing_id}
        val_draws = {s.drawing_id.strip().lower() for s in bundle.val_samples if s.drawing_id}
        test_draws = {s.drawing_id.strip().lower() for s in bundle.test_samples if s.drawing_id}

    train_images = {str(Path(s.image_path).resolve()) for s in bundle.train_samples if s.image_path}
    val_images = {str(Path(s.image_path).resolve()) for s in bundle.val_samples if s.image_path}
    test_images = {str(Path(s.image_path).resolve()) for s in bundle.test_samples if s.image_path}

    train_masks = {str(Path(s.mask_path).resolve()) for s in bundle.train_samples if s.mask_path}
    val_masks = {str(Path(s.mask_path).resolve()) for s in bundle.val_samples if s.mask_path}
    test_masks = {str(Path(s.mask_path).resolve()) for s in bundle.test_samples if s.mask_path}

    # 1. Project overlap check
    tv_proj = train_projs & val_projs
    tt_proj = train_projs & test_projs
    vt_proj = val_projs & test_projs

    if tv_proj:
        raise SplitLeakageError(f"Train/Val project leakage detected: {tv_proj}")
    if tt_proj:
        raise SplitLeakageError(f"Train/Test project leakage detected: {tt_proj}")
    if vt_proj:
        raise SplitLeakageError(f"Val/Test project leakage detected: {vt_proj}")

    # 2. Drawing overlap check
    tv_draw = train_draws & val_draws
    tt_draw = train_draws & test_draws
    vt_draw = val_draws & test_draws

    if tv_draw:
        raise SplitLeakageError(f"Train/Val drawing leakage detected: {tv_draw}")
    if tt_draw:
        raise SplitLeakageError(f"Train/Test drawing leakage detected: {tt_draw}")
    if vt_draw:
        raise SplitLeakageError(f"Val/Test drawing leakage detected: {vt_draw}")

    # 3. Path overlap check
    if (train_images & val_images) or (train_images & test_images) or (val_images & test_images):
        overlap = (train_images & val_images) | (train_images & test_images) | (val_images & test_images)
        raise SplitLeakageError(f"Direct image file path overlap detected between splits: {overlap}")

    if (train_masks & val_masks) or (train_masks & test_masks) or (val_masks & test_masks):
        overlap = (train_masks & val_masks) | (train_masks & test_masks) | (val_masks & test_masks)
        raise SplitLeakageError(f"Direct mask file path overlap detected between splits: {overlap}")

    # 4. Quarantine leakage check
    quarantine_projs = {s.project_id.strip().lower() for s in bundle.quarantine_samples if s.project_id}
    if quarantine_projs & val_projs:
        raise SplitLeakageError(f"Quarantined project leaked into validation split: {quarantine_projs & val_projs}")
    if quarantine_projs & test_projs:
        raise SplitLeakageError(f"Quarantined project leaked into test split: {quarantine_projs & test_projs}")

    return {
        "isolation_status": "VERIFIED_ZERO_LEAKAGE",
        "train_projects": len(train_projs),
        "val_projects": len(val_projs),
        "test_projects": len(test_projs),
        "train_samples": len(bundle.train_samples),
        "val_samples": len(bundle.val_samples),
        "test_samples": len(bundle.test_samples),
        "quarantine_samples": len(bundle.quarantine_samples),
    }


class ProjectDataSplitter:
    """
    Splits dataset samples by project/building ID with mathematical zero leakage.
    Supports site_id, building_id, and project_id group keys.
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

    def split(self, samples: List[Union[SampleRecord, Dict[str, Any]]]) -> SplitManifestBundle:
        """Executes multi-way greedy group partitioning and returns SplitManifestBundle."""
        records: List[SampleRecord] = [
            s if isinstance(s, SampleRecord) else SampleRecord.from_dict(s)
            for s in samples
        ]

        # 1. Segregate quarantined records
        active: List[SampleRecord] = []
        quarantine: List[SampleRecord] = []

        for r in records:
            if r.quarantine or r.is_pseudo_label or (r.project_id in self.quarantine_projects):
                quarantine.append(r)
            else:
                active.append(r)

        # 2. Group by group_key
        active_key = self.group_key
        groups: Dict[str, List[SampleRecord]] = {}
        for r in active:
            k = getattr(r, active_key, None) or r.project_id
            groups.setdefault(k, []).append(r)

        if len(groups) < 3:
            if (active_key == "project_id" or active_key == "site_id") and self.allow_drawing_fallback:
                logger.warning(f"Only {len(groups)} projects detected. Falling back to drawing_id grouping.")
                active_key = "drawing_id"
                groups = {}
                for r in active:
                    groups.setdefault(r.drawing_id, []).append(r)
                if len(groups) < 3:
                    raise InsufficientGroupsError(
                        f"Insufficient groups ({len(groups)}) even after drawing fallback. Minimum 3 required."
                    )
            else:
                raise InsufficientGroupsError(
                    f"Insufficient groups ({len(groups)}) for 3-way split with group_key='{active_key}'."
                )

        # 3. Greedy multi-way partitioning
        rng = random.Random(self.seed)
        group_items = list(groups.items())
        rng.shuffle(group_items)
        group_items.sort(key=lambda kv: len(kv[1]), reverse=True)

        total_weight = sum(len(g_samples) for _, g_samples in group_items)
        targets = [r * total_weight for r in self.split_ratios]

        bins: Tuple[List[SampleRecord], List[SampleRecord], List[SampleRecord]] = ([], [], [])
        counts = [0, 0, 0]

        for _, g_samples in group_items:
            shortfalls = [(targets[i] - counts[i]) / self.split_ratios[i] for i in range(3)]
            best_idx = int(shortfalls.index(max(shortfalls)))
            bins[best_idx].extend(g_samples)
            counts[best_idx] += len(g_samples)

        # Compute stats per split
        stats_map = self._compute_stats(bins, quarantine)

        bundle = SplitManifestBundle(
            split_ratios=self.split_ratios,
            group_key=active_key,
            seed=self.seed,
            train_samples=bins[0],
            val_samples=bins[1],
            test_samples=bins[2],
            quarantine_samples=quarantine,
            stats=stats_map,
        )

        # 4. Mandatory assertion of zero leakage
        assert_zero_leakage(bundle)

        # 5. Compute deterministic hash
        bundle.verification_hash = self._compute_manifest_hash(bundle)
        return bundle

    def export_manifests(
        self,
        bundle: SplitManifestBundle,
        output_dir: Union[str, Path],
    ) -> Dict[str, Path]:
        """
        Exports train.json, val.json, test.json, and splits_summary.json.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        exported: Dict[str, Path] = {}
        for name in ["train", "val", "test", "quarantine"]:
            split_samples = bundle.get_split(name)
            split_file = out / f"{name}.json"
            projects_in_split = sorted(list({s.project_id for s in split_samples}))
            drawings_in_split = sorted(list({s.drawing_id for s in split_samples}))

            payload = {
                "split_name": name,
                "version": "1.0",
                "count": len(split_samples),
                "total_projects": len(projects_in_split),
                "total_drawings": len(drawings_in_split),
                "projects": projects_in_split,
                "drawings": drawings_in_split,
                "samples": [s.to_dict() for s in split_samples],
            }
            with open(split_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            exported[name] = split_file

        summary_file = out / "splits_summary.json"
        summary_payload = {
            "version": "1.0",
            "seed": bundle.seed,
            "group_key": bundle.group_key,
            "split_ratios": bundle.split_ratios,
            "verification_hash": bundle.verification_hash,
            "isolation_status": "VERIFIED_ZERO_LEAKAGE",
            "total_samples": len(bundle.train_samples) + len(bundle.val_samples) + len(bundle.test_samples),
            "stats": {k: asdict(v) for k, v in bundle.stats.items()},
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)
        exported["summary"] = summary_file

        return exported

    def _compute_manifest_hash(self, bundle: SplitManifestBundle) -> str:
        hasher = hashlib.sha256()
        for name in ["train", "val", "test"]:
            ids = sorted(s.sample_id for s in bundle.get_split(name))
            hasher.update(f"[{name}:{','.join(ids)}]".encode("utf-8"))
        return hasher.hexdigest()

    def _compute_stats(
        self,
        bins: Tuple[List[SampleRecord], List[SampleRecord], List[SampleRecord]],
        quarantine: List[SampleRecord],
    ) -> Dict[str, SplitPartitionStats]:
        names = ["train", "val", "test"]
        stats = {}
        for name, samples in zip(names, bins):
            projs = sorted(list({s.project_id for s in samples}))
            draws = sorted(list({s.drawing_id for s in samples}))
            wall_cnt = sum(1 for s in samples if s.has_walls)
            tot_pix = sum(s.total_pixel_count for s in samples) or 1
            wall_pix = sum(s.wall_pixel_count for s in samples)
            stats[name] = SplitPartitionStats(
                split_name=name,
                total_projects=len(projs),
                total_drawings=len(draws),
                total_samples=len(samples),
                wall_samples_count=wall_cnt,
                empty_samples_count=len(samples) - wall_cnt,
                wall_pixel_percentage=round((wall_pix / tot_pix) * 100.0, 3),
                projects_list=projs,
            )
        if quarantine:
            q_projs = sorted(list({s.project_id for s in quarantine}))
            q_draws = sorted(list({s.drawing_id for s in quarantine}))
            q_wall = sum(1 for s in quarantine if s.has_walls)
            tot_pix = sum(s.total_pixel_count for s in quarantine) or 1
            wall_pix = sum(s.wall_pixel_count for s in quarantine)
            stats["quarantine"] = SplitPartitionStats(
                split_name="quarantine",
                total_projects=len(q_projs),
                total_drawings=len(q_draws),
                total_samples=len(quarantine),
                wall_samples_count=q_wall,
                empty_samples_count=len(quarantine) - q_wall,
                wall_pixel_percentage=round((wall_pix / tot_pix) * 100.0, 3),
                projects_list=q_projs,
            )
        return stats


def main(args: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Drywall Detection Project-Isolated Data Splitter")
    parser.add_argument("--input", type=str, required=True, help="Path to processed dataset metadata JSON or directory")
    parser.add_argument("--output", type=str, default="drywall_detection/data/splits", help="Output directory for manifests")
    parser.add_argument("--group-key", type=str, default="site_id", choices=["project_id", "site_id", "building_id", "drawing_id"])
    parser.add_argument("--ratios", type=float, nargs=3, default=[0.70, 0.15, 0.15], help="Split ratios: train val test")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--quarantine", type=str, nargs="*", default=["99th_street"], help="Projects to quarantine from val/test")
    parsed = parser.parse_args(args)

    input_path = Path(parsed.input)
    if input_path.is_file():
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            samples = data
        else:
            samples = data.get("samples") or data.get("tiles") or data.get("drawings") or []
    elif input_path.is_dir():
        cand = input_path / "dataset_manifest.json"
        if not cand.is_file():
            cand = input_path / "metadata.json"
        if cand.is_file():
            with open(cand, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                samples = data
            else:
                samples = data.get("samples") or data.get("tiles") or data.get("drawings") or []
        else:
            raise FileNotFoundError(f"No dataset_manifest.json or metadata.json found in directory: {input_path}")
    else:
        raise FileNotFoundError(f"Input path not found: {input_path}")

    splitter = ProjectDataSplitter(
        split_ratios=tuple(parsed.ratios),  # type: ignore
        group_key=parsed.group_key,
        seed=parsed.seed,
        quarantine_projects=parsed.quarantine,
    )
    bundle = splitter.split(samples)
    exported = splitter.export_manifests(bundle, parsed.output)
    print(f"Split manifests exported successfully to {parsed.output}:")
    for k, p in exported.items():
        print(f"  [{k}] -> {p}")
    return 0


__all__ = [
    "SampleRecord",
    "SplitPartitionStats",
    "SplitManifestBundle",
    "ProjectDataSplitter",
    "SplitLeakageError",
    "InsufficientGroupsError",
    "InvalidSplitRatioError",
    "assert_zero_leakage",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
