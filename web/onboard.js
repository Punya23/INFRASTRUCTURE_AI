/* The onboarding popup. The three-question wizard (invest/start.html) opens in a native <dialog> over the
   current page, so a first-time visitor answers before anything else. Mount with
   <script src="onboard.js" data-auto></script> (path relative to the page): data-auto opens it on load when
   this browser has no saved answers. window.InfraOnboard.open() reopens it ("Change my answers").
   The wizard saves answers to localStorage itself and only posts { type: 'infra:onboarded' }; this script
   then closes the dialog and fires a window "infra:onboarded" event. Nothing else crosses the frame. */
(function () {
  var script = document.currentScript;
  var auto = script.hasAttribute('data-auto');
  var base = script.src.slice(0, script.src.lastIndexOf('/') + 1); // the web/ root, wherever the page sits
  var PREFS_KEY = 'invest.prefs';   // same key as invest/js/prefs.js
  var DISMISSED_KEY = 'onboard.dismissed'; // per tab: closing the popup is not asked again until the next visit
  var dialog;

  function safe(fn, fallback) {
    try { return fn(); } catch (e) { return fallback; } // blocked storage must never break the page
  }

  // "Onboarded" means a valid target was saved; prefs.js checks the same thing on the way in.
  function hasAnswers() {
    return safe(function () {
      var t = (JSON.parse(localStorage.getItem(PREFS_KEY)) || {}).target;
      return !!t && ((t.type === 'state' && /^[A-Z]{2}$/.test(t.code)) || (t.type === 'city' && /^[a-z0-9-]{2,64}$/.test(t.id)));
    }, false);
  }

  function t(key, fallback) {
    var i18n = window.InfraI18n;
    return (i18n && i18n.t && i18n.t(key)) || fallback;
  }

  function build() {
    var style = document.createElement('style');
    style.textContent =
      '.onb{border:0;padding:0;background:#fff;border-radius:16px;inline-size:min(44rem,calc(100vw - 1.5rem));block-size:min(46rem,calc(100dvh - 1.5rem));box-shadow:0 24px 64px rgba(0,0,0,.3);overflow:hidden}' +
      '.onb::backdrop{background:rgba(9,30,36,.6);backdrop-filter:blur(2px)}' +
      '.onb__frame{display:block;inline-size:100%;block-size:100%;border:0}' +
      '.onb__close{position:absolute;inset-block-start:.6rem;inset-inline-end:.6rem;z-index:1;inline-size:2.25rem;block-size:2.25rem;border:0;border-radius:50%;background:#eef2f3;color:#0f2a30;font:600 1.25rem/1 system-ui,sans-serif;cursor:pointer}' +
      '.onb__close:hover{background:#dfe6e8}.onb__close:focus-visible{outline:3px solid #e08a1a;outline-offset:2px}';
    document.head.appendChild(style);

    dialog = document.createElement('dialog');
    dialog.className = 'onb';
    dialog.setAttribute('aria-label', t('onboard.title', 'Set up your search'));
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'onb__close';
    close.textContent = '×';
    close.setAttribute('aria-label', t('onboard.close', 'Close'));
    close.addEventListener('click', function () { dialog.close(); });
    var frame = document.createElement('iframe');
    frame.className = 'onb__frame';
    frame.title = dialog.getAttribute('aria-label');
    dialog.append(close, frame);
    document.body.appendChild(dialog);

    dialog.addEventListener('close', function () {
      safe(function () { sessionStorage.setItem(DISMISSED_KEY, '1'); });
      frame.removeAttribute('src'); // drop the wizard so a reopen starts fresh and reads the newest answers
    });
    window.addEventListener('message', function (event) {
      // same origin and from our own frame only; the message carries no data, the answers are in storage
      if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
      if (!event.data || event.data.type !== 'infra:onboarded') return;
      dialog.close();
      window.dispatchEvent(new CustomEvent('infra:onboarded'));
    });
  }

  function open() {
    if (!dialog) build();
    if (dialog.open) return;
    dialog.querySelector('iframe').src = base + 'invest/start.html?embed=1';
    dialog.showModal();
  }

  window.InfraOnboard = { open: open, hasAnswers: hasAnswers };

  if (auto && !hasAnswers() && !safe(function () { return sessionStorage.getItem(DISMISSED_KEY); }, null)) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', open);
    else open();
  }
})();
