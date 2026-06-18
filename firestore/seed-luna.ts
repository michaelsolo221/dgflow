import { Firestore } from "@google-cloud/firestore";
import * as fs from "fs";
import * as path from "path";

async function seed() {
  const db = new Firestore({ projectId: process.env.GOOGLE_CLOUD_PROJECT });
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "personas.json"), "utf-8"));

  await db.collection("personas").doc("luna").set(data.luna);
  console.log(`Seeded: luna (${data.luna.display_name}) — voice: ${data.luna.voice}`);
  console.log("Seed complete.");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
