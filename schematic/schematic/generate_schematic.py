#!/usr/bin/env python3
"""Generate the self-contained KiCad 10 schematic for the SSEMAS carrier.

The generated schematic embeds the small project symbol set, so it remains
portable and does not depend on a user-specific symbol library installation.
"""

from pathlib import Path
import re
import uuid


ROOT = Path(__file__).resolve().parent
PROJECT = "schematic"
SHEET_UUID = "6fdde713-3dc6-4f42-b4b8-8c7ec9905e31"
UUID_NAMESPACE = uuid.UUID("52b52b17-4be7-4cb5-8128-8bbfd22ad26e")


def uid(name: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, name))


def extract_symbols(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    symbols: dict[str, str] = {}
    depth = 0
    start = None
    for i, char in enumerate(text):
        if char == "(":
            depth += 1
            if depth == 2 and text.startswith("(symbol ", i):
                start = i
        elif char == ")":
            if depth == 2 and start is not None:
                block = text[start : i + 1]
                match = re.match(r'\(symbol "([^"]+)"', block)
                if match:
                    symbols[match.group(1)] = block
                start = None
            depth -= 1
    return symbols


def indent(block: str, tabs: int) -> str:
    prefix = "\t" * tabs
    return "\n".join(prefix + line if line else line for line in block.splitlines())


def embedded_library(symbols: dict[str, str], names: set[str]) -> str:
    output = ["\t(lib_symbols"]
    for name in sorted(names):
        block = symbols[name]
        block = block.replace(f'(symbol "{name}"', f'(symbol "ssemas:{name}"', 1)
        output.append(indent(block, 2))
    output.append("\t)")
    return "\n".join(output)


def effects(hidden: bool = False, justify: str | None = None) -> str:
    parts = ["(effects", "\t(font", "\t\t(size 1.27 1.27)", "\t)"]
    if justify:
        parts.append(f"\t(justify {justify})")
    parts.append(")")
    return "\n".join(parts)


def component(
    ref: str,
    symbol: str,
    value: str,
    footprint: str,
    x: float,
    y: float,
    pins: list[str],
    description: str,
) -> str:
    comp_uuid = uid(f"component:{ref}")
    pin_blocks = "\n".join(
        f'\t\t(pin "{pin}"\n\t\t\t(uuid "{uid(f"pin:{ref}:{pin}")}")\n\t\t)'
        for pin in pins
    )
    props = [
        ("Reference", ref, x + 2.54, y - 2.54, False),
        ("Value", value, x + 2.54, y, False),
        ("Footprint", footprint, x, y, True),
        ("Datasheet", "", x, y, True),
        ("Description", description, x, y, True),
    ]
    prop_text = []
    for name, val, px, py, hidden in props:
        hide = "\n\t\t\t(hide yes)" if hidden else ""
        prop_text.append(
            f'\t\t(property "{name}" "{val}"\n'
            f"\t\t\t(at {px:g} {py:g} 0){hide}\n"
            f"\t\t\t(show_name no)\n"
            f"\t\t\t(do_not_autoplace no)\n"
            f"{indent(effects(), 3)}\n"
            f"\t\t)"
        )
    return (
        "\t(symbol\n"
        f'\t\t(lib_id "ssemas:{symbol}")\n'
        f"\t\t(at {x:g} {y:g} 0)\n"
        "\t\t(unit 1)\n"
        "\t\t(body_style 1)\n"
        "\t\t(exclude_from_sim no)\n"
        "\t\t(in_bom yes)\n"
        "\t\t(on_board yes)\n"
        "\t\t(in_pos_files yes)\n"
        "\t\t(dnp no)\n"
        "\t\t(fields_autoplaced yes)\n"
        f'\t\t(uuid "{comp_uuid}")\n'
        + "\n".join(prop_text)
        + "\n"
        + pin_blocks
        + "\n"
        "\t\t(instances\n"
        f'\t\t\t(project "{PROJECT}"\n'
        f'\t\t\t\t(path "/{SHEET_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n'
        "\t\t\t\t\t(unit 1)\n"
        "\t\t\t\t)\n"
        "\t\t\t)\n"
        "\t\t)\n"
        "\t)"
    )


def label(name: str, x: float, y: float, tag: str, rotation: int = 180) -> str:
    return (
        f'\t(label "{name}"\n'
        "\t\t(exclude_from_sim no)\n"
        f"\t\t(at {x:g} {y:g} {rotation})\n"
        f"{indent(effects(justify='right bottom'), 2)}\n"
        f'\t\t(uuid "{uid(f"label:{tag}")}")\n'
        "\t)"
    )


def no_connect(x: float, y: float, tag: str) -> str:
    return (
        "\t(no_connect\n"
        f"\t\t(at {x:g} {y:g})\n"
        f'\t\t(uuid "{uid(f"nc:{tag}")}")\n'
        "\t)"
    )


def note(text: str, x: float, y: float, size: float = 1.27, bold: bool = False) -> str:
    bold_line = "\n\t\t\t(bold yes)" if bold else ""
    return (
        f'\t(text "{text}"\n'
        "\t\t(exclude_from_sim no)\n"
        f"\t\t(at {x:g} {y:g} 0)\n"
        "\t\t(effects\n"
        f"\t\t\t(font\n\t\t\t\t(size {size:g} {size:g}){bold_line}\n\t\t\t)\n"
        "\t\t)\n"
        f'\t\t(uuid "{uid(f"note:{text}")}")\n'
        "\t)"
    )


COMPONENTS = [
    ("J1", "CONN_2", "12V_INPUT", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", 30, 35, ["1", "2"], "12 V DC input"),
    ("J2", "CONN_4", "LM2596_MODULE", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 70, 36, ["1", "2", "3", "4"], "External buck converter: IN+, IN-, OUT-, OUT+"),
    ("J3", "CONN_11", "ESP32_DEVKIT_INTERFACE", "Connector_PinHeader_2.54mm:PinHeader_1x11_P2.54mm_Vertical", 125, 48, [str(i) for i in range(1, 12)], "Labeled cable interface to ESP32 DevKit V1"),
    ("J4", "CONN_5", "SIM800L_MODULE", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical", 185, 36, [str(i) for i in range(1, 6)], "SIM800L module interface"),
    ("U1", "CONN_4", "HC-SR04", "HC-SR04:TH_HC-SR04V", 30, 75, ["1", "2", "3", "4"], "HC-SR04 ultrasonic sensor module"),
    ("R2", "R", "2.2k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 55, 88, ["1", "2"], "HC-SR04 echo divider series resistor"),
    ("R3", "R", "3.3k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 55, 101, ["1", "2"], "HC-SR04 echo divider shunt resistor"),
    ("R4", "R", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 90, 88, ["1", "2"], "SIM800L RX divider series resistor"),
    ("R5", "R", "20k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 90, 101, ["1", "2"], "SIM800L RX divider shunt resistor"),
    ("R1", "R", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 125, 90, ["1", "2"], "Buzzer transistor base resistor"),
    ("R9", "R", "100k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 140, 101, ["1", "2"], "Buzzer base pull-down"),
    ("Q1", "Q_NPN_BCE", "2N2222", "Package_TO_SOT_THT:TO-92_Inline", 155, 91, ["1", "2", "3"], "Low-side buzzer driver"),
    ("BZ1", "BUZZER", "5V_ACTIVE_BUZZER", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", 180, 88, ["1", "2"], "5 V active buzzer"),
    ("D1", "D", "1N4148", "Diode_THT:D_DO-35_SOD27_P10.16mm_Horizontal", 180, 103, ["1", "2"], "Buzzer flyback diode"),
    ("R6", "R", "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 40, 127, ["1", "2"], "Green LED resistor"),
    ("D2", "LED", "GREEN", "LED_THT:LED_D3.0mm", 40, 140, ["1", "2"], "Green status LED"),
    ("R7", "R", "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 85, 127, ["1", "2"], "Yellow LED resistor"),
    ("D3", "LED", "YELLOW", "LED_THT:LED_D3.0mm", 85, 140, ["1", "2"], "Yellow status LED"),
    ("R8", "R", "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 130, 127, ["1", "2"], "Red LED resistor"),
    ("D4", "LED", "RED", "LED_THT:LED_D3.0mm", 130, 140, ["1", "2"], "Red status LED"),
    ("C1", "C_POLARIZED", "1000uF LOW-ESR", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", 180, 130, ["1", "2"], "SIM800L burst-current reservoir"),
    ("C2", "C", "100nF", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", 205, 130, ["1", "2"], "SIM800L high-frequency decoupling"),
    ("C3", "C_POLARIZED", "100uF", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", 180, 150, ["1", "2"], "5 V local decoupling"),
    ("C4", "C_POLARIZED", "100uF 25V", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", 205, 150, ["1", "2"], "12 V input decoupling"),
]


LABELS = [
    ("+12V_IN", 27.46, 33.73, "J1.1"), ("GND", 27.46, 36.27, "J1.2"),
    ("+12V_IN", 67.46, 32.19, "J2.1"), ("GND", 67.46, 34.73, "J2.2"),
    ("GND", 67.46, 37.27, "J2.3"), ("+4V_GSM", 67.46, 39.81, "J2.4"),
    ("+5V_USB", 122.46, 35.3, "J3.1"), ("GND", 122.46, 37.84, "J3.2"),
    ("HC_TRIG", 122.46, 40.38, "J3.3"), ("HC_ECHO_3V3", 122.46, 42.92, "J3.4"),
    ("SIM_TXD", 122.46, 45.46, "J3.5"), ("ESP_TXD_3V3", 122.46, 48, "J3.6"),
    ("BUZZ_CTRL", 122.46, 50.54, "J3.7"), ("GPIO2_GREEN", 122.46, 53.08, "J3.8"),
    ("GPIO4_YELLOW", 122.46, 55.62, "J3.9"), ("GPIO26_RED", 122.46, 58.16, "J3.10"),
    ("+4V_GSM", 182.46, 30.92, "J4.1"), ("GND", 182.46, 33.46, "J4.2"),
    ("SIM_TXD", 182.46, 36, "J4.3"), ("SIM_RXD", 182.46, 38.54, "J4.4"),
    ("+5V_USB", 27.46, 71.19, "U1.1"), ("HC_TRIG", 27.46, 73.73, "U1.2"),
    ("HC_ECHO_RAW", 27.46, 76.27, "U1.3"), ("GND", 27.46, 78.81, "U1.4"),
    ("HC_ECHO_RAW", 55, 84.19, "R2.1"), ("HC_ECHO_3V3", 55, 91.81, "R2.2"),
    ("HC_ECHO_3V3", 55, 97.19, "R3.1"), ("GND", 55, 104.81, "R3.2"),
    ("ESP_TXD_3V3", 90, 84.19, "R4.1"), ("SIM_RXD", 90, 91.81, "R4.2"),
    ("SIM_RXD", 90, 97.19, "R5.1"), ("GND", 90, 104.81, "R5.2"),
    ("BUZZ_CTRL", 125, 86.19, "R1.1"), ("BUZZ_BASE", 125, 93.81, "R1.2"),
    ("BUZZ_BASE", 140, 97.19, "R9.1"), ("GND", 140, 104.81, "R9.2"),
    ("BUZZ_BASE", 149.92, 91, "Q1.1"), ("GND", 157.54, 85.92, "Q1.2"),
    ("BUZZ_SW", 157.54, 96.08, "Q1.3"),
    ("BUZZ_SW", 177.46, 85.46, "BZ1.2"), ("+5V_USB", 177.46, 90.54, "BZ1.1"),
    ("+5V_USB", 176.19, 103, "D1.1"), ("BUZZ_SW", 183.81, 103, "D1.2"),
    ("GPIO2_GREEN", 40, 123.19, "R6.1"), ("LED_GREEN_A", 40, 130.81, "R6.2"),
    ("GND", 36.19, 140, "D2.1"), ("LED_GREEN_A", 43.81, 140, "D2.2"),
    ("GPIO4_YELLOW", 85, 123.19, "R7.1"), ("LED_YELLOW_A", 85, 130.81, "R7.2"),
    ("GND", 81.19, 140, "D3.1"), ("LED_YELLOW_A", 88.81, 140, "D3.2"),
    ("GPIO26_RED", 130, 123.19, "R8.1"), ("LED_RED_A", 130, 130.81, "R8.2"),
    ("GND", 126.19, 140, "D4.1"), ("LED_RED_A", 133.81, 140, "D4.2"),
    ("+4V_GSM", 180, 126.19, "C1.1"), ("GND", 180, 133.81, "C1.2"),
    ("+4V_GSM", 205, 126.19, "C2.1"), ("GND", 205, 133.81, "C2.2"),
    ("+5V_USB", 180, 146.19, "C3.1"), ("GND", 180, 153.81, "C3.2"),
    ("+12V_IN", 205, 146.19, "C4.1"), ("GND", 205, 153.81, "C4.2"),
]


# KiCad's default schematic connection grid is 1.27 mm (50 mil).  Snap every
# symbol origin to it and carry each pin label by the same delta.  Local pin
# coordinates in the project symbols are already exact multiples of 1.27 mm.
_original_origins = {entry[0]: (entry[4], entry[5]) for entry in COMPONENTS}
_snapped_components = []
_origin_shifts: dict[str, tuple[float, float]] = {}
for _entry in COMPONENTS:
    _x, _y = _entry[4], _entry[5]
    _sx, _sy = round(_x / 1.27) * 1.27, round(_y / 1.27) * 1.27
    _origin_shifts[_entry[0]] = (_sx - _x, _sy - _y)
    _snapped_components.append((*_entry[:4], _sx, _sy, *_entry[6:]))
COMPONENTS = _snapped_components
LABELS = [
    (
        _net,
        _x + _origin_shifts[_tag.split(".", 1)[0]][0],
        _y + _origin_shifts[_tag.split(".", 1)[0]][1],
        _tag,
    )
    for _net, _x, _y, _tag in LABELS
]


def main() -> None:
    symbols = extract_symbols(ROOT / "ssemas.kicad_sym")
    used = {entry[1] for entry in COMPONENTS}
    missing = used - symbols.keys()
    if missing:
        raise SystemExit(f"Missing symbol definitions: {sorted(missing)}")

    sections = [
        "(kicad_sch",
        "\t(version 20260306)",
        '\t(generator "eeschema")',
        '\t(generator_version "10.0")',
        f'\t(uuid "{SHEET_UUID}")',
        '\t(paper "A4")',
        "\t(title_block",
        '\t\t(title "Smart Sewage Monitoring System - Module Carrier")',
        '\t\t(date "2026-10-29")',
        '\t\t(rev "2.0")',
        '\t\t(company "SSEMAS")',
        '\t\t(comment 1 "ESP32 DevKit + HC-SR04 + SIM800L + external LM2596")',
        '\t\t(comment 2 "Set LM2596 output to 4.0 V before connecting SIM800L")',
        "\t)",
        embedded_library(symbols, used),
        note("SMART SEWAGE MONITORING SYSTEM - MODULE CARRIER", 110, 15, 2.0, True),
        note("ESP32 USB/VIN supplies the HC-SR04 and buzzer. The 12 V input feeds an external LM2596 set to 4.0 V for SIM800L.", 110, 20, 1.1),
        note("J3 pin order: 5V, GND, GPIO5, GPIO18, GPIO16, GPIO17, GPIO25, GPIO2, GPIO4, GPIO26, NC.", 110, 23, 1.0),
    ]
    for entry in COMPONENTS:
        sections.append(component(*entry))
    for net, x, y, tag in LABELS:
        sections.append(label(net, x, y, tag))
    _j3x, _j3y = next((entry[4], entry[5]) for entry in COMPONENTS if entry[0] == "J3")
    _j4x, _j4y = next((entry[4], entry[5]) for entry in COMPONENTS if entry[0] == "J4")
    sections.append(no_connect(_j3x - 2.54, _j3y + 12.7, "J3.11"))
    sections.append(no_connect(_j4x - 2.54, _j4y + 5.08, "J4.5"))
    sections.extend(
        [
            note("POWER / MODULE INTERFACES", 55, 27, 1.2, True),
            note("LEVEL SHIFTING AND BUZZER DRIVER", 65, 112, 1.2, True),
            note("STATUS INDICATORS AND DECOUPLING", 65, 118, 1.2, True),
            note("Fit C1 close to J4. Verify 4.0 V at J4 pin 1 before installing the SIM800L module.", 110, 165, 1.1, True),
            note("All module grounds are common. J3 is a labeled cable header; verify the pinout of the specific ESP32 DevKit used.", 110, 169, 1.0),
            "\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)",
            "\t(embedded_fonts no)",
            ")",
        ]
    )
    (ROOT / "schematic.kicad_sch").write_text("\n".join(sections) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
