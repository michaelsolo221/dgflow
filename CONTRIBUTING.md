# Contributing to dgflow

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Astral's package manager)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)

### Clone and Setup

```bash
git clone https://github.com/your-org/dgflow.git
cd dgflow
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
