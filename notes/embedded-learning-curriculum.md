---
tags: [note, course, curriculum, embedded]
created: 2026-08-10
---

# Embedded Learning Curriculum

Reference note. The map of five courses, of which
[[embedded-linux-course]] is the first one written. It exists because
nineteen project notes describe *what* to build and none of them describe
what has to be learned first, and it turned out that gap was mostly in the
same four or five places every time.

## Why these are written rather than bought

The alternative was to buy five courses instead of writing them, and it is
worth recording why that lost, because the answer is not that commercial
courses are bad.

A course sold to everyone has to be built for everyone, which forces three
compromises at once. The syllabus is the intersection of what its buyers
want rather than what any one of them wants. The level assumes a starting
point that is nobody's in particular. And the work is mostly watched rather
than done. Paying for that and then skipping half of it is the normal
outcome, and it is not the same half for any two people.

Writing them costs the time these notes took and removes all three: the
syllabus is only the parts worth learning here, the level is whatever is
actually known this month, and every module ends in hardware on the bench.
What is left to pay for is the hardware, which was going to be bought
regardless — 58 € for Embedded Linux, and the table below carries the same
figure for the other four.

The part a bought course genuinely cannot supply is being answered back. A
recorded lecture cannot notice that a foundation is missing, and it cannot
be argued with when it is wrong. Working through a module in Claude Code
does both, and the SessionStart hook makes it the default rather than
something to remember to ask for: explain the mechanism before writing the
code, and cover the gap rather than route around it. That is the same rule
these notes are written under — teach the mechanism, not the API surface —
so the session and the note it produces are held to one standard.

What a bought course still has that this does not is a deadline, and
somebody else's judgement that the order is right. The ordering below is
the substitute for the second. There is no substitute for the first, and
`status:` staying honest is the only thing that makes a stall visible.

The larger thing it does not have is review. Nothing here is fact-checked
by anyone — no instructor marks the work, no peer reads the notes, no
maintainer rejects a patch — and a wrong explanation arrives in the same
confident prose as a right one. That is a real hazard and it is not fully
solvable from inside.

What limits it is that most of this work ends in a physical result, and
hardware does not care what anyone believed. A number is measured or it is
not, a decoded frame is accepted by a real receiver or it is not, an
airframe flies or it does not. Nothing marks that work, but nothing needs
to — and that verdict is not available for the theory-shaped parts of a
bought syllabus either, so on the practical half this is better checked
than a course rather than worse.

The offset is partial in two ways worth naming. It only covers what the
build actually exercises: a misunderstanding that never touches the outcome
survives indefinitely. And the verdict can arrive late and be misread on
the way — [[subghz-collar-remote-clone]] beeped about 70% of the time for
months, and the first explanation for why fitted everything visible on
screen and was wrong, killed a session later by a hand measurement. **"It
works" and "I understand why it works" are separate claims, and only the
first one checks itself.** Keeping them apart is what `## Lessons` is for,
and why a killed hypothesis is written down next to the answer that
replaced it.

## What stays worth knowing

The courses below were first ordered on four things: the size of the gap, how
often a skill is reused across the projects, what the hardware costs, and what
the field actually asks for. A fifth criterion was missing. It does not change
what the courses are, but it changes the emphasis inside most of them — how
long a piece of knowledge keeps its value, now that most code can be written
by an agent. It ended up changing the order as well, once the first of those
four turned out to have been measured against the wrong thing.

The usual answer to that is to learn fundamentals and skip specific
technologies, and it is half wrong in a way that matters. The better axis is
**where the ground truth lives, and who can reach it.** An answer recoverable
from text that already exists is cheap to obtain: API surface, framework
idiom, config syntax, a driver written from a datasheet, a protocol
implemented from a spec. An answer that exists only inside a physical system,
and has to be measured out of it, is not. Neither is deciding what "correct"
means, which has to happen before anything can be checked against it.

[[subghz-collar-remote-clone]] is the evidence and it is already written down.
URH's Autodetect reported 400 samples per symbol against a true 417.75 — a
wrong number, stated confidently, in a format indistinguishable from a right
one, and only a hand measurement at the 50% crossing disagreed. The
capture-damage hypothesis for the 70% reliability was coherent, fitted
everything visible on screen, and was wrong; it died to a measurement rather
than to an argument. `esp_reset_reason()` turned out to be clobbered by the
OTA reflash that delivered the code reading it, which is written in no
document. The line from that note that generalises furthest is the one about
evidence: a tool that has not been run against a known answer is not one.

