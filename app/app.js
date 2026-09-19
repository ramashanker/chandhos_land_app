"use strict";

const INDIVIDUAL_SHEETS = [1, 2, 3, 4, 5].map((number) => ({
  number,
  id: `sheet-${number}`,
  label: String(number).padStart(2, "0"),
  image: `assets/BhuNaksha_Chandhos${number}_HD.png`,
  boundary: `assets/BhuNaksha_Chandhos${number}_Boundary.png`,
  pdf: `../docs/original/Chandhos_Paliganj_Naksha_${number}_HD.pdf`,
  projectedReference: [
    [285424.45557, 2801924.31651],
    [285552.98542, 2801817.85209],
    [286128.58924, 2799996.24079],
    [281433.28, 2800289.91238],
    [283979.42, 2796940.18],
  ][number - 1],
  geographicReference: [
    [25.305458, 84.846672],
    [25.305509, 84.870261],
    [25.288603, 84.874097],
    [25.289504, 84.856469],
    [25.281327, 84.861041],
  ][number - 1],
}));

const SHEETS = [
  {
    number: 0,
    id: "sheet-overall",
    label: "ALL",
    title: "Overall village",
    isOverall: true,
    image: "assets/BhuNaksha_Chandhos_Combined.png",
    boundary: "assets/BhuNaksha_Chandhos_Combined_GeoOverlay.png",
    pdf: "../docs/enhanced/Chandhaus_Cadastral_Map_Original_Aligned.pdf",
    geographicReference: [25.297660, 84.859500],
  },
  ...INDIVIDUAL_SHEETS,
];

const COMBINED_SHEET_BOUNDS = {
  1: { x: 1126, y: 250, width: 2149, height: 2196 },
  2: { x: 3245, y: 400, width: 2731, height: 2089 },
  3: { x: 3215, y: 2446, width: 2731, height: 2457 },
  4: { x: 351, y: 2424, width: 2898, height: 2470 },
  5: { x: 1246, y: 4860, width: 3266, height: 1845 },
};

const UNIT_TO_METRES = { m: 1, ft: 0.3048, yd: 0.9144 };
const UNIT_LABEL = { m: "m", ft: "ft", yd: "yd" };
const STORAGE_KEY = "chandhaus-naksha-workspace-v3-gps-controls";
const WEB_MERCATOR_RADIUS = 6378137;

const elements = {
  sheetList: document.querySelector("#sheetList"),
  detailSheet: document.querySelector("#detailSheet"),
  openPdf: document.querySelector("#openPdf"),
  viewport: document.querySelector("#mapViewport"),
  world: document.querySelector("#mapWorld"),
  image: document.querySelector("#mapImage"),
  scheduleOverlay: document.querySelector("#scheduleOverlay"),
  toggleSchedule: document.querySelector("#toggleSchedule"),
  scheduleLegend: document.querySelector("#scheduleLegend"),
  scheduleCoverage: document.querySelector("#scheduleCoverage"),
  plotLabels: document.querySelector("#plotLabels"),
  togglePlotLabels: document.querySelector("#togglePlotLabels"),
  overlay: document.querySelector("#overlay"),
  loading: document.querySelector("#loading"),
  zoomValue: document.querySelector("#zoomValue"),
  cursorPosition: document.querySelector("#cursorPosition"),
  imageResolution: document.querySelector("#imageResolution"),
  syncStatus: document.querySelector("#syncStatus"),
  viewerGrid: document.querySelector("#viewerGrid"),
  modeHint: document.querySelector("#modeHint"),
  calibrationBadge: document.querySelector("#calibrationBadge"),
  usePlot54Scale: document.querySelector("#usePlot54Scale"),
  calibrationForm: document.querySelector("#calibrationForm"),
  knownLength: document.querySelector("#knownLength"),
  lengthUnit: document.querySelector("#lengthUnit"),
  emptyResults: document.querySelector("#emptyResults"),
  results: document.querySelector("#results"),
  resultType: document.querySelector("#resultType"),
  resultMain: document.querySelector("#resultMain"),
  resultGrid: document.querySelector("#resultGrid"),
  finishArea: document.querySelector("#finishArea"),
  snapToLines: document.querySelector("#snapToLines"),
  measurementDetails: document.querySelector("#measurementDetails"),
  recordSearch: document.querySelector("#recordSearch"),
  recordList: document.querySelector("#recordList"),
  recordCount: document.querySelector("#recordCount"),
  locatePlot: document.querySelector("#locatePlot"),
  plotLocatorStatus: document.querySelector("#plotLocatorStatus"),
  clickedPlotInfo: document.querySelector("#clickedPlotInfo"),
  coordinateEditorBadge: document.querySelector("#coordinateEditorBadge"),
  coordinatePlot: document.querySelector("#coordinatePlot"),
  coordinateSheet: document.querySelector("#coordinateSheet"),
  coordinateX: document.querySelector("#coordinateX"),
  coordinateY: document.querySelector("#coordinateY"),
  coordinateStep: document.querySelector("#coordinateStep"),
  coordinateLoad: document.querySelector("#coordinateLoad"),
  coordinatePick: document.querySelector("#coordinatePick"),
  coordinateUp: document.querySelector("#coordinateUp"),
  coordinateDown: document.querySelector("#coordinateDown"),
  coordinateLeft: document.querySelector("#coordinateLeft"),
  coordinateRight: document.querySelector("#coordinateRight"),
  coordinateSave: document.querySelector("#coordinateSave"),
  coordinateRevert: document.querySelector("#coordinateRevert"),
  coordinateStatus: document.querySelector("#coordinateStatus"),
  geoViewport: document.querySelector("#geoViewport"),
  geoTiles: document.querySelector("#geoTiles"),
  geoTitle: document.querySelector("#geoTitle"),
  geoCoordinates: document.querySelector("#geoCoordinates"),
  geoReferenceNote: document.querySelector("#geoReferenceNote"),
  sheetMarker: document.querySelector("#sheetMarker"),
  markerLabel: document.querySelector("#markerLabel"),
  openGoogleMap: document.querySelector("#openGoogleMap"),
  geoAttribution: document.querySelector("#geoAttribution"),
  geoScale: document.querySelector("#geoScale"),
  linkZoom: document.querySelector("#linkZoom"),
  boundaryOverlay: document.querySelector("#boundaryOverlay"),
  toggleBoundary: document.querySelector("#toggleBoundary"),
  alignmentMode: document.querySelector("#alignmentMode"),
  adjustBoundary: document.querySelector("#adjustBoundary"),
  boundarySmaller: document.querySelector("#boundarySmaller"),
  boundaryLarger: document.querySelector("#boundaryLarger"),
  boundaryOpacity: document.querySelector("#boundaryOpacity"),
  boundarySaveStatus: document.querySelector("#boundarySaveStatus"),
};

const persisted = loadPersistedState();
const app = {
  activeSheet: 0,
  mode: "pan",
  scale: 0.1,
  minScale: 0.03,
  maxScale: 5,
  panX: 0,
  panY: 0,
  imageWidth: 1,
  imageHeight: 1,
  combinedImageWidth: 6328,
  combinedImageHeight: 6705,
  dragging: false,
  pointerStart: null,
  startPan: null,
  moved: false,
  sheets: persisted.sheets || {},
  draft: [],
  lastResult: null,
  records: [],
  linkViews: true,
  syncingViews: false,
  adjustingBoundary: false,
  boundaryDragStart: null,
  geoSheetIndex: 0,
  plotFocus: null,
  plotIndex: new Map(),
  boundarySnap: true,
  scheduleVisible: false,
  scheduleData: null,
  plotLabelsVisible: true,
  georeference: null,
  coordinateEditor: {
    plot: null,
    original: null,
    picking: false,
    dirty: false,
    saving: false,
  },
};

const snapCanvas = document.createElement("canvas");
const snapContext = snapCanvas.getContext("2d", { willReadFrequently: true });

const geo = {
  lat: SHEETS[0].geographicReference[0],
  lon: SHEETS[0].geographicReference[1],
  homeLat: SHEETS[0].geographicReference[0],
  homeLon: SHEETS[0].geographicReference[1],
  zoom: 15,
  basemap: "hybrid",
  dragging: false,
  pointerStart: null,
  centerStart: null,
};

function defaultBoundary(index = app.activeSheet) {
  const sheet = SHEETS[index];
  return {
    visible: true,
    heightMetres: sheet.isOverall ? 6480 : [2082, 2120, 1698, 1970, 1471][sheet.number - 1],
    scaleFactor: 1,
    rotation: 0,
    eastOffset: 0,
    northOffset: 0,
    opacity: 0.42,
    alignmentMode: sheet.isOverall ? "scale-locked" : "manual",
    georeferenceVersion: sheet.isOverall ? 2 : null,
  };
}

function sheetState(index = app.activeSheet) {
  const id = SHEETS[index].id;
  if (!app.sheets[id]) {
    app.sheets[id] = { calibration: null, measurements: [] };
  }
  if (!app.sheets[id].boundary) {
    app.sheets[id].boundary = defaultBoundary(index);
  }
  return app.sheets[id];
}

function loadPersistedState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    const cleaned = { sheets: saved.sheets || {} };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cleaned));
    return cleaned;
  } catch {
    return {};
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ sheets: app.sheets }));
}

function renderSheetButtons() {
  elements.sheetList.innerHTML = "";
  SHEETS.forEach((sheet, index) => {
    const button = document.createElement("button");
    button.className = `sheet-button${index === app.activeSheet ? " active" : ""}`;
    button.innerHTML = sheet.isOverall
      ? "<strong>Overall</strong><span>5-sheet village mosaic</span>"
      : `<strong>Sheet ${sheet.label}</strong><span>Original HD · A1</span>`;
    button.addEventListener("click", () => selectSheet(index));
    elements.sheetList.append(button);
  });
}

