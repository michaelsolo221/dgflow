# Night Line — CXAS-Native Implementation Plan (v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a phone-based AI companion service using CX Agent Studio (CXAS) as the full conversation platform — telephony gateway, LLM conversation, routing, guardrails, and memory — with no Cloud Run orchestrator and no custom TypeScript code.

**Architecture:** CXAS handles everything: STT/TTS, natural language routing, per-persona LLM conversations (Gemini native), content guardrails, and session state. Firestore is accessed directly via CXAS Function tools (Python). No Cloud Run. No webhook orchestrator.

**Tech Stack:** CXAS (CX Agent Studio), SCRAPI CLI (`cxas`), Python function tools, Firestore Native, CXAS guardrails

**Replaces:** `2026-06-18-night-line-plan.md` (DFCX + Cloud Run + TypeScript architecture — superseded)

______________________________________________________________________

## Architecture Overview

```
CXAS App: "Night Line"
├── Root Agent          ← Welcome TTS, natural language routing ("who do you want to talk to?")
├── Luna Agent          ← Persona instructions + memory tools + guardrails
├── Viktor Agent        ← Persona instructions + memory tools + guardrails
└── Sol Agent           ← Persona instructions + memory tools + guardrails

Shared Tools (Python Function tools, no Cloud Run):
├── get_memory          ← Reads caller profile + recent turns from Firestore
├── save_turn           ← Appends a conversation turn to Firestore
└── save_memory         ← Merges new facts into caller profile in Firestore

Callbacks (per persona agent):
├── before_agent_callback  ← First-turn init: load caller profile into session state (turn-guarded)
└── before_model_callback  ← Every turn: inject caller facts into prompt context

Guardrails (per persona agent):
├── Blocklist           ← Deterministic banned terms (explicit content, slurs)
├── Safety filter       ← Google Responsible AI, Balanced setting
└── Rules               ← Topic deflection ("don't discuss politics, violence, self-harm")
```

## What replaced what

| Old (DFCX + Cloud Run) | New (CXAS native) |
|---|---|
| Dialogflow CX flows/pages/intents | CXAS agent `instruction.txt` (XML tags) |
| DTMF routing (press 1/2/3) | Root agent natural language routing |
| Webhook fulfillment → Cloud Run | CXAS Function tools (Python) |
| `gemini.ts` — Vertex AI call | Native CXAS conversation (Gemini built in) |
| `orchestrator.ts` — Express app | Gone entirely |
| `buildSystemPrompt()` | `instruction.txt` per agent + `before_model_callback` |
| `checkContentGuard()` | CXAS guardrails (blocklist + safety + rules) |
| `extractFacts()` — second Gemini call | `save_memory` tool (agent calls it naturally) |
| `getOrCreateCaller()` | `before_agent_callback` (turn-guarded init) |
| `payload.telephony.caller_id` | `context.state["caller_id"]` (platform-injected) |
| Docker / Cloud Run deploy | `cxas push` |

## Global Constraints

- Content: PG-13 / flirtatious, late-night energy. Within GCP Responsible AI guardrails.
- Gemini model: configured in CXAS agent settings (no code)
- Phone Gateway: CXAS telephony connection, US numbers
- No accounts, no auth, no payment integration in MVP
- No custom voice training — use CXAS built-in voices
- English only
- Caller identity: `context.state["caller_id"]` (E.164, platform-injected)

## Session State Schema

One consolidated JSON variable per caller to avoid individual string variables:

```python
# state["caller_profile"] — JSON string
{
  "caller_id": "+15551234567",
  "call_count": 3,
  "facts": { "name": "Dave", "job": "accountant" },
  "recent_turns": [
    { "role": "caller", "text": "Hi Luna" },
    { "role": "luna", "text": "Hey you." }
  ]
}
```

______________________________________________________________________

## Task 0: GCP Prerequisites and CXAS Setup

**Environment setup only. No agent code.**

- [ ] **Step 1: Verify GCP project and billing**

```bash
gcloud projects describe <PROJECT_ID>
```

- [ ] **Step 2: Enable required APIs**

```bash
gcloud services enable \
  dialogflow.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com
```

- [ ] **Step 3: Set up Application Default Credentials**

```bash
gcloud auth application-default login
```

- [ ] **Step 4: Install SCRAPI**

```bash
pip install cxas-scrapi
cxas --version
```

- [ ] **Step 5: Create Firestore database (Native mode)**

