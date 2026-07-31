"""Lightweight U-Net for semantic segmentation (tissue / tumor masks).

This is a real, trainable `nn.Module` — not a stub — but it ships with
random initialization (no checkpoint). Train it on tile-level masks (e.g.
CAMELYON16 lesion annotations) and load the resulting `.pt` file via
`load_segmentation_model()` in `models/model_registry.py`. Until then, the
app's segmentation preview falls back to the classical CV tissue mask in
`services/image_processor.py`.

Architecture: standard encoder-decoder U-Net with skip connections
(Ronneberger et al., 2015), configurable depth/width so it stays cheap
enough to run on CPU for demo purposes.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNet(nn.Module):
    """Basic U-Net. Default `base_channels=16` keeps it small enough for CPU inference."""

    def __init__(self, in_channels: int = 3, num_classes: int = 2, base_channels: int = 16):
        super().__init__()
        c = base_channels
        self.enc1 = DoubleConv(in_channels, c)
        self.enc2 = DoubleConv(c, c * 2)
        self.enc3 = DoubleConv(c * 2, c * 4)
        self.enc4 = DoubleConv(c * 4, c * 8)
        self.pool = nn.MaxPool2d(2)

        self.bottleneck = DoubleConv(c * 8, c * 16)

        self.up4 = nn.ConvTranspose2d(c * 16, c * 8, 2, stride=2)
        self.dec4 = DoubleConv(c * 16, c * 8)
        self.up3 = nn.ConvTranspose2d(c * 8, c * 4, 2, stride=2)
        self.dec3 = DoubleConv(c * 8, c * 4)
        self.up2 = nn.ConvTranspose2d(c * 4, c * 2, 2, stride=2)
        self.dec2 = DoubleConv(c * 4, c * 2)
        self.up1 = nn.ConvTranspose2d(c * 2, c, 2, stride=2)
        self.dec1 = DoubleConv(c * 2, c)

        self.out_conv = nn.Conv2d(c, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))

        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.out_conv(d1)


def instance_count_from_mask(mask: "torch.Tensor") -> int:
    """Rough instance count via connected components on a binary mask (Mask R-CNN
    style instance segmentation is a heavier real dependency — see README for the
    `torchvision.models.detection.maskrcnn_resnet50_fpn` integration point)."""
    import cv2
    import numpy as np

    arr = mask.detach().cpu().numpy() if hasattr(mask, "detach") else np.asarray(mask)
    binary = (arr > 0.5).astype(np.uint8)
    num_labels, _ = cv2.connectedComponents(binary)
    return max(int(num_labels) - 1, 0)  # subtract background label
