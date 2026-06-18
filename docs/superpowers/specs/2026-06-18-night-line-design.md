# Night Line — Design Spec

**Date:** 2026-06-18
**Status:** Design approved, pending implementation plan

## Overview

A phone-based AI companion service — a modern recreation of late-night TV "chat line" ads where callers dial a number, choose a persona, and talk to an LLM-powered companion. Built on Dialogflow CX for telephony, with a custom orchestrator backend for persona management and memory.

Three layers: nostalgia play (retro 90s aesthetic), conceptual art (AI companionship commentary), sincere product (genuinely compelling conversations).

## Creative Constraints

- **Content:** PG-13 / flirtatious, late-night energy. Stays within GCP Responsible AI guardrails. Can evolve to risqué later.
- **Personas:** Multiple distinct characters (menu-selectable) with cross-call memory. Each remembers the caller between calls.
- **Scope:** Portfolio-grade MVP. Polished enough for a resume, not production billing.

## System Architecture

```
Caller dials (XXX) XXX-XXXX
        │
        ▼
┌─────────────────────────────┐
│   Dialogflow CX              │
│   ┌───────────────────────┐ │
│   │ Phone Gateway          │ │  STT → text
│   │ Conversation Profile   │ │  TTS ← text (WaveNet)
│   └───────────┬───────────┘ │
│               │              │
│   ┌───────────▼───────────┐ │
│   │ CX Flow (deterministic)│ │  DTMF menu, persona routing
│   │  "Press 1 for Luna…"  │ │
│   └───────────┬───────────┘ │
│               │              │
│   ┌───────────▼───────────┐ │
│   │ Webhook fulfillment    │─┼──► POST /converse
│   │ (converse page loop)   │ │    { payload.telephony.caller_id,
│   └───────────────────────┘ │      sessionInfo.parameters.persona,
└─────────────────────────────┘      transcript }

               │
               ▼
┌──────────────────────────────┐
│  Orchestrator (Cloud Run)     │
│  ┌──────────────────────────┐ │
│  │ POST /converse            │ │  receives call turn
│  │   → load caller + persona │ │  from Firestore
│  │   → build prompt (system  │ │
│  │     + history + utterance)│ │
│  │   → Gemini 3.1 Flash-Lite │ │  via Vertex AI
│  │   → save turn to Firestore│ │
│  │   → return response text  │ │  in WebhookResponse format
│  └──────────┬───────────────┘ │
│             │                 │
│  ┌──────────▼───────────────┐ │
│  │ Firestore (Native)         │ │
│  │   callers/{phone_e164}    │ │  caller profile + persona history
│  │   personas/{id}           │ │  persona definitions
│  └──────────────────────────┘ │
└──────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Landing Page (static site)   │
│  Cloud Storage + CDN          │
│  Retro aesthetic, persona     │
│  showcase, phone number       │
└──────────────────────────────┘
```

### Boundaries

- **Dialogflow CX** owns: phone number, STT, TTS, DTMF menu routing. Never touches LLM logic or persistent memory.
- **Orchestrator** owns: persona prompts, conversation history, LLM calls, caller identity, content filtering. Never touches audio.
- **Firestore** owns: persistent state (callers, personas, logs).
- **Landing page** is read-only marketing. No auth, no accounts, no backend.

### Key architectural decisions

- **Caller identity = phone number** (via `payload.telephony.caller_id`, E.164 format). No signup. Anonymous by default, persistent by caller ID. Requires Dialogflow CX Essentials Edition (not Trial).
- **One webhook endpoint** (`POST /converse`). All turns flow through it. Persona switching is a session parameter.
- **Gemini 3.1 Flash-Lite** as LLM. GA since 2026-05-07. 1M token context window. Standard `generateContent` API via Vertex AI. Designed for high-throughput, low-latency text generation. Deployed in `us-central1`.
- **Webhook auth** via ID Token (same GCP project — no API keys to manage).
- **No custom voice import** — use Google WaveNet/Neural voices per persona for distinctiveness.

## Call Flow

```
CALLER DIALS
    │
    ▼
WELCOME PAGE (CX Flow, static TTS)
    "Welcome to the Night Line. Pick your companion.
     Press 1 for Luna, the runaway heiress…
     Press 2 for Viktor, the noir detective…
     Press 3 for Sol, the stranded astronaut…"
    │
    ▼ DTMF input
ROUTE TO PERSONA PAGE (CX Flow)
    Sets session param: persona = "luna"
    │
    ▼ Entry fulfillment: webhook
PERSONA GREETING (from Firestore persona doc)
    Luna: "Hey you. Didn't think anyone would actually call."
    │ transition
    ▼
CONVERSE PAGE ─────────────────────────┐
    │                                   │
    │ event handlers:                   │
    │   sys.no-match-default            │  ← every open-ended utterance
    │     → webhook POST /converse      │
    │   sys.no-input-default            │  ← silence
    │     → TTS "Still with me?"        │
    │     → counter ×2, then goodbye    │
    │   sys.webhook.failed              │  ← timeout
    │     → TTS "Hmm, lost my train     │
    │        of thought. Say again?"    │
    │                                   │
    │ route: "goodbye" intent           │
    │   → Goodbye Page (end call)       │
    │                                   │
    └───────────────────────────────────┘
    LOOP indefinitely until caller hangs up
```

