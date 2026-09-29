// Pure helpers for the city page (no DOM): which areas to list, how to colour them, where to fly to.

// Best areas for the list: eligible areas only (population big enough to be a neighbourhood), the
// highest-scoring cell for each place name, unnamed cells kept one by one (they share no name), best
// first. `features` are GeoJSON features from /v1/cities/{id}/areas, already sorted by score for the
// requested preset, so the first cell seen for a name is that name's best.
export function bestAreas(features, limit = 10) {
  const seen = new Set();
  const out = [];
  for (const f of features ?? []) {
    const p = f.properties ?? {};
    if (!p.elig || !Number.isFinite(p.score)) continue;
    const name = typeof p.name === 'string' && p.name.trim() !== '' ? p.name.trim().toLowerCase() : null;
    if (name !== null) {
      if (seen.has(name)) continue;
      seen.add(name);
    }
    out.push(f);
    if (out.length === limit) break;
  }
  return out;
}

// Four thresholds that cut the scores into five classes of about equal size, so the map uses its whole
// colour ramp whatever the city's range is. Duplicates collapse (a city where most cells tie): the
// result can be shorter than four, and the caller draws fewer classes.
export function quantileBreaks(scores, classes = 5) {
  const sorted = (scores ?? []).filter(Number.isFinite).sort((a, b) => a - b);
  if (sorted.length === 0) return [];
  const cuts = [];
  for (let i = 1; i < classes; i += 1) {
    const value = sorted[Math.min(sorted.length - 1, Math.floor((i * sorted.length) / classes))];
    if (cuts.length === 0 || value > cuts[cuts.length - 1]) cuts.push(value);
  }
  // a threshold equal to the minimum would leave the first class empty
  return cuts.filter((c) => c > sorted[0]);
}

// Which class (0-based) a score falls in for the given thresholds: [40, 55] puts 39 in 0, 40 in 1, 55 in 2.
export function classOf(score, breaks) {
  let i = 0;
  while (i < breaks.length && score >= breaks[i]) i += 1;
  return i;
}

// Mean of the outer ring's corners, as [lon, lat]: good enough to centre a popup on a hexagon.
export function ringCentroid(geometry) {
  const ring = geometry?.type === 'Polygon' ? geometry.coordinates?.[0] : geometry?.coordinates?.[0]?.[0];
  if (!Array.isArray(ring) || ring.length < 3) return null;
  const closed = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1];
  const corners = closed ? ring.slice(0, -1) : ring;
  const sum = corners.reduce((a, [x, y]) => [a[0] + x, a[1] + y], [0, 0]);
  return [sum[0] / corners.length, sum[1] / corners.length];
}

// [west, south, east, north] over every ring of every feature; null when there is nothing to fit.
export function boundsOf(features) {
  let box = null;
  const visit = (coords) => {
    if (typeof coords[0] === 'number') {
      box = box
        ? [Math.min(box[0], coords[0]), Math.min(box[1], coords[1]), Math.max(box[2], coords[0]), Math.max(box[3], coords[1])]
        : [coords[0], coords[1], coords[0], coords[1]];
    } else {
      coords.forEach(visit);
    }
  };
  for (const f of features ?? []) if (f.geometry?.coordinates) visit(f.geometry.coordinates);
  return box;
}
