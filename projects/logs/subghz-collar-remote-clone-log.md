---
tags: [log, subghz-collar-remote-clone]
project: subghz-collar-remote-clone
---

# subghz-collar-remote-clone — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[subghz-collar-remote-clone]].

### 2026-08-15

Picked the smallest of the three open TODOs — flashing the standalone
`src/main.cpp` build to the perfboard prototype over USB — and it turned out not
to be as small as it looked. That build had compiled since 2026-08-11 but had
never once run on hardware, carrying three sessions of RF changes that were
validated only on the ESPHome path. Two things about it needed checking before
touching the board. First, it defaults to `timingMode = 0`, the legacy engine
that samples `micros()` *after* `digitalWrite()`, so the overhead of the write
itself isn't counted toward the timing target and compounds across all 616
edges of a burst — never confirmed working, unlike the deadline engine (mode 1)
the ESPHome path uses, which fixes a single timestamp at burst start and
accumulates ideal durations from it, so a late edge only eats into its own slot
rather than the next one's. Second, the standalone path has no `feed_wdt()` call
and holds the scheduler suspended across the *entire* ~2.96 s sequence, which
looked like the exact condition that reset the ESPHome board on 2026-08-11.
Reading the C3 Arduino SDK's `sdkconfig` settled that one before any flash:
`CONFIG_ESP_TASK_WDT_CHECK_IDLE_TASK_CPU0` is unset, so the idle task — the
thing that starved on the ESPHome path and took the watchdog down with it — was
never subscribed to the watchdog in the first place. Nothing feeds it, nothing
trips it. The two firmware paths turn out to have genuinely different watchdog
exposure, not just different mitigations for the same risk, and that's now
written into the repo's `CLAUDE.md` rather than left to be rediscovered.

The thing that actually cost time was the age key. Decryption failed with
`identity did not match any of the recipients` against a key file whose public
key I'd already verified matched `.sops.yaml` exactly — which should have been
impossible, and was the tell that the key simply wasn't being loaded at all. It
was sitting at `~/.config/sops/age/keys.txt`, the *Linux* default. sops is
written in Go and resolves its default key path with `os.UserConfigDir()`,
which returns `$HOME/.config` on Linux but `$HOME/Library/Application Support`
on macOS — so on this machine sops was looking somewhere else entirely and
saying so in the least helpful way possible: its error lists only the
`SOPS_AGE_*` environment variables it checked and never names the default path,
so a correct key in the wrong place reads exactly like a missing one. Moving
the same file to `~/Library/Application Support/sops/age/keys.txt` fixed it
immediately. Confirmed the copy at the wrong path was truly redundant (same
derived public key, survivor still matches the recipient) before deleting it,
rather than leaving two copies of a decryption key on disk. That correction is
now in `CLAUDE.md` and `README.md`, in the place a fresh clone would actually
read it.

With the key resolved, the build, flash and a decrypt-verify-restore round trip
all went cleanly — `signal.h` was restored from a pre-decrypt snapshot rather
than re-encrypted, since a fresh `sops -e -i` rolls a new data key and MAC and
would have diffed against `HEAD` for identical content. Talking to the board
afterward needed a way to send commands and read the serial console
non-interactively, since `pio device monitor` is interactive and never exits on
its own. Wrote a small pyserial script instead, which was worth understanding
rather than just using. `/dev/tty.usbmodem101` isn't a UART: the C3 has a USB
Serial/JTAG peripheral built into the silicon, and with
`ARDUINO_USB_CDC_ON_BOOT=1` set, Arduino's `Serial` binds to that peripheral
directly over USB CDC-ACM (Communications Device Class, Abstract Control
Model — the USB device class every microcontroller with native USB uses to look
like a serial port to a generic OS driver, without a vendor driver). Baud is
decorative there: the `SET_LINE_CODING` control request is accepted and
ignored, because a real USB-to-UART bridge would apply it to a physical UART
that doesn't exist on this path, and the actual bytes ride bulk endpoints at
whatever the 12 Mbit/s bus has spare. DTR and RTS aren't wires either — they're
two bits in a `SET_CONTROL_LINE_STATE` request, and the C3's USB Serial/JTAG
peripheral watches them the same way a classic board's DTR/RTS-to-EN/GPIO0
transistor circuit would, which is what let the script reset the board into a
known state before each run. Also switched the script from `/dev/tty.usbmodem101`
to `/dev/cu.usbmodem101` after working out the difference: `tty.*` is the BSD
*callin* device, whose `open()` blocks until DCD (Data Carrier Detect, the
modem-control signal that historically meant "a live connection exists," and
whose loss is where SIGHUP and `nohup` come from) is asserted — meant for a
line something dials *into*. `cu.*` is *callout*, for a device the host
initiates a connection to, which is every USB serial device on a Mac without
exception. `tty.*` had been working by accident because the C3 asserts DCD
unconditionally; `pio run --target upload` picking `cu.usbmodem101` on its own
during the later rebuild confirmed it was the outlier, not the norm.