### Webhook request (inbound to orchestrator)

```json
{
  "detectIntentResponseId": "...",
  "sessionInfo": {
    "session": "projects/.../sessions/...",
    "parameters": {
      "persona": "luna",
      "caller_id": "+15551234567"
    }
  },
  "pageInfo": { "currentPage": "converse" },
  "fulfillmentInfo": { "tag": "converse" },
  "payload": {
    "telephony": { "caller_id": "+15551234567" }
  },
  "intentInfo": {
    "lastMatchedIntent": "...",
    "parameters": {},
    "transcript": "So what's your story, Luna?"
  }
}
```

### Webhook response (returned to CX)

```json
{
  "fulfillmentResponse": {
    "messages": [
      { "text": { "text": ["My story? Baby, we'd be here all night. But I'll give you the short version…"] } }
    ]
  },
  "sessionInfo": {
    "parameters": {
      "turn_count": 5,
      "persona": "luna"
    }
  }
}
```

## Persona System

Personas are data, not code. Adding a new persona = Firestore write + CX flow DTMF route.

### Firestore: `personas/{id}`

```typescript
{
  id: "luna",
  display_name: "Luna",
  tagline: "The runaway heiress with a secret",
  voice: "en-US-Studio-O",           // Google WaveNet voice
  system_prompt: string,              // identity, backstory, speech patterns
  greeting: "Hey you. Didn't think anyone would actually call.",
  content_guard: {
    banned: ["politics", "violence", "self-harm"],
    deflect_to: "I don't really want to talk about that. Tell me about your day instead."
  }
}
```

- Voice selection per persona — each gets a distinct WaveNet voice.
- Content guard per persona — each defines its own boundaries.
- System prompt contains full persona: identity, backstory, personality traits, speech quirks, relationship stance.

## Memory Model

### Firestore: `callers/{phone_e164}`

```typescript
{
  phone: "+15551234567",
  first_call: Timestamp,
  last_call: Timestamp,
  personas: {
    "luna": {
      call_count: 6,
      last_call: Timestamp,
      turns: [
        { role: "luna", text: "Hey you…", ts: Timestamp },
        { role: "caller", text: "So what's your story?", ts: Timestamp },
        // ...
      ],
      facts: {
        "name": "Dave",
        "job": "accountant",
        "pet": "a cat named Chairman Meow"
      }
    },
    "viktor": { /* separate log, no cross-contamination */ }
  }
}
```

### Memory rules

- **Caller identity = phone number.** No accounts, no passwords. "Call the number, you're recognized."
- **Per-persona isolation.** Talking to Luna never references things Viktor said. Each relationship is independent.
- **Facts over raw dump.** Relationship state is curated key-value facts extracted from conversations. Included in the system prompt as "What you know about this person."
- **Sliding history window.** Last 20 turns go into the LLM prompt. Older turns remain in Firestore (retrievable later via summarization or on-demand).
- **Cross-call continuity.** Dave calls back next week → Luna remembers his name, job, cat.

## Orchestrator Design

### Stack

- **Runtime:** TypeScript + Express on Cloud Run
- **LLM:** Gemini 3.1 Flash-Lite via Vertex AI SDK (`@google-cloud/vertexai`)
- **Database:** Firestore Native mode (`@google-cloud/firestore`)
- **Deployment:** Cloud Run, `us-central1`, `--min-instances=1`, `--cpu-boost`

### POST /converse pseudocode

```
1.  Parse WebhookRequest JSON
2.  Extract: caller_id (payload.telephony.caller_id)
              persona_id (sessionInfo.parameters.persona)
              transcript (intentInfo / text field)
3.  Parallel Firestore loads:
      callers/{caller_id}
      personas/{persona_id}
4.  If new caller → create caller doc
    If new persona for caller → initialize persona subdoc
5.  Content guard check:
      if transcript matches banned topics → return deflection
6.  Build LLM prompt:
      system:  persona.system_prompt
               + "You know this about the caller:" + facts
               + persona.content_guard instructions
      history: last 20 turns from persona.turns
      user:    transcript
7.  Vertex AI generateContent({
      model: "gemini-3.1-flash-lite",
      contents: [...history, { role: "user", parts: [{ text: transcript }] }],
      systemInstruction: system_prompt,
      generationConfig: { temperature: 0.9, maxOutputTokens: 256 }
    })
    Timeout: 25s (under CX's 30s max webhook timeout)
8.  Extract basic facts from response (name, job, etc.) → update persona.facts
9.  Append turn to persona.turns
10. Return WebhookResponse JSON with outputAudioText
```

