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
