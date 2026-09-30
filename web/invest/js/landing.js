// Landing page: a live sample of the top cities in one state, and the source list from /v1/meta.
// Both are extras. The page reads completely without them, so each has its own skeleton, error and
// Retry, and a failure in one never touches the other.

import { api } from './api.js';
import { CITY_ID, DEFAULT_PRESET } from './config.js';
import { explain } from './explain.js';
import { formatCount, formatScore, tt } from './format.js';
import { hasSavedPrefs, loadPrefs } from './prefs.js';
import { clear, h, onLangChange, renderError, renderSkeleton, setStatus, setStatusKey } from './ui.js';

// The state the sample shows. Its name is in the locale strings inv.landing.sample.title and .more.
const SAMPLE_STATE = 'MH';
const SAMPLE_SIZE = 3;
const TIERS = new Set(['metro', 'large', 'mid']);

// meta.sources can list one credit more than once (the two GHSL years share name, license and
// attribution). Each distinct credit is kept once, in the order given. A source with neither a name
// nor an attribution has nothing to show and is left out. The attribution is shown under the name,
// so a leading "<name> — " is not repeated, and an attribution that only repeats the name is dropped.
export function uniqueSources(sources) {
  if (!Array.isArray(sources)) return [];
  const text = (v) => (typeof v === 'string' && v.trim() !== '' ? v.trim() : null);
  const seen = new Set();
  const out = [];
  for (const source of sources) {
    const attribution = text(source?.attribution);
    const name = text(source?.name) ?? attribution;
    if (name === null) continue;
    const license = text(source?.license);
    const key = JSON.stringify([name, license, attribution]);
    if (seen.has(key)) continue;
    seen.add(key);
    const lead = `${name} — `;
    const detail = attribution?.startsWith(lead) ? attribution.slice(lead.length).trim() : attribution;
    out.push({ name, license, attribution: detail === name || detail === '' ? null : detail });
  }
  return out;
}

// One driver per city for the sample. Top cities often share their strongest driver (every metro is
// near a highway), so each row takes its best driver whose factor no earlier row has shown, and its
// top driver when all of them have been shown. undefined for a city with no drivers.
export function sampleDrivers(cities) {
  const shown = new Set();
  return cities.map((city) => {
    const drivers = Array.isArray(city?.drivers) ? city.drivers.filter((d) => typeof d?.factor === 'string') : [];
    const pick = drivers.find((d) => !shown.has(d.factor)) ?? drivers[0];
    if (pick) shown.add(pick.factor);
    return pick;
  });
}

// The state whose top cities the personalised view lists: the saved state target, or the home state
// behind a saved city (looked up by the caller, since only the API knows a city's state), else the home
// state. null when there is none.
export function shortlistState(prefs, cityState) {
  const t = prefs.target;
  if (t?.type === 'state') return t.code;
  return (t?.type === 'city' ? cityState : null) ?? prefs.homeState ?? null;
}

// Link to a city page, or null when the id is not one the city page would accept.
export const cityHref = (id) =>
  typeof id === 'string' && CITY_ID.test(id) ? `city.html?c=${id}&preset=${DEFAULT_PRESET}` : null;

