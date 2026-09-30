// BRICS page simulation: the INFRA-AI pipeline run on made-up sample data for ten pilot cities.
// Nothing here is fetched, extracted or scored from real sources. The sample article, request and factor values are
// invented for the demo; the *checks* are the real ones the platform enforces (AGENTS.md invariants 2, 3, 4, 5).
// Pure functions, no DOM, so `node --test web/brics-sim.test.mjs` runs them.

// Score config. Invariant 4: a config-weighted sum of observable facts, never a model. Weights: team judgment, 2026-09-30.
export const FACTORS = [
  { id: 'stops',   label: 'Stops within 1 km of homes', weight: 0.35 },
  { id: 'freq',    label: 'Service frequency',          weight: 0.25 },
  { id: 'roads',   label: 'Road condition',             weight: 0.20 },
  { id: 'planned', label: 'Gap covered by funded projects', weight: 0.20 },
];
// Invariant 5: public outputs suppress any count below this. Basis: ADR-0011.
export const MIN_PUBLIC_COUNT = 5;

// `v` are observable-fact values in 0..1 (sample numbers). `article` is sample text, not a real report.
// `quote` must appear verbatim in `article` (invariant 3); the second claim below never does, to show the rejection.
export const COUNTRIES = [
  { id: 'IND', name: 'India', lang: 'Hindi', dir: 'ltr', city: 'Bengaluru', lonlat: [77.6, 12.97], live: true,
    v: { stops: 0.62, freq: 0.55, roads: 0.48, planned: 0.40 },
    article: 'शहर की नई मेट्रो लाइन का निर्माण इस साल शुरू होगा। लाइन में 12 स्टेशन होंगे।',
    gloss: 'Construction of the city\'s new metro line starts this year. The line will have 12 stations.',
    quote: 'लाइन में 12 स्टेशन होंगे',
    request: 'स्टेशन तक कोई बस नहीं है, कृपया बस सेवा शुरू करें। मेरा नंबर 9876543210 है।',
    requestGloss: 'There is no bus to the station, please start a bus service.' },
  { id: 'BRA', name: 'Brazil', lang: 'Portuguese', dir: 'ltr', city: 'São Paulo', lonlat: [-46.6, -23.55],
    v: { stops: 0.71, freq: 0.6, roads: 0.52, planned: 0.35 },
    article: 'A construção da nova linha de metrô da cidade começa este ano. A linha terá 12 estações.',
    gloss: 'Construction of the city\'s new metro line starts this year. The line will have 12 stations.',
    quote: 'A linha terá 12 estações',
    request: 'Não há ônibus até a estação, por favor criem uma linha. Meu telefone é 11 91234 5678.',
    requestGloss: 'There is no bus to the station, please create a route.' },
  { id: 'RUS', name: 'Russia', lang: 'Russian', dir: 'ltr', city: 'Kazan', lonlat: [49.1, 55.8],
    v: { stops: 0.78, freq: 0.66, roads: 0.58, planned: 0.30 },
    article: 'Строительство новой линии метро в городе начнётся в этом году. На линии будет 12 станций.',
    gloss: 'Construction of the city\'s new metro line starts this year. The line will have 12 stations.',
    quote: 'На линии будет 12 станций',
    request: 'До станции нет автобуса, пожалуйста, запустите маршрут. Мой телефон 8 912 345 67 89.',
    requestGloss: 'There is no bus to the station, please start a route.' },
  { id: 'CHN', name: 'China', lang: 'Mandarin', dir: 'ltr', city: 'Chengdu', lonlat: [104.07, 30.66],
    v: { stops: 0.82, freq: 0.74, roads: 0.69, planned: 0.45 },
    article: '本市新地铁线路将于今年开工建设。线路共设12座车站。',
    gloss: 'The city\'s new metro line starts construction this year. The line has 12 stations.',
    quote: '线路共设12座车站',
    request: '车站附近没有公交，请开通公交线路。我的电话是13800138000。',
    requestGloss: 'There is no bus near the station, please open a bus route.' },
  { id: 'ZAF', name: 'South Africa', lang: 'English', dir: 'ltr', city: 'Johannesburg', lonlat: [28.05, -26.2],
    v: { stops: 0.49, freq: 0.41, roads: 0.44, planned: 0.25 },
    article: 'Construction of the city\'s new bus corridor starts this year. The corridor will have 12 stations.',
    gloss: 'Construction of the city\'s new bus corridor starts this year. The corridor will have 12 stations.',
    quote: 'The corridor will have 12 stations',
    request: 'There is no bus to the station, please add a route. My number is 082 123 4567.',
    requestGloss: 'There is no bus to the station, please add a route.' },
  { id: 'EGY', name: 'Egypt', lang: 'Arabic', dir: 'rtl', city: 'Cairo', lonlat: [31.24, 30.04],
    v: { stops: 0.58, freq: 0.52, roads: 0.46, planned: 0.38 },
    article: 'سيبدأ بناء خط المترو الجديد في المدينة هذا العام. سيضم الخط 12 محطة.',
    gloss: 'Construction of the city\'s new metro line starts this year. The line will have 12 stations.',
    quote: 'سيضم الخط 12 محطة',
    request: 'لا توجد حافلة إلى المحطة، يرجى تشغيل خط حافلات. رقمي 01234567890.',
    requestGloss: 'There is no bus to the station, please run a bus line.' },
  { id: 'ETH', name: 'Ethiopia', lang: 'Amharic', dir: 'ltr', city: 'Addis Ababa', lonlat: [38.75, 9.03],
    v: { stops: 0.38, freq: 0.3, roads: 0.36, planned: 0.22 },
    article: 'የከተማዋ አዲስ የባቡር መስመር ግንባታ በዚህ ዓመት ይጀምራል። መስመሩ 12 ጣቢያዎች ይኖሩታል።',
    gloss: 'Construction of the city\'s new rail line starts this year. The line will have 12 stations.',
    quote: 'መስመሩ 12 ጣቢያዎች ይኖሩታል',
    request: 'ወደ ጣቢያው አውቶቡስ የለም፣ እባክዎ መስመር ይጀምሩ። ስልኬ 0911234567።',
    requestGloss: 'There is no bus to the station, please start a route.' },
  { id: 'IRN', name: 'Iran', lang: 'Persian', dir: 'rtl', city: 'Isfahan', lonlat: [51.67, 32.65],
    v: { stops: 0.55, freq: 0.5, roads: 0.5, planned: 0.33 },
    article: 'ساخت خط جدید مترو در این شهر امسال آغاز می‌شود. این خط ۱۲ ایستگاه خواهد داشت.',
    gloss: 'Construction of a new metro line in this city starts this year. The line will have 12 stations.',
    quote: 'این خط ۱۲ ایستگاه خواهد داشت',
    request: 'تا ایستگاه اتوبوسی نیست، لطفاً یک خط اتوبوس راه‌اندازی کنید. شماره من 09121234567 است.',
    requestGloss: 'There is no bus to the station, please set up a bus line.' },
  { id: 'ARE', name: 'UAE', lang: 'Arabic', dir: 'rtl', city: 'Abu Dhabi', lonlat: [54.37, 24.47],
    v: { stops: 0.6, freq: 0.63, roads: 0.81, planned: 0.5 },
    article: 'سيبدأ بناء خط المترو الجديد في المدينة هذا العام. سيضم الخط 12 محطة.',
    gloss: 'Construction of the city\'s new metro line starts this year. The line will have 12 stations.',
    quote: 'سيضم الخط 12 محطة',
    request: 'لا توجد حافلة إلى المحطة، يرجى تشغيل خط حافلات. رقمي 0501234567.',
    requestGloss: 'There is no bus to the station, please run a bus line.' },
  { id: 'IDN', name: 'Indonesia', lang: 'Bahasa Indonesia', dir: 'ltr', city: 'Surabaya', lonlat: [112.75, -7.25],
    v: { stops: 0.51, freq: 0.47, roads: 0.45, planned: 0.28 },
    article: 'Pembangunan jalur MRT baru di kota ini dimulai tahun ini. Jalur itu akan memiliki 12 stasiun.',
    gloss: 'Construction of the city\'s new MRT line starts this year. The line will have 12 stations.',
    quote: 'Jalur itu akan memiliki 12 stasiun',
    request: 'Tidak ada bus ke stasiun, tolong buka rute bus. Nomor saya 081234567890.',
    requestGloss: 'There is no bus to the station, please open a bus route.' },
];

