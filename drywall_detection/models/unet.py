"""
drywall_detection.models.unet
=============================
Native PyTorch ResNet18 U-Net semantic segmentation architecture for
architectural wall detection and drywall classification.

Features:
- Native torchvision.models.resnet18 hierarchical encoder.
- Symmetrical 4-stage convolutional decoder with skip connections.
- Parameter count: ~14.34M parameters (54.7 MB float32 weights).
- Zero third-party library dependencies (no segmentation_models_pytorch).
- Resilient offline fallback when pretrained weights are unavailable.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
import torchvision.models as models

logger = logging.getLogger(__name__)


class DoubleConv(nn.Module):
    """
    Standard U-Net Double Convolution block:
    [Conv2d -> BatchNorm -> ReLU] x 2
    """

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class DecoderBlock(nn.Module):
    """
    Decoder block with transposed convolution upsampling and skip-connection concatenation.
    """

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int) -> None:
        super().__init__()
        self.upsample = nn.ConvTranspose2d(
            in_channels,
            in_channels // 2,
            kernel_size=2,
            stride=2,
        )
        self.conv = DoubleConv(in_channels // 2 + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: Optional[torch.Tensor] = None) -> torch.Tensor:
        x_up = self.upsample(x)
        if skip is not None:
            # Handle possible 1-pixel rounding differences in odd resolutions
            if x_up.shape[2:] != skip.shape[2:]:
                diff_y = skip.size(2) - x_up.size(2)
                diff_x = skip.size(3) - x_up.size(3)
                x_up = nn.functional.pad(
                    x_up,
                    [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2],
                )
            x_cat = torch.cat([x_up, skip], dim=1)
        else:
            x_cat = x_up
        return self.conv(x_cat)


class UNetWallDetector(nn.Module):
    """
    ResNet18 U-Net for architectural wall segmentation.
    Produces output logits of shape [B, num_classes, H, W].
    """

    def __init__(
        self,
        num_classes: int = 4,
        in_channels: int = 3,
        pretrained: bool = False,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.in_channels = in_channels

        # 1. ResNet18 Encoder
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        try:
            backbone = models.resnet18(weights=weights)
        except Exception as exc:
            logger.warning("Could not download ResNet18 weights (%s); initializing with weights=None.", exc)
            backbone = models.resnet18(weights=None)

        if in_channels != 3:
            # Adapt first conv layer for custom input channel count
            self.encoder0 = nn.Sequential(
                nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
                backbone.bn1,
                backbone.relu,
            )
        else:
            self.encoder0 = nn.Sequential(
                backbone.conv1,
                backbone.bn1,
                backbone.relu,
            )

        self.maxpool = backbone.maxpool
        self.encoder1 = backbone.layer1  # 64 channels
        self.encoder2 = backbone.layer2  # 128 channels
        self.encoder3 = backbone.layer3  # 256 channels
        self.encoder4 = backbone.layer4  # 512 channels (bottleneck)

        # 2. Symmetrical Convolutional Decoder
        # up4: 512 -> 256, skip from encoder3 (256) -> dec output 256
        self.dec4 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256)
        # up3: 256 -> 128, skip from encoder2 (128) -> dec output 128
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128)
        # up2: 128 -> 64, skip from encoder1 (64) -> dec output 64
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)
        # up1: 64 -> 32 (upsample=ConvTrans(64, 32)), skip from encoder0 (64) -> dec output 64
        self.up1 = nn.ConvTranspose2d(64, 64, kernel_size=2, stride=2)
        self.dec1 = DoubleConv(64 + 64, 64)

        # up0: from H/2 to H
        self.up0 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec0 = DoubleConv(32, 32)

        # 3. Final 1x1 classification head
        self.final_conv = nn.Conv2d(32, num_classes, kernel_size=1)

    def forward(
        self,
        x: torch.Tensor,
        return_dict: bool = False,
    ) -> Union[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass producing [B, num_classes, H, W] logits.
        """
        # Encoder forward pass
        e0 = self.encoder0(x)         # [B, 64, H/2, W/2]
        x_mp = self.maxpool(e0)       # [B, 64, H/4, W/4]
        e1 = self.encoder1(x_mp)      # [B, 64, H/4, W/4]
        e2 = self.encoder2(e1)        # [B, 128, H/8, W/8]
        e3 = self.encoder3(e2)        # [B, 256, H/16, W/16]
        e4 = self.encoder4(e3)        # [B, 512, H/32, W/32]

        # Decoder forward pass with skip connections
        d4 = self.dec4(e4, e3)        # [B, 256, H/16, W/16]
        d3 = self.dec3(d4, e2)        # [B, 128, H/8, W/8]
        d2 = self.dec2(d3, e1)        # [B, 64, H/4, W/4]

        # up1 to H/2, cat with e0
        u1 = self.up1(d2)             # [B, 64, H/2, W/2]
        d1 = self.dec1(torch.cat([u1, e0], dim=1))  # [B, 64, H/2, W/2]

        # up0 to H
        u0 = self.up0(d1)             # [B, 32, H, W]
        d0 = self.dec0(u0)            # [B, 32, H, W]

        logits = self.final_conv(d0)  # [B, num_classes, H, W]

        if return_dict:
            return {"logits": logits}
        return logits

    def count_parameters(self) -> int:
        """Returns total parameter count."""
        return sum(p.numel() for p in self.parameters())

    def count_trainable_parameters(self) -> int:
        """Returns total trainable parameter count."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_unet(
    num_classes: int = 4,
    in_channels: int = 3,
    pretrained: bool = False,
    backbone: str = "resnet18",
    **kwargs: Any,
) -> nn.Module:
    """
    Factory helper to construct U-Net variants.
    Supports backbone="resnet34", "resnet18", or "lightweight".
    """
    b = backbone.lower()
    if "34" in b:
        return ResNet34UNet(
            num_classes=num_classes,
            in_channels=in_channels,
            pretrained=pretrained,
        )
    elif "light" in b:
        return LightweightUNet(
            num_classes=num_classes,
            in_channels=in_channels,
        )
    return UNetWallDetector(
        num_classes=num_classes,
        in_channels=in_channels,
        pretrained=pretrained,
    )


class ResNet34UNet(nn.Module):
    """
    ResNet-34 U-Net for architectural wall segmentation.
    Uses native torchvision.models.resnet34 encoder with symmetrical
    transposed convolution decoder and skip connections.
    Produces output logits of shape [B, num_classes, H, W].
    Total parameters: ~24.43M.
    """

    def __init__(
        self,
        num_classes: int = 4,
        in_channels: int = 3,
        pretrained: bool = False,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.in_channels = in_channels

        # ResNet34 Encoder
        weights = models.ResNet34_Weights.DEFAULT if pretrained else None
        try:
            backbone = models.resnet34(weights=weights)
        except Exception as exc:
            logger.warning("Could not download ResNet34 weights (%s); initializing with weights=None.", exc)
            backbone = models.resnet34(weights=None)

        if in_channels != 3:
            self.encoder0 = nn.Sequential(
                nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
                backbone.bn1,
                backbone.relu,
            )
        else:
            self.encoder0 = nn.Sequential(
                backbone.conv1,
                backbone.bn1,
                backbone.relu,
            )

        self.maxpool = backbone.maxpool
        self.encoder1 = backbone.layer1  # 64 channels
        self.encoder2 = backbone.layer2  # 128 channels
        self.encoder3 = backbone.layer3  # 256 channels
        self.encoder4 = backbone.layer4  # 512 channels (bottleneck)

        # Symmetrical Convolutional Decoder
        self.dec4 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256)
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128)
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)
        self.up1 = nn.ConvTranspose2d(64, 64, kernel_size=2, stride=2)
        self.dec1 = DoubleConv(64 + 64, 64)

        self.up0 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec0 = DoubleConv(32, 32)

        self.final_conv = nn.Conv2d(32, num_classes, kernel_size=1)

    def forward(
        self,
        x: torch.Tensor,
        return_dict: bool = False,
    ) -> Union[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass producing [B, num_classes, H, W] logits.
        """
        e0 = self.encoder0(x)         # [B, 64, H/2, W/2]
        x_mp = self.maxpool(e0)       # [B, 64, H/4, W/4]
        e1 = self.encoder1(x_mp)      # [B, 64, H/4, W/4]
        e2 = self.encoder2(e1)        # [B, 128, H/8, W/8]
        e3 = self.encoder3(e2)        # [B, 256, H/16, W/16]
        e4 = self.encoder4(e3)        # [B, 512, H/32, W/32]

        d4 = self.dec4(e4, e3)        # [B, 256, H/16, W/16]
        d3 = self.dec3(d4, e2)        # [B, 128, H/8, W/8]
        d2 = self.dec2(d3, e1)        # [B, 64, H/4, W/4]

        u1 = self.up1(d2)             # [B, 64, H/2, W/2]
        d1 = self.dec1(torch.cat([u1, e0], dim=1))  # [B, 64, H/2, W/2]

        u0 = self.up0(d1)             # [B, 32, H, W]
        d0 = self.dec0(u0)            # [B, 32, H, W]

        logits = self.final_conv(d0)  # [B, num_classes, H, W]

        if return_dict:
            return {"logits": logits}
        return logits

    def count_parameters(self) -> int:
        """Returns total parameter count."""
        return sum(p.numel() for p in self.parameters())

    def count_trainable_parameters(self) -> int:
        """Returns total trainable parameter count."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class LightweightUNet(nn.Module):
    """
    Lightweight 4-stage convolutional U-Net for ultra-fast CPU inference.
    Features:
    - 4 encoder stages (32 -> 64 -> 128 -> 256)
    - Bottleneck (512)
    - 4 decoder stages with skip connections
    - Total parameters: ~7.76M.
    """

    def __init__(
        self,
        num_classes: int = 4,
        in_channels: int = 3,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.in_channels = in_channels

        self.enc1 = DoubleConv(in_channels, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = DoubleConv(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.enc3 = DoubleConv(64, 128)
        self.pool3 = nn.MaxPool2d(2)
        self.enc4 = DoubleConv(128, 256)
        self.pool4 = nn.MaxPool2d(2)

        self.bottleneck = DoubleConv(256, 512)

        self.dec4 = DecoderBlock(512, 256, 256)
        self.dec3 = DecoderBlock(256, 128, 128)
        self.dec2 = DecoderBlock(128, 64, 64)
        self.dec1 = DecoderBlock(64, 32, 32)

        self.final_conv = nn.Conv2d(32, num_classes, kernel_size=1)

    def forward(
        self,
        x: torch.Tensor,
        return_dict: bool = False,
    ) -> Union[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass producing [B, num_classes, H, W] logits.
        """
        e1 = self.enc1(x)                # [B, 32, H, W]
        e2 = self.enc2(self.pool1(e1))   # [B, 64, H/2, W/2]
        e3 = self.enc3(self.pool2(e2))   # [B, 128, H/4, W/4]
        e4 = self.enc4(self.pool3(e3))   # [B, 256, H/8, W/8]

        b = self.bottleneck(self.pool4(e4))  # [B, 512, H/16, W/16]

        d4 = self.dec4(b, e4)            # [B, 256, H/8, W/8]
        d3 = self.dec3(d4, e3)           # [B, 128, H/4, W/4]
        d2 = self.dec2(d3, e2)           # [B, 64, H/2, W/2]
        d1 = self.dec1(d2, e1)           # [B, 32, H, W]

        logits = self.final_conv(d1)     # [B, num_classes, H, W]

        if return_dict:
            return {"logits": logits}
        return logits

    def count_parameters(self) -> int:
        """Returns total parameter count."""
        return sum(p.numel() for p in self.parameters())

    def count_trainable_parameters(self) -> int:
        """Returns total trainable parameter count."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
