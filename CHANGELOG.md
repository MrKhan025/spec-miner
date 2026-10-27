# Changelog

All notable changes to `spec-miner` are documented in this file.

## [1.1.0] - 2026-10-27

### Added
- **Optional OCR support for image-based / scanned datasheets**:
  - New module `spec_miner.ocr` using `pdf2image` + `pytesseract`.
  - Automatic fallback when native text/table extraction yields insufficient content.
  - CLI flag `--ocr` on `extract` and `troubleshoot` to force OCR.
  - Optional dependency group: `pip install "spec-miner[ocr]"`.
  - System package notes for `tesseract-ocr` and `poppler-utils`.

## [1.0.0] - 2026-10-26

### Added
- **PDF Datasheet Extraction Engine (`spec_miner.extractor`)**:
  - Automatic extraction of part numbers, manufacturers, package types, and key features.
  - Table and structured-text parsing for Operating Conditions and Absolute Maximum Ratings.
  - Pinout table extraction with voltage-domain tagging (`3.3V only`, `5V tolerant (FT)`, `Power`) and alternate peripheral function detection.
  - Communication interface detection (`I2C`, `SPI`, `UART`, `CAN`, `USB`, `ADC`, `PWM`) and thermal resistance ($\theta_{JA}$, $\theta_{JC}$, $T_{J(\max)}$) parsing.
  - Silicon errata & workaround extraction.
- **Hardware Troubleshooting & Root-Cause Engine (`spec_miner.troubleshooter`)**:
  - Automated validation of live or recorded electrical telemetry against Operating and Absolute Maximum datasheet limits with configurable guardbands.
  - Junction temperature estimation ($T_J = T_A + P_D \times \theta_{JA}$) and thermal derating checks.
  - Pin-state validation (detecting floating reset/input pins and 5V overvoltage on 3.3V-only pins).
  - Symptom-based root-cause matching against extracted silicon errata and an embedded hardware engineering knowledge base.
  - Side-by-side datasheet comparison (`compare_specs`) for drop-in replacement evaluation.
- **Multi-Format Exporter (`spec_miner.exporter`)**:
  - Export extracted specifications and diagnostic reports to JSON, Markdown, CSV, and dark-mode standalone HTML.
- **CLI & Interactive Web Utility (`spec_miner.cli`, `spec_miner.web`)**:
  - Rich terminal CLI (`extract`, `troubleshoot`, `compare`, `demo`, `serve`).
  - FastAPI web dashboard and REST endpoints (`/api/extract`, `/api/troubleshoot`, `/api/demo`, `/api/health`).
