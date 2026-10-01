/* The one site header. Every page adds <script src="site-header.js"></script> (path relative to the page) as the
   first thing in <body>; this script renders the brand, the six main links (current page marked), the language
   switcher slot that i18n.js fills, the dark-mode toggle, and the mobile menu.
   Change the links here and every page follows. */
(function () {
  var script = document.currentScript;
  var base = script.src.slice(0, script.src.lastIndexOf('/') + 1); // the web/ root, wherever the page sits
  var NAV = [
    { id: 'home',   href: 'index.html',        key: 'navHome',        label: 'Home' },
    { id: 'invest', href: 'invest/',           key: 'inv.nav',        label: 'Invest' },
    { id: 'nh',     href: 'nh-explorer.html',  key: 'navNhMap',       label: 'NH Map' },
    { id: 'policy', href: 'policymaker.html',  key: 'navPolicymaker', label: 'Policymaker View' },
    { id: 'method', href: 'methodology.html',  key: 'navMethodology', label: 'Methodology' },
    { id: 'brics',  href: 'brics.html',        key: 'navBrics',       label: 'BRICS' }
  ];

  var rel = location.pathname.slice(new URL(base).pathname.length);
  var current = rel.indexOf('invest/') === 0 ? 'invest'
    : (NAV.filter(function (n) { return n.href === rel; })[0] || (rel === '' ? NAV[0] : {})).id;

  function head(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    document.head.appendChild(el);
  }
  head('link', { rel: 'stylesheet', href: base + 'site-header.css' });
  head('link', { rel: 'stylesheet', href: base + 'dark-mode.css' });
  if (!document.querySelector('link[href*="family=Inter"]')) {
    head('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' });
  }
  // i18n.js puts a Material Symbols glyph in the language dropdown; the investor pages do not load that font themselves.
  if (!document.querySelector('link[href*="Material+Symbols"]')) {
    head('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200' });
  }

  /* --- Dark mode: read stored preference, fall back to OS preference --- */
  var THEME_KEY = 'infra-ai-theme';
  function getPreferredTheme() {
    var stored = null;
    try { stored = localStorage.getItem(THEME_KEY); } catch (e) { /* private browsing */ }
    if (stored === 'dark' || stored === 'light') return stored;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* noop */ }
    // Update the toggle button label and icon if it exists
    var btn = document.getElementById('sh-theme-toggle');
    if (btn) {
      var isDark = theme === 'dark';
      btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      btn.querySelector('.sh__theme-sun').style.display = isDark ? 'none' : 'block';
      btn.querySelector('.sh__theme-moon').style.display = isDark ? 'block' : 'none';
    }
  }
  // Apply theme immediately (before any paint) to avoid flash
  applyTheme(getPreferredTheme());

  // Listen for OS-level theme changes (only when user hasn't explicitly chosen)
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      var stored = null;
      try { stored = localStorage.getItem(THEME_KEY); } catch (ex) { /* noop */ }
      if (!stored) applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  /* --- SVG icons for the toggle --- */
  var SUN_ICON = '<svg class="sh__theme-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="5"/>' +
    '<line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>' +
    '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>' +
    '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>' +
    '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>' +
    '</svg>';
  var MOON_ICON = '<svg class="sh__theme-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>' +
    '</svg>';

  function links() {
    return NAV.map(function (n) {
      return '<a class="sh__link" href="' + base + n.href + '" data-i18n="' + n.key + '"' +
        (n.id === current ? ' aria-current="page"' : '') + '>' + n.label + '</a>';
    }).join('');
  }

  var header = document.createElement('header');
  header.className = 'sh';
  header.innerHTML =
    '<div class="sh__inner">' +
      '<a class="sh__brand" href="' + base + 'index.html" aria-label="INFRA-AI home">' +
        '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect width="48" height="48" rx="8" fill="#0E5A66"/>' +
        '<circle cx="24" cy="24" r="16" stroke="#E08A1E" stroke-width="2" stroke-dasharray="3 2"/>' +
        '<path d="M24 10V38M10 24H38" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>' +
        '<path d="M14 14L34 34M34 14L14 34" stroke="#fff" stroke-width="1.75" stroke-linecap="round" opacity=".8"/>' +
        '<circle cx="24" cy="24" r="5" fill="#E08A1E" stroke="#fff" stroke-width="1.5"/></svg>' +
        '<span>INFRA-AI</span><span class="sh__dpg">DPG</span></a>' +
      '<nav class="sh__nav" aria-label="Main">' + links() + '</nav>' +
      '<div class="sh__actions">' +
        '<div class="lang-switcher" id="lang-switcher"></div>' +
        '<button class="sh__theme-toggle" type="button" id="sh-theme-toggle" aria-label="Switch to dark mode" data-i18n-aria-label="navThemeToggle">' +
          SUN_ICON + MOON_ICON +
        '</button>' +
        '<button class="sh__burger" type="button" aria-label="Menu" data-i18n-aria-label="navMenu" aria-expanded="false" aria-controls="sh-menu">' +
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>' +
      '</div>' +
    '</div>' +
    '<nav class="sh__menu" id="sh-menu" aria-label="Main">' + links() + '</nav>';
  script.parentNode.insertBefore(header, script);

  // Set initial icon visibility now that the DOM exists
  applyTheme(getPreferredTheme());

  // Toggle handler
  var themeBtn = document.getElementById('sh-theme-toggle');
  themeBtn.addEventListener('click', function () {
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
  });

  var burger = header.querySelector('.sh__burger');
  var menu = header.querySelector('.sh__menu');
  burger.addEventListener('click', function () {
    burger.setAttribute('aria-expanded', String(menu.classList.toggle('is-open')));
  });
})();
