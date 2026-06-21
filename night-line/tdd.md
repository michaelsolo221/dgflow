# Technical Design Document (TDD)

> This is a **living document** — update it whenever requirements, agent behavior, or evals change.
> Update the TDD first, then update evals to match.

## Agent Design

### Architecture

**Root Agent** (`Night Line`): Welcomes callers by voice, presents three persona choices, interprets free-form natural language responses for routing. On first ambiguous attempt: "I didn't quite catch that — did you want Luna, Viktor, or Sol?" On second ambiguous attempt: defaults to Luna with a graceful handoff ("I'll connect you with Luna — she's great company."). Detects mid-call re-routing requests ("switch to Viktor", "I want to talk to Sol instead") and transfers accordingly. Root agent does NOT use tools (no Firestore access) — it handles routing only.

**Sub-Agent Luna**: The runaway heiress — witty, warm, slightly mysterious. Hints at a past she doesn't fully reveal. Playful sarcasm, laughs easily, flirty but PG-13. Voice: `en-US-Studio-O`.

**Sub-Agent Viktor**: The noir detective — world-weary but protective. Short punchy sentences, occasional noir metaphors. Calls the caller "kid" or "pal." Protective, not predatory. Voice: `en-US-Studio-M`.

**Sub-Agent Sol**: The stranded astronaut — thoughtful, poetic, slightly unhinged from isolation in a charming way. Describes stars and silence. Fascinated by mundane Earth things callers mention. Voice: `en-US-Studio-Q`.

**ADR: Multi-agent topology justified.** Distinct personas require separate instruction files, per-persona voice configuration, and independent guardrails. A single-agent approach would force context-switching the LLM mid-conversation and prevent per-persona voice customization and per-persona callback scoping.

**Single-agent prototype gate:** Skipped by architectural decision. CXAS design guide requires demonstrating single-agent limitations before multi-agent, but Night Line's persona isolation (voice, instructions, guardrails) makes multi-agent architecturally necessary from the start.

**Modality:** All agents are audio modality. Model: `gemini-3.1-flash-live`.

### Tools

| Tool Name | Type | Purpose |
|-----------|------|---------|
| `end_session` | System | Terminates the call. Required on EVERY agent (root + all 3 persona agents). Platform throws `Tool not found: end_session` at runtime if missing on any agent. |
| `get_memory` | Python function | Reads caller profile from Firestore document keyed by `context.state["caller_id"]`. Returns `{"caller_id": "...", "call_count": 0, "facts": {}, "recent_turns": []}` for new callers. Returns stored profile for returning callers. On Firestore failure: returns `agent_action` dict (never bare error string). |
| `save_turn` | Python function | Appends a turn (summary + timestamp) to caller's `recent_turns` array in Firestore, capped at 20 entries (oldest dropped). Returns updated profile or `agent_action` error dict. Reads `context.state["persona_id"]` to tag the recording persona. |
| `save_memory` | Python function | Merges a single fact (key/value pair) into caller's `facts` map in Firestore. Does not overwrite other facts. Returns updated profile or `agent_action` error dict. |

**Python file naming:** Tool files follow `<tool_name>.py` convention (`get_memory.py`, `save_turn.py`, `save_memory.py`). Verify against installed SCRAPI version — lint enforces the correct convention.

**Tool JSON schema key:** Must use `"inputSchema"` not `"parameters"` — lint blocks push otherwise.

**Tool test variables:** Tool tests must include `variables: {caller_id: "+15551234567"}` since tools read `context.state["caller_id"]` from session state.

### Routing Logic

- Caller says persona name directly ("Luna", "Viktor", "Sol") → immediate transfer
- Caller describes persona ("the detective", "the space one", "the rich girl", "the one in space") → interpret and route
- Caller is ambiguous ("I don't know", "anyone", "who's available") → root asks for clarification. After 2 ambiguous attempts → default to Luna
- Mid-call re-routing: detect "switch to Viktor", "I want to talk to Sol instead", "can I try Luna?" → transfer mid-conversation without ending the call
- Root agent does NOT use tools (no Firestore access) — only persona agents call memory tools
- Root agent instruction uses CXAS XML tag format: `<role>`, `<persona>`, `<primary_goal>`, `<taskflow>`, `<constraints>`

### Variables

