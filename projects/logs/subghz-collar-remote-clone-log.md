---
tags: [log, subghz-collar-remote-clone]
project: subghz-collar-remote-clone
---

# subghz-collar-remote-clone — build log

Session entries, newest last. Written by the SessionEnd hook.
The project note is [[subghz-collar-remote-clone]].

### 2026-08-09

Created a CLAUDE.md for the codebase and fixed three documentation bugs in
esphome/CLAUDE.md (frequency was listed as 433 MHz not 869.525 MHz,
pinout.h was claimed to be encrypted when it isn't, and TRANSMIT_GAP_US was
missing from the macro list).

Then attacked the core problem: the beep signal only triggers 70% of the
time on both firmware paths. Decrypted the payload to find every one of 224
elements was exactly 200 or 400 µs — a real SDR capture never looks that
clean. Tested the payload against five different line encodings (PWM,
Manchester, biphase FM0/FM1, PPM, NRZ) and none fit, plus the run lengths
cap at 2 ticks which has no standard explanation. This pointed strongly at
a two-bucket short/long classifier during capture; symbols are missing from
the frame and no base-tick tuning would fix it.

What surprised me: the payload's extreme regularity looked like a
deliberate encoding until I generated synthetic captures and verified the
tests. The real surprise was negative — not a single test expected to pass
actually did. That ruled out an entire category of problems and pointed
directly at capture damage.

Made the decision to refactor signal.h from absolute microseconds to
run-length ticks plus a BASE_TICK_US constant. This trades complexity (now
the payload is `tick × {1,2}` plus one scalar) for tractability (the scalar
can be swept at runtime without reflashing, which is the only way to find
whether 200 µs is actually wrong). Verified the refactor lossless
by round-trip and added a serial calibration mode to src/main.cpp. Both
builds pass.

Built tools/analyze_capture.py to take raw rtl_sdr IQ and run the entire
pipeline: envelope, run-length detection, base-tick recovery, frame
segmentation, and all encoding tests. Tested it against two synthetic
captures with known ground truth (208 µs base tick, PWM and NRZ data) and
caught three bugs: false clamping warnings on healthy PWM data, run
clustering that collapsed 4+5 ticks into a bogus "4.44x" group, and frame
splitting that invented phantom frames on an 8-tick gap.

Decided to do the measurements by hand first — capture with rtl_sdr,
measure individual pulses in URH, calculate the mean of each cluster — then
validate with the script. That is worth more than just running the tool,
since the point of this one is building SDR expertise.

Chose GNU Radio (via UTM Linux VM) + URH for the SDR work. Inspectrum was
skipped (URH's signal view covers what you'd need it for). Nothing was
uninstalled from the Mac; the "cleanup" premise didn't hold because
`hackrf` is a URH dependency, not a stray HackRF radio install.

Still outstanding: signal.h is plaintext in the working tree and needs
`sops -e -i include/signal.h` before any commit.

Next step is the manual capture at 869.275 MHz (250 kHz low to avoid
the RTL2832U's DC spike), measurement of 10–20 short and long pulses in
URH, and then running the script to validate whether the clamping
hypothesis holds.

### 2026-08-11

Validated the captured segments in URH — your three presses agree to within
0.5 ms of my automated edge detection and have identical 309±4 rising edges,
which means the capture is repeatable. The hold segment I'd cut earlier was
bad; the real hold runs 4.14 s continuously and is only weak because it was
captured at a different power setting, not truncated.

Measured pulses by hand in URH, 15–20 shorts and 15–20 longs. Found that
measuring edge-to-edge biases high by ~10 samples (the rise+fall time), but
measuring at 50% crossing on both sides cancels that. Your individual numbers
(436 samples short, 855 samples long) had that bias; mine (426.3 and 842.6)
were at the crossing. The span measurement — rise to rise across 21 periods,
not 20 — gave 417.75 samples per tick: 208.9 µs at 2 MSps.

**The clamping hypothesis is dead.** σ/mean was 0.6% on your measurements,
and three of four automated run clusters had σ ≈ 0.5 samples. Only 1T and 2T
runs exist and that's a genuine property of the transmitter, not damage. The
capture is honest.

Discovered that press2 was the exact complement of press1 rotated one tick —
same run-length magnitudes (200/200 at run offset 87 in an 88-run frame),
but opposite carrier assignment. This isn't a rotation of the tick string
(that wouldn't be a complement); it's a shift in the run sequence — the
transmitter emits durations and toggles a pin, so entering one position later
keeps every duration while flipping the carrier state on each interval. It's
a genuinely different physical transmission but decodes to an identical frame
downstream, which is why the collar accepts both.

Tested the toggle hypothesis with a 10-press capture: polarity sequence was
`A B A A A B A B A B`, no alternating discipline. Across all 13 presses in
three recordings: 8 A, 5 B. The remote emits both phases randomly (or from
some internal state I couldn't determine), but they carry the same code.

Identified that frame A (press1/press3) is the true phase: 88 elements, even
count, starts +1 ends −2, and repeats tile back-to-back without merging runs.
Frame B (press2, the odd-count 89-element version) is a phase shift artifact.

Rebuilt signal.h from the measured frame: `BASE_TICK_US 209` (was 200),
`SIGNAL_BEEP_TICKS` = clean 109-tick frame A (was 273-tick misaligned),
`TRANSMIT_GAP_US 5000` (was variable), `TRANSMIT_REPEAT 105` (was 50, adjusted
to keep ~2.9 s on air).

Fixed esphome/cc1101.h to read the gap from `TRANSMIT_GAP_US` instead of
hard-coded `delay(5)`. Split the gap into whole milliseconds via `delay()`
(which yields to the scheduler) and the sub-millisecond remainder via
`delayMicroseconds()` (which busy-waits). When the gap is 0, it yields
instead — getting this wrong would have turned ESPHome's Wi-Fi servicing
window into a 5 ms spin.

**Broke:** URH's *Autodetect parameters* reported 400 samples/symbol, which was
9% off. It fits a symbol length rather than measuring one, so do not trust it
for base-tick work. Hand measurement caught it.

**Surprised:** The whole capture was clean. Every run quantised at the true
417.75-sample grid, 0% off-grid across 13 presses. If the clamping hypothesis
had been right, I'd expect rounding errors scattered through the frame, not
a perfect fit. The stored payload wasn't damaged; it was mistimed and misaligned.

Created a temporary test build for ESPHome only (the standalone path is
cleaner): 3 short beeps followed by 3 long beeps, each independent, 1 s gap,
~13 s total. That's a 6-event reliability sample per trigger instead of 1.
Marked TEMPORARY in the code so removal is a clean delete.

**Still untested against the collar.** Everything is verified against
captures and compilers, but the reliability claim is unverified. The next
step is to flash and listen — does it reliably beep now? Both firmware
paths compile. signal.h is still plaintext and needs `sops -e -i` before
any commit. Documentation (CLAUDE.md, README.md) is stale and should update
once the collar confirms the change works.
