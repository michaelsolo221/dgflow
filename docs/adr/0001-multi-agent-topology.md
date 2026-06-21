# ADR-0001: Multi-Agent Topology

**Date:** 2026-06-20
**Status:** Accepted

## Context

Night Line offers three distinct persona companions (Luna, Viktor, Sol). Each needs:

- Independent voice configuration (`en-US-Studio-O/M/Q`)
- Character-specific system instructions
- Per-persona guardrails (blocklists, safety levels, topic rules)
- Per-persona callbacks (memory init, fact injection, farewell)

## Decision

Use a **multi-agent** CXAS topology: one root agent for welcome/routing, plus one sub-agent per persona.

## Alternatives Considered

**Single agent with dynamic prompting:** Load persona instructions at runtime and inject them via `before_model_callback`. Rejected because:

- Voice configuration is per-agent in CXAS, not per-turn
- Guardrails cannot be toggled dynamically; they'd need union rules that weaken per-persona boundaries
- Per-persona callback scoping is agent-level, not call-level in CXAS

## Consequences

- Four `instruction.txt` files to maintain (root + 3 personas)
- Four sets of callback files (3 persona agents share the same callback code but need per-agent copies)
- Routing must explicitly transfer to sub-agents via CXAS transfer tools
- Goldens that test multi-agent flows must end at transfer point, not after sub-agent first response (CXAS constraint)