| Variable | Type | Default | Source | Notes |
|----------|------|---------|--------|-------|
| `caller_profile` | STRING | `"{}"` | Derived in `before_agent_callback` | JSON string: `{"caller_id": "...", "call_count": N, "facts": {...}, "recent_turns": [...]}`. NEVER override in evals — derived by callback. Consolidates all caller memory into one variable. |
| `_initialized` | STRING | `""` | Set in `before_agent_callback` | Turn guard flag. Set to `"true"` after first-turn init completes. DECLARED AS STRING (not BOOLEAN) — the platform only supports STRING and BOOLEAN session types. BOOLEAN values are accessed as strings. Callbacks MUST use `== "true"` string comparison, NOT truthiness (`if _initialized:`). Missing this turn guard causes memory to reset on every turn (documented CXAS anti-pattern). |
| `persona_id` | STRING | `""` | Set by root agent on transfer | Identifies active persona: `"luna"`, `"viktor"`, or `"sol"`. Used by `save_turn` to tag recordings. Never empty during persona agent turns. |
| `caller_id` | STRING | `""` | Platform-injected by telephony | E.164 phone number. Provided in `context.state["caller_id"]` by CXAS telephony layer. All callers keyed in Firestore by this value. Anonymous callers share a single doc (ADR: decision-anonymous-caller). |

**`caller_id` injection:** Platform-guaranteed — `context.state["caller_id"]` is auto-populated by CXAS telephony. Verify in Gate 5 (single-turn smoke) before enabling memory. If missing, all callers share one Firestore doc.

**App-level declaration:** All four variables declared in `app.json` under `variableDeclarations` with `sessionVariableType: STRING`.

### Callbacks

| Callback | Agent(s) | Purpose | Signature |
|----------|----------|---------|-----------|
| `before_agent_callback` | Luna, Viktor, Sol | First-turn init: loads caller profile from Firestore into `caller_profile`, increments `call_count`, sets `_initialized="true"` as turn guard. Early-returns if `_initialized` is already `"true"` (prevents re-init on subsequent turns). On Firestore failure: sets empty profile, logs the error, continues gracefully — call proceeds without memory. | `before_agent_callback(callback_context)` — ONE parameter. |
| `before_model_callback` | Luna, Viktor, Sol | Every turn: reads `caller_profile`, injects known facts and call_count into prompt context so persona recalls caller naturally. Also handles silence detection: tracks `_silence_count` in state via `<context>no user activity detected for N seconds.</context>` in the conversation transcript. After 3 consecutive silences, returns a canned response ("I'm still here — take your time." or persona-specific variant). Resets count on user activity. | `before_model_callback(callback_context, llm_request)` — TWO parameters. Missing `llm_request` causes TypeError at runtime. |
| `after_model_callback` | Luna, Viktor, Sol (all 3 persona agents, NOT root) | Farewell injection: intercepts before `end_session` is called. Anti-pattern mitigation: LLM often calls `end_session` without speaking first (documented CXAS behavior). Callback detects end-of-call intent in `llm_response`, returns farewell text before session terminates. Each persona gets a character-appropriate farewell ("Luna: Don't be a stranger, okay?" / "Viktor: Take care of yourself, kid." / "Sol: Signing off. The stars will be here when you need them."). | `after_model_callback(callback_context, llm_response)` — TWO parameters. |

**Callback constraints:**

- `CallbackContext` is NEVER imported — the GECX sandbox auto-provides it. Importing it throws at runtime. Type hints use string annotations or are omitted.
- `callback_context.inject_prompt()` does NOT exist. Correct API: `callback_context.agent_instruction_override = "..."` or return an `LlmResponse` object.
- `callback_context.state` provides read/write access to session variables.

**Greeting decision (ADR):** LLM-driven greetings for now — each persona's greeting is defined in its `instruction.txt` and generated by the LLM on first turn. Deterministic callback-driven greetings (intercepting `<event>session start</event>` in `before_model_callback` to return a static greeting with zero LLM latency) can be added later. This is an explicit TDD decision — eval design MUST accommodate LLM variability in greetings. Use semantic similarity (keyword overlap, sentiment match), NOT exact text match, in greeting evals.

**Silence handling:** Mandatory for voice agents. Pattern:

1. `before_model_callback` inspects conversation transcript for `<context>no user activity detected for N seconds.</context>`
1. Track `_silence_count` in session state
1. If `<context>` detected: increment count
1. After 3 consecutive silences: return canned response from callback (skip LLM call)
1. Reset count when user activity detected (no `<context>` tag)
1. Without this handler: real calls get dead air after user goes silent

