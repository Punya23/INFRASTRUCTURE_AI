import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from './api.js';
import { clear, errorKey, h, onLangChange, renderError, renderSkeleton, setStatus, setStatusKey } from './ui.js';
import { tt } from './format.js';

// Node has no DOM and this project takes no test dependency, so this is a minimal stand-in: enough to
// see what h() does. Elements REFUSE direct property assignment, so h() reaching for a markup setter
// (or anything that is not a method call) fails the test; strings can only arrive through append().
function fakeElement(tag) {
  const state = { tag, attrs: {}, children: [], listeners: {}, styleProps: {} };
  const el = {
    state,
    nodeType: 1,
    dataset: {},
    style: { setProperty: (name, value) => { state.styleProps[name] = value; } },
    setAttribute: (name, value) => { state.attrs[name] = String(value); },
    removeAttribute: (name) => { delete state.attrs[name]; },
    getAttribute: (name) => state.attrs[name] ?? null,
    addEventListener: (type, fn) => { (state.listeners[type] ??= []).push(fn); },
    append: (...nodes) => { state.children.push(...nodes.map((n) => (typeof n === 'object' ? n : { text: String(n) }))); },
    replaceChildren: (...nodes) => { state.children.length = 0; el.append(...nodes); },
    click: () => { for (const fn of state.listeners.click ?? []) fn({ type: 'click' }); },
  };
  return new Proxy(el, { set(_, key) { throw new Error(`direct assignment to element.${String(key)}`); } });
}

function fakeDocument() {
  const listeners = {};
  return {
    listeners,
    createElement: fakeElement,
    addEventListener: (type, fn) => { (listeners[type] ??= []).push(fn); },
    removeEventListener: (type, fn) => { listeners[type] = (listeners[type] ?? []).filter((f) => f !== fn); },
  };
}

function withDom(t) {
  const original = globalThis.document;
  const doc = fakeDocument();
  globalThis.document = doc;
  t.after(() => { globalThis.document = original; });
  return doc;
}

const text = (el) => el.state.children.map((c) => c.text ?? text(c)).join('');

test('h: strings become text, never markup', (t) => {
  withDom(t);
  const payload = '<img src=x onerror=alert(1)>';
  const el = h('p', { class: 'note' }, payload, 42, null, undefined, false, true, ['a', ['b', null]]);
  assert.equal(el.state.tag, 'p');
  assert.equal(el.state.attrs.class, 'note');
  assert.deepEqual(el.state.children, [{ text: payload }, { text: '42' }, { text: 'a' }, { text: 'b' }]);
});

test('h: children passed where attrs belong fail loudly instead of becoming attributes', (t) => {
  withDom(t);
  assert.throws(() => h('p', 'text'), TypeError);
  assert.throws(() => h('p', h('span')), TypeError);
  assert.throws(() => h('ul', ['a', 'b']), TypeError);
  assert.doesNotThrow(() => h('p', null, 'text'));
  assert.doesNotThrow(() => h('p', undefined, 'text'));
});

test('h: zero is content, not "nothing"', (t) => {
  withDom(t);
  assert.deepEqual(h('span', null, 0).state.children, [{ text: '0' }]);
});

test('h: nested elements are appended as nodes', (t) => {
  withDom(t);
  const el = h('ul', null, h('li', null, 'one'), h('li', null, 'two'));
  assert.equal(el.state.children.length, 2);
  assert.equal(text(el), 'onetwo');
});

test('h: dataset, style custom properties, ARIA and boolean attributes', (t) => {
  withDom(t);
  const el = h('button', {
    dataset: { city: 'pune', rank: 1 },
    style: { '--value': 71 },
    'aria-pressed': false,
    'aria-expanded': true,
    role: 'button',
    disabled: true,
    hidden: false,
    title: null,
    id: undefined,
    type: 'button',
  });
  assert.deepEqual({ ...el.dataset }, { city: 'pune', rank: '1' });
  assert.deepEqual(el.state.styleProps, { '--value': '71' });
  assert.deepEqual(el.state.attrs, { 'aria-pressed': 'false', 'aria-expanded': 'true', role: 'button', disabled: '', type: 'button' });
});

