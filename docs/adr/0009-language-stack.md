# ADR-0009: Indian-language stack — Bhashini and AI4Bharat, English canonical text, originals kept

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §8.5, §8.6 · ADR-0008, ADR-0010

## Context

Citizens write and speak in any of India's 22 scheduled languages, often code-mixed (Hinglish) or in Latin script on WhatsApp. The government's own language platform, Bhashini, offers speech recognition, translation and speech synthesis; AI4Bharat publishes open models for the same tasks. Analytics need one canonical language for deduplication and aggregation.

## Decision

- Keep the original text or transcript; add English canonical text (`text_en`) for analytics and deduplication; reply and render the UI in the user's language.
- **Speech recognition:** Bhashini first; self-hosted AI4Bharat IndicConformer as fallback; Whisper as a last resort.
- **Translation:** Bhashini or IndicTrans2, with a glossary that keeps project and place names intact.
- **Romanized input:** detect it (for example `hi-Latn`) and transliterate with IndicXlit when needed; the understanding step sees both the original and the translation, which handles code-mixing.
- **Speech replies (Could):** Bhashini or Indic Parler-TTS.
- Language tags are BCP-47. A language is switched on only after it passes its gold-set evaluation.
- Pilot languages: English, Hindi, Kannada — plus Urdu for Lucknow if its evaluation passes.

## Consequences

- Good: aligned with India's digital public infrastructure; an open fallback for every step; consistent analytics.
- Bad: translation errors can leak into analytics — mitigated by keeping originals and showing both to the understanding step; Bhashini availability and rate limits — mitigated by fallback models.

## Alternatives considered

- An LLM for everything — no speech input, higher cost, less aligned with national infrastructure.
- English-only analytics without originals — loses nuance and cannot be audited.

## Revisit when

Evaluations show a single multilingual model beating this pipeline on both quality and cost.
