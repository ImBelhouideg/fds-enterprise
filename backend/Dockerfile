# ════════════════════════════════════════════════════════════════
# FDS Enterprise Platform — Dockerfile (Multi-stage)
# Stage 1: builder  — compile deps
# Stage 2: runtime  — lean production image
# ════════════════════════════════════════════════════════════════

FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip --quiet \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
LABEL maintainer="FDS Team <platform@fds.io>" \
      version="3.0.0" \
      description="FDS Enterprise Fraud Detection Platform"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 wget curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r fdsapp && useradd -r -g fdsapp -d /app fdsapp

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=fdsapp:fdsapp . .

RUN mkdir -p /app/uploads /app/models /app/logs \
    && chown -R fdsapp:fdsapp /app

USER fdsapp
EXPOSE 5000

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD wget -qO- http://localhost:5000/health || exit 1

CMD ["gunicorn", \
     "--worker-class", "gevent", \
     "--workers", "2", \
     "--worker-connections", "1000", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--preload", \
     "app:app"]
