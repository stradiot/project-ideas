# Project Ideas

Personal vault for hardware, embedded and RF projects — what to build, why
that one rather than an easier one, and what each is for learning.

Most of what follows is a plan rather than a finished thing, and `status:`
on every note says which is which: of nineteen projects, two are built, one
is being designed, one is parked with the reason written down, and the rest
are specified and waiting. The spec comes before the build deliberately.
Deciding where the build-it/buy-it line sits, and how far a project should
go before it stops teaching anything, is most of the thinking — so it gets
written down where it can be argued with later, including by me.

The notes are equally deliberate about the gaps. Where a project needs
something I cannot do yet, the note says so plainly, and
`notes/embedded-learning-curriculum.md` collects those gaps into the order
they are worth closing in. A vault that only recorded what already works
would be a worse map of where the work actually is.

Written by automation as much as by hand — see *The vault maintains itself*
at the bottom. Working on one of the linked repos is what updates the
project note, its log and the daily journal.

## Built

Two, and the second one is smaller than it sounds. Both are in use.

- `subghz-collar-remote-clone` — an ESP32-C3 and a CC1101 that replay a
  captured 869.525 MHz frame to beep a dog collar from Home Assistant.
  Firmware, own PCB, printed case, deployed. It is also the most honest
  thing here: the signal is replayed rather than decoded, the note says
  what that costs, and the open bug — the beep fires ~70% of the time — is
  traced in `projects/logs/subghz-collar-remote-clone-log.md` down to a
  damaged capture rather than a wrong encoding. That log is the best
  evidence in the vault of how a problem here actually gets worked.
- `beaglebone-green-case` — a parametric printed mounting tray for the
  BeagleBone Green, on the bench and holding the board. Walls and a lid
  wait until the board has a job that decides which connectors matter.

## Structure

- `projects/` — one note per project: what it is, what it teaches, what it
  is for, and the plan
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

An edge earns its place only if this project genuinely cannot begin without
an artifact, a piece of hardware or a load-bearing skill the other one
produces. Not enough: the same track, the same chip family, ascending
difficulty, or "I would learn that there first". **Using a thing is not the
same as having built it** — every Linux board has a bootloader, and that does
not put every Linux project behind the bootloader project. Courses are never
a `depends:` for the same reason.

## Up next

Everything whose prerequisites are already built. Derived from `depends:` and
`status:` — regenerate rather than edit by hand.

- `analog-am-transmitter-receiver`
- `bare-metal-bootloader`
- `ble-sensor-node-pcb`
- `embedded-linux-course`
- `freertos-pocket-console`
- `home-assistant-rotary-controller`
- `industrial-sensor-node-linux` — as a specification; the course builds it
- `printed-rc-plane`
- `rc-car-custom-controller`
- `subghz-linux-router`
- `usb-device-and-linux-driver`
- `uwb-precision-locator`

Twelve of nineteen, which is the point: very little here genuinely blocks
anything else, and a list that long stops being a recommendation. Only four
projects are actually waiting on something, and they are marked below.

Where to start is a judgement, not a derivation. Today it is
`embedded-linux-course` — the board is already owned, the whole course costs
58 €, and it is the widest gap between what the vault plans and what I can
do. `ble-sensor-node-pcb` is the other one worth starting, because three
projects want the board it produces.

At the other end: `printed-rc-plane` before `custom-flight-controller-drone`,
because a plane glides when the loop is wrong and a quadcopter falls. And the
drone is deliberately last — nothing blocks it, but it is the project that
most rewards already knowing what you are doing.

## Projects

Grouped by track. Order within a track is rough progression, not dependency —
`depends:` is the actual graph, and it is much sparser than this list looks.
Status in brackets, with what a project is waiting on where it is waiting.

**RF**

- `analog-am-transmitter-receiver` *[idea]* — crystal set → a shortwave regen set worth keeping → a DCF77 clock → a transmitter
- `subghz-collar-remote-clone` *[built]* — CC1101 raw replay of the collar remote, into Home Assistant
- `subghz-linux-router` *[idea]* — own decoder, CC1101 kernel driver, then my own L2 under the IP stack
- `lora-dog-collar-telemetry` *[idea, waiting on `freertos-pocket-console`]* — GPS + IMU collar, hand-packed binary protocol
- `uwb-precision-locator` *[idea]* — time-of-flight ranging and PDoA bearing; the dog indoors, the car in a garage

**Embedded firmware**

- `bare-metal-bootloader` *[idea]* — ARM startup by hand, then a serial bootloader with A/B rollback
- `freertos-pocket-console` *[idea]* — RTOS on protoboard, then a production handheld with its own PCB and case
- `ble-sensor-node-pcb` *[planning]* — custom nRF52840 carrier board in KiCad, Zephyr board port
- `thread-matter-growbox` *[idea, waiting on `ble-sensor-node-pcb`]* — battery planter first, then a self-sufficient growbox
- `thread-matter-noise-sensor` *[idea, waiting on `thread-matter-growbox`]* — I2S mic on ESP32-C6, noise events over Thread, live listen over Wi-Fi
- `home-assistant-rotary-controller` *[idea]* — T-Embed as a physical HA controller, encoder + display

**Embedded Linux**

- `embedded-linux-course` *[idea]* — the whole field in fourteen modules, on the BeagleBone already owned
- `industrial-sensor-node-linux` *[idea]* — device tree, IRQ driver, systemd, D-Bus; the specification the course's capstone builds
- `usb-device-and-linux-driver` *[idea]* — descriptors, host driver, gadget mode, dual-role and Power Delivery
- `beaglebone-pru-realtime` *[deferred]* — PRU timing; parked, and the note says why

**Mechanical**

- `beaglebone-green-case` *[built]* — printed skeleton tray for the BBG; full case to follow

**Control**

- `rc-car-custom-controller` *[idea]* — RC link decode, actuators, failsafe, a real PID — cheaply
- `printed-rc-plane` *[idea]* — printed airframe flown manually, then a wing leveller of my own
- `custom-flight-controller-drone` *[idea, waiting on `rc-car-custom-controller`]* — attitude loop and hover on a printed ducted whoop; last on purpose

Every project is chosen for what it teaches, first and above everything
else. That is the criterion that decides what gets built, which parts are
bought as finished blocks, and how far each one goes — where an easier
route and a more instructive one disagree, the instructive one wins, and
the reasoning gets written down in the note.

Practical use is the second constraint rather than the point. Deployment
target for most of the connected ones is the local Home Assistant
instance. A project that does not end up as something used is a project
that ends up in a drawer.

Both are stated outright: every note carries a `## Learning value` and a
`## Practical value` section, and several of the second ones say *none*.
The bootloader, the PRU project and the drone all admit that a better
version of the artifact already exists and can be bought or downloaded —
they are there for what building them teaches. Notes that do claim a use
are worth reading precisely because the others do not.

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
