"""
Specification & Diagnostic Exporter (`exporter.py`).

Exports extracted `HardwareSpec` and `DiagnosticReport` models to:
- JSON (`.json`)
- Markdown (`.md`)
- CSV tables (`.csv`)
- Standalone styled HTML report (`.html`)
"""

from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path
from typing import Optional

from .models import DiagnosticReport, HardwareSpec


class SpecExporter:
    """Serializes HardwareSpec and DiagnosticReport to JSON, Markdown, CSV, and HTML."""

    @staticmethod
    def to_json(
        spec: HardwareSpec,
        report: Optional[DiagnosticReport] = None,
        indent: int = 2,
    ) -> str:
        payload = {"hardware_spec": spec.to_dict()}
        if report is not None:
            payload["diagnostic_report"] = report.to_dict()
        return json.dumps(payload, indent=indent)

    @staticmethod
    def to_csv(spec: HardwareSpec) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["Symbol", "Parameter", "Category", "Min", "Typ", "Max", "Unit", "Conditions"]
        )
        for p in spec.electrical_parameters:
            writer.writerow(
                [
                    p.symbol,
                    p.parameter,
                    p.category,
                    "" if p.min_val is None else p.min_val,
                    "" if p.typ_val is None else p.typ_val,
                    "" if p.max_val is None else p.max_val,
                    p.unit,
                    p.conditions,
                ]
            )
        return buf.getvalue()

    @staticmethod
    def to_markdown(
        spec: HardwareSpec, report: Optional[DiagnosticReport] = None
    ) -> str:
        lines = [
            f"# Hardware Specification Report: `{spec.part_number}`",
            "",
            f"- **Manufacturer:** {spec.manufacturer}",
            f"- **Category:** {spec.category}",
            f"- **Packages:** {', '.join(spec.package_types) if spec.package_types else 'N/A'}",
            f"- **Source PDF:** `{spec.source_file}` ({spec.page_count} pages)",
            f"- **Description:** {spec.description}",
            "",
        ]

        if spec.features:
            lines.append("## Key Features")
            for feat in spec.features:
                lines.append(f"- {feat}")
            lines.append("")

        if spec.electrical_parameters:
            lines.extend(
                [
                    "## Electrical Characteristics",
                    "",
                    "| Symbol | Parameter | Category | Min | Typ | Max | Unit | Conditions |",
                    "| :--- | :--- | :--- | ---: | ---: | ---: | :--- | :--- |",
                ]
            )
            for p in spec.electrical_parameters:
                min_s = "-" if p.min_val is None else f"{p.min_val}"
                typ_s = "-" if p.typ_val is None else f"{p.typ_val}"
                max_s = "-" if p.max_val is None else f"{p.max_val}"
                lines.append(
                    f"| `{p.symbol}` | {p.parameter} | {p.category} | {min_s} | {typ_s} | {max_s} | {p.unit} | {p.conditions} |"
                )
            lines.append("")

        th = spec.thermal
        if any(
            v is not None
            for v in (
                th.operating_temp_min_c,
                th.operating_temp_max_c,
                th.max_junction_temp_c,
                th.theta_ja_c_per_w,
            )
        ):
            lines.extend(
                [
                    "## Thermal Characteristics",
                    "",
                    f"- **Operating Temperature Range:** {th.operating_temp_min_c} °C to {th.operating_temp_max_c} °C",
                    f"- **Maximum Junction Temperature ($T_{{J(\\max)}}$):** {th.max_junction_temp_c} °C",
                    f"- **Thermal Resistance ($\\theta_{{JA}}$):** {th.theta_ja_c_per_w} °C/W",
                    f"- **Thermal Resistance ($\\theta_{{JC}}$):** {th.theta_jc_c_per_w} °C/W",
                    "",
                ]
            )

        if spec.pinout:
            lines.extend(
                [
                    "## Pin Configuration",
                    "",
                    "| Pin # | Name | Type | Voltage Domain | Description |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for pin in spec.pinout:
                lines.append(
                    f"| {pin.pin_number} | `{pin.name}` | {pin.pin_type} | {pin.voltage_domain or '-'} | {pin.description} |"
                )
            lines.append("")

        if spec.errata:
            lines.extend(
                [
                    "## Known Silicon Errata",
                    "",
                    "| Code | Title | Symptom | Workaround |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            for err in spec.errata:
                lines.append(
                    f"| `{err.code}` | {err.title} | {err.symptom} | {err.workaround} |"
                )
            lines.append("")

        if report is not None:
            lines.extend(
                [
                    "## Hardware Diagnostic & Troubleshooting Report",
                    "",
                    f"**Summary:** {report.summary}",
                    "",
                    "| Severity | Rule ID | Parameter / Area | Observed | Expected | Diagnosis & Remediation |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for f in report.findings:
                lines.append(
                    f"| **{f.severity.value}** | `{f.rule_id}` | {f.parameter_or_area} | {f.observed} | {f.expected} | {f.message} **Fix:** {f.remediation} |"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_html(
        spec: HardwareSpec, report: Optional[DiagnosticReport] = None
    ) -> str:
        """Render a standalone styled HTML datasheet & troubleshooting report."""
        esc = html.escape
        rows_elec = "".join(
            f"<tr><td><code>{esc(p.symbol)}</code></td><td>{esc(p.parameter)}</td>"
            f"<td>{esc(p.category)}</td>"
            f"<td class='num'>{'' if p.min_val is None else p.min_val}</td>"
            f"<td class='num'>{'' if p.typ_val is None else p.typ_val}</td>"
            f"<td class='num'>{'' if p.max_val is None else p.max_val}</td>"
            f"<td>{esc(p.unit)}</td><td>{esc(p.conditions)}</td></tr>"
            for p in spec.electrical_parameters
        )

        rows_diag = ""
        if report:
            for f in report.findings:
                badge_cls = f.severity.value.lower()
                rows_diag += (
                    f"<tr><td><span class='badge {badge_cls}'>{esc(f.severity.value)}</span></td>"
                    f"<td><code>{esc(f.rule_id)}</code></td>"
                    f"<td>{esc(f.parameter_or_area)}</td>"
                    f"<td>{esc(f.observed)}</td>"
                    f"<td>{esc(f.expected)}</td>"
                    f"<td><strong>{esc(f.message)}</strong><br><small>{esc(f.remediation)}</small></td></tr>"
                )

        diag_section = (
            f"""
            <section class="card">
              <h2>Diagnostic &amp; Troubleshooting Report</h2>
              <p class="summary">{esc(report.summary)}</p>
              <table>
                <thead>
                  <tr><th>Severity</th><th>Rule ID</th><th>Area</th><th>Observed</th><th>Expected</th><th>Diagnosis &amp; Action</th></tr>
                </thead>
                <tbody>{rows_diag}</tbody>
              </table>
            </section>
            """
            if report
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>spec-miner Report — {esc(spec.part_number)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 2rem; }}
    .container {{ max-width: 1120px; margin: 0 auto; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; }}
    h1, h2 {{ color: #f8fafc; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.92rem; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 0.65rem 0.75rem; text-align: left; }}
    th {{ background: #0f172a; color: #94a3b8; font-weight: 600; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    code {{ background: #0f172a; padding: 0.15rem 0.4rem; border-radius: 4px; color: #38bdf8; }}
    .badge {{ padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }}
    .badge.critical {{ background: #7f1d1d; color: #fecaca; }}
    .badge.warning {{ background: #78350f; color: #fde68a; }}
    .badge.pass {{ background: #14532d; color: #bbf7d0; }}
    .badge.info {{ background: #1e3a8a; color: #bfdbfe; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>{esc(spec.part_number)} — <small>{esc(spec.manufacturer)}</small></h1>
      <p>{esc(spec.description)}</p>
      <p><strong>Category:</strong> {esc(spec.category)} | <strong>Packages:</strong> {esc(', '.join(spec.package_types) or 'N/A')} | <strong>Pages:</strong> {spec.page_count}</p>
    </div>
    {diag_section}
    <div class="card">
      <h2>Electrical Parameters</h2>
      <table>
        <thead>
          <tr><th>Symbol</th><th>Parameter</th><th>Category</th><th>Min</th><th>Typ</th><th>Max</th><th>Unit</th><th>Conditions</th></tr>
        </thead>
        <tbody>{rows_elec}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""

    @classmethod
    def save(
        cls,
        output_path: str | Path,
        spec: HardwareSpec,
        report: Optional[DiagnosticReport] = None,
        fmt: Optional[str] = None,
    ) -> Path:
        """Save HardwareSpec (and optional DiagnosticReport) to disk based on extension or format."""
        path = Path(output_path)
        ext = (fmt or path.suffix.lstrip(".")).lower()
        if ext == "json":
            content = cls.to_json(spec, report)
        elif ext in ("md", "markdown"):
            content = cls.to_markdown(spec, report)
        elif ext == "csv":
            content = cls.to_csv(spec)
        elif ext in ("html", "htm"):
            content = cls.to_html(spec, report)
        else:
            raise ValueError(f"Unsupported export format: {ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
