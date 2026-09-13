---
tags: [log, subghz-collar-remote-clone]
project: subghz-collar-remote-clone
---

# subghz-collar-remote-clone — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[subghz-collar-remote-clone]].

### 2026-09-13

The session where the RMT code finally met hardware. It worked, on both paths, on
the first flash — and then almost everything else the day produced was the same kind
of finding: a constant that had outlived the thing that justified it and gone on
being obeyed.

**The bring-up observation was not RF, and it proved itself.** The plan was to check
that the LED still lights and that `rmt_beep::init()` returns `ESP_OK`, because those
two together settle the whole stack the migration rests on: the group clock source,
the group prescale and the channel count. The LED claims the RMT group first — not at
`strip.begin()`, which touches no peripheral, but at the first `strip.show()`, since
`Adafruit_NeoPixel` calls `rmtInit()` lazily from inside `espShow()` — and asks for
`RMT_CLK_SRC_DEFAULT` at 10 MHz, which settles the group on APB with prescale 1.
`rmt_beep::init()` then asks for APB and `RMT_RESOLUTION_HZ` into a group whose clock
and prescale are already frozen, and each way it could fail has its own code: a source
mismatch is `ESP_ERR_INVALID_ARG` ("group clock conflict"), a missing memory block is
`ESP_ERR_NOT_FOUND`, and a prescale other than 1 puts the channel divider somewhere
other than 214. The serial log started after the boot lines had scrolled past, which
turned out not to matter: both init failures end in `while (true)` behind a red LED,
so reaching `System Ready` at all is the proof. Then the collar, 6/6.

**The transmit window is a clock measurement, not a formality.** `TX ...` to `TX done`
spanned 3.002 s against a predicted 3.00206 s, inside the 1 ms granularity of the
monitor's timestamps. That elapsed time is `frames x 109 x k / f_channel` with every
term known except the last, so it reads the achieved clock back off the board: a
channel divider of 107 would have shown 1.5 s and a group prescale of 2 would have
shown 6 s. The divider is 214 at runtime, not merely by inference from what the LED
asked for. The busy rejection is as clean: a press at 1.096 s into a beep was dropped,
and `TX done` still arrived 3.002 s after the *start* rather than after the press, so
nothing was queued, restarted or extended.

**The figures the firmware prints cannot be the seam reference.** `frame_duration_us()`
does the division last-but-one and truncates — 8502 ticks x 2.675 us is 22742.85,
printed as 22742 — and `beep_duration_actual_us()` then multiplies that already
truncated value by 132. The error accumulates to 112 us over a 3 s beep, which is
37 ppm: larger than the +14.38 ppm the symbol period itself carries, and therefore
larger than the effect the seam measurement exists to look for. Harmless as a display
and disqualifying as a reference, which is an easy distinction to miss when the number
is right there in the log.

**A yield for a call that no longer blocks.** The ESPHome path fired with a constant
half-second lag the standalone path did not have, and a constant lag is the signature
of a fixed script step rather than scheduler jitter. It was `delay: 500ms`, commented
as letting ESPHome "physically push the Blue color to the LED" — a yield, not a settle.
ESPHome's light component does not write the LED inline; it sets a target state and the
RMT write happens on a later main-loop pass. Under the bit-banged firmware the very next
step took the main loop away for the whole burst under `vTaskSuspendAll()`, so without
that delay the blue would not have appeared until after the beep. `begin_transmission()`
now returns in about 5 ms and the step after it is `wait_until`, which suspends the
script and hands control back, so the light component gets loop passes throughout the
3 s beep and the write lands within one iteration. Deleting the step cost nothing and
returned half a second between the press and the air. Nothing announced that the
workaround had become redundant; the migration that made it redundant is what wrote the
code that made it invisible.

**The amber that was never amber.** The Wi-Fi-down heartbeat read as dim red on the
bench, which looked like a colour-choice problem and was not. ESPHome emits
`(raw x max_brightness x local_brightness) ^ gamma` and applies brightness *linearly to
the 8-bit channel* before the gamma lookup, so brightness selects the index into a table
whose bottom entries are crushed. At `brightness: 15%` local brightness is 38: red 1.0
gives 255, `scale8(255,38)` = 38, table[38] = 317, `(317+128)/257` = **1**; green 0.35
gives 89, `scale8(89,38)` = 13, table[13] = 16, `(16+128)/257` = **0**. The pulse emitted
`(1, 0, 0)` — pure red at one count out of 255, with the green channel quantised away
before it reached the LED. Amber had never once been on screen, and `gamma_correct: 2.8`
appears nowhere in the YAML: it is ESPHome's default, inherited silently, and visible
only in the generated `main.cpp`. The tempting fix was to drop to two colours, which
would have adopted the artefact as the design and discarded the one thing the LED reports
that nothing else can — a dropped Wi-Fi link, where the device is alive and transmitting
but invisible to Home Assistant and to `esphome logs` alike.

Gamma attacks the ratio as well as the level, which is the half that is easy to miss: at
2.8, green 0.35 against red 1.0 emits 0.05 and still reads red, and even at generous
brightness it never becomes amber. Raising brightness alone would not have fixed it.
The choice was between raising both numbers under the curve and removing the curve, and
removing it won: gamma correction exists to make a *dimming sweep* perceptually smooth,
this LED shows three fixed colours and never sweeps, so the curve bought nothing and
cost the entire bottom of the range. With `gamma_correct: 1.0` a brightness percentage
is very nearly the emitted fraction and a colour ratio survives at any level. The
percentages were then rescaled so that removing the curve changed no emitted level
except the broken one — 50% to 20% and 80% to 20% stay within a count of where they
were, while the heartbeat went from 1 to 23, which is exactly what the standalone path
emits from `120` through `setBrightness(50)`.

**What is worth sharing, and the criterion that decides it.** Three things moved into
shared headers. `include/cc1101_config.h` holds the six RadioLib calls — frequency,
power, bit rate, RX bandwidth, OOK, standby — that had been duplicated verbatim in both
paths, with carrier and power as parameters defaulting to `signal.h` so the standalone
serial sweep still works. `include/reset_reason.h` turns `esp_reset_reason()` into a
string for both; the standalone path had never reported it at all, which is backwards
given that it is the path used for development. `include/led_policy.h` states the
palette as levels *emitted* by the WS2812, that being the only unit the two paths share:
ESPHome applies a float multiplier to float ratios, `Adafruit_NeoPixel` an 8-bit scale to
8-bit components, so a percentage means different light in the two and a level does not.
Consuming it made `strip.setBrightness(255)` the right call, which disables Adafruit's
scaling rather than maximising it — `b + 1` rolls a `uint8_t` to 0 and `show()` skips the
scaling pass at 0 — so components are now written literally and there is one scaling step
instead of two.

The LED *policy* was deliberately not shared, and working out why produced the more
useful result. ESPHome accepts `!lambda` on `brightness`, on the colour channels and on
`delay:`, all verified by putting one in and validating; it refuses one on `interval:`
with a flat "This option is not templatable!". So the coverage available is exactly
inverted. The three fields that can be shared are the ones whose divergence announces
itself — a wrong colour is visible the first time anyone looks at the board, which is
the LED's whole job — and the one that cannot be shared is the only one whose divergence
is invisible, since two devices pulsing at 5 s and 7 s look identical unless they are
side by side. That is the opposite of the case for `cc1101_config.h`, where a wrong
bandwidth cannot be seen without a range test. So the header is the specification, the
standalone path consumes it, and the YAML repeats the numbers as literals and cites it;
the enforcement is a comment rather than a compiler, which is acceptable only because
this particular failure reports itself.

**Housekeeping that nearly went wrong.** `include/signal.h` turned up in the diff with a
fresh data key, a fresh MAC and `lastmodified` a few minutes old — a full-file diff with
byte-identical plaintext, which is what a `sops -e -i` round trip always produces. It was
caught before the commit and reverted to HEAD's blob, and the plaintext had been verified
identical against a decrypt of HEAD beforehand. The pre-decrypt snapshot that would have
made this a non-event was never taken, which is the second time that step has been the
one skipped.

### 2026-09-12

The session that closed the last open question and then wrote the code. Three
things came off the list before implementation — what the C3 does when the loop
count is reached, and the two timing relations in TRM chapter 33 that had never
been checked against the chosen clocks — and a fourth, which was not on the list
at all, turned out to overturn a decision that had been treated as settled since
2026-09-10.

**The loop count reports; it does not stop.** `soc/esp32c3/include/soc/soc_caps.h`
defines `SOC_RMT_SUPPORT_TX_LOOP_COUNT 1` and says nothing at all about
`SOC_RMT_SUPPORT_TX_LOOP_AUTO_STOP`. In `esp_driver_rmt/src/rmt_tx.c` the outer
`#if SOC_RMT_SUPPORT_TX_LOOP_COUNT` compiles the loop-end handler in, and the
inner `#if !SOC_RMT_SUPPORT_TX_LOOP_AUTO_STOP` is a negation of an *undefined*
identifier, which the C preprocessor evaluates as `!0` — so the workaround branch
is live, and it calls `rmt_ll_tx_stop()` under a comment admitting that "some rmt
symbols have sneaked out". That settles the design question the manual could not:
`RMT_CHn_TX_LOOP_INT` fires, software stops the channel, and the number of frames
actually emitted is the requested count plus however long the interrupt took to be
serviced. The transmission can therefore be cut mid-frame. Worth carrying past this
project: `#if` on a macro that does not exist is not an error, it is zero, which is
what makes the idiom work and also what would make a misspelled capability macro
silently take the "unsupported" branch.

**Where the pin rests after an abort, and the step I stopped one short of.** My
first answer was that the level is user-configurable, pointing at `eot_level` in
`rmt_transmit_config_t` and `init_level` in the channel config. True of the config
struct, and it did not answer the question, which was about an abort rather than a
clean end. The mechanism is at `rmt_tx.c:759`:
`rmt_ll_tx_fix_idle_level(hal->regs, channel_id, t->flags.eot_level, true)` — that
last argument sets `RMT_IDLE_OUT_EN_CHn`, so the driver never takes the TRM's other
option of reading the level from the end marker. The resting level is a register
override applied whenever the channel is not transmitting, which is exactly why it
survives being stopped in the middle of a HIGH run. Had the driver passed `false`
there, an abort mid-frame would have left GDO0 high and the CC1101's power
amplifier gated on — an unmodulated carrier on 869.525 MHz until something else
touched the pin.

**The two arithmetic checks, and a direction I had backwards.** Equation 33.2 is
`1.5 x Tapb < 9 x Trmt_sclk`; substituting periods for frequencies gives
`f_rmt < 6 x f_apb`. That is an **upper** bound on the RMT working clock, not a
lower one: it stops the counting side outrunning the APB side that feeds it, so
dividing down — which is all the k-table work ever did — can never violate it. The
standalone pairing (XTAL 40 MHz against APB 80) clears it 12x, and the ESPHome
pairing is degenerate, since rmt_sclk *is* APB and the inequality reduces to
`f < 6f`. Equation 33.3, against run 87, is `10 x Tapb + 19 x Trmt_sclk` — 600 ns
on the XTAL pairing, 362.5 ns on the APB one — against 78 ticks of 2.675 us, which
is 208.65 us. Margins of 348x and 576x. Both relations get *easier* as rmt_sclk
speeds up relative to APB, because they bound a cross-domain handshake; the
intuition that a faster clock is the risky choice is the wrong way round here.

**Why the two paths were about to use different clocks, and why they must not.**
The 2026-09-10 clock chain had the standalone path on XTAL with `DIV_CNT` 107 and
the ESPHome path on APB with `DIV_CNT` 214, on the reasoning that the LED claims
the group clock under ESPHome and the standalone path has the peripheral to
itself. That second half was never checked and is false. `Adafruit_NeoPixel` does
not bit-bang on ESP32: `esp.c:81` calls
`rmtInit(pin, RMT_TX_MODE, RMT_MEM_NUM_BLOCKS_1, 10000000)`, the Arduino wrapper at
`esp32-hal-rmt.c:587` sets `tx_cfg.clk_src = RMT_CLK_SRC_DEFAULT`, and
`clk_tree_defs.h:188` defines that as APB on the C3. Meanwhile `rmt_common.c:199`
stores the first channel's source on the *group* and returns `ESP_ERR_INVALID_ARG`,
"group clock conflict", for any later mismatch. So asking for XTAL on the standalone
path would have hard-failed whichever channel was created second — and `rmtInit` is
called lazily from inside `espShow()`, meaning on the first `strip.show()` rather
than at `strip.begin()`, so which one lost would have depended on runtime flow. The
worst possible shape for a failure.

