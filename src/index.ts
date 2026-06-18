import { Firestore } from "@google-cloud/firestore";
import { getConfig } from "./config";
import { createApp } from "./orchestrator";

const config = getConfig();
const db = new Firestore({ projectId: config.projectId });
const app = createApp(db, config);

app.listen(config.port, () => {
  console.log(`Night Line orchestrator listening on port ${config.port}`);
});
