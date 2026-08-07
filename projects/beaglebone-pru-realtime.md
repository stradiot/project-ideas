---
tags: [project, embedded, linux, beaglebone, realtime]
status: idea
created: 2026-08-07
---

# BeagleBone PRU — Nanosecond-Precision I/O

## Goal

Use the BeagleBone's programmable real-time units — cores that run
independently of the Linux kernel and its scheduler — to do timing that
Linux fundamentally cannot do without tearing.

Learning goals:
- PRU architecture, its own instruction set and deterministic timing
- Sharing memory and signalling between Linux userspace and a PRU
- Where the boundary between "fast enough on Linux" and "needs real-time
  hardware" actually sits

Deliberately out of scope: doing this on a Raspberry Pi with DMA tricks.
The PRU is the subject.

## Architecture

Two candidate applications, both chosen because Linux scheduling makes them
impossible:

| Application | Why the PRU |
| --- | --- |
| Logic analyzer | Sampling GPIO at a fixed, jitter-free rate |
| NeoPixel driver | WS2812 timing is sub-microsecond; hundreds of LEDs must be driven without a single gap |

| Layer | Implementation |
| --- | --- |
| PRU | Bit-banging code in PRU assembly or C, cycle-counted |
| Interface | Shared memory + interrupts between PRU and ARM |
| Linux side | Userspace app via `remoteproc` / `rpmsg`, plus pin setup in the device tree |

The measurable claim: toggle a pin from the PRU and from Linux userspace,
capture both, and show the jitter difference on a scope. That comparison is
worth as much as the finished application.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Board | BeagleBone Black / AI | Two PRUs in the AM335x PRU-ICSS |
| Toolchain | TI PRU code generation tools, `remoteproc` | |
| Verification | Oscilloscope or a second logic analyzer | To prove the timing claim |
| Load | WS2812 strip, a few hundred LEDs | The stress case |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| BeagleBone Black | 60–90 € |
| WS2812 strip | 15–30 € |
| 5 V supply sized for the strip | 15–25 € |

## Software / firmware

- PRU firmware, loaded via `remoteproc`
- Device tree overlay for pin muxing to the PRU
- Userspace control app over `rpmsg`, feeding frames or draining samples

Shares the device-tree and driver ground covered in
[[industrial-sensor-node-linux]].

## Next steps

- [ ] Load a trivial PRU firmware, toggle a pin, measure the period
- [ ] Compare against a userspace GPIO toggle on a scope — quantify jitter
- [ ] Shared memory and `rpmsg` between PRU and Linux
- [ ] WS2812 timing implemented cycle-exactly, drive one LED, then a strip
- [ ] Scale to hundreds of LEDs, confirm no gaps under Linux load
- [ ] Stretch: sampling mode — the logic analyzer variant

## Build log
