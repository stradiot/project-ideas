---
tags: [project, course, embedded, linux, kernel, yocto]
status: idea
depends: []
created: 2026-08-10
repo: embedded-linux-course
---

# Embedded Linux Course

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Learn embedded Linux properly, from the boot ROM to a signed image that
updates itself in the field, on hardware I already own.

The test I want to be able to pass at the end is a specific one: hand me a
custom board with a supported SoC and no BSP, and I can bring it up — get a
console, get U-Boot running, get a mainline kernel booting, describe the
board in devicetree, write drivers for whatever is hanging off it, build a
reproducible image with Yocto, and ship updates to it that can roll back.
That is the job description, and every module below exists because it is
part of it.

Half of that test is already passed, and naming which half is what this note
is now organised around. The unpassed half is the phrase *with no BSP*: every
board worked on so far came with a board support package and booted without
U-Boot in the path, and nothing built on any of them was ever measured.

This is fourteen subjects, each one a note in `notes/` with the theory and
the exercises, and this note carries the order and the state. It is
deliberately long. Embedded Linux is not a weekend, and the honest version
of the syllabus is the one worth writing down.

### What is already covered, and why some modules below are short

Some modules here are noticeably thinner than others, and that is deliberate
rather than an oversight. The Advanced Embedded Software Development course
from the University of Colorado Boulder (Oct 2024 – May 2025) and the
`lcdcontrol` project that followed it (Jun 2025 – Jan 2026) between them
already covered a character driver with `ioctl` and `llseek`, cross-compiling
and the sysroot, a BusyBox root filesystem built by hand on top of a mainline
kernel, two Yocto layers with module, application and image recipes, and one
kernel Oops read back to a symbol. [[embedded-learning-curriculum]] holds the
inventory and the exact boundaries.

All of it ran on qemu-aarch64 and a Raspberry Pi 4. **None of it ran on the
BeagleBone**, so nothing below is ticked on account of it — an exercise that
would only repeat covered ground on a new board has been removed from the
plan instead, and what is left is either new or new on this hardware. The
boxes still mean what they say.

Deliberately out of scope: desktop Linux, Android and AOSP, x86 and server
work, and anything requiring an oscilloscope — nothing here is analog, and
that instrument belongs to the RF course rather than this one.

This is the only one of five courses written so far, and third in the order
they are meant to be done — behind RF and wireless and behind bare-metal and
RTOS firmware, ahead of hardware design and control systems. It was written
first and was meant to be done first; taking the inventory of what is already
known is what moved it. All five are mapped in
[[embedded-learning-curriculum]], along with the argument for that order and
what each would need when its turn comes.

## Learning value

The whole of it — this is a course, so there is nothing else here. Fourteen
modules, each with its own note in `notes/`:

- The boot chain end to end: ROM, SPL, U-Boot, and what hands control to
  what
- Describing hardware to a kernel — devicetree, and why a bus that cannot
  enumerate needs one
- Drivers as a subsystem rather than a file: the driver model, character
  devices, interrupts split top and bottom half, DMA and the memory API
- Building the userspace deliberately — cross-toolchains and ELF, Buildroot
  against Yocto, systemd and D-Bus as architecture
- Shipping: reproducible images, signed A/B updates that roll back, and
  measuring latency rather than asserting it

The test it is aimed at is stated in the goal above: an unfamiliar board
with a supported SoC and no BSP, brought up to a booting mainline kernel
with drivers for whatever is hanging off it.

## Practical value

None directly, and that is structural rather than a shortcoming. A course
produces a skill, not an artifact — which is exactly why no project in the
vault carries a course in its `depends:`, and why putting one there would
park half the vault behind a syllabus.

What it does produce indirectly is real. The capstone builds
[[industrial-sensor-node-linux]], which is a deployed device rather than an
exercise. The BeagleBone Green stops being a board that was bought and
becomes a board that is used, which is also what makes
[[beaglebone-green-case]] worth having. And it stays cheap either way: 58 €,
on hardware already owned, which is why being third in the order costs
nothing to sit on.

## Architecture

The board is the [[beaglebone-green-case|BeagleBone Green]] already on the
bench. It is not a compromise: AM335x is mainline-supported in both Linux
and U-Boot, TI publishes a full technical reference manual for it, it has a
PRU on die for the real-time module, and it boots from microSD in preference
to eMMC — which means the eMMC holds a working system that can always be
fallen back to, and every experiment risks nothing but a €4 card. The
Raspberry Pi stays where it is, running Home Assistant.

