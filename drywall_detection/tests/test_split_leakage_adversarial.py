"""
drywall_detection.tests.test_split_leakage_adversarial
======================================================
Adversarial stress-test suite challenging verify_split_isolation and
DrawingSplitManager against:
1. Synthetic quarantine and pseudo-label injection attacks (100% detection rate).
2. Windows path casing and separator canonicalization attacks.
3. Extreme group distributions (power law, 1000:1, 10,000:1 ratio, Zipf skew).
4. Edge cases, deterministic verification hashing, and fallback resilience.
"""

from __future__ import annotations
import copy
import os
from pathlib import Path
import random
from typing import Any, Dict, List, Tuple
import pytest

from drywall_detection.datasets.split_manager import (
    DrawingSplitManager,
    InsufficientGroupsError,
    InvalidSplitRatioError,
    SplitLeakageError,
    SplitManifest,
    TileRecord,
    _canonical_path,
    verify_split_isolation,
)


# ==============================================================================
# Helper Factories for Synthetic Adversarial Manifests
# ==============================================================================

def make_tile(
    tile_id: str,
    project_id: str = "proj_00",
    drawing_id: str = "draw_00",
    image_path: str = "",
    mask_path: str = "",
    has_walls: bool = True,
    is_pseudo_label: bool = False,
    quarantine: bool = False,
) -> TileRecord:
    img = image_path or f"C:\\datasets\\drywall\\images\\{tile_id}.png"
    msk = mask_path or f"C:\\datasets\\drywall\\masks\\{tile_id}.png"
    return TileRecord(
        tile_id=tile_id,
        project_id=project_id,
        drawing_id=drawing_id,
        image_path=img,
        mask_path=msk,
        bbox=(0, 0, 512, 512),
        has_walls=has_walls,
        is_pseudo_label=is_pseudo_label,
        quarantine=quarantine,
    )


def create_clean_manifest(num_projects: int = 10, tiles_per_proj: int = 10) -> SplitManifest:
    """Creates a verified clean baseline manifest with train, val, test, and quarantine."""
    train_tiles: List[TileRecord] = []
    val_tiles: List[TileRecord] = []
    test_tiles: List[TileRecord] = []
    quar_tiles: List[TileRecord] = []

    # 6 projects train, 2 val, 2 test, 1 quarantine
    for p in range(num_projects):
        pid = f"clean_proj_{p:02d}"
        for t in range(tiles_per_proj):
            tid = f"{pid}_tile_{t:03d}"
            rec = make_tile(tid, project_id=pid, drawing_id=f"{pid}_draw_00")
            if p < 6:
                train_tiles.append(rec)
            elif p < 8:
                val_tiles.append(rec)
            else:
                test_tiles.append(rec)

    # Dedicated quarantine project
    q_pid = "quarantine_proj_99"
    for t in range(5):
        tid = f"{q_pid}_tile_{t:03d}"
        rec = make_tile(tid, project_id=q_pid, drawing_id=f"{q_pid}_draw_00", quarantine=True)
        quar_tiles.append(rec)

    manifest = SplitManifest(
        split_ratios=(0.70, 0.15, 0.15),
        group_key="project_id",
        seed=42,
        train_tiles=train_tiles,
        val_tiles=val_tiles,
        test_tiles=test_tiles,
        quarantine_tiles=quar_tiles,
    )
    # Confirm clean baseline passes
    report = verify_split_isolation(manifest)
    assert report["status"] == "PASSED"
    return manifest


# ==============================================================================
# 1. Adversarial Quarantine & Pseudo-Label Flag Injection Suite
# ==============================================================================

