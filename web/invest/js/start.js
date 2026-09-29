// Onboarding: three short steps (home state, where to invest, what matters most). Nothing personal is
// asked; the answers are kept in this browser only (prefs.js) and become the URL of the result page.

import { api } from './api.js';
import { CITY_ID, DEFAULT_PRESET, PRESET_IDS, STATE_CODE } from './config.js';
import { tt } from './format.js';
import { loadPrefs, savePrefs } from './prefs.js';
import { i18nReady, renderShell } from './shell.js';
import { clear, errorKey, h, onLangChange, renderError, renderSkeleton, setStatus } from './ui.js';

renderShell();
await i18nReady;

const stepBox = document.getElementById('step');
const progress = document.getElementById('progress');
const statusEl = document.getElementById('step-status');
const resumeBox = document.getElementById('resume');

// choice: 'home' | 'state' | 'city' (what step 2 picked); stateCode is used by 'state', city by 'city'
const answers = { homeState: null, choice: null, stateCode: null, city: null, preset: DEFAULT_PRESET };
let step = 1;
let states = null;
let stateFilter = '';
let searchSeq = 0;
let searchTimer;

const stateOf = (code) => states?.find((s) => s.code === code) ?? null;
const stateName = (code) => stateOf(code)?.name ?? code;

function cityCountText(n) {
  if (n === 0) return tt('inv.start.cities.none');
  return n === 1 ? tt('inv.start.cities.one') : tt('inv.start.cities.n', { n });
}

// ---------- shared pieces ----------

function heading(key, params) {
  return h('h2', { id: 'step-heading', tabindex: '-1', dataset: { i18n: key } }, tt(key, params));
}

function wizardNav({ back, next, nextKey = 'inv.next', nextEnabled = true, skip }) {
  return h('div', { class: 'inv-wizard__nav' },
    back ? h('button', { class: 'inv-btn inv-btn--ghost', type: 'button', dataset: { i18n: 'inv.back' }, onclick: back }, tt('inv.back')) : h('span'),
    h('div', { class: 'inv-cluster' },
      skip ? h('button', { class: 'inv-btn inv-btn--ghost', type: 'button', dataset: { i18n: 'inv.skip.step' }, onclick: skip }, tt('inv.skip.step')) : null,
      h('button', { class: 'inv-btn inv-btn--primary', type: 'button', disabled: !nextEnabled, dataset: { i18n: nextKey }, onclick: next }, tt(nextKey))));
}

// Searchable grid of states. `onPick(code)` gets the choice; states with no city are not pickable
// when the grid is used to choose where to invest (needCities).
function stateGrid({ selected, onPick, needCities }) {
  const grid = h('div', { class: 'inv-tilegrid', role: 'group', 'aria-labelledby': 'step-heading' });
  const draw = () => {
    const needle = stateFilter.trim().toLowerCase();
    clear(grid);
    grid.append(...states
      .filter((s) => !needle || s.name.toLowerCase().includes(needle))
      .map((s) => h('button', {
        class: 'inv-tile', type: 'button', 'aria-pressed': String(s.code === selected),
        disabled: needCities && s.city_count === 0,
        onclick: () => onPick(s.code),
      },
      h('span', { class: 'inv-tile__name' }, s.name),
      h('span', { class: 'inv-small inv-muted' }, cityCountText(s.city_count)))));
  };
  draw();
  const filter = h('input', {
    class: 'inv-input', type: 'search', value: stateFilter, autocomplete: 'off',
    'aria-label': tt('inv.start.filter'), placeholder: tt('inv.start.filter'),
    dataset: { i18nAriaLabel: 'inv.start.filter', i18nPlaceholder: 'inv.start.filter' },
    oninput: (e) => { stateFilter = e.target.value; draw(); },
  });
  return h('div', { class: 'inv-stack inv-stack--tight' }, filter, grid);
}

// ---------- step 1: home state ----------

function renderStep1() {
  stepBox.append(
    heading('inv.start.s1.title'),
    h('p', { class: 'inv-muted', dataset: { i18n: 'inv.start.s1.hint' } }, tt('inv.start.s1.hint')),
    stateGrid({ selected: answers.homeState, onPick: (code) => { answers.homeState = code; go(1, false); } }),
    wizardNav({
      next: () => go(2),
      nextEnabled: answers.homeState != null,
      skip: () => { answers.homeState = null; if (answers.choice === 'home') answers.choice = null; go(2); },
    }));
}

// ---------- step 2: where to invest ----------

function choiceButton(key, params, active, onclick, description) {
  return h('button', { class: 'inv-choice', type: 'button', 'aria-pressed': String(active), disabled: description != null && description.disabled, onclick },
    h('span', { class: 'inv-choice__title', dataset: { i18n: key } }, tt(key, params)),
    description?.text ? h('span', { class: 'inv-small inv-muted' }, description.text) : null);
}

