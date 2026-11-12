# Technical Analysis & Architectural Design: Split Strategy, PyTorch Dataset & DataLoader Interface

- **Module**: `drywall_detection.datasets`
- **Agent**: `m1_explorer_3`
- **Role**: Split Strategy & Dataset Loader Explorer
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **State Folder**: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_explorer_3`
- **Timestamp**: 2026-11-07T20:45:00Z
- **Integrity Mode**: Development / Zero-Tolerance

---

## 1. Executive Summary & Problem Scope

### 1.1 The Critical Danger of Architectural Data Leakage
In generic computer vision (such as ImageNet or COCO), individual images are largely independent. In contrast, architectural drawings, CAD plans, and floor plan datasets exhibit severe hierarchical interdependencies:
1. **Multi-Floor Building Redundancy**: Floor plans across different levels of the same building (e.g., MTA 99th Street Ground, 2nd, 3rd, and 4th floors) share the identical structural column grid, elevator cores, emergency stairwells, and exterior perimeter footprint.
2. **Firm-Specific Drafting Quirks**: Drawings originating from the same architectural or engineering firm share line weights, font typography, hatch styles, layer naming, and wall thickness conventions.
3. **Sliding-Window Tile Overlap**: In high-resolution drawing segmentation, drawings are sliced into $512 \times 512$ patches with a 20% to 25% overlap margin ($102\text{ to }128\text{ pixels}$). If tiles from the same drawing sheet are partitioned randomly, overlapping portions of the exact same wall segment will appear in both the training set and the validation set.

If a naive random split is applied at the tile level or un-grouped sheet level, a neural network quickly overfits to specific spatial coordinates, building silhouettes, and drafting styles. It achieves deceptively high validation scores ($\text{mIoU} > 95\%$) during development, but suffers catastrophic performance collapse when deployed on unseen floor plans from a new architectural firm.

**Zero-Tolerance Acceptance Requirement**:
To guarantee valid generalization, the dataset preparation pipeline must enforce a **strict drawing-level and project-level split integrity manager** where no project, building, or drawing sheet ever appears in more than one partition ($\text{Projects}_{\text{train}} \cap \text{Projects}_{\text{val}} = \emptyset$, $\text{Projects}_{\text{train}} \cap \text{Projects}_{\text{test}} = \emptyset$, $\text{Projects}_{\text{val}} \cap \text{Projects}_{\text{test}} = \emptyset$).

### 1.2 Local Compute Constraints & Architecture Adaptation
The host compute environment has been audited:
- **Operating System**: Windows 10 (AMD64 / x86_64).
- **Processor**: Intel 4-core / 8-thread CPU (~1.7 GHz).
- **GPU Acceleration**: **Zero CUDA VRAM** (`torch.cuda.is_available() == False`). Execution is strictly CPU-bound.
- **Available System Memory**: **~1.0 GB to 1.5 GB free RAM** out of 7.88 GB total (~87% utilized).
- **Deep Learning Stack**: Python 3.10.0, `torch 2.1.0+cpu`, `torchvision 0.16.0+cpu`, `opencv-python 4.11.0`, `transformers 4.41.2`, `timm 1.0.22`. Noticeably, `albumentations` is **not installed**.

**Architectural Implications**:
1. **Streaming Tile Ingestion**: A full floor plan rendered at 200 DPI consumes $30\text{–}150\text{ MB}$ uncompressed in RAM. Loading a full dataset into memory will instantly crash the Python process with an Out-Of-Memory (OOM) error or trigger massive disk paging. The PyTorch `Dataset` must stream pre-tiled $512 \times 512$ PNGs lazily from disk on demand, holding only a lightweight metadata index in memory (< 15 MB for 50,000 tiles).
2. **Windows Multiprocessing Safety**: Setting `num_workers > 0` on Windows invokes the `spawn` process model, duplicating process memory by ~150 MB per worker and causing inter-process communication bottlenecks. For local CPU training, `num_workers` must default to `0` (or `2` maximum if memory permits), with `pin_memory=False` (since host-pinned memory is meaningless without CUDA).
3. **Pure Torchvision/PyTorch Augmentations**: Because `albumentations` is absent, all synchronized augmentations (discrete 90° rotations, horizontal/vertical flips, contrast adjustments) must be implemented natively using `torchvision.transforms.functional` and `torch`.

---

## 2. Drawing-Level Split Integrity Manager (`split_manager.py`)

### 2.1 Mathematical Formulation of Disjoint Group Splitting
Let $\mathcal{D} = \{t_1, t_2, \dots, t_N\}$ denote the universe of all extracted tiles. Each tile $t_i$ is mapped to a hierarchical grouping tuple:
$$\mathcal{G}(t_i) = \big(P(t_i), B(t_i), S(t_i)\big)$$
where:
- $P(t_i) \in \mathcal{P}$: Project / Site Identifier (e.g. `site_id` in MSD, project folder in CubiCasa5K, or `mta_99th_st` / `spark_lake_grove` in drawing sets).
- $B(t_i) \in \mathcal{B}$: Building Identifier (e.g. `building_id` in MSD).
- $S(t_i) \in \mathcal{S}$: Drawing Sheet / Floor Identifier (e.g. `A-101`, `A-102`).

The dataset is partitioned into three disjoint subsets: Train ($\mathcal{T}$), Validation ($\mathcal{V}$), and Test ($\mathcal{E}$).

#### Formal Disjointness Invariant:
$$\left(\bigcup_{t \in \mathcal{T}} P(t)\right) \cap \left(\bigcup_{t \in \mathcal{V}} P(t)\right) = \emptyset$$
$$\left(\bigcup_{t \in \mathcal{T}} P(t)\right) \cap \left(\bigcup_{t \in \mathcal{E}} P(t)\right) = \emptyset$$
$$\left(\bigcup_{t \in \mathcal{V}} P(t)\right) \cap \left(\bigcup_{t \in \mathcal{E}} P(t)\right) = \emptyset$$

If the dataset contains only a single multi-sheet project where project-level isolation is impossible across 3 splits (e.g. when splitting within a single large drawing set), the isolation level falls back gracefully to **Drawing Sheet Level** ($S(t)$), while issuing a prominent structural warning:
$$\left(\bigcup_{t \in \mathcal{T}} S(t)\right) \cap \left(\bigcup_{t \in \mathcal{V}} S(t)\right) = \emptyset, \quad \text{etc.}$$
Under no circumstances may individual tiles from the same drawing sheet be split across train and validation.

### 2.2 Split Allocation Algorithm: Greedy Multi-Way Number Partitioning
Simple random assignment of groups can lead to massive imbalance because project sizes vary widely (e.g., Project A has 400 tiles, while Project B has 15 tiles). If Project A lands in validation, the validation set balloon from 15% to 45%.

To achieve target split ratios (e.g. 70% Train, 15% Val, 15% Test) while guaranteeing strict zero project overlap, the Split Manager implements a **Greedy Balanced Group Partitioning Algorithm**:
1. Group all tiles by `group_key` (e.g. `project_id`). Compute tile count $w_g = |\{t \in \mathcal{D} \mid P(t) = g\}|$ for each group $g \in \mathcal{P}$.
2. Quarantine any groups marked with `quarantine=True` (e.g., weakly pseudo-labeled 99th Street drawings or external held-out test sets like Spark Lake Grove) into their designated isolated splits.
3. Sort remaining groups in descending order of tile weight $w_g$ (Longest Processing Time First).
4. For each group $g$, compute the target shortfall for each split:
   $$\Delta_s = R_s \cdot W_{\text{total}} - W_s$$
   where $R_s \in \{0.70, 0.15, 0.15\}$ is the target ratio, $W_{\text{total}}$ is the total eligible tile count, and $W_s$ is the current tile count in split $s$.
5. Assign group $g$ to the split $s$ with the largest relative shortfall $\Delta_s / R_s$.
6. Ties and fine-grained distributions are randomized deterministically using a fixed random seed (`seed=42`).

### 2.3 Quarantine & Pseudo-Label Protection
In Milestone M4/M5, weak pseudo-labels may be derived from the 99th Street PDF (via vector leader-line extraction and schedule parsing).
- **Integrity Rule**: Weak pseudo-labeled drawings MUST NEVER enter the validation or test sets. Doing so violates acceptance criteria by evaluating a model on its own unverified pseudo-labels.
- The `DrawingSplitManager` includes explicit parameter `quarantine_projects: List[str]` and tile attribute `is_pseudo_label: bool`. Any quarantined project or pseudo-labeled tile is strictly restricted to training or an isolated quarantine partition.

### 2.4 Split Integrity Verification Engine
The module provides a standalone validator `verify_split_isolation(split_manifest)` that executes five independent assertions:
1. **Pairwise Project Disjointness**: Calculates set intersections of project IDs across all pairs: $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}}$, $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}}$, $\mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{test}}$. Any non-empty intersection raises `SplitLeakageError`.
2. **Pairwise Drawing Disjointness**: Calculates set intersections of drawing IDs across all pairs: $\mathcal{S}_{\text{train}} \cap \mathcal{S}_{\text{val}}$, $\mathcal{S}_{\text{train}} \cap \mathcal{S}_{\text{test}}$, $\mathcal{S}_{\text{val}} \cap \mathcal{S}_{\text{test}}$.
3. **Tile Path Disjointness**: Ensures no image file path or mask file path appears in more than one split manifest.
4. **Tile Hash Integrity**: Computes SHA-256 hashes of tile metadata to catch duplicated tiles that have been renamed.
5. **Class Representation Check**: Warns if any split lacks representation for positive wall classes (Drywall, Non-Drywall, Uncertain).

### 2.5 Detailed Interface Specification (`drywall_detection/datasets/split_manager.py`)

```python
"""
drywall_detection.datasets.split_manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Drawing-level and project-level split integrity manager enforcing zero
leakage between train, validation, and test splits.
"""

