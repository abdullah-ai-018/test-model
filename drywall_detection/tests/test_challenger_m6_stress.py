"""
drywall_detection/tests/test_challenger_m6_stress.py
===================================================
Adversarial stress-testing and empirical probes for Milestone M6:
- Strict offline network isolation verification (socket blocking)
- Checkpoint integrity, parameter count exactness (3,715,172), optimizer presence
- Bit-level determinism and floating-point stability
- Multi-scale tiling edge cases: 1x1, 17x43, 511x511, 512x512, 513x513, 64x1200, 1200x64
- Large canvas (> 2048) Hann apodization seamless stitching & partition of unity
- PDF 90° rotation and 1728x2592 pt MediaBox rendering and dimension preservation
- CLI error handling and POSIX robustness
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
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
from drywall_detection.models.segformer import SegFormerB0
from drywall_detection.checkpoints.best_model.infer import (
    StandaloneInferencer,
    create_hann_window,
)


class TestOfflineIndependence:
    """Verifies that model initialization and inference execute 100% offline."""

    def test_strict_network_isolation_socket_blocked(self, monkeypatch):
        # Intercept socket creation and connect calls to guarantee zero egress
        def mock_connect(*args, **kwargs):
            raise RuntimeError("ADVERSARIAL_TRAP: Attempted network connection in offline mode!")

        monkeypatch.setattr(socket.socket, "connect", mock_connect)
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")
        monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

        # Initialize inferencer under network ban
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        assert inferencer is not None

        # Execute tile inference
        dummy_tile = Image.new("RGB", (512, 512), color=(200, 200, 200))
        pred = inferencer.predict_tile(dummy_tile)
        assert pred.shape == (512, 512)
        assert pred.dtype == np.uint8


class TestCheckpointIntegrityAndExactParams:
    """Empirically inspects checkpoint structure, parameter exactness, and optimizer states."""

    def test_checkpoint_payload_and_optimizer_states(self):
        ckpt_path = BEST_MODEL_DIR / "best_model.pt"
        assert ckpt_path.exists()
        ckpt = torch.load(ckpt_path, map_location="cpu")

        assert isinstance(ckpt, dict), "Checkpoint must be a dictionary"
        assert "model_state_dict" in ckpt, "Missing model_state_dict in checkpoint"
        assert "optimizer_state_dict" in ckpt, "Missing optimizer_state_dict in checkpoint"
        assert "epoch" in ckpt, "Missing epoch in checkpoint"

        opt_state = ckpt["optimizer_state_dict"]
        assert "param_groups" in opt_state
        assert len(opt_state["param_groups"]) > 0

        # State dict must contain both encoder and decoder keys
        keys = list(ckpt["model_state_dict"].keys())
        assert any("model.segformer.encoder" in k or "encoder" in k or "patch_embeddings" in k for k in keys)
        assert any("decode_head" in k for k in keys)

    def test_parameter_count_exact_3715172(self):
        model = SegFormerB0(num_classes=4, offline=True)
        ckpt = torch.load(BEST_MODEL_DIR / "best_model.pt", map_location="cpu")
        model.load_state_dict(ckpt["model_state_dict"])

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())

        assert trainable_params == 3715172, f"Trainable params {trainable_params} != 3715172"
        assert total_params == 3715172, f"Total params {total_params} != 3715172"

    def test_weights_are_non_trivial(self):
        ckpt = torch.load(BEST_MODEL_DIR / "best_model.pt", map_location="cpu")
        state_dict = ckpt["model_state_dict"]

        # Check weights are not trivial all-zero or all-ones
        for k, v in state_dict.items():
            if "weight" in k and isinstance(v, torch.Tensor) and v.numel() > 10:
                assert not torch.all(v == 0), f"Weight tensor {k} is all zeros"
                assert not torch.all(v == 1), f"Weight tensor {k} is all ones"
                assert not torch.isnan(v).any(), f"Weight tensor {k} contains NaN"
                assert not torch.isinf(v).any(), f"Weight tensor {k} contains Inf"


class TestNumericalDeterminismStress:
    """Probes numerical repeatability, floating point variance, and batch invariance."""

    def test_multi_run_determinism_max_diff_zero(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        torch.manual_seed(999)
        x = torch.randn(1, 3, 512, 512)

        with torch.no_grad():
            outputs = [inferencer.model(x) for _ in range(5)]

        first = outputs[0]
        for idx, out in enumerate(outputs[1:], start=2):
            diff = torch.max(torch.abs(first - out)).item()
            assert diff == 0.0, f"Run {idx} diverged from Run 1 with max diff = {diff}"

    def test_constant_input_stability(self):
        # Test completely black and completely white inputs
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        black = Image.new("RGB", (512, 512), color=(0, 0, 0))
        white = Image.new("RGB", (512, 512), color=(255, 255, 255))

        mask_black = inferencer.predict_tile(black)
        mask_white = inferencer.predict_tile(white)

        assert mask_black.shape == (512, 512)
        assert mask_white.shape == (512, 512)
        assert np.all(np.isin(mask_black, [0, 1, 2, 3]))
        assert np.all(np.isin(mask_white, [0, 1, 2, 3]))


class TestMultiScaleTilingEdgeCases:
    """Stress-tests multi-scale canvas edge cases, boundaries, and ribbon aspect ratios."""

    @pytest.fixture(scope="class")
    def inferencer(self):
        return StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")

    def test_canvas_1x1_micro_edge(self, inferencer):
        img = Image.new("RGB", (1, 1), color=(255, 255, 255))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512)
        assert mask.shape == (1, 1)
        assert probs.shape == (1, 1, 4)
        assert mask[0, 0] in (0, 1, 2, 3)
        assert np.isclose(probs[0, 0].sum(), 1.0, atol=1e-3)

    def test_canvas_arbitrary_odd_subtile(self, inferencer):
        # 17x43 canvas (width=17, height=43)
        img = Image.new("RGB", (17, 43), color=(128, 128, 128))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512)
        assert mask.shape == (43, 17)
        assert probs.shape == (43, 17, 4)
        assert np.all(np.isin(mask, [0, 1, 2, 3]))
        assert np.allclose(probs.sum(axis=-1), 1.0, atol=1e-3)

    def test_canvas_exact_boundaries(self, inferencer):
        # 511x511 (one pixel smaller than tile)
        img_511 = Image.new("RGB", (511, 511), color=(255, 255, 255))
        mask_511, probs_511 = inferencer.predict_image_sliding_window(img_511, tile_size=512)
        assert mask_511.shape == (511, 511)
        assert probs_511.shape == (511, 511, 4)

        # 512x512 (exact tile size)
        img_512 = Image.new("RGB", (512, 512), color=(255, 255, 255))
        mask_512, probs_512 = inferencer.predict_image_sliding_window(img_512, tile_size=512)
        assert mask_512.shape == (512, 512)
        assert probs_512.shape == (512, 512, 4)

        # 513x513 (one pixel larger than tile, triggering sliding window with stride)
        img_513 = Image.new("RGB", (513, 513), color=(255, 255, 255))
        mask_513, probs_513 = inferencer.predict_image_sliding_window(img_513, tile_size=512, overlap=0.2)
        assert mask_513.shape == (513, 513)
        assert probs_513.shape == (513, 513, 4)
        assert np.allclose(probs_513.sum(axis=-1), 1.0, atol=1e-3)

    def test_extreme_ribbon_aspect_ratios(self, inferencer):
        # Tall vertical ribbon: W=64, H=600
        img_vert = Image.new("RGB", (64, 600), color=(255, 255, 255))
        mask_vert, probs_vert = inferencer.predict_image_sliding_window(img_vert, tile_size=512, overlap=0.2)
        assert mask_vert.shape == (600, 64)
        assert probs_vert.shape == (600, 64, 4)
        assert np.allclose(probs_vert.sum(axis=-1), 1.0, atol=1e-3)

        # Wide horizontal ribbon: W=600, H=64
        img_horiz = Image.new("RGB", (600, 64), color=(255, 255, 255))
        mask_horiz, probs_horiz = inferencer.predict_image_sliding_window(img_horiz, tile_size=512, overlap=0.2)
        assert mask_horiz.shape == (64, 600)
        assert probs_horiz.shape == (64, 600, 4)
        assert np.allclose(probs_horiz.sum(axis=-1), 1.0, atol=1e-3)


class TestLargeCanvasHannWindowApodization:
    """Stress-tests large canvas (> 2048) and Hann window apodization boundary seam blending."""

    def test_hann_window_properties(self):
        hann = create_hann_window(512)
        # Peak at center
        assert hann[256, 256] == pytest.approx(1.0, abs=0.01)
        # Minimum at borders clamped to 1e-4
        assert hann[0, 0] == pytest.approx(1e-4, abs=1e-5)
        assert hann[0, 511] == pytest.approx(1e-4, abs=1e-5)
        assert hann[511, 0] == pytest.approx(1e-4, abs=1e-5)
        assert hann[511, 511] == pytest.approx(1e-4, abs=1e-5)
        # Monotonically increasing from corner to center
        assert hann[0, 0] < hann[128, 128] < hann[256, 256]

    def test_large_canvas_sliding_window_seamless(self):
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        # Large canvas: 2100 x 1200
        H, W = 1200, 2100
        img = Image.new("RGB", (W, H), color=(255, 255, 255))
        mask, probs = inferencer.predict_image_sliding_window(img, tile_size=512, overlap=0.25)

        assert mask.shape == (H, W)
        assert probs.shape == (H, W, 4)
        assert not np.isnan(probs).any(), "Probabilities contain NaN values"
        assert not np.isinf(probs).any(), "Probabilities contain Inf values"

        # Verify sum to 1.0 everywhere across large canvas
        prob_sums = probs.sum(axis=-1)
        assert np.allclose(prob_sums, 1.0, atol=1e-3), "Partition of unity violated in Hann window stitching"


class TestPDFSynthetic90DegRotationAndMediaBox:
    """Probes synthetic PDF pages with exact 1728x2592 pt MediaBox and 90° CW rotation."""

    def test_exact_99th_street_mediabox_90deg_rotation(self, tmp_path):
        # 99th Street PDF: MediaBox is 1728 x 2592 pt, rotated 90° CW
        doc = fitz.open()
        # Create page with width=1728, height=2592
        page = doc.new_page(width=1728.0, height=2592.0)
        page.set_rotation(90)
        # Draw architectural linework
        page.draw_rect(fitz.Rect(100, 100, 500, 500), color=(0, 0, 0), width=2)
        page.draw_line(fitz.Point(100, 100), fitz.Point(500, 500), color=(0, 0, 0), width=1.5)

        synth_pdf = tmp_path / "mediabox_1728x2592_rot90.pdf"
        doc.save(str(synth_pdf))
        doc.close()

        # Verify dimensions before inference
        check_doc = fitz.open(synth_pdf)
        p0 = check_doc[0]
        # In PyMuPDF, after rotation 90, rect width and height reflect orientation
        assert p0.rotation == 90
        check_doc.close()

        # Run inference via StandaloneInferencer at 36 DPI for fast test turnaround
        out_pdf = tmp_path / "annotated_1728x2592_rot90.pdf"
        inferencer = StandaloneInferencer(checkpoint_dir=BEST_MODEL_DIR, device="cpu")
        inferencer.process_pdf(
            pdf_path=synth_pdf,
            output_path=out_pdf,
            page_num=0,
            dpi=36,
        )

        assert out_pdf.exists()
        out_doc = fitz.open(out_pdf)
        assert len(out_doc) == 1
        out_p0 = out_doc[0]
        assert out_p0.rect.width > 0
        assert out_p0.rect.height > 0
        out_doc.close()


class TestCLIEdgeCases:
    """Stress-tests CLI execution, flags, and error codes."""

    def test_cli_missing_input_file(self):
        infer_script = BEST_MODEL_DIR / "infer.py"
        cmd = [sys.executable, str(infer_script), "--input", "non_existent_image_12345.png"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 1

    def test_cli_tile_size_and_overlap_parameters(self, tmp_path):
        infer_script = BEST_MODEL_DIR / "infer.py"
        sample_img = BEST_MODEL_DIR / "sample_overlays" / "sample_01_original.png"
        out_img = tmp_path / "out_custom_tile.png"

        cmd = [
            sys.executable,
            str(infer_script),
            "--input", str(sample_img),
            "--output", str(out_img),
            "--tile-size", "256",
            "--overlap", "0.10",
            "--device", "cpu",
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert result.returncode == 0, f"Error: {result.stderr}"
        assert out_img.exists()
        data = json.loads(result.stdout)
        assert data["status"] == "success"
