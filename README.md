# ⚡ spec-miner

[![License: MIT](https://img.shields.io/badge/License-MIT-0284c7.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-38bdf8.svg)](https://www.python.org/)
[![Interface: CLI & Web](https://img.shields.io/badge/Interface-Rich%20CLI%20%2B%20FastAPI%20Web-22c55e.svg)](pyproject.toml)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-0f172a.svg)](pyproject.toml)

**Open-source PDF hardware specification extraction and automated board troubleshooting CLI & Web utility.**

`spec-miner` transforms dense semiconductor PDF datasheets (microcontrollers, voltage regulators, sensors, and transceivers) into structured, machine-readable specifications and cross-checks live or recorded board telemetry against Operating Conditions, Absolute Maximum Ratings, thermal envelopes, pin voltage domains, and silicon errata.

## ✨ Key Capabilities

| Capability | Description | Output / Action |
| :--- | :--- | :--- |
| **PDF Spec Mining** | Parses electrical tables (`Min` / `Typ` / `Max`), pinouts, packages, interfaces (`I2C`, `SPI`, `UART`, `CAN`, `USB`, `ADC`), and thermal constants ($\theta_{JA}$, $\theta_{JC}$, $T_{J(\max)}$) using `pdfplumber` and `pypdf`. | `HardwareSpec` dataclass, JSON, CSV, Markdown, HTML |
| **Electrical Limit Diagnostics** | Validates measured board voltages, currents, and clock frequencies against Recommended Operating limits, configurable 5% guardbands, and Absolute Maximum Ratings. | `CRITICAL`, `WARNING`, `PASS`, or `INFO` findings |
| **Thermal Junction Estimator** | Computes silicon junction temperature ($T_J = T_A + P_D \times \theta_{JA}$) from ambient temperature and power dissipation and flags thermal derating violations. | Estimated $T_J$ (°C) & PCB cooling remediations |
| **Pin Domain & State Auditor** | Detects 5V overvoltage applied to non-5V-tolerant (`3.3V only`) pins and flags floating reset/input pins susceptible to CMOS shoot-through or spurious resets. | Pin-level DRC warnings & level-shifting fixes |
| **Silicon Errata & Symptom Matcher** | Correlates observed board symptoms (e.g., `I2C1 bus stuck`, `ADC reading noisy`, `brownout reset`) against extracted silicon errata tables and an embedded hardware fault knowledge base. | Matched errata codes & step-by-step workarounds |
| **Drop-In Component Comparison** | Compares two PDF datasheets side-by-side across package footprints and operating electrical ranges to evaluate second-source or drop-in replacements. | Terminal & programmatic compatibility matrix |
| **Interactive Web Dashboard & API** | Ships with a built-in dark-mode FastAPI web interface and REST endpoints for drag-and-drop PDF parsing and live troubleshooting. | Browser UI at `http://127.0.0.1:8000` + JSON API |

## 🏗️ System Architecture

```text
                       ┌──────────────────────────────┐
                       │  Semiconductor PDF Datasheet │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                     ┌────────────────────────────────┐
                     │   DatasheetExtractor Engine    │
                     │  (pdfplumber + pypdf + regex)  │
                     └────────────────┬───────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ Electrical & Thermal │  │ Pinout & Interfaces  │  │ Silicon Errata Notes │
│ (Min/Typ/Max, θJA)   │  │ (Domains, Alt Funcs) │  │ (Symptoms & Fixes)   │
└───────────┬──────────┘  └───────────┬──────────┘  └───────────┬──────────┘
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │     HardwareSpec Model       │
                       └──────────────┬───────────────┘
                                      │
      ┌───────────────────────────────┼───────────────────────────────┐
      ▼                               ▼                               ▼
┌───────────────┐           ┌───────────────────┐           ┌───────────────────┐
│ SpecExporter  │           │ Troubleshooter    │           │ Component Diff    │
│ JSON / MD /   │           │ + Board Telemetry │           │ Drop-In Cross-Ref │
│ CSV / HTML    │           │ + Fault Symptoms  │           │ Compatibility     │
└───────────────┘           └─────────┬─────────┘           └───────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │  Rich CLI & FastAPI Web UI   │
                       └──────────────────────────────┘
```

## 🚀 Quickstart

### 1. Installation

Clone the repository and install `spec-miner` in a Python 3.10+ virtual environment:

```bash
git clone https://github.com/mr-khan/spec-miner.git
cd spec-miner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Run the Built-In Demo

Generate a realistic 2-page microcontroller datasheet PDF (`examples/sample_mcu_datasheet.pdf`) and board fault telemetry payload (`examples/sample_readings.json`), then execute a full extraction and troubleshooting pass in one command:

```bash
spec-miner demo -d ./examples
```

## 💻 Command-Line Interface (CLI) Usage

### Extract Hardware Specifications from a PDF Datasheet

Extract electrical parameters, pinout tables, supported communication buses, and thermal limits to your terminal or export directly to `.json`, `.md`, `.csv`, or `.html`:

```bash
# Pretty-print extracted tables in the terminal
spec-miner extract ./examples/sample_mcu_datasheet.pdf

# Export structured specifications to JSON, Markdown, CSV, or standalone HTML
spec-miner extract ./examples/sample_mcu_datasheet.pdf -o ./examples/stm32_spec.json
spec-miner extract ./examples/sample_mcu_datasheet.pdf -o ./examples/stm32_spec.md
spec-miner extract ./examples/sample_mcu_datasheet.pdf -o ./examples/stm32_params.csv
spec-miner extract ./examples/sample_mcu_datasheet.pdf -o ./examples/stm32_report.html
```

### Troubleshoot Board Telemetry & Fault Symptoms

Pass either a JSON telemetry file (`-t`) or inline measurements (`-m SYMBOL=VALUE`) and observed symptoms (`-s`) to diagnose hardware faults against the datasheet:

```bash
# Diagnose using a recorded telemetry JSON file and export an HTML diagnostic report
spec-miner troubleshoot ./examples/sample_mcu_datasheet.pdf \
  -t ./examples/sample_readings.json \
  -o ./examples/diagnostic_report.html

# Diagnose inline bench measurements and symptoms directly from the shell
spec-miner troubleshoot ./examples/sample_mcu_datasheet.pdf \
  -m VDD=3.95 \
  -m IDD=152.0 \
  -m VREF=1.65 \
  --ambient 65.0 \
  --power 1.45 \
  -s "I2C1 bus stuck with BUSY flag high" \
  -s "ADC reading noisy on channel 0"
```

### Compare Two Datasheets for Drop-In Replacement

Compare package footprints and operating electrical ranges across two PDF datasheets:

```bash
spec-miner compare ./examples/sample_mcu_datasheet.pdf ./examples/candidate_replacement.pdf
```

### Launch the Interactive Web UI & FastAPI Server

Start the local web application and REST API server:

```bash
spec-miner serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser to upload PDF datasheets, edit JSON telemetry payloads, and inspect color-coded diagnostic findings interactively.

## 📊 Sample Diagnostic Output

When running `spec-miner troubleshoot` against `examples/sample_mcu_datasheet.pdf` (`STM32F405RG`) with `examples/sample_readings.json`, the engine produces structured findings across electrical, thermal, pinout, and silicon errata domains:

| Severity | Rule ID | Parameter / Area | Observed | Expected | Diagnosis & Actionable Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `ELEC-OP-MAX-EXCEEDED` | `IDD` (Supply Current Run Mode) | `152.0 mA` | `Min: 15.0, Typ: 87.0, Max: 138.0 mA` | `IDD` exceeds maximum recommended operating limit (`138.0 mA`). Inspect GPIO load shorts or peripheral clock gating. |
| **CRITICAL** | `ELEC-OP-MIN-BELOW` | `VREF` (ADC Reference Voltage) | `1.65 V` | `Min: 1.8, Typ: 3.3, Max: 3.6 V` | `VREF` (`1.65 V`) is below minimum recommended operating limit (`1.8 V`). Check reference LDO and ferrite bead drop. |
| **CRITICAL** | `THERM-TJ-EXCEEDED` | Estimated Junction Temp ($T_J$) | `130.2 °C` ($P_D=1.45\text{ W}$) | `<= 125.0 °C` | Calculated junction temperature (`130.2 °C`) exceeds silicon rating (`125.0 °C`). Reduce power dissipation or lower $\theta_{JA}$. |
| **CRITICAL** | `PIN-DOMAIN-OVERVOLTAGE` | Pin 14 (`PA0`) | `5.0V sensor output applied` | `Domain: 3.3V only` | Applying `5.0V` to non-5V-tolerant pin `PA0` risks ESD diode forward conduction. Use a level shifter or `FT` pin. |
| **WARNING** | `ELEC-GUARDBAND-TIGHT` | `VDD` (Operating Supply Voltage) | `3.55 V` | `Min: 1.8, Typ: 3.3, Max: 3.6 V` | `VDD` (`3.55 V`) is within 5% guardband of upper operating limit (`3.6 V`). Target nominal `3.3 V`. |
| **WARNING** | `PIN-FLOATING-INPUT` | Pin 7 (`NRST`) | `floating (unconnected)` | `Driven High/Low or Pulled Up/Down` | Control pin `NRST` is left floating. Tie `NRST` to `VDD` via external pull-up and 100 nF filter capacitor. |
| **WARNING** | `ERRATA-ERR-101` | Silicon Errata `ERR-101` | `I2C1 bus stuck with BUSY flag high` | `Datasheet Errata Advisory` | Matches silicon errata `ERR-101`. Toggle `SCL` 9 clock pulses via GPIO open-drain and set `SWRST` in `I2C_CR1`. |
| **PASS** | `ELEC-NOMINAL` | `VDDA` (Analog Supply Voltage) | `3.3 V` | `Min: 1.8, Typ: 3.3, Max: 3.6 V` | `VDDA` is within recommended datasheet operating specifications. |

## 🐍 Python SDK Usage

Use `spec_miner` directly inside automated hardware-in-the-loop (HIL) test benches or CI pipelines:

```python
from spec_miner import (
    DatasheetExtractor,
    HardwareTroubleshooter,
    SpecExporter,
    TelemetryReading,
)

# 1. Extract structured specifications from a PDF datasheet
extractor = DatasheetExtractor()
spec = extractor.extract("examples/sample_mcu_datasheet.pdf")

print(f"Mined {spec.part_number} ({spec.manufacturer}) with {len(spec.electrical_parameters)} parameters")

# 2. Validate bench measurements and symptoms against the mined specification
telemetry = TelemetryReading(
    measured_parameters={"VDD": 3.32, "IDD": 149.5, "VREF": 3.30},
    ambient_temp_c=55.0,
    power_dissipation_w=0.95,
    pin_states={"PA0": "5.0V applied", "NRST": "pulled high to 3.3V"},
    symptoms=["I2C1 bus stuck with BUSY flag high"],
)

troubleshooter = HardwareTroubleshooter(guardband_ratio=0.05)
report = troubleshooter.diagnose(spec, telemetry)

print(report.summary)
for finding in report.findings:
    print(f"[{finding.severity.value}] {finding.rule_id}: {finding.message}")

# 3. Export combined specification + diagnostic report to Markdown or HTML
SpecExporter.save("examples/hil_report.html", spec, report=report)
```

## 🌐 REST API Reference

When running `spec-miner serve`, the FastAPI server exposes interactive Swagger docs at `/docs` and the following endpoints:

| Method | Endpoint | Description | Request Body / Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Interactive single-page web UI for PDF upload and troubleshooting | None |
| `GET` | `/api/health` | Service health and version check | None |
| `POST` | `/api/extract` | Parse an uploaded PDF datasheet and return `hardware_spec` JSON | `multipart/form-data`: `file` (`.pdf`) |
| `POST` | `/api/troubleshoot` | Parse an uploaded PDF and evaluate against `telemetry` JSON | `multipart/form-data`: `file` (`.pdf`), `telemetry` (JSON string) |
| `POST` | `/api/demo` | Run built-in MCU datasheet extraction & fault troubleshooting demo | None |

## 📁 Repository Structure

```text
spec-miner/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Automated test matrix (Python 3.10, 3.11, 3.12)
├── examples/
│   ├── sample_mcu_datasheet.pdf    # Generated 2-page STM32F405RG datasheet PDF
│   ├── sample_readings.json        # Sample board telemetry & fault symptoms payload
│   └── sample_report.md            # Example exported Markdown specification report
├── src/
│   └── spec_miner/
│       ├── __init__.py             # Public package exports and version metadata
│       ├── models.py               # Dataclasses for specs, pins, thermal, errata & diagnostics
│       ├── extractor.py            # PDF table & text specification miner
│       ├── troubleshooter.py       # Electrical, thermal, pin & symptom diagnostic engine
│       ├── exporter.py             # JSON, Markdown, CSV, and HTML report generators
│       ├── sample_generator.py     # ReportLab PDF datasheet & telemetry generator
│       ├── cli.py                  # Click + Rich terminal CLI
│       └── web.py                  # FastAPI interactive Web UI & REST API
├── tests/
│   └── test_spec_miner.py          # End-to-end unit & integration test suite
├── CHANGELOG.md                    # Release history and version notes
├── CONTRIBUTING.md                 # Developer setup and contribution guidelines
├── LICENSE                         # MIT License
├── Makefile                        # Developer targets (install, test, demo, serve, clean)
├── pyproject.toml                  # PEP 621 package configuration & entry points
├── requirements.txt                # Runtime and testing dependencies
└── README.md                       # Project documentation
```

## 🧪 Running Tests

Run the full unit and integration test suite using `unittest` or `make`:

```bash
make test
# or directly:
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 🤝 Contributing

Contributions, vendor datasheet heuristics, and new hardware diagnostic rules are welcome! Please review `CONTRIBUTING.md` before submitting a pull request.

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for full license text. Copyright (c) 2026 Mr Khan.