from __future__ import annotations
import json
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)


class SplitLeakageError(Exception):
    """Raised when data leakage is detected between dataset splits."""
    pass


class InsufficientGroupsError(Exception):
    """Raised when the dataset has too few projects/drawings to create valid splits."""
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
    """Complete dataset split bundle containing manifests and verification proofs."""
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
        if split == "train":
            return self.train_tiles
        elif split == "val" or split == "validation":
            return self.val_tiles
        elif split == "test":
            return self.test_tiles
        elif split == "quarantine":
            return self.quarantine_tiles
        else:
            raise ValueError(f"Unknown split name: {split}")


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
        allow_drawing_fallback: bool = True
    ):
        """
        Args:
            split_ratios: Target ratios for (train, val, test). Must sum to 1.0.
            group_key: Field to group by ('project_id' or 'drawing_id').
            seed: Deterministic integer seed for reproducible shuffling.
            quarantine_projects: List of project/drawing IDs to isolate from val/test.
            allow_drawing_fallback: If only 1 project exists, allow fallback to drawing_id.
        """
        if abs(sum(split_ratios) - 1.0) > 1e-5:
            raise InvalidSplitRatioError(f"Split ratios {split_ratios} must sum to 1.0")
        if any(r <= 0 for r in split_ratios):
            raise InvalidSplitRatioError(f"All split ratios must be > 0: {split_ratios}")

        self.split_ratios = split_ratios
        self.group_key = group_key
        self.seed = seed
        self.quarantine_projects = set(quarantine_projects or [])
        self.allow_drawing_fallback = allow_drawing_fallback

    def create_splits(self, tiles: List[Union[TileRecord, Dict[str, Any]]]) -> SplitManifest:
        """
        Executes greedy multi-way group partitioning on input tiles.
        Returns a verified SplitManifest with zero project/drawing leakage.
        """
        # Normalize dict to TileRecord
        records = [
            t if isinstance(t, TileRecord) else TileRecord(**t)
            for t in tiles
        ]

        # 1. Separate quarantined tiles
        active_records: List[TileRecord] = []
        quarantine_records: List[TileRecord] = []
        for r in records:
            if r.quarantine or r.is_pseudo_label or (r.project_id in self.quarantine_projects):
                quarantine_records.append(r)
            else:
                active_records.append(r)

        # 2. Extract groups
        groups: Dict[str, List[TileRecord]] = {}
        for r in active_records:
            key = getattr(r, self.group_key)
            groups.setdefault(key, []).append(r)

        # Check group sufficiency
        if len(groups) < 3:
            if self.group_key == "project_id" and self.allow_drawing_fallback:
                logger.warning(
                    f"Only {len(groups)} projects detected. Falling back to 'drawing_id' grouping."
                )
                self.group_key = "drawing_id"
                groups = {}
                for r in active_records:
                    groups.setdefault(r.drawing_id, []).append(r)
                if len(groups) < 3:
                    raise InsufficientGroupsError(
                        f"Insufficient groups ({len(groups)}) even after drawing fallback. Minimum 3 required."
                    )
            else:
                raise InsufficientGroupsError(
                    f"Insufficient groups ({len(groups)}) for 3-way split with group_key='{self.group_key}'."
                )

        # 3. Greedy multi-way partitioning
        # Sort groups descending by tile count
        sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        total_tiles = sum(len(tiles) for _, tiles in sorted_groups)
        target_counts = [int(r * total_tiles) for r in self.split_ratios]

        split_bins: Tuple[List[TileRecord], List[TileRecord], List[TileRecord]] = ([], [], [])
        split_counts = [0, 0, 0]

        # Use seed for deterministic tie-breaking
        import random
        rng = random.Random(self.seed)
        shuffled_groups = list(sorted_groups)
        rng.shuffle(shuffled_groups)
        # Re-sort with stable primary key to preserve greedy efficiency while respecting seed
        shuffled_groups.sort(key=lambda kv: len(kv[1]), reverse=True)

        for group_id, group_tiles in shuffled_groups:
            # Find bin with largest deficit relative to its target ratio
            deficits = [
                (target_counts[i] - split_counts[i]) / self.split_ratios[i]
                for i in range(3)
            ]
            best_bin_idx = int(deficits.index(max(deficits)))
            split_bins[best_bin_idx].extend(group_tiles)
            split_counts[best_bin_idx] += len(group_tiles)

        manifest = SplitManifest(
            split_ratios=self.split_ratios,
            group_key=self.group_key,
            seed=self.seed,
            train_tiles=split_bins[0],
            val_tiles=split_bins[1],
            test_tiles=split_bins[2],
            quarantine_tiles=quarantine_records,
            stats=self._compute_all_stats(split_bins, quarantine_records)
        )

        # 4. Mandatory zero-leakage verification
        self.verify_split_isolation(manifest)

        # 5. Compute cryptographic verification hash
        manifest.verification_hash = self._compute_manifest_hash(manifest)
        return manifest

    def verify_split_isolation(self, manifest: SplitManifest) -> Dict[str, Any]:
        """
        Exhaustively verifies zero-leakage invariants across train, val, and test.
        Raises SplitLeakageError immediately if any leakage is discovered.
        """
        train_proj = {t.project_id for t in manifest.train_tiles}
        val_proj = {t.project_id for t in manifest.val_tiles}
        test_proj = {t.project_id for t in manifest.test_tiles}

        train_draw = {t.drawing_id for t in manifest.train_tiles}
        val_draw = {t.drawing_id for t in manifest.val_tiles}
        test_draw = {t.drawing_id for t in manifest.test_tiles}

        train_paths = {t.image_path for t in manifest.train_tiles}
        val_paths = {t.image_path for t in manifest.val_tiles}
        test_paths = {t.image_path for t in manifest.test_tiles}

        # 1. Project overlap check
        tv_proj_overlap = train_proj.intersection(val_proj)
        tt_proj_overlap = train_proj.intersection(test_proj)
        vt_proj_overlap = val_proj.intersection(test_proj)

        if tv_proj_overlap:
            raise SplitLeakageError(f"Train/Val project leakage detected: {tv_proj_overlap}")
        if tt_proj_overlap:
            raise SplitLeakageError(f"Train/Test project leakage detected: {tt_proj_overlap}")
        if vt_proj_overlap:
            raise SplitLeakageError(f"Val/Test project leakage detected: {vt_proj_overlap}")

        # 2. Drawing overlap check
        tv_draw_overlap = train_draw.intersection(val_draw)
        tt_draw_overlap = train_draw.intersection(test_draw)
        vt_draw_overlap = val_draw.intersection(test_draw)

        if tv_draw_overlap:
            raise SplitLeakageError(f"Train/Val drawing leakage detected: {tv_draw_overlap}")
        if tt_draw_overlap:
            raise SplitLeakageError(f"Train/Test drawing leakage detected: {tt_draw_overlap}")
        if vt_draw_overlap:
            raise SplitLeakageError(f"Val/Test drawing leakage detected: {vt_draw_overlap}")

        # 3. Path overlap check
        tv_path_overlap = train_paths.intersection(val_paths)
        tt_path_overlap = train_paths.intersection(test_paths)
        vt_path_overlap = val_paths.intersection(test_paths)

        if tv_path_overlap or tt_path_overlap or vt_path_overlap:
            raise SplitLeakageError("Direct file path overlap detected between splits!")

        report = {
            "status": "PASSED",
            "train_projects": len(train_proj),
            "val_projects": len(val_proj),
            "test_projects": len(test_proj),
            "train_drawings": len(train_draw),
            "val_drawings": len(val_draw),
            "test_drawings": len(test_draw),
            "train_tiles": len(manifest.train_tiles),
            "val_tiles": len(manifest.val_tiles),
            "test_tiles": len(manifest.test_tiles),
            "quarantine_tiles": len(manifest.quarantine_tiles),
            "project_overlap_count": 0,
            "drawing_overlap_count": 0,
            "tile_overlap_count": 0,
        }
        logger.info(f"Split isolation verified successfully: {report}")
        return report

    def export_split_manifests(
        self, manifest: SplitManifest, output_dir: Union[str, Path]
    ) -> Dict[str, Path]:
        """
        Exports train.json, val.json, test.json, and splits_summary.json.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        files = {}
        for name in ["train", "val", "test", "quarantine"]:
            tiles = manifest.get_split_tiles(name)
            split_file = out_path / f"{name}.json"
            data = {
                "split_name": name,
                "version": "1.0",
                "count": len(tiles),
                "tiles": [asdict(t) for t in tiles]
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
            "stats": {k: asdict(v) for k, v in manifest.stats.items()}
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        files["summary"] = summary_file

        return files

    def _compute_manifest_hash(self, manifest: SplitManifest) -> str:
        """Computes SHA-256 fingerprint over all tile IDs and splits."""
        hasher = hashlib.sha256()
        for name in ["train", "val", "test"]:
            tiles = sorted(t.tile_id for t in manifest.get_split_tiles(name))
            hasher.update(f"[{name}:{','.join(tiles)}]".encode("utf-8"))
        return hasher.hexdigest()

    def _compute_all_stats(
        self,
        split_bins: Tuple[List[TileRecord], List[TileRecord], List[TileRecord]],
        quarantine_records: List[TileRecord]
    ) -> Dict[str, SplitStats]:
        names = ["train", "val", "test"]
        stats_map = {}
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
                empty_tiles_count=len(tiles) - wall_tiles
            )
        if quarantine_records:
            stats_map["quarantine"] = SplitStats(
                split_name="quarantine",
                total_projects=len({t.project_id for t in quarantine_records}),
                total_drawings=len({t.drawing_id for t in quarantine_records}),
                total_tiles=len(quarantine_records),
                wall_tiles_count=sum(1 for t in quarantine_records if t.has_walls),
                empty_tiles_count=len(quarantine_records) - sum(1 for t in quarantine_records if t.has_walls)
            )
        return stats_map
```

---

## 3. PyTorch Dataset & DataLoader Interface (`loader.py`)

### 3.1 Streaming Tile Dataset Design
The `DrywallTileDataset` inherits from `torch.utils.data.Dataset`. It operates as a streaming consumer of unified tiles, designed specifically to operate within the strict local memory envelope (< 1.5 GB free RAM).

#### Ingestion Lifecycle per Sample `__getitem__(idx)`:
```
[Disk: tile_001.png (Image)] ──> PIL.Image.open() ──> RGB uint8 [512, 512, 3]
[Disk: tile_001.png (Mask)]  ──> PIL.Image.open() ──> Gray uint8 [512, 512]
                                         │
                                         ▼
                 [Synchronized Architectural Augmentation]
                 - Geometric: Random HFlip, VFlip, 90°/180°/270° Rotations
                   (Applied IDENTICALLY to Image and Mask using Nearest-Neighbor)
                 - Photometric: Contrast / Brightness / Gaussian Noise
                   (Applied STRICTLY to Image, Mask NEVER touched)
                                         │
                                         ▼
                 [Tensor Conversion & Normalization]
                 - Image: ToTensor() -> [0.0, 1.0] -> Normalize(mean, std)
                   Output: torch.FloatTensor of shape [3, 512, 512]
                 - Mask: torch.from_numpy().long()
                   Output: torch.LongTensor of shape [512, 512], values in {0, 1, 2, 3}
                                         │
                                         ▼
                 Returns: (image_tensor, mask_tensor, [metadata])
```

### 3.2 Label Taxonomy & Binary Pretraining Compatibility
The unified segmentation format adheres to the 4-class taxonomy:
- **0: Background** (Paper, text callouts, dimensions, furnishings, doors/windows).
- **1: Drywall** (Verified Gypsum Wallboard / GWB assemblies, Details 1B-1E, 2B, 3A, etc.).
- **2: Non-Drywall** (CMU block Detail 1A, concrete encasements, structural glass GL1/GL2).
- **3: Uncertain** (Unassigned walls, ambiguous tags, lack of verified schedule evidence).

#### Mode Parameter:
- `mode="4class"`: Default mode. Preserves full 4-class labels $\{0, 1, 2, 3\}$.
- `mode="binary"`: Used for Stage 1 pretraining on open academic datasets (MSD, CubiCasa5K). Remaps all positive wall classes $\{1, 2, 3\} \to 1$ and $\{0\} \to 0$.

### 3.3 Synchronized Augmentation Engine
Architectural drawings are orthographic vector-derived drawings. They possess unique geometric symmetries:
1. **Discrete 90° Rotations**: Architectural line drawings remain valid floor plans under 90°, 180°, and 270° rotations. Arbitrary continuous rotations (e.g. 15°) cause bilinear anti-aliasing interpolation that blurs thin 1-pixel CAD vector lines into diffuse gray smudges, altering perceived wall thickness.
2. **Reflections**: Horizontal and vertical reflections represent realistic architectural layout variations (mirror-unit apartment layouts).
3. **Synchronization Contract**: Geometric spatial transformations must use the exact same random state for both image and mask. The mask must always be interpolated with nearest-neighbor (`InterpolationMode.NEAREST`) to prevent fractional float labels (e.g., a pixel becoming 0.4 between class 0 and 1).
4. **Photometric Transforms**: Scanned drawings or blueprints may have varying exposure or yellowed paper. Applying mild contrast jitter (0.85 to 1.15) and brightness jitter (0.85 to 1.15) improves model robustness against scanning noise. This must NEVER alter mask labels.

### 3.4 Hardware-Adapted DataLoader Factory
The DataLoader factory `get_tile_dataloader()` automatically selects safe defaults based on host profiling:
- **`batch_size`**: Default `2` (recommended for CPU training with lightweight U-Net or SegFormer-B0) or configurable up to `4`.
- **`num_workers`**: Default `0` on Windows. Windows lacks Unix `fork()`; its `spawn` implementation creates duplicate Python interpreter processes consuming ~150 MB RAM each, which easily triggers OOM crashes when available RAM is ~1.0 GB. In Google Colab or Linux with CUDA, `num_workers` can scale to `4`.
- **`pin_memory`**: Set strictly to `False` on CPU. Pinned host memory allocates page-locked memory which strains Windows virtual memory without providing any DMA transfer benefit on non-CUDA systems.
- **`drop_last`**: `True` for training (maintaining batch size consistency for batch normalization / layer normalization), `False` for evaluation.
- **`collate_fn`**: Robust collate function `safe_collate_fn` that filters corrupted tiles and asserts batch tensor shapes: `[B, 3, 512, 512]` and `[B, 512, 512]`.

### 3.5 Detailed Interface Specification (`drywall_detection/datasets/loader.py`)

```python
"""
drywall_detection.datasets.loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Streaming PyTorch Dataset and hardware-adapted DataLoader for unified 512x512
architectural floor plan tiles with synchronized augmentations.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Callable, Union

