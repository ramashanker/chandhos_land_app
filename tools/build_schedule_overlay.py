#!/usr/bin/env python3
"""Build a conservative coloured overlay from Final_Schedule.csv.

Only plots with a verified label in plot-index.json are filled.  The printed
cadastral lines are treated as barriers, so this never guesses a parcel for an
unindexed plot.  Repeated CSV rows for the same plot are aggregated first.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs" / "Final_Schedule.csv"
INDEX_PATH = ROOT / "app" / "assets" / "plot-index.json"
MAP_PATH = ROOT / "app" / "assets" / "BhuNaksha_Chandhos_Combined.png"
BOUNDARY_PATH = ROOT / "app" / "assets" / "BhuNaksha_Chandhos_Combined_Boundary.png"
OVERLAY_PATH = ROOT / "app" / "assets" / "Final_Schedule_Overlay.png"
DATA_PATH = ROOT / "app" / "assets" / "final-schedule-map.json"

GREEN = np.array([23, 143, 79], dtype=np.uint8)
YELLOW = np.array([245, 183, 24], dtype=np.uint8)
OUTLINE = np.array([57, 70, 48], dtype=np.uint8)
BENCHMARK_AREAS = {50: 34.0, 54: 55.0, 77: 70.0}
PRIMARY_AREA_REFERENCE_PLOT = 77


def number(value: str) -> float:
    try:
        return float(value.strip())
    except (AttributeError, ValueError):
        return 0.0


def compact_number(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 4)


def unique_text(values: list[str]) -> str:
    return " · ".join(dict.fromkeys(value for value in values if value))


def load_schedule() -> tuple[dict[int, dict], dict]:
    records: dict[int, dict] = {}
    total = {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = {key.strip(): (value or "").strip() for key, value in raw.items()}
            if not row["Plot"].isdigit():
                total = {
                    "areaDismil": number(row["Area(Dismil)"]),
                    "scheduleA": number(row["Schedule A"]),
                    "scheduleB": number(row["Schedule B"]),
                }
                continue
            plot = int(row["Plot"])
            record = records.setdefault(plot, {
                "plot": plot,
                "areaDismil": 0.0,
                "scheduleA": 0.0,
                "scheduleB": 0.0,
                "tauji": [],
                "khata": [],
                "locations": [],
                "statuses": [],
                "sourceRows": 0,
            })
            record["areaDismil"] += number(row["Area(Dismil)"])
            record["scheduleA"] += number(row["Schedule A"])
            record["scheduleB"] += number(row["Schedule B"])
            record["tauji"].append(row["Tauji"])
            record["khata"].append(row["Khata"])
            record["locations"].append(row["Location"])
            record["statuses"].append(row["Status"])
            record["sourceRows"] += 1

    for record in records.values():
        record["areaDismil"] = compact_number(record["areaDismil"])
        record["scheduleA"] = compact_number(record["scheduleA"])
        record["scheduleB"] = compact_number(record["scheduleB"])
        record["tauji"] = unique_text(record["tauji"])
        record["khata"] = unique_text(record["khata"])
        record["location"] = unique_text(record.pop("locations"))
        record["status"] = unique_text(record.pop("statuses"))
        a, b = record["scheduleA"], record["scheduleB"]
        record["ownership"] = "joint" if a > 0 and b > 0 else "a" if a > 0 else "b"
    return records, total


def main() -> None:
    schedule, total = load_schedule()
    index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    plot_index = {int(item["plot"]): item for item in index_data["plots"]}

    boundary = np.asarray(Image.open(BOUNDARY_PATH).convert("RGBA"))
    height, width = boundary.shape[:2]
    source = Image.open(MAP_PATH).convert("RGB")
    source_scale = source.width / width
    map_image = np.asarray(source.resize((width, height), Image.LANCZOS))
    grey = np.dot(map_image[..., :3], [0.299, 0.587, 0.114])

    # Pale parcel interiors remain open; dark plot lines and labels are barriers.
    # The enhanced master has finer anti-aliased linework at this display
    # scale.  A slightly darker cutoff keeps parcel strokes closed, while the
    # lower component floor retains the smallest narrow cadastral strips.
    open_space = (boundary[..., 3] > 0) & (grey > 160)
    labels, _ = ndimage.label(open_space)
    sizes = np.bincount(labels.ravel())
    plausible = (sizes[labels] >= 20) & (sizes[labels] <= 60000)
    distance, nearest = ndimage.distance_transform_edt(~plausible, return_indices=True)

    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    mapped = 0
    benchmark_references = []
    yy, xx = np.indices((height, width))

    for plot, record in schedule.items():
        indexed = plot_index.get(plot)
        record["mapped"] = False
        if not indexed:
            continue
        x = int(round(indexed["x"] / source_scale))
        y = int(round(indexed["y"] / source_scale))
        if not (0 <= x < width and 0 <= y < height) or distance[y, x] > 15:
            continue
        near_y, near_x = int(nearest[0, y, x]), int(nearest[1, y, x])
        component = labels[near_y, near_x]
        if not component:
            continue
        mask = labels == component
        filled_mask = ndimage.binary_fill_holes(mask)
        record.update({
            "mapped": True,
            "x": round(float(indexed["x"]), 1),
            "y": round(float(indexed["y"]), 1),
            "sheet": int(indexed["sheet"]),
        })
        mapped += 1

        if plot in BENCHMARK_AREAS:
            overlay_pixel_area = int(filled_mask.sum())
            combined_pixel_area = overlay_pixel_area * source_scale * source_scale
            reference_dismil = BENCHMARK_AREAS[plot]
            square_metres = reference_dismil * 40.468564224
            benchmark_references.append({
                "plot": plot,
                "areaDismil": compact_number(reference_dismil),
                "squareMetres": round(square_metres, 6),
                "overlayPixelArea": overlay_pixel_area,
                "combinedPixelArea": round(combined_pixel_area, 3),
                "metresPerPixel": round(math.sqrt(square_metres / combined_pixel_area), 9),
            })

        if record["ownership"] == "joint":
            share = record["scheduleA"] / (record["scheduleA"] + record["scheduleB"])
            period = 14
            green_width = max(2, min(period - 2, int(round(period * share))))
            green_mask = mask & (((xx + yy) % period) < green_width)
            yellow_mask = mask & ~green_mask
            overlay[green_mask, :3] = GREEN
            overlay[yellow_mask, :3] = YELLOW
            overlay[mask, 3] = 170
        else:
            colour = GREEN if record["ownership"] == "a" else YELLOW
            overlay[mask, :3] = colour
            overlay[mask, 3] = 150

        edge = mask & ~ndimage.binary_erosion(mask)
        overlay[edge, :3] = OUTLINE
        overlay[edge, 3] = 225

    Image.fromarray(overlay, "RGBA").save(OVERLAY_PATH, optimize=True)
    benchmark_references.sort(key=lambda item: item["plot"])
    primary_reference = next(
        (item for item in benchmark_references if item["plot"] == PRIMARY_AREA_REFERENCE_PLOT),
        None,
    )
    reference_metres_per_pixel = primary_reference["metresPerPixel"] if primary_reference else 0.0
    for item in benchmark_references:
        predicted = item["combinedPixelArea"] * reference_metres_per_pixel**2 / 40.468564224
        item["referenceScaleAreaDismil"] = round(predicted, 4)
        item["differenceDismil"] = round(predicted - float(item["areaDismil"]), 4)
    benchmark = {
        "plots": [PRIMARY_AREA_REFERENCE_PLOT] if primary_reference else [],
        "referencePlot": PRIMARY_AREA_REFERENCE_PLOT,
        "references": [primary_reference] if primary_reference else [],
        "comparisonReferences": benchmark_references,
        "totalAreaDismil": compact_number(float(primary_reference["areaDismil"])) if primary_reference else 0,
        "totalSquareMetres": primary_reference["squareMetres"] if primary_reference else 0,
        "combinedPixelArea": primary_reference["combinedPixelArea"] if primary_reference else 0,
        "metresPerPixel": round(reference_metres_per_pixel, 9),
        "maximumReferenceDifferenceDismil": round(
            abs(primary_reference["differenceDismil"]) if primary_reference else 0, 4
        ),
        "method": "Area-derived isotropic scale from verified enclosed Plot 77 = 70 dismil",
    }
    output = {
        "source": "docs/Final_Schedule.csv",
        "method": "Verified plot-label seed with printed cadastral lines used as parcel barriers",
        "imageWidth": width,
        "imageHeight": height,
        "displayScale": source_scale,
        "uniquePlots": len(schedule),
        "mappedPlots": mapped,
        "unmappedPlots": len(schedule) - mapped,
        "total": {key: compact_number(value) for key, value in total.items()},
        "benchmark": benchmark,
        "plots": [schedule[key] for key in sorted(schedule)],
    }
    DATA_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OVERLAY_PATH.relative_to(ROOT)} ({mapped}/{len(schedule)} plots mapped)")
    print(f"Wrote {DATA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
