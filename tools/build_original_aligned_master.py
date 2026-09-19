#!/usr/bin/env python3
"""Build the five-piece Chandhos master from the original HD PDFs.

The supplied sheet01.png through sheet05.png files contain exact quarter-size
alpha silhouettes of the HD rasters. Their complementary edges solve the
puzzle translations without changing scale, rotation, or parcel geometry.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.pagesizes import A1, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from scipy import ndimage

from build_enhanced_assets import write_boundary, write_geo_overlay
from migrate_plot_index_to_enhanced import write_label_svg


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "docs" / "original"
ASSETS = ROOT / "app" / "assets"
OUTPUT_IMAGE = ASSETS / "BhuNaksha_Chandhos_Combined.png"
OUTPUT_PDF = ROOT / "docs" / "enhanced" / "Chandhaus_Cadastral_Map_Original_Aligned.pdf"
WIDTH, HEIGHT = 6328, 6705
SCALE = 1.07

# Exact quarter-scale puzzle solution, using Sheet 01 as the anchor:
#   01=(0,0), 02=(495,35), 04=(-181,508), 03=(488,513), 05=(28,1077).
# Multiplying by four gives native-raster offsets. The common output scale and
# Sheet 01 anchor retain the application's established coordinate system.
TRANSFORMS = {
    1: {"scale": SCALE, "x": 1126.0, "y": 250.0},
    2: {"scale": SCALE, "x": 3244.6, "y": 399.8},
    3: {"scale": SCALE, "x": 3214.6, "y": 2445.6},
    4: {"scale": SCALE, "x": 351.3, "y": 2424.2},
    5: {"scale": SCALE, "x": 1245.8, "y": 4859.6},
}


def extract_image(pdf: Path, temp: Path, sheet: int) -> Image.Image:
    prefix = temp / f"sheet-{sheet}"
    subprocess.run(
        ["pdfimages", "-png", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    files = sorted(temp.glob(f"sheet-{sheet}-*.png"))
    if not files:
        raise RuntimeError(f"No embedded raster found in {pdf}")
    return Image.open(files[0]).convert("RGB")


def guide_mask(sheet: int, source_size: tuple[int, int]) -> np.ndarray:
    """Load the exact silhouette from the supplied quarter-scale PNG guide."""
    guide = Image.open(ORIGINALS / f"sheet{sheet:02d}.png").convert("RGBA")
    alpha = np.asarray(guide.getchannel("A"))
    rows, columns = np.where(alpha > 0)
    crop = guide.getchannel("A").crop(
        (columns.min(), rows.min(), columns.max() + 1, rows.max() + 1)
    )
    expected = (crop.width * 4, crop.height * 4)
    if expected != source_size:
        raise RuntimeError(
            f"Sheet {sheet} guide/source mismatch: {expected} != {source_size}"
        )
    return np.asarray(crop.resize(source_size, Image.LANCZOS)) > 24


def place_sheet(
    sheet: int,
    source: Image.Image,
    source_mask: np.ndarray,
    selected_rgb: np.ndarray,
    selected_mask: np.ndarray,
    best_depth: np.ndarray,
) -> dict:
    transform = TRANSFORMS[sheet]
    width = round(source.width * transform["scale"])
    height = round(source.height * transform["scale"])
    resized = source.resize((width, height), Image.LANCZOS)
    mask = np.asarray(
        Image.fromarray((source_mask * 255).astype(np.uint8), "L").resize(
            (width, height), Image.LANCZOS
        )
    ) > 80
    depth = ndimage.distance_transform_edt(mask)
    rgb = np.asarray(resized)

    left, top = round(transform["x"]), round(transform["y"])
    right, bottom = left + width, top + height
    clip_left, clip_top = max(0, left), max(0, top)
    clip_right, clip_bottom = min(WIDTH, right), min(HEIGHT, bottom)
    sx0, sy0 = clip_left - left, clip_top - top
    sx1, sy1 = sx0 + clip_right - clip_left, sy0 + clip_bottom - clip_top

    incoming_mask = mask[sy0:sy1, sx0:sx1]
    incoming_depth = depth[sy0:sy1, sx0:sx1]
    destination_mask = selected_mask[clip_top:clip_bottom, clip_left:clip_right]
    destination_depth = best_depth[clip_top:clip_bottom, clip_left:clip_right]
    choose = incoming_mask & (~destination_mask | (incoming_depth > destination_depth))
    selected_rgb[clip_top:clip_bottom, clip_left:clip_right][choose] = rgb[sy0:sy1, sx0:sx1][choose]
    destination_mask[choose] = True
    destination_depth[choose] = incoming_depth[choose]

    return {"x": left, "y": top, "width": width, "height": height}


def write_pdf(image_path: Path) -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A1)
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle("Chandhos cadastral map — five original HD sheets aligned")
    pdf.setAuthor("Chandhos land map viewer")
    pdf.setSubject("Boundary-aware, seam-resolved cadastral mosaic with SH69 continuity")
    ratio = min((page_width - 28) / WIDTH, (page_height - 28) / HEIGHT)
    draw_width, draw_height = WIDTH * ratio, HEIGHT * ratio
    draw_left = (page_width - draw_width) / 2
    draw_bottom = (page_height - draw_height) / 2
    pdf.drawImage(
        ImageReader(str(image_path)),
        draw_left,
        draw_bottom,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
    )
    # Invisible, positioned text keeps the original linework uncluttered while
    # making verified plot numbers searchable in standard PDF readers.
    index_path = ASSETS / "plot-index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for item in index.get("plots", []):
            label = str(item["plot"])
            text = pdf.beginText()
            text.setFont("Helvetica-Bold", max(4.0, 18 * ratio))
            text.setTextRenderMode(3)
            text.setTextOrigin(
                draw_left + float(item["x"]) * ratio,
                draw_bottom + (HEIGHT - float(item["y"])) * ratio,
            )
            text.textOut(label)
            pdf.drawText(text)
    pdf.showPage()
    pdf.save()


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    layout_path = ASSETS / "chandhaus-combined-layout.json"
    previous_layout = (
        json.loads(layout_path.read_text(encoding="utf-8"))
        if layout_path.exists() else {"sheetTransforms": {}}
    )
    selected_rgb = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    selected_mask = np.zeros((HEIGHT, WIDTH), dtype=bool)
    best_depth = np.full((HEIGHT, WIDTH), -1.0, dtype=np.float32)
    sheet_bounds = {}

    with tempfile.TemporaryDirectory(prefix="chandhos-five-sheet-") as temp_name:
        temp = Path(temp_name)
        for sheet in range(1, 6):
            pdf = ORIGINALS / f"Chandhos_Paliganj_Naksha_{sheet}_HD.pdf"
            source = extract_image(pdf, temp, sheet)
            mask = guide_mask(sheet, source.size)
            detail = ImageEnhance.Contrast(source).enhance(1.035)
            detail = detail.filter(ImageFilter.UnsharpMask(radius=0.45, percent=55, threshold=3))
            detail.save(
                ASSETS / f"BhuNaksha_Chandhos{sheet}_HD.png",
                format="PNG", optimize=True, dpi=(225, 225),
            )
            write_boundary(mask, ASSETS / f"BhuNaksha_Chandhos{sheet}_Boundary.png", factor=4)
            sheet_bounds[str(sheet)] = place_sheet(
                sheet, source, mask, selected_rgb, selected_mask, best_depth
            )
            print(f"Placed original HD Sheet {sheet}", flush=True)

    output = Image.fromarray(selected_rgb, "RGB")
    output = ImageEnhance.Contrast(output).enhance(1.035)
    output = output.filter(ImageFilter.UnsharpMask(radius=0.55, percent=70, threshold=3))
    output.save(OUTPUT_IMAGE, format="PNG", optimize=True, dpi=(225, 225))

    write_boundary(selected_mask, ASSETS / "BhuNaksha_Chandhos_Combined_Boundary.png")
    write_geo_overlay(output, selected_mask, ASSETS / "BhuNaksha_Chandhos_Combined_GeoOverlay.png")

    # Move every indexed label with its source piece. This uses the previous
    # layout as the reference, so rebuilding is idempotent.
    index_path = ASSETS / "plot-index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        old_transforms = previous_layout.get("sheetTransforms", {})
        for item in index.get("plots", []):
            key = str(item.get("sheet"))
            old = old_transforms.get(key)
            new = TRANSFORMS.get(int(item.get("sheet", 0)))
            if not old or not new:
                continue
            old_scale = float(old.get("scale", SCALE))
            local_x = (float(item["x"]) - float(old["x"])) / old_scale
            local_y = (float(item["y"]) - float(old["y"])) / old_scale
            item["x"] = round(float(new["x"]) + local_x * float(new["scale"]), 1)
            item["y"] = round(float(new["y"]) + local_y * float(new["scale"]), 1)
        index["imageWidth"], index["imageHeight"] = WIDTH, HEIGHT
        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        write_label_svg(ASSETS / "plot-labels.svg", index["plots"], WIDTH, HEIGHT)
    write_pdf(OUTPUT_IMAGE)

    layout = {
        "width": WIDTH,
        "height": HEIGHT,
        "sourceScale": SCALE,
        "source": "docs/original/Chandhos_Paliganj_Naksha_1_HD.pdf through Chandhos_Paliganj_Naksha_5_HD.pdf",
        "registration": "Exact quarter-scale alpha-silhouette puzzle solution from sheet01.png through sheet05.png; shared boundaries and road intersections close at one common scale; no rotation or local parcel warping",
        "roadControl": "SH69 continuity and landholder-audited roadside plot order",
        "sheetTransforms": {str(key): value for key, value in TRANSFORMS.items()},
        "sheetBounds": sheet_bounds,
        "outputPdf": "docs/enhanced/Chandhaus_Cadastral_Map_Original_Aligned.pdf",
    }
    (ASSETS / "chandhaus-combined-layout.json").write_text(
        json.dumps(layout, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUTPUT_IMAGE.relative_to(ROOT)} ({WIDTH}x{HEIGHT})")
    print(f"Wrote {OUTPUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
