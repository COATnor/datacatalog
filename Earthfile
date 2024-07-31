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

RUN_PIP_CACHED:
    COMMAND
    ARG args
    RUN --mount=type=cache,target=/root/.cache/pip $args

INSTALL_CKAN_PIP:
    COMMAND
    ARG args
    DO +RUN_PIP_CACHED --args="ckan-pip3 install $args"

INSTALL_PIP:
    COMMAND
    ARG args
    DO +RUN_PIP_CACHED --args="python3 -m pip install $args"

language:
    DO +INSTALL --pkgs="gettext"
    COPY custom/ckan.po .
    RUN msgfmt ckan.po -o ckan.mo
    SAVE ARTIFACT ckan.mo

requirements:
    DO +INSTALL --pkgs="bsdmainutils"
    COPY --dir scripts .
    FOR ext IN oauth2 spatial harvest
        COPY ckanext/ckanext-${ext}/requirements.txt ckanext-${ext}.txt
    END
    FOR ext IN doi scheming
        COPY ckanext/ckanext-${ext}/setup.py ckanext-${ext}.py
    END
    COPY custom/requirements-extra.txt .
    RUN scripts/gather-requirements.sh ckanext-* requirements-extra.txt > requirements.in
    DO +INSTALL_PIP --args="pip-tools"
    RUN pip-compile --no-header \
            --output-file=requirements.txt \
            requirements.in \
            $CKAN_VENV/src/ckan/requirements.txt
    SAVE ARTIFACT requirements.txt AS LOCAL custom/requirements.txt

container-test:
    DO +INSTALL --pkgs="firefox xvfb"
    DO +INSTALL_PIP --args="pdm"
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
