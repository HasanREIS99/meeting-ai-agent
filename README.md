# Meeting Transcript Analyzer

AI-powered meeting transcript analyzer — upload a `.txt` transcript and receive structured analysis with topic clusters, summaries, action items, and uncertainty flags.

## Architecture

- **Backend:** Python 3.12 + FastAPI
- **LLM:** Anthropic Claude via LiteLLM (provider-agnostic abstraction)
- **Frontend:** Vanilla HTML/CSS/JS served by FastAPI
- **Auth:** GitLab OAuth 2.0 (OIDC)
- **Deployment:** Docker container

See `.factory/ARCHITECTURE.md` for full architecture decisions.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/HasanREIS99/meeting-ai-agent.git
cd meeting-ai-agent/src

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: at minimum set LLM_API_KEY (and LLM_MODEL/LLM_API_BASE
# if you're not using the default AI Hub provider)

# 4. Run
uvicorn meeting_analyzer.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

### Running tests

```bash
cd src
python run_tests.py
# or: pytest
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

## Requirements & docs

See `docs/analysis/` for the complete BRD, FRD, NFR, and test plan.

## License

Internal — adesso