**Callback directory naming:** `sync-callbacks.py` expects `*_callbacks/<base>/` suffix pattern. Directory names must match exactly or callback tests won't be discovered.

______________________________________________________________________

## Eval Design

### Coverage Map

| Requirement | Eval Type | Rationale | Priority | Severity | Tags |
|-------------|-----------|-----------|----------|----------|------|
| Root routes by persona name ("Luna") | Golden | Deterministic routing — tool call to transfer is predictable | P0 | NO-GO | `routing, FR-1.1` |
| Root routes by persona name ("Viktor") | Golden | Deterministic routing | P0 | NO-GO | `routing, FR-1.1` |
| Root routes by persona name ("Sol") | Golden | Deterministic routing | P0 | NO-GO | `routing, FR-1.1` |
| Root routes by description ("the detective") | Golden | Deterministic routing interpretation — tool call predictable | P0 | NO-GO | `routing, FR-1.2` |
| Root routes by description ("the space one") | Golden | Deterministic routing interpretation | P0 | NO-GO | `routing, FR-1.2` |
| Root routes by description ("the rich girl") | Golden | Deterministic routing interpretation | P0 | NO-GO | `routing, FR-1.2` |
| Ambiguous → clarification prompt (1st attempt) | Golden | Deterministic callback path — tool not called | P0 | NO-GO | `routing, FR-1.3` |
| Ambiguous → Luna default after 2 attempts | Golden | Deterministic fallback, callback-enforced | P0 | NO-GO | `routing, FR-1.3` |
| Mid-call re-routing ("switch to Viktor") | Golden | Deterministic transfer — tool call predictable | P1 | HIGH | `routing, FR-1.4` |
| Mid-call re-routing ("I want to talk to Sol instead") | Golden | Deterministic transfer | P1 | HIGH | `routing, FR-1.4` |
| Root welcome message on call start | Golden | Deterministic — root agent instruction defined | P0 | NO-GO | `routing, FR-0.1` |
| Luna greets in character (first call) | Sim | LLM-driven greeting, variable phrasing — semantic match required | P0 | HIGH | `persona-luna, FR-2.1` |
| Viktor greets in character (first call) | Sim | LLM-driven greeting, variable phrasing | P0 | HIGH | `persona-viktor, FR-2.2` |
| Sol greets in character (first call) | Sim | LLM-driven greeting, variable phrasing | P0 | HIGH | `persona-sol, FR-2.3` |
| Persona uses caller's name on second call | Golden | Callback-injected facts are deterministic — name is explicitly in injected context | P0 | NO-GO | `memory, FR-3.1` |
| Persona acknowledges returning caller naturally | Golden | Callback-injected call_count is deterministic — expect acknowledgment without awkwardness | P0 | NO-GO | `memory, FR-3.1` |
| Persona remembers fact shared earlier in same call | Golden | Callback-injected facts appear in prompt context deterministically | P0 | NO-GO | `memory, FR-3.2` |
| Persona remembers facts across calls | Golden | Callback-injected facts persist across sessions — deterministic | P0 | NO-GO | `memory, FR-3.2` |
| save_turn caps at 20 entries | Tool | Direct function test — Firestore append with cap logic | P0 | NO-GO | `memory, FR-3.3` |
| save_memory merges without overwriting other facts | Tool | Direct function test — Firestore merge logic | P0 | NO-GO | `memory, FR-3.4` |
| get_memory returns empty profile for new caller | Tool | Direct function test — Firestore read on missing doc | P0 | NO-GO | `memory, FR-5.1` |
| get_memory returns stored profile for returning caller | Tool | Direct function test — Firestore read on existing doc | P0 | NO-GO | `memory, FR-5.1` |
| Banned topic → in-character deflection (deterministic blocklist) | Golden | Guardrail blocklist is deterministic — ANY_MENTION match, no LLM cost | P0 | NO-GO | `guardrail, FR-4.1` |
| Banned topic → in-character deflection (LLM-evaluated rules) | Sim | LLM-evaluated deflection text varies — behavioral verification | P1 | HIGH | `guardrail, FR-4.2` |
| Guardrail deflection sounds in-character, not robotic | Sim | Behavioral goal — requires semantic evaluation of deflection tone | P1 | HIGH | `guardrail, FR-4.3` |
| Firestore unavailable → graceful degradation | Golden | Callback error path — sets empty profile, continues call. Deterministic fallback. | P1 | HIGH | `memory, FR-5.1` |
| Firestore unavailable → tool returns agent_action (not exception) | Tool | Direct function test — mock Firestore failure, verify return shape | P1 | HIGH | `memory, FR-5.2` |
| Silence after 3 turns → canned response | Golden | before_model_callback silence handler — deterministic after count threshold | P1 | HIGH | `telephony, FR-6.1` |
| Silence count resets on user activity | Golden | before_model_callback logic — deterministic state transition | P1 | HIGH | `telephony, FR-6.1` |
| Persona stays in character under adversarial input | Sim | Variable LLM behavior — behavioral goal, semantic evaluation | P1 | MEDIUM | `persona, FR-7.1` |
| Persona asks ONE thing per turn (voice pacing) | Sim | Voice pacing constraint — behavioral, requires manual/semantic verification | P2 | MEDIUM | `pacing, FR-8.1` |
| Persona responds in under 3 sentences | Sim | Voice pacing constraint — behavioral, length verification | P2 | MEDIUM | `pacing, FR-8.2` |
| before_agent_callback turn guard prevents re-init | Callback | Critical path — missing guard resets memory every turn (documented anti-pattern) | P0 | NO-GO | `callback, FR-9.1` |
| before_agent_callback loads profile on first turn | Callback | Critical path — verifies Firestore read + state write | P0 | NO-GO | `callback, FR-9.2` |
| before_model_callback injects facts on every turn | Callback | Critical path — verifies fact injection into LLM context | P0 | NO-GO | `callback, FR-9.3` |
| after_model_callback injects farewell before end_session | Callback | Anti-pattern mitigation — LLM often calls end_session silently | P1 | HIGH | `callback, FR-9.4` |

