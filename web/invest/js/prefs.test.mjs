import test from 'node:test';
import assert from 'node:assert/strict';
import { loadPrefs, savePrefs } from './prefs.js';

const DEFAULTS = { homeState: null, target: null, preset: 'balanced' };

// In-memory stand-in for localStorage.
function memoryStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return { getItem: (k) => (map.has(k) ? map.get(k) : null), setItem: (k, v) => { map.set(k, String(v)); }, map };
}
const stored = (prefs) => memoryStorage({ 'invest.prefs': JSON.stringify(prefs) });

test('nothing stored gives the defaults, as a fresh object each time', () => {
  const a = loadPrefs(memoryStorage());
  assert.deepEqual(a, DEFAULTS);
  a.preset = 'growth';
  assert.deepEqual(loadPrefs(memoryStorage()), DEFAULTS);
});

test('round trip, for a state target and for a city target', () => {
  const storage = memoryStorage();
  const state = { homeState: 'MH', target: { type: 'state', code: 'KA' }, preset: 'commuter' };
  assert.equal(savePrefs(state, storage), true);
  assert.deepEqual(loadPrefs(storage), state);
  const city = { homeState: null, target: { type: 'city', id: 'pune' }, preset: 'highway' };
  savePrefs(city, storage);
  assert.deepEqual(loadPrefs(storage), city);
});

test('a storage whose getItem throws gives the defaults', () => {
  const blocked = { getItem() { throw new DOMException('denied', 'SecurityError'); } };
  assert.deepEqual(loadPrefs(blocked), DEFAULTS);
});

test('no storage at all (the Node default) gives the defaults', () => {
  assert.deepEqual(loadPrefs(), DEFAULTS);
  assert.equal(savePrefs(DEFAULTS), false);
});

test('stored text that is not JSON, or not an object, gives the defaults', () => {
  for (const text of ['{oops', 'null', '"MH"', '42', '[]', '']) {
    assert.deepEqual(loadPrefs(memoryStorage({ 'invest.prefs': text })), DEFAULTS, text);
  }
});

test('garbage is sanitised field by field, keeping what is valid', () => {
  const garbage = { homeState: '<x>', target: { type: 'city', id: '../../etc' }, preset: 'moon' };
  assert.deepEqual(loadPrefs(stored(garbage)), DEFAULTS);
  const mixed = { homeState: 'mh', target: { type: 'state', code: 'GA' }, preset: 'growth' };
  assert.deepEqual(loadPrefs(stored(mixed)), { homeState: null, target: { type: 'state', code: 'GA' }, preset: 'growth' });
});

test('values of the wrong type never pass a pattern by coercion', () => {
  const odd = { homeState: ['MH'], target: { type: 'city', id: ['pune'] }, preset: ['balanced'] };
  assert.deepEqual(loadPrefs(stored(odd)), DEFAULTS);
  assert.deepEqual(loadPrefs(stored({ target: 'city:pune' })), DEFAULTS);
  assert.deepEqual(loadPrefs(stored({ target: { type: 'planet', code: 'MH', id: 'pune' } })), DEFAULTS);
});

test('savePrefs writes only the validated shape', () => {
  const storage = memoryStorage();
  savePrefs({ homeState: 'MH', target: null, preset: 'growth', email: 'a@b.c', extra: { deep: 1 } }, storage);
  assert.deepEqual(JSON.parse(storage.map.get('invest.prefs')), { homeState: 'MH', target: null, preset: 'growth' });
  savePrefs({ homeState: '<script>', preset: 'moon' }, storage);
  assert.deepEqual(JSON.parse(storage.map.get('invest.prefs')), DEFAULTS);
});

test('savePrefs with a throwing storage does not throw and says it failed', () => {
  const full = { setItem() { throw new DOMException('quota', 'QuotaExceededError'); } };
  assert.equal(savePrefs({ homeState: 'MH' }, full), false);
  assert.doesNotThrow(() => savePrefs(undefined, full));
});
