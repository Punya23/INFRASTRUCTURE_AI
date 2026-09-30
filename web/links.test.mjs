// Every local link on every page must land somewhere real: no bare "#", no missing file, no missing #anchor.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const pages = ['.', 'invest'].flatMap((d) => readdirSync(join(root, d)).filter((f) => f.endsWith('.html')).map((f) => join(d, f)));

for (const page of pages) {
  test(`links resolve: ${page}`, () => {
    const html = readFileSync(join(root, page), 'utf8');
    const problems = [];
    for (const [, href] of html.matchAll(/<a\b[^>]*?\shref="([^"]*)"/g)) {
      if (/^(https?:|mailto:)/.test(href)) continue;
      if (href === '#' || href === '') { problems.push(`dead link "${href}"`); continue; }
      const [path, anchor] = href.split('#');
      const file = path ? join(root, dirname(page), path.split('?')[0]) : join(root, page);
      const target = statSync(file, { throwIfNoEntry: false })?.isDirectory() ? join(file, 'index.html') : file;
      if (!existsSync(target)) { problems.push(`missing file for "${href}"`); continue; }
      if (anchor && !readFileSync(target, 'utf8').includes(`id="${anchor}"`)) problems.push(`missing anchor for "${href}"`);
    }
    assert.deepEqual(problems, []);
  });
}

// One shared header: every page mounts it, and each link it renders points at a real page.
test('every page mounts the shared header and its links resolve', () => {
  const js = readFileSync(join(root, 'site-header.js'), 'utf8');
  const hrefs = [...js.matchAll(/href: '([^']+)',\s+key:/g)].map((m) => m[1]);
  assert.equal(hrefs.length, 5);
  for (const href of hrefs) {
    const file = join(root, href);
    assert.ok(existsSync(statSync(file, { throwIfNoEntry: false })?.isDirectory() ? join(file, 'index.html') : file), href);
  }
  for (const page of pages) {
    const html = readFileSync(join(root, page), 'utf8');
    assert.match(html, /<script src="(\.\.\/)?site-header\.js"><\/script>/, `${page} does not mount the shared header`);
    assert.doesNotMatch(html, /<header\b/, `${page} still has its own header`);
  }
});
