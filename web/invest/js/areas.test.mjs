import test from 'node:test';
import assert from 'node:assert/strict';
import { bestAreas, boundsOf, classOf, quantileBreaks, ringCentroid } from './areas.js';

const cell = (id, name, score, elig = true) => ({ properties: { id, name, score, elig }, geometry: null });

test('bestAreas keeps the best cell per name, skips ineligible cells, and keeps unnamed cells one by one', () => {
  const features = [
    cell('a', 'Hinjewadi', 90), cell('b', 'hinjewadi ', 88), cell('c', null, 85),
    cell('d', 'Baner', 84, false), cell('e', null, 80), cell('f', 'Wakad', 79), cell('g', 'Kothrud', Number.NaN),
  ];
  assert.deepEqual(bestAreas(features, 10).map((f) => f.properties.id), ['a', 'c', 'e', 'f']);
  assert.deepEqual(bestAreas(features, 2).map((f) => f.properties.id), ['a', 'c']);
  assert.deepEqual(bestAreas(undefined), []);
});

test('quantileBreaks gives up to four increasing thresholds and collapses ties', () => {
  const spread = Array.from({ length: 100 }, (_, i) => i);
  assert.deepEqual(quantileBreaks(spread), [20, 40, 60, 80]);
  assert.deepEqual(quantileBreaks([50, 50, 50, 50, 50, 50, 50, 50, 50, 50]), []);
  assert.deepEqual(quantileBreaks([10, 10, 10, 10, 10, 10, 10, 10, 90, 90]), [90]);
  assert.deepEqual(quantileBreaks([]), []);
  assert.deepEqual(quantileBreaks([Number.NaN, 1]), []);
});

test('classOf puts a score on the higher class at a threshold', () => {
  assert.equal(classOf(39, [40, 55]), 0);
  assert.equal(classOf(40, [40, 55]), 1);
  assert.equal(classOf(55, [40, 55]), 2);
  assert.equal(classOf(99, []), 0);
});

test('ringCentroid averages the corners and ignores the repeated closing point', () => {
  const square = { type: 'Polygon', coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]] };
  assert.deepEqual(ringCentroid(square), [1, 1]);
  assert.equal(ringCentroid({ type: 'Polygon', coordinates: [[[0, 0], [1, 1]]] }), null);
  assert.equal(ringCentroid(null), null);
});

test('boundsOf covers every feature, points and polygons alike', () => {
  const features = [
    { geometry: { type: 'Polygon', coordinates: [[[1, 2], [3, 2], [3, 5], [1, 2]]] } },
    { geometry: { type: 'Point', coordinates: [-1, 4] } },
    { geometry: null },
  ];
  assert.deepEqual(boundsOf(features), [-1, 2, 3, 5]);
  assert.equal(boundsOf([]), null);
});
