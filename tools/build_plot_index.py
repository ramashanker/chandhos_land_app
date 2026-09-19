#!/usr/bin/env python3
"""Build a coordinate index of printed cadastral plot numbers.

The original PDFs are processed in overlapping tiles so small labels are never
reduced to a whole-sheet OCR canvas.  The generated browser index and SVG have
no runtime OCR dependency. Only high-confidence numeric detections in the known
number range for each source sheet are retained.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from build_combined_naksha import (
    ASSETS,
    ORIGINALS,
    PLACEMENTS,
    UPSCALE,
    alpha_bbox,
    extract_layer,
)


ROOT = Path(__file__).resolve().parents[1]
RANGES = {1: (1, 933), 2: (908, 2171), 3: (2170, 3845), 4: (3800, 6500)}
OCR_SCALE = 4
MIN_CONFIDENCE = 0.65
TILE_SIZE = 720
TILE_OVERLAP = 140
TILE_SCALE = 3

# Manually audited labels requested during development. Coordinates are in the
# untouched 2940 x 1524 source canvas, not in the enlarged combined image.
AUDITED = {
    41: {"sheet": 1, "sourceX": 1529.27, "sourceY": 405.13},
    47: {"sheet": 1, "sourceX": 1477.0, "sourceY": 287.0},
    58: {"sheet": 1, "sourceX": 1395.33, "sourceY": 410.33},
    75: {"sheet": 1, "sourceX": 1387.0, "sourceY": 312.0},
    77: {"sheet": 1, "sourceX": 1403.63, "sourceY": 261.73},
    110: {"sheet": 1, "sourceX": 1189.67, "sourceY": 314.33},
    # Visually audited vertical run beside plots 136 and 143. OCR previously
    # shifted 148 upward onto the parcel that is actually numbered 146.
    137: {"sheet": 1, "sourceX": 1255.67, "sourceY": 543.33},
    138: {"sheet": 1, "sourceX": 1274.67, "sourceY": 553.67},
    144: {"sheet": 1, "sourceX": 1274.67, "sourceY": 566.67},
    145: {"sheet": 1, "sourceX": 1276.4, "sourceY": 582.0},
    146: {"sheet": 1, "sourceX": 1274.67, "sourceY": 599.33},
    147: {"sheet": 1, "sourceX": 1274.67, "sourceY": 615.0},
    148: {"sheet": 1, "sourceX": 1274.67, "sourceY": 630.33},
    149: {"sheet": 1, "sourceX": 1274.67, "sourceY": 643.67},
    # Adjacent narrow parcels immediately west of plot 151.
    152: {"sheet": 1, "sourceX": 1237.33, "sourceY": 634.33},
    153: {"sheet": 1, "sourceX": 1223.67, "sourceY": 625.0},
    # Clear labels recovered by a lower-confidence OCR pass and then checked
    # digit-by-digit against full-resolution raster crops.
    206: {"sheet": 1, "sourceX": 1470.33, "sourceY": 602.0},
    220: {"sheet": 1, "sourceX": 1689.33, "sourceY": 653.67},
    252: {"sheet": 1, "sourceX": 1426.0, "sourceY": 706.67},
    255: {"sheet": 1, "sourceX": 1427.67, "sourceY": 759.67},
    283: {"sheet": 1, "sourceX": 1368.67, "sourceY": 787.67},
    375: {"sheet": 1, "sourceX": 1159.67, "sourceY": 766.67},
    407: {"sheet": 1, "sourceX": 960.67, "sourceY": 798.33},
    442: {"sheet": 1, "sourceX": 1019.33, "sourceY": 872.33},
    # Clear SH69 north-side label between Plots 450 and 362.
    446: {"sheet": 1, "sourceX": 1021.0, "sourceY": 926.3},
    475: {"sheet": 1, "sourceX": 1116.0, "sourceY": 1020.33},
    632: {"sheet": 1, "sourceX": 1656.0, "sourceY": 869.0},
    665: {"sheet": 1, "sourceX": 1440.67, "sourceY": 1042.33},
    719: {"sheet": 1, "sourceX": 1122.0, "sourceY": 604.0},
    808: {"sheet": 1, "sourceX": 1808.0, "sourceY": 841.0},
    810: {"sheet": 1, "sourceX": 1780.67, "sourceY": 818.0},
    837: {"sheet": 1, "sourceX": 1942.0, "sourceY": 701.67},
    900: {"sheet": 1, "sourceX": 1811.33, "sourceY": 377.0},
    924: {"sheet": 2, "sourceX": 692.33, "sourceY": 258.0},
    938: {"sheet": 2, "sourceX": 740.0, "sourceY": 799.67},
    980: {"sheet": 2, "sourceX": 710.0, "sourceY": 740.33},
    989: {"sheet": 2, "sourceX": 756.0, "sourceY": 814.33},
    1055: {"sheet": 2, "sourceX": 843.33, "sourceY": 870.33},
    1081: {"sheet": 2, "sourceX": 994.0, "sourceY": 539.0},
    1087: {"sheet": 2, "sourceX": 744.33, "sourceY": 1193.33},
    1094: {"sheet": 2, "sourceX": 881.33, "sourceY": 819.33},
    1103: {"sheet": 2, "sourceX": 951.0, "sourceY": 644.0},
    1110: {"sheet": 2, "sourceX": 829.0, "sourceY": 779.0},
    1145: {"sheet": 2, "sourceX": 852.83, "sourceY": 415.33},
    1149: {"sheet": 2, "sourceX": 861.67, "sourceY": 379.0},
    1169: {"sheet": 2, "sourceX": 922.67, "sourceY": 256.33},
    1186: {"sheet": 2, "sourceX": 969.67, "sourceY": 678.0},
    1203: {"sheet": 2, "sourceX": 1061.0, "sourceY": 780.0},
    1239: {"sheet": 2, "sourceX": 1364.33, "sourceY": 858.33},
    1265: {"sheet": 2, "sourceX": 1327.67, "sourceY": 797.67},
    1331: {"sheet": 2, "sourceX": 1191.0, "sourceY": 860.0},
    1368: {"sheet": 2, "sourceX": 1258.0, "sourceY": 1054.33},
    1369: {"sheet": 2, "sourceX": 1219.33, "sourceY": 989.33},
    1377: {"sheet": 2, "sourceX": 1134.67, "sourceY": 1078.33},
    1440: {"sheet": 2, "sourceX": 917.0, "sourceY": 1022.67},
    1445: {"sheet": 2, "sourceX": 967.33, "sourceY": 1068.33},
    1585: {"sheet": 2, "sourceX": 1312.33, "sourceY": 1086.33},
    1641: {"sheet": 2, "sourceX": 1430.5, "sourceY": 1156.0},
    1652: {"sheet": 2, "sourceX": 1317.67, "sourceY": 1221.33},
    1710: {"sheet": 2, "sourceX": 1553.0, "sourceY": 1180.67},
    1785: {"sheet": 2, "sourceX": 1410.33, "sourceY": 975.67},
    1805: {"sheet": 2, "sourceX": 1474.67, "sourceY": 861.33},
    1898: {"sheet": 2, "sourceX": 1679.67, "sourceY": 1174.67},
    1947: {"sheet": 2, "sourceX": 1714.0, "sourceY": 1116.33},
    1998: {"sheet": 2, "sourceX": 693.33, "sourceY": 912.67},
    2034: {"sheet": 2, "sourceX": 1749.33, "sourceY": 1106.0},
    2036: {"sheet": 2, "sourceX": 1826.0, "sourceY": 1108.0},
    2113: {"sheet": 2, "sourceX": 1993.67, "sourceY": 1068.33},
    2127: {"sheet": 2, "sourceX": 1927.0, "sourceY": 1186.0},
    2167: {"sheet": 2, "sourceX": 1880.33, "sourceY": 1086.0},
    2565: {"sheet": 3, "sourceX": 1200.5, "sourceY": 474.6},
    2636: {"sheet": 3, "sourceX": 983.67, "sourceY": 492.67},
    2761: {"sheet": 3, "sourceX": 885.5, "sourceY": 706.2},
    2766: {"sheet": 3, "sourceX": 943.33, "sourceY": 734.33},
    2868: {"sheet": 3, "sourceX": 1131.33, "sourceY": 586.67},
    2919: {"sheet": 3, "sourceX": 1355.5, "sourceY": 671.17},
    3027: {"sheet": 3, "sourceX": 1125.33, "sourceY": 659.67},
    3385: {"sheet": 3, "sourceX": 1130.33, "sourceY": 1239.67},
    3631: {"sheet": 3, "sourceX": 1206.0, "sourceY": 938.0},
    3803: {"sheet": 3, "sourceX": 1097.67, "sourceY": 694.0},
    3827: {"sheet": 3, "sourceX": 915.67, "sourceY": 1097.67},
    3693: {"sheet": 3, "sourceX": 1013.0, "sourceY": 944.0},
    4042: {"sheet": 4, "sourceX": 1282.0, "sourceY": 720.17},
    4144: {"sheet": 4, "sourceX": 1821.5, "sourceY": 523.2},
    4170: {"sheet": 4, "sourceX": 1761.0, "sourceY": 458.67},
    4178: {"sheet": 4, "sourceX": 1755.2, "sourceY": 483.8},
    # SH69 north-side run supplied by the landholder. The user-provided order
    # resolves the road-side 4207 label west of the adjacent narrow 4206 plot.
    4206: {"sheet": 4, "sourceX": 1645.0, "sourceY": 420.0},
    4207: {"sheet": 4, "sourceX": 1518.0, "sourceY": 456.0},
    4209: {"sheet": 4, "sourceX": 1700.0, "sourceY": 390.0},
    4385: {"sheet": 4, "sourceX": 1606.33, "sourceY": 682.0},
    4668: {"sheet": 4, "sourceX": 1295.67, "sourceY": 525.67},
    4883: {"sheet": 4, "sourceX": 1395.33, "sourceY": 814.67},
    5280: {"sheet": 4, "sourceX": 1724.67, "sourceY": 912.67},
    5900: {"sheet": 4, "sourceX": 1643.33, "sourceY": 1026.33},
    5902: {"sheet": 4, "sourceX": 1439.67, "sourceY": 1043.0},
    5906: {"sheet": 4, "sourceX": 1563.83, "sourceY": 1048.83},
    6035: {"sheet": 4, "sourceX": 1219.0, "sourceY": 757.67},
    6049: {"sheet": 4, "sourceX": 1188.0, "sourceY": 691.67},
    6438: {"sheet": 4, "sourceX": 1457.17, "sourceY": 1122.67},
}

# Visually rejected OCR readings. These were inspected at full source detail
# and were alternate readings of another label at the same coordinates (for
# example 908 read as 948). The raster label remains visible, but no incorrect
# clear/search label is emitted.
REJECTED_OCR = {
    1, 4, 8, 9, 14, 23, 33, 39, 40, 69, 72, 74, 79, 183, 235, 239,
    333, 416, 457, 470, 650, 748, 785, 863, 930, 948, 1183,
    1342, 1676, 1924, 3433, 3663, 4172, 4333, 4421, 4648, 4887,
    5059, 5875, 5975,
    6155, 6188,
}

# User-supplied topological constraint: these plots occur in this order along
# the north side of SH69. The labels are source-verified; the polyline between
# them is only an alignment guide, especially where the source sheets contain
# no map coverage.
SH69_NORTH_PLOT_ORDER = (
    450, 446, 362, 528, 520, 573,
    4209, 4208, 4207, 4206, 4178, 4144, 2761, 2782,
)


def combined_point(sheet: int, source_x: float, source_y: float, layout: dict) -> tuple[float, float]:
    origin = layout["cropOrigin"]
    placement = PLACEMENTS[sheet]
    return (
        (placement[0] + source_x - origin["x"]) * UPSCALE,
        (placement[1] + source_y - origin["y"]) * UPSCALE,
    )


def tile_starts(start: int, stop: int, size: int, overlap: int) -> list[int]:
    if stop - start <= size:
        return [start]
    values = list(range(start, stop - size + 1, size - overlap))
    final = stop - size
    if values[-1] != final:
        values.append(final)
    return values


def write_label_svg(output: Path, detections: dict[int, dict], layout: dict) -> None:
    guide_points = " ".join(
        f'{detections[plot]["x"]},{detections[plot]["y"]}'
        for plot in SH69_NORTH_PLOT_ORDER
        if plot in detections
    )
    labels = []
    for plot, item in sorted(detections.items()):
        labels.append(
            f'<text x="{item["x"]}" y="{item["y"]}" text-anchor="middle" '
            f'dominant-baseline="central">{plot}</text>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{layout["width"]}" height="{layout["height"]}" viewBox="0 0 {layout["width"]} {layout["height"]}">
  <style>
    text {{ font: 800 24px Arial, sans-serif; fill: #101713; stroke: rgba(255,255,255,.94); stroke-width: 5px; paint-order: stroke fill; }}
    .road-halo {{ fill: none; stroke: rgba(255,255,255,.88); stroke-width: 22px; stroke-linecap: round; stroke-linejoin: round; }}
    .road-guide {{ fill: none; stroke: #d65c2e; stroke-width: 10px; stroke-dasharray: 30 20; stroke-linecap: round; stroke-linejoin: round; opacity: .82; }}
  </style>
  <g aria-label="Approximate SH69 north-side plot-order guide">
    <title>Approximate SH69 north-side plot sequence; dashed spans across missing source coverage are inferred</title>
    <polyline class="road-halo" points="{guide_points}" />
    <polyline class="road-guide" points="{guide_points}" />
  </g>
  <g aria-label="OCR-verified plot number labels">{"".join(labels)}</g>
</svg>\n'''
    output.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output", type=Path, default=ASSETS / "plot-index.json")
    parser.add_argument("--minimum-confidence", type=float, default=MIN_CONFIDENCE)
    parser.add_argument("--label-svg", type=Path, default=ASSETS / "plot-labels.svg")
    parser.add_argument("--tile-size", type=int, default=TILE_SIZE)
    parser.add_argument("--tile-overlap", type=int, default=TILE_OVERLAP)
    parser.add_argument("--tile-scale", type=int, default=TILE_SCALE)
    parser.add_argument("--sheets", type=int, nargs="+", choices=range(1, 5), default=[1, 2, 3, 4])
    parser.add_argument("--merge-existing", action="store_true")
    parser.add_argument(
        "--audit-existing",
        action="store_true",
        help="Remove visually rejected readings from the existing index and rebuild its SVG",
    )
    args = parser.parse_args()

    layout = json.loads((ASSETS / "chandhaus-combined-layout.json").read_text())
    if args.audit_existing:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        detections = {
            int(item["plot"]): item
            for item in existing.get("plots", [])
            if int(item["plot"]) not in REJECTED_OCR
        }
        # Preserve source-label positions when a sheet placement is refined.
        # The current layout describes the coordinates in the existing index;
        # PLACEMENTS describes the coordinates being rebuilt.
        old_placements = layout.get("placements", {})
        for item in detections.values():
            sheet = int(item["sheet"])
            previous = old_placements.get(str(sheet))
            if not previous:
                continue
            item["x"] = round(item["x"] + (PLACEMENTS[sheet][0] - previous["x"]) * UPSCALE, 1)
            item["y"] = round(item["y"] + (PLACEMENTS[sheet][1] - previous["y"]) * UPSCALE, 1)
        for plot, item in AUDITED.items():
            x, y = combined_point(item["sheet"], item["sourceX"], item["sourceY"], layout)
            detections[plot] = {
                "plot": plot,
                "sheet": item["sheet"],
                "x": round(x, 1),
                "y": round(y, 1),
                "confidence": 1.0,
                "source": "audited",
            }
        existing["count"] = len(detections)
        existing["imageWidth"] = layout["width"]
        existing["imageHeight"] = layout["height"]
        existing["plots"] = sorted(detections.values(), key=lambda item: item["plot"])
        existing["audit"] = "Tiled OCR plus full visual label audit; false readings removed"
        existing["alignmentGuides"] = [{
            "id": "sh69-north-plot-order",
            "road": "SH 69",
            "side": "north",
            "plotOrder": list(SH69_NORTH_PLOT_ORDER),
            "basis": "user-supplied order with each printed label visually checked",
            "geometry": "approximate polyline through label centres; unsurveyed gaps are inferred",
        }]
        args.output.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        write_label_svg(args.label_svg, detections, layout)
        print(f"{args.output}: {len(detections)} audited plot labels")
        print(f"{args.label_svg}: scalable clear-number overlay")
        return

    if args.model_dir is None:
        parser.error("--model-dir is required unless --audit-existing is used")

    try:
        import easyocr
    except ImportError as error:
        raise SystemExit("EasyOCR is required only to rebuild this index") from error

    reader = easyocr.Reader(
        ["en"],
        gpu=False,
        model_storage_directory=str(args.model_dir),
        download_enabled=False,
        verbose=False,
    )
    detections: dict[int, dict] = {}
    if args.merge_existing and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        detections = {int(item["plot"]): item for item in existing.get("plots", [])}

    with tempfile.TemporaryDirectory(prefix="chandhaus-plot-ocr-") as temp_name:
        temp = Path(temp_name)
        for sheet in args.sheets:
            layer = extract_layer(ORIGINALS / f"BhuNaksha_Chandhos{sheet}.pdf", temp, sheet)
            left, top, right, bottom = alpha_bbox(layer)
            white = Image.new("RGB", layer.size, "white")
            white.paste(layer, mask=layer.getchannel("A"))
            low, high = RANGES[sheet]
            x_starts = tile_starts(left, right, args.tile_size, args.tile_overlap)
            y_starts = tile_starts(top, bottom, args.tile_size, args.tile_overlap)
            print(f"Sheet {sheet}: {len(x_starts) * len(y_starts)} OCR tiles", flush=True)
            for source_top in y_starts:
                for source_left in x_starts:
                    source_right = min(source_left + args.tile_size, right)
                    source_bottom = min(source_top + args.tile_size, bottom)
                    crop = white.crop((source_left, source_top, source_right, source_bottom)).resize(
                        ((source_right - source_left) * args.tile_scale,
                         (source_bottom - source_top) * args.tile_scale),
                        Image.LANCZOS,
                    )
                    results = reader.readtext(
                        np.asarray(crop),
                        detail=1,
                        paragraph=False,
                        allowlist="0123456789",
                        canvas_size=2560,
                        mag_ratio=1.0,
                        text_threshold=0.40,
                        low_text=0.20,
                        link_threshold=0.22,
                        min_size=4,
                        batch_size=16,
                    )
                    for box, text, confidence in results:
                        if not text.isdigit() or len(text) > 4 or confidence < args.minimum_confidence:
                            continue
                        plot = int(text)
                        if not low <= plot <= high:
                            continue
                        source_x = sum(point[0] for point in box) / 4 / args.tile_scale + source_left
                        source_y = sum(point[1] for point in box) / 4 / args.tile_scale + source_top
                        x, y = combined_point(sheet, source_x, source_y, layout)
                        candidate = {
                            "plot": plot,
                            "sheet": sheet,
                            "x": round(x, 1),
                            "y": round(y, 1),
                            "confidence": round(float(confidence), 3),
                            "source": "tiled-ocr",
                        }
                        if plot not in detections or confidence > detections[plot]["confidence"]:
                            detections[plot] = candidate

    for plot, item in AUDITED.items():
        x, y = combined_point(item["sheet"], item["sourceX"], item["sourceY"], layout)
        detections[plot] = {
            "plot": plot,
            "sheet": item["sheet"],
            "x": round(x, 1),
            "y": round(y, 1),
            "confidence": 1.0,
            "source": "audited",
        }

    for plot in REJECTED_OCR:
        if detections.get(plot, {}).get("source") != "audited":
            detections.pop(plot, None)

    payload = {
        "method": "high-confidence EasyOCR plus audited corrections",
        "minimumConfidence": args.minimum_confidence,
        "imageWidth": layout["width"],
        "imageHeight": layout["height"],
        "count": len(detections),
        "plots": sorted(detections.values(), key=lambda item: item["plot"]),
        "alignmentGuides": [{
            "id": "sh69-north-plot-order",
            "road": "SH 69",
            "side": "north",
            "plotOrder": list(SH69_NORTH_PLOT_ORDER),
            "basis": "user-supplied order with each printed label visually checked",
            "geometry": "approximate polyline through label centres; unsurveyed gaps are inferred",
        }],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_label_svg(args.label_svg, detections, layout)
    try:
        output_name = args.output.relative_to(ROOT)
    except ValueError:
        output_name = args.output
    print(f"{output_name}: {len(detections)} indexed plot labels")
    print(f"{args.label_svg}: scalable clear-number overlay")


if __name__ == "__main__":
    main()
