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

The full URH capture-analysis procedure — every setting, what each one
actually does, and the four traps that make them hard to get right — is
[[urh-ook-capture-analysis]].

## Now

The shock frame has a layout. Every frame this remote sends, beep and shock
alike, is **88 runs** of 1T or 2T with the levels carrying no information, and
splits as 31 preamble + 40 common + a 7-run value + a flag + the value's exact
complement + the flag repeated + one trailing short. Levels 0–7, 10, 18 and 19
are transcribed. The level-to-value map is a nonlinear lookup table — 0, 0, 1…6,
10, 101, 104 — with no formula to recover, and the flag reproduces across five
presses of one level while not being derivable from the value. A beep differs
from a shock in six run positions, two of them at the end of the common block.
Channel B is not captured yet and is the next axis. RMT migration remains the
other open item.

## Lessons

- **Polarity is not a property of a run-length OOK transmission, and
  complementing a capture cannot change its phase.** Levels alternate by
  construction — two adjacent runs at the same level would merge into one — so
  the level sequence is fully determined by the first one and carries nothing;
  all the information is in the durations. The transmitter emits those durations
  and toggles a pin, so entering the cycle one position later is a genuinely
  different waveform carrying the same code, and it is what makes a capture look
  inverted. The phase is *how many runs precede a given run*, so the fix is a
  rotation of the duration list — move the first duration to the end, re-render
  with the first run HIGH — not a complement, which moves no run boundary and
  leaves the phase exactly where it was. The detector is the parity of the count
  of unit runs before the first double. The same framing names the encoding for
  free: biphase fixes ticks-per-bit and lets the run count float, run-length does
  the reverse, and every frame here is 88 runs at 109, 111 or 113 ticks.
  [[subghz-collar-remote-clone-log#2026-09-02]]
- **A rule fitted where the high-order positions never move says nothing about
  them.** Levels 0–7 map to values 0–6, which exercise only the bottom three bit
  positions of a 7-bit field; the top four had zero observations. `value =
  level − 1`, fitted on those eight consecutive levels and tested against a
  held-out level 19, predicted 18 and got 104 — not a wrong rule so much as an
  unconstrained one, and eight consecutive small values look linear under almost
  any monotone map. Keeping one far-away capture back is what turned that into a
  one-capture falsification rather than a fifteen-capture grind. The follow-up
  test is adjacency: an intensity dial has to be smooth between neighbouring
  settings, so level 18 reading 101 is what established 104 as a real table entry
  rather than a mislabelled recording.
  [[subghz-collar-remote-clone-log#2026-09-02]]
- **A number that looks like a property of the signal is often a property of
  the tool's display.** Three of the four traps in a session of URH
  configuration had that shape. Samples/Symbol looked like a duration; it is a
  count, and the rate converting one to the other lives in a settings box, not
  in the `.complex` file, which has no header — so a 2 MSps capture read at
  URH's 1 MSps default shows every duration wrong by 2× while every sample
  count stays right. The dBm readout looked like an absolute level; it is
  `20·log₁₀(magnitude)` plus an undocumented offset, ~19 dB here, so absolute
  conversions into the threshold boxes failed twice while every *ratio* taken
  from the same figures checked out — a 12.8 dB plateau separation, and a duty
  cycle predicted to 0.16 dB that matched a bit census to a percent. The
  Demodulated view looked broken; it draws on a fixed 0–1 scale while the
  Analog view beside it auto-scales, so an envelope peaking near 0.05 renders
  as a line on the floor. The defence in each case is to carry the physical
  invariant, not the number: 208.647 µs survives a re-capture at a different
  rate, a different tool, a different day. "417" does not.
  [[subghz-collar-remote-clone-log#2026-09-01]]
- **Stacking the repeated frames validates the entire analysis chain, for
  free.** Cutting a decoded message at the frame period and checking the copies
  are byte-identical costs nothing and needs no external ground truth, yet the
  crop, the sample rate, the symbol slot, the centre and the noise gate would
  each show up as divergence between copies long before anything was visible by
  eye. Seven identical shock frames also settled a live worry — that a slot of
  417 samples against a true 417.294 would accumulate to a couple of ticks
  across a press — by showing URH slices on detected edges rather than a rigid
  grid. Same self-referential check that caught the burst-contiguity bug: ask
  whether the repeats in one recording agree with each other.
  [[subghz-collar-remote-clone-log#2026-09-01]]
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
  869.525 MHz beep was captured at 869.275 MHz — 250 kHz low — at 2 MSps in
  GNU Radio Companion running in a UTM Linux VM, since GNU Radio is not
  usable natively on the Mac, and fed from `rtl_tcp` on the Mac rather than
  USB passthrough, which drops samples at that rate. URH did the signal view,
  back on the Mac; Inspectrum was skipped because URH covers the same ground.
  Capture several presses in one recording, not one — the whole validation
  below depends on having repeats to compare.
  [[subghz-collar-remote-clone-log#2026-08-09]]
- **An overloaded receiver invents signals, and distorts the edges you came
  to measure.** With the remote held a few centimetres from the dongle and
  the gain up, the waterfall showed three marks, not one: the real burst at
  +245 kHz, its I/Q image at exactly −245 kHz (the tuner's I and Q paths are
  never perfectly balanced, so a ghost appears mirrored about the tuned
  centre), and a strong mark at −745 kHz — ≈3× the baseband offset, the
  signature of third-order intermodulation from a front end pushed out of its
  linear range. None of it is a harmonic; those are integer multiples and sit
  hundreds of MHz away. The generic test is to **retune and see what moves**:
  real transmissions stay put on an absolute axis, images and distortion
  products are manufactured relative to your tuning and follow it. So gain is
  a trade, not a level — early (LNA/RF) gain buys sensitivity because Friis
  makes the first stage dominate the noise figure, late gain preserves
  linearity — and with a transmitter in the hand you want the lowest RF gain
  that clears the noise floor, Gain Mode on Manual so an AGC cannot modulate
  the amplitudes being measured. Check the tuner rather than assuming it:
  `rtl_test -t` reported an Elonics E4000, where librtlsdr's per-stage IF
  gain is real, not the R820T2 where it is a no-op.
  [[subghz-collar-remote-clone-log#2026-08-09]]
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
- **The collar tolerates fully continuous drive, not just contiguous
  frames.** With the standalone path's inter-burst gap set to zero at
  runtime, 126 frames ran back-to-back over 2.87 s — the same shape as a
  real button hold rather than a series of taps — and decoded clean, 6/6.
  That's direct evidence against the receiver needing periodic silence to
  resettle, and it's the open question the RMT migration specifically
  needed answered, since RMT's point is sustained output with no CPU-timed
  gaps at all. [[subghz-collar-remote-clone-log#2026-08-15]]

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
| Analysis | Universal Radio Hacker | Step-by-step procedure in [[urh-ook-capture-analysis]] |
| Analysis | GNU Radio in a UTM Linux VM | Not usable natively on the Mac |
| Pipeline | `tools/analyze_capture.py` | IQ → envelope → run lengths → base tick → frame → encoding tests |
| Firmware | PlatformIO, and ESPHome for the HA path | Two paths, same signal |
| Console | pyserial against `/dev/cu.usbmodem101` | The C3 speaks native USB CDC-ACM, so the baud rate is decorative and DTR/RTS are control requests — [[usb-protocol-and-linux-stack]] |
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
- [x] Sweep `BASE_TICK_US` from the calibration mode, find where reliability peaks
      — **closed as overtaken, not performed.** Written while the timing
      hypothesis was still alive. The tick was since measured directly at
      208.647 µs frame-start to frame-start, and the real fault turned out to be
      burst structure, so there is no free parameter left to sweep. Kept rather
      than deleted because the sweep is why `signal.h` is parameterised by a
      single scalar at all, and that refactor is what made the timing hypothesis
      testable in seconds. [[subghz-collar-remote-clone-log#2026-08-13]]
- [x] Get the beep to fire every time, in the hand, at range

Same dog as [[lora-dog-collar-telemetry]] and
[[thread-matter-noise-sensor]] — this is the only one of the three he
notices. Doing the manual measurements before running the script is
deliberate: the SDR skill is the point, and it is the same skill
[[subghz-linux-router]] Phase 1 is built on.

It is also where [[embedded-learning-curriculum]] gets most of its evidence.
URH reporting 400 samples per symbol against a true 417.75, and the capture
damage hypothesis that fitted everything on screen and died to a hand
measurement, are what that note's argument about measurement rests on — and
the reason the RF course is ordered first there.

## Build log

Session entries live in [[subghz-collar-remote-clone-log]].
