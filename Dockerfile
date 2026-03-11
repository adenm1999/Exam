# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install dependencies into a prefix we can copy across
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="your-email@example.com"
LABEL description="Ducks Unlimited university chapters ETL pipeline"
RUN useradd --create-home --shell /bin/bash etl_user
WORKDIR /app
COPY --from=builder /install /usr/local
COPY etl/ ./etl/
USER etl_user
CMD ["python", "-m", "etl.pipeline"]
