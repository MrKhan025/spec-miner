"""
Hardware Troubleshooting & Diagnostic Engine (`troubleshooter.py`).

Validates live or recorded board telemetry (voltages, currents, clock frequencies,
thermal dissipation, pin states, and observed fault symptoms) against extracted
PDF datasheet specifications (`HardwareSpec`) and silicon errata.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .models import (
    DiagnosticFinding,
    DiagnosticReport,
    ElectricalParameter,
    ErrataItem,
    HardwareSpec,
    Severity,
    TelemetryReading,
)


class HardwareTroubleshooter:
    """Evaluates hardware telemetry and fault symptoms against extracted datasheet limits."""

    COMMON_FAULT_KB: List[Tuple[str, List[str], str, str]] = [
        (
            "KB-I2C-LOCKUP",
            ["i2c", "sda", "scl", "lockup", "bus stuck", "nack", "ack"],
            "I2C bus contention, missing pull-up resistors, or slave clock-stretching hang.",
            "Verify external pull-up resistors (typically 2.2 kΩ – 4.7 kΩ to VDD) on SDA/SCL and toggle SCL 9 clocks to release stuck slave devices.",
        ),
        (
            "KB-BROWNOUT-RESET",
            ["reset", "brownout", "reboot", "por", "bor", "drop", "unstable"],
            "Supply rail transient droop triggering Brown-Out Reset (BOR) or Power-On Reset (POR).",
            "Place 100 nF ceramic decoupling capacitors within 2 mm of each VDD pin plus a 4.7 µF–10 µF bulk capacitor near the rail entry.",
        ),
        (
            "KB-SPI-TIMING",
            ["spi", "miso", "mosi", "sck", "corrupt", "crc", "garbled"],
            "SPI CPOL/CPHA clock mode mismatch or excessive SCK ringing at high frequency.",
            "Confirm master and slave share identical CPOL/CPHA mode and add 22 Ω–33 Ω series termination resistor on SCK/MOSI near the driver.",
        ),
        (
            "KB-ADC-NOISE",
            ["adc", "jitter", "analog", "noise", "inaccurate", "reading", "vref"],
            "Analog reference (VREF+/VDDA) ripple or source impedance exceeding ADC sampling switch requirement.",
            "Filter VDDA/VREF+ via a ferrite bead + 100 nF/1 µF decoupling network and buffer high-impedance analog sources with a low-noise op-amp.",
        ),
        (
            "KB-THERMAL-THROTTLE",
            ["hot", "overheat", "thermal", "shutdown", "warm", "temperature"],
            "Excessive package power dissipation or insufficient PCB thermal via / copper plane area.",
            "Inspect load currents on GPIO/regulator outputs, verify exposed thermal pad soldering to PCB ground plane, and calculate Tj = Ta + Pd * Theta_JA.",
        ),
        (
            "KB-OSC-STARTUP",
            ["clock", "crystal", "xtal", "oscillator", "hse", "lse", "boot"],
            "External crystal oscillator startup failure due to mismatched load capacitance.",
            "Check CL1/CL2 load capacitors using CL = (C1 * C2)/(C1 + C2) + Cstray and ensure crystal ESR meets the datasheet oscillator transconductance spec.",
        ),
    ]

    def __init__(self, guardband_ratio: float = 0.05) -> None:
        """
        Args:
            guardband_ratio: Fraction of operating range (default 5%) within which
                a warning is raised before hitting hard min/max operating limits.
        """
        self.guardband_ratio = guardband_ratio

    def diagnose(
        self, spec: HardwareSpec, telemetry: TelemetryReading
    ) -> DiagnosticReport:
        """Run full diagnostic suite comparing telemetry against HardwareSpec."""
        findings: List[DiagnosticFinding] = []
        matched_errata: List[ErrataItem] = []

        # 1. Check measured electrical parameters against Operating and Absolute Maximum specs
        findings.extend(self._check_electrical_parameters(spec, telemetry))

        # 2. Check thermal envelope and estimate junction temperature
        thermal_findings, est_tj = self._check_thermal(spec, telemetry)
        findings.extend(thermal_findings)

        # 3. Check pin states and voltage domain safety
        findings.extend(self._check_pins(spec, telemetry))

        # 4. Match symptoms against datasheet errata and engineering knowledge base
        symptom_findings, errata_hits = self._analyze_symptoms(spec, telemetry)
        findings.extend(symptom_findings)
        matched_errata.extend(errata_hits)

        # Determine overall status
        if any(f.severity == Severity.CRITICAL for f in findings):
            overall = Severity.CRITICAL
        elif any(f.severity == Severity.WARNING for f in findings):
            overall = Severity.WARNING
        elif any(f.severity == Severity.PASS for f in findings):
            overall = Severity.PASS
        else:
            overall = Severity.INFO

        summary = self._build_summary(spec, overall, findings, matched_errata, est_tj)

        return DiagnosticReport(
            part_number=spec.part_number,
            source_file=spec.source_file,
            overall_status=overall,
            summary=summary,
            estimated_junction_temp_c=est_tj,
            findings=findings,
            matched_errata=matched_errata,
        )

    def compare_specs(
        self, spec_a: HardwareSpec, spec_b: HardwareSpec
    ) -> Dict[str, List[Dict[str, Optional[str]]]]:
        """Compare two HardwareSpec objects for drop-in replacement / cross-reference analysis."""
        comparison: List[Dict[str, Optional[str]]] = []

        comparison.append(
            {
                "attribute": "Part Number",
                "spec_a": spec_a.part_number,
                "spec_b": spec_b.part_number,
                "compatibility": "Reference",
            }
        )
        comparison.append(
            {
                "attribute": "Manufacturer",
                "spec_a": spec_a.manufacturer,
                "spec_b": spec_b.manufacturer,
                "compatibility": "Match" if spec_a.manufacturer == spec_b.manufacturer else "Cross-Vendor",
            }
        )

        shared_pkgs = set(spec_a.package_types) & set(spec_b.package_types)
        comparison.append(
            {
                "attribute": "Packages",
                "spec_a": ", ".join(spec_a.package_types) or "N/A",
                "spec_b": ", ".join(spec_b.package_types) or "N/A",
                "compatibility": f"Compatible ({', '.join(sorted(shared_pkgs))})"
                if shared_pkgs
                else "Footprint Mismatch",
            }
        )

        # Compare operating parameters by symbol
        symbols_a = {p.symbol.upper(): p for p in spec_a.electrical_parameters if p.category == "Operating"}
        symbols_b = {p.symbol.upper(): p for p in spec_b.electrical_parameters if p.category == "Operating"}

        for sym in sorted(set(symbols_a.keys()) | set(symbols_b.keys())):
            pa = symbols_a.get(sym)
            pb = symbols_b.get(sym)
            str_a = self._format_range(pa) if pa else "Not specified"
            str_b = self._format_range(pb) if pb else "Not specified"
            compat = "Check manually"
            if pa and pb:
                if pa.min_val == pb.min_val and pa.max_val == pb.max_val:
                    compat = "Exact Match"
                elif (
                    pa.min_val is not None
                    and pb.min_val is not None
                    and pa.max_val is not None
                    and pb.max_val is not None
                ):
                    if pb.min_val <= pa.min_val and pb.max_val >= pa.max_val:
                        compat = "B covers A's range (Drop-in safe)"
                    else:
                        compat = "Range Difference (Verify rails)"
            comparison.append(
                {
                    "attribute": f"Param: {sym}",
                    "spec_a": str_a,
                    "spec_b": str_b,
                    "compatibility": compat,
                }
            )

        return {"rows": comparison}

    def _check_electrical_parameters(
        self, spec: HardwareSpec, telemetry: TelemetryReading
    ) -> List[DiagnosticFinding]:
        findings: List[DiagnosticFinding] = []
        if not telemetry.measured_parameters:
            return findings

        # Group datasheet parameters by uppercase symbol
        op_params: Dict[str, ElectricalParameter] = {}
        abs_params: Dict[str, ElectricalParameter] = {}
        for param in spec.electrical_parameters:
            sym = param.symbol.strip().upper()
            if "abs" in param.category.lower():
                abs_params[sym] = param
            else:
                op_params[sym] = param

        for raw_sym, measured_val in telemetry.measured_parameters.items():
            sym = raw_sym.strip().upper()
            op_p = op_params.get(sym)
            abs_p = abs_params.get(sym)

            if op_p is None and abs_p is None:
                findings.append(
                    DiagnosticFinding(
                        rule_id="ELEC-UNKNOWN-PARAM",
                        severity=Severity.INFO,
                        parameter_or_area=raw_sym,
                        observed=f"{measured_val}",
                        expected="Not listed in datasheet table",
                        message=f"Measured parameter '{raw_sym}' has no direct symbol match in extracted tables.",
                        remediation="Verify symbol naming against datasheet electrical table (e.g., VDD, IDD, VIL, VIH, FCLK).",
                    )
                )
                continue

            unit = (op_p.unit if op_p else abs_p.unit if abs_p else "") or ""

            # 1. Check Absolute Maximum Ratings first
            if abs_p:
                if abs_p.max_val is not None and measured_val > abs_p.max_val:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="ELEC-ABS-MAX-EXCEEDED",
                            severity=Severity.CRITICAL,
                            parameter_or_area=f"{sym} ({abs_p.parameter})",
                            observed=f"{measured_val} {unit}".strip(),
                            expected=f"<= {abs_p.max_val} {unit} (Absolute Max)".strip(),
                            message=f"CRITICAL OVERSTRESS: {sym} ({measured_val} {unit}) exceeds Absolute Maximum Rating ({abs_p.max_val} {unit})! Permanent silicon latch-up or oxide breakdown risk.",
                            remediation=f"Immediately reduce {sym} below {op_p.max_val if op_p and op_p.max_val is not None else abs_p.max_val} {unit} and inspect upstream voltage regulator / TVS clamping.",
                        )
                    )
                    continue
                if abs_p.min_val is not None and measured_val < abs_p.min_val:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="ELEC-ABS-MIN-VIOLATION",
                            severity=Severity.CRITICAL,
                            parameter_or_area=f"{sym} ({abs_p.parameter})",
                            observed=f"{measured_val} {unit}".strip(),
                            expected=f">= {abs_p.min_val} {unit} (Absolute Min)".strip(),
                            message=f"CRITICAL UNDER-VOLTAGE/REVERSE STRESS: {sym} ({measured_val} {unit}) is below Absolute Minimum Rating ({abs_p.min_val} {unit}).",
                            remediation="Inspect polarity protection and ground bounce; add Schottky clamp if negative undershoot occurs.",
                        )
                    )
                    continue

            # 2. Check Recommended Operating Conditions
            if op_p:
                expected_str = self._format_range(op_p)
                if op_p.max_val is not None and measured_val > op_p.max_val:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="ELEC-OP-MAX-EXCEEDED",
                            severity=Severity.CRITICAL,
                            parameter_or_area=f"{sym} ({op_p.parameter})",
                            observed=f"{measured_val} {unit}".strip(),
                            expected=expected_str,
                            message=f"{sym} ({measured_val} {unit}) exceeds maximum recommended operating limit ({op_p.max_val} {unit}).",
                            remediation=f"Bring {sym} within [{op_p.min_val if op_p.min_val is not None else '-'}, {op_p.max_val}] {unit} to guarantee reliable operation.",
                        )
                    )
                    continue

                if op_p.min_val is not None and measured_val < op_p.min_val:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="ELEC-OP-MIN-BELOW",
                            severity=Severity.CRITICAL,
                            parameter_or_area=f"{sym} ({op_p.parameter})",
                            observed=f"{measured_val} {unit}".strip(),
                            expected=expected_str,
                            message=f"{sym} ({measured_val} {unit}) is below minimum recommended operating limit ({op_p.min_val} {unit}).",
                            remediation=f"Check power rail load regulation, IR drop across PCB traces, or brownout threshold for {sym}.",
                        )
                    )
                    continue

                # Check guardband proximity (within 5% of operating span)
                if op_p.min_val is not None and op_p.max_val is not None and op_p.max_val > op_p.min_val:
                    span = op_p.max_val - op_p.min_val
                    margin = span * self.guardband_ratio
                    if measured_val > (op_p.max_val - margin) or measured_val < (op_p.min_val + margin):
                        findings.append(
                            DiagnosticFinding(
                                rule_id="ELEC-GUARDBAND-TIGHT",
                                severity=Severity.WARNING,
                                parameter_or_area=f"{sym} ({op_p.parameter})",
                                observed=f"{measured_val} {unit}".strip(),
                                expected=expected_str,
                                message=f"{sym} ({measured_val} {unit}) is within {int(self.guardband_ratio * 100)}% guardband of operating limit ({expected_str}).",
                                remediation=f"Target nominal typical value ({op_p.typ_val} {unit}) to account for thermal drift and component tolerances.",
                            )
                        )
                        continue

                findings.append(
                    DiagnosticFinding(
                        rule_id="ELEC-NOMINAL",
                        severity=Severity.PASS,
                        parameter_or_area=f"{sym} ({op_p.parameter})",
                        observed=f"{measured_val} {unit}".strip(),
                        expected=expected_str,
                        message=f"{sym} is within recommended datasheet operating specifications.",
                        remediation="None required.",
                    )
                )

        return findings

    def _check_thermal(
        self, spec: HardwareSpec, telemetry: TelemetryReading
    ) -> Tuple[List[DiagnosticFinding], Optional[float]]:
        findings: List[DiagnosticFinding] = []
        est_tj: Optional[float] = None
        th = spec.thermal

        if telemetry.ambient_temp_c is not None:
            ta = telemetry.ambient_temp_c
            if th.operating_temp_min_c is not None and th.operating_temp_max_c is not None:
                expected_ta = f"{th.operating_temp_min_c} °C to {th.operating_temp_max_c} °C"
                if ta > th.operating_temp_max_c or ta < th.operating_temp_min_c:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-AMBIENT-OUT-OF-RANGE",
                            severity=Severity.CRITICAL,
                            parameter_or_area="Ambient Temperature (TA)",
                            observed=f"{ta:.1f} °C",
                            expected=expected_ta,
                            message=f"Ambient temperature ({ta:.1f} °C) violates rated operating range ({expected_ta}).",
                            remediation="Improve enclosure airflow, add heatsinking, or select an extended/automotive temperature grade part.",
                        )
                    )
                elif ta > (th.operating_temp_max_c - 10.0):
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-AMBIENT-HIGH",
                            severity=Severity.WARNING,
                            parameter_or_area="Ambient Temperature (TA)",
                            observed=f"{ta:.1f} °C",
                            expected=expected_ta,
                            message=f"Ambient temperature ({ta:.1f} °C) is within 10 °C of maximum ambient limit.",
                            remediation="Verify derating curve and junction temperature rise under peak load.",
                        )
                    )
                else:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-AMBIENT-OK",
                            severity=Severity.PASS,
                            parameter_or_area="Ambient Temperature (TA)",
                            observed=f"{ta:.1f} °C",
                            expected=expected_ta,
                            message="Ambient temperature is comfortably within datasheet operating limits.",
                            remediation="None required.",
                        )
                    )

            # Calculate estimated Junction Temperature Tj = Ta + Pd * Theta_JA
            if telemetry.power_dissipation_w is not None and th.theta_ja_c_per_w is not None:
                est_tj = round(ta + telemetry.power_dissipation_w * th.theta_ja_c_per_w, 2)
                tj_max = th.max_junction_temp_c or 125.0
                if est_tj > tj_max:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-TJ-EXCEEDED",
                            severity=Severity.CRITICAL,
                            parameter_or_area="Estimated Junction Temp (TJ)",
                            observed=f"{est_tj:.1f} °C (Pd={telemetry.power_dissipation_w}W, θJA={th.theta_ja_c_per_w}°C/W)",
                            expected=f"<= {tj_max:.1f} °C",
                            message=f"Calculated junction temperature ({est_tj:.1f} °C) exceeds maximum silicon rating ({tj_max:.1f} °C).",
                            remediation="Reduce power dissipation, lower switching frequency, or expand PCB copper thermal pad & thermal vias to lower effective θJA.",
                        )
                    )
                elif est_tj > (tj_max - 15.0):
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-TJ-ELEVATED",
                            severity=Severity.WARNING,
                            parameter_or_area="Estimated Junction Temp (TJ)",
                            observed=f"{est_tj:.1f} °C",
                            expected=f"<= {tj_max:.1f} °C (< {tj_max - 15.0:.1f} °C recommended)",
                            message=f"Estimated junction temperature ({est_tj:.1f} °C) has less than 15 °C thermal margin.",
                            remediation="Consider increasing PCB ground plane copper weight (2 oz) or airflow.",
                        )
                    )
                else:
                    findings.append(
                        DiagnosticFinding(
                            rule_id="THERM-TJ-PASS",
                            severity=Severity.PASS,
                            parameter_or_area="Estimated Junction Temp (TJ)",
                            observed=f"{est_tj:.1f} °C",
                            expected=f"<= {tj_max:.1f} °C",
                            message=f"Estimated junction temperature ({est_tj:.1f} °C) is well within safe thermal margin.",
                            remediation="None required.",
                        )
                    )

        return findings, est_tj

    def _check_pins(
        self, spec: HardwareSpec, telemetry: TelemetryReading
    ) -> List[DiagnosticFinding]:
        findings: List[DiagnosticFinding] = []
        if not telemetry.pin_states or not spec.pinout:
            return findings

        pin_lookup = {}
        for p in spec.pinout:
            pin_lookup[p.pin_number.upper()] = p
            pin_lookup[p.name.upper()] = p

        for pin_key, state_desc in telemetry.pin_states.items():
            pin = pin_lookup.get(pin_key.strip().upper())
            state_lower = state_desc.lower()
            if not pin:
                continue

            # Check for floating input/reset pins
            if "float" in state_lower or "unconnected" in state_lower or "nc" in state_lower:
                if "in" in pin.pin_type.lower() or "rst" in pin.name.lower() or "reset" in pin.name.lower():
                    findings.append(
                        DiagnosticFinding(
                            rule_id="PIN-FLOATING-INPUT",
                            severity=Severity.WARNING,
                            parameter_or_area=f"Pin {pin.pin_number} ({pin.name})",
                            observed=state_desc,
                            expected="Driven High/Low or Pulled Up/Down",
                            message=f"Input/Control pin {pin.name} (Pin {pin.pin_number}) is left floating, risking CMOS shoot-through current or spurious resets.",
                            remediation=f"Enable internal pull-up/pull-down resistor or tie {pin.name} to a defined logic rail via a 10 kΩ resistor.",
                        )
                    )

            # Check for 5V applied to 3.3V-only / non-5V-tolerant domain
            volt_match = re.search(r"(\d+(?:\.\d+)?)\s*v", state_lower)
            if volt_match and pin.voltage_domain:
                applied_v = float(volt_match.group(1))
                if applied_v >= 4.5 and "3.3v" in pin.voltage_domain.lower() and "5v" not in pin.voltage_domain.lower() and "ft" not in pin.voltage_domain.lower():
                    findings.append(
                        DiagnosticFinding(
                            rule_id="PIN-DOMAIN-OVERVOLTAGE",
                            severity=Severity.CRITICAL,
                            parameter_or_area=f"Pin {pin.pin_number} ({pin.name})",
                            observed=state_desc,
                            expected=f"Domain: {pin.voltage_domain}",
                            message=f"Applying {applied_v}V to non-5V-tolerant pin {pin.name} (rated domain: {pin.voltage_domain}) risks ESD diode forward conduction and rail back-powering.",
                            remediation=f"Use a level shifter or series current-limiting resistor for {pin.name}, or reassign signal to a 5V-tolerant (FT) pin.",
                        )
                    )

        return findings

    def _analyze_symptoms(
        self, spec: HardwareSpec, telemetry: TelemetryReading
    ) -> Tuple[List[DiagnosticFinding], List[ErrataItem]]:
        findings: List[DiagnosticFinding] = []
        matched_errata: List[ErrataItem] = []

        if not telemetry.symptoms:
            return findings, matched_errata

        combined_symptoms = " ".join(telemetry.symptoms).lower()
        symptom_tokens = set(re.findall(r"[a-z0-9_]+", combined_symptoms))

        # 1. Check against extracted datasheet silicon errata
        for err in spec.errata:
            err_text = f"{err.title} {err.symptom}".lower()
            err_tokens = set(re.findall(r"[a-z0-9_]+", err_text)) - {
                "the",
                "and",
                "when",
                "with",
                "from",
                "into",
                "mode",
                "high",
                "low",
            }
            overlap = symptom_tokens & err_tokens
            if len(overlap) >= 2 or any(
                kw in combined_symptoms for kw in [err.code.lower(), err.title.lower()]
            ):
                matched_errata.append(err)
                findings.append(
                    DiagnosticFinding(
                        rule_id=f"ERRATA-{err.code}",
                        severity=Severity.WARNING,
                        parameter_or_area=f"Silicon Errata {err.code}: {err.title}",
                        observed="; ".join(telemetry.symptoms),
                        expected="Datasheet Errata Advisory",
                        message=f"Reported symptom matches known silicon errata [{err.code}] ({err.symptom}).",
                        remediation=f"Datasheet Workaround: {err.workaround}",
                    )
                )

        # 2. Check against built-in hardware engineering knowledge base
        for kb_id, keywords, diagnosis, remediation in self.COMMON_FAULT_KB:
            if any(kw in combined_symptoms for kw in keywords):
                findings.append(
                    DiagnosticFinding(
                        rule_id=kb_id,
                        severity=Severity.WARNING,
                        parameter_or_area="Symptom Root-Cause Analysis",
                        observed="; ".join(telemetry.symptoms),
                        expected="Normal Subsystem Operation",
                        message=diagnosis,
                        remediation=remediation,
                    )
                )

        return findings, matched_errata

    @staticmethod
    def _format_range(param: ElectricalParameter) -> str:
        parts = []
        if param.min_val is not None:
            parts.append(f"Min: {param.min_val}")
        if param.typ_val is not None:
            parts.append(f"Typ: {param.typ_val}")
        if param.max_val is not None:
            parts.append(f"Max: {param.max_val}")
        joined = ", ".join(parts) if parts else "N/A"
        return f"{joined} {param.unit}".strip()

    @staticmethod
    def _build_summary(
        spec: HardwareSpec,
        overall: Severity,
        findings: List[DiagnosticFinding],
        matched_errata: List[ErrataItem],
        est_tj: Optional[float],
    ) -> str:
        crit = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        warn = sum(1 for f in findings if f.severity == Severity.WARNING)
        passed = sum(1 for f in findings if f.severity == Severity.PASS)
        tj_str = f" | Estimated TJ: {est_tj:.1f} °C" if est_tj is not None else ""
        return (
            f"[{overall.value}] {spec.part_number}: {crit} critical, {warn} warning(s), "
            f"{passed} nominal check(s), {len(matched_errata)} matched silicon errata{tj_str}."
        )
