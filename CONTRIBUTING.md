# Contributing to `spec-miner`

Thank you for your interest in contributing to **spec-miner**! Hardware engineers, embedded developers, and Python contributors are welcome.

## Development Setup

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/mr-khan/spec-miner.git
   cd spec-miner
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies and the package in editable mode:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
3. Run the automated test suite:
   ```bash
   make test
   ```

## Adding New Vendor Heuristics or Troubleshooting Rules

- **Datasheet Extraction Rules (`src/spec_miner/extractor.py`)**: Add table column aliases, package regexes, or peripheral patterns while preserving backward compatibility with existing PDFs.
- **Troubleshooting Knowledge Base (`src/spec_miner/troubleshooter.py`)**: Add new symptom signatures to `COMMON_FAULT_KB` or new electrical/thermal guardband checks with clear `rule_id` codes and actionable remediation guidance.
- **Unit Tests (`tests/test_spec_miner.py`)**: Include unit tests for any new extraction pattern or diagnostic rule before opening a Pull Request.

## Code Style

- Follow PEP 8 with a 100-character line limit (`ruff check .`).
- Include type annotations on all public functions, dataclasses, and methods.
