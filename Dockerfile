FROM ckan/ckan:latest

USER root

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        crudini \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

RUN ckan-paster make-config --no-interactive ckan "${CKAN_CONFIG}/production.ini" 

RUN ckan-pip install -e git+https://github.com/ckan/ckanext-spatial.git@stable#egg=ckanext-spatial \
    && ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckanext-spatial/pip-requirements.txt \
    && crudini --set $CKAN_CONFIG/production.ini app:main ckan.plugins "$(crudini --get $CKAN_CONFIG/production.ini app:main ckan.plugins) spatial_metadata spatial_query" \
    && crudini --set $CKAN_CONFIG/production.ini app:main ckanext.spatial.search_backend solr

# Install CKANext-harvest, dependency for CKANext-dcat 
RUN ckan-pip install -e git+https://github.com/ckan/ckanext-harvest.git@v1.1.1#egg=ckanext-harvest \
    && ckan-pip install -r $CKAN_VENV/src/ckanext-harvest/pip-requirements.txt \
    && crudini --set $CKAN_CONFIG/production.ini app:main ckan.plugins "$(crudini --get $CKAN_CONFIG/production.ini app:main ckan.plugins) harvest ckan_harvester"

RUN ckan-pip install -e git+https://github.com/ckan/ckanext-dcat.git@v0.0.7#egg=ckanext-dcat \
    && ckan-pip install -r $CKAN_VENV/src/ckanext-dcat/requirements.txt \
    && crudini --set $CKAN_CONFIG/production.ini app:main ckan.plugins "$(crudini --get $CKAN_CONFIG/production.ini app:main ckan.plugins) dcat dcat_rdf_harvester dcat_json_harvester dcat_json_interface structured_data" 

RUN ckan-pip install -e git+https://gitlab+deploy-token-18189:Bjbr5KuvuPgDZh7Cp2sQ@gitlab.com/nina-data/ckanext-coat.git#egg=ckanext-coat \
   && ckan-pip install -r $CKAN_VENV/src/ckanext-coat/requirements.txt \
   && crudini --set $CKAN_CONFIG/production.ini app:main ckan.plugins "$(crudini --get $CKAN_CONFIG/production.ini app:main ckan.plugins) coat"

ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan
EXPOSE 5000

CMD ["ckan-paster","serve","/etc/ckan/production.ini"]