The only thing XTAL bought was immunity to APB moving underneath a transmission,
and that is moot three times over: `CONFIG_PM_ENABLE is not set` in the Arduino
sdkconfig, the CPU is pinned at 160 MHz so APB is a fixed 80, and the driver takes
an `ESP_PM_CPU_FREQ_MAX` lock per non-DMA channel anyway. There is a bonus in the
group *prescale*, which is shared by the same mechanism: the first channel searches
upward from 1 and takes the highest group resolution that yields a workable channel
divider, and the LED asking for 10 MHz off 80 MHz settles on prescale 1 immediately
— which is the prescale the whole k table assumed. So the LED does not constrain
the radio here, it hands it the clock it wanted. One divider on both paths, 214, a
2.675 us tick, and a bit-identical waveform by construction rather than by
arithmetic coincidence.

**The implementation, which I handed over.** The three things worth doing by hand
were the buffer builder, the first bring-up observation, and one design decision;
I took the decision and gave away the rest. The decision was retrigger policy:
ignore-while-busy, because this device exists to emit one precise 3 s beep per
press and not to reproduce the original remote's press-and-hold. That was already
the ESPHome behaviour by accident — `mode: single` drops a second execution — and
is now deliberate on both paths.

What came out: a shared `include/rmt_beep.h` holding the whole transmit core, and
for the first time the radio logic is not duplicated. Every documented difference
between the two paths — who suspends the scheduler and for how long, who feeds the
watchdog, which timing engine runs — existed only because the CPU generated the
waveform, so all of it evaporated together. `FRAMES_PER_BURST`, `TRANSMIT_GAP_US`
and `TRANSMIT_REPEAT` collapse into `BEEP_DURATION_MS`, which the firmware rounds
to 132 frames of 22.743 ms. `BASE_TICK_US` 209 becomes `SYMBOL_TICKS` 78, which
moves the scalar the payload is parameterised by out of whole microseconds and into
channel ticks, from 1692 ppm to 14.38 ppm without touching a single run length.

One invariant broke in the other direction. `rmt_transmit()` returns immediately, so
the beep now runs in hardware while `loop()` keeps turning, and the standalone
heartbeat needs the same `strip.show()` guard the ESPHome one has always had —
previously unnecessary because `triggerTransmit()` blocked `loop()` and the two were
mutually exclusive by construction. Both ends of the pulse need it: guarding only
the start still lets a pulse that began just before a trigger blank the LED for the
whole beep.

**The payload was a rotation, and rebuilding it checked itself.** Verifying the
frame arithmetic showed the stored array's last element was `-2`, a long OFF run,
where the decode says run 87 is always short. The array was the canonical frame
rotated left by two runs — `canonical[j] == stored[(j+2) % 88]` — which tiles to the
same waveform and is why nothing ever noticed. I rebuilt it from the `Be_A` row of
the frame worksheet. That row gives run *lengths* only; the levels come from "run 0
is RF ON" plus alternation, so the assumption is load-bearing and untested by the
reconstruction itself. What tested it was reading the fields back: channel 45-46
`AB`, function 67-68 `AB`, level 71-78 `AAAAAAAA` (the worksheet says beep carries
value 0), redundancy 79-86 `BBBBAABA` (complement x4, copy x2 for beep, then `BA`
for channel A), run 87 short. Inverting the level assumption would have read the
level field as `BBBBBBBB` and broken the redundancy mask. Four independent
constraints agreeing is what makes the rebuilt frame trustworthy, not that it
happened to match what was already in the file.

Honest accounting of what the change buys, because it is less than it looks. For
131 of 132 frames the collar receives bit-identical RF. The last frame's truncated
run becomes canonical 87, which carries nothing about the command, instead of
redundancy position i = 6, which does — a real argument, but speculative, since
nothing establishes that the collar examines the trailing partial frame. And the
first frame now presents 31 leading unit runs rather than 33, because the old cut
started two runs into the preamble and picked up two short constant runs after it;
that is very slightly *worse* lead-in. The actual payoff is that the payload and
the documented field offsets now describe the same object.

**Nothing has been on the air.** Both paths compile and the working tree is
re-encrypted, and that is the whole claim. The first hardware check is not RF: a
boot where the LED still lights *and* `rmt_beep::init()` returns `ESP_OK` proves the
group clock source, the group prescale, the channel count and the block size all
agree in practice — the entire stack of assumptions from the last three sessions, in
one observation.

### 2026-09-10

A second session the same day, and again no code and nothing on the air. It
picked up where the clock chain left off — what the RMT transmitter does with its
buffer once the tick is fixed — and settled three things: which transmit mode
builds a burst of back-to-back frames, whether the frame's own content survives
being looped, and how the one part the manual does not describe gets measured.

**It opened by running ahead, again.** The question was only whether TX wrap
mode came next. What came back was the whole wrap-versus-loop comparison read out
of the ESP-IDF driver: which modes the driver treats as exclusive, where the 1023
cap comes from, where a batch seam falls. None of that was established — the
previous session had ended at the clock and never touched transmit behaviour —
and every point cited a driver line and no section of the manual, which is the
unsourced-claim shape already in Lessons. It was set aside and the transmitter
part of TRM chapter 33 (v1.4, pages 843–865) was read first-hand instead.

**The transmit modes.** Normal mode starts on `RMT_TX_START_CHn`, reads from the
channel's lowest RAM address, and stops at a zero-period entry, the end marker,
raising `RMT_CHn_TX_END_INT`; `RMT_TX_STOP_CHn` aborts mid-transmission. The idle
output level comes either from the end marker's level bit or from
`RMT_IDLE_OUT_LV_CHn`, selected by `RMT_IDLE_OUT_EN_CHn`, so idle is not
necessarily low.

Wrap mode (`RMT_MEM_TX_WRAP_EN_CHn`) exists for more pulse codes than fit in the
channel's RAM. The read pointer runs off the end of the channel's allocation and
back to its start until it meets an end marker; `RMT_CHn_TX_THR_EVENT_INT` fires
after `RMT_TX_LIM_CHn` entries, and software rewrites the region already sent.
My first reading needed two corrections. The rewritable region is the one
*behind* the pointer, not "any address not currently being sent" — writing ahead
of it races the transmitter. And the wrap happens within the channel's own
`RMT_MEM_SIZE_CHn` blocks, which extend only upward, so only channel 0 could ever
span all 192 words. One 44-word frame fits in a block, so wrap is not needed.
ESP-IDF turns it on for every TX channel regardless (`rmt_tx.c:334`), because it
is how ordinary long transmissions get refilled.

Continuous mode (`RMT_TX_CONTI_MODE_CHn`, 33.3.4.4) restarts from the first entry
at an end marker, or after the block's last entry if there is none. With
`RMT_TX_LOOP_CNT_EN_CHn` set, a counter increments on each end marker and
`RMT_CHn_TX_LOOP_INT` fires when it reaches `RMT_TX_LOOP_NUM_CHn`. That is the
burst: one frame in RAM, repeated in hardware. The end marker is required rather
than tidy, since it is the thing being counted. 88 runs fill 44 words exactly, so
the marker takes the 45th, still inside the 48-word block.

**The loop count, and three arithmetic slips.** I read the count as a 9-bit
field allowing 512 frames. The width was wrong: Register 33.16 puts
`RMT_TX_LIM_CHn` at bits 8:0 and `RMT_TX_LOOP_NUM_CHn` at 18:9, and 18:9 counted
inclusively is ten positions, so the maximum is 1023 — which is also
`RMT_LL_MAX_LOOP_COUNT_PER_BATCH` in `hal/esp32c3/include/hal/rmt_ll.h`. The
value was argued wrong too: that a zero-based field makes 511 the 512th frame.
That convention holds only where the manual writes the offset —
`RMT_SCLK_DIV_NUM + 1`, `RMT_CARRIER_HIGH_CHn + 1`, `RMT_DIV_CNT` with 0 meaning
256 — and for the loop count it writes none. The interrupt fires when a count of
end markers "reaches the value set", so the value is a count, and the IDF
low-level driver writes the requested count into the field unchanged
(`rmt_ll_tx_set_loop_count`). Whether a field is a count or an index depends on
what the hardware compares it against, not on a default. The duration was the
third: 1023 × 88 × T = 18.8 s treats 88 runs as 88 ticks, when frames run 109 to
113 ticks. At 113 ticks × 208.647 µs, 1023 frames is about 24.1 s. A beep is under
5 s, so one batch covers it with a wide margin and the batch boundary never
arises.

**The end-marker timing constraint.** 33.3.4.4 adds a condition: in continuous
mode the entry before a zero-period end marker must satisfy 10 × Tapb_clk + 19 ×
Trmt_sclk < period × Tclk_div, where every other non-zero entry only needs 33.1,
5 × Tapb_clk + 6 × Trmt_sclk < period × Tclk_div. The right-hand side is the
entry's real duration; the left is a fixed time built from the APB clock and the
RMT working clock. Both are minimum pulse widths. The manual never derives 5, 6,
10 or 19, so what follows is a reading and not a finding: the RAM sits on the APB
bus while the transmitter counts on rmt_sclk, so fetching the next entry crosses
between the two clocks and takes a few cycles of each, and any entry has to
outlast that. At an end marker in continuous mode there is more to do before
output resumes — recognise the zero, count, reset the read pointer, fetch entry
0 — hence a longer minimum on the entry before it. That would also explain why
Tapb_clk appears on the standalone path at all, where RMT counts off XTAL.
Neither 33.3 against run 87 nor 33.2, a relation between the two clocks (1.5 ×
Tapb_clk < 9 × Trmt_sclk), has been checked against the clock chain chosen
earlier today.

**Modulation, and what OOK actually is.** With `RMT_CARRIER_EN_CHn` set, a square
wave high for `RMT_CARRIER_HIGH_CHn + 1` and low for `RMT_CARRIER_LOW_CHn + 1`
rmt_sclk cycles (16 bits each, `RMT_CHnCARRIER_DUTY_REG`) fills the high runs of
the output, or the low runs if `RMT_CARRIER_OUT_LV_CHn` is cleared;
`RMT_CARRIER_EFF_EN_CHn` decides whether it also runs during idle. I could not see
what that added over normal mode, which already produces time high and time low,
and "OOK is exactly that". That was the misconception. Time high and time low is
the *envelope*. OOK is a carrier switched on and off by the envelope. In this
device GDO0 carries only the envelope, and the OOK signal exists only at the
CC1101's antenna, because the CC1101 synthesises the 869.525 MHz carrier and
gates its power amplifier with GDO0. A fixed-frequency carrier with the pulses on
top at a high or low amplitude is exactly what the RMT does, once a GPIO's only
two amplitudes are applied: carrier present or carrier absent. It matters wherever
nothing downstream makes a carrier — an IR LED emits only while current flows.

Normal mode could write the carrier out cycle by cycle, and the reason the carrier
stage exists is what that costs. An NEC IR frame at 38 kHz — a 9 ms burst, a
4.5 ms space, 32 bits each a 562.5 µs burst plus a 562.5 µs or 1687.5 µs space,
and a final 562.5 µs burst — is 67 envelope entries, about 34 words, one block.
With the carrier written out, the 9 ms burst alone is 342 cycles and 684 entries,
and the whole frame about 1050 words against 192 in the entire peripheral. The
carrier also counts rmt_sclk directly rather than channel ticks, so it gets fine
timing while the envelope keeps a tick coarse enough to fit 9 ms into 15 bits. Its
ceiling is one cycle high plus one low, half of rmt_sclk, so at most 40 MHz from
APB at 80 MHz. An antenna on the pin never reaches 869 MHz, and even where the
frequency is reachable a square wave's odd harmonics put a driver and a tuned
circuit between pin and radiator. Where it earns its place: IR remotes, the
peripheral's namesake (33.1); 40 kHz ultrasonic ranging; 125 kHz inductive links
and RFID readers driving a coil tuned to resonance, where
`RMT_CARRIER_EFF_EN_CHn` = 0 keeps the field up between commands.

