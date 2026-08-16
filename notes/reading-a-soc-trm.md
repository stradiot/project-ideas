---
tags: [note, course, embedded, linux, am335x, datasheet]
created: 2026-08-10
---

# Reading a SoC TRM

Reference note. The module [[embedded-linux-course]] opens with, and the one
that looks skippable. It is not: every later module is a question whose
answer is in a document nobody reads front to back, and knowing how to find
things in a five-thousand-page manual is a real skill that is never taught
anywhere.

The question it answers: what *is* this chip, and where do I look when the
kernel tells me nothing?

## The three documents, and which one to open

TI ships three separate things for the AM335x and they are not
interchangeable. Confusing them is the most common beginner failure, because
each answers a different question and none of them says so.

| Document | Answers | Size |
| --- | --- | --- |
| **Datasheet** (SPRS717) | Electrical: pin functions, voltages, timings, packages, absolute maximums | ~250 pp |
| **TRM** (SPRUH73) | Functional: every register, every bit, every peripheral's state machine | ~5000 pp |
| **Errata** (SPRZ360) | What is broken in silicon and what to do instead | ~100 pp |

If the question is *can this pin do SPI and what voltage is it*, that is the
datasheet. If the question is *which bit starts the transfer*, that is the
TRM. If the question is *why does the documented thing not work*, that is the
errata, and it is the document people find last and should find first.

For the BeagleBone Green there is a fourth: the board's schematic and system
reference manual, which is what connects the SoC's balls to the headers.
The SoC datasheet says a pin can be `spi0_d0`; only the board schematic says
whether it is wired to P9 pin 21 or to nothing at all.

## Reading a TRM without reading a TRM

Nobody reads it linearly. The structure is always the same and once it is
visible the document becomes a reference rather than a wall:

1. **Chapter 2 is the memory map.** Every peripheral's base address. This is
   the index to the whole chip — every other chapter is "what the registers
   at this base do".
2. **Each peripheral chapter has the same four parts**: an overview, an
   integration section (clocks, resets, interrupts, DMA requests — the part
   that actually matters and the part everyone skips), a functional
   description, and then the register table.
3. **The register table is the last thing to read**, not the first. A
   register description makes sense only once the state machine in the
   functional description is understood.
4. **The control module chapter** is where pin muxing lives, and it is
   separate from every peripheral. A peripheral that appears dead is usually
   a pin still muxed to something else.

The integration section is the one to slow down for. On the AM335x, a
peripheral needs its clock enabled in the PRCM, its pins muxed in the control
module, and its interrupt routed — three chapters away from each other, and
all three have to be right before a single register write does anything.
Linux does all of this from devicetree, which is precisely why
[[linux-devicetree]] is unreadable without knowing what it is describing.

## The chip, in one table

Worth being able to state without looking:

| | |
| --- | --- |
| Core | ARM Cortex-A8, ARMv7-A, 1 GHz on this board, NEON and VFPv3 |
| Caches | 32 KB L1 I and D, 256 KB L2 |
| On-chip RAM | 64 KB — small, and the reason the boot chain has two stages |
| Boot ROM | Masked, ~176 KB, unchangeable, decides everything before your code |
| DRAM | 512 MB DDR3 on the BBG, mapped from 0x8000_0000 |
| Storage | 4 GB eMMC and a microSD slot |
| PRU-ICSS | Two 200 MHz real-time cores with their own memories |
| Interconnect | L3 for bandwidth, L4 for peripherals — hence L4_WKUP / L4_PER / L4_FAST |

The 64 KB matters more than it looks. A bootloader that must initialise DDR
cannot itself live in DDR, so it must fit in 64 KB of SRAM — which is the
entire reason MLO and u-boot.img are two separate files, and the first thing
[[linux-boot-chain-uboot]] has to explain.

The peripheral bases follow the interconnect: things needed while the rest of
the chip is asleep sit in L4_WKUP (0x44C0_0000 upward — UART0, I2C0, GPIO0,
the control module and the PRCM), and the general peripherals sit in L4_PER
from 0x4800_0000. Recognising which side of that line a peripheral is on
explains a surprising number of power-management surprises later.

## The C that kernel code is written in

Not a language module — a short list of the things that look wrong the first
time and are load-bearing everywhere in [[linux-char-drivers-and-irqs]] and
after.

- **No floating point.** The kernel does not save FPU state across context
  switches on most paths. Integer and fixed-point only.
- **No standard library.** `printk` not `printf`, `kmalloc` not `malloc`,
  `strscpy` not `strcpy`. What looks like libc is a separate implementation
  with different guarantees.
