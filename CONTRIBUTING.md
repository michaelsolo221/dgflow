# Contributing to dgflow

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Astral's package manager)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)

### GCP Infrastructure Setup

Before running any CXAS commands, provision the required GCP resources:

```bash
# 1. Enable required APIs
gcloud services enable dialogflow.googleapis.com aiplatform.googleapis.com firestore.googleapis.com --project=YOUR_PROJECT_ID

# 2. Authenticate with Application Default Credentials
gcloud auth application-default login
# Verify:
gcloud auth application-default print-access-token

# 3. Create Firestore database in Native mode (nam5)
gcloud firestore databases create --database=night-line --location=nam5 --type=firestore-native --project=YOUR_PROJECT_ID

# 4. Create GCS bucket for audio eval recordings
gcloud storage buckets create gs://YOUR_PROJECT_ID-night-line-evals --location=us --project=YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

### Clone and Setup

```bash
git clone https://github.com/michaelsolo221/dgflow.git
cd dgflow
```

### Project Setup

Run the setup script to create the virtual environment and install core dependencies:

```bash
.agents/skills/cxas-agent-foundry/scripts/setup.sh
```

This creates `.venv/` with `cxas-scrapi` installed. Activate the environment:

```bash
source .venv/bin/activate
```

Then create the project files:

```bash
python .agents/skills/cxas-agent-foundry/scripts/setup-project.py \
  --project-id YOUR_PROJECT_ID \
  --name night-line \
  --modality audio
```

This creates `night-line/gecx-config.json` and `.active-project`. Replace `YOUR_PROJECT_ID` with your GCP project ID.

Finally, install development dependencies:

```bash
uv sync --dev
```

### Pre-commit Hooks

```bash
pre-commit install && pre-commit install --hook-type commit-msg
```

### Verify

```bash
source .venv/bin/activate && cxas --version
```

## Pre-commit Hooks

| Hook | What it does |
|------|-------------|
| `ruff` | Python linting and formatting — auto-fixes on commit |
| `mdformat` | Formats `SKILL.md` files |
| `pytest` | Runs tests on modified test files only |
| `brand-check-code` | Gemini-powered check on code files — blocks non-Google brand names |
| `brand-check-msg` | Same check on commit messages |

## Brand Check Bypass

The brand-check hooks use Gemini to verify code doesn't reference non-Google brand names.
When you legitimately need to reference third-party services (e.g., in tests or docs),
bypass the check with:

```bash
BRAND_CHECK_SKIP=1 git commit -m "your message"
```

This bypass is intentional — use it when the hook blocks legitimate references.
Do **NOT** use it to bypass checks on actual brand name violations.

## CI Checks

- **Ruff** — lint and format check
- **Build** — `uv build` + `twine check`
- **Tests** — `pytest` on Python 3.10 and 3.14
- **Semantic PR titles** — conventional commit format:
  `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

## Project Structure

```
night-line/        Main project source
cxas_app/          Agent configuration files
evals/             Evaluation test suites
.agents/skills/    CXAS skill definitions
```