function selectSheet(index) {
  app.activeSheet = index;
  app.geoSheetIndex = index;
  app.plotFocus = null;
  app.coordinateEditor.picking = false;
  elements.coordinatePick.classList.remove("active");
  elements.coordinatePick.textContent = "Place by clicking map";
  elements.clickedPlotInfo.classList.add("hidden");
  app.draft = [];
  app.lastResult = null;
  const sheet = SHEETS[index];
  elements.loading.classList.remove("hidden");
  elements.image.src = sheet.image;
  elements.image.alt = sheet.isOverall
    ? "Combined Chandhaus cadastral village map"
    : `Chandhaus cadastral map sheet ${sheet.label}`;
  elements.openPdf.href = sheet.pdf;
  elements.detailSheet.textContent = sheet.isOverall ? "Overall (1–5)" : sheet.label;
  setGeoSheet(sheet);
  renderSheetButtons();
  setMode("pan");
  updateCalibrationUI();
  renderResults();
  updateScheduleVisibility();
  updatePlotLabelsVisibility();
}

function updatePlotLabelsVisibility() {
  const visible = app.plotLabelsVisible && app.activeSheet === 0;
  elements.plotLabels.classList.toggle("hidden", !visible);
  elements.togglePlotLabels.classList.toggle("active", visible);
  elements.togglePlotLabels.setAttribute("aria-pressed", String(visible));
}

function togglePlotLabels() {
  const currentlyVisible = app.plotLabelsVisible && app.activeSheet === 0;
  app.plotLabelsVisible = !currentlyVisible;
  if (app.plotLabelsVisible && app.activeSheet !== 0) selectSheet(0);
  else updatePlotLabelsVisibility();
}

function updateScheduleVisibility() {
  const visible = app.scheduleVisible && app.activeSheet === 0;
  elements.scheduleOverlay.classList.toggle("hidden", !visible);
  elements.scheduleLegend.classList.toggle("hidden", !visible);
  elements.toggleSchedule.classList.toggle("active", visible);
  elements.toggleSchedule.setAttribute("aria-pressed", String(visible));
  elements.toggleSchedule.innerHTML = visible
    ? '<span aria-hidden="true">▧</span> Hide schedule'
    : '<span aria-hidden="true">▧</span> Display schedule';
}

function toggleSchedule() {
  const currentlyVisible = app.scheduleVisible && app.activeSheet === 0;
  app.scheduleVisible = !currentlyVisible;
  if (app.scheduleVisible && app.activeSheet !== 0) selectSheet(0);
  else updateScheduleVisibility();
}

elements.image.addEventListener("load", () => {
  app.imageWidth = elements.image.naturalWidth;
  app.imageHeight = elements.image.naturalHeight;
  elements.world.style.width = `${app.imageWidth}px`;
  elements.world.style.height = `${app.imageHeight}px`;
  elements.overlay.setAttribute("viewBox", `0 0 ${app.imageWidth} ${app.imageHeight}`);
  elements.imageResolution.textContent = `Resolution: ${app.imageWidth} × ${app.imageHeight}`;
  elements.loading.classList.add("hidden");
  requestAnimationFrame(() => app.plotFocus ? focusPlotRegion() : fitMap());
});

function focusPlotRegion() {
  if (!app.plotFocus || app.activeSheet !== 0) return;
  if (app.plotFocus.exact) {
    const rect = elements.viewport.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    app.scale = clamp(Math.min(rect.width / 900, rect.height / 700), app.minScale, app.maxScale);
    app.panX = rect.width / 2 - app.plotFocus.x * app.scale;
    app.panY = rect.height / 2 - app.plotFocus.y * app.scale;
    applyTransform();
    return;
  }
  const bounds = COMBINED_SHEET_BOUNDS[app.plotFocus.sheet];
  const rect = elements.viewport.getBoundingClientRect();
  if (!bounds || !rect.width || !rect.height) return;
  const padding = 65;
  app.scale = Math.min(
    (rect.width - padding * 2) / bounds.width,
    (rect.height - padding * 2) / bounds.height,
  );
  app.scale = clamp(app.scale, app.minScale, app.maxScale);
  app.panX = rect.width / 2 - (bounds.x + bounds.width / 2) * app.scale;
  app.panY = rect.height / 2 - (bounds.y + bounds.height / 2) * app.scale;
  applyTransform();
}

function fitMap() {
  const rect = elements.viewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const padding = 34;
  app.scale = Math.min(
    (rect.width - padding * 2) / app.imageWidth,
    (rect.height - padding * 2) / app.imageHeight,
  );
  app.minScale = Math.max(app.scale * 0.55, 0.01);
  app.panX = (rect.width - app.imageWidth * app.scale) / 2;
  app.panY = (rect.height - app.imageHeight * app.scale) / 2;
  applyTransform();
  if (app.linkViews && sheetState().calibration) syncGeoFromNaksha(1);
}

function applyTransform() {
  elements.world.style.transform = `translate(${app.panX}px, ${app.panY}px) scale(${app.scale})`;
  elements.zoomValue.textContent = `${Math.round(app.scale * 100)}%`;
  renderOverlay();
  updateLinkedScaleStatus();
}

function setNakshaScale(nextScale) {
  const rect = elements.viewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  const worldX = (centerX - app.panX) / app.scale;
  const worldY = (centerY - app.panY) / app.scale;
  app.scale = clamp(nextScale, app.minScale, app.maxScale);
  app.panX = centerX - worldX * app.scale;
  app.panY = centerY - worldY * app.scale;
  applyTransform();
}

function actualMapMetresPerPixel() {
  return 156543.03392804097 * Math.cos(geo.homeLat * Math.PI / 180) / 2 ** geo.zoom;
}

function nakshaMetresPerScreenPixel() {
  const calibration = sheetState().calibration;
  return calibration ? calibration.metresPerPixel / app.scale : null;
}

function syncGeoFromNaksha(proportionalFactor) {
  app.syncingViews = true;
  const targetMetresPerPixel = nakshaMetresPerScreenPixel();
  if (targetMetresPerPixel) {
    geo.zoom = clamp(Math.log2(
      156543.03392804097 * Math.cos(geo.homeLat * Math.PI / 180) / targetMetresPerPixel
    ), 3, 19.5);
  } else {
    geo.zoom = clamp(geo.zoom + Math.log2(proportionalFactor), 3, 19.5);
  }
  renderGeoMap();
  app.syncingViews = false;
}

function syncNakshaFromGeo(previousGeoZoom) {
  app.syncingViews = true;
  const calibration = sheetState().calibration;
  if (calibration) {
    setNakshaScale(calibration.metresPerPixel / actualMapMetresPerPixel());
  } else {
    setNakshaScale(app.scale * 2 ** (geo.zoom - previousGeoZoom));
  }
  app.syncingViews = false;
}

function updateLinkedScaleStatus() {
  if (!app.linkViews) {
    elements.syncStatus.textContent = "Independent zoom";
    return;
  }
  const metresPerPixel = nakshaMetresPerScreenPixel();
  elements.syncStatus.textContent = metresPerPixel
    ? `Matched ground scale · ${formatNumber(metresPerPixel)} m/screen px`
    : "Linked zoom · calibrate for matched ground scale";
}

function setViewMode(view) {
  elements.viewerGrid.dataset.view = view;
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  requestAnimationFrame(() => {
    if (view !== "map") applyTransform();
    if (view !== "naksha") renderGeoMap();
  });
}

function setGeoSheet(sheet) {
  app.geoSheetIndex = SHEETS.indexOf(sheet);
  const overallBoundary = sheet.isOverall ? sheetState(app.geoSheetIndex).boundary : null;
  const fittedCentre = sheet.isOverall && app.georeference
    ? overallBoundary.alignmentMode === "feature-fit"
      ? app.georeference.featureFitCentre
      : app.georeference.centre
    : null;
  const [lat, lon] = fittedCentre
    ? [fittedCentre.latitude, fittedCentre.longitude]
    : sheet.geographicReference;
  geo.lat = geo.homeLat = lat;
  geo.lon = geo.homeLon = lon;
  geo.zoom = sheet.isOverall ? 14 : 15;
  elements.geoTitle.textContent = sheet.isOverall ? "Chandhaus village area" : `Sheet ${sheet.label} area`;
  elements.markerLabel.textContent = sheet.isOverall ? "Village reference" : `Sheet ${sheet.label} reference`;
  elements.geoCoordinates.textContent = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
  elements.geoReferenceNote.textContent = sheet.isOverall
    ? app.georeference
      ? sheetState(app.geoSheetIndex).boundary.alignmentMode === "feature-fit"
        ? `Road/river feature fit · GPS RMS ${Math.round(app.georeference.featureFitRmsErrorMetres)} m`
        : `Plot 77 scale locked · ${formatDetailed(app.georeference.scaleLock.groundMetresPerNakshaPixel, 6)} m/Naksha px`
      : "Mapped Chandhaus locality centre (GeoNames / OSM)"
    : `Approximate Sheet ${sheet.label} centre derived from the stitched village map`;
  elements.openGoogleMap.href = `https://www.google.com/maps?q=${lat},${lon}&z=16`;
  elements.boundaryOverlay.src = sheet.boundary;
  app.adjustingBoundary = false;
  updateBoundaryControls();
  requestAnimationFrame(renderGeoMap);
}

function latLonToWorld(lat, lon, zoom) {
  const size = 256 * 2 ** zoom;
  const limitedLat = clamp(lat, -85.05112878, 85.05112878);
  const sin = Math.sin(limitedLat * Math.PI / 180);
  return {
    x: (lon + 180) / 360 * size,
    y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size,
  };
}

