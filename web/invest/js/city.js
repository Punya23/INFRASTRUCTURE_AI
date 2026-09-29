// City page: score summary, a hex map of the city's areas coloured by score, the best areas as a list
// (the keyboard and screen-reader way to reach the map), and a compare panel. Each section loads and
// fails on its own: a failed compare call leaves the map and the list working.

import { api } from './api.js';
import { bestAreas } from './areas.js';
import { meter, presetChips, rankMark, reasonChips, scoreRing, tierLabel } from './cards.js';
import { CITY_ID, DEFAULT_PRESET, PRESET_IDS } from './config.js';
import { formatCount, formatDelta, formatScore, tt } from './format.js';
import { createAreaMap, mapAvailable, RAMP } from './map.js';
import { loadPrefs, savePrefs } from './prefs.js';
import { i18nReady, renderShell } from './shell.js';
import { clear, errorKey, h, onLangChange, renderError, renderSkeleton, setStatus } from './ui.js';

renderShell();
await i18nReady;

const params = new URLSearchParams(window.location.search);
const cityId = params.get('c') ?? '';
const valid = CITY_ID.test(cityId);
if (!valid) window.location.replace('start.html');
let preset = PRESET_IDS.includes(params.get('preset')) ? params.get('preset') : DEFAULT_PRESET;

const $ = (id) => document.getElementById(id);
const els = {
  title: $('page-title'), badges: $('city-badges'), facts: $('city-facts'), presetBar: $('preset-bar'),
  presetDesc: $('preset-desc'), status: $('city-status'), summary: $('summary'), mapTitle: $('map-title'),
  map: $('map'), legend: $('legend'), toggles: $('toggles'), layerNote: $('layer-note'), best: $('best'),
  scope: $('scope'), compare: $('compare'),
};

const SCOPES = ['metros', 'peers', 'state', 'india'];
const LAYERS = ['stations', 'bus_stops', 'highways', 'toll_plazas'];

let meta = null;
let states = null;
let city = null;
let areas = null;
let compare = null;
let scope = null;         // null: the server's default for this city
let mapCtl = null;
let selectedId = null;
let requestId = 0;        // bumped when the preset changes: older answers are dropped
let compareSeq = 0;       // bumped on each compare request, so a slow older scope cannot overwrite a newer one
const layerOn = Object.fromEntries(LAYERS.map((l) => [l, false]));
const layerData = {};     // asset collections already fetched, per layer, for this city

const stateName = (code) => states?.find((s) => s.code === code)?.name ?? code;
const factorName = (id) => tt(`inv.factor.${id}`);

// ---------- header and summary ----------

function renderHead() {
  const name = city?.name ?? cityId;
  document.title = `${name} — ${tt('inv.title.suffix')}`;
  els.title.textContent = name;
  els.mapTitle.textContent = tt('inv.city.map', { city: name });
  clear(els.badges);
  clear(els.facts);
  if (city) {
    els.badges.append(
      h('span', { class: 'inv-badge' }, tierLabel(city.tier)),
      h('a', { href: `state.html?s=${encodeURIComponent(city.state)}&preset=${preset}` }, stateName(city.state)));
    const growth = city.factors?.built_up_growth?.value;
    els.facts.append(
      h('span', null, tt('inv.city.population', { n: formatCount(city.population) })),
      Number.isFinite(growth) ? h('span', null, tt('inv.city.growth', { pp: Math.round(growth) })) : null,
      h('span', null, city.data?.bus ? tt('inv.city.bus', { operator: city.data.bus.operator }) : tt('inv.city.nobus')));
  }
  clear(els.presetBar);
  els.presetBar.append(...presetChips(preset, pickPreset));
  els.presetDesc.textContent = tt(`inv.preset.${preset}.desc`);
}

function renderSummary() {
  if (!city || !meta) return;
  clear(els.summary);
  const coverage = city.coverage < 1 ? tt('inv.state.coverage', { pct: Math.round(city.coverage * 100) }) : null;
  els.summary.append(h('div', { class: 'inv-card inv-stack' },
    h('div', { class: 'inv-citycard__head' },
      scoreRing(city.score, { large: true }),
      h('div', { class: 'inv-citycard__meters', style: { flex: '1 1 14rem' } },
        meter('inv.group.access', city.access), meter('inv.group.momentum', city.momentum))),
    h('div', { class: 'inv-cluster' }, reasonChips(city.drivers.slice(0, 3), 'why', meta)),
    city.gaps.length
      ? h('div', { class: 'inv-cluster' }, h('span', { class: 'inv-small inv-muted' }, tt('inv.watch')), reasonChips(city.gaps.slice(0, 2), 'gap', meta))
      : null,
    coverage ? h('p', { class: 'inv-small inv-muted' }, coverage) : null));
}

// ---------- map, legend, layers ----------