What I build by hand, and what I take as a finished block:

| Block | Approach | Why this side of the line |
| --- | --- | --- |
| Cross-toolchain | Built once with crosstool-NG, then use a prebuilt | Building it once is what makes a sysroot stop being magic; doing it every time is a waste |
| U-Boot | From mainline source | The boot chain is half of embedded Linux and it is invisible until it breaks |
| Kernel | From mainline source | See below |
| Every driver | Written from scratch | The whole point |
| Root filesystem | Buildroot, once | BusyBox by hand and Yocto are both already done elsewhere; Buildroot is the one of the three never used, and the middle of the range is where the comparison is decided |
| BSP layer | Written from scratch | Including `meta-ti` wholesale is what a job does; writing one is what a course does — and consuming somebody else's is the only thing done so far, which makes this the sharpest remaining item in the whole module |
| The board, sensors, RT patch | Bought or taken as given | Nothing to learn from re-deriving them |

### Mainline over the vendor SDK, everywhere

TI ships a working SDK with a kernel tree, a U-Boot tree and a Yocto layer.
Using it, the board boots in an afternoon. I am not going to use it, except
to read it.

The reason is that a vendor tree teaches the vendor's tree. Mainline teaches
Linux. Everything transferable — how Kconfig composes, how the driver model
resolves probe order, how devicetree bindings get reviewed, why a subsystem
exists — is visible in mainline and papered over by an SDK that has already
made every decision. And the actual daily work of an embedded Linux engineer
is reconciling a vendor tree against mainline: forward-porting patches,
finding what the vendor changed and why, deciding what to upstream. That
work is impossible without knowing what mainline looks like first.

Where the vendor tree is genuinely ahead — the PRU remoteproc support, some
of the AM335x power management — the note says so and I read their patches
rather than pretending mainline has it.

### The rule that keeps this cheap

Nothing writes to eMMC until the production module. Every kernel, every
U-Boot, every rootfs goes on microSD. The board's boot ROM prefers the SD
card when one is inserted and there is a button to force it, so a completely
broken SD image is recovered by pulling the card out. This is why no second
board and no JTAG probe appear in the budget: there is nothing to brick.

### Where the exercises land

The exercises are not toys where they do not have to be. Three of them are
the first real steps of projects already in this vault:

- The GPIO interrupt driver and its D-Bus daemon are
  [[industrial-sensor-node-linux]], finished and on the wall.
- The CC1101 SPI driver and the `net_device` on top of it are phases 2 and 3
  of [[subghz-linux-router]], using the radio already on the bench.
- The PRU latency comparison is what decides whether
  [[beaglebone-pru-realtime]] deserves to stop being deferred.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Board | BeagleBone Green | Already owned |
| Console | USB-UART at 3.3 V, `picocom` | Already owned; J1 header, 115200 8N1 |
| Dev loop | TFTP + NFS root over Ethernet | No card swapping between builds — this is the single biggest time saver in the course |
| Build host | aarch64 Linux VM in UTM, ~100 GB | Yocto cannot run natively on macOS |
| Devicetree | `dtc`, `make dtbs_check` | |
| Tracing | `ftrace`, `trace-cmd`, `perf`, `bpftrace` | |
| Debug | `kgdboc` over the serial console | Cheaper and less fiddly than JTAG on this board |
| Timing | 8-channel USB logic analyzer, `sigrok` | SPI/I2C bring-up, then jitter measurement |
| Images | Buildroot, then `bitbake` | |

The BBG's JTAG pads are unpopulated and fine-pitch. `kgdboc` over the serial
console does everything JTAG would for this course, so the header stays
unsoldered and the probe unbought.

## Budget

Rough estimates. Listed against the module that first needs the item, so
nothing is bought before it is used.