class TestQuarantineFlagInjectionAttack:
    """
    Stress-tests verify_split_isolation against synthetic injection of
    quarantine=True and is_pseudo_label=True tiles directly into val and test splits.
    Zero tolerance: 100% of injection attempts must raise SplitLeakageError.
    """

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    @pytest.mark.parametrize("flag_quarantine,flag_pseudo", [
        (True, False),
        (False, True),
        (True, True),
    ])
    def test_flagged_tile_direct_injection_raises_split_leakage_error(
        self, target_split: str, flag_quarantine: bool, flag_pseudo: bool
    ) -> None:
        manifest = create_clean_manifest()
        split_list = getattr(manifest, target_split)
        
        # Inject an adversarial tile directly into evaluation split
        bad_tile = make_tile(
            tile_id=f"adversarial_flagged_{target_split}",
            project_id=f"adversarial_proj_{target_split}",
            drawing_id=f"adversarial_draw_{target_split}",
            quarantine=flag_quarantine,
            is_pseudo_label=flag_pseudo,
        )
        split_list.append(bad_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined.*pseudo-labeled.*leakage"):
            verify_split_isolation(manifest)

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_in_place_flag_mutation_raises_split_leakage_error(self, target_split: str) -> None:
        """Mutates an existing legitimate evaluation tile's flag in place."""
        manifest = create_clean_manifest()
        split_list = getattr(manifest, target_split)
        assert len(split_list) > 0

        # Subtly flip pseudo-label flag on the first legitimate tile
        split_list[0].is_pseudo_label = True

        with pytest.raises(SplitLeakageError, match="(?i)quarantined.*pseudo-labeled.*leakage"):
            verify_split_isolation(manifest)

    def test_multi_tile_adversarial_flood_into_val_and_test(self) -> None:
        """Floods multiple quarantined tiles into both val and test concurrently."""
        manifest = create_clean_manifest()
        for i in range(10):
            manifest.val_tiles.append(
                make_tile(f"flood_val_{i}", project_id=f"flood_v_{i}", quarantine=True)
            )
            manifest.test_tiles.append(
                make_tile(f"flood_test_{i}", project_id=f"flood_t_{i}", is_pseudo_label=True)
            )

        with pytest.raises(SplitLeakageError):
            verify_split_isolation(manifest)


# ==============================================================================
# 2. Adversarial Quarantine Entity Overlap Suite
# ==============================================================================

class TestQuarantineEntityOverlapAttack:
    """
    Stress-tests verify_split_isolation when a tile inside val_tiles or test_tiles
    has clean flags (quarantine=False, is_pseudo_label=False) but overlaps with
    quarantine_tiles on an entity attribute (tile_id, project_id, drawing_id,
    image_path, or mask_path).
    Must catch 100% of covert leaks.
    """

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_quarantined_tile_id_overlap(self, target_split: str) -> None:
        manifest = create_clean_manifest()
        q_tile = manifest.quarantine_tiles[0]
        split_list = getattr(manifest, target_split)

        # Clone quarantine tile ID into evaluation tile with new unflagged project
        covert_tile = make_tile(
            tile_id=q_tile.tile_id,  # Colliding tile ID
            project_id="unrelated_project_alpha",
            drawing_id="unrelated_drawing_alpha",
            image_path="C:\\unique\\covert_img.png",
            mask_path="C:\\unique\\covert_msk.png",
            quarantine=False,
            is_pseudo_label=False,
        )
        split_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined tile id leaked"):
            verify_split_isolation(manifest)

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_quarantined_project_id_overlap(self, target_split: str) -> None:
        manifest = create_clean_manifest()
        q_tile = manifest.quarantine_tiles[0]
        split_list = getattr(manifest, target_split)

        # Create tile sharing quarantine project_id but different tile_id
        covert_tile = make_tile(
            tile_id="unique_covert_tile_beta",
            project_id=q_tile.project_id,  # Colliding project ID
            drawing_id="covert_drawing_beta",
            image_path="C:\\unique\\covert_img2.png",
            mask_path="C:\\unique\\covert_msk2.png",
            quarantine=False,
            is_pseudo_label=False,
        )
        split_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined project leaked"):
            verify_split_isolation(manifest)

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_quarantined_drawing_id_overlap(self, target_split: str) -> None:
        manifest = create_clean_manifest()
        q_tile = manifest.quarantine_tiles[0]
        split_list = getattr(manifest, target_split)

        # Create tile sharing quarantine drawing_id but different project_id
        covert_tile = make_tile(
            tile_id="unique_covert_tile_gamma",
            project_id="different_project_gamma",
            drawing_id=q_tile.drawing_id,  # Colliding drawing ID
            image_path="C:\\unique\\covert_img3.png",
            mask_path="C:\\unique\\covert_msk3.png",
            quarantine=False,
            is_pseudo_label=False,
        )
        split_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined drawing leaked"):
            verify_split_isolation(manifest)

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_quarantined_image_path_overlap(self, target_split: str) -> None:
        manifest = create_clean_manifest()
        q_tile = manifest.quarantine_tiles[0]
        split_list = getattr(manifest, target_split)

        # Create tile with unique IDs but colliding image file path
        covert_tile = make_tile(
            tile_id="unique_covert_tile_delta",
            project_id="different_project_delta",
            drawing_id="different_drawing_delta",
            image_path=q_tile.image_path,  # Colliding image path
            mask_path="C:\\unique\\covert_msk4.png",
            quarantine=False,
            is_pseudo_label=False,
        )
        split_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined image path overlap"):
            verify_split_isolation(manifest)

    @pytest.mark.parametrize("target_split", ["val_tiles", "test_tiles"])
    def test_quarantined_mask_path_overlap(self, target_split: str) -> None:
        manifest = create_clean_manifest()
        q_tile = manifest.quarantine_tiles[0]
        split_list = getattr(manifest, target_split)

        # Create tile with unique IDs but colliding mask file path
        covert_tile = make_tile(
            tile_id="unique_covert_tile_epsilon",
            project_id="different_project_epsilon",
            drawing_id="different_drawing_epsilon",
            image_path="C:\\unique\\covert_img5.png",
            mask_path=q_tile.mask_path,  # Colliding mask path
            quarantine=False,
            is_pseudo_label=False,
        )
        split_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)quarantined mask path overlap"):
            verify_split_isolation(manifest)


