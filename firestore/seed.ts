import { Firestore } from "@google-cloud/firestore";
import * as fs from "fs";
import * as path from "path";

async function seed() {
  const db = new Firestore({ projectId: process.env.GOOGLE_CLOUD_PROJECT });
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "personas.json"), "utf-8"));

  const personas = data as Record<string, {
    id: string;
    display_name: string;
    voice: string;
  }>;

  for (const [id, persona] of Object.entries(personas)) {
    await db.collection("personas").doc(id).set(persona);
    console.log(`Seeded: ${id} (${persona.display_name}) — voice: ${persona.voice}`);
  }

  const validVoices = [
    "en-US-Studio-O", "en-US-Studio-M", "en-US-Studio-Q",
    "en-US-Wavenet-A", "en-US-Wavenet-B", "en-US-Wavenet-C",
    "en-US-Wavenet-D", "en-US-Wavenet-E", "en-US-Wavenet-F",
    "en-US-Neural2-A", "en-US-Neural2-B", "en-US-Neural2-C",
  ];
  for (const [id, persona] of Object.entries(personas)) {
    if (!validVoices.includes(persona.voice)) {
      console.warn(`WARNING: ${id} uses voice '${persona.voice}' — may not be a valid WaveNet ID`);
    }
  }

  console.log("Seed complete.");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