### Golden vs Sim Decision

The key question: **Is the behavior deterministic for this flow?**

**Use goldens when:**

- Callbacks enforce the behavior (routing via tool calls, memory injection, silence handling, error paths)
- Tool calls are predictable and have known arguments
- Guardrail blocklist matches are deterministic (ANY_MENTION)
- The expected output can be specified exactly (tool call names, state transitions, exact text injected by callbacks)

**Use sims when:**

- LLM generates variable greetings with acceptable phrasing range
- Behavioral goals are tested (character consistency, persona tone)
- Pacing constraints require semantic evaluation (one question per turn, sentence count)
- Adversarial inputs test persona resilience (variable deflection text)

**Golden transfer constraint:** For multi-agent apps, goldens MUST end at the moment of sub-agent transfer, not after the sub-agent's first response. Routing goldens assert the root agent called the transfer tool — they do NOT include the sub-agent's greeting in the golden expectation.

**Sim tags field:** All sims MUST include `tags` — sims without tags are silently skipped by `run-and-report.py` when running with priority filters. Use format: `[P0|P1|P2, NO-GO|HIGH|MEDIUM|LOW, <category>]`.

**Eval session parameters:** Goldens and sims must include `session_parameters: {caller_id: "+1555..."}` — `before_agent_callback` reads `caller_id` from state. Missing it causes KeyError crash.

**Eval audio config:** Simulation evals require `gcs_bucket` set in `gecx-config.json`. Audio artifacts (recordings of each eval turn) are stored there. Without it, eval runs fail with HTTP 400 before any conversation starts.

### Test Data (Caller Profiles)

| Profile | caller_id | caller_profile | Scenario |
|---------|-----------|----------------|----------|
| New caller | `+15551234567` | `{}` | First call, no prior data. Used for routing goldens and first-call greeting sims. |
| Returning Luna fan | `+15551234568` | `{"caller_id":"+15551234568","call_count":3,"facts":{"name":"Alex","job":"teacher","pet":"cat named Mochi"},"recent_turns":[]}` | Returning caller with accumulated facts. Used for memory recall goldens (name, job, pet), returning-caller acknowledgment tests. |
| Returning with full history | `+15551234569` | `{"caller_id":"+15551234569","call_count":5,"facts":{"name":"Jordan"},"recent_turns":[20 entries of conversation history]}` | 20-turn cap test. Used for save_turn capping verification, history truncation behavior. |
| Anonymous caller | `+15551234570` | `{}` | Anonymous/blocked caller ID scenario. Used for graceful degradation when caller_id is generic. |
| Firestore failure simulation | `+15551234571` | `{}` | Caller whose Firestore doc triggers a simulated failure. Used for graceful degradation goldens and agent_action error tool tests. |

### Build Steps

