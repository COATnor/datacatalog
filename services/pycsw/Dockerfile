FROM ghcr.io/astral-sh/uv:python3.11-trixie

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY coat2pycsw.py .
COPY mappings/topics.yaml mappings/

USER 1000

ENV COAT_URL=https://data.coat.no/
ENV DATABASE=sqlite:////home/pycsw/cite.db
ENV TIMEOUT=300

CMD ["uv", "run", "--no-sync", "python3", "coat2pycsw.py"]
