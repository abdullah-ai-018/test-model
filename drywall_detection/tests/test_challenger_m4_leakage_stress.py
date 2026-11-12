"""
drywall_detection.tests.test_challenger_m4_leakage_stress
=========================================================
Empirical challenger stress-test battery for Milestone M4:
1. assert_zero_leakage_manifests under adversarial and corrupted manifests:
   - Project leakage (train-val, train-test, val-test)
   - Drawing leakage (train-val, train-test, val-test)
   - Image and tile path leakage
   - Quarantine and pseudo-label infiltration into val/test
   - Manifest corruption (syntax errors, missing files, format variants)
   - Adversarial subtle vulnerabilities (path normalization & mask_path leakage)
2. Pseudo-label discount weighting (lambda=0.35) and CAD quarantine verification:
   - Mathematical and empirical gradient downweighting (exact ratio ||g_pseudo - 0.35 * g_sup|| < 1e-5)
   - Multiple discount factors (0.0, 0.5, 0.75, 1.0)
   - Strict CAD tile quarantine in official split manifests
   - Dataset loader metadata propagation audit
3. Standalone infer.py (StandaloneInferencer) stress tests:
   - Tiny images (32x32)
   - Odd non-divisible dimensions (733x521)
   - Pure noise inputs (uniform random and Gaussian)
   - Large image sliding-window stitching and memory profiling
   - Boundary edge cases (1x1, extreme aspect ratios, solid black/white, grayscale)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import tempfile
import tracemalloc
from typing import Any, Dict, List

import numpy as np
from PIL import Image
import pytest
import torch
import torch.nn as nn

from drywall_detection.models.metrics import assert_zero_leakage_manifests
from drywall_detection.models.trainer import Trainer, verify_split_isolation
from drywall_detection.models.unet import LightweightUNet
from drywall_detection.models.losses import CompoundSegmentationLoss
from drywall_detection.datasets.loader import DrywallTileDataset, get_tile_dataloader
from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer

logger = logging.getLogger(__name__)


# ==============================================================================
# Helper Mock Loaders & Optimizers
# ==============================================================================

class DummySingleBatchLoader:
    """Mock DataLoader yielding a single pre-configured batch."""
    def __init__(self, batch: Any) -> None:
        self.batch = batch

    def __iter__(self):
        yield self.batch

    def __len__(self) -> int:
        return 1


class GradientCapturingOptimizer(torch.optim.Optimizer):
    """Mock optimizer that records parameter gradients before zero_grad."""
    def __init__(self, params, lr: float = 1e-4) -> None:
        self.params = list(params)
        self.captured_grads: List[torch.Tensor] = []
        super().__init__(self.params, defaults={"lr": lr})

    def step(self, closure=None):
        self.captured_grads = [p.grad.clone() for p in self.params if p.grad is not None]

    def zero_grad(self, set_to_none: bool = False):
        for p in self.params:
            p.grad = None


def create_manifest(path: Path, tiles: List[Dict[str, Any]], key: str = "tiles") -> Path:
    """Helper creating a test manifest JSON file."""
    data = {key: tiles}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ==============================================================================
# 1. ASSERT_ZERO_LEAKAGE_MANIFESTS ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestAssertZeroLeakageManifestsStress:
    """Adversarial stress testing of manifest split integrity assertion gate."""

    @pytest.fixture
    def manifest_env(self, tmp_path):
        train_p = tmp_path / "train.json"
        val_p = tmp_path / "val.json"
        test_p = tmp_path / "test.json"
        return train_p, val_p, test_p

    def test_clean_split_manifests_pass(self, manifest_env):
        """Disjoint manifests pass without error."""
        t_path, v_path, te_path = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "proj_A", "drawing_id": "draw_A", "image_path": "a.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "proj_B", "drawing_id": "draw_B", "image_path": "b.png"}])
        create_manifest(te_path, [{"sample_id": "te1", "project_id": "proj_C", "drawing_id": "draw_C", "image_path": "c.png"}])

        # Should execute cleanly without raising
        assert_zero_leakage_manifests(t_path, v_path, te_path)

    @pytest.mark.parametrize("pair", [("train", "val"), ("train", "test"), ("val", "test")])
    def test_shared_project_id_raises_runtime_error(self, manifest_env, pair):
        """Project overlap between any pair of splits must raise RuntimeError."""
        t_path, v_path, te_path = manifest_env
        s1, s2 = pair

        tiles = {
            "train": [{"sample_id": "t1", "project_id": "SHARED_PROJ" if "train" in (s1, s2) else "proj_t", "drawing_id": "d_t", "image_path": "t.png"}],
            "val": [{"sample_id": "v1", "project_id": "SHARED_PROJ" if "val" in (s1, s2) else "proj_v", "drawing_id": "d_v", "image_path": "v.png"}],
            "test": [{"sample_id": "te1", "project_id": "SHARED_PROJ" if "test" in (s1, s2) else "proj_te", "drawing_id": "d_te", "image_path": "te.png"}],
        }

        create_manifest(t_path, tiles["train"])
        create_manifest(v_path, tiles["val"])
        create_manifest(te_path, tiles["test"])

        with pytest.raises(RuntimeError, match="Projects leaked"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    @pytest.mark.parametrize("pair", [("train", "val"), ("train", "test"), ("val", "test")])
    def test_shared_drawing_id_raises_runtime_error(self, manifest_env, pair):
        """Drawing ID overlap between any pair of splits must raise RuntimeError."""
        t_path, v_path, te_path = manifest_env
        s1, s2 = pair

        tiles = {
            "train": [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "SHARED_DRAW" if "train" in (s1, s2) else "d_t", "image_path": "t.png"}],
            "val": [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "SHARED_DRAW" if "val" in (s1, s2) else "d_v", "image_path": "v.png"}],
            "test": [{"sample_id": "te1", "project_id": "p_te", "drawing_id": "SHARED_DRAW" if "test" in (s1, s2) else "d_te", "image_path": "te.png"}],
        }

        create_manifest(t_path, tiles["train"])
        create_manifest(v_path, tiles["val"])
        create_manifest(te_path, tiles["test"])

        with pytest.raises(RuntimeError, match="Drawings leaked"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    @pytest.mark.parametrize("pair", [("train", "val"), ("train", "test"), ("val", "test")])
    def test_shared_image_path_raises_runtime_error(self, manifest_env, pair):
        """Image path overlap between any pair of splits must raise RuntimeError."""
        t_path, v_path, te_path = manifest_env
        s1, s2 = pair

        tiles = {
            "train": [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "shared_image.png" if "train" in (s1, s2) else "t.png"}],
            "val": [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "shared_image.png" if "val" in (s1, s2) else "v.png"}],
            "test": [{"sample_id": "te1", "project_id": "p_te", "drawing_id": "d_te", "image_path": "shared_image.png" if "test" in (s1, s2) else "te.png"}],
        }

        create_manifest(t_path, tiles["train"])
        create_manifest(v_path, tiles["val"])
        create_manifest(te_path, tiles["test"])

        with pytest.raises(RuntimeError, match="Image paths leaked"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    def test_shared_tile_path_raises_runtime_error(self, manifest_env):
        """tile_path field fallback overlap must raise RuntimeError."""
        t_path, v_path, _ = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "tile_path": "shared_tile.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "tile_path": "shared_tile.png"}])

        with pytest.raises(RuntimeError, match="Image paths leaked"):
            assert_zero_leakage_manifests(t_path, v_path)

    def test_quarantined_sample_in_validation_raises(self, manifest_env):
        """Tile with quarantine=True in validation split must raise RuntimeError."""
        t_path, v_path, _ = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "t.png"}])
        create_manifest(v_path, [{"sample_id": "v_bad", "project_id": "p_v", "drawing_id": "d_v", "image_path": "v.png", "quarantine": True}])

        with pytest.raises(RuntimeError, match=r"\[QUARANTINE LEAKAGE\] Quarantined sample v_bad"):
            assert_zero_leakage_manifests(t_path, v_path)

    def test_quarantined_sample_in_test_raises(self, manifest_env):
        """Tile with quarantine=True in test split must raise RuntimeError."""
        t_path, v_path, te_path = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "t.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "v.png"}])
        create_manifest(te_path, [{"sample_id": "te_bad", "project_id": "p_te", "drawing_id": "d_te", "image_path": "te.png", "quarantine": True}])

        with pytest.raises(RuntimeError, match=r"\[QUARANTINE LEAKAGE\] Quarantined sample te_bad"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    def test_pseudo_label_sample_in_validation_raises(self, manifest_env):
        """Tile with is_pseudo_label=True in validation split must raise RuntimeError."""
        t_path, v_path, _ = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "t.png"}])
        create_manifest(v_path, [{"sample_id": "v_pseudo", "project_id": "p_v", "drawing_id": "d_v", "image_path": "v.png", "is_pseudo_label": True}])

        with pytest.raises(RuntimeError, match=r"\[QUARANTINE LEAKAGE\] Pseudo-labeled sample v_pseudo"):
            assert_zero_leakage_manifests(t_path, v_path)

    def test_pseudo_label_sample_in_test_raises(self, manifest_env):
        """Tile with is_pseudo_label=True in test split must raise RuntimeError."""
        t_path, v_path, te_path = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "t.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "v.png"}])
        create_manifest(te_path, [{"sample_id": "te_pseudo", "project_id": "p_te", "drawing_id": "d_te", "image_path": "te.png", "is_pseudo_label": True}])

        with pytest.raises(RuntimeError, match=r"\[QUARANTINE LEAKAGE\] Pseudo-labeled sample te_pseudo"):
            assert_zero_leakage_manifests(t_path, v_path, te_path)

    def test_corrupted_json_syntax_raises(self, manifest_env):
        """Corrupted/malformed JSON syntax raises json.JSONDecodeError."""
        t_path, v_path, _ = manifest_env
        t_path.write_text("{malformed: json: [unclosed", encoding="utf-8")
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "v.png"}])

        with pytest.raises(json.JSONDecodeError):
            assert_zero_leakage_manifests(t_path, v_path)

    def test_missing_manifest_file_raises(self, tmp_path):
        """Non-existent manifest file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            assert_zero_leakage_manifests(tmp_path / "nonexistent_train.json", tmp_path / "nonexistent_val.json")

    def test_samples_key_schema_compatibility(self, manifest_env):
        """Manifests using 'samples' key instead of 'tiles' are fully supported."""
        t_path, v_path, _ = manifest_env
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_common", "drawing_id": "d_t", "image_path": "t.png"}], key="samples")
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_common", "drawing_id": "d_v", "image_path": "v.png"}], key="samples")

        with pytest.raises(RuntimeError, match="Projects leaked"):
            assert_zero_leakage_manifests(t_path, v_path)

    def test_empty_manifests_do_not_crash(self, manifest_env):
        """Empty manifests pass without false leakage detections."""
        t_path, v_path, te_path = manifest_env
        create_manifest(t_path, [])
        create_manifest(v_path, [])
        create_manifest(te_path, [])

        assert_zero_leakage_manifests(t_path, v_path, te_path)

    def test_adversarial_casing_vulnerability_demonstration(self, manifest_env):
        """
        Adversarial demonstration: String-based path comparison without canonicalization
        can allow case-differentiated paths to bypass image path check.
        """
        t_path, v_path, _ = manifest_env
        # Windows file system is case-insensitive, but string set intersection is case-sensitive
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "C:\\drawings\\sheet.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "c:\\drawings\\sheet.png"}])

        # Finding: Raw string set intersection {'C:\\...'} & {'c:\\...'} is empty!
        # assert_zero_leakage_manifests passes because it lacks Path.resolve() / .lower() normalization.
        try:
            assert_zero_leakage_manifests(t_path, v_path)
            bypassed = True
        except RuntimeError:
            bypassed = False

        # This asserts the empirical finding: raw string comparison does bypass on case difference
        assert bypassed is True, "Expected raw string comparison to bypass case-mismatched paths on Windows"

    def test_adversarial_mask_path_uninspected_demonstration(self, manifest_env):
        """
        Adversarial demonstration: assert_zero_leakage_manifests inspects image_path/tile_path
        but omits mask_path inspection.
        """
        t_path, v_path, _ = manifest_env
        # Different image paths but shared mask_path
        create_manifest(t_path, [{"sample_id": "t1", "project_id": "p_t", "drawing_id": "d_t", "image_path": "img_A.png", "mask_path": "shared_mask.png"}])
        create_manifest(v_path, [{"sample_id": "v1", "project_id": "p_v", "drawing_id": "d_v", "image_path": "img_B.png", "mask_path": "shared_mask.png"}])

        # Finding: mask_path overlap is not checked by assert_zero_leakage_manifests!
        try:
            assert_zero_leakage_manifests(t_path, v_path)
            bypassed = True
        except RuntimeError:
            bypassed = False

        assert bypassed is True, "Expected mask_path overlap to bypass assert_zero_leakage_manifests"


