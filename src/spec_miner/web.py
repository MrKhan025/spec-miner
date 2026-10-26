"""
FastAPI Web Application & Interactive Troubleshooting Dashboard (`web.py`).

Provides:
- Interactive browser UI (`GET /`) for uploading PDF datasheets, mining specs,
  and running live hardware diagnostics.
- REST API endpoints:
  - `GET /api/health`
  - `POST /api/extract`
  - `POST /api/troubleshoot`
  - `POST /api/demo`
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from . import __version__
from .extractor import DatasheetExtractor
from .models import TelemetryReading
from .sample_generator import generate_demo_bundle
from .troubleshooter import HardwareTroubleshooter

app = FastAPI(
    title="spec-miner Web & API Utility",
    description="Open-source PDF hardware specification extraction and troubleshooting engine",
    version=__version__,
)

extractor = DatasheetExtractor()
troubleshooter = HardwareTroubleshooter()


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>spec-miner — PDF Hardware Spec Extractor &amp; Troubleshooter</title>
  <style>
    :root {
      --bg: #0b1120;
      --panel: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --crit: #ef4444;
      --warn: #f59e0b;
      --pass: #22c55e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }
    header {
      border-bottom: 1px solid var(--border);
      background: rgba(15, 23, 42, 0.9);
      padding: 1.1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    header h1 { margin: 0; font-size: 1.35rem; letter-spacing: -0.02em; }
    header span.tag {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
      padding: 0.2rem 0.65rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    main { max-width: 1240px; margin: 1.8rem auto; padding: 0 1.5rem; display: grid; grid-template-columns: 380px 1fr; gap: 1.5rem; }
    @media (max-width: 920px) { main { grid-template-columns: 1fr; } }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.35rem;
      margin-bottom: 1.25rem;
    }
    .card h2 { margin-top: 0; font-size: 1.05rem; color: var(--accent); }
    label { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 0.35rem; margin-top: 0.85rem; }
    input[type="file"], textarea {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      padding: 0.6rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.82rem;
    }
    textarea { min-height: 170px; resize: vertical; }
    .btn-row { display: flex; gap: 0.65rem; margin-top: 1rem; }
    button {
      cursor: pointer;
      border: none;
      border-radius: 8px;
      padding: 0.65rem 1rem;
      font-weight: 600;
      font-size: 0.88rem;
      transition: background 0.15s;
    }
    button.primary { background: var(--accent); color: #0f172a; flex: 1; }
    button.primary:hover { background: var(--accent-hover); color: white; }
    button.secondary { background: #334155; color: var(--text); }
    button.secondary:hover { background: #475569; }
    table { width: 100%; border-collapse: collapse; font-size: 0.86rem; margin-top: 0.65rem; }
    th, td { border-bottom: 1px solid var(--border); padding: 0.55rem 0.6rem; text-align: left; }
    th { color: var(--muted); font-weight: 600; background: rgba(15, 23, 42, 0.5); }
    .badge { padding: 0.18rem 0.55rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700; display: inline-block; }
    .CRITICAL { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--crit); }
    .WARNING { background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid var(--warn); }
    .PASS { background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid var(--pass); }
    .INFO { background: rgba(56, 189, 248, 0.2); color: #7dd3fc; border: 1px solid var(--accent); }
    code { background: #0f172a; padding: 0.15rem 0.4rem; border-radius: 4px; color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1>⚡ spec-miner <small style="color:var(--muted);font-weight:400;">PDF Hardware Spec Extraction &amp; Troubleshooting</small></h1>
    <span class="tag">v1.0.0 • MIT License</span>
  </header>
  <main>
    <section>
      <div class="card">
        <h2>1. Upload Datasheet &amp; Telemetry</h2>
        <form id="analyzeForm">
          <label for="pdfFile">Hardware Datasheet (PDF)</label>
          <input type="file" id="pdfFile" name="file" accept=".pdf">

          <label for="telemetryJson">Measured Telemetry &amp; Symptoms (JSON)</label>
          <textarea id="telemetryJson">{
  "measured_parameters": {
    "VDD": 3.55,
    "IDD": 152.0,
    "VREF": 1.65
  },
  "ambient_temp_c": 65.0,
  "power_dissipation_w": 1.45,
  "pin_states": {
    "PA0": "5.0V sensor output applied",
    "NRST": "floating"
  },
  "symptoms": [
    "I2C1 bus stuck with BUSY flag high",
    "ADC reading noisy on channel 0"
  ]
}</textarea>
          <div class="btn-row">
            <button type="submit" class="primary">Extract &amp; Troubleshoot</button>
            <button type="button" id="demoBtn" class="secondary">Run Built-in Demo</button>
          </div>
        </form>
      </div>
    </section>

    <section id="resultsArea">
      <div class="card">
        <h2>2. Interactive Results</h2>
        <p style="color:var(--muted);">Upload a datasheet PDF or click <strong>Run Built-in Demo</strong> to inspect extracted electrical limits, pin configurations, silicon errata, and automated root-cause diagnostics.</p>
      </div>
    </section>
  </main>

  <script>
    const resultsArea = document.getElementById('resultsArea');
    function renderResponse(data) {
      const spec = data.hardware_spec;
      const diag = data.diagnostic_report;
      let html = `
        <div class="card">
          <h2>Component Overview: ${spec.part_number} (${spec.manufacturer})</h2>
          <p>${spec.description}</p>
          <p><strong>Category:</strong> ${spec.category} | <strong>Packages:</strong> ${(spec.package_types || []).join(', ') || 'N/A'} | <strong>Thermal θJA:</strong> ${spec.thermal.theta_ja_c_per_w ?? 'N/A'} °C/W</p>
        </div>
      `;
      if (diag) {
        const rows = (diag.findings || []).map(f => `
          <tr>
            <td><span class="badge ${f.severity}">${f.severity}</span></td>
            <td><code>${f.rule_id}</code></td>
            <td>${f.parameter_or_area}</td>
            <td>${f.observed}</td>
            <td>${f.expected}</td>
            <td><strong>${f.message}</strong><br><small style="color:var(--muted)">Fix: ${f.remediation}</small></td>
          </tr>
        `).join('');
        html += `
          <div class="card">
            <h2>Diagnostic &amp; Troubleshooting Findings</h2>
            <p><strong>${diag.summary}</strong></p>
            <table>
              <thead><tr><th>Severity</th><th>Rule</th><th>Parameter / Area</th><th>Observed</th><th>Expected</th><th>Diagnosis &amp; Remediation</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        `;
      }
      const pRows = (spec.electrical_parameters || []).map(p => `
        <tr>
          <td><code>${p.symbol}</code></td>
          <td>${p.parameter}</td>
          <td>${p.category}</td>
          <td>${p.min_val ?? '-'}</td>
          <td>${p.typ_val ?? '-'}</td>
          <td>${p.max_val ?? '-'}</td>
          <td>${p.unit}</td>
        </tr>
      `).join('');
      html += `
        <div class="card">
          <h2>Extracted Electrical Parameters (${(spec.electrical_parameters || []).length})</h2>
          <table>
            <thead><tr><th>Symbol</th><th>Parameter</th><th>Category</th><th>Min</th><th>Typ</th><th>Max</th><th>Unit</th></tr></thead>
            <tbody>${pRows}</tbody>
          </table>
        </div>
      `;
      resultsArea.innerHTML = html;
    }

    document.getElementById('demoBtn').addEventListener('click', async () => {
      const res = await fetch('/api/demo', { method: 'POST' });
      const data = await res.json();
      renderResponse(data);
    });

    document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById('pdfFile');
      const telemetryText = document.getElementById('telemetryJson').value;
      if (!fileInput.files.length) {
        alert('Please select a PDF datasheet first, or click "Run Built-in Demo".');
        return;
      }
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('telemetry', telemetryText);
      const res = await fetch('/api/troubleshoot', { method: 'POST', body: fd });
      const data = await res.json();
      renderResponse(data);
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the interactive single-page web utility."""
    return HTMLResponse(content=INDEX_HTML)


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__, "service": "spec-miner"}


