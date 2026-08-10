---
tags: [project, hardware, embedded, zephyr, thread, matter, iot]
status: idea
depends: [ble-sensor-node-pcb]
created: 2026-08-07
---

# Thread / Matter Growbox

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

End-to-end development of modern IoT devices — Zephyr firmware on an nRF
chip, Matter over Thread, showing up natively in Home Assistant. No WiFi on
the device, no cloud, no vendor app.

Deliberately out of scope: commercial certification, and switching mains
from anything I designed. Everything the box drives is low voltage.

Two phases. Each is a finished device on its own if the next never happens.

### Phase 1 — Smart planter

A battery sensor node in a pot: soil moisture, air temperature and humidity,
reported over Thread as Matter endpoints, with Home Assistant raising a
notification when the soil dries out. Watering stays manual.

That is deliberately the smallest useful device, because the interesting
part of phase 1 is not the sensing. It is running for weeks on a cell as a
Thread **sleepy end device** and being able to say why the current draw is
what it is.

**No light sensor and no pH.** Light where a pot sits does not change —
measure it once by hand when choosing the spot. And soil pH is not a thing a
probe in a pot can tell you: a real reading needs a soil-and-distilled-water
slurry measured in a beaker, which is a lab procedure. The cheap three-in-one
"soil pH meters" are two dissimilar metals reading conductivity, and they
are decorative. pH returns in phase 2, in a reservoir, where it is real.

### Phase 2 — Growbox

The same firmware stack grown into a self-sufficient enclosed grow space:
lighting, ventilation, irrigation from a reservoir, and the sensing to close
the loop. Mains-powered, which makes it a Thread **router** rather than a
sleepy end device — so the two phases between them cover both roles the mesh
has.

| Function | Implementation | Matter |
| --- | --- | --- |
| Grow light | 12/24 V LED strip, MOSFET, PWM | On/Off + Level Control |
| Ventilation | 12 V fan, PWM | On/Off + Level Control |
| Irrigation | 12 V pump, MOSFET | On/Off |
| Soil moisture | Capacitive probe per pot, ADC | Sensor endpoint |
| Air temp / humidity | BME280 or SHT4x, I2C | Sensor endpoints |
| Reservoir level | Float or capacitive | Boolean state |
| Reservoir pH | Glass electrode, buffered front end | Sensor endpoint |

PWM rather than a relay is a deliberate choice: dimming means the Level
Control cluster on top of On/Off, which is a materially richer piece of the
Matter data model than a switch, and it costs a MOSFET.

## Learning value

- Zephyr RTOS and the nRF Connect SDK on a board of my own
- Matter data model — clusters, endpoints, attributes — and what happens
  when a device needs more than one of each
- Thread as an IPv6 mesh, and both device roles in it: a battery sleepy end
  device and a mains-powered router
- Low-power design where the battery figure is measured, not claimed

## Practical value

Modest in phase 1 and substantial in phase 2, which is why they are split
and why each is a finished device on its own.

The planter tells me a pot has dried out, and watering stays manual — that
is a notification, not an automation, and a person walking past the plant
would notice the same thing eventually. The growbox is the one that
actually earns its keep: lighting, ventilation and irrigation from a
reservoir, closed around its own sensing, so a plant survives a fortnight
without anyone in the flat.

Both run with no cloud, no vendor app and no Wi-Fi on the device, which is
worth something on its own — nothing here stops working when a company
turns off a server.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | The carrier board from [[ble-sensor-node-pcb]] |
| Firmware | Zephyr RTOS + nRF Connect SDK |
| Networking | Matter over Thread — the device is an IPv6 node |
| Border Router | Home Assistant's OpenThread Border Router add-on |
| Drivers, phase 2 | A small add-on PCB off the carrier's GPIO header |
| Integration | Home Assistant, Matter integration |

### The Border Router is not built here

A Thread device with no Border Router reaches nothing, so one has to exist —
but `otbr-agent` is installed software, not something to implement. Thread
has no master either: Leader and Router roles are elected inside the mesh,
and the Border Router only bridges Thread's IPv6 to the LAN.

So it goes where it costs least: the **OpenThread Border Router add-on on
the Raspberry Pi already running Home Assistant**, plus a Thread-capable USB
radio. No second Pi, no separate build, and Matter devices land natively in
HA. The add-on route needs Home Assistant OS or Supervised — a plain Docker
install cannot run add-ons, and then a standalone `otbr-agent` on the same
Pi is the fallback.

What is still learned without building it: what a Border Router does at the
boundary, the mesh roles, commissioning and credentials, `ot-ctl`, and a
sniffer on the frames if the mesh misbehaves.

### Running on my own board

Phase 1 runs on the carrier board from [[ble-sensor-node-pcb]] rather than a
development kit. That is the point of having designed one: the board's
deliverable is a working out-of-tree Zephyr board definition, and this is
the application built on top of it. The DK stays what it is on that project
— the debug probe.

Phase 2 needs more current than a carrier board should source, so the
MOSFETs, flyback diodes, connectors and the 12 V rail live on a small add-on
board off the GPIO header. It is a deliberately easy second layout — no
power path, no radio, no USB — in the same spirit as the UWB extension that
note already plans.

### Water, electricity and the failure modes

The half the original note never designed, and the half that actually
matters once a pump exists.

- **Pump off is the power-on state.** Not a software default — the gate
  pulls low through a resistor, so a hung MCU or a reset mid-cycle leaves the
  pump off rather than running.
- **Dry-run protection.** A pump running dry burns out. The reservoir level
  sensor is what makes "empty" knowable rather than inferred from a timeout.