So, in rough order of how well it holds:

1. **Measurement and instrumentation.** Getting a number off physical hardware
   that can be defended — choosing what to measure, knowing the instrument's
   own error, and validating a tool against a known answer before believing
   it.
2. **Debugging where the model and the hardware disagree.** The errata, the
   clobbered register, the return path that was not where the schematic
   implied it was.
3. **Owning the specification.** What "works" means, which failure modes
   matter, and what the latency, power and spectrum budgets are.
4. **Architecture under physical constraint.** Power, thermal, timing, duty
   cycle, bill of materials, certification — trade-offs where being wrong is
   expensive and slow to find out about.
5. **Physics and mathematics with a long half-life.** Propagation, noise
   figure, matching, sampling, control theory. Forty years of evidence
   already.
6. **Reading and judging a system I did not write.** Errata, an unfamiliar
   kernel subsystem, generated code. The only one on this list whose value is
   rising.

What shrinks is memorising interfaces — API signatures, framework fluency,
tool menus, boilerplate. The tempting conclusion is to skip them entirely and
learn only the mechanism underneath, and that is the mistake, because the
interface is frequently the compressed record of the hard problem.
`-EPROBE_DEFER` exists because of a probe ordering problem, `regmap` because
every SPI and I²C driver was reimplementing the same register cache, the DMA
API because of cache coherency. Skipping the interface leaves the mechanism
with nothing to attach to, and leaves no way to tell correct-looking code from
correct code.

The conclusion is not that less code gets written, but that it gets written
for a different reason: enough to read and to judge, rather than enough to be
fluent at producing. Which is the rule this vault already applies to its own
notes — teach the mechanism rather than the API surface, and say what breaks
without the abstraction.

## What is already known

The criteria above were applied to an inventory taken from this vault, and
the vault is not where the work is recorded. Re-taking the inventory from the
repositories moved one item a long way and trimmed five others, so it is
written down here rather than left implicit: an ordering derived partly from
the size of a gap is only as good as the list of what is already closed.

### The Advanced Embedded Software Development course, Oct 2024 to May 2025

AESD, a graded online course from the University of Colorado Boulder, taken
to completion — nine assignments and a final project. What it covered:

- A character driver with a circular buffer, `llseek` and an `ioctl`
  interface, plus `scull` and the `misc-modules` examples built and loaded as
  out-of-tree modules.
- Cross-compilation for `arm64` with `aarch64-none-linux-gnu-`, including
  reading `file` output back to work out why a binary would not run.
- A root filesystem assembled by hand: mainline `linux-stable` v5.15.163 built
  from source, BusyBox on top, and the dynamic loader and its libraries
  (`ld-linux-aarch64.so.1`, `libc.so.6`) copied into place by hand — the
  exercise that makes a sysroot stop being magic.
- A Yocto layer, `meta-aesd`, with a recipe for each of those modules, an
  image recipe, and a patch applied to third-party source through the recipe
  rather than by editing the source.
- One kernel Oops, captured and read: a null dereference traced back to
  `faulty_write+0x18/0x20` through `ksys_write` and `el0t_64_sync`.
- POSIX threads and mutexes, and `fork`/`exec`/`wait` from the system-call
  side.

### lcdcontrol, Jun 2025 to Jan 2026

The follow-on, done alone, and the most recent Linux work here by seven
months. Three repositories driving an HD44780 16x2 character display from a
Raspberry Pi 4:

- `lcdcontrol` is an out-of-tree kernel module. A `cdev` with a dynamically
  allocated `dev_t` and a device class, `copy_from_user` into a `kzalloc`
  buffer, `mutex_lock_interruptible` around a 32-byte shadow copy of the
  screen, terminal-style scrolling when a line completes, `read` served from
  that shadow copy because the display's read/write pin is tied to ground,
  and `ioctl` commands for clear, display, cursor and blink.
- `lcdcontrol-user` is the userspace tool over that device node, including a
  monitor mode putting the IP address, the CPU temperature from
  `/sys/class/thermal`, uptime and hostname on the display.
