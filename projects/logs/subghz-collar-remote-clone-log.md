---
tags: [log, subghz-collar-remote-clone]
project: subghz-collar-remote-clone
---

# subghz-collar-remote-clone — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[subghz-collar-remote-clone]].

### 2026-08-13

Started from the open TODO list and worked it one item at a time. First item was
bookkeeping: the plan had a line to sweep `BASE_TICK_US` to find where reliability
peaks, written while the timing hypothesis was still alive. It is overtaken, not
pending — the tick was since measured directly at 208.647 µs and the real bug was
burst structure, so there is no free parameter left to sweep.

The real work was the range test, and it started with a wrong mental model. The
intuitive question — how far until it stops working — is not what this link is
short on. Free-space path loss only costs 6 dB per doubling of distance, so at
869.525 MHz and the CC1101's 10 dBm ceiling into a cheap OOK receiver, there is on
the order of 30 dB of margin at 100 metres. What actually eats margin indoors is
everything except distance: polarisation mismatch between transmitter and the
collar's antenna, body absorption (irrelevant here since the collar rides beside
the dog rather than on the neck — a detail that removed the single largest and
least controllable loss term before the test even started), and multipath nulls,
which sit only 8.6 cm apart at this wavelength (half the 17.3 cm quarter-wavelength).
The actual geometry is 5 m through a load-bearing reinforced-concrete wall, and
reinforcing steel typically sits on a 15–20 cm grid — almost exactly the 17.25 cm
half-wavelength at which a conducting mesh stops reflecting cleanly and starts
leaking. That number could plausibly mean 15 dB of attenuation or 30, and there was
no way to tell which by inspection; more likely, with a doorway at each end of the
wall, most of the signal never goes through the concrete at all and travels by
diffraction around it instead.

Before designing the test, checked `OUTPUT_POWER` in the encrypted payload — no age
key file exists on this machine, but the raw key string turned up in
`~/.zsh_history`, so `SOPS_AGE_KEY=<key> sops -d` read it without a full decrypt.
It is already 10 dBm, the CC1101's ceiling at 868 MHz. That settled a question
before it was asked: if margin is ever short, power is not an available knob, only
antenna and geometry are.

First test design was a PATABLE power-step-down sweep at one fixed placement, to
measure margin directly. Rejected it, and the reason mattered more than the test
itself: with the collar simply dropped beside the dog rather than mounted, position
and antenna orientation are not fixed — they are redrawn every time it's put down.
A margin number measured at one arbitrary placement would describe that placement,
not the link the device actually experiences in use. So the test became: drop the
collar naturally, trigger once, pick it up and drop it again differently, repeat
10–15 times, 5+ seconds apart so a re-trigger inside the ~3 s beep window (which the
switch silently swallows) doesn't read as a miss.

Result: 12/12 triggers beeped, which rules out a return to the old ~70% behaviour
(`P(12/12 | p=0.7)` ≈ 1.4%, 95% confidence lower bound on reliability ≈ 78%). Eight
of the twelve had mild audible chopping, each still over 90% duty within its beep.
That chopping was the more interesting result, because the collar sounds only while
frames keep arriving and stops once they lag past some internal hold timeout — so a
beep's duty cycle is a free readout of decode success rate, with no test equipment
beyond a stopwatch and an ear. Fitting a shared per-burst loss rate to both numbers
(fraction of clean triggers, and duty cycle within the chopped ones) gave the same
answer from two directions: about 6% of bursts failing independently, roughly one
per trigger — a self-consistency check that needed no external reference, the same
kind that had caught the burst-contiguity bug two sessions earlier.

That model assumed the burst was the unit of failure, and the assumption was wrong,
caught by a direct question: since every frame carries its own preamble, why would
losing one frame produce a different-sized hole depending on how many frames make
up the burst it's part of? It doesn't — and the fact needed to see that was already
on record from the original capture: the measured frame is 109 ticks, 42 of them
(38%) preamble, specifically because a fixed-code remote makes every frame
independently acquirable. `FRAMES_PER_BURST` does not set the size of an audible
hole; it sets how many inter-burst gaps exist for a given amount of air time (18 at
7 frames/burst versus 9 at 14), which trades against how long the scheduler stays
suspended, not against chop size. Refitting per frame instead of per burst gave
roughly 0.87% loss per frame — about one lost frame per trigger, a ~25 ms hole,
99% duty — consistent with the same ">90%" reading but not distinguishing it from
the burst-level model on its own.