function worldToLatLon(x, y, zoom) {
  const size = 256 * 2 ** zoom;
  const lon = x / size * 360 - 180;
  const n = Math.PI - 2 * Math.PI * y / size;
  const lat = 180 / Math.PI * Math.atan(Math.sinh(n));
  return { lat, lon };
}

function latLonToMercatorMetres(lat, lon) {
  const limitedLat = clamp(lat, -85.05112878, 85.05112878);
  return {
    x: WEB_MERCATOR_RADIUS * lon * Math.PI / 180,
    y: WEB_MERCATOR_RADIUS * Math.log(Math.tan(Math.PI / 4 + limitedLat * Math.PI / 360)),
  };
}

function renderGeoMap() {
  const rect = elements.geoViewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const tileZoom = Math.floor(geo.zoom);
  const fractionalScale = 2 ** (geo.zoom - tileZoom);
  const renderedTileSize = 256 * fractionalScale;
  const centerBase = latLonToWorld(geo.lat, geo.lon, tileZoom);
  const referenceBase = latLonToWorld(geo.homeLat, geo.homeLon, tileZoom);
  const center = { x: centerBase.x * fractionalScale, y: centerBase.y * fractionalScale };
  const reference = { x: referenceBase.x * fractionalScale, y: referenceBase.y * fractionalScale };
  const left = center.x - rect.width / 2;
  const top = center.y - rect.height / 2;
  const minX = Math.floor(left / renderedTileSize);
  const maxX = Math.floor((left + rect.width) / renderedTileSize);
  const minY = Math.floor(top / renderedTileSize);
  const maxY = Math.floor((top + rect.height) / renderedTileSize);
  const tileCount = 2 ** tileZoom;
  const fragment = document.createDocumentFragment();

  for (let tileY = minY; tileY <= maxY; tileY += 1) {
    if (tileY < 0 || tileY >= tileCount) continue;
    for (let tileX = minX; tileX <= maxX; tileX += 1) {
      const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
      const appendTile = (source, extraClass = "") => {
        const image = document.createElement("img");
        image.className = `geo-tile ${extraClass}`.trim();
        image.alt = "";
        image.draggable = false;
        image.src = source;
        image.style.width = `${renderedTileSize + 0.5}px`;
        image.style.height = `${renderedTileSize + 0.5}px`;
        image.style.left = `${tileX * renderedTileSize - left}px`;
        image.style.top = `${tileY * renderedTileSize - top}px`;
        fragment.append(image);
      };
      if (geo.basemap === "streets") {
        appendTile(`https://tile.openstreetmap.org/${tileZoom}/${wrappedX}/${tileY}.png`);
      } else if (geo.basemap === "topo") {
        appendTile(`https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/${tileZoom}/${tileY}/${wrappedX}`);
      } else {
        appendTile(`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${tileZoom}/${tileY}/${wrappedX}`);
        appendTile(
          `https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/${tileZoom}/${tileY}/${wrappedX}`,
          "geo-reference-tile",
        );
      }
    }
  }
  elements.geoTiles.replaceChildren(fragment);
  elements.sheetMarker.style.left = `${reference.x - left}px`;
  elements.sheetMarker.style.top = `${reference.y - top}px`;
  renderBoundaryOverlay(reference.x - left, reference.y - top);
  elements.geoAttribution.innerHTML = geo.basemap === "streets"
    ? '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
    : geo.basemap === "topo"
      ? "Tiles © Esri — World Topographic Map"
      : "Imagery and reference labels © Esri, Maxar, Earthstar Geographics, GIS User Community";
  elements.geoScale.textContent = `Geographic zoom ${geo.zoom.toFixed(1)} · ${formatNumber(actualMapMetresPerPixel())} m/px`;
  updateLinkedScaleStatus();
}

function renderBoundaryOverlay(referenceX, referenceY) {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  const image = elements.boundaryOverlay;
  if (!boundary.visible || !image.naturalWidth || !image.naturalHeight) {
    image.classList.add("hidden");
    return;
  }
  image.classList.remove("hidden");
  if (SHEETS[app.geoSheetIndex].isOverall && app.georeference) {
    renderGeoreferencedBoundary(boundary, image);
    return;
  }
  const metresPerPixel = actualMapMetresPerPixel();
  const height = boundary.heightMetres / metresPerPixel;
  const width = height * image.naturalWidth / image.naturalHeight;
  image.style.width = `${width}px`;
  image.style.height = `${height}px`;
  image.style.left = `${referenceX + boundary.eastOffset / metresPerPixel}px`;
  image.style.top = `${referenceY - boundary.northOffset / metresPerPixel}px`;
  image.style.opacity = String(boundary.opacity);
  image.style.transformOrigin = "center";
  image.style.transform = `translate(-50%, -50%) rotate(${boundary.rotation}deg)`;
}

function renderGeoreferencedBoundary(boundary, image) {
  const rect = elements.geoViewport.getBoundingClientRect();
  const transform = boundary.alignmentMode === "feature-fit"
    ? app.georeference.featureFitTransform
    : app.georeference.scaleLockedTransform || app.georeference.webMercatorTransform;
  const centre = latLonToMercatorMetres(geo.lat, geo.lon);
  const pixelsPerMetre = 256 * 2 ** geo.zoom / (2 * Math.PI * WEB_MERCATOR_RADIUS);
  const sourceXScale = app.georeference.imageWidth / image.naturalWidth;
  const sourceYScale = app.georeference.imageHeight / image.naturalHeight;
  const base = {
    a: pixelsPerMetre * transform.x[0] * sourceXScale,
    b: -pixelsPerMetre * transform.y[0] * sourceXScale,
    c: pixelsPerMetre * transform.x[1] * sourceYScale,
    d: -pixelsPerMetre * transform.y[1] * sourceYScale,
    e: rect.width / 2 + pixelsPerMetre * (transform.x[2] - centre.x),
    f: rect.height / 2 - pixelsPerMetre * (transform.y[2] - centre.y),
  };
  const centreX = image.naturalWidth / 2;
  const centreY = image.naturalHeight / 2;
  const mappedCentreX = base.a * centreX + base.c * centreY + base.e;
  const mappedCentreY = base.b * centreX + base.d * centreY + base.f;
  const radians = (boundary.rotation || 0) * Math.PI / 180;
  const scale = boundary.scaleFactor || 1;
  const cosine = Math.cos(radians) * scale;
  const sine = Math.sin(radians) * scale;
  const a = cosine * base.a - sine * base.b;
  const b = sine * base.a + cosine * base.b;
  const c = cosine * base.c - sine * base.d;
  const d = sine * base.c + cosine * base.d;
  const e = mappedCentreX + boundary.eastOffset / actualMapMetresPerPixel() - a * centreX - c * centreY;
  const f = mappedCentreY - boundary.northOffset / actualMapMetresPerPixel() - b * centreX - d * centreY;
  image.style.width = `${image.naturalWidth}px`;
  image.style.height = `${image.naturalHeight}px`;
  image.style.left = "0";
  image.style.top = "0";
  image.style.opacity = String(boundary.opacity);
  image.style.transformOrigin = "0 0";
  image.style.transform = `matrix(${a}, ${b}, ${c}, ${d}, ${e}, ${f})`;
}

function refreshBoundaryOverlay() {
  const rect = elements.geoViewport.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const center = latLonToWorld(geo.lat, geo.lon, geo.zoom);
  const reference = latLonToWorld(geo.homeLat, geo.homeLon, geo.zoom);
  renderBoundaryOverlay(
    reference.x - center.x + rect.width / 2,
    reference.y - center.y + rect.height / 2,
  );
}

function updateBoundaryControls() {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  const isOverall = SHEETS[app.geoSheetIndex].isOverall;
  const scaleLocked = isOverall && boundary.alignmentMode !== "feature-fit";
  elements.toggleBoundary.classList.toggle("active", boundary.visible);
  elements.toggleBoundary.textContent = boundary.visible ? "Naksha overlay on" : "Naksha overlay off";
  elements.adjustBoundary.classList.toggle("active", app.adjustingBoundary);
  elements.adjustBoundary.textContent = app.adjustingBoundary ? "Dragging…" : "Drag";
  elements.boundaryOpacity.value = String(Math.round(boundary.opacity * 100));
  elements.alignmentMode.classList.toggle("hidden", !isOverall);
  elements.alignmentMode.classList.toggle("active", scaleLocked);
  elements.alignmentMode.textContent = scaleLocked ? "Scale locked" : "Feature fit";
  elements.alignmentMode.title = scaleLocked
    ? "Plot 77 scale is locked; select to use the road/river feature fit"
    : "Road/river feature fit can change scale/skew; select to lock the Plot 77 scale";
  elements.boundarySmaller.disabled = scaleLocked;
  elements.boundaryLarger.disabled = scaleLocked;
  elements.boundarySmaller.title = scaleLocked ? "Disabled while Plot 77 scale is locked" : "Make selected overlay smaller";
  elements.boundaryLarger.title = scaleLocked ? "Disabled while Plot 77 scale is locked" : "Make selected overlay larger";
  elements.geoViewport.classList.toggle("adjusting-boundary", app.adjustingBoundary);
  const sheet = SHEETS[app.geoSheetIndex];
  elements.boundarySaveStatus.textContent = `Saved · ${sheet.isOverall ? "Overall" : `Sheet ${sheet.label}`}`;
}

function markBoundarySaved(message = "Saved") {
  const sheet = SHEETS[app.geoSheetIndex];
  elements.boundarySaveStatus.textContent = `${message} · ${sheet.isOverall ? "Overall" : `Sheet ${sheet.label}`}`;
}

