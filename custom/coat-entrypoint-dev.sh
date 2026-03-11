#!/bin/bash

set -eu

/coat-entrypoint.sh

function conf_set() { crudini --set "$CKAN_INI" app:main "$@"; }

crudini --set "$CKAN_INI" DEFAULT debug "true"
crudini --set "$CKAN_INI" app:main ckan.auth.create_user_via_api true
crudini --set "$CKAN_INI" app:main ckan.auth.user_create_organizations true

if [ -n "${CKAN_ADMIN_PASSWORD:-}" ]
then
    ckan user add admin email=admin@coat.no password="$CKAN_ADMIN_PASSWORD" fullname="COAT Admin" || true
    ckan sysadmin add admin || true
fi

exec "$@"
