---
tags: [note, course, embedded, linux, devicetree, kernel]
created: 2026-08-10
---

# Linux Devicetree

Reference note. Module 4 of [[embedded-linux-course]]. The counterpart to
[[zephyr-devicetree]], which describes the same syntax with an entirely
different lifecycle — and which is worth reading alongside this, because the
contrast is what makes both stop being mysterious.

The question it answers: how does a kernel that has never heard of this board
find out what is on it?

## Why it exists

x86 has firmware that enumerates: PCI and ACPI let the kernel ask the
hardware what is present. Embedded ARM has no such thing. An I2C sensor at
address 0x76 is electrically indistinguishable from nothing at all unless
someone says it is there.

Before devicetree, "someone" was a C file per board in `arch/arm/mach-*/`,
compiled into the kernel, registering platform devices by hand. By 2011 there
were thousands of them, no two boards could share a kernel binary, and the
ARM tree had become — in Linus's memorable assessment of the situation — a
mess of gratuitous and unmaintainable per-board code. Devicetree was the
answer: move the description out of the kernel into a data blob passed in at
boot, so one kernel binary serves many boards.

That history *is* the explanation. Devicetree is not a configuration
language and not an init system. It is a hardware description, and the test
for whether something belongs in it is whether it is a property of the board
rather than a property of what you want the software to do. Policy in
devicetree is the most common review rejection there is.

## Against Zephyr, since both get used here

[[zephyr-devicetree]] has the full table; the short version:

| | Linux | Zephyr |
| --- | --- | --- |
| Consumed | At boot, as a DTB blob in memory | At build time, by a Python script |
| Result | A live tree the kernel walks | C macros, no tree at runtime |
| Adding a device | Change the DTB, reboot | Rebuild the application |
| Unmatched node | Sits there, inert, no error | Generates nothing, no error |

Same syntax, opposite mechanics. Linux keeps the tree and probes against it;
Zephyr evaporates it at compile time. Having written both, the phrase "the
devicetree" stops being ambiguous.

## The syntax, in the parts that matter

```dts
&i2c1 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&i2c1_pins>;
    clock-frequency = <100000>;

    bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
    };
};
```

- **`compatible`** is the matching key. The kernel looks for a driver whose
  `of_match_table` contains this string. Wrong or absent, the node is inert
  and nothing is reported — this is the number one cause of "my device does
  not appear".
- **`reg`** means "where", interpreted by the parent bus: an address on I2C,
  a chip select on SPI, a base address and size on a memory-mapped bus. Its
  format is set by the parent's `#address-cells` and `#size-cells`, which is
  why the same-looking property means different things at different depths.
- **`status`** — `"okay"` or `"disabled"`. SoC `.dtsi` files declare every
  peripheral disabled; the board `.dts` enables the ones actually wired.
  Forgetting it is the number two cause.
- **Phandles** — `<&i2c1_pins>` — are references to other nodes. This is how
  the tree stops being a tree: a device points at its clocks, its regulators,
  its interrupt controller, its pin configuration.
- **`interrupts`** is interpreted by whatever `interrupt-parent` resolves to,
  and its cell count varies by controller. A GPIO interrupt is usually
  `<pin flags>` against a GPIO controller; a GIC interrupt is three cells.
- **`ranges`** describes address translation between a bus and its parent. An
  empty `ranges;` means one-to-one, which covers most cases.

`.dtsi` files are includes: the SoC file describes everything the chip has,
the board file says which of those are wired and to what. `am335x-bonegreen.dts`
includes the AM335x `.dtsi` and then enables and configures. That layering is
the whole design.

### pinctrl, which is where the time goes

A pin on the AM335x can be several things, and only one at a time. The
`pinctrl` subsystem takes a pin configuration from devicetree and programs
the control module registers traced by hand in [[reading-a-soc-trm]] exercise
5 — mux mode, pull up or down, input enable, slew.

A device references its pin group with `pinctrl-0` and names it in
`pinctrl-names`. The subsystem applies it before the driver probes. Two
devices claiming the same pin produce a probe failure with a genuinely useful
error message, which is one of the nicer things about the subsystem.

## Bindings, and why they are not optional

A binding is the schema for a `compatible`: which properties are required,
which are optional, what types and how many cells. They live in
`Documentation/devicetree/bindings/` as YAML, and they are validated:

```
make ARCH=arm dt_binding_check    # is the schema itself well-formed
make ARCH=arm dtbs_check          # do the trees conform to the schemas
```

This matters because devicetree is an **ABI**. A DTB written for one kernel
should still work on the next one, which means a binding cannot change
incompatibly once it is upstream. That is why binding review is strict and
why a binding patch is reviewed by different maintainers, more carefully,
than the driver that uses it. Writing one that passes `dtbs_check` is a
genuinely different skill from writing a driver, and it is where a lot of
first upstream attempts get sent back.

## Overlays, and the cape story

