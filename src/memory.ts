import { Firestore, Timestamp } from "@google-cloud/firestore";
import type { Caller, Turn, PersonaRelationship } from "./types";

export async function getOrCreateCaller(db: Firestore, phone: string): Promise<Caller> {
  const ref = db.collection("callers").doc(phone);
  const snap = await ref.get();
  if (snap.exists) {
    return snap.data() as Caller;
  }

  const caller: Caller = {
    phone,
    first_call: Timestamp.now(),
    last_call: Timestamp.now(),
    personas: {},
  };
  await ref.set(caller);
  return caller;
}

export async function appendTurn(
  db: Firestore,
  phone: string,
  personaId: string,
  role: string,
  text: string
): Promise<void> {
  const ref = db.collection("callers").doc(phone);
  const turn: Turn = {
    role,
    text,
    ts: Timestamp.now(),
  };

  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const caller = snap.data() as Caller | undefined;
    if (!caller) throw new Error(`Caller not found: ${phone}`);

    const persona: PersonaRelationship = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: Timestamp.now(),
      turns: [],
      facts: {},
    };

    persona.turns.push(turn);
    persona.last_call = Timestamp.now();
    caller.last_call = Timestamp.now();
    caller.personas[personaId] = persona;

    tx.set(ref, caller, { merge: true });
  });
}

export async function getRecentTurns(
  db: Firestore,
  phone: string,
  personaId: string,
  limit: number
): Promise<Turn[]> {
  const snap = await db.collection("callers").doc(phone).get();
  if (!snap.exists) return [];

  const caller = snap.data() as Caller;
  const turns = caller.personas[personaId]?.turns ?? [];
  return turns.slice(-limit);
}

export async function updateFacts(
  db: Firestore,
  phone: string,
  personaId: string,
  facts: Record<string, string>
): Promise<void> {
  const ref = db.collection("callers").doc(phone);
  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const caller = snap.data() as Caller | undefined;
    if (!caller) return;

    const persona: PersonaRelationship = caller.personas[personaId] ?? {
      call_count: 0,
      last_call: Timestamp.now(),
      turns: [],
      facts: {},
    };

    persona.facts = { ...persona.facts, ...facts };
    caller.personas[personaId] = persona;
    tx.set(ref, caller, { merge: true });
  });
}
