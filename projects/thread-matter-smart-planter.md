---
tags: [project, hardware, embedded, zephyr, thread, matter, iot]
status: idea
created: 2026-08-07
---

# Thread / Matter Smart Planter

## Goal

End-to-end development of a modern IoT device — from Zephyr firmware on an
nRF chip, through a self-hosted Thread Border Router, to the device showing
up natively in Home Assistant. No WiFi, no cloud, no vendor app.

Learning goals:
- Zephyr RTOS and the nRF Connect SDK on real hardware
- Matter data model — clusters, endpoints, attributes
- Thread as an IPv6 mesh, and what a Border Router actually does
- Low-power design: the thing has to run on a battery

Deliberately out of scope: a polished enclosure and any kind of commercial
certification.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | nRF52840 (DK first, custom board later) |
| Sensing | Capacitive soil moisture sensor, ADC |
| Actuation | Small water pump via MOSFET / driver |
| Firmware | Zephyr RTOS + nRF Connect SDK |
| Networking | Matter over Thread — the device is an IPv6 node |
| Infrastructure | OpenThread Border Router on a Raspberry Pi |
| Integration | Home Assistant, Matter integration |

### Bridge experiment

Once the planter itself works, the interesting extension: an application
that talks raw CC1101 to some old, dumb 433/868 MHz sensor and translates it
internally into a Matter structure, so the Thread network sees a device that
has no idea Matter exists. Shares hardware and decoding work with
[[subghz-linux-router]].

### Power

Battery operation is a design constraint from the start, not an
afterthought: Thread sleepy end device, sensor and pump power-gated via
GPIO, moisture measured on a slow interval rather than continuously.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Firmware | nRF Connect SDK, Zephyr, VS Code extension | |
| Hardware | nRF52840 DK | Onboard debugger, also usable as an RCP |
| Border Router | Raspberry Pi + OpenThread | Second nRF dongle as radio co-processor |
| Home automation | Home Assistant | Existing local instance |
| Debug | RTT logging, `ot-ctl`, Thread sniffer | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| nRF52840 DK | 45–60 € |
| nRF52840 dongle (RCP for the Border Router) | 10–15 € |
| Soil moisture sensor, capacitive | 3–8 € |
| Water pump + tubing + MOSFET | 10–15 € |
| LiPo cell + charger | 10–15 € |

## Software / firmware

- Zephyr application: ADC sampling, pump control, Matter cluster exposure
- Matter device type — a moisture sensor endpoint plus an on/off endpoint
  for the pump is enough to start
- OpenThread Border Router on the Pi, commissioned into Home Assistant

Hardware carries over from [[ble-sensor-node-pcb]] — same SoC, same SDK, so
a custom carrier board is a natural second revision.

## Next steps

- [ ] Zephyr blink and RTT logging on the DK
- [ ] Read the moisture sensor over ADC, calibrate dry vs. wet
- [ ] Drive the pump, add a hard safety timeout on runtime
- [ ] Bring up the OpenThread Border Router on the Pi
- [ ] Matter over Thread — commission the device, see it in Home Assistant
- [ ] Battery operation as a sleepy end device, measure actual current draw
- [ ] Stretch: CC1101 → Matter bridge for a legacy sensor

## Build log