- **`container_of`.** Given a pointer to a member, recover the struct that
  contains it. This is how the entire kernel does inheritance — a
  `struct device *` becomes your driver's private struct with it, everywhere.
  It is pointer arithmetic on `offsetof` and nothing more, and writing it
  once removes all the mystery.
- **Error pointers.** Functions return a valid pointer, or an error encoded
  *as* a pointer in the top page of the address space. `IS_ERR`, `PTR_ERR`,
  `ERR_PTR`. Checking for `NULL` where the API returns an error pointer is a
  crash that looks like a hardware fault.
- **`__iomem` and the accessors.** MMIO is not memory. `readl`/`writel` exist
  because the compiler must not cache, reorder or coalesce these accesses,
  and because they carry the barriers. A dereferenced `__iomem` pointer is a
  bug that sometimes works, which is the worst kind.
- **Endianness and fixed-width types.** `u32`, `__le16`, `be32_to_cpu`. The
  board is little-endian; the radio on the end of the SPI bus may not be.
- **Intrusive linked lists.** `struct list_head` embedded in the object
  rather than a container holding pointers. Same idea as `container_of`, and
  the same reason: no allocation, no indirection.

## Exercises

Nothing here needs more than the board, the console and the manuals.

1. **Get a console.** USB-UART at 3.3 V on the J1 header, `picocom -b 115200
   /dev/tty.usbserial-*`. Power the board and watch the stock image boot.
   *Success: U-Boot's banner and then a login prompt.* Note which pin was
   ground and which was which — a swapped pair produces exactly nothing and
   no error.

2. **Confirm what actually booted.** From that login: `cat /proc/cpuinfo`,
   `cat /proc/device-tree/model`, `dmesg | head -40`, `free -m`,
   `lsblk`. *Success: you can say which storage the running system came from
   and how much RAM the kernel actually found.*

3. **Identify the board by eye.** Without searching the web, use the
   silkscreen and the BBG schematic to name the SoC, the DRAM, the eMMC, the
   Ethernet PHY and the PMIC. *Success: five part numbers, each traced to a
   page in the schematic.*

4. **Find three register bases in the TRM.** McSPI0, GPIO1 and I2C0, using
   only the memory map chapter. Then say which interconnect each is on and
   what that implies. *Success: three addresses, and an explanation of why
   I2C0 is not next to I2C1.*

5. **Follow one pin end to end.** Pick a pin on the P9 header. Using the
   board schematic, find which SoC ball it is; using the datasheet, find
   every function that ball can be muxed to; using the TRM's control module
   chapter, find the register and field that selects between them. *Success:
   a written chain from header pin to mux register bit.* This is the exercise
   that makes devicetree's `pinctrl` nodes stop being magic.

6. **Read the errata.** Skim SPRZ360 and pick the three advisories most
   likely to matter for this course. *Success: three advisory numbers, what
   each breaks, and the documented workaround.* Then grep the kernel source
   for one of them and find where Linux implements that workaround — it will
   be there, usually with the advisory number in a comment.

7. **Write `container_of`.** From scratch, with `offsetof`, in a standalone
   C file. Test it by embedding a struct in another struct and recovering the
   outer from a pointer to the inner. *Success: it compiles with no warnings
   and you can explain why the cast to `char *` is necessary.*

8. **Deliberate breakage.** Write a small program that reads a `volatile`
   value in a loop and one that reads it without `volatile`, compile both at
   `-O2`, and diff the disassembly. *Success: the compiler has deleted the
   loop in one of them.* That deletion is why `__iomem` accessors exist.

## What industry expects here

That you reach for the manual before the search engine, and that you know
which manual. An engineer who answers "the datasheet says the pin can do
that, but the schematic shows it is not routed" in the first five minutes is
visibly different from one who spends a day on a driver for a pin that goes
nowhere.

Two specific things get probed. The first is the errata habit — being asked
"did you check the errata" and having already checked it is the difference
between a day and a week on some bugs. The second is being able to say what
happens between power-on and the first instruction of your code, which is
[[linux-boot-chain-uboot]] and is the single most common embedded interview
question there is.

## Where this leads

- [[embedded-linux-course]] — the course this module opens; its plan holds
  the order the modules run in
- [[linux-boot-chain-uboot]] — the 64 KB of SRAM above is why that module
  exists at all
- [[linux-devicetree]] — clocks, pin mux and interrupts are the three things
  the integration sections describe and devicetree configures
- [[industrial-sensor-node-linux]] — the first project where the pin-to-mux
  chain traced in exercise 5 has to be got right for real
