import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { CITY_ID, PRESET_IDS, STATE_CODE } from './config.js';

// api/openapi.yaml is the source of truth (AGENTS invariant 10); config.js repeats a few of its values so the
// pages can check ids from the address bar before any request. This fails when the two drift apart.
const yaml = readFileSync(new URL('../../../api/openapi.yaml', import.meta.url), 'utf8');

const patternOf = (param) => {
  const m = yaml.match(new RegExp(`\\n    ${param}:\\n(?:      .*\\n)*?      schema: \\{type: string, pattern: "([^"]+)"\\}`));
  assert.ok(m, `no ${param} pattern in api/openapi.yaml`);
  return m[1];
};

test('STATE_CODE equals the StateCode path parameter pattern', () => {
  assert.equal(STATE_CODE.source, patternOf('StateCode'));
  assert.equal(STATE_CODE.flags, '');
});

test('CITY_ID equals the CityId path parameter pattern', () => {
  assert.equal(CITY_ID.source, patternOf('CityId'));
  assert.equal(CITY_ID.flags, '');
});

test('PRESET_IDS equals the PresetId enum, in order', () => {
  const m = yaml.match(/\n    PresetId:\n      type: string\n      enum: \[([^\]]+)\]/);
  assert.ok(m, 'no PresetId enum in api/openapi.yaml');
  assert.deepEqual(PRESET_IDS, m[1].split(',').map((s) => s.trim()));
});
