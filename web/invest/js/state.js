// State result page: the best-placed cities in one state for one preset (spec section 4, step 3).
// The pure helpers at the top are unit-tested (state.test.mjs); the DOM code below runs only in a
// page that has #state-main, so importing this file in Node has no side effects.

import { DEFAULT_PRESET, PRESET_IDS, STATE_CODE } from './config.js';
import { api } from './api.js';
import { explain } from './explain.js';
import { formatCount, formatDelta, formatScore, tt } from './format.js';
import { loadPrefs } from './prefs.js';
import { clear, errorKey, h, onLangChange, renderError, renderSkeleton, setStatus, setStatusKey } from './ui.js';

const TOP_N = 5;       // cards asked for; a state with fewer cities shows fewer
const COMPARE_N = 3;   // rows in "Other metros to compare"
const MAX_WHY = 3;     // why-chips per card
const TIERS = new Set(['metro', 'large', 'mid']);

// ---------- pure helpers ----------

// { code, preset } from the address bar, or null when either is malformed (the page then goes back to
// start.html). A missing preset falls back to the visitor's saved one; a present but unknown one does not.
export function readParams(search, fallbackPreset = DEFAULT_PRESET) {
  const query = new URLSearchParams(search);
  const code = query.get('s') ?? '';
  const preset = query.has('preset') ? query.get('preset') : fallbackPreset;
  return STATE_CODE.test(code) && PRESET_IDS.includes(preset) ? { code, preset } : null;
}

// 'empty' (nothing to show), 'few' (the state has fewer than five cities) or 'full'.
export function listMode(total, shown) {
  if (!(shown > 0)) return 'empty';
  return total < TOP_N ? 'few' : 'full';
}

// Up to three why-chips as { key, params } from the city's drivers. A driver whose value could not be
// measured is not a reason, so it is left out rather than shown as "could not be measured".
export function whyChips(city, meta) {
  return (city.drivers ?? [])
    .map((driver) => explain('why', driver, meta))
    .filter((chip) => !chip.unknown)
    .slice(0, MAX_WHY);
}

// The single watch-out (the API lists the weakest factor first), or null when there is none.
export function gapChip(city, meta) {
  const gap = city.gaps?.[0];
  return gap ? explain('gap', gap, meta) : null;
}

// { key, params } for the best-area line, or null when the city has no eligible area. An unnamed area
// (46% of them) is described by the city it lies in; the card has no nearer place to name.
export function bestAreaLine(city) {
  const area = city.best_area;
  if (!area) return null;
  const score = formatScore(area.score);
  return area.name
    ? { key: 'inv.state.bestArea', params: { name: area.name, score } }
    : { key: 'inv.state.bestAreaUnnamed', params: { city: city.name, score } };
}

// What a meter shows for a 0-100 value: a fill, the text, and whether the factor was not observed.
export function meterView(x) {
  const known = Number.isFinite(x);
  return { unknown: !known, value: known ? Math.min(100, Math.max(0, x)) : 0, text: formatScore(x) };
}

// The share of the score's weight that was observed, as a whole percent, or null when it is all of it
// (or unknown). Never 100 for a partial coverage, so "99%" is the most a note can say.
export function coveragePct(coverage) {
  if (!Number.isFinite(coverage) || coverage >= 1) return null;
  return Math.min(99, Math.max(0, Math.round(coverage * 100)));
}

// Hands out a number per load; only the newest number is current, so an answer that arrives after a
// newer request was made can be told apart and dropped.
export function latestOnly() {
  let latest = 0;
  return { next: () => ++latest, isCurrent: (id) => id === latest, current: () => latest };
}

// ---------- page ----------

const $ = (id) => document.getElementById(id);

// English (and the visitor's language) may still be loading when the API answers; painting then would
// show raw keys. The first infra-ai-lang-change event paints instead.
const dictionaryReady = () => !globalThis.InfraI18n || globalThis.InfraI18n.t('inv.disclaimer') != null;

const view = {
  code: '',
  preset: DEFAULT_PRESET, // the preset whose cards are on screen (the chips show it too)
  mode: 'loading',        // loading | ok | notfound
  ref: null,              // { meta, names } fetched once
  data: null,             // /v1/states/{code}/cities
  compare: null,          // { status: 'loading' | 'ok' | 'error', data?, error? }
};
const loads = latestOnly(); // an answer for an older load is dropped

const stateName = () => view.ref?.names.get(view.code) ?? view.code;
const cityHref = (id) => `city.html?c=${encodeURIComponent(id)}&preset=${encodeURIComponent(view.preset)}`;

