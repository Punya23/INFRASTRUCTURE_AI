# ADR-0011: Privacy and do-no-harm by design (DPDP-aligned)

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §15 · ADR-0008, ADR-0010, ADR-0012

## Context

Citizen messages contain phone numbers, names, addresses and sometimes sensitive complaints. The Digital Personal Data Protection Act, 2023 requires notice, consent, purpose limitation, retention limits and erasure on request. The DPG Standard's "do no harm by design" indicator covers data privacy, inappropriate content and harassment. Growth signals could fuel land speculation or displacement, and digital requests over-represent connected, literate, urban residents.

## Decision

- **Notice and consent** at first contact, in the user's language; purpose: aggregating development needs.
- **Identifiers:** phone numbers and user ids are stored only as an HMAC-SHA256 with a server secret (`reporter_hash`). Raw contact details exist only for citizens who opt in to updates — encrypted, in a separate `contact` table, deleted 90 days after the linked issue closes or on request.
- **Redaction:** phone numbers, emails and Aadhaar- or PAN-like numbers are removed with patterns before any hosted model sees the text; names flagged by the understanding step are removed before storage.
- **Public outputs are aggregates:** counts below 5 are suppressed at hexagon level; message text is never public. Policymakers see redacted text behind a login, with an audit log.
- **No Aadhaar** and no identity verification.
- **Growth outlook:** hexagon or locality level only, never parcels; labeled informational, not investment advice; equity views (silent gaps) ship alongside growth views.
- **Moderation:** abusive or illegal content is filtered and never displayed.
- **Security:** TLS everywhere, encryption at rest, role-based access for dashboards, secrets outside the repository, rate limits per `reporter_hash`.

## Consequences

- Good: DPDP- and DPG-aligned; data exports can be published openly.
- Bad: analysts get less granular data; rotating the HMAC secret needs a migration plan.

## Alternatives considered

- Storing raw phone numbers for follow-up — unnecessary risk.
- No reporter identifier at all — cannot rate-limit or count distinct reporters.

## Revisit when

A deploying agency completes a legal review, or the phased DPDP Rules change obligations.
