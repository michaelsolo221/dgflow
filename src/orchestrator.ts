import express from "express";
import type { Firestore } from "@google-cloud/firestore";
import type { Config, WebhookRequest, WebhookResponse } from "./types";
import { loadPersona, buildSystemPrompt, checkContentGuard } from "./personas";
import { getOrCreateCaller, getRecentTurns, appendTurn, updateFacts } from "./memory";
import { generateResponse } from "./gemini";
import { extractFacts } from "./facts";
import { createHealthCheck } from "./health";

export function createApp(db: Firestore, config: Config): express.Express {
  const app = express();
  app.use(express.json());
  app.get("/healthz", createHealthCheck(db));

  app.post("/converse", async (req, res) => {
    try {
      const body = req.body as WebhookRequest;
      const personaId = String(body.sessionInfo?.parameters?.persona ?? "");
      const callerPhone = body.payload?.telephony?.caller_id ?? "unknown";
      const userText = body.text ?? "";
      const tag = body.fulfillmentInfo?.tag;

      if (!personaId) {
        return respond(res, "Sorry, something went wrong. Try calling again.", {});
      }

      let persona;
      try {
        persona = await loadPersona(db, personaId);
      } catch {
        return respond(res, "Sorry, I couldn't find that companion. Try calling again.", { persona: personaId });
      }

      if (tag === "greeting") {
        await getOrCreateCaller(db, callerPhone);
        return respond(res, persona.greeting, { persona: personaId });
      }

      const deflection = checkContentGuard(persona, userText);
      if (deflection) {
        return respond(res, deflection, { persona: personaId });
      }

      const caller = await getOrCreateCaller(db, callerPhone);
      const relationship = caller.personas[personaId];
      const facts = relationship?.facts ?? {};
      const history = await getRecentTurns(db, callerPhone, personaId, config.maxHistoryTurns);

      const systemPrompt = buildSystemPrompt(persona, facts);

      const responseText = await generateResponse(
        config,
        systemPrompt,
        history.map((t) => ({
          role: t.role === "caller" ? "user" : "model",
          parts: [{ text: t.text }],
        })),
        userText
      );

      await appendTurn(db, callerPhone, personaId, "caller", userText);
      await appendTurn(db, callerPhone, personaId, personaId, responseText);

      extractFacts(config, responseText, userText)
        .then((newFacts) => {
          if (Object.keys(newFacts).length > 0) {
            updateFacts(db, callerPhone, personaId, newFacts).catch(() => {});
          }
        })
        .catch(() => {});

      return respond(res, responseText, { persona: personaId });
    } catch (err) {
      console.error("Orchestrator error:", err);
      return respond(res, "Hmm, I lost my train of thought. Can you say that again?", {});
    }
  });

  return app;
}

function respond(
  res: express.Response,
  text: string,
  params: Record<string, string | number>
): void {
  const response: WebhookResponse = {
    fulfillmentResponse: { messages: [{ text: { text: [text] } }] },
    sessionInfo: { parameters: params },
  };
  res.json(response);
}
