.PHONY = generate deploy populate prepare clean

include tools/pycmd.mk

generate : clean templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.mo
	$(PYCMD) tools/docker.py --settings=settings/docker.yaml \
                                 --templates \
                                     tools/docker/templates/ckan \
                                     templates/ckan \
                                 --static \
                                    templates/ckan-static/i18n \
                                 --extensions=. \
                                 --output=output \
				dev \
				deploy \
				deploy-gitlab

templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.mo: templates/ckan-static/i18n/en_ZW/LC_MESSAGES/ckan.po
	msgfmt $< -o $@

deploy :
	$(PYCMD) tools/portainer.py $(NAME) $(PROJECT) --server=$(SERVER)

populate :
	$(PYCMD) tools/ckan.py --initial=settings/ckan.yaml --server=$(SERVER)

prepare :
	[ -d ckanext-coat ] || git clone git@gitlab.com:nina-data/ckanext-coat.git
	[ -d ckanext-coatcustom ] || git clone git@gitlab.com:nina-data/ckanext-coatcustom.git
	[ -d ckanext-scheming ] || git clone https://github.com/ckan/ckanext-scheming
	[ -d ckanext-dcat ] || git clone https://github.com/frafra/ckanext-dcat -b staging
	[ -d ckanext-kata ] || git clone https://github.com/mdlux/ckanext-kata
	[ -d ckanext-oaipmh ] || git clone https://github.com/mdlux/ckanext-oaipmh
	[ -d ckanext-datasetversions ] || git clone https://github.com/frafra/ckanext-datasetversions -b staging
	sudo chown -R 900 ckanext-*
	sudo chcon -Rt svirt_sandbox_file_t ckanext-* 2>/dev/null || :

clean :
	rm -rf output
	rm -f templates/ckan-static/i18n/*/*/*.mo
