#!/bin/bash

set -eu

/coat-entrypoint.sh

function conf_set() { crudini --set "$CKAN_INI" app:main "$@"; }

crudini --set "$CKAN_INI" DEFAULT debug "true"

exec "$@"
