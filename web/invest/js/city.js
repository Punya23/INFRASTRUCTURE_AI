// City page (spec section 8): header, hex map of areas, best areas list, infrastructure layers and the
// comparison panel. The three data sections load in parallel and fail on their own: each has a
// skeleton, and an error slot with Retry that sits next to its last good view.
//
// The helpers under "Pure" run in Node (city.test.mjs); the page starts only when there is a document.

import { api } from './api.js';
import { CITY_ID, DEFAULT_PRESET, PRESET_IDS } from './config.js';
import { explain } from './explain.js';
import { formatCount, formatDelta, formatScore, formatValue, tt } from './format.js';
import { ASSET_SOURCE, BREAKS, RAMP, cellCentre, createMap } from './map.js';
import { clear, h, onLangChange, renderError, renderSkeleton, setStatus } from './ui.js';

// ---------- Pure ----------

// An unnamed area borrows the name of the nearest named area within this distance; beyond it the label
// gives coordinates, because "near" a place 20 km away would mislead. About three H3 res-7 cells
// (team judgment, 2026-09-30).
export const NEAR_MAX_KM = 8;
export const BEST_AREAS = 10;
const MAX_ALIASES = 4;
export const SCOPES = ['metros', 'peers', 'state', 'india'];

// { id, preset } from the query string. A malformed id is null (the page shows not-found without a
// request); an unknown preset becomes the default and the page rewrites the address to say so.
export function readParams(search) {
  const params = new URLSearchParams(search);
  const id = params.get('c');
  const preset = params.get('preset');
  return {
    id: id !== null && CITY_ID.test(id) ? id : null,
    preset: PRESET_IDS.includes(preset) ? preset : DEFAULT_PRESET,
  };
}

export const cityHref = (id, preset) => `city.html?${new URLSearchParams({ c: id, preset })}`;

// Distance in km between two [lon, lat] points; flat-earth is exact enough within one city.
function km([x1, y1], [x2, y2]) {
  const perDegree = 111.2;
  const kx = perDegree * Math.cos(((y1 + y2) / 2) * (Math.PI / 180));
  return Math.hypot((x2 - x1) * kx, (y2 - y1) * perDegree);
}

// What to call each area, by id: { name } when it has one, { near } (the closest named area within
// maxKm), else { lat, lon } of its centre, rounded to 2 decimals. Never blank, never "null".
export function areaPlaces(features, maxKm = NEAR_MAX_KM) {
  const centres = features.map(cellCentre);
  const named = features.flatMap((f, i) => (f.properties.name ? [[f.properties.name, centres[i]]] : []));
  return new Map(features.map((f, i) => {
    if (f.properties.name) return [f.properties.id, { name: f.properties.name }];
    let near = null;
    let nearest = maxKm;
    for (const [name, centre] of named) {
      const d = km(centres[i], centre);
      if (d <= nearest) { near = name; nearest = d; }
    }
    const [lon, lat] = centres[i];
    return [f.properties.id, near ? { near } : { lat: Math.round(lat * 100) / 100, lon: Math.round(lon * 100) / 100 }];
  }));
}

export function placeText(place, t = tt) {
  if (place?.name) return place.name;
  if (place?.near) return t('inv.city.area.near', { place: place.near });
  if (place) return t('inv.city.area.at', { lat: place.lat.toFixed(2), lon: place.lon.toFixed(2) });
  return t('inv.city.area.unknown');
}

// The top n rankable areas, best first, one per name: several cells called "Baner" show as one row.
export function bestAreas(features, places, n = BEST_AREAS) {
  const seen = new Set();
  const out = [];
  for (const f of [...features].sort((a, b) => a.properties.rank - b.properties.rank)) {
    if (!f.properties.elig) continue;
    const place = places.get(f.properties.id);
    const key = place?.name ?? (place?.near ? `near:${place.near}` : f.properties.id);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(f);
    if (out.length === n) break;
  }
  return out;
}

// [title, kind] for an asset popup. A null name or ref gets a fallback label, never the text "null".
export function assetText(layerId, props, t = tt) {
  const named = (value, fallback) => (typeof value === 'string' && value.trim() ? value : t(fallback));
  switch (ASSET_SOURCE[layerId]) {
    case 'stations':
      return [named(props.name, 'inv.city.asset.station_unnamed'),
        t(props.mode === 'metro' ? 'inv.city.asset.metro' : 'inv.city.asset.rail')];
    case 'bus_stops':
      return [named(props.name, 'inv.city.asset.bus_unnamed'), t('inv.city.asset.bus')];
    case 'toll_plazas':
      return [named(props.name, 'inv.city.asset.toll_unnamed'), t('inv.city.asset.toll')];
    case 'highways': {
      const kind = t(props.kind === 'expressway_segment' ? 'inv.city.asset.expressway' : 'inv.city.asset.nh');
      const status = t(props.status === 'operational' ? 'inv.city.asset.open' : 'inv.city.asset.building');
      return [named(props.ref, 'inv.city.asset.highway_unnumbered'), `${kind}, ${status}`];
    }
    default:
      throw new TypeError(`assetText: unknown layer ${layerId}`);
  }
}

