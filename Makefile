PYTHON ?= python3
SRC = $(wildcard *.py)
.PHONY = generate prepare test style clean

ifdef VIRTUAL_ENV
  PYCMD = python -m pip install -r requirements.txt && python
else
  PYCMD = $(PYTHON) -m fades -V >/dev/null 2>&1 || $(PYTHON) -m pip install --user fades && $(PYTHON) -m fades -r requirements.txt -x python
endif

generate :
	$(PYCMD) dockerfiles-generator.py

prepare :
	git clone git@gitlab.com:nina-data/ckanext-coat.git
	sudo chown -R 900 ckanext-coat
	sudo chcon -Rt svirt_sandbox_file_t ckanext-coat 2>/dev/null || :

test : $(SRC)
	$(PYCMD) -m py_compile $^

style : $(SRC)
	$(PYCMD) -m flake8 $^
	$(PYCMD) -m pydocstyle $^

clean :
	rm -r output
	rm -r __pycache__
