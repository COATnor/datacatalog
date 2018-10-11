FROM ckan/ckan:latest

USER root

# Install required system packages
RUN apt-get -q -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade && \
    apt-get -q -y install crudini && \
    apt-get -q clean && \
    rm -rf /var/lib/apt/lists/*

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

RUN ckan-paster make-config --no-interactive ckan "${CKAN_CONFIG}/production.ini" 

{% for ext in extensions if target in ext.targets %}
{% if ext.local %}
RUN : && \
{% else %}
RUN ckan-pip install -e git+{{ ext.repository }}@{{ ext.version }}#egg={{ ext.name }} && \
    if [ -f $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt ]; then \
        ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt; \
    else \
        ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/requirements.txt; \
    fi && \
{% endif %}
{% if ext.settings_set %}
{% for key, value in ext.settings_set.items() %}
    crudini --set $CKAN_CONFIG/production.ini app:main {{ key }} "{{ value }}" && \
{% endfor %}
{% endif %}
{% if ext.settings_add %}
{% for key, value in ext.settings_add.items() %}
    crudini --set $CKAN_CONFIG/production.ini app:main {{ key }} "$(crudini --get $CKAN_CONFIG/production.ini app:main {{ key }} 2>/dev/null) {{ value }}" && \
{% endfor %}
{% endif %}
    :
{% endfor %}

COPY ckan-entrypoint-custom.sh /
RUN chmod +x ckan-entrypoint-custom.sh
ENTRYPOINT ["/ckan-entrypoint-custom.sh"]

USER ckan
EXPOSE 5000

CMD ["ckan-paster","serve","/etc/ckan/production.ini"]

