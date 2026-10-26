"""
spec-miner: Open-source PDF hardware specification extraction and troubleshooting CLI/web utility.

Copyright (c) 2026 Mr Khan
Licensed under the MIT License.
"""

__version__ = "1.0.0"
__author__ = "Mr Khan"
__license__ = "MIT"

from .models import (
    DiagnosticFinding,
    DiagnosticReport,
    ElectricalParameter,
    HardwareSpec,
    PinDefinition,
    Severity,
    SupportedInterface,
    TelemetryReading,
    ThermalCharacteristics,
)
from .extractor import DatasheetExtractor
from .troubleshooter import HardwareTroubleshooter
from .exporter import SpecExporter

__all__ = [
    "__version__",
    "DatasheetExtractor",
    "DiagnosticFinding",
    "DiagnosticReport",
    "ElectricalParameter",
    "HardwareSpec",
    "HardwareTroubleshooter",
    "PinDefinition",
    "Severity",
    "SpecExporter",
    "SupportedInterface",
    "TelemetryReading",
    "ThermalCharacteristics",
]
