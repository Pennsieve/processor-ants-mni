.PHONY: help test run clean

SERVICE_NAME ?= processor-ants-mni
export DOCKER_DEFAULT_PLATFORM ?= linux/amd64

.DEFAULT: help

help:
	@echo "Make Help for $(SERVICE_NAME)"
	@echo ""
	@echo "make test   - run the processor over data/input/ with the local Python (needs ANTs + nibabel on PATH)"
	@echo "make run    - build the image and run it over data/input/, writing to data/output/"
	@echo "make clean  - remove data/output/"
	@echo ""
	@echo "Put a T1w image under data/input/image/ first (see sample-input/README.md or sample-input/fetch-sample.sh)."

test: clean
	INPUT_DIR=data/input OUTPUT_DIR=data/output python3 -m processor.main
	@cat data/output/warped/provenance.json

run: clean
	docker compose -f docker-compose.yml down --remove-orphans
	docker compose -f docker-compose.yml build
	docker compose -f docker-compose.yml up --exit-code-from processor

clean:
	rm -rf data/output
