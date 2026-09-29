// Constants shared by the investor pages.

// Dev: `python3 -m http.server 8765` serves the pages and the Go API listens on :8080 (its CORS
// allow-list defaults to :8765). Anywhere else the API is expected on the same origin.
export const API_BASE = globalThis.location?.port === '8765' ? 'http://localhost:8080' : '';

// Every request gives up after this long and shows an error state with Retry.
export const FETCH_TIMEOUT_MS = 8000;

// Id patterns from spec section 7. api.js, prefs.js and the pages check values that come from the
// address bar or from storage with these, so a bad value never reaches a URL.
export const STATE_CODE = /^[A-Z]{2}$/;
export const CITY_ID = /^[a-z0-9-]{2,64}$/;

// The four scoring presets (spec section 4) and the one used when nothing is chosen.
export const PRESET_IDS = ['balanced', 'commuter', 'highway', 'growth'];
export const DEFAULT_PRESET = 'balanced';
