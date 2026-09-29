// The city map: MapLibre GL (the global maplibregl from unpkg) with the area hexagons and the
// optional infrastructure layers. This file knows MapLibre and nothing about wording: the page
// passes in a function that builds each popup's content, so every sentence stays in city.js.
//
// The pure helpers (cellCentre, bounds, baseLayers) run in Node for the tests.

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
const STYLE_TIMEOUT_MS = 6000;
const LOAD_TIMEOUT_MS = 15000;
const ATTRIBUTION = '© OpenStreetMap contributors';

// Five equal score bands, light to dark teal, ending past the brand teal. Fixed 20-point bands (not
// quantiles), so a colour means the same score in every city and under every preset. MapLibre needs
// literal colours, so the ramp lives here and the legend takes its swatches from the same array.
export const BREAKS = [20, 40, 60, 80];
// Colours in between the tokens: invest.css has no five-step ramp, so it is defined here only.
export const RAMP = ['#DCEDEA', '#A4D1CC', '#62A9AB', '#2A7A84', '#0A4550'];

// Every other map colour is a design token from invest.css, read once when the map is built. A missing
// token throws, so the page shows "map unavailable" instead of drawing in an invalid colour.
const TOKENS = { ink: '--text-primary', teal: '--brand-teal', saffron: '--accent-saffron', paper: '--surface', plain: '--surface-sunken', none: '--border-strong' };
function readColours() {
  const css = getComputedStyle(document.documentElement);
  return Object.fromEntries(Object.entries(TOKENS).map(([name, token]) => {
    const value = css.getPropertyValue(token).trim();
    if (!value) throw new Error(`design token ${token} is not defined`);
    return [name, value];
  }));
}

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
// labels also filter on a rank that is often null, which fills the console with warnings). Labels are
// matched both by id and by what their filter selects, so a renamed layer is still caught.
const COUNTRY_OR_STATE = /"(country|state)"/;
export const baseLayers = (layers) => layers.filter((layer) => {
  if (layer['source-layer'] === 'boundary') return false;
  if (/^label_(country|state)/.test(layer.id)) return false;
  return !(layer['source-layer'] === 'place' && COUNTRY_OR_STATE.test(JSON.stringify(layer.filter ?? null)));
});

