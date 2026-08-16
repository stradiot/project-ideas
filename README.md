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

## Why not a course

Buying one was the obvious alternative, and one *was* bought: Advanced
Embedded Software Development, a graded online course from the University of
Colorado Boulder, taken through nine assignments and a final project between
October 2024 and May 2025, and continued alone afterwards as an HD44780
display driver, a userspace tool and a two-layer Yocto build for a Raspberry
Pi 4. So the usual complaint — that a course is generic by construction,
pitched at nobody's level and mostly watched rather than done — is not what
this is. That one was graded, built rather than watched, and finished.

What it did not supply is narrower and more specific. Every board in it came
with a board support package already written, none of them booted through
U-Boot, and nothing built on any of them was ever measured. That is the shape
of what is left, and it is why the embedded Linux course here now spends its
time on bring-up, latency and tracing rather than on writing another recipe.

Writing the remaining four instead costs the time to write them down, and
buys a syllabus that is only the interesting parts, work that is hands-on
rather than watched, and a level that matches whatever is actually known. The
money goes on hardware instead of tuition — the embedded Linux course here is
fourteen modules and its entire budget is 58 € of parts, microSD cards, a
logic analyzer and a Wi-Fi dongle that would have been bought anyway. All
five are mapped in `notes/embedded-learning-curriculum.md`, along with an
inventory of what is already known, since an order derived partly from the
size of a gap is only as good as that list. The output is sometimes useful on
its own terms too, which a course exercise rarely is:
`subghz-collar-remote-clone` is a device in daily use.

What a course cannot do at all is answer back. Working through a project in
Claude Code means the mechanism gets explained before the code is written, a
missing foundation gets covered rather than routed around, and a wrong idea
can be argued with. That is the half worth having, and it is why the
SessionStart hook puts that instruction into every session rather than
leaving it to memory.

The honest cost is that none of this is reviewed. Nobody marks the work or
reads the notes, and a wrong explanation reads exactly like a right one.
What catches most of it is that the work ends in hardware, which does not
care what anyone believed — a number is measured or it is not, a decoded
frame is accepted by a real receiver or it is not, an airframe flies or it
does not. That check is partial: it only covers what the build exercises,
and it can be slow. `subghz-collar-remote-clone` beeped about 70% of the
time for months, and the first explanation for why was convincing and
wrong. So "it works" and "I understand why it works" are kept as separate
claims throughout, which is what `## Lessons` and the recorded dead ends are
for.

## Built

Two, and the second one is smaller than it sounds. Both are in use.

- `subghz-collar-remote-clone` — an ESP32-C3 and a CC1101 that replay a
  captured 869.525 MHz frame to beep a dog collar from Home Assistant.
  Firmware, own PCB, printed case, deployed. It is also the most honest
  thing here: the signal is replayed rather than decoded, and the note says
  what that costs. The beep fired ~70% of the time for most of the device's
  life; `projects/logs/subghz-collar-remote-clone-log.md` has the three
  sessions that took it apart, including the wrong answer — a damaged
  capture — that survived a whole session before hand measurement killed
  it. The cause was burst structure, and it is 6/6 on hardware now. That
  log is the best evidence in the vault of how a problem here actually gets
  worked, and its `## Lessons` section is where the reusable half ended up.
- `beaglebone-green-case` — a parametric printed mounting tray for the
  BeagleBone Green, on the bench and holding the board. Walls and a lid
  wait until the board has a job that decides which connectors matter.

## Structure

- `projects/` — one note per project: what it is, what it teaches, what it
  is for, and the plan
- `projects/logs/` — one build log per project, written per session, newest
  entry on top
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

Where to start is a judgement, not a derivation, and this one changed. It used
to be `embedded-linux-course`, on the grounds that it was the widest gap
between what the vault plans and what I can do. That turned out to be false —
a graded Linux course and a driver-plus-Yocto project of my own already cover
roughly a third of its syllabus, which is written up in
`notes/embedded-learning-curriculum.md`. The five courses are now ordered RF,
bare-metal and RTOS, embedded Linux, hardware design, control, aimed at
embedded software with RF as the main focus, so the place to start is the RF
material — and `analog-am-transmitter-receiver` is the project it begins in.
`ble-sensor-node-pcb` is the other one worth starting, because three projects
want the board it produces.

At the other end: `printed-rc-plane` before `custom-flight-controller-drone`,
because a plane glides when the loop is wrong and a quadcopter falls. And the
drone is deliberately last — nothing blocks it, but it is the project that
most rewards already knowing what you are doing.

Where the parts come from is a separate question from which project is next,
and `notes/parts-sourcing.md` answers it across every `## Budget` table at
once. Roughly half the vault's parts spend is commodity modules, motors and
wire where a marketplace is the obvious source; the rest is sorted by a
single test — whether a subtly wrong part would announce itself, or would
present as a bug in the thing being learned.

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
project's `## Now`, ticks any `## Plan` item the session finished, adds a dated
entry at the top of `projects/logs/<slug>-log.md`, records a `## Lessons`
bullet if the session produced one worth keeping, adds one line to
`journal/<date>.md`, then commits and pushes. An unlinked repo gets the
daily-note line only.

Reading order on a phone: `## Now` is the first thing in every note, so the
current state of a project is above the fold, and `## Lessons` follows it —
what the project has already taught, one bullet each, linking into the log
entry that holds the working. The long build-log prose lives in its own file
so it never buries the spec, and its entries run newest first so the top of
the file is the latest session.

What automation will not touch: frontmatter, Goal, Learning value, Practical
value, Architecture, Tools, Budget, and the wording of `## Plan` items. Those
are the design, and they change only by a deliberate edit.

If the push conflicts with an edit made from the phone, it stops and leaves the
commit local rather than resolving it. Nothing is ever force-pushed, so a
conflict is always waiting to be sorted out by hand.

Entries are written from the session transcript, so anything decided out loud
during the session is what ends up in the log.
