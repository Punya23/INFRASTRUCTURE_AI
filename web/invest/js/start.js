// The three-step onboarding wizard (spec section 8): which state, where to look, what matters.
// The top half is pure logic (unit-tested in start.test.mjs); the bottom half is the page and only
// runs in a browser. What the visitor picks is kept in this browser (prefs.js) and nowhere else.

import { api } from './api.js';
import { CITY_ID, DEFAULT_PRESET, PRESET_IDS, STATE_CODE } from './config.js';
import { tt } from './format.js';
import { loadPrefs, savePrefs } from './prefs.js';
import { clear, h, onLangChange, renderError, renderSkeleton, setStatus } from './ui.js';

// ---------- Pure logic ----------

// The API accepts 2 to 64 characters (spec section 7). Checking here means a one-letter or 200-letter
// query never becomes a request, and counting code points keeps Devanagari and Kannada honest.
export const MIN_SEARCH = 2;
export const MAX_SEARCH = 64;

// { text } when the query can be sent, otherwise { problem: 'empty' | 'short' | 'long' }.
export function searchText(raw) {
  const text = String(raw ?? '').trim().replace(/\s+/g, ' ');
  const length = [...text].length;
  if (length === 0) return { problem: 'empty' };
  if (length < MIN_SEARCH) return { problem: 'short' };
  if (length > MAX_SEARCH) return { problem: 'long' };
  return { text };
}