// The OpenFreeMap style, or a plain background when it cannot be fetched in time (offline, blocked,
// or the service is down). The hexagons and the attribution draw either way.
const plainStyle = (colours) => ({ version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': colours.plain } }] });

async function loadStyle(colours) {
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
    return { style: plainStyle(colours), fallback: true };
  } finally {
    clearTimeout(timer);
  }
}

// Asset layer id -> the /assets collection it draws. Toggles in the page name these ids.
export const ASSET_SOURCE = {
  'highways-open': 'highways', 'highways-building': 'highways', bus_stops: 'bus_stops',
  'stations-rail': 'stations', 'stations-metro': 'stations', toll_plazas: 'toll_plazas',
};

// [layer id, MapLibre layer spec], bottom to top.
const assetLayers = (c) => [
  ['highways-open', { type: 'line', filter: ['==', ['get', 'status'], 'operational'], paint: { 'line-color': c.teal, 'line-width': 3 } }],
  ['highways-building', { type: 'line', filter: ['!=', ['get', 'status'], 'operational'], paint: { 'line-color': c.saffron, 'line-width': 3, 'line-dasharray': [2, 1.5] } }],
  ['bus_stops', { type: 'circle', paint: { 'circle-radius': 2.5, 'circle-color': c.ink, 'circle-opacity': 0.7 } }],
  ['stations-rail', { type: 'circle', filter: ['==', ['get', 'mode'], 'rail'], paint: { 'circle-radius': 5, 'circle-color': c.paper, 'circle-stroke-color': c.ink, 'circle-stroke-width': 2.5 } }],
  ['stations-metro', { type: 'circle', filter: ['==', ['get', 'mode'], 'metro'], paint: { 'circle-radius': 6, 'circle-color': c.ink, 'circle-stroke-color': c.paper, 'circle-stroke-width': 2 } }],
  ['toll_plazas', { type: 'circle', paint: { 'circle-radius': 5, 'circle-color': c.saffron, 'circle-stroke-color': c.ink, 'circle-stroke-width': 1.5 } }],
];

// What a click on the map does: an asset under the pointer wins over the hexagon beneath it, and a
// click on neither closes the pinned popup.
export const clickAction = (asset, area) => (asset ? 'asset' : area ? 'area' : 'close');

// Resolves when the map has loaded. The timer runs only while the page is visible, because a browser
// does not render a background tab and a map opened there loads when it is shown.
function whenLoaded(map, ms) {
  return new Promise((resolve, reject) => {
    let timer;
    const arm = () => {
      clearTimeout(timer);
      if (!document.hidden) timer = setTimeout(() => { stop(); reject(new Error(`map did not load within ${ms} ms`)); }, ms);
    };
    const stop = () => { clearTimeout(timer); document.removeEventListener('visibilitychange', arm); };
    document.addEventListener('visibilitychange', arm);
    map.once('load', () => { stop(); resolve(); });
    arm();
  });
}

// Builds the map in the container element. Resolves to a controller once the map has loaded, or
// rejects when MapLibre is missing (the script did not load), cannot start (no WebGL) or does not load
// in time even on the plain background.
//   popupContent(kind, id | properties): a DOM node. kind 'area' gets the area id; kind is otherwise
//   the asset layer id and gets the feature's properties.
//   strings(): MapLibre's own UI text (its locale keys), in the page language; read again by relabel().
export async function createMap(container, { popupContent, strings }) {
  const gl = globalThis.maplibregl;
  if (!gl) throw new Error('MapLibre did not load');
  const colours = readColours();
  let { style, fallback } = await loadStyle(colours);
  const build = (mapStyle) => {
    const built = new gl.Map({
      container, style: mapStyle, center: [78.9, 22.5], zoom: 4, minZoom: 3, maxZoom: 16, locale: strings(),
      // the map sits inside a scrolling page: two fingers (or ctrl + wheel) move it, so a swipe or a
      // wheel over it still scrolls the page instead of trapping the visitor
      attributionControl: false, cooperativeGestures: true,
    });
    // compact: false keeps the attribution text on screen at every width
    built.addControl(new gl.AttributionControl({ compact: false, customAttribution: ATTRIBUTION }), 'bottom-right');
    built.addControl(new gl.NavigationControl({ showCompass: false }), 'top-right');
    return built;
  };
  let map = build(style);
  try {
    await whenLoaded(map, LOAD_TIMEOUT_MS);
  } catch (error) {
    map.remove();
    if (fallback) throw error;
    // the base map's tiles, sprites or fonts stalled: start again on the plain background
    console.warn('[invest] base map did not load, using a plain background:', error.message);
    fallback = true;
    map = build(plainStyle(colours));
    await whenLoaded(map, LOAD_TIMEOUT_MS);
  }

  const fillColour = ['step', ['coalesce', ['get', 'score'], -1], colours.none, 0, RAMP[0],
    ...BREAKS.flatMap((b, i) => [b, RAMP[i + 1]])];
  map.addSource('areas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, promoteId: 'id' });
  map.addLayer({ id: 'areas-fill', type: 'fill', source: 'areas', paint: {
    'fill-color': fillColour,
    // cells with too few residents to rank stay visible but step back
    'fill-opacity': ['case', ['get', 'elig'], 0.78, 0.3],
  } });
  map.addLayer({ id: 'areas-line', type: 'line', source: 'areas', paint: { 'line-color': colours.paper, 'line-width': 0.6, 'line-opacity': 0.8 } });
  map.addLayer({ id: 'areas-selected', type: 'line', source: 'areas', paint: {
    'line-color': colours.ink, 'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 3, 0],
  } });

  const hover = new gl.Popup({ closeButton: false, closeOnClick: false, focusAfterOpen: false, className: 'city-popup', maxWidth: '18rem', offset: 8 });
  // closeOnClick stays off: the click handler below decides, otherwise MapLibre's own close runs after
  // the handler has reopened the popup and every second click on the map closes it
  const pinned = new gl.Popup({ closeOnClick: false, focusAfterOpen: false, className: 'city-popup', maxWidth: '18rem', offset: 8 });
  let hoverId = null;
  let selectedId = null;

  const select = (id) => {
    if (selectedId != null) map.setFeatureState({ source: 'areas', id: selectedId }, { selected: false });
    selectedId = id;
    if (id != null) map.setFeatureState({ source: 'areas', id }, { selected: true });
  };
  pinned.on('close', () => select(null));

  const loadedAssets = () => Object.keys(ASSET_SOURCE).filter((id) => map.getLayer(id));

  // MapLibre reads its locale once; these put the current language on what it has already drawn.
  const relabel = () => {
    const t = strings();
    const set = (selector, apply) => container.querySelectorAll(selector).forEach(apply);
    set('.maplibregl-ctrl-zoom-in', (b) => { b.title = t['NavigationControl.ZoomIn']; b.setAttribute('aria-label', t['NavigationControl.ZoomIn']); });
    set('.maplibregl-ctrl-zoom-out', (b) => { b.title = t['NavigationControl.ZoomOut']; b.setAttribute('aria-label', t['NavigationControl.ZoomOut']); });
    set('.maplibregl-popup-close-button', (b) => b.setAttribute('aria-label', t['Popup.Close']));
    set('.maplibregl-desktop-message', (d) => { d.textContent = t[navigator.userAgent.includes('Mac') ? 'CooperativeGesturesHandler.MacHelpText' : 'CooperativeGesturesHandler.WindowsHelpText']; });
    set('.maplibregl-mobile-message', (d) => { d.textContent = t['CooperativeGesturesHandler.MobileHelpText']; });
    map.getCanvas().setAttribute('aria-label', t['Map.Title']);
  };
  const pin = (lngLat, content) => {
    pinned.setLngLat(lngLat).setDOMContent(content);
    if (!pinned.isOpen()) pinned.addTo(map);
    relabel();
  };

  map.on('mousemove', 'areas-fill', (e) => {
    const id = e.features[0]?.properties.id;
    map.getCanvas().style.cursor = 'pointer';
    if (id !== hoverId) {
      hoverId = id;
      hover.setDOMContent(popupContent('area', id));
    }
    hover.setLngLat(e.lngLat);
    if (!hover.isOpen()) hover.addTo(map);
  });
  map.on('mouseleave', 'areas-fill', () => {
    hoverId = null;
    map.getCanvas().style.cursor = '';
    hover.remove();
  });
  map.on('click', (e) => {
    const [asset] = map.queryRenderedFeatures(e.point, { layers: loadedAssets() });
    const [area] = map.queryRenderedFeatures(e.point, { layers: ['areas-fill'] });
    hover.remove();
    switch (clickAction(asset, area)) {
      case 'asset':
        select(null);
        pin(e.lngLat, popupContent(asset.layer.id, asset.properties));
        break;
      case 'area':
        pin(e.lngLat, popupContent('area', area.properties.id));
        select(area.properties.id);
        break;
      default:
        pinned.remove();
    }
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
      pin(centre, popupContent('area', feature.properties.id));
      select(feature.properties.id);
    },
    // Adds a collection once (a FeatureCollection; the page checks it); its layers start hidden.
    addAssets(source, collection) {
      if (map.getSource(source)) return;
      map.addSource(source, { type: 'geojson', data: collection });
      for (const [id, spec] of assetLayers(colours)) {
        if (ASSET_SOURCE[id] !== source) continue;
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
    relabel,
  };
}
