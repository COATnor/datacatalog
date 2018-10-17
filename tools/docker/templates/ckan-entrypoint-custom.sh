#!/bin/bash
set -e

CKAN_HOME=/usr/lib/ckan
CKAN_VENV=$CKAN_HOME/venv

{% for ext in extensions if target in ext.targets %}
{% if ext.settings_set_startup %}
{% for key, value in ext.settings_set_startup.items() %}
if [ -z {{ "${"+value+"}" }} ]; then
    {{ value }}="PLEASE_SET_{{ value }}"
fi
crudini --set $CKAN_CONFIG/production.ini app:main {{ key }} {{ "${"+value+"}" }}
{% endfor %}
{% endif %}
{% if ext.local %}
gosu ckan ckan-pip install -e $CKAN_VENV/src/{{ ext.name }}
if [ -f $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt ]; then
    gosu ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt ||  
    gosu ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/requirements.txt
fi
{% endif %}
{% endfor %}

gosu ckan /ckan-entrypoint.sh
{% include "ckan-entrypoint-custom/"+target ignore missing %}

exec gosu ckan "$@"
