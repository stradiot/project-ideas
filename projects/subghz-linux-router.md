---
tags: [project, hardware, embedded, linux, kernel, rf]
status: idea
depends: [subghz-collar-remote-clone, analog-am-transmitter-receiver]
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

Learning goals:
- Demodulating a raw OOK/FSK signal down to its binary payload
- Writing a Linux character driver for an SPI peripheral
- Hooking a driver into the Linux networking subsystem (`netdev`, netlink)

Deliberately out of scope: any attempt at a fast or spectrally polite
protocol. The result is allowed to be an extremely slow link — the point is
the stack, not the throughput.

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
maths here read as familiar rather than abstract, which is a reason to
build that one first even though it shares no components with this.

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

This is where the practical value lands, so it does not stop at a working
`ioctl`: a small userspace service exposes the blinds to Home Assistant as
a `cover` entity. At that point the flat has scheduled blinds, and the
project has paid for itself even if Phase 3 never happens.

If the problem turns out to be range rather than control, the standalone
answer is [[subghz-fixed-code-repeater]] — an always-on box that extends
the original remote without a Linux host in the path.

### Phase 3 — Network stack

Openly the education-only phase. There is no practical need for IP over a
CC1101 — WiFi exists, and it is better in every measurable way. The point
is to touch the Linux networking subsystem from underneath.

Phases 2 and 3 are modules 6 and 10 of [[embedded-linux-course]], using this
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
| Host | Raspberry Pi | SPI + free GPIO for GDO0/GDO2 |
| Kernel work | Cross-toolchain, kernel headers, `dmesg`/ftrace | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| RTL-SDR dongle | 25–40 € |
| CC1101 modules, 2 pcs | 5–10 € |
| Raspberry Pi (if not already owned) | 40–80 € |
| Wiring, antennas | ~10 € |

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
- [ ] Expose the blinds to Home Assistant as a `cover` — schedule them
- [ ] Convert to `net_device`, ping across two CC1101 nodes
- [ ] Netlink configuration interface

## Build log

Session entries live in [[subghz-linux-router-log]].
