"""
Comprehensive unit and integration test suite for `spec-miner`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner
from fastapi.testclient import TestClient

from spec_miner.cli import main
from spec_miner.exporter import SpecExporter
from spec_miner.extractor import DatasheetExtractor
from spec_miner.models import Severity, TelemetryReading
from spec_miner.sample_generator import (
    generate_demo_bundle,
    generate_sample_datasheet_pdf,
)
from spec_miner.troubleshooter import HardwareTroubleshooter
from spec_miner.web import app


class TestSpecMinerSuite(unittest.TestCase):
    """End-to-end tests for PDF extraction, hardware troubleshooting, CLI, exporters, and Web API."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp_dir = tempfile.TemporaryDirectory()
        cls.base_path = Path(cls.tmp_dir.name)
        cls.pdf_path, cls.telemetry_path = generate_demo_bundle(cls.base_path)
        cls.extractor = DatasheetExtractor()
        cls.troubleshooter = HardwareTroubleshooter()
        cls.spec = cls.extractor.extract(cls.pdf_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp_dir.cleanup()

    def test_01_pdf_metadata_and_overview_extraction(self) -> None:
        self.assertEqual(self.spec.part_number, "STM32F405RG")
        self.assertEqual(self.spec.manufacturer, "STMicroelectronics")
        self.assertIn("Microcontroller", self.spec.category)
        self.assertIn("LQFP-64", self.spec.package_types)
        self.assertGreaterEqual(len(self.spec.features), 5)

    def test_02_electrical_parameters_extraction(self) -> None:
        vdd = self.spec.get_parameter("VDD")
        self.assertIsNotNone(vdd)
        assert vdd is not None
        self.assertAlmostEqual(vdd.min_val or 0.0, 1.8)
        self.assertAlmostEqual(vdd.typ_val or 0.0, 3.3)
        self.assertAlmostEqual(vdd.max_val or 0.0, 3.6)
        self.assertEqual(vdd.unit, "V")

        vdd_max = self.spec.get_parameter("VDD_MAX")
        self.assertIsNotNone(vdd_max)
        assert vdd_max is not None
        self.assertEqual(vdd_max.category, "Absolute Maximum")
        self.assertAlmostEqual(vdd_max.max_val or 0.0, 4.0)

    def test_03_pinout_thermal_interfaces_and_errata_extraction(self) -> None:
        self.assertGreaterEqual(len(self.spec.pinout), 6)
        pin_names = {p.name for p in self.spec.pinout}
        self.assertIn("PA0", pin_names)
        self.assertIn("NRST", pin_names)

        protocols = {i.protocol for i in self.spec.interfaces}
        self.assertIn("I2C", protocols)
        self.assertIn("SPI", protocols)
        self.assertIn("UART", protocols)

        self.assertEqual(self.spec.thermal.operating_temp_min_c, -40.0)
        self.assertEqual(self.spec.thermal.operating_temp_max_c, 85.0)
        self.assertEqual(self.spec.thermal.max_junction_temp_c, 125.0)
        self.assertEqual(self.spec.thermal.theta_ja_c_per_w, 45.0)

        err_codes = {e.code for e in self.spec.errata}
        self.assertIn("ERR-101", err_codes)
        self.assertIn("ERR-104", err_codes)

    def test_04_troubleshooter_critical_and_warning_detection(self) -> None:
        raw = json.loads(self.telemetry_path.read_text(encoding="utf-8"))
        reading = TelemetryReading(
            measured_parameters=raw["measured_parameters"],
            ambient_temp_c=raw["ambient_temp_c"],
            power_dissipation_w=raw["power_dissipation_w"],
            symptoms=raw["symptoms"],
            pin_states=raw["pin_states"],
        )
        report = self.troubleshooter.diagnose(self.spec, reading)
        self.assertEqual(report.overall_status, Severity.CRITICAL)
        self.assertIsNotNone(report.estimated_junction_temp_c)
        # 65.0 + 1.45 * 45.0 = 130.25 C > 125.0 C Max Junction Temp
        self.assertAlmostEqual(report.estimated_junction_temp_c or 0.0, 130.25)

        rule_ids = {f.rule_id for f in report.findings}
        self.assertIn("ELEC-OP-MAX-EXCEEDED", rule_ids)  # IDD = 152 mA > 138 mA
        self.assertIn("ELEC-OP-MIN-BELOW", rule_ids)     # VREF = 1.65 V < 1.8 V
        self.assertIn("ELEC-GUARDBAND-TIGHT", rule_ids)  # VDD = 3.55 V near 3.6 V
        self.assertIn("THERM-TJ-EXCEEDED", rule_ids)     # Tj = 130.25 C > 125 C
        self.assertIn("PIN-DOMAIN-OVERVOLTAGE", rule_ids)  # 5V on PA0 (3.3V only)
        self.assertIn("PIN-FLOATING-INPUT", rule_ids)    # NRST floating
        self.assertIn("ERRATA-ERR-101", rule_ids)        # Matched I2C1 errata

    def test_05_troubleshooter_nominal_pass(self) -> None:
        nominal = TelemetryReading(
            measured_parameters={"VDD": 3.3, "VDDA": 3.3, "IDD": 85.0},
            ambient_temp_c=25.0,
            power_dissipation_w=0.28,
        )
        report = self.troubleshooter.diagnose(self.spec, nominal)
        self.assertEqual(report.overall_status, Severity.PASS)
        self.assertEqual(report.critical_count, 0)
        self.assertEqual(report.warning_count, 0)

    def test_06_exporters_json_md_csv_html(self) -> None:
        nominal = TelemetryReading(measured_parameters={"VDD": 3.3})
        report = self.troubleshooter.diagnose(self.spec, nominal)

        out_json = SpecExporter.save(self.base_path / "out.json", self.spec, report)
        self.assertTrue(out_json.exists())
        parsed = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(parsed["hardware_spec"]["part_number"], "STM32F405RG")

        out_md = SpecExporter.save(self.base_path / "out.md", self.spec, report)
        self.assertIn("# Hardware Specification Report", out_md.read_text(encoding="utf-8"))

        out_csv = SpecExporter.save(self.base_path / "out.csv", self.spec)
        self.assertIn("Symbol,Parameter,Category", out_csv.read_text(encoding="utf-8"))

        out_html = SpecExporter.save(self.base_path / "out.html", self.spec, report)
        self.assertIn("<!DOCTYPE html>", out_html.read_text(encoding="utf-8"))

    def test_07_cli_commands(self) -> None:
        runner = CliRunner()
        res_extract = runner.invoke(
            main, ["extract", str(self.pdf_path), "--quiet", "-f", "json"]
        )
        self.assertEqual(res_extract.exit_code, 0)
        self.assertIn("STM32F405RG", res_extract.output)

        res_troubleshoot = runner.invoke(
            main,
            [
                "troubleshoot",
                str(self.pdf_path),
                "-m",
                "VDD=3.95",
                "-s",
                "I2C1 bus stuck",
            ],
        )
        self.assertEqual(res_troubleshoot.exit_code, 0)
        self.assertIn("CRITICAL", res_troubleshoot.output)

        res_compare = runner.invoke(
            main, ["compare", str(self.pdf_path), str(self.pdf_path)]
        )
        self.assertEqual(res_compare.exit_code, 0)
        self.assertIn("Exact Match", res_compare.output)

    def test_08_web_api_endpoints(self) -> None:
        client = TestClient(app)
        r_health = client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["status"], "ok")

        r_index = client.get("/")
        self.assertEqual(r_index.status_code, 200)
        self.assertIn("spec-miner", r_index.text)

        r_demo = client.post("/api/demo")
        self.assertEqual(r_demo.status_code, 200)
        payload = r_demo.json()
        self.assertEqual(payload["hardware_spec"]["part_number"], "STM32F405RG")
        self.assertEqual(payload["diagnostic_report"]["overall_status"], "CRITICAL")

        with self.pdf_path.open("rb") as f:
            r_ext = client.post(
                "/api/extract",
                files={"file": ("sample_mcu_datasheet.pdf", f, "application/pdf")},
            )
        self.assertEqual(r_ext.status_code, 200)
        self.assertEqual(r_ext.json()["hardware_spec"]["part_number"], "STM32F405RG")


if __name__ == "__main__":
    unittest.main()
