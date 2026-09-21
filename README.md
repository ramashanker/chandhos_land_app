# Chandhaus Land App

A local, dependency-free viewer for the five Chandhos cadastral map sheets. It supports:

- a 6,328 × 6,705 high-resolution village master rebuilt from the five original HD PDFs;
- direct access to the aligned master PDF and all five original A1 detail PDFs;
- a dedicated **Download Overall PDF** button for saving the complete aligned master, with a
  searchable PDF text layer for every verified digital plot label;
- high-resolution zooming and panning;
- sheet-specific distance calibration from a known boundary length;
- automatic overall-map calibration from verified Plot 77 (70 dismil),
  with a button to restore that benchmark after a manual calibration;
- distance, parcel perimeter, and parcel area calculations;
- area conversions to dismil/decimal, acres, square metres, and square feet;
- boundary-line snapping for calibration, distance, and polygon vertices;
- detailed area results with dismil as the primary unit, acres, square metres, square feet,
  perimeter, calibration scale, aligned-point count, and every boundary side length;
- searchable, aggregated records from `docs/Final_Schedule.csv`, with a schedule overlay that is
  hidden by default: transparent green for Schedule A, yellow for Schedule B, and proportional
  green/yellow bands for joint-share plots;
- all 106 Final Schedule plot numbers searchable, with the current exact-mapping count shown live in the schedule legend and a safe source-sheet fallback for the remainder;
- hundreds of high-confidence, manually audited, or landholder-guided printed plot labels registered in the overall map and a
  safe source-sheet fallback for other plots;
- a default-on, scalable **Clear numbers** layer that keeps indexed plot labels sharp while zooming;
- click-to-identify on the overall naksha, showing the nearest verified printed plot number and source sheet without changing the current zoom;
- a persistent **Plot coordinate editor** for adding a digital plot number, placing it by clicking the map,
  editing X/Y directly, or nudging it in 1, 5, 10, or 25-pixel steps;
- an explicitly dashed, approximate SH69 north-side alignment guide through the verified plot order
  450, 446, 362, 528, 520, 573, 4209, 4208, 4207, 4206, 4178, 4144, 2761, and 2782;
- split-screen geographic context using OpenStreetMap, with a Google Maps shortcut;
- linked zoom between the naksha and geographic map, including matched ground scale after calibration;
- a default Plot 77 scale-locked transparent cadastral overlay on satellite imagery, anchored near the
  SH69/Punpun feature junction, plus an alternate road/river feature-fit mode using nine plot/GPS controls;
- move, rotation, opacity, and reset controls in scale-locked mode; feature-fit mode additionally allows
  manual overlay sizing;
- separate saved overlay placement for Overall and Sheets 1–5, with precise up/down/left/right controls (10 metres per click,
  or 50 metres with Shift-click), drag adjustment, automatic local saving, and an explicit Save position button;
- locally saved calibration and measurement overlays.

The Overall view uses all five `docs/original/Chandhos_Paliganj_Naksha_*_HD.pdf` files as its source
of truth. All pieces use one proportional scale: Sheets 01–04 were registered against matching
parcel and road linework, and Sheet 05 was tied to the shared southern seam controls. The visible `+`
and `−` controls and the mouse wheel zoom around the viewport centre or mouse cursor respectively.
Clicking the naksha, switching between Naksha/Split views, double-clicking, and resizing do not reset
the current zoom.

## Run locally

From the repository root, run:

```bash
python3 run_app.py
```

The app opens automatically at:

```text
http://localhost:8000/app/
```

No package installation or internet connection is required.

The cadastral viewer and measurements work offline. The side-by-side geographic map needs an
internet connection to load OpenStreetMap tiles.

## Share as one HTML file

`Chandhaus_Naksha_Desk_Standalone.html` is a self-contained version of the app. Send that one file
to a reviewer, who can download it and open it directly in a current Chrome, Edge, or Firefox
browser. It embeds the map sheets, overlays, plot/schedule data, and source PDFs. Only the optional
satellite/street/topographic background tiles and Google Maps shortcut require internet access.

The standalone coordinate editor saves changes only in that reviewer's browser; it cannot rewrite
the HTML file. Use the normal `python3 run_app.py` version when coordinate edits must be written back
to the project.

Rebuild the standalone file after changing app code or assets:

```bash
python3 tools/build_standalone_html.py
```

The generated one-page source is available at
`docs/enhanced/Chandhaus_Cadastral_Map_Original_Aligned.pdf`. The exact puzzle translations are
solved from the complementary alpha silhouettes in `sheet01.png` through `sheet05.png`, then applied
to the full-resolution PDF rasters at one common scale. To rebuild the master, all five detail
assets, boundaries, geographic overlay, and the PDF from the originals, run
`python3 tools/build_original_aligned_master.py`.

