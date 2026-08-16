---
tags: [note, course, embedded, linux, security, ota, secureboot]
created: 2026-08-10
---

# Shipping It: Security, Updates and Production

Reference note. The [[embedded-linux-course]] module after
[[linux-kernel-debugging]], and the last one before the capstone. Everything
so far produces a board that works on a bench. This is the module about the
distance between that and a device that can be sold, deployed and updated —
which is most of the distance.

The question it answers: what has to be true before a thousand of these can
go somewhere I cannot drive to?

## Verified boot, and an honest limitation

The chain of trust idea: each stage verifies the next before executing it,
anchored in something that cannot be changed.

On a proper implementation the anchor is the SoC's boot ROM, checking a
signature against a public key hash burned into one-time-programmable fuses.
**The AM335x on this board is GP — general purpose — silicon, and it cannot
do this.** The secure-boot variant is a different part number with the
efuses and the ROM support; GP devices execute whatever is in the first
sector. No amount of software makes a GP device securely bootable.

That is worth stating plainly rather than working around, because half of
embedded security writing is vague about where the root of trust actually
is, and a chain anchored in something writable is not a chain.

What **is** possible here, and genuinely useful:

**U-Boot verified boot.** U-Boot is built with a public key embedded in its
own devicetree, and it verifies the signature on a FIT image before booting
it. The FIT from [[linux-boot-chain-uboot]] gains signatures over the kernel,
the DTB and the initramfs, and `bootm` refuses anything that does not verify.

This protects against a tampered *kernel* — a real threat, since the kernel
lives on a partition that a userspace compromise or a swapped SD card could
reach. It does not protect against a tampered *U-Boot*, because nothing
checks U-Boot. On this board that is the honest boundary, and it is still
worth having: the exercise teaches exactly the mechanism used on parts where
the ROM does anchor it.

**dm-verity** extends it to the root filesystem: a Merkle tree of hashes over
a read-only block device, root hash passed on the kernel command line inside
the signed FIT, blocks verified as they are read. Tampering with any block
causes an I/O error rather than silently executing modified code. It composes
naturally with the read-only squashfs root from [[rootfs-buildroot-yocto]],
which is one of the reasons that design was chosen there.

Above this sit **TPMs** and **TEEs** (OP-TEE on ARM TrustZone) for key
storage and attestation — worth knowing exist, out of scope for a GP AM335x.

### Secrets without a secure element

Device-unique keys have to live somewhere. Without an OTP-fused root of trust
or a secure element, anything on the filesystem can be read by anyone
holding the board. The honest positions are: accept it and limit the blast
radius by making every key device-unique so one extraction compromises one
device; or add a secure element (an ATECC608 or similar, a couple of euros)
which is the real answer for a product.

What must not happen is a shared key across a fleet. That is the failure that
turns one extracted device into every device, and it happens constantly.

## Updates, which are the actual hard part

More devices are bricked by updates than by anything else. The requirements
are unforgiving:

- **Atomic.** Power loss at any instant leaves a bootable system. There is no
  "partially updated" state.
- **Verified** before being made active.
- **Rollback** automatically if the new version does not come up.
- **Bootloader-integrated**, because only the bootloader can decide which
  system to run.

### A/B

Two complete copies of kernel and rootfs. Update the inactive one, verify,
flip a flag, reboot into it. If it fails, the bootloader falls back.

The mechanism in U-Boot is `bootcount` and `bootlimit`: U-Boot increments a
counter each boot, the running system resets it once it is satisfied it is
healthy, and if the counter exceeds the limit U-Boot switches back to the
other slot. That "satisfied it is healthy" step is a real design decision —
kernel booted is not enough; the honest check is that the application is
serving its actual function, which means the update confirmation belongs in
the application and not in an init script.

Costs double the storage for kernel and rootfs. Data lives on a third,
shared partition that is never updated, which means data migration between
schema versions is a separate problem that still has to be solved.

The tools: **RAUC** (clean, well-documented, integrates with U-Boot's
bootcount), **SWUpdate** (more flexible, more configuration), **Mender**
(includes a fleet management server), **OSTree** for a git-like model that
updates at file granularity rather than partition. RAUC is the right choice
for learning it.

**Delta updates** matter when devices are on metered links — send only what
changed. Worth knowing the option exists; a rounding error on Ethernet, the
difference between viable and not on cellular.

### Watchdogs

Layered, and each layer catches what the one above cannot:

1. **Application** — `sd_notify` to systemd, from [[systemd-dbus-embedded]],
   with the timer-thread trap already met there.
2. **systemd** — restarts the service.
3. **SoC hardware watchdog** — `/dev/watchdog`, pinged by systemd; reboots the
   board if the whole system hangs.
4. **Bootloader bootcount** — if reboots keep happening, switch slots.

The last layer is what stops a reboot loop from being a permanent brick, and
it is the one most often missing.

## The things nobody plans for

**Provisioning.** Every device needs a serial number, a MAC address, per-device
keys and calibration data. These are not in the image — the image is
identical across the fleet. They go somewhere writable and unique, written by
a factory fixture, with a record kept. Designing this late means retrofitting
identity onto devices that already shipped.

**Field diagnostics.** When a device misbehaves in the field, what can be
recovered? Persistent journald with a size cap, ramoops from
[[linux-kernel-debugging]] surviving reboots, and a deliberate decision about
whether logs are ever uploaded — which is a privacy decision as much as a
technical one.

