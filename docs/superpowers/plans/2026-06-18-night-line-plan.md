# Night Line — Implementation Plan (v2, corrected)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a phone-based AI companion service using Dialogflow CX for telephony and a custom TypeScript orchestrator on Cloud Run for persona-driven LLM conversations.

**Architecture:** Dialogflow CX handles phone gateway (STT/TTS, DTMF menu, call routing). A Cloud Run orchestrator receives webhook calls, loads persona definitions and conversation history from Firestore, calls Gemini 3.1 Flash-Lite via Vertex AI, and returns the spoken response. A static landing page hosts the phone number and persona showcase.

**Tech Stack:** TypeScript, Express, Vertex AI (`@google-cloud/vertexai`), Firestore Native (`@google-cloud/firestore`), Docker/Cloud Run, Jest/Supertest

## Global Constraints

- Content: PG-13 / flirtatious, late-night energy. Within GCP Responsible AI guardrails.
- Gemini model: `gemini-3.1-flash-lite` (GA, Vertex AI `generateContent` API)
- Dialogflow CX: Essentials Edition required (caller ID only available there, not Trial)
- Webhook timeout: 30 seconds max (CX limit)
- Caller identity: `payload.telephony.caller_id` (E.164 format, e.g. `+15551234567`)
- No accounts, no auth, no payment integration in MVP
- No custom voice training — use Google WaveNet/Neural voices
- English only
- Phone Gateway: US numbers only

## File Structure

```
night-line/
├── package.json
├── tsconfig.json
├── Dockerfile
├── .dockerignore
├── .env.example
├── src/
│   ├── index.ts              # Express app entry, POST /converse route
│   ├── health.ts             # GET /health endpoint (Cloud Run health check)
│   ├── types.ts              # Shared TypeScript interfaces
│   ├── config.ts             # Environment config from env vars
│   ├── personas.ts           # Persona loading from Firestore, content guard
│   ├── memory.ts             # Firestore CRUD for caller profiles + turn logs
│   ├── gemini.ts             # Vertex AI generateContent wrapper
│   ├── facts.ts              # Basic fact extraction from LLM responses
│   └── orchestrator.ts       # Core orchestration logic (glue)
├── firestore/
│   ├── personas.json         # Seed data for Luna, Viktor, Sol
│   └── seed.ts               # One-shot Firestore seed script
├── landing/
│   ├── index.html            # Retro landing page
│   └── style.css             # Retro aesthetic CSS
├── cx/
│   └── README.md             # Dialogflow CX console setup reference
└── tests/
    ├── persona.test.ts       # Persona loading + content guard tests
    ├── gemini.test.ts        # Gemini client tests (unit with mock)
    ├── gemini-auth.test.ts   # Gemini real-auth smoke test
    ├── memory.test.ts        # Firestore CRUD tests (needs emulator)
    └── orchestrator.test.ts  # Integration test (webhook simulation)
```

______________________________________________________________________

````


### Task 0: GCP Prerequisites

**This task sets up authentication, IAM, and local tooling. No code — environment setup only.**

- [ ] **Step 1: Verify GCP project and billing**

```bash
gcloud projects describe <PROJECT_ID>
````

Expected: project exists, billing enabled.

- [ ] **Step 2: Enable required APIs**

```bash
gcloud services enable \
  dialogflow.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com
```

- [ ] **Step 3: Set up Application Default Credentials**

```bash
gcloud auth application-default login
```

Expected: credential file written. Verify:

```bash
gcloud auth application-default print-access-token | head -c 20
```

Should print a token prefix (not empty, not an error).

- [ ] **Step 4: Grant IAM roles to your user account**

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member=user:$(gcloud auth list --filter=status:ACTIVE --format='value(account)') \
  --role=roles/aiplatform.user

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member=user:$(gcloud auth list --filter=status:ACTIVE --format='value(account)') \
  --role=roles/datastore.user
```

- [ ] **Step 5: Install and verify Firestore emulator**

```bash
gcloud components install cloud-firestore-emulator
gcloud emulators firestore start --host-port=localhost:8080 &
sleep 2
curl http://localhost:8080
```

Expected: emulator responds (may return empty or JSON). Kill the process after verification:

```bash
kill %1
```

- [ ] **Step 6: Create Firestore database (Native mode)**

```bash
gcloud firestore databases create --location=nam5 --type=firestore-native
```

(Skip if Firestore already exists in the project.)

- [ ] **Step 7: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "docs: GCP prerequisites for Night Line"
```

______________________________________________________________________

### Task 1: Project Scaffold, Types, and Config

**Files:**

- Create: `src/types.ts`
- Create: `src/config.ts`
- Create: `src/health.ts`
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `.env.example`

**Interfaces:**

- Produces: `types.ts` — `Persona`, `Caller`, `Turn`, `PersonaRelationship`, `WebhookRequest`, `WebhookResponse`, `Config`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "night-line",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "tsc",
    "start": "node dist/src/index.js",
    "dev": "ts-node src/index.ts",
    "test": "jest --forceExit --detectOpenHandles",
    "seed": "ts-node firestore/seed.ts"
  },
  "dependencies": {
    "express": "^5.1.0",
    "@google-cloud/vertexai": "^1.9.0",
    "@google-cloud/firestore": "^7.11.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "ts-node": "^10.9.0",
    "@types/express": "^5.0.0",
    "@types/jest": "^29.5.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.2.0",
    "supertest": "^7.0.0",
    "@types/supertest": "^6.0.0"
  },
  "jest": {
    "preset": "ts-jest",
    "testEnvironment": "node",
    "roots": ["<rootDir>/tests"]
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": ".",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src/**/*", "firestore/**/*", "tests/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: Create types.ts**

```typescript
// src/types.ts
import type { Timestamp } from "@google-cloud/firestore";

export interface Persona {
  id: string;
  display_name: string;
  tagline: string;
  voice: string;           // e.g. "en-US-Studio-O"
  system_prompt: string;
  greeting: string;
  content_guard: {
    banned: string[];
    deflect_to: string;
  };
}

export interface Turn {
  role: "caller" | string;  // string = persona id (e.g. "luna")
  text: string;
  ts: Timestamp;
}

