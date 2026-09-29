import test from 'node:test';
import assert from 'node:assert/strict';
import { formatCount, formatDelta, formatKm, formatScore, formatValue, tt } from './format.js';

test('counts use Indian grouping in every language', () => {
  assert.equal(formatCount(6100000, 'en'), '61,00,000');
  // ICU groups kn-IN by thousands (6,100,000); the product wants lakh grouping in en, hi and kn.
  for (const lang of ['en', 'hi', 'kn', undefined]) assert.equal(formatCount(6100000, lang), '61,00,000');
  assert.equal(formatCount(999), '999');
  assert.equal(formatCount(143), '143');
});
test('an unobserved count is a dash, never 0 or NaN', () => {
  for (const x of [null, undefined, NaN]) assert.equal(formatCount(x), '—');
});

test('scores are whole numbers, unobserved is a dash', () => {
  assert.equal(formatScore(71.44), '71');
  assert.equal(formatScore(71.5), '72');
  assert.equal(formatScore(0), '0');
  for (const x of [null, undefined, NaN]) assert.equal(formatScore(x), '—');
});

test('deltas carry a sign; the minus is U+2212', () => {
  assert.equal(formatDelta(7.4), '+7');
  assert.equal(formatDelta(-11.2), '−11');
  assert.equal(formatDelta(0), '0');
  assert.equal(formatDelta(0.4), '0');
  assert.equal(formatDelta(-0.4), '0');
  assert.equal(formatDelta(null), '—');
  assert.equal(formatDelta(NaN), '—');
});

test('an observed zero is not unknown', () => {
  assert.equal(formatValue(undefined), '—');
  assert.equal(formatValue(null), '—');
  assert.equal(formatValue(NaN), '—');
  assert.equal(formatValue(0), '0.0');
  assert.equal(formatValue(2.24), '2.2');
  assert.equal(formatValue(2.246, 2), '2.25');
  assert.equal(formatValue('3.1'), '—', 'a string is a contract violation, not a number');
});

test('distances carry a localised unit and drop a trailing .0', () => {
  assert.equal(formatKm(3.14, 'en'), '3.1 km');
  assert.equal(formatKm(12, 'en'), '12 km');
  // The unit is written in the reader's script; the exact abbreviation is ICU data and can differ by version.
  assert.match(formatKm(3.1, 'hi'), /^3\.1 [\u0900-\u097F॰.]+$/u);
  assert.match(formatKm(3.1, 'kn'), /^3\.1 [\u0C80-\u0CFF.]+$/u);
  assert.equal(formatKm(3.1, 'zz'), '3.1 km', 'a language without a dictionary reads like English');
  assert.equal(formatKm(null, 'en'), '—');
});

test('tt fills tokens from a dictionary and falls back to the key', () => {
  assert.equal(tt('a {n} b', { n: 3 }, { 'a {n} b': 'x {n} y' }), 'x 3 y');
  assert.equal(tt('missing.key', {}, {}), 'missing.key');
  assert.equal(tt('missing {n}', { n: 1 }, {}), 'missing 1');
});
test('tt leaves unknown tokens untouched and never prints null, undefined or NaN', () => {
  const dict = { k: '{a} and {b} and {c} and {d}' };
  assert.equal(tt('k', { a: 1 }, dict), '1 and {b} and {c} and {d}');
  assert.equal(tt('k', { a: null, b: undefined, c: NaN, d: 0 }, dict), '{a} and {b} and {c} and 0');
  assert.equal(tt('k', undefined, dict), '{a} and {b} and {c} and {d}');
  assert.equal(tt('c', {}, { c: '{constructor} {toString}' }), '{constructor} {toString}', 'inherited properties are not parameters');
});
test('tt replaces every occurrence of a token', () => {
  assert.equal(tt('k', { n: 2 }, { k: '{n} of {n}' }), '2 of 2');
});
test('tt reads the live i18n dictionary when no dict is given', (t) => {
  t.after(() => { delete globalThis.InfraI18n; });
  globalThis.InfraI18n = { t: (key) => ({ 'inv.x': 'Only {n} cities' })[key] ?? null };
  assert.equal(tt('inv.x', { n: 3 }), 'Only 3 cities');
  assert.equal(tt('inv.unloaded'), 'inv.unloaded', 'null from i18n.js falls back to the key');
});
test('tt still works when i18n.js is absent', () => {
  assert.equal(tt('inv.x', { n: 3 }), 'inv.x');
});
