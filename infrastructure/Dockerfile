# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend ./backend

FROM python:3.12-slim AS production

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_DEBUG=false

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
COPY pyproject.toml ./

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8010"]
