// Small building blocks shared by the landing sample, the state result and the city page. All text
// goes through tt() and h(), so nothing from the API is parsed as markup.

import { PRESET_IDS } from './config.js';
import { h } from './ui.js';
import { explain } from './explain.js';
import { formatScore, tt } from './format.js';

// One chip per driver ("why") or gap ("watch-out"); the wording comes from explain() and the locale files.
export function reasonChips(items, kind, meta) {
  return (items ?? []).map((item) => {
    const { key, params } = explain(kind, item, meta);
    return h('span', { class: `inv-chip inv-chip--${kind === 'gap' ? 'gap' : 'why'}`, dataset: { i18n: key } }, tt(key, params));
  });
}

// Bar for a 0 to 100 value; null shows the hatched "not measured" bar, never an empty one.
export function meter(labelKey, value) {
  const known = Number.isFinite(value);
  return h('div', { class: `inv-meter${known ? '' : ' inv-meter--unknown'}`, style: { '--value': known ? Math.max(0, Math.min(100, value)) : 0 } },
    h('span', { class: 'inv-meter__label', dataset: { i18n: labelKey } }, tt(labelKey)),
    h('span', { class: 'inv-meter__value' }, formatScore(value)),
    h('div', { class: 'inv-meter__bar', 'aria-hidden': true }));
}

// Score ring with the number inside; the label is for screen readers.
export function scoreRing(score, { large = false } = {}) {
  const known = Number.isFinite(score);
  return h('div', {
    class: `inv-ring${large ? ' inv-ring--lg' : ''}`, style: { '--value': known ? score : 0 },
    role: 'img', 'aria-label': known ? tt('inv.score.aria', { n: formatScore(score) }) : '—',
  }, h('span', { class: 'inv-ring__value', 'aria-hidden': true }, formatScore(score)));
}

// The hexagonal rank mark; rank 1 is saffron.
export function rankMark(rank) {
  return h('span', { class: `inv-rank${rank === 1 ? ' inv-rank--top' : ''}`, role: 'img', 'aria-label': tt('inv.rank.aria', { n: rank }) },
    h('span', { 'aria-hidden': true }, rank));
}

export const tierLabel = (tier) => tt(`inv.tier.${tier}`);

// The four preset choices as toggle chips; `current` is pressed, onPick(id) gets a new choice.
export function presetChips(current, onPick) {
  return PRESET_IDS.map((id) => h('button', {
    class: 'inv-chip inv-chip--choice', type: 'button', 'aria-pressed': String(id === current),
    dataset: { i18n: `inv.preset.${id}` }, onclick: () => onPick(id),
  }, tt(`inv.preset.${id}`)));
}

// "Best area: X", or the unnamed wording when the area has no place name yet.
export function bestAreaText(bestArea, keyPrefix) {
  if (!bestArea) return null;
  return bestArea.name ? tt(`${keyPrefix}.best`, { name: bestArea.name }) : tt(`${keyPrefix}.best.unnamed`);
}