function popupContent(p) {
  const why = reasonChips((p.d ?? []).slice(0, 3), 'why', meta);
  const gaps = reasonChips((p.g ?? []).slice(0, 2), 'gap', meta);
  return h('div', { class: 'inv-stack inv-stack--tight' },
    h('div', { class: 'inv-popup__title' }, p.name || tt('inv.area.unnamed')),
    h('div', null, `${tt('inv.area.score', { n: formatScore(p.score) })} · ${tt('inv.area.pop', { n: formatCount(p.pop) })}`),
    h('div', { class: 'inv-small inv-muted' }, tt('inv.area.rank', { rank: p.rank, total: areas.features.length })),
    Number.isFinite(p.bus_stops) ? h('div', { class: 'inv-small inv-muted' }, tt('inv.area.bus', { n: p.bus_stops })) : null,
    p.elig ? null : h('div', { class: 'inv-small inv-muted' }, tt('inv.area.outside')),
    why.length ? h('div', { class: 'inv-popup__label' }, tt('inv.area.top')) : null,
    why.length ? h('div', { class: 'inv-cluster' }, why) : null,
    gaps.length ? h('div', { class: 'inv-popup__label' }, tt('inv.area.gaps')) : null,
    gaps.length ? h('div', { class: 'inv-cluster' }, gaps) : null);
}

function renderLegend() {
  clear(els.legend);
  if (!mapCtl) return;
  els.legend.append(
    h('strong', null, tt('inv.city.legend')),
    h('div', { class: 'inv-legend__ramp', 'aria-hidden': true }, RAMP.map((c) => h('i', { style: { background: c } }))),
    h('div', { class: 'inv-legend__ends' }, h('span', null, tt('inv.city.legend.low')), h('span', null, tt('inv.city.legend.high'))));
}

function renderToggles() {
  clear(els.toggles);
  els.toggles.append(...LAYERS.map((name) => {
    const disabled = name === 'bus_stops' && !city?.data?.bus;
    return h('label', { class: 'inv-toggle' },
      h('input', { type: 'checkbox', checked: layerOn[name], disabled: disabled || !mapCtl, onchange: (e) => toggleLayer(name, e.target) }),
      h('span', null, tt(`inv.layer.${name}`)));
  }));
}

async function toggleLayer(name, input) {
  if (!mapCtl) return;
  if (!input.checked) {
    layerOn[name] = false;
    mapCtl.setAssetLayer(name, false);
    return;
  }
  const mine = requestId;
  try {
    if (!layerData[name]) {
      els.layerNote.textContent = tt('inv.layer.loading');
      const assets = await api.assets(cityId, [name]);
      if (mine !== requestId) return;
      layerData[name] = assets[name] ?? null;
    }
    els.layerNote.textContent = '';
    if (!layerData[name]) { input.checked = false; return; } // this city has no such layer (no bus feed)
    layerOn[name] = true;
    mapCtl.setAssetLayer(name, true, layerData[name]);
  } catch (error) {
    input.checked = false;
    els.layerNote.textContent = tt(errorKey(error));
  }
}

function showMapUnavailable() {
  clear(els.map);
  els.map.append(h('p', { class: 'inv-map__note inv-muted' }, tt('inv.city.map.unavailable')));
}

async function initMap() {
  mapCtl?.destroy();
  mapCtl = null;
  clear(els.map);
  if (!areas) return;
  const mine = requestId;
  if (!mapAvailable()) {
    showMapUnavailable();
  } else {
    try {
      const ctl = await createAreaMap(els.map, areas, {
        popupContent,
        onSelect: (id) => { selectedId = id; renderBest(); },
      });
      if (mine !== requestId) { ctl.destroy(); return; }
      mapCtl = ctl;
      // layers the visitor had on before a preset change come back (their data is cached)
      for (const name of LAYERS) if (layerOn[name] && layerData[name]) mapCtl.setAssetLayer(name, true, layerData[name]);
    } catch {
      if (mine !== requestId) return;
      showMapUnavailable();
    }
  }
  renderLegend();
  renderToggles();
  renderBest();
}

// ---------- best areas ----------

function renderBest() {
  if (!areas || !meta) return; // keeps the skeleton until both have arrived
  clear(els.best);
  const rows = bestAreas(areas.features, 10);
  if (rows.length === 0) { els.best.append(h('p', { class: 'inv-muted' }, tt('inv.compare.empty'))); return; }
  els.best.append(h('ol', { class: 'inv-best inv-list' }, rows.map((f, i) => {
    const p = f.properties;
    const name = p.name || tt('inv.area.unnamed');
    const body = [
      rankMark(i + 1),
      h('span', { class: 'inv-stack inv-stack--tight' },
        h('strong', null, name),
        h('span', { class: 'inv-cluster' }, reasonChips((p.d ?? []).slice(0, 2), 'why', meta))),
      scoreRing(p.score),
    ];
    // without a map there is nothing to fly to, so the rows are plain text
    return h('li', null, mapCtl
      ? h('button', { class: 'inv-best__row', type: 'button', 'aria-current': String(p.id === selectedId), 'aria-label': tt('inv.city.best.show', { name }), onclick: () => mapCtl.flyToArea(p.id) }, body)
      : h('div', { class: 'inv-best__row' }, body));
  })));
}

