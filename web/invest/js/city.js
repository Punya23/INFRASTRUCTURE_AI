// City page (spec section 8): header, hex map of areas, best areas list, infrastructure layers and the
// comparison panel. The three data sections load in parallel and fail on their own: each has a
// skeleton, and an error slot with Retry that sits next to its last good view.
//
// The helpers under "Pure" run in Node (city.test.mjs); the page starts only when there is a document.

import { ApiError, api } from './api.js';
import { CITY_ID, DEFAULT_PRESET, PRESET_IDS } from './config.js';
import { explain } from './explain.js';
import { formatCount, formatDelta, formatScore, formatValue, tt } from './format.js';
import { loadPrefs } from './prefs.js';
import { ASSET_SOURCE, BREAKS, RAMP, cellCentre, createMap } from './map.js';
import { clear, errorKey, h, onLangChange, renderError, renderSkeleton, setStatus, setStatusKey } from './ui.js';

// ---------- Pure ----------

// An unnamed area borrows the name of the nearest named area within this distance; beyond it the label
// gives coordinates, because "near" a place 20 km away would mislead. About three H3 res-7 cells
// (team judgment, 2026-09-30).
export const NEAR_MAX_KM = 8;
export const BEST_AREAS = 10;
const MAX_ALIASES = 4;
export const SCOPES = ['metros', 'peers', 'state', 'india'];

// { id, preset } from the query string. A malformed id is null (the page shows not-found without a
// request). A missing preset falls back to the visitor's saved one; a present but unknown one is null
// and the page goes back to start.html, as the state page does: it is never quietly replaced.
export function readParams(search, fallbackPreset = DEFAULT_PRESET) {
  const params = new URLSearchParams(search);
  const id = params.get('c');
  const preset = params.has('preset') ? params.get('preset') : fallbackPreset;
  return {
    id: id !== null && CITY_ID.test(id) ? id : null,
    preset: PRESET_IDS.includes(preset) ? preset : null,
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

// Upcoming projects as map points: one per mode that has any, at that mode's city point, carrying the count
// (the badge size) and the mode. Nothing else is drawn from a project: the details are in the popup and list.
export function projectFeatures(projects) {
  const byMode = new Map();
  for (const p of projects ?? []) {
    if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon)) continue; // a project without a point is listed, never drawn
    const entry = byMode.get(p.mode) ?? { mode: p.mode, count: 0, lon: p.lon, lat: p.lat };
    entry.count += 1;
    byMode.set(p.mode, entry);
  }
  return {
    type: 'FeatureCollection',
    features: [...byMode.values()].map(({ mode, count, lon, lat }) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [lon, lat] }, properties: { mode, count },
    })),
  };
}

// The article's site, for "Source: …"; the link's own text when it is not a URL the browser can parse.
export function publisher(link) {
  try { return new URL(link).hostname.replace(/^www\./, ''); } catch { return String(link); }
}

// "12.5 km · ₹4,893 crore · 2 Apr 2026", only the parts the article states.
export function projectFacts(p, t = tt) {
  return [
    Number.isFinite(p.length_km) ? t('inv.city.projects.km', { n: formatValue(p.length_km) }) : null,
    Number.isFinite(p.cost_crore) ? t('inv.city.projects.crore', { n: formatCount(p.cost_crore) }) : null,
    p.event_date ? t('inv.city.projects.dated', { date: p.event_date }) : null,
  ].filter(Boolean).join(' · ');
}

// The collection an /assets answer holds for `source`. bus_stops may be null (the city has no bus
// feed: null is returned); anything else that is not a FeatureCollection fails closed.
export function assetCollection(data, source) {
  const collection = data?.[source];
  if (source === 'bus_stops' && collection === null) return null;
  if (collection?.type !== 'FeatureCollection' || !Array.isArray(collection.features)) {
    throw new ApiError('bad_response', `The server sent no ${source} collection`);
  }
  return collection;
}

// Attribution lines from the API's provenance (invariant 7: a licence is shown wherever its data is). Text
// only, null when the API sent nothing to show.
export const licenseLine = (city, t = tt) => (city?.license ? t('inv.city.license', { name: city.name, license: city.license }) : null);
export const busSourceLine = (source, t = tt) => (source?.operator && source.license
  ? t('inv.city.bus_source', { operator: source.operator, license: source.license, date: source.fetched_at })
  : null);

// Compare rows the page can link to: an id that fails the pattern is left out, never put in a link.
export const linkableCities = (others) => (others ?? []).filter((o) => typeof o?.id === 'string' && CITY_ID.test(o.id));

// True when an element is not wholly inside the viewport (so a scroll is needed to show it).
export const outOfView = (rect, viewportHeight) => rect.top < 0 || rect.bottom > viewportHeight;

