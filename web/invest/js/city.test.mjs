import test from 'node:test';
import assert from 'node:assert/strict';
import { areaPlaces, assetCollection, assetText, bestAreas, cityHref, compareReason, linkableCities, mapStrings, outOfView, placeText, readParams } from './city.js';
import { ASSET_SOURCE, BREAKS, RAMP, baseLayers, bounds, cellCentre, clickAction } from './map.js';

// A hexagon-ish ring around (lon, lat), closed like the API sends it.
const ring = (lon, lat, r = 0.01) => {
  const pts = [[lon, lat + r], [lon + r, lat + r / 2], [lon + r, lat - r / 2], [lon, lat - r], [lon - r, lat - r / 2], [lon - r, lat + r / 2]];
  return [...pts, pts[0]];
};
const area = (id, lon, lat, props = {}) => ({
  type: 'Feature',
  geometry: { type: 'Polygon', coordinates: [ring(lon, lat)] },
  properties: { id, name: null, elig: true, rank: 1, score: 50, ...props },
});
const echo = (key, params) => (params ? `${key} ${JSON.stringify(params)}` : key);

test('readParams keeps a valid id and preset, and refuses anything else without guessing', () => {
  assert.deepEqual(readParams('?c=pune&preset=commuter'), { id: 'pune', preset: 'commuter' });
  assert.deepEqual(readParams('?c=aurangabad-mh'), { id: 'aurangabad-mh', preset: 'balanced' });
  assert.deepEqual(readParams('?c=aurangabad-mh', 'growth'), { id: 'aurangabad-mh', preset: 'growth' }, 'a missing preset takes the saved one');
  for (const bad of ['?c=pune&preset=returns', '?c=pune&preset=', '?c=pune&preset=Balanced']) {
    assert.deepEqual(readParams(bad, 'growth'), { id: 'pune', preset: null }, `${bad}: unknown, so the page goes to start.html`);
  }
  for (const bad of ['', '?c=', '?c=P', '?c=../../etc/passwd', '?c=%3Cscript%3E', '?c=pune%20x', `?c=${'a'.repeat(65)}`]) {
    assert.equal(readParams(bad).id, null, bad);
  }
});

test('cityHref encodes both parameters', () => {
  assert.equal(cityHref('nagpur', 'growth'), 'city.html?c=nagpur&preset=growth');
});

test('cellCentre ignores the closing point and bounds frames every ring', () => {
  const [lon, lat] = cellCentre(area('a', 73.8, 18.5));
  assert.ok(Math.abs(lon - 73.8) < 1e-9 && Math.abs(lat - 18.5) < 1e-9);
  const box = bounds([area('a', 73.8, 18.5), area('b', 74, 18.7)]).flat();
  [73.79, 18.49, 74.01, 18.71].forEach((want, i) => assert.ok(Math.abs(box[i] - want) < 1e-9, `${box[i]} vs ${want}`));
  assert.equal(bounds([]), null);
});

test('the ramp has one colour per score band, and the bands rise', () => {
  assert.equal(RAMP.length, BREAKS.length + 1);
  assert.ok(BREAKS.every((b, i) => i === 0 || b > BREAKS[i - 1]));
});

test('areaPlaces: a name, else the nearest named area within reach, else coordinates', () => {
  const features = [
    area('named', 73.80, 18.50, { name: 'Baner' }),
    area('close', 73.83, 18.50),            // about 3 km east of Baner
    area('far', 74.20, 18.50),              // about 42 km away: coordinates, not "near"
    area('empty', 73.84, 18.50, { name: '' }),
  ];
  const places = areaPlaces(features);
  assert.deepEqual(places.get('named'), { name: 'Baner' });
  assert.deepEqual(places.get('close'), { near: 'Baner' });
  assert.deepEqual(places.get('far'), { lat: 18.5, lon: 74.2 });
  assert.deepEqual(places.get('empty'), { near: 'Baner' });
});

test('areaPlaces picks the closer of two named areas', () => {
  const places = areaPlaces([
    area('w', 73.70, 18.5, { name: 'West' }), area('e', 73.80, 18.5, { name: 'East' }), area('x', 73.78, 18.5),
  ]);
  assert.deepEqual(places.get('x'), { near: 'East' });
});

