/* The one site header. Every page adds <script src="site-header.js"></script> (path relative to the page) as the
   first thing in <body>; this script renders the brand, the five main links (current page marked), the language
   switcher slot that i18n.js fills, and the mobile menu. Change the links here and every page follows. */
(function () {
  var script = document.currentScript;
  var base = script.src.slice(0, script.src.lastIndexOf('/') + 1); // the web/ root, wherever the page sits
  var NAV = [
    { id: 'home',   href: 'index.html',        key: 'navHome',        label: 'Home' },
    { id: 'invest', href: 'invest/',           key: 'inv.nav',        label: 'Invest' },
    { id: 'nh',     href: 'nh-explorer.html',  key: 'navNhMap',       label: 'NH Map' },
    { id: 'policy', href: 'policymaker.html',  key: 'navPolicymaker', label: 'Policymaker View' },
    { id: 'method', href: 'methodology.html',  key: 'navMethodology', label: 'Methodology' }
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
  if (!document.querySelector('link[href*="family=Inter"]')) {
    head('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' });
  }
  // i18n.js puts a Material Symbols glyph in the language dropdown; the investor pages do not load that font themselves.
  if (!document.querySelector('link[href*="Material+Symbols"]')) {
    head('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200' });
  }

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
        '<button class="sh__burger" type="button" aria-label="Menu" data-i18n-aria-label="navMenu" aria-expanded="false" aria-controls="sh-menu">' +
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>' +
      '</div>' +
    '</div>' +
    '<nav class="sh__menu" id="sh-menu" aria-label="Main">' + links() + '</nav>';
  script.parentNode.insertBefore(header, script);

  var burger = header.querySelector('.sh__burger');
  var menu = header.querySelector('.sh__menu');
  burger.addEventListener('click', function () {
    burger.setAttribute('aria-expanded', String(menu.classList.toggle('is-open')));
  });
})();
