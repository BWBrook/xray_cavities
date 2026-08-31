MAKEDOC_DIR ?= /Users/bwbrook/work/makedoc
MAKEDOC_CONFIG := $(CURDIR)/settings/build.yaml

.PHONY: manuscript-validate manuscript-draft manuscript-submission manuscript-all manuscript-check

manuscript-validate:
	$(MAKE) -C "$(MAKEDOC_DIR)" CONFIG="$(MAKEDOC_CONFIG)" PROFILE=draft validate-config
	$(MAKE) -C "$(MAKEDOC_DIR)" CONFIG="$(MAKEDOC_CONFIG)" PROFILE=submission validate-config

manuscript-draft:
	$(MAKE) -C "$(MAKEDOC_DIR)" CONFIG="$(MAKEDOC_CONFIG)" PROFILE=draft -B all

manuscript-submission:
	$(MAKE) -C "$(MAKEDOC_DIR)" CONFIG="$(MAKEDOC_CONFIG)" PROFILE=submission -B all

manuscript-all: manuscript-draft manuscript-submission

manuscript-check:
	$(MAKE) -C "$(MAKEDOC_DIR)" CONFIG="$(MAKEDOC_CONFIG)" PROFILE=submission check
