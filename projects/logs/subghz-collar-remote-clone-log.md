---
tags: [log, subghz-collar-remote-clone]
project: subghz-collar-remote-clone
---

# subghz-collar-remote-clone — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[subghz-collar-remote-clone]].

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