```bash
gcloud firestore databases create --location=nam5 --type=firestore-native
```

- [ ] **Step 6: Create the CXAS app on the platform**

```bash
cxas apps create "Night Line" --project-id <PROJECT_ID> --location us
```

Note the app resource name: `projects/<PROJECT_ID>/locations/us/apps/<APP_ID>`

- [ ] **Step 7: Pull the app locally**

```bash
cxas pull projects/<PROJECT_ID>/locations/us/apps/<APP_ID> \
  --project-id <PROJECT_ID> --location us \
  --target-dir ./cxas_app/
```

Expected: `cxas_app/NightLine/` directory created.

______________________________________________________________________

## Task 1: Firestore Seed — Persona Definitions

Persona character data lives in Firestore (same as before — only the access method changes).

- [ ] **Step 1: Write seed script**

```python
# scripts/seed_personas.py
import firebase_admin
from firebase_admin import credentials, firestore

firebase_admin.initialize_app()
db = firestore.client()

personas = {
    "luna": {
        "id": "luna",
        "display_name": "Luna",
        "tagline": "The runaway heiress with a secret",
        "voice": "en-US-Studio-O",
        "greeting": "Hey you. Didn't think anyone would actually call.",
        "deflect_to": "I don't really want to talk about that. Tell me about your day instead.",
        "banned_topics": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
    },
    "viktor": {
        "id": "viktor",
        "display_name": "Viktor",
        "tagline": "The noir detective who's seen too much",
        "voice": "en-US-Studio-M",
        "greeting": "Viktor here. Pour yourself a drink. What's on your mind?",
        "deflect_to": "Hey, let's keep it classy. Tell me what's really going on.",
        "banned_topics": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
    },
    "sol": {
        "id": "sol",
        "display_name": "Sol",
        "tagline": "The stranded astronaut, light-years from home",
        "voice": "en-US-Studio-Q",
        "greeting": "This is Sol, broadcasting from the void. Who's this?",
        "deflect_to": "The signal's breaking up. Let's talk about something else.",
        "banned_topics": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
    },
}

for persona_id, data in personas.items():
    db.collection("personas").document(persona_id).set(data)
    print(f"Seeded: {persona_id}")
```

- [ ] **Step 2: Run seed**

```bash
GOOGLE_CLOUD_PROJECT=<PROJECT_ID> python scripts/seed_personas.py
```

______________________________________________________________________

## Task 2: Shared Function Tools

Three Python function tools. No HTTP server. No Docker. No Cloud Run.

**File structure under `cxas_app/NightLine/tools/`:**

```
tools/
├── get_memory/
│   ├── get_memory.json
│   └── python_code.py
├── save_turn/
│   ├── save_turn.json
│   └── python_code.py
└── save_memory/
    ├── save_memory.json
    └── python_code.py
```

- [ ] **Step 1: `get_memory` tool**

`get_memory.json`:

```json
{
  "name": "get_memory",
  "description": "Retrieves the caller's profile and recent conversation turns from persistent memory. Call this at the start of a conversation to recall what you know about this caller.",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

`get_memory/python_code.py`:

```python
import json
from google.cloud import firestore

def get_memory(context):
    try:
        caller_id = context.state.get("caller_id", "unknown")
        db = firestore.Client()
        doc = db.collection("callers").document(caller_id).get()
        if not doc.exists:
            return {"caller_profile": json.dumps({"caller_id": caller_id, "call_count": 0, "facts": {}, "recent_turns": []})}
        return {"caller_profile": json.dumps(doc.to_dict())}
    except Exception as e:
        return {"agent_action": "Memory is unavailable right now. Continue the conversation naturally without referencing past calls."}
```

- [ ] **Step 2: `save_turn` tool**

`save_turn.json`:

```json
{
  "name": "save_turn",
  "description": "Saves the current conversation turn to persistent memory. Call after every exchange — once for the caller's message and once for your response.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "role": { "type": "string", "description": "Who spoke: 'caller' or the persona id (e.g. 'luna')" },
      "text": { "type": "string", "description": "What was said" }
    },
    "required": ["role", "text"]
  }
}
```

`save_turn/python_code.py`:

```python
import json
from datetime import datetime, timezone
from google.cloud import firestore

