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

# Create a test sysadmin and write its API token to a shared volume so the
# test-api container can authenticate against CKAN 2.10+ (which no longer
# returns an apikey from user_create).
if [ -d /tokens ]
then
    ckan user add coat_test_admin email=coat_test_admin@coat.no \
        password="TestPassword123!" fullname="COAT Test Admin" 2>/dev/null || true  # pragma: allowlist secret
    ckan sysadmin add coat_test_admin 2>/dev/null || true
    TOKEN=$(ckan user token add coat_test_admin integration_test 2>&1 \
        | grep -oE 'eyJ[A-Za-z0-9_.-]+' || true)
    if [ -n "$TOKEN" ]; then
        echo "$TOKEN" > /tokens/api_token
    fi
    # The API test suite authenticates as a regular (non-sysadmin) user.
    # Local user registration via the API is blocked by the oauth2 plugin,
    # so the user is created here via the CLI and its token written to the
    # shared volume (consumed by the `client` fixture in tests/test_api.py).
    ckan user add test_apiuser email=apiuser@uit.no \
        password="TestPassword123!" fullname="Test API User" 2>/dev/null || true  # pragma: allowlist secret
    USER_TOKEN=$(ckan user token add test_apiuser integration_test 2>&1 \
        | grep -oE 'eyJ[A-Za-z0-9_.-]+' || true)
    if [ -n "$USER_TOKEN" ]; then
        echo "$USER_TOKEN" > /tokens/api_user_token
    fi
fi

exec "$@"