function boot(doc) {
  const sampleBody = doc.getElementById('sample-body');
  const sampleStatus = doc.getElementById('sample-status');
  const sourcesBody = doc.getElementById('sources-body');
  const asOf = doc.getElementById('sources-asof');

  let meta = null;   // last good /v1/meta; also sharpens the "no station within N km" wording
  let sample = null; // last good list of city cards
  let yours = null;  // { code, city, states } behind the personalised heading

  // With saved onboarding answers the page shows "yours" (their place, their preset, five cities) instead
  // of the generic Maharashtra sample; the same row renderer and loader serve both.
  const prefs = hasSavedPrefs() ? loadPrefs() : null;
  const list = prefs
    ? { body: doc.getElementById('yours-body'), status: doc.getElementById('yours-status'), size: 5, preset: prefs.preset }
    : { body: sampleBody, status: sampleStatus, size: SAMPLE_SIZE, preset: undefined };

  function cityRow(city, driver) {
    const href = cityHref(city.id);
    const name = typeof city.name === 'string' && city.name ? city.name : '—';
    const why = driver ? explain('why', driver, meta) : null;
    const score = formatScore(city.score);
    return h('li', { class: 'landing-sample__row' },
      h('span', { class: city.rank === 1 ? 'inv-rank inv-rank--top' : 'inv-rank' }, formatCount(city.rank)),
      h('p', { class: 'landing-sample__name' },
        href ? h('a', { href }, name) : name,
        TIERS.has(city.tier)
          ? h('span', { class: 'inv-badge', dataset: { i18n: `inv.tier.${city.tier}` } }, tt(`inv.tier.${city.tier}`))
          : null),
      why ? h('p', { class: 'inv-chip inv-chip--why landing-sample__why' }, tt(why.key, why.params)) : null,
      h('span', {
        class: 'inv-ring',
        ...(Number.isFinite(city.score)
          ? { role: 'img', 'aria-label': tt('inv.landing.sample.score', { score }) }
          : {}),
        style: { '--value': Number.isFinite(city.score) ? city.score : 0 },
      }, h('span', { class: 'inv-ring__value', 'aria-hidden': Number.isFinite(city.score) ? 'true' : null }, score)));
  }

  function renderSample() {
    if (!sample) return;
    clear(list.body);
    setStatus(list.status, '');
    const drivers = sampleDrivers(sample);
    list.body.append(sample.length
      ? h('ol', { class: 'landing-sample__list', role: 'list' }, sample.map((city, i) => cityRow(city, drivers[i])))
      : h('p', { class: 'inv-empty', dataset: { i18n: 'inv.landing.sample.empty' } }, tt('inv.landing.sample.empty')));
  }

  async function loadSample() {
    sample = null;
    renderSkeleton(list.body, list.size);
    setStatusKey(list.status, 'inv.loading');
    try {
      let code = SAMPLE_STATE;
      if (prefs) {
        // a saved city only carries its id, so its state comes from the API
        const city = prefs.target?.type === 'city' ? await api.city(prefs.target.id) : null;
        code = shortlistState(prefs, typeof city?.state === 'string' ? city.state : null);
        if (!code) throw new Error('no state to show');
        yours = { code, city, states: (await api.states()).states };
        paintYours();
      }
      const data = await api.stateCities(code, { limit: list.size, preset: list.preset });
      if (!Array.isArray(data?.cities)) throw new Error('unexpected state cities response');
      sample = data.cities.slice(0, list.size);
      renderSample();
    } catch (error) {
      if (error?.code === 'aborted') return;
      setStatus(list.status, '');
      renderError(list.body, error, loadSample);
    }
  }

  // Heading, sub line and buttons of the personalised block. Names come from the API, never from storage.
  function paintYours() {
    if (!yours) return;
    const { code, city, states } = yours;
    const stateName = states?.find((s) => s.code === code)?.name ?? code;
    const presetName = tt(`inv.preset.${prefs.preset}`);
    doc.getElementById('yours-title').textContent = tt('inv.you.title', { place: stateName });
    doc.getElementById('yours-sub').textContent = tt('inv.you.sub', { preset: presetName });
    const open = doc.getElementById('yours-open');
    open.textContent = tt('inv.you.open', { place: stateName });
    open.setAttribute('href', `state.html?s=${code}&preset=${prefs.preset}`);
    const cityLine = doc.getElementById('yours-city');
    clear(cityLine);
    cityLine.hidden = !(city && typeof city.name === 'string' && cityHref(prefs.target.id));
    if (!cityLine.hidden) {
      cityLine.append(h('a', { href: `city.html?c=${prefs.target.id}&preset=${prefs.preset}` }, tt('inv.you.city', { name: city.name })));
    }
  }

  function renderSources() {
    if (!meta) return;
    asOf.textContent = typeof meta.as_of === 'string' ? tt('inv.landing.sources.asof', { date: meta.as_of }) : '';
    clear(sourcesBody);
    sourcesBody.append(h('ul', { class: 'landing-sources', role: 'list' }, uniqueSources(meta.sources).map((s) =>
      h('li', { class: 'landing-sources__item' },
        h('p', { class: 'landing-sources__name' }, s.name),
        s.attribution ? h('p', { class: 'inv-small inv-muted' }, s.attribution) : null,
        s.license ? h('p', { class: 'inv-small' }, tt('inv.landing.sources.license', { license: s.license })) : null))));
  }

  async function loadMeta() {
    renderSkeleton(sourcesBody, 4);
    try {
      meta = await api.meta();
      renderSources();
      renderSample(); // the "far" wording of a why-chip can use the score bands now
    } catch (error) {
      if (error?.code === 'aborted') return;
      renderError(sourcesBody, error, loadMeta);
    }
  }

  // Text built with tt() is rebuilt in the new language; elements with data-i18n are handled by i18n.js.
  onLangChange(() => {
    doc.title = `${tt('inv.landing.headline')} | INFRA-AI`; // the static <title> stays English, so it is rebuilt like the rest
    renderSample();
    renderSources();
    paintYours();
  });
  if (prefs) {
    doc.getElementById('yours').hidden = false;
    doc.querySelector('.landing-hero').hidden = true;
    doc.getElementById('yours-change').addEventListener('click', () => globalThis.InfraOnboard?.open());
  }
  // finishing the popup saves new answers; reload to rebuild the page from them
  globalThis.addEventListener('infra:onboarded', () => globalThis.location.reload());
  loadSample();
  loadMeta();
}

// Only in a browser: the tests import the helpers above without a DOM.
if (globalThis.document?.getElementById('sample-body')) boot(globalThis.document);