test('h: on* attributes register listeners and never become inline handlers', (t) => {
  withDom(t);
  let clicks = 0;
  const el = h('button', { onclick: () => { clicks += 1; } }, 'go');
  el.click();
  assert.equal(clicks, 1);
  assert.equal(el.state.attrs.onclick, undefined);
  assert.throws(() => h('button', { onclick: 'alert(1)' }), TypeError);
  assert.throws(() => h('div', { onerror: '1' }), TypeError);
  assert.doesNotThrow(() => h('button', { onclick: false }), 'a conditional handler that is off is skipped');
  assert.equal(Object.keys(h('button', { onclick: null }).state.listeners).length, 0);
});

test('h: only http(s), mailto and relative URLs survive in href and src', (t) => {
  withDom(t);
  for (const ok of ['city.html?c=pune', '../index.html', '#how', 'https://www.openstreetmap.org/copyright', 'http://localhost:8080', 'mailto:a@b.c']) {
    assert.equal(h('a', { href: ok }).state.attrs.href, ok, ok);
  }
  for (const bad of ['javascript:alert(1)', ' JaVa\tScRiPt:alert(1)', 'java\nscript:alert(1)', 'data:text/html,<script>1</script>', 'vbscript:x', 'blob:https://x/y']) {
    assert.equal(h('a', { href: bad }).state.attrs.href, undefined, JSON.stringify(bad));
    assert.equal(h('img', { src: bad }).state.attrs.src, undefined, JSON.stringify(bad));
  }
});

test('clear empties a node and drops aria-busy', () => {
  const node = fakeElement('div');
  node.append('old');
  node.setAttribute('aria-busy', 'true');
  clear(node);
  assert.deepEqual(node.state.children, []);
  assert.equal(node.getAttribute('aria-busy'), null);
});

test('renderSkeleton fills the node with hidden placeholder rows and marks it busy', (t) => {
  withDom(t);
  const node = fakeElement('div');
  node.append('old content');
  renderSkeleton(node, 3);
  assert.equal(node.state.children.length, 3);
  for (const row of node.state.children) {
    assert.match(row.state.attrs.class, /\binv-skeleton\b/);
    assert.equal(row.state.attrs['aria-hidden'], 'true');
  }
  assert.equal(node.getAttribute('aria-busy'), 'true');

  const fallback = fakeElement('div');
  renderSkeleton(fallback);
  assert.equal(fallback.state.children.length, 3, 'three rows by default');
});

test('renderError shows the message as text, with a Retry button only when there is something to retry', (t) => {
  withDom(t);
  t.after(() => { delete globalThis.InfraI18n; });
  globalThis.InfraI18n = { t: (key) => key };
  const node = fakeElement('div');
  node.setAttribute('aria-busy', 'true');
  let retries = 0;
  renderError(node, '<b>Server</b> took too long', () => { retries += 1; });
  const [box] = node.state.children;
  assert.equal(box.state.attrs.role, 'alert');
  assert.match(box.state.attrs.class, /\binv-error\b/);
  const [message, button] = box.state.children;
  assert.deepEqual(message.state.children, [{ text: '<b>Server</b> took too long' }]);
  assert.equal(button.state.tag, 'button');
  assert.equal(button.state.attrs.type, 'button');
  assert.equal(button.dataset['i18n'], 'inv.retry');
  assert.equal(text(button), 'inv.retry');
  button.click();
  assert.equal(retries, 1);
  const seenArgs = [];
  renderError(node, 'again', (...args) => seenArgs.push(args));
  node.state.children[0].state.children[1].click();
  assert.deepEqual(seenArgs, [[]], 'the retry function is called without the click event');
  assert.equal(node.getAttribute('aria-busy'), null);

  renderError(node, 'Not found');
  assert.equal(node.state.children.length, 1, 'the previous error is replaced, not stacked');
  assert.equal(node.state.children[0].state.children.length, 1, 'no Retry without a handler');
  assert.equal(node.state.children[0].state.children[0].dataset.i18n, undefined, 'a plain string is shown as given');
});