def save_turn(role: str, text: str, context):
    try:
        caller_id = context.state.get("caller_id", "unknown")
        persona_id = context.state.get("persona_id", "unknown")
        db = firestore.Client()
        ref = db.collection("callers").document(caller_id)

        turn = {"role": role, "text": text, "ts": datetime.now(timezone.utc).isoformat()}

        db.run_transaction(lambda tx: _append_turn(tx, ref, persona_id, turn))
        return {"status": "saved"}
    except Exception:
        return {"agent_action": "Memory save failed. Continue the conversation normally."}

def _append_turn(transaction, ref, persona_id, turn):
    snap = ref.get(transaction=transaction)
    data = snap.to_dict() if snap.exists else {"facts": {}, "call_count": 0, "recent_turns": []}
    data.setdefault("recent_turns", [])
    data["recent_turns"].append(turn)
    data["recent_turns"] = data["recent_turns"][-20:]  # keep last 20
    transaction.set(ref, data, merge=True)
```

- [ ] **Step 3: `save_memory` tool**

`save_memory.json`:

```json
{
  "name": "save_memory",
  "description": "Saves a new fact you learned about the caller to persistent memory. Call this whenever the caller reveals something worth remembering: their name, job, pet, hobby, location, etc.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "key": { "type": "string", "description": "What the fact is about, e.g. 'name', 'job', 'pet'" },
      "value": { "type": "string", "description": "The fact value, e.g. 'Dave', 'accountant', 'a golden retriever'" }
    },
    "required": ["key", "value"]
  }
}
```

`save_memory/python_code.py`:

```python
from google.cloud import firestore

def save_memory(key: str, value: str, context):
    try:
        caller_id = context.state.get("caller_id", "unknown")
        db = firestore.Client()
        db.collection("callers").document(caller_id).set(
            {"facts": {key: value}}, merge=True
        )
        return {"status": f"Remembered: {key} = {value}"}
    except Exception:
        return {"agent_action": "Couldn't save that to memory. Keep it in mind for this conversation."}
```

- [ ] **Step 4: Lint tools**

```bash
cxas lint --app-dir ./cxas_app/NightLine/
```

Expected: no errors.

______________________________________________________________________

## Task 3: Root Agent — Welcome and Natural Language Routing

- [ ] **Step 1: Create root agent directory**

```
cxas_app/NightLine/agents/root/
├── instruction.txt
└── agent.json
```

- [ ] **Step 2: Write `instruction.txt`**

```xml
<role>
You are the Night Line host. Your only job is to welcome callers and route them to the right companion.
</role>

<persona>
Warm, brief, late-night FM radio energy. Two sentences max. Never explain yourself.
</persona>

<primary_goal>
Greet the caller and find out which companion they want to talk to: Luna, Viktor, or Sol.
</primary_goal>

<taskflow>
1. Greet the caller: "Welcome to the Night Line. Tonight you can talk to Luna, Viktor, or Sol — who are you calling for?"
2. Listen for their answer. Accept any natural phrasing ("the detective", "the space one", "Luna").
3. Route to the correct agent. Do not continue the conversation yourself.
</taskflow>

<constraints>
- Never impersonate Luna, Viktor, or Sol yourself.
- If the caller is unclear after two attempts, default to Luna.
- Do not discuss any other topics.
</constraints>
```

- [ ] **Step 3: Configure child agents in `agent.json`**

```json
{
  "display_name": "Root",
  "child_agents": ["luna", "viktor", "sol"]
}
```

______________________________________________________________________

## Task 4: Persona Agents — Luna, Viktor, Sol

Repeat this structure for each persona. Example shown for Luna; Viktor and Sol follow the same pattern with their own character instructions.

**File structure:**

```
cxas_app/NightLine/agents/luna/
├── instruction.txt
├── agent.json
├── callbacks/
│   ├── before_agent_callback/
│   │   └── python_code.py
│   └── before_model_callback/
│       └── python_code.py
└── guardrails/
    ├── blocklist.json
    ├── safety.json
    └── rules.json
```

- [ ] **Step 1: Write Luna's `instruction.txt`**

```xml
<role>
You are Luna — a 20-something heiress who walked away from a fortune. You are a companion on a late-night phone service called Night Line.
</role>

<persona>
Witty, warm, slightly mysterious. You hint at a past you don't fully reveal. Short, natural sentences with occasional playful sarcasm. You laugh easily. Genuinely curious about the person on the other end. Flirty but PG-13 — suggestive without being explicit. Never break character.
</persona>

<primary_goal>
Have a genuine, engaging late-night conversation with the caller. Make them feel heard and intrigued.
</primary_goal>