function nudgeBoundary(direction, event) {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  const stepMetres = event.shiftKey ? 50 : 10;
  if (direction === "left") boundary.eastOffset -= stepMetres;
  if (direction === "right") boundary.eastOffset += stepMetres;
  if (direction === "up") boundary.northOffset += stepMetres;
  if (direction === "down") boundary.northOffset -= stepMetres;
  persist();
  markBoundarySaved("Auto-saved");
  refreshBoundaryOverlay();
}

elements.boundaryOverlay.addEventListener("load", renderGeoMap);

function geoZoom(direction, clientX, clientY) {
  const previousZoom = geo.zoom;
  const nextZoom = clamp(previousZoom + direction, 3, 19.5);
  if (nextZoom === geo.zoom) return;
  const rect = elements.geoViewport.getBoundingClientRect();
  const anchorX = (clientX ?? rect.left + rect.width / 2) - rect.left;
  const anchorY = (clientY ?? rect.top + rect.height / 2) - rect.top;
  const center = latLonToWorld(geo.lat, geo.lon, geo.zoom);
  const anchorWorld = { x: center.x + anchorX - rect.width / 2, y: center.y + anchorY - rect.height / 2 };
  const factor = 2 ** (nextZoom - geo.zoom);
  const nextAnchorWorld = { x: anchorWorld.x * factor, y: anchorWorld.y * factor };
  const nextCenter = { x: nextAnchorWorld.x - anchorX + rect.width / 2, y: nextAnchorWorld.y - anchorY + rect.height / 2 };
  geo.zoom = nextZoom;
  const centerLatLon = worldToLatLon(nextCenter.x, nextCenter.y, geo.zoom);
  geo.lat = centerLatLon.lat;
  geo.lon = centerLatLon.lon;
  renderGeoMap();
  if (app.linkViews && !app.syncingViews) syncNakshaFromGeo(previousZoom);
}

function zoomAt(factor, clientX, clientY) {
  const rect = elements.viewport.getBoundingClientRect();
  const sx = clientX ?? rect.left + rect.width / 2;
  const sy = clientY ?? rect.top + rect.height / 2;
  const localX = sx - rect.left;
  const localY = sy - rect.top;
  const worldX = (localX - app.panX) / app.scale;
  const worldY = (localY - app.panY) / app.scale;
  const previousScale = app.scale;
  const nextScale = clamp(previousScale * factor, app.minScale, app.maxScale);
  app.panX = localX - worldX * nextScale;
  app.panY = localY - worldY * nextScale;
  app.scale = nextScale;
  applyTransform();
  if (app.linkViews && !app.syncingViews && nextScale !== previousScale) {
    syncGeoFromNaksha(nextScale / previousScale);
  }
}

function normalizedWheelDelta(event, viewport) {
  let delta = event.deltaY;
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) delta *= 16;
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
    delta *= Math.max(viewport.getBoundingClientRect().height, 1);
  }
  return clamp(delta, -180, 180);
}

function setMode(mode) {
  app.mode = mode;
  app.draft = [];
  elements.viewport.dataset.mode = mode;
  document.querySelectorAll("[data-tool]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tool === mode);
  });
  const hints = {
    pan: app.activeSheet === 0
      ? "Click to identify a plot · Drag to move · Mouse wheel or +/− to zoom"
      : "Drag to move · Mouse wheel or +/− to zoom",
    calibrate: "Click two endpoints of a known real-world length",
    distance: sheetState().calibration ? "Click start and end points" : "Calibrate this sheet before measuring",
    area: sheetState().calibration ? "Click each parcel corner, then Finish area" : "Calibrate this sheet before measuring",
  };
  const snapHint = mode === "pan" ? "" : app.boundarySnap ? " · Boundary snap on" : " · Free placement";
  elements.modeHint.textContent = `${hints[mode]}${snapHint}`;
  elements.finishArea.classList.toggle("hidden", mode !== "area");
  renderOverlay();
}

function pointFromEvent(event) {
  const rect = elements.viewport.getBoundingClientRect();
  return {
    x: clamp((event.clientX - rect.left - app.panX) / app.scale, 0, app.imageWidth),
    y: clamp((event.clientY - rect.top - app.panY) / app.scale, 0, app.imageHeight),
  };
}

function alignPointToBoundary(point) {
  if (!app.boundarySnap || !elements.image.complete || !elements.image.naturalWidth) {
    return { ...point, snapped: false };
  }
  const radius = Math.round(clamp(14 / app.scale, 4, 40));
  const size = radius * 2 + 1;
  const sourceX = Math.round(clamp(point.x - radius, 0, app.imageWidth - size));
  const sourceY = Math.round(clamp(point.y - radius, 0, app.imageHeight - size));
  snapCanvas.width = size;
  snapCanvas.height = size;
  snapContext.clearRect(0, 0, size, size);
  snapContext.drawImage(elements.image, sourceX, sourceY, size, size, 0, 0, size, size);
  const pixels = snapContext.getImageData(0, 0, size, size).data;
  let best = null;
  for (let y = 1; y < size - 1; y += 1) {
    for (let x = 1; x < size - 1; x += 1) {
      const offset = (y * size + x) * 4;
      const luminance = pixels[offset] * 0.2126 + pixels[offset + 1] * 0.7152 + pixels[offset + 2] * 0.0722;
      if (luminance > 92 || pixels[offset + 3] < 200) continue;
      const imageX = sourceX + x;
      const imageY = sourceY + y;
      const squaredDistance = (imageX - point.x) ** 2 + (imageY - point.y) ** 2;
      if (!best || squaredDistance < best.squaredDistance) {
        best = { x: imageX, y: imageY, squaredDistance };
      }
    }
  }
  return best ? { x: best.x, y: best.y, snapped: true } : { ...point, snapped: false };
}

elements.viewport.addEventListener("pointerdown", (event) => {
  elements.viewport.focus();
  app.pointerStart = { x: event.clientX, y: event.clientY };
  app.moved = false;
  if (app.mode === "pan" || event.button === 1 || event.shiftKey) {
    app.dragging = true;
    app.startPan = { x: app.panX, y: app.panY };
    elements.viewport.classList.add("dragging");
    elements.viewport.setPointerCapture(event.pointerId);
  }
});

elements.viewport.addEventListener("pointermove", (event) => {
  const point = pointFromEvent(event);
  elements.cursorPosition.textContent = `Position: ${Math.round(point.x)}, ${Math.round(point.y)} px`;
  if (!app.dragging) return;
  const dx = event.clientX - app.pointerStart.x;
  const dy = event.clientY - app.pointerStart.y;
  if (Math.abs(dx) + Math.abs(dy) > 3) app.moved = true;
  app.panX = app.startPan.x + dx;
  app.panY = app.startPan.y + dy;
  applyTransform();
});

elements.viewport.addEventListener("pointerup", (event) => {
  if (app.dragging) {
    const identify = !app.moved && app.mode === "pan" && event.button === 0;
    app.dragging = false;
    elements.viewport.classList.remove("dragging");
    if (identify) {
      const point = pointFromEvent(event);
      if (app.coordinateEditor.picking) placeCoordinateAt(point);
      else identifyPlotAt(point);
    }
    return;
  }
  if (!app.moved && app.mode !== "pan") addDraftPoint(alignPointToBoundary(pointFromEvent(event)));
});

elements.viewport.addEventListener("pointercancel", () => {
  app.dragging = false;
  elements.viewport.classList.remove("dragging");
});

elements.viewport.addEventListener("wheel", (event) => {
  event.preventDefault();
  const delta = normalizedWheelDelta(event, elements.viewport);
  if (!delta) return;
  zoomAt(Math.exp(-delta * 0.0018), event.clientX, event.clientY);
}, { passive: false });

elements.viewport.addEventListener("dblclick", (event) => {
  event.preventDefault();
});

function addDraftPoint(point) {
  if ((app.mode === "distance" || app.mode === "area") && !sheetState().calibration) {
    setMode("calibrate");
    return;
  }
  if (app.mode === "area" && app.draft.length >= 3 && distance(point, app.draft[0]) * app.scale <= 18) {
    finishArea();
    return;
  }
  if (app.draft.length && distance(point, app.draft.at(-1)) * app.scale < 4) return;
  app.draft.push(point);
  if (app.mode === "calibrate" && app.draft.length === 2) {
    elements.calibrationForm.classList.remove("hidden");
    elements.knownLength.focus();
  }
  if (app.mode === "distance" && app.draft.length === 2) {
    commitMeasurement("distance", app.draft);
    app.draft = [];
  }
  renderOverlay();
}

function identifyPlotAt(point) {
  if (app.activeSheet !== 0) return;
  const maximumDistance = clamp(70 / app.scale, 90, 450);
  let nearest = null;
  let nearestDistance = Infinity;
  for (const item of app.plotIndex.values()) {
    const candidateDistance = distance(point, item);
    if (candidateDistance < nearestDistance) {
      nearest = item;
      nearestDistance = candidateDistance;
    }
  }
  if (!nearest || nearestDistance > maximumDistance) {
    app.plotFocus = null;
    elements.clickedPlotInfo.innerHTML = "<strong>No indexed plot nearby</strong><small>Zoom in and click closer to a printed plot number.</small>";
    elements.clickedPlotInfo.classList.remove("hidden");
    elements.plotLocatorStatus.textContent = "No verified digital plot label was close enough to that map point.";
    elements.plotLocatorStatus.classList.add("warning");
    renderOverlay();
    return;
  }
  loadCoordinateEditorItem(nearest, false);
  app.plotFocus = {
    plot: Number(nearest.plot),
    sheet: Number(nearest.sheet),
    x: Number(nearest.x),
    y: Number(nearest.y),
    exact: true,
    source: nearest.source,
    selectedByClick: true,
    clickX: point.x,
    clickY: point.y,
  };
  elements.recordSearch.value = String(nearest.plot);
  elements.clickedPlotInfo.innerHTML = `<span>Selected plot</span><strong>${Number(nearest.plot)}</strong><small>Source Sheet ${Number(nearest.sheet)} · nearest verified printed label</small>`;
  elements.clickedPlotInfo.classList.remove("hidden");
  elements.plotLocatorStatus.textContent = `Clicked near Khasra ${Number(nearest.plot)} on Sheet ${Number(nearest.sheet)}. The target marks its verified printed label.`;
  elements.plotLocatorStatus.classList.remove("warning");
  renderOverlay();
}