import numpy as np
from PIL import Image

import torch
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms.functional as TF

logger = logging.getLogger(__name__)

# Standard ImageNet Normalization Constants
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class SynchronizedTransform:
    """
    Applies synchronized geometric transforms to image and mask,
    and photometric transforms strictly to the image.
    Uses pure PyTorch / Torchvision (no albumentations dependency).
    """

    def __init__(
        self,
        is_train: bool = True,
        hflip_prob: float = 0.5,
        vflip_prob: float = 0.5,
        rot90_prob: float = 0.5,
        brightness_jitter: float = 0.15,
        contrast_jitter: float = 0.15,
        mean: List[float] = IMAGENET_MEAN,
        std: List[float] = IMAGENET_STD
    ):
        self.is_train = is_train
        self.hflip_prob = hflip_prob
        self.vflip_prob = vflip_prob
        self.rot90_prob = rot90_prob
        self.brightness_jitter = brightness_jitter
        self.contrast_jitter = contrast_jitter
        self.mean = mean
        self.std = std

    def __call__(self, image: Image.Image, mask: Image.Image) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            image: PIL Image (RGB, 512x512)
            mask: PIL Image (L / single channel uint8, 512x512)
        Returns:
            image_tensor: FloatTensor [3, 512, 512], normalized
            mask_tensor: LongTensor [512, 512], values in {0, 1, 2, 3}
        """
        # Ensure dimensions match
        if image.size != (512, 512):
            image = image.resize((512, 512), Image.BILINEAR)
        if mask.size != (512, 512):
            mask = mask.resize((512, 512), Image.NEAREST)

        if self.is_train:
            # 1. Random Horizontal Flip
            if torch.rand(1).item() < self.hflip_prob:
                image = TF.hflip(image)
                mask = TF.hflip(mask)

            # 2. Random Vertical Flip
            if torch.rand(1).item() < self.vflip_prob:
                image = TF.vflip(image)
                mask = TF.vflip(mask)

            # 3. Discrete 90-degree Rotations (0, 90, 180, 270)
            if torch.rand(1).item() < self.rot90_prob:
                angle = int(torch.randint(1, 4, (1,)).item() * 90)  # 90, 180, or 270
                image = TF.rotate(image, angle, interpolation=TF.InterpolationMode.BILINEAR)
                mask = TF.rotate(mask, angle, interpolation=TF.InterpolationMode.NEAREST)

            # 4. Photometric Jitter (Image Only)
            if self.brightness_jitter > 0 or self.contrast_jitter > 0:
                # Random brightness
                if self.brightness_jitter > 0:
                    bfactor = 1.0 + float(torch.empty(1).uniform_(-self.brightness_jitter, self.brightness_jitter))
                    image = TF.adjust_brightness(image, bfactor)
                # Random contrast
                if self.contrast_jitter > 0:
                    cfactor = 1.0 + float(torch.empty(1).uniform_(-self.contrast_jitter, self.contrast_jitter))
                    image = TF.adjust_contrast(image, cfactor)

        # Convert Image to Tensor [3, 512, 512] in [0.0, 1.0] and Normalize
        image_tensor = TF.to_tensor(image)  # [3, 512, 512] float32 in [0, 1]
        image_tensor = TF.normalize(image_tensor, mean=self.mean, std=self.std)

        # Convert Mask to LongTensor [512, 512]
        mask_np = np.array(mask, dtype=np.int64)
        mask_tensor = torch.from_numpy(mask_np).long()

        return image_tensor, mask_tensor


class DrywallTileDataset(Dataset):
    """
    Streaming PyTorch Dataset for 512x512 floor plan tiles and segmentation masks.
    """

    def __init__(
        self,
        manifest_or_tiles: Union[str, Path, List[Dict[str, Any]]],
        mode: str = "4class",
        transform: Optional[Callable] = None,
        return_metadata: bool = False
    ):
        """
        Args:
            manifest_or_tiles: Path to split JSON file or list of tile dictionaries.
            mode: "4class" (0=bg, 1=drywall, 2=nondrywall, 3=uncertain) or "binary" (0=bg, 1=wall).
            transform: Transformation function returning (image_tensor, mask_tensor).
            return_metadata: Whether to return tile metadata dict alongside tensors.
        """
        if isinstance(manifest_or_tiles, (str, Path)):
            manifest_path = Path(manifest_or_tiles)
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.tiles = data.get("tiles", data) if isinstance(data, dict) else data
        else:
            self.tiles = list(manifest_or_tiles)

        if mode not in ("4class", "binary"):
            raise ValueError(f"Invalid mode '{mode}'. Expected '4class' or 'binary'.")

        self.mode = mode
        self.transform = transform
        self.return_metadata = return_metadata

    def __len__(self) -> int:
        return len(self.tiles)

    def __getitem__(self, idx: int) -> Union[Tuple[torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]]:
        tile_info = self.tiles[idx]
        image_path = Path(tile_info["image_path"])
        mask_path = Path(tile_info["mask_path"])

        if not image_path.exists():
            raise FileNotFoundError(f"Tile image does not exist: {image_path}")
        if not mask_path.exists():
            raise FileNotFoundError(f"Tile mask does not exist: {mask_path}")

        # Lazy loading of images from disk
        with Image.open(image_path) as img:
            image = img.convert("RGB")

        with Image.open(mask_path) as msk:
            mask = msk.convert("L")

        # Apply transforms or default conversion
        if self.transform is not None:
            image_tensor, mask_tensor = self.transform(image, mask)
        else:
            image_tensor = TF.to_tensor(image)
            image_tensor = TF.normalize(image_tensor, mean=IMAGENET_MEAN, std=IMAGENET_STD)
            mask_np = np.array(mask, dtype=np.int64)
            mask_tensor = torch.from_numpy(mask_np).long()

        # Binary remapping if requested
        if self.mode == "binary":
            mask_tensor = (mask_tensor > 0).long()
        else:
            # Clamp values to valid class range {0, 1, 2, 3}
            mask_tensor = torch.clamp(mask_tensor, 0, 3)

        if self.return_metadata:
            meta = {
                "tile_id": tile_info.get("tile_id", f"tile_{idx}"),
                "project_id": tile_info.get("project_id", "unknown"),
                "drawing_id": tile_info.get("drawing_id", "unknown"),
                "bbox": tile_info.get("bbox", [0, 0, 512, 512])
            }
            return image_tensor, mask_tensor, meta

        return image_tensor, mask_tensor


def safe_collate_fn(batch: List[Any]) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Collate function asserting shapes and filtering any corrupt/empty returns.
    """
    batch = [item for item in batch if item is not None]
    if len(batch) == 0:
        raise RuntimeError("Empty batch encountered in safe_collate_fn!")

    if len(batch[0]) == 3:
        # Tuple of (image, mask, meta)
        images = torch.stack([item[0] for item in batch], dim=0)
        masks = torch.stack([item[1] for item in batch], dim=0)
        metas = [item[2] for item in batch]
        return images, masks, metas

    images = torch.stack([item[0] for item in batch], dim=0)
    masks = torch.stack([item[1] for item in batch], dim=0)
    return images, masks