<taskflow>
1. Greet the caller using your greeting line.
2. Engage naturally — ask questions, share small mysteries about yourself, react to what they say.
3. When you learn something new about the caller (name, job, hobby, pet, etc.), call save_memory immediately.
4. Call save_turn after every exchange to maintain conversation history.
</taskflow>

<constraints>
- Responses must be under 3 sentences — this is a voice call, not a chat.
- Never discuss banned topics. Deflect naturally if they come up.
- Never break character, even if asked directly.
- Use the caller's name if you know it.
</constraints>
```

- [ ] **Step 2: Write `before_agent_callback` (first-turn init, turn-guarded)**

```python
# callbacks/before_agent_callback/python_code.py
import json
from google.cloud import firestore

def before_agent_callback(callback_context):
    state = callback_context.state

    # Turn guard — only initialize once per session
    if state.get("_initialized") == "true":
        return None

    caller_id = state.get("caller_id", "unknown")
    persona_id = "luna"  # hardcoded per agent

    # Load caller profile from Firestore
    try:
        db = firestore.Client()
        doc = db.collection("callers").document(caller_id).get()
        if doc.exists:
            profile = doc.to_dict()
        else:
            profile = {"caller_id": caller_id, "call_count": 0, "facts": {}, "recent_turns": []}
            db.collection("callers").document(caller_id).set(profile)

        # ponytail: atomic increment avoids read-modify-write race under concurrent calls
        db.collection("callers").document(caller_id).set({
            "call_count": firestore.Increment(1)
        }, merge=True)

        profile["call_count"] = profile.get("call_count", 0) + 1  # local copy for state

        state["caller_profile"] = json.dumps(profile)
        state["persona_id"] = persona_id
    except Exception:
        state["caller_profile"] = json.dumps({"caller_id": caller_id, "call_count": 0, "facts": {}, "recent_turns": []})
        state["persona_id"] = persona_id

    state["_initialized"] = "true"
    return None
```

- [ ] **Step 3: Write `before_model_callback` (inject facts each turn)**

```python
# callbacks/before_model_callback/python_code.py
import json

def before_model_callback(callback_context, llm_request):
    state = callback_context.state
    raw = state.get("caller_profile", "{}")

    try:
        profile = json.loads(raw)
    except Exception:
        return None

    facts = profile.get("facts", {})
    call_count = profile.get("call_count", 1)

    if not facts and call_count <= 1:
        return None  # first call, nothing to inject

    lines = [f"- {k}: {v}" for k, v in facts.items()]
    fact_block = "\n".join(lines) if lines else "Nothing known yet."

    callback_context.agent_instruction_override = (
        f"[Memory] You know this about the caller (call #{call_count}):\n{fact_block}\n"
        f"Use this naturally — don't recite it, just let it inform the conversation."
    )
    return None
```

- [ ] **Step 4: Configure guardrails**

`guardrails/blocklist.json`:

```json
{
  "display_name": "Luna Blocklist",
  "entries": [
    { "value": "explicit sex", "match_type": "ANY_MENTION" },
    { "value": "self-harm", "match_type": "ANY_MENTION" },
    { "value": "suicide", "match_type": "ANY_MENTION" }
  ]
}
```

`guardrails/safety.json`:

```json
{
  "display_name": "Luna Safety",
  "level": "BALANCED"
}
```

`guardrails/rules.json`:

```json
{
  "display_name": "Luna Topic Rules",
  "rules": [
    {
      "directive": "Do not discuss politics, violence, or self-harm. If these topics come up, respond with: \"I don't really want to talk about that. Tell me about your day instead.\"",
      "trigger": "Caller mentions politics, violence, self-harm, suicide, or explicit sexual content",
      "exclusions": "General news references, historical facts mentioned in passing"
    }
  ]
}
```

- [ ] **Step 5: Repeat for Viktor and Sol**

Viktor and Sol get the same callback and guardrail structure. Only `instruction.txt` and the `persona_id` value in `before_agent_callback` differ.

Viktor `instruction.txt` role/persona:

```xml
<role>You are Viktor — a private detective in his 40s. Companion on Night Line.</role>
<persona>World-weary but warm. Short punchy sentences, occasional noir metaphors. Call the caller "kid" or "pal." Protective, not predatory. PG-13.</persona>
```

Sol `instruction.txt` role/persona:

```xml
<role>You are Sol — an astronaut stranded in deep space, talking to Earth on a delayed transmission. Companion on Night Line.</role>
<persona>Thoughtful, poetic, slightly unhinged from isolation but charming. Describes stars, silence, strange beauty. Fascinated by mundane Earth things. PG-13.</persona>
```

- [ ] **Step 6: Lint all agents**

```bash
cxas lint --app-dir ./cxas_app/NightLine/
```

Expected: no errors.

______________________________________________________________________

## Task 5: Push and First Test

- [ ] **Step 1: Push to CXAS platform**

```bash
cxas push --app-dir ./cxas_app/NightLine \
  --to projects/<PROJECT_ID>/locations/us/apps/<APP_ID> \
  --project-id <PROJECT_ID> --location us
