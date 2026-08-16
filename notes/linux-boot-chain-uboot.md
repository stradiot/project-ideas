---
tags: [note, course, embedded, linux, uboot, boot]
created: 2026-08-10
---

# The Linux Boot Chain and U-Boot

Reference note. The [[embedded-linux-course]] module after
[[cross-toolchains-and-elf]]. Every project note in this vault begins at a
booted Linux, which quietly assumes the hardest and least documented part of
embedded work has already happened.

The question it answers: what runs between power-on and `start_kernel`, and
what do I do when the board says nothing at all?

## The chain, and why it has so many links

On the AM335x, power-on to shell is five programs, each one loading the next:

```
Boot ROM  →  MLO (SPL)  →  u-boot.img  →  kernel + DTB  →  init
 in mask     in 64 KB      in DDR         in DDR          userspace
 ROM         SRAM
```

The reason for the two U-Boot stages is the 64 KB of on-chip SRAM from
[[reading-a-soc-trm]]. At reset there is no DRAM — DDR3 needs its controller
configured, its timings set and a calibration sequence run before a single
byte can be stored. So something has to run without DRAM, and that something
must fit in 64 KB. That is SPL, shipped as `MLO`. Its entire job is: set up
clocks, initialise DDR, find the next stage, load it into the DRAM that now
exists, jump.

Full U-Boot then has room to be large: drivers for MMC, Ethernet, USB and
filesystems, a scripting environment, and enough of a device model to be
recognisably a small OS. Its job is to find a kernel and a devicetree, put
them somewhere sensible, and hand over.

Understanding this shape transfers directly. Nearly every SoC does the same
thing under different names — SPL/MLO here, BL1/BL2/BL31 on ARM Trusted
Firmware parts, the bootrom/bl2 split on others. The constraint that creates
it is always the same: no DRAM yet.

## The boot ROM decides before you do

The masked ROM is the one part that cannot be changed, and it decides
everything about recovery. At reset it samples the SYSBOOT pins and gets an
ordered list of places to look — MMC0 (the SD card), MMC1 (eMMC), SPI, UART0,
USB0 — and tries each in turn.

It looks for either a raw image at a fixed offset or a file called `MLO` in
the first FAT partition, depending on the mode. And crucially, **an invalid
image is skipped and the list continues**. That fall-through is the safety
net the whole course rests on: as long as the eMMC holds a working system,
a completely broken SD card boots the eMMC instead.

On the BeagleBone the boot button (S2) held at power-on changes which device
is tried first. Which order is default and which the button selects is worth
confirming on the board rather than trusting any note — including this one —
because it is the difference between an experiment and a brick, and it takes
one minute to verify by experiment.

The UART and USB entries in that list are the real recovery path. A board
with nothing valid on any storage will sit there offering to receive an image
over serial, which is how a genuinely bricked board comes back without a
programmer.

## U-Boot, as a thing to actually use

The environment is a key-value store, persisted somewhere on the media, and
it is the whole user interface.

- `bootcmd` — what runs automatically after `bootdelay`
- `bootargs` — the kernel command line, passed on to Linux
- `printenv`, `setenv`, `saveenv` — read, change, persist
- `bdinfo` — what U-Boot thinks the memory map is

The commands worth knowing early: `mmc list` and `mmc part`, `ls mmc 0:1`,
`load mmc 0:1 ${loadaddr} zImage`, `tftp`, `dhcp`, `md` and `mw` for reading
and writing memory directly, `bootz` / `booti` / `bootm` to start a kernel,
and `go` for a raw jump.

Modern U-Boot mostly does not need hand-written `bootcmd` any more:
**distroboot** scans devices in a configured order, looks for
`extlinux/extlinux.conf` or `boot.scr`, and does the right thing. That is why
a stock SD image "just boots". Knowing that the generic mechanism is what is
running — and being able to turn it off and do it by hand — is the actual
skill.

### The handover

`bootz ${loadaddr} - ${fdt_addr_r}` passes three things to the kernel: the
kernel image, optionally an initramfs, and the devicetree blob's address.
ATAGs, the old mechanism, are dead on ARM; a modern ARM kernel expects a DTB
pointer in r2 and nothing else. This is where [[linux-devicetree]] physically
enters the picture — the blob U-Boot hands over is the only description of
the hardware the kernel will get.

FIT images are the better way to do this. A single file containing kernel,
one or more DTBs and optionally an initramfs, each with a hash, described by
an image tree source. Two reasons to care: one file instead of three, and —
the important one — the hashes can be **signed**, which is the entire basis
of verified boot in [[embedded-linux-production]].

## The development loop that saves the course

Swapping an SD card for every kernel rebuild is the default workflow and it
is miserable. The alternative, set up once:

- kernel and DTB fetched over **TFTP** from the build host
- root filesystem mounted over **NFS** from a directory on the build host

