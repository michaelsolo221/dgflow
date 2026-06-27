# CXAS Coding Conventions

Single source of truth for agent authoring. All issues, PRs, and coding agents should reference this file before writing or reviewing CXAS agent code.

## 1. Naming Conventions

| What | Convention | Example |
|---|---|---|
| Agent directories | `snake_case` | `root_agent/`, `luna_agent/` |
| Agent JSON files | Match directory name | `root_agent.json` |
| Agent `name` field | Match directory name | `"name": "root_agent"` |
| Agent `displayName` | Must match `name` field exactly | `"displayName": "root_agent"` |
| `childAgents` array | Directory name strings (underscores) | `["luna_agent", "viktor_agent"]` |
| Tool directories | `snake_case` | `get_memory/` |
| Tool JSON files | `<tool_name>.json` | `get_memory.json` |
| Tool Python files | Always `python_function/python_code.py` | `get_memory/python_function/python_code.py` |
| Callback directories | `<type>_callbacks/<base>/` | `before_agent_callbacks/init/` |

## 2. CLI Invocation

```bash
# Setup (one-time)
.agents/skills/cxas-agent-foundry/scripts/setup.sh
source .venv/bin/activate

# After setup, use bare cxas in the activated venv
cxas lint --app-dir <project>/cxas_app/
cxas push --app-dir <project>/cxas_app/<AppName> \
  --to projects/<id>/locations/<loc>/apps/<app_id> \
  --project-id <id> --location <loc>
cxas pull projects/<id>/locations/<loc>/apps/<app_id> \
  --project-id <id> --location <loc> --target-dir <project>/cxas_app/

# Auth prefix (required for CLI auth in some environments)
GOOGLE_CLOUD_PROJECT=<id> cxas push ...
```

**Either** `source .venv/bin/activate && cxas` (setup.sh approach) **or** `uv run cxas` (upstream preference) — both work. Pick one and stay consistent.

## 3. Required `app.json` Fields

```json
{
  "rootAgent": "<agent_dir_name>",
  "childAgents": [],
  "variableDeclarations": [
    {"name": "caller_profile", "type": "STRING", "defaultValue": ""},
    {"name": "_initialized", "type": "STRING", "defaultValue": "false"},
    {"name": "persona_id", "type": "STRING", "defaultValue": "unknown"},
    {"name": "caller_id", "type": "STRING", "defaultValue": ""}
  ],
  "modelSettings": {"model": "gemini-2.0-flash-live-001"},
  "loggingSettings": {
    "evaluationAudioRecordingConfig": {
      "gcsBucket": "gs://<real-bucket-name>"
    }
  }
}
```

Audio agents require `loggingSettings` with a real GCS bucket — placeholder strings return HTTP 400 on every eval run.

## 4. YAML Format Gotchas

| File type | Top-level key | Common mistake | Consequence |
|---|---|---|---|
| Golden evals | `conversations:` | — | — |
| Simulation evals | list at top level | — | — |
| Tool tests | `tests:` | `test_cases:` | **Silent zero-test-run — runner reports 0 tests, no error** |
| Callback tests | pytest files, not YAML | — | — |

Every sim must have `tags: [P0, HIGH, <category>]`. Sims without tags are silently skipped by `run-and-report.py` when running with priority filters.

## 5. Platform Gotchas Checklist

- [ ] `end_session` on every agent — root AND all persona agents. Missing = `Tool not found: end_session` at runtime.
- [ ] `inputSchema` not `parameters` in tool JSON — lint error, push blocked.
- [ ] Do NOT import `CallbackContext` — GECX sandbox auto-provides it; importing throws at runtime.
- [ ] State values are strings — `_initialized` is `"true"` not `True`; compare with `== "true"`.
- [ ] `caller_id` required in session parameters — `before_agent_callback` reads it from state; missing = KeyError crash.
- [ ] `gcsBucket` must be a real bucket — every audio eval returns HTTP 400 without it.
- [ ] `deployed_app_id` is the short name — not the full resource path; SDK handles pathing.
- [ ] `displayName` must match `name` exactly — mismatches cause `400 Reference not found` on push.
- [ ] `childAgents` values are directory names — underscores, not spaces or display names. Push returns `400 Reference not found` if mismatched.
- [ ] Silence handling required for voice — detect `<context>no user activity` in `before_model_callback`; use `part.text_or_transcript()` not `part.text` (audio parts return `None` for `.text`).
- [ ] Multi-model-call guard on `after_model_callback` — fires on EACH model call; check `callback_context.events` to prevent double injection.
- [ ] `LlmResponse.from_parts()` not raw constructor — `LlmResponse(content=Content(parts=[...]))` fails at runtime.
- [ ] `end_session` cannot be called from callbacks — return `Content` response; platform handles teardown.
- [ ] `speakingRate` in platform config, not instructions — persona-level pacing is unreliable on the live model.
- [ ] `cxas push` before `cxas run` — evals test the deployed app, not local files. Stale deploy = tests pass against old code.

