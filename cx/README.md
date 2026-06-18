# Dialogflow CX Agent — Night Line

⚠️ **Canonical source:** https://github.com/michaelsolo221/night-line-agent

The agent definition lives in a dedicated repo because Dialogflow CX Git integration requires agent-only files at the root (it deletes non-agent files on push).

This `cx/` directory is a local copy for reference. Edit in `night-line-agent` and restore from there.

## Quick restore

```bash
cd night-line-agent && zip -r /tmp/agent.zip agent.json flows/ intents/ webhooks/ generativeSettings/

ACCESS_TOKEN=$(gcloud auth print-access-token)
curl -X POST \
  "https://us-central1-dialogflow.googleapis.com/v3/projects/superb-tendril-409615/locations/us-central1/agents/5c1fa4bf-24b8-4dc6-8de4-91da9aa7e165:restore" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Goog-User-Project: superb-tendril-409615" \
  -H "Content-Type: application/json" \
  -d "{\"agentContent\": \"$(base64 -i /tmp/agent.zip)\"}"
```

See [night-line-agent/README.md](https://github.com/michaelsolo221/night-line-agent/blob/main/README.md) for full docs.