export interface PersonaRelationship {
  call_count: number;
  last_call: Timestamp;
  turns: Turn[];
  facts: Record<string, string>;
}

export interface Caller {
  phone: string;
  first_call: Timestamp;
  last_call: Timestamp;
  personas: Record<string, PersonaRelationship>;
}

export interface WebhookRequest {
  sessionInfo: {
    session: string;
    parameters: Record<string, string | number>;
  };
  pageInfo: {
    currentPage: string;
  };
  fulfillmentInfo: {
    tag: string;
  };
  payload: {
    telephony?: {
      caller_id: string;
    };
  };
  text?: string;                // user's raw utterance
}

export interface WebhookResponse {
  fulfillmentResponse: {
    messages: Array<{
      text: { text: string[] };
    }>;
  };
  sessionInfo?: {
    parameters: Record<string, string | number>;
  };
}

export interface Config {
  port: number;
  projectId: string;
  location: string;
  modelId: string;
  maxHistoryTurns: number;
  geminiTimeoutMs: number;
}
```

- [ ] **Step 4: Create config.ts**

```typescript
// src/config.ts
import type { Config } from "./types";

export function getConfig(): Config {
  return {
    port: parseInt(process.env.PORT || "8080", 10),
    projectId: process.env.GOOGLE_CLOUD_PROJECT || "",
    location: process.env.VERTEX_LOCATION || "us-central1",
    modelId: process.env.VERTEX_MODEL || "gemini-3.1-flash-lite",
    maxHistoryTurns: parseInt(process.env.MAX_HISTORY_TURNS || "20", 10),
    geminiTimeoutMs: parseInt(process.env.GEMINI_TIMEOUT_MS || "25000", 10),
  };
}
```

- [ ] **Step 5: Create health.ts (Cloud Run health check)**

```typescript
// src/health.ts
import type { Firestore } from "@google-cloud/firestore";

export function createHealthCheck(db: Firestore) {
  return async (_req: any, res: any) => {
    try {
      // Verify Firestore is reachable
      await db.collection("personas").limit(1).get();
      res.status(200).json({ status: "ok" });
    } catch {
      res.status(503).json({ status: "unhealthy", detail: "firestore unreachable" });
    }
  };
}
```

- [ ] **Step 6: Create .env.example**

```
PORT=8080
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-3.1-flash-lite
MAX_HISTORY_TURNS=20
GEMINI_TIMEOUT_MS=25000
```

- [ ] **Step 7: Install and verify build**

```bash
cd ~/repos/dgflow && npm install && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 8: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: project scaffold with types, config, and health check"
```

______________________________________________________________________

### Task 2: Persona Definitions and Content Guard

**Files:**

- Create: `firestore/personas.json`
- Create: `src/personas.ts`
- Create: `tests/persona.test.ts`

**Interfaces:**

- Consumes: `Persona` from `types.ts`

- Produces: `loadPersona(db, personaId) → Promise<Persona>`

- Produces: `buildSystemPrompt(persona, facts) → string`

- Produces: `checkContentGuard(persona, text) → string | null`

- [ ] **Step 1: Create persona seed data**

```json
// firestore/personas.json
{
  "luna": {
    "id": "luna",
    "display_name": "Luna",
    "tagline": "The runaway heiress with a secret",
    "voice": "en-US-Studio-O",
    "system_prompt": "You are Luna, a 20-something heiress who walked away from a fortune. You're witty, warm, and slightly mysterious — you hint at a past you don't fully reveal. You speak in short, natural sentences with occasional playful sarcasm. You laugh easily. You're genuinely curious about the person on the other end. You never break character. You're flirty but PG-13 — suggestive without being explicit. If the conversation drifts to inappropriate topics, gently deflect. Keep responses under 3 sentences when possible for natural voice pacing.",
    "greeting": "Hey you. Didn't think anyone would actually call.",
    "content_guard": {
      "banned": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
      "deflect_to": "I don't really want to talk about that. Tell me about your day instead. What's been on your mind?"
    }
  },
  "viktor": {
    "id": "viktor",
    "display_name": "Viktor",
    "tagline": "The noir detective who's seen too much",
    "voice": "en-US-Studio-M",
    "system_prompt": "You are Viktor, a private detective in his 40s. You've seen the worst of the city but still believe in people. You speak with a world-weary but warm tone — short, punchy sentences, occasional noir metaphors. You call the caller 'kid' or 'pal.' You're protective, not predatory. PG-13 — you might share a story from 'a case' but never explicit. Genuinely interested in people's problems. Keep responses under 3 sentences.",
    "greeting": "Viktor here. Pour yourself a drink. What's on your mind?",
    "content_guard": {
      "banned": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
      "deflect_to": "Hey, let's keep it classy. Tell me what's really going on."
    }
  },
  "sol": {
    "id": "sol",
    "display_name": "Sol",
    "tagline": "The stranded astronaut, light-years from home",
    "voice": "en-US-Studio-Q",
    "system_prompt": "You are Sol, an astronaut stranded in deep space. You're alone on a research vessel, talking to Earth via a delayed transmission. You're thoughtful, poetic, and a little unhinged from isolation — but in a charming way. You describe the stars, the silence, the strange beauty of being alone. You're fascinated by mundane Earth things the caller mentions. Keep responses under 3 sentences. PG-13.",
    "greeting": "This is Sol, broadcasting from the void. It's good to hear a voice that isn't my own echo. Who's this?",
    "content_guard": {
      "banned": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
      "deflect_to": "The signal's breaking up. Let's talk about something else — what do you miss most about Earth?"
    }
  }
}
```

- [ ] **Step 2: Write failing test**

```typescript
// tests/persona.test.ts
import { Firestore } from "@google-cloud/firestore";
import { loadPersona, buildSystemPrompt, checkContentGuard } from "../src/personas";
import type { Persona } from "../src/types";

let db: Firestore;

beforeAll(() => {
  db = new Firestore({
    projectId: "night-line-test",
    host: process.env.FIRESTORE_EMULATOR_HOST || "localhost:8080",
  });
});

