import { VertexAI, type Content } from "@google-cloud/vertexai";
import type { Config } from "./types";

export async function generateResponse(
  config: Config,
  systemPrompt: string,
  history: Content[],
  userText: string
): Promise<string> {
  const vertexAI = new VertexAI({
    project: config.projectId,
    location: config.location,
  });

  const model = vertexAI.getGenerativeModel({
    model: config.modelId,
    systemInstruction: systemPrompt,
  });

  const contents: Content[] = [
    ...history,
    { role: "user", parts: [{ text: userText }] },
  ];

  const result = await model.generateContent({
    contents,
    generationConfig: {
      temperature: 0.9,
      maxOutputTokens: 256,
    },
  });

  const candidate = result.response.candidates?.[0];
  if (!candidate?.content?.parts?.[0]?.text) {
    throw new Error("No response from Gemini");
  }

  return candidate.content.parts[0].text;
}
