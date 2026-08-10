---
tags: [note, course, embedded, linux, debugging, ftrace, perf, ebpf]
created: 2026-08-10
---

# Kernel Debugging and Performance

Reference note. Module 12 of [[embedded-linux-course]]. Every earlier module
planted bugs deliberately; this is the one about finding them on purpose,
with the right tool rather than by staring.

The question it answers: the board is misbehaving and there is no debugger
attached — now what?

## The ladder

Pick the cheapest tool that can answer the question. Reaching for the most
powerful one first is how afternoons disappear.

| Tool | Answers | Cost |
| --- | --- | --- |
| `printk` / `dev_dbg` | "Does it get here, with what value" | Recompile, and it changes timing |
| Dynamic debug | Same, toggled at runtime | Nearly free |
| Tracepoints | "What did the subsystem do" | Free when off |
| `ftrace` | "What called what, and how long" | Low |
| `perf` | "Where does the time go" | Sampling overhead |
| eBPF | "Answer this custom question live" | Needs the toolchain |
| `kgdb` | "Stop and inspect state" | Stops the machine |
| ramoops / kdump | "What happened before it died" | Setup in advance |

### printk, done properly

Levels matter — `pr_err` through `pr_debug` — because they control what
reaches a console that may be a 115200 baud serial line. That line is slow
enough that verbose logging **changes the timing of the system**, which
makes race conditions disappear when instrumented. This is the classic
heisenbug and the reason tracing exists.

**Dynamic debug** is the improvement: `pr_debug` statements compiled in but
inert, enabled per file, per function or per line at runtime through
`/sys/kernel/debug/dynamic_debug/control`. Debug output in production
builds, costing nothing until needed. Drivers should use `dev_dbg` and
friends throughout for exactly this reason.

## ftrace

The kernel's built-in tracer, driven through `/sys/kernel/tracing`. No
external tooling, always available.

- **`function`** — every kernel function entered
- **`function_graph`** — call graph with timing per function; the most
  immediately useful for "why is probe slow"
- **tracepoints** — static instrumentation points that subsystem authors
  placed deliberately, with structured arguments. Stable, cheap, and the
  right thing to use where one exists
- **kprobes / uprobes** — attach to any kernel or userspace function
  dynamically, including ones with no tracepoint
- **the latency tracers** — `irqsoff`, `preemptoff`, `wakeup_rt` from
  [[linux-realtime-and-latency]]

`trace-cmd` is the friendly front end and produces files that KernelShark
visualises. On a target this small, recording with `trace-cmd` and analysing
on the host is the sensible split.

The filtering is what makes it usable — tracing every function on a 1 GHz
core produces more data than the board can write. `set_ftrace_filter` with a
module name or a function glob turns a firehose into an answer.

## perf

Sampling profiler plus counters. `perf top` for a live view, `perf record` /
`perf report` for a profile, `perf stat` for cycles, cache misses and branch
mispredictions, `perf sched` for scheduling latency.

Flamegraphs are the presentation that makes profiles readable — stack depth
on one axis, aggregate time on the other, and the wide plateau is the answer.

Two embedded caveats. Sampling needs the PMU, which needs kernel support
enabled. And symbols need to survive to the target, or the profile is a list
of hex addresses — which means either not stripping, or keeping the unstripped
binaries and resolving on the host. Getting this set up before it is urgently
needed is worth the hour.

## eBPF

Programs verified for safety and run in the kernel, attached to tracepoints,
kprobes or events. `bpftrace` gives a one-liner language over it:

```
bpftrace -e 'kprobe:spi_sync { @[comm] = count(); }'
```

Custom questions, answered live, on a running system, with no recompile —
which is genuinely a different capability from everything above.

The embedded caveat is real: eBPF needs a recent kernel with BTF, a
reasonably large kernel config, and the toolchain to compile programs. On a
constrained device this is often not available, and the CO-RE mechanism
(compile once, run everywhere) exists precisely to allow compiling
elsewhere. Knowing whether it is available on a given target is part of
knowing the tool.