**Simultaneous mode.** Starting two channels from software is two writes to
`RMT_TX_START_CHn`, and anything scheduled between them delays the second by an
unbounded amount. `RMT_TX_SIM_EN` starts the channels selected in
`RMT_TX_SIM_CHn` from one trigger, with the offset between them bounded within 3 ×
Tclk_div (33.3.4.5). The first guess, differential pairs, does not fit: a
differential pair needs every edge aligned, the bound covers only the start — up
to about 8 µs at a 2.675 µs tick — and differential links are normally driven from
one single-ended signal through a transceiver. It suits relative timing that is
coarse against 3 ticks: a quadrature pair, a setup time between two lines such as
a stepper's DIR before STEP, or two ultrasonic transducers steered by a controlled
delay. The C3 has only two TX channels, which caps all of it.

**Whether the frame survives being looped.** Burst contiguity is the property this
firmware turns on, so the seam between the last entry and entry 0 had two halves:
what the peripheral does there, which nothing read so far describes, and what the
frame's content requires, which is independent of any peripheral. My first
argument for the content half was that a transmission has to start HIGH, since a
leading LOW is indistinguishable from the silence before it, and has to end LOW,
since a transmitter cannot hold HIGH forever; so every frame starts HIGH and ends
LOW, and the seam is a LOW→HIGH edge. The conclusion was right for this frame and
the argument did not carry it.

The silence argument constrains the two ends of a whole transmission, where the
neighbour is silence. At the seam run 87 sits directly against run 0 and there is
no silence. And "the exact same frames repeated" assumed the rest: what was
measured identical across frames is durations — in a run-length code that is all
there is to measure — and whether they are identical in levels too depends on the
run count. An 87-run frame starting HIGH ends HIGH, so the next copy has to start
LOW or two HIGH runs merge. An odd-length frame therefore repeats as alternately
inverted copies, and a receiver that only measures durations cannot tell those
from identical ones: AAA AAA goes HIGH-LOW-HIGH, LOW-HIGH-LOW. So odd run counts
are not impossible in a protocol. What is impossible is looping an odd-length
frame out of a single RMT block, because each 16-bit entry stores its own level
bit (33.3.2) and the transmitter outputs it verbatim, never enforcing alternation.
The rule belongs to the peripheral, not to the code.

Drawing it out exposed the next slip. I had AAA followed by silence becoming
AAAA, "because the transmitter has to go low eventually". Counting edges gave four
for both AAA and AAAA followed by silence, and I concluded a receiver reads both as
AAAA. But a run is the gap between consecutive edges, so four edges bound three
runs: AAA and AAAA followed by silence are the same waveform, and both read as AAA.
The fourth run of AAAA is LOW, a LOW run is closed only by a rising edge, and
silence never produces one. What falls out is not about frame parity at all — a
transmission that ends on a LOW run always loses that run — and protocols deal
with it in one of two ways. NEC IR carries each bit in the space after a burst, so
its 32nd space would run straight into silence; its final 562.5 µs burst carries
no data and exists only to close that space. The other way is to make the
unmeasurable run carry nothing.

That second way is this frame. 88 runs is even, so a frame starting HIGH ends LOW
and looping it puts a real LOW→HIGH edge at every seam. That edge, the opening
edge of the next frame's run 0, is what gives run 87 its duration inside a press.
On the last frame of a press run 87 is lost to silence, and it costs nothing
because run 87 is always short. I first put that as "run 87 carries no
information", which was stronger than the evidence: it is constant across what
this handset sends, and whether it is also constant across handsets is part of
the untested question about the 68 constant runs, which needs a second remote. The
safe statement is that it carries nothing about the command. Information is about
variation, not length — AAAA in the level field is four real bits, because each
of those positions takes both values across the 20 dial settings.

**Measuring the peripheral half.** The manual says only that the transmitter
"starts transmitting the first data again", so this gets measured with the
RTL-SDR once there is RMT output to capture. The first plan was the usual decode,
calling the seam too large if the decode changed. That cannot work as a detector.
The decode rounds every run to 1T or 2T, so run 87 only decodes as B once stretched
past 1.5 T — half of 208.647 µs is 104.3 µs, exactly 39 channel ticks at k = 78 —
and every seam effect a peripheral could plausibly add, from the sub-µs scale of
33.3's left-hand side up to a few ticks, decodes identically to a perfect seam. A
stretch would not add a run either: time spent at the seam is LOW, run 87 is LOW,
and the two merge. The measurement that can see µs-scale timing is the one the base
tick came from, frame start to frame start, rising edge to rising edge at the same
structural position, where rise-time bias cancels.

Sizing what else lengthens that period took two more corrections. The SDR's sample
clock cancels between captures on the same dongle, but only its fixed offset, not
drift across the weeks since the reference capture. The RMT's +14.38 ppm and the
ESP's crystal error do not cancel against the real remote at all: comparing
against a reference measures a difference, it does not remove one. The crystal
requirement is in Espressif's ESP32-C3 Hardware Design Guidelines (Schematic
Checklist, Clock Source): 40 MHz, accurate within ±10 ppm, trimmed by adjusting the
load capacitors while measuring the 2.4 GHz test tone, because the radio's carrier
comes from the same crystal. That is a requirement on board designers, not a
measurement of this C3 Mini. Against the longest frame, 113 ticks or 23.58 ms, the
rounding comes to about 0.34 µs and the crystal to at most about 0.24 µs — under
0.6 µs together, a fifth of one channel tick and roughly one sample at 2 MSps. I
also had it wrong that a rate error grows with the span while a seam stretch is
fixed: over whole frames both add a constant per frame, so what separates them is a
span with no seam in it against a span that crosses one. (The guidelines' old PDF
URL now serves an HTML page; they live on docs.espressif.com.)

**Where the precision stopped.** At that point the question became whether any of
it mattered, and mostly it does not. The acceptance test is functional — the frame
decodes the same and the collar beeps reliably — and the collar's history suggests
a wide timing margin: the old payload ran every run at 200 µs, 4% short of
208.647, and still beeped about 70% of the time, a shortfall later traced to burst
structure rather than timing. A one-tick stretch on run 87 is 1.3% of one run.
That is an inference from history, not a measurement of the collar. The rigour
had kept tightening past what the decision needed, and "does it work" and "what
exactly does the peripheral do" should have been separated several steps earlier.
What stays is a single comparison, the period across a span containing a seam
against a span without one, to learn whether continuous mode adds output time at
the jump back — a fact about the chip worth having for anything that later loops
RMT output.

**Still open before implementation.** What the C3 does when the loop count is
reached: 33.3.4.4 says only that an interrupt fires, not whether output stops, and
that decides how a beep ends and whether the IDF `loop_count` API is usable as it
stands. The manual cannot settle it; `soc/esp32c3/include/soc/soc_caps.h` and the
loop-end handler in `esp_driver_rmt/src/rmt_tx.c` are where it is answered. Beside
it, the arithmetic of 33.2 against the chosen clock pairing and of 33.3 against
run 87. Then implementation, and then the seam measurement.

### 2026-09-10

No code, nothing on the air. The session was the RMT chapter of the ESP32-C3
technical reference manual and the ESP-IDF source that drives the peripheral,
and it closed the question blocking everything else: what a tick is worth, and
whether the onboard LED leaves the transmitter free to choose one.

**It opened on a false premise that had already been written down as fact.** The
project note and this repository's `CLAUDE.md` both carried a short list of
"peripheral facts already established" — 32-bit symbols holding two entries,
48-word channel blocks, 88 runs fitting as 44 symbols — and none of it had ever
been read out of the manual. It was asserted in an earlier session, written into
the documentation, and read back a week later as the project's own finding. One
item was also wrong: "88 runs = 44 symbols against a 48-symbol block"
double-counts, since a symbol and a word are the same object here. The correct
statement is 88 pulses = 44 words against a 48-word block, so the default
partition holds 96 pulses. Same conclusion, wrong units, sitting in the
repository looking settled.

**The RAM.** Four channels, two of them able to transmit (0 and 1), sharing one
192 × 32-bit block of private SRAM. Shared is the operative word — spreading
across channels buys no capacity. By default the RAM is partitioned 48 words per
channel, and a channel can be configured to claim its neighbours' blocks, but
only upward: channel 0 can take all 192 words, channel 1 can reach blocks 1
through 3, channel 3 is stuck with its own. That asymmetry, plus channel 0 being
a transmit channel, is what makes channel 0 the candidate. Section 33.3.2 gives
the format: each 32-bit row holds two 16-bit pulse codes, each a 1-bit level and
a 15-bit period counting `clk_div` cycles, and a zero period is an
end-of-transmission marker. 88 runs is 44 words, so the default block suffices
and the memory configuration never needs touching. Establishing the headroom and
then declining to use it was the right order — the extension rules are known now
if the frame ever grows.

The RAM is reachable over the APB bus while the transmitter reads it, which
looks like a concurrency hazard and is not one for a single-shot transmission out
of a pre-filled static buffer: the transmitter only reads, and the contents do
not change. That scoping is the part to carry, because it stops being true under
TX wrap mode, where the CPU refills the half the transmitter has already passed
and the threshold interrupt becomes the synchronisation primitive.

**The clock, and a wrong turn worth keeping.** The C3 has three clock origins —
PLL, crystal oscillator, and on-die RC — giving PLL_CLK at 320 or 480 MHz,
XTAL_CLK at 40 MHz, XTAL32K_CLK at 32 kHz, RC_FAST_CLK at a nominal 17.5 MHz,
RC_FAST_DIV_CLK at RC_FAST/256, and RC_SLOW_CLK at a nominal 136 kHz. RMT accepts
three of them: APB, RC_FAST and XTAL.

The first choice was RC_FAST, on two arguments. One was right: APB_CLK follows
whatever the CPU clock is sourced from, so dynamic frequency scaling can move it
underneath a transmission in flight, and a tick that changes mid-frame is not a
tick. The other rested on "there is no external oscillator", which is false — it
conflated the absent 32.768 kHz crystal, which this board genuinely does not
populate, with the 40 MHz crystal, which it must have, because the C3's radio
cannot run without one and this device runs Wi-Fi. The device working is the
proof; no document was needed.

That left the mechanism to get right rather than the fact. An RC oscillator sets
its frequency from an on-die resistor and capacitor, both of which vary with
process, temperature and supply voltage — which is exactly why the manual says
"17.5 MHz **by default**" and "adjustable frequency". A crystal is a mechanical
resonator whose frequency comes from the physical dimensions of a quartz slab and
holds to parts per million across the same conditions. ESP-IDF can calibrate
RC_FAST against the crystal at boot, but that only pins down where it is at boot
and does nothing about drift afterwards. Choosing an RC source to escape a
variable clock inverts the actual stability picture. XTAL_CLK is the answer, and
it also happens to be immune to the frequency scaling that disqualified APB.

**The fractional divider.** `rmt_sclk = clk_src / (RMT_SCLK_DIV_NUM + 1 +
RMT_SCLK_DIV_A / RMT_SCLK_DIV_B)`, and the reason the formula reads as
unexplained variables is that they are not derived from anything — they are
register fields in `RMT_SYS_CONF_REG`, written directly. `DIV_NUM` is 8 bits,
`DIV_A` and `DIV_B` 6 bits each. The `+ 1` is the standard zero-based counter
convention: a down-counter reloaded with N takes N+1 cycles to come round, so
writing 0 divides by 1 and the integer part spans 1 to 256.

What a fractional divider physically does is the part worth understanding.
Hardware cannot emit a clock cycle 17.5 source cycles long — a cycle is a whole
number of edges or it is nothing. So it dithers: an accumulator adds `DIV_A` each
output period and, when it reaches `DIV_B`, stretches that one period by a single
extra source cycle. Out of every `DIV_B` periods, exactly `DIV_A` are long, and
the average comes out exact. `A/B` is therefore not a magnitude but a duty ratio
between two integer divisors. The consequence is that the long-run rate is exactly
right while individual periods jitter by up to one source-clock period.

