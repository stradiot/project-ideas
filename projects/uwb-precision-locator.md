---
tags: [project, hardware, embedded, uwb, rf, esp32, home-assistant]
status: idea
depends: []
created: 2026-08-09
---

# UWB Precision Locator

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Measure the time a radio pulse takes to fly across a room, and turn that
into a position accurate enough to be worth trusting. Light covers about
30 cm per nanosecond, so this is a project about counting picoseconds with
a €25 part — and about all the ways that measurement lies until it is
calibrated.

Learning goals:
- Time-of-flight ranging, and why single-sided two-way ranging fails
- Antenna delay calibration — the step that separates ±10 cm from ±3 m
- Phase-difference-of-arrival: recovering a bearing from two antennas
- Turning a noisy range and a noisy angle into a filtered position
- Non-line-of-sight detection — knowing when the measurement is a lie

Two things it ends up doing, both of which have been actual annoyances:

1. Where the dog is in the room he is left in — position alongside the
   sound from [[thread-matter-noise-sensor]], so a noise event comes with
   a place.
2. Finding the car in an underground garage, where GPS is gone and the
   only current method is walking around listening for the horn.

Deliberately out of scope: designing any UWB antenna or its matching. The
radio arrives as a pre-certified module with its antennas already on it,
exactly as in [[ble-sensor-node-pcb]]. Also out of scope: anything
resembling a commercial RTLS — no site survey, no ceiling grid.

## Architecture

### The constraint that shapes everything

The flat is small, and a box screwed into every corner of every room is a
mess nobody wants to live with. That single constraint rules out the
textbook approach and forces the interesting one.

| Topology | Infrastructure | What you get |
| --- | --- | --- |
| Two-way ranging, 1 anchor + 1 tag | One box | A distance. A scalar, no direction |
| Multilateration, 3+ anchors | Three boxes per room | 2D position — and the mess |
| **PDoA, 1 dual-antenna anchor** | **One box** | **Distance *and* bearing — 2D from one device** |

So: phase-difference-of-arrival, not multilateration. One anchor per room
that matters, and none anywhere else. This is the same trick behind the
arrow in a phone's precision-finding screen.

### One device, two roles

The anchor and the handheld finder are the same design, differing only in
where they get power and whether anyone is looking at them.

| Role | Power | Output |
| --- | --- | --- |
| Room anchor | Mains, on a shelf | x/y into Home Assistant |
| Handheld finder | Battery, in a pocket | Distance and an arrow on a screen |

That second role is [[freertos-pocket-console]] with a UWB module bolted
on — the same way the LoRa ground station gave it a reason to exist. The
garage case needs *no installed infrastructure at all*: the thing doing
the locating is in your hand, and the only fixed part is a tag left in the
car.

### Phases

Each phase is useful on its own if the next never happens.

**Phase 1 — A distance.** Two ESP32s, one DWM3000EVB each, wired over SPI
with jumper wires. Implement single-sided TWR first and watch it fail: the
two crystals differ by a few ppm, and over a millisecond of turnaround
that error becomes metres. Then double-sided TWR, which cancels it by
construction. Understanding *why* the second one works is the single most
transferable thing in the project.

**Phase 2 — Calibration.** The raw range will be wrong by a metre or more,
consistently, because the signal spends time inside the antenna and the
chip before it is timestamped. That is the antenna delay, it is different
per unit, and there is no way to guess it. Measure against a tape at
several known distances and fit; with three units, the three pairwise
measurements solve for all three delays at once.

**Phase 3 — An angle.** A DWM3001C-based unit has two antennas a known
fraction of a wavelength apart. The same pulse arrives at them with a
phase difference that maps to a bearing. At channel 5 the wavelength is
about 46 mm, so the spacing is millimetres and comes from the module —
which is precisely why the module is bought rather than built.

**Phase 4 — The two jobs.** Anchor in the dog's room publishing x/y;
handheld and car tag for the garage.

### When the measurement is lying

A dog behind a sofa or a car behind a concrete pillar is a non-line-of-sight
path. The direct pulse is attenuated, a reflection arrives stronger, and a
naive receiver reports the reflection's longer path as the truth — a
confident, wrong answer.

The DW3000 exposes enough diagnostics to catch this: the first-path power
against the total received power, and the shape of the leading edge. When
they disagree, the fix is suspect and should be published as suspect.

This is the same conclusion [[lora-dog-collar-telemetry]] reaches about a
stale GPS fix and [[home-assistant-rotary-controller]] reaches about a
screen it cannot verify. A system that says "2.4 m, but I am unsure" is
useful; one that says "2.4 m" when it means 6 m is worse than nothing.

### What was rejected, and why

**BLE RSSI presence.** The thing UWB exists to replace. Signal strength
through a body or a wall moves more than signal strength across a room,
which is why room-level BLE presence flaps. Not a starting point.

**A passive tag on the dog.** Asked for, and the answer is no. UWB ranging
requires the tag to receive a pulse and transmit a timed reply — there is
no passive backscatter UWB to buy. The dog wears a powered device or he is
not tracked by this method.

