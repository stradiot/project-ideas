---
tags: [note, course, embedded, linux, realtime, preempt-rt, pru]
created: 2026-08-10
---

# Real-Time and Latency

Reference note. Module 11 of [[embedded-linux-course]]. It exists because
[[beaglebone-pru-realtime]] reaches for a dedicated real-time core without
anything first establishing what the CPU could have done — which is the
wrong order, and the reason that project is correctly deferred until this
module produces a number.

The question it answers: how late can this be, worst case, and how do I know?

## What real-time means, and does not

Real-time is not fast. It is **bounded**. A system that responds in 10 µs
average and 40 ms occasionally is worse, for control, than one that always
responds in 500 µs. The metric is the worst case, and an average latency
figure is close to meaningless.

The distinction that follows:

- **Hard real-time** — a missed deadline is a failure. Motor commutation,
  a flight control loop.
- **Soft real-time** — a missed deadline degrades quality. Audio, video.

Linux with PREEMPT_RT is very good soft real-time and adequate hard
real-time for deadlines in the tens of microseconds and up. Below that,
Linux is the wrong tool and no amount of tuning changes it — which is what
the PRU is for, and knowing where that line falls is this module's real
deliverable.

## Where the latency comes from

Latency is the delay from an event to the code that handles it running. On a
stock kernel the contributors, roughly in order of how much damage they do:

1. **Interrupts disabled.** Nothing can happen. A driver holding interrupts
   off for a long section is the classic offender, and it is usually someone
   else's driver.
2. **Preemption disabled.** A higher-priority task cannot displace a lower
   one — every spinlock does this.
3. **Long non-preemptible kernel sections.** Big loops in syscalls or
   drivers.
4. **Priority inversion.** A high-priority task waits on a lock held by a
   low-priority one that is itself preempted by a middle-priority task.
5. **Page faults.** A first touch of a page, or worse a swap-in, on the
   critical path.
6. **Cache and TLB misses**, which is why a rarely-run handler is slow the
   first time.
7. **Frequency scaling and idle states.** Waking from a deep idle state costs
   real microseconds; frequency ramping costs more.

## The preemption models

| Model | Behaviour |
| --- | --- |
| `PREEMPT_NONE` | Kernel never preempted. Best throughput, worst latency. Servers |
| `PREEMPT_VOLUNTARY` | Explicit reschedule points. Desktops |
| `PREEMPT` | Kernel preemptible except in critical sections |
| `PREEMPT_RT` | Nearly everything preemptible |

PREEMPT_RT's mechanism is worth knowing because it explains both the benefit
and the cost:

- **Spinlocks become sleeping mutexes**, so holding one no longer disables
  preemption. `raw_spinlock_t` remains a true spinlock for the few places
  that need one.
- **Interrupt handlers become kernel threads** by default, schedulable and
  preemptible, with priorities. The pattern
  [[linux-char-drivers-and-irqs]] uses for threaded IRQs becomes the norm.
- **Priority inheritance** on those mutexes, which is the fix for inversion.
- **Softirqs** are threaded too.

The cost is throughput: more context switches, more locking overhead. A
PREEMPT_RT kernel is measurably slower at bulk work. That trade is the whole
decision.

The patch set lived out of tree from the mid-2000s and was finally merged
into mainline in 2024 — which is worth knowing both as history and because a
great deal of documentation predates it and describes applying patches that
are now a config option.

## Making userspace real-time

A PREEMPT_RT kernel does not make an application real-time. The application
has to ask:

- **`SCHED_FIFO`** or `SCHED_RR` with a priority, via
  `sched_setscheduler`. Above normal tasks, and it will monopolise the CPU if
  it misbehaves — which is what `sched_rt_runtime_us` exists to prevent.
- **`SCHED_DEADLINE`** — specify runtime, period and deadline and let the
  kernel admit or reject the task. More principled, less used.
- **`mlockall(MCL_CURRENT|MCL_FUTURE)`** — lock the address space into RAM.
  Without it, a page fault on the critical path costs everything.
- **Pre-fault the stack and pre-allocate everything.** No `malloc` in the
  real-time loop; the allocator can block.
- **Priority-inherit mutexes** between real-time threads
  (`PTHREAD_PRIO_INHERIT`), or inversion moves into userspace.

System-level tuning: **`isolcpus`** to keep the scheduler off a core,
**`nohz_full`** to stop the timer tick on it, **IRQ affinity** to move
unrelated interrupts elsewhere, and disabling frequency scaling and deep idle
states. On this single-core board isolation is not available, which is itself
a useful constraint to have met — CPU isolation is one of the biggest wins
available on multi-core parts, and its absence here is part of why the PRU
comparison comes out so stark.

## Measuring

**`cyclictest`** is the standard: a real-time thread sleeps for a fixed
interval and measures how late it actually woke. Run it under load —
`hackbench`, `stress-ng`, heavy I/O — because unloaded numbers mean nothing.

Read the **maximum**, not the average, and run for hours: the worst case
appears rarely and it is the only number that matters. A histogram
(`-h`) is the right output, and the shape of the tail says more than any
single figure.