test('renderError given the error itself lets i18n.js fill the wording in when its dictionary arrives', (t) => {
  withDom(t);
  t.after(() => { delete globalThis.InfraI18n; });
  globalThis.InfraI18n = { t: () => null }; // the dictionary has not loaded yet: tt() can only give the key
  const node = fakeElement('div');
  renderError(node, new ApiError('timeout', 'x'), () => {});
  const [message] = node.state.children[0].state.children;
  assert.equal(message.dataset.i18n, 'inv.error.timeout');
  assert.equal(text(message), 'inv.error.timeout', 'until then the key stands in, and data-i18n replaces it');

  renderError(node, new Error('secret internal detail'));
  const [generic] = node.state.children[0].state.children;
  assert.equal(generic.dataset.i18n, 'inv.error.generic');
  assert.ok(!text(generic).includes('secret'));
});

test('setStatus makes the node a polite live region and sets its text', () => {
  const node = statusNode();
  setStatus(node, 'Showing 5 cities');
  assert.equal(node.attrs['aria-live'], 'polite');
  assert.equal(node.attrs.role, 'status');
  assert.equal(node.textContent, 'Showing 5 cities');
  setStatus(node, undefined);
  assert.equal(node.textContent, '');
});

function statusNode() {
  return {
    attrs: { 'data-i18n': 'inv.loading' },
    dataset: {},
    textContent: 'old',
    setAttribute(name, value) { this.attrs[name] = value; },
    removeAttribute(name) { delete this.attrs[name]; },
  };
}

test('setStatus never announces a raw key: before the dictionary loads the status stays empty', (t) => {
  t.after(() => { delete globalThis.InfraI18n; });
  globalThis.InfraI18n = { t: () => null };
  const node = statusNode();
  setStatus(node, tt('inv.state.status', { n: 5 })); // no tokens in the key, so tt() returns the bare key
  assert.equal(node.textContent, '');
  setStatus(node, 'Cities listed: 5');
  assert.equal(node.textContent, 'Cities listed: 5');
});

test('setStatusKey lets i18n.js fill the wording in, and a later setStatus takes the key away', (t) => {
  t.after(() => { delete globalThis.InfraI18n; });
  globalThis.InfraI18n = { t: () => null };
  const node = statusNode();
  setStatusKey(node, 'inv.error.timeout');
  assert.equal(node.textContent, '', 'not the key');
  assert.equal(node.dataset.i18n, 'inv.error.timeout');
  globalThis.InfraI18n = { t: () => 'The server took too long.' };
  setStatusKey(node, 'inv.error.timeout');
  assert.equal(node.textContent, 'The server took too long.');
  setStatus(node, 'Cities listed: 5');
  assert.equal(node.attrs['data-i18n'], undefined, 'a stale key must not overwrite this text on a language change');
});

test('onLangChange calls back with the new language and can unsubscribe', (t) => {
  const doc = withDom(t);
  const seen = [];
  const off = onLangChange((lang) => seen.push(lang));
  assert.equal(doc.listeners['infra-ai-lang-change'].length, 1);
  doc.listeners['infra-ai-lang-change'][0]({ detail: { lang: 'hi', config: {} } });
  doc.listeners['infra-ai-lang-change'][0]({});
  assert.deepEqual(seen, ['hi', undefined]);
  off();
  assert.equal(doc.listeners['infra-ai-lang-change'].length, 0);
});

test('errorKey picks a specific message for the codes people can act on, a generic one otherwise', () => {
  for (const code of ['timeout', 'network', 'rate_limited', 'not_found']) {
    assert.equal(errorKey(new ApiError(code, 'x')), `inv.error.${code}`);
  }
  for (const code of ['internal', 'bad_response', 'bad_request', 'aborted', 'made_up', '__proto__', 'constructor']) {
    assert.equal(errorKey(new ApiError(code, 'x')), 'inv.error.generic', code);
  }
  assert.equal(errorKey(new Error('secret internal detail')), 'inv.error.generic');
  assert.equal(errorKey(undefined), 'inv.error.generic');
});
