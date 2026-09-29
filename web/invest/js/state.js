// State result: the top five cities of a state under the chosen preset, each with its score, the two
// group meters, why-chips built from the real numbers, one watch-out and the best area. An aside compares
// the leading city with other metros. Every failure has a visible state; nothing is scored as zero.

import { api } from './api.js';
import { bestAreaText, meter, presetChips, rankMark, reasonChips, scoreRing, tierLabel } from './cards.js';
import { DEFAULT_PRESET, PRESET_IDS, STATE_CODE } from './config.js';
import { formatCount, formatDelta, tt } from './format.js';
import { loadPrefs, savePrefs } from './prefs.js';
import { i18nReady, renderShell } from './shell.js';
import { clear, h, onLangChange, renderError, renderSkeleton, setStatus } from './ui.js';

renderShell();
await i18nReady;

const params = new URLSearchParams(window.location.search);
const code = params.get('s') ?? '';
const valid = STATE_CODE.test(code);
if (!valid) {
  window.location.replace('start.html'); // nothing sensible to show without a state
}
let preset = PRESET_IDS.includes(params.get('preset')) ? params.get('preset') : DEFAULT_PRESET;

const titleEl = document.getElementById('page-title');
const subEl = document.getElementById('page-sub');
const presetBar = document.getElementById('preset-bar');
const presetDesc = document.getElementById('preset-desc');
const listStatus = document.getElementById('list-status');
const citiesBox = document.getElementById('cities');
const aside = document.getElementById('aside');
const asideBody = document.getElementById('aside-body');

let meta = null;
let states = null;
let result = null;   // the stateCities answer for the current preset
let compare = null;  // the compare answer for the leading city
let requestId = 0;   // a newer request makes an older answer irrelevant

const stateName = () => states?.find((s) => s.code === code)?.name ?? code;

function renderHeading() {
  const name = stateName();
  document.title = `${tt('inv.state.title', { state: name })} — ${tt('inv.title.suffix')}`;
  titleEl.textContent = tt('inv.state.title', { state: name });
  subEl.textContent = result && result.total > 0
    ? tt('inv.state.sub', { preset: tt(`inv.preset.${preset}`), n: result.total }) : '';
  clear(presetBar);
  presetBar.append(...presetChips(preset, pickPreset));
  presetDesc.textContent = tt(`inv.preset.${preset}.desc`);
}

function cityCard(city) {
  const gap = reasonChips(city.gaps.slice(0, 1), 'gap', meta);
  const best = bestAreaText(city.best_area, 'inv.state');
  const coverage = city.coverage < 1 ? tt('inv.state.coverage', { pct: Math.round(city.coverage * 100) }) : null;
  return h('article', { class: 'inv-card inv-card--lift inv-citycard' },
    h('div', { class: 'inv-citycard__head' },
      rankMark(city.rank),
      h('div', { class: 'inv-citycard__title inv-stack inv-stack--tight' },
        h('h3', null, h('a', { href: `city.html?c=${encodeURIComponent(city.id)}&preset=${preset}` }, city.name)),
        h('div', { class: 'inv-cluster' },
          h('span', { class: 'inv-badge' }, tierLabel(city.tier)),
          h('span', { class: 'inv-small inv-muted' }, tt('inv.city.population', { n: formatCount(city.population) })))),
      scoreRing(city.score)),
    h('div', { class: 'inv-citycard__meters' },
      meter('inv.group.access', city.access), meter('inv.group.momentum', city.momentum)),
    h('div', { class: 'inv-cluster' }, reasonChips(city.drivers.slice(0, 3), 'why', meta)),
    gap.length ? h('div', { class: 'inv-cluster' }, h('span', { class: 'inv-small inv-muted' }, tt('inv.watch')), gap) : null,
    h('div', { class: 'inv-citycard__foot' },
      h('span', { class: 'inv-small inv-muted' }, [best, coverage].filter(Boolean).join(' · ')),
      h('a', { class: 'inv-btn inv-btn--secondary', href: `city.html?c=${encodeURIComponent(city.id)}&preset=${preset}` },
        tt('inv.state.explore', { city: city.name }))));
}

