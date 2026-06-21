# Build Steps

1. Gather requirements (gate 1)
1. TDD + user approval (gate 2)
1. Scaffold app (gate 3)
1. Lint clean (gate 4)
1. Generate evals — one eval-writer dispatch per type (gate 5)
1. Push + verify (gate 6)

# Slice 3: Walking Skeleton — First Phone Call

1. [x] Create root agent directory: `night-line/cxas_app/NightLine/agents/root_agent/`
1. [x] Write `instruction.txt` with CXAS XML tags: role, persona, guidelines, constraints, taskflow
1. [x] Write `root_agent.json` with name, displayName, tools: ["end_session"], childAgents: []
1. [x] Update `app.json`: rootAgent set to "root_agent"
1. [ ] (GCP) Run `uv run cxas lint --app-dir night-line/cxas_app/`
1. [ ] (GCP) Run `uv run cxas llm-lint` on root agent instruction.txt
1. [ ] (GCP) Push to platform: `uv run cxas push --app-dir night-line/cxas_app/NightLine --to projects/<id>/locations/us/apps/<app_id>`
1. [ ] (GCP) Verify `gecx-config.json` deployed_app_id is correct
1. [ ] (GCP) Run all 6 build verification gates: `python gate-check.py`
1. [ ] (GCP) Connect telephony in CES Console, claim US number
1. [ ] (GCP) Place real call: verify root agent greeting, clean conversation flow
1. [ ] (GCP) Verify caller_id injection in session logs
