#!/usr/bin/env python3
"""Extract approximate filled sheet silhouettes from the rendered naksha pages."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"


def extract(sheet: int) -> None:
    source = ASSETS / f"BhuNaksha_Chandhos{sheet}_HD.jpg"
    destination = ASSETS / f"BhuNaksha_Chandhos{sheet}_Boundary.png"

    with Image.open(source) as original:
        image = original.convert("RGB")
        image.thumbnail((1100, 1550), Image.LANCZOS)
        pixels = np.asarray(image)

    red, green, blue = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    mask = (
        (red > 225)
        & (green > 165)
        & (green < 248)
        & (blue > 105)
        & (blue < 225)
        & ((red.astype(int) - green.astype(int)) > 8)
    )

    # Join parcels across their thin dark internal boundary lines.
    mask = ndimage.binary_closing(mask, structure=np.ones((9, 9)), iterations=2)
    mask = ndimage.binary_fill_holes(mask)
    labels, count = ndimage.label(mask)
    if not count:
        raise RuntimeError(f"No map silhouette found for sheet {sheet}")
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    mask = labels == (int(np.argmax(sizes)) + 1)
    mask = ndimage.binary_fill_holes(mask)

    rows, columns = np.where(mask)
    pad = 12
    y0, y1 = max(0, rows.min() - pad), min(mask.shape[0], rows.max() + pad + 1)
    x0, x1 = max(0, columns.min() - pad), min(mask.shape[1], columns.max() + pad + 1)
    mask = mask[y0:y1, x0:x1]

    inner = ndimage.binary_erosion(mask, structure=np.ones((5, 5)))
    outline = mask & ~inner
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = (255, 190, 40, 62)
    rgba[outline] = (225, 66, 42, 230)
    Image.fromarray(rgba, "RGBA").save(destination, optimize=True)
    print(f"{destination.relative_to(ROOT)}: {mask.shape[1]}x{mask.shape[0]}")


if __name__ == "__main__":
    for sheet_number in range(1, 5):
        extract(sheet_number)
