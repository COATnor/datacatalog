.PHONY = generate deploy compose attach populate prepare clean

include tools/pycmd.mk

generate : clean templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.mo
	$(PYCMD) tools/docker.py --settings=settings/docker.yaml \
                                 --templates \
                                     tools/docker/templates/ckan \
                                     templates/ckan \
                                 --static \
                                    templates/ckan-static/i18n \
                                 --extensions=ckanext \
                                 --output=output \
				dev \
				deploy

templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.mo: templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.po
	msgfmt $< -o $@

deploy :
	$(PYCMD) tools/portainer.py $(NAME) $(PROJECT) --server=$(SERVER)

compose :
	docker-compose -f output/dev/docker-compose.yml up $(OPTS)

attach :
	docker attach $$(docker container ls -q -f name=^ckan$$)

populate :
	$(PYCMD) tools/ckan.py --initial=settings/ckan.yaml --server=$(SERVER)

prepare :
	sudo chmod -R g+w ckanext/ckanext-*
	sudo chown -R 900 ckanext/ckanext-*
	sudo chcon -Rt svirt_sandbox_file_t ckanext/ckanext-* 2>/dev/null || :


clean :
	rm -rf output
	rm -f templates/ckan-static/i18n/*/*/*.mo
