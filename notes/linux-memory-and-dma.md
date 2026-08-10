---
tags: [note, course, embedded, linux, kernel, dma, memory]
created: 2026-08-10
---

# Kernel Memory and DMA

Reference note. Module 7 of [[embedded-linux-course]]. The drivers so far
have moved bytes a register at a time with the CPU doing the work. This is
the module about moving them properly, and about the fact that the address
the CPU uses and the address the hardware uses are not the same number.

The question it answers: why does the data look right in the kernel and
wrong in the device?

## Allocating

Three allocators, chosen by size and by whether the memory must be
physically contiguous:

| Call | Gives | Contiguous | Limit |
| --- | --- | --- | --- |
| `kmalloc` | Small buffers | Physically, yes | A few hundred KB in practice, and it degrades |
| `vmalloc` | Large buffers | Virtually only | Large, but unusable for DMA |
| `alloc_pages` | Whole pages | Physically, yes | Order-limited by fragmentation |
| `dma_alloc_coherent` | DMA buffers | Physically, yes | The right answer for hardware |

The distinction that matters: **hardware does not know about page tables.**
A device given a `vmalloc` buffer will happily read whatever physical pages
happen to sit at those addresses, which are not the pages the driver thinks
it is using. This produces corruption that looks random and is not.

Physical contiguity also gets harder over uptime. After a week of running,
allocating 1 MB physically contiguous may simply fail, even with memory free
— fragmentation. A driver that allocates its big buffers at probe time and
keeps them is doing the right thing; one that allocates per transfer is
building a time bomb.

### GFP flags

`GFP_KERNEL` may sleep to reclaim memory. `GFP_ATOMIC` may not, draws from an
emergency reserve, and fails more readily. The rule from
[[linux-char-drivers-and-irqs]] applies directly: in an interrupt handler or
holding a spinlock, `GFP_KERNEL` is a bug — and one the kernel will report
loudly with `CONFIG_DEBUG_ATOMIC_SLEEP` on.

`GFP_DMA` is mostly historical on ARM and usually not what is wanted; the DMA
API handles the constraints.

## Three kinds of address

This is the conceptual core of the module.

| Address | Who uses it | How to get it |
| --- | --- | --- |
| **Virtual** | The CPU, through the MMU | What every pointer is |
| **Physical** | The memory controller | `virt_to_phys`, and rarely needed directly |
| **DMA / bus** | The device | `dma_map_*` — and *only* from there |

On a simple system the DMA address equals the physical address, which is
exactly why this is easy to get wrong: code that assumes it works fine until
it meets an IOMMU, a bus with an offset, or a device with a 32-bit
limitation on a machine with more memory than that. The rule is absolute:
**a device is only ever given an address from the DMA API**, never
`virt_to_phys`.

`ioremap` is the other direction — taking the physical address of a
peripheral's registers, from devicetree, and mapping it so the CPU can reach
it. The result is `__iomem` and must be touched only through `readl`/`writel`,
for the reasons in [[reading-a-soc-trm]].

## Coherent versus streaming

Two ways to have a DMA buffer, and the choice is a real one.

**Coherent** — `dma_alloc_coherent()`. The kernel gives back a buffer that is
uncached, or otherwise kept consistent, so CPU and device always see the same
data with no explicit synchronisation. Simple and correct; slower for CPU
access because the cache is not helping. Right for small, long-lived,
frequently-touched things like descriptor rings.

**Streaming** — `dma_map_single()` / `dma_unmap_single()`. The buffer is
ordinary cached memory, mapped for the device for the duration of one
transfer, with an explicit direction. Fast for the CPU; requires getting the
cache maintenance right.

### The cache coherency trap, which is the point of the module

The Cortex-A8 in the AM335x is not cache-coherent with its DMA masters. So:

- **Device to memory** (`DMA_FROM_DEVICE`): the CPU may hold stale cached
  copies of those lines. They must be *invalidated* before the CPU reads, or
  it reads old data over the top of a perfectly successful transfer.
- **Memory to device** (`DMA_TO_DEVICE`): the CPU's writes may still be
  sitting in cache. They must be *cleaned* out to memory before the device
  reads, or it transfers stale data.

`dma_map_single` and `dma_unmap_single` do this, in the right direction, if
the direction argument is correct. `dma_sync_single_for_cpu` and
`_for_device` do it when a buffer is reused without unmapping.

Get the direction wrong, or skip the sync, and the result is data that is
sometimes right — right when the cache line happened to be evicted, wrong
otherwise. It looks like flaky hardware. It is the classic embedded bug, and
it is why exercise 5 below is worth doing deliberately.

The other rule: **a buffer mapped for DMA belongs to the device.** The CPU
must not touch it until it is unmapped or synced back. And DMA buffers must
not share a cache line with anything else, which is why `kmalloc` returns
DMA-safe alignment and why a buffer embedded in the middle of a struct is a
bug waiting to happen.

## dmaengine, and scatter-gather

