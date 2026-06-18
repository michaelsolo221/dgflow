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