# ==============================================================================
# 2. PSEUDO-LABEL DISCOUNT WEIGHTING & QUARANTINE VERIFICATION
# ==============================================================================

class TestPseudoLabelDiscountAndQuarantine:
    """Stress testing of pseudo-label discount lambda=0.35 and CAD quarantine."""

    def test_pseudo_label_loss_and_gradient_exact_downweighting(self):
        """
        Verify that when a tile has is_pseudo_label=True (or weak_pseudo_label),
        Trainer applies lambda=0.35, resulting in EXACTLY 0.35x gradients compared to supervised.
        """
        torch.manual_seed(42)
        m_sup = LightweightUNet(num_classes=4)
        opt_sup = GradientCapturingOptimizer(m_sup.parameters(), lr=1e-4)

        torch.manual_seed(42)
        m_pse = LightweightUNet(num_classes=4)
        opt_pse = GradientCapturingOptimizer(m_pse.parameters(), lr=1e-4)

        x = torch.randn(1, 3, 128, 128)
        y = torch.randint(0, 4, (1, 128, 128))

        batch_sup = (x, y, [{"is_pseudo_label": False}])
        batch_pse = (x, y, [{"is_pseudo_label": True}])

        t_sup = Trainer(
            m_sup,
            DummySingleBatchLoader(batch_sup),
            DummySingleBatchLoader(()),
            optimizer=opt_sup,
            gradient_accumulation_steps=1,
            pseudo_label_discount=0.35,
            clip_grad_norm=0.0,
        )
        t_pse = Trainer(
            m_pse,
            DummySingleBatchLoader(batch_pse),
            DummySingleBatchLoader(()),
            optimizer=opt_pse,
            gradient_accumulation_steps=1,
            pseudo_label_discount=0.35,
            clip_grad_norm=0.0,
        )

        res_sup = t_sup.train_one_epoch(1)
        res_pse = t_pse.train_one_epoch(1)

        # 1. Loss ratio check
        loss_ratio = res_pse["train_loss"] / res_sup["train_loss"]
        assert abs(loss_ratio - 0.35) < 1e-5, f"Loss ratio {loss_ratio} != 0.35"

        # 2. Gradient ratio check across all network parameters
        assert len(opt_sup.captured_grads) == len(opt_pse.captured_grads)
        max_diff = 0.0
        for g_sup, g_pse in zip(opt_sup.captured_grads, opt_pse.captured_grads):
            expected_g_pse = g_sup * 0.35
            diff = (g_pse - expected_g_pse).abs().max().item()
            if diff > max_diff:
                max_diff = diff

        assert max_diff < 1e-5, f"Max gradient discrepancy {max_diff:.2e} exceeds tolerance 1e-5"

    def test_weak_pseudo_label_string_triggers_discount(self):
        """label_type='weak_pseudo_label' triggers identical lambda=0.35 discount."""
        torch.manual_seed(42)
        m_sup = LightweightUNet(num_classes=4)
        opt_sup = GradientCapturingOptimizer(m_sup.parameters(), lr=1e-4)

        torch.manual_seed(42)
        m_pse = LightweightUNet(num_classes=4)
        opt_pse = GradientCapturingOptimizer(m_pse.parameters(), lr=1e-4)

        x = torch.randn(1, 3, 128, 128)
        y = torch.randint(0, 4, (1, 128, 128))

        batch_sup = (x, y, [{"label_type": "ground_truth"}])
        batch_pse = (x, y, [{"label_type": "weak_pseudo_label"}])

        t_sup = Trainer(m_sup, DummySingleBatchLoader(batch_sup), DummySingleBatchLoader(()), optimizer=opt_sup, gradient_accumulation_steps=1, pseudo_label_discount=0.35, clip_grad_norm=0.0)
        t_pse = Trainer(m_pse, DummySingleBatchLoader(batch_pse), DummySingleBatchLoader(()), optimizer=opt_pse, gradient_accumulation_steps=1, pseudo_label_discount=0.35, clip_grad_norm=0.0)

        t_sup.train_one_epoch(1)
        t_pse.train_one_epoch(1)

        max_diff = max(
            (g_pse - g_sup * 0.35).abs().max().item()
            for g_sup, g_pse in zip(opt_sup.captured_grads, opt_pse.captured_grads)
        )
        assert max_diff < 1e-5

    @pytest.mark.parametrize("discount", [0.0, 0.1, 0.5, 0.75, 1.0])
    def test_arbitrary_pseudo_label_discount_factors(self, discount: float):
        """Trainer respects user-configured pseudo_label_discount values."""
        torch.manual_seed(100)
        m1 = LightweightUNet(num_classes=4)
        opt1 = GradientCapturingOptimizer(m1.parameters(), lr=1e-4)

        torch.manual_seed(100)
        m2 = LightweightUNet(num_classes=4)
        opt2 = GradientCapturingOptimizer(m2.parameters(), lr=1e-4)

        x = torch.randn(1, 3, 128, 128)
        y = torch.randint(0, 4, (1, 128, 128))

        t_base = Trainer(m1, DummySingleBatchLoader((x, y, [{}])), DummySingleBatchLoader(()), optimizer=opt1, gradient_accumulation_steps=1, clip_grad_norm=0.0)
        t_disc = Trainer(m2, DummySingleBatchLoader((x, y, [{"is_pseudo_label": True}])), DummySingleBatchLoader(()), optimizer=opt2, gradient_accumulation_steps=1, pseudo_label_discount=discount, clip_grad_norm=0.0)

        t_base.train_one_epoch(1)
        t_disc.train_one_epoch(1)

        for g_base, g_disc in zip(opt1.captured_grads, opt2.captured_grads):
            diff = (g_disc - g_base * discount).abs().max().item()
            assert diff < 1e-5

    def test_official_cad_tiles_strictly_quarantined_from_val_and_test(self):
        """
        Verify that 99th Street CAD tiles and quarantined samples are strictly
        quarantined from validation and test splits in official dataset directories.
        """
        candidate_dirs = [
            Path("drywall_detection/data/processed/splits"),
            Path("drywall_detection/data/splits"),
        ]

        for base in candidate_dirs:
            if not base.exists():
                continue

            quarantine_path = base / "quarantine.json"
            val_path = base / "val.json"
            test_path = base / "test.json"

            if not (val_path.exists() and test_path.exists()):
                continue

            v_data = json.loads(val_path.read_text(encoding="utf-8"))
            te_data = json.loads(test_path.read_text(encoding="utf-8"))

            v_tiles = v_data.get("tiles") or v_data.get("samples") or []
            te_tiles = te_data.get("tiles") or te_data.get("samples") or []

            # 1. Check no tile in val has quarantine or pseudo_label flag
            for t in v_tiles:
                assert not t.get("quarantine", False), f"Quarantined tile in {val_path}: {t.get('sample_id')}"
                assert not t.get("is_pseudo_label", False), f"Pseudo-labeled tile in {val_path}: {t.get('sample_id')}"
                assert t.get("project_id") != "mta_99th_street_quarantine"

            # 2. Check no tile in test has quarantine or pseudo_label flag
            for t in te_tiles:
                assert not t.get("quarantine", False), f"Quarantined tile in {test_path}: {t.get('sample_id')}"
                assert not t.get("is_pseudo_label", False), f"Pseudo-labeled tile in {test_path}: {t.get('sample_id')}"
                assert t.get("project_id") != "mta_99th_street_quarantine"

            # 3. If quarantine.json exists, verify zero overlap with val and test
            if quarantine_path.exists():
                q_data = json.loads(quarantine_path.read_text(encoding="utf-8"))
                q_tiles = q_data.get("tiles") or q_data.get("samples") or []
                q_ids = {t["sample_id"] for t in q_tiles if "sample_id" in t}
                v_ids = {t["sample_id"] for t in v_tiles if "sample_id" in t}
                te_ids = {t["sample_id"] for t in te_tiles if "sample_id" in t}

                assert len(q_ids & v_ids) == 0, f"Quarantined IDs found in val: {q_ids & v_ids}"
                assert len(q_ids & te_ids) == 0, f"Quarantined IDs found in test: {q_ids & te_ids}"

    def test_verify_split_isolation_rejects_injected_quarantine(self):
        """verify_split_isolation runtime helper rejects contaminated DataLoader."""
        class MockLoader:
            def __init__(self, tiles):
                self.dataset = type("DS", (), {"tiles": tiles})()

        train_l = MockLoader([{"project_id": "p1", "drawing_id": "d1"}])
        val_l = MockLoader([{"project_id": "p2", "drawing_id": "d2", "quarantine": True, "sample_id": "bad_q"}])

        with pytest.raises(ValueError, match="Quarantined sample bad_q found in val split"):
            verify_split_isolation(train_l, val_l)

    def test_finding_dataset_loader_omits_pseudo_label_metadata(self, tmp_path):
        """
        Documented Finding: DrywallTileDataset.__getitem__ drops is_pseudo_label
        from the constructed meta dict.
        """
        img_p = tmp_path / "img.png"
        msk_p = tmp_path / "msk.png"
        Image.new("RGB", (512, 512), (255, 255, 255)).save(img_p)
        Image.new("L", (512, 512), 0).save(msk_p)

        manifest = [
            {
                "tile_id": "t1",
                "project_id": "p1",
                "drawing_id": "d1",
                "image_path": str(img_p),
                "mask_path": str(msk_p),
                "is_pseudo_label": True,
                "label_type": "weak_pseudo_label",
            }
        ]

        ds = DrywallTileDataset(manifest, return_metadata=True)
        _, _, meta = ds[0]

        # The finding is that is_pseudo_label is absent from meta in DrywallTileDataset
        assert "is_pseudo_label" not in meta, "Expected finding: is_pseudo_label not preserved in DrywallTileDataset meta"