function meter(labelKey, score) {
  const m = meterView(score);
  return h('div', { class: `inv-meter${m.unknown ? ' inv-meter--unknown' : ''}`, style: { '--value': m.value } },
    h('span', { class: 'inv-meter__label' }, tt(labelKey)),
    h('span', { class: 'inv-meter__value' }, m.text),
    h('span', { class: 'inv-meter__bar', 'aria-hidden': true }));
}

function cityCard(city) {
  const { meta } = view.ref;
  const why = whyChips(city, meta).map((c) => h('li', null, h('span', { class: 'inv-chip inv-chip--why' }, tt(c.key, c.params))));
  const gap = gapChip(city, meta);
  const area = bestAreaLine(city);
  const pct = coveragePct(city.coverage);
  return h('li', { class: 'inv-card inv-card--lift state-card' },
    h('div', { class: 'state-card__head' },
      h('span', { class: `inv-rank${city.rank === 1 ? ' inv-rank--top' : ''}`, role: 'img', 'aria-label': tt('inv.state.rank', { n: city.rank }) }, String(city.rank)),
      h('div', { class: 'state-card__who' },
        h('h2', null, city.name),
        h('p', { class: 'inv-small inv-muted' }, stateName(), ' · ', tt('inv.state.people', { n: formatCount(city.population) })),
        TIERS.has(city.tier) ? h('span', { class: 'inv-badge' }, tt(`inv.tier.${city.tier}`)) : null),
      h('div', { class: 'inv-ring', style: { '--value': meterView(city.score).value }, role: 'img', 'aria-label': tt('inv.state.score', { score: formatScore(city.score) }) },
        h('span', { class: 'inv-ring__value' }, formatScore(city.score)))),
    h('div', { class: 'state-card__meters' }, meter('inv.group.access', city.access), meter('inv.group.momentum', city.momentum)),
    why.length
      ? h('ul', { class: 'inv-list state-why' }, why)
      : h('p', { class: 'inv-small inv-muted' }, tt('inv.state.whyNone')),
    // The watch-out differs from a why-chip by shape (a squarer box with a hollow hexagon and dashed
    // edge, see state.css) and by its visible "Watch-out" label, not by tint alone.
    gap ? h('p', { class: 'inv-chip inv-chip--gap state-gap' },
      h('span', { class: 'state-gap__label' }, tt('inv.state.watch')),
      h('span', null, tt(gap.key, gap.params))) : null,
    area ? h('p', { class: 'inv-small' }, tt(area.key, area.params)) : null,
    pct != null ? h('p', { class: 'inv-small inv-muted' }, tt('inv.state.coverage', { pct })) : null,
    h('a', { class: 'inv-btn inv-btn--secondary state-card__go', href: cityHref(city.id) }, tt('inv.state.explore', { city: city.name })));
}

function paintHeading() {
  const named = view.mode === 'ok';
  $('state-title').textContent = named ? tt('inv.state.heading', { state: stateName() }) : tt('inv.state.headingPlain');
  document.title = named ? tt('inv.state.docTitle', { state: stateName() }) : tt('inv.state.headingPlain') + ' · INFRA-AI';
  const active = view.preset;
  for (const button of $('presets').querySelectorAll('button')) {
    button.setAttribute('aria-pressed', String(button.dataset.preset === active));
  }
  $('preset-desc').textContent = tt(`inv.preset.${active}.desc`);
}

function paintResults() {
  const box = $('state-results');
  const summary = $('state-summary');
  const chooser = h('a', { class: 'inv-btn inv-btn--primary', href: 'start.html' }, tt('inv.state.choose'));
  const { cities, total } = view.data ?? { cities: [], total: 0 };
  const mode = view.mode === 'ok' ? listMode(total, cities.length) : 'notfound';
  const params = { state: stateName(), n: formatCount(mode === 'few' ? total : cities.length), total: formatCount(total) };
  clear(box);
  summary.textContent = '';
  // the aside and the preset chips only make sense next to at least one city
  const withCities = mode === 'few' || mode === 'full';
  $('state-aside').hidden = !withCities;
  $('preset-group').hidden = !withCities;
  document.querySelector('.state-split').toggleAttribute('data-single', !withCities);

  if (mode === 'notfound') {
    box.append(h('div', { class: 'inv-empty inv-stack' }, h('p', null, tt('inv.error.not_found')), chooser));
    setStatusKey($('state-status'), 'inv.error.not_found');
  } else if (mode === 'empty') {
    box.append(h('div', { class: 'inv-empty inv-stack' },
      h('h2', null, tt('inv.state.empty.title', params)),
      h('p', null, tt('inv.state.empty.body')),
      chooser));
    setStatus($('state-status'), tt('inv.state.empty.title', params));
  } else {
    summary.textContent = mode === 'few'
      ? tt(total === 1 ? 'inv.state.few.one' : 'inv.state.few', params)
      : tt('inv.state.summary', params);
    box.append(h('ol', { class: 'inv-list state-list' }, cities.map(cityCard)));
    setStatus($('state-status'), tt('inv.state.status', { n: cities.length }));
  }
}

