#!/usr/bin/env python3
"""Run repeatable tiled Tesseract OCR over enhanced Chandhaus rasters.

This is an audit/build helper rather than a browser dependency.  It keeps all
numeric candidates (including alternate readings) so a later build step can
cross-check them against the legal schedule and the same label on another
rendering of the map.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


def starts(length: int, size: int, overlap: int) -> list[int]:
    values = list(range(0, max(1, length - size + 1), size - overlap))
    last = max(0, length - size)
    if not values or values[-1] != last:
        values.append(last)
    return values


def run_tesseract(image: Image.Image, psm: int) -> list[dict[str, str]]:
    with tempfile.NamedTemporaryFile(suffix=".png") as source:
        image.save(source.name)
        result = subprocess.run(
            [
                "tesseract", source.name, "stdout", "--psm", str(psm),
                "-c", "tessedit_char_whitelist=0123456789", "tsv",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    return list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sheet", type=int, default=0)
    parser.add_argument("--tile", type=int, default=1100)
    parser.add_argument("--overlap", type=int, default=180)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--psm", type=int, nargs="+", default=[11])
    parser.add_argument("--rotations", type=int, nargs="+", default=[0, 90, 270])
    args = parser.parse_args()

    source = Image.open(args.image).convert("RGB")
    candidates: list[dict] = []
    x_values = starts(source.width, args.tile, args.overlap)
    y_values = starts(source.height, args.tile, args.overlap)
    total = len(x_values) * len(y_values) * len(args.rotations) * len(args.psm)
    current = 0
    for top in y_values:
        for left in x_values:
            tile = source.crop((left, top, min(left + args.tile, source.width), min(top + args.tile, source.height)))
            grey = ImageEnhance.Contrast(ImageOps.grayscale(tile)).enhance(1.8)
            enlarged = grey.resize((grey.width * args.scale, grey.height * args.scale), Image.LANCZOS)
            for rotation in args.rotations:
                rotated = enlarged.rotate(rotation, expand=True, fillcolor=255)
                for psm in args.psm:
                    current += 1
                    print(f"{current}/{total}: tile {left},{top} rotation {rotation} psm {psm}", flush=True)
                    for row in run_tesseract(rotated, psm):
                        text = (row.get("text") or "").strip()
                        try:
                            confidence = float(row.get("conf", "-1"))
                        except ValueError:
                            continue
                        if not text.isdigit() or not 1 <= len(text) <= 4 or confidence < 0:
                            continue
                        rx = float(row["left"]) + float(row["width"]) / 2
                        ry = float(row["top"]) + float(row["height"]) / 2
                        # Map the centre from the rotated tile back to its source.
                        if rotation == 0:
                            ux, uy = rx, ry
                        elif rotation == 90:
                            ux, uy = rotated.height - ry, rx
                        elif rotation == 270:
                            ux, uy = ry, rotated.width - rx
                        elif rotation == 180:
                            ux, uy = rotated.width - rx, rotated.height - ry
                        else:
                            continue
                        candidates.append({
                            "plot": int(text), "sheet": args.sheet,
                            "x": round(left + ux / args.scale, 2),
                            "y": round(top + uy / args.scale, 2),
                            "confidence": round(confidence / 100, 3),
                            "rotation": rotation, "psm": psm,
                        })
    payload = {
        "image": str(args.image), "width": source.width, "height": source.height,
        "count": len(candidates), "candidates": candidates,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(candidates)} candidates)")


if __name__ == "__main__":
    main()