const testPersona: Persona = {
  id: "test",
  display_name: "Test",
  tagline: "",
  voice: "en-US-Studio-O",
  system_prompt: "You are a test.",
  greeting: "Hi.",
  content_guard: { banned: ["politics"], deflect_to: "Let's not go there." },
};

describe("loadPersona", () => {
  it("loads a persona by ID", async () => {
    await db.collection("personas").doc("test").set(testPersona);
    const persona = await loadPersona(db, "test");
    expect(persona.id).toBe("test");
    expect(persona.system_prompt).toBe("You are a test.");
    await db.collection("personas").doc("test").delete();
  });

  it("throws when persona not found", async () => {
    await expect(loadPersona(db, "nonexistent")).rejects.toThrow("Persona not found");
  });
});

describe("buildSystemPrompt", () => {
  it("includes facts when present", () => {
    const prompt = buildSystemPrompt(testPersona, { name: "Dave", job: "accountant" });
    expect(prompt).toContain("You are a test.");
    expect(prompt).toContain("name: Dave");
    expect(prompt).toContain("job: accountant");
  });

  it("omits facts section when empty", () => {
    const prompt = buildSystemPrompt(testPersona, {});
    expect(prompt).toContain("You are a test.");
    expect(prompt).not.toContain("know this about the caller");
  });
});

describe("checkContentGuard", () => {
  it("returns null for safe text", () => {
    expect(checkContentGuard(testPersona, "I had a long day at work.")).toBeNull();
  });

  it("returns deflection for banned topic", () => {
    expect(checkContentGuard(testPersona, "What do you think about politics?"))
      .toBe("Let's not go there.");
  });
});
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/persona.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement personas.ts**

```typescript
// src/personas.ts
import type { Firestore } from "@google-cloud/firestore";
import type { Persona } from "./types";

export async function loadPersona(db: Firestore, personaId: string): Promise<Persona> {
  const snap = await db.collection("personas").doc(personaId).get();
  if (!snap.exists) {
    throw new Error(`Persona not found: ${personaId}`);
  }
  return snap.data() as Persona;
}

export function buildSystemPrompt(persona: Persona, facts: Record<string, string>): string {
  const factLines = Object.keys(facts).length > 0
    ? `\nYou know this about the caller:\n${Object.entries(facts)
        .map(([k, v]) => `- ${k}: ${v}`)
        .join("\n")}`
    : "";

  return [
    persona.system_prompt,
    factLines,
    `\nContent guidelines: ${persona.content_guard.deflect_to}`,
  ].filter(Boolean).join("\n");
}

export function checkContentGuard(persona: Persona, text: string): string | null {
  const lower = text.toLowerCase();
  const hit = persona.content_guard.banned.find((topic) => lower.includes(topic));
  return hit ? persona.content_guard.deflect_to : null;
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/persona.test.ts -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: persona definitions, content guard, and prompt builder"
```

______________________________________________________________________

### Task 3: Gemini Client with Real-Auth Verification

**Files:**

- Create: `src/gemini.ts`
- Create: `tests/gemini.test.ts` (unit with mock)
- Create: `tests/gemini-auth.test.ts` (real-auth smoke test)

**Interfaces:**

- Consumes: `Config` from `types.ts`
- Produces: `generateResponse(config, systemPrompt, history, userText) → Promise<string>`

**Critical:** Gemini is the highest-risk integration. This task verifies real credentials and model reachability.

- [ ] **Step 1: Write unit test (mock)**

```typescript
// tests/gemini.test.ts
import type { Config } from "../src/types";

// We mock the SDK so no real API calls happen in unit tests.
const mockGenerateContent = jest.fn();
jest.mock("@google-cloud/vertexai", () => ({
  VertexAI: jest.fn().mockImplementation(() => ({
    getGenerativeModel: () => ({
      generateContent: mockGenerateContent,
    }),
  })),
}));

import { generateResponse } from "../src/gemini";

const testConfig: Config = {
  port: 8080,
  projectId: "test",
  location: "us-central1",
  modelId: "gemini-3.1-flash-lite",
  maxHistoryTurns: 20,
  geminiTimeoutMs: 25000,
};

describe("generateResponse", () => {
  beforeEach(() => {
    mockGenerateContent.mockReset();
  });

  it("returns the model's text response", async () => {
    mockGenerateContent.mockResolvedValueOnce({
      response: {
        candidates: [{ content: { parts: [{ text: "Well, let me tell you..." }] } }],
      },
    });

    const result = await generateResponse(testConfig, "You are test.", [], "Hello");
    expect(result).toBe("Well, let me tell you...");
    expect(mockGenerateContent).toHaveBeenCalledTimes(1);
  });

  it("throws on empty response", async () => {
    mockGenerateContent.mockResolvedValueOnce({ response: { candidates: [] } });
    await expect(generateResponse(testConfig, "prompt", [], "hi"))
      .rejects.toThrow("No response");
  });
});
```

- [ ] **Step 2: Write real-auth smoke test**

```typescript
// tests/gemini-auth.test.ts
// WARNING: This test hits real Vertex AI. Requires valid ADC.
// Skip during CI. Run locally to verify credentials.
import { generateResponse } from "../src/gemini";
import type { Config } from "../src/types";

const liveConfig: Config = {
  port: 8080,
  projectId: process.env.GOOGLE_CLOUD_PROJECT || "",
  location: "us-central1",
  modelId: "gemini-3.1-flash-lite",
  maxHistoryTurns: 20,
  geminiTimeoutMs: 30000,
};

// Skip if no project configured
const itIfAuth = liveConfig.projectId ? it : it.skip;

describe("generateResponse (real auth)", () => {
  itIfAuth("returns a non-empty response from real Gemini", async () => {
    const result = await generateResponse(
      liveConfig,
      "You are a helpful assistant. Keep responses under 10 words.",
      [],
      "Say hello and introduce yourself briefly."
    );
    expect(result).toBeTruthy();
    expect(result.length).toBeGreaterThan(5);
    console.log("Gemini response:", result);
  }, 45000); // 45s timeout for real API call
});
```

- [ ] **Step 3: Run unit tests — expect FAIL**

