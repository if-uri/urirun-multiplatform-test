PYTHON ?= python3
TEST_PYTHON := .work/venv/bin/python
URIRUN := .work/venv/bin/urirun

.PHONY: install doctor-build doctor-test doctor-health test check

install:
	$(PYTHON) scripts/bootstrap.py
	$(PYTHON) scripts/install_urirun.py

doctor-build:
	$(PYTHON) -m compileall -q scripts tests

doctor-test:
	$(PYTHON) scripts/run_tests.py -q -m stable

doctor-health:
	test -s reports/summary.json
	$(URIRUN) --version

test: doctor-test

check: doctor-build doctor-test doctor-health
