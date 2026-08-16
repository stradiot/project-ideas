---
tags: [project, hardware, analog, rf]
status: idea
depends: []
created: 2026-08-07
---

# Analog AM — From Crystal Set to Walkie-Talkie

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Understand radio as physics rather than as a library call. AM is the
simplest modulation there is — a carrier whose amplitude follows the audio
— so it can be built out of a coil, a capacitor and a diode, tuned by hand,
and watched on a scope. Nothing here is written against someone else's
driver.

Two things get kept at the end, and they are both receivers: a regenerative
shortwave set in a box that gets listened to, and a DCF77 clock that sets
itself and lives on the office desk.

Deliberately out of scope: precision, audio quality, and anything needing
an instrument I do not own. No crystal ovens, no impedance-controlled
boards, no surface mount.

### What is actually receivable

The obvious plan — tune in a local AM station — no longer works here.
Slovakia switched off both of its mediumwave transmitters on 31 December
2022 (Košice 702 kHz and Nitra/Jarok 1098 kHz), and most of western Europe
went dark earlier. There is nothing local left to hear.

What still exists, and what this project actually targets:

| Band | What is there | Notes |
| --- | --- | --- |
| Mediumwave, at night | Skywave from Hungary, Poland, Romania, Spain | Dead in daylight, loud after dark — the ionosphere is part of the experiment |
| Shortwave, 49 / 41 / 31 m | International broadcasters, still active | Needs the regenerative stage and a longer wire |
| 27 MHz CB | Other people, and eventually me | Licence-exempt, and the band I transmit on |
| 77.5 kHz | DCF77 time signal from Mainflingen | Always on, always receivable, and decodable |

The night-time-only behaviour of mediumwave is not a disappointment. It is
the single most direct demonstration of propagation there is.

## Learning value

- Resonance in practice — winding a coil and tuning a tank until a station
  appears
- Amplitude modulation and envelope detection, built from parts
- Gain, selectivity and why a crystal set needs neither a battery nor an
  amplifier to work
- Harmonic filtering on a transmitter output, and why it is mandatory

## Practical value

Split, and only the receiving half has any. The regenerative shortwave set
is a radio that gets listened to, and the DCF77 clock sets itself off a
transmitter in Mainflingen and sits on the office desk — both are things
that stay in use after the learning is done.

The transmitting half has none and is not pretending otherwise. Two 27 MHz
handsets that reach across a street are worse in every way than the phones
already in both pockets. That stage exists because building a transmitter
is the only way to be made to care about harmonic filtering and duty cycle,
and it is kept deliberately small for the same reason.

## Architecture

Four stages, each working on its own before the next one starts.

### Stage 1 — Crystal set

LC tank, germanium diode, high-impedance earpiece. No power supply at all —
the received signal itself drives the earpiece. Coil wound by hand on a
ferrite rod, tuned with a variable capacitor, fed by as long a wire antenna
as the flat allows.

Success: sweep the capacitor after dark and hear a station appear.

### Stage 2 — Regenerative receiver

One transistor with controlled positive feedback. The regeneration control
takes the stage right up to the edge of oscillation, where gain and
selectivity both peak — the clearest possible demonstration of what
feedback does, because it is adjusted by hand while listening.

This is what reaches the shortwave broadcast bands, and it is **built as a
keeper** rather than as a breadboard step: a proper chassis, a tuning dial
worth turning, a real audio stage and a speaker. Shortwave broadcasting is
still alive on 49, 41 and 31 m, and a hand-built regen set is a thing people
genuinely sit and listen to. Building it to be dismantled would waste the
one stage here with a lasting product at the end of it.

### Stage 3 — Transmitter

27 MHz oscillator, crystal-controlled for stability, with the audio
modulating its amplitude.

The output filter is not optional. A bare oscillator radiates strong
harmonics — at 54 MHz, 81 MHz and upward, straight into bands where they
have no business being. A pi-network low-pass filter on the output fixes
that, and the RTL-SDR proves whether it worked.

| Sub-block | Implementation |
| --- | --- |
| Carrier | Crystal oscillator at 27 MHz |
| Modulator | Audio varying the amplitude of the output stage |
| Filter | Pi-network low-pass, harmonics measured before and after |
| Antenna | Short whip with a loading coil, tuned |

