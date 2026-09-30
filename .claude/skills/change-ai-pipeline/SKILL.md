---
name: change-ai-pipeline
description: Use when touching any AI step in INFRA-AI — LLM prompts or JSON schemas for news extraction, citizen-message understanding or area briefs; speech recognition, translation, transliteration or embeddings; or changing a model or provider. Enforces evidence verification, citations, prompt versioning, gold-set evaluation and provider swappability.
---

# Change an AI step

Read first: ADR-0008 (LLM boundary), ADR-0009 (language stack), `AGENTS.md` invariants 3, 5, 11. For Claude API code, load the `claude-api` skill before writing it.
Paths follow docs/PLAN.md §12; if one does not exist yet, create it there.

## Rules that never bend

1. The model reads and structures text. It never originates facts, numbers or scores.
2. Every extracted claim carries a verbatim `evidence` quote, and code checks that the quote appears in the source text (after normalizing whitespace and Unicode). No match → review queue, never the database.
3. Every brief sentence cites fact ids from the supplied facts, and every number in the text appears in those facts. Validation fails → regenerate once → templated brief. Fail closed.
4. Outputs are schema-constrained (structured outputs) and validated after parsing; stage, kind and category are enums. Check the stop reason (including refusals) before parsing.
5. One function per capability in `ml/ai/<capability>.py` (`extract_events`, `understand_request`, `write_brief`, `transcribe`, `translate`, `embed`); the provider is picked by an environment variable. No provider SDK calls anywhere else.
6. Every stored output records `extractor` = model id + prompt version.
7. Citizen text is redacted (phone, email, Aadhaar- or PAN-like numbers) before any hosted model sees it; raw citizen text is never logged at info level.

## Workflow

1. Prompts live in `ml/ai/prompts/<capability>/vN.md`. Never edit a released version — add `vN+1`.
2. Run the gold-set evaluation: `make eval CAP=<capability>` (exists from M3). Gold sets are `ml/eval/<capability>/*.jsonl` — at least English, Hindi and Kannada, including code-mixed and romanized text.
3. Compare against the current version per field and per language, and put the table in the PR. A regression in any language blocks the merge unless the PR justifies it.
4. Model choice: default `claude-opus-5`. Tune `effort` per route before considering a cheaper model. Moving a route to a different model tier is a team decision, recorded in an ADR with the evaluation numbers.
5. Cost: bulk jobs use the Message Batches API; keep the system prompt and schema stable and first, so prompt caching works. State the cost per 1,000 items in the PR.
6. Real-time paths (chat replies, briefs): measure p95 latency against docs/PLAN.md §14.

## Adding a language

- At least 50 labeled citizen messages (including voice) and 30 labeled articles in the gold sets before switching it on.
- Measure the speech-recognition word error rate on 20+ real voice notes; if it is poor, keep the language text-only and say so in the UI.
