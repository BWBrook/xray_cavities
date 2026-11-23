MAKEDOC_DIR ?= $(HOME)/work/makedoc
PYTHON ?= .venv/bin/python
MAKEDOC = PYTHONPATH="$(MAKEDOC_DIR)/src" "$(PYTHON)" -m makedoc
MAKEDOC_CONFIG := $(CURDIR)/settings/build.yaml

.PHONY: manuscript-validate manuscript-draft manuscript-submission manuscript-all manuscript-check

manuscript-validate:
	"$(PYTHON)" scripts/claims/check_claims.py
	$(MAKEDOC) check -c "$(MAKEDOC_CONFIG)" --all

manuscript-draft:
	"$(PYTHON)" scripts/claims/check_claims.py
	$(MAKEDOC) build -c "$(MAKEDOC_CONFIG)" -p draft

manuscript-submission:
	"$(PYTHON)" scripts/claims/check_claims.py --strict
	$(MAKEDOC) check -c "$(MAKEDOC_CONFIG)" -p submission
	$(MAKEDOC) build -c "$(MAKEDOC_CONFIG)" -p submission --strict

manuscript-all: manuscript-draft manuscript-submission

manuscript-check: manuscript-submission
