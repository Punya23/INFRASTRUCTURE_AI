import test from 'node:test';
import assert from 'node:assert/strict';
import { API_BASE, CITY_ID, DEFAULT_PRESET, FETCH_TIMEOUT_MS, PRESET_IDS, STATE_CODE } from './config.js';

test('outside the dev port the API is on the same origin', () => {
  assert.equal(API_BASE, '');
  assert.equal(FETCH_TIMEOUT_MS, 8000);
});

test('served from the dev port 8765 the API is on localhost:8080', async (t) => {
  t.after(() => { delete globalThis.location; });
  globalThis.location = { port: '8765' };
  const dev = await import('./config.js?dev-port');
  assert.equal(dev.API_BASE, 'http://localhost:8080');
  globalThis.location = { port: '' };
  assert.equal((await import('./config.js?other-port')).API_BASE, '');
  globalThis.location = { port: '8766' };
  assert.equal((await import('./config.js?second-checkout')).API_BASE, 'http://localhost:8081');
});

test('id patterns match spec section 7', () => {
  for (const ok of ['MH', 'KA']) assert.ok(STATE_CODE.test(ok), ok);
  for (const bad of ['mh', 'M', 'MHA', 'M1', 'MH\n', '']) assert.ok(!STATE_CODE.test(bad), JSON.stringify(bad));
  for (const ok of ['pune', 'aurangabad-mh', 'a1', 'a'.repeat(64)]) assert.ok(CITY_ID.test(ok), ok);
  for (const bad of ['p', 'Pune', 'pune_1', 'a b', '../x', 'a'.repeat(65), 'pune\n']) assert.ok(!CITY_ID.test(bad), JSON.stringify(bad));
});

test('the default preset is one of the four presets', () => {
  assert.deepEqual(PRESET_IDS, ['balanced', 'commuter', 'highway', 'growth']);
  assert.ok(PRESET_IDS.includes(DEFAULT_PRESET));
});