- **Runtime limit** on top of that, because a stuck level sensor is also a
  failure.
- **An overflow path** — where the water goes if the moisture reading is
  wrong and the pump runs anyway. A tray, a drain, and a pot that cannot
  hold more than the tray can.
- **Physical separation.** Water above, electronics below and sealed, and
  the LiPo nowhere near either. Phase 2 is mains-adjacent and the cell is the
  part that objects most to being wet.
- **Nothing I designed switches mains.** One external PSU, everything
  downstream at 12 V or lower. A grow light big enough to need mains gets a
  commercial smart plug, and stops being part of my device.

### The moisture probe is not a sensor yet

Capacitive probes give a raw ADC value, not a moisture percentage, and it
shifts with soil type, salinity and temperature. It needs a dry reading and
a saturated reading per soil, recorded, and a note of which soil they were
taken in.

The common breakout boards also corrode: the traces sit under thin solder
mask and the exposed via barrels wick water. They get coated in epoxy before
they go anywhere near a pot, and they are treated as consumable regardless.

### Bridge experiment

Once the box works, the interesting extension: an application that talks raw
CC1101 to some old, dumb 433/868 MHz sensor and translates it internally
into a Matter structure, so the Thread network sees a device that has no idea
Matter exists. Shares hardware and decoding work with [[subghz-linux-router]].

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Firmware | nRF Connect SDK, Zephyr, VS Code extension | |
| Hardware | The board from [[ble-sensor-node-pcb]] | Its DK is the debug probe |
| Border Router | HA's OpenThread BR add-on | On the Pi already running HA |
| Thread radio | USB dongle for the BR | Connect ZBT-1, or an nRF52840 dongle as RCP |
| Home automation | Home Assistant | Existing local instance |
| Debug | RTT logging, `ot-ctl`, Thread sniffer | |
| Power | Nordic PPK2 or a bench supply with µA resolution | Phase 1's whole claim is a current figure |

## Budget

Rough estimates, split by phase. The nRF52840 DK is gone from this budget —
it belongs to [[ble-sensor-node-pcb]], which needs it as a debug probe
regardless.

| Item | Cost |
| --- | --- |
| **Phase 1** | |
| Thread radio dongle for the Border Router | 25–40 € |
| Soil moisture sensor, capacitive, ×2 spare | 5–10 € |
| BME280 / SHT4x | 3–6 € |
| LiPo cell + charger | 10–15 € |
| Epoxy, potting, pot and tray | ~10 € |
| **Phase 2** | |
| Driver add-on PCB, fabricated | 20–35 € |
| MOSFETs, diodes, connectors, 12 V PSU | 20–30 € |
| LED grow strip, 12/24 V | 25–40 € |
| Fan, pump, tubing | 15–25 € |
| Reservoir, level sensor, plumbing | 15–25 € |
| pH probe + buffered front end + solutions | 45–60 € |
| Tent or enclosure | 40–80 € |

Phase 1 is around 55–80 €. Phase 2 roughly triples it, and is a decision
taken after phase 1 has been running in a pot for a month.

## Software / firmware

- Zephyr application: ADC sampling, I2C sensors, Matter cluster exposure
- Phase 1 Matter model: moisture, temperature and humidity sensor endpoints
- Phase 2 Matter model: multiple endpoints — On/Off plus Level Control for
  light and fan, On/Off for the pump, sensors for the rest
- Sleepy end device in phase 1; router in phase 2, with the polling and
  power behaviour that difference implies
- MCUboot for OTA — a device sealed next to a reservoir cannot be updated
  over SWD. [[bare-metal-bootloader]] covers what MCUboot is actually doing
  underneath, which is worth knowing before trusting a sealed box to it.
- Home Assistant automations: the notification in phase 1, the schedules and
  the closed loop in phase 2

The Thread network established here is infrastructure, not a one-off — the
second device to join it is [[thread-matter-noise-sensor]], which reaches the
same Matter data model from ESP-IDF instead of Zephyr and is worth building
afterwards for exactly that contrast. Once there are several such devices,
[[home-assistant-rotary-controller]] is how they get driven without reaching
for a phone.

## Plan

**Phase 1 — the planter**

- [ ] Border Router up: HA's OTBR add-on plus the radio dongle, mesh formed
- [ ] Zephyr blink and RTT logging on my own board, not a DK
- [ ] Read the moisture probe over ADC; record dry and saturated calibration
- [ ] Coat the probe, and note how long the coating lasts
- [ ] BME280 over I2C, temperature and humidity sane against a reference
- [ ] Matter over Thread — commission it, see the endpoints in Home Assistant
- [ ] Sleepy end device: measure actual current draw and write the number down
- [ ] Home Assistant automation that tells me the plant needs water
- [ ] Leave it in a pot for a month and find out what the battery really does

**Phase 2 — the growbox**

- [ ] Decide the scale — what is grown, and where the box lives
- [ ] Driver add-on board: MOSFETs, flyback diodes, 12 V rail, connectors
- [ ] Light on PWM, exposed as On/Off plus Level Control, dimming from HA
- [ ] Fan on PWM, and a reason for the speed it settles at
- [ ] Reservoir, level sensor, and pump-off proven as the power-on state
- [ ] Pump with dry-run protection, runtime limit and an overflow path
- [ ] Pull the power mid-cycle, repeatedly, and confirm nothing floods
- [ ] pH probe in the reservoir, calibrated against buffer solutions
- [ ] Close the loop: schedules and thresholds, running unattended for a week
- [ ] Stretch: CC1101 → Matter bridge for a legacy sensor

## Build log

Session entries live in [[thread-matter-growbox-log]].
