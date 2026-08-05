#!/bin/sh
set -e

CONFIG="${CKAN_CONFIG}/production.ini"

# Wait for PostgreSQL
while ! pg_isready -h db -U ckan; do
  sleep 1;
done

# If we don't already have a config file, bootstrap
if [ ! -e "$CONFIG" ]; then
  echo "Generating config at ${CONFIG}..."
  ckan generate config "$CONFIG"
fi

ckan --config "$CONFIG" db init
exec "$@"
