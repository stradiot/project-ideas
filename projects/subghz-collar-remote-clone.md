---
tags: [project, hardware, embedded, rf, subghz, esp32, home-assistant]
status: built
depends: []
repo: d-control-400-remote
github: https://github.com/stradiot/d-control-400-remote
created: 2026-08-09
---

# Sub-GHz Collar Remote Clone

The one project here that was built before the vault existed, so this note
is written backwards from a finished device rather than forwards from an
idea. Code in `d-control-400-remote`.

## Now

Signal decoded and rebuilt. The tick is 208.9 µs (not 200 µs); the frame is
109 ticks (not 273); the old payload was mistimed and misaligned rather than
damaged. New firmware compiled and ready to test. Next: flash and listen to
the collar — does it reliably beep now?

## Goal

Trigger the beep on a Dogtrace d-control 400 collar from Home Assistant,
instead of only from the original handheld remote. The beep is a recall
signal — the useful half of that device — and having it reachable from
automation means it works when the remote is on the kitchen table.

Deliberately out of scope: the shock function. Capturing that button press
would work identically and it is not being done. Also out of scope: a
universal remote — each handheld carries its own identifier, so this is a
structural template that happens to be loaded with mine.

## Learning value

- Capturing a real transmission on an SDR and turning IQ into timings
- Driving a CC1101 by bit-banging OOK, with no formal protocol decode
- ESPHome as an integration path, against bare PlatformIO firmware
- Keeping a captured signal out of a public repo without breaking the build
- Taking one thing all the way: firmware, PCB, enclosure, deployed

## Practical value

Real, collected, and in daily use — the only project here that can say all
three. The recall beep now fires from Home Assistant, which means it works
when the handheld remote is on the kitchen table, and that was the entire
premise.

It is worth being precise about the remaining gap: the beep fires about 70%
of the time, so in practice it is retried. A device that works most of the
time is genuinely useful and genuinely not finished, and calling it either
one alone would be wrong.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | Wemos LOLIN C3 Mini — ESP32-C3 |
| Radio | CC1101, 868 MHz part with the 26 MHz crystal |
| Carrier | 869.525 MHz, OOK |
| Payload | Captured fixed-code frame, as run-length ticks × `BASE_TICK_US` |
| Modulation | Bit-banged asynchronous timings — no packet engine, no sync word |
| Trigger | BOOT button on GPIO 9, or Home Assistant over ESPHome |
| Secrets | `include/signal.h` encrypted with sops |
| Physical | Own PCB (gerbers) and a 3D printed case and lid |

### Replay, not decode — and what that costs

The protocol is not published, so nothing here is reverse engineered. The
frame was captured with an SDR, cleaned up, and is re-emitted as raw
timings. That was the fast route to a working device, and it worked: the
collar beeps.

It also turned out to be the expensive route, and that is the most useful
thing this project has produced. The beep fires about 70% of the time, on
both firmware paths — and with no decoded model of the frame there is
nothing to check a failure against. No preamble to verify, no checksum to
recompute, no way to tell a bad transmission from a bad capture.

That is precisely the argument [[subghz-linux-router]] makes for writing
the decoder by hand, arrived at from the other direction and at the cost of
a device that is unreliable in the hands. Recognition is what this project
skipped, and it is the thing every later sub-GHz build starts from.

### Where the 70% is coming from

Established so far, from decrypting and analysing the stored payload:

- Every one of the 224 elements is exactly 200 or 400 µs. A genuine SDR
  capture is never that clean — those are quantised values, not measured ones.
- The payload fits none of PWM, Manchester, biphase FM0/FM1, PPM or NRZ,
  and run lengths cap at two ticks, which no standard line code explains.

Both point at the same cause: a two-bucket short/long classifier applied
during capture, which threw away symbols that were neither. If that holds,
no amount of tuning the base tick will fix it, because information is
already missing — it has to be re-captured.

The counter-evidence was worth as much as evidence would have been. Every
encoding test was expected to pass and none did, which ruled out an entire
category of explanation in one pass.

### The refactor that made it testable

`signal.h` moved from absolute microseconds to run-length ticks plus a
single `BASE_TICK_US` scalar, verified lossless by round trip. The payload
became `tick × {1,2}` and one number — and that number can be swept from a
serial calibration mode at runtime, without reflashing between attempts.

Trading a slightly more abstract payload for the ability to test a
hypothesis in seconds instead of minutes is the right trade whenever the
hypothesis is "the timebase is wrong".

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Capture | RTL-SDR | Tune 250 kHz low — the RTL2832U puts a DC spike dead centre |
| Analysis | Universal Radio Hacker | Signal view covers what Inspectrum would be for |
| Analysis | GNU Radio in a UTM Linux VM | Not usable natively on the Mac |
| Pipeline | `tools/analyze_capture.py` | IQ → envelope → run lengths → base tick → frame → encoding tests |
| Firmware | PlatformIO, and ESPHome for the HA path | Two paths, same signal |
| Secrets | sops | `include/signal.h` is never committed in plaintext |
| Enclosure | Fusion 360 | Same tool noted for enclosures in [[ble-sensor-node-pcb]] |

`analyze_capture.py` was validated against two synthetic captures with
known ground truth before being trusted, which caught three bugs in it:
false clamping warnings on healthy PWM data, run clustering that collapsed
4 and 5 ticks into a bogus 4.44× group, and frame splitting that invented
phantom frames on an 8-tick gap. A tool that has not been run against a
known answer is not evidence.

## Budget

Already spent.

| Item | Cost |
| --- | --- |
| Wemos LOLIN C3 Mini | ~5 € |
| CC1101 module, 868 MHz | 3–5 € |
| Antenna, perfboard, wiring | ~10 € |
| PCB fabrication | 10–20 € |
| Filament for the enclosure | ~2 € |

## Software / firmware

- `src/main.cpp` — button handling, LED feedback, transmit sequence, and
  the serial calibration mode for sweeping the base tick
- `include/signal.h` — RF parameters and the captured payload, sops encrypted
- `include/pinout.h` — pin map for the custom SPI routing on the C3
- `esphome/d-control-400.yaml` + `cc1101.h` — the Home Assistant path
- `tools/analyze_capture.py` — the whole analysis pipeline in one script

## Plan

- [ ] `sops -e -i include/signal.h` — it is plaintext in the working tree
- [x] Capture at 869.275 MHz with the RTL-SDR, 250 kHz below the carrier
- [x] Measure 10–20 short and long pulses by hand in URH, mean per cluster
- [x] Run `analyze_capture.py` on the real capture, check it against the hand
      measurements rather than the other way round
- [x] Confirm or kill the clamping hypothesis
- [x] If confirmed: re-capture without the two-bucket classifier, rebuild the payload
- [ ] Sweep `BASE_TICK_US` from the calibration mode, find where reliability peaks
- [ ] Get the beep to fire every time, in the hand, at range

Same dog as [[lora-dog-collar-telemetry]] and
[[thread-matter-noise-sensor]] — this is the only one of the three he
notices. Doing the manual measurements before running the script is
deliberate: the SDR skill is the point, and it is the same skill
[[subghz-linux-router]] Phase 1 is built on.

## Build log

Session entries live in [[subghz-collar-remote-clone-log]].
