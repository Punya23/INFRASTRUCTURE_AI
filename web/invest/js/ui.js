// DOM helpers shared by the investor pages. Text is only ever set as text: strings reach the page as
// text nodes, and attributes are set one by one, so nothing from the API is parsed as markup.

import { tt } from './format.js';

// Only these URL schemes may appear in href, src, action and formaction. Control characters and
// whitespace are stripped first because browsers ignore them inside a scheme ("java\tscript:").
const URL_ATTRS = new Set(['href', 'src', 'action', 'formaction']);
const hasSafeScheme = (value) => {
  const bare = String(value).replace(/[\x00-\x1f\s]/g, '');
  return !/^[a-z][a-z0-9+.-]*:/i.test(bare) || /^(https?|mailto):/i.test(bare);
};

// h('a', { class: 'inv-btn', href: 'start.html', dataset: { id: 1 } }, 'Start')
//   class, id and other names: set as attributes; false, null and undefined are skipped, true sets an empty value
//   aria-*: always written as text, so aria-pressed="false" is kept ("false" is a value, not an absence)
//   dataset: { name: value }    style: { '--value': 71 } (custom properties and kebab-case names)
//   on*: a function, added as an event listener. A string would become an inline handler, so it throws
//   href, src, action, formaction: dropped unless relative or http, https or mailto
//   children: strings and numbers become text; arrays are flattened; null, undefined and booleans are skipped
export function h(tag, attrs, ...children) {
  if (attrs != null && (typeof attrs !== 'object' || Array.isArray(attrs) || attrs.nodeType)) {
    throw new TypeError('h: the second argument is attrs (an object or null); children come after it');
  }
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs ?? {})) {
    const aria = name.startsWith('aria-');
    if (value == null || (value === false && !aria)) continue;
    if (name === 'dataset') {
      for (const [key, v] of Object.entries(value)) if (v != null) el.dataset[key] = String(v);
    } else if (name === 'style') {
      for (const [key, v] of Object.entries(value)) if (v != null) el.style.setProperty(key, String(v));
    } else if (/^on/i.test(name)) {
      if (typeof value !== 'function') throw new TypeError(`h: ${name} must be a function, not markup`);
      el.addEventListener(name.slice(2).toLowerCase(), value);
    } else if (value === true && !aria) {
      el.setAttribute(name, '');
    } else if (!URL_ATTRS.has(name) || hasSafeScheme(value)) {
      el.setAttribute(name, String(value));
    }
  }
  el.append(...children.flat(Infinity).filter((c) => c != null && typeof c !== 'boolean'));
  return el;
}

// Empties a node. Also ends the busy state that renderSkeleton set.
export function clear(node) {
  node.removeAttribute('aria-busy');
  node.replaceChildren();
}

// Placeholder rows shaped by .inv-skeleton in invest.css, so the page does not jump when data arrives.
// Hidden from assistive technology; announce loading with setStatus.
export function renderSkeleton(node, rows = 3) {
  clear(node);
  node.setAttribute('aria-busy', 'true');
  node.append(...Array.from({ length: rows }, () => h('div', { class: 'inv-skeleton', 'aria-hidden': true })));
}

// What to tell the visitor about a failed request. Only the codes a person can act on get their own
// wording; everything else, including unexpected errors, reads the same and leaks no detail.
const SPECIFIC_ERRORS = new Set(['timeout', 'network', 'rate_limited', 'not_found']);
const errorKey = (error) => `inv.error.${SPECIFIC_ERRORS.has(error?.code) ? error.code : 'generic'}`;
export const errorText = (error) => tt(errorKey(error));

// Replaces the children of `node` with an error message and, when there is something to retry, a
// Retry button. To keep the last good view on screen, pass a separate slot next to it, not the
// container that holds that view.
// `message` is a string, or the error itself (an ApiError or anything else that was thrown). Passing
// the error is the better call: the message then carries data-i18n, so i18n.js fills in the wording
// when its dictionary arrives. A request that fails fast, with the API down, can finish before that
// dictionary has loaded, and a string built by tt() at that moment would be the raw key.
export function renderError(node, message, onRetry) {
  clear(node);
  const key = typeof message === 'string' ? null : errorKey(message);
  node.append(h('div', { class: 'inv-error', role: 'alert' },
    h('p', { class: 'inv-error__message', dataset: { i18n: key } }, key ? tt(key) : message),
    typeof onRetry === 'function'
      // called without the click event, so a retry function never receives it as an argument
      ? h('button', { class: 'inv-btn inv-btn--secondary', type: 'button', dataset: { i18n: 'inv.retry' }, onclick: () => onRetry() }, tt('inv.retry'))
      : null));
}

// Calls cb(lang) each time i18n.js has applied a language (it also fires once after the first load,
// so text built with tt() is rendered again once the dictionary is there). Gives back an unsubscribe function.
export function onLangChange(cb) {
  const listener = (event) => cb(event.detail?.lang);
  document.addEventListener('infra-ai-lang-change', listener);
  return () => document.removeEventListener('infra-ai-lang-change', listener);
}

// A polite live region for screen readers: "Loading…", "Showing 5 cities". Put the node in the HTML
// (visually hidden is fine) so it exists before its text changes.
export function setStatus(node, text) {
  node.setAttribute('role', 'status');
  node.setAttribute('aria-live', 'polite');
  node.textContent = text ?? '';
}