@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)) -> JSONResponse:
    """Extract structured hardware specifications from an uploaded PDF datasheet."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF (.pdf)")

    content = await file.read()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / file.filename
        tmp_pdf.write_bytes(content)
        spec = extractor.extract(tmp_pdf)

    return JSONResponse(content={"hardware_spec": spec.to_dict()})


@app.post("/api/troubleshoot")
async def api_troubleshoot(
    file: UploadFile = File(...),
    telemetry: Optional[str] = Form(default=None),
) -> JSONResponse:
    """Extract hardware specs from an uploaded PDF and run diagnostic troubleshooting."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF (.pdf)")

    telemetry_obj = TelemetryReading()
    if telemetry:
        try:
            raw: Dict[str, Any] = json.loads(telemetry)
            telemetry_obj = TelemetryReading(
                measured_parameters={
                    k: float(v) for k, v in raw.get("measured_parameters", {}).items()
                },
                ambient_temp_c=raw.get("ambient_temp_c"),
                power_dissipation_w=raw.get("power_dissipation_w"),
                symptoms=raw.get("symptoms", []),
                pin_states=raw.get("pin_states", {}),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid telemetry JSON payload: {exc}"
            ) from exc

    content = await file.read()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / file.filename
        tmp_pdf.write_bytes(content)
        spec = extractor.extract(tmp_pdf)
        report = troubleshooter.diagnose(spec, telemetry_obj)

    return JSONResponse(
        content={
            "hardware_spec": spec.to_dict(),
            "diagnostic_report": report.to_dict(),
        }
    )


@app.post("/api/demo")
def api_demo() -> JSONResponse:
    """Run an instant end-to-end extraction and troubleshooting demo using a generated MCU datasheet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path, json_path = generate_demo_bundle(tmpdir)
        spec = extractor.extract(pdf_path)
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        reading = TelemetryReading(
            measured_parameters={
                k: float(v) for k, v in raw.get("measured_parameters", {}).items()
            },
            ambient_temp_c=raw.get("ambient_temp_c"),
            power_dissipation_w=raw.get("power_dissipation_w"),
            symptoms=raw.get("symptoms", []),
            pin_states=raw.get("pin_states", {}),
        )
        report = troubleshooter.diagnose(spec, reading)

    return JSONResponse(
        content={
            "hardware_spec": spec.to_dict(),
            "diagnostic_report": report.to_dict(),
        }
    )
