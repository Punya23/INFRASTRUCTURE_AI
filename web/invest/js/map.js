// The city map: MapLibre GL (the global maplibregl from unpkg) with the area hexagons and the
// optional infrastructure layers. This file knows MapLibre and nothing about wording: the page
// passes in a function that builds each popup's content, so every sentence stays in city.js.
//
// The pure helpers (cellCentre, bounds, baseLayers) run in Node for the tests.

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
const STYLE_TIMEOUT_MS = 6000;
const ATTRIBUTION = '© OpenStreetMap contributors';

// Five equal score bands, light to dark teal, ending past the brand teal. Fixed 20-point bands (not
// quantiles), so a colour means the same score in every city and under every preset. MapLibre needs
// literal colours, so the ramp lives here and the legend takes its swatches from the same array.
export const BREAKS = [20, 40, 60, 80];
export const RAMP = ['#DCEDEA', '#A4D1CC', '#62A9AB', '#2A7A84', '#0A4550'];
const NO_SCORE = '#C8C5BB';     // --border-strong: a cell without a score (not expected in the data)
const PLAIN_BG = '#EFEDE6';     // --surface-sunken: the background when the base map cannot load
const INK = '#14202B';          // --text-primary: selected-cell outline, station rings
const SAFFRON = '#E08A1E';      // --accent-saffron: highways under construction
const TEAL = '#0E5A66';         // --brand-teal

// Centre of an H3 cell: the mean of its ring's corners (the closing point is not counted twice).
export function cellCentre(feature) {
  const ring = feature.geometry.coordinates[0];
  const corners = ring.length > 1 && ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1]
    ? ring.slice(0, -1) : ring;
  const sum = corners.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
  return [sum[0] / corners.length, sum[1] / corners.length];
}

// [[west, south], [east, north]] around every polygon, or null when there is nothing to frame.
export function bounds(features) {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const f of features) {
    for (const [x, y] of f.geometry.coordinates[0]) {
      if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y;
    }
  }
  return Number.isFinite(w) ? [[w, s], [e, n]] : null;
}

// ADR-0007: national and state outlines come only from the Survey of India-compliant layer, so the
// base map's OSM boundary lines are removed, and with them the country and state labels (the country
// labels also filter on a rank that is often null, which fills the console with warnings).
export const baseLayers = (layers) => layers.filter((layer) =>
  layer['source-layer'] !== 'boundary' && !/^label_(country|state)/.test(layer.id));

