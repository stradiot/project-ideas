---
tags: [note, course, embedded, linux, yocto, buildroot, bsp]
created: 2026-08-10
---

# Root Filesystems, Buildroot and Yocto

Reference note. The [[embedded-linux-course]] module after
[[linux-memory-and-dma]], and the first that leaves kernel space. Everything
so far ran on an NFS root someone else assembled. This is the module about
building the userspace half of the system, and it is the largest single gap
between the project notes in this vault and the actual embedded Linux job.

The question it answers: how does a directory full of files become a
reproducible product image that another person can rebuild in two years?

## What a root filesystem actually is

Less than it looks. A kernel needs: something to mount as `/`, and a program
at a known path to execute as PID 1. That is the entire contract.

The minimum that works is a statically-linked BusyBox and a shell script:

```
/bin/busybox      (static)
/init             (#!/bin/sh, mounts /proc and /sys, execs a shell)
/dev, /proc, /sys, /tmp   (empty mount points)
```

Building that by hand once is worth an afternoon, because every later
abstraction is hiding it. The directories that then appear — `/etc`, `/lib`,
`/usr`, `/var`, `/run` — are convention (the FHS), populated by the init
system and the packages, not by the kernel.

Two mechanisms get confused constantly:

- **initramfs** — a cpio archive unpacked into a tmpfs that *is* the initial
  root. Either built into the kernel image or loaded alongside it. Nothing to
  mount, no storage drivers needed. On embedded it is often the whole system,
  not just a stepping stone.
- **real root** — a filesystem on actual storage, mounted by the kernel from
  `root=` or pivoted into from the initramfs.

The initramfs is the escape hatch for anything needing setup before the real
root exists: decrypting it, verifying it, choosing between A/B slots. That
last one is [[embedded-linux-production]].

### Choosing a filesystem

| Filesystem | Use |
| --- | --- |
| **ext4** | The default for SD and eMMC. Journalled, well understood |
| **squashfs** | Read-only, compressed. Small, fast to mount, cannot be corrupted by a power cut |
| **overlayfs** | A writable layer over a read-only one — the standard trick |
| **UBIFS / UBI** | Raw NAND only. Not applicable to eMMC or SD |
| **tmpfs** | RAM. For `/run`, `/tmp`, and anything that must not survive |

The design that matters for an embedded product: **read-only root, with
writable data on a separate partition.** Usually squashfs plus an overlay,
or ext4 mounted `ro`. It makes the system immune to power-cut corruption in
the part that matters, it makes updates atomic because the whole rootfs is
one object to replace, and it makes tampering detectable — which is the
precondition for dm-verity later.

A device that gets yanked from the wall a thousand times will corrupt a
writable ext4 root eventually. This is not a theoretical concern; it is the
most common field failure in the category.

## Three ways to build one

### By hand

BusyBox plus a directory tree. Total control, no tooling, and completely
unmaintainable past about ten packages. Worth doing exactly once, to know
what the others produce.

### Buildroot

A giant Makefile with a `menuconfig`. Point it at a target and a package set;
it downloads, cross-compiles and produces an image.

- **Fast, simple, and readable.** A package is a `.mk` and a `Config.in`,
  usually thirty lines. Anyone can read the whole system in a day.
- **No binary packages.** No package manager on the target — the image is the
  unit.
- **No incremental rebuild across config changes.** Change the toolchain and
  it rebuilds everything, which is the main daily annoyance.
- **`BR2_EXTERNAL`** keeps your own packages and defconfigs outside the
  Buildroot tree, which is how to use it without forking it.

### Yocto / OpenEmbedded

A build system in the way that Buildroot is not: bitbake as the engine, and a
layered metadata model.

- **Layers** compose. `meta-ti` for the SoC, `meta-openembedded` for extra
  packages, your own `meta-mything` on top. A layer can override or extend
  another without forking it — that is what a `.bbappend` is for.
- **Recipes** (`.bb`) describe one package: where the source is (`SRC_URI`),
  its license, its dependencies (`DEPENDS` at build time, `RDEPENDS` at
  runtime), and tasks that fetch, configure, compile and install.
