FROM ghcr.io/astral-sh/uv:python3.11-trixie

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY coat_bulk_download coat_bulk_download

ENV COAT_URL=https://data.coat.no/

CMD ["uv", "run", "--no-sync", "uvicorn", "coat_bulk_download.app:app", "--host", "0.0.0.0"]