## kgdb, without JTAG

`kgdboc` runs the kernel debugger over the serial console — full source-level
debugging, breakpoints and single-stepping, with no hardware probe. Boot with
`kgdboc=ttyS0,115200 kgdbwait` and connect `arm-linux-gnueabihf-gdb` to the
port.

Two constraints that matter: the console is now shared between the debugger
and the kernel's own output, and **the whole machine stops at a breakpoint**
— so it cannot be used to debug anything with a timing requirement, and a
breakpoint in an interrupt path may make the system unrecoverable.

This is why the budget in [[embedded-linux-course]] has no JTAG probe. JTAG
is better — it can debug the very earliest boot code, before any of this
works — but for driver debugging on a booted kernel, `kgdboc` is enough and
costs nothing.

## Reading a crash

An Oops is a report; a panic is a stop. Both dump registers, a call trace and
the faulting address.

The workflow:

1. `PC is at <function+0xNN/0xMM>` — the function, the offset, the size.
2. `scripts/decode_stacktrace.sh` with `vmlinux` and the source tree turns
   the trace into file and line numbers.
3. `objdump -dS` on the module or `vmlinux`, find the offset, look at the
   instruction and what register it dereferenced.
4. A faulting address near zero is a null dereference; a faulting address
   that is a recognisable poison value (`0x6b6b6b6b` for freed slab memory
   with `slub_debug` on) says use-after-free immediately.

The kernel is stripped in a production image, so this only works if the
matching `vmlinux` and modules were kept from the build. **Keeping build
artifacts per release is a production requirement**, not an optional
nicety — without them a field crash log is unreadable, and this is a lesson
teams tend to learn exactly once.

### Post-mortem on a headless box

The board panics on a wall at 3 a.m. and reboots. The console log is gone.

**ramoops / pstore** solves this: a region of RAM is reserved and marked as
not cleared by the bootloader, the kernel writes the tail of the log there on
panic, and after reboot it appears at `/sys/fs/pstore/`. Contents survive a
warm reset because DRAM contents largely persist across one.

Setting this up costs a devicetree node and a config option, and it is the
difference between "it rebooted, we do not know why" and a stack trace. Any
device shipping without it is choosing not to know.

`kdump` — booting a second kernel to dump the first one's memory — is the
heavyweight version and is usually too much for a 512 MB embedded board.

## Memory and locking debuggers

These belong in every development build, and the earlier modules should have
had them on:

| Option | Finds |
| --- | --- |
| **KASAN** | Use-after-free, out-of-bounds, at the moment of access, with allocation and free traces |
| **KFENCE** | The same class, sampled, cheap enough for production |
| **kmemleak** | Allocations never freed |
| **lockdep** | Lock-ordering violations *before* they deadlock |
| **`slub_debug`** | Poisoning and redzones; the `0x6b6b6b6b` above |
| **`DEBUG_ATOMIC_SLEEP`** | Sleeping in atomic context |

Lockdep is the standout. It builds a graph of lock acquisition order and
reports an inversion the first time it is *possible*, not the one time in ten
thousand it actually deadlocks. Deadlocks found by reasoning are deadlocks
found late.

KASAN costs roughly 2–3× memory and a large slice of performance, so it is a
development-build option — but it turns "corruption somewhere, sometimes"
into a precise report, and the class of bug it finds is the class that is
otherwise undebuggable.

## Static analysis

Before a patch is sent anywhere:

- **`checkpatch.pl`** — style and a surprising number of real bugs. Mandatory
  before any submission; a patch that fails it will not be read.
- **`sparse`** (`make C=1`) — kernel-specific type checking. Catches
  `__user` pointers dereferenced directly, `__iomem` misuse, endianness
  errors. Exactly the mistakes from [[linux-char-drivers-and-irqs]] and
  [[linux-memory-and-dma]].
- **`smatch`** — deeper flow analysis, finds real null-deref and error-path
  bugs.
- **Coccinelle** (`make coccicheck`) — semantic patching; both finds patterns
  and fixes them mechanically across the tree.

## Exercises

Plant the bugs deliberately; that is the point.

1. **Dynamic debug.** Convert the drivers to `dev_dbg` and enable one file's
   output at runtime. *Success: debug output with no rebuild, and none when
   disabled.*

2. **Trace a probe.** `function_graph` on the driver's probe path. *Success: a
   call graph with per-function timings, and the slowest call identified.*

3. **Use a tracepoint.** Find an existing one in a subsystem you use, enable
   it, read its structured output. *Success: an understanding of why this
   beats adding a `printk` to someone else's code.*

4. **Deliberate breakage — null dereference.** Plant one, take the Oops, run
   `decode_stacktrace.sh`, land on the source line. *Success: the exact line,
   from the log alone.*

5. **Deliberate breakage — use-after-free.** With `slub_debug=P` and then
   with KASAN. *Success: the poison pattern recognised in the first case;
   allocation and free stack traces in the second. Note how much faster the
   second is.*

6. **Deliberate breakage — lock inversion.** Two locks taken in opposite
   orders in two paths, without ever actually deadlocking. Run with lockdep.
   *Success: lockdep reports the potential deadlock on first occurrence.*

7. **ramoops.** Reserve the region, configure pstore, panic the kernel
   deliberately with sysrq, reboot, recover the log. *Success: the panic
   readable from `/sys/fs/pstore/` after a power cycle.* Keep this
   configuration for the production image.

8. **Flamegraph the daemon.** `perf record` on the sensor daemon under load,
   generate a flamegraph. *Success: an image, and a correct statement about
   where time actually goes — usually somewhere unexpected.*

9. **bpftrace, if available.** Count SPI transactions by process, or
   histogram the latency between the PIR interrupt and the daemon's wakeup.
   *Success: a histogram from a live system with no code changes.* If the
   kernel lacks BTF, establishing that and why is itself the result.

10. **kgdb.** `kgdboc` over the console, breakpoint in probe, single-step,
    inspect. *Success: source-level debugging with no probe hardware.* Then
    try a breakpoint in an interrupt handler and see what happens.

11. **Clean the drivers.** `checkpatch.pl --strict`, `make C=1` with sparse,
    and `make coccicheck`, on everything written in this course, until clean.
    *Success: no warnings.* Sparse will find at least one real bug — it
    usually does, and it is usually a missing `__user` or a wrong-endian
    access.

## What industry expects here

A ladder, climbed in order. Someone who reaches for `printk` for everything
and someone who attaches a debugger to everything are both slower than
someone who picks the right rung.

Specifically probed:

- **ftrace and perf** as basic literacy, not specialist knowledge.
- **Reading an Oops** unaided, and knowing that `vmlinux` and unstripped
  modules must be archived per release for that to be possible.
- **Post-mortem on a headless device** — the answer is ramoops or pstore, and
  it is configured before shipping rather than after the first field failure.
- **lockdep and KASAN in development builds by default.** The expected
  answer to "how do you find race conditions" is "the tooling finds them",
  not "careful review".
- **`checkpatch` clean** before anything is sent anywhere, which is
  non-negotiable if [[embedded-linux-course]]'s upstream-patch capstone is
  ever attempted.

The deeper expectation is a debugging method: reproduce, narrow, instrument
at the narrowest point, and change one thing at a time. It sounds obvious and
it is the thing that most reliably separates people under pressure.

## Where this leads

- [[embedded-linux-course]] — the course this is module 12 of
- [[linux-char-drivers-and-irqs]] — the bugs planted there, found properly
- [[linux-memory-and-dma]] — KASAN and the DMA coherency bug
- [[linux-realtime-and-latency]] — the latency tracers in their own context
- [[embedded-linux-production]] — ramoops, artifact archival and field
  diagnostics as product requirements
- [[subghz-collar-remote-clone]] — the same instinct that validated an
  analysis tool against synthetic captures before trusting it, applied to
  the kernel
