#!/usr/bin/env python3
"""Start the Chandhaus Naksha Desk and open it in the default browser."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPOSITORY = Path(__file__).resolve().parent
ASSETS = REPOSITORY / "app" / "assets"
PLOT_INDEX = ASSETS / "plot-index.json"
PLOT_LABELS = ASSETS / "plot-labels.svg"
PLOT_OVERRIDES = ASSETS / "plot-coordinate-overrides.json"
SCHEDULE_BUILDER = REPOSITORY / "tools" / "build_schedule_overlay.py"
SCHEDULE_DATA = ASSETS / "final-schedule-map.json"
GEOREFERENCE_BUILDER = REPOSITORY / "tools" / "build_georeference.py"
GEOREFERENCE_DATA = ASSETS / "naksha-georeference.json"
WRITE_LOCK = threading.Lock()


def atomic_json_write(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_plot_labels(data: dict) -> None:
    labels = "".join(
        f'<text x="{item["x"]}" y="{item["y"]}" text-anchor="middle" '
        f'dominant-baseline="central">{item["plot"]}</text>'
        for item in sorted(data["plots"], key=lambda item: int(item["plot"]))
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{data["imageWidth"]}" height="{data["imageHeight"]}" viewBox="0 0 {data["imageWidth"]} {data["imageHeight"]}">
  <style>text {{ font: 800 18px Arial, sans-serif; fill: #101713; stroke: rgba(255,255,255,.94); stroke-width: 4px; paint-order: stroke fill; }}</style>
  <g aria-label="Verified digital plot number labels">{labels}</g>
</svg>
'''
    temporary = PLOT_LABELS.with_suffix(".svg.tmp")
    temporary.write_text(svg, encoding="utf-8")
    os.replace(temporary, PLOT_LABELS)


def rebuild_schedule_overlay(plot: int) -> dict:
    try:
        completed = subprocess.run(
            [sys.executable, str(SCHEDULE_BUILDER)],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"updated": False, "error": str(error)}
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Schedule rebuild failed"
        return {"updated": False, "error": message[-500:]}

    try:
        schedule = json.loads(SCHEDULE_DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"updated": False, "error": f"Schedule data unavailable after rebuild: {error}"}
    record = next((item for item in schedule.get("plots", []) if int(item["plot"]) == plot), None)
    return {
        "updated": True,
        "inSchedule": record is not None,
        "mapped": bool(record and record.get("mapped")),
        "mappedPlots": int(schedule.get("mappedPlots", 0)),
        "uniquePlots": int(schedule.get("uniquePlots", 0)),
    }


def rebuild_georeference() -> dict:
    try:
        completed = subprocess.run(
            [sys.executable, str(GEOREFERENCE_BUILDER)],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"updated": False, "error": str(error)}
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Georeference rebuild failed"
        return {"updated": False, "error": message[-500:]}
    try:
        data = json.loads(GEOREFERENCE_DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"updated": False, "error": f"Georeference unavailable after rebuild: {error}"}
    return {
        "updated": True,
        "activeMode": data.get("activeMode"),
        "nakshaMetresPerPixel": data.get("scaleLock", {}).get("groundMetresPerNakshaPixel"),
    }


def save_plot_coordinate(payload: dict) -> dict:
    try:
        plot = int(payload["plot"])
        sheet = int(payload["sheet"])
        x = round(float(payload["x"]), 1)
        y = round(float(payload["y"]), 1)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Plot, sheet, x and y must be numeric") from error

    if not 1 <= plot <= 7000:
        raise ValueError("Plot number must be between 1 and 7000")
    if not 1 <= sheet <= 5:
        raise ValueError("Sheet must be between 1 and 5")

    with WRITE_LOCK:
        index = json.loads(PLOT_INDEX.read_text(encoding="utf-8"))
        width = float(index["imageWidth"])
        height = float(index["imageHeight"])
        if not 0 <= x <= width or not 0 <= y <= height:
            raise ValueError(f"Coordinates must stay inside 0–{width:g} × 0–{height:g}")

        item = {
            "plot": plot,
            "sheet": sheet,
            "x": x,
            "y": y,
            "confidence": 1.0,
            "source": "in-app-coordinate-editor",
            "basis": "Saved with the local plot coordinate editor",
        }
        plots = {int(entry["plot"]): entry for entry in index["plots"]}
        plots[plot] = item
        index["plots"] = sorted(plots.values(), key=lambda entry: int(entry["plot"]))
        index["count"] = len(index["plots"])

        overrides = {"version": 1, "coordinateSystem": "combined-master-pixels", "plots": {}}
        if PLOT_OVERRIDES.exists():
            overrides = json.loads(PLOT_OVERRIDES.read_text(encoding="utf-8"))
        overrides.setdefault("plots", {})[str(plot)] = item

        atomic_json_write(PLOT_OVERRIDES, overrides)
        atomic_json_write(PLOT_INDEX, index)
        write_plot_labels(index)
        schedule = rebuild_schedule_overlay(plot)
        georeference = rebuild_georeference()
        return {
            "ok": True,
            "item": item,
            "count": index["count"],
            "schedule": schedule,
            "georeference": georeference,
        }


class ChandhausRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        path = urlparse(self.path).path
        if path in {
            "/app/assets/Final_Schedule_Overlay.png",
            "/app/assets/final-schedule-map.json",
            "/app/assets/plot-index.json",
            "/app/assets/plot-labels.svg",
            "/app/assets/naksha-georeference.json",
        }:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path != "/api/plot-coordinate":
            self.send_json(404, {"ok": False, "error": "Unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16384:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(200, save_plot_coordinate(payload))
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})
        except OSError as error:
            self.send_json(500, {"ok": False, "error": f"Could not save: {error}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Chandhaus map viewer")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    os.chdir(REPOSITORY)
    url = f"http://127.0.0.1:{args.port}/app/"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ChandhausRequestHandler)

    print(f"Chandhaus Naksha Desk is running at {url}")
    print("Press Ctrl+C to stop it.")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
