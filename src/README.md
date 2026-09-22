# Meeting Transcript Analyzer

AI-powered meeting transcript analyzer — upload a `.txt` transcript and receive structured analysis with topic clusters, summaries, action items, and uncertainty flags.

## Architecture

- **Backend:** Python 3.12 + FastAPI
- **LLM:** Anthropic Claude via LiteLLM (provider-agnostic abstraction)
- **Frontend:** Vanilla HTML/CSS/JS served by FastAPI
- **Auth:** GitLab OAuth 2.0 (OIDC)
- **Deployment:** Docker container

See `.factory/ARCHITECTURE.md` for full architecture decisions (5 ADRs).

## Quick Start

```bash
# 1. Clone & enter source directory
cd src

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run
uvicorn meeting_analyzer.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

## Docker

```bash
docker compose -f src/docker-compose.yml up --build
```

## API

- **Docs:** http://localhost:8000/api/docs
- **Health:** `POST /api/v1/health`
- **Analyze:** `POST /api/v1/analyze` (multipart/form-data with `.txt` file)
- **Validate:** `POST /api/v1/validate` (pre-upload check)
- **Auth:** `POST /api/v1/auth/login`, `/logout`, `/verify`

## Requirements

See `docs/analysis/` for the complete BRD, FRD, NFR, and test plan.

## License

Internal — adesso