// The OpenFreeMap style, or a plain background when it cannot be fetched in time (offline, blocked,
// or the service is down). The hexagons and the attribution draw either way.
async function loadStyle() {
  const plain = { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': PLAIN_BG } }] };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), STYLE_TIMEOUT_MS);
  try {
    const response = await fetch(STYLE_URL, { signal: controller.signal });
    if (!response.ok) throw new Error(`style HTTP ${response.status}`);
    const style = await response.json();
    if (!Array.isArray(style?.layers)) throw new Error('style has no layers');
    return { style: { ...style, layers: baseLayers(style.layers) }, fallback: false };
  } catch (error) {
    console.warn('[invest] base map style unavailable, using a plain background:', error.message);
    return { style: plain, fallback: true };
  } finally {
    clearTimeout(timer);
  }
}

// Asset layers: [layer id, source id, MapLibre layer spec]. Toggles in the page name these ids.
const ASSET_LAYERS = [
  ['highways-open', 'highways', { type: 'line', filter: ['==', ['get', 'status'], 'operational'], paint: { 'line-color': TEAL, 'line-width': 3 } }],
  ['highways-building', 'highways', { type: 'line', filter: ['!=', ['get', 'status'], 'operational'], paint: { 'line-color': SAFFRON, 'line-width': 3, 'line-dasharray': [2, 1.5] } }],
  ['bus_stops', 'bus_stops', { type: 'circle', paint: { 'circle-radius': 2.5, 'circle-color': INK, 'circle-opacity': 0.7 } }],
  ['stations-rail', 'stations', { type: 'circle', filter: ['==', ['get', 'mode'], 'rail'], paint: { 'circle-radius': 5, 'circle-color': '#FFFFFF', 'circle-stroke-color': INK, 'circle-stroke-width': 2.5 } }],
  ['stations-metro', 'stations', { type: 'circle', filter: ['==', ['get', 'mode'], 'metro'], paint: { 'circle-radius': 6, 'circle-color': INK, 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2 } }],
  ['toll_plazas', 'toll_plazas', { type: 'circle', paint: { 'circle-radius': 5, 'circle-color': SAFFRON, 'circle-stroke-color': INK, 'circle-stroke-width': 1.5 } }],
];
export const ASSET_SOURCE = Object.fromEntries(ASSET_LAYERS.map(([id, source]) => [id, source]));

// Builds the map in the container element. Resolves to a controller once the style has loaded, or rejects when
// MapLibre is missing (the script did not load) or cannot start (no WebGL).
//   popupContent(kind, id | properties): a DOM node. kind 'area' gets the area id; kind is otherwise
//   the asset layer id and gets the feature's properties.
export async function createMap(container, { popupContent }) {
  const gl = globalThis.maplibregl;
  if (!gl) throw new Error('MapLibre did not load');
  const { style, fallback } = await loadStyle();
  const map = new gl.Map({
    container, style, center: [78.9, 22.5], zoom: 4, minZoom: 3, maxZoom: 16,
    // the map sits inside a scrolling page: two fingers (or ctrl + wheel) move it, so a swipe or a
    // wheel over it still scrolls the page instead of trapping the visitor
    attributionControl: false, cooperativeGestures: true,
  });
  // compact: false keeps the attribution text on screen at every width
  map.addControl(new gl.AttributionControl({ compact: false, customAttribution: ATTRIBUTION }), 'bottom-right');
  map.addControl(new gl.NavigationControl({ showCompass: false }), 'top-right');
  // The style is already in hand, so 'load' comes; a failed tile or sprite only logs and never blocks it.
  await new Promise((resolve) => map.once('load', resolve));

  const fillColour = ['step', ['coalesce', ['get', 'score'], -1], NO_SCORE, 0, RAMP[0],
    ...BREAKS.flatMap((b, i) => [b, RAMP[i + 1]])];
  map.addSource('areas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, promoteId: 'id' });
  map.addLayer({ id: 'areas-fill', type: 'fill', source: 'areas', paint: {
    'fill-color': fillColour,
    // cells with too few residents to rank stay visible but step back
    'fill-opacity': ['case', ['get', 'elig'], 0.78, 0.3],
  } });
  map.addLayer({ id: 'areas-line', type: 'line', source: 'areas', paint: { 'line-color': '#FFFFFF', 'line-width': 0.6, 'line-opacity': 0.8 } });
  map.addLayer({ id: 'areas-selected', type: 'line', source: 'areas', paint: {
    'line-color': INK, 'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 3, 0],
  } });

  const hover = new gl.Popup({ closeButton: false, closeOnClick: false, focusAfterOpen: false, className: 'city-popup', maxWidth: '18rem', offset: 8 });
  const pinned = new gl.Popup({ closeOnClick: true, focusAfterOpen: false, className: 'city-popup', maxWidth: '18rem', offset: 8 });
  let hoverId = null;
  let selectedId = null;

  const select = (id) => {
    if (selectedId != null) map.setFeatureState({ source: 'areas', id: selectedId }, { selected: false });
    selectedId = id;
    if (id != null) map.setFeatureState({ source: 'areas', id }, { selected: true });
  };
  pinned.on('close', () => select(null));

  const assetIds = ASSET_LAYERS.map(([id]) => id);
  const loadedAssets = () => assetIds.filter((id) => map.getLayer(id));

  map.on('mousemove', 'areas-fill', (e) => {
    const id = e.features[0]?.properties.id;
    map.getCanvas().style.cursor = 'pointer';
    if (id !== hoverId) {
      hoverId = id;
      hover.setDOMContent(popupContent('area', id));
    }
    hover.setLngLat(e.lngLat).addTo(map);
  });
  map.on('mouseleave', 'areas-fill', () => {
    hoverId = null;
    map.getCanvas().style.cursor = '';
    hover.remove();
  });
  map.on('click', (e) => {
    // an asset under the pointer wins over the hexagon beneath it
    const [asset] = map.queryRenderedFeatures(e.point, { layers: loadedAssets() });
    if (asset) {
      hover.remove();
      pinned.setLngLat(e.lngLat).setDOMContent(popupContent(asset.layer.id, asset.properties)).addTo(map);
      return;
    }
    const [area] = map.queryRenderedFeatures(e.point, { layers: ['areas-fill'] });
    if (!area) return;
    hover.remove();
    pinned.setLngLat(e.lngLat).setDOMContent(popupContent('area', area.properties.id)).addTo(map);
    select(area.properties.id);
  });

  return {
    fallback,
    // Replaces the hexagons; frames them the first time only, so a preset switch keeps the view.
    setAreas(features, { fit }) {
      hover.remove();
      pinned.remove();
      map.getSource('areas').setData({ type: 'FeatureCollection', features });
      const box = fit && bounds(features);
      if (box) map.fitBounds(box, { padding: 24, animate: false });
    },
    // Flies to one area and opens its popup: the path from the keyboard list into the map.
    showArea(feature) {
      const centre = cellCentre(feature);
      const reduce = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      map.flyTo({ center: centre, zoom: Math.max(map.getZoom(), 12), essential: false, animate: !reduce });
      hover.remove();
      pinned.setLngLat(centre).setDOMContent(popupContent('area', feature.properties.id)).addTo(map);
      select(feature.properties.id);
    },
    // Adds a source's data once; its layers start hidden.
    addAssets(source, collection) {
      if (map.getSource(source)) return;
      map.addSource(source, { type: 'geojson', data: collection ?? { type: 'FeatureCollection', features: [] } });
      for (const [id, src, spec] of ASSET_LAYERS) {
        if (src !== source) continue;
        map.addLayer({ id, source, layout: { visibility: 'none' }, ...spec });
        map.on('mouseenter', id, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; });
      }
    },
    hasAssets: (source) => Boolean(map.getSource(source)),
    setVisible(layerId, visible) {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
    },
    closePopups() { hover.remove(); pinned.remove(); },
  };
}
