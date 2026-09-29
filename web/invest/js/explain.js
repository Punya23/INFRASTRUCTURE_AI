// Turns one driver (a "why") or one gap (a "watch-out") into a locale key plus the numbers to fill in.
// No sentence is written here and no model is involved: the wording lives in web/locales under
// inv.why.* and inv.gap.*, and every number comes from the stored facts (invariant 3).
//
//   item = { factor, value, unit, share, band_km, ... } as served by the API
//   meta = /v1/meta, used only for the last knot of a factor's score curve

const DISTANCE_FACTORS = new Set(['nh_access', 'rail_access', 'metro_access']);
const PREFIX = { why: 'inv.why', gap: 'inv.gap' };

const known = Number.isFinite;
const round1 = (x) => Math.round(x * 10) / 10;

// The last knot of the factor's bands: beyond it the sub-score has reached its floor ("far").
// meta.factors is a list of { id, bands }; an object keyed by id is accepted too.
function lastKnot(meta, factor) {
  const factors = meta?.factors;
  const entry = Array.isArray(factors) ? factors.find((f) => f.id === factor) : factors?.[factor];
  const bands = entry?.bands;
  return bands?.length ? bands[bands.length - 1][0] : undefined;
}

export function explain(kind, item, meta) {
  const prefix = PREFIX[kind];
  if (!prefix) throw new TypeError(`explain: kind must be "why" or "gap", got ${String(kind)}`);
  const { factor, value, share, band_km: bandKm } = item;
  const unknown = { key: `${prefix}.${factor}.unknown`, params: {} };

  if (DISTANCE_FACTORS.has(factor)) {
    if (known(share) && known(bandKm)) {
      return { key: `${prefix}.${factor}.share`, params: { pct: Math.round(share * 100), km: bandKm } };
    }
    if (!known(value)) return unknown;
    const last = lastKnot(meta, factor);
    if (last !== undefined && value > last) return { key: `${prefix}.${factor}.far`, params: { km: last } };
    return { key: `${prefix}.${factor}.near`, params: { km: round1(value) } };
  }
  if (factor === 'road_strength') {
    return known(value) ? { key: `${prefix}.road_strength`, params: { km: round1(value) } } : unknown;
  }
  if (factor === 'built_up_growth') {
    return known(value) ? { key: `${prefix}.built_up_growth`, params: { pp: Math.round(value) } } : unknown;
  }
  // A factor this build has no wording for: tt() shows the raw key, never an invented sentence.
  return unknown;
}
