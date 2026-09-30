import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, api, getJson } from './api.js';

const reply = (body, status = 200) => async () =>
  new Response(typeof body === 'string' ? body : JSON.stringify(body), { status });

// Stubs the global fetch (which api.* uses) and records every requested URL; restored after each test.
function recordFetch(t, body = {}) {
  const urls = [];
  t.mock.method(globalThis, 'fetch', async (url) => { urls.push(url); return new Response(JSON.stringify(body)); });
  return urls;
}

test('200 gives the parsed JSON', async () => {
  assert.deepEqual(await getJson('/v1/meta', { fetchImpl: reply({ a: 1 }) }), { a: 1 });
});

test('an error body becomes an ApiError carrying the server code, message and status', async () => {
  const fetchImpl = reply({ error: { code: 'bad_request', message: 'unknown preset' } }, 400);
  await assert.rejects(getJson('/x', { fetchImpl }), (e) =>
    e instanceof ApiError && e.status === 400 && e.code === 'bad_request' && e.message === 'unknown preset');
});

test('an error status without the contract body is bad_response and keeps the status', async () => {
  await assert.rejects(getJson('/x', { fetchImpl: reply('<html>502</html>', 502) }),
    { name: 'ApiError', code: 'bad_response', status: 502 });
  await assert.rejects(getJson('/x', { fetchImpl: reply({ oops: true }, 500) }),
    { code: 'bad_response', status: 500 });
});

test('a fetch that never settles and ignores the signal still times out', async () => {
  const fetchImpl = () => new Promise(() => {});
  await assert.rejects(getJson('/x', { fetchImpl, timeoutMs: 20 }), { name: 'ApiError', code: 'timeout', status: 0 });
});

test('the timeout aborts the request signal and is reported as a timeout, not a network error', async () => {
  let seen;
  const fetchImpl = (url, { signal }) => new Promise((_, reject) => {
    seen = signal;
    signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
  });
  await assert.rejects(getJson('/x', { fetchImpl, timeoutMs: 20 }), { code: 'timeout' });
  assert.equal(seen.aborted, true);
});

test('a rejected fetch (offline, refused, CORS) is a network error', async () => {
  const fetchImpl = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(getJson('/x', { fetchImpl }), { name: 'ApiError', code: 'network' });
});

test('a 200 that is not JSON, or not an object, is bad_response', async () => {
  for (const body of ['<html>hello</html>', '', 'null', '"text"', '42']) {
    await assert.rejects(getJson('/x', { fetchImpl: reply(body) }), { code: 'bad_response', status: 200 }, body);
  }
});

test('a body that stalls after the headers also times out', async () => {
  const fetchImpl = async () => ({ ok: true, status: 200, json: () => new Promise(() => {}) });
  await assert.rejects(getJson('/x', { fetchImpl, timeoutMs: 20 }), { code: 'timeout' });
});

test('the caller can cancel: an aborted signal rejects with code aborted and cancels the request', async () => {
  const controller = new AbortController();
  let seen;
  const fetchImpl = (url, { signal }) => { seen = signal; return new Promise(() => {}); };
  const pending = getJson('/x', { fetchImpl, signal: controller.signal, timeoutMs: 5000 });
  controller.abort();
  await assert.rejects(pending, { code: 'aborted' });
  assert.equal(seen.aborted, true);
  await assert.rejects(getJson('/x', { fetchImpl, signal: AbortSignal.abort() }), { code: 'aborted' }, 'already aborted');
});

test('the timer is cleared as soon as the answer arrives', async (t) => {
  const cleared = [];
  const realClear = globalThis.clearTimeout;
  t.mock.method(globalThis, 'clearTimeout', (id) => { cleared.push(id); realClear(id); });
  await getJson('/x', { fetchImpl: reply({}) });
  assert.equal(cleared.length, 1);
});

test('stateCities keeps the query in a fixed order', async (t) => {
  const urls = recordFetch(t);
  await api.stateCities('MH', { preset: 'commuter', limit: 3 });
  assert.deepEqual(urls, ['/v1/states/MH/cities?preset=commuter&limit=3']);
});

test('options that were not given are omitted, not sent as "undefined"', async (t) => {
  const urls = recordFetch(t);
  await api.stateCities('GA');
  await api.stateCities('GA', { preset: undefined, limit: null });
  await api.meta();
  await api.states();
  assert.deepEqual(urls, ['/v1/states/GA/cities', '/v1/states/GA/cities', '/v1/meta', '/v1/states']);
});

test('searchCities URL-encodes the query, Devanagari and markup included', async (t) => {
  const urls = recordFetch(t);
  await api.searchCities('पुणे');
  await api.searchCities('<script>alert(1)</script>', { limit: 8 });
  await api.searchCities('new delhi');
  assert.equal(urls[0], '/v1/cities?q=%E0%A4%AA%E0%A5%81%E0%A4%A3%E0%A5%87');
  assert.ok(!/[<>]/.test(urls[1]) && urls[1].endsWith('&limit=8'), urls[1]);
  assert.equal(urls[2], '/v1/cities?q=new+delhi');
});

test('city, areas, assets and compare build their paths and queries', async (t) => {
  const urls = recordFetch(t);
  await api.city('pune', { preset: 'growth' });
  await api.areas('pune', { preset: 'growth', limit: 1000 });
  await api.assets('pune', ['stations', 'bus_stops']);
  await api.assets('pune');
  await api.compare('pune', { preset: 'highway', scope: 'metros', limit: 5 });
  await api.projects('pune');
  assert.deepEqual(urls, [
    '/v1/cities/pune?preset=growth',
    '/v1/cities/pune/areas?preset=growth&limit=1000',
    '/v1/cities/pune/assets?layers=stations%2Cbus_stops',
    '/v1/cities/pune/assets',
    '/v1/cities/pune/compare?preset=highway&scope=metros&limit=5',
    '/v1/cities/pune/projects',
  ]);
});

test('an id that could steer a path is rejected before any request is made', async (t) => {
  const urls = recordFetch(t);
  const hostile = ['../../etc/passwd', 'pune/../delhi', 'Pune', 'p', '', 'a b', 'pune?x=1', 'a'.repeat(65), undefined, null, 42, ['pune']];
  for (const id of hostile) {
    await assert.rejects(api.city(id), { name: 'ApiError', code: 'bad_request', status: 400 }, String(id));
    await assert.rejects(api.areas(id), { code: 'bad_request' });
    await assert.rejects(api.assets(id), { code: 'bad_request' });
    await assert.rejects(api.compare(id), { code: 'bad_request' });
    await assert.rejects(api.projects(id), { code: 'bad_request' });
  }
  for (const code of ['mh', 'MHA', 'M', '../', 'M/', undefined]) {
    await assert.rejects(api.stateCities(code), { code: 'bad_request' }, String(code));
  }
  assert.deepEqual(urls, []);
});
