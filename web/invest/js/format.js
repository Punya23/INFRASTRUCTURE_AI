// Number and text formatting. Pure: no DOM. Every formatter shows a dash for a value that was not
// observed, so an unmeasured factor can never read as 0, NaN or null.

const DASH = '—';   // U+2014
const MINUS = '−';  // U+2212, wider than a hyphen and the same width as the plus sign

// Indian (lakh and crore) grouping with Latin digits for every language. ICU groups kn-IN by
// thousands (6,100,000), which Kannada readers in India do not expect, and the text around a
// number is English for languages that have no dictionary yet.
const COUNT = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

export const formatCount = (n) => (Number.isFinite(n) ? COUNT.format(n) : DASH);

export const formatScore = (x) => (Number.isFinite(x) ? String(Math.round(x)) : DASH);

// +7, −11, 0. A change that rounds to zero is plain 0, never +0 or −0.
export function formatDelta(x) {
  if (!Number.isFinite(x)) return DASH;
  const rounded = Math.round(x);
  if (rounded === 0) return '0';
  return rounded > 0 ? `+${rounded}` : `${MINUS}${-rounded}`;
}

// A raw value with fixed decimals. An observed zero is "0.0"; only a missing value is a dash.
// A small negative that rounds to zero is "0.0" too, never "-0.0".
export function formatValue(x, digits = 1) {
  if (!Number.isFinite(x)) return DASH;
  const text = x.toFixed(digits);
  return /^-0(\.0+)?$/.test(text) ? text.slice(1) : text;
}

// "3.1 km" in English, with the unit written in the reader's script for Hindi and Kannada.
const KM_LOCALE = { hi: 'hi-IN', kn: 'kn-IN' };
const kmFormats = new Map();

export function formatKm(x, lang) {
  if (!Number.isFinite(x)) return DASH;
  const locale = KM_LOCALE[lang] ?? 'en-IN';
  if (!kmFormats.has(locale)) {
    kmFormats.set(locale, new Intl.NumberFormat(locale, {
      style: 'unit', unit: 'kilometer', unitDisplay: 'short', maximumFractionDigits: 1,
    }));
  }
  return kmFormats.get(locale).format(x);
}

// Translate `key` (from i18n.js, or `dict` in tests) and fill {name} tokens from `params`. Falls back
// to the key itself, so a missing string is visible instead of blank. A token with no usable
// parameter (missing, null, undefined, NaN or infinite) is left as written, never printed as a value.
export function tt(key, params, dict) {
  const found = dict ? dict[key] : globalThis.InfraI18n?.t(key);
  const text = typeof found === 'string' && found !== '' ? found : key;
  return text.replace(/\{(\w+)\}/g, (token, name) => {
    const value = params && Object.hasOwn(params, name) ? params[name] : undefined;
    const unusable = value == null || (typeof value === 'number' && !Number.isFinite(value));
    return unusable ? token : String(value);
  });
}
