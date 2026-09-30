# ADR-0008: LLMs read, structure and summarize — evidence-verified, cited and provider-swappable

- Status: Proposed
- Date: 2026-09-28
- Deciders: project team
- Related: docs/PLAN.md §8.4–8.6, §14 · ADR-0003, ADR-0009, ADR-0011 · skill `change-ai-pipeline`

## Context

News, press releases, tenders and citizen messages are unstructured and multilingual. LLMs extract structure well but can invent details — a false "metro station coming" claim misleads residents and investors. The DPG Standard requires every proprietary dependency to have an open alternative. Costs must stay manageable at national scale.

## Decision

- **Scope:** LLMs only (1) filter relevance, (2) extract structured events, (3) understand citizen messages and (4) write briefs from facts we supply. They never produce scores, and never facts without a source.
- **Guardrails in code:** JSON-schema-constrained outputs (structured outputs); a verbatim evidence quote checked against the source text; briefs cite fact ids and may use only numbers found in those facts. Any failure → review queue or templated fallback (fail closed).
- **Traceability:** every stored output records the model id and prompt version; prompts are versioned files in `ml/ai/prompts/`; changes are gated on gold-set evaluations.
- **Swappability:** one function per capability in `ml/ai/`; the provider is chosen by an environment variable; no provider SDK calls anywhere else.
- **Default provider:** Claude, model `claude-opus-5`, with `effort` tuned per route (low for relevance filtering and intake, higher for extraction and briefs); the Message Batches API for bulk jobs; a stable prompt prefix so caching works. An open-weights model sits behind the same functions for sovereign or self-hosted deployments.
- Moving any route to a cheaper model is a team decision backed by gold-set numbers, recorded as a new ADR.

## Consequences

- Good: trustworthy, auditable outputs; a provider change touches one module.
- Bad: strict verification rejects some true claims whose evidence was paraphrased, which adds review work; sending citizen text to a hosted model needs the safeguards in ADR-0011.

## Alternatives considered

- Only small fine-tuned models — weaker across 22 languages without labeled data; heavy upfront work.
- Rules and regular expressions — brittle across languages and phrasing.
- Letting the LLM write briefs freely — impossible to verify.

## Revisit when

Gold sets show a cheaper or open model within tolerance for a route, or a deploying agency requires fully self-hosted inference.