- **Classes** (`.bbclass`) hold shared logic — `cmake.bbclass`,
  `systemd.bbclass`, `module.bbclass` for kernel modules.
- **The three axes**: `MACHINE` (which board), `DISTRO` (policy — what init
  system, what libc, what features), and the **image recipe** (which packages).
  Keeping these separate is the point of the whole design, and conflating
  them is the most common way a Yocto setup becomes unmaintainable.
- **sstate** is the shared-state cache, and it is what makes Yocto usable at
  all. Without it every change rebuilds the world; with it a shared sstate
  mirror means a colleague's first build takes minutes.
- **`devtool`** — `devtool modify` to check out a recipe's source and hack on
  it, `devtool finish` to fold the changes back as patches. This is how
  day-to-day work actually happens and it is much less well known than it
  should be.

### Which one

An honest answer, because it is an interview question:

- **Buildroot** when the product is small and fixed, the team is small, the
  image is the unit of delivery, and nobody needs to add packages in the
  field. It is faster to learn, faster to build, and far easier to reason
  about.
- **Yocto** when there are multiple products sharing a platform, when the SoC
  vendor ships a BSP layer, when licensing needs auditing, when an SDK has to
  be handed to application teams, or when someone needs binary package feeds.

Yocto's complexity is real and mostly justified by scale. Choosing it for a
one-board hobby project is how people end up hating it.

## The parts nobody mentions

**SDK generation.** `bitbake -c populate_sdk <image>` produces an installable
cross-toolchain with a sysroot matching the image exactly. This is what gets
handed to application developers who should not have to build a distribution
to compile their program. It also solves the "which compiler built this"
problem from [[cross-toolchains-and-elf]] — the toolchain comes out of the
build system, versioned with everything else.

**License compliance.** Yocto tracks the license of every recipe and can emit
a manifest of everything in the image and its licenses. This is not
bureaucracy: shipping a device containing GPL code creates an obligation to
provide corresponding source, and "we do not know what is in our image" is
not a defence. `LICENSE` and `LIC_FILES_CHKSUM` in a recipe exist to make the
build fail when an upstream project changes its license text — which is
exactly when someone should be looking.

The related deliverable is an **SBOM**, increasingly a contractual and
regulatory requirement rather than a nicety. Yocto can generate one; knowing
that is a differentiator.

## Exercises

The Yocto build host is the aarch64 Linux VM, ~100 GB free. Set
`DL_DIR` and `SSTATE_DIR` outside the build directory before the first build,
so nothing is downloaded twice for the rest of the course.

Four of these are a second pass rather than a first, and it is worth knowing
which before spending a weekend on them. **1** (a rootfs by hand) was done for
qemu-aarch64 with a mainline kernel underneath it. **6** (a first Yocto build)
was done twice, for `raspberrypi4-64` and for qemu. **7** (an own layer) and
**8** (a `.bbappend`) are `meta-lcdcontrol` and `meta-rpi-config`, which
between them carry a module recipe, an application recipe, two image recipes
and an append that installs configuration into `/etc`. Those four are kept
because they are what the theory above is *for*, and repeating one on new
hardware is cheap — but the module's time belongs in **3** (Buildroot, never
used at all), **9** (a machine configuration, the only one of these never
approached), **11** and **12**. See [[embedded-learning-curriculum]] for the
inventory this comes from.

Exercise **13** also changes character. It asks for Buildroot and Yocto
compared from having built both; Yocto has been built twice and Buildroot not
once, so the comparison is currently half-informed, which is a more honest
starting position than none and a worse one than it looks.

1. **A rootfs by hand.** Static BusyBox, a two-line `/init`, packed as a cpio
   initramfs, booted over TFTP. *Success: a shell prompt, with the whole
   filesystem in RAM and no storage involved.*

2. **Break it on purpose.** Remove `/init`. Boot. *Success: the panic message,
   recognised as "the kernel is fine, PID 1 is missing" from
   [[linux-kernel-build-and-config]] exercise 9.*

