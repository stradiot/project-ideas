---
tags: [project, embedded, linux, kernel, systemd]
status: idea
depends: []
created: 2026-08-07
---

# Industrial Sensor Node on Embedded Linux

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Build a monitoring device that behaves like a professional embedded Linux
product rather than a hobby script — robust, resource-constrained,
supervised, and correct all the way from the interrupt to the D-Bus message.

Deliberately out of scope: the sensing itself is trivial on purpose. A PIR
and a USB thermometer are enough — the interesting part is everything
around them.

## Learning value

- Device Tree overlays for pin configuration on a real board
- Interrupt handling in a driver, split into top half and bottom half
- systemd as an architecture, not just an init system: cgroup limits,
  socket activation, watchdog
- D-Bus as the local IPC layer

## Practical value

Low, and deliberately so. What it produces is a box that notices motion and
reports a temperature, which a 15 € ESP32 already does better, cheaper and
on a battery. Nobody should build this to get the measurement.

Its actual output is a specification. This note is what
[[embedded-linux-course]] builds as its capstone, and the reason the sensing
was chosen to be trivial is that every interesting decision then lives in
the plumbing — the interrupt path, the supervision, the IPC boundary —
where the course needs them to be.

## Architecture

| Block | Implementation | What I learn |
| --- | --- | --- |
| Motion | PIR sensor on GPIO, edge-triggered interrupt | IRQ handling, debouncing in kernel |
| Temperature | USB device (USB thermometer or serial converter) | USB subsystem, hotplug |
| Pin setup | Device Tree Overlay | DT syntax, pinctrl, overlay loading |
| Kernel | Char driver exposing both sources | `file_operations`, `poll`, wait queues |
| Userspace | Daemon in C | Reading from the driver, publishing events |
| Supervision | systemd | cgroups, socket activation, watchdog |
| IPC | D-Bus | Signals to other local processes |

### Interrupt path

The PIR interrupt handler stays minimal — acknowledge, timestamp, schedule
the bottom half. Everything expensive (buffering, waking readers) happens in
a workqueue or tasklet. That split is the reason this sensor was chosen at
all.

### Daemon under systemd

The daemon deliberately does **not** start at boot. It is socket-activated:
systemd holds the listening socket, and the daemon is only started when
something on the network actually asks for data. Combined with strict
`MemoryMax` / `CPUQuota` in the unit file, the idle cost of the whole node
approaches zero.

A systemd watchdog (`WatchdogSec` plus `sd_notify` pings from the daemon)
restarts the service if it freezes — and, escalated, reboots the board.

### Where it ends up

D-Bus is the right local IPC layer, but a `busctl` session is a demo, not a
deployment. A small bridge subscribes to the daemon's D-Bus signals and
republishes them over MQTT, so the node appears in Home Assistant as motion
and temperature entities and the board goes on the wall.

That bridge is deliberately the last thing built. Everything below it —
overlay, driver, interrupt split, socket activation, watchdog — has to work
first, and the bridge is what stops the whole thing from being switched off
after the demo.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Board | Raspberry Pi / BeagleBone | Needs free GPIO and DT overlay support |
| Sensors | PIR (HC-SR501), USB thermometer | Cheap, boring, sufficient |
| Debug | `dmesg`, ftrace, `systemd-analyze`, `busctl` | |
| Logic capture | Cheap 8-ch logic analyzer | For the GPIO edges |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| PIR sensor | 2–5 € |
| USB thermometer / serial converter | 10–20 € |
| Board (if not already owned) | 40–80 € |

## Software / firmware

- Device Tree Overlay — pin muxing, interrupt declaration
- Kernel module: char device, IRQ handler + bottom half, `poll` support
- Daemon in C: reads the char device, exposes readings over D-Bus,
  answers the socket-activated network request, pings the watchdog
- systemd unit files: `.socket` + `.service` with cgroup limits
- D-Bus → MQTT bridge, so the node lands in Home Assistant

## Plan

- [ ] Wire the PIR, confirm edges with the logic analyzer
- [ ] Write and load the Device Tree Overlay
- [ ] Char driver with IRQ, top half / bottom half split
- [ ] Add the USB device as a second data source
- [ ] Daemon in C, reading from the driver
- [ ] Socket activation + cgroup limits in the unit file
- [ ] D-Bus interface, verify with `busctl`
- [ ] Watchdog — deliberately hang the daemon and watch it come back
- [ ] Bridge D-Bus to MQTT, mount the board, see it live in Home Assistant

### This note is the specification; the course is the build

This device does not get built twice. [[embedded-linux-course]]'s capstone
*is* this node — same BeagleBone, same PIR, same wall, same Home Assistant
entities — and the course builds every piece of it along the way: the
overlay in module 4, the threaded IRQ driver in 5, the subsystem rewrite in
6, the socket-activated daemon with its watchdog and D-Bus in 9, and then
the whole thing productionised in the capstone with a Yocto BSP layer, a
signed FIT image and A/B updates that roll back.

So what lives here is the *design* — what the device must do, why the
interrupt splits where it does, why the daemon is socket-activated, and why
the MQTT bridge is the last thing built. What lives there is the sequence
that gets it made. Reading this note is how you know what to aim at; working
through the course is how it ends up on the wall.

One thing this note is honest about that the course cannot be: the sensing
is a pretext. A €50 mains-powered SBC detecting motion is a job a €15
battery Zigbee sensor does better, and if a motion sensor were the goal that
is what should be bought. The goal is a device that behaves like a product
from the interrupt upward, and the PIR is the cheapest honest excuse to
build one.

This is the note the other kernel-side work leans on. The char device and
its `file_operations` reappear in [[usb-device-and-linux-driver]], where the
data source is a USB peripheral of my own rather than a GPIO pin, and the
device tree work reappears in [[beaglebone-pru-realtime]] as pin muxing for
a PRU. [[zephyr-devicetree]] is the same syntax on the other side of the
fence — resolved at build time, with no tree left at runtime — and the
contrast is worth seeing having written an overlay here first.
[[beaglebone-green-case]] is where the physical end of this lands if the
board turns out to be the BeagleBone Green: mounting the node on a wall is
the requirement that decides what the full case has to be.

## Build log

Session entries live in [[industrial-sensor-node-linux-log]].
