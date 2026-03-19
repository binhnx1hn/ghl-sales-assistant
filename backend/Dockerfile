# GHL Sales Assistant Backend
# Production-optimized Dockerfile
#
# Usage:
#   docker build -t ghl-assistant-api .
#   docker run -p 8000:8000 --env-file .env ghl-assistant-api

# ── Stage 1: Dependencies ──────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Production ───────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="GHL Sales Assistant Team"
LABEL version="1.0.0"
LABEL description="GHL Sales Assistant FastAPI Backend"

# Security: create non-root user
RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --create-home appuser

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Ensure appuser owns the workdir
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# WORKERS env var controls uvicorn worker count (default: 2)
ENV WORKERS=2

# Run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS}
