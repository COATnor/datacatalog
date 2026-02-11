FROM ghcr.io/astral-sh/uv:python3.9-trixie

RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    rm /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -qy --no-install-recommends \
        chromium chromium-driver

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,sharing=locked,target=/root/.cache/uv \
    uv sync --locked

COPY base.py .

ENV PATH="/usr/lib/chromium:$PATH"
ENTRYPOINT ["uv", "run", "pytest", "base.py", "-v", "--headless"]
