// The city map: H3 areas as a filled layer coloured by score, optional asset layers (stations, bus stops,
// highways, toll plazas), a popup per click. Only OpenStreetMap base tiles are fetched from outside
// (OpenFreeMap "positron"); if that style cannot be reached the areas still draw on a plain background.
// Popups are DOM nodes, never HTML strings. MapLibre itself is a global from the page's script tag.

import { boundsOf, classOf, quantileBreaks, ringCentroid } from './areas.js';

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
const STYLE_TIMEOUT_MS = 4000;
const LOAD_TIMEOUT_MS = 12000;
const PLAIN_STYLE = { version: 8, sources: {}, layers: [{ id: 'plain-bg', type: 'background', paint: { 'background-color': '#EFEDE6' } }] };

// Five steps of one hue, light to dark (the same teal as the brand). Fills only, never text.
export const RAMP = ['#E2EEF0', '#A9CCD2', '#6BA5AF', '#2F7C89', '#0E5A66'];

const ASSET_STYLES = {
  highways: { type: 'line', paint: { 'line-color': ['match', ['get', 'status'], 'under_construction', '#D97706', '#14202B'], 'line-width': 2.5, 'line-opacity': 0.85 } },
  stations: { type: 'circle', paint: { 'circle-radius': 5, 'circle-color': ['match', ['get', 'mode'], 'metro', '#7B3FA0', '#3A6EA5'], 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 1.5 } },
  bus_stops: { type: 'circle', minzoom: 11, paint: { 'circle-radius': 2.5, 'circle-color': '#3A6EA5', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 0.75 } },
  toll_plazas: { type: 'circle', paint: { 'circle-radius': 5, 'circle-color': '#E08A1E', 'circle-stroke-color': '#14202B', 'circle-stroke-width': 1.5 } },
};

export const mapAvailable = () => typeof globalThis.maplibregl?.Map === 'function';

async function pickStyle(fetchImpl = fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), STYLE_TIMEOUT_MS);
  try {
    const response = await fetchImpl(STYLE_URL, { signal: controller.signal });
    return response.ok ? STYLE_URL : PLAIN_STYLE;
  } catch {
    return PLAIN_STYLE;
  } finally {
    clearTimeout(timer);
  }
}

// Creates the map inside `container` and resolves with a controller once the style has loaded.
//   areas: GeoJSON FeatureCollection (each feature has properties.id and properties.score)
//   popupContent(properties) -> Node, shown when an area is clicked
//   onSelect(id) is called when an area is clicked
export async function createAreaMap(container, areas, { popupContent, onSelect } = {}) {
  if (!mapAvailable()) throw new Error('maplibre-unavailable');
  const { maplibregl } = globalThis;
  const style = await pickStyle();
  const map = new maplibregl.Map({
    container, style, attributionControl: false, dragRotate: false, pitchWithRotate: false,
    center: [78.9, 22.5], zoom: 4, maxZoom: 16,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({ customAttribution: '© OpenStreetMap contributors', compact: false }), 'bottom-right');
  // Our layers need the style, not the base tiles, so the areas can draw before the tiles arrive.
  // Only a style that never loads is an error.
  await Promise.race([
    new Promise((resolve) => map.once('style.load', resolve)),
    new Promise((_, reject) => setTimeout(() => reject(new Error('map load timeout')), LOAD_TIMEOUT_MS)),
  ]);

  const features = areas.features ?? [];
  const byId = new Map(features.map((f) => [f.properties.id, f]));
  const breaks = quantileBreaks(features.map((f) => f.properties.score));
  const fillColor = ['step', ['get', 'score'], RAMP[0], ...breaks.flatMap((b, i) => [b, RAMP[i + 1]])];

  map.addSource('areas', { type: 'geojson', data: areas });
  map.addLayer({ id: 'areas-fill', type: 'fill', source: 'areas', paint: { 'fill-color': fillColor, 'fill-opacity': ['case', ['boolean', ['get', 'elig'], false], 0.8, 0.35] } });
  map.addLayer({ id: 'areas-line', type: 'line', source: 'areas', paint: { 'line-color': '#FFFFFF', 'line-width': 0.75 } });
  map.addLayer({ id: 'areas-selected', type: 'line', source: 'areas', filter: ['==', ['get', 'id'], ''], paint: { 'line-color': '#E08A1E', 'line-width': 3 } });

  let popup = null;
  const show = (lngLat, node) => {
    popup?.remove();
    popup = new maplibregl.Popup({ className: 'inv-popup', maxWidth: '20rem', closeButton: true }).setLngLat(lngLat).setDOMContent(node).addTo(map);
  };
  const select = (id, lngLat) => {
    const feature = byId.get(id);
    if (!feature) return;
    map.setFilter('areas-selected', ['==', ['get', 'id'], id]);
    if (popupContent) show(lngLat, popupContent(feature.properties));
    onSelect?.(id);
  };
  const assetLayerIds = () => Object.keys(ASSET_STYLES).map((l) => `asset-${l}`).filter((l) => map.getLayer(l));
  map.on('click', 'areas-fill', (e) => {
    // asset layers sit above the areas and have their own popups; do not also open an area popup
    const layers = assetLayerIds();
    if (layers.length && map.queryRenderedFeatures(e.point, { layers }).length) return;
    select(e.features[0].properties.id, e.lngLat);
  });
  map.on('mouseenter', 'areas-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'areas-fill', () => { map.getCanvas().style.cursor = ''; });

  const box = boundsOf(features);
  if (box) map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 32, duration: 0 });

  return {
    breaks,
    // the fill colour a score gets, for the legend
    colorOf: (score) => RAMP[Math.min(classOf(score, breaks), RAMP.length - 1)],
    flyToArea(id) {
      const feature = byId.get(id);
      const centre = feature && ringCentroid(feature.geometry);
      if (!centre) return;
      map.flyTo({ center: centre, zoom: Math.max(map.getZoom(), 12), duration: 600 });
      select(id, centre);
    },
    // Adds (once) or shows/hides one asset layer. `data` is needed only the first time.
    setAssetLayer(name, visible, data) {
      const id = `asset-${name}`;
      if (!map.getLayer(id)) {
        if (!data) return false;
        map.addSource(id, { type: 'geojson', data });
        map.addLayer({ id, source: id, ...ASSET_STYLES[name] });
        map.on('click', id, (e) => {
          const p = e.features[0].properties;
          const text = document.createElement('div');
          text.className = 'inv-popup__title';
          text.textContent = p.name || p.ref || name;
          show(e.lngLat, text);
        });
        map.on('mouseenter', id, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; });
      }
      map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
      return true;
    },
    hasAssetLayer: (name) => Boolean(map.getLayer(`asset-${name}`)),
    resize: () => map.resize(),
    destroy: () => map.remove(),
  };
}