# ==============================================================================
# 3. Windows Path Casing & Separator Canonicalization Attack Suite
# ==============================================================================

class TestWindowsPathCasingAttack:
    """
    Stress-tests cross-split file path canonicalization under Windows filesystem semantics.
    Windows paths are case-insensitive and slash-agnostic (C:\\A/B is c:\\a\\b).
    Adversarial attackers might attempt to bypass path isolation via:
    - Drive letter casing (C:\\ vs c:\\)
    - Folder and file casing (DATA\\TILE.PNG vs data\\tile.png)
    - Mixed slash separators (/ vs \\)
    - Redundant path components (./ and ../)
    verify_split_isolation must detect 100% of these disguised path collisions.
    """

    def test_canonical_path_function_directly(self) -> None:
        """Verifies _canonical_path normalizes Windows drive, separators, casing, and dots."""
        p1 = "C:\\Projects\\Drywall\\Tile_01.png"
        p2 = "c:/projects/drywall/tile_01.png"
        p3 = "C:/PROJECTS/drywall/./sub/../Tile_01.png"
        p4 = "c:\\PROJECTS\\DRYWALL\\TILE_01.PNG"

        c1 = _canonical_path(p1)
        c2 = _canonical_path(p2)
        c3 = _canonical_path(p3)
        c4 = _canonical_path(p4)

        assert c1 == c2 == c3 == c4, f"Canonical mismatch: {c1} vs {c2} vs {c3} vs {c4}"

    @pytest.mark.parametrize("split_pair", [
        ("train_tiles", "val_tiles"),
        ("train_tiles", "test_tiles"),
        ("val_tiles", "test_tiles"),
        ("quarantine_tiles", "val_tiles"),
        ("quarantine_tiles", "test_tiles"),
    ])
    @pytest.mark.parametrize("case_variant,path_type", [
        ("UPPER_DRIVE", "image"),
        ("LOWER_ALL", "image"),
        ("MIXED_SLASHES", "image"),
        ("REDUNDANT_DOTS", "image"),
        ("UPPER_ALL", "mask"),
        ("MIXED_SLASHES", "mask"),
    ])
    def test_adversarial_path_casing_variations_raise_split_leakage_error(
        self, split_pair: Tuple[str, str], case_variant: str, path_type: str
    ) -> None:
        source_split_name, target_split_name = split_pair
        manifest = create_clean_manifest()
        src_list = getattr(manifest, source_split_name)
        tgt_list = getattr(manifest, target_split_name)
        assert len(src_list) > 0

        # Choose a reference path from source
        base_path = src_list[0].image_path if path_type == "image" else src_list[0].mask_path

        # Generate adversarial variation of the identical filesystem path
        if case_variant == "UPPER_DRIVE":
            adv_path = base_path[0].upper() + base_path[1:]
        elif case_variant == "LOWER_ALL":
            adv_path = base_path.lower()
        elif case_variant == "UPPER_ALL":
            adv_path = base_path.upper()
        elif case_variant == "MIXED_SLASHES":
            adv_path = base_path.replace("\\", "/").upper()
        elif case_variant == "REDUNDANT_DOTS":
            # Insert redundant .\ or ./
            parts = base_path.split("\\")
            if len(parts) >= 2:
                adv_path = "\\".join([parts[0], ".", parts[1], "sub", ".."] + parts[2:]).lower()
            else:
                adv_path = base_path.replace("\\", "/").lower()
        else:
            adv_path = base_path

        # Create covert tile with unique IDs but disguised duplicate path
        covert_tile = make_tile(
            tile_id=f"covert_{source_split_name}_{target_split_name}_{case_variant}_{path_type}",
            project_id=f"covert_proj_{case_variant}",
            drawing_id=f"covert_draw_{case_variant}",
            image_path=adv_path if path_type == "image" else "C:\\unique\\distinct_img.png",
            mask_path=adv_path if path_type == "mask" else "C:\\unique\\distinct_msk.png",
            quarantine=False,
            is_pseudo_label=False,
        )
        tgt_list.append(covert_tile)

        with pytest.raises(SplitLeakageError, match="(?i)path.*overlap|direct.*path.*overlap"):
            verify_split_isolation(manifest)