@pytest.fixture(scope="module")
def shared_inferencer():
    """Instantiate single offline inferencer for the test suite."""
    return StandaloneInferencer(device="cpu")


# ==============================================================================
# 3. STANDALONE INFERENCER ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestStandaloneInferencerStress:
    """Adversarial stress-testing of standalone infer.py (StandaloneInferencer)."""

    def test_infer_tiny_image_32x32(self, shared_inferencer):
        """
        Images smaller than tile_size (32x32) must be padded to 512x512 for inference
        and strictly unpadded back to (32, 32) without shape distortions or crashes.
        """
        tiny_np = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        tiny_img = Image.fromarray(tiny_np)

        mask, probs = shared_inferencer.predict_image_sliding_window(tiny_img)

        assert mask.shape == (32, 32), f"Expected mask shape (32, 32), got {mask.shape}"
        assert probs.shape == (32, 32, 4), f"Expected probs shape (32, 32, 4), got {probs.shape}"
        assert mask.dtype == np.uint8
        assert not np.isnan(probs).any()
        assert not np.isinf(probs).any()
        assert np.all(np.isin(mask, [0, 1, 2, 3]))

    def test_infer_odd_resolution_733x521(self, shared_inferencer):
        """
        Images with non-divisible odd dimensions (733x521) must be processed seamlessly
        via sliding-window Hann stitching and restored to exact dimensions (521, 733).
        """
        odd_np = np.random.randint(0, 255, (521, 733, 3), dtype=np.uint8)
        odd_img = Image.fromarray(odd_np)

        mask, probs = shared_inferencer.predict_image_sliding_window(odd_img)

        assert mask.shape == (521, 733), f"Expected mask shape (521, 733), got {mask.shape}"
        assert probs.shape == (521, 733, 4), f"Expected probs shape (521, 733, 4), got {probs.shape}"
        assert not np.isnan(probs).any()
        assert not np.isinf(probs).any()
        # Verify probability sum across channels equals ~1.0
        sums = np.sum(probs, axis=-1)
        assert np.allclose(sums, 1.0, atol=1e-3), "Probabilities do not sum to 1.0"

    def test_infer_pure_noise_image(self, shared_inferencer):
        """
        Pure Gaussian and uniform noise images must execute stably without NaNs or zero-divisions.
        """
        # 1. Uniform noise
        uni_noise = Image.fromarray(np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8))
        mask_u, probs_u = shared_inferencer.predict_image_sliding_window(uni_noise)
        assert not np.isnan(probs_u).any()
        assert not np.isinf(probs_u).any()

        # 2. Gaussian noise
        gauss_raw = np.clip(np.random.normal(128, 50, (512, 512, 3)), 0, 255).astype(np.uint8)
        gauss_noise = Image.fromarray(gauss_raw)
        mask_g, probs_g = shared_inferencer.predict_image_sliding_window(gauss_noise)
        assert not np.isnan(probs_g).any()
        assert not np.isinf(probs_g).any()

    def test_infer_large_image_stitching_and_memory_consumption(self, shared_inferencer):
        """
        Large high-resolution image (1024x1024) stitching memory profiling.
        Verifies peak memory allocation remains bounded (<120 MB).
        """
        large_np = np.full((1024, 1024, 3), 240, dtype=np.uint8)
        large_img = Image.fromarray(large_np)

        tracemalloc.start()
        mask, probs = shared_inferencer.predict_image_sliding_window(large_img)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        logger.info("Peak memory for 1024x1024 stitching: %.2f MB", peak_mb)

        assert mask.shape == (1024, 1024)
        assert probs.shape == (1024, 1024, 4)
        assert peak_mb < 120.0, f"Memory consumption {peak_mb:.2f} MB exceeds 120 MB ceiling for 1024x1024"

    def test_infer_extreme_aspect_ratios(self, shared_inferencer):
        """
        Extreme ribbon/strip dimensions (64x1024 and 1024x64) handled without indexing faults.
        """
        # Horizontal strip (1024 wide, 64 high)
        h_strip = Image.fromarray(np.random.randint(0, 255, (64, 1024, 3), dtype=np.uint8))
        m_h, _ = shared_inferencer.predict_image_sliding_window(h_strip)
        assert m_h.shape == (64, 1024)

        # Vertical strip (64 wide, 1024 high)
        v_strip = Image.fromarray(np.random.randint(0, 255, (1024, 64, 3), dtype=np.uint8))
        m_v, _ = shared_inferencer.predict_image_sliding_window(v_strip)
        assert m_v.shape == (1024, 64)

    def test_infer_solid_black_and_solid_white(self, shared_inferencer):
        """Solid black (0) and solid white (255) images process without normalization overflow."""
        black = Image.fromarray(np.zeros((512, 512, 3), dtype=np.uint8))
        m_b, p_b = shared_inferencer.predict_image_sliding_window(black)
        assert not np.isnan(p_b).any()

        white = Image.fromarray(np.full((512, 512, 3), 255, dtype=np.uint8))
        m_w, p_w = shared_inferencer.predict_image_sliding_window(white)
        assert not np.isnan(p_w).any()

    def test_infer_single_pixel_image(self, shared_inferencer):
        """Degenerate 1x1 image handled gracefully with padding and unpadding."""
        one_px = Image.fromarray(np.array([[[200, 200, 200]]], dtype=np.uint8))
        m, p = shared_inferencer.predict_image_sliding_window(one_px)
        assert m.shape == (1, 1)
        assert p.shape == (1, 1, 4)

    def test_infer_grayscale_mode_l_handled(self, shared_inferencer):
        """Single-channel Mode 'L' grayscale input converted and processed correctly."""
        gray = Image.fromarray(np.random.randint(0, 255, (256, 256), dtype=np.uint8), mode="L")
        m, p = shared_inferencer.predict_image_sliding_window(gray)
        assert m.shape == (256, 256)
        assert p.shape == (256, 256, 4)