function applyCalibration() {
  const known = Number(elements.knownLength.value);
  if (!(known > 0) || app.draft.length !== 2) {
    elements.knownLength.focus();
    return;
  }
  const pixels = distance(app.draft[0], app.draft[1]);
  const unit = elements.lengthUnit.value;
  sheetState().calibration = {
    metresPerPixel: known * UNIT_TO_METRES[unit] / pixels,
    known,
    unit,
    points: [...app.draft],
    source: "manual-length",
  };
  app.draft = [];
  elements.knownLength.value = "";
  elements.calibrationForm.classList.add("hidden");
  persist();
  updateCalibrationUI();
  if (app.linkViews) syncGeoFromNaksha(1);
  setMode("distance");
}

function cancelCalibration() {
  app.draft = [];
  elements.calibrationForm.classList.add("hidden");
  setMode("pan");
}

function finishArea() {
  if (app.draft.length < 3) return;
  commitMeasurement("area", app.draft);
  app.draft = [];
  renderOverlay();
}

function commitMeasurement(type, points) {
  const measurement = { type, points: points.map((point) => ({ ...point })), createdAt: Date.now() };
  sheetState().measurements.push(measurement);
  app.lastResult = measurement;
  persist();
  renderResults();
}

function undo() {
  if (app.draft.length) {
    app.draft.pop();
  } else {
    sheetState().measurements.pop();
    app.lastResult = sheetState().measurements.at(-1) || null;
    persist();
  }
  renderOverlay();
  renderResults();
}

function clearMeasurements() {
  app.draft = [];
  sheetState().measurements = [];
  app.lastResult = null;
  persist();
  renderOverlay();
  renderResults();
}

function updateCalibrationUI() {
  const calibration = sheetState().calibration;
  elements.calibrationBadge.textContent = calibration?.source === "plot77-area"
    ? "Plot 77 · 70 dismil"
    : calibration?.source === "plot54-area"
      ? "Plot 54 · 55 dismil"
    : calibration
      ? `${formatNumber(calibration.known)} ${UNIT_LABEL[calibration.unit]} reference`
      : "Not calibrated";
  elements.calibrationBadge.className = `badge ${calibration ? "ok" : "warning"}`;
  elements.usePlot54Scale.classList.toggle("hidden", app.activeSheet !== 0);
}

function renderOverlay() {
  const state = sheetState();
  const all = [...state.measurements];
  const radius = clamp(5 / app.scale, 5, 35);
  const fontSize = clamp(14 / app.scale, 14, 80);
  const parts = [];

  if (app.plotFocus?.exact && app.activeSheet === 0) {
    const radius = 24 / app.scale;
    const line = 34 / app.scale;
    if (app.plotFocus.selectedByClick) {
      parts.push(`<path d="M ${app.plotFocus.clickX} ${app.plotFocus.clickY} L ${app.plotFocus.x} ${app.plotFocus.y}" class="plot-click-link" />`);
      parts.push(`<circle cx="${app.plotFocus.clickX}" cy="${app.plotFocus.clickY}" r="${8 / app.scale}" class="plot-click-point" />`);
    }
    parts.push(`<circle cx="${app.plotFocus.x}" cy="${app.plotFocus.y}" r="${radius}" class="plot-target-ring" />`);
    parts.push(`<path d="M ${app.plotFocus.x - line} ${app.plotFocus.y} H ${app.plotFocus.x + line} M ${app.plotFocus.x} ${app.plotFocus.y - line} V ${app.plotFocus.y + line}" class="plot-target-cross" />`);
    parts.push(`<text x="${app.plotFocus.x}" y="${app.plotFocus.y - 38 / app.scale}" text-anchor="middle" font-size="${22 / app.scale}" class="plot-focus-label">Khasra ${escapeHtml(app.plotFocus.plot)} · Sheet ${app.plotFocus.sheet}</text>`);
  } else if (app.plotFocus && app.activeSheet === 0) {
    const bounds = COMBINED_SHEET_BOUNDS[app.plotFocus.sheet];
    if (bounds) {
      const inset = 10 / app.scale;
      parts.push(`<rect x="${bounds.x + inset}" y="${bounds.y + inset}" width="${bounds.width - inset * 2}" height="${bounds.height - inset * 2}" rx="${18 / app.scale}" class="plot-sheet-focus" />`);
      parts.push(`<text x="${bounds.x + 26 / app.scale}" y="${bounds.y + 55 / app.scale}" font-size="${22 / app.scale}" class="plot-focus-label">Khasra ${escapeHtml(app.plotFocus.plot)} · source Sheet ${app.plotFocus.sheet}</text>`);
    }
  }

  if (state.calibration?.points) {
    parts.push(svgLine(state.calibration.points, "calibration", radius, fontSize, "Calibration"));
  }
  all.forEach((measurement, index) => {
    const label = measurement.type === "distance" ? `Distance ${index + 1}` : `Area ${index + 1}`;
    parts.push(svgShape(measurement.points, measurement.type, radius, fontSize, label, measurement.type === "area"));
  });
  if (app.draft.length) {
    parts.push(svgShape(app.draft, `draft-${app.mode}`, radius, fontSize, "", app.mode === "area"));
  }
  elements.overlay.innerHTML = parts.join("");
}

function svgLine(points, cssClass, radius, fontSize, label) {
  return svgShape(points, cssClass, radius, fontSize, label, false);
}

function svgShape(points, cssClass, radius, fontSize, label, close) {
  const coords = points.map((point) => `${point.x},${point.y}`).join(" ");
  const end = points.at(-1);
  const shape = close && points.length > 2
    ? `<polygon points="${coords}" class="measure-shape ${cssClass}" />`
    : `<polyline points="${coords}" class="measure-shape ${cssClass}" />`;
  const dots = points.map((point, index) =>
    `<circle cx="${point.x}" cy="${point.y}" r="${radius}" class="measure-point ${cssClass}${point.snapped ? " snapped" : ""}"><title>Point ${index + 1}${point.snapped ? " · snapped to boundary" : ""}</title></circle>`
  ).join("");
  const text = label && end
    ? `<text x="${end.x + radius * 1.6}" y="${end.y - radius * 1.6}" font-size="${fontSize}" class="measure-label">${label}</text>`
    : "";
  return `${shape}${dots}${text}`;
}

function renderResults() {
  const measurement = app.lastResult || sheetState().measurements.at(-1);
  const calibration = sheetState().calibration;
  if (!measurement || !calibration) {
    elements.emptyResults.classList.remove("hidden");
    elements.results.classList.add("hidden");
    elements.measurementDetails.innerHTML = "";
    return;
  }
  elements.emptyResults.classList.add("hidden");
  elements.results.classList.remove("hidden");
  const metresPerPixel = calibration.metresPerPixel;

  if (measurement.type === "distance") {
    const metres = polylineLength(measurement.points) * metresPerPixel;
    elements.resultType.textContent = "Measured distance";
    elements.resultMain.textContent = `${formatNumber(metres)} m`;
    elements.resultGrid.innerHTML = resultItems([
      ["Feet", `${formatNumber(metres / 0.3048)} ft`],
      ["Yards", `${formatNumber(metres / 0.9144)} yd`],
    ]);
    elements.measurementDetails.innerHTML = measurementMethodDetails(calibration, measurement.points);
  } else {
    const perimeter = polygonPerimeter(measurement.points) * metresPerPixel;
    const squareMetres = polygonArea(measurement.points) * metresPerPixel * metresPerPixel;
    const dismil = squareMetres / 40.468564224;
    const acres = dismil / 100;
    elements.resultType.textContent = "Parcel area · dismil/decimal";
    elements.resultMain.textContent = `${formatDetailed(dismil, 4)} dismil`;
    elements.resultGrid.innerHTML = resultItems([
      ["Acres", formatDetailed(acres, 6)],
      ["Square metres", `${formatDetailed(squareMetres, 2)} m²`],
      ["Square feet", `${formatDetailed(squareMetres / 0.09290304, 2)} ft²`],
      ["Perimeter", `${formatDetailed(perimeter, 2)} m`],
      ["Perimeter feet", `${formatDetailed(perimeter / 0.3048, 2)} ft`],
      ["Boundary points", String(measurement.points.length)],
    ]);
    elements.measurementDetails.innerHTML = areaMeasurementDetails(measurement.points, metresPerPixel, calibration);
  }
}

function measurementMethodDetails(calibration, points) {
  const snapped = points.filter((point) => point.snapped).length;
  const benchmark = app.scheduleData?.benchmark;
  const referenceDetails = calibration.source === "plot77-area" && benchmark
    ? `<span>Reference check</span><strong>${benchmark.references.map((item) => `Plot ${item.plot}: ${formatDetailed(item.referenceScaleAreaDismil, 2)}/${item.areaDismil}`).join(" · ")} dismil</strong>
       <span>Maximum difference</span><strong>${formatDetailed(benchmark.maximumReferenceDifferenceDismil, 2)} dismil</strong>`
    : "";
  return `<div class="measurement-method">
    <span>Calibration</span><strong>${calibration.source === "plot77-area" ? "Plot 77 · 70 dismil area" : calibration.source === "plot54-area" ? "Plot 54 · 55 dismil area" : "Known boundary length"}</strong>
    <span>Scale</span><strong>${formatDetailed(calibration.metresPerPixel, 6)} m/source px</strong>
    ${referenceDetails}
    <span>Aligned points</span><strong>${snapped} of ${points.length}</strong>
  </div>`;
}

