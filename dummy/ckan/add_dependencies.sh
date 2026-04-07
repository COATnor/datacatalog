#!/bin/sh

set -ex

VERSION="2.11.4"

uvx crudini --set pyproject.toml project dependencies '[]'

uv add "setuptools==77.0.3"

uv add -r "https://raw.githubusercontent.com/ckan/ckan/refs/tags/ckan-$VERSION/requirements.txt"
uv add "ckan @ git+https://github.com/ckan/ckan@ckan-$VERSION"
