// What the visitor chose on the start page, kept in the browser only (invariant 5: no accounts, no
// personal data). Values are checked again on the way in and on the way out, because storage can
// hold anything. The address bar stays the source of truth on later pages.

import { CITY_ID, DEFAULT_PRESET, PRESET_IDS, STATE_CODE } from './config.js';

const KEY = 'invest.prefs';

const isStateCode = (v) => typeof v === 'string' && STATE_CODE.test(v);
const isCityId = (v) => typeof v === 'string' && CITY_ID.test(v);

// Keeps each field only if it is valid, so one bad field does not discard the others.
function sanitize(raw) {
  const p = raw !== null && typeof raw === 'object' ? raw : {};
  const t = p.target;
  let target = null;
  if (t?.type === 'state' && isStateCode(t.code)) target = { type: 'state', code: t.code };
  else if (t?.type === 'city' && isCityId(t.id)) target = { type: 'city', id: t.id };
  return {
    homeState: isStateCode(p.homeState) ? p.homeState : null,
    target,
    preset: PRESET_IDS.includes(p.preset) ? p.preset : DEFAULT_PRESET,
  };
}

// Reading globalThis.localStorage can itself throw (blocked storage), so it happens inside the try.
export function loadPrefs(storage) {
  try {
    return sanitize(JSON.parse((storage ?? globalThis.localStorage).getItem(KEY)));
  } catch {
    return sanitize(null); // blocked, missing or not JSON: start from the defaults
  }
}

// Reports whether it was saved. A failure is not an error for the visitor: private mode or a full
// quota just means the choices are not remembered.
export function savePrefs(prefs, storage) {
  try {
    (storage ?? globalThis.localStorage).setItem(KEY, JSON.stringify(sanitize(prefs)));
    return true;
  } catch {
    return false;
  }
}