// The stub "extractor" proposes two claims per article; it is a fixture, no model is called. The second one
// carries a quote that is not in the source, which is exactly what the verifier must reject.
export function candidateClaims(c) {
  return [
    { id: 'F1', text: 'New transit line, 12 stations, construction starts this year', stations: 12, quote: c.quote },
    { id: 'X1', text: 'Line opens next year', quote: 'the line opens next year' },
  ];
}

// Invariant 3: a claim is kept only if its evidence quote is a verbatim substring of the source. Else it goes to review.
export function verifyClaims(claims, article) {
  const kept = [], rejected = [];
  for (const cl of claims) (cl.quote && article.includes(cl.quote) ? kept : rejected).push(cl);
  return { kept, rejected };
}

// Invariant 5: strip phone-like digit runs (8+ digits, spaces and dashes allowed) before storage or any hosted model.
export function redact(text) {
  return text.replace(/\+?\d[\d\s-]{6,}\d/g, '[phone removed]');
}

// Invariants 4 + 2: weighted sum with stored drivers; a factor outside 0..1 or weights not summing to 1 throws, not defaults.
export function score(values, factors = FACTORS) {
  const total = factors.reduce((s, f) => s + f.weight, 0);
  if (Math.abs(total - 1) > 1e-9) throw new Error(`factor weights sum to ${total}, expected 1`);
  const drivers = factors.map((f) => {
    const v = values[f.id];
    if (typeof v !== 'number' || v < 0 || v > 1) throw new Error(`factor ${f.id} must be a number in 0..1, got ${v}`);
    return { id: f.id, label: f.label, weight: f.weight, value: v, points: Math.round(f.weight * v * 100) };
  });
  return { score: Math.round(drivers.reduce((s, d) => s + d.weight * d.value * 100, 0)), drivers };
}

