.PHONY = generate deploy populate prepare clean

include tools/pycmd.mk

generate :
	$(PYCMD) tools/docker.py --settings=settings/docker.yaml \
                                 --templates=tools/docker/templates-ckan \
                                 --extensions=. \
                                 --output=output

deploy :
	$(PYCMD) tools/portainer.py $(NAME) $(PROJECT) $(SERVER)

populate :
	$(PYCMD) tools/ckan.py --initial=settings/ckan.yaml $(SERVER)

prepare :
	git clone git@gitlab.com:nina-data/ckanext-coat.git
	sudo chown -R 900 ckanext-coat
	sudo chcon -Rt svirt_sandbox_file_t ckanext-coat 2>/dev/null || :

clean :
	rm -r output
