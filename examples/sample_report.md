# Hardware Specification Report: `STM32F405RG`

- **Manufacturer:** STMicroelectronics
- **Category:** Microcontroller (MCU)
- **Packages:** LQFP-64, VQFN-48, WLCSP-90
- **Source PDF:** `sample_mcu_datasheet.pdf` (2 pages)
- **Description:** The STM32F405RG is a high-performance ARM Cortex-M4 32-bit RISC microcontroller operating at up to 168 MHz with FPU, 1 MB Flash memory, 192 KB SRAM, and rich industrial communication peripherals. KEY FEATURES

## Key Features
- Core: ARM 32-bit Cortex-M4 CPU with FPU, frequency up to 168 MHz
- Memories: 1024 KB Flash memory and 192 KB SRAM (including 64 KB CCM data RAM)
- Clock, reset and supply management: 1.8 V to 3.6 V application supply and I/Os
- 3x 12-bit ADC (2.4 MSPS) up to 24 channels and 2x 12-bit D/A converters
- 3x I2C (400 kHz Fast-Mode), 3x SPI (42 MHz), 4x UART (10.5 Mbps), 2x CAN (1 Mbps), 1x USB 2.0 OTG FS
- Operating Temperature Range: -40 °C to +85 °C | Storage Temperature Range: -65 °C to +150 °C
- Maximum Junction Temperature: +125 °C | Theta_JA: 45.0 °C/W | Theta_JC: 12.0 °C/W

## Electrical Characteristics

| Symbol | Parameter | Category | Min | Typ | Max | Unit | Conditions |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- | :--- |
| `VDD_MAX` | Maximum Supply Voltage | Absolute Maximum | -0.3 | - | 4.0 | V | Absolute maximum rating |
| `VIN_MAX` | Maximum Input Pin Voltage | Absolute Maximum | -0.3 | - | 4.0 | V | Non-5V tolerant pins |
| `VDD` | Operating Supply Voltage | Operating | 1.8 | 3.3 | 3.6 | V | Full speed operation |
| `VDDA` | Analog Supply Voltage | Operating | 1.8 | 3.3 | 3.6 | V | ADC active |
| `VIL` | Input Low Level Voltage | Operating | -0.3 | 0.0 | 0.8 | V | VDD = 3.3V |
| `VIH` | Input High Level Voltage | Operating | 2.0 | 3.3 | 3.6 | V | Non-FT GPIO, VDD=3.3V |
| `IDD` | Supply Current Run Mode | Operating | 15.0 | 87.0 | 138.0 | mA | fHCLK = 168 MHz, peripherals on |
| `FCLK` | System Clock Frequency | Operating | 0.0 | 168.0 | 168.0 | MHz | PLL driven from HSE |
| `VREF` | ADC Reference Voltage | Operating | 1.8 | 3.3 | 3.6 | V | Low-noise reference required |

## Thermal Characteristics

- **Operating Temperature Range:** -40.0 °C to 85.0 °C
- **Maximum Junction Temperature ($T_{J(\max)}$):** 125.0 °C
- **Thermal Resistance ($\theta_{JA}$):** 45.0 °C/W
- **Thermal Resistance ($\theta_{JC}$):** 12.0 °C/W

## Pin Configuration

| Pin # | Name | Type | Voltage Domain | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `VBAT` | Power | 1.65V-3.6V | Backup battery supply for RTC and backup registers |
| 7 | `NRST` | Input | 3.3V | External active-low system reset input with internal pull-up |
| 14 | `PA0` | I/O | 3.3V only | General purpose I/O, ADC1_IN0, TIM2_CH1, WKUP |
| 29 | `PB6` | I/O | 5V tolerant (FT) | I2C1_SCL, TIM4_CH1, USART1_TX |
| 30 | `PB7` | I/O | 5V tolerant (FT) | I2C1_SDA, TIM4_CH2, USART1_RX |
| 41 | `PA5` | I/O | 3.3V only | SPI1_SCK, ADC1_IN5, DAC_OUT2 |
| 64 | `VDD` | Power | 3.3V | Digital power supply rail |

## Known Silicon Errata

| Code | Title | Symptom | Workaround |
| :--- | :--- | :--- | :--- |
| `ERR-101` | I2C1 Bus Busy Flag Lockup | I2C1 BUSY flag remains stuck high after master reset or SDA glitch | Toggle SCL 9 clock pulses via GPIO open-drain mode and set SWRST bit in I2C_CR1 |
| `ERR-104` | ADC1 Switching Noise on PA5 | High ADC conversion jitter when SPI1_SCK toggles concurrently on PA5 | Disable SPI1 clock during precision 12-bit ADC sampling or add RC anti-aliasing filter |