// Substring on the name, exact on the two-letter code; blank keeps everything.
export function filterStates(states, text) {
  const q = String(text ?? '').trim().toLowerCase();
  if (!q) return states;
  return states.filter((s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase() === q);
}

// Which item an arrow key moves to in a list (cols = 1) or a grid (cols = items per row); null for
// any other key. Stops at the ends. From "nothing active" (-1), a forward key lands on the first
// item and a backward key on the last.
export function moveIndex(index, key, count, cols) {
  if (count < 1) return null;
  const last = count - 1;
  const clamp = (i) => Math.min(last, Math.max(0, i));
  switch (key) {
    case 'Home': return 0;
    case 'End': return last;
    case 'ArrowRight': return index < 0 ? 0 : clamp(index + 1);
    case 'ArrowLeft': return index < 0 ? last : clamp(index - 1);
    case 'ArrowDown': return index < 0 ? 0 : clamp(index + cols);
    case 'ArrowUp': return index < 0 ? last : clamp(index - cols);
    default: return null;
  }
}

// What a key does in the city box, given how many results are listed and which one is highlighted:
// { type: 'move' | 'pick', index }, { type: 'close' }, or null when the key is not ours. With nothing
// listed no key does anything, so Enter can never pick a row the visitor cannot see.
export function cityKeyAction(key, count, active) {
  if (count < 1) return null;
  if (key === 'Escape') return { type: 'close' };
  if (key === 'ArrowDown' || key === 'ArrowUp') return { type: 'move', index: moveIndex(active, key, count, 1) };
  if (key === 'Enter') {
    const index = active >= 0 ? active : (count === 1 ? 0 : -1);
    return index >= 0 ? { type: 'pick', index } : null;
  }
  return null;
}

// answers = { homeState, choice: 'home' | 'state' | 'city' | null, stateCode, city: {id, name, state}, preset }.
// The choice says which answer is the destination, so going Back and changing the home state
// cannot leave a stale destination behind.
export function resolveTarget(a) {
  if (a.choice === 'home' && a.homeState) return { type: 'state', code: a.homeState };
  if (a.choice === 'state' && a.stateCode) return { type: 'state', code: a.stateCode };
  if (a.choice === 'city' && a.city?.id) return { type: 'city', id: a.city.id };
  return null;
}

// The page to open, or null when there is no valid destination. Ids are checked again here because
// they come from storage and from the API, and they end up in a URL.
export function destination(a) {
  const target = resolveTarget(a);
  if (!target) return null;
  const preset = PRESET_IDS.includes(a.preset) ? a.preset : DEFAULT_PRESET;
  if (target.type === 'state') return STATE_CODE.test(target.code) ? `state.html?s=${target.code}&preset=${preset}` : null;
  return CITY_ID.test(target.id) ? `city.html?c=${target.id}&preset=${preset}` : null;
}

// From saved prefs (already sanitised by prefs.js). A saved city has no name until it is looked up.
export function initialAnswers(prefs) {
  const t = prefs.target;
  const answers = { homeState: prefs.homeState, choice: null, stateCode: null, city: null, preset: prefs.preset };
  if (t?.type === 'state') {
    if (t.code === prefs.homeState) answers.choice = 'home';
    else Object.assign(answers, { choice: 'state', stateCode: t.code });
  } else if (t?.type === 'city') {
    Object.assign(answers, { choice: 'city', city: { id: t.id, name: null, state: null } });
  }
  return answers;
}

export const toPrefs = (a) => ({ homeState: a.homeState, target: resolveTarget(a), preset: a.preset });

// ---------- The page ----------

const TOTAL = 3;
const STEP_SHORT = ['inv.start.step1.short', 'inv.start.step2.short', 'inv.start.step3.short'];
const STEP_HEADING = ['inv.start.step1.heading', 'inv.start.step2.heading', 'inv.start.step3.heading'];
const TIERS = new Set(['metro', 'large', 'mid']);
const DEBOUNCE_MS = 250;

const model = {
  step: 0,
  answers: null,
  states: null,        // [{code, name, city_count}] once loaded
  statesError: null,   // the ApiError when loading failed
  stateFilter: '',
  query: '',           // the text in the city box
  search: { kind: 'idle' }, // idle | hint | loading | results | error
  results: [],
  active: -1,          // the highlighted city result
  resume: null,        // page to open for "Continue where you left off"
  resumeTarget: null,
  resumeCityName: null,
  ready: false,        // the dictionary has arrived, so tt() gives words and not keys
  pendingFocus: null,
  message: null,       // a key for a one-time warning shown above the buttons on the next render
  nodes: {},           // parts of the city box that change without rebuilding the step
};
let root;
let status;
let debounceTimer;
let searchToken = 0;
let shownMessage = null; // the warning this render carries, for nav() to draw

const stateName = (code) => model.states?.find((s) => s.code === code)?.name ?? code;
const canNext = () => model.step !== 1 || resolveTarget(model.answers) !== null;

function cityCountText(n) {
  if (!Number.isInteger(n) || n < 0) return '';
  if (n === 0) return tt('inv.start.cities.none');
  return n === 1 ? tt('inv.start.cities.one') : tt('inv.start.cities.other', { n });
}

// A group of choices as radio buttons with one tab stop and arrow keys, so a keyboard visitor does not
// tab through 36 states. As in the ARIA radio pattern, an arrow key moves focus and picks; onPick's second
// argument says it came from the keyboard, so a pick that would move focus elsewhere can leave it here.
function radioGroup({ labelledby, items, selected, onPick, className, itemClass, focusPrefix }) {
  const start = Math.max(0, items.findIndex((item) => item.value === selected));
  const buttons = items.map((item, i) => h('button', {
    type: 'button',
    role: 'radio',
    class: itemClass,
    'aria-checked': item.value === selected,
    tabindex: i === start ? 0 : -1,
    dataset: { focus: `${focusPrefix}-${item.value}` },
    onclick: () => onPick(item.value, false),
  }, item.children));
  const group = h('div', { role: 'radiogroup', 'aria-labelledby': labelledby, class: className }, buttons);
  group.addEventListener('keydown', (event) => {
    const from = buttons.indexOf(document.activeElement);
    const cols = buttons.filter((b) => b.offsetTop === buttons[0].offsetTop).length;
    const to = from < 0 ? null : moveIndex(from, event.key, buttons.length, cols);
    if (to === null) return;
    event.preventDefault();
    if (to !== from) onPick(items[to].value, true); // rebuilds the step and puts focus back on this item
  });
  return group;
}

const tileChildren = (name, meta) => [
  h('span', { class: 'start-tile__name' }, name),
  meta ? h('span', { class: 'start-tile__meta' }, meta) : null,
];

// The searchable grid of states, shared by step 1 and the "Another state" choice of step 2.
function stateGrid({ selected, onPick, labelledby }) {
  const holder = h('div', { class: 'start-tiles-holder' });
  const paint = () => {
    if (model.statesError) return renderError(holder, model.statesError, loadStates);
    if (!model.states) return renderSkeleton(holder, 3);
    clear(holder);
    const shown = filterStates(model.states, model.stateFilter);
    if (shown.length === 0) {
      holder.append(h('div', { class: 'inv-empty' }, h('p', null, tt('inv.start.states.none'))));
      return;
    }
    holder.append(radioGroup({
      labelledby,
      selected,
      onPick,
      className: 'start-tiles',
      itemClass: 'start-tile',
      focusPrefix: 'state',
      items: shown.map((s) => ({ value: s.code, children: tileChildren(s.name, cityCountText(s.city_count)) })),
    }));
  };
  paint();
  const input = h('input', {
    id: 'state-filter',
    class: 'start-input',
    dataset: { focus: 'state-filter' },
    type: 'text',
    autocomplete: 'off',
    spellcheck: 'false',
    value: model.stateFilter,
    placeholder: tt('inv.start.states.filter.placeholder'),
    oninput: (event) => {
      model.stateFilter = event.target.value;
      paint();
      if (model.states) setStatus(status, tt('inv.start.states.shown', { n: filterStates(model.states, model.stateFilter).length, total: model.states.length }));
    },
  });
  return h('div', { class: 'start-states' },
    h('label', { class: 'start-label', for: 'state-filter' }, tt('inv.start.states.filter')),
    input,
    holder);
}

// ----- the city box: a combobox over a listbox -----

function onQuery(value) {
  const a = model.answers;
  model.query = value;
  model.results = []; // the rows on screen belong to the old text; no key may act on them
  model.active = -1;
  if (a.city && value !== a.city.name) a.city = null; // typing over a chosen city un-chooses it
  clearTimeout(debounceTimer);
  searchToken += 1; // an answer still on its way is now stale
  const s = searchText(value);
  if (s.problem === 'empty') model.search = { kind: 'idle' };
  else if (s.problem) model.search = { kind: 'hint', problem: s.problem };
  else {
    model.search = { kind: 'loading' };
    debounceTimer = setTimeout(() => runSearch(s.text), DEBOUNCE_MS);
  }
  paintSearch();
}

async function runSearch(text) {
  const mine = ++searchToken;
  let body;
  try {
    body = await api.searchCities(text);
  } catch (error) {
    // aborted: nobody is waiting for that request any more, so there is nothing to show
    if (mine !== searchToken || error?.code === 'aborted') return;
    model.search = { kind: 'error', error, text };
    paintSearch();
    return;
  }
  if (mine !== searchToken) return;
  const rows = Array.isArray(body.cities) ? body.cities : [];
  model.results = rows.filter((c) => c && typeof c.name === 'string' && typeof c.id === 'string' && CITY_ID.test(c.id));
  model.active = -1;
  model.search = { kind: 'results' };
  paintSearch();
}

function setActive(i) {
  const { input, list } = model.nodes;
  if (i === null || i >= list.children.length) return;
  model.active = i;
  [...list.children].forEach((li, n) => {
    li.classList.toggle('is-active', n === i);
    li.setAttribute('aria-selected', String(n === i));
  });
  if (i >= 0) {
    input.setAttribute('aria-activedescendant', list.children[i].id);
    list.children[i].scrollIntoView({ block: 'nearest' });
  } else input.removeAttribute('aria-activedescendant');
}

function pickCity(i) {
  const r = model.results[i];
  if (!r) return;
  clearTimeout(debounceTimer);
  searchToken += 1;
  model.answers.city = { id: r.id, name: r.name, state: typeof r.state === 'string' ? r.state : null };
  model.answers.choice = 'city';
  model.query = r.name;
  model.search = { kind: 'idle' };
  model.results = [];
  model.active = -1;
  model.pendingFocus = 'city-input';
  render();
}

// Repaints what a search changes: the hint line, the list and the error slot, plus the chosen-city line
// and the Next button, without rebuilding the input the visitor is typing in.
function paintSearch() {
  const { input, hint, list, errorSlot, selected, next } = model.nodes;
  if (!input?.isConnected) return;
  const s = model.search;
  clear(errorSlot);
  list.replaceChildren();
  let text = '';
  if (s.kind === 'hint') text = tt(s.problem === 'short' ? 'inv.start.city.short' : 'inv.start.city.long');
  else if (s.kind === 'loading') text = tt('inv.start.city.searching');
  else if (s.kind === 'error') renderError(errorSlot, s.error, () => { model.search = { kind: 'loading' }; paintSearch(); runSearch(s.text); });
  else if (s.kind === 'results') {
    const n = model.results.length;
    if (n === 0) text = tt('inv.start.city.none');
    else {
      text = n === 1 ? tt('inv.start.city.found.one') : tt('inv.start.city.found.other', { n });
      list.append(...model.results.map((r, i) => {
        const alias = r.matched && r.matched.toLowerCase() !== r.name.toLowerCase() ? tt('inv.start.city.alias', { alias: r.matched }) : null;
        return h('li', {
          id: `city-opt-${i}`,
          role: 'option',
          class: 'start-result',
          'aria-selected': false,
          onmousedown: (event) => event.preventDefault(), // keep focus in the box
          onclick: () => pickCity(i),
        },
        h('span', { class: 'start-result__name' }, r.name),
        h('span', { class: 'start-result__meta' }, typeof r.state === 'string' ? stateName(r.state) : ''),
        TIERS.has(r.tier) ? h('span', { class: 'inv-badge' }, tt(`inv.tier.${r.tier}`)) : null,
        alias ? h('span', { class: 'start-result__meta' }, alias) : null);
      }));
    }
  }
  const open = list.children.length > 0;
  list.hidden = !open;
  input.setAttribute('aria-expanded', String(open));
  input.removeAttribute('aria-activedescendant');
  setStatus(hint, text);

  const city = model.answers.city;
  selected.hidden = !city;
  selected.textContent = !city ? ''
    : !city.name ? tt('inv.start.city.selected.saved')
    : city.state ? tt('inv.start.city.selected', { name: city.name, state: stateName(city.state) })
    : city.name;
  next?.setAttribute('aria-disabled', String(!canNext()));
}

function citySearch() {
  const input = h('input', {
    id: 'city-input',
    class: 'start-input',
    type: 'text',
    role: 'combobox',
    autocomplete: 'off',
    spellcheck: 'false',
    'aria-autocomplete': 'list',
    'aria-expanded': false,
    'aria-controls': 'city-listbox',
    'aria-describedby': 'city-hint',
    value: model.query,
    placeholder: tt('inv.start.city.placeholder'),
    dataset: { focus: 'city-input' },
    oninput: (event) => onQuery(event.target.value),
    onkeydown: (event) => {
      const action = cityKeyAction(event.key, model.results.length, model.active);
      if (!action) return;
      event.preventDefault();
      if (action.type === 'pick') pickCity(action.index);
      else if (action.type === 'move') setActive(action.index);
      else {
        model.search = { kind: 'idle' };
        model.results = [];
        paintSearch();
      }
    },
  });
  const hint = h('p', { id: 'city-hint', class: 'start-hint inv-small', role: 'status', 'aria-live': 'polite' });
  const list = h('ul', { id: 'city-listbox', class: 'start-results inv-list', role: 'listbox', 'aria-label': tt('inv.start.city.results'), hidden: true });
  const errorSlot = h('div');
  const selected = h('p', { class: 'start-selected', hidden: true });
  Object.assign(model.nodes, { input, hint, list, errorSlot, selected });
  return h('div', { class: 'start-city' },
    h('label', { class: 'start-label', for: 'city-input' }, tt('inv.start.city.label')),
    input, hint, list, errorSlot, selected);
}

// ----- steps -----

function nav({ onNext, onSkip, nextKey = 'inv.start.next', needKey }) {
  const next = h('button', {
    type: 'button',
    class: 'inv-btn inv-btn--primary',
    'aria-disabled': !canNext(),
    dataset: { focus: 'next' },
    onclick: () => (canNext() ? onNext() : warn(needKey)),
  }, tt(nextKey));
  model.nodes.next = next;
  return [
    shownMessage ? h('p', { class: 'start-message', role: 'alert' }, tt(shownMessage)) : null,
    h('div', { class: 'start-nav' },
    model.step > 0 ? h('button', { type: 'button', class: 'inv-btn inv-btn--ghost', onclick: () => goTo(model.step - 1) }, tt('inv.start.back')) : null,
    h('div', { class: 'start-nav__forward' },
      onSkip ? h('button', { type: 'button', class: 'inv-btn inv-btn--ghost', onclick: onSkip }, tt('inv.start.skip')) : null,
      next)),
  ];
}

// Shows a warning above the buttons; it is visible and also announced (role="alert").
function warn(key) {
  model.message = key;
  render();
}

const heading = (key) => h('h2', { id: 'step-heading', tabindex: -1, dataset: { focus: 'heading' } }, tt(key));

function stepState() {
  const a = model.answers;
  return [
    heading(STEP_HEADING[0]),
    h('p', { class: 'inv-muted' }, tt('inv.start.step1.hint')),
    stateGrid({
      selected: a.homeState,
      labelledby: 'step-heading',
      onPick: (code) => { a.homeState = code; model.pendingFocus = `state-${code}`; render(); },
    }),
    nav({
      onNext: () => goTo(1),
      onSkip: () => { a.homeState = null; if (a.choice === 'home') a.choice = null; goTo(1); },
    }),
  ];
}

function stepPlace() {
  const a = model.answers;
  const items = [
    a.homeState ? { value: 'home', children: tileChildren(tt('inv.start.where.home', { state: stateName(a.homeState) })) } : null,
    { value: 'state', children: tileChildren(tt('inv.start.where.state')) },
    { value: 'city', children: tileChildren(tt('inv.start.where.city')) },
  ].filter(Boolean);
  return [
    heading(STEP_HEADING[1]),
    radioGroup({
      labelledby: 'step-heading',
      items,
      selected: a.choice,
      className: 'start-options',
      itemClass: 'start-tile start-tile--large',
      focusPrefix: 'choice',
      onPick: (choice, byArrow) => {
        a.choice = choice;
        model.pendingFocus = choice === 'city' && !byArrow ? 'city-input' : `choice-${choice}`;
        render();
      },
    }),
    a.choice === 'state' ? h('div', { class: 'start-reveal' },
      h('p', { id: 'state-group-label', class: 'start-label' }, tt('inv.start.states.label')),
      stateGrid({
        selected: a.stateCode,
        labelledby: 'state-group-label',
        onPick: (code) => { a.stateCode = code; model.pendingFocus = `state-${code}`; render(); },
      })) : null,
    a.choice === 'city' ? h('div', { class: 'start-reveal' }, citySearch()) : null,
    nav({ onNext: () => goTo(2), needKey: 'inv.start.need.place' }),
  ];
}

function stepPreset() {
  const a = model.answers;
  return [
    heading(STEP_HEADING[2]),
    h('p', { class: 'inv-muted' }, tt('inv.start.step3.hint')),
    radioGroup({
      labelledby: 'step-heading',
      selected: a.preset,
      className: 'start-options',
      itemClass: 'start-tile start-tile--large',
      focusPrefix: 'preset',
      items: PRESET_IDS.map((id) => ({ value: id, children: tileChildren(tt(`inv.preset.${id}`), tt(`inv.preset.${id}.desc`)) })),
      onPick: (id) => { a.preset = id; model.pendingFocus = `preset-${id}`; render(); },
    }),
    nav({ onNext: finish, nextKey: 'inv.start.finish' }),
  ];
}

function progress() {
  return h('div', { class: 'start-progress' },
    h('p', { class: 'inv-small inv-muted' }, tt('inv.start.progress', { n: model.step + 1, total: TOTAL })),
    h('ol', { class: 'start-progress__list inv-list', 'aria-label': tt('inv.start.progress.label') },
      STEP_SHORT.map((key, i) => h('li', {
        class: `start-progress__item${i < model.step ? ' is-done' : ''}${i === model.step ? ' is-current' : ''}`,
        'aria-current': i === model.step ? 'step' : null,
      },
      h('span', { class: 'start-progress__hex', 'aria-hidden': true }, i + 1),
      h('span', { class: 'start-progress__label' }, tt(key))))));
}

function resumeBanner() {
  if (!model.resume || model.step !== 0) return null;
  const t = model.resumeTarget;
  const place = t?.type === 'state' ? (model.states ? stateName(t.code) : null) : model.resumeCityName;
  return h('section', { class: 'start-resume', 'aria-labelledby': 'resume-title' },
    h('div', null,
      h('h2', { id: 'resume-title', class: 'start-resume__title' }, tt('inv.start.resume.title')),
      h('p', { class: 'inv-small inv-muted' }, place ? tt('inv.start.resume.body', { place }) : tt('inv.start.resume.body.plain'))),
    h('a', { class: 'inv-btn inv-btn--secondary', href: model.resume }, tt('inv.start.resume.go')));
}

function render() {
  if (!model.ready) return renderSkeleton(root, 4);
  const active = document.activeElement;
  const focusKey = model.pendingFocus ?? active?.dataset?.focus;
  // a rebuild while the visitor types (states arrive, language changes) must not move their caret
  const caret = model.pendingFocus === null && active?.selectionStart != null ? [active.selectionStart, active.selectionEnd] : null;
  model.pendingFocus = null;
  shownMessage = model.message;
  model.message = null;
  model.nodes = {};
  clear(root);
  const step = [stepState, stepPlace, stepPreset][model.step]();
  root.append(...[progress(), resumeBanner(), h('section', { class: 'start-panel' }, step)].filter(Boolean));
  if (model.step === 1 && model.answers.choice === 'city') paintSearch();
  const target = focusKey && [...root.querySelectorAll('[data-focus]')].find((el) => el.dataset.focus === focusKey);
  if (target) {
    target.focus();
    if (target.tagName === 'INPUT') target.setSelectionRange(...(caret ?? [target.value.length, target.value.length]));
  }
}

function goTo(step) {
  model.step = step;
  model.stateFilter = '';
  model.pendingFocus = 'heading';
  render();
  // focus moving to the heading already reads the heading aloud; the status adds only the position
  setStatus(status, tt('inv.start.progress', { n: step + 1, total: TOTAL }));
}

function finish() {
  const url = destination(model.answers);
  if (!url) { // the destination went stale (for example a saved state the API no longer lists)
    model.message = 'inv.start.need.place';
    goTo(1);
    return;
  }
  savePrefs(toPrefs(model.answers)); // a blocked or full storage only means the choices are not remembered
  location.assign(url);
}

// ----- data -----

async function loadStates() {
  model.statesError = null;
  model.states = null;
  render();
  try {
    const body = await api.states();
    const rows = Array.isArray(body.states) ? body.states : [];
    model.states = rows.filter((s) => s && typeof s.name === 'string' && STATE_CODE.test(s.code));
    // a state saved earlier that the API no longer lists is dropped, not shown as a bare code
    const known = (code) => model.states.some((s) => s.code === code);
    const a = model.answers;
    if (a.homeState && !known(a.homeState)) a.homeState = null;
    if (a.stateCode && !known(a.stateCode)) a.stateCode = null;
    if (!resolveTarget(a)) a.choice = null;
    // the resume link must not point at a state the answers above just dropped
    if (model.resumeTarget?.type === 'state' && !known(model.resumeTarget.code)) model.resume = model.resumeTarget = null;
  } catch (error) {
    if (error?.code === 'aborted') return;
    model.statesError = error;
  }
  render();
}

// A saved city is only an id; its name comes from the API so the box and the banner can show it.
async function hydrateCity() {
  const saved = model.answers.city;
  if (!saved) return;
  try {
    const city = await api.city(saved.id);
    if (model.answers.city?.id !== saved.id || typeof city.name !== 'string') return;
    saved.name = city.name;
    saved.state = typeof city.state === 'string' ? city.state : null;
    model.resumeCityName = city.name;
    if (model.query === '') model.query = city.name;
  } catch (error) {
    if (error?.code === 'aborted') return;
    // a city that is gone is dropped (fail closed); any other failure leaves the saved id, which still works
    if (error?.code === 'not_found' || error?.code === 'bad_request') {
      model.answers.city = null;
      model.answers.choice = null;
      model.resume = null;
    }
  }
  render();
}

function init() {
  root = document.getElementById('wizard');
  status = document.getElementById('start-status');
  model.answers = initialAnswers(loadPrefs());
  model.resume = destination(model.answers);
  model.resumeTarget = resolveTarget(model.answers);
  model.ready = globalThis.InfraI18n?.t('inv.start.title') != null;
  // i18n.js announces once its dictionary has loaded; if it never does, show the page anyway after 2 s
  onLangChange(() => { model.ready = true; render(); });
  setTimeout(() => { if (!model.ready) { model.ready = true; render(); } }, 2000);
  render();
  loadStates();
  hydrateCity();
}

if (typeof document !== 'undefined') init();
