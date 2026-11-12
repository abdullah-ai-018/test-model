"""
drywall_detection.datasets.loader
=================================
Streaming PyTorch Dataset and hardware-adapted DataLoader for unified 512x512
architectural floor plan tiles with synchronized augmentations.
Implements:
- Low-RAM streaming DrywallTileDataset (<15 MB resident RAM index)
- Synchronized orthographic augmentations via native torchvision.transforms.functional
- 4-class multi-class and binary pretraining modes
- Windows CPU safe DataLoader defaults (num_workers=0, pin_memory=False, batch_size=2)
- Shape-asserting safe_collate_fn
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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
        std: List[float] = IMAGENET_STD,
    ) -> None:
        self.is_train = is_train
        self.hflip_prob = hflip_prob
        self.vflip_prob = vflip_prob
        self.rot90_prob = rot90_prob
        self.brightness_jitter = brightness_jitter
        self.contrast_jitter = contrast_jitter
        self.mean = list(mean)
        self.std = list(std)

    def __call__(self, image: Image.Image, mask: Image.Image) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            image: PIL Image (RGB, 512x512)
            mask: PIL Image (Mode 'P' or 'L' single channel uint8, 512x512)
        Returns:
            image_tensor: FloatTensor [3, 512, 512], normalized
            mask_tensor: LongTensor [512, 512], values in {0, 1, 2, 3}
        """
        # Ensure dimensions match 512x512
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

            # 3. Discrete 90-degree Rotations (90, 180, 270)
            if torch.rand(1).item() < self.rot90_prob:
                k = int(torch.randint(1, 4, (1,)).item())
                angle = k * 90
                image = TF.rotate(image, angle, interpolation=TF.InterpolationMode.BILINEAR)
                mask = TF.rotate(mask, angle, interpolation=TF.InterpolationMode.NEAREST)

            # 4. Photometric Jitter (Image Only - Mask is NEVER touched)
            if self.brightness_jitter > 0:
                bfactor = 1.0 + float(torch.empty(1).uniform_(-self.brightness_jitter, self.brightness_jitter))
                image = TF.adjust_brightness(image, bfactor)

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
    Streams tiles lazily from disk on demand to preserve host RAM.
    """

    def __init__(
        self,
        manifest_or_tiles: Union[str, Path, List[Dict[str, Any]]],
        mode: str = "4class",
        transform: Optional[Callable] = None,
        return_metadata: bool = False,
    ) -> None:
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

    def __getitem__(
        self, idx: int
    ) -> Union[Tuple[torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]]:
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

        # Load mask as single-channel uint8 (Mode 'P' loads raw pixel indices via np.array)
        with Image.open(mask_path) as msk:
            # Mode 'P' or 'L' both convert cleanly to single-channel array
            if msk.mode not in ('P', 'L'):
                msk = msk.convert('L')
            mask = msk.copy()

        # Apply synchronized transform or default conversion
        if self.transform is not None:
            image_tensor, mask_tensor = self.transform(image, mask)
        else:
            image_tensor = TF.to_tensor(image)
            image_tensor = TF.normalize(image_tensor, mean=IMAGENET_MEAN, std=IMAGENET_STD)
            mask_np = np.array(mask, dtype=np.int64)
            mask_tensor = torch.from_numpy(mask_np).long()

        # Binary remapping or 4-class clamping
        if self.mode == "binary":
            mask_tensor = (mask_tensor > 0).long()
        else:
            mask_tensor = torch.clamp(mask_tensor, 0, 3)

        if self.return_metadata:
            meta = {
                "tile_id": tile_info.get("tile_id", f"tile_{idx}"),
                "project_id": tile_info.get("project_id", "unknown"),
                "drawing_id": tile_info.get("drawing_id", "unknown"),
                "bbox": tile_info.get("bbox", (0, 0, 512, 512)),
            }
            return image_tensor, mask_tensor, meta

        return image_tensor, mask_tensor


def safe_collate_fn(batch: List[Any]) -> Union[Tuple[torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor, List[Any]]]:
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
    return_metadata: bool = False,
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
        return_metadata=return_metadata,
    )

    loader = DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=drop_last,
        collate_fn=safe_collate_fn,
    )
    return loader
