---
tags: [note, course, embedded, linux, kernel, kconfig]
created: 2026-08-10
---

# Building and Configuring the Kernel

Reference note. The [[embedded-linux-course]] module after
[[linux-boot-chain-uboot]]. Between a U-Boot prompt and a driver there is a
kernel that has to be built, configured, booted and — when it does not
boot — diagnosed.

The question it answers: what am I actually choosing when I build a kernel,
and how do I find out what it did before it said anything?

## The tree, in the parts that get opened

Twenty-odd top-level directories, of which a handful are where the time
goes:

| Directory | What is in it |
| --- | --- |
| `arch/arm/` | The port. `boot/dts/` holds every board's devicetree |
| `drivers/` | The overwhelming majority of the source, by volume |
| `kernel/` | Scheduler, time, tracing — the actual core |
| `mm/` | Memory management |
| `net/` | The network stack |
| `fs/` | Filesystems and the VFS |
| `include/linux/` | The internal API surface |
| `Documentation/` | Better than its reputation, and where bindings live |
| `scripts/` | `checkpatch.pl`, `decode_stacktrace.sh`, Kconfig, kbuild |

The thing to internalise early: `drivers/` is most of the kernel, and the
best documentation for writing a driver is three existing drivers for
similar hardware. Reading the tree is the skill; there is no book that
substitutes.

## Kconfig, and the reason defconfigs exist

Tens of thousands of options with dependencies between them. `make
menuconfig` is the browser; `.config` is the answer; `defconfig` files under
`arch/arm/configs/` are curated starting points.

The mechanics worth knowing:

- **`make savedefconfig`** reduces a `.config` to the minimal set of options
  that differ from the defaults, which is what belongs in version control.
  Committing a full `.config` is committing twelve thousand lines that mostly
  say "default", and it makes every future diff unreadable.
- **`y` versus `m`.** Built into the image, or a loadable module. On a small
  embedded system with fixed hardware, `y` for what is always needed and no
  modules at all is a legitimate and common choice — it removes an entire
  class of "the module was not in the initramfs" problems.
- **`make olddefconfig`** when moving to a new kernel version: takes the
  existing answers, accepts defaults for everything new, asks nothing.
  `oldconfig` asks about each one, which is educational once and tedious
  after.
- **Config fragments** — small files merged with `scripts/kconfig/merge_config.sh`
  — are how Yocto and Buildroot layer changes on top of a base defconfig
  without forking it. Worth using by hand here so it is familiar there.
- **`multi_v7_defconfig`** boots on an enormous range of ARM boards by
  including nearly everything. It is the right first build and the wrong
  final one.

## The build

```
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- omap2plus_defconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc) zImage dtbs modules
make ARCH=arm INSTALL_MOD_PATH=<rootfs> modules_install
```

Outputs: `arch/arm/boot/zImage` (self-decompressing), the DTBs under
`arch/arm/boot/dts/`, and modules installed into a rootfs tree with a
`lib/modules/<version>/` directory that `depmod` has indexed.

Two things that cause real confusion. **`O=` for out-of-tree builds** keeps
the source clean and lets several configs share one checkout — worth using
from the start. And **modules must match the kernel exactly**, by version and
by config; `vermagic` mismatch is the error, and it appears constantly when a
kernel is rebuilt and the modules are not reinstalled.

## What happens at `start_kernel`

Boot is not one step, and knowing the sequence turns "it hangs" into a
question with a location:

1. `zImage`'s decompressor unpacks the real kernel and jumps to it.
2. Architecture setup: the DTB is parsed early to find memory and the
   console, page tables are built, the MMU comes on.
3. `start_kernel()` — scheduler, memory allocators, timers, interrupts, and
   the console handover.
4. **initcalls** run in levels: `early`, `core`, `postcore`, `arch`,
   `subsys`, `fs`, `device`, `late`. Every driver's registration is an
   initcall at one of these levels, which is why a driver cannot assume a
   subsystem is up unless it is at a later level than it — the ordering
   problem that `-EPROBE_DEFER` in [[linux-driver-model-and-subsystems]]
   exists to solve properly.
5. The root filesystem is mounted, and `/sbin/init` is executed as PID 1. If
   that fails the kernel panics, and the message says so.

The two flags that make all of this visible: **`earlycon`** gives a console
before the real driver is up, covering step 2 and 3 where most silent hangs
live; **`initcall_debug`** prints every initcall and how long it took, which
is both a debugging tool and the raw material for boot-time work.