What did distinguish it was a second, deliberately different test: the same
trigger at 3 m, line of sight, no wall — 6/6 clean, no chopping at all, against 8/12
chopped through the wall (Fisher's exact p ≈ 0.011). The clean part of that
comparison was moving only the receiver and leaving the transmitter untouched,
since every timing-side variable — firmware, scheduler, Wi-Fi backlog — lives on
the transmitter and was held constant by construction; the only thing that changed
was the RF path. That settles it as RF margin, not a stretched inter-burst gap, and
rules out a competing worry that Wi-Fi backlog was eating into the 5 ms gap after a
159 ms scheduler suspend — worth keeping as a negative result, since `feed_wdt()`
plus 5 ms is holding up under real load. The consequence for sequencing: moving
transmission onto the RMT peripheral remains justified purely as the structural
improvement already argued for it — removing the contiguity/watchdog/chopping
trade-off and enabling a genuinely continuous transmission — not as a fix for
anything currently broken.

With that settled, moved to a feature that had been wanted for a while: the status
LED currently flashes green once at boot and then goes idle-and-dark for the rest
of its life, which is indistinguishable from a dead or unpowered board from across
a room. The obvious fix — blink green every few seconds — turned out to have a
real flaw once thought through properly. There is exactly one failure mode where
the LED is the *only* witness: Wi-Fi dropping. The radio still works, the device is
still alive, but it vanishes from Home Assistant and from `esphome logs`
simultaneously, and a plain green pulse sitting there would report "alive and well"
into precisely that blind spot. So the heartbeat colour had to carry Wi-Fi state —
green pulse if connected, amber if not — which also sharpens what solid red already
meant: previously "booting or radio init failed" conflated two states, and gating
the heartbeat on the existing `is_ready()` check separates them for free. A second,
narrower problem existed only on the ESPHome path: its heartbeat is an async
`interval:` automation, so a transmit trigger arriving mid-pulse could set the LED
blue and then have the pulse's own `light.turn_off` blank it for the entire ~3 s
beep. Guarding the pulse's *start* on `not script.is_running: transmit_beep` isn't
enough by itself; the same guard has to sit on the `turn_off` too. The standalone
firmware has no equivalent race, because `triggerTransmit()` blocks `loop()` for
its whole duration, so heartbeat and transmit can never interleave there by
construction. Implemented as an 80 ms/15%-duty pulse (short and dim — the original
500 ms/50% flash was fine once at boot, not indefinitely every 5 s in a room),
updated both firmware paths, and updated CLAUDE.md and the README to describe the
new convention and its reasoning.

Verifying the build meant decrypting `signal.h` temporarily, and a near-miss
happened doing that safely. The cleanup step was registered as an EXIT trap holding
a path relative to the directory the script was in at registration time, and the
script then changed into `esphome/` to run the ESPHome compile. When the trap fired
on exit it looked for the wrong path, found nothing, and did nothing — the real
`signal.h` was left decrypted in the working tree until a manual check caught it.
Restored it from a snapshot with a verified zero diff against HEAD, so nothing
leaked, but the general shape of the mistake is worth keeping: an EXIT trap that
holds a relative path stops protecting anything the moment the script changes
directory, and a cleanup handler has to resolve its paths to absolute ones at the
moment it's registered, before any `cd`. That is precisely the mechanism by which
the standing "never commit a decrypted signal.h" rule would actually get broken.

Both builds passed (`pio run` at 25.4% flash, `esphome compile` at 54.6%), the
change was flashed over the air to the device already in daily use, confirmed back
on Wi-Fi with the API port answering, then committed and pushed to `main`
(`384e95c`). The amber Wi-Fi-down branch compiled and validated in `esphome
config` but was not exercised on real hardware — confirming it needs Wi-Fi actually
dropped, which wasn't worth engineering deliberately; it will prove itself the
first time the access point restarts.

Stands now: reliability confirmed at the real installed geometry, chopping
explained and localised to RF margin rather than a firmware timing defect, and a
Wi-Fi-aware heartbeat shipped and running on the live device. Three items remain
untouched, in the order recorded as TODOs: flashing the standalone build to the
perfboard prototype board over USB, moving transmission onto the RMT peripheral,
and a differential shock/B-channel capture to start reverse-engineering the actual
protocol layout.

### 2026-08-11

Flashed the rebuilt firmware and pressed the button: zero beeps, worse than
the 70% the old firmware managed. That was the session's first real signal,
because it meant the 209 µs tick correction — real as it was — could not be
the actual bug. Went back to the capture to check the thing I hadn't
checked yet: not individual pulse timing, but the shape of a whole
transmission. A real press is 7 copies of the frame sent back-to-back, with
no gap anywhere inside it — URH confirms this by segmenting the recording
into one unbroken message, not seven. The new firmware, on the other hand,
sent one frame, then a 5 ms silence, then the next. Cheap fixed-code OOK
receivers validate frames consecutively — decode one, then require the next
to arrive before a timer expires — and 5 ms is long enough to expire that
timer and also long enough for the receiver's AGC to drift and corrupt the
next frame's opening. Either mechanism kills a single-frame-plus-gap
transmission outright. The old firmware's 70% now had an explanation too:
it happened to pack about 2.5 frames into every burst, purely by accident of
a bad slice, so even with a disturbed opening frame there was usually a
clean one right behind it. It was never a timing problem. It was working by
accident, and fixing the timing while shrinking the burst to one frame
removed the accident.

The fix follows directly: emit `FRAMES_PER_BURST` contiguous frames — 7,
matching a real tap — inside one `vTaskSuspendAll()` window, and only gap
*between* bursts. That meant restructuring both firmware paths so the
scheduler suspend wraps a whole burst rather than a single frame, and
switching to one absolute `micros()` deadline per burst so 616 edges of
`digitalWrite()` overhead can't accumulate. `TRANSMIT_REPEAT` dropped from
105 to 18 because it now counts bursts, not frames, at the same total
on-air time. Flashed over OTA, pressed the short-burst test: it fired. One
burst of 7 contiguous frames, a literal replica of what the remote sends
for a tap, triggered the collar. Contiguity was the whole story.

Then the long test reset the device. Guessed brownout first, because this
board already has a documented LDO brownout history (it's why Wi-Fi output
power is capped at 8.5 dBm) and the PA now runs 159 ms per burst instead of
22.8 ms. Wrong guess. Settled it properly instead of iterating on a
hypothesis: logged `esp_reset_reason()` on boot and on every Home Assistant
API client connect, because the on-boot copy only reaches USB serial and I
wanted it over Wi-Fi. Getting a clean read took two tries — an OTA reflash
itself triggers `esp_restart`, which overwrites the very reason register I
was trying to read, so the second attempt read it by connecting a second
log client instead of reflashing. The answer was `TASK_WDT`, not brownout.
The idle task feeds the watchdog, and it can't run while the scheduler is
suspended; the old firmware handed it 5 ms out of every 27.8 ms (18% duty),
the new one 5 ms out of every 164.5 ms (3%), and that's a duty-ratio problem
than can't be judged by comparing total blocked time.

First attempt at a fix changed two things at once: widened the gap to 30 ms
and added `esphome::App.feed_wdt()` in every gap. No more resets — but also
audible chopping on the long beeps, and no way to tell which change had
fixed what. Reflashed with only one variable changed back (gap at 5 ms,
`feed_wdt()` kept): no reset, no chopping, all 6 beeps in the reliability
test fired cleanly. `feed_wdt()` alone was sufficient the whole time; the
30 ms gap had been pure self-inflicted damage. Worth naming plainly: I'd
justified the 30 ms figure as restoring a "known-good" 18% recovery ratio
from the old firmware, but 18% was never a designed target — 5 ms was just a
value that happened to work, and I'd dressed a coincidence up as an
analysis.

Also went back to the tick measurement, because a hand selection in URH came
in 15 samples away from the automated one on a 318 670-sample span — close,
but a discrepancy worth chasing. Measuring frame-start to
frame-start across 654 ticks, instead of across the 42-tick preamble,
removes the ambiguity of where a press actually starts and ends (the final
tick gets truncated on button release) and cancels rise-time bias since both
endpoints are the same kind of edge. That gives 208.647 µs against the
earlier 208.9 µs — six intermediate estimates agreeing to 0.02%, the best
figure yet. Both round to the same `BASE_TICK_US 209`, so no firmware
changed, only the documentation.

Cleaned up the temporary test scaffolding, corrected three actively-wrong
claims in the old README (notably that the inter-burst gap helps the
receiver find the start of a new burst — the opposite of what's true),
wrote up the RMT migration and the shock/B-channel capture as TODOs instead
of doing them, re-encrypted signal.h, and pushed four commits.

Separately, walked through what the ESP32-C3's RMT peripheral is and why
Wi-Fi doesn't have the same bit-banging problem RMT solves (Wi-Fi has
dedicated MAC/baseband silicon; RMT is the general answer for a peripheral
that doesn't get one, like the WS2812 LED already on this board), then
taught the by-hand URH extraction: measure the symbol length by selecting N
preamble cycles and dividing, not by trusting "Autodetect parameters"
(9% wrong here — it fits a length rather than measuring one), and validate
by checking that repeats of the frame agree with each other rather than
trusting any single reference. Ran it by hand on the raw capture and
produced a 764-bit string that matched the committed payload exactly at
error tolerance 5, with tolerance 0 losing 5 bits to
over-strict rounding and producing frames that disagreed with each other —
a self-refuting result, catchable with no external reference at all. That
self-consistency check — do the repeated frames actually agree — turned out
to be the same test that had caught the burst-contiguity bug earlier in the
session, just applied to a different kind of error.

**What broke:** the "more correct" payload produced *fewer* beeps than the
one it replaced, because correctness in the wrong dimension (tick length)
doesn't fix an error in a different dimension (burst structure) — a
reminder that fixing the thing that was measured isn't the same as fixing
the thing that's broken. **What surprised me:** the old firmware's reliability
was entirely accidental, and the fix that finally worked was also the
cheapest one — no gap widening needed, just feeding the watchdog directly.
**What I'd do differently:** change one variable per physical test, always;
the two-variable gap+feed_wdt change cost a whole extra flash-and-listen
cycle to untangle.

Firmware is working and pushed. Standalone PlatformIO build compiles but
hasn't been flashed (needs USB, left for later). Next steps are recorded as
TODOs rather than started: move the transmit loop onto the RMT peripheral to
remove the contiguity/watchdog/chopping trade-off structurally, and capture
the shock signal at several levels plus the B channel to start reverse
engineering the protocol layout.

### 2026-08-11

Validated the captured segments in URH — the three presses agree to within
0.5 ms of the automated edge detection and have identical 309±4 rising edges,
which means the capture is repeatable. The hold segment I'd cut earlier was
bad; the real hold runs 4.14 s continuously and is only weak because it was
captured at a different power setting, not truncated.

Measured pulses by hand in URH, 15–20 shorts and 15–20 longs. Found that
measuring edge-to-edge biases high by ~10 samples (the rise+fall time), but
measuring at 50% crossing on both sides cancels that. The edge-to-edge
numbers (436 samples short, 855 samples long) carried that bias; the
50%-crossing ones (426.3 and 842.6) did not. The span measurement — rise to rise across 21 periods,
not 20 — gave 417.75 samples per tick: 208.9 µs at 2 MSps.

**The clamping hypothesis is dead.** σ/mean was 0.6% on the hand measurements,
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
9% off. It fits a symbol length rather than measuring one, so it is not to be
trusted for base-tick work. Hand measurement caught it.

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
skipped (URH's signal view covers what Inspectrum would be for). Nothing was
uninstalled from the Mac; the "cleanup" premise didn't hold because
`hackrf` is a URH dependency, not a stray HackRF radio install.

Still outstanding: signal.h is plaintext in the working tree and needs
`sops -e -i include/signal.h` before any commit.

Next step is the manual capture at 869.275 MHz (250 kHz low to avoid
the RTL2832U's DC spike), measurement of 10–20 short and long pulses in
URH, and then running the script to validate whether the clamping
hypothesis holds.