// "Metro access +11 · Built-up growth −8": the largest factor where the other city is ahead and the
// largest where it is behind (sub-score differences, other minus this city).
export function compareReason(other, t = tt) {
  return [other.better?.[0], other.worse?.[0]]
    .filter((item) => item && Number.isFinite(item.delta))
    .map((item) => `${t(`inv.factor.${item.factor}`)} ${formatDelta(item.delta)}`)
    .join(' · ');
}

// ---------- Page ----------

function boot() {
  const $ = (id) => document.getElementById(id);
  const el = {
    main: $('city-main'), notFound: $('not-found'), status: $('city-status'),
    head: $('city-head'), headMsg: $('city-head-msg'), presets: $('city-presets'), presetDesc: $('city-preset-desc'),
    map: $('city-map'), mapNote: $('city-map-note'), legend: $('city-legend'), layers: $('city-layers'),
    layerMsg: $('city-layer-msg'), areasMsg: $('city-areas-msg'), best: $('city-best'),
    scopes: $('city-scopes'), compare: $('city-compare'), compareMsg: $('city-compare-msg'),
  };

  const params = readParams(location.search);
  const s = {
    id: params.id, preset: params.preset, scope: null,
    city: null, states: null, areas: null, places: new Map(), byId: new Map(), compare: null,
    map: null, fitted: false,
  };
  if (!s.id) return showNotFound();
  syncUrl();

  function syncUrl() {
    const href = cityHref(s.id, s.preset);
    if (location.search !== href.slice('city.html'.length)) history.replaceState(null, '', href);
  }

  // Hoisted, so an invalid id can bail out before anything else is set up. The title is set again
  // when the dictionary arrives: an invalid id gets here before i18n.js has loaded it.
  function showNotFound() {
    if (!el.notFound.hidden) return;
    el.main.hidden = true;
    el.notFound.hidden = false;
    const title = () => { document.title = tt('inv.city.notfound.title'); };
    title();
    onLangChange(title);
  }

  // One data section: a sequence number drops answers that a newer request has replaced, the
  // skeleton shows only until there is something to keep, and a failure keeps the last good view.
  function section({ body, msg, rows, load, render }) {
    let seq = 0;
    let hasData = false;
    const run = async () => {
      const mine = ++seq;
      msg.replaceChildren();
      if (hasData) body.setAttribute('aria-busy', 'true');
      else if (rows) renderSkeleton(body, rows);
      try {
        const data = await load();
        if (mine !== seq) return;
        body.removeAttribute('aria-busy');
        hasData = true;
        render(data);
      } catch (error) {
        if (mine !== seq || error?.code === 'aborted') return;
        body.removeAttribute('aria-busy');
        if (!hasData && rows) clear(body);
        // the id passed the pattern but no such city exists (or the server refused it)
        if (error?.code === 'not_found' || error?.code === 'bad_request') return showNotFound();
        renderError(msg, error, run);
      }
    };
    return run;
  }

  // ----- Header -----
  const stateName = (code) => s.states?.get(code) ?? code;

  const loadHead = section({
    body: el.head, msg: el.headMsg, rows: 3,
    load: async () => {
      // the state name is a nicety: without it the header shows the code
      const [city, states] = await Promise.all([api.city(s.id, { preset: s.preset }), s.states ?? api.states().catch(() => null)]);
      return { city, states };
    },
    render({ city, states }) {
      s.city = city;
      if (states && !(states instanceof Map)) s.states = new Map(states.states.map((st) => [st.code, st.name]));
      renderHead();
      renderLegend();
      renderBusToggle();
      if (s.compare) renderCompare();
    },
  });

  function meter(labelKey, value) {
    const known = Number.isFinite(value);
    return h('div', { class: `inv-meter${known ? '' : ' inv-meter--unknown'}`, style: { '--value': known ? value : 0 } },
      h('span', { class: 'inv-meter__label' }, tt(labelKey)),
      h('span', { class: 'inv-meter__value' }, formatScore(value)),
      h('span', { class: 'inv-meter__bar', 'aria-hidden': true }));
  }

  // Merged urban regions can list twenty places; name a few and count the rest.
  function aliasText(aliases) {
    const shown = aliases.slice(0, MAX_ALIASES).join(', ');
    return aliases.length > MAX_ALIASES
      ? tt('inv.city.aliases_more', { names: shown, n: aliases.length - MAX_ALIASES })
      : tt('inv.city.aliases', { names: shown });
  }

  function fact(labelKey, value) {
    return h('div', { class: 'city-fact' }, h('dt', null, tt(labelKey)), h('dd', null, value));
  }

  function renderHead() {
    const c = s.city;
    const score = c.score;
    const growth = c.factors?.built_up_growth?.value;
    const bus = c.data?.bus;
    document.title = tt('inv.city.doc_title', { name: c.name });
    el.head.replaceChildren(
      h('a', { class: 'city-crumb', href: `state.html?${new URLSearchParams({ s: c.state, preset: s.preset })}` },
        tt('inv.city.back', { state: stateName(c.state) })),
      h('div', { class: 'city-head__grid' },
        h('div', { class: 'city-head__title inv-stack--tight' },
          h('div', { class: 'inv-cluster' },
            h('h1', null, c.name),
            h('span', { class: 'inv-badge' }, tt(`inv.tier.${c.tier}`))),
          h('p', { class: 'inv-lead' }, stateName(c.state)),
          c.aliases?.length ? h('p', { class: 'inv-small inv-muted' }, aliasText(c.aliases)) : null),
        h('div', { class: 'city-score' },
          h('div', { class: 'inv-ring inv-ring--lg', style: { '--value': Number.isFinite(score) ? score : 0 }, role: 'img', 'aria-label': tt('inv.city.score_aria', { score: formatScore(score) }) },
            h('span', { class: 'inv-ring__value', 'aria-hidden': true }, formatScore(score))),
          h('div', { class: 'city-score__text inv-stack--tight' },
            h('p', { class: 'city-score__label' }, tt('inv.city.score'), ' ', h('span', { class: 'inv-muted' }, tt(`inv.preset.${s.preset}`))),
            meter('inv.group.access', c.access),
            meter('inv.group.momentum', c.momentum),
            c.coverage < 1 ? h('p', { class: 'inv-small inv-muted' }, tt('inv.city.coverage', { pct: Math.round(c.coverage * 100) })) : null))),
      h('dl', { class: 'city-facts' },
        fact('inv.city.fact.population', formatCount(c.population)),
        fact('inv.city.fact.growth', Number.isFinite(growth) ? tt('inv.city.growth_value', { pp: formatValue(growth) }) : formatValue(growth)),
        fact('inv.city.fact.stations', tt('inv.city.stations_value', { metro: formatCount(c.data?.metro_stations), rail: formatCount(c.data?.rail_stations) })),
        fact('inv.city.fact.bus', bus ? tt('inv.city.bus.yes', { operator: bus.operator }) : tt('inv.city.bus.no'))));
    el.map.setAttribute('aria-label', tt('inv.city.map.label', { name: c.name }));
  }

  // ----- Presets -----
  function renderPresets() {
    el.presets.replaceChildren(...PRESET_IDS.map((id) => h('button', {
      type: 'button', class: 'inv-chip inv-chip--choice', 'aria-pressed': String(id === s.preset),
      onclick: () => choosePreset(id),
    }, tt(`inv.preset.${id}`))));
    el.presetDesc.textContent = tt(`inv.preset.${s.preset}.desc`);
  }

  function choosePreset(id) {
    if (id === s.preset) return;
    s.preset = id;
    syncUrl();
    renderPresets();
    setStatus(el.status, tt('inv.loading'));
    loadHead();
    loadAreas();
    loadCompare();
  }

  // ----- Map, legend and best areas -----
  const areaPopup = (id) => {
    const f = s.byId.get(id);
    if (!f) return h('p', null, tt('inv.city.area.unknown'));
    const p = f.properties;
    return h('div', { class: 'city-pop inv-stack--tight' },
      h('p', { class: 'city-pop__title' }, placeText(s.places.get(id))),
      h('p', { class: 'city-pop__score' }, h('span', { class: 'inv-num' }, formatScore(p.score)), ' ', tt('inv.city.area.score_suffix')),
      p.elig ? null : h('p', { class: 'inv-small inv-muted' }, tt('inv.city.area.unranked')),
      reasons(p, 3),
      h('p', { class: 'inv-small' }, p.bus_stops == null ? tt('inv.city.area.bus_none') : tt('inv.city.area.bus', { n: formatCount(p.bus_stops) })));
  };

  const popupContent = (kind, idOrProps) => {
    if (kind === 'area') return areaPopup(idOrProps);
    const [title, sub] = assetText(kind, idOrProps);
    return h('div', { class: 'city-pop inv-stack--tight' }, h('p', { class: 'city-pop__title' }, title), h('p', { class: 'inv-small inv-muted' }, sub));
  };

  // Why-chips (drivers) and at most one watch-out (gap). The watch-out differs by shape and by a
  // visible label, not by colour alone.
  function reasons(props, maxWhy) {
    const why = (props.d ?? []).slice(0, maxWhy).map((d) => {
      const { key, params } = explain('why', d);
      return h('li', { class: 'inv-chip inv-chip--why' }, tt(key, params));
    });
    const gap = props.g?.[0];
    let watch = null;
    if (gap) {
      const { key, params } = explain('gap', gap);
      watch = h('li', { class: 'inv-chip inv-chip--gap city-gap' },
        h('span', { class: 'city-gap__label' }, tt('inv.city.watch_out')), ' ', tt(key, params));
    }
    return why.length || watch ? h('ul', { class: 'city-reasons', role: 'list' }, why, watch) : null;
  }

  function renderLegend() {
    const shown = s.areas?.length;
    const total = s.city?.cells;
    const bands = [0, ...BREAKS];
    el.legend.replaceChildren(
      h('p', { class: 'city-legend__title' }, tt('inv.city.legend.title')),
      h('ol', { class: 'city-legend__ramp', role: 'list' }, RAMP.map((colour, i) => h('li', null,
        h('span', { class: 'city-legend__swatch', style: { 'background-color': colour }, 'aria-hidden': true }),
        `${bands[i]}–${bands[i + 1] ?? 100}`))),
      h('p', { class: 'city-legend__note' },
        h('span', { class: 'city-legend__swatch city-legend__swatch--faded', style: { 'background-color': RAMP[3] }, 'aria-hidden': true }),
        tt('inv.city.legend.faded')),
      h('p', { class: 'city-legend__note', hidden: !(total > shown) },
        tt('inv.city.legend.partial', { shown: formatCount(shown), total: formatCount(total) })));
  }

  function renderBest() {
    const rows = bestAreas(s.areas, s.places);
    if (!rows.length) {
      el.best.replaceChildren(h('li', { class: 'inv-empty' }, h('p', null, tt('inv.city.best.empty'))));
      return;
    }
    el.best.replaceChildren(...rows.map((f, i) => h('li', { class: 'city-best__item' },
      h('button', { type: 'button', class: 'city-best__btn', onclick: () => showOnMap(f) },
        h('span', { class: `inv-rank${i === 0 ? ' inv-rank--top' : ''}` }, String(i + 1)),
        h('span', { class: 'city-best__name' }, placeText(s.places.get(f.properties.id))),
        h('span', { class: 'city-best__score inv-num' }, formatScore(f.properties.score)),
        h('span', { class: 'inv-visually-hidden' }, tt('inv.city.best.show'))),
      reasons(f.properties, 2))));
  }

  function showOnMap(feature) {
    const name = placeText(s.places.get(feature.properties.id));
    if (!s.map) {
      setStatus(el.status, tt('inv.city.map.unavailable'));
      return;
    }
    el.map.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    s.map.showArea(feature);
    setStatus(el.status, tt('inv.city.best.shown', { name }));
  }

  function applyAreasToMap() {
    if (!s.map || !s.areas) return;
    s.map.setAreas(s.areas, { fit: !s.fitted });
    s.fitted = true;
  }

  const loadAreas = section({
    body: el.best, msg: el.areasMsg, rows: 5,
    load: () => api.areas(s.id, { preset: s.preset, limit: 1000 }),
    render(collection) {
      s.areas = collection.features;
      s.byId = new Map(s.areas.map((f) => [f.properties.id, f]));
      s.places = areaPlaces(s.areas);
      renderBest();
      renderLegend();
      applyAreasToMap();
      setStatus(el.status, tt('inv.city.areas_loaded', { n: formatCount(s.areas.length) }));
    },
  });

  // ----- Layers (lazy: each collection is fetched the first time one of its toggles is switched on) -----
  const assetLoads = new Map();
  function ensureAssets(source) {
    if (!assetLoads.has(source)) {
      const load = api.assets(s.id, [source]).then((data) => s.map.addAssets(source, data[source]));
      load.catch(() => assetLoads.delete(source)); // a later toggle tries again
      assetLoads.set(source, load);
    }
    return assetLoads.get(source);
  }

  async function toggleLayer(input) {
    const layer = input.value;
    el.layerMsg.replaceChildren();
    if (!s.map) { input.checked = false; return; } // the toggles are hidden until the map is ready
    if (!input.checked) return s.map.setVisible(layer, false);
    if (!s.map.hasAssets(ASSET_SOURCE[layer])) setStatus(el.status, tt('inv.loading'));
    try {
      await ensureAssets(ASSET_SOURCE[layer]);
    } catch (error) {
      if (error?.code === 'aborted') return;
      input.checked = false;
      renderError(el.layerMsg, error, () => { input.checked = true; toggleLayer(input); });
      return;
    }
    s.map.setVisible(layer, input.checked); // it may have been switched off while loading
    setStatus(el.status, '');
  }

  function renderBusToggle() {
    const input = el.layers.querySelector('input[value="bus_stops"]');
    const note = $('city-bus-note');
    // only a loaded city can say it has no feed; until then the toggle stays usable (an empty layer at worst)
    const none = s.city ? !s.city.data?.bus : false;
    input.disabled = none || !s.map;
    note.hidden = !none;
  }

  el.layers.addEventListener('change', (event) => { if (event.target.matches('input')) toggleLayer(event.target); });

  // ----- Compare -----
  function renderScopes() {
    el.scopes.replaceChildren(...SCOPES.map((scope) => h('button', {
      type: 'button', class: 'inv-chip inv-chip--choice', 'aria-pressed': String(scope === (s.scope ?? s.compare?.scope)),
      onclick: () => { if (scope !== (s.scope ?? s.compare?.scope)) { s.scope = scope; renderScopes(); loadCompare(); } },
    }, tt(`inv.city.scope.${scope}`))));
  }

  function renderCompare() {
    const cmp = s.compare;
    const base = s.city?.name ?? cmp.base.name;
    if (!cmp.others.length) {
      el.compare.replaceChildren(h('p', { class: 'inv-empty' }, tt('inv.city.compare.empty')));
      return;
    }
    el.compare.replaceChildren(
      h('p', { class: 'city-cmp__here' }, tt('inv.city.compare.here', { rank: cmp.base_rank, total: cmp.total + 1 })),
      h('p', { class: 'inv-small inv-muted' }, tt('inv.city.compare.note', { name: base })),
      h('ol', { class: 'city-cmp__list', role: 'list' }, cmp.others.map((o) => {
        const up = Math.round(o.delta) > 0;
        const why = compareReason(o);
        return h('li', null, h('a', { class: 'city-cmp__row', href: cityHref(o.id, s.preset) },
          h('span', { class: 'city-cmp__name' }, o.name, ' ', h('span', { class: 'inv-small inv-muted' }, stateName(o.state))),
          h('span', { class: 'city-cmp__score inv-num' }, formatScore(o.score)),
          h('span', { class: `inv-delta${up ? ' inv-delta--up' : ''}` }, formatDelta(o.delta),
            h('span', { class: 'inv-visually-hidden' }, ` ${tt('inv.city.compare.vs', { name: base })}`)),
          why ? h('span', { class: 'city-cmp__why inv-small' }, why) : null));
      })));
  }

  const loadCompare = section({
    body: el.compare, msg: el.compareMsg, rows: 4,
    load: () => api.compare(s.id, { preset: s.preset, scope: s.scope ?? undefined }),
    render(cmp) {
      s.compare = cmp;
      renderScopes();
      renderCompare();
    },
  });

  // ----- Start -----
  renderPresets();
  renderScopes();
  renderLegend();
  loadHead();
  loadAreas();
  loadCompare();

  createMap(el.map, { popupContent }).then((ctl) => {
    s.map = ctl;
    el.mapNote.hidden = true;
    el.layers.hidden = false;
    renderBusToggle();
    applyAreasToMap();
  }).catch((error) => {
    console.warn('[invest] map unavailable:', error?.message ?? error);
    el.mapNote.hidden = false;
    el.mapNote.textContent = tt('inv.city.map.unavailable');
    el.mapNote.dataset.i18n = 'inv.city.map.unavailable';
  });

  // Text built from data is rendered again in the new language; keyed static text is i18n.js's job.
  onLangChange(() => {
    renderPresets();
    renderScopes();
    renderLegend();
    s.map?.closePopups();
    if (s.city) renderHead();
    if (s.areas) renderBest();
    if (s.compare) renderCompare();
  });
}

if (globalThis.document) boot();
