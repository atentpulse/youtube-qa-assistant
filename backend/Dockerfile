# Multi-stage production Dockerfile for YtGenius Backend
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for C-extensions and native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a local user prefix, excluding Windows-only pywin32
COPY requirements.txt .
RUN grep -iv "^pywin32" requirements.txt > /tmp/requirements.linux.txt \
    && pip install --no-cache-dir --user -r /tmp/requirements.linux.txt \
    && rm /tmp/requirements.linux.txt

# Final production image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime dependencies (libpq for PostgreSQL, curl for healthchecks, libgomp1 for PyTorch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group with proper home directory
RUN groupadd -r ytgenius && useradd -r -g ytgenius -m -d /home/ytgenius -s /sbin/nologin ytgenius

# Copy compiled python dependencies from builder with explicit ownership
COPY --from=builder --chown=ytgenius:ytgenius /root/.local /home/ytgenius/.local

# Copy application and migration assets
COPY --chown=ytgenius:ytgenius . /app

# Ensure non-root user environment and PATH includes installed wheels
ENV HOME=/home/ytgenius \
    PYTHONUSERBASE=/home/ytgenius/.local \
    PATH="/home/ytgenius/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER ytgenius

EXPOSE 8000

# Container healthcheck against /health/live
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Production command: apply migrations and start uvicorn with 4 worker processes
CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
