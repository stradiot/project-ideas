---
tags: [project, embedded, linux, kernel, systemd]
status: idea
created: 2026-08-07
---

# Industrial Sensor Node on Embedded Linux

## Goal

Build a monitoring device that behaves like a professional embedded Linux
product rather than a hobby script — robust, resource-constrained,
supervised, and correct all the way from the interrupt to the D-Bus message.

Learning goals:
- Device Tree overlays for pin configuration on a real board
- Interrupt handling in a driver, split into top half and bottom half
- systemd as an architecture, not just an init system: cgroup limits,
  socket activation, watchdog
- D-Bus as the local IPC layer

Deliberately out of scope: the sensing itself is trivial on purpose. A PIR
and a USB thermometer are enough — the interesting part is everything
around them.

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

## Next steps

- [ ] Wire the PIR, confirm edges with the logic analyzer
- [ ] Write and load the Device Tree Overlay
- [ ] Char driver with IRQ, top half / bottom half split
- [ ] Add the USB device as a second data source
- [ ] Daemon in C, reading from the driver
- [ ] Socket activation + cgroup limits in the unit file
- [ ] D-Bus interface, verify with `busctl`
- [ ] Watchdog — deliberately hang the daemon and watch it come back

## Build log
