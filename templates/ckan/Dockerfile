FROM registry.gitlab.com/nina-data/ckan/nina-2-8-4/ckan

USER root

# Install required system packages
RUN apt-get -q -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade && \
    apt-get -q -y install crudini libsasl2-dev python-dev libldap2-dev libssl-dev \
{% for ext in extensions if target in ext.targets %}
{% if ext.packages %}
{% for pkg in ext.packages %}
{{ pkg }} \
{% endfor %}
{% endif %}
{% endfor %}
&& \
    apt-get -q clean && \
    rm -rf /var/lib/apt/lists/*

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

RUN ckan-paster make-config --no-interactive ckan "${CKAN_CONFIG}/production.ini"

{% for ext in extensions if not ext.dummy %}
COPY {{ extensions_path }}/{{ ext.name }} $CKAN_VENV/src/{{ ext.name }}
{% endfor %}

{% for ext in extensions if target in ext.targets %}
RUN : && \
{% if not ext.dummy %}
{% if not target.startswith('dev') %}
    ckan-pip install --no-cache-dir -e $CKAN_VENV/src/{{ ext.name }} && \
{% endif %}
    for filename in pip-requirements.txt requirements.txt dev-requirements.txt; do \
    if [ -f $CKAN_VENV/src/{{ ext.name }}/$filename ]; then \
        ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/$filename; \
    fi \
    done && \
{% endif %}
{% if ext.settings_set %}
{% for section, key, value in ext.settings_set %}
    crudini --set $CKAN_CONFIG/production.ini {{ section }} {{ key }} "{{ value }}" && \
{% endfor %}
{% endif %}
{% if ext.settings_add %}
{% for section, key, value in ext.settings_add %}
    crudini --set $CKAN_CONFIG/production.ini {{ section }} {{ key }} "$(crudini --get $CKAN_CONFIG/production.ini {{ section }} {{ key }} 2>/dev/null) {{ value }}" && \
{% endfor %}
{% endif %}
    :
{% endfor %}

{% block extra_setup %}
{% endblock %}

#COPY patches /patches
#RUN cd $CKAN_VENV/src/ckan; \
#    for patchfile in /patches/*; do \
#        patch -p1 -i "$patchfile"; \
#    done

ADD {{ output_path }}/{{ target }}/i18n/en_ZW /usr/lib/ckan/venv/src/ckan/ckan/i18n/en_ZW

# https://github.com/ufoscout/docker-compose-wait
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.6.0/wait /wait
RUN chmod +x /wait

COPY {{ output_path }}/{{ target }}/ckan-entrypoint-custom.sh /
RUN chmod +x ckan-entrypoint-custom.sh
ENTRYPOINT ["/ckan-entrypoint-custom.sh"]

EXPOSE 5000

CMD ["ckan-paster", "serve", "--reload", "/etc/ckan/production.ini"]
