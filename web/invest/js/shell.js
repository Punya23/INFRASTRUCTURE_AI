// Header and footer shared by the four investor pages. Each page has <header id="inv-header"> and
// <footer id="inv-footer"> placeholders plus a skip link; this fills them in. Text carries data-i18n so
// ../i18n.js translates it, and tt() gives the English starting text.
//
// The language switcher: ../i18n.js finds .lang-switcher and swaps these buttons for its dropdown when
// the DOM is ready. This module runs before that, so the container exists in time.

import { h } from './ui.js';
import { tt } from './format.js';

// Resolves once ../i18n.js has applied a language, so a page can render text with tt() from the first
// paint instead of showing keys. It also resolves after 1.5 s: if the dictionary never arrives the page
// still renders (with the English text tt() is given) instead of waiting forever.
export const i18nReady = new Promise((resolve) => {
  if (globalThis.InfraI18n?.t?.('inv.nav')) { resolve(); return; }
  const done = () => { document.removeEventListener('infra-ai-lang-change', done); resolve(); };
  document.addEventListener('infra-ai-lang-change', done);
  setTimeout(done, 1500);
});

const link = (href, key, current) =>
  h('a', { href, dataset: { i18n: key }, 'aria-current': current ? 'page' : null }, tt(key));

// current: 'invest' on every page of this flow (the one nav item that is "here")
export function renderShell({ current = 'invest' } = {}) {
  const header = document.getElementById('inv-header');
  const footer = document.getElementById('inv-footer');

  if (header) {
    header.classList.add('inv-header');
    header.replaceChildren(h('div', { class: 'inv-container inv-header__inner' },
      h('a', { class: 'inv-brand', href: 'index.html' },
        h('span', { dataset: { i18n: 'inv.brand' } }, tt('inv.brand')),
        h('span', { class: 'inv-brand__product', dataset: { i18n: 'inv.nav' } }, tt('inv.nav'))),
      h('nav', { class: 'inv-nav', 'aria-label': tt('inv.nav.label'), dataset: { i18nAriaLabel: 'inv.nav.label' } },
        link('../index.html', 'inv.nav.explore', false),
        link('../nh-explorer.html', 'inv.nav.nhmap', false),
        link('index.html', 'inv.nav', current === 'invest')),
      h('div', { class: 'lang-switcher', id: 'lang-switcher' },
        h('button', { class: 'lang-btn', type: 'button', dataset: { lang: 'en' } }, 'English'),
        h('button', { class: 'lang-btn', type: 'button', dataset: { lang: 'hi' } }, 'हिन्दी'),
        h('button', { class: 'lang-btn', type: 'button', dataset: { lang: 'kn' } }, 'ಕನ್ನಡ')),
      h('a', { class: 'inv-btn inv-btn--primary', href: 'start.html', dataset: { i18n: 'inv.cta.start' } }, tt('inv.cta.start'))));
  }

  if (footer) {
    footer.classList.add('inv-footer');
    footer.replaceChildren(h('div', { class: 'inv-container inv-stack inv-stack--tight' },
      h('p', { class: 'inv-disclaimer', dataset: { i18n: 'inv.disclaimer' } }, tt('inv.disclaimer')),
      h('p', { dataset: { i18n: 'inv.footer.attribution' } }, tt('inv.footer.attribution')),
      h('p', { dataset: { i18n: 'inv.footer.dpg' } }, tt('inv.footer.dpg'))));
  }
}
