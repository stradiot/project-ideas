---
tags: [project, hardware, embedded, ble]
status: planning
depends: []
created: 2026-08-07
---

# BLE Sensor Node — Custom PCB

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Custom carrier board around a certified nRF52840 module. BLE sensor with
USB, battery power and SPI flash for data logging.

### Its first job

A board without a job becomes a board in a drawer, so the first revision
gets deployed rather than shelved: room climate — temperature, humidity,
pressure from the I2C sensor — logged to the SPI flash and advertised over
BLE, picked up by Home Assistant. Battery powered, no wires, left in a room
for weeks.

That deployment is also the only honest test of the power path and the
sleep current, because a bench measurement will not catch a board that dies
after nine days.

Its second job is [[usb-device-and-linux-driver]] — the nRF52840's native
USB is already routed on this board, so it doubles as the device end of
that project with no new hardware. Full-speed and device-only, which is the
whole of what this silicon can do on USB; host, dual-role and Power Delivery
live on other hardware in that note.

Its third is [[thread-matter-growbox]], which is what this board's Zephyr
work is actually for. That project runs on this board rather than a
development kit — the deliverable here is a working out-of-tree board
definition, and the growbox is the application built on top of it.

Its third is a UWB radio, as a second board rather than a revision of this
one. [[uwb-precision-locator]] proves the ranging on bought modules first;
what comes back here afterwards is a small extension carrying a DWM3000 —
SPI, IRQ, reset, power, and nothing else. The antenna is inside that module
exactly as it is inside the Raytac, so the rule below holds unchanged. It
is a deliberately easy second PCB: no power path, no USB, no charger, just
interconnects onto a header this board already has.

Deliberately out of scope: anything requiring surgical precision (antenna,
RF matching, crystals, DRAM) is avoided by using a pre-certified module.

## Learning value

- PCB schematic and layout in KiCad from scratch
- Power management — LiPo charging, power path, LDO
- Zephyr board porting (custom devicetree, out-of-tree board)

## Practical value

The highest of any unbuilt project here, because the output is a board that
three other projects consume rather than a demonstration that gets put in a
drawer.

Directly: a battery room-climate sensor left in a room for weeks and read by
Home Assistant. Indirectly, and worth more — it is the device end of
[[usb-device-and-linux-driver]] with no new hardware, the target
[[thread-matter-growbox]] runs on instead of a development kit, and the
carrier the DWM3000 extension for [[uwb-precision-locator]] plugs into. The
deliverable that gets reused most is the out-of-tree Zephyr board
definition, not the PCB.

## Architecture

### Module — bought, not designed

**Raytac MDBT50Q-1MV2** (nRF52840), ~5–8 €

- Integrated chip antenna, matching network, crystals
- Certified — FCC / CE / BLE SIG
- Castellated pads, 0.5 mm pitch — not BGA
- Same SoC as the nRF52840 DK, so firmware experience carries over

### Designed myself

| Block | Implementation | What I learn |
| --- | --- | --- |
| USB | USB-C connector + USBLC6-2SC6 (ESD), D+/D− straight into nRF52840 | Native USB peripheral, enumeration |
| Power | MCP73831 LiPo charger, 3.3 V LDO (MCP1700 / TLV70233), USB/battery power path | Battery management, power sequencing |
| Flash | W25Q32 SPI NOR | SPI driver, littlefs, partitioning |
| Sensor | I2C header (BME280 / SHT4x) + power gating via GPIO | I2C, current consumption |
| Debug | SWD header (SWDIO / SWCLK / RESET) | Flashing and debugging via external probe |
| I/O | GPIO breakout, status LED, user + reset button | Power budget, extensibility |

### Not designed

- Antenna, RF matching, crystals — all inside the module
- External DRAM — nRF52840 has internal RAM and flash
- Anything high-speed (PCIe, HDMI, USB3) — needs controlled impedance

### Pitfalls

Not precision-related, but easy to get wrong:

- Decoupling caps as close to module VDD pins as possible — follow the
  Raytac layout guide exactly
- Ground keep-out zone under the module antenna — no copper, no traces;
  the guide defines it precisely
