#!/bin/bash

set -eu

/coat-entrypoint.sh

CONFIG="${CKAN_CONFIG}/production.ini"
function conf_set() { crudini --set "$CONFIG" app:main "$@"; }

crudini --set "$CONFIG" DEFAULT debug "true"

exec "$@"
