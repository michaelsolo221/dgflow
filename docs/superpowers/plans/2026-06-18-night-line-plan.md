### Task 1: Project Scaffold, Types, and Config

**Files:**
- Create: `night-line/package.json`
- Create: `night-line/tsconfig.json`
- Create: `night-line/.env.example`
- Create: `night-line/src/types.ts`
- Create: `night-line/src/config.ts`

**Interfaces:**
- Produces: `types.ts` exports types used by all subsequent tasks
- Produces: `config.ts` exports `getConfig()` returning typed `Config`

- [ ] **Step 1: Create project directory and package.json**

```bash
mkdir -p night-line/src night-line/tests night-line/firestore night-line/landing night-line/cx
```

```json
// night-line/package.json
{
  "name": "night-line",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
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
    "@types/supertest": "^6.0.0",
    "@firebase/rules-unit-testing": "^3.0.0"
  },
  "jest": {
    "preset": "ts-jest",
    "testEnvironment": "node",
    "roots": ["<rootDir>/tests"]
  }
}
```

- [ ] **Step 2: Install dependencies**

```bash
cd night-line && npm install
```

- [ ] **Step 3: Create tsconfig.json**

```json
// night-line/tsconfig.json
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

- [ ] **Step 4: Create types.ts**

```typescript
// night-line/src/types.ts
import type { Timestamp } from "@google-cloud/firestore";

/** Persona definition loaded from Firestore personas/{id} */
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

/** A single conversation turn */
export interface Turn {
  role: "caller" | string;  // string = persona id (e.g. "luna")
  text: string;
  ts: Timestamp;
}

/** Per-persona relationship data within a caller doc */
export interface PersonaRelationship {
  call_count: number;
  last_call: Timestamp;
  turns: Turn[];
  facts: Record<string, string>;  // e.g. { "name": "Dave", "pet": "... }
}

/** Caller document in Firestore callers/{phone_e164} */
export interface Caller {
  phone: string;
  first_call: Timestamp;
  last_call: Timestamp;
  personas: Record<string, PersonaRelationship>;
}

/** Shape of Dialogflow WebhookRequest (subset we use) */
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
  intentInfo?: {
    parameters: Record<string, unknown>;
  };
}

/** Shape of Dialogflow WebhookResponse (subset we return) */
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

/** App configuration from environment */
export interface Config {
  port: number;
  projectId: string;
  location: string;          // Vertex AI region, e.g. "us-central1"
  modelId: string;           // "gemini-3.1-flash-lite"
  maxHistoryTurns: number;   // sliding window size, default 20
  geminiTimeoutMs: number;   // default 25000
}
```

- [ ] **Step 5: Create config.ts**

```typescript
// night-line/src/config.ts
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

- [ ] **Step 6: Create .env.example**

```bash
# night-line/.env.example
PORT=8080
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-3.1-flash-lite
MAX_HISTORY_TURNS=20
GEMINI_TIMEOUT_MS=25000
```

- [ ] **Step 7: Verify build compiles**

```bash
cd night-line && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 8: Commit**

```bash
cd night-line && git init && git add -A && git commit -m "feat: project scaffold with types and config"
```
```

---

### Task 2: Persona Definitions and Content Guard

**Files:**
- Create: `night-line/firestore/personas.json`
- Create: `night-line/src/personas.ts`
- Create: `night-line/tests/persona.test.ts`

**Interfaces:**
- Consumes: `Persona` from `types.ts`
- Produces: `loadPersona(personaId: string) → Persona`
- Produces: `buildSystemPrompt(persona: Persona, facts: Record<string,string>) → string`
- Produces: `checkContentGuard(persona: Persona, text: string) → string | null`  (null = allowed, string = deflection response)

- [ ] **Step 1: Create persona seed data**

```json
// night-line/firestore/personas.json
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
    "system_prompt": "You are Sol, an astronaut stranded in deep space. You're alone on a research vessel, talking to Earth via a delayed transmission. You're thoughtful, poetic, and a little unhinged from isolation — but in a charming way. You describe the stars, the silence, the strange beauty of being alone. You're fascinated by mundane Earth things the caller mentions ('What's rain like? I've forgotten.'). Keep responses under 3 sentences. PG-13.",
    "greeting": "This is Sol, broadcasting from the void. It's good to hear a voice that isn't my own echo. Who's this?",
    "content_guard": {
      "banned": ["politics", "violence", "self-harm", "suicide", "explicit sex"],
      "deflect_to": "The signal's breaking up. Let's talk about something else — what do you miss most about Earth?"
    }
  }
}
```