// Aggregates below MIN_PUBLIC_COUNT are suppressed, not shown as small numbers.
export function publicCount(n) {
  return n >= MIN_PUBLIC_COUNT ? { shown: true, n } : { shown: false, n: null };
}

// Invariant 3: the brief may only use numbers that appear in the fact set; otherwise fall back to a template.
export function briefNumbersValid(brief, facts) {
  const allowed = new Set(facts.map(String));
  return (brief.match(/\d+/g) || []).every((n) => allowed.has(n));
}

// Brief ids ([S1], [F1], [R1]) are fact ids, so the ids themselves are allowed numbers (1).
export function buildBrief(c, result, kept, feederRequests) {
  const weakest = result.drivers.reduce((a, b) => (b.value < a.value ? b : a));
  const weakPct = Math.round(weakest.value * 100);
  const stations = kept.length ? kept[0].stations : null;
  const pub = publicCount(feederRequests);
  const parts = [`${c.city}: access score ${result.score} of 100 [S1].`,
    `Weakest driver: ${weakest.label.toLowerCase()} at ${weakPct}% [S1].`];
  if (stations) parts.push(`One reported project: ${stations} stations, construction starts this year [F1].`);
  if (pub.shown) parts.push(`${pub.n} residents asked for a feeder bus to the station [R1].`);
  const brief = parts.join(' ');
  const facts = [result.score, weakPct, stations, pub.n, 1, 100].filter((x) => x !== null);
  return briefNumbersValid(brief, facts)
    ? { text: brief, templated: false }
    : { text: `${c.city}: see the scorecard for facts and sources.`, templated: true };
}

