#!/usr/bin/env python3
"""Create high-resolution, dimension-preserving BhuNaksha PDFs."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas


PAGE_SIZE = (595.0, 842.0)


def render_and_enhance(source: Path, destination: Path, dpi: int) -> None:
    """Render one PDF page, gently improve legibility, and store a JPEG."""
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-l",
            "1",
            "-r",
            str(dpi),
            "-singlefile",
            "-png",
            str(source),
            str(destination.with_suffix("")),
        ],
        check=True,
    )

    rendered = destination.with_suffix(".png")
    with Image.open(rendered) as image:
        cleaned = image.convert("RGB")
        cleaned = ImageEnhance.Contrast(cleaned).enhance(1.06)
        cleaned = cleaned.filter(
            ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3)
        )
        cleaned.save(
            destination,
            format="JPEG",
            quality=98,
            subsampling=0,
            optimize=True,
            dpi=(dpi, dpi),
        )
    rendered.unlink()


def draw_compass(pdf: canvas.Canvas) -> None:
    """Draw a compact four-direction marker in the page's empty left margin."""
    center_x, center_y = 75.0, 520.0
    radius = 27.0
    ink = HexColor("#202020")

    pdf.saveState()
    pdf.setStrokeColor(ink)
    pdf.setFillColor(white)
    pdf.setLineWidth(1.25)
    pdf.circle(center_x, center_y, radius, stroke=1, fill=1)
    pdf.line(center_x, center_y - radius + 5, center_x, center_y + radius - 5)
    pdf.line(center_x - radius + 5, center_y, center_x + radius - 5, center_y)

    # Filled arrowhead distinguishes geographic north from the other axes.
    arrow_y = center_y + radius - 3
    path = pdf.beginPath()
    path.moveTo(center_x, arrow_y)
    path.lineTo(center_x - 5, arrow_y - 11)
    path.lineTo(center_x + 5, arrow_y - 11)
    path.close()
    pdf.setFillColor(ink)
    pdf.drawPath(path, stroke=0, fill=1)

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(center_x, center_y + radius + 10, "NORTH")
    pdf.drawCentredString(center_x, center_y - radius - 17, "SOUTH")
    pdf.drawRightString(center_x - radius - 5, center_y - 3, "WEST")
    pdf.drawString(center_x + radius + 5, center_y - 3, "EAST")
    pdf.restoreState()


def write_pdf(images: list[Path], output: Path, directions: bool = False) -> None:
    """Place each enhanced page at the originals' exact 595 x 842 pt size."""
    pdf = canvas.Canvas(str(output), pagesize=PAGE_SIZE, pageCompression=1)
    pdf.setTitle(output.stem)
    pdf.setAuthor("Dimension-preserving BhuNaksha enhancement")
    pdf.setSubject("600 DPI cleaned land naksha; original page geometry retained")
    for image in images:
        pdf.drawImage(
            ImageReader(str(image)),
            0,
            0,
            width=PAGE_SIZE[0],
            height=PAGE_SIZE[1],
            preserveAspectRatio=False,
            mask=None,
        )
        if directions:
            draw_compass(pdf)
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument(
        "--directions",
        action="store_true",
        help="Add a north-up compass marker in the empty left margin",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    individual_outputs: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="bhunaksha-enhance-") as temp:
        temp_dir = Path(temp)
        enhanced_images: list[Path] = []
        for source in args.inputs:
            image = temp_dir / f"{source.stem}_HD.jpg"
            render_and_enhance(source, image, args.dpi)
            enhanced_images.append(image)

            suffix = "_HD_Directions" if args.directions else "_HD"
            output = args.output_dir / f"{source.stem}{suffix}.pdf"
            write_pdf([image], output, directions=args.directions)
            individual_outputs.append(output)

        combined_name = (
            "BhuNaksha_Chandhos_1-4_HD_Directions.pdf"
            if args.directions
            else "BhuNaksha_Chandhos_1-4_HD.pdf"
        )
        write_pdf(
            enhanced_images,
            args.output_dir / combined_name,
            directions=args.directions,
        )

    for output in individual_outputs:
        print(output)
    print(args.output_dir / combined_name)


if __name__ == "__main__":
    main()
