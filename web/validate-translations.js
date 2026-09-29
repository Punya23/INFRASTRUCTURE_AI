/**
 * =============================================================================
 * INFRA-AI Translation Validation Script
 * =============================================================================
 * Compares all locale JSON files against en.json to find:
 *   - Missing keys (present in en.json but not in the locale)
 *   - Extra keys (present in locale but not in en.json)
 *   - Empty values
 *
 * Usage:
 *   node validate-translations.js
 *
 * Exit code 0 if only non-critical issues; exit code 1 if English keys missing.
 * =============================================================================
 */
const fs = require('fs');
const path = require('path');

const LOCALES_DIR = path.join(__dirname, 'locales');
const EN_FILE = path.join(LOCALES_DIR, 'en.json');

// Load English as source of truth
let enKeys;
try {
  const enData = JSON.parse(fs.readFileSync(EN_FILE, 'utf8'));
  enKeys = Object.keys(enData);
  console.log(`\n✅  English source of truth: ${enKeys.length} keys\n`);
} catch (e) {
  console.error(`❌  CRITICAL: Cannot read ${EN_FILE}:`, e.message);
  process.exit(1);
}

// Discover all locale files
const localeFiles = fs.readdirSync(LOCALES_DIR)
  .filter(f => f.endsWith('.json') && f !== 'en.json')
  .sort();

let totalIssues = 0;
let criticalIssues = 0;
const results = [];

for (const file of localeFiles) {
  const code = file.replace('.json', '');
  const filePath = path.join(LOCALES_DIR, file);

  let localeData;
  try {
    localeData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    console.error(`❌  ${code}: Failed to parse ${file}: ${e.message}`);
    criticalIssues++;
    continue;
  }

  const localeKeys = Object.keys(localeData);
  const missing = enKeys.filter(k => !(k in localeData));
  const extra = localeKeys.filter(k => !enKeys.includes(k));
  const empty = localeKeys.filter(k => localeData[k] === '' || localeData[k] === null);
  const coverage = ((localeKeys.length - extra.length) / enKeys.length * 100).toFixed(1);

  const status = missing.length === 0 ? '✅' : (missing.length <= 10 ? '⚠️' : '🔶');

  results.push({
    code,
    total: localeKeys.length,
    missing: missing.length,
    extra: extra.length,
    empty: empty.length,
    coverage
  });

  console.log(`${status}  ${code.toUpperCase().padEnd(4)} — ${localeKeys.length} keys, ${coverage}% coverage`);
  if (missing.length > 0) {
    console.log(`       Missing ${missing.length} keys: ${missing.slice(0, 8).join(', ')}${missing.length > 8 ? '...' : ''}`);
    totalIssues += missing.length;
  }
  if (extra.length > 0) {
    console.log(`       Extra ${extra.length} keys: ${extra.join(', ')}`);
  }
  if (empty.length > 0) {
    console.log(`       Empty ${empty.length} values: ${empty.join(', ')}`);
    totalIssues += empty.length;
  }
}

// Summary
console.log('\n' + '═'.repeat(60));
console.log('TRANSLATION COVERAGE SUMMARY');
console.log('═'.repeat(60));
console.log(`Source of truth (en.json): ${enKeys.length} keys`);
console.log(`Locales validated: ${localeFiles.length}`);
console.log(`Total missing translations: ${totalIssues}`);
console.log(`Critical issues: ${criticalIssues}`);
console.log('');

// Table
console.log('Code  Keys  Coverage  Missing  Extra  Empty');
console.log('----  ----  --------  -------  -----  -----');
for (const r of results) {
  console.log(
    `${r.code.padEnd(6)}${String(r.total).padEnd(6)}${(r.coverage + '%').padEnd(10)}${String(r.missing).padEnd(9)}${String(r.extra).padEnd(7)}${r.empty}`
  );
}

console.log('');
if (criticalIssues > 0) {
  console.log('❌  FAIL: Critical issues found (unparseable locale files)');
  process.exit(1);
} else if (totalIssues === 0) {
  console.log('✅  PASS: All translations complete');
} else {
  console.log(`⚠️  PASS with warnings: ${totalIssues} missing/empty translations (fallback to English will be used)`);
}
process.exit(0);