Then a second stage: each channel has its own 8-bit `RMT_DIV_CNT`, dividing
`rmt_sclk` again to reach that channel's counting tick. `rmt_sclk` is module-wide
and only `DIV_CNT` is per-channel — the low-level driver makes this explicit with
`(void)channel; // the source clock is set for all channels`. That single fact is
what dragged the LED into a clocking decision.

**Reparameterising made the search tractable.** Guessing divider fields and
checking the result is the wrong direction. Choosing **k, the number of ticks in
one symbol period T**, forces everything else: the tick is T/k, a 1T run is k in
the period field and a 2T run is 2k, and the total divisor needed is D = N/k,
where N = 40 MHz × 208.647 µs = 8345.88 source cycles per symbol. The constraint
box is `DIV_NUM+1` ≤ 256, `DIV_A`/`DIV_B` ≤ 63 with A < B, `DIV_CNT` ≤ 256,
2k ≤ 32767 from the 15-bit period field, and D ≥ 1 because a clock cannot be
divided by less than one. Both ceilings on k are worth checking against each
other; the 15-bit field is not automatically the binding one.

The objective chosen was an integer D, and it needed sharpening twice. First,
integer is not the same as exactly representable — the fractional divider
represents any `m + a/b` with b ≤ 63 with no error at all, so what integer D
actually buys is `DIV_A = 0` and therefore no dithering and no jitter. Second,
integer alone is not sufficient: with `DIV_A = 0`, D = (`DIV_NUM+1`) × `DIV_CNT`,
a product of two factors each ≤ 256, so a prime above 256 is an integer that
cannot be expressed. And since N is not itself a whole number of source cycles,
an exactly integer D is unreachable for every k — what is really being minimised
is the residual after rounding.

**The finding that collapsed the table.** Sweeping k and rounding D produced an
error column with the same values repeating: +14.38 ppm on fifteen different
rows, spanning k = 1 to k = 4173, and −225.26 ppm on a dozen more. Multiplying
k by D on any of them gives 8346. Those rows are the same clock rate, differing
only in how the rate is partitioned between the group divider, the channel
divider and the period field. So **k is not a choice about accuracy at all**, and
+14.38 ppm — the residual from rounding 8345.88 to 8346 — is a floor no k can
improve. For scale, the shipped bit-banged firmware rounds T to `BASE_TICK_US =
209`, which is 1692 ppm; and the underlying measurement, 272910 samples over 654
ticks, carries roughly 3.7 ppm per sample of endpoint uncertainty, so 14.38 ppm
sits a few times above the measurement's own noise and two orders below what is
in use today.

k = 1 was the first pick, and its appeal is more than readability: with the tick
equal to T, `SIGNAL_BEEP_TICKS` — signed run lengths already stored in T units,
every element ±1 or ±2 — maps element-for-element onto RMT entries, sign becoming
the level bit and magnitude the period. The encoding chosen years ago to make the
base-tick sweep possible turns out to be the RMT entry format.

**The LED, which is on the same peripheral.** The two firmware paths diverge here
and nobody chose it: `src/main.cpp` drives the WS2812B through `Adafruit_NeoPixel`,
which bit-bangs and takes no RMT channel, while `esphome/d-control-400.yaml` uses
`esp32_rmt_led_strip`, which does.

Worth writing down how that LED actually works, because it decides what kind of
conflict this is. It is a latch, not a refresh. Twenty-four bits of GRB are
clocked in at 800 kHz; the first LED keeps the first 24 and forwards everything
after that down the chain, which is how a strip addresses itself with no
addressing at all. Holding the line low for more than 50 µs latches. After that
nothing is sent — the controller runs its own constant-current PWM from the
latched value indefinitely. There is no brightness field, brightness being the
8-bit value itself, and no duration field, duration being the host's problem. So
the 80 ms heartbeat is one frame green, a software delay, one frame black, and
with a single LED each frame is 24 × 1.25 µs = 30 µs. The channel is busy for
under 100 µs a few times per five seconds. Runtime contention is nil. The
conflict is entirely at configuration time, over a `rmt_sclk` both channels must
live with permanently.

Filtering the candidate ticks against WS2812 timings — T0H 350 ns, T1H 700 ns,
T0L 800 ns, T1L 600 ns, each ±150 ns — killed k = 1 and k = 2 and nothing else.
At k = 1 the fastest `rmt_sclk` any factorisation of 8346 allows gives a 975 ns
tick, which cannot place a 350 ns interval at all.

**Reading the driver mattered more than the filter.** Five facts out of the
installed ESP-IDF and ESPHome 2026.7.4, all of which change the shape of the
problem:

- The group clock source is shared and a mismatch is fatal. In
  `rmt_common.c:199` the first channel created sets `group->clk_src`; a later
  channel asking for a different one is refused with `ESP_ERR_INVALID_ARG` and
  the log line "group clock conflict".
- `esp32_rmt_led_strip` asks for `RMT_CLK_SRC_DEFAULT`, which on the C3 resolves
  to APB, and sets `resolution_hz` to the full source frequency
  (`led_strip.cpp:96-97`). So it claims APB at group prescale 1.
- The first channel also wins the group prescale, and the search that picks it
  (`s_rmt_set_group_prescale`, `rmt_common.c:146`) starts at 1 and takes the
  first value where the channel prescale fits in 256 — optimising for highest
  frequency, explicitly, rather than for anyone's rounding error.
- The driver never uses the fractional divider. It hardcodes
  `rmt_ll_set_group_clock_src(..., group_prescale, 1, 0)`, so `DIV_A`/`DIV_B` are
  unreachable from the public API. The integer-D objective happens to align with
  that exactly, so it costs nothing here.
- At ESPHome's stock settings the LED consumes both transmit channels.
  `light.py:85` defaults `rmt_symbols` to 96 on the C3; `rmt_tx.c:115` converts
  that to 96/48 = 2 memory blocks; and the comment at `rmt_tx.c:105` spells out
  the consequence — "a channel can take up its neighbour's memory block, so the
  neighbour channel won't work". With only two transmit candidates on this part,
  a two-block LED channel leaves none. `rmt_symbols: 48` in the YAML fixes it and
  is not optional.

One aside undercuts the original reason for rejecting APB: when power management
is enabled the driver takes an `ESP_PM_CPU_FREQ_MAX` lock per channel
(`rmt_common.c:230`), with a comment saying it does so even for APB to keep RMT
stable. The frequency-scaling hazard is one the driver already defends against.

**Where it landed.** The priority was stated as signal precision first, with the
LED to be taken off RMT entirely if sharing cost anything — a defensible trade,
since one frame per LED state change is trivial to bit-bang. It turned out to
cost nothing. With the LED holding the group clock at APB 80 MHz and prescale 1,
only `DIV_CNT` ≤ 256 is left, which caps how coarse the transmitter's tick can
be; and because APB at 80 MHz is exactly twice XTAL at 40 MHz, nine values of k
give an identical tick and identical error on both firmware paths. The choice is
**k = 78**: `DIV_CNT` 107 off XTAL on the standalone path, 214 off APB under
ESPHome, a 2.675 µs tick either way, 1T = 78 ticks and 2T = 156 against a 32767
ceiling, at +14.38 ppm. Both paths emit the same waveform, which is what
`CLAUDE.md`'s rule about RF changes landing in both wants. Two conditions come
with it besides the memory setting: APB has to be requested explicitly rather
than inherited, since otherwise a boot failure depends on component
initialisation order, and the driver will log a "channel resolution loss" warning
because 80 MHz / 214 is not a whole number of hertz, which is arithmetic rather
than a real loss.

Incidental, and it closes an open question standing in `CLAUDE.md`:
`RMT_LL_MAX_LOOP_COUNT_PER_BATCH` is 1023, so the C3 does have hardware transmit
looping and continuous output does not necessarily need a wrap-around refill
interrupt. What that buys, and what happens at the seam between loop iterations
given that burst contiguity is the property this whole firmware turns on, is the
next session.

### 2026-09-08

No code and nothing on the air. The remaining open item on this project is moving
transmission off the CPU and onto the RMT peripheral, and the question underneath
that is whether GPIO8 can carry the waveform at all — GDO0 is wired there, and
GPIO8 turned out to be one of only three pins on this board carrying a 10 kΩ
pull-up that nothing else gets. Answering it meant reading the LOLIN C3 Mini
schematic (v2.1.0) end to end and then the ESP32-C3 datasheet, and the entry
follows that order because that is the order the answer assembles in.

The session opened badly: the request was for the schematic link so the reading
could be done firsthand, and what came back was the reading. Worth recording
because it is the same failure this project has hit before, and the correction
holds for the rest of the entry — the analysis below is mine, checked rather than
handed over.

**J1, the USB-C receptacle.** Only D+/D- are wired for data, and they appear
twice: A6/A7 and B6/B7, shorted pairwise on the board. The reason is that a
Type-C plug can be inserted either way up, which swaps the A and B rows. A device
that only speaks USB 2 shorts the rows together so the differential pair reaches
the SoC in either orientation; a USB 3 host keeps them separate because it has
the SuperSpeed pairs to work with and needs to know which row is live. The
absence of those SuperSpeed pairs, rather than the doubled D+/D-, is what
actually establishes this as a USB-2-only port.

CC1 and CC2 each carry a 5.1 kΩ pull-down. That is Type-C's entire negotiation
layer in two resistors: a source presents pull-ups on its CC lines, a sink
presents 5.1 kΩ pull-downs (Rd), and when the source sees its pull-up dragged
down through Rd it learns both that something is attached and that it is a sink,
so it may switch on VBUS. Which of the two CC pins moved also gives it the cable
orientation. The value is not free — 5.1 kΩ is specified, and the source signals
its available current (default / 1.5 A / 3 A) by varying *its* pull-up against
that fixed number. SBU1/SBU2 are the sideband pins used for alternate modes and
debug, and are floating here, which is consistent with USB 2 only.

**SW1 on EN, and the capacitor I read backwards.** A 10 kΩ pull-up to 3V3 with
the button shorting to ground is obvious enough. The 1 µF cap is not, and my
first reading — that it forces the button to be held during boot — is wrong in
its direction. The cap charges *through* the 10 kΩ, so the RC slows EN rising,
never falling. With τ = 10 kΩ × 1 µF = 10 ms that holds the SoC in reset for
about 10 ms after 3V3 comes up, which is a power-on reset delay giving the rail
time to settle; on button release it stretches the reset pulse by the same
amount. Debounce is a side effect, not the purpose. The generalisation is that
an RC on a reset line should be read by asking which edge it slows before asking
what it is for.

**U2, the ME6211C33 regulator, and a mistake with a payoff.** VBUS in, CE tied to
the input so the regulator is permanently enabled, 3V3 out. The 10 µF on the
input I dismissed as smoothing that the regulator itself already does — and that
dismissal is the error. An LDO's power supply rejection ratio is finite and falls
as frequency rises: good at DC, useless in the MHz. Meanwhile the host is metres
of cable inductance away, so when the load steps hard the input rail sags long
before the host can respond. The 10 µF is a local energy reservoir for exactly
that transient. This is not abstract here: the ESPHome config caps Wi-Fi at
`output_power: 8.5dBm` to stop brownout on this regulator, a fix found
empirically months ago, and a Wi-Fi transmit burst is precisely the load step
described. The empirical hack now has a circuit behind it.

The output carries 10 µF and 100 nF in parallel, which is the standard pairing
and worth understanding rather than copying. The 10 µF is bulk and satisfies the
LDO control loop's minimum output capacitance for stability. The 100 nF is not a
smaller version of the same thing — a large MLCC has more parasitic inductance
and self-resonates at a lower frequency, above which it stops behaving as a
capacitor at all, so a small part in a small package covers the band the big one
has abandoned. Two capacitors, two frequency ranges, one flat impedance curve.