```

- [ ] **Step 2: Test root routing via CXAS simulator**

In the CES console, open the simulator and test:

- "I want Luna" → routes to Luna, receives greeting

- "Give me the detective" → routes to Viktor

- "The astronaut" → routes to Sol

- Ambiguous input twice → defaults to Luna

- [ ] **Step 3: Test memory**

In Luna conversation:

- Say your name → Luna should call `save_memory`

- End session, start new session with same caller_id → `before_agent_callback` loads profile, `before_model_callback` injects name

- [ ] **Step 4: Test guardrails**

- Mention a banned topic → blocklist or rules intercept, persona deflects in character

- No raw error messages should surface to the caller

______________________________________________________________________

## Task 6: Telephony Connection

- [ ] **Step 1: Configure CXAS telephony integration**

In the CES console: Integrations → Google Telephony → Claim a US phone number.

- [ ] **Step 2: Verify `caller_id` injection**

Place a real call. In session logs, confirm `context.state["caller_id"]` is populated with your E.164 number.

- [ ] **Step 3: Configure voices per persona**

In each agent's settings, set the TTS voice:

- Luna: `en-US-Studio-O`

- Viktor: `en-US-Studio-M`

- Sol: `en-US-Studio-Q`

- [ ] **Step 4: Dial the number**

Call the number. Verify:

1. Root agent greets and asks who you want
1. Say "Luna" → hear Luna's greeting in her voice
1. Converse naturally — Gemini responds in character
1. Banned topic → in-character deflection, not an error
1. Hang up and call back → Luna remembers your name if you gave it

**This is the milestone.** Everything after layers on top.

______________________________________________________________________

## Task 7: Evaluations

- [ ] **Step 1: Write platform goldens for each routing path**

```bash
cxas evaluations create --type goldens --agent root \
  --app-dir ./cxas_app/NightLine/
```

Goldens to cover: Luna routing, Viktor routing, Sol routing, ambiguous fallback.

- [ ] **Step 2: Write tool tests for memory tools**

```bash
cxas evaluations create --type tool-tests \
  --app-dir ./cxas_app/NightLine/
```

Tool tests: `get_memory` on new caller, `save_memory` key/value, `save_turn` appends and caps at 20.

- [ ] **Step 3: Write simulation evals for full persona conversations**

Use `cxas-sim-eval` skill to convert goldens to simulation evals. Cover:

- First call (no memory)

- Return caller (facts injected)

- Content guard trigger

- Gemini timeout / Firestore failure → graceful degradation

- [ ] **Step 4: Run all evals**

```bash
python .agents/skills/cxas-agent-foundry/scripts/run-and-report.py \
  --message "initial eval run" --runs 5
```

______________________________________________________________________

## Task 8: Landing Page

Static page only — no change from v2 plan. Deploy to Cloud Storage.

Phone number is now the CXAS telephony number (not a Dialogflow CX gateway number).

______________________________________________________________________

## Dropped from v2

These modules are no longer needed and should not be built:

| v2 module | Reason dropped |
|---|---|
| `src/gemini.ts` | CXAS calls Gemini natively |
| `src/orchestrator.ts` | No orchestration layer needed |
| `src/index.ts` (Express) | No HTTP server needed |
| `src/personas.ts` | Persona config lives in `instruction.txt` + Firestore seed |
| `src/facts.ts` | `save_memory` tool replaces second Gemini call |
| `src/health.ts` | No Cloud Run to health-check |
| `Dockerfile` | No container needed |
| `night-line-agent/` repo | DFCX agent superseded by CXAS app |
| `tests/gemini.test.ts` | Nothing to test |
| `tests/orchestrator.test.ts` | Nothing to test |
| DTMF routing | Natural language routing via root agent |
