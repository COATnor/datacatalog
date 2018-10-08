PYTHON ?= python3

generate :
	if test -z "$$VIRTUAL_ENV"; then \
	    $(PYTHON) -m fades -V &>/dev/null || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades -r requirements.txt dockerfiles-generator.py; \
	else \
	    $(PYTHON) -m pip install -r requirements.txt && $(PYTHON) dockerfiles-generator.py; \
	fi

prepare :
	git clone git@gitlab.com:nina-data/ckanext-coat.git
	sudo chown -R 900 ckanext-coat
	sudo chcon -Rt svirt_sandbox_file_t ckanext-coat 2>/dev/null || :

clean :
	rm -r output
