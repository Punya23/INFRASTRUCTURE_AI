// Client for the investor API (spec section 7). Pure: no DOM. Every failure is an ApiError, so a
// page has one path to handle: show an error state with Retry and keep the last good view.

import { API_BASE, CITY_ID, FETCH_TIMEOUT_MS, STATE_CODE } from './config.js';

// code: the server's error code (bad_request, not_found, rate_limited, internal) or one of ours:
//   timeout, network (offline, refused or blocked by CORS), bad_response (not the JSON we expect), aborted.
// status: the HTTP status, or 0 when there was no response.
export class ApiError extends Error {
  constructor(code, message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

async function request(url, signal, fetchImpl) {
  let response;
  try {
    response = await fetchImpl(url, { signal });
  } catch {
    throw new ApiError('network', 'Could not reach the server');
  }
  let body;
  try {
    body = await response.json();
  } catch {
    body = undefined; // not JSON; the status decides below
  }
  if (!response.ok) {
    const error = body?.error;
    if (typeof error?.code === 'string') {
      throw new ApiError(error.code, typeof error.message === 'string' ? error.message : error.code, response.status);
    }
    throw new ApiError('bad_response', `Unexpected HTTP ${response.status}`, response.status);
  }
  if (body === null || typeof body !== 'object') {
    throw new ApiError('bad_response', 'The server did not send a JSON object', response.status);
  }
  return body;
}

// GET path (which starts with /v1/) and give back the parsed JSON object.
// The request is aborted after timeoutMs, and it is also raced against a timer: a fetch that ignores
// the abort signal, or a body that stalls after the headers, still cannot hang the page.
// `signal` lets the caller cancel (code "aborted"), for example when a newer request replaces this one.
export async function getJson(path, { timeoutMs = FETCH_TIMEOUT_MS, fetchImpl = fetch, signal } = {}) {
  const controller = new AbortController();
  let timer;
  let onAbort;
  const interrupted = new Promise((_, reject) => {
    const stop = (error) => {
      reject(error);
      controller.abort();
    };
    timer = setTimeout(() => stop(new ApiError('timeout', `No answer within ${timeoutMs} ms`)), timeoutMs);
    if (signal) {
      onAbort = () => stop(new ApiError('aborted', 'Request cancelled'));
      if (signal.aborted) onAbort();
      else signal.addEventListener('abort', onAbort, { once: true });
    }
  });
  try {
    return await Promise.race([request(API_BASE + path, controller.signal, fetchImpl), interrupted]);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

// "?a=1&b=2" from the entries that have a value; undefined and null are left out, never sent as text.
function query(params) {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) if (value != null) search.set(name, String(value));
  const text = search.toString();
  return text ? `?${text}` : '';
}

// Ids come from the address bar or storage, so they are checked before they become part of a path.
// The server would answer the same 400; this just never sends it.
function checked(value, pattern, what) {
  if (typeof value === 'string' && pattern.test(value)) return value;
  throw new ApiError('bad_request', `Invalid ${what}`, 400);
}

// Methods that take an id are async so that an invalid id rejects instead of throwing.
export const api = {
  meta: () => getJson('/v1/meta'),
  states: () => getJson('/v1/states'),
  stateCities: async (code, { preset, limit } = {}) =>
    getJson(`/v1/states/${checked(code, STATE_CODE, 'state code')}/cities${query({ preset, limit })}`),
  searchCities: (q, { limit } = {}) => getJson(`/v1/cities${query({ q, limit })}`),
  city: async (id, { preset } = {}) =>
    getJson(`/v1/cities/${checked(id, CITY_ID, 'city id')}${query({ preset })}`),
  areas: async (id, { preset, limit } = {}) =>
    getJson(`/v1/cities/${checked(id, CITY_ID, 'city id')}/areas${query({ preset, limit })}`),
  // layers: an array such as ['stations', 'bus_stops'], or omitted for all four.
  assets: async (id, layers) =>
    getJson(`/v1/cities/${checked(id, CITY_ID, 'city id')}/assets${query({ layers: Array.isArray(layers) ? layers.join(',') : layers })}`),
  // Upcoming bus and metro projects found in news; each one carries its verbatim evidence and source link.
  projects: async (id) => getJson(`/v1/cities/${checked(id, CITY_ID, 'city id')}/projects`),
  compare: async (id, { preset, scope, limit } = {}) =>
    getJson(`/v1/cities/${checked(id, CITY_ID, 'city id')}/compare${query({ preset, scope, limit })}`),
};