`setenv bootargs 'console=ttyS0,115200 root=/dev/nfs rw nfsroot=<host>:<path>,v3 ip=dhcp'`
and a `bootcmd` that TFTPs both images. Now a rebuild is `make && reboot the
board`, the rootfs is a normal directory that can be edited with a normal
editor, and the SD card comes out of the loop entirely. Every later module
assumes this is running.

## When the board says nothing

The silent-board checklist, in order, because the causes are ranked by how
often they are actually the cause:

1. **Power.** Is it browning out? A USB port that cannot supply the current
   produces a board that starts and dies mid-boot, and it looks exactly like
   a software fault. This is why the budget has a 5 V supply in it.
2. **Console wiring.** TX to RX, ground connected, 3.3 V not 5 V, right
   `/dev/tty*`, 115200 8N1. Swapped TX/RX gives perfect silence.
3. **Boot source.** Did it try the device you think it tried? Pull the SD
   card and see whether the behaviour changes.
4. **Bad first stage.** Garbage characters instead of a banner usually means
   a baud mismatch; total silence after previously working usually means the
   MLO is bad.
5. **U-Boot loads, kernel does not.** Now there is a console and a prompt,
   and this is no longer a hard problem.
6. **Kernel starts, then silence.** Almost always `console=` wrong in
   `bootargs`, or the DTB does not match the kernel. `earlycon` exists
   precisely for this and is the first thing to add.

## Exercises

Everything on microSD. The eMMC is not written to in this module, which is
what makes all of it safe.

1. **Map the chain by observation.** Boot the stock image and record where
   each stage announces itself — SPL banner, U-Boot banner, kernel first
   line, init. *Success: five timestamps and the ability to say which program
   printed each.*

2. **Build mainline U-Boot.** `am335x_evm_defconfig`, cross-compiled. Put
   `MLO` and `u-boot.img` on a FAT partition on a fresh card, boot it, reach
   the prompt. *Success: a U-Boot prompt from a binary you built.*

3. **Explore the environment.** `printenv`, `bdinfo`, `mmc list`, `ls mmc
   0:1`. Change `bootdelay`, `saveenv`, reboot, confirm it persisted, and
   find out where on the media it was stored. *Success: you can say which
   sectors hold the environment.*

4. **Boot a kernel by hand.** No distroboot — `load`, `load`, `bootz` typed
   out. *Success: the kernel starts from commands you typed.* Then read the
   `extlinux.conf` that distroboot would have used and see that it says the
   same thing.

5. **Set up TFTP and NFS root.** As above. *Success: a full rebuild-and-boot
   cycle without touching the card.* Budget real time for this one; it is
   mostly host-side networking and it is worth every minute.

6. **Build and boot a FIT image.** Write an `.its`, run `mkimage`, boot it
   with `bootm`. *Success: one file replaces three.* Keep this — it is the
   input to signing in [[embedded-linux-production]].

7. **Add a U-Boot command.** Something trivial that prints a register or the
   board's serial. *Success: it runs from the prompt.* The point is finding
   out that U-Boot has a driver model, a Kconfig and a build system that all
   look familiar — it is much more like the kernel than it looks.

8. **Deliberate breakage — corrupt the MLO.** Overwrite the first stage on
   the SD card with garbage. Power on. Observe what the ROM does. *Success:
   the board boots the eMMC instead, and you have watched the fall-through
   that makes this whole course low-risk.* Then restore the card.

9. **Deliberate breakage — break `bootargs`.** Remove `console=`, boot, and
   watch a kernel that is running perfectly say nothing at all. Recover it
   with `earlycon`. *Success: silence diagnosed as a console problem rather
   than a crash.*

10. **Change the boot order.** Establish by experiment what the boot button
    actually does on this board, and write it down. *Success: a rule you
    trust, tested twice.*

## What industry expects here

This is the single most common embedded Linux interview question, phrased as
"walk me through what happens from power-on to your application running".
The answer is expected to include why there are two bootloader stages, what
initialises DRAM, how the kernel finds out about the hardware, and what the
handover looks like.

In practice the expectation is that bringing up a new board is not
frightening: get a console, get SPL running, get DDR right, get to a U-Boot
prompt, and the rest is ordinary work. DDR timing bring-up on a genuinely new
board — running the vendor's register calculator, fixing what it gets
wrong — is a specialist job, but knowing that it is the job is the baseline.

The other expectation is treating the bootloader as part of the product. It
has a version, it is in the build system, it can be updated, and updating it
is the most dangerous operation the device supports. Bootloaders are where
field bricking comes from.

## Where this leads

- [[embedded-linux-course]] — the course this is a module of; its plan holds
  the order
- [[reading-a-soc-trm]] — the 64 KB of SRAM that forces the two-stage split
- [[cross-toolchains-and-elf]] — the toolchain used to build all of it
- [[linux-kernel-build-and-config]] — the next link in the chain
- [[linux-devicetree]] — the blob U-Boot hands over
- [[embedded-linux-production]] — where FIT images grow signatures and
  `bootcount` grows rollback
- [[bare-metal-bootloader]] — the same problem on a Cortex-M with no ROM to
  help and no DDR to initialise, which makes the comparison instructive in
  both directions