## 6. Callback Signature Reference

```python
# before_agent — one parameter
def before_agent_callback(callback_context):
    # Return None to proceed, or Content to preempt
    if callback_context.state.get("_initialized") == "true":
        return None  # Turn guard — MUST be first check
    ...

# before_model — two parameters
def before_model_callback(callback_context, llm_request):
    # Mutate llm_request to inject context, or return LlmResponse to preempt
    ...

# after_model — two parameters
def after_model_callback(callback_context, llm_response):
    # Check callback_context.events for multi-call guard
    # Return LlmResponse.from_parts() to inject text before end_session
    ...
```

## 7. CI/CD Hygiene

- [ ] `__pycache__/` and `*.pyc` in `.gitignore`
- [ ] `uv sync --extra dev` (not `--dev`) for dev dependencies
- [ ] `pytest` must have real tests — `|| [ $? -eq 5 ]` suppression masks zero-test failures
- [ ] Remove brand-check hooks until a real binary exists; don't hardcode `BRAND_CHECK_SKIP=1`
- [ ] `mdformat` in CI, not just pre-commit
- [ ] `uv` dependency cache enabled (`cache: true` on `astral-sh/setup-uv@v3`)
- [ ] Verify model ID against the actual CXAS API before shipping

## 8. Eval Session Parameters Template

Every golden, sim, callback test mock, and tool test that touches `before_agent_callback` must include:

```yaml
session_parameters:
  caller_id: "+15551234567"
```

Missing `caller_id` causes KeyError in the Firestore lookup path — the #1 silent eval failure.

## 9. Symptom → Cause Debug Reference

Match the error message to the fix without scanning every gotcha:

| Symptom | Likely cause | Fix |
|---|---|---|
| `Tool not found: end_session` at runtime | Missing `end_session` on one or more agents | Add `"end_session"` to every agent's `tools` array in its JSON file |
| `400 Reference not found` on `cxas push` | `childAgents` value doesn't match directory name | Use underscores + exact dir name (e.g. `"luna_agent"`, not `"Luna Agent"`) |
| Eval runner reports 0 tests, no error | `test_cases:` key instead of `tests:` in tool test YAML | Rename top-level key to `tests:` |
| `KeyError: 'caller_id'` in callback | Missing `session_parameters` in eval YAML | Add `caller_id: "+15551234567"` to session_parameters |
| `CallbackContext` import error at runtime | You imported `CallbackContext` | Delete the import — sandbox auto-provides it |
| Audio eval consistently returns HTTP 400 | Placeholder GCS bucket in `loggingSettings` | Replace bucket name with a real GCS bucket |
| `TypeError: callback() takes 1 positional argument but 2 were given` | Wrong callback signature | See §6 — `before_agent` takes 1 param, `before_model`/`after_model` take 2 |
| Silence handling never triggers | Using `part.text` on audio parts (returns `None`) | Use `part.text_or_transcript()` — audio parts have transcript, not text |
| `end_session` called from callback but nothing happens | Platform ignores `end_session` from callbacks | Return a `Content` response instead; platform handles teardown |
| Push succeeds but calls fail silently | `deployed_app_id` is the full resource path | Set it to the short name only (e.g. `"night-line-app"`) |

## 10. Anti-Pattern Side-by-Side

### 10.1 CallbackContext Import

