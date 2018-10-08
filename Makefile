PYTHON ?= python3

generate :
	$(PYTHON) -m fades -V &>/dev/null || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades dockerfiles-generator.py

clean :
	rm -r output
