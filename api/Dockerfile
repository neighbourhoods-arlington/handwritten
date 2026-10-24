FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv — хурдан dependency суулгалт
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dependencies-ийг эхэлж суулгаж layer cache ашиглана
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Эх код
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
