---
tags: [project, hardware, embedded, linux, kernel, rf]
status: idea
depends: [subghz-collar-remote-clone]
created: 2026-08-07
---

# Sub-GHz Linux Router & RF Cloner

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Build a network bridge between the Linux world and the non-standard sub-GHz
RF devices around the flat — starting with the blinds remote, ending with a
real network interface that speaks my own protocol.

Deliberately out of scope: any attempt at a fast or spectrally polite
protocol. The result is allowed to be an extremely slow link — the point is
the stack, not the throughput.

## Learning value

- Demodulating a raw OOK/FSK signal down to its binary payload
- Writing a Linux character driver for an SPI peripheral
- Hooking a driver into the Linux networking subsystem (`netdev`, netlink)

## Practical value

Front-loaded, and it runs out on purpose. Phase 1 ends with the blinds
remote decoded properly rather than replayed, which puts the blinds into
Home Assistant as something that can be commanded and understood. That is a
real device doing a real job.

Phase 3 is openly the education-only phase. An `rf0` interface carrying my
own L2 under the IP stack is slower and less reliable than the Wi-Fi
already in the flat, and nothing will be run over it once it works. It is
kept because writing a network interface is the only way to find out what a
network interface is, and the note would rather say that than dress it up
as infrastructure.

## Architecture

Three phases, each usable on its own if the next one never happens.

### Phase 1 — Analysis

Capture the blinds remote with a cheap SDR (RTL-SDR). Write the decoder
myself in C: from raw samples to symbol timing to the binary payload.
No `rtl_433`, no ready-made decoders — the whole point is knowing what the
preamble, the sync word and the payload actually look like.

[[analog-am-transmitter-receiver]] is the same signal chain done in
hardware — envelope detection built from a diode and an earpiece instead of
written in C. Having demodulated something by hand once makes the sample
maths here read as familiar rather than abstract. Worth doing at some point
for that reason, but not before this: the two share no components, and
neither one blocks the other.

The case for doing it this way is not theoretical: it is
[[subghz-collar-remote-clone]], which took the other route. That one
captured a frame, replayed the raw timings without decoding anything, and
had a working device in days — then spent far longer stuck at 70%
reliability with no model of the frame to debug against. Skipping the
decoder is genuinely faster right up to the first thing that goes wrong.

### Phase 2 — Kernel and low-level

CC1101 module wired to a Raspberry Pi (or another Linux board) over SPI.
Custom character driver that initialises the radio and pushes raw frames
through it. Success criterion is physical: the blinds actually go down when
the cloned frame is transmitted.

The blinds are the *test signal*, not the product — they already reach Home
Assistant through their own gateway, and nothing here improves on that. What
they give is something no bench measurement can: an unambiguous physical
confirmation that the decoder read the frame correctly and the driver
transmitted it correctly. A slat that moves is worth more than a log line
that says the write succeeded.

### Phase 3 — Network stack

Openly the education-only phase, and the reason the whole project exists.
There is no practical need for IP over a CC1101 — WiFi exists and is better
in every measurable way. The point is to build a link layer from nothing and
watch the rest of the stack accept it.

The deliverable is specific: **`ping` across the radio, then `ssh` through
it, then a packet capture showing TCP retransmitting over a link I
designed.** Nothing about that is useful. All of it is the thing worth
knowing.

### Which floor "from scratch" means

The CC1101 does modulation and demodulation. Everything above it is mine:
preamble, sync word, frame format, addressing, length, CRC, acknowledgement
and retry, fragmentation for an MTU that does not fit, and the `net_device`
that carries IP over the result. That is the PPP analogy done properly, and
it is where the kernel learning lives.

The layer below — designing the waveform itself, with pulse shaping, symbol
timing recovery and carrier correction — belongs to the RF course and a
transmit-capable SDR, not here. Doing both eventually is the interesting
part: a MAC of mine on someone else's PHY, then a PHY of mine underneath it,
and a comparison between them.

Phases 2 and 3 are [[linux-driver-model-and-subsystems]] and
[[linux-networking-and-netdev]] in [[embedded-linux-course]], using this
same CC1101: the SPI driver with GDO0 as a threaded IRQ, then the
`net_device` on top of it. The course also insists on measuring what the
resulting link can actually carry, which is the honest version of the
argument this section is already making.

Extend the driver from a char device into a proper network device. The
radio shows up in Linux as a standard interface — `rf0` — with netlink used
to configure radio parameters (frequency, data rate, modulation) from
userspace.

| Layer | Implementation |
| --- | --- |
| PHY | CC1101 over SPI, GDO pins as interrupts |
| Driver | Kernel module — char device first, then `net_device` |
| Config | Netlink from userspace, not ioctl/sysfs hacks |
| Above | Plain IP — whatever the kernel wants to send |

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Capture | RTL-SDR + GQRX / Universal Radio Hacker | Only for analysis, not for TX |
| Transmit | CC1101 module (868 MHz) | SPI, 3.3 V logic |
| Host | BeagleBone Green | Already owned; SPI plus free GPIO for GDO0/GDO2 |
| Kernel work | Cross-toolchain, kernel headers, `dmesg`/ftrace | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| RTL-SDR dongle | already owned |
| CC1101 modules, 2 pcs | 5–10 € |
| Linux host | already owned — the BeagleBone Green |
| Wiring, antennas | ~10 € |

Effectively free. The radio, the SDR and the board are all already on the
bench, which is most of why this project is worth doing at all.

## Software / firmware

- Userspace decoder in C — sample stream in, payload out
- Kernel module, out of tree, built against the board's kernel headers
- Small userspace tool over netlink for configuring `rf0`

Legal note: transmitting on 868 MHz means staying inside ISM duty-cycle and
power limits, and only ever targeting my own devices.

## Plan

- [ ] Capture the blinds remote, identify modulation and symbol rate
- [ ] Decode the payload by hand, then automate it in C
- [ ] Wire CC1101 over SPI, get the chip ID back — proof the bus works
- [ ] Char driver: raw TX, replay the captured frame, move the blinds
- [ ] Design the frame format — preamble, sync, addressing, length, CRC
- [ ] Acknowledgement and retry, then fragmentation for an oversized MTU
- [ ] Convert to `net_device`, ping across two CC1101 nodes
- [ ] Netlink configuration interface
- [ ] `ssh` over `rf0`, and a capture of TCP retransmitting on my own link
- [ ] Measure it honestly — throughput, latency, loss — and write the numbers down

## Build log

Session entries live in [[subghz-linux-router-log]].
