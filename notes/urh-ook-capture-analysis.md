---
tags: [note, rf, sdr, urh, ook, subghz, analysis]
created: 2026-09-01
---

# Analysing an OOK Capture by Hand in URH

Reference note. The procedure behind [[subghz-collar-remote-clone]] — turning
an RTL-SDR IQ recording of a fixed-code OOK remote into a tick-accurate bit
transcription, without letting the tool guess anything.

Written from the 2026-09-01 session, where the shock capture was decoded for
the first time. Roughly two hours of that session went into settings that the
data could not tell us and the tool would not name, so this is mostly a record
of which numbers mean what — and of the four traps that cost the time.

## What URH actually does to your signal

The Interpretation tab is four stages, and **none of them are measurements**.
Every one is a value you assert, and the tool will happily produce
confident-looking output from wrong ones.

1. **Envelope.** For ASK it computes `|I + jQ|` per sample — the magnitude of
   the complex baseband sample. This is what everything downstream thresholds.
2. **Noise** — the *gate*. Magnitude below it means "no carrier at all". Not a
   `0`, an **absence**. Sub-noise regions become **pauses**, and pauses are what
   split a recording into separate messages.
3. **Samples/Symbol** — the slot width. URH slices the above-gate signal and
   emits one bit per slot.
4. **Center** — the *slicer*. Of what survived the gate, above is `1`, below
   is `0`.

The two thresholds do different jobs on the same axis, which is why setting
them to the same number does not necessarily break anything: the gate only has
to be *under* the OFF plateau, while the slicer has to be *between* the
plateaus. One value can satisfy both.

**The output is one bit per tick, not one bit per protocol symbol.** A 2-tick
ON run comes out as `11`. The bit string is a run-length transcription written
longhand, and that is deliberate — see step 4.

## The procedure

### 1. Crop each press into its own signal, by hand

Select one press in the recording and *Create signal from selection*.

**Why, and not the noise gate.** In OOK the `0` symbol *is* the absence of
carrier, so the OFF level inside a frame and the silence between presses are
the same physical quantity — measured at −24.4 and −24.4 dBm respectively on
this capture. **No setting of the noise gate can separate them**, because there
is nothing there to separate. Amplitude cannot do this job at all.

What *does* separate them is duration: the longest OFF run inside a frame is
2 ticks (~835 samples), while the gap between presses is on the order of a
second. Six orders of magnitude, and zero amplitude difference.

So segmentation has to be done by duration or by hand, and by hand is one drag
of a mouse. This is not a workaround — it **dissolves the whole OOK bind**. On
a cropped signal the gate has no work left to do, so it can be driven far below
the OFF plateau and forgotten about, instead of being tuned into a window it
may not even have.

### 2. Set the sample rate, knowing it changes nothing

Signal details (the blue **i** button) → sample rate.

**A `.complex` from a GNU Radio file sink is raw interleaved floats. No header,
no metadata, nothing that records the rate.** URH cannot read it from the file;
it holds its own value and defaults to 1 MSps.

That value is used for exactly one thing: **converting sample counts into times
for display.** It touches no bit. But if it is wrong, every millisecond and
microsecond on screen is wrong by that ratio, silently and plausibly.

Set it right anyway, because you are about to want durations you can trust.

### 3. Measure Samples/Symbol — in samples

Zoom in (X-Zoom until a tick is tens of pixels wide), select single runs, read
the **samples** figure from the info bar. Measure ten or fifteen across the
press.

**It is a count of samples. The sample rate does not enter into it.** A
208.647 µs tick occupies 417.3 samples in a 2 MSps file whether URH believes
the rate is 2 MSps, 1 MSps or 40 Hz. This is the one quantity in the panel that
no display setting can corrupt, which is exactly why you measure in it.

What you are looking for is the **run alphabet**: how many distinct clusters,
and where. This remote has two — ~417 and ~834 samples — on both the ON and the
OFF side, with nothing between and nothing longer. A third cluster would be a
far more interesting finding than anything further down this list.

⚠️ **Never use *Autodetect parameters* for this.** It reported 400 against a
true 417.294 — 9% off — because it fits a symbol length rather than measuring
one.

### 4. Set the slot to the *shortest* run, not to a symbol pair

Type the short-run count (here 417). Not the pair period.

**Why, when a "symbol" in a real line code is a high+low pair.** Because that is
a *decoding* decision, and the encoding is precisely what you do not know yet —
it is the thing the whole capture campaign exists to find. Slot the signal at
the shortest run and URH's output is an **uncommitted transcription** of the
level sequence at tick resolution, against which every encoding hypothesis stays
testable. Slot it at an assumed pair period and you have baked a guess into
what you will later treat as raw data.

