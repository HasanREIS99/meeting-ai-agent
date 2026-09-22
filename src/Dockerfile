# ── Python ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies (langdetect needs libicu for some locales)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libicu72 && \
    rm -rf /var/lib/apt/lists/*

# ── Dependencies ────────────────────────────────────────────────────
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Application ─────────────────────────────────────────────────────
COPY . .

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "meeting_analyzer.main:app", "--host", "0.0.0.0", "--port", "8000"]