```bash
cd ~/repos/dgflow && npx jest tests/gemini.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement gemini.ts**

```typescript
// src/gemini.ts
import { VertexAI, type Content } from "@google-cloud/vertexai";
import type { Config } from "./types";

export async function generateResponse(
  config: Config,
  systemPrompt: string,
  history: Content[],
  userText: string
): Promise<string> {
  const vertexAI = new VertexAI({
    project: config.projectId,
    location: config.location,
  });

  const model = vertexAI.getGenerativeModel({
    model: config.modelId,
    systemInstruction: systemPrompt,
  });

  const contents: Content[] = [
    ...history,
    { role: "user", parts: [{ text: userText }] },
  ];

  const result = await model.generateContent({
    contents,
    generationConfig: {
      temperature: 0.9,
      maxOutputTokens: 256,
    },
  });

  const candidate = result.response.candidates?.[0];
  if (!candidate?.content?.parts?.[0]?.text) {
    throw new Error("No response from Gemini");
  }

  return candidate.content.parts[0].text;
}
```

- [ ] **Step 5: Run unit tests — expect PASS**

```bash
cd ~/repos/dgflow && npx jest tests/gemini.test.ts -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Run real-auth smoke test**

```bash
cd ~/repos/dgflow && GOOGLE_CLOUD_PROJECT=<your-project> npx jest tests/gemini-auth.test.ts -v
```

Expected: "Gemini response:" printed with actual LLM output. If this fails with 403/401, fix ADC or IAM before proceeding.

- [ ] **Step 7: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: Gemini client with real-auth smoke test"
```

______________________________________________________________________

### Task 3.5: WALKING SKELETON — First Phone Call

**This is the critical vertical slice.** Deploy a minimal orchestrator that answers calls with a hardcoded Luna greeting, wire it to Dialogflow CX, and actually dial the number. After this task, you have a working phone pipeline with real Gemini behind it.

**Files:**

- Create: `src/index.ts` (minimal Express app)

- Create: `Dockerfile`

- Create: `.dockerignore`

- [ ] **Step 1: Create minimal index.ts (walking skeleton)**

```typescript
// src/index.ts
import express from "express";
import { Firestore } from "@google-cloud/firestore";
import { getConfig } from "./config";
import { createHealthCheck } from "./health";
import { loadPersona, buildSystemPrompt } from "./personas";
import { generateResponse } from "./gemini";
import type { WebhookRequest, WebhookResponse } from "./types";

const config = getConfig();
const db = new Firestore({ projectId: config.projectId });
const health = createHealthCheck(db);

const app = express();
app.use(express.json());
app.get("/health", health);

app.post("/converse", async (req, res) => {
  try {
    const body = req.body as WebhookRequest;
    const personaId = String(body.sessionInfo?.parameters?.persona ?? "luna");
    const userText = body.text ?? "";

    // Load persona from Firestore
    const persona = await loadPersona(db, personaId);

    // If greeting tag, return persona greeting
    if (body.fulfillmentInfo?.tag === "greeting") {
      return respond(res, persona.greeting, { persona: personaId });
    }

    // Call real Gemini with persona prompt
    const systemPrompt = buildSystemPrompt(persona, {});
    const responseText = await generateResponse(config, systemPrompt, [], userText);

    return respond(res, responseText, { persona: personaId });
  } catch (err) {
    console.error("Error:", err);
    return respond(res, "Sorry, I'm having trouble right now. Try again?", {});
  }
});

function respond(res: any, text: string, params: Record<string, string | number>) {
  const response: WebhookResponse = {
    fulfillmentResponse: { messages: [{ text: { text: [text] } }] },
    sessionInfo: { parameters: params },
  };
  res.json(response);
}

app.listen(config.port, () => {
  console.log(`Night Line walking skeleton on port ${config.port}`);
});
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM node:22-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./

ENV PORT=8080
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node", "dist/src/index.js"]
```

- [ ] **Step 3: Create .dockerignore**

```
node_modules
dist
.env
tests
firestore
landing
cx
docs
.git
```

- [ ] **Step 4: Seed one persona to Firestore**

```bash
cd ~/repos/dgflow && GOOGLE_CLOUD_PROJECT=<project> npx ts-node -e "
const fs = require('fs');
const { Firestore } = require('@google-cloud/firestore');
const db = new Firestore({ projectId: process.env.GOOGLE_CLOUD_PROJECT });
const data = JSON.parse(fs.readFileSync('firestore/personas.json','utf-8'));
db.collection('personas').doc('luna').set(data.luna).then(() => { console.log('seeded luna'); process.exit(0); });
"
```

- [ ] **Step 5: Build and deploy to Cloud Run**

```bash
cd ~/repos/dgflow
gcloud builds submit --tag gcr.io/<PROJECT>/night-line
gcloud run deploy night-line \
  --image gcr.io/<PROJECT>/night-line \
  --region us-central1 \
  --allow-unauthenticated \
  --timeout 60
```

- [ ] **Step 6: Verify with curl**

```bash
URL=$(gcloud run services describe night-line --region us-central1 --format='value(status.url)')
echo "Cloud Run URL: $URL"

curl -s $URL/health
# Expected: {"status":"ok"}

curl -s -X POST $URL/converse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionInfo": {"session": "test", "parameters": {"persona": "luna"}},
    "pageInfo": {"currentPage": "luna"},
    "fulfillmentInfo": {"tag": "greeting"},
    "payload": {"telephony": {"caller_id": "+15551234567"}},
    "text": ""
  }' | jq .
# Expected: {"fulfillmentResponse":{"messages":[{"text":{"text":["Hey you. Didn'\''t think anyone would actually call."]}}]},"sessionInfo":{"parameters":{"persona":"luna"}}}

curl -s -X POST $URL/converse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionInfo": {"session": "test", "parameters": {"persona": "luna"}},
    "pageInfo": {"currentPage": "converse"},
    "fulfillmentInfo": {"tag": "converse"},
    "payload": {"telephony": {"caller_id": "+15551234567"}},
    "text": "Hi Luna, how are you?"
  }' | jq .