function paintAside() {
  const body = $('aside-body');
  const top = view.data?.cities?.[0];
  if (!dictionaryReady() || !top || !view.compare) return;
  $('aside-sub').textContent = tt('inv.state.compare.sub', { city: top.name, state: stateName() });
  const { status, data, error } = view.compare;
  if (status === 'loading') return renderSkeleton(body, 3);
  if (status === 'error') return renderError(body, error, () => loadCompare(top.id, view.preset, loads.current()));
  clear(body);
  if (!data.others?.length) {
    body.append(h('p', { class: 'inv-muted' }, tt('inv.state.compare.none')));
    return;
  }
  body.append(h('ol', { class: 'inv-list state-compare' }, data.others.map((other) =>
    h('li', null, h('a', { class: 'state-compare__row', href: cityHref(other.id) },
      h('span', { class: 'state-compare__name' },
        h('strong', null, other.name),
        h('span', { class: 'inv-small inv-muted' }, view.ref.names.get(other.state) ?? other.state)),
      h('span', { class: 'state-compare__nums' },
        h('span', { class: 'inv-num state-compare__score' }, formatScore(other.score)),
        h('span', { class: `inv-delta${other.delta > 0 ? ' inv-delta--up' : ''}` },
          tt('inv.state.deltaVs', { delta: formatDelta(other.delta), city: top.name }))))))));
}

function paint() {
  if (!dictionaryReady()) return;
  paintHeading();
  if (view.mode === 'loading') return;
  paintResults();
  if (view.mode === 'ok') paintAside();
}

async function ensureRef() {
  if (view.ref) return view.ref;
  const [meta, list] = await Promise.all([api.meta(), api.states()]);
  view.ref = { meta, names: new Map(list.states.map((s) => [s.code, s.name])) };
  return view.ref;
}

async function loadCompare(topId, preset, mine) {
  view.compare = { status: 'loading' };
  paintAside();
  try {
    // scope is explicit: the aside is titled "metros", which the API default only gives to a metro
    const data = await api.compare(topId, { preset, scope: 'metros', limit: COMPARE_N });
    if (loads.isCurrent(mine)) view.compare = { status: 'ok', data };
  } catch (error) {
    if (!loads.isCurrent(mine) || error.code === 'aborted') return;
    view.compare = { status: 'error', error };
  }
  if (loads.isCurrent(mine)) paintAside();
}

async function load(preset) {
  const mine = loads.next();
  const results = $('state-results');
  clear($('state-error'));
  $('presets').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.preset === preset)));
  if (view.data) results.setAttribute('aria-busy', 'true'); // keep the last good cards on screen
  else renderSkeleton(results, 3);
  setStatusKey($('state-status'), 'inv.loading');
  try {
    const [, data] = await Promise.all([ensureRef(), api.stateCities(view.code, { preset, limit: TOP_N })]);
    if (!loads.isCurrent(mine)) return;
    Object.assign(view, { mode: 'ok', preset, data, compare: null });
    results.removeAttribute('aria-busy');
    const url = new URL(location.href);
    url.searchParams.set('preset', preset);
    history.replaceState(null, '', url);
    paint();
    if (data.cities.length) loadCompare(data.cities[0].id, preset, mine);
  } catch (error) {
    if (!loads.isCurrent(mine) || error.code === 'aborted') return;
    results.removeAttribute('aria-busy');
    if (error.code === 'not_found' || error.code === 'bad_request') {
      Object.assign(view, { mode: 'notfound', data: null });
      paint();
      return;
    }
    if (!error.code) console.error(error);
    if (!view.data) clear(results);
    paint(); // puts the chips back on the preset that is still on screen
    renderError($('state-error'), error, () => load(preset));
    setStatusKey($('state-status'), errorKey(error)); // else the "Loading…" set above would stay announced
  }
}

function boot() {
  const params = readParams(location.search, loadPrefs().preset);
  if (!params) {
    location.replace('start.html');
    return;
  }
  view.code = params.code;
  view.preset = params.preset;
  for (const button of $('presets').querySelectorAll('button')) {
    button.addEventListener('click', () => load(button.dataset.preset));
  }
  onLangChange(paint);
  load(params.preset);
}

if (typeof document !== 'undefined' && document.getElementById('state-main')) boot();
