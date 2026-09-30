import test from 'node:test';
import assert from 'node:assert/strict';
import { cityHref, sampleDrivers, shortlistState, uniqueSources } from './landing.js';

test('uniqueSources keeps each distinct credit once, in order', () => {
  const ghsl = { name: 'European Commission, JRC', license: 'CC-BY-4.0', attribution: 'European Commission, JRC — GHSL GHS-BUILT-S R2023A' };
  const osm = { name: '© OpenStreetMap contributors', license: 'ODbL-1.0', attribution: '© OpenStreetMap contributors' };
  const pop = { name: 'WorldPop', license: 'CC-BY-4.0', attribution: 'WorldPop India 2020' };
  assert.deepEqual(uniqueSources([ghsl, osm, { ...ghsl, id: 'second-year' }, pop]), [
    { name: 'European Commission, JRC', license: 'CC-BY-4.0', attribution: 'GHSL GHS-BUILT-S R2023A' }, // name not repeated
    { name: '© OpenStreetMap contributors', license: 'ODbL-1.0', attribution: null }, // only the name
    { name: 'WorldPop', license: 'CC-BY-4.0', attribution: 'WorldPop India 2020' }, // no "name — " lead: kept whole
  ]);
});

test('uniqueSources keeps two sources that differ only in attribution', () => {
  const a = { name: 'ChennaiGTFS', license: 'MIT', attribution: 'metro feed' };
  assert.equal(uniqueSources([a, { ...a, attribution: 'bus feed' }]).length, 2);
});

test('uniqueSources falls back to the attribution for a missing name and drops empty entries', () => {
  assert.deepEqual(uniqueSources([
    { name: null, license: 'CC-BY-4.0', attribution: 'WorldPop' },
    { name: '  ', license: 'x', attribution: '' },
    null,
    'text',
  ]), [{ name: 'WorldPop', license: 'CC-BY-4.0', attribution: null }]);
  assert.deepEqual(uniqueSources({ sources: [] }), []);
  assert.deepEqual(uniqueSources(undefined), []);
});

test('sampleDrivers shows a different factor on each row while one is left', () => {
  const d = (factor) => ({ factor, points: 1 });
  const cities = [
    { drivers: [d('nh_access'), d('built_up_growth')] },
    { drivers: [d('nh_access'), d('built_up_growth'), d('metro_access')] },
    { drivers: [d('nh_access'), d('rail_access')] },
    { drivers: [d('nh_access')] },          // every factor already shown: its top driver
    { drivers: [] },
    { drivers: null },
  ];
  assert.deepEqual(sampleDrivers(cities).map((x) => x?.factor),
    ['nh_access', 'built_up_growth', 'rail_access', 'nh_access', undefined, undefined]);
});

test('cityHref links only ids the city page accepts', () => {
  assert.equal(cityHref('pune'), 'city.html?c=pune&preset=balanced');
  for (const bad of ['../etc/passwd', 'Pune', 'a', '<script>', null, 7]) assert.equal(cityHref(bad), null, String(bad));
});

test('shortlistState: state target wins, a city uses its own state, home state is the fallback', () => {
  const p = (target, homeState = null) => ({ target, homeState });
  assert.equal(shortlistState(p({ type: 'state', code: 'KA' }, 'MH')), 'KA');
  assert.equal(shortlistState(p({ type: 'city', id: 'pune' }, 'KA'), 'MH'), 'MH');
  assert.equal(shortlistState(p({ type: 'city', id: 'pune' }, 'KA'), null), 'KA');
  assert.equal(shortlistState(p(null, null), null), null);
});