**Reference designators**, since they had never been looked up properly. IEEE 315
and ASME Y14.44 define the class letters and they hold remarkably well across
vendors and decades: R, C, L for passives, D for diodes including LEDs, Q for
transistors, U for integrated circuits, Y for crystals, K for relays, F for
fuses, TP for test points. The pair worth knowing exactly is J and P — J is a
jack, the connector half fixed to the board, and P is the plug, the half that
moves. Most modern boards label every connector J regardless, which is why two
pin headers here are J2 and J3. The numbers are instance counters with no
meaning. It is convention rather than enforcement, and the IEC 81346 scheme used
in plant and machine drawings assigns letters by function instead and does not
line up — connectors are X there.

**The header silkscreen, and why it can be ignored.** J2/J3 label GPIO0/1/4 as
SPI and GPIO8/10 as I2C. Those are suggestions, and this repository already
proves it: `include/pinout.h` puts the CC1101's MOSI on GPIO3 while the
silkscreen calls GPIO4 MOSI, and the radio works. The mechanism is the GPIO
matrix, and the difference from the STM32 habit is real rather than cosmetic. ST
gives each pad an alternate-function mux with a fixed menu chosen at design time.
The ESP32 has a small IO MUX of that kind for a few fast fixed functions, plus a
full crossbar — the GPIO matrix — through which almost any peripheral signal can
reach almost any pad. That is why the RMT output is a routing choice and not a
pinout constraint, which is the whole reason this matters today.

**The die marking.** Legible under a lamp: `ESP32-C3`, `122022`, `FH4PPG4330`,
`FD00PKP828`. FH4 decodes from the ordering nomenclature — F for in-package
flash, H for the high-temperature flash grade, 4 for 4 MB. The rest does not fit
the nomenclature, and I took that as evidence of a different variant and guessed
ESP32-C3FH4AZ. Wrong step: the leftover does not fit because it is not part of
the ordering code at all. The ordering code ends at FH4 and what follows is
lot and trace marking. Had it been the AZ variant the marking would say AZ. The
same correction kills the idea that the last string is a serial number — package
markings are lot-level and identical across a whole reel, and the genuine unique
per-die identifier is the base MAC in eFuse. The stronger source than a lid under
a lamp is the chip itself: the boot ROM prints chip identity and silicon revision
on the serial line before any firmware runs, and if the two ever disagree the
boot log wins.

**The strapping pins, which is what the session was for.** GPIO2, GPIO8 and
GPIO9 are the three pins with 10 kΩ pull-ups, and the datasheet names exactly
that set: strapping pins are sampled during reset to select operational settings
and are ordinary GPIOs afterwards. GPIO9 has an internal weak pull-up active at
reset and so needs no external resistor; GPIO2 and GPIO8 float by default, which
is why the board supplies them. The two boot modes are SPI Boot, needing GPIO2
high and GPIO9 high with GPIO8 don't-care, and Joint Download Boot, needing GPIO2
high, GPIO8 high and GPIO9 low — the latter being what SW2 on GPIO9 is for.

My first conclusion was that GPIO8 cannot be hard-wired because it would break
the boot, and it is wrong in a way worth keeping. GPIO8 is don't-care in SPI
Boot, so forcing it low breaks nothing about booting: the board starts normally,
every time, forever. What it destroys is Joint Download Boot, which is to say the
ability to flash it ever again. The consequence was misnamed, and the failure it
actually produces is the quieter one. The constraint is also directional rather
than a prohibition — tying GPIO8 high is fine, and is roughly what the 10 kΩ
already does weakly. GPIO2 is the pin where "breaks the boot" is literally true,
since it must be high in both modes. So all three are strapping pins and the cost
of getting each one wrong is different.

What this settles for the RMT work: nothing prevents redefining GPIO8 after
reset. Firmware cannot violate a strapping constraint, because firmware does not
begin running until the sampling window has closed; only external circuitry can
force a wrong level. GPIO8 is therefore free to take an RMT channel through the
matrix. Parked deliberately: whether the CC1101's GDO0 presents high impedance
while the ESP is still in reset is a CC1101 question rather than an ESP one, and
it is not blocking, since this board demonstrably boots and flashes today.

What is already established about the peripheral itself, before the reading
starts. RMT — Remote Control Transceiver, named for the infrared remote codes it
was built to shift — is a generic pulse-train engine hanging off the APB bus with
its own private SRAM. A symbol is one 32-bit word holding two entries of
`{level: 1 bit, duration: 15 bits}`, durations counted in RMT ticks set by a
per-channel divider off a selectable source clock, and a zero duration marks the
end of a transmission. The C3 has four channels, two TX and two RX, each with a
48-word block; the 88 runs of a frame are 44 words, so a whole frame fits in one
block with room to spare. That is the property the entire migration rests on.
Also noted: the WS2812B on IO7 is normally driven by RMT on ESP32, so this board
already has an RMT consumer soldered to it, which will matter when channels get
allocated.

Next is the RMT chapter of the technical reference manual, and the first question
to take to it is clocking — what source clocks and dividers exist, and what tick
resolution to choose given that T is 208.647 µs, that runs are 1T and 2T, and
that a duration field is 15 bits wide.

### 2026-09-07

A documentation session, and the first with nothing measured off the air. The
README had been written incrementally alongside the work and never read end to
end as a stranger would read it, so the job was to check every claim in it
against the thing it described — the source, the gerbers, the build config, the
decode. The fixes matter less than the pattern the checks turned up, which is
that documentation drifts in two distinct ways and only one of them looks like
an error while it is happening.

The first way is ordinary staleness, and the source settles it immediately.
`printState()` in `main.cpp` prints `g  inter-burst us`, while the README's
command table called `g` the inter-frame gap — the one distinction the whole
burst-contiguity finding rests on. `t` calls `triggerTransmit()`, which runs the
entire sequence of `TRANSMIT_REPEAT` bursts, not the single burst the table
promised. `b` was not documented at all. `platformio.ini` carries a comment
explaining why it deliberately sets no `upload_port`, and both the README and
the repo's `CLAUDE.md` still instructed the reader to edit that port. And the
README opened its FreeRTOS section by calling the ESP32-C3 a dual-core chip; it
is single-core RISC-V. None of these are subtle. They are what happens when a
file is edited in place for two months and never re-read against the code.

The second way is more interesting: claims that were true when written and were
overtaken by later findings, which read as authoritative precisely because they
were once earned. The oversampling section still reasoned from "the 200 µs
pulses" and "roughly 5.0 kBaud", both retired by the 208.647 µs measurement.
Worse, the calibration section argued that a wrong base tick makes a receiver
with bit synchronisation lose lock partway through a frame — but the frame is
run-length coded, there is no bit sync to lose, and the 200 µs payload triggered
the collar about 70% of the time, so the argument was contradicted by this
project's own evidence sitting three sections away. "The final ON tick is cut
short" should always have read *frame*: a press ends when the button is
released, which truncates the last frame at an arbitrary point, and that is the
actual reason the total period count of a message is unknowable and the
measurement has to be taken frame-start to frame-start. The "42-period preamble"
never existed either — the decode established the preamble as 31 short runs,
with the visible alternating stretch being that plus however many short runs
trail the previous frame, a data-dependent length and therefore not something to
measure across.

The PCB question was the one worth the session. I had recorded that the board
lacked the copper cutout under the C3's antenna on the second layer, and wrote
that into the README as a known defect of the revision before checking it. Then
I parsed the gerbers. A gerber region is a polygon bracketed by `G36`/`G37`, and
its polarity comes from the most recent `%LPD*%` (dark — add copper) or `%LPC*%`
(clear — remove it), so a pour keepout is simply a clear polygon inside the
pour. There were two large ones: X 32.893–45.000 mm present on both copper
layers, and X 18.108–30.350 mm on the top layer only. Nothing in the file says
which is which. A gerber is geometry with no semantics attached — no nets, no
component identities, not even a layer's purpose beyond its filename — so
deciding which void is the antenna keepout requires knowing the module's
orientation, and the silkscreen would not say. It draws the C3's body at
X 7.62–41.91 and one 6.35 × 7.62 mm rectangle at the extreme low-X end, and that
rectangle reads equally well as a USB-C outline or an antenna marking. The two
readings put the antenna at opposite ends of the module and each was internally
consistent, so I stopped and asked rather than picking the one that suited the
claim I had already written. An EasyEDA screenshot answered it in a glance: the
antenna meander sits at high-X, the small rectangle is the USB connector
overhanging the board edge, and the keepout is cut through both layers. The
original README sentence was right, my correction was wrong, and the defect I
had reported was not there.

The stray top-only void resolved the next day from the other direction. Diffing
a fresh export against the committed one showed the board outline and all 28
drill positions byte-identical, some bottom-layer rerouting, and that void
simply gone — a legacy artefact of an earlier revision. That is the useful half:
one gerber cannot be read for intent, but the difference between two exports
isolates exactly what moved, which makes a diff carry meaning that neither file
holds on its own.

Four candidate files came out of EasyEDA and three were worth keeping. The
gerber replaced the committed one. `board-outline.dxf` was the surprise — it
declares `$INSUNITS = 4` (millimetres) and its `BoardOutLine` polyline lands on
X 12.827–61.087, Y 36.195–76.835, matching the gerber outline exactly, with the
drilled holes, the pads and the module footprints on separate DXF layers. That
makes it the export the mechanical side actually wants: an exact 2D sketch to
build a case or a panel cutout from without opening an EDA tool. The two Photo
View SVGs went into `doc/` as top and bottom views, and are worth having because
they show the keepout on both layers, which is the one PCB claim in the README
that wanted a picture. The OBJ was skipped, and the reason is a property of the
exporter rather than a preference: its coordinates are EasyEDA canvas units
rather than millimetres, needing a ×0.254 scale, and it extrudes to 10 units ≈
2.54 mm against a specified 1.6 mm board, so both the scale and the thickness
are wrong and it carries no components at all. A STEP export is the file to take
if a PCB solid is ever wanted, matching the enclosure, which already ships as
STEP.

The manufacturing table went the same way. Grepping the whole gerber set for
material, thickness, finish, mask colour or copper weight returns nothing, and
`How-to-order-PCB.txt` is a two-line link to EasyEDA's documentation — gerbers
carry geometry only, so all four rows were fab order-form settings describing
one person's order rather than anything reproducible from the files. Two facts
survived: 1.6 mm, because the enclosure's standoffs are dimensioned around it,
and 1 oz copper, because the 0.5 mm power trace width was chosen against it.
Leaded HASL and a black mask are free choice, and stating them read as a
recommendation not meant. Checking the first of those also corrected an
assumption of my own — I had thought board thickness was a fit constraint, but
the enclosure render shows the board bolting onto four standoff bosses rather
than sliding into a slot, so thickness only shifts stack height inside the case.

Two claims had to be retracted outright, and they are the same failure twice.
The README described the beep as a recall signal. It is not — it is a
prohibitive command, used when the dog is home alone and doing something it
should not, observed on a camera that is outside this project entirely; a recall
over Home Assistant would serve no purpose. The motivation does not belong in
the README in any form: the project is the integration of the beep trigger,
irrespective of what the beep is for, and the intro now says only that. The
second was "the level map lives in the remote, so the collar holds a second,
different map from value to electrical output." The clause before the *so* is an
observation. The clause after it was never measured — nothing captured
establishes that the transmitted level value is a physical quantity rather than
an opaque index, nor what its units are, and without that there is no basis for
saying the collar performs any mapping of its own. Both sentences entered the
documentation as reasonable readings and hardened into assertions by being
restated, which is how they survived a decode session that was otherwise careful
about exactly this.

What remained was editorial. The symbol-period measurement was sitting under
"Technical Specifics", a section otherwise devoted to why the firmware is
configured as it is, when its only audience is someone capturing their own
remote — and that audience was being served again two hundred lines later by a
separate capture section that did not know it existed. Merging them left
Technical Specifics as four sections of firmware rationale and put the
measurement next to the analysis script. Of the three open questions, only the
per-handset identifier survived, because the "device specific" disclaimer rests
on it; the level-map formula concerns the shock function that the README
declares out of scope two screens earlier, and the two-collar limit is labelled
optional in its own text. The serial console's four "still good for" bullets
were a to-do list, two items of which are reported as already done elsewhere in
the same file. The README is now written for someone who has never seen the
repo: the sops material is out of the build path entirely — a fresh clone needs
its own `signal.h` from the template, not an age key — and what remains of it is
the committed pre-commit guard and the `core.hooksPath` shim, which are the only
parts that bind anyone else working here.

