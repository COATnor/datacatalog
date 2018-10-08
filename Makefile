PYTHON ?= python3

generate :
	if test -z "$$VIRTUAL_ENV"; then \
	    $(PYTHON) -m fades -V &>/dev/null || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades dockerfiles-generator.py; \
	else \
	    $(PYTHON) -m pip install -r requirements.txt && $(PYTHON) dockerfiles-generator.py; \
	fi

clean :
	rm -r output
