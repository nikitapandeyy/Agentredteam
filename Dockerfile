# ── Stage 1: dependency installer ────────────────────────────────
# We use a separate stage to install packages so the final image
# doesn't need build tools (gcc, make, etc.) installed.
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed by some packages (psycopg[binary] needs them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: final runtime image ─────────────────────────────────
FROM python:3.12-slim

# Security: run as a non-root user
# If the app is ever compromised, the attacker has no root access
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy only the application code (not .env, .venv, tests, etc.)
COPY app/ ./app/
COPY dashboard/ ./dashboard/

# Cloud Run sets PORT to 8080. We default to 8080 locally too.
# The app reads this at startup via uvicorn's --port flag.
ENV PORT=8080

# Switch to non-root user
USER appuser

# Health check: Cloud Run uses this to know when the container is ready
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"

# Start the server.
# Shell form (not exec form) so $PORT is expanded.
CMD uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
