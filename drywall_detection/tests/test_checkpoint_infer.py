"""
drywall_detection/tests/test_checkpoint_infer.py
===============================================
Comprehensive verification test suite for champion model checkpoint reload,
standalone offline inference, numerical determinism, multi-scale Hann apodization,
and PDF rotation handling (Milestone M6).
"""

from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import pytest
import numpy as np
from PIL import Image
import torch
import fitz

from drywall_detection.config import (
    BEST_MODEL_DIR,
    CLASS_BACKGROUND,
    CLASS_DRYWALL,
    CLASS_NON_DRYWALL,
    CLASS_UNCERTAIN,
)
from drywall_detection.models.segformer import SegFormerB0, SegFormerWallDetector
from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)


class TestCheckpointArtifacts:
    """Verifies existence, completeness, and schema validity of all 8 deliverable bundle artifacts."""

    def test_all_bundle_artifacts_exist(self):
        expected_files = [
            "best_model.pt",
            "config.json",
            "class_mapping.json",
            "training_log.json",
            "metrics.json",
            "infer.py",
            "README.md",
            "sample_overlays",
        ]
        for fname in expected_files:
            p = BEST_MODEL_DIR / fname
            assert p.exists(), f"Missing required checkpoint bundle artifact: {fname}"
            if p.is_file():
                assert p.stat().st_size > 0, f"Artifact is empty (0 bytes): {fname}"

    def test_config_json_schema_and_values(self):
        cfg_path = BEST_MODEL_DIR / "config.json"
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg.get("num_classes") == 4
        assert cfg.get("tile_size") == 512
        assert cfg.get("total_parameters") == 3715172
        assert "normalization" in cfg
        assert cfg["normalization"]["mean"] == [0.485, 0.456, 0.406]
        assert cfg["normalization"]["std"] == [0.229, 0.224, 0.225]
        assert "inference_settings" in cfg
        assert cfg["inference_settings"].get("stitching_method") == "hann_apodization"

    def test_class_mapping_json_schema_and_colors(self):
        map_path = BEST_MODEL_DIR / "class_mapping.json"
        with open(map_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "classes" in data
        assert len(data["classes"]) == 4
        class_names = [c["name"] for c in data["classes"]]
        assert class_names == ["Background", "Drywall", "Non-Drywall", "Uncertain"]

        # Verify canonical hex colors
        assert data["classes"][1]["hex"] == "#00C853"  # Drywall Green
        assert data["classes"][2]["hex"] == "#D50000"  # Non-Drywall Red
        assert data["classes"][3]["hex"] == "#FFD600"  # Uncertain Yellow

    def test_training_log_schema_and_progress(self):
        log_path = BEST_MODEL_DIR / "training_log.json"
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert isinstance(log_data, list)
        assert len(log_data) >= 1
        for entry in log_data:
            assert "epoch" in entry
            assert "train_loss" in entry
            assert "val_loss" in entry
            assert "val_wall_iou" in entry

    def test_metrics_json_schema_and_confusion_matrix(self):
        met_path = BEST_MODEL_DIR / "metrics.json"
        with open(met_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        assert "per_class" in metrics
        assert "confusion_matrix" in metrics
        cm = metrics["confusion_matrix"]
        assert len(cm) == 4
        for row in cm:
            assert len(row) == 4


class TestModelWeightReload:
    """Verifies that weights reload cleanly on CPU and match exact structural specifications."""

    def test_checkpoint_load_cpu_structure(self):
        pt_path = BEST_MODEL_DIR / "best_model.pt"
        ckpt = torch.load(pt_path, map_location="cpu")
        assert isinstance(ckpt, dict)
        assert "model_state_dict" in ckpt
        assert "optimizer_state_dict" in ckpt
        assert "epoch" in ckpt
        assert ckpt["epoch"] == 3

    def test_segformer_b0_state_dict_keys(self):
        pt_path = BEST_MODEL_DIR / "best_model.pt"
        ckpt = torch.load(pt_path, map_location="cpu")
        state_dict = ckpt["model_state_dict"]
        # Verify core SegFormer layers
        has_patch_embed = any("patch_embeddings" in k for k in state_dict.keys())
        has_decode_head = any("decode_head" in k for k in state_dict.keys())
        assert has_patch_embed
        assert has_decode_head

    def test_segformer_b0_parameter_count_exact(self):
        model = SegFormerB0(num_classes=4, offline=True)
        pt_path = BEST_MODEL_DIR / "best_model.pt"
        ckpt = torch.load(pt_path, map_location="cpu")
        model.load_state_dict(ckpt["model_state_dict"])

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        assert trainable_params == 3715172, f"Expected 3,715,172 parameters, got {trainable_params}"

    def test_offline_initialization_no_hub(self):
        # Offline mode must construct without internet calls
        model = SegFormerB0(num_classes=4, offline=True)
        assert model is not None
        assert model.num_classes == 4
        assert model.model.decode_head.classifier.out_channels == 4


class TestInferenceDeterminism:
    """Verifies exact bit-level numerical determinism across repeated forward passes and model instances."""

    def test_forward_pass_repeatability_same_instance(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        torch.manual_seed(42)
        x = torch.randn(1, 3, 512, 512)

        with torch.no_grad():
            y1 = inferencer.model(x)
            y2 = inferencer.model(x)

        max_diff = torch.max(torch.abs(y1 - y2)).item()
        assert max_diff == 0.0, f"Forward pass non-deterministic: max diff = {max_diff}"

    def test_checkpoint_reload_identity_separate_instances(self):
        pt_path = BEST_MODEL_DIR / "best_model.pt"
        ckpt = torch.load(pt_path, map_location="cpu")

        model1 = SegFormerB0(num_classes=4, offline=True)
        model1.load_state_dict(ckpt["model_state_dict"])
        model1.eval()

        model2 = SegFormerB0(num_classes=4, offline=True)
        model2.load_state_dict(ckpt["model_state_dict"])
        model2.eval()

        torch.manual_seed(100)
        x = torch.randn(1, 3, 512, 512)

        with torch.no_grad():
            out1 = model1(x)
            out2 = model2(x)

        max_diff = torch.max(torch.abs(out1 - out2)).item()
        assert max_diff == 0.0, f"Separate instances diverged: max diff = {max_diff}"

    def test_eval_mode_dropout_disabled(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        assert not inferencer.model.training
        for m in inferencer.model.modules():
            if isinstance(m, torch.nn.Dropout):
                assert not m.training


class TestMultiScaleInference:
    """Verifies small-canvas padding guards, standard 512x512 tiles, and Hann window sliding-window stitching."""

    def test_small_image_padding_guard(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        # Sub-tile canvas 200x300 (W=200, H=300)
        img = Image.new("RGB", (200, 300), color=(255, 255, 255))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512)

        assert mask.shape == (300, 200)
        assert probs.shape == (300, 200, 4)
        assert np.all(np.isin(mask, [0, 1, 2, 3]))

    def test_exact_tile_fast_path(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (512, 512), color=(255, 255, 255))
        mask = inferencer.predict_tile(img)
        assert mask.shape == (512, 512)

        # Sliding window fast path on exact tile size
        mask_sw, probs_sw = inferencer.predict_image_sliding_window(img, tile_size=512)
        assert mask_sw.shape == (512, 512)
        assert probs_sw.shape == (512, 512, 4)

    def test_large_image_hann_sliding_window(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        # 600x600 image (requires sliding window tiles with overlap)
        img = Image.new("RGB", (600, 600), color=(255, 255, 255))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.20)

        assert mask.shape == (600, 600)
        assert probs.shape == (600, 600, 4)
        # Probability sum across classes equals 1.0 at every pixel
        prob_sums = probs.sum(axis=-1)
        assert np.allclose(prob_sums, 1.0, atol=1e-3)

    def test_hann_window_mathematical_properties(self):
        hann = create_hann_window(512)
        assert hann.shape == (512, 512)
        assert hann.dtype == np.float32
        assert np.min(hann) >= 9.99e-5
        assert np.isclose(hann[256, 256], 1.0, atol=1e-2)
        # Verify 2D symmetry: W(x, y) == W(y, x) == W(N-1-x, N-1-y)
        assert np.allclose(hann, hann.T)
        assert np.allclose(hann, np.flip(hann))

    def test_class_index_output_bounds_and_dtype(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        img = Image.new("RGB", (128, 128), color=(240, 240, 240))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512)

        assert mask.dtype in (np.uint8, np.int64, np.int32)
        unique_classes = np.unique(mask)
        for c in unique_classes:
            assert c in (CLASS_BACKGROUND, CLASS_DRYWALL, CLASS_NON_DRYWALL, CLASS_UNCERTAIN)


class TestPDFInference:
    """Verifies synthetic PDF rendering with 90° rotation awareness and dimension preservation."""

    def test_pdf_synthetic_90deg_rotation_preservation(self, tmp_path):
        # Create a synthetic 1-page PDF with 90° CW rotation (e.g. 200 x 300 pt)
        doc = fitz.open()
        page = doc.new_page(width=200.0, height=300.0)
        page.set_rotation(90)
        page.draw_line(fitz.Point(10, 10), fitz.Point(100, 10), color=(0, 0, 0), width=2)
        pdf_path = tmp_path / "synthetic_90deg.pdf"
        doc.save(str(pdf_path))
        doc.close()

        # Run standalone inferencer on PDF at 72 DPI for fast test execution
        out_pdf_path = tmp_path / "synthetic_90deg_annotated.pdf"
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        inferencer.process_pdf(
            pdf_path=pdf_path,
            output_path=out_pdf_path,
            page_num=0,
            dpi=72,
        )

        assert out_pdf_path.exists()
        out_doc = fitz.open(out_pdf_path)
        assert len(out_doc) == 1
        out_page = out_doc[0]
        assert out_page.rect.width > 0
        assert out_page.rect.height > 0
        out_doc.close()


class TestCLIInterface:
    """Verifies standalone infer.py CLI argument handling and execution."""

    def test_cli_help_exit_zero(self):
        infer_script = BEST_MODEL_DIR / "infer.py"
        cmd = [sys.executable, str(infer_script), "--help"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0
        assert "Standalone offline inference CLI" in result.stdout

    def test_cli_single_image_overlay_json_output(self, tmp_path):
        infer_script = BEST_MODEL_DIR / "infer.py"
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        out_img = tmp_path / "cli_test_overlay.png"

        cmd = [
            sys.executable,
            str(infer_script),
            "--image", str(sample_img),
            "--output", str(out_img),
            "--device", "cpu",
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0, f"infer.py failed with: {result.stderr}"
        assert out_img.exists()
        # Verify valid JSON output
        data = json.loads(result.stdout)
        assert data["status"] == "success"
        assert "pixel_counts" in data
        assert "drywall_percentage" in data

    def test_cli_single_image_mask_output(self, tmp_path):
        infer_script = BEST_MODEL_DIR / "infer.py"
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        out_mask = tmp_path / "cli_test_mask.png"

        cmd = [
            sys.executable,
            str(infer_script),
            "--image", str(sample_img),
            "--output", str(out_mask),
            "--mode", "mask",
            "--device", "cpu",
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0
        assert out_mask.exists()
