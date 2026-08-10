---
tags: [project, embedded, linux, beaglebone, realtime]
status: deferred
depends: [industrial-sensor-node-linux]
created: 2026-08-07
---

# BeagleBone PRU — Nanosecond-Precision I/O

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Use the BeagleBone's programmable real-time units — cores that run
independently of the Linux kernel and its scheduler — to do timing that
Linux fundamentally cannot do without tearing.

Deliberately out of scope: doing this on a Raspberry Pi with DMA tricks.
The PRU is the subject.

## Learning value

- PRU architecture, its own instruction set and deterministic timing
- Sharing memory and signalling between Linux userspace and a PRU
- Where the boundary between "fast enough on Linux" and "needs real-time
  hardware" actually sits

## Practical value

None. A €10 logic analyzer does the job the PRU would be doing here, better
and immediately, and that is a large part of why this one is deferred rather
than queued.

The last of the three learning goals is the one that survives without the
build: knowing where the line between a userspace loop and dedicated
real-time hardware actually falls is worth having before it is needed in
anger, and it is the sort of judgement that is normally acquired by getting
it wrong on something that mattered.

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
[[industrial-sensor-node-linux]], which is the prerequisite: pin muxing and
overlays are assumed here rather than taught.

The deferral gets decided rather than assumed in module 11 of
[[embedded-linux-course]], which measures what a tuned PREEMPT_RT kernel can
actually hold on this board and then measures the same GPIO toggle on a PRU.
Two numbers and a ratio are what should settle whether this project is worth
un-deferring, and reaching for a real-time core before taking that
measurement is the wrong order.

Work like this is the reason [[beaglebone-green-case]] stays an open tray:
proving the jitter claim means a scope probe on the header while the board
runs, which no closed enclosure allows.

### Why this one is deferred

It is the only project in the vault that fails its own second test. The
learning is real — deterministic timing outside the kernel's reach is not
something the other projects go near — but neither candidate application is
something the flat needs. A logic analyzer is an instrument that already
exists on the bench for €10, and an LED strip is a demo. Nothing here ends
up mounted and used, which is the definition of a drawer project.

It also needs a board bought for this and nothing else. So it waits until
either a real timing problem turns up in another project, or the WS2812
strip acquires an actual job.

## Plan

- [ ] Load a trivial PRU firmware, toggle a pin, measure the period
- [ ] Compare against a userspace GPIO toggle on a scope — quantify jitter
- [ ] Shared memory and `rpmsg` between PRU and Linux
- [ ] WS2812 timing implemented cycle-exactly, drive one LED, then a strip
- [ ] Scale to hundreds of LEDs, confirm no gaps under Linux load
- [ ] Stretch: sampling mode — the logic analyzer variant

## Build log

Session entries live in [[beaglebone-pru-realtime-log]].