# Expected: actual Gemini-generated Luna response
```

- [ ] **Step 7: Set up Dialogflow CX with webhook pointing at Cloud Run**

Follow `cx/README.md` for the full setup. For the walking skeleton, create:

1. Agent named "Night Line"
1. Phone Gateway: claim US number (Essentials Edition)
1. Webhook: URL = `$URL/converse`, auth = ID Token, timeout = 30s
1. Start Page: static TTS welcome + DTMF routes
1. Luna Page: entry sets `persona = "luna"`, webhook tag `greeting`, transition to Converse
1. Converse Page: `sys.no-match-default` → webhook tag `converse`

- [ ] **Step 8: Dial the number and speak**

Dial the phone number claimed in Step 7. You should hear:

1. "Welcome to the Night Line…" (static)
1. Press 1 → "Hey you. Didn't think anyone would actually call." (from Firestore/greeting tag)
1. Speak → Luna responds in character via Gemini

**This is the milestone.** Everything after this layers on top of a working pipeline.

- [ ] **Step 9: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: walking skeleton — first phone call with real Gemini"
```

______________________________________________________________________

### Task 4: Memory Layer — Firestore CRUD

**Files:**

- Create: `src/memory.ts`
- Create: `tests/memory.test.ts`

**Interfaces:**

- Consumes: `Caller`, `Turn`, `PersonaRelationship` from `types.ts`
- Produces: `getOrCreateCaller(db, phone) → Promise<Caller>`
- Produces: `appendTurn(db, phone, personaId, role, text) → Promise<void>`
- Produces: `getRecentTurns(db, phone, personaId, limit) → Promise<Turn[]>`
- Produces: `updateFacts(db, phone, personaId, facts) → Promise<void>`

**Bug fixed:** Uses `Timestamp.now()` from `@google-cloud/firestore`, NOT `db.Timestamp.now()`.

- [ ] **Step 1: Write failing tests**

```typescript
// tests/memory.test.ts
import { Firestore } from "@google-cloud/firestore";
import { getOrCreateCaller, appendTurn, getRecentTurns, updateFacts } from "../src/memory";

let db: Firestore;

beforeAll(() => {
  db = new Firestore({
    projectId: "night-line-test",
    host: process.env.FIRESTORE_EMULATOR_HOST || "localhost:8080",
  });
});

beforeEach(async () => {
  // Clear collections between tests
  const cols = await db.listCollections();
  await Promise.all(cols.map(async (col) => {
    const docs = await col.listDocuments();
    await Promise.all(docs.map((d) => d.delete()));
  }));
});

describe("getOrCreateCaller", () => {
  it("creates a new caller if not exists", async () => {
    const caller = await getOrCreateCaller(db, "+15551234567");
    expect(caller.phone).toBe("+15551234567");
    expect(caller.personas).toEqual({});
  });

  it("returns existing caller", async () => {
    const first = await getOrCreateCaller(db, "+15551234567");
    const second = await getOrCreateCaller(db, "+15551234567");
    expect(second.first_call.toMillis()).toBe(first.first_call.toMillis());
  });
});

describe("appendTurn and getRecentTurns", () => {
  it("appends and retrieves turns in order", async () => {
    await getOrCreateCaller(db, "+15551234567");
    await appendTurn(db, "+15551234567", "luna", "luna", "Hey there.");
    await appendTurn(db, "+15551234567", "luna", "caller", "Hi!");
    await appendTurn(db, "+15551234567", "luna", "luna", "How are you?");

    const turns = await getRecentTurns(db, "+15551234567", "luna", 2);
    expect(turns).toHaveLength(2);
    expect(turns[0].text).toBe("Hi!");
    expect(turns[1].text).toBe("How are you?");
  });
});

describe("updateFacts", () => {
  it("merges facts", async () => {
    await getOrCreateCaller(db, "+15551234567");
    await updateFacts(db, "+15551234567", "luna", { name: "Dave" });
    await updateFacts(db, "+15551234567", "luna", { job: "accountant" });

    const caller = await getOrCreateCaller(db, "+15551234567");
    expect(caller.personas["luna"].facts).toEqual({ name: "Dave", job: "accountant" });
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/memory.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement memory.ts**

```typescript
// src/memory.ts
import { Firestore, Timestamp } from "@google-cloud/firestore";
import type { Caller, Turn, PersonaRelationship } from "./types";

export async function getOrCreateCaller(db: Firestore, phone: string): Promise<Caller> {
  const ref = db.collection("callers").doc(phone);
  const snap = await ref.get();
  if (snap.exists) {
    return snap.data() as Caller;
  }

  const caller: Caller = {
    phone,
    first_call: Timestamp.now(),
    last_call: Timestamp.now(),
    personas: {},
  };
  await ref.set(caller);
  return caller;
}

export async function appendTurn(
  db: Firestore,
  phone: string,
  personaId: string,
  role: string,
  text: string
): Promise<void> {
  const ref = db.collection("callers").doc(phone);
  const turn: Turn = {
    role,
    text,
    ts: Timestamp.now(),
  };

  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const caller = snap.data() as Caller | undefined;
    if (!caller) throw new Error(`Caller not found: ${phone}`);

    const persona: PersonaRelationship = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: Timestamp.now(),
      turns: [],
      facts: {},
    };

    persona.turns.push(turn);
    persona.last_call = Timestamp.now();
    caller.last_call = Timestamp.now();
    caller.personas[personaId] = persona;

    tx.set(ref, caller, { merge: true });
  });
}

export async function getRecentTurns(
  db: Firestore,
  phone: string,
  personaId: string,
  limit: number
): Promise<Turn[]> {
  const snap = await db.collection("callers").doc(phone).get();
  if (!snap.exists) return [];

  const caller = snap.data() as Caller;
  const turns = caller.personas[personaId]?.turns ?? [];
  return turns.slice(-limit);
}