function areaMeasurementDetails(points, metresPerPixel, calibration) {
  const sides = points.map((point, index) => {
    const next = points[(index + 1) % points.length];
    const metres = distance(point, next) * metresPerPixel;
    return `<div><span>Side ${index + 1} · P${index + 1}→P${(index + 1) % points.length + 1}</span><strong>${formatDetailed(metres, 2)} m <small>${formatDetailed(metres / 0.3048, 2)} ft</small></strong></div>`;
  }).join("");
  return `${measurementMethodDetails(calibration, points)}
    <div class="side-details"><h4>Boundary side lengths</h4>${sides}</div>
    <p class="calculation-detail">Closed-polygon area calculated from the aligned source-image vertices and your calibration scale.</p>`;
}

function resultItems(items) {
  return items.map(([label, value]) =>
    `<div class="result-item"><span>${label}</span><strong>${value}</strong></div>`
  ).join("");
}

function distance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function polylineLength(points) {
  return points.slice(1).reduce((sum, point, index) => sum + distance(points[index], point), 0);
}

function polygonPerimeter(points) {
  return polylineLength(points) + distance(points.at(-1), points[0]);
}

function polygonArea(points) {
  return Math.abs(points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point.x * next.y - next.x * point.y;
  }, 0) / 2);
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: value < 10 ? 3 : 2 }).format(value);
}

function formatDetailed(value, maximumFractionDigits) {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits }).format(value);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

