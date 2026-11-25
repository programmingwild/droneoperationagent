# syntax=docker/dockerfile:1
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only torch first to keep the image lean, then the rest.
COPY requirements.txt ./
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    && pip install -r requirements.txt

COPY backend ./backend
COPY scripts ./scripts
COPY data ./data
COPY --from=web /web/dist ./web/dist

# Bake the corpus + embeddings into the image (fast, offline cold start).
RUN python scripts/make_sample_assets.py && python scripts/make_sample_paper.py \
    && python -m backend.app.rag.ingest --reset

COPY frontend ./frontend
COPY .streamlit ./.streamlit

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