- Route USB D+/D− as a pair, matched length, away from switching
  regulators (even at full speed where impedance control isn't needed)
- RESET pin — pull-up and debounce cap per the recommended circuit
- Power sequencing on USB ↔ battery transition — test unplugging USB
  mid-charge

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Schematic + layout | KiCad | Community standard for nRF52840; git-friendly text format |
| Mechanical / enclosure | Fusion 360 | Later, only if an enclosure is needed |
| PCB | 2-layer | Sufficient; 4 layers only for a better ground plane |
| Debugger | nRF52840 DK | Onboard J-Link via the Debug Out header |
| Hand soldering | Pinecil V2 | Enough for THT and larger SMD passives |

KiCad over Fusion despite having a personal-use Fusion licence: reference
designs and footprints for Raytac modules are almost always KiCad, forums
discuss KiCad specifics, and the text-based project format fits the
existing git workflow.

## Fabrication

SMD soldering is untrained, no hot air station, no paste. Strategy is to
let JLCPCB place the critical SMD parts and hand-solder only what's
manageable.

| Parameter | Value |
| --- | --- |
| Fab | JLCPCB |
| PCB quantity | 5 |
| PCBA quantity | 2 |
| Remainder | 3 bare boards — for SMD practice later |

PCBA 2 rather than 1: setup and extended part fees are charged once
regardless of assembled quantity. The second board only costs the parts,
and is a spare if the first dies during debugging.

### BOM split

| Assembled by JLCPCB | Hand-soldered (Pinecil) |
| --- | --- |
| Raytac module | Pin headers |
| USBLC6-2SC6 | Buttons |
| MCP73831 | LED |
| LDO | JST battery connector |
| W25Q32 | USB-C, if a THT variant is used |
| Small SMD passives |  |

Side effect: fewer extended parts lowers the JLCPCB cost, and leaves some
actual hands-on work.

## Budget

| Item | Cost |
| --- | --- |
| nRF52840 DK — the debug probe | 45–60 € |
| PCB, 5 pcs + shipping + VAT | 20–40 € |
| Components incl. spares | 20–30 € |
| JLCPCB assembly (setup + extended parts) | 30–50 € |
| SMD practice board (AliExpress) | 2–5 € |
| **Total — first iteration** | **~115–180 €** |
| Each further layout revision | 30–50 € |

The DK is bought here rather than borrowed. It is the only debug probe in
the plan, a custom board with no working firmware cannot be brought up
without one, and every other nRF project in the vault runs on hardware this
project produces — so nothing else is going to buy it first.

Budget for at least two revisions. The first board almost never works
fully, and accounting for that upfront saves frustration later.

## Firmware — Zephyr / nRF Connect SDK

A custom board means a custom board definition. Ideally as an out-of-tree
board via `BOARD_ROOT`, which also means learning the Zephyr module system.

### Board definition files

| File | Contents |
| --- | --- |
| `<board>.dts` | Devicetree — which peripherals, wired where |
| `<board>-pinctrl.dtsi` | Mapping functions to specific pins |
| `<board>_defconfig` | Kconfig defaults for the board |
| `board.yml` | Metadata — SoC, revisions |
| `Kconfig.<board>` | Board-specific Kconfig |

### To define in the DTS

- `&spi0` with W25Q32 as a child node (`compatible: jedec,spi-nor`) plus
  partitions for littlefs
- `&i2c0` on the pins routed to the sensor header
- `&uart0`, if broken out
- Chosen nodes: `zephyr,console`, `zephyr,code-partition`
- Aliases `led0` and `sw0` — so sample apps work unmodified
- USB device node, plus the corresponding Kconfig options

Approach: copy an existing definition from NCS — either
`nrf52840dk_nrf52840`, or better one of the `raytac_mdbt50q_db*`
definitions from Zephyr upstream — and go through it line by line.
No need to write from scratch, but the goal is understanding every line.

See [[zephyr-devicetree]] for notes on devicetree itself.

## Plan

- [ ] Get the Raytac MDBT50Q-1MV2 hardware/layout guide and KiCad footprint
- [ ] Order an SMD practice board, practise drag soldering with the Pinecil
- [ ] Draw the schematic in KiCad
- [ ] Layout, run DRC, verify the antenna keep-out zone
- [ ] Order from JLCPCB — PCB 5, PCBA 2
- [ ] Hand-solder the THT parts
- [ ] Zephyr board definition, first blink
- [ ] BLE advertising, then I2C sensor and logging to flash
- [ ] Measure sleep current, size the battery against a realistic interval
- [ ] Into Home Assistant, board left in a room — first real deployment

## Build log

Session entries live in [[ble-sensor-node-pcb-log]].
