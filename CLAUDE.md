@AGENTS.md

## Claude Code notes

- Project skills in `.claude/skills/` are auto-discovered — use the one that matches the task before you start (table in AGENTS.md).
- Before writing Claude API code in `ml/ai/`, load the `claude-api` skill. Project defaults: model `claude-opus-5`, structured outputs, the Message Batches API for bulk jobs, `effort` tuned per route (ADR-0008).
- Anything that spans more than one component: write the plan first, then build milestone by milestone (docs/PLAN.md §13).
