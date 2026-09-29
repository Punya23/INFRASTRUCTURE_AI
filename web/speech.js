/**
 * =============================================================================
 * INFRA-AI Speech Service (speech.js)
 * =============================================================================
 * Modular STT and TTS with provider abstraction.
 * Uses Web Speech API (browser-native) as default provider.
 * Architecture supports swapping to Bhashini, Google Cloud, or Azure
 * via environment configuration (ADR-0008: swappable AI providers).
 *
 * Integrates with i18n.js for locale-aware speech:
 *   - Reads INFRA_I18N.getCurrentLang() for active language
 *   - Uses speechLocale from LANGUAGES registry for provider codes
 *   - Syncs when language changes via INFRA_I18N events
 *
 * Privacy (ADR-0011): No raw audio stored. Browser API processes locally.
 * When using cloud providers, audio is sent to the configured endpoint only.
 * =============================================================================
 */
(function (root) {
  'use strict';

  // =========================================================================
  // SPEECH LOCALE MAP — maps i18n codes to Web Speech API BCP-47 tags
  // Falls back to LANGUAGES[].speechLocale from i18n.js when available
  // =========================================================================
  var SPEECH_LOCALES = {
    'en': 'en-IN',  'hi': 'hi-IN',  'mr': 'mr-IN',  'kn': 'kn-IN',
    'bn': 'bn-IN',  'gu': 'gu-IN',  'ta': 'ta-IN',  'te': 'te-IN',
    'ml': 'ml-IN',  'pa': 'pa-IN',  'or': 'or-IN',  'as': 'as-IN',
    'ur': 'ur-IN',  'pt': 'pt-BR',  'ru': 'ru-RU',  'zh': 'zh-CN',
    'ar': 'ar-SA',  'id': 'id-ID'
  };

  // =========================================================================
  // PROVIDER DETECTION
  // =========================================================================
  var SpeechRecognition = root.SpeechRecognition || root.webkitSpeechRecognition;
  var SpeechSynthesis = root.speechSynthesis;

  function isSTTSupported() {
    return !!SpeechRecognition;
  }

  function isTTSSupported() {
    return !!SpeechSynthesis;
  }

  function getSpeechLocale(langCode) {
    // Try i18n.js LANGUAGES registry first
    if (root.INFRA_I18N && root.INFRA_I18N.getLanguageConfig) {
      var config = root.INFRA_I18N.getLanguageConfig(langCode);
      if (config && config.speechLocale) return config.speechLocale;
    }
    return SPEECH_LOCALES[langCode] || 'en-IN';
  }

  function getCurrentLang() {
    if (root.INFRA_I18N && root.INFRA_I18N.getCurrentLang) {
      return root.INFRA_I18N.getCurrentLang();
    }
    return document.documentElement.lang || 'en';
  }

  // =========================================================================
  // SPEECH-TO-TEXT SERVICE
  // =========================================================================
  function STTService() {
    this.recognition = null;
    this.isRecording = false;
    this.isPaused = false;
    this.startTime = null;
    this.timerInterval = null;
    this.onResult = null;       // callback(text, isFinal)
    this.onError = null;        // callback(errorCode, message)
    this.onStateChange = null;  // callback(state: 'idle'|'recording'|'processing'|'error')
    this.onDuration = null;     // callback(seconds)
    this.transcript = '';
    this.maxDurationMs = 120000; // 2 minute limit
    this.maxTimer = null;
  }

  STTService.prototype.isAvailable = function () {
    return isSTTSupported();
  };

  STTService.prototype.getSupportedLocales = function () {
    // Web Speech API doesn't expose this; return our known-supported list
    return Object.keys(SPEECH_LOCALES);
  };

  STTService.prototype.isLocaleSupported = function (langCode) {
    // Optimistic for Web Speech API — browser will error if truly unsupported
    return !!SPEECH_LOCALES[langCode];
  };

  STTService.prototype.start = function (options) {
    var self = this;
    options = options || {};

    if (!this.isAvailable()) {
      this._emitError('not-supported', 'Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (this.isRecording) {
      this.stop();
      return;
    }

    var lang = options.lang || getCurrentLang();
    var locale = getSpeechLocale(lang);

    this.recognition = new SpeechRecognition();
    this.recognition.lang = locale;
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.transcript = '';

    this.recognition.onstart = function () {
      self.isRecording = true;
      self.isPaused = false;
      self.startTime = Date.now();
      self._startTimer();
      self._emitState('recording');

      // Safety: auto-stop after max duration
      self.maxTimer = setTimeout(function () {
        if (self.isRecording) {
          self.stop();
          self._emitError('timeout', 'Recording reached the 2-minute limit.');
        }
      }, self.maxDurationMs);
    };

    this.recognition.onresult = function (event) {
      var interim = '';
      var final = '';

      for (var i = event.resultIndex; i < event.results.length; i++) {
        var result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        self.transcript += final;
        if (self.onResult) self.onResult(self.transcript, true);
      } else if (interim) {
        if (self.onResult) self.onResult(self.transcript + interim, false);
      }
    };

    this.recognition.onerror = function (event) {
      var msg;
      switch (event.error) {
        case 'not-allowed':
          msg = 'Microphone permission was denied. Please allow microphone access in your browser settings.';
          break;
        case 'no-speech':
          msg = 'No speech was detected. Please try again and speak clearly.';
          break;
        case 'audio-capture':
          msg = 'No microphone was found. Please connect a microphone and try again.';
          break;
        case 'network':
          msg = 'Network error during speech recognition. Please check your connection.';
          break;
        case 'language-not-supported':
          msg = 'Speech recognition is not available for the selected language. Please try English or switch to text input.';
          break;
        default:
          msg = 'Speech recognition error: ' + event.error;
      }
      self._cleanup();
      self._emitError(event.error, msg);
    };

    this.recognition.onend = function () {
      if (self.isRecording) {
        // Ended unexpectedly (browser stopped it) — still deliver transcript
        self._cleanup();
        self._emitState('idle');
        if (self.transcript && self.onResult) {
          self.onResult(self.transcript, true);
        }
      }
    };

    try {
      this.recognition.start();
    } catch (e) {
      this._emitError('start-failed', 'Failed to start recording: ' + e.message);
    }
  };

  STTService.prototype.stop = function () {
    if (this.recognition && this.isRecording) {
      this.recognition.stop();
    }
    this._cleanup();
    this._emitState('idle');
  };

  STTService.prototype.getTranscript = function () {
    return this.transcript;
  };

  STTService.prototype.clearTranscript = function () {
    this.transcript = '';
  };

  STTService.prototype._startTimer = function () {
    var self = this;
    this._stopTimer();
    this.timerInterval = setInterval(function () {
      if (self.startTime && self.onDuration) {
        var elapsed = Math.floor((Date.now() - self.startTime) / 1000);
        self.onDuration(elapsed);
      }
    }, 250);
  };

  STTService.prototype._stopTimer = function () {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  };

  STTService.prototype._cleanup = function () {
    this.isRecording = false;
    this.isPaused = false;
    this._stopTimer();
    if (this.maxTimer) {
      clearTimeout(this.maxTimer);
      this.maxTimer = null;
    }
  };

  STTService.prototype._emitState = function (state) {
    if (this.onStateChange) this.onStateChange(state);
  };

  STTService.prototype._emitError = function (code, message) {
    this._emitState('error');
    if (this.onError) this.onError(code, message);
  };

  // =========================================================================
  // TEXT-TO-SPEECH SERVICE
  // =========================================================================
  function TTSService() {
    this.utterance = null;
    this.isPlaying = false;
    this.isPaused = false;
    this.onStateChange = null;  // callback(state: 'idle'|'playing'|'paused'|'error')
    this.onError = null;        // callback(code, message)
    this._voiceCache = {};
  }

  TTSService.prototype.isAvailable = function () {
    return isTTSSupported();
  };

  TTSService.prototype.speak = function (text, options) {
    var self = this;
    options = options || {};

    if (!this.isAvailable()) {
      this._emitError('not-supported', 'Text-to-speech is not supported in this browser.');
      return;
    }

    if (!text || !text.trim()) {
      this._emitError('empty-text', 'No text provided for speech.');
      return;
    }

    // Stop any current speech
    this.stop();

    var lang = options.lang || getCurrentLang();
    var locale = getSpeechLocale(lang);
    var rate = options.rate || 0.95;
    var pitch = options.pitch || 1.0;

    this.utterance = new SpeechSynthesisUtterance(text);
    this.utterance.lang = locale;
    this.utterance.rate = rate;
    this.utterance.pitch = pitch;

    // Try to find a matching voice
    var voice = this._findVoice(locale);
    if (voice) {
      this.utterance.voice = voice;
    }

    this.utterance.onstart = function () {
      self.isPlaying = true;
      self.isPaused = false;
      self._emitState('playing');
    };

    this.utterance.onend = function () {
      self.isPlaying = false;
      self.isPaused = false;
      self._emitState('idle');
    };

    this.utterance.onerror = function (event) {
      self.isPlaying = false;
      self.isPaused = false;
      if (event.error === 'canceled' || event.error === 'interrupted') {
        self._emitState('idle');
      } else {
        self._emitError(event.error, 'Speech synthesis error: ' + event.error);
      }
    };

    this.utterance.onpause = function () {
      self.isPaused = true;
      self._emitState('paused');
    };

    this.utterance.onresume = function () {
      self.isPaused = false;
      self._emitState('playing');
    };

    SpeechSynthesis.speak(this.utterance);
  };

  TTSService.prototype.pause = function () {
    if (this.isPlaying && !this.isPaused) {
      SpeechSynthesis.pause();
    }
  };

  TTSService.prototype.resume = function () {
    if (this.isPaused) {
      SpeechSynthesis.resume();
    }
  };

  TTSService.prototype.stop = function () {
    SpeechSynthesis.cancel();
    this.isPlaying = false;
    this.isPaused = false;
    this._emitState('idle');
  };

  TTSService.prototype.togglePause = function () {
    if (this.isPaused) {
      this.resume();
    } else if (this.isPlaying) {
      this.pause();
    }
  };

  TTSService.prototype._findVoice = function (locale) {
    if (this._voiceCache[locale]) return this._voiceCache[locale];

    var voices = SpeechSynthesis.getVoices();
    var langPrefix = locale.split('-')[0];
    var match = null;

    // Exact match first
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].lang === locale) {
        match = voices[i];
        break;
      }
    }

    // Prefix match
    if (!match) {
      for (var j = 0; j < voices.length; j++) {
        if (voices[j].lang.startsWith(langPrefix)) {
          match = voices[j];
          break;
        }
      }
    }

    if (match) this._voiceCache[locale] = match;
    return match;
  };

  TTSService.prototype._emitState = function (state) {
    if (this.onStateChange) this.onStateChange(state);
  };

  TTSService.prototype._emitError = function (code, message) {
    this._emitState('error');
    if (this.onError) this.onError(code, message);
  };

  // =========================================================================
  // UI COMPONENT FACTORY
  // =========================================================================

  /**
   * Creates a microphone button with full recording UI.
   * @param {Object} opts
   * @param {HTMLElement} opts.targetInput - textarea/input to fill with transcription
   * @param {HTMLElement} opts.container - element to append the mic UI into
   * @param {Function} [opts.onTranscript] - callback(text) when final text ready
   */
  function createMicButton(opts) {
    var stt = new STTService();
    var container = opts.container;
    var targetInput = opts.targetInput;

    // Build UI
    var wrapper = document.createElement('div');
    wrapper.className = 'speech-mic-wrapper';
    wrapper.setAttribute('role', 'group');
    wrapper.setAttribute('aria-label', 'Voice input controls');

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'speech-mic-btn';
    btn.setAttribute('aria-label', 'Record voice input');
    btn.title = 'Record voice input';
    btn.innerHTML = '<span class="material-symbols-outlined speech-mic-icon">mic</span>';

    var statusEl = document.createElement('div');
    statusEl.className = 'speech-mic-status';
    statusEl.setAttribute('aria-live', 'polite');
    statusEl.style.display = 'none';

    var durationEl = document.createElement('span');
    durationEl.className = 'speech-mic-duration';

    var stateTextEl = document.createElement('span');
    stateTextEl.className = 'speech-mic-state-text';

    statusEl.appendChild(durationEl);
    statusEl.appendChild(stateTextEl);

    var errorEl = document.createElement('div');
    errorEl.className = 'speech-mic-error';
    errorEl.setAttribute('role', 'alert');
    errorEl.style.display = 'none';

    wrapper.appendChild(btn);
    wrapper.appendChild(statusEl);
    wrapper.appendChild(errorEl);
    container.appendChild(wrapper);

    // Check support
    if (!stt.isAvailable()) {
      btn.disabled = true;
      btn.title = 'Voice input not supported in this browser';
      btn.setAttribute('aria-label', 'Voice input not supported');
      btn.classList.add('speech-mic-disabled');
      return { stt: stt, element: wrapper };
    }

    // Wire callbacks
    stt.onResult = function (text, isFinal) {
      if (targetInput) {
        targetInput.value = text;
        targetInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (isFinal && opts.onTranscript) {
        opts.onTranscript(text);
      }
    };

    stt.onStateChange = function (state) {
      btn.classList.remove('speech-mic-recording', 'speech-mic-processing');
      errorEl.style.display = 'none';

      switch (state) {
        case 'recording':
          btn.classList.add('speech-mic-recording');
          btn.innerHTML = '<span class="material-symbols-outlined speech-mic-icon">stop</span>';
          btn.setAttribute('aria-label', 'Stop recording');
          statusEl.style.display = 'flex';
          stateTextEl.textContent = 'Recording…';
          break;
        case 'processing':
          btn.classList.add('speech-mic-processing');
          btn.innerHTML = '<span class="material-symbols-outlined speech-mic-icon">hourglass_top</span>';
          statusEl.style.display = 'flex';
          stateTextEl.textContent = 'Processing…';
          break;
        case 'idle':
          btn.innerHTML = '<span class="material-symbols-outlined speech-mic-icon">mic</span>';
          btn.setAttribute('aria-label', 'Record voice input');
          statusEl.style.display = 'none';
          durationEl.textContent = '';
          break;
        case 'error':
          btn.innerHTML = '<span class="material-symbols-outlined speech-mic-icon">mic</span>';
          btn.setAttribute('aria-label', 'Record voice input');
          statusEl.style.display = 'none';
          break;
      }
    };

    stt.onDuration = function (seconds) {
      var min = Math.floor(seconds / 60);
      var sec = seconds % 60;
      durationEl.textContent = (min < 10 ? '0' : '') + min + ':' + (sec < 10 ? '0' : '') + sec;
    };

    stt.onError = function (code, message) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
      // Auto-hide after 8 seconds
      setTimeout(function () { errorEl.style.display = 'none'; }, 8000);
    };

    btn.addEventListener('click', function () {
      if (stt.isRecording) {
        stt.stop();
      } else {
        errorEl.style.display = 'none';
        stt.clearTranscript();
        // Preserve existing text
        if (targetInput && targetInput.value.trim()) {
          stt.transcript = targetInput.value.trim() + ' ';
        }
        stt.start();
      }
    });

    return { stt: stt, element: wrapper, button: btn };
  }

  /**
   * Creates a TTS "Listen" button.
   * @param {Object} opts
   * @param {Function} opts.getText - returns the text to speak
   * @param {HTMLElement} opts.container - element to append button into
   * @param {string} [opts.label] - button label text
   */
  function createListenButton(opts) {
    var tts = new TTSService();

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'speech-listen-btn';
    btn.setAttribute('aria-label', opts.label || 'Listen to this content');
    btn.innerHTML =
      '<span class="material-symbols-outlined speech-listen-icon">volume_up</span>' +
      '<span class="speech-listen-label">' + (opts.label || 'Listen') + '</span>';

    if (!tts.isAvailable()) {
      btn.disabled = true;
      btn.title = 'Text-to-speech not supported';
      btn.classList.add('speech-listen-disabled');
      opts.container.appendChild(btn);
      return { tts: tts, element: btn };
    }

    tts.onStateChange = function (state) {
      btn.classList.remove('speech-listen-playing', 'speech-listen-paused');
      switch (state) {
        case 'playing':
          btn.classList.add('speech-listen-playing');
          btn.querySelector('.speech-listen-icon').textContent = 'pause';
          btn.querySelector('.speech-listen-label').textContent = 'Pause';
          break;
        case 'paused':
          btn.classList.add('speech-listen-paused');
          btn.querySelector('.speech-listen-icon').textContent = 'play_arrow';
          btn.querySelector('.speech-listen-label').textContent = 'Resume';
          break;
        case 'idle':
          btn.querySelector('.speech-listen-icon').textContent = 'volume_up';
          btn.querySelector('.speech-listen-label').textContent = opts.label || 'Listen';
          break;
      }
    };

    tts.onError = function (code, msg) {
      console.warn('[INFRA-AI TTS]', code, msg);
      btn.querySelector('.speech-listen-icon').textContent = 'volume_up';
      btn.querySelector('.speech-listen-label').textContent = opts.label || 'Listen';
    };

    btn.addEventListener('click', function () {
      if (tts.isPlaying && !tts.isPaused) {
        tts.pause();
      } else if (tts.isPaused) {
        tts.resume();
      } else {
        var text = typeof opts.getText === 'function' ? opts.getText() : '';
        if (text) tts.speak(text);
      }
    });

    opts.container.appendChild(btn);
    return { tts: tts, element: btn };
  }

  // =========================================================================
  // CLEANUP ON NAVIGATION
  // =========================================================================
  root.addEventListener('beforeunload', function () {
    if (SpeechSynthesis) SpeechSynthesis.cancel();
  });

  // =========================================================================
  // PUBLIC API
  // =========================================================================
  root.INFRA_SPEECH = {
    STTService: STTService,
    TTSService: TTSService,
    createMicButton: createMicButton,
    createListenButton: createListenButton,
    isSTTSupported: isSTTSupported,
    isTTSSupported: isTTSSupported,
    getSpeechLocale: getSpeechLocale,
    getCurrentLang: getCurrentLang,
    SPEECH_LOCALES: SPEECH_LOCALES
  };

})(typeof window !== 'undefined' ? window : this);
