import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Reads the design tokens straight from invest.css so a palette edit that breaks contrast fails here.
const css = readFileSync(new URL('../invest.css', import.meta.url), 'utf8');
const root = css.match(/:root\s*\{([^}]*)\}/)?.[1] ?? '';
const tokens = Object.fromEntries(
  [...root.matchAll(/--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;/g)].map(([, name, hex]) => [name, hex.toUpperCase()]));

const channel = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
const luminance = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel(n >> 16) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
};
const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

// Spec section 8 pins these seven; they mirror web/index.html.
const PINNED = {
  'canvas-base': '#F7F6F2', surface: '#FFFFFF', 'text-primary': '#14202B', 'text-secondary': '#5B6773',
  'border-subtle': '#E3E1DA', 'brand-teal': '#0E5A66', 'accent-saffron': '#E08A1E',
};

// [foreground, background, minimum ratio, where it is used]. 4.5 is WCAG AA for text, 3 for UI boundaries and graphics.
const PAIRS = [
  ['text-primary', 'canvas-base', 4.5, 'body text on the page'],
  ['text-primary', 'surface', 4.5, 'text on cards'],
  ['text-primary', 'surface-sunken', 4.5, 'plain chip, language menu button'],
  ['text-primary', 'teal-tint', 4.5, 'choice chip on hover'],
  ['text-primary', 'border-subtle', 4.5, 'language menu button on hover'],
  ['text-primary', 'accent-saffron', 4.5, 'top-rank marker'],
  ['text-primary', 'error-tint', 4.5, 'error message'],
  ['text-secondary', 'canvas-base', 4.5, 'secondary text, placeholders, footer, disclaimer'],
  ['text-secondary', 'surface', 4.5, 'meter labels, badges, language menu'],
  ['text-secondary', 'surface-sunken', 4.5, 'neutral delta chip'],
  ['text-secondary', 'surface-hover', 4.5, 'language menu secondary text on hover'],
  ['brand-teal', 'canvas-base', 4.5, 'links, ghost buttons, current nav item'],
  ['brand-teal', 'surface', 4.5, 'links and secondary buttons on cards'],
  ['brand-teal', 'teal-tint', 4.5, 'secondary and ghost buttons on hover'],
  ['brand-teal-hover', 'canvas-base', 4.5, 'link on hover'],
  ['brand-teal-hover', 'teal-tint', 4.5, 'reason chip'],
  ['on-brand', 'brand-teal', 4.5, 'primary button, selected chip, rank marker, skip link'],
  ['on-brand', 'brand-teal-hover', 4.5, 'primary button on hover'],
  ['saffron-ink', 'saffron-tint', 4.5, 'watch-out chip'],
  ['up-ink', 'up-tint', 4.5, 'positive delta chip'],
  ['focus-ring', 'canvas-base', 3, 'focus outline on the page'],
  ['focus-ring', 'surface', 3, 'focus outline on cards'],
  ['border-control', 'canvas-base', 3, 'choice chip boundary on the page'],
  ['border-control', 'surface', 3, 'choice chip boundary on cards'],
  ['brand-teal', 'track', 3, 'meter and ring fill against their track'],
  ['error-ink', 'error-tint', 3, 'error accent bar'],
];

test('the seven pinned tokens keep the values from spec section 8', () => {
  for (const [name, hex] of Object.entries(PINNED)) assert.equal(tokens[name], hex, name);
});

test('every text and UI pair in invest.css meets WCAG AA', () => {
  const failures = [];
  for (const [fg, bg, min, where] of PAIRS) {
    assert.ok(tokens[fg] && tokens[bg], `invest.css :root has no hex token for ${fg} or ${bg}`);
    const ratio = contrast(tokens[fg], tokens[bg]);
    if (ratio < min) failures.push(`${where}: ${fg} ${tokens[fg]} on ${bg} ${tokens[bg]} is ${ratio.toFixed(2)}:1, needs ${min}:1`);
  }
  assert.deepEqual(failures, []);
});

test('saffron is never used as text on light backgrounds (2.7:1, fails AA)', () => {
  assert.ok(contrast(tokens['accent-saffron'], tokens.surface) < 3);
  assert.doesNotMatch(css, /(?<![-\w])color:\s*var\(--accent-saffron\)/);
});
