---
tags: [note, course, embedded, linux, kernel, driver, iio]
created: 2026-08-10
---

# The Driver Model and Subsystems

Reference note. Module 6 of [[embedded-linux-course]], and the module that
separates someone who can make hardware work from someone who can write a
driver that would be accepted upstream.

The question it answers: [[linux-char-drivers-and-irqs]] produced a working
sensor driver — why would anyone reject it?

## The model, in one idea

The kernel separates **devices** (things that exist) from **drivers** (code
that can handle them), and a **bus** matches them. Nothing is hardcoded;
everything is registration and matching.

```
bus_type
 ├── devices    ← from devicetree, USB enumeration, PCI scan…
 └── drivers    ← from modules, each with a match table
        ↓
     probe(dev)  when a match is found
     remove(dev) when either goes away
```

This means a driver never knows *whether* its hardware exists. It registers,
and `probe()` is called if and when something matching turns up. That
inversion is the thing to internalise: a driver's `init` should do almost
nothing but register.

For a memory-mapped peripheral described in devicetree, the bus is the
platform bus and matching is by `compatible` against `of_match_table` — the
other half of the mechanism in [[linux-devicetree]]. For I2C and SPI, the
device comes from a child node of the bus controller. For USB, it comes from
enumeration and matching is by vendor and product ID, which is
[[usb-device-and-linux-driver]].

### `probe()`, and the ordering problem

`probe()` gets resources: `platform_get_irq()`, `devm_ioremap_resource()`,
`devm_gpiod_get()`, `devm_regulator_get()`, `devm_clk_get()`. Any of these
can fail because the thing being asked for has not been registered yet — the
regulator driver may probe after this one.

The answer is **`-EPROBE_DEFER`**. Return it, and the kernel puts the device
back on a list and retries later, after something else has probed
successfully. This is how the kernel resolves arbitrary dependency graphs
without anyone specifying an order, and it is why initcall levels are not
something to rely on.

The practical consequence: propagate `-EPROBE_DEFER` rather than swallowing
it, and never print an error for it — a deferred probe is normal, and a
driver that logs an error every retry is a driver that fills the log.

### `devm_`, and why remove() should be empty

Every `devm_`-prefixed allocation is registered against the device and freed
automatically when it goes away — in reverse order, including on a failed
probe. Using them consistently means the error path in `probe()` becomes
`return ret;` at every step and `remove()` becomes empty or nearly so.

This is not a convenience. Hand-rolled unwind paths in `probe()` are one of
the most reliable sources of leaks and double-frees in the kernel, because
the error path is the code nobody tests. `devm_` deletes the entire category.

## Subsystems, and the actual lesson of this module

Here is the thing the char driver got wrong.

A char driver invents an interface. Its `/dev/pir` emits some format someone
made up; a program has to be written specifically for it; nothing else in the
system knows what it is. Multiply that by every sensor on every board and
there is no such thing as a generic tool.

A **subsystem** is a contract. Write to it and every existing tool works:

| Subsystem | For | Userspace sees |
| --- | --- | --- |
| **IIO** | ADCs, sensors, anything sampled | `/sys/bus/iio/`, buffers, triggers, `libiio` |
| **input** | Buttons, keys, touch, motion events | `/dev/input/event*`, `evtest`, X and Wayland |
| **hwmon** | Temperature, voltage, fan monitoring | `sensors`, and every monitoring stack |
| **LED class** | Indicators | `/sys/class/leds/`, with triggers |
| **gpiochip** | GPIO controllers | `libgpiod`, `gpioget`, `gpiomon` |
| **rtc, watchdog, pwm, thermal** | What they say | Standard tools and standard semantics |
| **net_device** | Anything carrying packets | The entire IP stack — see [[linux-networking-and-netdev]] |

The BME280 written as an IIO driver is readable by `iio_generic_buffer`,
graphable by tools that have never heard of it, and usable by anything
speaking `libiio`. The same sensor as a char device is a private protocol.

This is why upstream rejects char drivers for anything with a subsystem, and
it is close to a reflex among reviewers. "Why is this not IIO?" is the first
comment on a sensor driver posted to a mailing list, and the answer had
better not be "I did not know about it".

The buffered path in IIO is worth reaching, not just the sysfs one — a
trigger, a buffer, and timestamped samples pushed from an interrupt is the
real structure, and it is the same shape as almost every data-producing
driver in the kernel.

### regmap

Almost every I2C or SPI device is a bank of registers. Everyone wrote the
same read-modify-write, endianness and paging code, badly, until `regmap`
absorbed it: describe the register layout once, get `regmap_read`,
`regmap_write`, `regmap_update_bits`, plus caching, volatile-register
handling and debugfs register dumps for free.

