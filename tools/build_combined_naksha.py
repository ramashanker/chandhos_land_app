#!/usr/bin/env python3
"""Build one lossless village mosaic from the four original BhuNaksha sheets.

The PDFs contain one raster map plus a soft mask.  The fixed translations below
were recovered from repeated edge strips, then refined against the State
Highway 69 centreline and parcel lines crossing the joins.  No parcel geometry
is redrawn or warped.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "docs" / "original"
ASSETS = ROOT / "app" / "assets"
OUTPUT_PDF = ROOT / "docs" / "enhanced" / "BhuNaksha_Chandhos_Combined_One_Page.pdf"

# Origin of each unmodified 2940 x 1524 source canvas in a shared pixel plane.
# Adjacent sheets overlap by only their printed edge strip.
PLACEMENTS = {
    1: (0, 54),
    2: (1275, 0),
    3: (1545, 791),
    # Sheet 4 is aligned to Sheet 3 where the divided SH69 carriageway crosses
    # the cut beside Plots 2761 and 2766. The y=932 placement makes all three
    # printed carriageway edges continuous at the shared seam.
    4: (472, 932),
}
UPSCALE = 3
MARGIN = 40
# Preserve the established Overall coordinate system across rebuilds.
CANVAS_ORIGIN = (847, 91)

# Each neighbouring PDF repeats a narrow printed edge strip.  Assigning that
# strip to one sheet on either side of a shared seam prevents semi-transparent
# edge pixels from being composited twice (the visible ghost/overlap conflict).
EDGE_JOINS = (
    (1, 2, "vertical"),
    (2, 3, "horizontal"),
    (4, 3, "vertical"),
)


def extract_layer(pdf: Path, directory: Path, sheet: int) -> Image.Image:
    prefix = directory / f"sheet{sheet}"
    subprocess.run(
        ["pdfimages", "-png", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    colour = Image.open(directory / f"sheet{sheet}-000.png").convert("RGB")
    alpha = Image.open(directory / f"sheet{sheet}-001.png").convert("L")
    colour.putalpha(alpha)
    return colour


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = np.asarray(image.getchannel("A"))
    rows, columns = np.where(alpha > 8)
    return int(columns.min()), int(rows.min()), int(columns.max() + 1), int(rows.max() + 1)


def resolve_edge_overlaps(layers: dict[int, Image.Image]) -> list[dict]:
    """Split repeated neighbour strips at one deterministic shared seam."""
    notes = []
    for first, second, orientation in EDGE_JOINS:
        first_image, second_image = layers[first], layers[second]
        first_x, first_y = PLACEMENTS[first]
        second_x, second_y = PLACEMENTS[second]
        first_box = alpha_bbox(first_image)
        second_box = alpha_bbox(second_image)
        left = max(first_x + first_box[0], second_x + second_box[0])
        top = max(first_y + first_box[1], second_y + second_box[1])
        right = min(first_x + first_box[2], second_x + second_box[2])
        bottom = min(first_y + first_box[3], second_y + second_box[3])
        if left >= right or top >= bottom:
            continue

        first_alpha = np.asarray(first_image.getchannel("A")).copy()
        second_alpha = np.asarray(second_image.getchannel("A")).copy()
        first_view = first_alpha[top - first_y:bottom - first_y, left - first_x:right - first_x]
        second_view = second_alpha[
            top - second_y:bottom - second_y,
            left - second_x:right - second_x,
        ]
        shared = (first_view > 0) & (second_view > 0)
        if orientation == "vertical":
            seam = (left + right) / 2
            coordinates = np.arange(left, right)[None, :]
            remove_first = shared & (coordinates >= seam)
            remove_second = shared & (coordinates < seam)
        else:
            seam = (top + bottom) / 2
            coordinates = np.arange(top, bottom)[:, None]
            remove_first = shared & (coordinates >= seam)
            remove_second = shared & (coordinates < seam)
        first_view[remove_first] = 0
        second_view[remove_second] = 0
        first_image.putalpha(Image.fromarray(first_alpha, "L"))
        second_image.putalpha(Image.fromarray(second_alpha, "L"))
        notes.append({
            "sheets": [first, second],
            "orientation": orientation,
            "overlapSourcePixels": {
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
            },
            "seamSourceCoordinate": seam,
            "sharedPixelsResolved": int(shared.sum()),
        })
    return notes


def write_pdf(image_path: Path) -> None:
    width, height = landscape(A3)
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=(width, height), pageCompression=1)
    pdf.setTitle("Chandhaus combined cadastral naksha — Sheets 1 to 4")
    pdf.setAuthor("Combined from the original Bihar BhuNaksha raster sheets")
    pdf.setSubject("One-page lossless mosaic; parcel geometry is not redrawn or warped")
    with Image.open(image_path) as image:
        ratio = min((width - 36) / image.width, (height - 36) / image.height)
        draw_width, draw_height = image.width * ratio, image.height * ratio
        pdf.drawImage(
            ImageReader(str(image_path)),
            (width - draw_width) / 2,
            (height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
        )
    pdf.showPage()
    pdf.save()


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    layers: dict[int, Image.Image] = {}

    with tempfile.TemporaryDirectory(prefix="chandhaus-mosaic-") as temp_name:
        temp = Path(temp_name)
        for sheet in range(1, 5):
            layers[sheet] = extract_layer(
                ORIGINALS / f"BhuNaksha_Chandhos{sheet}.pdf", temp, sheet
            )

        overlap_notes = resolve_edge_overlaps(layers)

        extents = []
        for sheet, image in layers.items():
            x, y = PLACEMENTS[sheet]
            left, top, right, bottom = alpha_bbox(image)
            extents.append((x + left, y + top, x + right, y + bottom))
        crop_left, crop_top = CANVAS_ORIGIN
        crop_right = max(item[2] for item in extents) + MARGIN
        crop_bottom = max(item[3] for item in extents) + MARGIN

        mosaic = Image.new(
            "RGBA", (crop_right - crop_left, crop_bottom - crop_top), (255, 255, 255, 0)
        )
        sheet_bounds = {}
        for sheet, image in layers.items():
            x, y = PLACEMENTS[sheet]
            mosaic.alpha_composite(image, (x - crop_left, y - crop_top))
            left, top, right, bottom = alpha_bbox(image)
            sheet_bounds[str(sheet)] = {
                "x": (x + left - crop_left) * UPSCALE,
                "y": (y + top - crop_top) * UPSCALE,
                "width": (right - left) * UPSCALE,
                "height": (bottom - top) * UPSCALE,
            }

        white = Image.new("RGB", mosaic.size, "white")
        white.paste(mosaic, mask=mosaic.getchannel("A"))
        enlarged = white.resize(
            (white.width * UPSCALE, white.height * UPSCALE), Image.LANCZOS
        )
        enlarged = ImageEnhance.Contrast(enlarged).enhance(1.10)
        enlarged = enlarged.filter(
            ImageFilter.UnsharpMask(radius=0.8, percent=125, threshold=2)
        )

        image_path = ASSETS / "BhuNaksha_Chandhos_Combined.png"
        enlarged.save(image_path, format="PNG", optimize=True, dpi=(300, 300))

        boundary = np.asarray(mosaic.getchannel("A")) > 8
        boundary_image = np.zeros((*boundary.shape, 4), dtype=np.uint8)
        boundary_image[boundary] = (255, 190, 40, 65)
        outline = boundary & ~np.asarray(
            Image.fromarray(boundary).filter(ImageFilter.MinFilter(5)), dtype=bool
        )
        boundary_image[outline] = (225, 66, 42, 230)
        Image.fromarray(boundary_image, "RGBA").save(
            ASSETS / "BhuNaksha_Chandhos_Combined_Boundary.png", optimize=True
        )

        # Transparent cadastral linework for visual comparison with satellite
        # imagery. Geometry remains untouched; only colour/alpha are changed.
        native_rgb = np.asarray(white)
        grey = np.dot(native_rgb[..., :3], [0.299, 0.587, 0.114])
        geo_overlay = np.zeros((*boundary.shape, 4), dtype=np.uint8)
        geo_overlay[boundary, :3] = (238, 180, 43)
        geo_overlay[boundary, 3] = 54
        ink = boundary & (grey < 205)
        ink_alpha = np.clip((215 - grey) * 2.2 + 75, 90, 255).astype(np.uint8)
        geo_overlay[ink, :3] = (12, 30, 22)
        geo_overlay[ink, 3] = ink_alpha[ink]
        Image.fromarray(geo_overlay, "RGBA").save(
            ASSETS / "BhuNaksha_Chandhos_Combined_GeoOverlay.png", optimize=True
        )

        metadata = {
            "width": enlarged.width,
            "height": enlarged.height,
            "sourceScale": UPSCALE,
            "registration": "edge strips + SH69, paeen and canal continuity; translation only; repeated edge pixels split at shared seams; no warping",
            "registrationNotes": {
                "sheet4": "placed at y=932 from the Plot 2761/2766 SH69 control; all three printed carriageway edges continue across the Sheet 4–3 join",
                "edgeOverlapResolution": overlap_notes,
            },
            "cropOrigin": {"x": crop_left, "y": crop_top},
            "placements": {
                str(sheet): {"x": point[0], "y": point[1]}
                for sheet, point in PLACEMENTS.items()
            },
            "sheetBounds": sheet_bounds,
        }
        (ASSETS / "chandhaus-combined-layout.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        write_pdf(image_path)

    print(f"{image_path.relative_to(ROOT)}: {enlarged.width}x{enlarged.height}")
    print(OUTPUT_PDF.relative_to(ROOT))


if __name__ == "__main__":
    main()
