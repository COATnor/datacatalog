VERSION 0.6
FROM registry.gitlab.com/nina-data/ckan/nina-ckan-2-9-7/ckan

USER root
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN rm /etc/apt/apt.conf.d/docker-clean

INSTALL:
    COMMAND
    ARG pkgs
    RUN --mount=type=cache,target=/var/cache/apt \
        --mount=type=cache,target=/var/lib/apt/lists \
        apt-get -q -y update && \
        DEBIAN_FRONTEND=noninteractive apt-get -yq install $pkgs

INSTALL_PY:
    COMMAND
    ARG args
    RUN --mount=type=cache,target=/root/.cache/pip ckan-pip3 install $args

INSTALL_PIPX:
    COMMAND
    ARG args
    DO +INSTALL --pkgs="pipx"
    RUN --mount=type=cache,target=/root/.cache/pip pipx install $args

language:
    DO +INSTALL --pkgs="gettext"
    COPY custom/ckan.po .
    RUN msgfmt ckan.po -o ckan.mo
    SAVE ARTIFACT ckan.mo

requirements-auto:
    DO +INSTALL --pkgs="bsdmainutils"
    COPY --dir scripts .
    FOR ext IN oauth2 spatial harvest
        COPY ckanext/ckanext-${ext}/requirements.txt ckanext-${ext}.txt
    END
    FOR ext IN doi scheming
        COPY ckanext/ckanext-${ext}/setup.py ckanext-${ext}.py
    END
    RUN scripts/gather-requirements.sh ckanext-* > requirements.in
    RUN sed -i -r -f scripts/fix_requirements.sed requirements.in
    SAVE ARTIFACT requirements.in

requirements:
    DO +INSTALL_PIPX --args="pip-tools"
    COPY +requirements-auto/requirements.in .
    RUN pip-compile --no-annotate --no-header \
            --output-file=requirements.txt \
            requirements.in \
            $CKAN_VENV/src/ckan/requirements.txt
    SAVE ARTIFACT requirements.txt

build:
    COPY +requirements/requirements.txt .
    DO +INSTALL_PY --args="wheel"
    RUN --mount=type=cache,target=/root/.cache/pip \
        ckan-pip3 wheel -r requirements.txt -w wheels
    SAVE ARTIFACT wheels

container:
    DO +INSTALL --pkgs="crudini"
    COPY --dir +build/wheels .
    DO +INSTALL_PY --args="wheels/*.whl"
    FOR extension IN coat coatcustom datasetversions doi harvest oauth2 scheming spatial
        COPY ckanext/ckanext-${extension} $CKAN_VENV/src/ckanext/ckanext-${extension}
        DO +INSTALL_PY --args="--no-deps -e $CKAN_VENV/src/ckanext/ckanext-${extension}"
    END
    DO +INSTALL_PY --pkgs="gunicorn"
    # https://github.com/pallets-eco/flask-debugtoolbar/issues/195
    DO +INSTALL_PY --args="packaging git+https://github.com/pallets-eco/flask-debugtoolbar.git@02c99a7b64d317e21189d627ec0a6eada58e3744"
    COPY +language/ckan.mo $CKAN_VENV/src/ckan/ckan/i18n/en/LC_MESSAGES/ckan.mo
    COPY custom/coat-entrypoint.sh custom/coat-entrypoint-dev.sh .
    ENV CKAN_INI=/etc/ckan/production.ini
    RUN mkdir -p /var/lib/ckan/webassets/.webassets-cache
    ENTRYPOINT ["/coat-entrypoint.sh"]
    CMD ["gunicorn", "--chdir", "/usr/lib/ckan/venv/src/ckan", "wsgi:application", "-b", "0.0.0.0:5000"]
    ARG CONTAINER_IMAGE=nina-ckan-coat:dev
    SAVE IMAGE --push $CONTAINER_IMAGE

container-test:
    DO +INSTALL --pkgs="firefox xvfb"
    DO +INSTALL_PIPX --args="pdm"
    RUN wget -q https://raw.githubusercontent.com/eficode/wait-for/v2.2.3/wait-for -O /wait-for && chmod +x /wait-for
    ENV COAT_URL="http://localhost:5000/"
    ENV TIMEOUT=300
    ENV DISPLAY=:99
    WORKDIR /app
    COPY tests/pdm.lock tests/pyproject.toml .
    RUN pdm install --no-self && pdm run seleniumbase install geckodriver
    COPY tests/base.py .
    ENTRYPOINT ["/bin/bash", "-xeu", "-c", "exec /wait-for --timeout $TIMEOUT $COAT_URL -- $0 $@"]
    CMD ["pdm", "run", "pytest", "--browser", "firefox", "base.py"]
    ARG CONTAINER_IMAGE=nina-ckan-coat:test
    SAVE IMAGE --push $CONTAINER_IMAGE
