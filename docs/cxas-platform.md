# CX Agent Studio (CXAS) — Platform Reference

A stable-link reference for the CXAS platform used by Night Line. Prefer following these links over relying on training-data knowledge — the platform is evolving rapidly.

## What it is

CX Agent Studio (CES) is Google's hosted agent platform built on the `google.cloud.ces_v1beta` proto. It runs multi-modal voice agents on GCP infrastructure, handles telephony, and exposes a Python callback SDK.

SDK on PyPI: `cxas-scrapi` — source at https://github.com/GoogleCloudPlatform/cxas-scrapi  
Agent authoring guide: https://github.com/GoogleCloudPlatform/cxas-scrapi/blob/main/AGENTS.md

## Key concepts

| Concept | What it is |
|---|---|
| **App** | Top-level resource — maps to `app.json` + subdirectories |
| **Agent** | A persona with an instruction, model, tools, guardrails, and callbacks |
| **Tool / PythonFunction** | Python callable exposed to the agent; schema inferred from signature |
| **Guardrail** | Input/output filter attached to an agent |
| **VariableDeclaration** | Session-scoped typed slot declared in `app.json` |
| **CallbackContext** | Runtime object passed to callbacks; exposes `.state` dict (the session variables) |

## CLI quick reference

```bash
# from night-line/ dir, using uv
uv run cxas lint --app-dir cxas_app/NightLine/
uv run cxas push --app-dir cxas_app/NightLine/ \
  --project-id <project> --location us \
  --to "projects/<project>/locations/us/apps/<app-id>"
uv run cxas apps list --project-id <project> --location us
uv run cxas pull "<app-name>" --project-id <project> --location us --target-dir <dir>
```

## Callbacks

Three hooks available on each agent, executed in order per turn:

1. `before_agent_callback` — fires once on the first turn; use for init / memory load
2. `before_model_callback` — fires before every model call; use for context injection
3. `after_model_callback` — fires after every model response; use for logging / farewell detection

All receive `callback_context: CallbackContext`. Session state is at `callback_context.state` (dict, string-typed values).

## Known proto constraints (hard-won)

- `rootAgent` is **not** a valid `App` field — omit from `app.json`
- `inputSchema` is **not** valid on `Tool` or `PythonFunction` — schema is inferred from Python signature
- Location for this project: `us` (not `global`, not `us-central1`)
- `BOOLEAN` session variables are accessed as strings — use `"true"` / `""`

## Links

| Resource | URL |
|---|---|
| CXAS console | https://console.cloud.google.com/customer-engagement/agent-studio |
| CES API reference | https://cloud.google.com/generative-ai-app-builder/docs/reference/rest |
| cxas-scrapi repo | https://github.com/GoogleCloudPlatform/cxas-scrapi |
| AGENTS.md authoring guide | https://github.com/GoogleCloudPlatform/cxas-scrapi/blob/main/AGENTS.md |
| Gemini live models | https://cloud.google.com/vertex-ai/generative-ai/docs/live-api |