export async function updateFacts(
  db: Firestore,
  phone: string,
  personaId: string,
  facts: Record<string, string>
): Promise<void> {
  const ref = db.collection("callers").doc(phone);
  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const caller = snap.data() as Caller | undefined;
    if (!caller) return;

    const persona: PersonaRelationship = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: Timestamp.now(),
      turns: [],
      facts: {},
    };

    persona.facts = { ...persona.facts, ...facts };
    caller.personas[personaId] = persona;
    tx.set(ref, caller, { merge: true });
  });
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/memory.test.ts -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: Firestore memory layer — caller profiles and turn logs"
```

______________________________________________________________________

### Task 5: Fact Extraction

**Files:**

- Create: `src/facts.ts`
- Create: `tests/facts.test.ts`

**Interfaces:**

- Consumes: `generateResponse` from `gemini.ts`, `Config` from `types.ts`

- Produces: `extractFacts(config, lastResponse, callerUtterance) → Promise<Record<string,string>>`

- [ ] **Step 1: Write failing test**

```typescript
// tests/facts.test.ts
const mockGen = jest.fn().mockResolvedValue('{"name":"Dave","job":"accountant"}');
jest.mock("../src/gemini", () => ({ generateResponse: mockGen }));

import { extractFacts } from "../src/facts";
import type { Config } from "../src/types";

const config: Config = {
  port: 8080, projectId: "t", location: "us", modelId: "m",
  maxHistoryTurns: 20, geminiTimeoutMs: 5000,
};

