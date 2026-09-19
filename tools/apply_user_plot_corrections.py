#!/usr/bin/env python3
"""Apply visually checked, user-guided plot corrections to the enhanced master."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from migrate_plot_index_to_enhanced import write_label_svg


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
INDEX = ASSETS / "plot-index.json"
LAYOUT = ASSETS / "chandhaus-combined-layout.json"
COORDINATE_OVERRIDES = ASSETS / "plot-coordinate-overrides.json"
REFERENCE_TRANSFORMS = {
    1: {"scale": 1.07, "x": 1126.0, "y": 250.0},
    2: {"scale": 1.07, "x": 3214.0, "y": 382.0},
    3: {"scale": 1.07, "x": 2983.0, "y": 2352.0},
    4: {"scale": 1.07, "x": 380.0, "y": 2396.0},
    5: {"scale": 1.07, "x": 1120.0, "y": 4768.0},
}

# Coordinates are label/parcel centres in the aligned master. Sheets 1-4 keep
# their audited coordinate frame when the fifth southern sheet is appended.
# Sheet 01 positions were checked directly on the enhanced raster.  The
# 4206-4209 run follows the landholder's corrected left-to-right seam order.
CORRECTIONS = {
    48: (1, 2229.0, 707.0, "right of Plot 51"),
    49: (1, 2254.0, 626.0, "right of Plot 50"),
    58: (1, 2270.0, 908.0, "below Plot 57"),
    64: (1, 2255.0, 944.0, "below Plot 58"),
    74: (1, 2160.0, 694.0, "right of Plot 75"),
    76: (1, 2155.0, 641.0, "below Plot 77 and above Plot 75"),
    82: (1, 2053.0, 791.0, "below Plot 81 and right of Plot 87"),
    560: (1, 2292.0, 1990.0, "right of Plot 265 and above Plot 561"),
    616: (1, 2481.0, 1854.0, "below Plot 618; left of Plot 617"),
    617: (1, 2518.0, 1868.0, "below Plot 618; right of Plot 616"),
    618: (1, 2504.0, 1813.0, "below Plot 625"),
    624: (1, 2541.0, 1763.0, "right of Plot 623 and above Plot 625"),
    625: (1, 2541.0, 1803.0, "right of Plot 623 and below Plot 624"),
    671: (1, 2481.0, 2381.0, "leftmost in 671-672-673 run"),
    672: (1, 2515.0, 2381.0, "between Plots 671 and 673"),
    673: (1, 2555.0, 2385.0, "right of Plot 672 and below Plot 676"),
    676: (1, 2570.0, 2350.0, "above Plot 673 at the Sheet 01/04 seam"),
    5879: (4, 2290.0, 4125.0, "slightly higher in the adjacent plot right of Plot 5870"),
    5881: (4, 2230.0, 4230.0, "in the plot immediately left of Plot 5879"),
    5882: (4, 2104.0, 4218.0, "inner parcel at the centre of Plot 5870"),
    5891: (4, 2370.0, 4294.0, "immediately left of Plot 5890"),
    5892: (4, 2315.0, 4294.0, "left of Plot 5891"),
    4209: (4, 2360.0, 2460.0, "left of Plot 4208"),
    4208: (4, 2390.0, 2485.0, "between Plots 4209 and 4207"),
    4207: (4, 2420.0, 2510.0, "right of Plot 4208 and left of Plot 4206"),
    4206: (4, 2535.0, 2580.0, "right of Plot 4207"),
}

SH69_ORDER = [
    450, 446, 362, 528, 520, 573,
    4209, 4208, 4207, 4206, 4178, 4144, 2761, 2782,
]

# High-confidence labels unique to the newly supplied fifth HD sheet. Source
# coordinates are transformed by x=1120+1.07x and y=4768+1.07y.
SHEET5_VERIFIED = {
    6302: (3076.0, 5788.8),
}

# Visually confirmed against the clear original sheets after fine tiled OCR.
# Coordinates are native pixels in the corresponding HD sheet.
CLEAR_SHEET_VERIFIED = {
    250: (1, 1309.83, 1200.0, 0.85),
    457: (1, 1335.67, 1741.17, 1.0),
    675: (1, 1561.83, 1213.67, 1.0),
    2954: (3, 1189.83, 856.0, 0.76),
    3697: (3, 331.5, 1306.0, 0.96),
    6283: (5, 2800.0, 158.0, 1.0),
    6291: (5, 2540.0, 260.0, 1.0),
    6407: (5, 1518.0, 184.0, 1.0),
    6419: (5, 1322.0, 52.0, 1.0),
    6442: (5, 666.0, 112.0, 1.0),
    6447: (5, 728.0, 214.0, 1.0),
    6448: (5, 872.0, 192.0, 1.0),
    6450: (5, 968.0, 229.0, 1.0),
    6456: (5, 1130.0, 390.0, 1.0),
    6469: (5, 1010.0, 400.0, 1.0),
    6580: (5, 1518.0, 1440.0, 1.0),
}

# Landholder-verified labels on Sheet 03. Coordinates are native pixels in
# BhuNaksha_Chandhos3_HD.png so they remain attached to their parcels if the
# combined-sheet alignment is refined later. The former OCR result 3027 is the
# same parcel as 2802 and must not remain as a searchable duplicate.
SHEET3_USER_VERIFIED = {
    2619: (629.8, 315.7, "corrected from the erroneous OCR label 2614"),
    2686: (373.2, 106.4, "corrected from the erroneous OCR label 2636"),
    2685: (340.0, 213.0, "parcel directly below Plot 2686"),
    2673: (345.0, 410.0, "leftmost parcel in the 2673-2641-2643 run"),
    2641: (425.0, 445.0, "parcel immediately right of Plot 2673"),
    2643: (530.0, 450.0, "parcel immediately right of Plot 2641"),
    2769: (477.5, 535.0, "shared parcel directly below Plots 2641 and 2643"),
    2785: (495.0, 748.0, "above Plot 2783; Plot 2783 is above Plot 2782"),
    2801: (667.7, 626.7, "above Plot 2819; corrected from the erroneous OCR label 3803"),
    2802: (739.2, 537.9, "corrected from the erroneous OCR label 3027"),
    2800: (800.0, 527.0, "first parcel right of Plot 2802"),
    2803: (858.0, 575.0, "parcel below and right of Plot 2800"),
}

# Landholder-verified labels on Sheet 04, in native sheet pixels.
SHEET4_USER_VERIFIED = {
    5844: (1620.0, 1280.0, "parcel directly above Plot 5845"),
    5845: (1620.0, 1365.2, "parcel immediately left of Plot 5847"),
    5864: (1775.0, 1460.0, "parcel immediately left of Plot 5866"),
    5908: (1480.0, 2040.5, "parcel immediately left of Plot 5907"),
    5909: (1480.0, 2100.0, "below Plot 5908 and left of Plot 5907"),
    5910: (1400.0, 2100.0, "parcel directly below Plot 5912"),
    5912: (1400.0, 1935.0, "below Plot 5917, above Plot 5910, and above-left of Plot 5908"),
    5917: (1370.0, 1855.0, "parcel directly above Plot 5912"),
}

REMOVED_MISREADS = {
    2614: "Sheet 03 OCR misread corrected to Plot 2619",
    2636: "Sheet 03 OCR misread corrected to Plot 2686",
    3027: "Sheet 03 OCR misread corrected to Plot 2802",
    3803: "Sheet 03 OCR misread corrected to Plot 2801",
}


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    current_transforms = {
        int(key): value for key, value in layout["sheetTransforms"].items()
    }

    def aligned(sheet: int, x: float, y: float) -> tuple[float, float]:
        reference = REFERENCE_TRANSFORMS[sheet]
        current = current_transforms[sheet]
        local_x = (x - reference["x"]) / reference["scale"]
        local_y = (y - reference["y"]) / reference["scale"]
        return (
            round(current["x"] + local_x * current["scale"], 1),
            round(current["y"] + local_y * current["scale"], 1),
        )

    plots = {int(item["plot"]): item for item in data["plots"]}
    for plot in REMOVED_MISREADS:
        plots.pop(plot, None)
    for plot, (sheet, x, y, basis) in CORRECTIONS.items():
        x, y = aligned(sheet, x, y)
        plots[plot] = {
            "plot": plot,
            "sheet": sheet,
            "x": x,
            "y": y,
            "confidence": 1.0,
            "source": "user-guided-enhanced-audit",
            "basis": basis,
        }
    for plot, (x, y) in SHEET5_VERIFIED.items():
        x, y = aligned(5, x, y)
        plots[plot] = {
            "plot": plot,
            "sheet": 5,
            "x": x,
            "y": y,
            "confidence": 0.96,
            "source": "original-hd-sheet5-verified-ocr",
        }
    for plot, (sheet, source_x, source_y, confidence) in CLEAR_SHEET_VERIFIED.items():
        transform = current_transforms[sheet]
        plots[plot] = {
            "plot": plot,
            "sheet": sheet,
            "x": round(transform["x"] + source_x * transform["scale"], 1),
            "y": round(transform["y"] + source_y * transform["scale"], 1),
            "confidence": confidence,
            "source": "clear-original-hd-visually-verified-ocr",
        }
    sheet3_transform = current_transforms[3]
    for plot, (source_x, source_y, basis) in SHEET3_USER_VERIFIED.items():
        plots[plot] = {
            "plot": plot,
            "sheet": 3,
            "x": round(sheet3_transform["x"] + source_x * sheet3_transform["scale"], 1),
            "y": round(sheet3_transform["y"] + source_y * sheet3_transform["scale"], 1),
            "confidence": 1.0,
            "source": "user-guided-clear-sheet-audit",
            "basis": basis,
        }
    sheet4_transform = current_transforms[4]
    for plot, (source_x, source_y, basis) in SHEET4_USER_VERIFIED.items():
        plots[plot] = {
            "plot": plot,
            "sheet": 4,
            "x": round(sheet4_transform["x"] + source_x * sheet4_transform["scale"], 1),
            "y": round(sheet4_transform["y"] + source_y * sheet4_transform["scale"], 1),
            "confidence": 1.0,
            "source": "user-guided-clear-sheet-audit",
            "basis": basis,
        }
    coordinate_override_plots = []
    if COORDINATE_OVERRIDES.exists():
        overrides = json.loads(COORDINATE_OVERRIDES.read_text(encoding="utf-8"))
        for plot_text, override in overrides.get("plots", {}).items():
            plot = int(plot_text)
            plots[plot] = {
                "plot": plot,
                "sheet": int(override["sheet"]),
                "x": round(float(override["x"]), 1),
                "y": round(float(override["y"]), 1),
                "confidence": 1.0,
                "source": "in-app-coordinate-editor",
                "basis": override.get("basis", "Saved with the local plot coordinate editor"),
            }
            coordinate_override_plots.append(plot)
    data["plots"] = sorted(plots.values(), key=lambda item: int(item["plot"]))
    data["count"] = len(data["plots"])
    with Image.open(ASSETS / "BhuNaksha_Chandhos_Combined.png") as master:
        data["imageWidth"], data["imageHeight"] = master.size
    data["userCorrections"] = {
        "plotCount": len(CORRECTIONS) + len(SHEET3_USER_VERIFIED) + len(SHEET4_USER_VERIFIED),
        "plots": sorted(set(CORRECTIONS) | set(SHEET3_USER_VERIFIED) | set(SHEET4_USER_VERIFIED)),
        "basis": "Landholder topology checked against enhanced parcel linework",
        "removedMisreads": {str(plot): reason for plot, reason in REMOVED_MISREADS.items()},
        "coordinateEditorPlots": sorted(coordinate_override_plots),
    }
    data["alignmentGuides"] = [{
        "id": "sh69-north-plot-order",
        "road": "SH 69",
        "side": "north",
        "plotOrder": SH69_ORDER,
        "basis": "landholder-corrected left-to-right order",
        "geometry": "approximate polyline through verified or user-guided parcel centres",
    }]
    INDEX.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_label_svg(
        ASSETS / "plot-labels.svg",
        data["plots"],
        int(data["imageWidth"]),
        int(data["imageHeight"]),
    )
    correction_count = len(CORRECTIONS) + len(SHEET3_USER_VERIFIED) + len(SHEET4_USER_VERIFIED)
    print(f'Applied {correction_count} corrections; {len(plots)} labels indexed')


if __name__ == "__main__":
    main()
