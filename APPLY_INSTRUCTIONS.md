# How to apply the OCR support patch

These files are ready to drop into your `spec-miner` repository.

## Files included

```
spec-miner-ocr/
├── APPLY_INSTRUCTIONS.md          ← this file
├── CHANGELOG.md                   ← updated changelog (v1.1.0)
├── pyproject.toml                 ← adds [project.optional-dependencies] ocr
├── requirements.txt               ← comments for optional OCR deps
└── src/
    └── spec_miner/
        ├── ocr.py                 ← NEW module
        ├── extractor.py           ← updated (OCR fallback + enable_ocr flag)
        └── cli.py                 ← updated (--ocr flag on extract & troubleshoot)
```

## Steps

1. Copy the files into your local clone, preserving paths:

   ```bash
   cd /path/to/your/spec-miner

   # New file
   cp /path/to/spec-miner-ocr/src/spec_miner/ocr.py src/spec_miner/

   # Overwrite existing files
   cp /path/to/spec-miner-ocr/src/spec_miner/extractor.py src/spec_miner/
   cp /path/to/spec-miner-ocr/src/spec_miner/cli.py src/spec_miner/
   cp /path/to/spec-miner-ocr/pyproject.toml .
   cp /path/to/spec-miner-ocr/requirements.txt .
   cp /path/to/spec-miner-ocr/CHANGELOG.md .
   ```

2. Install optional OCR dependencies:

   ```bash
   # System packages
   # Ubuntu/Debian:
   sudo apt-get install -y tesseract-ocr poppler-utils
   # macOS:
   brew install tesseract poppler

   # Python packages
   pip install -e ".[ocr]"
   # or
   pip install pdf2image pytesseract
   ```

3. Test:

   ```bash
   # Automatic fallback (runs OCR only when little text is found)
   spec-miner extract your_scanned.pdf

   # Force OCR
   spec-miner extract your_scanned.pdf --ocr
   spec-miner troubleshoot your_scanned.pdf --ocr -t readings.json
   ```

## Notes

- OCR is completely optional. Without the `ocr` extra the tool works exactly as before.
- When `--ocr` is not passed, OCR is used only as an automatic fallback for PDFs that yield very little native text.
- The original `models.py`, `exporter.py`, `troubleshooter.py`, `web.py`, and `sample_generator.py` are unchanged and do not need to be replaced.
