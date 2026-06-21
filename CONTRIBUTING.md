# Contributing to dgflow

## Development Setup

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (Astral's package manager — `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)

### GCP Setup

You need access to the shared GCP project (`superb-tendril-409615`) or your own project. If using your own, replace `superb-tendril-409615` with your project ID throughout.

```bash
# Authenticate
gcloud auth application-default login
gcloud auth application-default print-access-token  # verify

# Enable required APIs (only needed once per project)
gcloud services enable dialogflow.googleapis.com aiplatform.googleapis.com firestore.googleapis.com \
  --project=superb-tendril-409615

# Create Firestore database (only needed once per project)
gcloud firestore databases create --database=night-line --location=nam5 \
  --type=firestore-native --project=superb-tendril-409615

# Create GCS bucket for eval recordings (only needed once per project)
gcloud storage buckets create gs://superb-tendril-409615-night-line-evals \
  --location=us --project=superb-tendril-409615
```

### Clone and Setup

```bash
git clone https://github.com/michaelsolo221/dgflow.git
cd dgflow

# Create venv and install all dependencies (cxas-scrapi is on public PyPI)
uv venv .venv
source .venv/bin/activate
uv sync --extra dev
```

Verify:

```bash
cxas --version
```

### gecx-config.json

`night-line/gecx-config.json` is pre-populated for the shared project. If using your own GCP project, update `gcp_project_id`, `gcs_bucket`, and `deployed_app_id` (the last one is set automatically on first `cxas push`).

### Pre-commit Hooks

```bash
pre-commit install && pre-commit install --hook-type commit-msg
```

## Running Tests

Tests in `tests/` are unit tests that run **offline** — no GCP credentials needed:

```bash
uv run pytest tests/ -v
```

Tool, callback, and eval tests (in `night-line/`) require GCP credentials (ADC set up above).

## Pre-commit Hooks

| Hook | What it does |
|------|-------------|
| `ruff` | Python linting and formatting — auto-fixes on commit |
| `mdformat` | Formats markdown files |
| `pytest` | Runs tests on modified test files only |
| `brand-check-code` | Gemini-powered check on code files — requires ADC credentials |
| `brand-check-msg` | Same check on commit messages — requires ADC credentials |

The brand-check hooks use Gemini via Application Default Credentials. Ensure `gcloud auth application-default login` has been run. To bypass when legitimately referencing third-party names:

```bash
BRAND_CHECK_SKIP=1 git commit -m "your message"
```

Do **not** use this to bypass actual brand name violations.

## CI Checks

- **Ruff** — lint and format check
- **Tests** — `pytest` on Python 3.12
- **Semantic PR titles** — conventional commit format:
  `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

## Project Structure

```
night-line/        Main CXAS agent project
  cxas_app/        Agent configuration files
  evals/           Evaluation test suites
tests/             Offline unit tests
docs/              Conventions, ADRs, agent skill docs
scripts/           Utility scripts (gate-check, seed-personas)
.agents/skills/    CXAS skill definitions
```

## Contributor Workflows

### Add a Persona Agent

Files to touch, in order:

1. **Create agent directory** — `night-line/cxas_app/NightLine/agents/<name>/`
   - `instruction.txt` — XML-tagged (`<role>`, `<persona>`, `<primary_goal>`, `<taskflow>`, `<constraints>`)
   - `<name>.json` — `name`, `displayName`, `tools: ["end_session", "get_memory", "save_turn", "save_memory"]`
1. **Register in app.json** — add `"<name>"` to `childAgents` array
1. **Wire callbacks** — copy `*_callbacks/` directories from an existing persona agent (same callback code, per-agent scope)
1. **Add voice** — update `gecx-config.json` `agentVoiceMapping` with the new agent's voice
1. **Add persona to seed data** — `firestore/personas.json`: add entry with `voice_id`, `tagline`, `name`
1. **Teach the root agent to route** — update `root_agent/instruction.txt` `<step name="Route">`: add description keywords and transfer logic
1. **Add eval coverage** (see `night-line/tdd.md` coverage map):
   - Routing golden: does the root agent transfer to the new persona?
   - Greeting sim: does the persona greet in character?
   - Guardrail golden/sim: per-persona deflection responses
1. **Lint + push** — `cxas lint` then `cxas push` (see conventions.md §2)
1. **Run evals** — `cxas eval run` on the new evals; verify all pass
1. **Test live** — place a call, confirm routing to the new persona and character-consistent responses

See `docs/conventions.md` for naming rules, callback signatures, and platform gotchas.
See `night-line/tdd.md` §Agent Design for architecture decisions.
