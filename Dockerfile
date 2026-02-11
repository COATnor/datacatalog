FROM ghcr.io/astral-sh/uv:python3.9-trixie AS base
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    rm /etc/apt/apt.conf.d/docker-clean && \
    apt-get update

FROM base AS language
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get install -qy --no-install-recommends gettext
COPY custom/ckan.po .
RUN msgfmt ckan.po -o /ckan.mo

FROM base
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get install -qy --no-install-recommends \
        postgresql-client
WORKDIR /usr/lib/ckan/

COPY ckanext/ ckanext/
COPY dummy/ dummy/
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,sharing=locked,target=/root/.cache/uv \
    uv sync --locked


COPY custom/coat-entrypoint.sh custom/coat-entrypoint-dev.sh custom/ckan-entrypoint.sh /
COPY wsgi.py .

ENV CKAN_HOME=/usr/lib/ckan
ENV CKAN_VENV=$CKAN_HOME/.venv
ENV CKAN_CONFIG=$CKAN_VENV/lib/python3.9/site-packages/ckan/config
ENV CKAN_INI=$CKAN_CONFIG/production.ini
ENV CKAN_STORAGE_PATH=/var/lib/ckan

COPY --from=language /ckan.mo $CKAN_VENV/lib/python3.9/site-packages/ckan/i18n/en/LC_MESSAGES/ckan.mo
RUN mkdir -p $CKAN_STORAGE_PATH/webassets/.webassets-cache

ENV PATH="$CKAN_VENV/bin:$PATH"

ENTRYPOINT ["/coat-entrypoint.sh"]
CMD ["gunicorn", "wsgi:application", "-b", "0.0.0.0:5000"]