### Latency budget

| Step | Target |
|---|---|
| STT (Dialogflow) | streaming, hidden |
| Webhook network (CX → Cloud Run) | <50ms (same region) |
| Firestore reads (parallel) | <100ms |
| Gemini 3.1 Flash-Lite | ~600ms TTFB |
| Firestore writes | <50ms |
| Webhook network (Cloud Run → CX) | <50ms |
| TTS (Dialogflow) | streaming, hidden |
| **Total call turn** | **~1s perceived** (partial responses hide gap) |

### Error handling

- **Gemini timeout** → graceful response. Webhook returns fallback text within CX's 30s window.
- **Firestore unavailable** → fallback stateless response. Log error.
- **CX `sys.webhook.failed`** → TTS "Hmm, lost my train of thought. Say that again?"
- **`sys.no-input-default`** → Count to 2, then end call gracefully.

## Dialogflow CX Design

### Flows and Pages

```
Default Start Flow
  ├── Start Page
  │     entry: TTS welcome message with DTMF menu
  │     routes: DTMF 1→2→3 to persona pages
  │
  ├── Luna Page
  │     entry: set $session.params.persona = "luna"
  │     entry: webhook "greeting" → returns persona.greeting
  │     transition → Converse Page
  │
  ├── Viktor Page  (same pattern)
  ├── Sol Page     (same pattern)
  │
  ├── Converse Page
  │     event handlers:
  │       sys.no-match-default:
  │         webhook "converse" → POST /converse
  │         partial responses: enabled
  │       sys.no-input-default:
  │         condition: $session.params.silence_count < 2
  │         static: "Still with me?"
  │         set: $session.params.silence_count = $sys.func.ADD(…, 1)
  │       sys.no-input-default:
  │         condition: $session.params.silence_count >= 2
  │         static: "Alright, take care. Call back anytime."
  │         transition → End Session
  │       sys.webhook.failed:
  │         static: "Hmm, lost my train of thought. Say that again?"
  │     routes:
  │       intent: "goodbye" → Goodbye Page
  │
  └── Goodbye Page
        static: "Goodnight. Call again soon."
        transition → End Session
```

### Configuration checklist

- Phone Gateway: US number, Essentials Edition
- Conversation Profile: `phone_call` speech model, WaveNet voice per persona
- Webhook URL: Cloud Run HTTPS endpoint
- Webhook auth: ID Token (same GCP project)
- Webhook timeout: 30 seconds
- Partial responses: enabled on converse webhook

## Landing Page

Static site on Cloud Storage + Cloud CDN. Single page:
- Hero: phone number (large, prominent)
- Persona cards: name, tagline, vibe
- Retro aesthetic: dark background, neon/grainy text, fake scanlines
- Tech: Astro or plain HTML/CSS, deploy via `gcloud storage cp`

No accounts. No auth. Zero backend. Not worth more design time.

## Cost Model

### GCP costs (per minute of call)

| Resource | Rate | Per minute |
|---|---|---|
| Dialogflow CX voice audio | $0.001/sec | $0.06 |
| Gemini 3.1 Flash-Lite | ~$0.00001875/1K chars in, ~$0.000075/1K chars out | ~$0.01 |
| Cloud Run (1 min-instance) | ~$0.000018/hour idle + request pricing | negligible |
| Firestore | Free tier more than covers MVP | $0 |
| Phone Gateway number rental | ~$1/month | $0 |
| **Total operator cost** | | **~$0.07/min** |

### Caller pricing (if monetized)

Premium rate phone line or in-call credit card capture. Not in MVP scope.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Webhook + LLM latency exceeds CX timeout (30s) | Partial responses hide gap; Gemini Flash-Lite targets ~600ms; 25s budget leaves margin |
| Cold starts cause first-turn timeout | `--min-instances=1` on Cloud Run + `--cpu-boost` |
| Content guardrail violations | Per-persona banned topic lists; Gemini safety filters as second layer; deflection responses |
| Gemini 3.1 Flash-Lite deprecated (like 2.0 Flash) | Model is a config knob; architecture is model-agnostic |
| Caller ID unavailable (Trial Edition) | Essentials Edition required; validated in search results |
| STT errors on poor audio | `phone_call` speech model optimized for telephony; graceful fallback prompts |

## Non-Goals (explicitly out of scope)

- Stripe/payment integration
- User accounts or authentication
- Custom voice model training
- Multi-language support (English only for MVP)
- Admin dashboard
- Analytics/metrics beyond Cloud Logging
- Text/SMS interface

## Implementation Notes

- Dialogflow CX console migrated to Conversational Agents console (Oct 2025). Use the new unified console.
- Generative Playbooks NOT used (no SLA, limited control). All generative logic is in the orchestrator.
- `gemini-3.1-flash-lite-preview` deprecated 2026-05-25. Use GA `gemini-3.1-flash-lite`.
- Phone Gateway supports US numbers only. Factor this into testing.
