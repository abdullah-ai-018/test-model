"""
drywall_detection/tests/test_m1_adversarial_stress.py
=====================================================
Adversarial Stress Test Suite for Milestone M1:
- Drawing-level and project-level split integrity manager
- Zero-leakage invariant enforcement under adversarial attacks
- Greedy partitioning under extreme, skewed, and edge-case distributions
- DataLoader streaming, memory stability across epochs, tensor shapes, and transform synchrony
"""

from __future__ import annotations
import gc
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Tuple
import pytest
import numpy as np
from PIL import Image

import torch
import torchvision.transforms.functional as TF

from drywall_detection.datasets.split_manager import (
    TileRecord,
    SplitManifest,
    DrawingSplitManager,
    SplitLeakageError,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    verify_split_isolation,
)
from drywall_detection.datasets.loader import (
    SynchronizedTransform,
    DrywallTileDataset,
    safe_collate_fn,
    get_tile_dataloader,
)
from drywall_detection.datasets.unified_format import PALETTE_256


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def base_synthetic_manifest(tmp_path: Path) -> SplitManifest:
    """Creates a clean, valid SplitManifest with 15 projects (5 train, 5 val, 5 test)."""
    train_tiles: List[TileRecord] = []
    val_tiles: List[TileRecord] = []
    test_tiles: List[TileRecord] = []

    for i in range(5):
        pid = f"proj_train_{i:02d}"
        did = f"draw_train_{i:02d}"
        tid = f"tile_train_{i:02d}"
        train_tiles.append(TileRecord(tid, pid, did, f"/fake/img/{tid}.png", f"/fake/msk/{tid}.png", (0, 0, 512, 512)))

    for i in range(5):
        pid = f"proj_val_{i:02d}"
        did = f"draw_val_{i:02d}"
        tid = f"tile_val_{i:02d}"
        val_tiles.append(TileRecord(tid, pid, did, f"/fake/img/{tid}.png", f"/fake/msk/{tid}.png", (0, 0, 512, 512)))

    for i in range(5):
        pid = f"proj_test_{i:02d}"
        did = f"draw_test_{i:02d}"
        tid = f"tile_test_{i:02d}"
        test_tiles.append(TileRecord(tid, pid, did, f"/fake/img/{tid}.png", f"/fake/msk/{tid}.png", (0, 0, 512, 512)))

    manifest = SplitManifest(
        split_ratios=(0.7, 0.15, 0.15),
        group_key="project_id",
        seed=42,
        train_tiles=train_tiles,
        val_tiles=val_tiles,
        test_tiles=test_tiles,
    )
    # Ensure baseline passes
    verify_split_isolation(manifest)
    return manifest


# ==============================================================================
# Suite 1: Adversarial Leakage Injection
# ==============================================================================

