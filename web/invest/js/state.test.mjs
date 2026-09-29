import test from 'node:test';
import assert from 'node:assert/strict';
import { bestAreaLine, factorsUsed, gapChip, listMode, meterView, readParams, whyChips } from './state.js';

test('readParams accepts a state code with a known or missing preset', () => {
  assert.deepEqual(readParams('?s=MH&preset=commuter'), { code: 'MH', preset: 'commuter' });
  assert.deepEqual(readParams('?s=GA'), { code: 'GA', preset: 'balanced' });
  assert.deepEqual(readParams('?s=GA', 'growth'), { code: 'GA', preset: 'growth' });
});

test('readParams rejects anything that is not a state code or a preset', () => {
  for (const search of ['', '?s=', '?s=mh', '?s=MHA', '?s=M', '?s=../x', '?s=MH&preset=', '?s=MH&preset=cheap', '?preset=balanced']) {
    assert.equal(readParams(search), null, search);
  }
});

test('listMode tells none, fewer than five, and five or more apart', () => {
  assert.equal(listMode(0, 0), 'empty');
  assert.equal(listMode(1, 1), 'few');
  assert.equal(listMode(4, 4), 'few');
  assert.equal(listMode(5, 5), 'full');
  assert.equal(listMode(26, 5), 'full');
  assert.equal(listMode(undefined, 0), 'empty'); // a broken total never claims cities that were not sent
});

const META = { factors: [{ id: 'nh_access', bands: [[0, 100], [25, 0]] }] };

test('whyChips keeps at most three, in order, and drops unmeasured drivers', () => {
  const drivers = [
    { factor: 'nh_access', value: 1, share: 1, band_km: 10 },
    { factor: 'rail_access', value: null, share: null, band_km: null },
    { factor: 'built_up_growth', value: 5.8 },
    { factor: 'road_strength', value: 1.1 },
    { factor: 'metro_access', value: 1.5 },
  ];
  assert.deepEqual(whyChips({ drivers }, META).map((c) => c.key),
    ['inv.why.nh_access.share', 'inv.why.built_up_growth', 'inv.why.road_strength']);
  assert.deepEqual(whyChips({}, META), []);
});

test('gapChip explains the first gap and is null without one', () => {
  const city = { gaps: [{ factor: 'metro_access', value: 192.9, share: 0, band_km: 2 }] };
  assert.deepEqual(gapChip(city, META), { key: 'inv.gap.metro_access.share', params: { pct: 0, km: 2 } });
  assert.equal(gapChip({ gaps: [] }, META), null);
  assert.equal(gapChip({}, META), null);
});

test('bestAreaLine names the area, falls back to the city for an unnamed one, and hides when absent', () => {
  assert.deepEqual(bestAreaLine({ name: 'Pune', best_area: { name: 'Ajmera', score: 92.1 } }),
    { key: 'inv.state.bestArea', params: { name: 'Ajmera', score: '92' } });
  assert.deepEqual(bestAreaLine({ name: 'Nagpur', best_area: { name: null, score: 90.7 } }),
    { key: 'inv.state.bestAreaUnnamed', params: { city: 'Nagpur', score: '91' } });
  assert.equal(bestAreaLine({ name: 'X', best_area: null }), null);
  assert.equal(bestAreaLine({ name: 'X' }), null);
});

test('meterView shows a dash and an empty fill for an unobserved value, never 0', () => {
  assert.deepEqual(meterView(71.4), { unknown: false, value: 71.4, text: '71' });
  assert.deepEqual(meterView(0), { unknown: false, value: 0, text: '0' });
  assert.deepEqual(meterView(null), { unknown: true, value: 0, text: '—' });
  assert.deepEqual(meterView(NaN), { unknown: true, value: 0, text: '—' });
  assert.equal(meterView(140).value, 100);
});

test('factorsUsed reports N of M only when coverage is below 1 and never N = M', () => {
  assert.equal(factorsUsed(1, 5), null);
  assert.equal(factorsUsed(undefined, 5), null);
  assert.equal(factorsUsed(0.8, 0), null);
  assert.deepEqual(factorsUsed(0.85, 5), { n: 4, m: 5 });
  assert.deepEqual(factorsUsed(0.98, 5), { n: 4, m: 5 });
  assert.deepEqual(factorsUsed(0, 5), { n: 0, m: 5 });
});
