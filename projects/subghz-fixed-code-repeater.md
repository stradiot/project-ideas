---
tags: [project, hardware, embedded, rf, subghz]
status: idea
depends: [subghz-collar-remote-clone]
created: 2026-08-07
---

# Sub-GHz Fixed-Code Repeater

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

The blinds remote works from the sofa and nowhere else. Build a small
always-on box that listens for its frames and retransmits them, so the
remote reaches the far end of the flat.

Learning goals:
- Receive → validate → retransmit as a real-time embedded problem
- Duty-cycle budgeting on 868 MHz, and why a repeater burns it twice
- Why fixed-code remotes are trivially defeated, by defeating one

Deliberately out of scope: a general-purpose repeater for arbitrary
protocols. It repeats my frames, from my remote, and nothing else.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | Small microcontroller, always powered |
| Radio | CC1101 — one, half-duplex, or two for RX/TX overlap |
| Decode | Frame recognition reusing the decoder work from Phase 1 of [[subghz-linux-router]] |
| Filter | Whitelist of known frames; everything else is ignored |
| Power | Mains via a USB supply — this thing never sleeps |

One radio or two is the first real design decision. One CC1101 is cheaper
and simpler but must switch RX→TX, which means a gap where frames are
missed. Two lets the repeat start while the original is still in the air,
at the cost of desensitising the receiver. Start with one.

The whitelist is what separates this from
[[subghz-collar-remote-clone]], which transmits a stored capture blind. A
repeater has to *recognise* a frame before it repeats it, so the decoder is
not optional here the way it was skippable there — and the same CC1101 and
the same 868 MHz bring-up work carries straight over from that build.

### What stops it misbehaving

The naive version — repeat anything you hear — breaks immediately. Three
rules make it work:

| Rule | Reason |
| --- | --- |
| Whitelist | Only frames matching my remote's payload are repeated |
| Loop suppression | A frame is not repeated if it was just transmitted — otherwise the repeater feeds itself forever |
| Repeat budget | Hard cap on transmissions per hour, to stay inside the ISM duty cycle |

The loop suppression is the interesting one: the repeater hears its own
output, and a naive whitelist match will happily re-trigger on it. A
hold-off window after each transmission is the cheapest fix.

### Why fixed code is broken

The remote sends the same bits every time. Capture once, replay forever —
no key, no counter, no challenge. That is the entire vulnerability, and
this project is a working demonstration of it.

That is also why the repeater is possible at all: a rolling-code remote
could not be repeated this way, because the receiver would reject a
replayed counter value. Building the thing that only works on fixed code is
the clearest way to understand what rolling code buys.

Scoped to my own blinds, in my own flat.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Radio | CC1101 module (868 MHz) | Same part as [[subghz-linux-router]] |
| MCU | Any small board with SPI and free GPIO | GDO0/GDO2 as interrupts |
| Verification | RTL-SDR | Watch the repeat on the waterfall, confirm no self-triggering |
| Range test | The far end of the flat | The only test that matters |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| CC1101 modules, 2 pcs | 5–10 € |
| MCU board | 5–15 € |
| Enclosure, USB supply, antenna | 10–15 € |

## Software / firmware

- Frame decoder on the MCU — the same symbol timing and payload logic
  already written for the host in [[subghz-linux-router]], ported down
- Whitelist match, hold-off timer, duty-cycle counter
- A status LED that distinguishes "heard something" from "repeated it" —
  otherwise debugging range problems is guesswork

Legal note: 868 MHz ISM duty-cycle and power limits apply, and a repeater
doubles the airtime for every button press. The repeat budget is not
optional.

## Plan

- [ ] CC1101 receiving, print raw frames — confirm the remote is decoded
- [ ] Whitelist match against the known payload, LED on recognition
- [ ] Retransmit after a fixed delay, confirm the blinds respond
- [ ] Add hold-off, verify it does not trigger on its own output
- [ ] Duty-cycle counter with a hard cap
- [ ] Enclosure, mains supply, mount it at the range boundary
- [ ] Measure the actual coverage gain, remote in hand

## Build log

Session entries live in [[subghz-fixed-code-repeater-log]].