- [ ] **Step 2: Write failing test for loadPersona**

```typescript
// night-line/tests/persona.test.ts
import { loadPersona } from "../src/personas";
import { getFirestore, clearFirestore, seedPersona } from "./setup";

describe("loadPersona", () => {
  it("loads a persona by ID", async () => {
    const db = getFirestore();
    await seedPersona(db, {
      id: "luna",
      display_name: "Luna",
      tagline: "Test",
      voice: "en-US-Studio-O",
      system_prompt: "You are Luna.",
      greeting: "Hey.",
      content_guard: { banned: [], deflect_to: "..." }
    });

    const persona = await loadPersona(db, "luna");
    expect(persona.id).toBe("luna");
    expect(persona.system_prompt).toBe("You are Luna.");
  });

  it("throws when persona not found", async () => {
    const db = getFirestore();
    await expect(loadPersona(db, "nonexistent")).rejects.toThrow("Persona not found: nonexistent");
  });
});

describe("checkContentGuard", () => {
  it("returns null for safe text", () => {
    const persona = makeTestPersona();
    const result = checkContentGuard(persona, "I had a long day at work.");
    expect(result).toBeNull();
  });

  it("returns deflection for banned topic", () => {
    const persona = makeTestPersona();
    const result = checkContentGuard(persona, "What do you think about politics?");
    expect(result).toBe(persona.content_guard.deflect_to);
  });
});

function makeTestPersona() {
  return {
    id: "test",
    display_name: "Test",
    tagline: "",
    voice: "en-US-Studio-O",
    system_prompt: "You are a test.",
    greeting: "Hi.",
    content_guard: {
      banned: ["politics"],
      deflect_to: "Let's not go there."
    }
  };
}
```

- [ ] **Step 3: Write setup.ts for Firestore emulator**

```typescript
// night-line/tests/setup.ts
import { Firestore } from "@google-cloud/firestore";
import type { Persona } from "../src/types";

let _db: Firestore | null = null;

export function getFirestore(): Firestore {
  if (!_db) {
    _db = new Firestore({
      projectId: "night-line-test",
      host: process.env.FIRESTORE_EMULATOR_HOST || "localhost:8080",
    });
  }
  return _db;
}

export async function clearFirestore(db: Firestore): Promise<void> {
  // Delete all docs in test collections
  const cols = await db.listCollections();
  await Promise.all(cols.map(async (col) => {
    const docs = await col.listDocuments();
    await Promise.all(docs.map((d) => d.delete()));
  }));
}

export async function seedPersona(db: Firestore, persona: Persona): Promise<void> {
  await db.collection("personas").doc(persona.id).set(persona);
}
```

- [ ] **Step 4: Run test — expect FAIL (no implementation yet)**

```bash
# Start Firestore emulator first
gcloud emulators firestore start --host-port=localhost:8080 &
# Wait a moment, then:
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/persona.test.ts
```
Expected: FAIL — `Cannot find module '../src/personas'`

- [ ] **Step 5: Implement personas.ts**

```typescript
// night-line/src/personas.ts
import type { Firestore } from "@google-cloud/firestore";
import type { Persona } from "./types";

/**
 * Load a persona definition from Firestore.
 */
export async function loadPersona(db: Firestore, personaId: string): Promise<Persona> {
  const snap = await db.collection("personas").doc(personaId).get();
  if (!snap.exists) {
    throw new Error(`Persona not found: ${personaId}`);
  }
  return snap.data() as Persona;
}

/**
 * Build the full system prompt from persona + caller facts.
 */
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

/**
 * Check if caller's text contains banned topics. Returns deflection text or null.
 */
export function checkContentGuard(persona: Persona, text: string): string | null {
  const lower = text.toLowerCase();
  const hit = persona.content_guard.banned.find((topic) => lower.includes(topic));
  return hit ? persona.content_guard.deflect_to : null;
}
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/persona.test.ts -v
```
Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: persona loading, prompt builder, and content guard"
```

---

### Task 3: Gemini Client Wrapper

**Files:**
- Create: `night-line/src/gemini.ts`
- Create: `night-line/tests/gemini.test.ts`

**Interfaces:**
- Consumes: `Config` from `config.ts`
- Produces: `generateResponse(config, systemPrompt, history, userText) → Promise<string>`

- [ ] **Step 1: Write failing test**

```typescript
// night-line/tests/gemini.test.ts
// NOTE: This test uses a mock since real Vertex AI requires auth.
// For integration testing, use a real API key.
import { generateResponse } from "../src/gemini";

