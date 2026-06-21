# Build Steps

1. Gather requirements (gate 1)
2. TDD + user approval (gate 2)
3. Scaffold app (gate 3)
4. Lint clean (gate 4)
5. Generate evals — one eval-writer dispatch per type (gate 5)
6. Push + verify (gate 6)


# Slice 3: Walking Skeleton — First Phone Call

1. [x] Create root agent directory: `night-line/cxas_app/NightLine/agents/root_agent/`
2. [x] Write `instruction.txt` with CXAS XML tags: role, persona, guidelines, constraints, taskflow
3. [x] Write `root_agent.json` with name, displayName, tools: ["end_session"], childAgents: []
4. [x] Update `app.json`: rootAgent set to "root_agent"
5. [ ] (GCP) Run `uv run cxas lint --app-dir night-line/cxas_app/`
6. [ ] (GCP) Run `uv run cxas llm-lint` on root agent instruction.txt
7. [ ] (GCP) Push to platform: `uv run cxas push --app-dir night-line/cxas_app/NightLine --to projects/<id>/locations/us/apps/<app_id>`
8. [ ] (GCP) Verify `gecx-config.json` deployed_app_id is correct
9. [ ] (GCP) Run all 6 build verification gates: `python gate-check.py`
10. [ ] (GCP) Connect telephony in CES Console, claim US number
11. [ ] (GCP) Place real call: verify root agent greeting, clean conversation flow
12. [ ] (GCP) Verify caller_id injection in session logs