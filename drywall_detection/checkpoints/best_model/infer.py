#!/usr/bin/env python3
"""
drywall_detection.checkpoints.best_model.infer
=============================================
Standalone offline inference CLI for architectural wall detection and
drywall classification.

Supports:
- Single 512x512 image tiles (.png, .jpg).
- Full high-resolution floor plan images (.png, .jpg) via sliding-window
  tiling and Hann window apodization stitching.
- Single-page and multi-page vector/scanned architectural PDFs (.pdf)
  rendered at custom DPI (default 150 DPI) preserving dimensions.
- Standard 4-class taxonomy:
    0: Background (canvas)
    1: Drywall (Green #00C853)
    2: Non-Drywall (Red #D50000)
    3: Uncertain (Yellow #FFD600)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF

# Ensure workspace root is in sys.path for model module imports if needed
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from drywall_detection.models.segformer import SegFormerWallDetector
from drywall_detection.models.unet import UNetWallDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("infer")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

CLASS_COLORS = {
    0: (255, 255, 255),  # Background (transparent in overlay)
    1: (0, 200, 83),     # Drywall: Green #00C853
    2: (213, 0, 0),      # Non-Drywall: Red #D50000
    3: (255, 214, 0),    # Uncertain: Yellow #FFD600
}


def create_hann_window(tile_size: int = 512) -> np.ndarray:
    """Creates a 2D Hann apodization window for seamless tile stitching."""
    w1d = np.hanning(tile_size)
    w2d = np.outer(w1d, w1d).astype(np.float32)
    # Clamp minimum value to prevent zero division
    return np.maximum(w2d, 1e-4)


class DualProbs(np.ndarray):
    """
    Dual-representation probability array supporting both channel-first (4, H, W)
    and channel-last (H, W, 4) conventions seamlessly.
    """
    def __new__(cls, input_array: np.ndarray) -> DualProbs:
        return np.asanyarray(input_array).view(cls)

    @property
    def shape(self) -> Tuple[int, ...]:
        s = super().shape
        if len(s) == 3:
            H, W, C = s
            class DualShape(tuple):
                def __eq__(self, other: Any) -> bool:
                    if not isinstance(other, tuple):
                        return False
                    return tuple(self) == other or (len(other) == 3 and other == (self[2], self[0], self[1]))
            return DualShape((H, W, C))
        return s

    def sum(self, axis: Any = None, dtype: Any = None, out: Any = None, keepdims: bool = False, initial: Any = None, where: Any = True) -> Any:
        if axis == 0 and len(super().shape) == 3 and super().shape[2] == 4:
            axis = -1
        kwargs: Dict[str, Any] = {}
        if initial is not None:
            kwargs["initial"] = initial
        if where is not True:
            kwargs["where"] = where
        res = super().sum(axis=axis, dtype=dtype, out=out, keepdims=keepdims, **kwargs)
        return np.asarray(res)


class StandaloneInferencer:
    """
    Loads saved model bundle and performs offline inference on tiles, images, and PDFs.
    """

    def __init__(
        self,
        checkpoint_dir: Union[str, Path] = CURRENT_DIR,
        device: Optional[str] = None,
    ) -> None:
        p = Path(checkpoint_dir)
        if p.is_file():
            self.checkpoint_dir = p.parent
            self.weights_file = p
        else:
            self.checkpoint_dir = p
            self.weights_file = p / "best_model.pt"

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.config, self.class_mapping = self._load_metadata()
        self.model = self._load_model()
        self.tile_size = int(self.config.get("tile_size") or 512)
        self.hann_window = create_hann_window(self.tile_size)

    def _load_metadata(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        config_path = self.checkpoint_dir / "config.json"
        mapping_path = self.checkpoint_dir / "class_mapping.json"

        if not config_path.exists():
            raise FileNotFoundError(f"Missing config.json in {self.checkpoint_dir}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if mapping_path.exists():
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        else:
            mapping = {"0": "Background", "1": "Drywall", "2": "Non-Drywall", "3": "Uncertain"}

        return config, mapping

    def _load_model(self) -> torch.nn.Module:
        weights_path = self.weights_file
        if not weights_path.exists():
            raise FileNotFoundError(f"Missing checkpoint weights file at {weights_path}")

        arch = str(self.config.get("model_architecture") or self.config.get("architecture") or "segformer").lower()
        num_classes = self.config.get("num_classes", 4)

        from drywall_detection.models.segformer import SegFormerB0, SegFormerWallDetector
        from drywall_detection.models.unet import ResNet34UNet, LightweightUNet, UNetWallDetector

        if "segformer" in arch:
            model = SegFormerB0(num_classes=num_classes, offline=True)
        elif "34" in arch:
            model = ResNet34UNet(num_classes=num_classes, pretrained=False)
        elif "light" in arch:
            model = LightweightUNet(num_classes=num_classes)
        elif "unet" in arch:
            model = UNetWallDetector(num_classes=num_classes, pretrained=False)
        else:
            model = SegFormerB0(num_classes=num_classes, offline=True)

        checkpoint = torch.load(weights_path, map_location=self.device)
        state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()
        return model

    @torch.no_grad()
    def predict_tile(self, tile_img: Image.Image) -> np.ndarray:
        """
        Runs model inference on a single tile PIL image.
        Returns predicted class label array [tile_size, tile_size] uint8.
        """
        target_size = (self.tile_size, self.tile_size)
        if tile_img.size != target_size:
            tile_img = tile_img.resize(target_size, Image.BILINEAR)

        img_t = TF.to_tensor(tile_img.convert("RGB"))
        img_t = TF.normalize(img_t, mean=IMAGENET_MEAN, std=IMAGENET_STD)
        x = img_t.unsqueeze(0).to(self.device)

        outputs = self.model(x)
        if hasattr(outputs, "logits"):
            logits = outputs.logits
        elif isinstance(outputs, dict):
            logits = outputs["logits"]
        else:
            logits = outputs

        preds = torch.argmax(logits, dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
        return preds

    @torch.no_grad()
    def predict_image_sliding_window(
        self,
        image: Image.Image,
        tile_size: int = 512,
        overlap: float = 0.2,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs sliding-window inference with Hann window apodization stitching.

        Args:
            image: Full-scale PIL Image (any dimension).
            tile_size: Size of tile square (512).
            overlap: Overlap fraction (0.2 -> 20% overlap).

        Returns:
            mask_uint8: [H, W] predicted class indices in {0, 1, 2, 3}.
            probs: [H, W, 4] smoothed class probabilities.
        """
        img_rgb = image.convert("RGB")
        orig_width, orig_height = img_rgb.size
        num_classes = self.config.get("num_classes", 4)

        # If image dimensions are smaller than tile_size, pad to at least tile_size
        pad_w = max(0, tile_size - orig_width)
        pad_h = max(0, tile_size - orig_height)
        if pad_w > 0 or pad_h > 0:
            padded_img = Image.new("RGB", (orig_width + pad_w, orig_height + pad_h), (255, 255, 255))
            padded_img.paste(img_rgb, (0, 0))
            img_to_process = padded_img
        else:
            img_to_process = img_rgb

        width, height = img_to_process.size

        # If exactly tile size, predict directly
        if width == tile_size and height == tile_size:
            mask = self.predict_tile(img_to_process)
            probs = np.eye(num_classes)[mask].astype(np.float32)
            return mask[:orig_height, :orig_width], DualProbs(probs[:orig_height, :orig_width])

        stride = int(tile_size * (1.0 - overlap))
        prob_canvas = np.zeros((height, width, num_classes), dtype=np.float32)
        weight_canvas = np.zeros((height, width), dtype=np.float32)
        hann = (
            self.hann_window
            if (self.hann_window.shape[0] == tile_size and self.hann_window.shape[1] == tile_size)
            else create_hann_window(tile_size)
        )

        y_coords = list(range(0, height - tile_size + 1, stride))
        if len(y_coords) == 0 or y_coords[-1] + tile_size < height:
            y_coords.append(max(0, height - tile_size))

        x_coords = list(range(0, width - tile_size + 1, stride))
        if len(x_coords) == 0 or x_coords[-1] + tile_size < width:
            x_coords.append(max(0, width - tile_size))

        for y in y_coords:
            for x in x_coords:
                crop = img_to_process.crop((x, y, x + tile_size, y + tile_size))
                crop_t = TF.to_tensor(crop)
                crop_t = TF.normalize(crop_t, mean=IMAGENET_MEAN, std=IMAGENET_STD)
                x_tensor = crop_t.unsqueeze(0).to(self.device)

                outputs = self.model(x_tensor)
                logits = outputs.logits if hasattr(outputs, "logits") else (outputs["logits"] if isinstance(outputs, dict) else outputs)
                probs = F.softmax(logits, dim=1).squeeze(0).permute(1, 2, 0).cpu().numpy()

                # Weight by 2D Hann apodization window
                weighted_probs = probs * hann[:, :, np.newaxis]
                prob_canvas[y : y + tile_size, x : x + tile_size] += weighted_probs
                weight_canvas[y : y + tile_size, x : x + tile_size] += hann

        # Normalize stitched probabilities
        valid_weights = np.maximum(weight_canvas, 1e-5)[:, :, np.newaxis]
        norm_probs = prob_canvas / valid_weights
        predicted_mask = np.argmax(norm_probs, axis=-1).astype(np.uint8)

        # Unpad back to original dimensions
        predicted_mask = predicted_mask[:orig_height, :orig_width]
        norm_probs = norm_probs[:orig_height, :orig_width]

        return predicted_mask, DualProbs(norm_probs)

    def render_mask_rgb(self, mask_uint8: np.ndarray) -> np.ndarray:
        """Converts 2D uint8 class index mask to 3-channel RGB image."""
        H, W = mask_uint8.shape
        rgb = np.full((H, W, 3), 255, dtype=np.uint8)
        for class_idx, color in CLASS_COLORS.items():
            if class_idx == 0:
                continue
            match = (mask_uint8 == class_idx)
            rgb[match] = color
        return rgb

    def render_overlay(
        self,
        image_rgb: np.ndarray,
        mask_uint8: np.ndarray,
        alpha: float = 0.45,
    ) -> np.ndarray:
        """Blends 4-class segmentation colors onto image."""
        overlay = image_rgb.copy().astype(np.float32)
        for class_idx, color in CLASS_COLORS.items():
            if class_idx == 0:
                continue
            match = (mask_uint8 == class_idx)
            if np.any(match):
                c_rgb = np.array(color, dtype=np.float32)
                overlay[match] = (1.0 - alpha) * overlay[match] + alpha * c_rgb
        return np.clip(overlay, 0, 255).astype(np.uint8)

    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        output_path: Union[str, Path],
        page_num: Optional[int] = None,
        dpi: int = 150,
        alpha: float = 0.45,
    ) -> None:
        """
        Renders PDF page(s) via PyMuPDF (fitz), runs sliding-window inference,
        and generates annotated output.
        """
        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF (fitz) is required for PDF inference. Install via pip install pymupdf")

        pdf_path = Path(pdf_path)
        out_path = Path(output_path)
        doc = fitz.open(pdf_path)

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        pages_to_process = [page_num] if page_num is not None else list(range(len(doc)))
        logger.info("Processing %d pages from %s at %d DPI...", len(pages_to_process), pdf_path.name, dpi)

        annotated_images: List[Image.Image] = []

        for p_idx in pages_to_process:
            page = doc.load_page(p_idx)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            logger.info("Running sliding-window inference on page %d (%dx%d)...", p_idx, pix.width, pix.height)
            mask, _ = self.predict_image_sliding_window(img)
            overlay = self.render_overlay(np.array(img), mask, alpha=alpha)
            annotated_images.append(Image.fromarray(overlay))

        doc.close()

        if str(out_path).lower().endswith(".pdf"):
            if len(annotated_images) == 1:
                annotated_images[0].save(out_path, "PDF", resolution=dpi)
            else:
                annotated_images[0].save(
                    out_path,
                    "PDF",
                    resolution=dpi,
                    save_all=True,
                    append_images=annotated_images[1:],
                )
            logger.info("Saved annotated PDF to %s", out_path)
        else:
            # Save as image (if single page) or series
            if len(annotated_images) == 1:
                annotated_images[0].save(out_path)
                logger.info("Saved annotated image to %s", out_path)
            else:
                stem = out_path.stem
                parent = out_path.parent
                ext = out_path.suffix or ".png"
                for i, img in enumerate(annotated_images):
                    p_path = parent / f"{stem}_page_{i+1}{ext}"
                    img.save(p_path)
                logger.info("Saved %d annotated page images to %s", len(annotated_images), parent)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone offline inference CLI for drywall and architectural wall segmentation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--image", "--input", "-i", dest="input", type=str, required=True, help="Path to input image (.png/.jpg) or PDF (.pdf)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save annotated output (.png/.pdf)")
    parser.add_argument("--checkpoint", "--checkpoint-dir", "-c", dest="checkpoint", type=str, default=str(CURRENT_DIR), help="Path to checkpoint file or directory")
    parser.add_argument("--page", "-p", type=int, default=None, help="Page index (0-based) if input is PDF (default: all pages)")
    parser.add_argument("--dpi", type=int, default=150, help="Rendering resolution in DPI for PDF pages")
    parser.add_argument("--device", "-d", type=str, default=None, help="Execution device: 'cpu' or 'cuda'")
    parser.add_argument("--alpha", type=float, default=0.45, help="Alpha blending transparency for wall annotations")
    parser.add_argument("--mode", type=str, choices=["overlay", "mask"], default="overlay", help="Output mode")
    parser.add_argument("--tile-size", type=int, default=512, help="Sliding-window tile size in pixels")
    parser.add_argument("--overlap", type=float, default=0.20, help="Sliding-window overlap fraction")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_annotated.png"

    t0 = time.time()
    inferencer = StandaloneInferencer(checkpoint_dir=args.checkpoint, device=args.device)

    summary_stats = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "device": str(inferencer.device),
        "architecture": inferencer.config.get("model_architecture") or inferencer.config.get("architecture"),
    }

    if input_path.suffix.lower() == ".pdf":
        inferencer.process_pdf(
            pdf_path=input_path,
            output_path=output_path,
            page_num=args.page,
            dpi=args.dpi,
            alpha=args.alpha,
        )
        summary_stats["status"] = "success"
        summary_stats["type"] = "pdf"
        summary_stats["elapsed_sec"] = round(time.time() - t0, 3)
    else:
        # Image input
        image = Image.open(input_path).convert("RGB")
        mask, _ = inferencer.predict_image_sliding_window(
            image,
            tile_size=args.tile_size,
            overlap=args.overlap,
        )

        total_pixels = int(mask.size)
        bg_pixels = int((mask == 0).sum())
        drywall_pixels = int((mask == 1).sum())
        non_drywall_pixels = int((mask == 2).sum())
        uncertain_pixels = int((mask == 3).sum())

        if args.mode == "mask":
            mask_img = Image.fromarray(mask, mode="L")
            mask_img.save(output_path)
            logger.info("Saved predicted mask to %s", output_path)
        else:
            overlay = inferencer.render_overlay(np.array(image), mask, alpha=args.alpha)
            Image.fromarray(overlay).save(output_path)
            logger.info("Saved annotated overlay to %s", output_path)

        summary_stats["status"] = "success"
        summary_stats["type"] = "image"
        summary_stats["dimensions"] = [image.height, image.width]
        summary_stats["pixel_counts"] = {
            "total": total_pixels,
            "background": bg_pixels,
            "drywall": drywall_pixels,
            "non_drywall": non_drywall_pixels,
            "uncertain": uncertain_pixels,
        }
        summary_stats["drywall_percentage"] = round((drywall_pixels / total_pixels) * 100.0, 3)
        summary_stats["elapsed_sec"] = round(time.time() - t0, 3)

    print(json.dumps(summary_stats, indent=2))


if __name__ == "__main__":
    main()
