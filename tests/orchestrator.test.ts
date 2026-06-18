import request from "supertest";
import { Firestore } from "@google-cloud/firestore";

const mockGen = jest.fn().mockResolvedValue("I'm doing great, thanks!");
jest.mock("../src/gemini", () => ({ generateResponse: mockGen }));

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

// eslint-disable-next-line @typescript-eslint/no-var-requires
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