jest.mock("@google-cloud/vertexai", () => {
  const mockGenerateContent = jest.fn();
  return {
    VertexAI: jest.fn().mockImplementation(() => ({
      getGenerativeModel: jest.fn().mockReturnValue({
        generateContent: mockGenerateContent,
      }),
    })),
    __mockGenerateContent: mockGenerateContent, // expose for tests
  };
});

import { __mockGenerateContent } from "@google-cloud/vertexai";

describe("generateResponse", () => {
  it("returns the model's text response", async () => {
    __mockGenerateContent.mockResolvedValueOnce({
      response: {
        candidates: [{
          content: {
            parts: [{ text: "Well, let me tell you a story..." }],
          },
        }],
      },
    });

    const config = {
      projectId: "test",
      location: "us-central1",
      modelId: "gemini-3.1-flash-lite",
      geminiTimeoutMs: 25000,
    };

    const result = await generateResponse(
      config as any,
      "You are a test assistant.",
      [],
      "Hello"
    );

    expect(result).toBe("Well, let me tell you a story...");
    expect(__mockGenerateContent).toHaveBeenCalledTimes(1);
  });

  it("throws on empty response", async () => {
    __mockGenerateContent.mockResolvedValueOnce({
      response: { candidates: [] },
    });

    const config = { geminiTimeoutMs: 1000 } as any;
    await expect(
      generateResponse(config, "prompt", [], "hi")
    ).rejects.toThrow("No response from Gemini");
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd night-line && npx jest tests/gemini.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement gemini.ts**

```typescript
// night-line/src/gemini.ts
import { VertexAI, type Content } from "@google-cloud/vertexai";
import type { Config } from "./config";

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

- [ ] **Step 4: Run test — expect PASS**

```bash
cd night-line && npx jest tests/gemini.test.ts -v
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: Gemini 3.1 Flash-Lite client wrapper"
```

---

### Task 4: Memory Layer — Firestore CRUD

**Files:**
- Create: `night-line/src/memory.ts`
- Create: `night-line/tests/memory.test.ts`

**Interfaces:**
- Consumes: `Caller`, `Turn`, `PersonaRelationship` from `types.ts`
- Produces: `getOrCreateCaller(db, phone) → Promise<Caller>`
- Produces: `appendTurn(db, phone, personaId, role, text) → Promise<void>`
- Produces: `getRecentTurns(db, phone, personaId, limit) → Promise<Turn[]>`
- Produces: `updateFacts(db, phone, personaId, facts) → Promise<void>`

- [ ] **Step 1: Write failing tests**

```typescript
// night-line/tests/memory.test.ts
import { getFirestore, clearFirestore } from "./setup";
import { getOrCreateCaller, appendTurn, getRecentTurns, updateFacts } from "../src/memory";
import type { Firestore } from "@google-cloud/firestore";

describe("memory", () => {
  let db: Firestore;

  beforeEach(async () => {
    db = getFirestore();
    await clearFirestore(db);
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
    it("appends turns and retrieves them in order", async () => {
      await getOrCreateCaller(db, "+15551234567");
      await appendTurn(db, "+15551234567", "luna", "luna", "Hey there.");
      await appendTurn(db, "+15551234567", "luna", "caller", "Hi Luna!");
      await appendTurn(db, "+15551234567", "luna", "luna", "How was your day?");

      const turns = await getRecentTurns(db, "+15551234567", "luna", 2);
      expect(turns).toHaveLength(2);
      expect(turns[0].text).toBe("Hi Luna!");
      expect(turns[1].text).toBe("How was your day?");
    });
  });

  describe("updateFacts", () => {
    it("merges facts into existing facts", async () => {
      await getOrCreateCaller(db, "+15551234567");
      await updateFacts(db, "+15551234567", "luna", { name: "Dave" });
      await updateFacts(db, "+15551234567", "luna", { job: "accountant" });

      const caller = await getOrCreateCaller(db, "+15551234567");
      expect(caller.personas["luna"].facts).toEqual({
        name: "Dave",
        job: "accountant",
      });
    });
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/memory.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement memory.ts**

```typescript
// night-line/src/memory.ts
import type { Firestore, Timestamp } from "@google-cloud/firestore";
import type { Caller, Turn, PersonaRelationship } from "./types";

export async function getOrCreateCaller(db: Firestore, phone: string): Promise<Caller> {
  const ref = db.collection("callers").doc(phone);
  const snap = await ref.get();
  if (snap.exists) {
    return snap.data() as Caller;
  }

  const caller: Caller = {
    phone,
    first_call: db.Timestamp.now(),
    last_call: db.Timestamp.now(),
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
    ts: db.Timestamp.now(),
  };

  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const caller = snap.data() as Caller | undefined;
    if (!caller) throw new Error(`Caller not found: ${phone}`);

    const persona = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: db.Timestamp.now(),
      turns: [],
      facts: {},
    };

    persona.turns.push(turn);
    caller.last_call = db.Timestamp.now();
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

    const persona = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: db.Timestamp.now(),
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
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/memory.test.ts -v
```
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: Firestore memory layer for caller profiles and turn logs"
```

---

### Task 5: Fact Extraction from LLM Responses

**Files:**
- Create: `night-line/src/facts.ts`
- Create: `night-line/tests/facts.test.ts`

**Interfaces:**
- Consumes: `generateResponse` from `gemini.ts`, `Config` from `config.ts`
- Produces: `extractFacts(config, lastResponse, callerUtterance) → Promise<Record<string,string>>`

- [ ] **Step 1: Write failing test**

```typescript
// night-line/tests/facts.test.ts
import { extractFacts } from "../src/facts";

// This test verifies the extraction prompt, not the actual LLM call.
jest.mock("../src/gemini", () => ({
  generateResponse: jest.fn().mockResolvedValue(
    '{"name": "Dave", "job": "accountant"}'
  ),
}));

import { generateResponse } from "../src/gemini";

describe("extractFacts", () => {
  it("parses JSON facts from LLM response", async () => {
    const config = { geminiTimeoutMs: 5000 } as any;
    const facts = await extractFacts(
      config,
      "Nice to meet you, Dave. What kind of accounting?",
      "I'm Dave, I'm an accountant."
    );

    expect(facts).toEqual({ name: "Dave", job: "accountant" });
  });

  it("returns empty object on malformed JSON", async () => {
    (generateResponse as jest.Mock).mockResolvedValueOnce("not json");
    const config = { geminiTimeoutMs: 5000 } as any;
    const facts = await extractFacts(config, "OK", "Hi");
    expect(facts).toEqual({});
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd night-line && npx jest tests/facts.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement facts.ts**

```typescript
// night-line/src/facts.ts
import { generateResponse } from "./gemini";
import type { Config } from "./config";

const FACTS_SYSTEM = `You extract key facts about a person from a conversation.
Return ONLY a JSON object with string values. Use keys like "name", "job", "pet", "hobby", "location", etc.
If you learn nothing new, return {}. Never include sensitive information.
Example: {"name": "Alice", "job": "engineer"}`;

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
    // Gemini may wrap in markdown code fences
    const cleaned = raw.replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "");
    const parsed = JSON.parse(cleaned);
    if (typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed as Record<string, string>;
  } catch {
    return {};
  }
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd night-line && npx jest tests/facts.test.ts -v
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: fact extraction from LLM responses"
```

---

### Task 6: Orchestrator Core — POST /converse Endpoint

**Files:**
- Create: `night-line/src/orchestrator.ts`
- Modify: `night-line/src/index.ts`
- Create: `night-line/tests/orchestrator.test.ts`

**Interfaces:**
- Consumes: All previous modules (personas, memory, gemini, facts, config)
- Produces: Express app with `POST /converse` returning `WebhookResponse`

- [ ] **Step 1: Write integration test**

```typescript
// night-line/tests/orchestrator.test.ts
import request from "supertest";
import { createApp } from "../src/orchestrator";
import { getFirestore, clearFirestore, seedPersona } from "./setup";
import type { Firestore } from "@google-cloud/firestore";

// Mock Gemini to avoid real API calls
jest.mock("../src/gemini", () => ({
  generateResponse: jest.fn().mockResolvedValue("I'm doing great, thanks for asking!"),
}));

let db: Firestore;

beforeEach(async () => {
  db = getFirestore();
  await clearFirestore(db);
  await seedPersona(db, {
    id: "luna",
    display_name: "Luna",
    tagline: "Test",
    voice: "en-US-Studio-O",
    system_prompt: "You are Luna.",
    greeting: "Hey there.",
    content_guard: { banned: ["politics"], deflect_to: "Let's not go there." },
  });
});

describe("POST /converse", () => {
  it("returns a greeting for a new caller on first turn", async () => {
    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: {
          session: "test-session",
          parameters: { persona: "luna" },
        },
        pageInfo: { currentPage: "luna" },
        fulfillmentInfo: { tag: "greeting" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hello",
      });

    expect(res.status).toBe(200);
    const body = res.body;
    expect(body.fulfillmentResponse.messages[0].text.text[0]).toBeTruthy();
    expect(body.sessionInfo.parameters.persona).toBe("luna");
  });

  it("returns deflection for banned content", async () => {
    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: {
          session: "test-session",
          parameters: { persona: "luna" },
        },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "What do you think about politics?",
      });

    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toBe("Let's not go there.");
  });

  it("returns error response when persona not found", async () => {
    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: { session: "test", parameters: { persona: "nobody" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hi",
      });

    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toContain("Sorry");
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/orchestrator.test.ts
```
Expected: FAIL — `createApp` not found.

- [ ] **Step 3: Implement orchestrator.ts**

```typescript
// night-line/src/orchestrator.ts
import express from "express";
import type { Firestore } from "@google-cloud/firestore";
import type { Config, WebhookRequest, WebhookResponse } from "./types";
import { loadPersona, buildSystemPrompt, checkContentGuard } from "./personas";
import { getOrCreateCaller, getRecentTurns, appendTurn, updateFacts } from "./memory";
import { generateResponse } from "./gemini";
import { extractFacts } from "./facts";

export function createApp(db: Firestore, config: Config): express.Express {
  const app = express();
  app.use(express.json());

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

      // Handle greeting tag (first interaction with persona)
      if (tag === "greeting") {
        await getOrCreateCaller(db, callerPhone);
        return respond(res, persona.greeting, { persona: personaId });
      }

      // Content guard
      const deflection = checkContentGuard(persona, userText);
      if (deflection) {
        return respond(res, deflection, { persona: personaId });
      }

      // Load caller + conversation history
      const caller = await getOrCreateCaller(db, callerPhone);
      const relationship = caller.personas[personaId];
      const facts = relationship?.facts ?? {};
      const history = await getRecentTurns(db, callerPhone, personaId, config.maxHistoryTurns);

      // Build system prompt
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

      // Save turn
      await appendTurn(db, callerPhone, personaId, "caller", userText);
      await appendTurn(db, callerPhone, personaId, personaId, responseText);

      // Extract facts (fire-and-forget, don't block response)
      extractFacts(config, responseText, userText)
        .then((newFacts) => {
          if (Object.keys(newFacts).length > 0) {
            updateFacts(db, callerPhone, personaId, newFacts);
          }
        })
        .catch(() => { /* best effort */ });

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
    fulfillmentResponse: {
      messages: [{ text: { text: [text] } }],
    },
    sessionInfo: { parameters: params },
  };
  res.json(response);
}
```

- [ ] **Step 4: Create index.ts (Express entry point)**

```typescript
// night-line/src/index.ts
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
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/orchestrator.test.ts -v
```
Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: orchestrator core — POST /converse endpoint"
```

---

### Task 7: Error Handling, Timeouts, and Resilience

**Files:**
- Modify: `night-line/src/orchestrator.ts` — add timeout wrapper, Firestore fallback
- Modify: `night-line/tests/orchestrator.test.ts` — add error scenario tests

**Interfaces:**
- No new exports. Internal resilience improvements.

- [ ] **Step 1: Add error scenario tests**

Append to `night-line/tests/orchestrator.test.ts`:

```typescript
describe("POST /converse — error handling", () => {
  it("returns fallback when Gemini throws", async () => {
    const { generateResponse } = require("../src/gemini");
    generateResponse.mockRejectedValueOnce(new Error("API timeout"));

    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: { session: "test", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        payload: { telephony: { caller_id: "+15551234567" } },
        text: "Hi",
      });

    expect(res.status).toBe(200);
    expect(res.body.fulfillmentResponse.messages[0].text.text[0])
      .toContain("lost my train of thought");
  });

  it("returns fallback when no persona in session", async () => {
    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: { session: "test", parameters: {} },
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
    const app = createApp(db, { geminiTimeoutMs: 5000 } as any);

    const res = await request(app)
      .post("/converse")
      .send({
        sessionInfo: { session: "test", parameters: { persona: "luna" } },
        pageInfo: { currentPage: "converse" },
        fulfillmentInfo: { tag: "converse" },
        text: "Hi",
      });

    expect(res.status).toBe(200);
    const text = res.body.fulfillmentResponse.messages[0].text.text[0];
    // Should still work with "unknown" caller
    expect(text).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests — expect 3 new FAILs**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest tests/orchestrator.test.ts -v
```
Expected: some pass, 3 new error-handling tests FAIL (the existing error handler already catches generic errors, but we need to verify Gemini throw and no-persona cases work).

- [ ] **Step 3: The existing orchestrator already handles these**

The current `try/catch` in `POST /converse` catches Gemini errors. The no-persona check is in place. Missing payload falls through to "unknown" caller which is created. No code changes needed — these tests should pass if the orchestrator's error handling is correct.

If any fail, fix the specific handler in orchestrator.ts. Common fixes:
- Ensure Gemini errors are caught in the outer try/catch
- Ensure `callerPhone` defaults to `"unknown"` when `payload?.telephony?.caller_id` is missing (already: `?? "unknown"`)

- [ ] **Step 4: Run full test suite**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest --forceExit
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd night-line && git add -A && git commit -m "test: error handling scenarios for orchestrator"
```

---

### Task 8: Dialogflow CX Agent Setup

**Files:**
- Create: `night-line/cx/README.md`

**Interfaces:**
- No code. This task documents the console setup.

- [ ] **Step 1: Write CX setup reference**

Create `night-line/cx/README.md`:

```markdown
# Dialogflow CX Agent Setup

## Prerequisites
- GCP project with Dialogflow CX API enabled
- Essentials Edition (not Trial — caller ID requires paid tier)
- Cloud Run orchestrator deployed and URL known

## 1. Create Agent
- Console: Conversational Agents → Create Agent
- Name: "Night Line"
- Default language: en-US
- Time zone: (your timezone)

## 2. Enable Phone Gateway
- Manage → Integrations → Phone Gateway
- Claim a US phone number
- Set up billing (Essentials Edition)

## 3. Create Conversation Profile
- Create a profile with:
  - Speech model: `phone_call` (optimized for telephony)
  - Language: en-US

## 4. Create Webhook
- Manage → Webhooks → Create
- Name: "orchestrator"
- URL: `https://<cloud-run-url>/converse`
- Auth: ID Token (same GCP project)
- Timeout: 30 seconds

## 5. Build Flows and Pages

### Start Page
- Entry fulfillment: TTS agent says:
  "Welcome to the Night Line. Pick your companion.
   Press 1 for Luna, the runaway heiress…
   Press 2 for Viktor, the noir detective…
   Press 3 for Sol, the stranded astronaut…"
- Routes:
  - DTMF condition: `$session.params.dtmf_digit = 1` → Luna Page
  - DTMF condition: `$session.params.dtmf_digit = 2` → Viktor Page
  - DTMF condition: `$session.params.dtmf_digit = 3` → Sol Page

### Luna Page
- Entry: Parameter preset: `persona = "luna"`
- Entry: Webhook fulfillment (tag: `greeting`) → calls POST /converse
- Transition: → Converse Page

### Viktor Page
- Entry: Parameter preset: `persona = "viktor"`
- Entry: Webhook fulfillment (tag: `greeting`)
- Transition: → Converse Page

### Sol Page
- Entry: Parameter preset: `persona = "sol"`
- Entry: Webhook fulfillment (tag: `greeting`)
- Transition: → Converse Page

### Converse Page
- Event handlers:

  1. **sys.no-match-default** (fires on every unrecognized utterance)
     - Webhook fulfillment (tag: `converse`)
     - Enable: Return Partial Response (filler: "Hmm…")

  2. **sys.no-input-default** (condition: `$session.params.silence_count < 2`)
     - Static TTS: "Still with me?"
     - Parameter preset: `silence_count = $sys.func.ADD($session.params.silence_count, 1)`

  3. **sys.no-input-default** (condition: `$session.params.silence_count >= 2`)
     - Static TTS: "Alright, take care. Call back anytime."
     - Transition → End Session

  4. **sys.webhook.failed**
     - Static TTS: "Hmm, lost my train of thought. Say that again?"

- Routes:
  - Intent: "goodbye" (training phrases: "goodbye", "bye", "good night", "I have to go", "talk later")
    → Goodbye Page

### Goodbye Page
- Entry: Static TTS: "Goodnight. Call again soon."
- Transition → End Session

## 6. Voice Configuration
Set WaveNet voice per page in Conversation Profile or via SSML in webhook responses.
By default, use the profile's voice. Consider SSML `<voice>` tags if fine control needed.

## 7. Test
- Use the CX Simulator to test the flow
- Dial the number and speak
- Verify:
  - DTMF menu works
  - Greeting is spoken
  - Conversation loops until hangup
  - "goodbye" ends call
  - Silence after 2 prompts ends call
```

- [ ] **Step 2: Commit**

```bash
cd night-line && git add -A && git commit -m "docs: Dialogflow CX agent setup reference"
```

---

### Task 9: Firestore Seed Script

**Files:**
- Create: `night-line/firestore/seed.ts`

- [ ] **Step 1: Write seed script**

```typescript
// night-line/firestore/seed.ts
import { Firestore } from "@google-cloud/firestore";
import * as fs from "fs";
import * as path from "path";

async function seed() {
  const db = new Firestore({ projectId: process.env.GOOGLE_CLOUD_PROJECT });
  const personasPath = path.join(__dirname, "personas.json");
  const personas = JSON.parse(fs.readFileSync(personasPath, "utf-8"));

  for (const [id, persona] of Object.entries(personas)) {
    await db.collection("personas").doc(id).set(persona);
    console.log(`Seeded persona: ${id}`);
  }

  console.log("Seed complete.");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
```

- [ ] **Step 2: Dry-run seed (requires GCP auth)**

```bash
cd night-line && GOOGLE_CLOUD_PROJECT=<your-project> npx ts-node firestore/seed.ts
```
Expected: Three persona docs written to Firestore.

- [ ] **Step 3: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: Firestore seed script for personas"
```

---

### Task 10: Docker + Cloud Run Deployment

**Files:**
- Create: `night-line/Dockerfile`
- Create: `night-line/.dockerignore`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# night-line/Dockerfile
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

- [ ] **Step 2: Create .dockerignore**

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

- [ ] **Step 3: Build and test locally**

```bash
cd night-line && docker build -t night-line .
docker run -p 8080:8080 -e GOOGLE_CLOUD_PROJECT=<your-project> -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/key.json -v $GOOGLE_APPLICATION_CREDENTIALS:/tmp/key.json night-line
```
Expected: "Night Line orchestrator listening on port 8080"

- [ ] **Step 4: Deploy to Cloud Run**

```bash
gcloud builds submit --tag gcr.io/<project>/night-line
gcloud run deploy night-line \
  --image gcr.io/<project>/night-line \
  --region us-central1 \
  --min-instances 1 \
  --cpu-boost \
  --timeout 60 \
  --allow-unauthenticated
```

- [ ] **Step 5: Verify deployment**

```bash
curl -X POST https://<cloud-run-url>/converse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionInfo": {"session": "test", "parameters": {"persona": "luna"}},
    "pageInfo": {"currentPage": "converse"},
    "fulfillmentInfo": {"tag": "converse"},
    "payload": {"telephony": {"caller_id": "+15551234567"}},
    "text": "Hi Luna, how are you?"
  }'
```
Expected: JSON response with `fulfillmentResponse.messages[0].text.text[0]` containing a Luna-style response.

- [ ] **Step 6: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: Dockerfile and Cloud Run deployment"
```

---

### Task 11: Landing Page

**Files:**
- Create: `night-line/landing/index.html`
- Create: `night-line/landing/style.css`

- [ ] **Step 1: Create landing page**

```html
<!-- night-line/landing/index.html -->
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
      <div class="persona-card">
        <h2>Luna</h2>
        <p class="tagline">The runaway heiress with a secret</p>
      </div>
      <div class="persona-card">
        <h2>Viktor</h2>
        <p class="tagline">The noir detective who's seen too much</p>
      </div>
      <div class="persona-card">
        <h2>Sol</h2>
        <p class="tagline">The stranded astronaut, light-years from home</p>
      </div>
    </div>

    <footer>
      <p class="disclaimer">$0.99/minute. 18+ only. For entertainment purposes.</p>
    </footer>
  </main>
</body>
</html>
```

- [ ] **Step 2: Create retro CSS**

```css
/* night-line/landing/style.css */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #0a0a0f;
  color: #e0c0ff;
  font-family: 'Courier New', Courier, monospace;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
  position: relative;
}

.scanlines {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.1) 2px,
    rgba(0, 0, 0, 0.1) 4px
  );
  pointer-events: none;
  z-index: 10;
}

main {
  position: relative;
  z-index: 1;
  padding: 2rem;
  max-width: 600px;
}

.title {
  font-size: 4rem;
  color: #ff69b4;
  text-shadow: 0 0 20px #ff69b4, 0 0 60px #ff69b4;
  letter-spacing: 0.3em;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.2rem;
  color: #8888aa;
  margin-bottom: 2rem;
}

.phone-number {
  background: #151520;
  border: 2px solid #ff69b4;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 0 30px rgba(255, 105, 180, 0.2);
}

.phone-number .label {
  display: block;
  font-size: 0.9rem;
  color: #8888aa;
  margin-bottom: 0.5rem;
}

.phone-number .number {
  font-size: 2.5rem;
  color: #ffffff;
  letter-spacing: 0.2em;
}

.personas {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}

.persona-card {
  background: #151520;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 1rem;
  width: 160px;
}

.persona-card h2 {
  color: #ff69b4;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.persona-card .tagline {
  color: #8888aa;
  font-size: 0.8rem;
}

.disclaimer {
  font-size: 0.7rem;
  color: #444;
  margin-top: 2rem;
}
```

- [ ] **Step 3: Deploy to Cloud Storage**

```bash
gsutil mb gs://night-line-landing
gsutil cp landing/index.html landing/style.css gs://night-line-landing/
gsutil iam ch allUsers:objectViewer gs://night-line-landing
gsutil web set -m index.html gs://night-line-landing
```

- [ ] **Step 4: Verify**

Open `https://storage.googleapis.com/night-line-landing/index.html` in a browser. Verify retro aesthetic, persona cards, and phone number display.

- [ ] **Step 5: Commit**

```bash
cd night-line && git add -A && git commit -m "feat: retro landing page"
```

---

### Task 12: Final Integration Verification

- [ ] **Step 1: Run full test suite**

```bash
cd night-line && FIRESTORE_EMULATOR_HOST=localhost:8080 npx jest --forceExit --verbose
```
Expected: All tests PASS.

- [ ] **Step 2: Manual end-to-end test**

1. Deploy orchestrator to Cloud Run (Task 10)
2. Seed Firestore with personas (Task 9)
3. Configure Dialogflow CX agent (Task 8)
4. Dial the phone number
5. Verify:
   - DTMF menu plays
   - Press 1 → Luna greeting plays
   - Speak → Luna responds in character
   - Say "politics" → deflection
   - Say "goodbye" → call ends
   - Stay silent 3 times → call ends
   - Call back → Luna remembers you (if facts were extracted)

- [ ] **Step 3: Commit any fixes**

```bash
cd night-line && git add -A && git commit -m "chore: final integration verification"
```