Then find the cause with the tracers, which is the part people skip:

- **`irqsoff`** — longest period with interrupts disabled, with a stack trace
- **`preemptoff`** — longest with preemption disabled
- **`wakeup_rt`** — worst wake-up latency for a real-time task

These name the offending function. Nearly always it is a driver, and often
one nobody in the room wrote — which is a genuinely common real-world
outcome and worth having experienced.

## When Linux is the wrong tool

Below roughly tens of microseconds, or when jitter must be near zero, the
answer is not to tune harder:

- **PRU-ICSS.** Two 200 MHz cores on this SoC, no cache, no pipeline
  surprises, deterministic to the instruction. Loaded by `remoteproc`,
  talked to via `rpmsg` and shared memory. Cycle-counted code with genuinely
  exact timing, and it is on the chip already.
- **A separate microcontroller** doing the timing-critical work, with Linux
  as the supervisor. Common, boring, effective — and the architecture behind
  most of the projects in this vault.
- **FPGA** for genuinely parallel hard timing.

The shared-memory interface to the PRU is the same coherency problem as
[[linux-memory-and-dma]], in a different shape.

## Exercises

The €12 logic analyzer earns its place here — jitter has to be measured
externally, because a system cannot honestly measure its own lateness.

1. **Baseline.** `cyclictest -m -p80 -i200 -h400` for an hour, idle.
   *Success: a histogram and a maximum, written down.*

2. **Under load.** Repeat with `hackbench` and heavy I/O running. *Success: a
   much worse maximum, and an appreciation of why unloaded numbers are
   marketing.*

3. **PREEMPT_RT.** Rebuild with it, repeat both. *Success: a table of four
   maxima. Average may worsen; the maximum should improve substantially.*

4. **Find the offender.** With the `irqsoff` tracer, identify the longest
   interrupts-off section under load. *Success: a function name and a stack
   trace.* Then look at what it is doing and form an opinion about whether it
   could be shorter.

5. **A real-time thread, measured externally.** `SCHED_FIFO`, `mlockall`,
   toggling a GPIO at a fixed period. Measure the actual period on the logic
   analyzer. *Success: a jitter figure from an instrument, not from the
   system under test.*

6. **Deliberate breakage — remove `mlockall`.** And allocate in the loop.
   *Success: latency spikes appear, correlated with the allocations.*

7. **Deliberate breakage — priority inversion.** Three threads, a shared
   mutex without priority inheritance, and a middle-priority CPU hog. Provoke
   it. *Success: the high-priority thread blocked by the low one, measured.*
   Then enable `PTHREAD_PRIO_INHERIT` and watch it resolve. This is the
   Mars Pathfinder bug, reproduced on a desk.

8. **IRQ affinity and tick.** Move interrupts, try `nohz_full`, measure.
   *Success: a measured effect, or a measured absence of one — the single
   core limits what is possible, and knowing that is the result.*

9. **The PRU comparison.** Same GPIO toggle on a PRU, cycle-counted.
   *Success: jitter measured on the same instrument, and a ratio.* Expect
   orders of magnitude.

10. **Decide about [[beaglebone-pru-realtime]].** With both numbers in hand,
    write down whether a PRU is justified for the WS2812 case, and what
    latency requirement would justify it. *Success: a decision with a number
    behind it.* Either outcome is a good outcome; the deferral becomes
    informed rather than a hunch.

## What industry expects here

That "real-time" is used precisely. An engineer who says "we need real-time"
without a number is asking for nothing; the expected form is "worst-case
response under 200 µs at the 99.999th percentile, under full load".

Specifically probed:

- **Worst case, not average**, and measuring under load for a long time.
- **What PREEMPT_RT actually does** — threaded interrupts, sleeping
  spinlocks, priority inheritance — and what it costs in throughput.
- **Priority inversion**, its mechanism and its fix. This is a standard
  interview question and Pathfinder is the standard illustration.
- **`mlockall` and no allocation in the loop**, which is where naive
  real-time applications fail regardless of the kernel.
- Knowing when to stop tuning and move the work off the CPU. Reaching for a
  PRU or an MCU is engineering judgement when there are measurements behind
  it, and cargo cult when there are not.

The mature position: Linux is not a real-time operating system that happens
to have jitter — it is a throughput-optimised system that can be tuned to
bounded latency at a cost. Knowing the cost is the expertise.

## Where this leads

- [[embedded-linux-course]] — the course this is module 11 of
- [[linux-char-drivers-and-irqs]] — threaded IRQs, which PREEMPT_RT makes
  universal
- [[linux-memory-and-dma]] — the shared-memory interface to the PRU
- [[linux-kernel-debugging]] — the tracers used here, in full
- [[beaglebone-pru-realtime]] — the project this module exists to make a
  decision about
- [[custom-flight-controller-drone]] — the other end of the argument: a
  1 kHz attitude loop with measured jitter, on bare metal, because the answer
  there is already known to be "not Linux"