The debugfs dump alone justifies it — being able to `cat` a device's entire
register set while debugging is worth more than the code it saves.

## Exercises

The BME280 and the CC1101 from the bench. This module is where the sensor
budget line gets used.

1. **A platform driver that does nothing.** Devicetree node, `of_match_table`,
   `probe()` that logs and returns. *Success: `dmesg` shows probe on boot, and
   `/sys/bus/platform/drivers/` has the entry.* Then remove the node and
   confirm probe does not run.

2. **BME280 as a char driver, deliberately.** I2C client driver, registers
   read by hand, values exposed through the char interface from
   [[linux-char-drivers-and-irqs]]. *Success: correct temperature, pressure
   and humidity.* Keep this — it is the "before".

3. **Rewrite it as IIO.** Same sensor, `iio_device_alloc`, channels, `read_raw`.
   *Success: `cat /sys/bus/iio/devices/iio:device0/in_temp_input` gives the
   right number, and `iio_info` describes the device without being told
   anything.* Compare the two drivers side by side; that diff is the module.

4. **Add a buffer and a trigger.** Sampled on a timer, pushed into a buffer
   with timestamps. *Success: `iio_generic_buffer` streams samples at the rate
   requested.*

5. **Convert to regmap.** Delete the hand-rolled register access. *Success:
   the driver is shorter, and `/sys/kernel/debug/regmap/` dumps every
   register.*

6. **Convert everything to `devm_`.** *Success: `remove()` is empty, and the
   probe error path is a single `return ret` at each stage.*

7. **Deliberate breakage — probe order.** Add a regulator dependency whose
   driver probes late, so the sensor gets `-EPROBE_DEFER` on first attempt.
   *Success: the deferral visible in `dmesg` with `initcall_debug`, and a
   successful probe on retry.* Then swallow the `-EPROBE_DEFER` instead of
   returning it and watch the device never appear — the failure mode this
   teaches.

8. **PIR as an input device.** Rewrite exercise 6 of the previous module as
   an `input_dev` reporting `EV_SW` or `EV_KEY`. *Success: `evtest` shows
   events with no custom program written at all.* This is the moment the
   subsystem argument becomes obvious rather than theoretical.

9. **CC1101 SPI driver skeleton.** `spi_driver`, devicetree node with chip
   select, read the part number register over SPI to prove the bus works,
   GDO0 as a threaded IRQ. *Success: the part number matches the datasheet,
   and the logic analyzer shows a clean transaction with the right mode and
   speed.* This is phase 2 of [[subghz-linux-router]] beginning.

10. **Write down the subsystem for each.** For every driver in this course:
    which subsystem it belongs in, or the argument for why nothing fits.
    *Success: a short written answer per driver.* For the CC1101 the honest
    answer is interesting — it ends up a `net_device` in
    [[linux-networking-and-netdev]], and getting there is the point.

## What industry expects here

That a subsystem is looked for before code is written. The reflex — "there is
a framework for this, and I should be using it" — is what distinguishes
someone who has had patches reviewed from someone who has only made things
work.

Concretely probed:

- **`-EPROBE_DEFER`**: what it is, why it exists, what happens if it is
  swallowed. This comes up constantly because it is the source of an entire
  class of "works sometimes, depending on module load order" bugs.
- **`devm_`** as the default, and why hand-written unwind paths are a smell.
- **Which subsystem** a given device belongs to, and being able to justify a
  char device when one genuinely is right — a device with no analogue in any
  framework, which is rarer than people think.
- **regmap**, at least by name and purpose.

The gap this module closes is specific: making the hardware respond is
perhaps a fifth of writing a driver. The rest is fitting it into the kernel
so that it composes with everything else, survives module unload, handles
probe deferral, and does not need its own bespoke userspace.

## Where this leads

- [[embedded-linux-course]] — the course this is module 6 of
- [[linux-char-drivers-and-irqs]] — the "before" this module rewrites
- [[linux-devicetree]] — `compatible` matched against `of_match_table`
- [[linux-memory-and-dma]] — what happens when the buffers get large enough
  to matter
- [[linux-networking-and-netdev]] — `net_device` as the subsystem the CC1101
  eventually belongs in
- [[subghz-linux-router]] — the CC1101 driver started in exercise 9 is that
  project's phase 2
- [[usb-device-and-linux-driver]] — the same driver model with USB as the bus
- [[industrial-sensor-node-linux]] — its sensors, written the way that would
  survive review
