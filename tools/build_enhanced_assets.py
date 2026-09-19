#!/usr/bin/env python3
"""Install the user-supplied enhanced naksha PDFs as the app's map assets."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
ENHANCED = ROOT / "docs" / "enhanced"
ASSETS = ROOT / "app" / "assets"
MASTER_PDF = ENHANCED / "Chandhaus_Cadastral_Map_Aligned.pdf"

# Coordinates recovered by registering several parcel-line patches in each
# detailed sheet against the aligned master.  Sheet 01 is the 0.5 master
# reference; the other scales exactly follow the factors printed in the PDF.
SHEET_TRANSFORMS = {
    1: {"scale": 0.5, "x": 1126.0, "y": 250.0},
    2: {"scale": 0.46395, "x": 3214.0, "y": 382.0},
    3: {"scale": 0.6838, "x": 2983.0, "y": 2352.0},
    4: {"scale": 0.8024, "x": 380.0, "y": 2396.0},
}


def extract_images(pdf: Path, prefix: Path) -> list[Path]:
    subprocess.run(
        ["pdfimages", "-png", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return sorted(prefix.parent.glob(f"{prefix.name}-*.png"))


def paper_mask(image: Image.Image) -> np.ndarray:
    """Return the largest connected cream cadastral-paper region."""
    rgb = np.asarray(image.convert("RGB"))
    high = rgb.max(axis=2)
    low = rgb.min(axis=2)
    cream = (rgb[..., 0] > 175) & (rgb[..., 1] > 145) & ((high - low) > 18)
    cream = ndimage.binary_closing(cream, iterations=3)
    labels, count = ndimage.label(cream)
    if not count:
        return cream
    sizes = np.bincount(labels.ravel())
    # A few sheets touch only through thin linework, so retain every substantial
    # paper component rather than assuming the geometry is one polygon.
    threshold = max(500, int(sizes.max() * 0.002))
    mask = sizes[labels] >= threshold
    return ndimage.binary_fill_holes(mask)


def write_boundary(mask: np.ndarray, output: Path, factor: int = 3) -> None:
    small = Image.fromarray((mask * 255).astype(np.uint8), "L").resize(
        (max(1, mask.shape[1] // factor), max(1, mask.shape[0] // factor)),
        Image.LANCZOS,
    )
    alpha = np.asarray(small) > 80
    outline = alpha & ~ndimage.binary_erosion(alpha, iterations=2)
    rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    rgba[alpha] = (255, 190, 40, 62)
    rgba[outline] = (225, 66, 42, 225)
    Image.fromarray(rgba, "RGBA").save(output, optimize=True)


def write_geo_overlay(image: Image.Image, mask: np.ndarray, output: Path, factor: int = 3) -> None:
    size = (max(1, image.width // factor), max(1, image.height // factor))
    rgb = np.asarray(image.convert("RGB").resize(size, Image.LANCZOS))
    small_mask = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8), "L").resize(size, Image.LANCZOS)
    ) > 80
    grey = np.dot(rgb, [0.299, 0.587, 0.114])
    rgba = np.zeros((*small_mask.shape, 4), dtype=np.uint8)
    rgba[small_mask, :3] = (238, 180, 43)
    rgba[small_mask, 3] = 52
    ink = small_mask & (grey < 205)
    rgba[ink, :3] = (12, 30, 22)
    rgba[ink, 3] = np.clip((215 - grey[ink]) * 2.2 + 75, 90, 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(output, optimize=True)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chandhaus-enhanced-") as temp_name:
        temp = Path(temp_name)
        master_files = extract_images(MASTER_PDF, temp / "master")
        master = Image.open(master_files[0]).convert("RGB")
        master.save(
            ASSETS / "BhuNaksha_Chandhos_Combined.png",
            format="PNG", optimize=True, dpi=(225, 225),
        )
        master_mask = paper_mask(master)
        write_boundary(master_mask, ASSETS / "BhuNaksha_Chandhos_Combined_Boundary.png")
        write_geo_overlay(master, master_mask, ASSETS / "BhuNaksha_Chandhos_Combined_GeoOverlay.png")

        sheet_bounds = {}
        for sheet in range(1, 5):
            files = extract_images(
                ENHANCED / f"Chandhaus_Naksha_{sheet:02d}_Enhanced.pdf",
                temp / f"sheet{sheet}",
            )
            colour = Image.open(files[0]).convert("RGB")
            if len(files) > 1:
                alpha = Image.open(files[1]).convert("L")
                white = Image.new("RGB", colour.size, "white")
                white.paste(colour, mask=alpha)
                colour = white
            colour.save(
                ASSETS / f"BhuNaksha_Chandhos{sheet}_HD.jpg",
                format="JPEG", quality=95, subsampling=0, optimize=True, dpi=(225, 225),
            )
            mask = paper_mask(colour)
            write_boundary(mask, ASSETS / f"BhuNaksha_Chandhos{sheet}_Boundary.png", factor=4)
            rows, columns = np.where(mask)
            transform = SHEET_TRANSFORMS[sheet]
            left = transform["x"] + columns.min() * transform["scale"]
            top = transform["y"] + rows.min() * transform["scale"]
            right = transform["x"] + (columns.max() + 1) * transform["scale"]
            bottom = transform["y"] + (rows.max() + 1) * transform["scale"]
            sheet_bounds[str(sheet)] = {
                "x": round(left, 1), "y": round(top, 1),
                "width": round(right - left, 1), "height": round(bottom - top, 1),
            }

        layout = {
            "width": master.width,
            "height": master.height,
            "sourceScale": 1,
            "source": "docs/enhanced/Chandhaus_Cadastral_Map_Aligned.pdf",
            "registration": "User-supplied seam-aligned master; proportional sheet transforms verified against parcel linework",
            "sheetTransforms": {str(key): value for key, value in SHEET_TRANSFORMS.items()},
            "sheetBounds": sheet_bounds,
        }
        (ASSETS / "chandhaus-combined-layout.json").write_text(
            json.dumps(layout, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Installed enhanced master: {master.width}x{master.height}")
        print("Installed four enhanced detail sheets and map boundaries")


if __name__ == "__main__":
    main()