An overlay is a devicetree fragment applied to an existing tree — the way to
add hardware without forking a board file. `.dtbo`, applied either by U-Boot
before boot or at runtime via configfs.

The BeagleBone's history here is worth knowing because it explains why the
tooling looks odd. The board's expansion boards ("capes") had an EEPROM, and
the vendor kernel carried a "cape manager" that read it and loaded overlays
automatically. It never went upstream — runtime overlay support was
contentious for years, since a tree that changes under a running kernel
breaks assumptions all over the driver model. Mainline has runtime overlay
support now but no cape manager, so on a mainline kernel the overlay is
applied deliberately, usually from U-Boot. Vendor-tree tutorials describing
the cape manager will not work, and the reason is this.

For this course, applying from U-Boot is the right default: it happens before
the kernel probes anything, so none of the runtime complications arise.

## Debugging

The single most useful thing, and the direct equivalent of Zephyr's
`build/zephyr/zephyr.dts`:

```
dtc -I fs -O dts /sys/firmware/devicetree/base
```

That decompiles the tree the running kernel actually has, after every include
and every overlay. When a node "is not being picked up", the answer is in
that output, and it is nearly always one of:

- `status` is not `"okay"`, or the parent bus is disabled — which silently
  disables every child
- The `compatible` matches no driver in this kernel — check
  `/sys/bus/*/drivers/` and the config
- The overlay referenced a label that does not exist on this board
- The driver is a module and was never loaded, which is not a devicetree
  problem at all but looks identical

Also useful: `/sys/firmware/devicetree/base` browsed directly as files, and
`/sys/kernel/debug/pinctrl/` for what the pin muxing actually ended up as.

## Exercises

1. **Decompile the live tree.** `dtc -I fs` on the running board, diff it
   against the `.dts` source in the kernel tree. *Success: an explanation for
   every difference — includes resolved, phandles numbered, overlays applied.*

2. **Add a sensor.** BME280 on I2C1 as an overlay applied from U-Boot.
   *Success: `dmesg` shows the driver probing, and the device appears under
   `/sys/bus/i2c/devices/`.*

3. **Deliberate breakage — three ways.** In turn: set `status = "disabled"`;
   disable the parent I2C bus; misspell the `compatible`. Observe each.
   *Success: three distinct failure signatures, and the ability to tell them
   apart from `dmesg` and the decompiled tree alone.* The third one is the
   nastiest because nothing is logged at all.

4. **Mux a pin.** Take a free P9 pin, mux it as GPIO through a `pinctrl`
   node, drive an LED from sysfs. *Success: the LED lights, and
   `/sys/kernel/debug/pinctrl/` confirms the mux.* Then mux it to something
   else and watch the claim conflict.

5. **Read the interrupt chain.** For the PIR sensor's GPIO, follow
   `interrupt-parent` up through the tree to the GIC. *Success: the full
   chain written out, with the cell format at each level.*

6. **Write a binding.** Invent a `compatible` for a driver of your own, write
   the YAML, run `dt_binding_check` and `dtbs_check` until both pass.
   *Success: clean output.* Expect this to take longer than it looks; the
   schema language is fussy and that fussiness is the point.

7. **Overlay both ways.** Apply the same overlay from U-Boot, then at runtime
   via configfs. *Success: both work, and you can describe what is riskier
   about the second.*

8. **Read a real board file.** Open `am335x-bonegreen.dts` and its includes
   and account for every node — what it is, whether it is enabled, what it
   points at. *Success: no unexplained nodes.* This is the exercise that makes
   the syntax fluent, and there is no substitute for it.

## What industry expects here

Fluency, because on a new board this is most of the first month's work. The
board comes up, and then every peripheral is a devicetree node that has to be
written correctly against a binding, with the right clocks, regulators, pin
configuration and interrupt.

The specific things that get probed:

- **Description versus configuration.** Reviewers reject policy in
  devicetree, and knowing where that line is — a sensor's I2C address is
  description, its sampling rate usually is not — is the mark of someone who
  has been through review.
- **Devicetree is ABI.** A shipped DTB has to keep working across kernel
  upgrades. Products that got this wrong have field devices that cannot take
  an update.
- **Debugging by decompiling the live tree** rather than by rereading the
  source, since the source is not what the kernel got.
- Being able to write a binding that passes `dtbs_check`, which is the
  concrete deliverable if any of this is ever upstreamed.

## Where this leads

- [[embedded-linux-course]] — the course this is module 4 of
- [[zephyr-devicetree]] — the same language, resolved at build time, with
  nothing left at runtime
- [[reading-a-soc-trm]] — the control module registers `pinctrl` is
  programming
- [[linux-kernel-build-and-config]] — where the DTB is built and what hands
  it over
- [[linux-driver-model-and-subsystems]] — `compatible` is matched against
  `of_match_table`, and this is the other half of that mechanism
- [[industrial-sensor-node-linux]] — the project whose overlay this is
  practice for
- [[beaglebone-pru-realtime]] — pin muxing for the PRU, same mechanism
