---
tags: [note, course, embedded, linux, kernel, driver, interrupts]
created: 2026-08-10
---

# Char Drivers and Interrupts

Reference note. Module 5 of [[embedded-linux-course]], and the first module
that writes kernel code. It is also the module whose lesson is partly
"do not do it this way" — the char driver is the right way to *learn* the
kernel's shape and usually the wrong way to ship a sensor, which is what
[[linux-driver-model-and-subsystems]] is for.

The question it answers: what does kernel code have to obey that userspace
code does not?

## The four rules of being in the kernel

Everything in this module follows from these, and the failure modes are all
variations of ignoring one.

1. **There is no memory protection.** A bad pointer does not fault a process;
   it corrupts something else, possibly minutes before the crash. This is why
   `copy_to_user` exists rather than `memcpy` — a userspace pointer must
   never be trusted or dereferenced directly.
2. **Some code cannot sleep.** Interrupt handlers, and anything holding a
   spinlock, run in *atomic context*. Sleeping there deadlocks the machine.
   `might_sleep()` is the annotation; `GFP_ATOMIC` is the allocation flag; the
   discipline of knowing which context you are in is the single most
   important habit in kernel programming.
3. **Everything is concurrent.** Two CPUs, preemption, interrupts. A driver's
   `read` can be entered twice simultaneously, and its interrupt handler can
   fire in the middle. Assuming otherwise works right up until it does not.
4. **The user is hostile, or at least careless.** Every value from userspace
   is attacker-controlled: sizes, offsets, ioctl arguments. Validate before
   use, and validate after copying rather than before, or the value can change
   underneath.

## The module

```c
static int __init foo_init(void) { ... }
static void __exit foo_exit(void) { ... }
module_init(foo_init);
module_exit(foo_exit);
MODULE_LICENSE("GPL");
```

`MODULE_LICENSE` is not a formality. Symbols exported with
`EXPORT_SYMBOL_GPL` — which is most of the interesting ones — are unavailable
to a module that does not declare a GPL-compatible license, and the module
will fail to load with unresolved symbols. This is a deliberate technical
enforcement of a legal position, and it is worth understanding rather than
copy-pasting past.

Out-of-tree builds use kbuild against a configured kernel tree:

```make
obj-m += foo.o
all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
```

The module records a `vermagic` — kernel version, config, compiler — and
refuses to load into anything that does not match. That is the error from
[[linux-kernel-build-and-config]] exercise 6 and it will recur.

## The char device, in four steps

```
alloc_chrdev_region()   →  a major/minor range
cdev_init() + cdev_add()→  bind file_operations to it
class_create()          →  a class, so udev knows what this is
device_create()         →  the node appears at /dev/foo
```

That last step is the one worth understanding: the kernel does not create
`/dev` entries. It emits a uevent; `udev` in userspace sees it and creates the
node, with a name and permissions from its rules. The kernel and the device
node are more loosely coupled than they look, which is what makes the udev
rules in [[systemd-dbus-embedded]] necessary.

`file_operations` is the interface: `open`, `release`, `read`, `write`,
`poll`, `unlocked_ioctl`, `mmap`. Each one is called from a process context —
so they *may* sleep — with a `struct file *` whose `private_data` is where
per-open state goes.

`container_of` from [[reading-a-soc-trm]] earns its keep here: the framework
hands back a pointer to an embedded struct, and the driver's own state is
recovered from it. This pattern is the whole kernel.

## Locking, chosen by context

| Primitive | Sleeps | Use when |
| --- | --- | --- |
| `mutex` | Yes | Process context, critical section may be long or may sleep |
| `spinlock` | No | Short critical section, or shared with an interrupt handler |
| `spin_lock_irqsave` | No | Shared with an interrupt handler *on the same CPU* |
| `atomic_t` | No | A single counter, nothing more |
| RCU | — | Read-mostly data; read side is nearly free, writers pay |

The rule that prevents most deadlocks: **never sleep holding a spinlock**,
and that includes calling anything that might allocate with `GFP_KERNEL`,
copy to userspace, or take a mutex. The kernel will tell you, loudly, if
`CONFIG_DEBUG_ATOMIC_SLEEP` is on — and it should be on for the whole of this
course.

The other rule: if data is touched by both an interrupt handler and process
context, the process-context side must use `spin_lock_irqsave` or the
interrupt can fire while the lock is held and deadlock the CPU against
itself.

## Blocking, and `poll`

A `read` with no data should not spin and should not return zero. It should
sleep:

```c
wait_event_interruptible(dev->wq, dev->has_data);
```

and the producer — usually the interrupt path — calls `wake_up_interruptible`.
`interruptible` matters: a task blocked uninterruptibly cannot be killed, and
a driver that leaves processes in `D` state is a driver people hate.

`poll` is what lets a single-threaded program wait on this device alongside a
socket and a timer. The implementation is two lines — `poll_wait()` on the
wait queue, then return the ready mask — and it is what makes the device
usable from an event loop, which is exactly what the daemon in
[[systemd-dbus-embedded]] needs.

## Interrupts

`request_irq()` binds a handler to an IRQ number, which on a devicetree
system comes from `platform_get_irq()` or `gpiod_to_irq()` rather than being
hardcoded.

The handler runs with interrupts disabled on that line, in atomic context,
and everything about it must be short. Which is why the work gets split:

