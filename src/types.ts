import type { Timestamp } from "@google-cloud/firestore";

export interface Persona {
  id: string;
  display_name: string;
  tagline: string;
  voice: string;
  system_prompt: string;
  greeting: string;
  content_guard: {
    banned: string[];
    deflect_to: string;
  };
}

export interface Turn {
  role: "caller" | string;
  text: string;
  ts: Timestamp;
}

export interface PersonaRelationship {
  call_count: number;
  last_call: Timestamp;
  turns: Turn[];
  facts: Record<string, string>;
}

export interface Caller {
  phone: string;
  first_call: Timestamp;
  last_call: Timestamp;
  personas: Record<string, PersonaRelationship>;
}

export interface WebhookRequest {
  sessionInfo: {
    session: string;
    parameters: Record<string, string | number>;
  };
  pageInfo: {
    currentPage: string;
  };
  fulfillmentInfo: {
    tag: string;
  };
  payload: {
    telephony?: {
      caller_id: string;
    };
  };
  text?: string;
}

export interface WebhookResponse {
  fulfillmentResponse: {
    messages: Array<{
      text: { text: string[] };
    }>;
  };
  sessionInfo?: {
    parameters: Record<string, string | number>;
  };
}

export interface Config {
  port: number;
  projectId: string;
  location: string;
  modelId: string;
  maxHistoryTurns: number;
  geminiTimeoutMs: number;
}