| Item | Cost | First needed |
| --- | --- | --- |
| microSD ×3, 16 GB A1 | 12 € | Boot chain — one to break, one known-good, one for A/B slots |
| 5 V 2 A supply | 8 € | Boot chain — USB power browns out and looks exactly like a boot bug |
| PIR sensor (HC-SR501) | 2 € | Char drivers — a real edge interrupt |
| BME280 breakout, I2C | 4 € | Driver model — the IIO exercise |
| 8-ch USB logic analyzer | 12 € | Driver model — SPI bring-up, later jitter |
| USB Wi-Fi dongle, mainline `mac80211` | 12 € | Networking — `ath9k_htc` if it can still be found, else `rtl8xxxu` |
| Breadboard, jumpers, headers | 8 € | Char drivers |
| **Total** | **58 €** | |

Not bought, deliberately: an oscilloscope (nothing here is analog), a JTAG
probe (see Tools), a second board (nothing to brick), a Raspberry Pi (one is
owned and busy).

Sourcing: [[parts-sourcing]] — the microSD cards and the 5 V supply are the
two lines where a bad part imitates the boot bug this course exists to teach
diagnosing, and the breadboard, jumpers and headers are three separate
customs classifications, which is more duty than they are worth.

## Software / firmware

The stack, in the order it gets built:

- **Toolchain** — `arm-linux-gnueabihf`, prebuilt from ARM for the aarch64
  host, plus one built by hand with crosstool-NG to see what is inside it
- **Bootloader** — mainline U-Boot: SPL/MLO, DDR init, environment,
  distroboot, FIT images, and later verified boot and `bootcount` rollback
- **Kernel** — mainline Linux, `multi_v7_defconfig` reduced to a board
  defconfig; out-of-tree modules built against it
- **Devicetree** — `am335x-bonegreen.dts` extended by overlay, with YAML
  bindings that pass `dtbs_check`
- **Drivers** — char + IRQ first, then the driver model properly: I2C and
  SPI client drivers, `regmap`, IIO, LED class, and a `net_device`
- **Root filesystem** — Buildroot, then Yocto with an own BSP layer and an
  own machine configuration; the BusyBox-by-hand step is not repeated
- **Userspace** — C daemon under systemd with socket activation, cgroup
  limits and `sd_notify` watchdog; D-Bus for local IPC; a D-Bus → MQTT
  bridge into Home Assistant
- **Production** — signed FIT images verified by U-Boot, dm-verity,
  RAUC A/B updates with rollback, SBOM and license manifest

## Plan

The whole arc, in build order. Fourteen modules; each one has a note in
`notes/` holding the theory and the exercises, and the boxes here are the
milestones from it.

This list is the order of record, which is why no module note carries a
number. Numbering them meant that inserting or moving one silently falsified
thirteen other notes and every project that pointed at them, and a field
nothing recomputes is a field that goes stale. A note names the module it
follows instead, and the sequence below is where the order actually lives.

**Ground — the board and the manual** ([[reading-a-soc-trm]])

- [ ] Serial console up on J1, `picocom` at 115200, watch the stock eMMC image boot
- [ ] Identify every major chip on the board from silkscreen and datasheet alone
- [ ] Find the McSPI0 register base and the GPIO1 base in the AM335x TRM without searching the web
- [ ] Read the AM335x errata sheet and write down the three that would affect this course
- [ ] Implement `container_of` from scratch and explain the offset arithmetic

**Toolchains and ELF** ([[cross-toolchains-and-elf]])

- [ ] Build a toolchain with crosstool-NG and use it for a static hello, run on the board over NFS
- [ ] Read the ELF: sections, symbols, relocations, the interpreter path
- [ ] Link the same source against musl and against glibc, compare size and `ldd`
- [ ] Break it on purpose — soft-float against hard-float — and read the error until it is obvious
- [ ] Cross-build one autotools and one CMake package correctly, with a toolchain file

**The boot chain** ([[linux-boot-chain-uboot]])

- [ ] Build mainline U-Boot for `am335x_evm`, boot it from SD, reach the prompt
- [ ] Map the whole chain out loud: ROM → MLO → u-boot.img → kernel → init
- [ ] Set up TFTP + NFS root and boot the board with no card swapping
- [ ] Add a custom command to U-Boot and run it from the prompt
- [ ] Build a FIT image with kernel + DTB and boot that instead
- [ ] Corrupt the MLO deliberately, observe the failure mode, recover the card
- [ ] Write down what the boot pins do and how the SD card wins over eMMC

**The kernel** ([[linux-kernel-build-and-config]])

