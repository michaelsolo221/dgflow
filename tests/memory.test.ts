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
