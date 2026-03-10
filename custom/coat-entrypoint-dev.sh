#!/bin/bash

set -eu

/coat-entrypoint.sh

function conf_set() { crudini --set "$CKAN_INI" app:main "$@"; }

crudini --set "$CKAN_INI" DEFAULT debug "true"
crudini --set "$CKAN_INI" app:main ckan.auth.create_user_via_api true
crudini --set "$CKAN_INI" app:main ckan.auth.user_create_organizations true

exec "$@"
