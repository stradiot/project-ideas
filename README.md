# Project Ideas

Personal vault for hardware, embedded and infrastructure projects.

## Structure

- `projects/` — one note per project: what it is, why, and the plan
- `projects/logs/` — one build log per project, appended per session
- `notes/` — reference notes, deep dives, linked from projects
- `journal/` — daily notes
- `templates/` — note templates

A project note whose code lives in a repo under `~/Documents/personal` carries
that directory name in its frontmatter, and the remote alongside it:

```
status: built
depends: [industrial-sensor-node-linux]
repo: subghz-linux-router
github: https://github.com/stradiot/subghz-linux-router
```

`repo:` is the only link between note and code. It is exact — nothing is
inferred from names, and a project without it is simply unlinked. `github:` is
for reading; nothing reads it but a person.

`status:` is `idea` → `planning` → `active` → `built`, or `deferred`.
`depends:` lists the projects that have to be *built* first — the real
prerequisite graph, which is not the same as the wikilinks. Wikilinks say two
projects are related; `depends:` says one cannot start.

## Up next

Everything whose prerequisites are already built. Derived from `depends:` and
`status:` — regenerate rather than edit by hand.

- `analog-am-transmitter-receiver` — RF, no prerequisites
- `subghz-fixed-code-repeater` — unblocked by the collar remote being built
- `bare-metal-bootloader` — the root of the whole firmware track
- `embedded-linux-course` — the course, on hardware already owned
- `industrial-sensor-node-linux` — the root of the Linux track
- `rc-car-custom-controller` — the root of the control track

The firmware track is the one worth starting: four projects sit behind
`bare-metal-bootloader` and nothing behind it is reachable until it is done.

## Projects

Grouped by track, in dependency order — each is blocked by the one above
unless marked otherwise. Status in brackets.

**RF**

- `analog-am-transmitter-receiver` *[idea, ready]* — crystal set → regenerative RX → 27 MHz walkie-talkie pair
- `subghz-collar-remote-clone` *[built]* — CC1101 raw replay of the collar remote, into Home Assistant
- `subghz-linux-router` *[idea]* — SDR capture, own decoder, CC1101 kernel driver, `net_device`
- `subghz-fixed-code-repeater` *[idea, ready]* — store-and-forward range extender for the blinds
- `lora-dog-collar-telemetry` *[idea]* — GPS + IMU collar, hand-packed binary protocol
- `uwb-precision-locator` *[idea]* — time-of-flight ranging and PDoA bearing; the dog indoors, the car in a garage

**Embedded firmware**

- `bare-metal-bootloader` *[idea, ready]* — ARM startup by hand, then a serial bootloader with A/B rollback
- `freertos-pocket-console` *[idea]* — RTOS tasks and queues; ends up as the collar's ground station
- `ble-sensor-node-pcb` *[planning]* — custom nRF52840 carrier board in KiCad, Zephyr board port
- `thread-matter-smart-planter` *[idea]* — Zephyr, Thread Border Router, Matter into Home Assistant
- `thread-matter-noise-sensor` *[idea]* — I2S mic on ESP32-C6, noise events over Thread, live listen over Wi-Fi
- `home-assistant-rotary-controller` *[idea]* — T-Embed as a physical HA controller, encoder + display

**Embedded Linux**

- `embedded-linux-course` *[idea, ready]* — the whole field in fourteen modules, on the BeagleBone already owned
- `industrial-sensor-node-linux` *[idea, ready]* — device tree, IRQ driver, systemd, D-Bus, into Home Assistant
- `usb-device-and-linux-driver` *[idea]* — own USB peripheral and the kernel driver that claims it
- `beaglebone-pru-realtime` *[deferred]* — PRU timing; parked, and the note says why

**Mechanical**

- `beaglebone-green-case` *[built]* — printed skeleton tray for the BBG; full case to follow

**Control**

- `rc-car-custom-controller` *[idea, ready]* — RC link decode, actuators, failsafe, a real PID — cheaply
- `custom-flight-controller-drone` *[idea]* — attitude loop and hover; airframe bought last

Every project is chosen for what it teaches, first and above everything
else. That is the criterion that decides what gets built, which parts are
bought as finished blocks, and how far each one goes — where an easier
route and a more instructive one disagree, the instructive one wins, and
the reasoning gets written down in the note.

Practical use is the second constraint rather than the point. Deployment
target for most of the connected ones is the local Home Assistant
instance. A project that does not end up as something used is a project
that ends up in a drawer.

## Workflow

- Mac: nvim + obsidian.nvim, plain git
- Android: Obsidian mobile + Git plugin (HTTPS remote), pull before editing, push after
- Text only. No binaries, no LFS in this repo.

### The vault maintains itself

This vault is written, not edited. Working on a linked repo in Claude Code is
what updates it: on session start it pulls; on session end it rewrites that
project's `## Now`, ticks any `## Plan` item the session finished, appends a
dated entry to `projects/logs/<slug>-log.md`, adds one line to
`journal/<date>.md`, then commits and pushes. An unlinked repo gets the
daily-note line only.

Reading order on a phone: `## Now` is the first thing in every note, so the
current state of a project is above the fold and the plan follows it. The long
build-log prose lives in its own file so it never buries the spec.

What automation will not touch: frontmatter, Goal, Architecture, Tools,
Budget, and the wording of `## Plan` items. Those are the design, and they
change only by a deliberate edit.

If the push conflicts with an edit made from the phone, it stops and leaves the
commit local rather than resolving it. Nothing is ever force-pushed, so a
conflict is always waiting to be sorted out by hand.

Entries are written from the session transcript, so anything decided out loud
during the session is what ends up in the log.