```python
# WRONG — import throws NameError at runtime in GECX sandbox
from gecx import CallbackContext

def before_agent_callback(callback_context: CallbackContext):
    ...

# RIGHT — sandbox auto-provides it; omit the import and type hint
def before_agent_callback(callback_context):
    ...
```

### 10.2 State Value Comparisons

```python
# WRONG — truthiness fails: "false" is a non-empty string, so it's truthy
if callback_context.state.get("_initialized"):
    return None  # always returns here, even on first turn

# RIGHT — string comparison
if callback_context.state.get("_initialized") == "true":
    return None
```

### 10.3 Tool Schema Key

```json
// WRONG — lint blocks push
{
  "name": "get_memory",
  "parameters": { "type": "object", "properties": { ... } }
}

// RIGHT
{
  "name": "get_memory",
  "inputSchema": { "type": "object", "properties": { ... } }
}
```

### 10.4 LlmResponse Construction

```python
# WRONG — fails at runtime
from gecx.types import Content, LlmResponse, Part
response = LlmResponse(content=Content(parts=[Part(text="Goodbye")]))

# RIGHT — use factory method
from gecx.types import LlmResponse
response = LlmResponse.from_parts(["Goodbye"])
```

### 10.5 childAgents Values

```json
// WRONG — push returns 400 Reference not found
{ "childAgents": ["Luna Agent", "Viktor Agent"] }

// RIGHT — directory names, underscores
{ "childAgents": ["luna_agent", "viktor_agent"] }
```

## 11. Multi-Persona Symmetry Rules

When a callback bug is fixed in one persona agent, it must be fixed in all three. When a new persona is added, it must implement the full callback contract.

**Required init callback outputs** (all three persona agents):

```python
callback_context.state["caller_profile"] = json.dumps(data)
callback_context.state["is_returning"] = "true" if data["call_count"] > 1 else "false"
callback_context.state["persona_id"] = "<persona>"
callback_context.state["_initialized"] = "true"
```

Missing `is_returning` means any downstream instruction or logic that checks it gets an empty string for that persona.

**Returning-caller threshold in instructions** — always `call_count > 1`, never `> 0`. The init callback increments `call_count` before the instruction reads it; a first-time caller always has `call_count = 1`.

**Consecutive user-role guard in inject_facts** — Gemini Live rejects two consecutive `role="user"` messages. Always use the guarded append:

```python
fact_part = Part.from_text(text=facts_text)
if llm_request.contents and llm_request.contents[-1].role == "user":
    llm_request.contents[-1].parts.append(fact_part)
else:
    llm_request.contents.append(Content(role="user", parts=[fact_part]))
```

**Eval copies vs production** (`evals/callback_tests/agents/` vs `cxas_app/NightLine/agents/`):

- Eval copies exist for the CXAS sim runner. Tests should import from `cxas_app/` via importlib, not from the eval copy.
- When production code changes, update the eval copy in the same PR or they silently diverge.
- CI currently imports from eval copies; any divergence means CI passes but production is broken.

**app.json session params** — every param with an empty default must be set by a callback. `caller_id` is the only exception (platform-injected by telephony). The CI `check_session_params.py` script enforces this.

**Sim eval caller IDs** — use distinct `caller_id` per persona test case. Shared IDs accumulate Firestore state across sequential runs, corrupting `call_count` and `is_returning` for subsequent tests.

## 12. First-Push Validation Checklist

After `cxas push` succeeds, verify the deployment is actually functional:

- [ ] `cxas lint --app-dir night-line/cxas_app/` passes with zero errors
- [ ] `cxas llm-lint --agent-dir night-line/cxas_app/NightLine/agents/root_agent/` (v1.5.0+; not available as CLI subcommand in v1.4.1)
- [ ] `gecx-config.json` `deployed_app_id` is set (short name, not full path)
- [ ] Place a test call via CES Console — verify greeting plays
- [ ] Check session logs: `caller_id` is populated (not empty string)
- [ ] Check Firestore: new caller document created with `call_count ≥ 1`
- [ ] Run one golden eval: `cxas eval run night-line/evals/goldens/welcome.yaml` — passes
- [ ] Run one sim eval: `cxas eval run night-line/evals/simulations/greeting_luna.yaml` — passes (≥ 80% semantic match for sims)

Common first-push failures and their causes are in §9 above.