**Debug access.** The serial console that made this whole course possible is
a login prompt on a header. On a shipped device that is either disabled,
authenticated, or accepted as a known risk. It should be a decision with a
line in a document, not an oversight.

**Archived build artifacts.** `vmlinux`, unstripped modules, the exact
manifest, per release. Without them a field crash log is unreadable, which
[[linux-kernel-debugging]] makes concrete.

**Compliance.** The license manifest and SBOM from
[[rootfs-buildroot-yocto]] stop being paperwork here: shipping GPL code
creates an obligation to provide corresponding source, including for the
kernel and any modified packages, and regulation in this area — the EU's
Cyber Resilience Act being the current example — is moving towards making
an SBOM and a vulnerability-handling process mandatory rather than
admirable. A device with a ten-year field life needs a story for security
updates over that whole life.

## Exercises

1. **Sign a FIT image.** Generate a key pair, sign the FIT from
   [[linux-boot-chain-uboot]], embed the public key in U-Boot's devicetree,
   boot with verification required. *Success: it boots, and the log says the
   signature was checked.*

2. **Deliberate breakage — tamper.** Flip one byte in the signed image. Boot.
   *Success: U-Boot refuses, with a clear message, and does not execute it.*

3. **Write down the boundary.** Given GP silicon, state exactly what the
   previous two exercises do and do not protect against, and what a
   secure-boot part would add. *Success: an honest paragraph.* This is more
   valuable than the exercises themselves.

4. **dm-verity.** Build a read-only rootfs with a verity hash tree, pass the
   root hash in the signed command line, boot it. *Success: it boots; then
   modify one block on the image and watch the read fail rather than
   succeed with modified content.*

5. **RAUC A/B.** Partition for two slots, integrate with U-Boot's
   `bootcount`, install an update bundle, reboot into it. *Success: the new
   slot is running and the old one is intact.*

6. **Deliberate breakage — the failed update.** Build a bundle whose kernel
   panics, or whose application never confirms health. Install it. *Success:
   the board tries it, fails, and comes back on the old slot unattended, with
   no intervention.* This is the single most important exercise in the
   module — an update system that has never been tested failing is an update
   system that does not work.

7. **Power-cut the update.** Pull power at several points during an install.
   *Success: every time, the board boots something.* Do this at least ten
   times, at different moments.

8. **Health check that means something.** Make the update confirmation depend
   on the sensor daemon actually publishing a reading, not on the system
   having booted. *Success: an update where the kernel boots fine but the
   application is broken still rolls back.*

9. **Provisioning.** A factory script writing a serial number and a
   per-device key to a provisioning partition, with the image itself
   identical across devices. *Success: two "devices" from one image, with
   distinct identities.*

10. **Persistent diagnostics.** Journald persistent with a size cap, ramoops
    configured, both surviving a power cut. *Success: logs and a panic trace
    readable after an unclean reboot.*

11. **Compliance pack.** License manifest and SBOM for the final image, plus
    a written statement of the GPL obligations shipping it would create.
    *Success: a document naming components and obligations.*

12. **Threat model, one page.** Who might attack this, with what access, and
    what the mitigations are — including the ones deliberately not
    implemented. *Success: a page that is honest about residual risk.*

## The questions this has to answer

This module is the difference between something that works on the bench and
something that can be shipped, and that difference takes the form of a
specific short list of questions. Each one is a failure mode that has already
burned somebody, which is why they are worth being able to answer out loud and
without notes rather than merely recognising:

- **How do you update in the field, and what happens when it fails?** A
  complete answer names A/B, atomicity, bootloader integration and automatic
  rollback, and includes having *tested* the rollback.
- **Where is your root of trust?** The good answer names the hardware anchor,
  or says honestly that there is not one and what that means. The bad answer
  is vague.
- **What happens on power loss mid-write?** Should be answerable for every
  writable thing on the device.
- **How do you debug a device you cannot touch?** ramoops, persistent logs,
  archived symbols.
- **What is in your image and what do you owe for it?** Answerable from the
  manifest, not from archaeology.
- **Fleet-wide shared keys**, recognised immediately as the mistake it is.

The mindset difference: a bench prototype optimises for making it work; a
product optimises for what happens when it does not. Every exercise above is
about a failure — tampering, a bad update, a power cut, a hang, a crash with
nobody watching — and being able to say what the device does in each case is
what "production ready" actually means.

## Where this leads

- [[embedded-linux-course]] — the course this closes; the capstone
  assembles all of this
- [[linux-boot-chain-uboot]] — the FIT image that now carries signatures, and
  the `bootcount` that now means something
- [[rootfs-buildroot-yocto]] — the read-only root that verity needs, and the
  manifest that compliance needs
- [[systemd-dbus-embedded]] — the watchdog chain's first two layers
- [[linux-kernel-debugging]] — ramoops and archived symbols as product
  requirements rather than conveniences
- [[bare-metal-bootloader]] — A/B slots, trial boot and rollback on a
  microcontroller, which is the same design at a hundredth of the scale and
  a good way to see the idea clearly
- [[thread-matter-growbox]] — MCUboot OTA for a sealed device, the same
  argument in the firmware world: once it is potted next to water, the update
  path is the only way in
