// WARNING: This test hits real Vertex AI. Requires valid ADC.
// Skip during CI. Run locally to verify credentials.
import { generateResponse } from "../src/gemini";
import type { Config } from "../src/types";

const liveConfig: Config = {
  port: 8080,
  projectId: process.env.GOOGLE_CLOUD_PROJECT || "",
  location: "us-central1",
  modelId: "gemini-2.5-flash",
  maxHistoryTurns: 20,
  geminiTimeoutMs: 30000,
};

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
  }, 45000);
});
