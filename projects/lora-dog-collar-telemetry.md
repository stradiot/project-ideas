---
tags: [project, hardware, embedded, lora, gps, imu]
status: idea
created: 2026-08-07
---

# LoRa Telemetry Collar for Working Dogs

## Goal

A rugged, battery-powered, long-range tracker for the wolfdog. Not just
position — also what the dog is actually doing: running, walking, or lying
down.

Learning goals:
- LoRa link budget and what "long range" costs in throughput
- Sensor fusion on an IMU — orientation and activity classification
- Bit-level binary protocol design under a hard payload limit

Deliberately out of scope: LoRaWAN and any public network. Point-to-point
to my own receiving station.

The indoor counterpart is [[thread-matter-noise-sensor]] — same dog, same
question of what he is doing unsupervised, answered with a microphone
instead of a radio link.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | Low-power microcontroller (nRF52 / STM32L) |
| Radio | LoRa module (SX1276 / SX1262), 868 MHz |
| Position | GPS receiver over UART, NMEA parsed on device |
| Motion | 6-axis IMU — accelerometer + gyroscope |
| Power | LiPo, charging over USB, deep sleep between transmissions |
| Ground station | Second LoRa module + host, decoding and logging |

### Activity classification

The IMU is not just logged — it is interpreted on the device. Windowed
accelerometer magnitude and variance separate running / walking / resting;
the gyro gives orientation. Only the resulting class is transmitted, not
raw samples.

### Payload packing

LoRa throughput is tiny, so the payload is packed by hand, bit by bit — no
JSON, no text. Latitude and longitude as scaled integers, activity as a
2–3 bit enum, battery as a few bits, fix quality as a flag.

| Field | Bits | Note |
| --- | --- | --- |
| Latitude | 32 | Scaled integer, not float text |
| Longitude | 32 | |
| Activity | 3 | Enum: rest / walk / run / unknown |
| Heading | 8 | Quantised |
| Battery | 6 | |
| Flags | 4 | Fix valid, low battery, … |

Transmission interval adapts to activity: frequent while the dog is
working, rare while it rests — saves both airtime and battery.

### Out of range

The collar will go out of range — that is normal, not a fault, and the
ground station has to behave sensibly when it does. A blank screen is the
one unacceptable answer.

| State | Display |
| --- | --- |
| Packet received | Live position, activity, battery |
| Nothing for N intervals | Last known position, with the age of the fix shown |
| Extended silence | Last fix plus a clear "stale" indication |

The collar keeps transmitting on its schedule regardless — there is no
handshake, so it has no idea whether anyone is listening. Which means the
age of the fix is the only honest thing the handheld can show.

[[home-assistant-rotary-controller]] hits the same problem from the other
direction — a screen that cannot verify what it is displaying — and lands
on the same answer.

### Ground station

The receiving end is [[freertos-pocket-console]] with a LoRa module added:
a handheld with a screen and buttons, carried on the walk. That is what
turns the console from a Tetris toy into equipment, and it is why the
console's task priorities have to be right — packets arrive whenever the
collar sends, not when the UI is ready for them.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Radio | SX1262 module | Better sensitivity and lower current than SX1276 |
| GPS | u-blox module | Good indoor/outdoor fix behaviour |
| IMU | MPU6050 / ICM-42688 | Shared experience with [[custom-flight-controller-drone]] |
| Field testing | Actual walks with the dog | The only honest range test |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| LoRa modules, 2 pcs (collar + station) | 20–30 € |
| GPS module | 15–25 € |
| IMU | 3–10 € |
| MCU board | 10–25 € |
| LiPo + charger + enclosure | 20–30 € |

## Software / firmware

- Firmware: GPS NMEA parsing, IMU sampling and classification, packing,
  LoRa TX, deep sleep scheduling
- Ground station: unpacking, logging, map view, stale-fix handling —
  running on [[freertos-pocket-console]] as a handheld

Legal note: 868 MHz ISM duty cycle limits apply to the collar as well —
the adaptive interval has to respect them.

## Next steps

- [ ] LoRa point-to-point link between two modules, measure real range
- [ ] GPS fix, parse NMEA, sanity-check coordinates
- [ ] IMU sampling, collect labelled data from actual walks
- [ ] Activity classifier, validated against the labelled data
- [ ] Binary payload format, encoder and decoder written together
- [ ] Power budget — measure sleep and TX current, size the battery
- [ ] Handheld ground station, last-known-position and fix age on screen
- [ ] Enclosure and collar mount, survive rain and mud

## Build log
