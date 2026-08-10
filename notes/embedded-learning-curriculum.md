---
tags: [note, course, curriculum, embedded]
created: 2026-08-10
---

# Embedded Learning Curriculum

Reference note. The map of five courses, of which
[[embedded-linux-course]] is the first one written. It exists because
eighteen project notes describe *what* to build and none of them describe
what has to be learned first, and it turned out that gap was mostly in the
same four or five places every time.

## The five courses

Each one is a project note when it gets written, with subject deep-dives in
`notes/` and exercises reusing hardware from the projects it unblocks.

| Course | Arc | Unblocks | New hardware |
| --- | --- | --- | --- |
| **Embedded Linux** — written | Boot ROM → drivers → Yocto BSP → signed A/B updates | 4 projects | ~58 € |
| **RF and wireless** | Radio as physics → DSP and IQ → modulation and coding → own PHY and MAC | 6 projects | ~150 € instruments, plus an optional TX-capable SDR |
| **Bare-metal and RTOS** | Reset vector → drivers by datasheet → FreeRTOS → Zephyr → OTA | 7 projects | ~35 € |
| **Hardware design** | Datasheets → KiCad → layout and SI → fab and assembly → bring-up | 2 projects | ~120 € plus fab runs |
| **Control and real-time** | Sensors → filtering → PID → state estimation → sensor fusion | 2 projects | shares the RC gear |

### Which one to do second

The honest answer is bare-metal and RTOS, and it is not close. Seven of
eighteen projects sit behind [[bare-metal-bootloader]] and
[[freertos-pocket-console]] — the whole firmware track, both Thread and
Matter projects, the LoRa collar, the UWB locator and the HA controller.
Nothing in that half of the vault is reachable until those two exist. The
RF course is the more interesting one to read and the firmware course is the
one that unblocks the vault.

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

Instruments are the real cost: a NanoVNA and a TinySA are what turn antenna
work from guessing into measuring, and a TX-capable SDR is what makes
building an own PHY possible at all. An oscilloscope belongs to this course
rather than the Linux one.

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
[[rc-car-custom-controller]] and [[custom-flight-controller-drone]].

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
  projects the second course would be built around, and the vault's real
  bottleneck
- [[zephyr-devicetree]] — the first reference note written here, and a good
  example of the shape the course modules take