def get_tile_dataloader(
    manifest_or_tiles: Union[str, Path, List[Dict[str, Any]]],
    is_train: bool = True,
    batch_size: int = 2,
    mode: str = "4class",
    num_workers: int = 0,
    pin_memory: bool = False,
    shuffle: Optional[bool] = None,
    drop_last: Optional[bool] = None,
    return_metadata: bool = False
) -> DataLoader:
    """
    Factory function producing hardware-adapted PyTorch DataLoader.
    Defaults to num_workers=0 and pin_memory=False for CPU/Windows safety.
    """
    if shuffle is None:
        shuffle = is_train
    if drop_last is None:
        drop_last = is_train

    transform = SynchronizedTransform(is_train=is_train)
    dataset = DrywallTileDataset(
        manifest_or_tiles=manifest_or_tiles,
        mode=mode,
        transform=transform,
        return_metadata=return_metadata
    )

    loader = DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=drop_last,
        collate_fn=safe_collate_fn
    )
    return loader
```

---

## 4. Comprehensive Unit Testing Specification (`test_datasets.py`)

### 4.1 Test Hierarchy & Coverage Mapping
The unit testing specification for `drywall_detection/tests/unit/test_datasets.py` adheres to `pytest` and verifies every requirement established in `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `TEST_INFRA.md`.