### Stage 4 — Walkie-talkie pair

Two units, each a receiver and a transmitter with a PTT switch selecting
between them. Talk across the flat, then from the street.

This is the **learning exercise, not a product**, and it is worth being
honest about that: nobody needs a pair of 27 MHz AM handhelds in 2026, a
phone is better in every respect, and homebrew gear is not type-approved so
the link is milliwatts across a street. What stages 3 and 4 are for is
building a transmitter — oscillator, modulator, harmonic filtering, antenna
matching — which is where most of the real RF engineering lives and which
nothing else in this vault covers. The pair is how that gets proven.

Voice over a radio link is a want in its own right, and it comes back later
somewhere better suited to it: a pair of handhelds that are not necessarily
analog and not necessarily AM. Digital voice over the RF course's own PHY is
the interesting version of that, and it belongs there rather than here.

### DCF77 clock — a keeper

77.5 kHz from Mainflingen, roughly 800 km away, transmitting continuously
and receivable across Slovakia with a ferrite rod and one amplifier stage.
The signal is amplitude-modulated in the crudest possible way: the carrier
drops for 100 ms or 200 ms once per second, and those two lengths are the
zeros and ones of a 59-bit frame carrying the date and time.

Receiving it is pure analog. Decoding it is a small, self-contained C
program written from the specification. The result is a clock that sets
itself and stays on the office desk — permanent value, near-zero cost, and
the only thing in this project with a job to do every day.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Measurement | Oscilloscope | Non-negotiable — the envelope has to be seen |
| Verification | RTL-SDR | Confirms the carrier is where I think it is, and shows the harmonics |
| Build | Breadboard, enamelled wire, ferrite rods, variable capacitors | Coils wound by hand |
| Antenna | Long wire indoors, short whip for 27 MHz | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Passives, transistors, germanium diodes | 10–20 € |
| Variable capacitors, ferrite rods, enamelled wire | 10–15 € |
| High-impedance earpiece | 5–10 € |
| 27 MHz crystals, PTT switches, second set of parts | 15–25 € |
| Whip antennas and loading coil wire | ~10 € |

Under 60 € for all four stages. Nothing here needs a part with a tolerance
worth paying for.

Sourcing: [[parts-sourcing]] — the ferrite rods and variable capacitors are
the vault's clearest case for buying from AliExpress, the germanium detector
is its clearest case against, and the rest of this BOM is the shape the
July 2026 flat duty punishes worst: many distinct cheap parts wanted once.

## Software / firmware

None for the analog stages — that is the appeal.

The one exception is the optional DCF77 decoder: a small C program turning
the demodulated pulse train into a date and time, written from the frame
specification rather than pulled from a library. Same instinct as the
hand-written decoder in [[subghz-linux-router]], one band lower and far
simpler.

## Plan

- [ ] Wind a coil, build the crystal set, sweep the band after dark
- [ ] Hear a real station — first proof the physics works
- [ ] Add the regenerative stage, compare sensitivity and selectivity
- [ ] Reach a shortwave broadcast band with a longer wire
- [ ] Build the regen properly — chassis, dial, audio stage, speaker
- [ ] Listen to it for an evening, and keep it
- [ ] DCF77 front end: ferrite rod, amplifier, clean pulses on the scope
- [ ] Decode the 59-bit frame in C, from the specification
- [ ] Clock built and on the office desk, setting itself
- [ ] Build the 27 MHz oscillator, confirm frequency on the scope and SDR
- [ ] Add amplitude modulation, verify the envelope
- [ ] Pi-network output filter — measure harmonics before and after
- [ ] Second unit, PTT switching, first two-way contact across the flat
- [ ] Measure the real range outdoors

Legal note: 27 MHz CB is licence-exempt in Slovakia under ECC/DEC/(11)03,
with 4 W permitted for AM. Homebrew equipment is not type-approved, though,
so the honest approach is milliwatts, a properly filtered output, and a
link that reaches across the street rather than across the town.

Winding coils and tuning a tank by hand is the same intuition needed for
antennas on [[subghz-linux-router]] and [[lora-dog-collar-telemetry]] —
where the antenna is bought, but the reason it works is identical.

## Build log

Session entries live in [[analog-am-transmitter-receiver-log]].
