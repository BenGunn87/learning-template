.DEFAULT_GOAL := help

PYTHON ?= python3
NPM ?= npm
PORT ?= 8000
VENV_PYTHON := .venv/bin/python

.PHONY: help web-install web-build web web-demo web-dev

help:
	@printf '%s\n' \
	  'make web-install  Install Python and frontend dependencies' \
	  'make web-build    Build the frontend' \
	  'make web          Build and run the repository viewer' \
	  'make web-demo     Build and run the demo viewer' \
	  'make web-dev      Run Vite (backend: make web in another terminal)' \
	  'Override backend port: make web PORT=8001'

$(VENV_PYTHON):
	$(PYTHON) -m venv .venv

web-install: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r web/requirements.txt
	$(NPM) --prefix web ci

web-build:
	$(NPM) --prefix web run build

web: web-build
	$(VENV_PYTHON) -m web --port $(PORT)

web-demo: web-build
	$(VENV_PYTHON) -m web --demo --port $(PORT)

web-dev:
	$(NPM) --prefix web run dev
