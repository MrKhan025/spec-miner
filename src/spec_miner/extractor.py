"""
PDF Hardware Specification Extractor (`extractor.py`).

Extracts structured hardware specifications, electrical characteristics tables,
pinouts, thermal ratings, communication interfaces, and silicon errata from PDF
datasheets using `pdfplumber` and `pypdf`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
from pypdf import PdfReader

from .models import (
    ElectricalParameter,
    ErrataItem,
    HardwareSpec,
    PinDefinition,
    SupportedInterface,
    ThermalCharacteristics,
)


class DatasheetExtractor:
    """Extracts structured hardware specifications from PDF datasheets."""

    KNOWN_MANUFACTURERS = [
        "Texas Instruments",
        "STMicroelectronics",
        "Microchip",
        "NXP",
        "Analog Devices",
        "Infineon",
        "Espressif",
        "Nordic Semiconductor",
        "Raspberry Pi",
        "Renesas",
        "Maxim Integrated",
        "ON Semiconductor",
        "Vishay",
        "Broadcom",
        "Lattice",
        "Xilinx",
        "Altera",
        "Silicon Labs",
    ]

    PACKAGE_PATTERNS = [
        r"\b(?:LQFP|TQFP|QFN|VQFN|WQFN|BGA|TFBGA|WLCSP|SOIC|TSSOP|SOT-23|DIP|PDIP|TO-220|QFP)(?:-\d+)?\b"
    ]

    INTERFACE_PATTERNS = [
        ("I2C", r"(?:(\d+)\s*[x×]?\s*)?\b(?:I2C|I²C|TWI)\b(?:\s*\(([^)]+)\))?"),
        ("SPI", r"(?:(\d+)\s*[x×]?\s*)?\bSPI\b(?:\s*\(([^)]+)\))?"),
        ("UART", r"(?:(\d+)\s*[x×]?\s*)?\b(?:UART|USART)\b(?:\s*\(([^)]+)\))?"),
        ("CAN", r"(?:(\d+)\s*[x×]?\s*)?\b(?:CAN(?:-FD)?)\b(?:\s*\(([^)]+)\))?"),
        ("USB", r"(?:(\d+)\s*[x×]?\s*)?\bUSB(?:\s*2\.0|\s*OTG|\s*FS|\s*HS)?\b"),
        ("ADC", r"(?:(\d+)\s*[x×]?\s*)?\b(\d+-bit\s+ADC|ADC)\b"),
        ("PWM", r"(?:(\d+)\s*[x×]?\s*)?\bPWM\b"),
    ]

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    def extract(self, pdf_path: str | Path) -> HardwareSpec:
        """Parse a PDF datasheet and return a populated HardwareSpec model."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"Datasheet PDF not found: {path}")

        pages_text: List[str] = []
        extracted_tables: List[List[List[Optional[str]]]] = []
        raw_meta: Dict[str, Any] = {}

        # Read metadata with pypdf
        try:
            reader = PdfReader(str(path))
            if reader.metadata:
                for k, v in reader.metadata.items():
                    if v is not None:
                        raw_meta[str(k).lstrip("/")] = str(v)
        except Exception as exc:
            if self.strict:
                raise RuntimeError(f"Failed to read PDF metadata: {exc}") from exc

        # Extract text and tables via pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                tables = page.extract_tables() or []
                extracted_tables.extend(tables)

        full_text = "\n".join(pages_text)
        return self.extract_from_text_and_tables(
            full_text=full_text,
            tables=extracted_tables,
            source_file=os.path.basename(str(path)),
            page_count=page_count,
            raw_metadata=raw_meta,
        )

    def extract_from_text_and_tables(
        self,
        full_text: str,
        tables: Optional[List[List[List[Optional[str]]]]] = None,
        source_file: str = "inline.pdf",
        page_count: int = 1,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> HardwareSpec:
        """Extract HardwareSpec from extracted text and table structures."""
        tables = tables or []
        raw_metadata = raw_metadata or {}

        part_number = self._extract_part_number(full_text, source_file)
        manufacturer = self._extract_manufacturer(full_text, raw_metadata)
        category = self._extract_category(full_text)
        description = self._extract_description(full_text)
        packages = self._extract_packages(full_text)
        features = self._extract_features(full_text)
        electrical_params = self._extract_electrical_parameters(full_text, tables)
        pinout = self._extract_pinout(full_text, tables)
        interfaces = self._extract_interfaces(full_text)
        thermal = self._extract_thermal(full_text, tables)
        errata = self._extract_errata(full_text, tables)

        return HardwareSpec(
            part_number=part_number,
            manufacturer=manufacturer,
            category=category,
            description=description,
            package_types=packages,
            source_file=source_file,
            page_count=page_count,
            features=features,
            electrical_parameters=electrical_params,
            pinout=pinout,
            interfaces=interfaces,
            thermal=thermal,
            errata=errata,
            raw_metadata=raw_metadata,
        )

    def _extract_part_number(self, text: str, fallback_filename: str) -> str:
        # Look for explicit part number headers
        explicit = re.search(
            r"(?:Part\s*Number|Device|Model)\s*[:\-]\s*([A-Z0-9][A-Z0-9\-_]{3,24})",
            text,
            re.IGNORECASE,
        )
        if explicit:
            return explicit.group(1).strip()

        # Look for standard semiconductor part number patterns near top of document
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:12]:
            match = re.search(
                r"\b([A-Z]{2,6}\d{2,5}[A-Z0-9\-]{1,10})\b",
                line,
            )
            if match and match.group(1).upper() not in {
                "LQFP48",
                "LQFP64",
                "QFN32",
                "VQFN48",
                "TSSOP20",
                "SOIC8",
                "SOT23",
                "USB20",
                "IEEE802",
            }:
                return match.group(1)

        stem = Path(fallback_filename).stem.upper()
        return stem if stem else "UNKNOWN-IC"

    def _extract_manufacturer(self, text: str, metadata: Dict[str, Any]) -> str:
        explicit = re.search(
            r"Manufacturer\s*[:\-]\s*([^\n\r|]+)", text, re.IGNORECASE
        )
        if explicit:
            return explicit.group(1).strip()

        for mfg in self.KNOWN_MANUFACTURERS:
            if re.search(rf"\b{re.escape(mfg)}\b", text, re.IGNORECASE):
                return mfg

        if "Author" in metadata and metadata["Author"].strip():
            return metadata["Author"].strip()

        return "Generic Semiconductor"

    def _extract_category(self, text: str) -> str:
        lower = text.lower()
        if "microcontroller" in lower or "mcu" in lower or "cortex-m" in lower:
            return "Microcontroller (MCU)"
        if "step-down" in lower or "buck converter" in lower or "ldo" in lower or "voltage regulator" in lower:
            return "Power Management IC (PMIC / Regulator)"
        if "transceiver" in lower:
            return "Communication Transceiver"
        if "operational amplifier" in lower or "op-amp" in lower:
            return "Operational Amplifier"
        if "sensor" in lower:
            return "Sensor IC"
        return "Integrated Circuit"

    def _extract_description(self, text: str) -> str:
        desc_match = re.search(
            r"(?:DESCRIPTION|OVERVIEW|GENERAL DESCRIPTION)\s*\n+([^\n]+(?:\n[^\n]+){0,2})",
            text,
            re.IGNORECASE,
        )
        if desc_match:
            cleaned = " ".join(desc_match.group(1).split())
            return cleaned[:280]

        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 25]
        return lines[0][:280] if lines else "Hardware component specification."

    def _extract_packages(self, text: str) -> List[str]:
        found: List[str] = []
        for pattern in self.PACKAGE_PATTERNS:
            for match in re.findall(pattern, text):
                pkg = match.upper()
                if pkg not in found:
                    found.append(pkg)
        return found

    def _extract_features(self, text: str) -> List[str]:
        features: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("•", "-", "*", "■")) and 8 <= len(stripped) <= 140:
                item = stripped.lstrip("•-* ").strip()
                if item and item not in features:
                    features.append(item)
            if len(features) >= 10:
                break
        return features

    def _extract_electrical_parameters(
        self, text: str, tables: List[List[List[Optional[str]]]]
    ) -> List[ElectricalParameter]:
        params: List[ElectricalParameter] = []
        seen_symbols: set[Tuple[str, str]] = set()

        # 1. Extract from tables
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = [self._clean_cell(c).lower() for c in table[0]]
            if not any(k in " ".join(header) for k in ("symbol", "parameter", "min", "max", "unit")):
                continue

            idx_map = self._map_electrical_columns(header)
            if idx_map.get("symbol") is None and idx_map.get("parameter") is None:
                continue

            for row in table[1:]:
                if not row or len(row) < 3:
                    continue
                symbol = self._get_cell(row, idx_map.get("symbol"))
                parameter = self._get_cell(row, idx_map.get("parameter"))
                if not symbol and not parameter:
                    continue
                if symbol.lower() in ("symbol", "param"):
                    continue

                min_val = self._parse_float(self._get_cell(row, idx_map.get("min")))
                typ_val = self._parse_float(self._get_cell(row, idx_map.get("typ")))
                max_val = self._parse_float(self._get_cell(row, idx_map.get("max")))
                unit = self._get_cell(row, idx_map.get("unit"))
                conditions = self._get_cell(row, idx_map.get("conditions"))
                category = self._get_cell(row, idx_map.get("category")) or (
                    "Absolute Maximum"
                    if "abs" in parameter.lower() or "max rating" in conditions.lower()
                    else "Operating"
                )

                if min_val is None and typ_val is None and max_val is None:
                    continue

                key = (symbol.upper(), category)
                if key not in seen_symbols:
                    seen_symbols.add(key)
                    params.append(
                        ElectricalParameter(
                            symbol=symbol or parameter[:12],
                            parameter=parameter or symbol,
                            min_val=min_val,
                            typ_val=typ_val,
                            max_val=max_val,
                            unit=unit,
                            conditions=conditions,
                            category=category,
                        )
                    )

        # 2. Fallback / supplement from structured text lines
        # Matches lines like: VDD | Supply Voltage | 1.8 | 3.3 | 3.6 | V | Operating
        line_regex = re.compile(
            r"^\s*([A-Za-z][A-Za-z0-9_]{1,14})\s*[|\t]\s*([^|\t]+?)\s*[|\t]\s*"
            r"([\-+]?\d+(?:\.\d+)?|[-—])\s*[|\t]\s*([\-+]?\d+(?:\.\d+)?|[-—])\s*[|\t]\s*"
            r"([\-+]?\d+(?:\.\d+)?|[-—])\s*[|\t]\s*([A-Za-z%°ΩΩµμ/]+)"
            r"(?:\s*[|\t]\s*([^\n|]+))?",
            re.MULTILINE,
        )
        for match in line_regex.finditer(text):
            symbol, param_name, min_s, typ_s, max_s, unit, cond = match.groups()
            cond_str = (cond or "").strip()
            cat = "Absolute Maximum" if "absolute" in cond_str.lower() else "Operating"
            key = (symbol.strip().upper(), cat)
            if key not in seen_symbols:
                seen_symbols.add(key)
                params.append(
                    ElectricalParameter(
                        symbol=symbol.strip(),
                        parameter=param_name.strip(),
                        min_val=self._parse_float(min_s),
                        typ_val=self._parse_float(typ_s),
                        max_val=self._parse_float(max_s),
                        unit=unit.strip(),
                        conditions=cond_str,
                        category=cat,
                    )
                )

        return params

    def _map_electrical_columns(self, header: List[str]) -> Dict[str, Optional[int]]:
        mapping: Dict[str, Optional[int]] = {
            "symbol": None,
            "parameter": None,
            "min": None,
            "typ": None,
            "max": None,
            "unit": None,
            "conditions": None,
            "category": None,
        }
        for i, col in enumerate(header):
            if "sym" in col and mapping["symbol"] is None:
                mapping["symbol"] = i
            elif ("param" in col or "description" in col or "rating" in col) and mapping["parameter"] is None:
                mapping["parameter"] = i
            elif "min" in col and mapping["min"] is None:
                mapping["min"] = i
            elif ("typ" in col or "nom" in col) and mapping["typ"] is None:
                mapping["typ"] = i
            elif "max" in col and mapping["max"] is None:
                mapping["max"] = i
            elif "unit" in col and mapping["unit"] is None:
                mapping["unit"] = i
            elif ("cond" in col or "note" in col) and mapping["conditions"] is None:
                mapping["conditions"] = i
            elif ("cat" in col or "type" in col) and mapping["category"] is None:
                mapping["category"] = i
        return mapping

    def _extract_pinout(
        self, text: str, tables: List[List[List[Optional[str]]]]
    ) -> List[PinDefinition]:
        pins: List[PinDefinition] = []
        seen_pins: set[str] = set()

        for table in tables:
            if not table or len(table) < 2:
                continue
            header = [self._clean_cell(c).lower() for c in table[0]]
            if not ("pin" in " ".join(header) and ("name" in " ".join(header) or "signal" in " ".join(header))):
                continue

            pin_idx = next((i for i, c in enumerate(header) if "pin" in c or "no" in c), 0)
            name_idx = next((i for i, c in enumerate(header) if "name" in c or "sig" in c), 1)
            type_idx = next((i for i, c in enumerate(header) if "type" in c or "dir" in c or "i/o" in c), 2)
            domain_idx = next((i for i, c in enumerate(header) if "domain" in c or "volt" in c or "supply" in c), None)
            desc_idx = next((i for i, c in enumerate(header) if "desc" in c or "func" in c), len(header) - 1)

            for row in table[1:]:
                if not row or len(row) < 3:
                    continue
                pin_num = self._get_cell(row, pin_idx)
                pin_name = self._get_cell(row, name_idx)
                if not pin_num or not pin_name or pin_num.lower() in ("pin", "no", "#"):
                    continue
                if pin_num in seen_pins:
                    continue
                seen_pins.add(pin_num)

                pin_type = self._get_cell(row, type_idx) or "I/O"
                domain = self._get_cell(row, domain_idx) if domain_idx is not None else ""
                desc = self._get_cell(row, desc_idx)
                alt_funcs = [
                    fn.strip()
                    for fn in re.findall(r"\b(?:SPI\d*_[A-Z]+|I2C\d*_[A-Z]+|UART\d*_[A-Z]+|ADC\d*_IN\d+|TIM\d+_CH\d+|PWM\d*)\b", desc)
                ]
                pins.append(
                    PinDefinition(
                        pin_number=pin_num,
                        name=pin_name,
                        pin_type=pin_type,
                        description=desc,
                        alternate_functions=alt_funcs,
                        voltage_domain=domain,
                    )
                )

        return pins

    def _extract_interfaces(self, text: str) -> List[SupportedInterface]:
        interfaces: List[SupportedInterface] = []
        seen: set[str] = set()
        for proto, pattern in self.INTERFACE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if proto in seen:
                    continue
                seen.add(proto)
                groups = match.groups()
                count = int(groups[0]) if groups and groups[0] and groups[0].isdigit() else 1
                detail = groups[1] if len(groups) > 1 and groups[1] else ""
                speed_match = re.search(
                    rf"\b{proto}\b[^\n.]*?(\d+(?:\.\d+)?\s*(?:MHz|kHz|Mbps|kbps|MSPS|ksps))",
                    text,
                    re.IGNORECASE,
                )
                speed = speed_match.group(1) if speed_match else ""
                interfaces.append(
                    SupportedInterface(
                        protocol=proto,
                        count=count,
                        max_speed=speed,
                        details=detail,
                    )
                )
        return interfaces

    def _extract_thermal(
        self, text: str, tables: List[List[List[Optional[str]]]]
    ) -> ThermalCharacteristics:
        thermal = ThermalCharacteristics()

        op_temp = re.search(
            r"Operating\s+Temperature(?:\s+Range)?\s*[:\-]?\s*([\-+]?\d+(?:\.\d+)?)\s*°?C?\s*(?:to|–|-|\.\.)\s*\+?([\-+]?\d+(?:\.\d+)?)\s*°?C",
            text,
            re.IGNORECASE,
        )
        if op_temp:
            thermal.operating_temp_min_c = float(op_temp.group(1))
            thermal.operating_temp_max_c = float(op_temp.group(2))

        st_temp = re.search(
            r"Storage\s+Temperature(?:\s+Range)?\s*[:\-]?\s*([\-+]?\d+(?:\.\d+)?)\s*°?C?\s*(?:to|–|-|\.\.)\s*\+?([\-+]?\d+(?:\.\d+)?)\s*°?C",
            text,
            re.IGNORECASE,
        )
        if st_temp:
            thermal.storage_temp_min_c = float(st_temp.group(1))
            thermal.storage_temp_max_c = float(st_temp.group(2))

        tj_match = re.search(
            r"(?:Maximum\s+Junction\s+Temperature|Tj\(max\)|TJ_MAX)\s*[:\-]?\s*\+?(\d+(?:\.\d+)?)\s*°?C",
            text,
            re.IGNORECASE,
        )
        if tj_match:
            thermal.max_junction_temp_c = float(tj_match.group(1))

        tja_match = re.search(
            r"(?:Theta_JA|θJA|RθJA|Junction-to-Ambient)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*°?C/W",
            text,
            re.IGNORECASE,
        )
        if tja_match:
            thermal.theta_ja_c_per_w = float(tja_match.group(1))

        tjc_match = re.search(
            r"(?:Theta_JC|θJC|RθJC|Junction-to-Case)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*°?C/W",
            text,
            re.IGNORECASE,
        )
        if tjc_match:
            thermal.theta_jc_c_per_w = float(tjc_match.group(1))

        # Check tables for thermal parameters as well
        for table in tables:
            for row in table or []:
                row_text = " ".join(self._clean_cell(c) for c in row if c)
                if not row_text:
                    continue
                if thermal.theta_ja_c_per_w is None and re.search(r"θJA|Theta_JA|Junction-to-Ambient", row_text, re.I):
                    nums = re.findall(r"\b\d+(?:\.\d+)?\b", row_text)
                    if nums:
                        thermal.theta_ja_c_per_w = float(nums[0])
                if thermal.theta_jc_c_per_w is None and re.search(r"θJC|Theta_JC|Junction-to-Case", row_text, re.I):
                    nums = re.findall(r"\b\d+(?:\.\d+)?\b", row_text)
                    if nums:
                        thermal.theta_jc_c_per_w = float(nums[0])
                if thermal.max_junction_temp_c is None and re.search(r"Junction\s+Temperature|TJ_MAX", row_text, re.I):
                    nums = re.findall(r"\b\d+(?:\.\d+)?\b", row_text)
                    if nums:
                        thermal.max_junction_temp_c = float(nums[-1])

        return thermal

    def _extract_errata(
        self, text: str, tables: List[List[List[Optional[str]]]]
    ) -> List[ErrataItem]:
        errata_list: List[ErrataItem] = []
        seen_codes: set[str] = set()

        for table in tables:
            if not table or len(table) < 2:
                continue
            header = " ".join(self._clean_cell(c).lower() for c in table[0])
            if "errata" not in header and "workaround" not in header:
                continue
            for row in table[1:]:
                if not row or len(row) < 4:
                    continue
                code = self._clean_cell(row[0])
                title = self._clean_cell(row[1])
                symptom = self._clean_cell(row[2])
                workaround = self._clean_cell(row[3])
                if code and code not in seen_codes and code.lower() != "code":
                    seen_codes.add(code)
                    errata_list.append(
                        ErrataItem(
                            code=code,
                            title=title,
                            symptom=symptom,
                            workaround=workaround,
                        )
                    )

        # Regex fallback for inline errata blocks: [ERR-01] Title: Symptom | Workaround: ...
        pattern = re.compile(
            r"\[(ERR-\d+)\]\s*([^:\n]+):\s*([^|\n]+)\|\s*Workaround:\s*([^\n]+)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            code, title, symptom, workaround = match.groups()
            if code not in seen_codes:
                seen_codes.add(code)
                errata_list.append(
                    ErrataItem(
                        code=code.strip(),
                        title=title.strip(),
                        symptom=symptom.strip(),
                        workaround=workaround.strip(),
                    )
                )

        return errata_list

    @staticmethod
    def _clean_cell(cell: Optional[str]) -> str:
        if cell is None:
            return ""
        return " ".join(str(cell).split()).strip()

    def _get_cell(self, row: List[Optional[str]], idx: Optional[int]) -> str:
        if idx is None or idx < 0 or idx >= len(row):
            return ""
        return self._clean_cell(row[idx])

    @staticmethod
    def _parse_float(value: str) -> Optional[float]:
        if not value:
            return None
        cleaned = value.replace("−", "-").replace("–", "-").strip()
        if cleaned in ("-", "—", "N/A", "NA", ""):
            return None
        match = re.search(r"[\-+]?\d+(?:\.\d+)?", cleaned)
        return float(match.group(0)) if match else None