Also worth dispelling: a symbol here is not a carrier cycle. This is
**baseband IQ** — the tuner already mixed 869.525 MHz down to near zero, so
there are no carrier cycles in the file. One would last 1.15 ns and need a
sample rate above 1.7 GSps to see. Each sample is an amplitude-and-phase
measurement of the envelope, nothing more.

### 5. Getting a precise tick: span many periods, divide

You cannot get better than about a percent from one run measured edge to edge.
The uncertainty is in the rendering and in where a rise "starts", not in your
mouse, so no amount of care fixes it.

**Measurement error divides by the number of periods you span.** Take both
endpoints at the *same structural position* (frame-start to frame-start, both
rising edges) several frames apart and divide by the tick count between them.
A ±10 sample endpoint error across 654 ticks becomes ±0.015 samples on the
answer. Same mouse, two orders of magnitude better.

Taking both endpoints at the same structural position is what makes the
rise-time bias **cancel** rather than add. Measuring edge-to-edge on a single
pulse biases high by the rise plus the fall — which is visible in practice:
hand measurements of this remote read 209 and 418 µs against derived values of
208.647 and 417.294, both biased high, consistently.

### 6. Make the Demodulated view readable — view, then zoom, then Y-Scale

Signal view → **Demodulated** *first*, then set X-Zoom, then drive the
**Y-Scale slider hard toward the top**.

Three traps stacked here, and together they cost most of the session:

- **Switching the view resets the x-range.** Zoom first and you lose it.
- **At full zoom-out the plot is meaningless.** A whole press across ~1400 px
  is ~240 samples per pixel against a 417-sample tick, so every pixel column
  contains both levels and renders as one solid smear. Zoom to about one frame.
- **The Analog view auto-scales to the data; the Demodulated view does not.**
  It spans the full 0–1 range. With an envelope peaking around 0.05 the entire
  trace lives in the bottom few percent and draws as a flat line on the floor.
  It needs 25–50× vertical magnification, not a nudge.

That asymmetry is why the analog view looked perfectly healthy throughout while
the demodulated view looked broken. **It was never broken.**

And the demodulated view is not optional decoration: it is the **only
instrument calibrated in the units the Noise and Center boxes take.** Everything
else in the window reports on a different scale.

### 7. Place the thresholds

**Noise: an order of magnitude below the OFF plateau.** On a cropped signal
there is no cost to going low, and there is a real cost to going high.

⚠️ The dBm figure for the OFF state is the **mean of a distribution, not a
floor.** The OFF state is the envelope of thermal noise, which is Rayleigh
distributed and straddles its mean broadly — roughly half its samples sit
underneath. A gate placed "just below the OFF level" lands *inside* that
distribution and classifies a large fraction of OFF samples as pause, shredding
one message into hundreds of fragments. Below the *distribution*, not below its
mean.

**Center: the middle of the working band, found by sweeping.** Raise it until
the output goes all-`0` (slicer above the ON plateau), lower it until the
output goes all-`1` (slicer below OFF), and sit midway.

The sweep is not a fallback — it is a **measurement of both plateaus in the
box's own units**, using the decoder itself as the instrument. Its edges *are*
the two levels, and their ratio should match the plateau separation measured
independently in dB (12.8 dB → 4.4× here).

Geometric or arithmetic midpoint? Geometric gives equal *ratio* margin,
arithmetic gives equal *absolute* margin. Which is right depends on what could
flip a bit: multiplicative perturbations (fading, gain drift) want geometric,
additive ones (thermal noise, the same absolute size on both plateaus) want
arithmetic. Here it does not matter, and the reason is worth knowing: **URH
decides over a run of ~417 samples, not per sample**, which averages the noise
down by √417 ≈ 20×. The margin is tens of standard deviations wide either way.

### 8. Error tolerance: leave it at 5

A debounce on edge detection. URH walks the envelope looking for center
crossings; an excursion shorter than this many samples is treated as a glitch
rather than a level change. Without it a noisy envelope chattering across the
center manufactures a spray of one-sample runs at every transition.

At 5 samples against a 417-sample tick it filters at 1.2% of a symbol. It is
**not** a knob for fixing a bad decode: if the center is misplaced there are no
crossings to debounce.