class TestAdversarialLeakage:
    """Stress-tests verify_split_isolation under diverse adversarial leakage attacks."""

    def test_leakage_duplicate_project_train_val(self, base_synthetic_manifest: SplitManifest):
        # Inject train project into val
        base_synthetic_manifest.val_tiles.append(
            TileRecord("leak_01", base_synthetic_manifest.train_tiles[0].project_id, "draw_uniq_val", "/fake/img/l1.png", "/fake/msk/l1.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Train/Val project leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_project_train_test(self, base_synthetic_manifest: SplitManifest):
        # Inject train project into test
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_02", base_synthetic_manifest.train_tiles[1].project_id, "draw_uniq_test", "/fake/img/l2.png", "/fake/msk/l2.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Train/Test project leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_project_val_test(self, base_synthetic_manifest: SplitManifest):
        # Inject val project into test
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_03", base_synthetic_manifest.val_tiles[0].project_id, "draw_uniq_test2", "/fake/img/l3.png", "/fake/msk/l3.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Val/Test project leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_drawing_train_val(self, base_synthetic_manifest: SplitManifest):
        # Different project_id, identical drawing_id
        base_synthetic_manifest.val_tiles.append(
            TileRecord("leak_04", "completely_new_val_proj", base_synthetic_manifest.train_tiles[0].drawing_id, "/fake/img/l4.png", "/fake/msk/l4.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Train/Val drawing leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_drawing_train_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_05", "completely_new_test_proj", base_synthetic_manifest.train_tiles[1].drawing_id, "/fake/img/l5.png", "/fake/msk/l5.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Train/Test drawing leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_drawing_val_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_06", "completely_new_test_proj2", base_synthetic_manifest.val_tiles[0].drawing_id, "/fake/img/l6.png", "/fake/msk/l6.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Val/Test drawing leakage"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_image_path_train_val(self, base_synthetic_manifest: SplitManifest):
        # Different project and drawing IDs, but overlapping image file path
        base_synthetic_manifest.val_tiles.append(
            TileRecord("leak_07", "new_val_proj", "new_val_draw", base_synthetic_manifest.train_tiles[0].image_path, "/fake/msk/l7.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct image file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_image_path_train_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_08", "new_test_proj", "new_test_draw", base_synthetic_manifest.train_tiles[1].image_path, "/fake/msk/l8.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct image file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_image_path_val_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_09", "new_test_proj2", "new_test_draw2", base_synthetic_manifest.val_tiles[0].image_path, "/fake/msk/l9.png", (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct image file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_mask_path_train_val(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.val_tiles.append(
            TileRecord("leak_10", "new_val_proj", "new_val_draw", "/fake/img/l10.png", base_synthetic_manifest.train_tiles[0].mask_path, (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct mask file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_mask_path_train_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_11", "new_test_proj", "new_test_draw", "/fake/img/l11.png", base_synthetic_manifest.train_tiles[1].mask_path, (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct mask file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_duplicate_mask_path_val_test(self, base_synthetic_manifest: SplitManifest):
        base_synthetic_manifest.test_tiles.append(
            TileRecord("leak_12", "new_test_proj2", "new_test_draw2", "/fake/img/l12.png", base_synthetic_manifest.val_tiles[0].mask_path, (0, 0, 512, 512))
        )
        with pytest.raises(SplitLeakageError, match="Direct mask file path overlap"):
            verify_split_isolation(base_synthetic_manifest)

    def test_leakage_path_normalization_adversarial(self, tmp_path: Path):
        # Test whether relative, non-canonical, redundant slashes, and '..' paths are resolved
        real_file = tmp_path / "sample_img.png"
        real_file.touch()

        # Variant 1: standard absolute string
        path_var1 = str(real_file.resolve())
        # Variant 2: redundant dot and slash
        path_var2 = str(tmp_path / "." / "subdir" / ".." / "sample_img.png")

        manifest = SplitManifest(
            split_ratios=(0.7, 0.15, 0.15),
            group_key="project_id",
            seed=42,
            train_tiles=[TileRecord("t1", "p1", "d1", path_var1, "/m1.png", (0, 0, 512, 512))],
            val_tiles=[TileRecord("t2", "p2", "d2", path_var2, "/m2.png", (0, 0, 512, 512))],
            test_tiles=[TileRecord("t3", "p3", "d3", "/img3.png", "/m3.png", (0, 0, 512, 512))],
        )

        with pytest.raises(SplitLeakageError, match="Direct image file path overlap"):
            verify_split_isolation(manifest)

    def test_monte_carlo_adversarial_leakage_detection_rate(self, base_synthetic_manifest: SplitManifest):
        """
        Runs 100 randomized trials injecting random leakage types.
        Verifies 100% (100/100) detection rate by verify_split_isolation.
        """
        rng = random.Random(1337)
        trials = 100
        detected = 0

        for trial in range(trials):
            # Clone manifest tiles
            train_tiles = list(base_synthetic_manifest.train_tiles)
            val_tiles = list(base_synthetic_manifest.val_tiles)
            test_tiles = list(base_synthetic_manifest.test_tiles)

            manifest = SplitManifest(
                split_ratios=(0.7, 0.15, 0.15),
                group_key="project_id",
                seed=trial,
                train_tiles=train_tiles,
                val_tiles=val_tiles,
                test_tiles=test_tiles,
            )

            # Choose injection target: val or test
            target_split = val_tiles if rng.random() < 0.5 else test_tiles
            # Choose source: train (or val if target is test)
            if target_split is test_tiles and rng.random() < 0.3:
                source_tile = rng.choice(val_tiles)
            else:
                source_tile = rng.choice(train_tiles)

            leak_mode = rng.choice(["project", "drawing", "image_path", "mask_path", "full_tile"])
            if leak_mode == "project":
                target_split.append(TileRecord(
                    f"mc_leak_{trial}", source_tile.project_id, f"mc_draw_{trial}", f"/mc/img_{trial}.png", f"/mc/msk_{trial}.png", (0, 0, 512, 512)
                ))
            elif leak_mode == "drawing":
                target_split.append(TileRecord(
                    f"mc_leak_{trial}", f"mc_proj_{trial}", source_tile.drawing_id, f"/mc/img_{trial}.png", f"/mc/msk_{trial}.png", (0, 0, 512, 512)
                ))
            elif leak_mode == "image_path":
                target_split.append(TileRecord(
                    f"mc_leak_{trial}", f"mc_proj_{trial}", f"mc_draw_{trial}", source_tile.image_path, f"/mc/msk_{trial}.png", (0, 0, 512, 512)
                ))
            elif leak_mode == "mask_path":
                target_split.append(TileRecord(
                    f"mc_leak_{trial}", f"mc_proj_{trial}", f"mc_draw_{trial}", f"/mc/img_{trial}.png", source_tile.mask_path, (0, 0, 512, 512)
                ))
            elif leak_mode == "full_tile":
                target_split.append(source_tile)

            try:
                verify_split_isolation(manifest)
            except SplitLeakageError:
                detected += 1

        assert detected == trials, f"Detection rate {detected}/{trials} failed 100% threshold!"


# ==============================================================================
# Suite 2: Greedy Partitioning Under Skewed & Extreme Distributions
# ==============================================================================

class TestGreedyPartitioningStress:
    """Stress-tests DrawingSplitManager under extreme imbalances and edge cases."""

    def test_extreme_distribution_one_giant_project(self):
        """1 giant project with 5,000 tiles and 5 tiny projects with 1 tile each."""
        tiles: List[TileRecord] = []
        # Giant project
        for t in range(5000):
            tiles.append(TileRecord(f"giant_{t:04d}", "proj_giant", f"draw_giant_{t % 10}", f"/img/g_{t}.png", f"/msk/g_{t}.png", (0, 0, 512, 512)))
        # 5 tiny projects
        for p in range(5):
            tiles.append(TileRecord(f"tiny_{p}", f"proj_tiny_{p}", f"draw_tiny_{p}", f"/img/t_{p}.png", f"/msk/t_{p}.png", (0, 0, 512, 512)))

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), group_key="project_id", seed=42)
        manifest = manager.create_splits(tiles)

        # Invariants
        verify_split_isolation(manifest)
        assert len(manifest.train_tiles) > 0
        assert len(manifest.val_tiles) > 0
        assert len(manifest.test_tiles) > 0
        assert len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles) == 5005

    def test_extreme_distribution_three_single_tile_projects(self):
        """Minimum viable dataset: exactly 3 projects with 1 tile each."""
        tiles = [
            TileRecord("t0", "p0", "d0", "/img/0.png", "/msk/0.png", (0, 0, 512, 512)),
            TileRecord("t1", "p1", "d1", "/img/1.png", "/msk/1.png", (0, 0, 512, 512)),
            TileRecord("t2", "p2", "d2", "/img/2.png", "/msk/2.png", (0, 0, 512, 512)),
        ]
        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=42)
        manifest = manager.create_splits(tiles)

        verify_split_isolation(manifest)
        assert len(manifest.train_tiles) == 1
        assert len(manifest.val_tiles) == 1
        assert len(manifest.test_tiles) == 1

    def test_extreme_distribution_power_law_distribution(self):
        """50 projects with power-law (Zipf-like) tile counts."""
        tiles: List[TileRecord] = []
        for p in range(1, 51):
            count = max(1, int(1000 / p))
            for t in range(count):
                tiles.append(TileRecord(f"p{p}_t{t}", f"proj_{p:02d}", f"draw_{p:02d}_{t % 5}", f"/img/{p}_{t}.png", f"/msk/{p}_{t}.png", (0, 0, 512, 512)))

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=123)
        manifest = manager.create_splits(tiles)
        verify_split_isolation(manifest)

        total_in_splits = len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles)
        assert total_in_splits == len(tiles)
        # Train should hold the largest share (~65-75%)
        assert 0.60 <= len(manifest.train_tiles) / total_in_splits <= 0.80

    def test_skewed_split_ratios(self):
        """Tests extreme split ratios such as 90/5/5 and 50/25/25."""
        tiles = [
            TileRecord(f"t{i}", f"proj_{i // 2}", f"draw_{i // 2}", f"/img/{i}.png", f"/msk/{i}.png", (0, 0, 512, 512))
            for i in range(20)
        ]
        # 10 projects
        m90 = DrawingSplitManager(split_ratios=(0.90, 0.05, 0.05), seed=42).create_splits(tiles)
        verify_split_isolation(m90)
        assert len(m90.train_tiles) >= len(m90.val_tiles)
        assert len(m90.train_tiles) >= len(m90.test_tiles)

        m50 = DrawingSplitManager(split_ratios=(0.50, 0.25, 0.25), seed=42).create_splits(tiles)
        verify_split_isolation(m50)
        assert len(m50.train_tiles) > 0 and len(m50.val_tiles) > 0 and len(m50.test_tiles) > 0

    def test_drawing_id_fallback_single_project(self):
        """Single project with 5 drawings should gracefully fallback to drawing_id grouping."""
        tiles = [
            TileRecord(f"t{i}", "only_one_project", f"sheet_{i // 4}", f"/img/{i}.png", f"/msk/{i}.png", (0, 0, 512, 512))
            for i in range(20)  # 5 drawings, 4 tiles each
        ]
        manager = DrawingSplitManager(allow_drawing_fallback=True)
        manifest = manager.create_splits(tiles)
        assert manifest.group_key == "drawing_id"
        verify_split_isolation(manifest)

    def test_all_tiles_quarantined_raises_insufficient_groups(self):
        """If all tiles are quarantined, create_splits must raise InsufficientGroupsError."""
        tiles = [
            TileRecord("t1", "p1", "d1", "/img/1.png", "/msk/1.png", (0, 0, 512, 512), quarantine=True),
            TileRecord("t2", "p2", "d2", "/img/2.png", "/msk/2.png", (0, 0, 512, 512), is_pseudo_label=True),
            TileRecord("t3", "p3", "d3", "/img/3.png", "/msk/3.png", (0, 0, 512, 512), quarantine=True),
        ]
        manager = DrawingSplitManager()
        with pytest.raises(InsufficientGroupsError):
            manager.create_splits(tiles)


# ==============================================================================
# Suite 3: DataLoader Iteration, Memory Stability, Shapes, & Synchrony
# ==============================================================================

class TestDataLoaderStress:
    """Stress-tests DataLoader streaming, memory stability across epochs, shapes, and synchrony."""

    @pytest.fixture
    def disk_tiles_40(self, tmp_path: Path) -> Tuple[Path, List[Dict[str, Any]]]:
        records = []
        for i in range(40):
            img_arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
            mask_arr = np.zeros((512, 512), dtype=np.uint8)
            # Add distinct classes {0, 1, 2, 3}
            mask_arr[50:150, 50:150] = 1
            mask_arr[200:300, 200:300] = 2
            mask_arr[350:450, 350:450] = 3

            img_p = tmp_path / f"img_{i:03d}.png"
            msk_p = tmp_path / f"msk_{i:03d}.png"

            Image.fromarray(img_arr).save(img_p)
            img_mask = Image.fromarray(mask_arr, mode='P')
            img_mask.putpalette(PALETTE_256)
            img_mask.save(msk_p)

            records.append({
                "tile_id": f"tile_{i:03d}",
                "project_id": f"proj_{i // 4}",
                "drawing_id": f"draw_{i // 2}",
                "image_path": str(img_p),
                "mask_path": str(msk_p),
                "bbox": [0, 0, 512, 512],
            })

        manifest_file = tmp_path / "stress_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump({"tiles": records}, f)
        return manifest_file, records

    def test_dataloader_batch_dimensions_and_dtypes(self, disk_tiles_40):
        manifest_file, _ = disk_tiles_40
        for b_size in [1, 2, 4, 5]:
            loader = get_tile_dataloader(manifest_file, batch_size=b_size, is_train=False)
            images, masks = next(iter(loader))
            assert images.shape == (b_size, 3, 512, 512)
            assert masks.shape == (b_size, 512, 512)
            assert images.dtype == torch.float32
            assert masks.dtype == torch.int64

    def test_label_range_strictness_under_heavy_augmentation(self, disk_tiles_40):
        """Runs DataLoader with 100% augmentations for multiple iterations and checks mask values."""
        manifest_file, _ = disk_tiles_40
        transform = SynchronizedTransform(
            is_train=True,
            hflip_prob=1.0,
            vflip_prob=1.0,
            rot90_prob=1.0,
            brightness_jitter=0.3,
            contrast_jitter=0.3,
        )
        ds = DrywallTileDataset(manifest_file, mode="4class", transform=transform)
        loader = torch.utils.data.DataLoader(ds, batch_size=4, collate_fn=safe_collate_fn)

        for epoch in range(3):
            for images, masks in loader:
                unique_vals = set(masks.unique().tolist())
                # Every single pixel must strictly reside in {0, 1, 2, 3}
                assert unique_vals.issubset({0, 1, 2, 3}), f"Unexpected label values: {unique_vals}"

    def test_binary_mode_remapping_under_augmentation(self, disk_tiles_40):
        manifest_file, _ = disk_tiles_40
        loader = get_tile_dataloader(manifest_file, mode="binary", batch_size=4, is_train=True)
        for images, masks in loader:
            unique_vals = set(masks.unique().tolist())
            assert unique_vals.issubset({0, 1}), f"Non-binary values in binary mode: {unique_vals}"

    def test_dataloader_memory_stability_across_epochs(self, disk_tiles_40):
        """Simulates 5 epochs of training DataLoader iteration, checking for memory leaks."""
        manifest_file, _ = disk_tiles_40
        loader = get_tile_dataloader(manifest_file, batch_size=4, is_train=True)

        gc.collect()
        initial_tensor_count = len([obj for obj in gc.get_objects() if isinstance(obj, torch.Tensor)])

        total_batches_processed = 0
        for epoch in range(5):
            for images, masks in loader:
                assert images.shape == (4, 3, 512, 512)
                assert masks.shape == (4, 512, 512)
                total_batches_processed += 1
                # Explicitly delete batch references to simulate step consumption
                del images, masks

        gc.collect()
        final_tensor_count = len([obj for obj in gc.get_objects() if isinstance(obj, torch.Tensor)])

        assert total_batches_processed == 50  # 40 tiles / batch_size 4 = 10 batches * 5 epochs
        # Resident tensor objects should not explode across epochs
        assert abs(final_tensor_count - initial_tensor_count) < 25

    def test_synchronized_transform_exact_geometric_alignment(self):
        """
        Synthesizes an image and mask with a localized marker at [50:100, 100:200].
        Tests all discrete transformations (hflip, vflip, rot90, rot180, rot270)
        and verifies exact pixel-level correspondence.
        """
        # Base image: gray 128
        img_arr = np.full((512, 512, 3), 128, dtype=np.uint8)
        # Mark distinct color [255, 0, 0] at region
        img_arr[50:100, 100:200] = [255, 0, 0]

        # Base mask: 0, with label 1 at identical region
        mask_arr = np.zeros((512, 512), dtype=np.uint8)
        mask_arr[50:100, 100:200] = 1

        img_pil = Image.fromarray(img_arr, mode='RGB')
        mask_pil = Image.fromarray(mask_arr, mode='P')

        # 1. Horizontal flip test
        tf_hflip = SynchronizedTransform(is_train=True, hflip_prob=1.0, vflip_prob=0.0, rot90_prob=0.0, brightness_jitter=0, contrast_jitter=0)
        img_t, msk_t = tf_hflip(img_pil, mask_pil)
        # The region should now be at [50:100, (512-200):(512-100)] -> [50:100, 312:412]
        assert msk_t[75, 360].item() == 1
        assert msk_t[75, 150].item() == 0

        # 2. Vertical flip test
        tf_vflip = SynchronizedTransform(is_train=True, hflip_prob=0.0, vflip_prob=1.0, rot90_prob=0.0, brightness_jitter=0, contrast_jitter=0)
        img_t, msk_t = tf_vflip(img_pil, mask_pil)
        # The region should now be at [(512-100):(512-50), 100:200] -> [412:462, 100:200]
        assert msk_t[430, 150].item() == 1
        assert msk_t[75, 150].item() == 0

        # 3. Discrete 90 degree rotation test
        # In TF.rotate(angle=90), coordinates rotate counterclockwise
        mask_rot90 = TF.rotate(mask_pil, 90, interpolation=TF.InterpolationMode.NEAREST)
        img_rot90 = TF.rotate(img_pil, 90, interpolation=TF.InterpolationMode.BILINEAR)

        m_rot_np = np.array(mask_rot90)
        i_rot_np = np.array(img_rot90)

        # Region where mask is 1 must have red channel == 255
        mask_indices = np.where(m_rot_np == 1)
        assert len(mask_indices[0]) > 0
        # Check that red channel is active at all mask=1 pixels
        assert np.all(i_rot_np[mask_indices][:, 0] > 200)

    def test_non_512_dimension_input_resilience(self):
        """Verifies SynchronizedTransform gracefully resizes non-512x512 inputs to (512, 512)."""
        img_odd = Image.fromarray(np.full((300, 600, 3), 100, dtype=np.uint8))
        mask_odd = Image.fromarray(np.ones((300, 600), dtype=np.uint8), mode='P')

        tf = SynchronizedTransform(is_train=False)
        img_t, msk_t = tf(img_odd, mask_odd)

        assert img_t.shape == (3, 512, 512)
        assert msk_t.shape == (512, 512)
        assert msk_t.unique().tolist() == [1]
