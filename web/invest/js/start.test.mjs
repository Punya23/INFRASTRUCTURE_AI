import assert from 'node:assert/strict';
import { test } from 'node:test';

import { destination, filterStates, initialAnswers, moveIndex, resolveTarget, searchText, toPrefs } from './start.js';

test('searchText: trims, collapses spaces and counts characters, not bytes', () => {
  assert.deepEqual(searchText('  thane  '), { text: 'thane' });
  assert.deepEqual(searchText('new    delhi'), { text: 'new delhi' });
  assert.deepEqual(searchText('ठाणे'), { text: 'ठाणे' }); // 4 code points, well over 2 bytes each
  assert.deepEqual(searchText('a'.repeat(64)), { text: 'a'.repeat(64) });
});

test('searchText: too short, too long and empty never reach the API', () => {
  assert.deepEqual(searchText(''), { problem: 'empty' });
  assert.deepEqual(searchText('   '), { problem: 'empty' });
  assert.deepEqual(searchText(undefined), { problem: 'empty' });
  assert.deepEqual(searchText('a'), { problem: 'short' });
  assert.deepEqual(searchText(' a '), { problem: 'short' });
  assert.deepEqual(searchText('a'.repeat(65)), { problem: 'long' });
  assert.deepEqual(searchText('a'.repeat(200)), { problem: 'long' });
});

test('searchText: hostile text is valid search text; escaping is the renderer\'s job', () => {
  assert.equal(searchText('<script>alert(1)</script>').text, '<script>alert(1)</script>');
  assert.equal(searchText('../../etc/passwd').text, '../../etc/passwd');
  assert.equal(searchText("' OR 1=1 --").text, "' OR 1=1 --");
});

test('filterStates: substring on name, exact on code, case-insensitive; blank keeps all', () => {
  const states = [
    { code: 'MH', name: 'Maharashtra' },
    { code: 'MP', name: 'Madhya Pradesh' },
    { code: 'GA', name: 'Goa' },
  ];
  assert.equal(filterStates(states, '').length, 3);
  assert.equal(filterStates(states, '   ').length, 3);
  assert.deepEqual(filterStates(states, 'MAHA').map((s) => s.code), ['MH']);
  assert.deepEqual(filterStates(states, 'ma').map((s) => s.code), ['MH', 'MP']);
  assert.deepEqual(filterStates(states, 'ga').map((s) => s.code), ['GA']); // by code
  assert.deepEqual(filterStates(states, 'zzz'), []);
});

test('moveIndex: arrows, Home and End clamp at the ends; other keys are not ours', () => {
  assert.equal(moveIndex(0, 'ArrowRight', 5, 3), 1);
  assert.equal(moveIndex(4, 'ArrowRight', 5, 3), 4);
  assert.equal(moveIndex(0, 'ArrowLeft', 5, 3), 0);
  assert.equal(moveIndex(1, 'ArrowDown', 5, 3), 4);
  assert.equal(moveIndex(3, 'ArrowDown', 5, 3), 4); // no row below: clamp to the last
  assert.equal(moveIndex(4, 'ArrowUp', 5, 3), 1);
  assert.equal(moveIndex(1, 'ArrowUp', 5, 3), 0);
  assert.equal(moveIndex(2, 'Home', 5, 3), 0);
  assert.equal(moveIndex(2, 'End', 5, 3), 4);
  assert.equal(moveIndex(-1, 'ArrowDown', 5, 1), 0); // a list with nothing active yet starts at the top
  assert.equal(moveIndex(2, 'Enter', 5, 3), null);
  assert.equal(moveIndex(0, 'ArrowDown', 0, 1), null); // nothing to move to
});

test('resolveTarget: the choice decides which answer counts', () => {
  const base = { homeState: 'MH', stateCode: 'KA', city: { id: 'pune' }, preset: 'balanced' };
  assert.deepEqual(resolveTarget({ ...base, choice: 'home' }), { type: 'state', code: 'MH' });
  assert.deepEqual(resolveTarget({ ...base, choice: 'state' }), { type: 'state', code: 'KA' });
  assert.deepEqual(resolveTarget({ ...base, choice: 'city' }), { type: 'city', id: 'pune' });
  assert.equal(resolveTarget({ ...base, choice: null }), null);
  assert.equal(resolveTarget({ ...base, homeState: null, choice: 'home' }), null); // step 1 skipped
  assert.equal(resolveTarget({ ...base, city: null, choice: 'city' }), null);
});

test('destination: state and city pages with the preset; anything malformed is null', () => {
  const a = { homeState: 'MH', stateCode: null, city: null, choice: 'home', preset: 'balanced' };
  assert.equal(destination(a), 'state.html?s=MH&preset=balanced');
  assert.equal(destination({ ...a, choice: 'city', city: { id: 'aurangabad-mh' }, preset: 'commuter' }), 'city.html?c=aurangabad-mh&preset=commuter');
  assert.equal(destination({ ...a, choice: 'city', city: { id: '../../etc/passwd' } }), null);
  assert.equal(destination({ ...a, homeState: 'mh' }), null);
  assert.equal(destination({ ...a, choice: null }), null);
  assert.equal(destination({ ...a, preset: 'moon' }), 'state.html?s=MH&preset=balanced'); // unknown preset falls back
});

test('initialAnswers and toPrefs round-trip what was saved', () => {
  assert.deepEqual(initialAnswers({ homeState: 'MH', target: { type: 'state', code: 'MH' }, preset: 'highway' }),
    { homeState: 'MH', choice: 'home', stateCode: null, city: null, preset: 'highway' });
  assert.deepEqual(initialAnswers({ homeState: 'MH', target: { type: 'state', code: 'KA' }, preset: 'balanced' }),
    { homeState: 'MH', choice: 'state', stateCode: 'KA', city: null, preset: 'balanced' });
  assert.deepEqual(initialAnswers({ homeState: null, target: { type: 'city', id: 'pune' }, preset: 'growth' }),
    { homeState: null, choice: 'city', stateCode: null, city: { id: 'pune', name: null, state: null }, preset: 'growth' });
  assert.deepEqual(initialAnswers({ homeState: null, target: null, preset: 'balanced' }),
    { homeState: null, choice: null, stateCode: null, city: null, preset: 'balanced' });

  const answers = initialAnswers({ homeState: 'MH', target: { type: 'city', id: 'pune' }, preset: 'commuter' });
  assert.deepEqual(toPrefs(answers), { homeState: 'MH', target: { type: 'city', id: 'pune' }, preset: 'commuter' });
});