Real drivers rarely program a DMA controller directly. The **dmaengine**
framework abstracts it: request a channel, configure it for the peripheral,
prepare a transfer, submit it, get a completion callback. The AM335x's EDMA
sits behind this, and the SPI and MMC drivers use it.

**Scatter-gather** is the acknowledgement that a large userspace buffer is
not physically contiguous. Rather than copying it into one that is, the
device is given a list of physical fragments — `dma_map_sg()` maps the whole
list at once. This is how zero-copy actually works in practice, and it is
what makes the difference between a driver that can saturate a bus and one
that cannot.

## mmap, and getting userspace out of the way

`read()` on a driver copies: device to kernel buffer, kernel buffer to
userspace. For a stream of samples that is two copies too many.

`mmap` in a driver maps the buffer's pages directly into the process's
address space — `remap_pfn_range` for simple cases, or
`dma_mmap_coherent` for a coherent DMA buffer. After that userspace reads the
data where the hardware put it, with no syscall per sample.

The cost is that synchronisation becomes the application's problem: with no
`read()` boundary, something else must say where the valid data ends. Usually
an ioctl, or a shared index in the same mapping with the right barriers. This
is the design every high-rate capture path in Linux uses, V4L2 and ALSA and
the SDR drivers included — the RTL-SDR captures in
[[subghz-collar-remote-clone]] came out of exactly this mechanism.

DMA-BUF is the generalisation — sharing a buffer between two *drivers*
without a round trip through userspace — and is worth knowing exists.

## Exercises

1. **Allocator comparison.** Allocate 1 MB with each of `kmalloc`,
   `vmalloc` and `alloc_pages`. Report success, and print the virtual and
   physical addresses. *Success: the `vmalloc` buffer is virtually contiguous
   and physically is not, demonstrated by printing the physical address of
   several pages within it.*

2. **Fragmentation.** Loop allocating progressively larger contiguous blocks
   until failure, on a freshly booted board and again after heavy filesystem
   activity. *Success: two different numbers, and an argument for allocating
   at probe time.*

3. **Deliberate breakage — the wrong GFP flag.** `GFP_KERNEL` from an
   interrupt handler, with `CONFIG_DEBUG_ATOMIC_SLEEP` on. *Success: the
   splat, and the fix.*

4. **`mmap` a buffer.** Expose the driver's ring buffer through `mmap`, write
   a counter from the kernel, read it from userspace with no syscall.
   *Success: userspace sees the value change without calling `read`.*

5. **Streaming DMA on SPI — done right.** Move a block over McSPI using
   dmaengine with correct `dma_map_single` and direction. *Success: the data
   arrives intact, repeatedly, and the logic analyzer shows the transfer.*

6. **Deliberate breakage — skip the sync.** Then remove the
   `dma_sync_single_for_cpu` before reading. *Success: stale data, sometimes.*
   Then make it fail more reliably by touching the buffer with the CPU first
   to warm the cache. This is the exercise the module exists for — the bug is
   invisible in code review and obvious once seen.

7. **Deliberate breakage — the wrong direction.** Map `DMA_TO_DEVICE` for a
   receive. *Success: corruption, and the ability to recognise the pattern.*

8. **Measure it.** Throughput for the same data via `read()` versus `mmap`,
   and CPU-driven SPI versus DMA. *Success: four numbers and an explanation
   of the gaps.* Keep them; the argument for DMA in
   [[subghz-linux-router]] is quantitative or it is nothing.

9. **KASAN.** Plant a use-after-free on a `kmalloc` buffer. *Success: KASAN
   reports it with both the allocation and free stack traces, at the moment of
   the bad access rather than an hour later.*

## What industry expects here

That the three address spaces are never confused, and that `virt_to_phys` for
a device address is recognised as wrong on sight.

Cache coherency is the one that gets asked about, because it is the one that
produces field failures. The expected answer to "we get occasional corruption
on this DMA path" starts with direction arguments and sync calls, not with
suspecting the hardware.

Also expected: knowing that physically contiguous allocation gets harder over
uptime and allocating accordingly; knowing that a DMA-mapped buffer must not
be touched by the CPU; and knowing why `mmap` exists on high-rate devices and
what problem it creates in exchange.

This module is also where the memory-safety tooling stops being optional.
KASAN and `slub_debug` in the development build, always — the class of bug
here is exactly the class that is undebuggable without them, which
[[linux-kernel-debugging]] takes further.

## Where this leads

- [[embedded-linux-course]] — the course this is module 7 of
- [[linux-char-drivers-and-irqs]] — where `kmalloc` and atomic context first
  appeared
- [[linux-driver-model-and-subsystems]] — `devm_` allocations and `ioremap`
  from `probe`
- [[linux-networking-and-netdev]] — `sk_buff` is the networking answer to
  everything on this page
- [[linux-kernel-debugging]] — KASAN, KFENCE and kmemleak in earnest
- [[subghz-linux-router]] — the SPI path that has to actually keep up with
  a radio
- [[beaglebone-pru-realtime]] — shared memory between the PRU and the CPU is
  the same coherency problem in a different shape
