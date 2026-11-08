# SSEMAS Smart Sewage Monitoring Carrier

This directory contains the editable KiCad 10 schematic and routed two-layer PCB for the module-level system shown in the wiring reference:

- ESP32 DevKit V1
- HC-SR04 ultrasonic sensor
- SIM800L module
- external LM2596 buck converter, adjusted to 4.0 V
- transistor-driven 5 V buzzer
- green, yellow, and red status LEDs

Open `schematic.kicad_pro` in KiCad. The main editable sources are:

- `schematic.kicad_sch` — self-contained schematic with embedded project symbols
- `schematic.kicad_pcb` — placed, routed, copper-filled PCB
- `HC-SR04.pretty/TH_HC-SR04V.kicad_mod` — project-local ultrasonic sensor footprint
- `ssemas.kicad_sym` — reusable project symbol library

## Interface pin order

### J2 — LM2596 module

1. IN+ / 12 V
2. IN- / GND
3. OUT- / GND
4. OUT+ / 4.0 V

### J3 — ESP32 DevKit cable

1. VIN/5V from USB
2. GND
3. GPIO5 — HC-SR04 TRIG
4. GPIO18 — divided HC-SR04 ECHO
5. GPIO16/RX — SIM800L TXD
6. GPIO17/TX — SIM800L RXD divider
7. GPIO25 — buzzer
8. GPIO2 — green LED
9. GPIO4 — yellow LED
10. GPIO26 — red LED
11. reserved / no connection

### J4 — SIM800L module

1. VCC / 4.0 V
2. GND
3. TXD
4. RXD
5. RST / no connection

## Electrical notes

- Adjust the LM2596 output to **4.0 V before installing the SIM800L**.
- Power the ESP32 DevKit from USB. J3 pin 1 carries that 5 V rail to the HC-SR04 and buzzer.
- C1 is a 1000 uF low-ESR reservoir capacitor for SIM800L transmit-current bursts.
- The HC-SR04 ECHO divider is 2.2 kΩ / 3.3 kΩ, producing about 3.0 V from a 5 V echo signal.
- The SIM800L RX divider is 10 kΩ / 20 kΩ, producing about 2.2 V from the ESP32's 3.3 V TX signal.
- All module grounds are common.
- J3 is a labeled cable interface because ESP32 DevKit clones vary; verify the actual board pin labels before wiring the cable.

## Validation

The generated design passes KiCad 10 checks:

- ERC: 0 errors, 0 warnings
- DRC: 0 violations, 0 unconnected pads, 0 footprint errors

Reports are in `reports/`. Gerber and drill files are in `fabrication/`.

## Regeneration

The deterministic generators are retained for maintainability:

```bash
python3 generate_schematic.py
python3 generate_pcb.py
```

They require KiCad 10 and its Python `pcbnew` module.