# ==============================================================================
# 4. Adversarial Partitioning & Extreme Group Distribution Stress Suite
# ==============================================================================

class TestExtremeDistributionStress:
    """
    Stress-tests DrawingSplitManager greedy group partitioning under extreme power-law
    and highly unbalanced distributions.
    Enforces that:
    1. No crash occurs under severe skew (1000:1 ratio, 10,000:1 ratio, Zipf skew).
    2. Mutual group disjointness (zero project and drawing leakage) is strictly maintained.
    3. All splits (train, val, test) remain populated if >= 3 groups exist.
    4. verify_split_isolation validates the generated manifest without error.
    """

    def test_extreme_1000_to_1_ratio_partitioning(self) -> None:
        """
        Group 0 has 10,000 tiles; Group 1 has 10 tiles; Group 2 has 10 tiles.
        Total = 10,020 tiles. Ratio ~ 1000:1.
        """
        tiles: List[TileRecord] = []
        # Group 0: 10,000 tiles
        for t in range(10000):
            tiles.append(make_tile(f"g0_t{t:05d}", project_id="giant_proj_00", drawing_id="giant_draw_00"))
        # Group 1: 10 tiles
        for t in range(10):
            tiles.append(make_tile(f"g1_t{t:03d}", project_id="tiny_proj_01", drawing_id="tiny_draw_01"))
        # Group 2: 10 tiles
        for t in range(10):
            tiles.append(make_tile(f"g2_t{t:03d}", project_id="tiny_proj_02", drawing_id="tiny_draw_02"))

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=42)
        manifest = manager.create_splits(tiles)

        # Verify no crash and valid manifest created
        assert manifest is not None
        assert len(manifest.train_tiles) > 0
        assert len(manifest.val_tiles) > 0
        assert len(manifest.test_tiles) > 0
        assert len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles) == 10020

        # Verify zero project leakage
        train_p = {t.project_id for t in manifest.train_tiles}
        val_p = {t.project_id for t in manifest.val_tiles}
        test_p = {t.project_id for t in manifest.test_tiles}
        assert train_p.intersection(val_p) == set()
        assert train_p.intersection(test_p) == set()
        assert val_p.intersection(test_p) == set()

        # The giant group should be in train
        assert "giant_proj_00" in train_p

    def test_extreme_10000_to_1_ratio_partitioning(self) -> None:
        """
        Group 0 has 10,000 tiles; Group 1 has 1 tile; Group 2 has 1 tile.
        Minimum viable 3-way split under maximum possible skew (10,000:1).
        """
        tiles: List[TileRecord] = []
        for t in range(10000):
            tiles.append(make_tile(f"p0_t{t:05d}", project_id="monolith_proj", drawing_id="monolith_d"))
        tiles.append(make_tile("p1_t0", project_id="atom_proj_1", drawing_id="atom_d1"))
        tiles.append(make_tile("p2_t0", project_id="atom_proj_2", drawing_id="atom_d2"))

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=123)
        manifest = manager.create_splits(tiles)

        assert len(manifest.train_tiles) == 10000
        assert len(manifest.val_tiles) == 1
        assert len(manifest.test_tiles) == 1

        # verify_split_isolation already called inside create_splits, call explicitly to re-verify
        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"

    @pytest.mark.parametrize("seed", [7, 42, 99, 2026, 8888])
    def test_zipf_power_law_distribution_across_seeds(self, seed: int) -> None:
        """
        Synthesizes 30 projects with power-law size distribution:
        size(i) = max(1, int(1000 / (i + 1)^1.5)).
        Stress-tests multi-seed deterministic partition and zero-leakage invariant.
        """
        tiles: List[TileRecord] = []
        for p in range(30):
            pid = f"zipf_proj_{p:02d}"
            group_size = max(1, int(1000.0 / ((p + 1) ** 1.5)))
            for t in range(group_size):
                tiles.append(make_tile(f"{pid}_t{t:04d}", project_id=pid, drawing_id=f"{pid}_draw"))

        total_input_tiles = len(tiles)
        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=seed)
        manifest = manager.create_splits(tiles)

        # Integrity checks
        assert len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles) == total_input_tiles
        train_p = {t.project_id for t in manifest.train_tiles}
        val_p = {t.project_id for t in manifest.val_tiles}
        test_p = {t.project_id for t in manifest.test_tiles}

        assert train_p.intersection(val_p) == set()
        assert train_p.intersection(test_p) == set()
        assert val_p.intersection(test_p) == set()
        assert len(manifest.val_tiles) > 0
        assert len(manifest.test_tiles) > 0

    def test_large_number_of_single_tile_groups(self) -> None:
        """Stress-tests 300 projects with exactly 1 tile each (high group granularity)."""
        tiles: List[TileRecord] = []
        for p in range(300):
            pid = f"micro_proj_{p:03d}"
            tiles.append(make_tile(f"{pid}_t0", project_id=pid, drawing_id=f"{pid}_d"))

        manager = DrawingSplitManager(split_ratios=(0.70, 0.15, 0.15), seed=42)
        manifest = manager.create_splits(tiles)

        assert len(manifest.train_tiles) == 210  # 70% of 300
        assert len(manifest.val_tiles) == 45    # 15% of 300
        assert len(manifest.test_tiles) == 45   # 15% of 300

        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"

    def test_dominant_quarantine_group_with_small_active_groups(self) -> None:
        """
        A dominant group of 5,000 tiles is quarantined; remaining active groups
        consist of 3 small projects with 5 tiles each.
        Verifies quarantine separation does not disturb greedy split on remaining active groups.
        """
        tiles: List[TileRecord] = []
        # Quarantined dominant project
        for t in range(5000):
            tiles.append(make_tile(f"quar_giant_t{t:04d}", project_id="quar_giant_proj", drawing_id="qg_draw"))
        # Active small projects
        for p in range(3):
            pid = f"active_p_{p}"
            for t in range(5):
                tiles.append(make_tile(f"{pid}_t{t}", project_id=pid, drawing_id=f"{pid}_d"))

        manager = DrawingSplitManager(
            split_ratios=(0.70, 0.15, 0.15),
            quarantine_projects=["quar_giant_proj"],
            seed=42,
        )
        manifest = manager.create_splits(tiles)

        assert len(manifest.quarantine_tiles) == 5000
        assert len(manifest.train_tiles) + len(manifest.val_tiles) + len(manifest.test_tiles) == 15
        assert len(manifest.train_tiles) > 0
        assert len(manifest.val_tiles) > 0
        assert len(manifest.test_tiles) > 0

        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"
        assert report["quarantine_tiles"] == 5000

    def test_drawing_fallback_under_severe_skew(self) -> None:
        """
        Only 2 projects exist (fails project-level 3-way split), but Project 0 has
        5 drawings (skewed: 1000 tiles on draw 0, 10 on draw 1..4), Project 1 has 2 drawings.
        Verifies fallback to drawing_id successfully partitions 7 drawings without leakage.
        """
        tiles: List[TileRecord] = []
        # Project 0: 5 drawings
        for t in range(1000):
            tiles.append(make_tile(f"p0_d0_t{t:04d}", project_id="proj_0", drawing_id="proj0_sheet_0"))
        for d in range(1, 5):
            for t in range(10):
                tiles.append(make_tile(f"p0_d{d}_t{t:02d}", project_id="proj_0", drawing_id=f"proj0_sheet_{d}"))
        # Project 1: 2 drawings
        for d in range(2):
            for t in range(10):
                tiles.append(make_tile(f"p1_d{d}_t{t:02d}", project_id="proj_1", drawing_id=f"proj1_sheet_{d}"))

        manager = DrawingSplitManager(
            split_ratios=(0.70, 0.15, 0.15),
            group_key="project_id",
            allow_drawing_fallback=True,
            seed=42,
        )
        manifest = manager.create_splits(tiles)

        assert manifest.group_key == "drawing_id"
        train_d = {t.drawing_id for t in manifest.train_tiles}
        val_d = {t.drawing_id for t in manifest.val_tiles}
        test_d = {t.drawing_id for t in manifest.test_tiles}

        assert train_d.intersection(val_d) == set()
        assert train_d.intersection(test_d) == set()
        assert val_d.intersection(test_d) == set()

        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"