test('placeText never shows a blank or the word null', () => {
  assert.equal(placeText({ name: 'Wakad' }, echo), 'Wakad');
  assert.equal(placeText({ near: 'Wakad' }, echo), 'inv.city.area.near {"place":"Wakad"}');
  assert.equal(placeText({ lat: 18.5, lon: 73 }, echo), 'inv.city.area.at {"lat":"18.50","lon":"73.00"}');
  assert.equal(placeText(undefined, echo), 'inv.city.area.unknown');
});

test('bestAreas: rankable only, best first, one row per name, at most ten', () => {
  const features = [
    area('c', 0, 0, { name: 'Baner', rank: 3 }),
    area('a', 0, 0, { name: 'Baner', rank: 1 }),
    area('b', 0, 0, { name: 'Tiny', rank: 2, elig: false }),
    area('d', 0, 0, { name: 'Wakad', rank: 4 }),
    ...Array.from({ length: 20 }, (_, i) => area(`n${i}`, 0, 0, { name: `N${i}`, rank: 10 + i })),
  ];
  const places = areaPlaces(features);
  const best = bestAreas(features, places);
  assert.deepEqual(best.slice(0, 3).map((f) => f.properties.id), ['a', 'd', 'n0']);
  assert.equal(best.length, 10);
  assert.ok(!best.some((f) => f.properties.id === 'b'));
});

test('bestAreas groups unnamed areas by the place they are near, keeps coordinate ones apart', () => {
  const features = [
    area('named', 73.80, 18.5, { name: 'Baner', rank: 5, elig: false }),
    area('n1', 73.82, 18.5, { rank: 1 }),
    area('n2', 73.83, 18.5, { rank: 2 }),
    area('f1', 75, 18.5, { rank: 3 }),
    area('f2', 76, 18.5, { rank: 4 }),
  ];
  assert.deepEqual(bestAreas(features, areaPlaces(features)).map((f) => f.properties.id), ['n1', 'f1', 'f2']);
});

test('assetText falls back to a label for null or blank names and refs', () => {
  assert.deepEqual(assetText('stations-metro', { name: null, mode: 'metro' }, echo), ['inv.city.asset.station_unnamed', 'inv.city.asset.metro']);
  assert.deepEqual(assetText('stations-rail', { name: 'Pune Junction', mode: 'rail' }, echo), ['Pune Junction', 'inv.city.asset.rail']);
  assert.deepEqual(assetText('bus_stops', {}, echo), ['inv.city.asset.bus_unnamed', 'inv.city.asset.bus']);
  assert.deepEqual(assetText('toll_plazas', { name: '  ' }, echo), ['inv.city.asset.toll_unnamed', 'inv.city.asset.toll']);
  assert.deepEqual(assetText('highways-building', { ref: null, kind: 'expressway_segment', status: 'under_construction' }, echo),
    ['inv.city.asset.highway_unnumbered', 'inv.city.asset.expressway, inv.city.asset.building']);
  assert.deepEqual(assetText('highways-open', { ref: 'NH 48', kind: 'nh_segment', status: 'operational' }, echo),
    ['NH 48', 'inv.city.asset.nh, inv.city.asset.open']);
  assert.throws(() => assetText('nope', {}, echo), TypeError);
});

test('compareReason names the biggest lead and the biggest lag with signed points', () => {
  const other = {
    better: [{ factor: 'metro_access', delta: 50.2 }, { factor: 'rail_access', delta: 4 }],
    worse: [{ factor: 'built_up_growth', delta: -45 }],
  };
  assert.equal(compareReason(other, echo), 'inv.factor.metro_access +50 · inv.factor.built_up_growth −45');
  assert.equal(compareReason({ better: [], worse: [{ factor: 'nh_access', delta: -3 }] }, echo), 'inv.factor.nh_access −3');
  assert.equal(compareReason({ better: [], worse: [] }, echo), '');
  assert.equal(compareReason({}, echo), '');
});