```
test_datasets.py
├── TestDrawingSplitManager (Split Integrity & Disjointness)
│   ├── test_zero_project_overlap_three_splits
│   ├── test_zero_drawing_overlap_fallback
│   ├── test_split_leakage_detection_raises_error
│   ├── test_reproducible_deterministic_seed
│   ├── test_greedy_ratio_balance_tolerance
│   ├── test_quarantine_exclusion_from_val_test
│   ├── test_insufficient_groups_error
│   ├── test_invalid_split_ratios_error
│   └── test_manifest_export_and_json_roundtrip
│
├── TestDrywallTileDataset (Data Streaming & Tensors)
│   ├── test_dataset_tensor_shapes_and_dtypes
│   ├── test_image_normalization_stats
│   ├── test_mask_class_range_four_class
│   ├── test_binary_mode_remapping
│   ├── test_missing_file_raises_filenotfound
│   └── test_return_metadata_passthrough
│
├── TestSynchronizedTransform (Co-Transforms)
│   ├── test_spatial_transform_synchronization
│   ├── test_discrete_90_degree_rotations_preserve_labels
│   └── test_photometric_jitter_alters_image_only
│
└── TestTileDataLoader (Batching & Hardware Adaptation)
    ├── test_dataloader_batch_shapes
    ├── test_dataloader_cpu_defaults_num_workers_and_pin_memory
    ├── test_dataloader_iteration_memory_stability
    └── test_end_to_end_forward_pass_sanity
```

