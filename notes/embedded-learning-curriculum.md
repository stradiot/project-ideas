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

Embedded Linux went first anyway, for a reason that stands: the board was
already owned, the course costs 58 €, and it is the half of the field the
existing notes are thinnest on.

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

### Bare-metal and RTOS, in outline

Cortex-M architecture, the vector table and the reset handler, linker
scripts, `.data` and `.bss` by hand, then peripherals driven from the
reference manual with no HAL. Interrupts and the NVIC. A serial bootloader
with A/B slots — [[bare-metal-bootloader]] entire. Then RTOS concepts where
getting them wrong is visible: stack sizing, priority inversion, starvation
under trace. Then Zephyr, devicetree and Kconfig and an out-of-tree board
port, which is [[ble-sensor-node-pcb]]. Then low power measured in µA,
testing and HIL, and MCUboot in production.

### Hardware design, in outline

Reading datasheets and reference designs, schematic capture, the power tree,
footprint discipline, stackup and return paths, signal integrity, RF layout
and antenna keepouts, DFM and JLCPCB, hand SMD assembly, and bring-up.
[[ble-sensor-node-pcb]] is already at `planning` and is this course's
project.

### Control and real-time, in outline

Sensor characterisation and noise, filtering, PID properly — including
anti-windup and derivative kick, which is where hand-tuned loops actually
fail — then state estimation and complementary filters, then sensor fusion.
[[rc-car-custom-controller]], [[printed-rc-plane]] and
[[custom-flight-controller-drone]], in that order: a loop that surges, then
a loop that glides when it is wrong, then a loop that falls.

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
    lists. The cheapest credible industry signal available.
12. **Automated testing for embedded** — ptest, KernelCI and LAVA, boot
    farms, hardware-in-the-loop.

**Visible from the other four courses, worth flagging early:**

- **EMC and pre-compliance.** Both RF and hardware design need it, and a
  device that radiates is a device that can fail certification.
- **Functional safety and coding standards** — MISRA, static analysis,
  requirements traceability. Dull, and asked about in interviews for any
  job where the firmware can hurt someone.
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