- `lcdcontrol-yocto` is the build. Two layers, split deliberately:
  `meta-lcdcontrol` holds the module and application recipes, and
  `meta-rpi-config` holds the product — a development image carrying
  `kernel-devsrc`, a toolchain and `strace`, and a production image with
  `debug-tweaks` off and root reachable only by SSH key. The board support
  package layer, `meta-raspberrypi`, is consumed unmodified.

### Where both of them stop

This is the useful half, and it is specific.

Everything above ran on qemu-aarch64 or a Raspberry Pi 4. Both already have a
board support package, so a machine configuration has never been written for a
board that had none. Neither boots through U-Boot — the Raspberry Pi hands off
from a GPU-side bootloader — so the boot chain below the kernel is untouched,
and so is a board that comes up saying nothing at all.

No driver written so far is bound to hardware by description. `hd44780.c`
takes its six GPIO numbers from macros and requests them with `gpio_request`
and `gpio_direction_output`, the integer interface that the descriptor
interface in `linux/gpiod.h` replaced. There is no `platform_driver`, no
`probe`, no `of_match_table` and no devicetree node: the module's `init` grabs
pins by number, which works on exactly one board. That is a sharper statement
of the gap than "the vault knows char drivers", and it is the one to plan
against.

Nothing in either was measured. No latency number, no power number, no trace.

### What this does to the argument at the top of this note

The case for writing these courses is that a bought one is generic by
construction, pitched at nobody's level, mostly watched rather than done, and
half-skipped. AESD was none of those. It was graded, the assignments were
built rather than watched, and it was finished. Paying for it was not the
mistake that argument predicts.

What it did not supply is narrower, and it is what the Linux course below is
now actually for: a board with no board support package, a boot chain with
U-Boot in it, and any measurement whatsoever. The rest of the argument stands
for the four courses that are not about Linux, where nothing has been bought
and nothing has been taken.

## The five courses

Each one is a project note when it gets written, with subject deep-dives in
`notes/` and exercises reusing hardware from the projects it feeds. In the
order they are meant to be done, which is argued below.

| Course | Arc | Projects it feeds | New hardware |
| --- | --- | --- | --- |
| **RF and wireless** | Radio as physics → DSP and IQ → modulation and coding → own PHY and MAC | 5 | ~150 € instruments, plus a TX-capable SDR |
| **Bare-metal and RTOS** | Reset vector → drivers by datasheet → FreeRTOS → Zephyr → OTA | 6 | ~35 € |
| **Embedded Linux** — written | Boot ROM → drivers → Yocto BSP → signed A/B updates | 4 | ~58 € |
| **Hardware design** | Datasheets → KiCad → layout and SI → fab and assembly → bring-up | 3 | ~120 € plus fab runs |
| **Control and real-time** | Sensors → filtering → PID → state estimation → sensor fusion | 3 | shares the RC gear |

"Feeds" is not a dependency. No project in the vault has a course in its
`depends:`, and none should — a course is where a skill is learned, not an
artifact another project consumes. Putting one in the graph would park half
the vault behind a fourteen-module syllabus, which is exactly the shape the
dependency graph was pruned to remove.

### The order, and what would change it

The first version of this ordering had Embedded Linux first and RF second,
and it was built from four inputs: the size of the gap, how often a skill is
reused across the projects, what the hardware costs, and what the field asks
for. Two of those were wrong. The gap sizing came from the vault rather than
from the repositories, and the section above is what it looks like corrected.
And "what the field asks for" was left general when it did not have to be:
the work is aimed at embedded software with RF as the main focus, and an
order that does not say so is being decided by something it has not written
down.

**RF and wireless, first.** It scores highest of the five on the criterion
above — propagation and noise figure do not get a version bump, and almost
every step is measurement-bound, which is the one thing on that list nothing
else can supply. Its instruments are what make every other course's
measurements possible rather than asserted. It holds the only open technical
problem in the vault. And it is the direction the rest is aimed at, which on
its own would be enough.

The cost objection was what kept it second, and it survives contact only if
the purchases are treated as one lump. They are not, and the module list
below already stages them. The crystal set, the regenerative receiver, dB and
transmission lines, link budgets, sampling and complex baseband, the
modulations and the receive chain all run on the RTL-SDR and the CC1101
already on the bench, for nothing. A NanoVNA and a TinySA (~150 € together)
are first needed at antenna measurement and matching. A transmit-capable
SDR — ADALM-Pluto at ~230 €, or a HackRF at ~150 € — is first needed at the
PHY module, which is the last one. So the expensive part of the most
expensive course is late *inside* it, and putting the course first does not
put the spending first.

