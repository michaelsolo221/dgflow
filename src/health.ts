import type { Firestore } from "@google-cloud/firestore";
import type { Request, Response } from "express";

export function createHealthCheck(db: Firestore) {
  return async (_req: Request, res: Response): Promise<void> => {
    try {
      await db.collection("personas").limit(1).get();
      res.status(200).json({ status: "ok" });
    } catch {
      res.status(503).json({ status: "unhealthy", detail: "firestore unreachable" });
    }
  };
}