function citySearch() {
  const listId = 'city-results';
  const results = h('ul', { class: 'inv-options', id: listId, role: 'listbox', hidden: true, 'aria-label': tt('inv.start.s2.search') });
  const note = h('p', { class: 'inv-small inv-muted', role: 'status' });
  const input = h('input', {
    class: 'inv-input', type: 'search', role: 'combobox', autocomplete: 'off', spellcheck: 'false',
    'aria-autocomplete': 'list', 'aria-expanded': 'false', 'aria-controls': listId,
    'aria-label': tt('inv.start.s2.search'), placeholder: tt('inv.start.s2.search'),
    dataset: { i18nAriaLabel: 'inv.start.s2.search', i18nPlaceholder: 'inv.start.s2.search' },
  });
  let items = [];
  let active = -1;

  const close = () => {
    results.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    active = -1;
  };
  const choose = (city) => {
    answers.city = { id: city.id, name: city.name };
    answers.choice = 'city';
    go(2, false);
  };
  const highlight = (i) => {
    active = i;
    [...results.children].forEach((li, n) => li.setAttribute('aria-selected', String(n === i)));
    if (i >= 0) input.setAttribute('aria-activedescendant', `city-opt-${i}`);
    else input.removeAttribute('aria-activedescendant');
  };
  const show = (found) => {
    items = found;
    clear(results);
    results.append(...found.map((c, i) => h('li', {
      class: 'inv-option', id: `city-opt-${i}`, role: 'option', 'aria-selected': 'false',
      // mousedown, not click: the input loses focus first and would close the list before a click lands
      onmousedown: (e) => { e.preventDefault(); choose(c); },
    },
    h('strong', null, c.name),
    h('span', { class: 'inv-small inv-muted' }, `${stateName(c.state)} · ${tt(`inv.tier.${c.tier}`)}`),
    c.matched && c.matched !== c.name ? h('span', { class: 'inv-small inv-muted' }, tt('inv.start.s2.matched', { alias: c.matched })) : null)));
    results.hidden = found.length === 0;
    input.setAttribute('aria-expanded', String(found.length > 0));
    highlight(-1);
  };

  const run = async (q) => {
    const seq = ++searchSeq;
    note.textContent = tt('inv.start.s2.searching');
    try {
      const { cities } = await api.searchCities(q, { limit: 8 });
      if (seq !== searchSeq) return; // a newer search replaced this one
      show(cities);
      note.textContent = cities.length ? '' : tt('inv.start.s2.nomatch');
    } catch (error) {
      if (seq !== searchSeq) return;
      show([]);
      // a query the server refuses (400) is simply "no match"; anything else is worth saying
      note.textContent = error?.code === 'bad_request' ? tt('inv.start.s2.nomatch') : tt(errorKey(error));
    }
  };

  input.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = input.value.trim();
    if (q.length < 2) { searchSeq += 1; show([]); note.textContent = ''; return; }
    searchTimer = setTimeout(() => run(q), 250);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' && items.length) { e.preventDefault(); highlight((active + 1) % items.length); }
    else if (e.key === 'ArrowUp' && items.length) { e.preventDefault(); highlight((active - 1 + items.length) % items.length); }
    else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); choose(items[active]); }
    else if (e.key === 'Escape') close();
  });
  input.addEventListener('blur', close);

  return h('div', { class: 'inv-stack inv-stack--tight' },
    input, results, note,
    answers.city ? h('p', { class: 'inv-chip inv-chip--why' }, tt('inv.chosen', { name: answers.city.name })) : null);
}

function renderStep2() {
  const home = answers.homeState ? stateOf(answers.homeState) : null;
  const homeOk = home && home.city_count > 0;
  const ready = (answers.choice === 'home' && homeOk)
    || (answers.choice === 'state' && answers.stateCode != null)
    || (answers.choice === 'city' && answers.city != null);
  const pick = (choice) => () => { answers.choice = choice; go(2, false); };

  stepBox.append(
    heading('inv.start.s2.title'),
    h('div', { class: 'inv-choices' },
      home ? choiceButton('inv.start.s2.home', { state: home.name }, answers.choice === 'home', pick('home'),
        homeOk ? null : { disabled: true, text: cityCountText(0) }) : null,
      choiceButton('inv.start.s2.other', {}, answers.choice === 'state', pick('state')),
      choiceButton('inv.start.s2.city', {}, answers.choice === 'city', pick('city'))),
    answers.choice === 'state'
      ? stateGrid({ selected: answers.stateCode, needCities: true, onPick: (code) => { answers.stateCode = code; go(2, false); } })
      : null,
    answers.choice === 'city' ? citySearch() : null,
    wizardNav({ back: () => go(1), next: () => go(3), nextEnabled: ready }));
}

// ---------- step 3: what matters most ----------

