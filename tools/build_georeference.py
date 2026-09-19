#!/usr/bin/env python3
"""Fit the overall naksha to user-supplied GPS plot controls.

The fit is deliberately affine: it can translate, rotate, skew, and scale the
historic raster without bending individual parcel lines.  GPS pins are
approximate, so residuals are retained in the output rather than hidden.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "app" / "assets" / "plot-index.json"
OUTPUT_PATH = ROOT / "app" / "assets" / "naksha-georeference.json"
SCHEDULE_PATH = ROOT / "app" / "assets" / "final-schedule-map.json"
EARTH_RADIUS = 6378137.0
DEFAULT_NAKSHA_METRES_PER_PIXEL = 0.923431839
# Approximate shared SH69/Punpun feature junction on the aligned master. The
# scale-locked transform preserves the prior feature fit at this anchor while
# replacing its undersized/skewed linear part with a uniform Naksha scale.
SCALE_LOCK_ANCHOR_PIXEL = (3250.0, 4920.0)

# Decimal degrees. Plot 5900 was supplied as 25°17'22.2"N 84°51'23.0"E.
CONTROL_POINTS = {
    110: (25.315378, 84.851277),
    362: (25.306473, 84.850521),
    475: (25.305933, 84.850550),
    2824: (25.297260, 84.867231),
    3670: (25.294896, 84.867512),
    3827: (25.291564, 84.864548),
    6174: (25.288316, 84.855135),
    5902: (25.289115, 84.855216),
    5900: (25.289500, 84.856388888889),
    4144: (25.300493, 84.860486),
}


def to_mercator(latitude: float, longitude: float) -> tuple[float, float]:
    limited = max(-85.05112878, min(85.05112878, latitude))
    x = EARTH_RADIUS * math.radians(longitude)
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(limited) / 2))
    return x, y


def from_mercator(x: float, y: float) -> tuple[float, float]:
    longitude = math.degrees(x / EARTH_RADIUS)
    latitude = math.degrees(2 * math.atan(math.exp(y / EARTH_RADIUS)) - math.pi / 2)
    return latitude, longitude


def main() -> None:
    source = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    index = {int(item["plot"]): item for item in source["plots"]}
    included = []
    excluded = []
    design = []
    eastings = []
    northings = []

    for plot, (latitude, longitude) in CONTROL_POINTS.items():
        item = index.get(plot)
        if not item:
            excluded.append({
                "plot": plot,
                "latitude": latitude,
                "longitude": longitude,
                "reason": "Printed label could not be identified unambiguously",
            })
            continue
        x, y = float(item["x"]), float(item["y"])
        easting, northing = to_mercator(latitude, longitude)
        design.append([x, y, 1.0])
        eastings.append(easting)
        northings.append(northing)
        included.append({
            "plot": plot,
            "sheet": int(item["sheet"]),
            "pixelX": x,
            "pixelY": y,
            "latitude": latitude,
            "longitude": longitude,
        })

    matrix = np.asarray(design, dtype=float)
    feature_east_coefficients = np.linalg.lstsq(matrix, eastings, rcond=None)[0]
    feature_north_coefficients = np.linalg.lstsq(matrix, northings, rcond=None)[0]

    naksha_metres_per_pixel = DEFAULT_NAKSHA_METRES_PER_PIXEL
    if SCHEDULE_PATH.exists():
        schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
        naksha_metres_per_pixel = float(
            schedule.get("benchmark", {}).get("metresPerPixel", naksha_metres_per_pixel)
        )
    reference_latitude = sum(latitude for latitude, _ in CONTROL_POINTS.values()) / len(CONTROL_POINTS)
    mercator_metres_per_pixel = naksha_metres_per_pixel / math.cos(math.radians(reference_latitude))
    feature_linear = np.array([
        feature_east_coefficients[:2],
        feature_north_coefficients[:2],
    ])
    u, _, vt = np.linalg.svd(feature_linear)
    orientation = u @ vt
    locked_linear = mercator_metres_per_pixel * orientation
    anchor_pixel = np.asarray(SCALE_LOCK_ANCHOR_PIXEL, dtype=float)
    feature_translation = np.array([
        feature_east_coefficients[2],
        feature_north_coefficients[2],
    ])
    anchor_mercator = feature_linear @ anchor_pixel + feature_translation
    locked_translation = anchor_mercator - locked_linear @ anchor_pixel
    locked_east_coefficients = np.array([
        locked_linear[0, 0], locked_linear[0, 1], locked_translation[0]
    ])
    locked_north_coefficients = np.array([
        locked_linear[1, 0], locked_linear[1, 1], locked_translation[1]
    ])

    locked_distances = []
    feature_distances = []
    for row, item, target_east, target_north in zip(
        matrix, included, eastings, northings, strict=True
    ):
        feature_east = float(row @ feature_east_coefficients)
        feature_north = float(row @ feature_north_coefficients)
        feature_distance = math.hypot(feature_east - target_east, feature_north - target_north)
        feature_distances.append(feature_distance)
        fitted_east = float(row @ locked_east_coefficients)
        fitted_north = float(row @ locked_north_coefficients)
        east_error = fitted_east - target_east
        north_error = fitted_north - target_north
        distance = math.hypot(east_error, north_error)
        locked_distances.append(distance)
        fitted_latitude, fitted_longitude = from_mercator(fitted_east, fitted_north)
        item.update({
            "fittedLatitude": round(fitted_latitude, 8),
            "fittedLongitude": round(fitted_longitude, 8),
            "eastErrorMetres": round(east_error, 2),
            "northErrorMetres": round(north_error, 2),
            "errorMetres": round(distance, 2),
            "featureFitErrorMetres": round(feature_distance, 2),
        })

    width, height = int(source["imageWidth"]), int(source["imageHeight"])
    centre_row = np.array([width / 2, height / 2, 1.0])
    centre_latitude, centre_longitude = from_mercator(
        float(centre_row @ locked_east_coefficients),
        float(centre_row @ locked_north_coefficients),
    )
    feature_centre_latitude, feature_centre_longitude = from_mercator(
        float(centre_row @ feature_east_coefficients),
        float(centre_row @ feature_north_coefficients),
    )
    feature_transform = {
        "x": [round(float(value), 12) for value in feature_east_coefficients],
        "y": [round(float(value), 12) for value in feature_north_coefficients],
    }
    locked_transform = {
        "x": [round(float(value), 12) for value in locked_east_coefficients],
        "y": [round(float(value), 12) for value in locked_north_coefficients],
    }
    payload = {
        "version": 2,
        "method": "Plot 77 scale-locked similarity transform anchored to the prior SH69/Punpun feature fit",
        "activeMode": "scale-locked",
        "imageWidth": width,
        "imageHeight": height,
        "controlPointCount": len(included),
        "excludedControlPointCount": len(excluded),
        "rmsErrorMetres": round(math.sqrt(sum(value * value for value in locked_distances) / len(locked_distances)), 2),
        "maximumErrorMetres": round(max(locked_distances), 2),
        "featureFitRmsErrorMetres": round(math.sqrt(sum(value * value for value in feature_distances) / len(feature_distances)), 2),
        "featureFitMaximumErrorMetres": round(max(feature_distances), 2),
        "centre": {
            "latitude": round(centre_latitude, 8),
            "longitude": round(centre_longitude, 8),
        },
        "featureFitCentre": {
            "latitude": round(feature_centre_latitude, 8),
            "longitude": round(feature_centre_longitude, 8),
        },
        "webMercatorTransform": locked_transform,
        "scaleLockedTransform": locked_transform,
        "featureFitTransform": feature_transform,
        "scaleLock": {
            "referencePlot": 77,
            "referenceAreaDismil": 70,
            "groundMetresPerNakshaPixel": round(naksha_metres_per_pixel, 12),
            "webMercatorMetresPerNakshaPixel": round(mercator_metres_per_pixel, 12),
            "referenceLatitude": round(reference_latitude, 8),
            "anchorPixel": {
                "x": SCALE_LOCK_ANCHOR_PIXEL[0],
                "y": SCALE_LOCK_ANCHOR_PIXEL[1],
            },
            "anchorBasis": "Approximate SH69/Punpun feature junction retained from the road/river fit",
        },
        "controls": included,
        "excludedControls": excluded,
        "note": "Scale-locked mode preserves the Plot 77 cadastral scale but cannot perfectly match every approximate GPS, road and river control. Feature-fit mode improves visual coincidence by allowing affine scale/skew. Neither mode is surveyed legal georeferencing.",
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"{OUTPUT_PATH.relative_to(ROOT)}: {len(included)} controls, "
        f"RMS {payload['rmsErrorMetres']} m"
    )


if __name__ == "__main__":
    main()