⚠️ It is not free to zero, either. At Error tolerance 0 the beep capture
silently lost five bits and produced seven frames that disagreed with each other
while still looking entirely plausible.

### 9. Read the frame out and verify by repetition

Every frame opens with a preamble, and in a tick-resolution transcription a
preamble is unmistakable — the longest run of alternating `1010101010…` in the
string. Find two successive preamble starts, count the bits between: that is the
frame period.

Then cut the message into copies of that period and **stack them**.

**Byte-identical copies is the strongest validation in the whole chain**, and it
is free. Every setting upstream — the crop, the sample rate, the slot width, the
center, the gate — would show up as divergence between copies long before it
showed up as anything visible by eye. In particular it settles the accumulated
drift question: a slot of 417 against a true 417.294 would grow to a couple of
full ticks across seven frames, so if the seventh copy matches the first, URH is
slicing on detected edges rather than a rigid grid and **nothing accumulates**.

It is also self-referential in the good way — it needs no external ground truth,
no decoded model, no second tool. The same class of check that caught the
burst-contiguity bug on this project two sessions running.

## The trap that cost the most: dB has a reference you do not know

URH's info bar reports a level in **dBm** for the current selection. It is
tempting to convert that straight into the Noise and Center boxes. It does not
work, and it fails in a way that looks like arithmetic error rather than a
category error.

The readout is `20·log₁₀(magnitude) + some offset`, and **the offset is not
documented and not derivable from the data.** On this capture it amounted to a
factor of roughly 9 — about 19 dB — between the dB scale and the box scale.

So:

- **Differences in dB transfer perfectly.** The 12.8 dB separation between the
  ON and OFF plateaus is real and usable.
- **Absolute values do not transfer at all.** Converting −11.32 dBm to a Center
  value produced 0.266 against a true figure near 0.05.

The pattern was visible in the evidence the whole time, which is the lesson:
every *ratio* derived from those dB figures checked out, and every *absolute*
did not. Mixing the two plateau powers at 50/50 duty predicted the whole-press
figure of −13.95 dBm to within 0.16 dB, back-solving to 52% ON — against 53.2%
counted from the decoded bits afterwards. Two completely independent
measurements, one from RF power and one from a bit census, agreeing to about a
percent. Meanwhile both attempts at an absolute conversion were wrong.

**Ratios survive an unknown reference. Absolute levels don't.** Use the dB
readout for separations, duty cycles and sanity checks; get absolute thresholds
from the demodulated view or from the sweep.

## The general shape of it

Three of the four traps in this note have the same structure: **a number that
looks like a property of the signal is actually a property of the tool's
display.**

- Samples/Symbol looked like a duration; it is a count, and the rate that turns
  one into the other lives in a settings box, not in the file.
- The dBm readout looked like an absolute level; it is a ratio to an unnamed
  reference.
- The Demodulated view looked empty; it was drawn on a fixed scale while its
  neighbour auto-scaled.

The defence is the same in each case: **carry the physical invariant, not the
number.** The tick is 208.647 µs — that survives a re-capture at a different
rate, a different tool, a different day. "417" does not, and quietly becomes
wrong the moment anything upstream changes.

## Worked result — what this produced

Channel A, shock, level 0, RTL-SDR at 2.000 MSps:

| | Beep (2026-08) | Shock level 0 (2026-09-01) |
| --- | --- | --- |
| Tick | 208.647 µs | same |
| Run alphabet | 1T, 2T only | same |
| Frame period | 109 ticks | **111 ticks** |
| Runs per frame | 88 | **89** |
| Preamble | 42 ticks | **34 ticks** |
| Duty | — | 53.2% ones |

Working URH settings: Noise 0.01 · Center 0.035 · Samples/Symbol 417 · Error
tolerance 5 · ASK · Bits/Symbol 1 · sample rate 2 MSps · Demodulated view.

⚠️ Note that the preamble boundary is a **judgement call** — the alternation
runs one tick further before `11` breaks it, and the beep's 42 was drawn by the
same eye. The frame *period* is not a judgement call: it is fixed by the fact
that copies cut at that spacing come out identical.

## What this note deliberately does not cover

Turning the tick transcription into protocol bits — the encoding, the field
layout, the checksum. That needs the differential family (all 20 levels, then
channel B), not a better procedure, and it is
[[subghz-collar-remote-clone]]'s next open item.

⚠️ Capturing shock frames implies being able to transmit them. The collar must
not be worn by an animal during this work. Decoded transcriptions stay out of
the public repo, for the same reason `signal.h` is sops-encrypted.