function renderCities() {
  clear(citiesBox);
  if (!result) return;
  if (result.total === 0) {
    citiesBox.append(h('div', { class: 'inv-empty inv-stack' },
      h('h2', { style: { 'font-size': 'var(--fs-lg)' } }, tt('inv.state.none.title', { state: stateName() })),
      h('p', null, tt('inv.state.none.body')),
      h('a', { class: 'inv-btn inv-btn--primary', href: 'start.html' }, tt('inv.state.pick'))));
    return;
  }
  if (result.cities.length < 5) {
    const n = result.cities.length;
    citiesBox.append(h('p', { class: 'inv-muted' }, n === 1 ? tt('inv.state.few.one', { state: stateName() }) : tt('inv.state.few', { n, state: stateName() })));
  }
  citiesBox.append(...result.cities.map(cityCard));
}

function renderAside() {
  if (!compare || compare.others.length === 0) { aside.hidden = true; return; }
  aside.hidden = false;
  clear(asideBody);
  asideBody.append(h('ul', { class: 'inv-compare inv-list' }, ...compare.others.map((o) => h('li', null,
    h('a', { class: 'inv-compare__row', href: `city.html?c=${encodeURIComponent(o.id)}&preset=${preset}` },
      h('span', { class: 'inv-compare__top' },
        h('strong', null, o.name),
        h('span', { class: `inv-delta${o.delta > 0 ? ' inv-delta--up' : ''}` }, formatDelta(o.delta))),
      h('span', { class: 'inv-small inv-muted' }, `${tierLabel(o.tier)} · ${tt('inv.score.aria', { n: Math.round(o.score) })}`))))));
}

function renderAll() {
  renderHeading();
  renderCities();
  renderAside();
  if (result) setStatus(listStatus, tt('inv.state.sub', { preset: tt(`inv.preset.${preset}`), n: result.total }));
}

function notFound() {
  document.title = `${tt('inv.state.notfound.title')} — ${tt('inv.title.suffix')}`;
  titleEl.textContent = tt('inv.state.notfound.title');
  subEl.textContent = '';
  presetBar.replaceChildren();
  presetDesc.textContent = '';
  aside.hidden = true;
  clear(citiesBox);
  citiesBox.append(h('div', { class: 'inv-empty inv-stack' },
    h('p', null, tt('inv.state.notfound.body')),
    h('a', { class: 'inv-btn inv-btn--primary', href: 'start.html' }, tt('inv.state.pick'))));
}

async function load() {
  const mine = ++requestId;
  renderSkeleton(citiesBox, 3);
  aside.hidden = true;
  let cities;
  try {
    const [m, s, c] = await Promise.all([
      meta ?? api.meta(),
      states ? { states } : api.states(),
      api.stateCities(code, { preset, limit: 5 }),
    ]);
    meta = m;
    states = s.states;
    cities = c;
  } catch (error) {
    if (mine !== requestId) return;
    if (error?.code === 'not_found') { notFound(); return; }
    renderHeading();
    renderError(citiesBox, error, load);
    return;
  }
  if (mine !== requestId) return;
  if (!states.some((s) => s.code === code)) { notFound(); return; }
  result = cities;
  compare = null;
  renderAll();
  if (result.cities[0]) loadCompare(mine, result.cities[0].id);
}

// The aside is a bonus: when it fails the page keeps everything else.
async function loadCompare(mine, cityId) {
  try {
    const answer = await api.compare(cityId, { preset, scope: 'metros', limit: 3 });
    if (mine !== requestId) return;
    compare = answer;
    renderAside();
  } catch {
    aside.hidden = true;
  }
}

function pickPreset(next) {
  if (next === preset) return;
  preset = next;
  window.history.replaceState(null, '', `?s=${encodeURIComponent(code)}&preset=${preset}`);
  savePrefs({ ...loadPrefs(), preset });
  load();
}

if (valid) {
  renderHeading();
  load();
  onLangChange(() => { if (result) renderAll(); else renderHeading(); });
}
