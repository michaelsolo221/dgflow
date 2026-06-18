import type { Config } from "../src/types";

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