// ---------- compare ----------

function renderCompare() {
  if (!compare) return;
  clear(els.scope);
  clear(els.compare);
  els.scope.append(...SCOPES.map((s) => h('button', {
    class: 'inv-chip inv-chip--choice', type: 'button', 'aria-pressed': String(s === compare.scope),
    dataset: { i18n: `inv.scope.${s}` }, onclick: () => setScope(s),
  }, tt(`inv.scope.${s}`))));
  const chip = (kind, r) => h('span', { class: `inv-chip inv-chip--${kind}` },
    tt('inv.compare.better', { factor: factorName(r.factor), delta: formatDelta(r.delta) }));
  els.compare.append(h('div', { class: 'inv-stack' },
    h('p', null, h('strong', null, tt('inv.compare.here', { rank: compare.base_rank, total: compare.total + 1 }))),
    compare.others.length === 0
      ? h('p', { class: 'inv-muted' }, tt('inv.compare.empty'))
      : h('ul', { class: 'inv-compare inv-list' }, compare.others.map((o) => h('li', null,
        h('a', { class: 'inv-compare__row', href: `city.html?c=${encodeURIComponent(o.id)}&preset=${preset}`, 'aria-label': tt('inv.compare.open', { city: o.name }) },
          h('span', { class: 'inv-compare__top' },
            h('strong', null, o.name),
            h('span', { class: `inv-delta${o.delta > 0 ? ' inv-delta--up' : ''}` }, formatDelta(o.delta))),
          h('span', { class: 'inv-small inv-muted' }, `${stateName(o.state)} · ${tierLabel(o.tier)} · ${tt('inv.area.score', { n: formatScore(o.score) })}`),
          h('span', { class: 'inv-cluster' }, [...o.better.map((r) => chip('why', r)), ...o.worse.map((r) => chip('gap', r))])))))));
}

// ---------- loading ----------

function notFound() {
  document.title = `${tt('inv.city.notfound.title')} — ${tt('inv.title.suffix')}`;
  els.title.textContent = tt('inv.city.notfound.title');
  ['badges', 'facts', 'presetBar', 'summary', 'best', 'scope', 'compare', 'legend', 'toggles', 'map'].forEach((k) => clear(els[k]));
  els.presetDesc.textContent = '';
  els.summary.append(h('div', { class: 'inv-empty inv-stack' },
    h('p', null, tt('inv.city.notfound.body')),
    h('a', { class: 'inv-btn inv-btn--primary', href: 'start.html' }, tt('inv.state.pick'))));
}

async function loadCity(mine) {
  renderSkeleton(els.summary, 2);
  try {
    const [m, c] = await Promise.all([meta ?? api.meta(), api.city(cityId, { preset })]);
    if (mine !== requestId) return;
    meta = m;
    city = c;
  } catch (error) {
    if (mine !== requestId) return;
    if (error?.code === 'not_found') { notFound(); return; }
    renderError(els.summary, error, () => loadCity(requestId));
    return;
  }
  if (!states) {
    api.states().then((s) => { states = s.states; renderHead(); renderCompare(); }).catch(() => {});
  }
  renderHead();
  renderSummary();
  renderBest();
  renderToggles();
  setStatus(els.status, tt('inv.city.map', { city: city.name }));
}

async function loadAreas(mine) {
  renderSkeleton(els.best, 3);
  try {
    const a = await api.areas(cityId, { preset, limit: 1000 });
    if (mine !== requestId) return;
    areas = a;
  } catch (error) {
    if (mine !== requestId || error?.code === 'not_found') return; // a missing city is loadCity's page to show
    renderError(els.best, error, () => loadAreas(requestId));
    return;
  }
  renderBest(); // the list does not wait for the map: it is the way in when the map is slow or missing
  await initMap();
}

async function loadCompare(mine) {
  const seq = ++compareSeq;
  renderSkeleton(els.compare, 3);
  try {
    const answer = await api.compare(cityId, { preset, ...(scope ? { scope } : {}) });
    if (mine !== requestId || seq !== compareSeq) return;
    compare = answer;
    scope = compare.scope;
  } catch (error) {
    if (mine !== requestId || seq !== compareSeq || error?.code === 'not_found') return;
    clear(els.scope);
    renderError(els.compare, error, () => loadCompare(requestId));
    return;
  }
  renderCompare();
}

function load() {
  const mine = ++requestId;
  Promise.all([loadCity(mine), loadAreas(mine), loadCompare(mine)]);
}

function pickPreset(next) {
  if (next === preset) return;
  preset = next;
  window.history.replaceState(null, '', `?c=${encodeURIComponent(cityId)}&preset=${preset}`);
  savePrefs({ ...loadPrefs(), preset });
  selectedId = null;
  load();
}

function setScope(next) {
  if (next === scope) return;
  scope = next;
  loadCompare(requestId);
}

if (valid) {
  renderHead();
  load();
  onLangChange(() => { renderHead(); renderSummary(); renderLegend(); renderToggles(); renderBest(); renderCompare(); });
}