| Mechanism | Context | Use |
| --- | --- | --- |
| **Hard IRQ** | Atomic | Acknowledge the hardware, grab a timestamp, schedule the rest |
| **Threaded IRQ** | Process, can sleep | The default good answer — the handler is a kernel thread |
| **Workqueue** | Process, can sleep | Deferred work not tied to an IRQ |
| **Softirq / tasklet** | Atomic | Legacy; tasklets are deprecated, do not reach for them |

For anything on a slow bus — an I2C or SPI sensor that has just asserted an
interrupt line — a **threaded IRQ** is the answer, because the bus transaction
itself sleeps. `request_threaded_irq()` with `IRQF_ONESHOT` keeps the line
masked until the thread completes, which is what a level-triggered device
needs.

This is precisely the shape [[industrial-sensor-node-linux]] describes for
the PIR: minimal hard handler, everything real in the thread. Building it here
means that project starts already solved.

## Exercises

Every one of these is on the board, over NFS root, with `CONFIG_DEBUG_ATOMIC_SLEEP`,
`CONFIG_PROVE_LOCKING` and `CONFIG_KASAN` available in the kernel config.

Exercises **1** and **2** are the ground this module starts from rather than
new work: three char drivers with `class_create`, a `/dev` node and a
fixed-size buffer already exist across the older repositories, one of them
with `ioctl` and `llseek` on top. What none of them has is any of **3** to
**10** — no wait queue, no `poll`, no interrupt of any kind, no lock ever
contended on purpose, and neither lockdep nor KASAN ever switched on. That is
where the module actually is. See [[embedded-learning-curriculum]].

1. **Hello module.** Load, unload, read `dmesg`. *Success: both messages, and
   `lsmod` showing it in between.* Then add a module parameter and set it at
   `insmod` time.

2. **Char device with a ring buffer.** `open`/`read`/`write`/`release`, a
   fixed-size circular buffer, a `/dev` node created via `class_create`.
   *Success: `echo` into it and `cat` it back, correctly, including across the
   wrap.*

3. **Make `read` block.** Wait queue, `wait_event_interruptible`, woken by
   `write`. *Success: a `cat` that sits waiting and returns the moment
   something is written from another terminal, and can still be killed with
   Ctrl-C.*

4. **Add `poll`.** Then write a userspace program that `select`s on the device
   and stdin at once. *Success: one process handling both without threads or
   polling loops.*

5. **Deliberate breakage — race it.** Two processes writing concurrently, no
   locking, small buffer. Find the corruption. *Success: reproducible
   corruption, then a correct fix, and an argument for why you chose a mutex
   rather than a spinlock.*

6. **PIR on a real interrupt.** Devicetree node from [[linux-devicetree]],
   `gpiod_to_irq`, `request_threaded_irq`, timestamp into the ring buffer,
   wake the waiters. *Success: waving at the sensor produces a line out of
   `cat /dev/pir`, and `/proc/interrupts` shows the count rising.*

7. **Deliberate breakage — sleep in atomic context.** Call something that
   sleeps while holding a spinlock. *Success: the "BUG: sleeping function
   called from invalid context" splat, read and understood, including the
   line it points at.* This is the single most valuable planted bug in the
   module.

8. **Deliberate breakage — the interrupt deadlock.** Use plain `spin_lock`
   in process context on a lock the interrupt handler also takes. Provoke it.
   *Success: a hung CPU, and the fix being `spin_lock_irqsave`.*

9. **Turn on the debuggers.** Rebuild with lockdep and KASAN. Re-run
   exercises 5, 7 and 8. *Success: each bug is now reported precisely, before
   it does damage.* Note how much less clever debugging is needed once these
   are on, and consider that they should have been on from exercise 1.

10. **Debounce properly.** The PIR will produce bursts. Debounce it in the
    kernel with a timer rather than in userspace. *Success: one event per
    wave, and a written justification for the window chosen.*

## What industry expects here

Context discipline, above everything. Being asked "can this function sleep?"
and answering instantly, for any given function, is the baseline. The
follow-up is the interrupt split: what goes in the hard handler, what goes in
the thread, and why.

Locking is the other half. Which primitive, why, what happens if an interrupt
fires mid-section, and whether lockdep is enabled in the development build.
The correct answer to "how do you find a deadlock" is "lockdep found it
before it happened", not "I read the code carefully".

And then the thing this module deliberately sets up: an experienced reviewer
will look at the PIR char driver from exercise 6 and ask why it is not an
input device or an IIO device. That question is [[linux-driver-model-and-subsystems]],
and having built the char version first is what makes the answer land.

## Where this leads

- [[embedded-linux-course]] — the course this is module 5 of
- [[linux-devicetree]] — where the driver's interrupt and pins come from
- [[linux-driver-model-and-subsystems]] — the right way to write most of
  this, and why
- [[linux-memory-and-dma]] — what `kmalloc` was doing and what happens when
  the buffer needs to be shared with hardware
- [[linux-kernel-debugging]] — lockdep and KASAN taken seriously
- [[industrial-sensor-node-linux]] — the PIR driver here is that project's
  kernel side, already written
- [[usb-device-and-linux-driver]] — the same `file_operations` with a USB
  peripheral underneath instead of a GPIO
