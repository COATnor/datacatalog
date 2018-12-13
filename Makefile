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
	sudo chown -R 900 ckanext-coat
	sudo chcon -Rt svirt_sandbox_file_t ckanext-coat 2>/dev/null || :

clean :
	rm -rf output
