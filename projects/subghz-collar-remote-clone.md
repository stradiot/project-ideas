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

Reliability now confirmed at the real installed geometry: 12/12 beeps
through the load-bearing wall with placement redrawn each time, and the
occasional chopping there traced to RF margin rather than a firmware timing
bug, so RMT stays a structural improvement rather than a required fix. Also
shipped a continuous LED heartbeat (green pulse if Wi-Fi is up, amber if
not) so idle reads as alive instead of dark, deployed over the air and
pushed to `main`. Three items remain untouched: flashing the standalone
build to the perfboard prototype over USB, moving transmission onto the RMT
peripheral, and a differential shock/B-channel capture to start on the
protocol. Next up is the USB flash.

## Lessons

- **The 70% was burst structure, not timing.** A real press is 7 copies of
  the frame sent back-to-back with no gap anywhere inside — URH segments a
  recording of one into a single unbroken message, not seven. Cheap
  fixed-code OOK receivers validate frames consecutively: decode one, then
  require the next before a timer expires. A 5 ms gap expires that timer,
  and is also long enough for the receiver's AGC to drift and corrupt the
  next frame's opening. The old firmware happened to pack ~2.5 frames into
  each burst through a bad slice, so a clean frame usually followed a
  disturbed one — 70% was an accident, not a design.
  [[subghz-collar-remote-clone-log#2026-08-11]]
- **A correction in the wrong dimension makes things worse.** Fixing the
  base tick to a measured-correct 209 µs while shrinking the burst to one
  frame took reliability from 70% to *zero*. The tick was genuinely wrong
  and genuinely not the bug; correctness in one dimension does nothing for
  an error in another, and the drop is what finally pointed at burst
  structure. [[subghz-collar-remote-clone-log#2026-08-11]]
- **Tune off-centre, because the DC spike belongs to the receiver.** The
  RTL2832U puts a spike at whatever frequency it is tuned to, so a carrier
  captured dead centre sits under an artefact that is not in the air. The
  869.525 MHz beep was captured at 869.275 MHz — 250 kHz low — at 2 MSps
  with `rtl_sdr`, then read in GNU Radio running in a UTM Linux VM, since it
  is not usable natively on the Mac. URH did the signal view; Inspectrum was
  skipped because URH covers the same ground. Capture several presses in one
  recording, not one — the whole validation below depends on having repeats
  to compare. [[subghz-collar-remote-clone-log#2026-08-09]]
- **A tool that has not been run against a known answer is not evidence.**
  `tools/analyze_capture.py` — IQ to envelope to run lengths to base tick to
  frame to encoding tests — was validated against two synthetic captures
  with ground truth (208 µs base tick, PWM and NRZ) before being pointed at
  real data, and that caught three bugs in it: false clamping warnings on
  healthy PWM, run clustering that collapsed 4 and 5 ticks into a bogus
  4.44× group, and frame splitting that invented phantom frames on an 8-tick
  gap. Any of the three would have been read as a property of the signal.
  Doing the URH measurements by hand first and checking the script against
  them, rather than the other way round, is the same guard from the other
  side — as is asking whether repeated frames in one recording agree with
  each other, which needs no external reference at all and caught both the
  burst-contiguity bug and an over-strict rounding tolerance later on.
  [[subghz-collar-remote-clone-log#2026-08-09]]
- **Measure the symbol, do not let the tool fit it.** URH's *Autodetect
  parameters* reported 400 samples/symbol against a true 417.75 — 9% off,
  because it fits a symbol length rather than measuring one. Measure
  frame-start to frame-start across 654 ticks (not across the 42-tick
  preamble, where the final tick truncates on button release), taking both
  endpoints at the 50% crossing; edge-to-edge biases high by ~10 samples of
  rise and fall time. That gives 208.647 µs at 2 MSps.
  [[subghz-collar-remote-clone-log#2026-08-11]]
- **Replay without decode is what made the failure undiagnosable.** With no
  decoded model of the frame there is no preamble to verify, no checksum to
  recompute, and no way to separate a bad transmission from a bad capture —
  so the first hypothesis (a two-bucket classifier had damaged the capture)
  survived a whole session before hand measurement killed it. That is
  [[subghz-linux-router]]'s argument for writing the decoder by hand,
  arrived at from the expensive direction.
  [[subghz-collar-remote-clone-log#2026-08-09]]
- **Suspending the scheduler is a duty-ratio problem, not a total-blocked-time
  one.** Contiguous bursts need `vTaskSuspendAll()` around a whole burst, and
  that handed the idle task 5 ms out of every 164.5 ms (3%) where the old
  firmware gave it 5 ms out of 27.8 ms (18%) — the idle task feeds the
  watchdog, so `TASK_WDT` fired. `esphome::App.feed_wdt()` in the gap fixed
  it alone; the 30 ms gap shipped alongside it was self-inflicted damage
  that caused audible chopping. Reading `esp_reset_reason()` settled
  brownout-vs-watchdog in one flash instead of iterating on a guess — but
  only on the second try, because an OTA reflash calls `esp_restart` and
  overwrites the very register being read. The gap and the `feed_wdt()` call
  also went in together, both fixed the resets, and untangling which one
  mattered cost an extra flash-and-listen cycle: one variable per physical
  test, always. [[subghz-collar-remote-clone-log#2026-08-11]]
- **Chopping at range is RF margin, not a firmware timing defect, and
  `FRAMES_PER_BURST` does not set the size of a chop.** Each frame carries
  its own preamble (42 of 109 ticks, 38%) so it is independently acquirable,
  meaning a lost decode drops the tone for about one frame's worth
  regardless of how many frames make up its burst; what `FRAMES_PER_BURST`
  actually trades is the number of inter-burst gaps against how long the
  scheduler stays suspended. Localised to RF rather than a stretched
  inter-burst gap by moving only the receiver: 6/6 clean at 3 m
  line-of-sight against 8/12 chopped at 5 m through a load-bearing wall
  (Fisher's exact p ≈ 0.011), with every timing-side variable held fixed on
  the transmitter. [[subghz-collar-remote-clone-log#2026-08-13]]

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

It is worth being precise about how long that took to be true. The beep
fired about 70% of the time for the whole period the device was in daily
use, and was retried in practice; a device that works most of the time is
genuinely useful and genuinely not finished, and calling it either one
alone would have been wrong. That is fixed now — 6/6 on the reliability
test after the burst-contiguity change — and the sentence stays here
because the 70% version is what shipped first and was lived with.

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
thing this project has produced. The beep fired about 70% of the time on
both firmware paths — and with no decoded model of the frame there was
nothing to check a failure against. No preamble to verify, no checksum to
recompute, no way to tell a bad transmission from a bad capture. Diagnosing
it took three sessions and one hypothesis that turned out to be wrong.

That is precisely the argument [[subghz-linux-router]] makes for writing
the decoder by hand, arrived at from the other direction and at the cost of
a device that was unreliable in the hands for as long as it was. Recognition
is what this project skipped, and it is the thing every later sub-GHz build
starts from.

### Where the 70% came from

The first answer was wrong, and it is worth keeping because of how
convincing it was. Decrypting the stored payload showed that every one of
the 224 elements was exactly 200 or 400 µs — a genuine SDR capture is never
that clean — and that the payload fit none of PWM, Manchester, biphase
FM0/FM1, PPM or NRZ, with run lengths capping at two ticks that no standard
line code explains. Both pointed at a two-bucket short/long classifier
applied during capture, throwing away symbols that were neither. Every
encoding test was expected to pass and none did, which felt like it had
ruled out an entire category of explanation in one pass.

Hand measurement in URH killed it. Every run quantised at the true
417.75-sample grid, 0% off-grid across 13 presses, with σ/mean of 0.6% — if
symbols had been discarded there would be rounding errors scattered through
the frame rather than a perfect fit. Only 1T and 2T runs exist because the
transmitter only emits those. The capture was honest; the payload was
mistimed and misaligned, not damaged.

The real cause was in a dimension nobody had measured: burst structure. That
is the first entry under [[#Lessons]], and the reason the section exists.

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

- [x] `sops -e -i include/signal.h` — it is plaintext in the working tree
- [x] Capture at 869.275 MHz with the RTL-SDR, 250 kHz below the carrier
- [x] Measure 10–20 short and long pulses by hand in URH, mean per cluster
- [x] Run `analyze_capture.py` on the real capture, check it against the hand
      measurements rather than the other way round
- [x] Confirm or kill the clamping hypothesis
- [x] If confirmed: re-capture without the two-bucket classifier, rebuild the payload
- [ ] Sweep `BASE_TICK_US` from the calibration mode, find where reliability peaks
- [x] Get the beep to fire every time, in the hand, at range

Same dog as [[lora-dog-collar-telemetry]] and
[[thread-matter-noise-sensor]] — this is the only one of the three he
notices. Doing the manual measurements before running the script is
deliberate: the SDR skill is the point, and it is the same skill
[[subghz-linux-router]] Phase 1 is built on.

## Build log

Session entries live in [[subghz-collar-remote-clone-log]].
