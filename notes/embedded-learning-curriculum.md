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

## What stays worth knowing

The courses below were ordered on four things: the size of the gap, how often
a skill is reused across the projects, what the hardware costs, and what the
field actually asks for. A fifth criterion was missing. It does not change
what the courses are, but it changes the emphasis inside most of them — how
long a piece of knowledge keeps its value, now that most code can be written
by an agent.

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

## The five courses

Each one is a project note when it gets written, with subject deep-dives in
`notes/` and exercises reusing hardware from the projects it feeds.

| Course | Arc | Projects it feeds | New hardware |
| --- | --- | --- | --- |
| **Embedded Linux** — written | Boot ROM → drivers → Yocto BSP → signed A/B updates | 4 | ~58 € |
| **RF and wireless** | Radio as physics → DSP and IQ → modulation and coding → own PHY and MAC | 5 | ~150 € instruments, plus a TX-capable SDR |
| **Bare-metal and RTOS** | Reset vector → drivers by datasheet → FreeRTOS → Zephyr → OTA | 6 | ~35 € |
| **Hardware design** | Datasheets → KiCad → layout and SI → fab and assembly → bring-up | 3 | ~120 € plus fab runs |
| **Control and real-time** | Sensors → filtering → PID → state estimation → sensor fusion | 3 | shares the RC gear |

"Feeds" is not a dependency. No project in the vault has a course in its
`depends:`, and none should — a course is where a skill is learned, not an
artifact another project consumes. Putting one in the graph would park half
the vault behind a fourteen-module syllabus, which is exactly the shape the
dependency graph was pruned to remove.

### Which one to do second

Bare-metal and RTOS, and the reason has changed since this note was first
written. It used to be "it unblocks the vault" — back when a chain of
questionable dependencies put seven projects behind
[[bare-metal-bootloader]] and [[freertos-pocket-console]]. That chain is
gone: nothing depends on the bootloader at all now, and only the LoRa collar
waits on the console.

The real argument is simpler and better. Cortex-M firmware is the most
*reused* skill in the vault — it turns up in the bootloader, the console, the
custom board, the growbox, the car, the plane and the drone — and it is the
one where I currently have nothing. Learning it early makes seven projects
easier rather than possible, which is a weaker claim but a true one.

RF is the standing counter-argument, and it got stronger once the criterion
above was written down: it scores highest of the five on durability, its
instruments make every other course's measurements possible, and it holds the
only open technical problem in the vault. What keeps it second is cost and
sequence rather than value — the instruments are ~150 € before a TX-capable
SDR at 150–230 €, against ~35 € for bare-metal, and the two projects the
Cortex-M course is built around are already written while the RF course is
not. If the RF course gets written before the bare-metal one starts, this
ordering should be revisited rather than defended.

Embedded Linux went first anyway, for a reason that stands: the board was
already owned, the course costs 58 €, and it is the half of the field the
existing notes are thinnest on.

It is also the course most exposed to the criterion above, which is worth
saying rather than working around. Yocto recipes, Kconfig, devicetree syntax
and driver boilerplate are text-mediated work, and text-mediated work is what
an agent already does well. What survives the test is what the gap list below
was already pointing at: bring-up when the board says nothing at all, latency
as a measured quantity, ftrace and perf and eBPF as a discipline, power
measured in µA, and upstreaming — where the acceptance test is a maintainer
with no reason to be kind. Those are the modules to spend time in, and none of
them is the one that writes a recipe.

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
syllabus does. That is the argument against the ordering above, and it is
recorded there rather than here.

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

## Topics the projects do not cover, and should

These came out of writing the Linux course. Each one is genuinely part of
the field and appears in no project note in this vault. Listed here so they
have somewhere to be turned into projects from.

**In the Linux course, absent from the projects:**

1. **Yocto, Buildroot and BSP construction.** The largest single gap. This
   is the embedded Linux job description more often than driver work is, and
   nothing in `projects/` mentions it.
2. **The boot chain.** Every note begins at a booted Linux. Nothing covers
   SPL, DDR init, boot order, U-Boot, or what to do when the board says
   nothing at all.
3. **Cross-toolchains, ELF and ABI.** Assumed by every project, learned by
   none.
4. **Kernel subsystems.** The vault knows char drivers. Industry writes IIO,
   input, hwmon and `regmap` drivers, and a char driver for a sensor gets
   rejected on sight upstream.
5. **DMA and kernel memory management.** Absent, and the source of a large
   share of real embedded bugs.
6. **Latency as a measured quantity.** [[beaglebone-pru-realtime]] reaches
   for a PRU without anything first establishing what the CPU could actually
   have done, which is the wrong order.
7. **Power management on Linux** — runtime PM, cpuidle, cpufreq,
   suspend/resume, wakeup sources. Absent, and decisive for any
   battery-powered Linux device.
8. **Security and updates** — verified boot, dm-verity, A/B, provisioning,
   SBOM, license compliance. Absent, and it is most of the distance between
   a working build and a product.
9. **The Linux wireless stack** — `mac80211`, `cfg80211`/`nl80211`,
   regulatory domains. The vault has sub-GHz and Thread and nothing about
   Wi-Fi.
10. **Observability** — ftrace, perf, eBPF, ramoops post-mortem — as a
    discipline rather than as `printk`.
11. **Upstreaming.** `checkpatch`, patch series, binding review, mailing
    lists. The only item on this list whose outcome cannot be self-assessed:
    a patch is correct enough for a maintainer to take, or it is not.
12. **Automated testing for embedded** — ptest, KernelCI and LAVA, boot
    farms, hardware-in-the-loop.

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
  whose value is going up rather than down.
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

- [[embedded-linux-course]] — the one that exists, and the source of most of
  the list above
- [[bare-metal-bootloader]] and [[freertos-pocket-console]] — the two
  projects the second course would be built around, and between them the
  most reused skill set in the vault
- [[zephyr-devicetree]] — the first reference note written here, and a good
  example of the shape the course modules take
