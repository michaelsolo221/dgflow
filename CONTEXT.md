# Night Line — Domain Context

AI companion phone service using CX Agent Studio (CXAS). Late-night voice conversations with persona-driven characters.

## Glossary

| Term | Definition |
|------|------------|
| **Root Agent** | Entrypoint: welcomes callers, presents persona choices, interprets free-form routing. No Firestore access. |
| **Persona Agent** | Per-character sub-agent (Luna, Viktor, Sol). Each has its own `instruction.txt`, voice, tools, callbacks, and guardrails. |
| **Caller Profile** | JSON blob in Firestore keyed by `caller_id` (E.164). Contains `facts`, `call_count`, `recent_turns`. |
| **Turn Guard** | `_initialized` session variable set to `"true"` after first-turn init in `before_agent_callback`. Prevents memory reset on every turn. |
| **CXAS** | Customer Experience Agent Studio — GCP platform handling STT/TTS, LLM conversation, routing, guardrails, session state. |
| **SCRAPI** | `cxas` CLI tool for push/pull/lint/eval of CXAS agents. |

## Architecture Decision Records

See `docs/adr/` for numbered ADRs.

## File Map

```
night-line/cxas_app/NightLine/   ← pushed to CXAS platform
  app.json                        ← app config (variables, model, tools, root agent)
  agents/root_agent/              ← host: welcome + natural language routing
  agents/luna/                    ← persona sub-agent
  agents/viktor/                  ← persona sub-agent
  agents/sol/                     ← persona sub-agent
  tools/                          ← Python function tools (get_memory, save_turn, save_memory)
night-line/gecx-config.json       ← SCRAPI project config
night-line/tdd.md                 ← technical design doc (living document)
scripts/                          ← seed, gate checks
tests/                            ← pytest tests
firestore/personas.json           ← seed data for persona definitions
```
