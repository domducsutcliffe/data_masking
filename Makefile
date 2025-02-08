export PYTHONPATH := $(shell pwd)

.DEFAULT_GOAL := run

PYTHON = ./venv/bin/python3
PIP = ./venv/bin/pip

venv: requirements.txt
	python3 -m venv venv
	$(PIP) install -r requirements.txt


run: venv
	$(PYTHON) src/main.py