"""
Data models for hardware specification extraction and diagnostic troubleshooting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Severity levels for hardware diagnostic findings."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"


@dataclass
class ElectricalParameter:
    """Represents a single electrical operating or absolute maximum parameter."""

    symbol: str
    parameter: str
    min_val: Optional[float] = None
    typ_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: str = ""
    conditions: str = ""
    category: str = "Operating"  # "Absolute Maximum" or "Operating"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PinDefinition:
    """Represents a hardware pinout definition extracted from a datasheet."""

    pin_number: str
    name: str
    pin_type: str  # e.g., Power, I/O, Input, Output, Analog, GND
    description: str = ""
    alternate_functions: List[str] = field(default_factory=list)
    voltage_domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SupportedInterface:
    """Represents a communication or peripheral interface supported by the component."""

    protocol: str  # e.g., I2C, SPI, UART, CAN, USB, PWM, ADC
    count: int = 1
    max_speed: str = ""
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThermalCharacteristics:
    """Thermal resistance and operating temperature specifications."""

    operating_temp_min_c: Optional[float] = None
    operating_temp_max_c: Optional[float] = None
    storage_temp_min_c: Optional[float] = None
    storage_temp_max_c: Optional[float] = None
    max_junction_temp_c: Optional[float] = None
    theta_ja_c_per_w: Optional[float] = None
    theta_jc_c_per_w: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrataItem:
    """Known hardware silicon errata or troubleshooting note from documentation."""

    code: str
    title: str
    symptom: str
    workaround: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HardwareSpec:
    """Complete structured hardware specification mined from a PDF datasheet."""

    part_number: str
    manufacturer: str = "Unknown"
    category: str = "Integrated Circuit"
    description: str = ""
    package_types: List[str] = field(default_factory=list)
    source_file: str = ""
    page_count: int = 0
    features: List[str] = field(default_factory=list)
    electrical_parameters: List[ElectricalParameter] = field(default_factory=list)
    pinout: List[PinDefinition] = field(default_factory=list)
    interfaces: List[SupportedInterface] = field(default_factory=list)
    thermal: ThermalCharacteristics = field(default_factory=ThermalCharacteristics)
    errata: List[ErrataItem] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def get_parameter(self, symbol: str) -> Optional[ElectricalParameter]:
        """Look up an electrical parameter by symbol (case-insensitive)."""
        target = symbol.strip().lower()
        for param in self.electrical_parameters:
            if param.symbol.strip().lower() == target:
                return param
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "category": self.category,
            "description": self.description,
            "package_types": self.package_types,
            "source_file": self.source_file,
            "page_count": self.page_count,
            "features": self.features,
            "electrical_parameters": [p.to_dict() for p in self.electrical_parameters],
            "pinout": [p.to_dict() for p in self.pinout],
            "interfaces": [i.to_dict() for i in self.interfaces],
            "thermal": self.thermal.to_dict(),
            "errata": [e.to_dict() for e in self.errata],
            "raw_metadata": self.raw_metadata,
        }


@dataclass
class TelemetryReading:
    """Measured hardware telemetry or observed fault conditions for troubleshooting."""

    measured_parameters: Dict[str, float] = field(default_factory=dict)
    ambient_temp_c: Optional[float] = None
    power_dissipation_w: Optional[float] = None
    symptoms: List[str] = field(default_factory=list)
    pin_states: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnosticFinding:
    """A single diagnostic check result or troubleshooting recommendation."""

    rule_id: str
    severity: Severity
    parameter_or_area: str
    observed: str
    expected: str
    message: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class DiagnosticReport:
    """Aggregate report generated by the hardware troubleshooting engine."""

    part_number: str
    source_file: str
    overall_status: Severity
    summary: str
    estimated_junction_temp_c: Optional[float] = None
    findings: List[DiagnosticFinding] = field(default_factory=list)
    matched_errata: List[ErrataItem] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.PASS)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_number": self.part_number,
            "source_file": self.source_file,
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "estimated_junction_temp_c": self.estimated_junction_temp_c,
            "counts": {
                "critical": self.critical_count,
                "warning": self.warning_count,
                "pass": self.pass_count,
                "total": len(self.findings),
            },
            "findings": [f.to_dict() for f in self.findings],
            "matched_errata": [e.to_dict() for e in self.matched_errata],
        }
