#!/bin/bash
set -e

CKAN_HOME=/usr/lib/ckan
CKAN_VENV=$CKAN_HOME/venv

{% for ext in extensions if target in ext.targets %}
{% if ext.settings_set_startup %}
{% for key, value in ext.settings_set_startup.items() %}
crudini --set $CKAN_CONFIG/production.ini app:main {{ key }} {{ "${"+value+"}" }}
{% endfor %}
{% endif %}
{% if ext.local %}
chroot --userspec=ckan / ckan-pip install -e $CKAN_VENV/src/{{ ext.name }}
for filename in pip-requirements.txt requirements.txt dev-requirements.txt; do
if [ -f $CKAN_VENV/src/{{ ext.name }}/$filename ]; then
    chroot --userspec=ckan / ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/{{ ext.name }}/$filename
    break
fi
done
{% endif %}
{% endfor %}

chroot --userspec=ckan / /ckan-entrypoint.sh
{% include "ckan-entrypoint-custom/"+target ignore missing %}

exec chroot --userspec=ckan / "$@"
