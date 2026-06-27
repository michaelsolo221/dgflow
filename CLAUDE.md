## Agent skills

### Issue tracker

GitHub Issues at `michaelsolo221/dgflow`. PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.

## CXAS Conventions

Before writing or reviewing CXAS agent code, read `docs/conventions.md`. It is the definitive source for naming, CLI invocation, `app.json` required fields, YAML gotchas, platform pitfalls, callback signatures, CI hygiene, and eval session parameters.

For platform overview, known proto constraints, callback order, and canonical links to GCP console / cxas-scrapi docs, see `docs/cxas-platform.md`.

## Local verification

```bash
uv sync --extra dev && uv run ruff check . && uv run ruff format --check . && uv run pytest -v
uv run cxas lint --app-dir night-line/cxas_app/NightLine/
python3 night-line/scripts/check_session_params.py
```

This is what CI runs in `lint` + `test` jobs. No cloud creds needed.

## Running evals (cloud)

ADC is configured (`gcloud auth application-default login`). cxas-scrapi picks it up automatically — no env vars or service account files.

```bash
APP="projects/superb-tendril-409615/locations/us/apps/8093c2b8-e21e-4435-a5e4-dd454657d183"

# Deploy latest code first (evals run against the deployed app, not local files)
uv run cxas push --app-dir night-line/cxas_app/NightLine --to "$APP" \
  --project-id superb-tendril-409615 --location us

# Push evals, then run
uv run cxas push-eval --app-name "$APP" --file night-line/evals/simulations/first_call.yaml
uv run cxas run --app-name "$APP" --tags P0 --wait

# Tool tests (direct, no push)
uv run cxas test-tools --app-name "$APP" --test-file night-line/evals/tool_tests/get_memory.yaml
```

Always `cxas push` before `cxas run` — evals test the deployed app, not local files.

## Repository architecture

| Repo | Purpose |
|---|---|
| [`michaelsolo221/dgflow`](https://github.com/michaelsolo221/dgflow) (this repo) | Cloud Run webhook app — TypeScript/Express orchestrator, persona loading, Gemini integration, Firestore memory. |
| [`michaelsolo221/night-line-agent`](https://github.com/michaelsolo221/night-line-agent) | Dialogflow CX agent definition — flows, pages, intents, webhooks (JSON package format). |

The `cx/` directory in this repo is a local copy for reference. The canonical agent source is `night-line-agent`.
