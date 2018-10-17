PYTHON ?= python3
REQUIREMENTS = $(realpath requirements.txt)
SRC = $(wildcard tools/*.py)
.PHONY = generate deploy populate prepare test style clean

ifdef VIRTUAL_ENV
  PYCMD = python -m pip install -r $(REQUIREMENTS) && python
else
  PYCMD = $(PYTHON) -m fades -V >/dev/null 2>&1 || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades -r$(REQUIREMENTS) -x python
endif

generate :
	$(PYCMD) tools/docker.py --templates=tools/docker/templates-ckan --settings=settings/docker.yaml

deploy :
	$(PYCMD) tools/portainer.py $(NAME) $(PROJECT) $(SERVER)

populate :
	$(PYCMD) tools/ckan.py $(SERVER) --initial=settings/ckan.yaml

prepare :
	git clone git@gitlab.com:nina-data/ckanext-coat.git
	sudo chown -R 900 ckanext-coat
	sudo chcon -Rt svirt_sandbox_file_t ckanext-coat 2>/dev/null || :

test : $(SRC)
	$(PYCMD) -m py_compile $^

style : $(SRC)
	-$(PYCMD) -m flake8 $^
	-$(PYCMD) -m pydocstyle $^

clean :
	rm -rf output
	rm -rf tools/*/__pycache__
