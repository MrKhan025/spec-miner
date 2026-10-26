"""
Sample Hardware Datasheet PDF & Telemetry Generator (`sample_generator.py`).

Generates realistic multi-section hardware datasheet PDFs (using ReportLab) and
sample telemetry JSON files for demos, CLI quickstarts, and automated testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_sample_datasheet_pdf(output_path: str | Path) -> Path:
    """Create a realistic 2-page MCU datasheet PDF (`STM32F405RG`) with tables and errata."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="STM32F405RG Hardware Datasheet",
        author="STMicroelectronics",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#1e3a8a"),
    )
    body_style = styles["BodyText"]

    story = []
    story.append(Paragraph("Part Number: STM32F405RG", title_style))
    story.append(
        Paragraph(
            "Manufacturer: STMicroelectronics | Packages: LQFP-64, VQFN-48, WLCSP-90",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("DESCRIPTION", h2_style))
    story.append(
        Paragraph(
            "The STM32F405RG is a high-performance ARM Cortex-M4 32-bit RISC microcontroller "
            "operating at up to 168 MHz with FPU, 1 MB Flash memory, 192 KB SRAM, and rich "
            "industrial communication peripherals.",
            body_style,
        )
    )

    story.append(Paragraph("KEY FEATURES", h2_style))
    features = [
        "- Core: ARM 32-bit Cortex-M4 CPU with FPU, frequency up to 168 MHz",
        "- Memories: 1024 KB Flash memory and 192 KB SRAM (including 64 KB CCM data RAM)",
        "- Clock, reset and supply management: 1.8 V to 3.6 V application supply and I/Os",
        "- 3x 12-bit ADC (2.4 MSPS) up to 24 channels and 2x 12-bit D/A converters",
        "- 3x I2C (400 kHz Fast-Mode), 3x SPI (42 MHz), 4x UART (10.5 Mbps), 2x CAN (1 Mbps), 1x USB 2.0 OTG FS",
        "- Operating Temperature Range: -40 °C to +85 °C | Storage Temperature Range: -65 °C to +150 °C",
        "- Maximum Junction Temperature: +125 °C | Theta_JA: 45.0 °C/W | Theta_JC: 12.0 °C/W",
    ]
    for feat in features:
        story.append(Paragraph(feat, body_style))

    story.append(Paragraph("ELECTRICAL CHARACTERISTICS", h2_style))
    elec_data = [
        ["Symbol", "Parameter", "Min", "Typ", "Max", "Unit", "Conditions", "Category"],
        ["VDD_MAX", "Maximum Supply Voltage", "-0.3", "-", "4.0", "V", "Absolute maximum rating", "Absolute Maximum"],
        ["VIN_MAX", "Maximum Input Pin Voltage", "-0.3", "-", "4.0", "V", "Non-5V tolerant pins", "Absolute Maximum"],
        ["VDD", "Operating Supply Voltage", "1.8", "3.3", "3.6", "V", "Full speed operation", "Operating"],
        ["VDDA", "Analog Supply Voltage", "1.8", "3.3", "3.6", "V", "ADC active", "Operating"],
        ["VIL", "Input Low Level Voltage", "-0.3", "0.0", "0.8", "V", "VDD = 3.3V", "Operating"],
        ["VIH", "Input High Level Voltage", "2.0", "3.3", "3.6", "V", "Non-FT GPIO, VDD=3.3V", "Operating"],
        ["IDD", "Supply Current Run Mode", "15.0", "87.0", "138.0", "mA", "fHCLK = 168 MHz, peripherals on", "Operating"],
        ["FCLK", "System Clock Frequency", "0.0", "168.0", "168.0", "MHz", "PLL driven from HSE", "Operating"],
        ["VREF", "ADC Reference Voltage", "1.8", "3.3", "3.6", "V", "Low-noise reference required", "Operating"],
    ]
    t_elec = Table(elec_data, repeatRows=1)
    t_elec.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(t_elec)

    story.append(Paragraph("PIN CONFIGURATION", h2_style))
    pin_data = [
        ["Pin", "Name", "Type", "Voltage Domain", "Description"],
        ["1", "VBAT", "Power", "1.65V-3.6V", "Backup battery supply for RTC and backup registers"],
        ["7", "NRST", "Input", "3.3V", "External active-low system reset input with internal pull-up"],
        ["14", "PA0", "I/O", "3.3V only", "General purpose I/O, ADC1_IN0, TIM2_CH1, WKUP"],
        ["29", "PB6", "I/O", "5V tolerant (FT)", "I2C1_SCL, TIM4_CH1, USART1_TX"],
        ["30", "PB7", "I/O", "5V tolerant (FT)", "I2C1_SDA, TIM4_CH2, USART1_RX"],
        ["41", "PA5", "I/O", "3.3V only", "SPI1_SCK, ADC1_IN5, DAC_OUT2"],
        ["64", "VDD", "Power", "3.3V", "Digital power supply rail"],
    ]
    t_pin = Table(pin_data, repeatRows=1)
    t_pin.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ]
        )
    )
    story.append(t_pin)

    story.append(Paragraph("SILICON ERRATA & TROUBLESHOOTING NOTES", h2_style))
    errata_data = [
        ["Code", "Title", "Symptom", "Workaround"],
        [
            "ERR-101",
            "I2C1 Bus Busy Flag Lockup",
            "I2C1 BUSY flag remains stuck high after master reset or SDA glitch",
            "Toggle SCL 9 clock pulses via GPIO open-drain mode and set SWRST bit in I2C_CR1",
        ],
        [
            "ERR-104",
            "ADC1 Switching Noise on PA5",
            "High ADC conversion jitter when SPI1_SCK toggles concurrently on PA5",
            "Disable SPI1 clock during precision 12-bit ADC sampling or add RC anti-aliasing filter",
        ],
    ]
    t_err = Table(errata_data, repeatRows=1)
    t_err.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ]
        )
    )
    story.append(t_err)

    doc.build(story)
    return path


def generate_sample_telemetry_json(output_path: str | Path) -> Path:
    """Generate a sample board telemetry & fault symptom JSON file for troubleshooting demos."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "measured_parameters": {
            "VDD": 3.55,
            "VDDA": 3.3,
            "IDD": 152.0,
            "VREF": 1.65,
            "FCLK": 168.0,
        },
        "ambient_temp_c": 65.0,
        "power_dissipation_w": 1.45,
        "pin_states": {
            "PA0": "5.0V sensor output applied directly",
            "NRST": "floating (unconnected)",
        },
        "symptoms": [
            "I2C1 bus stuck with BUSY flag high after warm reset",
            "ADC reading noisy and inaccurate on channel 0",
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def generate_demo_bundle(directory: str | Path) -> Tuple[Path, Path]:
    """Generate both the sample datasheet PDF and sample telemetry JSON in `directory`."""
    base = Path(directory)
    pdf_path = generate_sample_datasheet_pdf(base / "sample_mcu_datasheet.pdf")
    json_path = generate_sample_telemetry_json(base / "sample_readings.json")
    return pdf_path, json_path
