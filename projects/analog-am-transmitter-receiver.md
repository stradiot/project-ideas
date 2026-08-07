---
tags: [project, hardware, analog, rf]
status: idea
created: 2026-08-07
---

# Analog AM Transmitter and Receiver

## Goal

Build a physical radio link with no digital RF modules involved — an
oscillator, a modulator, and a receiver made of a coil, a capacitor and a
diode. Physical proof of understanding what a carrier wave is and how
information rides on it.

Learning goals:
- Oscillator and LC tank design, resonance in practice
- Amplitude modulation and envelope detection
- Working with analog circuits on a breadboard, with a scope in hand

Deliberately out of scope: range, audio quality, and anything resembling a
usable radio station. A metre of range is a success.

## Architecture

### Transmitter

Simple oscillator generating the carrier, with an audio input (phone
headphone output) modulating its amplitude. Built on breadboard first;
a small custom PCB only if the breadboard parasitics make it hopeless.

### Receiver

Two options, ideally both:

| Variant | Parts | What it demonstrates |
| --- | --- | --- |
| Crystal set | LC tank, germanium diode, high-impedance earpiece | Detection with zero power supply |
| One-transistor | LC tank, diode detector, single-stage amplifier | Why gain matters |

Tuning the LC tank to the transmitter's carrier and hearing audio come out
is the whole deliverable.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Measurement | Oscilloscope | Non-negotiable for this one |
| Optional | RTL-SDR | Independent confirmation that the carrier is where I think it is |
| Build | Breadboard, enamelled wire, variable capacitor | Coils wound by hand |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Passives, transistors, germanium diodes | 10–20 € |
| Variable capacitor, ferrite rod / wire | 10–15 € |
| High-impedance earpiece | 5–10 € |

## Software / firmware

None. That is the appeal.

## Next steps

- [ ] Build the oscillator, confirm the carrier frequency on the scope
- [ ] Add amplitude modulation from an audio source, verify the envelope
- [ ] Wind the receiving coil, build the crystal set, tune it
- [ ] Hear audio out of the earpiece — first end-to-end link
- [ ] Add the one-transistor amplifier stage, compare
- [ ] Measure how far it actually reaches

Keep transmit power low enough to stay legal and to avoid interfering with
anything — a bench-scale link only.

## Build log