function renderStep3() {
  const radios = PRESET_IDS.map((id) => h('button', {
    class: 'inv-preset', type: 'button', role: 'radio', 'aria-checked': String(answers.preset === id),
    tabindex: answers.preset === id ? '0' : '-1',
    onclick: () => { answers.preset = id; go(3, false); },
  },
  h('span', { class: 'inv-preset__name', dataset: { i18n: `inv.preset.${id}` } }, tt(`inv.preset.${id}`)),
  h('span', { class: 'inv-small inv-muted', dataset: { i18n: `inv.preset.${id}.desc` } }, tt(`inv.preset.${id}.desc`))));
  const group = h('div', {
    class: 'inv-presets', role: 'radiogroup', 'aria-labelledby': 'step-heading',
    onkeydown: (e) => {
      const i = PRESET_IDS.indexOf(answers.preset);
      const move = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (!move) return;
      e.preventDefault();
      answers.preset = PRESET_IDS[(i + move + PRESET_IDS.length) % PRESET_IDS.length];
      go(3, false);
      document.querySelector('.inv-preset[aria-checked="true"]')?.focus();
    },
  }, radios);
  stepBox.append(heading('inv.start.s3.title'), group, wizardNav({ back: () => go(2), next: finish, nextKey: 'inv.start.go' }));
}

// The result page and its query string. Values are checked again here because they may come from storage.
function targetUrl() {
  const preset = encodeURIComponent(answers.preset);
  const code = answers.choice === 'home' ? answers.homeState : answers.stateCode;
  if (answers.choice === 'city' && CITY_ID.test(answers.city?.id ?? '')) {
    return { target: { type: 'city', id: answers.city.id }, url: `city.html?c=${encodeURIComponent(answers.city.id)}&preset=${preset}` };
  }
  if (STATE_CODE.test(code ?? '')) {
    return { target: { type: 'state', code }, url: `state.html?s=${encodeURIComponent(code)}&preset=${preset}` };
  }
  return null;
}

function finish() {
  const dest = targetUrl();
  if (!dest) { go(2); return; }
  savePrefs({ homeState: answers.homeState, target: dest.target, preset: answers.preset });
  window.location.assign(dest.url);
}

// ---------- flow ----------

function renderStep() {
  clear(stepBox);
  [...progress.children].forEach((li, i) => { li.dataset.state = i + 1 < step ? 'done' : i + 1 === step ? 'current' : 'todo'; });
  if (!states && step !== 3) return;
  ({ 1: renderStep1, 2: renderStep2, 3: renderStep3 })[step]();
}

// Move to a step. moveFocus is false when only the current step's own state changed (a tile was picked).
function go(next, moveFocus = true) {
  step = next;
  renderStep();
  if (moveFocus) {
    setStatus(statusEl, `${tt('inv.start.progress', { n: step })}: ${document.getElementById('step-heading')?.textContent ?? ''}`);
    document.getElementById('step-heading')?.focus();
  }
}

async function loadStates() {
  renderSkeleton(stepBox, 4);
  try {
    states = (await api.states()).states;
  } catch (error) {
    renderError(stepBox, error, loadStates);
    return;
  }
  renderStep();
}

// ---------- resume ----------

function showResume(prefs) {
  clear(resumeBox);
  resumeBox.append(h('div', { class: 'inv-card inv-stack inv-stack--tight' },
    h('strong', { dataset: { i18n: 'inv.start.resume' } }, tt('inv.start.resume')),
    h('p', { class: 'inv-small inv-muted', dataset: { i18n: 'inv.start.resume.hint' } }, tt('inv.start.resume.hint')),
    h('div', { class: 'inv-cluster' },
      h('button', { class: 'inv-btn inv-btn--primary', type: 'button', dataset: { i18n: 'inv.start.resume' }, onclick: () => { restore(prefs); clear(resumeBox); go(3); } }, tt('inv.start.resume')),
      h('button', { class: 'inv-btn inv-btn--ghost', type: 'button', dataset: { i18n: 'inv.start.reset' }, onclick: () => { savePrefs({}); clear(resumeBox); go(1); } }, tt('inv.start.reset')))));
}

function restore(prefs) {
  answers.homeState = prefs.homeState;
  answers.preset = prefs.preset;
  if (prefs.target?.type === 'city') {
    answers.choice = 'city';
    answers.city = { id: prefs.target.id, name: prefs.target.id };
    api.city(prefs.target.id).then((c) => { if (answers.city?.id === c.id) answers.city.name = c.name; }).catch(() => {});
  } else if (prefs.target?.type === 'state') {
    if (prefs.target.code === prefs.homeState) answers.choice = 'home';
    else { answers.choice = 'state'; answers.stateCode = prefs.target.code; }
  }
}

const saved = loadPrefs();
if (saved.homeState || saved.target) showResume(saved);
loadStates();
onLangChange(() => { renderStep(); });
