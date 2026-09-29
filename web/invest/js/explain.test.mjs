import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { explain } from './explain.js';
import { tt } from './format.js';

const meta = { factors: [
  { id: 'metro_access', bands: [[0,100],[1,90],[2,70],[5,30],[10,0]] },
  { id: 'nh_access', bands: [[0,100],[2,90],[5,70],[10,40],[25,0]] },
  { id: 'road_strength', bands: [[0,0],[3,100]] },
  { id: 'built_up_growth', bands: [[0,0],[40,100]] },
] };

test('share wins when the city summary has one', () => {
  assert.deepEqual(
    explain('why', { factor: 'metro_access', value: 3.1, unit: 'km', share: 0.22, band_km: 2 }, meta),
    { key: 'inv.why.metro_access.share', params: { pct: 22, km: 2 } });
});
test('beyond the last knot reads as far', () => {
  assert.deepEqual(explain('gap', { factor: 'metro_access', value: 40.2, unit: 'km', share: null, band_km: null }, meta),
    { key: 'inv.gap.metro_access.far', params: { km: 10 } });
});
test('near value is rounded to one decimal', () => {
  assert.deepEqual(explain('why', { factor: 'nh_access', value: 1.84, unit: 'km' }, meta),
    { key: 'inv.why.nh_access.near', params: { km: 1.8 } });
});
test('unobserved is unknown, never zero', () => {
  assert.equal(explain('why', { factor: 'road_strength', value: null }, meta).key, 'inv.why.road_strength.unknown');
  assert.equal(explain('why', { factor: 'built_up_growth', value: null }, meta).key, 'inv.why.built_up_growth.unknown');
});
test('growth and roads', () => {
  assert.deepEqual(explain('why', { factor: 'built_up_growth', value: 24.4 }, meta), { key: 'inv.why.built_up_growth', params: { pp: 24 } });
  // exactly one point is singular in English ("1 percentage point"); 0 and decimals that round elsewhere are not
  assert.deepEqual(explain('why', { factor: 'built_up_growth', value: 1.2 }, meta), { key: 'inv.why.built_up_growth.one', params: { pp: 1 } });
  assert.equal(explain('gap', { factor: 'built_up_growth', value: 0.8 }, meta).key, 'inv.gap.built_up_growth.one');
  assert.equal(explain('gap', { factor: 'built_up_growth', value: 0.2 }, meta).key, 'inv.gap.built_up_growth');
  assert.equal(explain('gap', { factor: 'built_up_growth', value: 2 }, meta).key, 'inv.gap.built_up_growth');
  assert.deepEqual(explain('why', { factor: 'road_strength', value: 2.24 }, meta), { key: 'inv.why.road_strength', params: { km: 2.2 } });
});

// Edge cases beyond the brief's examples.
test('a distance factor with no value and no share is unknown, whatever the kind', () => {
  for (const kind of ['why', 'gap']) {
    assert.deepEqual(explain(kind, { factor: 'rail_access', value: null, share: null, band_km: null }, meta),
      { key: `inv.${kind}.rail_access.unknown`, params: {}, unknown: true });
  }
});
test('NaN and undefined are unobserved too, not "NaN km"', () => {
  assert.equal(explain('why', { factor: 'nh_access', value: NaN }, meta).key, 'inv.why.nh_access.unknown');
  assert.equal(explain('gap', { factor: 'built_up_growth' }, meta).key, 'inv.gap.built_up_growth.unknown');
});
test('a share of exactly zero is an observation, not a missing value', () => {
  assert.deepEqual(explain('gap', { factor: 'metro_access', value: 12, share: 0, band_km: 2 }, meta),
    { key: 'inv.gap.metro_access.none', params: { km: 2 } });
  assert.deepEqual(explain('gap', { factor: 'nh_access', value: 12, share: 0.004, band_km: 10 }, meta),
    { key: 'inv.gap.nh_access.none', params: { km: 10 } }); // rounds to 0%: same wording, never "Only 0%"
  assert.deepEqual(explain('gap', { factor: 'nh_access', value: 12, share: 0.006, band_km: 10 }, meta),
    { key: 'inv.gap.nh_access.share', params: { pct: 1, km: 10 } });
});
test('only unmeasured wording carries the unknown flag', () => {
  assert.equal(explain('why', { factor: 'road_strength', value: null }, meta).unknown, true);
  assert.equal(explain('why', { factor: 'road_strength', value: 1 }, meta).unknown, undefined);
  assert.equal(explain('gap', { factor: 'metro_access', value: 5, share: 0, band_km: 2 }, meta).unknown, undefined);
});
test('a value exactly on the last knot is near, not far', () => {
  assert.deepEqual(explain('why', { factor: 'metro_access', value: 10 }, meta),
    { key: 'inv.why.metro_access.near', params: { km: 10 } });
});
test('without bands in meta the value is still reported as near, never guessed as far', () => {
  assert.deepEqual(explain('gap', { factor: 'rail_access', value: 30 }, meta),
    { key: 'inv.gap.rail_access.near', params: { km: 30 } });
  assert.equal(explain('gap', { factor: 'nh_access', value: 99 }, undefined).key, 'inv.gap.nh_access.near');
});
test('meta.factors keyed by id works as well as a list', () => {
  const byId = { factors: { metro_access: { bands: [[0, 100], [10, 0]] } } };
  assert.equal(explain('gap', { factor: 'metro_access', value: 11 }, byId).key, 'inv.gap.metro_access.far');
});
test('a factor this build has no wording for gets a key that tt() shows verbatim', () => {
  assert.deepEqual(explain('why', { factor: 'air_quality', value: 3 }, meta), { key: 'inv.why.air_quality.unknown', params: {}, unknown: true });
});
test('an unknown kind is a programming error', () => {
  assert.throws(() => explain('what', { factor: 'nh_access', value: 1 }, meta), TypeError);
});

// The wording lives in web/locales/en.json. This ties the two together: a key explain() can produce
// with no English text would show up on a card as "inv.why.metro_access.far".
test('every key explain() can return has English wording that its parameters fill completely', () => {
  const en = JSON.parse(readFileSync(new URL('../../locales/en.json', import.meta.url), 'utf8'));
  const factors = ['nh_access', 'rail_access', 'metro_access', 'road_strength', 'built_up_growth'];
  const everyMeta = { factors: factors.map((id) => ({ id, bands: [[0, 100], [10, 0]] })) };
  const branches = factors.flatMap((factor) => [
    { factor, value: 1.2, share: 0.3, band_km: 2 }, // share
    { factor, value: 40, share: 0, band_km: 2 },    // none (distance factors only)
    { factor, value: 1.2 },                         // near, or the plain wording for roads and growth
    { factor, value: 999 },                         // far
    { factor, value: null },                        // unknown
  ]);
  const used = new Set();
  for (const kind of ['why', 'gap']) {
    for (const item of branches) {
      const { key, params } = explain(kind, item, everyMeta);
      assert.ok(typeof en[key] === 'string' && en[key] !== '', `no English wording for ${key}`);
      assert.doesNotMatch(tt(key, params, en), /\{\w+\}/, `${key} keeps a token its params do not fill`);
      used.add(key);
    }
  }
  const orphans = Object.keys(en).filter((k) => /^inv\.(why|gap)\./.test(k) && !used.has(k));
  assert.deepEqual(orphans, [], 'wording that explain() never asks for');
  assert.equal(used.size, 40);
});
