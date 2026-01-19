#!/bin/bash

REMOTE="box"
FILE_PATH="Data Management/resources_COAT_data_formatting/species_and_locality_lists/COAT_species_list.xlsx"

set -ex

cd "$(dirname "$0")"
rclone copy "$REMOTE":"COAT/$FILE_PATH" .
mv "$(basename "$FILE_PATH")" species.xlsx
duckdb -f generate.sql
jq  --indent 4 '[.[].full_name]' taxonomy.json > "../../ckanext/ckanext-coatcustom/ckanext/coatcustom/presets/names.json"