## Which tree

A real decision, made once per product:

- **Mainline** — newest, and where all upstream work happens. What this
  course uses, for the reasons in [[embedded-linux-course]].
- **LTS** — a mainline release maintained with fixes for years. What most
  products should ship, because "we will just track mainline" survives
  contact with a release schedule about as long as expected.
- **Vendor tree** — the SoC vendor's fork, usually an old LTS with thousands
  of out-of-tree patches. Has support mainline lacks; has bugs mainline
  fixed years ago; is where most industry time is actually spent.

The daily work in a lot of jobs is the reconciliation: what did the vendor
change, is it upstream, can it be, and what happens at the next rebase. That
work is only possible for someone who knows what mainline looks like, which
is the argument for learning on mainline even though it is harder.

## Exercises

TFTP and NFS root from [[linux-boot-chain-uboot]] should be running before
starting; this module involves a lot of rebuilds.

1. **Build and boot mainline.** `omap2plus_defconfig`, boot it over TFTP with
   NFS root. *Success: a shell on a kernel you built.*

2. **Reduce it.** Turn the multi-board defconfig into a board defconfig:
   remove other platforms, filesystems and drivers this board has no use for.
   Rebuild, reboot, `savedefconfig`. *Success: it still boots, the image is
   materially smaller, and you can justify every removal.* This is the
   exercise that teaches Kconfig, because breaking the boot two or three
   times is part of it.

3. **Read the boot.** Boot with `initcall_debug` and walk the timeline.
   *Success: the three slowest initcalls named, with a theory about each.*

4. **Print before the console exists.** Add a `printk` early in
   `start_kernel`, boot without `earlycon` — it appears late, buffered — then
   with it, and it appears immediately. *Success: an explanation of where
   those characters were in between.*

5. **Baseline the boot time.** Reset to shell prompt, measured. Write the
   number down. *Success: a number to beat in [[systemd-dbus-embedded]].*

6. **Out-of-tree module.** A trivial `hello.ko` with its own Makefile, built
   against this kernel, loaded on the board. *Success: `insmod` and the
   message in `dmesg`.* Then rebuild the kernel with any config change,
   try to load the old module, and read the `vermagic` complaint.

7. **Config fragments.** Express exercise 2's changes as a fragment merged
   onto the base defconfig instead of a full `.config`. *Success: same kernel,
   and a diff a human can read.* This is exactly the mechanism Yocto uses.

8. **Deliberate breakage — bisect.** Take a range of upstream commits, plant
   a change that breaks the boot somewhere in the middle, and find it with
   `git bisect run`. *Success: the offending commit, found mechanically
   rather than by reading.* Kernel bisection is a genuine industry skill and
   it is much easier to learn on a planted bug than a real one at 2 a.m.

9. **Deliberate breakage — panic on no root.** Boot with `root=` pointing
   somewhere wrong. Read the panic. *Success: the message identified as "the
   kernel is fine, the rootfs is not", which is a distinction that matters in
   [[rootfs-buildroot-yocto]].*

## What industry expects here

That building a kernel is routine, and that a `.config` is a design artifact
under version control as a defconfig or fragments — not a file someone
generated on their laptop two years ago and nobody dares regenerate.

Specifically probed: the difference between `y` and `m` and when each is
right; what `initcall` levels are and why probe order is not something to
rely on; being able to bisect; and being honest about the mainline-versus-
vendor tradeoff rather than dogmatic in either direction. An engineer who
says "we ship the vendor tree because their DDR and PRU support is not
upstream, and here is our plan for the parts that could be" is giving the
right answer.

Boot time comes up more than expected, because it is a product requirement
in a lot of devices. Knowing that the measurement starts with
`initcall_debug` and `systemd-analyze`, and that the answer is usually "stop
probing things you do not have", is the expected level.

## Where this leads

- [[embedded-linux-course]] — the course this is a module of; its plan holds
  the order
- [[linux-boot-chain-uboot]] — what hands control to this
- [[linux-devicetree]] — the description this kernel is given of the board
- [[linux-char-drivers-and-irqs]] — the first module built against this
  kernel
- [[rootfs-buildroot-yocto]] — where the defconfig becomes a recipe and the
  build stops being run by hand
- [[linux-kernel-debugging]] — where `initcall_debug` grows into ftrace
