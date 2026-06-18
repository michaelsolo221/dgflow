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
