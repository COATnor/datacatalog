.PHONY = generate deploy populate prepare clean

include tools/pycmd.mk

generate : clean
	$(PYCMD) tools/docker.py --settings=settings/docker.yaml \
                                 --templates \
                                     tools/docker/templates/ckan \
                                     templates/ckan \
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
	[ -d ckanext-coat ] || git clone git@gitlab.com:nina-data/ckanext-coat.git
	[ -d ckanext-coatcustom ] || git clone git@gitlab.com:nina-data/ckanext-coatcustom.git -b metadata_v2
	[ -d ckanext-scheming ] || git clone https://github.com/ckan/ckanext-scheming
	[ -d ckanext-datasetversions ] || git clone https://github.com/frafra/ckanext-datasetversions -b staging
	sudo chown -R 900 ckanext-*
	sudo chcon -Rt svirt_sandbox_file_t ckanext-* 2>/dev/null || :

clean :
	rm -rf output