**The last item in the TODO was what the RMT's loop wrap costs, and the obvious
way to measure it was the wrong way.** In loop mode the frame sits in the
channel's 48-word memory block and the hardware replays it from the top when the
reader meets the end marker, which is why contiguity stopped being something the
firmware maintains. The reference manual's entire statement about that moment is
that the transmitter "starts transmitting the first data again"; it does not say
whether the jump back costs any output time. The cheapest non-zero hypothesis is
that the address reset eats one clock — one channel tick is 2.675 µs, or 118 ppm
of a 22.743 ms frame — and a decode cannot see that, because any decoder rounds a
deviation under half a symbol away and half a symbol here is 104 µs.

**The SDR route was abandoned once it became clear there is no seam-free span to
compare against.** One beep captured at 2 Msps read "3.00 s" in URH against
6003640 samples selected, which is the first thing worth not being misled by: the
seconds field is a two-decimal display and the sample count is the measurement,
so the resolution was never 10 ms but 0.5 µs. What actually limits an SDR here is
elsewhere. An OOK edge arrives smeared through the receiver's filter chain, so a
threshold crossing is uncertain by several samples no matter what rate is used —
raising the rate describes the same ramp with more points rather than sharpening
it. And the sample count converts to seconds only through the dongle's
uncompensated 28.8 MHz crystal, good to tens of ppm and drifting as it warms,
which is the same size as the effect. Both problems are cured by taking a ratio
of two spans inside one capture: the crystal cancels because both spans ride it,
and a long span divides the edge uncertainty by the number of frames it covers.
That is how the 208.647 µs symbol period was measured in the first place. It
fails here for a reason particular to the RMT — the whole beep is one frame
played 132 times, so *every* frame boundary is a wrap and no multi-frame span is
seam-free. The reference would have had to come from inside a single frame, about
22.7 ms, where ±1 µs of edge uncertainty is 44 ppm against a 118 ppm effect:
enough to see one tick at under 3σ, not enough to tell one tick from two.

**Moving the measurement on-chip fixed the clock problem and left the endpoint
problem, and the endpoint problem has a standard shape.** The RMT channel divides
APB, APB comes from the PLL, and the PLL is locked to the same 40 MHz crystal that
clocks the CPU and the systimer — so an on-chip timestamp and the waveform are
counting one oscillator through different integer dividers, and crystal error and
drift are common-mode. The SDR by contrast introduces a second, independent,
uncalibrated crystal and makes its error inseparable from the answer. What on-chip
timestamps cannot do is land on an edge: the start falls after `rmt_transmit()`
has enabled the channel but before the first edge reaches the pin, and the end
falls after the peripheral raised its interrupt, the CPU took the vector, the
driver ran its prologue, and the channel overran slightly because the C3 has loop
count but no loop auto-stop. Every one of those is fixed and unknown, and a fixed
offset added to one elapsed time has precisely the signature of a fixed per-seam
cost summed over that beep — same sign, same magnitude, same on every press. That
is what had already disqualified the morning's 3.002 s serial window. The frame
count is the lever that separates them, because the offsets do not scale with it
and the seam does: fit elapsed time against frame count, let the intercept absorb
every fixed cost, and read the slope.

**The first instrument produced a confident, reproducible, impossible answer.**
The `m` command sweeps nine beeps from 22 to 1011 frames — the ceiling being the
ten-bit loop counter's 1023 — timestamps each, and prints raw pairs for fitting
off-device rather than a derived period, since a single point cannot give one.
The first version timestamped with `esp_cpu_get_cycle_count()`, chosen because
the prediction is then an exact integer with no rounding anywhere: 8502 ticks ×
214 APB cycles × 2 = 3,638,856 CPU cycles per frame. The three consecutive
176-frame steps agreed with each other to 1 ppm at 3,630,197 cycles — 2369 ppm
*below* prediction. A wrap can only add time, so the measurement was not merely
wrong but impossible, which is the useful kind of wrong.

**The monitor's own timestamps convicted the instrument rather than the
hardware.** Those come from the host, an entirely separate clock. Each interval
between consecutive `TX done` lines should be the 2 s sweep gap plus about 5 ms
of settle plus N × 22.74285 ms, and all eight matched inside a millisecond, the
longest of them 25 s — which pins the frame period to roughly 40 ppm and says the
divider is 214 and the frame is 22.74285 ms. Dividing the cycle counts by those
durations then reads the counter's rate off directly: 159.621 MHz across the
clean middle of the range, stable to 1 ppm, against a nominal 160.

**`esp_cpu_get_cycle_count()` is not a clock on this part.** It dispatches to
`rv_utils_get_cycle_count()`, which branches on `SOC_CPU_HAS_CSR_PC` — defined as
1 for the C3 in `soc_caps.h` — and on that branch reads CSR 0x7e2, `PCCR`,
Espressif's performance counter governed by `PCER` (which event) and `PCMR` (under
what conditions). The architectural RISC-V `mcycle` path is compiled out. So what
comes back counts a selected event under configurable conditions, not a guaranteed
tick of the CPU clock, and it loses roughly one count in 422. I did not pin down
which event or condition is responsible — that needs the TRM's PCER/PCMR tables —
and it does not change what follows. Dynamic frequency scaling was the first guess
and the data rules it out: a switch between 160 and 80 MHz cannot produce a 0.24%
deficit stable to 1 ppm across three consecutive steps, and no power-management
config is enabled. `getCpuFrequencyMhz()` reported 160 throughout, because it
reports the *configured* frequency and is no evidence at all about the counter.

**The replacement is `esp_timer_get_time()`, for reasons that are properties of
the silicon rather than preferences.** The C3's systimer has exactly one clock
source — `clk_tree_defs.h` declares `SYSTIMER_CLK_SRC_XTAL` and nothing else, with
`DEFAULT` aliased to it — and that is the same crystal the PLL behind the RMT's
APB clock is locked to, so the common-mode cancellation survives the swap. It is
also a free-running peripheral counter, which makes it indifferent to stalls,
clock gating and CPU power state: the entire class of thing that broke the other
one. At 1 µs granularity it resolves 0.04 ppm over a 23 s batch against a 118 ppm
effect. The cycle counter stayed in as a diagnostic printed beside the
microseconds, so the sweep now reports its own reference's rate rather than
assuming it — which is the part worth copying, and exactly what the first version
lacked.

**The wrap is free.** Residuals against the predicted 22,742.85 µs per frame came
out flat — +5.30, +5.60, +6.20, +5.40, +3.80, +4.20, +4.60, +4.85, +4.65 µs across
22 to 1011 frames, a 46× range with no ramp in it. The endpoint slope is −0.66 ns
per frame, and with ±1 µs of quantisation at each end the bound is about ±2 ns.
One APB clock is 12.5 ns, so it is excluded six times over: the peripheral reloads
its read pointer with no bubble and the manual's sentence turns out to be literally
true. The +5 µs common to every point is the fixed software cost at the two ends,
which is where the design intended it to land. Waveform shape at the seam needed
no separate check, because 88 runs starting ON and ending OFF always puts an OFF
run against an ON run there, and two same-level runs merging is the only shape
failure that could hide inside an unchanged duration. The same run also confirms
the realised channel rate at runtime to better than 0.1 ppm, a far sharper check
on the divider than the morning's 3.002 s window, and it settles that the
+14.38 ppm claimed for `SYMBOL_TICKS` is the real figure rather than an arithmetic
one.

**One bug was mine, and it was in the worst place for one.** The first sweep's
summary printed `endpoint dcycles : -704521101` because `Serial.print()` has no
64-bit overload and I had cast a 3.59e9-count span to `int32_t`. The raw pairs
were fine, so nothing was lost — but the only line in the output that looked like
a *result* was the one that was garbage, inside an instrument whose entire job is
to be trusted. Everything wide goes through a `printI64()` helper now, and the
prediction moved to nanoseconds, since 22742.85 µs is a whole number of
nanoseconds and is not one of microseconds: the same divide-last discipline that
disqualified `printState()` as a reference.

**Reviewing the documentation turned up four stale claims rather than the one I
went looking for.** `triggerTransmit()` was renamed `startTransmit()` in the
migration and left standing in the LED section, pointing at a symbol that greps to
nothing. The safety gate described a standalone "flag" that does not exist:
ESPHome keeps running with `is_ready()` false and genuinely needs new trigger
paths put behind it, whereas all three standalone init failures halt in
`while (true)` so `loop()` is never reached and there is no trigger path to guard
— the same guarantee by opposite means. The heartbeat was documented as gated on
`is_ready()` on both paths; only ESPHome's is, and only ESPHome's needs to be. And
the gamma rescaling was documented as having preserved emitted levels, 50%→15% and
80%→54%, while the committed YAML uses 20% everywhere: those figures are the ones
that *would* have preserved the old appearance, and the choice actually taken
unified both solid states onto `LED_LEVEL_SOLID` and moved two levels doing it,
the transmitting blue from 135 to 51. The doc described a decision that was
considered and not made.


### 2026-09-06

The differential campaign closed. Beep and shock, channels A and B, all twenty
shock levels — 42 distinct frames, and a layout in which every one of the 88 runs
is accounted for. The decode is structural rather than a replay for the first
time since the project started.

The session opened on a channel B beep transcription and the first correction was
mine. The recorded B frames sat in canonical form — 31 unit runs, then a double —
and I read that as evidence the cut had needed no rotation. It is not evidence of
anything. The canonical cut is defined on durations alone, and the levels
alternate run by run, so the resulting A/B run string is *invariant* under exactly
the operation I was claiming to detect: two presses of the same button entering
the duration cycle at opposite points produce byte-identical run strings. The
quantity that does carry it is the level the run at the cut actually held, and
across the six presses in `beep_channel_B.cfile` that came out 3 HIGH and 3 LOW —
so half of them had needed the rotation after all. Recognising which quantity is
invariant under the operation in question is the whole of that check.

Verifying it properly meant a second, independent path from IQ to run string:
magnitude envelope, 20 µs boxcar, Otsu threshold per press, run lengths quantised
at 417.294 samples per tick, then the cut. No URH anywhere in it. Run against
`press_shock_A_0/7/18/19.complex` first, where the answers were already written
down, it reproduced all four transcriptions character for character; only then was
it pointed at the new captures. That order is the same guard as the synthetic
ground truth used on `analyze_capture.py` a month ago, and it earned its keep
immediately, because the cut criterion had a bug that would otherwise have read as
a property of the signal. I first required the 31 unit runs to be preceded by a
double — anchoring on the *start* of the visible alternating stretch — and got
zero frames on every file. The stretch at a frame boundary is not 31 runs long: it
is 31 preamble runs plus however many short runs trail the previous frame, which
is data-dependent. The invariant is the *last* 31 unit runs before a double.
Anchored that way it found six to nine frames in every press, byte-identical
within each press, no interior run outside the 1T/2T alphabet across all 41
presses, and maximum quantisation error of 0.03 T on the clean captures.

With that, `press_shock_A.cfile` and `shock_channel_B.cfile` gave twenty levels on
each channel — 21 presses on the A file, the last two byte-identical, so levels 0
to 19 plus a repeat. The eleven A-side levels that already had hand transcriptions
matched exactly, which also confirmed the capture order was ascending.

The beep pair localised the channel first. `Be_A` and `Be_B` differ in exactly four
run positions — 45, 46, 85 and 86 — and both pairs are adjacent transpositions,
`AB` against `BA`, so both beeps come to 21 long runs and 109 ticks. A transposition
conserves the tick count where a true complement of a two-run field would move it
by two, which is worth keeping straight: "complement" in this frame already names
the value/¬value redundancy, and using it for a transposition hides the invariant.
Position 45 falls fourteen runs inside the 36-run block that had been the identity
candidate, which killed "the common block is the remote's identity" as stated. That
block was only ever *invariant under the two axes varied so far*, and channel was
not one of them — the same shape as the `level − 1` failure, arriving on schedule.

