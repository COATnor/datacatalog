FROM ckan/ckan-solr:2.11-solr9-spatial

USER root

ENV SOLR_SCHEMA_FILE="/opt/solr/server/solr/configsets/ckan/conf/managed-schema"

RUN --mount=type=bind,source=schema-coat.sed,target=/tmp/schema-coat.sed \
    --mount=type=bind,source=schema-coatcustom.sed,target=/tmp/schema-coatcustom.sed \
    sed -i -f /tmp/schema-coat.sed "$SOLR_SCHEMA_FILE" && \
    sed -i -f /tmp/schema-coatcustom.sed "$SOLR_SCHEMA_FILE"

USER solr
