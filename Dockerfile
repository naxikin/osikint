# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

RUN useradd --create-home --uid 10001 osintuser \
    && mkdir -p /app/output \
    && chown -R osintuser:osintuser /app

USER osintuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fs http://localhost:8000/healthz || exit 1

CMD ["python", "dashboard/app.py"]