Analysing channel B from scratch, without assuming the A-family layout, then
produced the result that made the rest fall out. The A frames satisfy a seven-run
field complemented seven runs later with a flag repeated identically after it. The
B frames do not. They satisfy a *six*-run complement, with the next run copied
rather than complemented and the one after that complemented rather than copied.
Both readings are exact on their own family and both fail on the other, across all
twenty levels. Two mutually exclusive descriptions of the same twenty commands is
not an ambiguity to resolve by preferring one; it is the tell that the description
is in the wrong coordinates.

The move that fixed it was to stop reading the second block as a value and start
reading it as a relation. For each of the eight positions 79 to 86, ask whether it
is a copy or the complement of the position eight runs earlier, and write the
answer out as an eight-character pattern. Every shock frame on channel A gives
`~~~~~~~=`; every shock frame on channel B gives `~~~~~~=~`; the beeps give
`~~~~==~=` and `~~~~===~`. Four positions always complement. The next two
complement for a shock and copy for a beep. The last two are one of each, and
which one decides the channel. So the second block is not a check field at all —
it is the level field re-emitted through a mask, and **the mask is where the
command is restated**. Each command field appears twice: once outright in its own
two runs, and once as a perturbation of the redundancy. A receiver that validates
the two halves against each other reads the command out of the comparison itself,
which buys error detection and addressing from the same bits. That is a genuinely
economical design and it is the find of the session.

The layout, with `A` a one-tick run and `B` a two-tick run:

```
0-30    preamble        31 short runs
31-44   constant        handset
45-46   channel         AB = A, BA = B
47-66   constant        handset
67-68   function        AB = beep, BA = shock
69-70   constant        handset
71-78   level           8 runs, MSB first, B = 1
79-86   redundancy      run 79+i against run 71+i:
                          i = 0..3  always complement
                          i = 4,5   complement = shock, copy = beep
                          i = 6,7   (complement, copy) = channel A
                                    (copy, complement) = channel B
87      constant        always short
```

Sixty-eight of the 88 runs are constant across everything this handset sends. The
other twenty are the whole command surface.

That layout overturns the reading from 2026-09-02, which had a seven-run value
followed by a flag. The level field is eight runs and the flag is part of it. One
observation settles it: levels 0 and 1 differ in exactly one run, the eighth, so
if that run were a flag rather than a value bit the collar could not tell those two
levels apart. The eight-run reading is also the only one that separates all twenty
levels — read as seven runs the map is `0, 0, 1, 2, …`, colliding at the bottom,
where the eight-run map is `0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 21, 25, 33, 41, 57,
77, 117, 157, 202, 209` and strictly increasing, which is what an intensity dial
has to be. The map is still a lookup table with no formula recovered, and it lives
in the *remote* rather than the collar: the handset decides what value to
transmit, so the collar holds a second and separate map from value to electrical
output.

Two things stayed unconstrained rather than unknown, and the distinction matters.
Positions 83 and 84 hold copies where every shock frame holds complements, and on
the beeps the corresponding level runs are both `A` — so "83/84 copies 75/76" and
"83/84 is constant `AA` on beeps" fit identically. There is exactly one observation
of the beep tail, because the two beep frames differ only in the four channel
positions, and the beep has no level to vary. No further beep capture can help.
Likewise, runs 69 and 70 not moving is evidence they do not distinguish beep from
shock, and nothing more; a third function would be needed and this handset has
only two. A field with one observation is not weakly constrained, it is
unconstrained, and more of the same capture will never touch it.

Neither does the channel or the function field ever take `AA` or `BB` — only the
two transposed values, in the direct fields and in the mask alike. Two readings fit
and 42 frames cannot separate them: two-bit fields with two spare states, leaving
room for two more functions and two more channels, or one-bit fields in a balanced
1-of-2 code where `AA` and `BB` are invalid codewords and there is no headroom at
all. The d-control range includes models with more channels, so a higher model in
the family would settle it.

A question that came up late is worth writing down because the obvious answer is
wrong. It looked as though a frame could simply be rotated — move the trailing
short run to the front so the preamble reads 32 — with no consequence. For a
single isolated frame that is false, and visibly so: `AABBABA` and `AAABBAB` are
different transmissions. What makes the rotation free is that the object being
described is not a frame but a periodic stream, and a frame is a window on it.
Repeat both and the second is the first shifted by one run, with an `A` prepended
and an `A` dropped from the tail; every interior run boundary is in the same place.
The assumption doing the work is therefore the burst-contiguity finding from
2026-08-11: a single frame is never transmitted, because one frame followed by a
gap produced zero beeps. So for analysis a rotation is free bookkeeping. For the
firmware it is not — `signal.h` holds one frame and repeats it, so rotating the
stored payload really would shift the emitted burst by one run at each end. Almost
certainly harmless, and still a change to the air rather than to the description.

What is left needs hardware rather than analysis, in descending order of value. A
second remote would split the 68 constant runs into what differs between handsets
(identity) and what agrees (protocol framing) — and that is the assumption the
project's scope note has rested on from the start without ever being tested. It
carries a confounder: two remotes may also differ by firmware revision, since
remote and collar ship as a pair, and a revision field would appear in the same
diff. A third handset disambiguates, and so does the shape, an identifier being
likely contiguous where a revision counter sits apart and stays small. Second is
whether a formula sits behind the level-to-value map: if the transmitted value is a
physical quantity — pulse width being plausible for a switched source — the table
is samples of a curve, and testing that means putting a scope on the collar's
output rather than capturing more RF, so it needs no purchase at all. Third and
highly optional is whether the two-collar limit is enforced by the protocol; nothing
in the frame enforces it, so two collars paired to one channel should both fire.

The repository caught up with all of this. The schema above is now in the README
and `CLAUDE.md`; the 68 constant runs and the level table stay in
`signal_captures.txt`, which is sops-encrypted under the same age recipient as
`include/signal.h` rather than relying on a `.gitignore` pattern that never matched
it. That split is deliberate: the schema is protocol structure that anyone with
this model and an SDR can rediscover, while the constants are one handset's
identity and are the only thing that makes a frame this remote's. Also corrected: the
README had described the transmission as mimicking a PWM bit-stream. It does not.
PWM requires exactly half the runs to be long and the real frames have 21 long runs
out of 88 — the count that killed PWM on 2026-09-02 had simply never made it into
the public document.

