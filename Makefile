PYTHON ?= python3
REQUIREMENTS = $(realpath requirements.txt)
SRC = $(wildcard tools/*/*.py)
.PHONY = generate deploy populate prepare test style clean

ifdef VIRTUAL_ENV
  PYCMD = python -m pip install -r $(REQUIREMENTS) && python
else
  PYCMD = $(PYTHON) -m fades -V >/dev/null 2>&1 || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades -r$(REQUIREMENTS) -x python
endif

generate :
	cd tools/docker && $(PYCMD) generator.py

deploy :
	cd tools/portainer && $(PYCMD) deploy.py $(NAME) $(PROJECT) $(SERVER)

populate :
	cd tools/ckan && $(PYCMD) populate.py $(SERVER)

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
	rm -r tools/docker/output
	rm -r tools/*/__pycache__
