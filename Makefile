.PHONY: help install test demo serve clean

PYTHON ?= python3
PYTHONPATH := src

help:
	@echo "spec-miner Makefile targets:"
	@echo "  make install   - Install package in editable mode"
	@echo "  make test      - Run unit and integration test suite"
	@echo "  make demo      - Generate sample MCU datasheet PDF and run live CLI demo"
	@echo "  make serve     - Start the interactive Web UI and FastAPI server on port 8000"
	@echo "  make clean     - Remove build and cache artifacts"

install:
	$(PYTHON) -m pip install -e .

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

demo:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m spec_miner.cli demo -d ./examples

serve:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m spec_miner.cli serve --host 127.0.0.1 --port 8000

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +
