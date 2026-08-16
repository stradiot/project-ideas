---
tags: [note, course, embedded, linux, toolchain, elf]
created: 2026-08-10
---

# Cross-Toolchains and ELF

Reference note. The [[embedded-linux-course]] module that follows
[[reading-a-soc-trm]]. Every other module compiles something for a machine
that is not the one compiling it, and this is the module that makes that
stop being a magic incantation copied off a wiki.

The question it answers: what is actually inside `arm-linux-gnueabihf-gcc`,
and why does the same source produce a binary that runs here and not there?

## Why cross-compilation exists at all

The board has a 1 GHz single core and 512 MB of RAM. A kernel build on it
takes most of a day; a Yocto build would take a week and run out of disk
first. So the build happens on the fast machine and the result runs on the
slow one, and everything awkward about embedded development follows from
that split.

The tempting alternative — compile on the target, it is a real Linux after
all — is a trap worth naming. It works for one program, then the target
needs headers, then a compiler, then the build takes forever, then the thing
being shipped contains a toolchain, and then the image is 800 MB and the
build is not reproducible because it depends on what happened to be installed
on that board. Every embedded shop learns this once.

## The four parts

A "toolchain" is four things that must agree with each other:

| Part | Job | Failure if mismatched |
| --- | --- | --- |
| **binutils** | Assembler, linker, `objdump`, `readelf` | Link errors, wrong relocations |
| **gcc** | Compiles to ARM instructions | Wrong ISA, illegal instruction on target |
| **libc** | The C library *for the target* | Runs on the host, segfaults on the board |
| **sysroot** | The target's headers and libraries | Links against host libs, fails at load |

The sysroot is the part that is genuinely conceptually new. It is a directory
that pretends to be the target's `/`, holding `usr/include` and `usr/lib` as
the target has them. When cross-compiling, the compiler must look there and
not in the host's `/usr/include`, because the host's headers describe the
host's kernel and the host's libc. Almost every confusing cross-build failure
is a build system that found a host header.

## The triplet, and what it actually encodes

`arm-linux-gnueabihf` is four decisions:

- `arm` — the architecture
- `linux` — there is a kernel and a libc, as opposed to bare metal
  (`arm-none-eabi`, which is what [[bare-metal-bootloader]] would use)
- `gnu` — the libc is glibc
- `eabihf` — the ABI, and specifically **hard float**: floating-point
  arguments are passed in VFP registers

The `hf` is the one that bites. Soft-float and hard-float binaries cannot
call each other, and the error message when they meet does not say so
clearly. A library built soft-float linked into a hard-float program fails
at link time with something about incompatible floating-point ABIs, and the
fix is never in the source.

The choice of libc matters more than people expect:

| libc | Size | Where it fits |
| --- | --- | --- |
| **glibc** | Largest | The default; complete, fast, and what almost everything expects |
| **musl** | Small, clean | Static linking is genuinely small; some glibc-isms missing |
| **uClibc-ng** | Small | Long-standing embedded choice, Buildroot's default for years |
| **bionic** | — | Android's; mentioned only so it is recognisable |

## ELF, in the parts that matter

The output is an ELF file, and being able to read one is what turns "it does
not run" into a diagnosis.

- **Sections** are for the linker: `.text` code, `.rodata` constants,
  `.data` initialised variables, `.bss` zero-initialised and taking no space
  in the file. **Segments** are for the loader — the same bytes grouped by
  what permissions they need. `readelf -S` and `readelf -l` show the two
  views.
- **`.bss` occupying no file space** is why a hello world is 8 KB and a
  program with a 10 MB array is still 8 KB. It is also exactly what the
  startup code in [[bare-metal-bootloader]] has to zero by hand, because on
  bare metal nobody else will.
- **Symbols** — `nm` — defined, undefined, local, global. An undefined symbol
  at link time is a missing library; an undefined symbol at *load* time is a
  missing shared object, which is a different problem with a similar message.
- **Relocations** are the entries saying "patch this address once you know
  where things landed". They are what makes position-independent code
  possible and what `objdump -r` shows.
- **The interpreter.** A dynamically linked ELF names its loader in a
  `PT_INTERP` header — usually `/lib/ld-linux-armhf.so.3`. If that exact path
  does not exist on the target, the kernel refuses to run the binary and says
  "No such file or directory" about a file that plainly exists. This error
  costs everyone a day exactly once.

Static versus dynamic is a real design decision on embedded, not a default.
Static: one file, no loader, no version skew, larger per binary, and every
binary must be rebuilt to fix a libc CVE. Dynamic: shared pages across
processes, one library to patch, and a whole class of deployment problems.
For an initramfs with three programs in it, static wins. For a full image
with two hundred, it does not.

## Build systems, and where they look

The whole job of cross-compiling a package is convincing its build system to
use the cross-compiler and the sysroot instead of the host's.

- **autotools**: `./configure --host=arm-linux-gnueabihf`. `--host` is the
  machine the output runs on; `--build` is the one compiling. Getting these
  backwards is a classic.
- **CMake**: a toolchain file setting `CMAKE_SYSTEM_NAME`,
  `CMAKE_C_COMPILER` and `CMAKE_FIND_ROOT_PATH`, plus the `FIND_ROOT_PATH_MODE_*`
  variables that stop `find_library` wandering into `/usr/lib`.
- **Meson**: a cross file, which is the same idea declared rather than
  scripted.
- **pkg-config**: needs `PKG_CONFIG_SYSROOT_DIR` and `PKG_CONFIG_LIBDIR`, or
  it will cheerfully report the host's library flags and the link will fail
  in a way that points nowhere near the cause.

This is exactly the drudgery Buildroot and Yocto exist to absorb, which is
worth feeling once before [[rootfs-buildroot-yocto]] takes it away.

## Exercises

The build host is the aarch64 Linux VM. ARM publishes aarch64-hosted
`arm-none-linux-gnueabihf` toolchains, so the prebuilt route works there.

Exercise **1** is already done, for `arm64` with `aarch64-none-linux-gnu-`,
including the `file`-output check — and so is the substance of **4**, though
by the opposite route: rather than renaming the loader to break a working
binary, the loader and its libraries were copied into a hand-built root
filesystem until the binary started working. Same lesson, arrived at from the
other side. The rest of this list is untouched, and **3**, **6** and **7** are
where the module actually earns its place: what is inside the toolchain, and
what an ABI mismatch looks like when it fails. See
[[embedded-learning-curriculum]].

1. **Hello, cross.** Build a static hello with the prebuilt toolchain, get it
   onto the board, run it. *Success: it prints.* Check `file` on it first and
   confirm it says ARM, EABI5, statically linked.

2. **Set up the NFS loop now.** Export a directory from the build host, mount
   it on the board, and from here on never copy a binary by hand again.
   *Success: rebuild on the host, run on the board, no card and no `scp`.*
   This pays for itself within the week.

3. **Read the ELF.** On that binary: `readelf -h`, `-S`, `-l`, `nm`,
   `objdump -d | head -50`. *Success: you can point at where execution starts,
   name three sections and say what each holds, and explain why `.bss` has a
   size but no file offset.*

4. **Dynamic, and the interpreter trap.** Rebuild the same source dynamically.
   Run it — it works. Now find its `PT_INTERP` with `readelf -l`, rename that
   loader on the target, and run it again. *Success: "No such file or
   directory" for a file that exists, and you know exactly why.* Put it back.

5. **musl versus glibc.** Build the same source against both, statically.
   Compare sizes. *Success: a number, and an opinion about which belongs in an
   initramfs.*

6. **Deliberate breakage — the ABI wall.** Compile one object with
   `-mfloat-abi=soft` and link it against a hard-float program. *Success: the
   linker's exact complaint, and the ability to recognise it instantly next
   time.* This error appears for real whenever a stray prebuilt library gets
   into an image.

7. **Build a toolchain.** crosstool-NG, targeting `arm-unknown-linux-gnueabihf`.
   It will take a while. *Success: the toolchain builds and rebuilds the
   exercise-1 binary.* Then look inside the sysroot it produced and find the
   kernel headers, and understand why the toolchain needed the kernel's
   version to exist at all.

8. **Cross-build two real packages.** One autotools (`zlib` or `libpng`), one
   CMake. Install both into the sysroot, then build a program that links
   against them. *Success: it links and runs on the board.* Then deliberately
   unset `PKG_CONFIG_LIBDIR` and watch a build find the host's copy — the
   failure mode this module is really about.

## What industry expects here

That "it does not run on the target" is a five-minute problem, not a
day-long one, because the diagnosis is mechanical: check `file`, check
`readelf -l` for the interpreter, check the libc, check the float ABI.

Beyond that: knowing that a toolchain has a version and that it is part of
the product. Two engineers with different toolchains produce different
binaries, and the answer is that the toolchain comes out of the build
system — which is what [[rootfs-buildroot-yocto]] and its SDK are for. The
question "which compiler built the firmware currently in the field" should
have an answer, and on a lot of projects it does not.

## Where this leads

- [[embedded-linux-course]] — the course this is a module of; its plan holds
  the order
- [[reading-a-soc-trm]] — the previous module; `-mcpu` and NEON only make
  sense knowing what core is in the chip
- [[linux-boot-chain-uboot]] — the first real thing built with this toolchain
- [[rootfs-buildroot-yocto]] — where all of this becomes someone else's
  problem, correctly
- [[bare-metal-bootloader]] — the same tools with `arm-none-eabi` and no libc
  at all, where `.bss` becomes something you have to zero yourself