test('baseLayers drops every boundary line and the country and state labels (ADR-0007)', () => {
  const layers = [
    { id: 'water' }, { id: 'boundary_2', 'source-layer': 'boundary' }, { id: 'boundary_disputed', 'source-layer': 'boundary' },
    { id: 'label_country_1', 'source-layer': 'place' }, { id: 'label_state', 'source-layer': 'place' },
    { id: 'label_city', 'source-layer': 'place' }, { id: 'highway_major', 'source-layer': 'transportation' },
  ];
  assert.deepEqual(baseLayers(layers).map((l) => l.id), ['water', 'label_city', 'highway_major']);
});

test('baseLayers also drops a renamed country or state label, by what its filter selects', () => {
  const layers = [
    { id: 'place_country_major', 'source-layer': 'place', filter: ['==', ['get', 'class'], 'country'] },
    { id: 'place-region', 'source-layer': 'place', filter: ['all', ['==', 'class', 'state'], ['<=', 'rank', 6]] },
    { id: 'place_town', 'source-layer': 'place', filter: ['==', ['get', 'class'], 'town'] },
    { id: 'poi', 'source-layer': 'poi', filter: ['==', ['get', 'class'], 'state'] },
  ];
  assert.deepEqual(baseLayers(layers).map((l) => l.id), ['place_town', 'poi']);
});

test('clickAction: asset over hexagon, hexagon, else close the pinned popup', () => {
  assert.equal(clickAction({ id: 's' }, { id: 'a' }), 'asset');
  assert.equal(clickAction(undefined, { id: 'a' }), 'area');
  assert.equal(clickAction(undefined, undefined), 'close');
});

test('every layer toggle in city.html names a known asset layer', async () => {
  const { readFileSync } = await import('node:fs');
  const html = readFileSync(new URL('../city.html', import.meta.url), 'utf8');
  const values = [...html.matchAll(/<input type="checkbox" value="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(values.sort(), Object.keys(ASSET_SOURCE).sort());
});

test('assetCollection fails closed on anything but a FeatureCollection, and reads a null bus feed as none', () => {
  const fc = { type: 'FeatureCollection', features: [] };
  assert.equal(assetCollection({ stations: fc }, 'stations'), fc);
  assert.equal(assetCollection({ bus_stops: null }, 'bus_stops'), null);
  for (const bad of [{}, { stations: null }, { stations: { type: 'Feature' } }, { stations: { type: 'FeatureCollection' } }, null]) {
    assert.throws(() => assetCollection(bad, 'stations'), (e) => e.code === 'bad_response', JSON.stringify(bad));
  }
  assert.throws(() => assetCollection({}, 'bus_stops'), (e) => e.code === 'bad_response');
});

test('linkableCities leaves out rows whose id could not be a city id', () => {
  const rows = [{ id: 'nagpur' }, { id: '../x' }, { id: 'javascript:alert(1)' }, { id: null }, {}, { id: 'aurangabad-mh' }];
  assert.deepEqual(linkableCities(rows).map((r) => r.id), ['nagpur', 'aurangabad-mh']);
  assert.deepEqual(linkableCities(undefined), []);
});

test('outOfView is true only when part of the element is off screen', () => {
  assert.equal(outOfView({ top: 10, bottom: 500 }, 900), false);
  assert.equal(outOfView({ top: -5, bottom: 500 }, 900), true);
  assert.equal(outOfView({ top: 400, bottom: 950 }, 900), true);
});

test('mapStrings gives every MapLibre string the page uses from an inv.city key', () => {
  const strings = mapStrings((key) => key);
  assert.deepEqual(Object.keys(strings).sort(), [
    'CooperativeGesturesHandler.MacHelpText', 'CooperativeGesturesHandler.MobileHelpText', 'CooperativeGesturesHandler.WindowsHelpText',
    'Map.Title', 'NavigationControl.ZoomIn', 'NavigationControl.ZoomOut', 'Popup.Close']);
  assert.ok(Object.values(strings).every((v) => v.startsWith('inv.city.map.')));
});

test('every inv.city key the map strings use is in the English dictionary', async () => {
  const { readFileSync } = await import('node:fs');
  const en = JSON.parse(readFileSync(new URL('../../locales/en.json', import.meta.url), 'utf8'));
  for (const key of Object.values(mapStrings((k) => k))) assert.equal(typeof en[key], 'string', key);
});