**Bare-metal and RTOS, second.** The old argument for it holds unchanged and
is still the second-best one here: Cortex-M firmware is the most *reused*
skill in the vault — the bootloader, the console, the custom board, the
growbox, the car, the plane and the drone — and it is the one where I have
nothing. Reading and pruning somebody else's mbed firmware on a MAX32620,
which is what the health-sensor project actually was, is not the same as
having written a reset handler. It costs ~35 €, and for RF work in particular
it is the course that matters most after RF itself: a radio driver on a
Cortex-M is the shape most of that work takes.

**Embedded Linux, third.** It went first, and the reason it went first was
that the board was already owned, the course costs 58 €, and it was believed
to be the thinnest part of the field. The first two hold. The third was
false — it is the best-covered track here, not the thinnest, and roughly a
third of the syllabus below was already built twice on other boards.

It is also the course most exposed to the criterion above, which was written
before the inventory and reads better after it. Yocto recipes, Kconfig,
devicetree syntax and driver boilerplate are text-mediated work, and
text-mediated work is what an agent already does well — and, it turns out,
what has already been done here by hand. What survives the test is what the
gap list below was pointing at: bring-up when the board says nothing at all,
latency as a measured quantity, ftrace and perf and eBPF as a discipline,
power measured in µA, DMA where the cache and the device disagree, and
upstreaming, where the acceptance test is a maintainer with no reason to be
kind. Those are the modules to spend time in, and none of them is the one
that writes a recipe.

**Hardware design, fourth.** It sits after RF on purpose. The parts of it
that matter most for the aim are RF layout, matching networks and antenna
keepouts, and none of those can be brought up without the vector network
analyser and the spectrum analyser the RF course buys. It is also the only
course with a cost that recurs — fab runs — and the slowest feedback loop
here, two weeks to be told the return path was wrong.

**Control and real-time, last.** This is the largest genuine gap in the
inventory: no repository contains a control loop of any kind, and it is the
only track the audit made *worse* rather than better. It is last anyway, and
the honest reason is relevance rather than difficulty — it is the furthest of
the five from where the work is aimed. It scores second only to RF on
durability, so if the aim changes this is the one that moves, and it moves a
long way.

What would change this order: the RF course being written is what unlocks
it — the two projects the Cortex-M course is built around are already
specified while the RF course is still an outline, and an outline cannot be
started. If that stays true for long, bare-metal goes first by default rather
than by argument, and that should be recorded as what happened rather than
presented as the plan.

### RF and wireless, in outline

Starts where [[analog-am-transmitter-receiver]] starts — a crystal set, so
that resonance and impedance are things that have been touched before they
are things in an equation — and ends with a PHY and MAC written from
nothing. In between: dB and transmission lines, instruments and antenna
measurement, matching networks and the Smith chart, link budgets and noise
figure, sampling and complex baseband, the modulations, the receive chain
that recovers timing and carrier, error coding, then chipset radios at
register level, spread spectrum, and the 802.15.4 and BLE link layers.

It also finishes the open problem in [[subghz-collar-remote-clone]]
properly, since the encoding that fits none of the standard schemes is
exactly what the receive-chain and coding modules are for.

**The capture-and-replay module**, which absorbed a project that used to
stand on its own. Take an arbitrary signal off the air with the RTL-SDR,
analyse it down to symbols, and transmit it back — validated against the
blinds remote, because a slat that moves is an unambiguous answer. Then
repeat across modulations: OOK, 2-FSK, 4-FSK, GFSK, MSK, and the encodings
on top of them — Manchester, PWM, PPM, and the whitening and CRCs that hide
underneath. The CC1101 already on the bench transmits all of those, and its
raw async mode bit-bangs arbitrary OOK timing, so most of this module costs
nothing.

The repeater-shaped problems come with it: matching a frame against a
whitelist before acting on it, suppressing the loop when a transmitter hears
its own output, and budgeting an 868 MHz duty cycle that a repeat spends
twice. Those were worth learning; a box in the hallway that repeats a remote
whose blinds already reach Home Assistant through their own gateway was not.

