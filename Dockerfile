FROM registry.gitlab.com/nina-data/ckan/nina-ckan-2-9-7/ckan AS base

USER root
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN rm /etc/apt/apt.conf.d/docker-clean && \
    apt-get update

FROM base AS language
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get install -qy --no-install-recommends gettext
COPY custom/ckan.po .
RUN msgfmt ckan.po -o /ckan.mo

FROM base
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get install -qy --no-install-recommends crudini

COPY custom/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    ckan-pip3 install -r requirements.txt

COPY ckanext/ $CKAN_VENV/src/ckanext/
RUN --mount=type=cache,target=/root/.cache/pip \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-coat && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-coatcustom && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-datasetversions && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-doi && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-harvest && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-oauth2 && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-scheming && \
    ckan-pip3 install --no-deps -e $CKAN_VENV/src/ckanext/ckanext-spatial && \
    :

COPY --from=language /ckan.mo $CKAN_VENV/src/ckan/ckan/i18n/en/LC_MESSAGES/ckan.mo
COPY custom/coat-entrypoint.sh custom/coat-entrypoint-dev.sh ./
ENV CKAN_INI=/etc/ckan/production.ini
RUN mkdir -p /var/lib/ckan/webassets/.webassets-cache
ENTRYPOINT ["/coat-entrypoint.sh"]
CMD ["gunicorn", "--chdir", "/usr/lib/ckan/venv/src/ckan", "wsgi:application", "-b", "0.0.0.0:5000"]