- [ ] Build a mainline kernel and boot it over TFTP
- [ ] Reduce a defconfig to a board defconfig and justify every symbol removed
- [ ] Boot with `initcall_debug` and read the init timeline end to end
- [ ] Add a `printk` in `start_kernel` and see it before the console handover
- [ ] Measure boot time from reset to shell and record the baseline number
- [ ] Bisect a deliberately planted regression across a range of kernel commits
- [ ] Build and load an out-of-tree module against this exact kernel

**Devicetree** ([[linux-devicetree]])

- [ ] Decompile the running DTB with `dtc -I fs` and diff it against source
- [ ] Add an I2C sensor node and watch the driver probe from `dmesg`
- [ ] Mux a pin through `pinctrl` and verify the change with an LED
- [ ] Write a YAML binding for an own `compatible` and pass `make dtbs_check`
- [ ] Break `status` and the bus parent on purpose, diagnose both from the tree
- [ ] Build an overlay, apply it from U-Boot, then apply one at runtime

**Char drivers and interrupts** ([[linux-char-drivers-and-irqs]])

- [ ] Add `poll` support backed by a wait queue, prove it with `select` in userspace
- [ ] Race it from two processes, find the corruption, fix it with the right lock
- [ ] PIR on a GPIO edge with a threaded IRQ handler waking the readers
- [ ] Sleep in a spinlock deliberately and read the resulting splat
- [ ] Turn on lockdep and KASAN and trip each one on purpose

**The driver model and subsystems** ([[linux-driver-model-and-subsystems]])

The longest module here, and the only one that grew. Three char drivers exist
across this vault and the older repositories and not one of them is bound to
hardware by description — they take their pins from macros. That first box is
the correction.

- [ ] A `platform_driver` bound by devicetree — `of_match_table`, a real `probe`, and GPIOs taken with `devm_gpiod_get` rather than by number
- [ ] BME280 as a plain I2C char driver, values readable and correct
- [ ] Rewrite it as an IIO driver, read it with `iio_generic_buffer`
- [ ] Convert the register access to `regmap` and delete the hand-rolled code
- [ ] Convert every allocation to `devm_*` and prove remove is now empty
- [ ] Trigger `-EPROBE_DEFER` deliberately and watch the retry succeed
- [ ] CC1101 SPI driver skeleton with GDO0 as a threaded IRQ, probing cleanly
- [ ] Write down which subsystem each of this course's drivers belongs in, and why a char device would be rejected upstream

**Memory and DMA** ([[linux-memory-and-dma]])

- [ ] Compare `kmalloc`, `vmalloc` and `alloc_pages` for a large buffer, know when each fails
- [ ] Use the wrong GFP flag in atomic context and read the resulting failure
- [ ] `mmap` a driver buffer into userspace and share a counter through it
- [ ] Streaming DMA on McSPI with correct `dma_map`/`sync` calls
- [ ] Skip the sync deliberately and observe stale cache data
- [ ] Measure throughput: `read()` versus `mmap`, and explain the difference

**Root filesystems** ([[rootfs-buildroot-yocto]])

- [ ] Buildroot image that boots and auto-loads the drivers written so far
- [ ] Package an own daemon as a Buildroot package in `BR2_EXTERNAL`
- [ ] Set up the Yocto build host and build `core-image-minimal` for the board
- [ ] Write a machine conf for a custom AM335x board, with no `meta-ti` underneath it
- [ ] Generate an SDK with `populate_sdk` and build against it
- [ ] Produce a license manifest and identify the actual GPL obligations
- [ ] Write down when Buildroot is the right answer and when Yocto is

**systemd, D-Bus and userspace** ([[systemd-dbus-embedded]])

- [ ] Daemon in C reading the driver, running as a plain unit
- [ ] Convert it to socket activation so it does not start at boot
- [ ] Add cgroup limits, then exceed them on purpose and watch the kill
- [ ] Add `sd_notify` and `WatchdogSec`, hang the daemon, watch it come back
- [ ] Export a D-Bus interface, watch a PIR event arrive under `busctl monitor`
- [ ] Write a udev rule giving the device a stable name and correct permissions
- [ ] Cut boot-to-daemon-ready time with `systemd-analyze` and record the number
- [ ] Bridge D-Bus to MQTT, see motion and temperature in Home Assistant

**Networking** ([[linux-networking-and-netdev]])