The actual A/B test came down to two questions, both answered with the collar
stationary and untouched between runs so placement couldn't confound the
result. First, mode 0 versus mode 1: 6/6 clean on mode 0, 5/6 clean on mode 1
with the standard 5 ms inter-burst gap — Fisher's exact p = 1.0, a statistical
non-result. The unobstructed, close-range geometry had too much margin to
expose mode 0's compounding error; the test confirmed both engines work
without ranking them. Defaulted to mode 1 anyway, to match the already-
validated ESPHome path rather than because it scored better, and left mode 0
reachable through the serial `m 0` command rather than deleting it. Second,
the gap itself: reading `transmitSequence()` showed `TRANSMIT_GAP_US` sits
*inside* `vTaskSuspendAll()` on the standalone path, unlike the ESPHome path
where the same constant sits outside the resume and is where `feed_wdt()`
runs — so on standalone the gap is a busy-wait yielding to nothing, with no
possible justification except an RF-side one, and the capture record already
said real presses have no gap anywhere inside a transmission. Setting it to
zero at runtime (`g 0`, no reflash) and firing six more triggers gave 6/6 beeped,
6/6 clean — 126 contiguous frames over 2.87 s, structurally the same shape as a
real button hold rather than a series of taps. That's the first direct evidence
that the collar's receiver tolerates fully continuous drive rather than needing
periodic silence to resettle, and it's evidence the RMT migration specifically
needed, since RMT's whole point is sustained output with no CPU-timed gaps.
`TRANSMIT_GAP_US` itself was left at 5000 in `signal.h` — it's shared with the
ESPHome path, where removing it reproduces the 2026-08-11 watchdog reset — so
the gapless result stays a standalone-only finding, not a payload change.

Also pinned `platformio.ini`'s `platform =` line to a specific release URL
after noticing the unpinned form silently resolves to whatever's already
installed locally rather than a fixed version, and dropped `build_flags` and
the hardcoded `upload_port`/`monitor_port` that the board JSON and PlatformIO's
own auto-detection already handle — auto-detection picked `cu.usbmodem101` on
its own, which was the check that the callout-device reasoning above was right.
Closed the session by pushing three commits, deleting the now-confirmed-
redundant key copy at the Linux path, and ticking the `Sweep BASE_TICK_US` plan
item as overtaken-not-performed, a bookkeeping correction that had been sitting
unticked since 2026-08-13.

Where this leaves it: the standalone firmware has run on hardware for the
first time and works — 18/18 beeps across the three tested configurations. Two
TODOs remain, and RMT migration is now the better-founded one to start next,
since the gapless result removes the open question of whether the collar can
tolerate sustained output at all.

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

Second session of the day, and the one that produced the captures everything
after it is measured from. It turned out to be mostly about the *receiver*
rather than the collar.