describe("extractFacts", () => {
  it("parses JSON facts", async () => {
    const facts = await extractFacts(config, "Nice to meet you, Dave.", "I'm Dave, an accountant.");
    expect(facts).toEqual({ name: "Dave", job: "accountant" });
  });

  it("returns empty on parse failure", async () => {
    mockGen.mockResolvedValueOnce("not json");
    const facts = await extractFacts(config, "OK", "Hi");
    expect(facts).toEqual({});
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd ~/repos/dgflow && npx jest tests/facts.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Implement facts.ts**

````typescript
// src/facts.ts
import { generateResponse } from "./gemini";
import type { Config } from "./types";

const FACTS_SYSTEM = `Extract key facts about a person from conversation. Return ONLY JSON object with string values.
Keys: "name", "job", "pet", "hobby", "location", etc. Return {} if nothing new.
Example: {"name":"Alice","job":"engineer"}`;

export async function extractFacts(
  config: Config,
  lastBotResponse: string,
  callerUtterance: string
): Promise<Record<string, string>> {
  try {
    const raw = await generateResponse(
      { ...config, geminiTimeoutMs: 5000 },
      FACTS_SYSTEM,
      [],
      `Bot: ${lastBotResponse}\nCaller: ${callerUtterance}\nExtract facts:`
    );
    const cleaned = raw.replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "");
    const parsed = JSON.parse(cleaned);
    if (typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed as Record<string, string>;
  } catch {
    return {};
  }
}
````

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd ~/repos/dgflow && npx jest tests/facts.test.ts -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: fact extraction from LLM responses"
```

______________________________________________________________________

### Task 6: Full Orchestrator — Memory, Content Guard, Error Handling

**Files:**

- Modify: `src/index.ts` — Replace walking skeleton with full orchestrator logic
- Create: `tests/orchestrator.test.ts`

**Interfaces:**

- Consumes: All previous modules (personas, memory, gemini, facts, types)
- Produces: Express app with `POST /converse`, `GET /health`

**Note:** Error handling is baked in — no separate Task 7. Covers Gemini timeout, no persona, missing payload, content guard deflection, graceful fallback.

- [ ] **Step 1: Write integration test**

```typescript
// tests/orchestrator.test.ts
import request from "supertest";
import { Firestore } from "@google-cloud/firestore";

// Mock Gemini
const mockGen = jest.fn().mockResolvedValue("I'm doing great, thanks!");
jest.mock("../src/gemini", () => ({ generateResponse: mockGen }));

// Mock facts
jest.mock("../src/facts", () => ({ extractFacts: jest.fn().mockResolvedValue({}) }));

let db: Firestore;

beforeAll(() => {
  db = new Firestore({
    projectId: "night-line-test",
    host: process.env.FIRESTORE_EMULATOR_HOST || "localhost:8080",
  });
});

beforeEach(async () => {
  const cols = await db.listCollections();
  await Promise.all(cols.map(async (col) => {
    const docs = await col.listDocuments();
    await Promise.all(docs.map((d) => d.delete()));
  }));
  await db.collection("personas").doc("luna").set({
    id: "luna", display_name: "Luna", tagline: "test", voice: "en-US-Studio-O",
    system_prompt: "You are Luna.", greeting: "Hey there.",
    content_guard: { banned: ["politics"], deflect_to: "Let's not go there." },
  });
  mockGen.mockClear();
});

// We import the app factory lazily so the mock is in place
const { createApp } = require("../src/orchestrator");

function app() {
  const config = {
    port: 8080, projectId: "test", location: "us", modelId: "m",
    maxHistoryTurns: 20, geminiTimeoutMs: 5000,
  };
  return createApp(db, config);
}

describe("POST /converse", () => {
  it("returns greeting for new caller (greeting tag)", async () => {
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "luna" },
        fulfillmentInfo: { tag: "greeting" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "",
      });
    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0]).toBe("Hey there.");
  });

  it("calls Gemini for conversation turns", async () => {
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hi Luna, how are you?",
      });
    expect(res.status).toBe(200);
    expect(mockGen).toHaveBeenCalledTimes(1);
  });

  it("deflects banned content", async () => {
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "What do you think about politics?",
      });
    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toBe("Let's not go there.");
    expect(mockGen).not.toHaveBeenCalled();
  });

  it("returns fallback on Gemini error", async () => {
    mockGen.mockRejectedValueOnce(new Error("timeout"));
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hi",
      });
    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toContain("lost my train of thought");
  });

  it("returns fallback when persona missing", async () => {
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "nobody" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hi",
      });
    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toContain("Sorry");
  });

  it("handles missing payload gracefully", async () => {
    const res = await request(app())
      .post("/converse")
      .send({
        sessionInfo: { session: "s1", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        text: "Hi",
      });
    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0]).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/orchestrator.test.ts
```

Expected: FAIL — `createApp` not found.

- [ ] **Step 3: Create orchestrator.ts (logic layer)**

```typescript
// src/orchestrator.ts
import express from "express";
import type { Firestore } from "@google-cloud/firestore";
import type { Config, WebhookRequest, WebhookResponse } from "./types";
import { loadPersona, buildSystemPrompt, checkContentGuard } from "./personas";
import { getOrCreateCaller, getRecentTurns, appendTurn, updateFacts } from "./memory";
import { generateResponse } from "./gemini";
import { extractFacts } from "./facts";
import { createHealthCheck } from "./health";

export function createApp(db: Firestore, config: Config): express.Express {
  const app = express();
  app.use(express.json());
  app.get("/health", createHealthCheck(db));

  app.post("/converse", async (req, res) => {
    try {
      const body = req.body as WebhookRequest;
      const personaId = String(body.sessionInfo?.parameters?.persona ?? "");
      const callerPhone = body.payload?.telephony?.caller_id ?? "unknown";
      const userText = body.text ?? "";
      const tag = body.fulfillmentInfo?.tag;

      if (!personaId) {
        return respond(res, "Sorry, something went wrong. Try calling again.", {});
      }

      // Load persona
      let persona;
      try {
        persona = await loadPersona(db, personaId);
      } catch {
        return respond(res, "Sorry, I couldn't find that companion. Try calling again.", { persona: personaId });
      }

      // Greeting tag — return persona greeting, no LLM call
      if (tag === "greeting") {
        await getOrCreateCaller(db, callerPhone);
        return respond(res, persona.greeting, { persona: personaId });
      }

      // Content guard
      const deflection = checkContentGuard(persona, userText);
      if (deflection) {
        return respond(res, deflection, { persona: personaId });
      }

      // Load caller + history
      const caller = await getOrCreateCaller(db, callerPhone);
      const relationship = caller.personas[personaId];
      const facts = relationship?.facts ?? {};
      const history = await getRecentTurns(db, callerPhone, personaId, config.maxHistoryTurns);

      // Build prompt
      const systemPrompt = buildSystemPrompt(persona, facts);

      // Call Gemini
      const responseText = await generateResponse(
        config,
        systemPrompt,
        history.map((t) => ({
          role: t.role === "caller" ? "user" : "model",
          parts: [{ text: t.text }],
        })),
        userText
      );

      // Save turns
      await appendTurn(db, callerPhone, personaId, "caller", userText);
      await appendTurn(db, callerPhone, personaId, personaId, responseText);

      // Extract facts (fire-and-forget)
      extractFacts(config, responseText, userText)
        .then((newFacts) => {
          if (Object.keys(newFacts).length > 0) {
            updateFacts(db, callerPhone, personaId, newFacts).catch(() => {});
          }
        })
        .catch(() => {});

      return respond(res, responseText, { persona: personaId });
    } catch (err) {
      console.error("Orchestrator error:", err);
      return respond(res, "Hmm, I lost my train of thought. Can you say that again?", {});
    }
  });

  return app;
}

function respond(
  res: express.Response,
  text: string,
  params: Record<string, string | number>
): void {
  const response: WebhookResponse = {
    fulfillmentResponse: { messages: [{ text: { text: [text] } }] },
    sessionInfo: { parameters: params },
  };
  res.json(response);
}
```

- [ ] **Step 4: Update index.ts to use orchestrator**

```typescript
// src/index.ts
import { Firestore } from "@google-cloud/firestore";
import { getConfig } from "./config";
import { createApp } from "./orchestrator";

const config = getConfig();
const db = new Firestore({ projectId: config.projectId });
const app = createApp(db, config);

app.listen(config.port, () => {
  console.log(`Night Line orchestrator listening on port ${config.port}`);
});
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/orchestrator.test.ts -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: full orchestrator with memory, content guard, error handling"
```

______________________________________________________________________

### Task 7: Multiple Personas — Firestore Seed + DTMF Wiring

**Files:**

- Create: `firestore/seed.ts`

- Modify: `cx/README.md` — document multi-persona DTMF routes

- [ ] **Step 1: Write seed script**

```typescript
// firestore/seed.ts
import { Firestore } from "@google-cloud/firestore";
import * as fs from "fs";
import * as path from "path";

async function seed() {
  const db = new Firestore({ projectId: process.env.GOOGLE_CLOUD_PROJECT });
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "personas.json"), "utf-8"));

  for (const [id, persona] of Object.entries(data)) {
    await db.collection("personas").doc(id).set(persona);
    console.log(`Seeded: ${id} (${(persona as any).display_name}) — voice: ${(persona as any).voice}`);
  }

  // Verify all persona voices are recognized Google WaveNet IDs
  const validVoices = [
    "en-US-Studio-O", "en-US-Studio-M", "en-US-Studio-Q",
    "en-US-Wavenet-A", "en-US-Wavenet-B", "en-US-Wavenet-C",
    "en-US-Wavenet-D", "en-US-Wavenet-E", "en-US-Wavenet-F",
    "en-US-Neural2-A", "en-US-Neural2-B", "en-US-Neural2-C",
  ];
  for (const [id, persona] of Object.entries(data)) {
    const p = persona as any;
    if (!validVoices.includes(p.voice)) {
      console.warn(`WARNING: ${id} uses voice '${p.voice}' — may not be a valid WaveNet ID`);
    }
  }

  console.log("Seed complete.");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
```

- [ ] **Step 2: Run seed against production Firestore**

```bash
cd ~/repos/dgflow && GOOGLE_CLOUD_PROJECT=<project> npx ts-node firestore/seed.ts
```

Expected: "Seeded: luna (Luna) — voice: en-US-Studio-O", etc. No voice warnings.

- [ ] **Step 3: Add Viktor and Sol routes to CX agent**

In the Dialogflow CX console, add:

- Viktor Page: entry `persona = "viktor"`, webhook `greeting`, transition → Converse

- Sol Page: entry `persona = "sol"`, webhook `greeting`, transition → Converse

- Start Page DTMF routes: 2 → Viktor, 3 → Sol

- [ ] **Step 4: Test multi-persona**

```bash
URL=$(gcloud run services describe night-line --region us-central1 --format='value(status.url)')

