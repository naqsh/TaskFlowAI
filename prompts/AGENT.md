# Prompt Packs (v2.0.0)

This directory contains prompt packs for each agent role.

## Per-agent layout (12 files = 11 + CONTRACT)

Each of `context`, `planner`, `verification`, `adversarial`, `critic`, `orchestrator` must contain:

1. `system.md` — include CRITICAL SECURITY RULE + spotlighting instructions
2. `context.md`
3. `instructions.md`
4. `examples.md` — at least 3 examples with `<thinking>` blocks
5. `output-schema.md`
6. `tools.md`
7. `reasoning.md`
8. `guardrails.md`
9. `input-security.md`
10. `quality-checklist.md`
11. `CHANGELOG.md` — version `v2.0.0`
12. `CONTRACT.md` — must specify `max_tokens` / token budget

XML structure for instructional content: `<instructions>`, `<examples>`, `<external_content>`.

## Loader

`backend/llm/prompt_loader.py` loads packs, fails fast on missing files, and assembles
cache-friendly system blocks (stable content first; dynamic user input last).

## OpenAI / Claude caching notes (TF-039)

- **Do not change whitespace** in stable prompt files casually — OpenAI prefix caching is
  sensitive to exact byte prefixes.
- Prompt version string is included in the stable block; bumping version invalidates cache.
- Claude uses `cache_control: { type: ephemeral }` on the last stable system block.
- Cache warming deferred to MVP 6 (TF-058). See `docs/OBSERVABILITY.md`.