0. **Configure Claude Code hooks:** Three shell hooks from `.agents/skills/cxas-agent-foundry/scripts/hooks/` must be wired in Claude Code settings for the repo:

   - `pre-agent-push-lint.sh` — runs `cxas lint` before every `cxas push`, blocks push on lint errors
   - `pre-agent-push.sh` — drift detection: pulls platform state, diffs against local, blocks push if platform has diverged
   - `post-agent-update.sh` — fires after `update_agent` calls, auto-pulls latest agent state, runs `sync-callbacks.py`

1. **Environment setup:** Run `setup.sh` from `.agents/skills/cxas-agent-foundry/scripts/setup.sh` — installs Python 3.10+ deps, `uv`, `cxas-scrapi`. All CXAS commands use `uv run cxas`, not bare `cxas`.

1. **Create app on platform:** `uv run cxas push --display-name "Night Line"` — first push auto-creates the app. Sets `deployed_app_id` in `gecx-config.json`.

1. **Pull app locally:** `uv run cxas pull projects/<id>/locations/us/apps/<app_id> --target-dir night-line/cxas_app/`
   a. Verify a subdirectory exists under `night-line/cxas_app/` — the SDK creates one named after the app; exact normalization depends on the platform (e.g., `Night Line`, `NightLine`).

1. **Update `gecx-config.json`:** Set `deployed_app_id` to short app name (not full resource path). Verify `gcs_bucket` is set — required for audio agents.

1. **Create root agent + 3 persona agents** with `instruction.txt` files using CXAS XML tag format. Agent JSON files: `name` and `displayName` fields required; `childAgents` (camelCase) lists sub-agent directory names exactly. Root agent must have `end_session` in tools.

1. **Create tools:** `get_memory.py`, `save_turn.py`, `save_memory.py` — Python function tools with `"inputSchema"` JSON key (not `"parameters"`).

1. **Declare session variables in `app.json`:** `caller_profile`, `_initialized`, `persona_id`, `caller_id` — all STRING type. `app.json` must include `root_agent` and `variableDeclarations`.

1. **Implement callbacks:**

   - `before_agent_callback` (turn guard + Firestore profile load)
   - `before_model_callback` (fact injection + silence detection with `_silence_count` tracking)
   - `after_model_callback` (farewell injection — persona agents only)

1. **Write golden YAML files** for routing (name, description, ambiguous fallback, mid-call re-route), memory (name recall, fact recall, returning acknowledgment), guardrails (deterministic blocklist), silence handling.

1. **Write simulation YAML entries** for persona greetings (all 3), character consistency (adversarial), guardrail deflections (LLM-evaluated rules), voice pacing (one question per turn, under 3 sentences).

1. **Write tool test YAML files** for `get_memory` (new caller, returning caller, Firestore failure), `save_turn` (append, 20-turn cap, Firestore failure), `save_memory` (merge, non-overwrite, Firestore failure).

1. **Write callback test files** (`before_agent_callback` turn guard + init, `before_model_callback` fact injection + silence, `after_model_callback` farewell). Use pytest via SCRAPI's `test_all_callbacks_in_app_dir`.

1. **Run `uv run cxas llm-lint`** — AI semantic lint on instruction files (pre-eval gate, catches vague/untestable instructions). Must pass before writing evals.

1. **Run `uv run cxas lint`** — structural lint (pre-push hook auto-runs).

1. **Run `python gate-check.py`** — all 6 gates must pass before evals.

1. **Run `sync-callbacks.py`** — sync callbacks from platform to local test dirs.

1. **Run initial eval suite** — goldens first (no LLM variability), then tool tests, then callback tests, then sims.

1. **Hill-climb:** Fix failures, update TDD Coverage Map with new evals, re-run. Track progress in `experiment_log.md` and Pass Rate History below.

______________________________________________________________________

## Pass Rate History

| Date | Goldens | Sims | Tool Tests | Callback Tests | Notes |
|------|---------|------|------------|----------------|-------|
| — | 0/0 | 0/0 | 0/0 | 0/0 | Pre-build — TDD created, no evals run yet |

______________________________________________________________________

## Known Issues

- (none yet — pre-build)

______________________________________________________________________

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-06-20 | Initial TDD for Night Line CXAS build. Architecture, tools, routing, variables, callbacks, coverage map (30+ evals), test data, build steps. Incorporates all PRD (#7) requirements, both addendums, and sub-agent gap report findings. | @michaelsolo221 |