One repo change first, made before touching real data.
`tools/analyze_capture.py` could only read `rtl_sdr`'s interleaved `uint8`, and
the files this session was going to produce are int16 (URH `.complex16s`) and
float32 (GNU Radio's File Sink). Identical `I,Q,I,Q` layout on disk, different
sample type — read one as the other and you get plausible-looking noise with no
error at all. Added `--iq-format {u8,s16,f32}`. A misparse there would have been
read as a property of the signal, which is the same failure mode the synthetic-
capture validation was built to catch.

**Doing the capture in a GNU Radio GUI meant building a VM, and two of those
decisions were real ones.** Virtualization, not emulation: the host is an M1
Max and Ubuntu 26.04 LTS ships a native arm64 desktop ISO with `gnuradio`
3.10.12 and `gr-osmosdr` 0.2.6 built for it, so emulating x86_64 through QEMU's
TCG interpreter would have cost roughly 10× for nothing. The subtler one is
*which* UTM backend: Apple Virtualization and QEMU are both hardware-accelerated
on Apple Silicon — "QEMU" does not mean slow, it still runs guest ARM64 code
directly through Hypervisor.framework — but USB passthrough exists only on the
QEMU backend, and that choice can't be changed later without rebuilding the VM.
Picked QEMU, gave up Rosetta, which is worthless here.

Then didn't use the passthrough at all. RTL-SDR through QEMU's USB emulation
drops samples at exactly the rates that matter (2 MSps), so the actual path was
`rtl_tcp -a 0.0.0.0` on the Mac with the guest reaching it over UTM's shared
network at `192.168.64.1:1234`, pasted straight into the Osmocom Source's device
argument. The backend decision that looked load-bearing was insurance, not the
mechanism — worth remembering as the shape of the thing rather than as a
regret, since it cost nothing to keep the option.

Disk sizing was settled by reading the qcow2 header directly (`>IIQIIQ`
unpacked from the first 32 bytes) rather than trusting `du`: the Yocto VM's
image declares 549.8 GB virtual against ~120 GB actually consumed. qcow2 is
sparse, so a 512 GiB "disk" is a ceiling, not a reservation — but it also never
shrinks on its own, so deleting build artifacts inside a guest frees space to
the guest and not to macOS. That is the argument for the arrangement that
shipped: IQ captures live on the *host* side of a VirtFS (9p) share at
`~/UTM/sdr-captures`, so a bad capture deleted is space actually returned, and
`analyze_capture.py` reads the files in place with no copy step. Two 9p details
that bit or nearly bit: the `/etc/fstab` line got pasted into a shell because a
fenced code block made it look runnable (`Command 'share' not found`), and 9p
throughput is uneven enough that capturing 8 MB/s straight onto the share risks
a stall and a hole in the recording you'd never see — so capture to the guest's
local disk and `cp` afterwards.

Two of my UTM instructions were simply wrong and got corrected by screenshots:
the display device (the default `virtio-gpu-gl-pci` was already the right one;
`virtio-ramfb-gl` is the compatibility fallback) and the location of the USB
settings, which live under **Input**, not Sharing or QEMU, because UTM groups
the USB controller with the emulated keyboard and mouse that hang off the same
bus. The useful part of that exchange was incidental: the screenshot showed
`Use Hypervisor` ticked, which is the concrete confirmation that "QEMU backend"
here still means hardware virtualization.

`rtl_tcp` then said `No supported devices found`, and the tempting theory —
UTM had already claimed the dongle into the guest, which would make the host
lose it — was wrong. `ioreg -p IOUSB` enumerated all three of the M1 Max's XHCI
controllers with *zero* devices on any of them. Nothing was plugged in at all,
which explained the host and guest symptoms in one go. Enumerating the bus beat
reasoning about who might be holding the device.

## What IQ and gr-osmosdr actually are

Written down because the whole capture rests on it. **I = in-phase,
Q = quadrature.** Sampling an 869.525 MHz carrier directly would need 1.74 GSps
by Nyquist, so the SDR mixes it against a local oscillator at the tuned
frequency and keeps the difference — the carrier collapses to near 0 Hz and the
modulation riding on it fits in 2 MSps. But mixing down *once* destroys the sign
of the offset: +10 kHz and −10 kHz produce an identical output. So it mixes
twice, against oscillators 90° apart — `cos` gives I, `sin` gives Q — and the
pair, treated as `I + jQ`, recovers everything: magnitude `√(I²+Q²)` is carrier
strength, `atan2(Q,I)` is phase, and the rate of change of phase is the signed
frequency offset. Complex sampling is also why observable bandwidth equals the
sample rate rather than half of it, which is what `2MSps-2MHz` in the old
filenames meant. **For OOK only the magnitude matters** — the carrier is either
on or off, phase is thrown away — and that is literally one line of
`analyze_capture.py`: `np.hypot(iq[0::2], iq[1::2])`.

**gr-osmosdr** is the bridge between GNU Radio (deliberately hardware-agnostic
DSP) and real radios: an Osmocom Source/Sink pair behind one uniform interface,
where the *only* thing that changes between an RTL dongle on USB, an rtl_tcp
stream, a HackRF or a Pluto is the device argument string. That is also why a
Pluto purchase later would cost no rework.

## The three marks on the waterfall

With the flowgraph running (osmocom Source → Waterfall + Frequency sink, no
processing at all) and tuned deliberately 250 kHz low at 869.275 MHz — the
RTL2832U parks a DC spike in its exact centre bin, so a carrier captured dead
centre sits under an artefact the receiver invented, which is the flaw in the
March captures — pressing the remote produced *three* marks, not one. My first
read of the axis was also wrong: the span was ~27 kHz where `samp_rate = 2e6`
demands 2 MHz, because the `samp_rate` variable block was still at its 32k
default. Every frequency read off that plot was scaled wrong until it was fixed.

Corrected, the picture was: DC spike at 869.275, the real signal at 869.52
(+245 kHz, exactly where `signal.h` says the carrier is), a weak mark at 869.03
(−245 kHz), and a strong one at 868.53 (−745 kHz).

The proposed reading was "harmonic", and the arithmetic kills that instantly —
a harmonic is an integer multiple, so the second harmonic of 869.525 MHz is
1739.05 MHz, never a few hundred kHz away. The three real candidates are
sidebands (which *are* your signal — keying a carrier on and off smears energy
either side at multiples of the keying rate; an OOK burst that looked like one
infinitely thin line would mean nothing was being sent), an I/Q image (the
dongle's I and Q paths are never perfectly balanced, producing a ghost mirrored
about the tuned centre), and dongle spurs (fixed, and indifferent to the
button).

−245 kHz against +245 kHz is equal and opposite about the centre: that one is
the I/Q image. **−745 kHz is ≈ 3 × the baseband offset, which is the textbook
signature of third-order intermodulation** — the front end pushed out of its
linear range by a transmitter held a few centimetres away, manufacturing
frequencies that were never transmitted. It fit everything: it vanished on
button release, so the remote caused it; and it was strong, because third-order
products grow three times faster in dB than the signal producing them. Dropping
the gain and moving a few metres away made it disappear entirely while the real
burst faded gradually — the different rate of decay being the confirmation. The
general-purpose version of that test, worth more than the specific diagnosis:
**retune, and see what moves.** Real transmissions stay put on an absolute axis;
images and intermodulation products are manufactured relative to your tuning and
follow it.

This mattered for the actual goal rather than being trivia. A front end in
compression distorts pulse edges, and pulse edges to sub-microsecond precision
are the entire measurement this project needed.

## Gain, and the tuner I got wrong

RF, IF and BB are three amplifiers at three points in the chain:
`antenna → [LNA: RF gain] → [mixer] → [VGA: IF gain] → [BB] → ADC`. The tension
between them is the whole of receiver setup. **Early gain buys sensitivity** —
by Friis, noise added by the first stage is amplified by everything after it, so
the LNA dominates the receiver's noise figure and weak signals need it.
**Late gain preserves linearity** — every amplifier is linear only over a range,
and the 868.53 MHz mark was what exceeding it looks like. Distant weak signal →
more RF gain; transmitter in your hand → far less. VGA is just "variable gain
amplifier", the stage an AGC loop would normally drive, which is exactly why
Gain Mode stays **Manual** here: an AGC chasing the level mid-burst would
modulate the very amplitudes being measured.

I asserted the dongle was an R820T2, where the single tuner gain maps to RF and
IF/BB do nothing. `rtl_test -t` said **Elonics E4000** — rarer, discontinued,
52–2185 MHz with a PLL gap at 1094–1236 MHz that doesn't matter at 869 — and on
the E4000 librtlsdr's per-stage IF gain control is real, so there are two live
knobs here, not one. Gain is quantised to 14 discrete steps from −1.0 to 42.0 dB
with no zero. That correction exists only because the tuner was checked instead
of assumed.

## The capture, designed to answer a question

The observation that a held button produces repeated frames prompted a
hypothesis — the collar beeps for as long as it keeps receiving, so the remote
streams frames while the button is down. That is already what the firmware
assumes (`TRANSMIT_REPEAT` is a duration knob, not a retry count). But it has
two versions that differ in a way that matters: **purely gated**, where a quick
tap sends one or two frames, versus **fixed minimum burst**, where a tap fires a
set number regardless. One tap cannot distinguish them, so `press.cfile` was
recorded as *three separate quick taps* in one run, spaced seconds apart, so the
frame counts can be compared against each other. `hold.cfile` is one 3–4 s hold.
Designing the recording around the discriminating comparison, rather than
recording one instance and reasoning about it afterwards, is the same move that
the shock/B-channel decode plan rests on.

Both files came back at 245× and 250× peak-to-noise, better contrast than the
March captures and no clipping. Two things about them worth carrying forward:
**the first ~1 second of each file is junk** — a strong burst at 40–170 ms in
both, at near-identical positions, which is `rtl_tcp` starting to stream and the
tuner's gain settling, not the remote. And at 5 ms resolution the three taps all
landed in the same length bucket, which *hints* at the fixed-minimum-burst
version, but 5 ms blocks are far too coarse to claim it. Events: taps at 4980,
10045 and 14725 ms in `press`; one hold from 6635 to 10750 ms (~4.1 s) in
`hold`. Cut those out into `tap1/tap2/tap3.complex` (6.4 MB each) and
`hold_seg.complex` (24 MB) so URH isn't chewing on 41 million samples — same
bytes, renamed to the extension URH recognises as complex float32.

One number fell out along the way that is uncomfortable independent of the
timing question: a real tap is on air for roughly 85–137 ms, while the firmware
was sending 50 repeats, about 3 seconds. The clone transmits something like 25×
longer than the original ever does — which matters for the band's duty-cycle
limit and for how long the scheduler stays suspended.

Stopped deliberately without measuring a single pulse. The hand measurements in
URH — 15–20 individual runs recorded as raw *sample counts* rather than rounded
microseconds, cluster means rather than modes, and above all whether any 3× or
4× run exists — are the independent evidence, and `analyze_capture.py` is only
allowed to be the check afterwards.

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