The optional `tools/ocr_enhanced_naksha.py` audit helper runs tiled Tesseract passes against an
enhanced raster and records numeric candidates for review; OCR is not needed to run the web app.
`tools/build_plot_index.py` remains the legacy-original-sheet index builder, and its output must be
passed through `tools/migrate_plot_index_to_enhanced.py` before use with the aligned master.
Low-confidence or visually false readings are excluded so an uncertain number does not point to an
unrelated parcel. The enhanced raster labels remain visible for numbers OCR cannot verify.
The five individual app sheets are generated as lossless enhanced PNGs rather than JPEGs, preserving
thin digit strokes for zooming and progressive one-by-one transcription.

`tools/build_georeference.py` writes two auditable EPSG:3857 transforms. The default **Scale locked**
transform preserves the Plot 77 calibration of 0.923431839 ground metres per Naksha pixel and anchors
the map near the shared SH69/Punpun feature junction. The alternate **Feature fit** transform uses
nine plot/GPS controls and permits affine scale/skew to improve visual road and river coincidence.
Plot 3670 remains excluded because its printed label could not be identified unambiguously. The
source evidence is internally inconsistent—the scale-locked GPS residual is much larger than the
feature-fit residual—so neither transform is represented as surveyed or legally authoritative.

`tools/build_schedule_overlay.py` reads `docs/Final_Schedule.csv`, aggregates repeated plot rows,
and rebuilds `app/assets/Final_Schedule_Overlay.png` plus its browser data. It colours only plots
whose printed labels have verified index coordinates; unindexed plots remain searchable by their
source sheet and are not given a guessed boundary. Run it after editing the final schedule:

```bash
python3 tools/build_schedule_overlay.py
```

If port 8000 is already in use, choose another one with `python3 run_app.py --port 8080`.

## Editing or adding a plot coordinate

Use the **Plot coordinate editor** in the right panel while the app is running through
`python3 run_app.py`:

1. Enter a plot number and select **Load / add**. Clicking an indexed plot on the overall map also
   loads it into the editor.
2. Select **Place by clicking map** and click inside the correct parcel, or change X/Y directly.
3. Use the arrow pad for precise adjustment and select a 1, 5, 10, or 25-pixel movement step.
4. Select **Save position**. The digital-number layer and exact plot search update immediately.

Saving also rebuilds and reloads the Final Schedule overlay. If the plot exists in
`docs/Final_Schedule.csv` and the saved point is inside a closed parcel, its green/yellow schedule
colour appears immediately. If the point is too close to linework or outside a closed parcel, the
editor reports that it needs to be moved farther inside and saved again.
The scale-locked georeference is also rebuilt so changes to Plot 77 or a GPS-control plot cannot
leave the geographic overlay using stale scale/alignment data.

Persistent edits are stored separately in `app/assets/plot-coordinate-overrides.json`. Normal map
rebuilds apply this file last, so editor changes are not overwritten by OCR or audited defaults.

## Measuring a parcel

The overall village map starts with the verified **Plot 77 · 70 dismil** area benchmark.
On the puzzle-aligned original-HD mosaic its enclosed map area is 3,322.05 combined-image square
pixels, producing an isotropic scale of 0.923431839 metres per source pixel. Select
**Use Plot 77 · 70 dismil scale** at any time to restore it.
Because this is an area-derived cadastral-map scale, resulting distances and areas are planning
estimates rather than survey measurements.

1. On the overall map, use the Plot 77 benchmark; for an individual sheet, zoom to a boundary whose
   real length is known.
2. For individual sheets, choose **Calibrate**, click both endpoints, and enter the known length.
3. Choose **Distance** to measure a line, or **Area** to click around a parcel.
4. Keep **Boundary snap** enabled so each click aligns to a nearby printed line. Snapped points are
   shown in yellow with a green outline. Select **Free points** only when a boundary is unclear.
5. For an area, click **Finish area** after adding at least three corners, or click close to the
   first point to close the polygon automatically.

Area conversion uses `1 acre = 100 dismil`, `1 dismil = 435.6 square feet`, and
`1 dismil = 40.468564224 square metres`.

Measurements are derived from the user-supplied calibration and are intended for understanding
and planning. They are not a substitute for official survey measurements or legal demarcation.
The overall geographic view is centred from the fitted plot/GPS controls. Individual sheet centres
remain approximate derivatives of the stitched layout.
The satellite cadastral overlay is extracted from the combined naksha and is intentionally
adjustable because the source PDFs do not contain surveyed georeferencing control points.
Plot numbers are used to choose and highlight the correct source-sheet region. The PDFs contain no
text layer or parcel coordinates, so the highlighted satellite reference and sheet boundary are not
an exact legal parcel location.
