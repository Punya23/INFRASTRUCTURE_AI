# ADR-0010: Citizen intake — WhatsApp first, Telegram and web fallbacks, persist-then-acknowledge processing

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §8.5 · ADR-0005, ADR-0009, ADR-0011

## Context

The problem statement requires intake by voice, text and messaging apps across language regions. WhatsApp is India's most-used messaging app but needs Meta business verification; Telegram does not. Voice processing takes seconds, messaging providers retry webhooks that do not answer quickly, and the AI services can be down.

## Decision

- **Channels:** WhatsApp Cloud API (primary), a Telegram bot (fallback and demo), a web app with microphone and location, IVR / missed call (Could). One processing pipeline for all of them.
- **Persist, then acknowledge:** the webhook verifies the provider signature, inserts the raw message into `inbound_message` (unique provider message id) and returns 200. A Python worker claims jobs with `FOR UPDATE SKIP LOCKED`, retries with backoff, dead-letters after 5 attempts and replies asynchronously.
- **Location:** a shared pin first; else a landmark geocoded inside the city; else ask for a pin. Store the precision.
- **Deduplication into issues:** same category, within 300 m, embedding similarity ≥ 0.8 (thresholds in config).
- **Request types:** `new_facility`, `repair`, `service`. Questions ("what's coming near me?") get an area brief and are not counted as demand.
- A consent notice on first contact; opt-in for status updates (ADR-0011).

## Consequences

- Good: no message is lost when AI services fail; idempotent under provider retries; channels are interchangeable.
- Bad: replies arrive seconds later (acceptable in chat); WhatsApp limits proactive messages outside its 24-hour window to approved templates.

## Alternatives considered

- Processing inside the webhook — timeouts, duplicate processing, lost messages.
- A separate message broker — an extra service (ADR-0005).
- App-only intake — excludes low-end phones and low-literacy users.

## Revisit when

Sustained intake exceeds ~200 messages per second, or a grievance system such as CPGRAMS offers an integration API (then add an Open311 bridge).
