#!/bin/bash

REMOTE="box"
PRESETS_PATH="../../ckanext/ckanext-coatcustom/ckanext/coatcustom/presets"
SPECIES_PATH="Data Management/resources_COAT_data_formatting/species_and_locality_lists/COAT_species_list.xlsx"
LOCALITIES_PATH="Data Management/resources_COAT_data_formatting/species_and_locality_lists/locality_taxonomy_COAT_coordinates.xlsx"

set -ex

cd "$(dirname "$0")"

rclone copy "$REMOTE":"COAT/$SPECIES_PATH" .
rclone copy "$REMOTE":"COAT/$LOCALITIES_PATH" .
mv "$(basename "$SPECIES_PATH")" species.xlsx
mv "$(basename "$LOCALITIES_PATH")" localities.xlsx

duckdb -f generate.sql
jq  --indent 4 '[.[].full_name]' taxonomy.json > "$PRESETS_PATH/names.json"
jq  --indent 4 . localities.json > "$PRESETS_PATH/locations.json"