The last piece was a `pre-commit` hook refusing to commit either encrypted file in
plaintext, checking the staged blob rather than the working tree — a decrypted
working copy with ciphertext staged is fine, and the reverse is the accident being
guarded against. It detects encryption by looking for sops's own `"sops"` key and
`ENC[AES256_GCM` envelope, so it needs no age key. Installing it caused the one
real failure of the session, and it was a fork bomb: roughly 3000 processes in two
minutes. A repo-local `core.hooksPath` replaces the global one rather than adding
to it, so I wrote a `prepare-commit-msg` shim to chain through to the global
commit-message generator. But that generator already chains the *other* way, into
the repo's local hook, resolving it with `git rev-parse --git-path
hooks/prepare-commit-msg` — which honours `core.hooksPath` and therefore resolved
straight back to the shim. Shim execs global, global calls local, local execs
global. The generator's own guard compares the resolved local hook against `$0` and
correctly answers "that is not me", because it is not; a two-hop cycle is invisible
to a one-hop check. An environment variable set before the exec breaks it on second
entry. The deeper mistake was procedural rather than technical: I had tested the
`pre-commit` half against four known cases and enabled the pair, having never
exercised the shim at all. A partial test read as a passing one.

### 2026-09-02

Carried on with the differential shock campaign, exporting more levels out of URH
— channel A levels 0 through 4 first, then 5, 6, 7, 10, 18 and 19 — and pasted
the beep frame from `include/signal.h` in beside them as a reference. Almost all
of the session went on getting those transcriptions onto a common footing.
Comparing them was quick once they were comparable, and the interesting mechanism
was in the "once".

The first thing wrong was that some frames looked inverted, and one of them also
had a preamble a tick shorter than the rest. Those turned out to be a single
observation rather than two. On an alternating run, inverting and shifting by one
tick are the *same* operation, so their composition is the identity there — the
flip is invisible across the whole preamble, and its only trace is the point
where the alternation breaks, which moves by one. It was also not one odd frame
out of five: levels 0 and 4 sat in one polarity and the beep with levels 1–3 in
the other, a 4:2 split rather than an outlier.

Working out where a frame legitimately starts came from OOK physics rather than
from the data agreeing with itself. The carrier goes from silence to HIGH, so the
first tick of a frame is fixed. The next frame's preamble also starts HIGH, and
two adjacent HIGH runs would merge into one, so a frame has to *end* LOW. A
preamble is alternating single ticks by definition, so a double run cannot live
in one and must belong to data — which means the last double before a preamble is
the current frame's, and it cannot be halved because that would leave the frame
ending HIGH. Those constraints pin the boundary exactly, and the result is a
frame of **88 runs, starting HIGH, ending LOW, no run longer than 2T**. I had
been reaching for a weaker argument first — that a correct frame is the one that
tiles back-to-back without merging runs — which reaches the same criterion but
justifies it by self-consistency rather than by the channel.

That criterion is necessary and not sufficient, and the gap is exactly the
polarity problem. It fixes *where the periodic stream is split* and says nothing
about which position of the transmitter's duration cycle a given press entered
on, which is a second, independent free parameter. The quantity that carries it
is the count of unit runs before the first double: the first run is HIGH by
physics and the levels alternate run by run, so run *i* is HIGH exactly when *i*
is even, and the parity of the preamble length is what decides whether the first
double lands on carrier or on silence. Counts came out 31 for the beep and levels
1–3, 32 for levels 0 and 4 — same criterion satisfied, opposite phase.

Normalising it took two false starts, both instructive. Moving the
preamble/payload marker buys nothing, because the physical constraints above
already pin the marker *given* the tick string — there is no freedom left in it,
which is why the attempt produced a frame with implausible field lengths and a
byte-identical bit string. Complementing every tick does nothing either, and for
a sharper reason: complementing moves no run boundary, and the phase *is* how
many runs precede a given run. Checked directly, `comp(L4)` still had 32 unit
runs before its first double, and it started LOW and ended HIGH, failing both
physical constraints. The operation that works is a rotation of the duration
list — take the 88 durations, move the first to the end, re-render with the first
run HIGH — which in tick terms is: drop the first tick, complement the rest,
append one `0`. The complement is present but it is the shift doing the work.
This is the transmitter's own degree of freedom, recorded on 2026-08-11: it emits
durations and toggles a pin, so entering one position later is a genuinely
different waveform carrying the same code.

With every frame normalised, the encoding fell out of a census with no decoding
at all. Levels carry nothing — two adjacent runs at the same level would merge,
so the level sequence is fully determined by the first one — which immediately
kills NRZ, Manchester, PWM and PPM, all of which need the level to mean
something. That leaves biphase and run-length, and those two are separated by one
pair of numbers: biphase fixes ticks-per-bit and lets the run count float,
run-length does the reverse. Every frame measured came to **88 runs** with tick
counts of 109, 111 and 113, across two functions and eleven levels, and
`ticks = 88 + (number of 2T runs)` holds as an identity. It is run-length. The
same counting killed a PWM-style short+long pair per bit outright: that requires
exactly half the runs to be long — 44 of 88 — and the measured counts are 21 for
the beep and 23–25 for the shock frames.

This also corrects the headline from 2026-09-01, which had shock level 0 at 111
ticks and **89** runs against the beep's 109 and 88. The 89 was the phase artifact
— a cut through a double, splitting it into a leading and a trailing half. Every
frame is 88 runs; what varies is how many of them are long.

The field layout then came out of diffing the levels against each other, in run
space rather than tick space. A tick-indexed diff is the wrong instrument here: a
single short↔long change shifts every downstream tick by one position, so the
comparison goes out of alignment at the first difference and reports the whole
remainder as changed. The 88-element duration sequence has no such problem — it
is the same length for every frame and index-aligned end to end. The layout:

```
31 preamble | 40 common | 7 value | 1 flag | 7 = ¬value | 1 = flag | 1 short
```

The complement is exact on all eleven shock frames, including three that were
held out of the fit. Two different redundancy schemes sit side by side: the value
is duplicated *inverted*, the flag is duplicated *identically*. A complement
guards against a stuck slicer; a plain repeat only guards against a dropped run,
so the transmitter is treating them as different kinds of field.

The value is not the level. Fitting `value = level − 1` on levels 0–7 and holding
19 back predicted 18 and got 104. The failure mechanism is worth keeping: levels
0–7 produce values 0–6, which only ever exercise the bottom three bit positions
— the top four had *zero* observations, so the rule was not wrong about them, it
was unconstrained. Level 10 then read 10 rather than the predicted 9, killing
`level − 1` outright. The remaining worry was whether 104 was real or a
mislabelled capture, and the test for that is adjacency: an intensity dial has to
be monotone and reasonably smooth between neighbouring settings, so if 104 belongs
to the same table its neighbour must be close to it. Level 18 came in at 101. The
map is a nonlinear lookup table — `0, 0, 1, 2, 3, 4, 5, 6, …, 10, …, 101, 104` —
with no formula to recover, which is a real answer rather than a gap.

The flag survived two readings and one reproducibility check. "Level > 0" died on
level 18, which reads `A` like level 0. "Derived from the value" died on levels 0
and 1, which have byte-identical value fields and different flags, so no parity or
checksum over the value can produce it. Then five separate presses of level 18,
recorded as raw demodulations of varying quality — 778 to 827 ticks, two opening
with a 5-tick run of junk longer than the 2T alphabet allows, one starting
mid-frame on a `0` — normalised to a single byte-identical frame, value `BBAABAB`
(101), flag `A`, five for five. That check was worth doing rather than assuming,
because this project has already found one field that varies press to press and
not with the message: the A/B duration phase, 8 A and 5 B across 13 presses of the
same beep button. The flag is not that; it is level-determined and unexplained.

Finally, beep against shock, using data already on the table. Re-cutting the beep
to the canonical 31-unit-run form is a rotation by **two** runs, and an even
rotation preserves every level assignment where the odd one used for the phase fix
flips them all. Aligned, the two differ in exactly six run positions: 67 and 68
inside the common block, and 78, 83, 84 and 86 in the tail. Thirty-eight of the
forty common runs are identical between a beep and a shock, so whatever selects
the function is two runs wide and sits at the end of the common block. The
complement relation also fails for the beep — value `AAAAAAA` against a check
field of `BBBBAAB` rather than `BBBBBBB` — so those seventeen tail runs are not
doing the same job in a beep frame as in a shock frame.

Two things parked rather than solved. The visible alternating stretch at a frame
boundary is not a fixed length: it is the 31 preamble runs plus however many short
runs trail the *previous* frame, which is data-dependent — 32 when the flag is
`B`, 34 for level 18, whose frame ends on three shorts. So "the longest
alternating run is the preamble" gives a different answer per level, and the
invariant to cut on is 31 unit runs immediately before the first double.
Separately, the first frame of several recordings carries a preamble two runs
longer than the rest, along with trailing alternating fragments after the last
frame; a longer opening preamble for receiver acquisition is a normal design, but
two ticks against a 6.7 ms preamble is thin, and one raw capture is exactly
periodic from tick zero, so it may be a demodulator edge effect. It needs checking
against the raw captures rather than the cuts.

Still outstanding and not fixed: `.gitignore` has the pattern `signal_captures`,
which matches only a path named exactly that, so `signal_captures.txt` is
untracked and *not* ignored. It wants to be `signal_captures*` — the file now
holds decoded shock frames for eleven levels of one physical remote, in a public
repo. Channel B is not captured yet, and is the next axis: it is what separates
the remote's identity, invariant across everything this handset sends, from the
command fields, which is currently the whole content of those forty dark runs.

### 2026-09-01

Started the second open TODO — the differential shock capture — with 20
recordings already in hand (channel A, levels 0 through 19) and no memory of how
the URH side of the beep analysis had been done. It turned out that not
remembering was the honest position, because the previous URH work was hand
measurement in the signal view only: select a region, read a sample count,
distrust every automatic feature. Twenty levels is a different job. It is not
measuring, it is diffing, and 20 × 88 runs does not go by eye — so this session
needed URH's demodulator, which meant trusting it, which meant configuring it
from scratch. About two hours went into settings the data could not supply and
the tool would not name.

The four stages of the Interpretation tab are envelope, noise gate, symbol slot
and centre slicer, and none of them is a measurement — every one is asserted,
and the tool produces confident-looking output from wrong ones. The first
correction was structural: in OOK the `0` symbol *is* the absence of carrier, so
the OFF level inside a frame and the silence between presses are the same
physical quantity. Measured, they were −24.4 dBm and −24.4 dBm. No setting of
the noise gate can separate those, because there is nothing there to separate;
what separates them is duration, 2 ticks against a second, six orders of
magnitude with zero amplitude difference. Cropping each press into its own
signal by hand does not work around that bind, it dissolves it — on a cropped
signal the gate has no segmentation left to do and can be driven far below the
OFF plateau and forgotten.

The longest detour was a two-times factor that turned out to be a display
setting. A `.complex` from a GNU Radio file sink is raw interleaved floats with
no header, so URH cannot read the sample rate from the file; it holds its own
value, defaults to 1 MSps, and uses it for exactly one thing — converting sample
counts into times for display. It touches no bit. So a 2 MSps capture read
through a 1 MSps setting shows every duration wrong by a factor of two while
every sample count stays exactly right, and I spent a while arguing from the
millisecond figures before noticing that 342446 samples were being reported as
342.45 ms. My own first conclusion from that was wrong in the other direction —
I read the durations as truthful and proposed halving Samples/Symbol to 209,
when the file really was 2 MSps and the correct answer was the 417 already
there. The mechanism worth keeping is what makes both errors impossible:
**Samples/Symbol is a count of samples, and the sample rate does not enter into
it.** A 208.647 µs tick occupies 417.3 samples in a 2 MSps file whatever URH
believes the rate to be. Measuring in samples is immune to the whole class of
mistake, and that is why the resolution was a hand measurement of run widths
rather than an argument about rates.

Hand measurement of ten to fifteen runs gave two clusters, ~417 and ~834
samples, on both the ON and the OFF side, with nothing between and nothing
longer — the beep's alphabet exactly, and the first fact about the shock signal
that was measured rather than assumed. Both readings came in slightly high, 209
and 418 µs against derived 208.647 and 417.294, which is the expected
edge-to-edge bias: catching the rise at one end and the fall at the other. That
consistency is a better outcome than hitting the number, because the residual is
explained rather than lucky. Getting the precise tick by hand is not a matter of
measuring one run more carefully — the uncertainty is in the rendering, not the
mouse. It comes from spanning many periods and dividing, which is what the
beep's 272910 samples across 654 ticks did: a ±10 sample endpoint error becomes
±0.015 samples on the answer, and taking both endpoints at the same structural
position makes the rise-time bias cancel instead of add.

Setting Samples/Symbol to the shortest run rather than to a high+low pair was a
deliberate choice and worth recording with its reason. In a real line code a
symbol is a pair, and slotting at the pair period is right — but which line code
is exactly the unknown this capture campaign exists to resolve. Slot at the
shortest run and the output is an uncommitted transcription of the level
sequence at tick resolution, against which any encoding hypothesis stays
testable; slot at an assumed pair period and a guess has been baked into what
gets treated as raw data afterwards. That is the same class of mistake as the
two-bucket classifier this project spent a session suspecting.

The expensive dead end was the dBm readout. The info bar reports a level for the
current selection, the plateaus measured −11.32 and −24.15 dBm, and converting
those into the Noise and Centre boxes felt like arithmetic. It is not: the
readout is `20·log₁₀(magnitude)` plus an undocumented offset, about 19 dB on this
capture, so an absolute conversion gave 0.266 for a centre whose true value was
near 0.05. Two attempts failed, the first because I framed the choice as
amplitude-ratio versus power-ratio when the real question is what the conversion
targets — power goes as amplitude squared, so recovering an *amplitude* from a
power figure is /20 regardless of the readout being labelled in dBm. That
correction was right and still produced a wrong number, which is what finally
pointed at the reference offset. The tell had been visible throughout: every
*ratio* taken from those figures checked out and every *absolute* did not. The
12.8 dB plateau separation was real. Mixing the two plateau powers at 50/50 duty
predicted the whole-press figure of −13.95 dBm to within 0.16 dB, back-solving to
52% ON, against 53.2% counted from the decoded bits afterwards — two independent
measurements, one RF power and one a bit census, agreeing to about a percent.
Ratios survive an unknown reference; absolute levels do not.

Three separate things were keeping the Demodulated view blank, and I twice told
myself to abandon it before working out that it is the only instrument in the
window calibrated in the units the Noise and Centre boxes actually take.
Switching the view resets the x-range, so zooming first loses it. At full
zoom-out a press across ~1400 px is ~240 samples per pixel against a 417-sample
tick, so every pixel column holds both levels and renders as one solid smear.
And the Analog view auto-scales to the data while the Demodulated view spans a
fixed 0–1 — with an envelope peaking near 0.05 the whole trace sits in the bottom
few percent as a flat line on the floor, needing 25–50× vertical magnification
rather than a nudge. That asymmetry is why the analog view looked healthy
throughout while the demodulated one looked broken. It was never broken. View,
then zoom, then Y-Scale, and two clean plateaus appeared immediately.

One threshold trap is worth stating separately because it nearly repeated the
shredding: the dBm figure for the OFF state is the mean of a distribution, not a
floor. OFF is the envelope of thermal noise, Rayleigh distributed, straddling
its mean broadly with roughly half its samples underneath — so a gate placed
"just below the OFF level" lands inside that distribution and classifies a large
fraction of OFF samples as pause. Below the distribution, not below its mean.
Centre placement mattered less than expected, and the reason is worth knowing:
URH decides over a run of ~417 samples rather than per sample, averaging the
noise down by √417 ≈ 20×, so the margin is tens of standard deviations wide and
anything in the broad middle works. The confirmation of that came for free —
the bit string at Centre 0.0100 was byte-identical to the one at 0.0325, a
factor of 3.25 with not one bit flipped.

The decode itself then fell out in one step. Every frame opens with a preamble,
and at tick resolution a preamble is unmistakable — the longest run of
alternating `1010101010…` in the string. Two successive preamble starts give the
frame period; cutting the message at that period and stacking the copies gives
the verification. Seven byte-identical frames, which is the strongest check
available in the chain and costs nothing: the crop, the sample rate, the slot
width, the centre and the gate would all show up as divergence between copies
long before anything was visible by eye. It also settled the drift question I
had raised, that a slot of 417 against a true 417.294 would accumulate to a
couple of full ticks across seven frames. It does not, so URH slices on detected
edges rather than a rigid grid.

Shock level 0 on channel A: **111 ticks per frame, 89 runs, maximum run 2, 53.2%
ones**, against the beep's 109 ticks and 88 runs. Same tick, same run alphabet,
two ticks and one run longer. The preamble came out 34 ticks against the beep's
42, but that split is a judgement call — the alternation runs one tick further
before `11` breaks it, and the beep's 42 was drawn by the same eye. The frame
*period* is not a judgement call: it is fixed by copies at that spacing coming
out identical, and it is the number to compare on. What the two-tick difference
means is the open question, and it needs the other 19 levels beside it rather
than more analysis of this one.

Closed by writing the procedure up as `notes/urh-ook-capture-analysis.md` and
linking it from the top of the project note, since the session's real cost was
rediscovering settings that the transcription file cannot record. The
transcription now carries its URH settings in a header for that reason, and was
added to `.gitignore` rather than committed — it is a decoded shock frame for
one physical remote in a public repo, which is the thing `signal.h` is
sops-encrypted to avoid. Three of the four traps in that note share a shape:
a number that looks like a property of the signal is actually a property of the
tool's display. The defence is to carry the physical invariant rather than the
number — 208.647 µs survives a re-capture at a different rate; "417" quietly
becomes wrong.

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