async function loadRecords(cacheVersion = "") {
  try {
    const suffix = cacheVersion ? `?v=${encodeURIComponent(cacheVersion)}` : "";
    const response = await fetch(`assets/final-schedule-map.json${suffix}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Final schedule unavailable");
    app.scheduleData = await response.json();
    app.records = app.scheduleData.plots;
    const overlayVersion = cacheVersion || String(Date.now());
    elements.scheduleOverlay.src = `assets/Final_Schedule_Overlay.png?v=${encodeURIComponent(overlayVersion)}`;
    elements.scheduleCoverage.textContent = `${app.scheduleData.mappedPlots} of ${app.scheduleData.uniquePlots} plots mapped`;
    elements.usePlot54Scale.disabled = !app.scheduleData.benchmark;
    applyAreaBenchmark(false);
    renderRecords("");
  } catch {
    elements.recordCount.textContent = "Unavailable";
    elements.scheduleCoverage.textContent = "Overlay unavailable";
    elements.recordList.innerHTML = '<div class="no-records">Run the local server from the repository root to load Final_Schedule.csv data.</div>';
  }
}

function applyAreaBenchmark(force = true) {
  const benchmark = app.scheduleData?.benchmark;
  if (!benchmark) return;
  const overall = sheetState(0);
  if (!force && overall.calibration && !["plot54-area", "multi-plot-area", "plot77-area"].includes(overall.calibration.source)) return;
  overall.calibration = {
    source: "plot77-area",
    metresPerPixel: benchmark.metresPerPixel,
    known: benchmark.totalAreaDismil,
    unit: "dismil",
    benchmarkPlots: benchmark.plots,
    benchmarkPixelArea: benchmark.combinedPixelArea,
  };
  persist();
  if (app.activeSheet === 0) {
    updateCalibrationUI();
    renderResults();
    updateLinkedScaleStatus();
    if (app.linkViews) syncGeoFromNaksha(1);
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"' && quoted && text[i + 1] === '"') { field += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(field); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += char;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function field(record, startsWith) {
  const key = Object.keys(record).find((item) => item.startsWith(startsWith));
  return key ? record[key] : "";
}

function renderRecords(query) {
  const normalized = query.trim().toLowerCase();
  const filtered = app.records.filter((record) =>
    !normalized || Object.values(record).some((value) => String(value).toLowerCase().includes(normalized))
  );
  elements.recordCount.textContent = `${filtered.length} of ${app.records.length}`;
  if (!filtered.length) {
    elements.recordList.innerHTML = '<div class="no-records">No matching land record.</div>';
    return;
  }
  elements.recordList.innerHTML = filtered.slice(0, 100).map((record) => {
    const khasra = record.plot;
    const khata = record.khata;
    const area = record.areaDismil;
    const location = record.location;
    const status = record.status;
    return `<article class="record-card" data-plot="${escapeHtml(khasra)}" role="button" tabindex="0" title="Locate Khasra ${escapeHtml(khasra)} on the combined naksha">
      <div class="record-title"><strong>Khasra ${escapeHtml(khasra)}</strong><span>${escapeHtml(status)}</span></div>
      <p class="record-location">${escapeHtml(location || "Location not recorded")}</p>
      <div class="record-meta"><span>Khata ${escapeHtml(khata)}</span><span>${escapeHtml(area)} dismil</span><span class="${record.mapped ? "mapped-chip" : "unmapped-chip"}">${record.mapped ? "Mapped" : "Sheet only"}</span></div>
      <div class="record-shares"><span class="share-chip a">A ${escapeHtml(record.scheduleA)} dismil</span><span class="share-chip b">B ${escapeHtml(record.scheduleB)} dismil</span></div>
    </article>`;
  }).join("");
}

function sourceSheetForPlot(plot) {
  if (plot <= 933) return 1;
  if (plot <= 2171) return 2;
  if (plot <= 3845) return 3;
  if (plot <= 6175) return 4;
  return 5;
}

function coordinateEditorStatus(message, type = "") {
  elements.coordinateStatus.textContent = message;
  elements.coordinateStatus.className = `coordinate-status${type ? ` ${type}` : ""}`;
}

function setCoordinateEditorEnabled(enabled) {
  [
    elements.coordinateSheet,
    elements.coordinateX,
    elements.coordinateY,
    elements.coordinatePick,
    elements.coordinateUp,
    elements.coordinateDown,
    elements.coordinateLeft,
    elements.coordinateRight,
    elements.coordinateRevert,
  ].forEach((control) => { control.disabled = !enabled; });
  elements.coordinateSave.disabled = !enabled || !app.coordinateEditor.dirty || app.coordinateEditor.saving;
}

function coordinateValues() {
  const plot = Number(elements.coordinatePlot.value);
  const sheet = Number(elements.coordinateSheet.value);
  if (!elements.coordinateX.value.trim() || !elements.coordinateY.value.trim()) return null;
  const x = Number(elements.coordinateX.value);
  const y = Number(elements.coordinateY.value);
  if (!Number.isInteger(plot) || plot < 1 || plot > 7000) return null;
  if (!Number.isInteger(sheet) || sheet < 1 || sheet > 5) return null;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return {
    plot,
    sheet,
    x: clamp(Math.round(x * 10) / 10, 0, app.combinedImageWidth),
    y: clamp(Math.round(y * 10) / 10, 0, app.combinedImageHeight),
  };
}

function showCoordinatePreview(markDirty = true) {
  const item = coordinateValues();
  if (!item || app.coordinateEditor.plot !== item.plot) return;
  elements.coordinateX.value = item.x.toFixed(1);
  elements.coordinateY.value = item.y.toFixed(1);
  if (markDirty) app.coordinateEditor.dirty = true;
  app.plotFocus = { ...item, exact: true, source: "coordinate-editor-preview" };
  elements.coordinateEditorBadge.textContent = app.coordinateEditor.dirty ? "Unsaved" : "Loaded";
  elements.coordinateEditorBadge.className = `badge${app.coordinateEditor.dirty ? " dirty" : ""}`;
  setCoordinateEditorEnabled(true);
  renderOverlay();
}

function loadCoordinateEditorItem(item, focus = true) {
  if (app.activeSheet !== 0) selectSheet(0);
  app.plotLabelsVisible = true;
  updatePlotLabelsVisibility();
  app.coordinateEditor.plot = Number(item.plot);
  app.coordinateEditor.original = app.plotIndex.has(Number(item.plot))
    ? { ...app.plotIndex.get(Number(item.plot)) }
    : null;
  app.coordinateEditor.picking = false;
  app.coordinateEditor.dirty = false;
  elements.coordinatePlot.value = String(item.plot);
  elements.coordinateSheet.value = String(item.sheet);
  elements.coordinateX.value = Number(item.x).toFixed(1);
  elements.coordinateY.value = Number(item.y).toFixed(1);
  elements.coordinatePick.classList.remove("active");
  elements.coordinatePick.textContent = "Place by clicking map";
  showCoordinatePreview(false);
  coordinateEditorStatus(
    app.coordinateEditor.original
      ? `Plot ${item.plot} loaded. Change X/Y, click the map, or use the arrow buttons.`
      : `New plot ${item.plot}. Choose its exact position on the overall map, then save.`,
  );
  if (focus) requestAnimationFrame(focusPlotRegion);
}

function loadCoordinateEditor() {
  const plot = Number(elements.coordinatePlot.value);
  if (!Number.isInteger(plot) || plot < 1 || plot > 7000) {
    coordinateEditorStatus("Enter a plot number between 1 and 7000.", "warning");
    elements.coordinatePlot.focus();
    return;
  }
  const existing = app.plotIndex.get(plot);
  if (existing) {
    loadCoordinateEditorItem(existing);
    return;
  }
  const sheet = sourceSheetForPlot(plot);
  const bounds = COMBINED_SHEET_BOUNDS[sheet];
  loadCoordinateEditorItem({
    plot,
    sheet,
    x: bounds.x + bounds.width / 2,
    y: bounds.y + bounds.height / 2,
  });
  startCoordinatePick();
}

function startCoordinatePick() {
  if (!app.coordinateEditor.plot) return;
  if (app.activeSheet !== 0) selectSheet(0);
  setMode("pan");
  app.coordinateEditor.picking = true;
  elements.coordinatePick.classList.add("active");
  elements.coordinatePick.textContent = "Click a position on map…";
  elements.modeHint.textContent = `Click the new centre for Plot ${app.coordinateEditor.plot} · drag still pans`;
  coordinateEditorStatus(`Click inside the correct parcel for Plot ${app.coordinateEditor.plot}.`, "warning");
}

function placeCoordinateAt(point) {
  elements.coordinateX.value = point.x.toFixed(1);
  elements.coordinateY.value = point.y.toFixed(1);
  app.coordinateEditor.picking = false;
  elements.coordinatePick.classList.remove("active");
  elements.coordinatePick.textContent = "Place by clicking map";
  showCoordinatePreview(true);
  setMode("pan");
  coordinateEditorStatus(`Plot ${app.coordinateEditor.plot} preview moved to X ${point.x.toFixed(1)}, Y ${point.y.toFixed(1)}. Save when correct.`);
}

function nudgeCoordinate(dx, dy) {
  if (!app.coordinateEditor.plot) return;
  const step = Number(elements.coordinateStep.value) || 1;
  elements.coordinateX.value = String(Number(elements.coordinateX.value) + dx * step);
  elements.coordinateY.value = String(Number(elements.coordinateY.value) + dy * step);
  showCoordinatePreview(true);
  coordinateEditorStatus(`Moved Plot ${app.coordinateEditor.plot} by ${step} px. Save when correct.`);
}

function revertCoordinateEditor() {
  const original = app.coordinateEditor.original;
  if (original) {
    loadCoordinateEditorItem(original, false);
    coordinateEditorStatus(`Reverted Plot ${original.plot} to its last saved position.`);
  } else {
    loadCoordinateEditor();
  }
}

async function saveCoordinateEditor() {
  const item = coordinateValues();
  if (!item) {
    coordinateEditorStatus("Enter valid plot, sheet, X and Y values.", "warning");
    return;
  }
  app.coordinateEditor.saving = true;
  setCoordinateEditorEnabled(true);
  elements.coordinateEditorBadge.textContent = "Saving…";
  coordinateEditorStatus("Saving the coordinate to the local project…");
  try {
    const response = await fetch("/api/plot-coordinate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.ok) throw new Error(result.error || "Save failed");
    app.plotIndex.set(item.plot, result.item);
    app.coordinateEditor.original = { ...result.item };
    app.coordinateEditor.dirty = false;
    app.coordinateEditor.saving = false;
    const assetVersion = Date.now();
    elements.plotLabels.src = `assets/plot-labels.svg?v=${assetVersion}`;
    elements.scheduleOverlay.src = `assets/Final_Schedule_Overlay.png?v=${assetVersion}`;
    await loadRecords(String(assetVersion));
    if (result.georeference?.updated) {
      await loadGeoreference(String(assetVersion));
      refreshBoundaryOverlay();
    }
    app.plotFocus = { ...result.item, exact: true };
    elements.coordinateEditorBadge.textContent = "Saved";
    elements.coordinateEditorBadge.className = "badge saved";
    setCoordinateEditorEnabled(true);
    const schedule = result.schedule || {};
    const scheduleNote = !schedule.updated
      ? ` Schedule refresh failed: ${schedule.error || "unknown error"}.`
      : !schedule.inSchedule
        ? " This plot is not listed in the Final Schedule."
        : schedule.mapped
          ? " Its Final Schedule colour is now displayed."
          : " It is in the Final Schedule, but the point is not inside a closed parcel; move it farther inside the parcel and save again.";
    const georeferenceNote = result.georeference?.updated
      ? " The scale-locked map transform was refreshed."
      : result.georeference?.error
        ? ` Map alignment refresh failed: ${result.georeference.error}.`
        : "";
    coordinateEditorStatus(
      `Plot ${item.plot} saved at X ${item.x.toFixed(1)}, Y ${item.y.toFixed(1)} on Sheet ${item.sheet}.${scheduleNote}${georeferenceNote}`,
      schedule.updated && (!schedule.inSchedule || schedule.mapped) && result.georeference?.updated !== false ? "success" : "warning",
    );
    if (schedule.updated && schedule.inSchedule && schedule.mapped) {
      app.scheduleVisible = true;
      updateScheduleVisibility();
    }
    elements.plotLocatorStatus.textContent = `Plot ${item.plot} was saved with the coordinate editor and is searchable immediately.`;
    elements.plotLocatorStatus.classList.remove("warning");
    renderOverlay();
  } catch (error) {
    app.coordinateEditor.saving = false;
    elements.coordinateEditorBadge.textContent = "Not saved";
    elements.coordinateEditorBadge.className = "badge dirty";
    setCoordinateEditorEnabled(true);
    coordinateEditorStatus(`${error.message}. Start the app with python3 run_app.py to enable saving.`, "warning");
  }
}

function locatePlot(value) {
  elements.clickedPlotInfo.classList.add("hidden");
  const match = String(value).match(/\d{1,5}/);
  const plot = match ? Number(match[0]) : NaN;
  if (!Number.isInteger(plot) || plot < 1 || plot > 7000) {
    elements.plotLocatorStatus.textContent = "Enter a valid numeric khasra / plot number.";
    elements.plotLocatorStatus.classList.add("warning");
    return;
  }
  const sourceSheet = sourceSheetForPlot(plot);
  const indexed = app.plotIndex.get(plot);
  if (app.activeSheet !== 0) selectSheet(0);
  app.plotFocus = indexed
    ? { plot, sheet: indexed.sheet, x: indexed.x, y: indexed.y, exact: true, source: indexed.source }
    : { plot, sheet: sourceSheet, exact: false };
  const locatedSheet = indexed?.sheet || sourceSheet;
  const sourceIndex = SHEETS.findIndex((sheet) => sheet.number === locatedSheet);
  setGeoSheet(SHEETS[sourceIndex]);
  elements.markerLabel.textContent = `Khasra ${plot} · approximate Sheet ${locatedSheet} area`;
  elements.plotLocatorStatus.textContent = indexed
    ? `Khasra ${plot} found on Sheet ${locatedSheet}. The target marks its printed label in the combined naksha.`
    : `Khasra ${plot} belongs to Sheet ${locatedSheet}, but its tiny printed label was not indexed confidently. The source-sheet area is highlighted instead.`;
  elements.plotLocatorStatus.classList.remove("warning");
  const url = new URL(window.location.href);
  url.searchParams.set("plot", String(plot));
  window.history.replaceState(null, "", url);
  renderOverlay();
  requestAnimationFrame(focusPlotRegion);
}

async function loadPlotIndex() {
  try {
    const response = await fetch("assets/plot-index.json");
    if (!response.ok) throw new Error("Plot index unavailable");
    const data = await response.json();
    app.plotIndex = new Map(data.plots.map((item) => [Number(item.plot), item]));
    app.combinedImageWidth = Number(data.imageWidth) || app.combinedImageWidth;
    app.combinedImageHeight = Number(data.imageHeight) || app.combinedImageHeight;
    elements.plotLocatorStatus.textContent = `${data.count} OCR-verified or manually audited plot labels are searchable by exact position. Other numbers fall back to their source sheet.`;
    const requestedPlot = new URLSearchParams(window.location.search).get("plot");
    if (requestedPlot) {
      elements.recordSearch.value = requestedPlot;
      locatePlot(requestedPlot);
    }
  } catch {
    elements.plotLocatorStatus.textContent = "Exact label index unavailable; plot searches will locate the source sheet.";
  }
}

async function loadGeoreference(cacheVersion = "") {
  try {
    const suffix = cacheVersion ? `?v=${encodeURIComponent(cacheVersion)}` : "";
    const response = await fetch(`assets/naksha-georeference.json${suffix}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Georeference unavailable");
    app.georeference = await response.json();
    const overallBoundary = sheetState(0).boundary;
    if (overallBoundary.georeferenceVersion !== app.georeference.version) {
      Object.assign(overallBoundary, {
        alignmentMode: app.georeference.activeMode || "scale-locked",
        georeferenceVersion: app.georeference.version,
        scaleFactor: 1,
        rotation: 0,
        eastOffset: 0,
        northOffset: 0,
      });
      persist();
    }
    const centre = app.georeference.centre;
    SHEETS[0].geographicReference = [centre.latitude, centre.longitude];
  } catch {
    app.georeference = null;
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.tool)));
elements.snapToLines.addEventListener("click", () => {
  app.boundarySnap = !app.boundarySnap;
  elements.snapToLines.classList.toggle("active", app.boundarySnap);
  elements.snapToLines.setAttribute("aria-pressed", String(app.boundarySnap));
  elements.snapToLines.innerHTML = app.boundarySnap
    ? '<span aria-hidden="true">⌖</span> Boundary snap'
    : '<span aria-hidden="true">○</span> Free points';
  if (app.mode !== "pan") {
    const separator = elements.modeHint.textContent.indexOf(" · Boundary snap on");
    const freeSeparator = elements.modeHint.textContent.indexOf(" · Free placement");
    const cut = separator >= 0 ? separator : freeSeparator;
    const base = cut >= 0 ? elements.modeHint.textContent.slice(0, cut) : elements.modeHint.textContent;
    elements.modeHint.textContent = `${base}${app.boundarySnap ? " · Boundary snap on" : " · Free placement"}`;
  }
});
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => setViewMode(button.dataset.view)));
document.querySelectorAll("[data-basemap]").forEach((button) => button.addEventListener("click", () => {
  geo.basemap = button.dataset.basemap;
  document.querySelectorAll("[data-basemap]").forEach((item) => item.classList.toggle("active", item === button));
  renderGeoMap();
}));
elements.linkZoom.addEventListener("click", () => {
  app.linkViews = !app.linkViews;
  elements.linkZoom.classList.toggle("active", app.linkViews);
  elements.linkZoom.setAttribute("aria-pressed", String(app.linkViews));
  elements.linkZoom.textContent = app.linkViews ? "↔ Linked zoom" : "↔ Independent";
  if (app.linkViews) syncGeoFromNaksha(1);
  updateLinkedScaleStatus();
});
elements.toggleBoundary.addEventListener("click", () => {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  boundary.visible = !boundary.visible;
  persist();
  markBoundarySaved("Auto-saved");
  updateBoundaryControls();
  refreshBoundaryOverlay();
});
elements.alignmentMode.addEventListener("click", () => {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  if (!SHEETS[app.geoSheetIndex].isOverall) return;
  boundary.alignmentMode = boundary.alignmentMode === "feature-fit" ? "scale-locked" : "feature-fit";
  boundary.scaleFactor = 1;
  boundary.rotation = 0;
  boundary.eastOffset = 0;
  boundary.northOffset = 0;
  persist();
  updateBoundaryControls();
  setGeoSheet(SHEETS[app.geoSheetIndex]);
  markBoundarySaved(boundary.alignmentMode === "scale-locked" ? "Plot 77 scale locked" : "Feature fit loaded");
});
elements.adjustBoundary.addEventListener("click", () => {
  app.adjustingBoundary = !app.adjustingBoundary;
  updateBoundaryControls();
});
elements.boundarySmaller.addEventListener("click", () => {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  if (SHEETS[app.geoSheetIndex].isOverall && boundary.alignmentMode !== "feature-fit") return;
  if (SHEETS[app.geoSheetIndex].isOverall && app.georeference) boundary.scaleFactor = (boundary.scaleFactor || 1) * 0.9;
  else boundary.heightMetres *= 0.9;
  persist();
  markBoundarySaved("Auto-saved");
  refreshBoundaryOverlay();
});
elements.boundaryLarger.addEventListener("click", () => {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  if (SHEETS[app.geoSheetIndex].isOverall && boundary.alignmentMode !== "feature-fit") return;
  if (SHEETS[app.geoSheetIndex].isOverall && app.georeference) boundary.scaleFactor = (boundary.scaleFactor || 1) * 1.1;
  else boundary.heightMetres *= 1.1;
  persist();
  markBoundarySaved("Auto-saved");
  refreshBoundaryOverlay();
});
document.querySelector("#boundaryRotate").addEventListener("click", () => {
  const boundary = sheetState(app.geoSheetIndex).boundary;
  boundary.rotation = (boundary.rotation + 5) % 360;
  persist();
  markBoundarySaved("Auto-saved");
  refreshBoundaryOverlay();
});
elements.boundaryOpacity.addEventListener("input", () => {
  sheetState(app.geoSheetIndex).boundary.opacity = Number(elements.boundaryOpacity.value) / 100;
  persist();
  markBoundarySaved("Auto-saved");
  refreshBoundaryOverlay();
});
document.querySelector("#boundaryReset").addEventListener("click", () => {
  sheetState(app.geoSheetIndex).boundary = defaultBoundary(app.geoSheetIndex);
  app.adjustingBoundary = false;
  persist();
  markBoundarySaved("Reset saved");
  updateBoundaryControls();
  refreshBoundaryOverlay();
});
document.querySelector("#boundaryLeft").addEventListener("click", (event) => nudgeBoundary("left", event));
document.querySelector("#boundaryUp").addEventListener("click", (event) => nudgeBoundary("up", event));
document.querySelector("#boundaryDown").addEventListener("click", (event) => nudgeBoundary("down", event));
document.querySelector("#boundaryRight").addEventListener("click", (event) => nudgeBoundary("right", event));
document.querySelector("#boundarySave").addEventListener("click", () => {
  persist();
  markBoundarySaved("Saved");
});
document.querySelector(".boundary-controls").addEventListener("pointerdown", (event) => event.stopPropagation());
document.querySelector(".geo-controls").addEventListener("pointerdown", (event) => event.stopPropagation());
document.querySelector("#zoomIn").addEventListener("click", () => zoomAt(1.25));
document.querySelector("#zoomOut").addEventListener("click", () => zoomAt(0.8));
document.querySelector("#undo").addEventListener("click", undo);
document.querySelector("#clear").addEventListener("click", clearMeasurements);
document.querySelector("#applyCalibration").addEventListener("click", applyCalibration);
document.querySelector("#cancelCalibration").addEventListener("click", cancelCalibration);
document.querySelector("#geoZoomIn").addEventListener("click", () => geoZoom(0.5));
document.querySelector("#geoZoomOut").addEventListener("click", () => geoZoom(-0.5));
document.querySelector("#geoReset").addEventListener("click", () => {
  const previousZoom = geo.zoom;
  geo.lat = geo.homeLat;
  geo.lon = geo.homeLon;
  geo.zoom = SHEETS[app.geoSheetIndex].isOverall ? 14 : 15;
  renderGeoMap();
  if (app.linkViews) syncNakshaFromGeo(previousZoom);
});
elements.geoViewport.addEventListener("pointerdown", (event) => {
  geo.dragging = true;
  geo.pointerStart = { x: event.clientX, y: event.clientY };
  if (app.adjustingBoundary) {
    const boundary = sheetState(app.geoSheetIndex).boundary;
    app.boundaryDragStart = { east: boundary.eastOffset, north: boundary.northOffset };
  } else {
    geo.centerStart = latLonToWorld(geo.lat, geo.lon, geo.zoom);
  }
  elements.geoViewport.classList.add("dragging");
  elements.geoViewport.setPointerCapture(event.pointerId);
});
elements.geoViewport.addEventListener("pointermove", (event) => {
  if (!geo.dragging) return;
  if (app.adjustingBoundary) {
    const boundary = sheetState(app.geoSheetIndex).boundary;
    const metresPerPixel = actualMapMetresPerPixel();
    boundary.eastOffset = app.boundaryDragStart.east + (event.clientX - geo.pointerStart.x) * metresPerPixel;
    boundary.northOffset = app.boundaryDragStart.north - (event.clientY - geo.pointerStart.y) * metresPerPixel;
    refreshBoundaryOverlay();
    return;
  }
  const center = {
    x: geo.centerStart.x - (event.clientX - geo.pointerStart.x),
    y: geo.centerStart.y - (event.clientY - geo.pointerStart.y),
  };
  const location = worldToLatLon(center.x, center.y, geo.zoom);
  geo.lat = location.lat;
  geo.lon = location.lon;
  renderGeoMap();
});
elements.geoViewport.addEventListener("pointerup", () => {
  if (app.adjustingBoundary) {
    persist();
    markBoundarySaved("Auto-saved");
  }
  geo.dragging = false;
  elements.geoViewport.classList.remove("dragging");
});
elements.geoViewport.addEventListener("pointercancel", () => {
  geo.dragging = false;
  elements.geoViewport.classList.remove("dragging");
});
elements.geoViewport.addEventListener("wheel", (event) => {
  event.preventDefault();
  const delta = normalizedWheelDelta(event, elements.geoViewport);
  if (!delta) return;
  geoZoom(clamp(-delta / 360, -0.5, 0.5), event.clientX, event.clientY);
}, { passive: false });
elements.finishArea.addEventListener("click", finishArea);
elements.usePlot54Scale.addEventListener("click", () => applyAreaBenchmark(true));
elements.toggleSchedule.addEventListener("click", toggleSchedule);
elements.togglePlotLabels.addEventListener("click", togglePlotLabels);
elements.coordinateLoad.addEventListener("click", loadCoordinateEditor);
elements.coordinatePlot.addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadCoordinateEditor();
});
elements.coordinatePick.addEventListener("click", startCoordinatePick);
elements.coordinateUp.addEventListener("click", () => nudgeCoordinate(0, -1));
elements.coordinateDown.addEventListener("click", () => nudgeCoordinate(0, 1));
elements.coordinateLeft.addEventListener("click", () => nudgeCoordinate(-1, 0));
elements.coordinateRight.addEventListener("click", () => nudgeCoordinate(1, 0));
elements.coordinateSave.addEventListener("click", saveCoordinateEditor);
elements.coordinateRevert.addEventListener("click", revertCoordinateEditor);
[elements.coordinateSheet, elements.coordinateX, elements.coordinateY].forEach((control) => {
  control.addEventListener("change", () => showCoordinatePreview(true));
});
elements.recordSearch.addEventListener("input", (event) => renderRecords(event.target.value));
elements.locatePlot.addEventListener("click", () => locatePlot(elements.recordSearch.value));
elements.recordSearch.addEventListener("keydown", (event) => {
  if (event.key === "Enter") locatePlot(event.target.value);
});
elements.recordList.addEventListener("click", (event) => {
  const card = event.target.closest("[data-plot]");
  if (card) locatePlot(card.dataset.plot);
});
elements.recordList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest("[data-plot]");
  if (card) { event.preventDefault(); locatePlot(card.dataset.plot); }
});
elements.knownLength.addEventListener("keydown", (event) => { if (event.key === "Enter") applyCalibration(); });
window.addEventListener("resize", renderGeoMap);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setMode("pan");
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); undo(); }
});

async function initialize() {
  await loadGeoreference();
  selectSheet(0);
  loadPlotIndex();
  loadRecords();
}

initialize();