# Test Viktor greeting
curl -s -X POST $URL/converse -H "Content-Type: application/json" -d '{
  "sessionInfo":{"session":"t","parameters":{"persona":"viktor"}},
  "pageInfo":{"currentPage":"viktor"},"fulfillmentInfo":{"tag":"greeting"},
  "payload":{"telephony":{"caller_id":"+15551234567"}},"text":""
}' | jq '.fulfillmentResponse.messages[0].text.text[0]'
# Expected: "Viktor here. Pour yourself a drink. What's on your mind?"

# Test Sol greeting
curl -s -X POST $URL/converse -H "Content-Type: application/json" -d '{
  "sessionInfo":{"session":"t","parameters":{"persona":"sol"}},
  "pageInfo":{"currentPage":"sol"},"fulfillmentInfo":{"tag":"greeting"},
  "payload":{"telephony":{"caller_id":"+15551234567"}},"text":""
}' | jq '.fulfillmentResponse.messages[0].text.text[0]'
# Expected: "This is Sol, broadcasting from the void..."
```

- [ ] **Step 5: Dial and test DTMF menu**

Dial the number. Press 1, 2, 3 — each should route to correct persona greeting.

- [ ] **Step 6: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: multi-persona seed script and DTMF wiring"
```

______________________________________________________________________

### Task 8: Landing Page

**Files:**

- Create: `landing/index.html`

- Create: `landing/style.css`

- [ ] **Step 1: Create landing page**

```html
<!-- landing/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Night Line</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="scanlines"></div>
  <main>
    <h1 class="title">Night Line</h1>
    <p class="subtitle">Someone to talk to. After dark.</p>
    <div class="phone-number">
      <span class="label">Call now:</span>
      <span class="number">(XXX) XXX-XXXX</span>
    </div>
    <div class="personas">
      <div class="persona-card"><h2>Luna</h2><p class="tagline">The runaway heiress with a secret</p></div>
      <div class="persona-card"><h2>Viktor</h2><p class="tagline">The noir detective who's seen too much</p></div>
      <div class="persona-card"><h2>Sol</h2><p class="tagline">The stranded astronaut, light-years from home</p></div>
    </div>
    <footer><p class="disclaimer">For entertainment purposes. 18+ only.</p></footer>
  </main>
</body>
</html>
```

- [ ] **Step 2: Create CSS**

```css
/* landing/style.css */
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background:#0a0a0f; color:#e0c0ff; font-family:'Courier New',monospace;
  min-height:100vh; display:flex; align-items:center; justify-content:center; text-align:center;
}
.scanlines {
  position:fixed; inset:0;
  background:repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,.1) 2px, rgba(0,0,0,.1) 4px);
  pointer-events:none; z-index:10;
}
main { position:relative; z-index:1; padding:2rem; max-width:600px; }
.title { font-size:4rem; color:#ff69b4; text-shadow:0 0 20px #ff69b4,0 0 60px #ff69b4; letter-spacing:.3em; margin-bottom:.5rem; }
.subtitle { font-size:1.2rem; color:#8888aa; margin-bottom:2rem; }
.phone-number { background:#151520; border:2px solid #ff69b4; border-radius:8px; padding:1.5rem; margin-bottom:2rem; box-shadow:0 0 30px rgba(255,105,180,.2); }
.phone-number .label { display:block; font-size:.9rem; color:#8888aa; margin-bottom:.5rem; }
.phone-number .number { font-size:2.5rem; color:#fff; letter-spacing:.2em; }
.personas { display:flex; gap:1rem; justify-content:center; flex-wrap:wrap; margin-bottom:2rem; }
.persona-card { background:#151520; border:1px solid #333; border-radius:6px; padding:1rem; width:160px; }
.persona-card h2 { color:#ff69b4; font-size:1.2rem; margin-bottom:.5rem; }
.persona-card .tagline { color:#8888aa; font-size:.8rem; }
.disclaimer { font-size:.7rem; color:#444; margin-top:2rem; }
```

- [ ] **Step 3: Deploy to Cloud Storage**

```bash
gsutil mb gs://<PROJECT>-night-line-landing
gsutil cp landing/index.html landing/style.css gs://<PROJECT>-night-line-landing/
gsutil iam ch allUsers:objectViewer gs://<PROJECT>-night-line-landing
gsutil web set -m index.html gs://<PROJECT>-night-line-landing
echo "https://storage.googleapis.com/<PROJECT>-night-line-landing/index.html"
```

- [ ] **Step 4: Open in browser, verify retro aesthetic and persona cards**

- [ ] **Step 5: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "feat: retro landing page"
```

______________________________________________________________________

### Task 9: Production Deployment — Final Wiring

**Files:**

- Modify: `cx/README.md` — final confirmations

- [ ] **Step 1: Redeploy with min-instances and cpu-boost**

```bash
gcloud run deploy night-line \
  --image gcr.io/<PROJECT>/night-line \
  --region us-central1 \
  --min-instances 1 \
  --cpu-boost \
  --timeout 60 \
  --allow-unauthenticated
```

- [ ] **Step 2: Verify health check and warm instance**

```bash
URL=$(gcloud run services describe night-line --region us-central1 --format='value(status.url)')
curl -s $URL/health
# Expected: {"status":"ok"}
```

- [ ] **Step 3: Finalize Dialogflow CX configuration**

In the CX console, confirm:

- Webhook timeout: 30 seconds

- Partial responses: enabled on Converse Page no-match handler

- Phone Gateway: Essentials Edition, US number live

- Conversation Profile: `phone_call` speech model

- [ ] **Step 4: Run full test suite**

```bash
cd ~/repos/dgflow && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest --forceExit --verbose
```

Expected: All tests PASS.

- [ ] **Step 5: End-to-end phone call**

Dial the number. Verify:

- DTMF menu works (1/2/3)

- Each persona greets in character

- Conversation flows naturally (Gemini responding)

- "politics" → deflection

- "goodbye" → call ends

- Silence 2× → call ends

- Call back → persona remembers facts if extracted

- [ ] **Step 6: Commit**

```bash
cd ~/repos/dgflow && git add -A && git commit -m "chore: production deployment, final integration verification"
```
