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
