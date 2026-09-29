// Constants shared by the investor pages.

// Dev: `python3 -m http.server 8765` serves the pages and the Go API listens on :8080 (its CORS
// allow-list defaults to :8765). A second checkout can serve on 8766 with its API on :8081 and
// INVEST_CORS_ORIGINS=http://localhost:8766. Anywhere else the API is expected on the same origin.
const DEV_API_PORT = { 8765: 8080, 8766: 8081 };
const devPort = DEV_API_PORT[globalThis.location?.port];
export const API_BASE = devPort ? `http://localhost:${devPort}` : '';

// Every request gives up after this long and shows an error state with Retry.
export const FETCH_TIMEOUT_MS = 8000;

// Id patterns from spec section 7. api.js, prefs.js and the pages check values that come from the
// address bar or from storage with these, so a bad value never reaches a URL.
export const STATE_CODE = /^[A-Z]{2}$/;
export const CITY_ID = /^[a-z0-9-]{2,64}$/;

// The four scoring presets (spec section 4) and the one used when nothing is chosen.
export const PRESET_IDS = ['balanced', 'commuter', 'highway', 'growth'];
export const DEFAULT_PRESET = 'balanced';