- [ ] A virtual `net_device` that can be assigned an address and pinged
- [ ] Add NAPI polling, and explain what problem it solves
- [ ] Configure it over netlink instead of ioctl, and know why that matters
- [ ] Carry IP over 868 MHz — CC1101 driver wired up as `rf0`
- [ ] Measure what that link can actually do and be honest about it
- [ ] Put the USB dongle in monitor mode, capture frames, check the regulatory domain
- [ ] Trace one packet with ftrace from the driver to the socket

**Real-time and latency** ([[linux-realtime-and-latency]])

- [ ] Baseline `cyclictest` under load on the stock kernel, keep the histogram
- [ ] Build PREEMPT_RT, repeat the measurement, compare worst case not average
- [ ] Find the biggest offender with the `irqsoff` and `wakeup_rt` tracers
- [ ] `SCHED_FIFO` thread toggling a GPIO, jitter measured on the logic analyzer
- [ ] Pin IRQs and isolate a CPU, measure the improvement
- [ ] Same toggle on the PRU, compare by orders of magnitude, decide about [[beaglebone-pru-realtime]]

**Debugging and performance** ([[linux-kernel-debugging]])

- [ ] Plant a null deref, a use-after-free and a deadlock; find each with the right tool
- [ ] Read an Oops properly — `decode_stacktrace.sh` back to a source line, on a driver of mine rather than a planted one
- [ ] Set up ramoops and recover a panic log across a reboot
- [ ] `ftrace` a driver's probe path with `function_graph`
- [ ] Flamegraph the daemon under `perf`, find where it actually spends time
- [ ] Attach `kgdb` over the serial console and single-step through probe
- [ ] Run `checkpatch`, `sparse` and `coccinelle` over every driver until clean

**Production** ([[embedded-linux-production]])

- [ ] Sign a FIT image, verify it in U-Boot, tamper with it and watch it refuse
- [ ] Write down honestly what GP silicon means for secure boot on this board
- [ ] dm-verity over a read-only rootfs
- [ ] RAUC A/B on SD with U-Boot `bootcount` rollback
- [ ] Ship a deliberately broken update and prove the rollback works unattended
- [ ] Provision a serial number and a per-device key from a factory script
- [ ] Produce an SBOM for the final image

**Capstone — the whole stack, as a product**

- [ ] Own Yocto BSP layer for the board, without including `meta-ti` wholesale
- [ ] U-Boot and kernel recipes carrying own patches
- [ ] Driver, daemon and image recipes in that layer
- [ ] Signed FIT, dm-verity rootfs, RAUC A/B, all wired together
- [ ] RT-tuned with a measured, written-down `cyclictest` number
- [ ] In Home Assistant, on the wall, running from the image
- [ ] Reproducible from a clean checkout with one command
- [ ] Submit one patch upstream — a binding fix or a documentation correction counts

That last box is deliberate. It is the only item here that cannot be
self-assessed: a patch is either correct enough for a maintainer to take or
it is not, and the person deciding has no idea who I am and no reason to be
kind. Every other box can be ticked by convincing myself. This one costs
nothing but nerve, and it is the only external check in the whole course.

Because this note carries `repo: embedded-linux-course`, the boxes above are
ticked by the SessionEnd hook — which only fires for sessions started in
that repo. Exercise code goes there, not here.

Nothing in the vault has this course in its `depends:`, and nothing should.
A course is where a skill is learned, not an artifact another project
consumes — putting it in the graph would park the entire Linux track behind
a fourteen-module syllabus, which is the shape that graph was pruned to
remove. Every project below can be started tomorrow. Doing this first only
makes them easier.

[[industrial-sensor-node-linux]] is the closest thing to an exception, and
even there the relationship runs the other way: that note is the
specification, and the capstone here is the build. Same board, same PIR,
same wall — it does not get made twice.
[[usb-device-and-linux-driver]] leans on the driver model and the memory
work, and its gadget and dual-role half runs on this same BeagleBone.
[[subghz-linux-router]] is the CC1101 exercises taken to their conclusion,
and [[beaglebone-pru-realtime]] is deferred until the real-time module
produces a number that justifies it. [[zephyr-devicetree]] is the
same syntax with an entirely different lifecycle, and the contrast is
sharpest having written both. [[embedded-learning-curriculum]] holds the
other four courses.

## Build log

Session entries live in [[embedded-linux-course-log]].