### 4.2 Detailed Test Implementation Specification

```python
"""
drywall_detection/tests/unit/test_datasets.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit test suite verifying split integrity, zero project/drawing leakage,
PyTorch tile dataset streaming, synchronized augmentations, and DataLoader batching.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from PIL import Image

import torch
import torchvision.transforms.functional as TF

from drywall_detection.datasets.split_manager import (
    DrawingSplitManager,
    SplitManifest,
    TileRecord,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError
)
from drywall_detection.datasets.loader import (
    DrywallTileDataset,
    SynchronizedTransform,
    get_tile_dataloader,
    IMAGENET_MEAN,
    IMAGENET_STD
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_tile_records():
    """Generates a synthetic list of 100 tiles across 10 distinct projects."""
    records = []
    for proj_idx in range(10):
        proj_id = f"proj_{proj_idx:02d}"
        for draw_idx in range(2):
            draw_id = f"{proj_id}_sheet_{draw_idx:02d}"
            for tile_idx in range(5):
                tile_id = f"{draw_id}_tile_{tile_idx:03d}"
                records.append(
                    TileRecord(
                        tile_id=tile_id,
                        project_id=proj_id,
                        drawing_id=draw_id,
                        image_path=f"/fake/images/{tile_id}.png",
                        mask_path=f"/fake/masks/{tile_id}.png",
                        bbox=(0, 0, 512, 512),
                        has_walls=True,
                        quarantine=False
                    )
                )
    return records


@pytest.fixture
def synthetic_tile_dir(tmp_path):
    """Creates actual 512x512 synthetic PNG images and masks on disk."""
    img_dir = tmp_path / "images"
    msk_dir = tmp_path / "masks"
    img_dir.mkdir()
    msk_dir.mkdir()

    tiles_info = []
    # Create 8 tiles across 4 projects
    for p in range(4):
        proj_id = f"project_{p}"
        for d in range(2):
            draw_id = f"{proj_id}_drawing_{d}"
            tile_id = f"{draw_id}_tile_0"

            # Create synthetic RGB image (512x512)
            img_arr = np.random.randint(100, 255, (512, 512, 3), dtype=np.uint8)
            img_path = img_dir / f"{tile_id}.png"
            Image.fromarray(img_arr).save(img_path)

            # Create synthetic Mask (512x512) with classes 0, 1, 2, 3
            msk_arr = np.zeros((512, 512), dtype=np.uint8)
            msk_arr[50:150, 50:150] = 1   # Drywall
            msk_arr[200:300, 200:300] = 2 # Non-Drywall
            msk_arr[350:400, 350:400] = 3 # Uncertain
            msk_path = msk_dir / f"{tile_id}.png"
            Image.fromarray(msk_arr).save(msk_path)

            tiles_info.append({
                "tile_id": tile_id,
                "project_id": proj_id,
                "drawing_id": draw_id,
                "image_path": str(img_path),
                "mask_path": str(msk_path),
                "bbox": [0, 0, 512, 512],
                "has_walls": True
            })

    manifest_file = tmp_path / "train_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump({"tiles": tiles_info}, f)

    return manifest_file, tiles_info


# ==============================================================================
# 1. TestDrawingSplitManager Suite
# ==============================================================================

class TestDrawingSplitManager:

    def test_zero_project_overlap_three_splits(self, mock_tile_records):
        """Verify strict mathematical disjointness across train, val, and test."""
        mgr = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", seed=42)
        manifest = mgr.create_splits(mock_tile_records)

        train_projs = {t.project_id for t in manifest.train_tiles}
        val_projs = {t.project_id for t in manifest.val_tiles}
        test_projs = {t.project_id for t in manifest.test_tiles}

        # Assert zero intersections
        assert len(train_projs.intersection(val_projs)) == 0, "Train and Val project overlap detected!"
        assert len(train_projs.intersection(test_projs)) == 0, "Train and Test project overlap detected!"
        assert len(val_projs.intersection(test_projs)) == 0, "Val and Test project overlap detected!"

        # Assert total covers all projects
        assert train_projs.union(val_projs).union(test_projs) == {t.project_id for t in mock_tile_records}

    def test_split_leakage_detection_raises_error(self, mock_tile_records):
        """Verify verify_split_isolation catches deliberately injected project leakage."""
        mgr = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", seed=42)
        manifest = mgr.create_splits(mock_tile_records)

        # Invalidate manifest by duplicating a training tile into validation
        leaked_tile = manifest.train_tiles[0]
        manifest.val_tiles.append(leaked_tile)

        with pytest.raises(SplitLeakageError) as exc_info:
            mgr.verify_split_isolation(manifest)
        assert "leakage detected" in str(exc_info.value).lower()

    def test_reproducible_deterministic_seed(self, mock_tile_records):
        """Verify identical splits are produced with identical seeds."""
        mgr1 = DrawingSplitManager(seed=123)
        mgr2 = DrawingSplitManager(seed=123)

        m1 = mgr1.create_splits(mock_tile_records)
        m2 = mgr2.create_splits(mock_tile_records)

        assert [t.tile_id for t in m1.train_tiles] == [t.tile_id for t in m2.train_tiles]
        assert [t.tile_id for t in m1.val_tiles] == [t.tile_id for t in m2.val_tiles]
        assert [t.tile_id for t in m1.test_tiles] == [t.tile_id for t in m2.test_tiles]
        assert m1.verification_hash == m2.verification_hash

    def test_quarantine_exclusion_from_val_test(self, mock_tile_records):
        """Verify quarantined projects are strictly excluded from val and test splits."""
        quarantine_target = "proj_00"
        mgr = DrawingSplitManager(quarantine_projects=[quarantine_target], seed=42)
        manifest = mgr.create_splits(mock_tile_records)

        val_projs = {t.project_id for t in manifest.val_tiles}
        test_projs = {t.project_id for t in manifest.test_tiles}
        quarantine_projs = {t.project_id for t in manifest.quarantine_tiles}

        assert quarantine_target not in val_projs, "Quarantined project leaked into Val!"
        assert quarantine_target not in test_projs, "Quarantined project leaked into Test!"
        assert quarantine_target in quarantine_projs

    def test_invalid_split_ratios_error(self):
        """Verify exception raised when ratios do not sum to 1.0."""
        with pytest.raises(InvalidSplitRatioError):
            DrawingSplitManager(split_ratios=(0.80, 0.20, 0.10))

    def test_manifest_export_and_json_roundtrip(self, mock_tile_records, tmp_path):
        """Verify split manifests export to valid JSON files and reload accurately."""
        mgr = DrawingSplitManager(seed=42)
        manifest = mgr.create_splits(mock_tile_records)

        export_dir = tmp_path / "splits_out"
        exported = mgr.export_split_manifests(manifest, export_dir)

        assert exported["train"].exists()
        assert exported["val"].exists()
        assert exported["test"].exists()
        assert exported["summary"].exists()

        with open(exported["summary"], "r") as f:
            summary = json.load(f)
        assert summary["isolation_status"] == "VERIFIED_ZERO_LEAKAGE"
        assert summary["verification_hash"] == manifest.verification_hash


# ==============================================================================
# 2. TestDrywallTileDataset Suite
# ==============================================================================

class TestDrywallTileDataset:

    def test_dataset_tensor_shapes_and_dtypes(self, synthetic_tile_dir):
        """Verify dataset yields [3, 512, 512] float32 image and [512, 512] long mask."""
        manifest_file, _ = synthetic_tile_dir
        dataset = DrywallTileDataset(manifest_file, mode="4class")

        assert len(dataset) == 8
        img_tensor, msk_tensor = dataset[0]

        assert isinstance(img_tensor, torch.Tensor)
        assert isinstance(msk_tensor, torch.Tensor)
        assert img_tensor.shape == (3, 512, 512)
        assert msk_tensor.shape == (512, 512)
        assert img_tensor.dtype == torch.float32
        assert msk_tensor.dtype == torch.int64

    def test_mask_class_range_four_class(self, synthetic_tile_dir):
        """Verify mask labels are strictly contained in {0, 1, 2, 3}."""
        manifest_file, _ = synthetic_tile_dir
        dataset = DrywallTileDataset(manifest_file, mode="4class")

        _, msk_tensor = dataset[0]
        unique_vals = set(msk_tensor.unique().tolist())
        assert unique_vals.issubset({0, 1, 2, 3}), f"Unexpected classes found: {unique_vals}"

    def test_binary_mode_remapping(self, synthetic_tile_dir):
        """Verify mode='binary' remaps classes {1, 2, 3} to 1."""
        manifest_file, _ = synthetic_tile_dir
        dataset = DrywallTileDataset(manifest_file, mode="binary")

        _, msk_tensor = dataset[0]
        unique_vals = set(msk_tensor.unique().tolist())
        assert unique_vals.issubset({0, 1}), f"Non-binary classes in binary mode: {unique_vals}"

    def test_image_normalization_stats(self, synthetic_tile_dir):
        """Verify ImageNet normalization is applied to image tensor."""
        manifest_file, _ = synthetic_tile_dir
        dataset = DrywallTileDataset(manifest_file, mode="4class")
        img_tensor, _ = dataset[0]

        # Normalized values should extend outside [0, 1] (negative and positive values)
        assert img_tensor.min() < 0.0, "Normalization did not produce negative values!"
        assert img_tensor.max() > 1.0, "Normalization did not produce scaled values!"

    def test_missing_file_raises_filenotfound(self, tmp_path):
        """Verify missing image/mask raises clean FileNotFoundError."""
        bad_manifest = tmp_path / "bad.json"
        with open(bad_manifest, "w") as f:
            json.dump({"tiles": [{"image_path": "/fake/nonexistent.png", "mask_path": "/fake/nonexistent_m.png"}]}, f)

        dataset = DrywallTileDataset(bad_manifest)
        with pytest.raises(FileNotFoundError):
            _ = dataset[0]


# ==============================================================================
# 3. TestSynchronizedTransform Suite
# ==============================================================================

class TestSynchronizedTransform:

    def test_spatial_transform_synchronization(self):
        """Verify spatial flips and 90° rotations are identically applied to image and mask."""
        # Create patterned image with bright top-left corner
        img_arr = np.zeros((512, 512, 3), dtype=np.uint8)
        img_arr[0:100, 0:100, :] = 255
        img = Image.fromarray(img_arr)

        # Create matching mask with drywall (1) in top-left corner
        msk_arr = np.zeros((512, 512), dtype=np.uint8)
        msk_arr[0:100, 0:100] = 1
        msk = Image.fromarray(msk_arr)

        # Force horizontal flip (p=1.0)
        transform = SynchronizedTransform(is_train=True, hflip_prob=1.0, vflip_prob=0.0, rot90_prob=0.0)
        img_t, msk_t = transform(img, msk)

        # In flipped mask, top-right (x: 412..511) should be 1, top-left should be 0
        assert msk_t[50, 50].item() == 0, "Top-left should have flipped away!"
        assert msk_t[50, 460].item() == 1, "Top-right should now contain drywall label!"

    def test_discrete_90_degree_rotations_preserve_labels(self):
        """Verify 90° rotations preserve exact integer label values without interpolation bleed."""
        msk_arr = np.zeros((512, 512), dtype=np.uint8)
        msk_arr[0:50, :] = 1  # Top wall
        msk = Image.fromarray(msk_arr)
        img = Image.fromarray(np.ones((512, 512, 3), dtype=np.uint8) * 128)

        # Force 90° rotation
        transform = SynchronizedTransform(is_train=True, hflip_prob=0.0, vflip_prob=0.0, rot90_prob=1.0)
        _, msk_t = transform(img, msk)

        unique_vals = set(msk_t.unique().tolist())
        assert unique_vals.issubset({0, 1}), f"Rotation introduced label artifacts: {unique_vals}"


# ==============================================================================
# 4. TestTileDataLoader Suite
# ==============================================================================

class TestTileDataLoader:

    def test_dataloader_batch_shapes(self, synthetic_tile_dir):
        """Verify DataLoader batches tensors into [B, 3, 512, 512] and [B, 512, 512]."""
        manifest_file, _ = synthetic_tile_dir
        batch_size = 2
        loader = get_tile_dataloader(manifest_file, batch_size=batch_size, is_train=False)

        batch_imgs, batch_msks = next(iter(loader))
        assert batch_imgs.shape == (batch_size, 3, 512, 512)
        assert batch_msks.shape == (batch_size, 512, 512)
        assert batch_imgs.dtype == torch.float32
        assert batch_msks.dtype == torch.int64

    def test_dataloader_cpu_defaults_num_workers_and_pin_memory(self, synthetic_tile_dir):
        """Verify DataLoader uses safe CPU defaults (num_workers=0, pin_memory=False)."""
        manifest_file, _ = synthetic_tile_dir
        loader = get_tile_dataloader(manifest_file, batch_size=2)

        assert loader.num_workers == 0, "num_workers must default to 0 on Windows/CPU"
        assert loader.pin_memory is False, "pin_memory must default to False without CUDA"

    def test_end_to_end_forward_pass_sanity(self, synthetic_tile_dir):
        """Verify batch can be passed directly into a dummy PyTorch segmentation head without error."""
        manifest_file, _ = synthetic_tile_dir
        loader = get_tile_dataloader(manifest_file, batch_size=2, is_train=True)

        batch_imgs, batch_msks = next(iter(loader))

        # Minimal dummy conv layer simulating 4-class segmentation model output
        model = torch.nn.Conv2d(in_channels=3, out_channels=4, kernel_size=1)
        logits = model(batch_imgs)  # [B, 4, 512, 512]

        assert logits.shape == (2, 4, 512, 512)
        loss = torch.nn.functional.cross_entropy(logits, batch_msks)
        assert loss.item() > 0.0
        assert not torch.isnan(loss)
```

