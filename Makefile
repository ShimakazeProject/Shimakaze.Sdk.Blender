# Build and development helpers for the Shimakaze SDK extension.
# Set BLENDER to the path of your Blender 4.5 executable if it is not on PATH.

BLENDER ?= blender
DIST := dist

.PHONY: build lint format clean

build:
	rm -rf $(DIST)
	mkdir -p $(DIST)
	$(BLENDER) --command extension build --source-dir extension --output-dir $(DIST)

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

clean:
	rm -rf $(DIST) .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
