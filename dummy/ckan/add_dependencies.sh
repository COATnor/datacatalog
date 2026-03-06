#!/bin/sh

set -ex

VERSION="2.9.7"

uv add "setuptools<46" wheel Cython

uv add -r ../../ckanext/ckanext-harvest/requirements.txt
uv add -r ../../ckanext/ckanext-spatial/requirements.txt

uv add -r "https://raw.githubusercontent.com/ckan/ckan/refs/tags/ckan-$VERSION/requirements.txt"
uv add "ckan @ git+https://github.com/ckan/ckan@ckan-$VERSION"
