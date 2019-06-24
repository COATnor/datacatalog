.PHONY = generate deploy populate prepare clean

include tools/pycmd.mk

generate : clean
	$(PYCMD) tools/docker.py --settings=settings/docker.yaml \
                                 --templates \
                                     tools/docker/templates/ckan \
                                     templates/ckan \
                                     templates/ckan-solr-managed \
                                 --extensions=. \
                                 --output=output \
				dev \
				deploy \
				deploy-gitlab

deploy :
	$(PYCMD) tools/portainer.py $(NAME) $(PROJECT) --server=$(SERVER)

populate :
	$(PYCMD) tools/ckan.py --initial=settings/ckan.yaml --server=$(SERVER)

prepare :
	git clone git@gitlab.com:nina-data/ckanext-coat.git
	git clone git@gitlab.com:nina-data/ckanext-coatcustom.git
	git clone https://github.com/frafra/ckanext-datasetversions -b private-datasets
	sudo chown -R 900 ckanext-*
	sudo chcon -Rt svirt_sandbox_file_t ckanext-* 2>/dev/null || :

clean :
	rm -rf output