3. **Buildroot image.** Configure for the board, build, boot from SD.
   *Success: it boots to a login.*

4. **Package your own work.** The driver and daemon from earlier modules as
   Buildroot packages in a `BR2_EXTERNAL` tree, loaded at boot. *Success: a
   fresh image where the PIR driver is already loaded and the daemon running,
   with nothing done by hand.*

5. **Read-only root.** Rebuild with a squashfs root and an overlay for
   `/etc` and `/var`. *Success: it boots, the root is genuinely read-only —
   `touch /foo` fails — and the writable paths still work.* Then pull the
   power fifty times during writes and confirm nothing is corrupted.

6. **Yocto, first build.** poky plus `meta-ti`, `MACHINE` set for the board,
   `core-image-minimal`. *Success: an image that boots.* Expect the first
   build to take hours; this is normal and is what sstate exists to prevent
   repeating.

7. **Your own layer.** `bitbake-layers create-layer meta-mything`. Recipes
   for the kernel module and the daemon. Add them to an image recipe.
   *Success: the same result as exercise 4, in Yocto.*

8. **A `.bbappend`.** Change the kernel configuration by appending a config
   fragment to the kernel recipe, without forking it — using the fragments
   from [[linux-kernel-build-and-config]] exercise 7. *Success: `zcat
   /proc/config.gz` on the target shows the change.*

9. **A machine config.** Write one for a hypothetical custom AM335x board:
   its own devicetree, its own U-Boot config, its own set of machine
   features. *Success: `MACHINE=myboard bitbake core-image-minimal`
   completes.* This is the BSP skill the whole module is for.

10. **`devtool`.** Use `devtool modify` on a package, change something, build,
    and `devtool finish` to turn it into a patch in your layer. *Success: a
    `.patch` file and a recipe that applies it.*

11. **Generate and use an SDK.** `populate_sdk`, install it, build a program
    against it outside the Yocto tree. *Success: a binary that runs on the
    image.*

12. **License manifest.** Produce one for the image. Identify every
    GPL-licensed component and state precisely what obligations shipping this
    device would create. *Success: a written answer, naming components.* Then
    generate an SBOM.

13. **Buildroot versus Yocto, written down.** Having built both, write the
    argument for each. *Success: an opinion you can defend that is not
    "Yocto is complicated".*

## What industry expects here

For a large share of embedded Linux roles this module *is* the job. Not
driver writing — maintaining the layer, upgrading the vendor BSP, adding
packages, keeping builds reproducible, cutting image size, generating SDKs
and license manifests.

What gets probed:

- **Layers, and not forking.** The correct answer to "the vendor's recipe is
  wrong" is a `.bbappend` in your layer, never an edit to theirs. Someone who
  has edited `meta-ti` in place has told you a lot.
- **Machine, distro, image separation.** Conflating them is the most common
  structural mistake.
- **sstate**, what it caches, and why a shared mirror matters to a team.
- **Reproducibility.** Can this image be rebuilt bit-identically in two
  years? What is pinned, what floats, what happens when an upstream tarball
  disappears — which is why `PREMIRRORS` and an own source mirror exist.
- **Licensing.** Being able to answer "what is in this image and what do we
  owe" without a week of archaeology.
- **Image size and boot time**, both of which are usually product
  requirements and both of which are attacked from here.

The honest framing: Yocto is disliked, widely, and mostly by people who were
handed a broken setup. The engineer who understands the layer model is the
one who fixes it, and that is a durable, well-paid position to be in.

## Where this leads

- [[embedded-linux-course]] — the course this is a module of; its plan holds
  the order
- [[cross-toolchains-and-elf]] — all of that drudgery, absorbed correctly
- [[linux-kernel-build-and-config]] — the defconfig becomes a recipe and a
  fragment
- [[systemd-dbus-embedded]] — what PID 1 becomes once the rootfs has one
- [[embedded-linux-production]] — the image gets signed, verified and made
  updatable
- [[industrial-sensor-node-linux]] — the point where that project stops being
  a board with files on it and becomes something reproducible
