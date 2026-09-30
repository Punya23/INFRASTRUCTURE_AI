/**
 * =============================================================================
 * INFRA-AI Internationalization Engine (i18n.js)
 * =============================================================================
 * Central language configuration, lazy-loaded JSON translations, RTL support,
 * font management, browser language detection, localStorage persistence,
 * speech locale mapping, and fallback chain.
 *
 * Extends the existing data-i18n attribute mechanism.
 * Conforms to ADR-0008 (Swappable AI providers) and ADR-0011 (Privacy by default).
 *
 * Usage:
 *   <script src="i18n.js"></script>
 *   Elements: <span data-i18n="navExplore">Explore</span>
 *   Placeholders: <input data-i18n-placeholder="searchPlaceholder" placeholder="Search...">
 *   Titles: <button data-i18n-title="zoomInTitle" title="Zoom in">
 *   ARIA: <button data-i18n-aria-label="closeModal" aria-label="Close">
 *   Options: <option data-i18n="optRoadSafety" value="road-safety">Road Safety</option>
 * =============================================================================
 */
(function (root) {
  'use strict';

  // =========================================================================
  // LANGUAGE REGISTRY — add a new language by adding one entry here + its JSON
  // =========================================================================
  var LANGUAGES = [
    { code: 'en', displayName: 'English',    nativeName: 'English',    region: 'India',         direction: 'ltr', enabled: true,  fallback: null, fontFamily: "'Inter', system-ui, sans-serif",                                        speechLocale: 'en-IN'  },
    { code: 'hi', displayName: 'Hindi',      nativeName: 'हिन्दी',      region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Devanagari', 'Inter', system-ui, sans-serif",                  speechLocale: 'hi-IN'  },
    { code: 'mr', displayName: 'Marathi',    nativeName: 'मराठी',       region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Devanagari', 'Inter', system-ui, sans-serif",                  speechLocale: 'mr-IN'  },
    { code: 'kn', displayName: 'Kannada',    nativeName: 'ಕನ್ನಡ',       region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Kannada', 'Inter', system-ui, sans-serif",                    speechLocale: 'kn-IN'  },
    { code: 'bn', displayName: 'Bengali',    nativeName: 'বাংলা',       region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Bengali', 'Inter', system-ui, sans-serif",                    speechLocale: 'bn-IN'  },
    { code: 'gu', displayName: 'Gujarati',   nativeName: 'ગુજરાતી',     region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Gujarati', 'Inter', system-ui, sans-serif",                   speechLocale: 'gu-IN'  },
    { code: 'ta', displayName: 'Tamil',      nativeName: 'தமிழ்',       region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Tamil', 'Inter', system-ui, sans-serif",                      speechLocale: 'ta-IN'  },
    { code: 'te', displayName: 'Telugu',     nativeName: 'తెలుగు',      region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Telugu', 'Inter', system-ui, sans-serif",                     speechLocale: 'te-IN'  },
    { code: 'ml', displayName: 'Malayalam',  nativeName: 'മലയാളം',      region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Malayalam', 'Inter', system-ui, sans-serif",                  speechLocale: 'ml-IN'  },
    { code: 'pa', displayName: 'Punjabi',    nativeName: 'ਪੰਜਾਬੀ',      region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Gurmukhi', 'Inter', system-ui, sans-serif",                  speechLocale: 'pa-IN'  },
    { code: 'or', displayName: 'Odia',       nativeName: 'ଓଡ଼ିଆ',       region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Oriya', 'Inter', system-ui, sans-serif",                     speechLocale: 'or-IN'  },
    { code: 'as', displayName: 'Assamese',   nativeName: 'অসমীয়া',     region: 'India',         direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Bengali', 'Inter', system-ui, sans-serif",                    speechLocale: 'as-IN'  },
    { code: 'ur', displayName: 'Urdu',       nativeName: 'اردو',        region: 'India',         direction: 'rtl', enabled: true,  fallback: 'en', fontFamily: "'Noto Nastaliq Urdu', 'Noto Sans Arabic', 'Inter', system-ui, sans-serif", speechLocale: 'ur-IN' },
    { code: 'pt', displayName: 'Portuguese', nativeName: 'Português',   region: 'International', direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Inter', system-ui, sans-serif",                                        speechLocale: 'pt-BR'  },
    { code: 'ru', displayName: 'Russian',    nativeName: 'Русский',     region: 'International', direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Inter', system-ui, sans-serif",                                        speechLocale: 'ru-RU'  },
    { code: 'zh', displayName: 'Chinese',    nativeName: '中文',         region: 'International', direction: 'ltr', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans SC', 'Inter', system-ui, sans-serif",                        speechLocale: 'zh-CN'  },
    { code: 'ar', displayName: 'Arabic',     nativeName: 'العربية',      region: 'International', direction: 'rtl', enabled: true,  fallback: 'en', fontFamily: "'Noto Sans Arabic', 'Inter', system-ui, sans-serif",                    speechLocale: 'ar-SA'  },
    { code: 'id', displayName: 'Indonesian', nativeName: 'Bahasa Indonesia', region: 'International', direction: 'ltr', enabled: true, fallback: 'en', fontFamily: "'Inter', system-ui, sans-serif",                                    speechLocale: 'id-ID'  }
  ];

  // =========================================================================
  // FONT URLS — loaded on demand per script family
  // =========================================================================
  var FONT_URLS = {
    'Noto Sans Devanagari': 'https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap',
    'Noto Sans Kannada':    'https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@400;500;600;700&display=swap',
    'Noto Sans Bengali':    'https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap',
    'Noto Sans Gujarati':   'https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@400;500;600;700&display=swap',
    'Noto Sans Tamil':      'https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;500;600;700&display=swap',
    'Noto Sans Telugu':     'https://fonts.googleapis.com/css2?family=Noto+Sans+Telugu:wght@400;500;600;700&display=swap',
    'Noto Sans Malayalam':  'https://fonts.googleapis.com/css2?family=Noto+Sans+Malayalam:wght@400;500;600;700&display=swap',
    'Noto Sans Gurmukhi':   'https://fonts.googleapis.com/css2?family=Noto+Sans+Gurmukhi:wght@400;500;600;700&display=swap',
    'Noto Sans Oriya':      'https://fonts.googleapis.com/css2?family=Noto+Sans+Oriya:wght@400;500;600;700&display=swap',
    'Noto Sans Arabic':     'https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;600;700&display=swap',
    'Noto Nastaliq Urdu':   'https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;500;600;700&display=swap',
    'Noto Sans SC':         'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap'
  };

  // Track which fonts have been loaded
  var loadedFonts = {};

  // =========================================================================
  // STATE
  // =========================================================================
  var currentLang = 'en';
  var translationCache = {};  // { locale: { key: value } }
  var STORAGE_KEY = 'infra-ai-lang';

  // =========================================================================
  // HELPERS
  // =========================================================================
  function getLanguageConfig(code) {
    for (var i = 0; i < LANGUAGES.length; i++) {
      if (LANGUAGES[i].code === code) return LANGUAGES[i];
    }
    return null;
  }

  function getEnabledLanguages() {
    return LANGUAGES.filter(function (l) { return l.enabled; });
  }

  function getIndianLanguages() {
    return getEnabledLanguages().filter(function (l) { return l.region === 'India'; });
  }

  function getInternationalLanguages() {
    return getEnabledLanguages().filter(function (l) { return l.region === 'International'; });
  }

  // =========================================================================
  // FONT LOADING — load script-specific fonts on demand
  // =========================================================================
  function loadFontForLanguage(langConfig) {
    if (!langConfig) return;
    var families = langConfig.fontFamily.split(',');
    families.forEach(function (raw) {
      var family = raw.trim().replace(/^'|'$/g, '');
      if (family === 'Inter' || family === 'system-ui' || family === 'sans-serif') return;
      if (loadedFonts[family]) return;
      var url = FONT_URLS[family];
      if (!url) return;
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      link.setAttribute('data-i18n-font', family);
      document.head.appendChild(link);
      loadedFonts[family] = true;
    });
  }

  // =========================================================================
  // TRANSLATION LOADING — lazy fetch from locales/<code>.json
  // =========================================================================
  function getLocalesBasePath() {
    // Derive path relative to the current page
    var scripts = document.getElementsByTagName('script');
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].src || '';
      if (src.indexOf('i18n.js') !== -1) {
        return src.replace(/i18n\.js.*$/, 'locales/');
      }
    }
    return 'locales/';
  }

  var localesBasePath = null;

  function loadTranslation(code, callback) {
    if (translationCache[code]) {
      callback(translationCache[code]);
      return;
    }
    if (!localesBasePath) localesBasePath = getLocalesBasePath();
    var url = localesBasePath + code + '.json';
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try {
            translationCache[code] = JSON.parse(xhr.responseText);
          } catch (e) {
            console.warn('[i18n] Failed to parse ' + url, e);
            translationCache[code] = {};
          }
        } else {
          console.warn('[i18n] Failed to load ' + url + ' (status ' + xhr.status + ')');
          translationCache[code] = {};
        }
        callback(translationCache[code]);
      }
    };
    xhr.send();
  }

  // =========================================================================
  // TRANSLATION LOOKUP — with fallback chain
  // =========================================================================
  function t(key) {
    var dict = translationCache[currentLang];
    if (dict && dict[key] !== undefined && dict[key] !== '') return dict[key];

    // Fallback chain
    var config = getLanguageConfig(currentLang);
    if (config && config.fallback) {
      var fbDict = translationCache[config.fallback];
      if (fbDict && fbDict[key] !== undefined && fbDict[key] !== '') return fbDict[key];
    }

    // Final fallback to English
    var enDict = translationCache['en'];
    if (enDict && enDict[key] !== undefined && enDict[key] !== '') return enDict[key];

    // Return null — caller should keep original text
    return null;
  }

  // =========================================================================
  // APPLY TRANSLATIONS — update all data-i18n* elements in the DOM
  // =========================================================================
  function applyTranslations() {
    // data-i18n — textContent
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      var val = t(key);
      if (val !== null) els[i].textContent = val;
    }
    // data-i18n-placeholder
    var phs = document.querySelectorAll('[data-i18n-placeholder]');
    for (var j = 0; j < phs.length; j++) {
      var pKey = phs[j].getAttribute('data-i18n-placeholder');
      var pVal = t(pKey);
      if (pVal !== null) phs[j].setAttribute('placeholder', pVal);
    }
    // data-i18n-title
    var tls = document.querySelectorAll('[data-i18n-title]');
    for (var k = 0; k < tls.length; k++) {
      var tKey = tls[k].getAttribute('data-i18n-title');
      var tVal = t(tKey);
      if (tVal !== null) tls[k].setAttribute('title', tVal);
    }
    // data-i18n-aria-label
    var als = document.querySelectorAll('[data-i18n-aria-label]');
    for (var m = 0; m < als.length; m++) {
      var aKey = als[m].getAttribute('data-i18n-aria-label');
      var aVal = t(aKey);
      if (aVal !== null) als[m].setAttribute('aria-label', aVal);
    }
    // data-i18n-html — innerHTML (for strings with inline tags)
    var hEls = document.querySelectorAll('[data-i18n-html]');
    for (var h = 0; h < hEls.length; h++) {
      var hKey = hEls[h].getAttribute('data-i18n-html');
      var hVal = t(hKey);
      if (hVal !== null) hEls[h].innerHTML = hVal;
    }
  }

  // =========================================================================
  // RTL SUPPORT
  // =========================================================================
  function applyDirection(langConfig) {
    var dir = (langConfig && langConfig.direction === 'rtl') ? 'rtl' : 'ltr';
    document.documentElement.setAttribute('dir', dir);
    document.documentElement.setAttribute('lang', langConfig ? langConfig.code : 'en');

    // Toggle body class for CSS hooks
    if (dir === 'rtl') {
      document.body.classList.add('rtl');
      document.body.classList.remove('ltr');
    } else {
      document.body.classList.add('ltr');
      document.body.classList.remove('rtl');
    }
  }

  // =========================================================================
  // FONT APPLICATION
  // =========================================================================
  function applyFont(langConfig) {
    if (langConfig && langConfig.fontFamily) {
      document.body.style.fontFamily = langConfig.fontFamily;
    }
  }

  // =========================================================================
  // LANGUAGE SWITCHER DROPDOWN — update active state
  // =========================================================================
  function updateSwitcherUI() {
    var config = getLanguageConfig(currentLang);
    // Update collapsed button text
    var toggles = document.querySelectorAll('.i18n-dropdown-toggle');
    for (var i = 0; i < toggles.length; i++) {
      var label = toggles[i].querySelector('.i18n-lang-label');
      if (label && config) label.textContent = config.nativeName;
    }
    // Mark active item
    var items = document.querySelectorAll('.i18n-lang-option');
    for (var j = 0; j < items.length; j++) {
      var isActive = items[j].getAttribute('data-lang') === currentLang;
      items[j].classList.toggle('active', isActive);
      var check = items[j].querySelector('.i18n-check');
      if (check) check.style.visibility = isActive ? 'visible' : 'hidden';
    }

    // Also update old-style lang-btn for backwards compat
    var oldBtns = document.querySelectorAll('.lang-btn[data-lang]');
    for (var k = 0; k < oldBtns.length; k++) {
      oldBtns[k].classList.toggle('active', oldBtns[k].getAttribute('data-lang') === currentLang);
    }
  }

  // =========================================================================
  // PERSISTENCE
  // =========================================================================
  function saveLanguage(code) {
    try { localStorage.setItem(STORAGE_KEY, code); } catch (e) { /* silent */ }
  }

  function getSavedLanguage() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  // =========================================================================
  // BROWSER LANGUAGE DETECTION
  // =========================================================================
  function detectBrowserLanguage() {
    var langs = navigator.languages || [navigator.language || navigator.userLanguage || ''];
    for (var i = 0; i < langs.length; i++) {
      var tag = langs[i].toLowerCase();
      // Try exact match first
      var exact = getLanguageConfig(tag);
      if (exact && exact.enabled) return exact.code;
      // Try base language (e.g. "mr-in" → "mr")
      var base = tag.split('-')[0];
      var baseConfig = getLanguageConfig(base);
      if (baseConfig && baseConfig.enabled) return baseConfig.code;
    }
    return 'en';
  }

  // =========================================================================
  // SET LANGUAGE — main public API
  // =========================================================================
  function setLanguage(code, skipPersist) {
    var config = getLanguageConfig(code);
    if (!config || !config.enabled) {
      config = getLanguageConfig('en');
      code = 'en';
    }
    currentLang = code;

    // Load font
    loadFontForLanguage(config);

    // Load English as baseline (always available for fallback)
    loadTranslation('en', function () {
      loadTranslation(code, function () {
        applyTranslations();
        applyDirection(config);
        applyFont(config);
        updateSwitcherUI();

        // Persist
        if (!skipPersist) saveLanguage(code);

        // Fire custom event for other scripts to react
        var evt;
        try {
          evt = new CustomEvent('infra-ai-lang-change', { detail: { lang: code, config: config } });
        } catch (e) {
          evt = document.createEvent('CustomEvent');
          evt.initCustomEvent('infra-ai-lang-change', true, true, { lang: code, config: config });
        }
        document.dispatchEvent(evt);
      });
    });
  }

  // =========================================================================
  // SPEECH LOCALE — for Web Speech API
  // =========================================================================
  function getSpeechLocale() {
    var config = getLanguageConfig(currentLang);
    return config ? config.speechLocale : 'en-IN';
  }

  function isSpeechSupported(langCode) {
    // Speech codes known to be supported by Web Speech API
    var supported = ['en', 'hi', 'mr', 'kn', 'ta', 'te', 'bn', 'gu', 'ml'];
    return supported.indexOf(langCode || currentLang) !== -1;
  }

  // =========================================================================
  // DROPDOWN INJECTOR — builds the language switcher dropdown into existing header
  // =========================================================================
  function injectLanguageSwitcher() {
    // Find the existing lang-switcher or lang-switch container
    var container = document.querySelector('.lang-switcher') || document.querySelector('.lang-switch');
    if (!container) return;

    var config = getLanguageConfig(currentLang);
    var indian = getIndianLanguages();
    var international = getInternationalLanguages();

    // Build dropdown HTML
    var html = '';
    html += '<div class="i18n-dropdown" id="i18n-dropdown">';
    html += '  <button class="i18n-dropdown-toggle" id="i18n-dropdown-toggle" type="button" aria-label="Select language" aria-expanded="false" aria-haspopup="listbox">';
    html += '    <span class="material-symbols-outlined" style="font-size:18px;">language</span>';
    html += '    <span class="i18n-lang-label">' + (config ? config.nativeName : 'English') + '</span>';
    html += '    <span class="material-symbols-outlined i18n-chevron" style="font-size:16px;">expand_more</span>';
    html += '  </button>';
    html += '  <div class="i18n-dropdown-menu" id="i18n-dropdown-menu" role="listbox" aria-label="Languages">';
    html += '    <div class="i18n-dropdown-header">Select language</div>';
    html += '    <div class="i18n-group-label">INDIAN LANGUAGES</div>';
    for (var i = 0; i < indian.length; i++) {
      var il = indian[i];
      var activeI = il.code === currentLang;
      html += '    <button class="i18n-lang-option' + (activeI ? ' active' : '') + '" data-lang="' + il.code + '" role="option" aria-selected="' + activeI + '" type="button">';
      html += '      <span class="i18n-check material-symbols-outlined" style="font-size:16px;visibility:' + (activeI ? 'visible' : 'hidden') + ';">check</span>';
      html += '      <span class="i18n-native">' + il.nativeName + '</span>';
      html += '      <span class="i18n-display">' + il.displayName + '</span>';
      html += '    </button>';
    }
    html += '    <div class="i18n-group-divider"></div>';
    html += '    <div class="i18n-group-label">BRICS / INTERNATIONAL</div>';
    for (var j = 0; j < international.length; j++) {
      var intl = international[j];
      var activeJ = intl.code === currentLang;
      html += '    <button class="i18n-lang-option' + (activeJ ? ' active' : '') + '" data-lang="' + intl.code + '" role="option" aria-selected="' + activeJ + '" type="button">';
      html += '      <span class="i18n-check material-symbols-outlined" style="font-size:16px;visibility:' + (activeJ ? 'visible' : 'hidden') + ';">check</span>';
      html += '      <span class="i18n-native">' + intl.nativeName + '</span>';
      html += '      <span class="i18n-display">' + intl.displayName + '</span>';
      html += '    </button>';
    }
    html += '  </div>';
    html += '</div>';

    // Replace content
    container.innerHTML = html;
    container.style.display = 'flex';
    container.style.background = 'none';
    container.style.border = 'none';
    container.style.padding = '0';

    // Bind events
    var toggle = document.getElementById('i18n-dropdown-toggle');
    var menu = document.getElementById('i18n-dropdown-menu');
    if (toggle && menu) {
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = menu.classList.contains('open');
        menu.classList.toggle('open');
        toggle.setAttribute('aria-expanded', !isOpen);
      });

      menu.addEventListener('click', function (e) {
        var option = e.target.closest('.i18n-lang-option');
        if (option) {
          var lang = option.getAttribute('data-lang');
          setLanguage(lang);
          menu.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
        }
      });

      // Close on outside click
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.i18n-dropdown')) {
          menu.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
        }
      });

      // Keyboard navigation
      toggle.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggle.click();
        }
        if (e.key === 'Escape') {
          menu.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
        }
      });

      menu.addEventListener('keydown', function (e) {
        var options = menu.querySelectorAll('.i18n-lang-option');
        var idx = Array.prototype.indexOf.call(options, document.activeElement);
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          var next = idx < options.length - 1 ? idx + 1 : 0;
          options[next].focus();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          var prev = idx > 0 ? idx - 1 : options.length - 1;
          options[prev].focus();
        } else if (e.key === 'Escape') {
          menu.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.focus();
        }
      });
    }
  }

  // =========================================================================
  // INJECT CSS — dropdown and RTL styles
  // =========================================================================
  function injectStyles() {
    var css = '';

    // Dropdown styles
    css += '.i18n-dropdown { position: relative; display: inline-flex; }';
    css += '.i18n-dropdown-toggle {';
    css += '  display: inline-flex; align-items: center; gap: 0.375rem;';
    css += '  padding: 0.3125rem 0.625rem; border-radius: 0.5rem;';
    css += '  background: var(--surface-container-high, #dde9f9);';
    css += '  border: 1px solid var(--outline-variant, #bfc8ca);';
    css += '  color: var(--on-surface, #111d28);';
    css += '  font-family: inherit; font-size: 0.8125rem; font-weight: 500;';
    css += '  cursor: pointer; transition: all 0.2s; white-space: nowrap;';
    css += '  min-height: 2.25rem;';
    css += '}';
    css += '.i18n-dropdown-toggle:hover { background: var(--surface-container, #e3efff); }';
    css += '.i18n-dropdown-toggle:focus-visible { outline: 2px solid var(--primary, #00414b); outline-offset: 2px; }';
    css += '.i18n-chevron { transition: transform 0.2s; }';
    css += '.i18n-dropdown-menu.open ~ .i18n-dropdown-toggle .i18n-chevron,';
    css += '.i18n-dropdown-toggle[aria-expanded="true"] .i18n-chevron { transform: rotate(180deg); }';

    css += '.i18n-dropdown-menu {';
    css += '  display: none; position: absolute; top: calc(100% + 0.375rem);';
    css += '  right: 0; z-index: 100;';
    css += '  min-width: 14rem; max-height: 24rem; overflow-y: auto;';
    css += '  background: var(--surface-container-lowest, #ffffff);';
    css += '  border: 1px solid var(--outline-variant, #bfc8ca);';
    css += '  border-radius: 0.75rem; box-shadow: 0px 8px 24px rgba(20,32,43,0.14);';
    css += '  padding: 0.375rem 0;';
    css += '}';
    css += '.i18n-dropdown-menu.open { display: block; }';

    css += '.i18n-dropdown-header {';
    css += '  padding: 0.625rem 0.875rem 0.375rem;';
    css += '  font-size: 0.8125rem; font-weight: 600;';
    css += '  color: var(--on-surface, #111d28);';
    css += '}';

    css += '.i18n-group-label {';
    css += '  padding: 0.5rem 0.875rem 0.25rem;';
    css += '  font-size: 0.6875rem; font-weight: 600;';
    css += '  letter-spacing: 0.05em; text-transform: uppercase;';
    css += '  color: var(--outline, #70797b);';
    css += '}';

    css += '.i18n-group-divider {';
    css += '  margin: 0.25rem 0.625rem;';
    css += '  border-top: 1px solid var(--outline-variant, #bfc8ca);';
    css += '}';

    css += '.i18n-lang-option {';
    css += '  display: flex; align-items: center; gap: 0.5rem;';
    css += '  width: 100%; padding: 0.4375rem 0.875rem;';
    css += '  font-family: inherit; font-size: 0.875rem;';
    css += '  color: var(--on-surface, #111d28); background: transparent;';
    css += '  border: none; cursor: pointer; transition: background 0.15s;';
    css += '  text-align: left; min-height: 2.25rem;';
    css += '}';
    css += '.i18n-lang-option:hover { background: var(--surface-container-low, #edf4ff); }';
    css += '.i18n-lang-option:focus-visible { outline: 2px solid var(--primary, #00414b); outline-offset: -2px; border-radius: 0.25rem; }';
    css += '.i18n-lang-option.active { color: var(--primary, #00414b); font-weight: 600; }';

    css += '.i18n-check { color: var(--primary, #00414b); flex-shrink: 0; }';
    css += '.i18n-native { flex: 1; }';
    css += '.i18n-display { font-size: 0.75rem; color: var(--outline, #70797b); flex-shrink: 0; }';

    // RTL overrides
    css += 'html[dir="rtl"] .i18n-dropdown-menu { left: 0; right: auto; }';
    css += 'html[dir="rtl"] .i18n-lang-option { text-align: right; }';

    // Scrollbar for dropdown
    css += '.i18n-dropdown-menu::-webkit-scrollbar { width: 4px; }';
    css += '.i18n-dropdown-menu::-webkit-scrollbar-thumb { background: var(--outline-variant, #bfc8ca); border-radius: 4px; }';
    css += '.i18n-dropdown-menu { scrollbar-width: thin; scrollbar-color: var(--outline-variant, #bfc8ca) transparent; }';

    // ===== RTL LAYOUT OVERRIDES =====
    css += 'html[dir="rtl"] body { text-align: right; }';
    css += 'html[dir="rtl"] .header-inner,';
    css += 'html[dir="rtl"] .header-actions,';
    css += 'html[dir="rtl"] .brand-group,';
    css += 'html[dir="rtl"] .brand-link,';
    css += 'html[dir="rtl"] .main-nav,';
    css += 'html[dir="rtl"] .nav-pills { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .notice-inner { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .notice-left,';
    css += 'html[dir="rtl"] .notice-right { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-input-group { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-actions { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-input { text-align: right; }';
    css += 'html[dir="rtl"] .chapter-header { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .chapter-footer { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .city-name-row { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .voice-info { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .voice-actions { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .footer-grid { direction: rtl; }';
    css += 'html[dir="rtl"] .trust-grid { direction: rtl; }';
    css += 'html[dir="rtl"] .trust-title { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .metrics-grid { direction: rtl; }';
    css += 'html[dir="rtl"] .hot-issue { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .precision-badge { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .eyebrow-pill { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .voice-entry-header { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .modal-header { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .form-group { text-align: right; }';
    css += 'html[dir="rtl"] .form-input,';
    css += 'html[dir="rtl"] .form-select,';
    css += 'html[dir="rtl"] .form-textarea { text-align: right; }';
    css += 'html[dir="rtl"] .btn-primary,';
    css += 'html[dir="rtl"] .btn-accent,';
    css += 'html[dir="rtl"] .btn-secondary,';
    css += 'html[dir="rtl"] .btn-full { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .gazette-badge { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .ground-truth-badge { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .footer-brand-name { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .footer-dpg { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .voice-verified { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .success-icon { text-align: center; }';
    css += 'html[dir="rtl"] .tab-bar { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .mobile-nav { text-align: right; }';

    // Explore page RTL
    css += 'html[dir="rtl"] .filter-bar { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-bar { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .near-me-btn { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-item { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .search-item-left { flex-direction: row-reverse; }';
    css += 'html[dir="rtl"] .project-card-header { flex-direction: row-reverse; }';

    // Mobile responsive dropdown
    css += '@media (max-width: 767px) {';
    css += '  .i18n-dropdown-toggle .i18n-lang-label { max-width: 4.5rem; overflow: hidden; text-overflow: ellipsis; }';
    css += '}';

    var style = document.createElement('style');
    style.setAttribute('data-i18n-styles', 'true');
    style.textContent = css;
    document.head.appendChild(style);
  }

  // =========================================================================
  // VOICE UNSUPPORTED MESSAGE
  // =========================================================================
  function getVoiceUnsupportedMessage() {
    var key = 'voiceUnsupported';
    var msg = t(key);
    return msg || "Voice input isn't available in this language yet. You can type instead.";
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  function init() {
    // Inject styles first
    injectStyles();

    // Determine initial language
    var saved = getSavedLanguage();
    var initial = 'en';
    if (saved && getLanguageConfig(saved) && getLanguageConfig(saved).enabled) {
      initial = saved;
    } else if (!saved) {
      initial = detectBrowserLanguage();
    }

    // Pre-load English (always needed for fallback), then set language
    loadTranslation('en', function () {
      // Build the dropdown
      injectLanguageSwitcher();
      // Set language
      setLanguage(initial, !!saved); // Don't re-persist if was already saved
    });
  }

  // =========================================================================
  // PUBLIC API
  // =========================================================================
  root.InfraI18n = {
    LANGUAGES:              LANGUAGES,
    setLanguage:            setLanguage,
    getCurrentLang:         function () { return currentLang; },
    t:                      t,
    getLanguageConfig:      getLanguageConfig,
    getEnabledLanguages:    getEnabledLanguages,
    getIndianLanguages:     getIndianLanguages,
    getInternationalLanguages: getInternationalLanguages,
    getSpeechLocale:        getSpeechLocale,
    isSpeechSupported:      isSpeechSupported,
    getVoiceUnsupportedMessage: getVoiceUnsupportedMessage,
    applyTranslations:      applyTranslations,
    loadTranslation:        loadTranslation
  };

  // Also expose setLanguage globally for backward compat with existing code
  root.setLanguage = setLanguage;

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(typeof self !== 'undefined' ? self : this);
