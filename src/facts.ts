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