// MapLibre's own UI text (its locale keys) in the page language.
export const mapStrings = (t = tt) => ({
  'Map.Title': t('inv.city.map.title'),
  'NavigationControl.ZoomIn': t('inv.city.map.zoom_in'),
  'NavigationControl.ZoomOut': t('inv.city.map.zoom_out'),
  'Popup.Close': t('inv.city.map.close'),
  'CooperativeGesturesHandler.WindowsHelpText': t('inv.city.map.gesture_ctrl'),
  'CooperativeGesturesHandler.MacHelpText': t('inv.city.map.gesture_cmd'),
  'CooperativeGesturesHandler.MobileHelpText': t('inv.city.map.gesture_touch'),
});

// ---------- Page ----------

function boot() {
  const $ = (id) => document.getElementById(id);
  const el = {
    main: $('city-main'), notFound: $('not-found'), status: $('city-status'),
    head: $('city-head'), headMsg: $('city-head-msg'), presets: $('city-presets'), presetDesc: $('city-preset-desc'),
    map: $('city-map'), mapNote: $('city-map-note'), legend: $('city-legend'), layers: $('city-layers'),
    layerMsg: $('city-layer-msg'), areasMsg: $('city-areas-msg'), best: $('city-best'), bestLoading: $('city-best-loading'),
    scopes: $('city-scopes'), compare: $('city-compare'), compareMsg: $('city-compare-msg'),
    license: $('city-license'), busSource: $('city-bus-source'),
    projects: $('city-projects'), projectsMsg: $('city-projects-msg'),
  };

  const params = readParams(location.search, loadPrefs().preset);
  if (!params.preset) return location.replace('start.html');
  const s = {
    id: params.id, preset: params.preset, scope: null,
    city: null, states: null, areas: null, places: new Map(), byId: new Map(), compare: null,
    map: null, fitted: false, busSource: null, projects: null, projectsOnMap: false,
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
  // run() resolves to true when it rendered, false when it failed, undefined when a newer run took over.
  function section({ body, msg, skeleton = body, rows, load, render, onError, decidesCity = false }) {
    let seq = 0;
    let hasData = false;
    const run = async () => {
      const mine = ++seq;
      msg.replaceChildren();
      if (hasData) body.setAttribute('aria-busy', 'true');
      else renderSkeleton(skeleton, rows);
      try {
        const data = await load();
        if (mine !== seq) return undefined;
        body.removeAttribute('aria-busy');
        if (skeleton !== body) clear(skeleton);
        hasData = true;
        render(data);
        return true;
      } catch (error) {
        if (mine !== seq || error?.code === 'aborted') return undefined;
        body.removeAttribute('aria-busy');
        if (!hasData || skeleton !== body) clear(skeleton); // never the last good view
        // a bug in this page, not a failed request: say so in the console, the visitor still gets Retry
        if (!(error instanceof ApiError)) console.error('[invest] city page:', error);
        // the id passed the pattern but no such city exists (or the server refused it). Only the header
        // request says so: a not_found from another section (an older API without that route) is that section's error.
        if (decidesCity && (error?.code === 'not_found' || error?.code === 'bad_request')) { showNotFound(); return false; }
        onError?.();
        renderError(msg, error, run);
        setStatusKey(el.status, errorKey(error)); // else a "Loading…" set by a preset switch stays announced
        return false;
      }
    };
    return run;
  }

  // ----- Header -----
  const stateName = (code) => s.states?.get(code) ?? code;

  const loadHead = section({
    body: el.head, msg: el.headMsg, rows: 3, decidesCity: true,
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
    const license = licenseLine(c);
    el.license.textContent = license ?? '';
    el.license.hidden = !license;
  }

  // The bus stops' own operator and licence, once the layer's data has arrived (the header only knows the operator).
  function renderBusSource() {
    const line = busSourceLine(s.busSource);
    el.busSource.textContent = line ?? '';
    el.busSource.hidden = !line;
  }

  // ----- Presets -----
  function renderPresets() {
    el.presets.replaceChildren(...PRESET_IDS.map((id) => h('button', {
      type: 'button', class: 'inv-chip inv-chip--choice', 'aria-pressed': String(id === s.preset),
      onclick: () => choosePreset(id),
    }, tt(`inv.preset.${id}`))));
    el.presetDesc.textContent = tt(`inv.preset.${s.preset}.desc`);
  }

  // All three sections follow the preset. If any of them cannot load it, the page goes back to the
  // preset it was showing and reloads the sections that had already switched (the API answers are
  // cacheable, so that is usually instant): chips, header, map, list and compare then agree again,
  // and the failed section keeps its error with Retry.
  async function choosePreset(id) {
    if (id === s.preset) return;
    const previous = s.preset;
    s.preset = id;
    syncUrl();
    renderPresets();
    setStatusKey(el.status, 'inv.loading');
    const loaders = [loadHead, loadAreas, loadCompare];
    const done = await Promise.all(loaders.map((load) => load()));
    if (s.preset !== id || !done.includes(false)) return; // a newer choice took over, or all is shown
    s.preset = previous;
    syncUrl();
    renderPresets();
    await Promise.all(loaders.filter((_, i) => done[i] === true).map((load) => load()));
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

  // A badge's popup: the headlines of that mode's projects, each with its article link.
  const projectsPopup = (mode) => {
    const mine = (s.projects?.projects ?? []).filter((p) => p.mode === mode);
    return h('div', { class: 'city-pop inv-stack--tight' },
      h('p', { class: 'city-pop__title' }, tt(`inv.city.projects.popup.${mode}`, { n: mine.length })),
      h('ul', { class: 'city-pop__list', role: 'list' }, mine.slice(0, 4).map((p) => h('li', { class: 'inv-small' },
        h('a', { href: p.source_ref, target: '_blank', rel: 'noopener noreferrer' }, p.name), ' · ', tt(`inv.city.projects.stage.${p.stage}`)))),
      mine.length > 4 ? h('p', { class: 'inv-small inv-muted' }, tt('inv.city.projects.popup.more', { n: mine.length - 4 })) : null);
  };

  const popupContent = (kind, idOrProps) => {
    if (kind === 'area') return areaPopup(idOrProps);
    if (ASSET_SOURCE[kind] === 'projects') return projectsPopup(idOrProps.mode);
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
      setStatusKey(el.status, 'inv.city.map.unavailable');
      return;
    }
    if (outOfView(el.map.getBoundingClientRect(), innerHeight)) {
      el.map.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    }
    s.map.showArea(feature);
    setStatus(el.status, tt('inv.city.best.shown', { name }));
  }

  function applyAreasToMap() {
    if (!s.map || !s.areas) return;
    s.map.setAreas(s.areas, { fit: !s.fitted });
    s.fitted = true;
  }

  const areasStatus = () => setStatus(el.status, tt('inv.city.areas_loaded', { n: formatCount(s.areas.length) }));

  const loadAreas = section({
    body: el.best, skeleton: el.bestLoading, msg: el.areasMsg, rows: 5,
    load: () => api.areas(s.id, { preset: s.preset, limit: 1000 }),
    render(collection) {
      s.areas = collection.features;
      s.byId = new Map(s.areas.map((f) => [f.properties.id, f]));
      s.places = areaPlaces(s.areas);
      renderBest();
      renderLegend();
      applyAreasToMap();
      areasStatus();
    },
  });

  // ----- Layers (lazy: each collection is fetched the first time one of its toggles is switched on) -----
  const assetLoads = new Map();
  function ensureAssets(source) {
    if (!assetLoads.has(source)) {
      const load = api.assets(s.id, [source]).then((data) => {
        const collection = assetCollection(data, source);
        if (collection) s.map.addAssets(source, collection);
        if (source === 'bus_stops') { s.busSource = data.bus_source ?? null; renderBusSource(); }
        return collection;
      });
      load.catch(() => assetLoads.delete(source)); // a later toggle tries again
      assetLoads.set(source, load);
    }
    return assetLoads.get(source);
  }

  // One error per layer, labelled with the layer's name, so switching one layer never hides another's.
  const layerErrors = new Map();
  function clearLayerError(layer) {
    layerErrors.get(layer)?.remove();
    layerErrors.delete(layer);
  }
  function showLayerError(input, error) {
    const slot = h('div', { class: 'city-layers__error' });
    renderError(slot, error, () => { input.checked = true; toggleLayer(input); });
    const box = h('div', null, h('p', { class: 'inv-small' }, input.closest('label').textContent.trim()), slot);
    clearLayerError(input.value);
    layerErrors.set(input.value, box);
    el.layerMsg.append(box);
  }

  async function toggleLayer(input) {
    const layer = input.value;
    clearLayerError(layer);
    if (!s.map) { input.checked = false; return; } // the toggles are hidden until the map is ready
    if (!input.checked) return s.map.setVisible(layer, false);
    if (ASSET_SOURCE[layer] === 'projects') return s.map.setVisible(layer, true); // already on the map: its toggle is enabled only then
    if (!s.map.hasAssets(ASSET_SOURCE[layer])) setStatusKey(el.status, 'inv.loading');
    let collection;
    try {
      collection = await ensureAssets(ASSET_SOURCE[layer]);
    } catch (error) {
      if (error?.code === 'aborted') return;
      if (!(error instanceof ApiError)) console.error('[invest] city page:', error);
      input.checked = false;
      showLayerError(input, error);
      return;
    }
    if (collection === null) { // the server says this city has no bus feed after all
      s.noBusFeed = true;
      input.checked = false;
      renderBusToggle();
      return;
    }
    s.map.setVisible(layer, input.checked); // it may have been switched off while loading
    setStatus(el.status, '');
  }

  function renderBusToggle() {
    const input = el.layers.querySelector('input[value="bus_stops"]');
    const note = $('city-bus-note');
    // only a loaded city can say it has no feed; until then the toggle stays usable (an empty layer at worst)
    const none = s.noBusFeed || (s.city ? !s.city.data?.bus : false);
    input.disabled = none || !s.map;
    note.hidden = !none;
  }

  el.layers.addEventListener('change', (event) => { if (event.target.matches('input')) toggleLayer(event.target); });

  // ----- Upcoming projects: a list under the map, and one badge per mode on it -----
  function renderProjects() {
    const list = s.projects?.projects ?? [];
    const name = s.city?.name ?? s.id;
    el.projects.replaceChildren(...(list.length ? list.map((p) => h('li', { class: 'city-projects__item' },
      h('div', { class: 'inv-cluster' },
        h('span', { class: 'inv-badge' }, tt(`inv.city.projects.mode.${p.mode}`)),
        h('span', { class: 'inv-chip' }, tt(`inv.city.projects.stage.${p.stage}`))),
      h('p', { class: 'city-projects__name' }, h('a', { href: p.source_ref, target: '_blank', rel: 'noopener noreferrer' }, p.name)),
      p.evidence === p.name ? null : h('blockquote', { class: 'city-projects__quote inv-small' }, `“${p.evidence}”`), // the headline is the quote when it is all the text there is
      h('p', { class: 'inv-small inv-muted' }, [projectFacts(p), tt('inv.city.projects.source', { source: publisher(p.source_ref), license: p.license })].filter(Boolean).join(' · '))))
      : [h('li', { class: 'inv-empty' }, tt('inv.city.projects.empty', { name }))]));
  }

  // Draws the badges once both the map and the projects are there, whichever arrives last. A mode with none stays
  // disabled; the others are switched on, because showing them is the point of the layer.
  function applyProjectsToMap() {
    if (!s.map || !s.projects || s.projectsOnMap) return;
    s.projectsOnMap = true;
    const fc = projectFeatures(s.projects.projects);
    if (!fc.features.length) return;
    s.map.addAssets('projects', fc);
    for (const { properties: { mode } } of fc.features) {
      const input = el.layers.querySelector(`input[value="projects-${mode}"]`);
      input.disabled = false;
      input.checked = true;
      s.map.setVisible(`projects-${mode}`, true);
    }
  }

  const loadProjects = section({
    body: el.projects, msg: el.projectsMsg, rows: 2,
    load: () => api.projects(s.id),
    render(data) {
      s.projects = data;
      renderProjects();
      applyProjectsToMap();
    },
  });

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
    const others = linkableCities(cmp.others);
    if (!others.length) {
      el.compare.replaceChildren(h('p', { class: 'inv-empty' }, tt('inv.city.compare.empty')));
      return;
    }
    el.compare.replaceChildren(
      h('p', { class: 'city-cmp__here' }, tt('inv.city.compare.here', { rank: cmp.base_rank, total: cmp.total + 1 })),
      h('p', { class: 'inv-small inv-muted' }, tt('inv.city.compare.note', { name: base })),
      h('ol', { class: 'city-cmp__list', role: 'list' }, others.map((o) => {
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
      s.scope = cmp.scope;
      renderScopes();
      renderCompare();
    },
    // the chips go back to the scope the rows below still show
    onError() {
      s.scope = s.compare?.scope ?? null;
      renderScopes();
    },
  });

  // ----- Start -----
  renderPresets();
  renderScopes();
  renderLegend();
  loadHead();
  loadAreas();
  loadCompare();
  loadProjects();

  createMap(el.map, { popupContent, strings: () => mapStrings() }).then((ctl) => {
    s.map = ctl;
    ctl.relabel(); // the language may have been applied while the map was still loading
    el.mapNote.hidden = true;
    el.layers.hidden = false;
    renderBusToggle();
    applyAreasToMap();
    applyProjectsToMap();
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
    s.map?.relabel();
    if (s.city) renderHead();
    renderBusSource();
    if (s.areas) { renderBest(); areasStatus(); }
    if (s.compare) renderCompare();
    if (s.projects) renderProjects();
  });
}

if (globalThis.document) boot();
