# Eval Run Log

> Append one row per eval run. Use this to spot regressions and track fix cycles.

## Columns

| date | slice | eval_type | pass_rate | total | failures | root_cause |
|------|-------|-----------|-----------|-------|----------|------------|
| YYYY-MM-DD | N | golden|sim|tool|callback | X/Y | Z | list ids | what caused failures |

## Example

| date | slice | eval_type | pass_rate | total | failures | root_cause |
|------|-------|-----------|-----------|-------|----------|------------|
| 2026-06-20 | 3 | golden | 8/12 | 12 | routing_viktor, routing_sol, guardrail_deflect, silence_3 | childAgents had display names instead of dir names |

## Legend

- **date** — when the run happened
- **slice** — build slice number (see `night-line/todo.md`)
- **eval_type** — `golden`, `sim`, `tool`, `callback`, or `all`
- **pass_rate** — `passes/total` count (not percentage)
- **total** — total evals in the run
- **failures** — comma-separated list of failing eval names
- **root_cause** — one sentence: what was wrong and what fixed it