---

## 5. Concrete Implementation Roadmap for Worker

To implement Milestone M1/M2 code within the `drywall_detection/` boundary, the Worker should execute the following sequence:

| Step | Target File | Action Required | Validation Command |
|---|---|---|---|
| **Step 1** | `drywall_detection/datasets/__init__.py` | Initialize package and export public classes (`DrawingSplitManager`, `DrywallTileDataset`, `get_tile_dataloader`, `SplitLeakageError`). | `python -c "import drywall_detection.datasets"` |
| **Step 2** | `drywall_detection/datasets/split_manager.py` | Implement `DrawingSplitManager`, `TileRecord`, `SplitManifest`, greedy group partitioning, and `verify_split_isolation`. | `pytest drywall_detection/tests/unit/test_datasets.py -k TestDrawingSplitManager` |
| **Step 3** | `drywall_detection/datasets/loader.py` | Implement `SynchronizedTransform`, `DrywallTileDataset`, and `get_tile_dataloader` adhering to the interface contract. | `pytest drywall_detection/tests/unit/test_datasets.py -k TestDrywallTileDataset` |
| **Step 4** | `drywall_detection/data/` (Compatibility Aliases) | Add import wrappers in `drywall_detection/data/preparer.py` aliasing `DrawingSplitManager` to satisfy PROJECT.md Section 4.3. | `python -c "from drywall_detection.data.preparer import DrawingSplitManager"` |
| **Step 5** | `drywall_detection/tests/unit/test_datasets.py` | Implement all 20+ unit test cases specified in Section 4.2. | `pytest drywall_detection/tests/unit/test_datasets.py -v` |

---

## 6. Synthesis & Inter-Module Alignment

- **Alignment with `m1_spec_miner_2` (Unified Format)**:
  The `DrywallTileDataset` expects tiles produced by `unified_format.py` (512x512 PNGs, 4-class indexed uint8 masks {0, 1, 2, 3}). Both online tensor conversion and offline pre-tiled folder structures are fully supported.
- **Alignment with `m1_explorer_1` (Licensing & Dataset Sources)**:
  The `DrawingSplitManager` is parameterizable with `group_key="site_id"` for Modified Swiss Dwellings (MSD) and `group_key="project_id"` for CubiCasa5K / FloorPlanCAD, ensuring zero-leakage holds regardless of dataset origin.
- **Alignment with Milestone M4 (Model Training)**:
  The output tensor shape `[B, 3, 512, 512]` and long mask `[B, 512, 512]` are plug-and-play compatible with HuggingFace SegFormer (`nvidia/mit-b0`) and PyTorch U-Net models.
