"""
Command-Line Interface (`cli.py`) for `spec-miner`.

Commands:
- `spec-miner extract <pdf>`       : Mine electrical specs, pinouts, interfaces & errata
- `spec-miner troubleshoot <pdf>`  : Diagnose board telemetry & symptoms against datasheet
- `spec-miner compare <pdfA> <pdfB>`: Compare two component datasheets for drop-in replacement
- `spec-miner demo`                : Generate sample PDF datasheet & run live diagnostic demo
- `spec-miner serve`               : Launch the interactive Web UI & REST API server
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .exporter import SpecExporter
from .extractor import DatasheetExtractor
from .models import DiagnosticReport, HardwareSpec, Severity, TelemetryReading
from .sample_generator import generate_demo_bundle
from .troubleshooter import HardwareTroubleshooter

console = Console()


def _render_spec_to_console(spec: HardwareSpec) -> None:
    """Pretty-print a mined HardwareSpec using Rich panels and tables."""
    header_text = (
        f"[bold cyan]{spec.part_number}[/bold cyan] — [bold]{spec.manufacturer}[/bold]\n"
        f"[dim]{spec.description}[/dim]\n\n"
        f"[bold]Category:[/bold] {spec.category}  |  "
        f"[bold]Packages:[/bold] {', '.join(spec.package_types) or 'N/A'}  |  "
        f"[bold]Pages:[/bold] {spec.page_count}"
    )
    console.print(Panel(header_text, title="⚡ Mined Hardware Specification", border_style="cyan"))

    if spec.electrical_parameters:
        table = Table(title="Electrical Characteristics", show_lines=False, header_style="bold cyan")
        table.add_column("Symbol", style="bold yellow")
        table.add_column("Parameter")
        table.add_column("Category", style="dim")
        table.add_column("Min", justify="right")
        table.add_column("Typ", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Unit")
        table.add_column("Conditions", style="dim")

        for p in spec.electrical_parameters:
            table.add_row(
                p.symbol,
                p.parameter,
                p.category,
                "-" if p.min_val is None else str(p.min_val),
                "-" if p.typ_val is None else str(p.typ_val),
                "-" if p.max_val is None else str(p.max_val),
                p.unit,
                p.conditions,
            )
        console.print(table)

    if spec.pinout:
        pin_table = Table(title="Pin Configuration", header_style="bold magenta")
        pin_table.add_column("Pin #", style="bold")
        pin_table.add_column("Name", style="cyan")
        pin_table.add_column("Type")
        pin_table.add_column("Voltage Domain")
        pin_table.add_column("Description")
        for pin in spec.pinout:
            pin_table.add_row(
                pin.pin_number,
                pin.name,
                pin.pin_type,
                pin.voltage_domain or "-",
                pin.description,
            )
        console.print(pin_table)


def _render_report_to_console(report: DiagnosticReport) -> None:
    """Pretty-print a DiagnosticReport using Rich tables."""
    color_map = {
        Severity.CRITICAL: "red",
        Severity.WARNING: "yellow",
        Severity.PASS: "green",
        Severity.INFO: "blue",
    }
    b_color = color_map.get(report.overall_status, "cyan")
    console.print(
        Panel(
            f"[bold {b_color}]{report.summary}[/bold {b_color}]",
            title="🔍 Hardware Troubleshooting Report",
            border_style=b_color,
        )
    )

    table = Table(title="Diagnostic Findings & Remediations", show_lines=True)
    table.add_column("Severity", style="bold")
    table.add_column("Rule ID", style="cyan")
    table.add_column("Parameter / Area")
    table.add_column("Observed")
    table.add_column("Expected")
    table.add_column("Diagnosis & Action")

    for f in report.findings:
        sev_col = color_map.get(f.severity, "white")
        table.add_row(
            f"[{sev_col}]{f.severity.value}[/{sev_col}]",
            f.rule_id,
            f.parameter_or_area,
            f.observed,
            f.expected,
            f"{f.message}\n[dim]Fix: {f.remediation}[/dim]",
        )
    console.print(table)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="spec-miner")
def main() -> None:
    """spec-miner: Open-source PDF hardware spec extraction and troubleshooting CLI/web utility."""


@main.command("extract")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Export path (.json, .md, .csv, or .html).",
)
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["json", "md", "csv", "html"], case_sensitive=False),
    help="Explicit export format override.",
)
@click.option("--quiet", is_flag=True, help="Suppress rich console table output.")
@click.option("--ocr", is_flag=True, help="Force OCR for image-based / scanned PDFs.")
def extract_cmd(
    pdf_path: Path, output: Optional[Path], fmt: Optional[str], quiet: bool, ocr: bool
) -> None:
    """Extract electrical specifications, pinouts, thermal limits, and errata from a PDF datasheet."""
    extractor = DatasheetExtractor(enable_ocr=ocr)
    spec = extractor.extract(pdf_path)

    if not quiet:
        _render_spec_to_console(spec)

    if output:
        saved = SpecExporter.save(output, spec, fmt=fmt)
        console.print(f"[bold green]✓ Saved extracted specifications to:[/bold green] {saved}")
    elif fmt:
        if fmt.lower() == "json":
            click.echo(SpecExporter.to_json(spec))
        elif fmt.lower() == "md":
            click.echo(SpecExporter.to_markdown(spec))
        elif fmt.lower() == "csv":
            click.echo(SpecExporter.to_csv(spec))
        elif fmt.lower() == "html":
            click.echo(SpecExporter.to_html(spec))


@main.command("troubleshoot")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-t",
    "--telemetry",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to JSON file containing measured parameters, ambient temp, pin states, and symptoms.",
)
@click.option(
    "-m",
    "--measure",
    multiple=True,
    help="Inline measurement in SYMBOL=VALUE format (e.g., -m VDD=3.85 -m IDD=150).",
)
@click.option(
    "-s",
    "--symptom",
    multiple=True,
    help="Observed fault symptom description (repeatable, e.g., -s 'I2C1 bus stuck').",
)
@click.option("--ambient", type=float, default=None, help="Measured ambient temperature in °C.")
@click.option("--power", type=float, default=None, help="Estimated package power dissipation in Watts.")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Export diagnostic report to file (.json, .md, or .html).",
)
@click.option("--ocr", is_flag=True, help="Force OCR for image-based / scanned PDFs.")
def troubleshoot_cmd(
    pdf_path: Path,
    telemetry: Optional[Path],
    measure: Tuple[str, ...],
    symptom: Tuple[str, ...],
    ambient: Optional[float],
    power: Optional[float],
    output: Optional[Path],
    ocr: bool,
) -> None:
    """Validate live or recorded hardware measurements and symptoms against a PDF datasheet."""
    extractor = DatasheetExtractor(enable_ocr=ocr)
    spec = extractor.extract(pdf_path)

    measured_params: Dict[str, float] = {}
    symptoms_list: List[str] = []
    pin_states: Dict[str, str] = {}
    ambient_val = ambient
    power_val = power

    if telemetry:
        raw = json.loads(telemetry.read_text(encoding="utf-8"))
        for k, v in raw.get("measured_parameters", {}).items():
            measured_params[str(k)] = float(v)
        if ambient_val is None and raw.get("ambient_temp_c") is not None:
            ambient_val = float(raw["ambient_temp_c"])
        if power_val is None and raw.get("power_dissipation_w") is not None:
            power_val = float(raw["power_dissipation_w"])
        symptoms_list.extend(raw.get("symptoms", []))
        pin_states.update(raw.get("pin_states", {}))

    for item in measure:
        if "=" not in item:
            raise click.BadParameter(f"Measurement '{item}' must use SYMBOL=VALUE format (e.g. VDD=3.3)")
        k, v_str = item.split("=", 1)
        measured_params[k.strip()] = float(v_str.strip())

    symptoms_list.extend(symptom)

    reading = TelemetryReading(
        measured_parameters=measured_params,
        ambient_temp_c=ambient_val,
        power_dissipation_w=power_val,
        symptoms=symptoms_list,
        pin_states=pin_states,
    )

    engine = HardwareTroubleshooter()
    report = engine.diagnose(spec, reading)
    _render_report_to_console(report)

    if output:
        saved = SpecExporter.save(output, spec, report=report)
        console.print(f"[bold green]✓ Saved diagnostic report to:[/bold green] {saved}")


@main.command("compare")
@click.argument("pdf_a", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("pdf_b", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def compare_cmd(pdf_a: Path, pdf_b: Path) -> None:
    """Compare two PDF datasheets side-by-side for drop-in replacement compatibility."""
    extractor = DatasheetExtractor()
    spec_a = extractor.extract(pdf_a)
    spec_b = extractor.extract(pdf_b)

    engine = HardwareTroubleshooter()
    diff = engine.compare_specs(spec_a, spec_b)

    table = Table(
        title=f"Component Comparison: {spec_a.part_number} vs {spec_b.part_number}",
        header_style="bold cyan",
    )
    table.add_column("Attribute / Parameter", style="bold")
    table.add_column(spec_a.part_number, style="yellow")
    table.add_column(spec_b.part_number, style="green")
    table.add_column("Compatibility Assessment")

    for row in diff["rows"]:
        table.add_row(
            row["attribute"] or "",
            row["spec_a"] or "",
            row["spec_b"] or "",
            row["compatibility"] or "",
        )
    console.print(table)


@main.command("demo")
@click.option(
    "-d",
    "--dir",
    "target_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./examples"),
    show_default=True,
    help="Directory where sample PDF datasheet and telemetry JSON will be generated.",
)
def demo_cmd(target_dir: Path) -> None:
    """Generate a sample MCU datasheet PDF and telemetry JSON, then run a live diagnostic demo."""
    pdf_path, json_path = generate_demo_bundle(target_dir)
    console.print(
        f"[bold green]✓ Generated sample datasheet:[/bold green] {pdf_path}\n"
        f"[bold green]✓ Generated sample telemetry:[/bold green] {json_path}\n"
    )

    extractor = DatasheetExtractor()
    spec = extractor.extract(pdf_path)
    _render_spec_to_console(spec)

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    reading = TelemetryReading(
        measured_parameters={k: float(v) for k, v in raw["measured_parameters"].items()},
        ambient_temp_c=raw["ambient_temp_c"],
        power_dissipation_w=raw["power_dissipation_w"],
        symptoms=raw["symptoms"],
        pin_states=raw["pin_states"],
    )
    engine = HardwareTroubleshooter()
    report = engine.diagnose(spec, reading)
    _render_report_to_console(report)


@main.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
def serve_cmd(host: str, port: int) -> None:
    """Launch the interactive Web UI and FastAPI REST server."""
    import uvicorn

    console.print(
        Panel(
            f"Starting [bold cyan]spec-miner[/bold cyan] Web UI & API server at [underline]http://{host}:{port}[/underline]",
            border_style="cyan",
        )
    )
    uvicorn.run("spec_miner.web:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
