// Landing page: a live sample (top three Maharashtra cities), the honeycomb built from the top city's own
// areas, and the sources with their licenses. The page reads well without any of it: every request
// failing leaves the static text, and the sample shows an error with Retry.

import { api } from './api.js';
import { bestAreaText, rankMark, reasonChips, scoreRing, tierLabel } from './cards.js';
import { tt } from './format.js';
import { i18nReady, renderShell } from './shell.js';
import { clear, h, onLangChange, renderError, renderSkeleton } from './ui.js';

renderShell();
await i18nReady;

const sampleBody = document.getElementById('sample-body');
const tilesBox = document.getElementById('hero-tiles');
const sourcesList = document.getElementById('sources-list');
let meta = null;
let sample = null;

function renderSample() {
  if (!sample || !meta) return;
  clear(sampleBody);
  sampleBody.append(...sample.cities.map((city) => {
    const why = reasonChips(city.drivers.slice(0, 1), 'why', meta);
    const best = bestAreaText(city.best_area, 'inv.sample');
    return h('div', { class: 'inv-sample__item' },
      rankMark(city.rank),
      h('div', { class: 'inv-stack inv-stack--tight' },
        h('div', { class: 'inv-cluster' },
          h('a', { href: `city.html?c=${encodeURIComponent(city.id)}&preset=balanced` }, h('strong', null, city.name)),
          h('span', { class: 'inv-badge' }, tierLabel(city.tier))),
        h('div', { class: 'inv-cluster' }, why),
        best ? h('p', { class: 'inv-small inv-muted' }, best) : null),
      scoreRing(city.score));
  }));
}

function renderSources() {
  if (!meta) return;
  clear(sourcesList);
  sourcesList.append(...meta.sources.map((source) => h('li', { class: 'inv-stack inv-stack--tight' },
    h('strong', null, source.name),
    h('p', { class: 'inv-small inv-muted' }, tt('inv.sources.license', { license: source.license })),
    h('p', { class: 'inv-small inv-muted' }, source.attribution))));
}

// Honeycomb: rows of 5, 4, 5, 4, 3 cells. Tint follows the area's score; the best area is saffron.
const ROWS = [5, 4, 5, 4, 3];
const CELLS = ROWS.reduce((a, b) => a + b, 0);
function renderTiles(scores) {
  clear(tilesBox);
  const lo = Math.min(...scores);
  const span = Math.max(...scores) - lo || 1;
  let i = 0;
  for (const count of ROWS) {
    const row = h('div', { class: 'inv-tiles__row' });
    for (let c = 0; c < count; c += 1, i += 1) {
      const score = scores[i];
      row.append(h('span', {
        class: `inv-tiles__cell${i === 0 ? ' inv-tiles__cell--top' : ''}`,
        style: { '--t': score == null ? 0.1 : (0.15 + (0.8 * (score - lo)) / span).toFixed(2) },
      }));
    }
    tilesBox.append(row);
  }
}

// Decoration only: a failure here is silent because the page has lost nothing that matters.
async function loadTiles(cityId) {
  try {
    const areas = await api.areas(cityId, { preset: 'balanced', limit: CELLS });
    const scores = areas.features.map((f) => f.properties.score);
    if (scores.length) renderTiles(scores);
  } catch {
    // keep the empty motif
  }
}

// Meta feeds both the sample's wording and the sources list; the sources show even if the sample fails.
const metaReady = api.meta().then((m) => { meta = m; renderSources(); renderSample(); }).catch(() => {});

async function loadSample() {
  renderSkeleton(sampleBody, 3);
  try {
    sample = await api.stateCities('MH', { limit: 3 });
    await metaReady;
    if (!meta) meta = await api.meta(); // the first request failed; a retry gets another chance
  } catch (error) {
    renderError(sampleBody, error, loadSample);
    return;
  }
  renderSample();
  renderSources();
  if (sample.cities[0]) loadTiles(sample.cities[0].id);
}

loadSample();
onLangChange(() => { renderSample(); renderSources(); });
