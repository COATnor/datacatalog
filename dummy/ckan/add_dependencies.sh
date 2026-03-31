#!/bin/sh

set -ex

VERSION="2.11.4"

uv add "setuptools<46" wheel Cython

uv add -r "https://raw.githubusercontent.com/ckan/ckan/refs/tags/ckan-$VERSION/requirements.txt"
uv add "ckan @ git+https://github.com/ckan/ckan@ckan-$VERSION"
