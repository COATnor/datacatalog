#!/bin/bash
set -e

CKAN_HOME=/usr/lib/ckan
CKAN_VENV=$CKAN_HOME/venv

{% for ext in extensions if target in ext.targets and ext.local %}
ckan-pip install -e $CKAN_VENV/src/{{ ext.name }}
if [ -f $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt ]; then
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/pip-requirements.txt ||  
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/requirements.txt
fi
{% endfor %}

exec /ckan-entrypoint.sh "$@"