// Resident requests for the demo topics. Fixture counts; the second topic is under the threshold to show suppression.
export const DEMO_REQUESTS = { feeder: 7, footpath: 3 };

// Country profiles: who would supply the official numbers and boundaries, which privacy regime applies, and
// what is still to do before a pilot. Agency and statute names are public-record pointers for planning, not legal
// advice, and each needs checking with local counsel before any real work (the page says so). Nothing is ingested.
export const PROFILES = {
  IND: { stats: 'MoSPI / Census of India', boundary: 'Survey of India', privacy: 'Digital Personal Data Protection Act, 2023', note: 'Live today: OSM, WorldPop, PIB press releases and tenders are already in the pipeline.', script: 'Devanagari (and 20 more languages)' },
  BRA: { stats: 'IBGE', boundary: 'IBGE (official territorial mesh)', privacy: 'LGPD (Lei 13.709/2018)', note: 'Portuguese is already a UI language; needs a gold set for Brazilian news and requests.', script: 'Latin' },
  RUS: { stats: 'Rosstat', boundary: 'Rosreestr', privacy: 'Federal Law 152-FZ on Personal Data', note: 'Data-localisation and cross-border rules apply; hosting must be reviewed before any pilot.', script: 'Cyrillic' },
  CHN: { stats: 'National Bureau of Statistics', boundary: 'Ministry of Natural Resources', privacy: 'Personal Information Protection Law (PIPL, 2021)', note: 'Mapping and cross-border data rules are strict; licensing of any boundary data comes first.', script: 'Simplified Han' },
  ZAF: { stats: 'Stats SA', boundary: 'Chief Directorate: National Geo-spatial Information', privacy: 'Protection of Personal Information Act (POPIA)', note: 'English is the working language; other official languages would follow the same config route.', script: 'Latin' },
  EGY: { stats: 'CAPMAS', boundary: 'Egyptian Survey Authority', privacy: 'Personal Data Protection Law No. 151 of 2020', note: 'Arabic right-to-left layout is exercised by this page; speech and translation need a gold set.', script: 'Arabic (right to left)' },
  ETH: { stats: 'Ethiopian Statistics Service', boundary: 'Ethiopian Mapping Agency', privacy: 'Personal Data Protection Proclamation No. 1321/2024', note: 'Amharic has thin open corpora; the gold set would need to be built by hand.', script: 'Ethiopic (Ge\'ez)' },
  IRN: { stats: 'Statistical Centre of Iran', boundary: 'National Cartographic Center', privacy: 'No single comprehensive statute; confirm the current position', note: 'Persian right-to-left; hosted AI providers and data access need a separate sanctions and access review.', script: 'Persian (right to left)' },
  ARE: { stats: 'Federal Competitiveness and Statistics Centre', boundary: 'Per-emirate survey authorities', privacy: 'Federal Decree-Law 45 of 2021 (PDPL)', note: 'Boundaries and open data sit with each emirate, so the pilot starts from one emirate.', script: 'Arabic (right to left)' },
  IDN: { stats: 'BPS (Statistics Indonesia)', boundary: 'BIG (Geospatial Information Agency)', privacy: 'Personal Data Protection Law No. 27 of 2022', note: 'Island geography needs ferry and bus-rapid-transit modes in the field config.', script: 'Latin' },
};

// The same checklist for every member; status is "not started" for all but India, because nothing else is built.
export const READINESS = [
  'Licence review of each dataset (ADR-0012)',
  'Official boundary source agreed (ADR-0007)',
  'Privacy review against the local law',
  'Gold set for the national language (ADR-0008)',
  'One city config file (config/cities/)',
];