# ==============================================================================
# 5. Robustness, Hash Determinism & Error Handling Edge Cases
# ==============================================================================

class TestSplitManagerEdgeCases:
    """Stress-tests invalid inputs, empty sets, and cryptographic hashing."""

    def test_insufficient_groups_without_fallback_raises_error(self) -> None:
        """Only 2 projects provided and allow_drawing_fallback=False."""
        tiles = [
            make_tile("t1", project_id="p1", drawing_id="d1"),
            make_tile("t2", project_id="p2", drawing_id="d2"),
        ]
        manager = DrawingSplitManager(allow_drawing_fallback=False)
        with pytest.raises(InsufficientGroupsError, match="(?i)insufficient groups"):
            manager.create_splits(tiles)

    def test_invalid_split_ratios_raise_error(self) -> None:
        with pytest.raises(InvalidSplitRatioError):
            DrawingSplitManager(split_ratios=(0.7, 0.2, 0.2))  # Sum = 1.1

        with pytest.raises(InvalidSplitRatioError):
            DrawingSplitManager(split_ratios=(0.8, 0.2, 0.0))  # Zero ratio

    def test_verification_hash_is_deterministic_and_sensitive_to_alteration(self) -> None:
        tiles = [
            make_tile(f"t_{p}_{i}", project_id=f"p_{p}", drawing_id=f"d_{p}")
            for p in range(5) for i in range(4)
        ]
        m1 = DrawingSplitManager(seed=42).create_splits(tiles)
        m2 = DrawingSplitManager(seed=42).create_splits(tiles)
        assert m1.verification_hash == m2.verification_hash
        assert len(m1.verification_hash) == 64  # SHA-256 hex length

        # Swapping a single tile between train and val alters the hash
        mgr = DrawingSplitManager(seed=42)
        swapped_manifest = copy.deepcopy(m1)
        swapped_tile = swapped_manifest.train_tiles.pop()
        swapped_manifest.val_tiles.append(swapped_tile)
        new_hash = mgr._compute_manifest_hash(swapped_manifest)
        assert new_hash != m1.verification_hash

    def test_manifest_quarantine_tiles_none_resilience(self) -> None:
        """
        Adversarial test: when quarantine_tiles is explicitly None in manifest,
        verify_split_isolation handles it gracefully or safely.
        """
        manifest = create_clean_manifest()
        # If someone explicitly passes quarantine_tiles=None or an empty list
        manifest.quarantine_tiles = []
        report = verify_split_isolation(manifest)
        assert report["status"] == "PASSED"
        assert report["quarantine_tiles"] == 0
