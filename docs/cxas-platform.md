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

## Agent JSON structure

Each agent directory needs a `<name>.json` with explicit callback and child declarations — the server does **not** auto-discover from directory structure:

```json
{
  "name": "luna_agent",
  "displayName": "luna_agent",
  "instruction": "agents/luna_agent/instruction.txt",
  "tools": ["end_session", "get_memory"],
  "childAgents": ["sub_agent_name"],
  "beforeAgentCallbacks": [{"pythonCode": "agents/luna_agent/before_agent_callbacks/init/python_code.py"}],
  "beforeModelCallbacks": [{"pythonCode": "agents/luna_agent/before_model_callbacks/inject_facts/python_code.py"}],
  "afterModelCallbacks":  [{"pythonCode": "agents/luna_agent/after_model_callbacks/farewell/python_code.py"}]
}
```

- `displayName` must match `name` exactly — displayName mismatches cause 400 on push
- `childAgents` values must be exact `name` field values (not displayName)
- Omit `childAgents` entirely on leaf agents (empty array `[]` may cause issues)
- Custom tools must also be listed in `app.json`'s top-level `tools` array
- `end_session` is a platform system tool — do not create a `tools/end_session/` directory

## Callbacks

Three hooks available on each agent, executed in order per turn:

1. `before_agent_callback` — fires once on the first turn; use for init / memory load
2. `before_model_callback` — fires before every model call; use for context injection
3. `after_model_callback` — fires after every model response; use for logging / farewell detection

All receive `callback_context: CallbackContext`. Session state is at `callback_context.state` (dict, string-typed values).

**Platform globals — do NOT import these:** `CallbackContext`, `Content`, `Part`, `LlmResponse`, `LlmRequest` are auto-injected into the callback sandbox. Importing `gecx` will cause a 400 push failure. Only standard library imports (`typing`, `json`, `re`) need explicit import statements.

Template: https://github.com/GoogleCloudPlatform/cxas-scrapi/tree/main/.agents/skills/cxas-agent-foundry/assets/project-template

## Known proto constraints (hard-won)

- `rootAgent` **is** a valid `App` field — set it to the entry agent name (e.g. `"root_agent"`)
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
