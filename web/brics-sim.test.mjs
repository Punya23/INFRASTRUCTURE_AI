import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { COUNTRIES, FACTORS, DEMO_REQUESTS, candidateClaims, verifyClaims, redact, score, publicCount, briefNumbersValid, buildBrief } from './brics-sim.js';

const root = dirname(fileURLToPath(import.meta.url));

test('fixture: ten members, India first and live, factor weights sum to 1', () => {
  assert.equal(COUNTRIES.length, 10);
  assert.equal(COUNTRIES.filter((c) => c.live).map((c) => c.id).join(), 'IND');
  assert.ok(Math.abs(FACTORS.reduce((s, f) => s + f.weight, 0) - 1) < 1e-9);
});

test('every country: real quote kept, made-up quote rejected (invariant 3)', () => {
  for (const c of COUNTRIES) {
    const { kept, rejected } = verifyClaims(candidateClaims(c), c.article);
    assert.deepEqual(kept.map((k) => k.id), ['F1'], c.id);
    assert.deepEqual(rejected.map((k) => k.id), ['X1'], c.id);
  }
});

test('every country: phone number is removed from the request, the text survives (invariant 5)', () => {
  for (const c of COUNTRIES) {
    const out = redact(c.request);
    assert.ok(out.includes('[phone removed]'), c.id);
    assert.doesNotMatch(out, /\d{6,}/, c.id);
    assert.ok(out.length > 20, c.id);
  }
  assert.equal(redact('no numbers here'), 'no numbers here');
  assert.equal(redact('room 12, floor 3'), 'room 12, floor 3');
});

test('score is the config-weighted sum, with drivers that add up (invariant 4)', () => {
  assert.equal(score({ stops: 1, freq: 1, roads: 1, planned: 1 }).score, 100);
  const s = score({ stops: 0.5, freq: 0.5, roads: 0.5, planned: 0.5 });
  assert.equal(s.score, 50);
  assert.equal(s.drivers.length, FACTORS.length);
  for (const c of COUNTRIES) assert.ok(score(c.v).score >= 0 && score(c.v).score <= 100);
});

test('score fails closed on bad input and bad config (invariant 2)', () => {
  assert.throws(() => score({ stops: 1.2, freq: 0, roads: 0, planned: 0 }), /0\.\.1/);
  assert.throws(() => score({ stops: 1, freq: 1, roads: 1 }), /planned/);
  assert.throws(() => score({ stops: 1, freq: 1, roads: 1, planned: 1 }, [{ id: 'stops', label: 'x', weight: 0.5 }]), /sum/);
});

test('counts under 5 are suppressed', () => {
  assert.deepEqual(publicCount(DEMO_REQUESTS.feeder), { shown: true, n: 7 });
  assert.deepEqual(publicCount(DEMO_REQUESTS.footpath), { shown: false, n: null });
  assert.equal(publicCount(4).shown, false);
  assert.equal(publicCount(5).shown, true);
});

test('brief uses only fact numbers; an invented number is caught', () => {
  assert.equal(briefNumbersValid('score 62 of 100 [S1]', [62, 100, 1]), true);
  assert.equal(briefNumbersValid('score 63 of 100', [62, 100]), false);
  for (const c of COUNTRIES) {
    const r = score(c.v);
    const b = buildBrief(c, r, verifyClaims(candidateClaims(c), c.article).kept, DEMO_REQUESTS.feeder);
    assert.equal(b.templated, false, c.id);
    assert.ok(b.text.includes(`score ${r.score} of 100`), c.id);
  }
});

test('brief drops the request and project lines when there is nothing safe to say', () => {
  const c = COUNTRIES[0];
  const b = buildBrief(c, score(c.v), [], DEMO_REQUESTS.footpath);
  assert.doesNotMatch(b.text, /residents asked/);
  assert.doesNotMatch(b.text, /stations/);
});

test('map data: every member has a path and a pin inside the map', () => {
  const world = JSON.parse(readFileSync(join(root, 'brics-world.json'), 'utf8'));
  const members = new Set(world.c.filter((c) => c.m).map((c) => c.m));
  for (const c of COUNTRIES) {
    assert.ok(members.has(c.id), `${c.id} missing from brics-world.json`);
    assert.ok(Math.abs(c.lonlat[0]) <= 180 && c.lonlat[1] <= 84 && c.lonlat[1] >= -58, `${c.id} pin outside map`);
  }
});
