---
tags: [project, hardware, analog, rf]
status: idea
created: 2026-08-07
---

# Analog AM — From Crystal Set to Walkie-Talkie

## Goal

Understand radio as physics rather than as a library call. AM is the
simplest modulation there is — a carrier whose amplitude follows the audio
— so it can be built out of a coil, a capacitor and a diode, tuned by hand,
and watched on a scope. Nothing here is written against someone else's
driver.

The project ends in something that gets used: a pair of 27 MHz AM handhelds
that actually talk to each other.

Learning goals:
- Resonance in practice — winding a coil and tuning a tank until a station
  appears
- Amplitude modulation and envelope detection, built from parts
- Gain, selectivity and why a crystal set needs neither a battery nor an
  amplifier to work
- Harmonic filtering on a transmitter output, and why it is mandatory

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

This is what reaches the shortwave broadcast bands.

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

This is the deliverable — a thing that works and gets kept, rather than a
breadboard that gets photographed and dismantled.

### Optional — DCF77 clock

77.5 kHz from Mainflingen, roughly 800 km away, transmitting continuously
and receivable across Slovakia with a ferrite rod and one amplifier stage.
The signal is amplitude-modulated in the crudest possible way: the carrier
drops for 100 ms or 200 ms once per second, and those two lengths are the
zeros and ones of a 59-bit frame carrying the date and time.

Receiving it is pure analog. Decoding it is a small, self-contained C
program written from the specification. The result is a clock that sets
itself and stays on a shelf — permanent value, near-zero cost.

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

## Software / firmware

None for the analog stages — that is the appeal.

The one exception is the optional DCF77 decoder: a small C program turning
the demodulated pulse train into a date and time, written from the frame
specification rather than pulled from a library. Same instinct as the
hand-written decoder in [[subghz-linux-router]], one band lower and far
simpler.

## Next steps

- [ ] Wind a coil, build the crystal set, sweep the band after dark
- [ ] Hear a real station — first proof the physics works
- [ ] Add the regenerative stage, compare sensitivity and selectivity
- [ ] Reach a shortwave broadcast band with a longer wire
- [ ] Build the 27 MHz oscillator, confirm frequency on the scope and SDR
- [ ] Add amplitude modulation, verify the envelope
- [ ] Pi-network output filter — measure harmonics before and after
- [ ] Second unit, PTT switching, first two-way contact across the flat
- [ ] Measure the real range outdoors
- [ ] Optional: DCF77 receiver and my own decoder, into a self-setting clock

Legal note: 27 MHz CB is licence-exempt in Slovakia under ECC/DEC/(11)03,
with 4 W permitted for AM. Homebrew equipment is not type-approved, though,
so the honest approach is milliwatts, a properly filtered output, and a
link that reaches across the street rather than across the town.

Winding coils and tuning a tank by hand is the same intuition needed for
antennas on [[subghz-linux-router]] and [[lora-dog-collar-telemetry]] —
where the antenna is bought, but the reason it works is identical.

## Build log
