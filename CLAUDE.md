## Agent skills

### Issue tracker

GitHub Issues at `michaelsolo221/dgflow`. PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.

## CXAS Conventions

Before writing or reviewing CXAS agent code, read `docs/conventions.md`. It is the definitive source for naming, CLI invocation, `app.json` required fields, YAML gotchas, platform pitfalls, callback signatures, CI hygiene, and eval session parameters.

## Repository architecture

| Repo | Purpose |
|---|---|
| [`michaelsolo221/dgflow`](https://github.com/michaelsolo221/dgflow) (this repo) | Cloud Run webhook app — TypeScript/Express orchestrator, persona loading, Gemini integration, Firestore memory. |
| [`michaelsolo221/night-line-agent`](https://github.com/michaelsolo221/night-line-agent) | Dialogflow CX agent definition — flows, pages, intents, webhooks (JSON package format). |

The `cx/` directory in this repo is a local copy for reference. The canonical agent source is `night-line-agent`.
