#!/bin/bash

set -eu

/ckan-entrypoint.sh

CONFIG="${CKAN_CONFIG}/production.ini"
function conf_set() { crudini --set "$CONFIG" app:main "$@"; }
function conf_get() { crudini --get "$CONFIG" app:main "$@"; }
function conf_set_list() {
    param="$1"
    shift
    for var in "$@"; do
        crudini --set --list --list-sep=' ' "$CONFIG" app:main "$param" "$var"
    done
}

#ckan
conf_set ckan.site_title "COAT Data Portal"
conf_set ckan.site_description "Climate-ecological Observatory for Arctic Tundra (COAT)"
conf_set ckan.site_logo "/images/coat.png"
conf_set ckan.site_intro_text "Climate-ecological Observatory for Arctic Tundra (COAT)"
conf_set ckan.site_about "
# About

**COAT** (*Climate-ecological Observatory for Arctic Tundra*, [www.coat.no](https://www.coat.no)) is an adaptive, ecosystem based, observation system for Arctic tundra in Norway.

The COAT Data Portal hosts ecological and climatic primary monitoring data from COATs monitoring sites in high-arctic (Svalbard) and low-arctic (Varanger) tundra, as well as certain prioritized data from outside these regions.
In addition, the COAT Data Portal contains a number of secondary (derived) datasets, termed COAT state variables, which are calculated from primary data originating either from within COAT or requested from other data repositories.
The state variables are the primary input to the quantitative analysis and predictive modelling performed in COAT.

## Data policy and licenses

In COAT, we aim to publish all research data unless limited by either privacy or license restrictions. This means that the majority of COAT data are distributed under the Creative Commons Public License (CC BY 4.0).
Our commitment to data access includes the provision of metadata to enable data users to assess the content and significance of the data they download, as well as codes necessary to produce the summary analyses, tables and plots that in time will be provided on the COAT website.

A detailed description of the Data Portal and COAT's Data Management Policy and procedures can be found in the: [Data Management Plan](/dmp).

## Documentation

[coatnor.github.io](https://coatnor.github.io/) contains more details about the COAT Data portal and its usage.
"
conf_set ckan.datastore.sqlalchemy.pool_pre_ping true
conf_set ckan.search.show_all_types everything
conf_set ckan.favicon "/images/coat.png"

#ckanext-coatcustom
conf_set_list ckan.plugins coatcustom

#ckanext-scheming
conf_set_list ckan.plugins scheming_datasets scheming_organizations
conf_set_list scheming.dataset_schemas \
    ckanext.coatcustom:coat_schema.json \
    ckanext.coatcustom:coat_statevariable_schema.json \
    ckanext.coatcustom:coat_protocol_schema.json \
    ckanext.coatcustom:coat_dmp_schema.json
conf_set scheming.organization_schemas ckanext.coatcustom:coat_org_schema.json
conf_set scheming.presets ckanext.coatcustom:coat_presets.json
conf_set scheming.dataset_fallback false

#ckanext-spatial
conf_set_list ckan.plugins spatial_metadata spatial_query
conf_set ckanext.spatial.search_backend solr

#ckanext-dcat
conf_set_list ckan.plugins dcat structured_data
conf_set_list ckanext.dcat.rdf.profiles euro_dcat_ap coat_dcat_profile

#ckanext-harvest
conf_set_list ckan.plugins harvest ckan_harvester

#ckanext-metaexport
conf_set_list ckan.plugins metaexport

#ckanext-iso19115
conf_set_list ckan.plugins iso19115
conf_set ckanext.iso19115.misc.cache_dir "$CACHE_DIR"

#ckanext-doi
conf_set_list ckan.plugins doi
conf_set ckanext.doi.publisher NINA
conf_set ckanext.doi.site_title COAT
conf_set ckanext.doi.prefix "$DOI_PREFIX"
conf_set ckanext.doi.account_name "$DOI_ACCOUNT_NAME"
conf_set ckanext.doi.account_password "$DOI_ACCOUNT_PWD"
conf_set ckanext.doi.test_mode "$DOI_TEST_MODE"

#ckanext-oauth2
if [ "${ENV:=}" == "prod" ]
then
    conf_set_list ckan.plugins oauth2
    conf_set ckan.oauth2.profile_api_url "https://auth.dataporten.no/userinfo"
    conf_set_list ckan.oauth2.scope profile userinfo-name userinfo-photo email
    conf_set ckan.oauth2.profile_api_user_field email
    conf_set ckan.oauth2.profile_api_fullname_field name
    conf_set ckan.oauth2.profile_api_mail_field email
fi

#ckanext-datasetversions
conf_set_list ckan.plugins datasetversions

#ckanext-coat
conf_set_list ckan.plugins coat
conf_set ckanext.coat.resource_name_globally_unique true
conf_set ckanext.coat.custom_form false

: ${USERSPEC:=root}
chroot --userspec=$USERSPEC / ckan -c "${CONFIG}" search-index rebuild # workaround
chroot --userspec=$USERSPEC / ckan -c "${CONFIG}" doi initdb

exec "$@"
