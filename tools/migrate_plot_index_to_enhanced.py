#!/usr/bin/env python3
"""Move verified plot-label coordinates from the former mosaic to the aligned master."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
INDEX = ASSETS / "plot-index.json"

# Affine maps from the previous 7818x6249 Overall image to the enhanced master.
# They are sheet-specific because the supplied aligned PDF proportionally
# resized Sheets 02-04.  The constants come from multiple matching labels and
# were then verified by normalized parcel-line correlation.
TRANSFORMS = {
    1: (0.6666666667, 1046.0, 0.6666666667, 143.3333333),
    2: (0.6185454344, 1186.222787, 0.6188889221, 307.092705),
    3: (0.9215500829, -1266.95513, 0.9216416545, -831.746129),
    4: (1.0684580458, -1682.651686, 1.0674686056, -1504.016982),
}


def write_label_svg(output: Path, plots: list[dict], width: int, height: int) -> None:
    labels = "".join(
        f'<text x="{item["x"]}" y="{item["y"]}" text-anchor="middle" '
        f'dominant-baseline="central">{item["plot"]}</text>'
        for item in sorted(plots, key=lambda item: item["plot"])
    )
    output.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>text {{ font: 800 18px Arial, sans-serif; fill: #101713; stroke: rgba(255,255,255,.94); stroke-width: 4px; paint-order: stroke fill; }}</style>
  <g aria-label="Verified digital plot number labels">{labels}</g>
</svg>\n''',
        encoding="utf-8",
    )


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    if data.get("imageWidth") == 6328 and data.get("imageHeight") == 4954:
        print("Plot index is already in enhanced-master coordinates")
        return
    if data.get("imageWidth") != 7818 or data.get("imageHeight") != 6249:
        raise SystemExit("Refusing to migrate an index with an unknown coordinate system")
    for item in data["plots"]:
        ax, bx, ay, by = TRANSFORMS[int(item["sheet"])]
        item["x"] = round(ax * float(item["x"]) + bx, 1)
        item["y"] = round(ay * float(item["y"]) + by, 1)
        item["source"] = f'enhanced-{item.get("source", "verified")}'
    data.update({
        "imageWidth": 6328,
        "imageHeight": 4954,
        "method": "Verified legacy labels registered onto the user-supplied aligned enhanced master",
        "registration": "Sheet-specific proportional affine transfer, parcel-line correlation verified",
    })
    INDEX.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_label_svg(ASSETS / "plot-labels.svg", data["plots"], 6328, 4954)
    print(f'Migrated {len(data["plots"])} verified plot labels to the enhanced master')


if __name__ == "__main__":
    main()