Instruments are the real cost: a NanoVNA and a TinySA are what turn antenna
work from guessing into measuring, and a **TX-capable SDR** is what makes
building an own PHY possible at all — an ADALM-Pluto at around 230 € (full
duplex, 70 MHz–6 GHz, Analog Devices' own teaching platform) or a HackRF at
around 150 € (half duplex, 8-bit, wider but coarser). Bought when the PHY
module is reached, not before: everything up to that point runs on the
RTL-SDR and the CC1101. An oscilloscope belongs to this course rather than
the Linux one.

The PHY module is also the other half of a split that starts in
[[subghz-linux-router]]: a MAC and an L2 of mine on someone else's
modulation there, a modulation of mine here, and a comparison between them
that neither project could produce alone.

This is the course the criterion above weights up hardest. Propagation and
noise figure do not get a version bump, and almost every step is
measurement-bound — an antenna is matched or it is not, and no amount of
reasoning about it substitutes for a VNA and a hand on the trimmer. It also
holds the one genuinely open problem in the vault, the collar encoding that
fits none of the standard schemes, and an open problem teaches better than a
syllabus does. That was written as the argument against an earlier ordering
that had this course second; it is the argument for the present one.

### Bare-metal and RTOS, in outline

Cortex-M architecture, the vector table and the reset handler, linker
scripts, `.data` and `.bss` by hand, then peripherals driven from the
reference manual with no HAL. Interrupts and the NVIC. A serial bootloader
with A/B slots — [[bare-metal-bootloader]] entire. Then RTOS concepts where
getting them wrong is visible: stack sizing, priority inversion, starvation
under trace. Then Zephyr, devicetree and Kconfig and an out-of-tree board
port, which is [[ble-sensor-node-pcb]]. Then low power measured in µA,
testing and HIL, and MCUboot in production.

The split inside this course is the sharpest of the five. The concepts —
memory map, linker script, interrupt latency, priority inversion, stack
sizing — are durable, and are also exactly where generated code is confidently
wrong, because none of them is visible in the code that violates them. The
code itself is the most substitutable in the vault. So the weight belongs on
measuring the latency and breaking the RTOS deliberately to watch the failure
mode, rather than on writing the driver a second time.

### Hardware design, in outline

Reading datasheets and reference designs, schematic capture, the power tree,
footprint discipline, stackup and return paths, signal integrity, RF layout
and antenna keepouts, DFM and JLCPCB, hand SMD assembly, and bring-up.
[[ble-sensor-node-pcb]] is already at `planning` and is this course's
project.

Durable in the physics, disposable in the tooling. Stackup, return paths,
signal integrity and the power tree are spatial judgement about where current
actually flows, checked by a fab run that takes two weeks to tell me I was
wrong. KiCad is the part that will be replaced, and is the part worth the
least time.

### Control and real-time, in outline

Sensor characterisation and noise, filtering, PID properly — including
anti-windup and derivative kick, which is where hand-tuned loops actually
fail — then state estimation and complementary filters, then sensor fusion.
[[rc-car-custom-controller]], [[printed-rc-plane]] and
[[custom-flight-controller-drone]], in that order: a loop that surges, then
a loop that glides when it is wrong, then a loop that falls.

Second only to RF on the criterion above, and for the same reason: the
mathematics is from the 1960s and still governs, and the plant is physical, so
a tune is confirmed by a vehicle that stops oscillating rather than by
anything that can be argued. "Bounded, not fast" is judgement, and a loop that
falls out of the sky is an acceptance test nothing can talk its way past.

It also starts from further back than any of the other four. Nothing I have
written contains a control loop — no PID, no filter, no state estimator, in
any repository — so unlike the Linux course there is no covered ground to
subtract. That is an argument for its value and not for its position; it is
last because it is furthest from where the work is aimed, and those are
different things.

### The subject that is not a course

USB has a full project note, a subject deep-dive and no course to belong to.
That is not an oversight — it is what a *bus* looks like against a syllabus
built out of *arcs*, and it is worth writing down rather than leaving as a
hole in the map, because until now this note did not mention USB at all.

Its three halves attach to three different courses. Descriptors, endpoints,
transfer types and device firmware are bare-metal work on the nRF52840.
The host driver, the gadget framework and TCPM are Embedded Linux, and are
already counted there — [[usb-device-and-linux-driver]] is one of the four
projects that course feeds. The connector, the CC resistors, the ESD array
and the differential pair are hardware design. A fifteenth module would
either teach the same protocol three times or park two courses behind a
third, so the subject lives in [[usb-protocol-and-linux-stack]] and the work
lives in the project, which is the same split every course module already
uses.

Against the criterion at the top of this note it splits cleanly, and the
split is the useful part. The protocol layer is durable: host-mastered
polling, descriptors, the four transfer types and the data toggle have not
moved since 1996 and will outlast every API written on top of them. The
kernel side is exactly the text-mediated work the criterion marks down —
a `usb_driver` skeleton is boilerplate an agent writes correctly. What sits
in between is the part that earns the time, and it is measurement-bound in
the same way the RF course is: an enumeration that fails at step four, a
descriptor read back off the wire with `usbmon`, a device that NAKs forever
and looks alive. None of that is arguable from a datasheet, and it is why
the project's plan is built around deliberate breakage rather than around
getting a driver to work once.

Reading order rather than dependency: the note is worth having read before
the bare-metal course reaches the custom board, since the descriptor set is
designed at schematic time and the 5.1 kΩ CC resistors are decided before
anything is programmable at all.

## Topics the projects do not cover, and should

These came out of writing the Linux course. Each one is genuinely part of
the field and appears in no project note in this vault. Listed here so they
have somewhere to be turned into projects from.

The first version of this list conflated two different claims — *absent from
`projects/`* and *not known* — and they come apart badly, because the work in
`## What is already known` is in neither the vault nor the project notes. So
each item below now says which of the two it is, and where a thing has been
done once already, what specifically is left. Six of the twelve shrank and one
disappeared.

**In the Linux course, absent from the projects:**

1. **A board with no board support package.** This replaces what used to read
   "Yocto, Buildroot and BSP construction — the largest single gap", which was
   the wrongest sentence in this note: two Yocto builds exist, one of them
   with a hand-written layer split, and recipes, `.bbappend`s, image variants
   and `local.conf` are all worked ground. What is left of it is narrow and
   worth stating exactly. **Buildroot** has never been used at all — the two
   routes taken were a BusyBox root filesystem by hand and Yocto, with nothing
   in between. And both builds consumed a BSP layer somebody else wrote,
   `meta-raspberrypi` or qemu's, so writing a machine configuration for a
   board that has none is untouched. That is the gap; the tool is not.
2. **The boot chain.** Every note begins at a booted Linux, and so does every
   build so far — the Raspberry Pi hands off from a GPU-side bootloader, so
   U-Boot has never been in the path. SPL, DDR init, boot order, FIT images
   and what to do when the board says nothing at all: all untouched. A
   mainline kernel built from source is not, and that part of the module is a
   second pass rather than a first.
3. **ELF and the ABI.** Cross-compilation itself is done — a toolchain
   triplet, a sysroot, and the dynamic loader copied in by hand until the
   interpreter path stopped being mysterious. What is left is the layer under
   it: ELF sections, relocations and symbol resolution read directly; the
   soft-float against hard-float ABI wall, hit on purpose; musl against glibc;
   and building a toolchain rather than using one.
4. **Binding a driver to hardware by description.** The vault and the
   repositories between them have three char drivers and not one
   `of_match_table`. `hd44780.c` takes its GPIO numbers from macros — so the
   gap is `platform_driver`, `probe`, devicetree matching and the `gpiod`
   descriptor interface first, and then the subsystems: IIO, input, hwmon and
   `regmap`. A char driver for a sensor gets rejected on sight upstream, and
   knowing *why* is this item rather than knowing that it does.
5. **DMA and kernel memory management.** Absent, and the source of a large
   share of real embedded bugs.
6. **Latency as a measured quantity.** [[beaglebone-pru-realtime]] reaches
   for a PRU without anything first establishing what the CPU could actually
   have done, which is the wrong order. Nothing anywhere has been measured,
   which makes this the widest of the twelve.
7. **Power management on Linux** — runtime PM, cpuidle, cpufreq,
   suspend/resume, wakeup sources. Absent, and decisive for any
   battery-powered Linux device.
8. **Security and updates** — verified boot, dm-verity, A/B, provisioning,
   SBOM. Absent, and it is most of the distance between a working build and a
   product. The nearest thing already done is a production image built apart
   from the development one, with `debug-tweaks` off and root reachable only
   by key — which is the posture without any of the mechanism.
9. **The Linux wireless stack** — `mac80211`, `cfg80211`/`nl80211`,
   regulatory domains. The vault has sub-GHz and Thread and nothing about
   Wi-Fi. Bringing Wi-Fi *up* on a built image is done — the firmware package,
   NetworkManager, `iw` — which is configuration and not the stack.
10. **Observability** — ftrace, perf, eBPF, ramoops post-mortem — as a
    discipline rather than as `printk`. One Oops has been read back to a
    symbol and an offset, which is the entry point to this and nothing more.
11. **Upstreaming.** `checkpatch`, patch series, binding review, mailing
    lists. Writing a patch and carrying it in a recipe is done; being told no
    by somebody who maintains the subsystem is not. Still the only item on
    this list whose outcome cannot be self-assessed: a patch is correct enough
    for a maintainer to take, or it is not.
12. **Automated testing for embedded** — ptest, KernelCI and LAVA, boot
    farms, hardware-in-the-loop. Nothing in the vault is tested at all, and
    the test harnesses met so far were supplied rather than written.

**Visible from the other four courses, worth flagging early:**

- **EMC and pre-compliance.** Both RF and hardware design need it, and a
  device that radiates is a device that can fail certification. It ranks
  higher than the rest of this list under the criterion at the top: it is
  regulatory, physical and measured, the answer is not in any text, and a
  chamber booking is not something to meet for the first time at the end of a
  project.
- **Instrumentation, as a subject rather than a purchase.** It appears above
  only as "instruments are the real cost", filed under the RF budget, and that
  undersells it — getting a number off hardware that can be defended is the
  first durable skill and the one every other measurement here rests on. What
  a scope's bandwidth and probe loading actually do to an edge, what a VNA
  calibration is compensating for, what a spectrum analyser's resolution
  bandwidth does to a noise floor, and how to establish ground truth before
  believing a tool. Half of it was learned in anger on
  [[subghz-collar-remote-clone]] and none of it is written down.
- **Reading and judging a system I did not write.** Errata against observed
  behaviour, an unfamiliar kernel subsystem read well enough to extend it,
  someone else's driver reviewed for what it gets wrong. Nothing in the vault
  covers it, everything in the vault assumes it, and it is the one item here
  whose value is going up rather than down. This bullet used to say nothing
  covered it *anywhere*, and that was wrong in an interesting direction: the
  MAX32620 health-sensor project was 293,000 lines of vendor mbed firmware
  imported whole, and the only work of mine in it deleted 287 lines of device
  drivers that were not needed and added a heart-rate characteristic to the
  BLE service — seventeen lines. Reading enough of somebody else's firmware to
  know which 287 lines were safe to remove is precisely this skill. One
  instance five years ago is not coverage, but it is not zero, and it is the
  only evidence for the durable skill this note ranks as rising fastest.
- **Functional safety and coding standards** — MISRA, static analysis,
  requirements traceability. Dull, and not optional the moment the firmware
  can hurt someone.
- **Unit testing embedded C** off-target, with the hardware behind a seam.
  Nothing in the vault is tested at all.
- **Fixed-point arithmetic and numerical care** on parts with no FPU — the
  flight controller will meet this whether or not it is planned for.

### Projects these suggest

Not written yet, and only worth writing if they survive the vault's own
test — that a project has to end up used, not demonstrated:

- A reproducible, signed, A/B-updatable product image, as a thing that
  actually runs something in the flat rather than as a Yocto exercise
- A mainline-quality IIO driver taken through review to acceptance —
  the [[ble-sensor-node-pcb]] sensor is a candidate
- A battery-powered Linux node profiled for runtime PM, which is the honest
  counterweight to assuming Linux means mains power
- A two-board boot-test rig — one board power-cycling and flashing the
  other — which would serve every course here

## Where this sits

- [[embedded-linux-course]] — the only one written, now third in the order
  rather than first, and the source of most of the list above
- [[subghz-collar-remote-clone]] — the RF course's starting material and its
  one open problem, and the project that supplies most of the evidence for
  the criterion this note is ordered by
- [[bare-metal-bootloader]] and [[freertos-pocket-console]] — the two
  projects the second course would be built around, and between them the
  most reused skill set in the vault
- [[zephyr-devicetree]] — the first reference note written here, and a good
  example of the shape the course modules take