**60 GHz mmWave radar, no tag at all.** The honest alternative for "where
is something in this room" with nothing worn: an LD2450 reports x/y for a
few moving targets for about €15, straight into Home Assistant. It is
rejected here for two reasons. It cannot tell *which* target it sees — dog,
person or curtain — and the entire project would be configuring someone
else's sensor. Worth remembering if the collar tag turns out to be the part
he will not tolerate.

**The phone as the tag.** Not possible on the current one: UWB has been a
Pixel *Pro* feature since the 6 Pro, and the Pixel 7 does not have it. Even
with the hardware, Android's ranging API only talks to FiRa-compliant
devices, which means running a certified MAC stack on the tag instead of
writing the ranging protocol — the part actually worth learning. Buying
DWM3001C-based hardware keeps the door open, because that module can run
Qorvo's FiRa stack later. Designed for, not built now.

### Power, and how the tags stay alive

UWB is not a coin-cell technology — a ranging exchange costs tens of
milliamps, and a tag that ranges continuously is a tag that is flat by
Thursday. Both tags sleep and are woken:

| Tag | Wake condition | Expected duty |
| --- | --- | --- |
| Collar | Periodic, faster while the IMU says he is moving | Seconds apart at most |
| Car | BLE advertisement from the handheld, then UWB | Days idle, minutes active |

The car tag's BLE wake-up is how commercial finders do it, and it is the
same radio and the same low-power problem as [[ble-sensor-node-pcb]].

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Radio, phase 1 | 2× Qorvo DWM3000EVB | 3.3 V logic, SPI — wires straight to an ESP32 |
| MCU, phase 1 | ESP32 boards already owned | Nothing bought, nothing modified |
| Radio, phase 3 | DWM3001CDK | Dual antenna for PDoA; the antenna spacing is the product |
| Ground truth | Tape measure, marked floor | Calibration is worthless without it |
| Debug | Logic analyzer on SPI, UART logs of raw timestamps | The timestamps are the whole story |

Legal note: EU UWB operation sits in 6–8.5 GHz at −41.3 dBm/MHz EIRP —
below the noise floor of most things, and indoor-oriented. Off-the-shelf
modules are built to it; the limits are worth reading once anyway.

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| DWM3000EVB, 2 pcs | 40–60 € |
| ESP32 boards | Already owned |
| Jumper wires, protoboard | ~5 € |
| DWM3001CDK, for PDoA | 60–90 € |
| Collar tag — LiPo, charger, enclosure | 15–25 € |
| Car tag — LiPo, enclosure | 10–20 € |
| Handheld | Reuses [[freertos-pocket-console]] |

Phase 1 costs about 50 € on top of parts already in the drawer, and it is
the phase that decides whether the rest is worth doing.

## Hardware of my own — later

Once the ranging works on bought boards, the UWB radio becomes an
extension board for [[ble-sensor-node-pcb]]: a DWM3000 module, its SPI and
IRQ lines, reset, and power. Interconnects only — the antenna is inside
the module and stays there.

That keeps the same build-vs-buy line that note already draws, and it is a
much smaller first custom board than starting from the radio.

One wrinkle worth knowing before committing: the PDoA part, DWM3001C, has
its own nRF52833 inside it, so putting *that* on an nRF52840 carrier means
two MCUs on one board. Either the extension board carries the plain
DWM3000 and does ranging only, or the DWM3001C's own MCU becomes the node
and the carrier gets simpler. That decision belongs after phase 3, when
the answer is obvious.

## Software / firmware

- SPI driver for the DW3000, then TX/RX with hardware timestamping
- SS-TWR, then DS-TWR — written in that order, deliberately
- Antenna delay calibration as a stored per-unit constant, not a magic number
- PDoA: phase difference to bearing, including the ambiguity it comes with
- A filter turning range and bearing into a tracked position — the same
  estimation problem as [[custom-flight-controller-drone]], one dimension
  down and much slower
- NLOS confidence from first-path diagnostics, published alongside the fix
- Home Assistant integration for the room anchor; a finder app on the
  console for the garage

## Plan

- [ ] Wire one DWM3000EVB to an ESP32, read the device ID over SPI
- [ ] Transmit and receive a frame between two units, print raw timestamps
- [ ] SS-TWR, log the error, prove the clock offset is what causes it
- [ ] DS-TWR, watch the same error disappear
- [ ] Antenna delay calibration against a tape measure, at 1 m and 5 m
- [ ] Range across the flat — through a wall, behind furniture, note where it breaks
- [ ] First-path vs. total power logged, find the threshold that flags NLOS
- [ ] DWM3001CDK: bearing from phase difference, checked against a marked floor
- [ ] Filter range and bearing into a position that does not jitter
- [ ] Room anchor into Home Assistant, x/y for the dog next to the noise sensor
- [ ] Car tag with BLE wake, finder app on the console — find the car for real
- [ ] Stretch: UWB extension board for [[ble-sensor-node-pcb]]

## Build log

Session entries live in [[uwb-precision-locator-log]].
