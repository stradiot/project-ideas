---
tags: [note, zephyr, devicetree, embedded, linux]
created: 2026-08-09
---

# Zephyr Devicetree

Reference note. Linked from [[ble-sensor-node-pcb]], where a custom board
means writing a devicetree by hand for the first time.

## The thing that trips everyone up first

Zephyr borrows the *syntax* of Linux devicetree and almost none of its
*mechanics*.

| | Linux | Zephyr |
| --- | --- | --- |
| When it is read | At boot, as a compiled DTB blob | At build time, by a Python script |
| What the kernel/app gets | A tree parsed in memory | C macros in a generated header |
| Cost of an unused node | A parsed node sitting in RAM | Nothing — it does not exist |
| Changing it | Reflash the DTB, reboot | Rebuild the application |

So in Zephyr there is no devicetree at runtime. `build/zephyr/include/generated/`
holds the result, and everything the application knows about hardware was
frozen when it compiled. A driver is instantiated because a node with the
right `compatible` existed at build time — not because anything probed.

The Linux behaviour is the one exercised in
[[industrial-sensor-node-linux]] and [[beaglebone-pru-realtime]]: an
overlay compiled to a `.dtbo` and loaded against a running kernel. Same
language, entirely different lifecycle. Worth doing both before deciding
that either one is "how devicetree works".

## Files, and which one to actually edit

| File | Owner | Purpose |
| --- | --- | --- |
| `<soc>.dtsi` | Zephyr | The SoC's peripherals, addresses, interrupts |
| `<board>.dts` | The board | Which of those are wired, and to what |
| `<board>-pinctrl.dtsi` | The board | Which function lands on which pin |
| `app.overlay` / `boards/<board>.overlay` | The application | Local changes, no forking required |

The overlay is almost always the right place. It merges on top of the board
DTS, so a project can add an I2C sensor without touching a board definition
that other applications share.

## The single most useful debugging artifact

`build/zephyr/zephyr.dts` — the fully merged tree, after every `.dtsi`,
`.dts` and overlay has been applied. When a node "is not being picked up",
the answer is in that file, and it is usually one of:

- `status` is not `"okay"`, so nothing was generated at all
- The `compatible` string has no matching binding, so the node is inert
- The overlay edited a node label that does not exist on this board
- The bus parent is disabled, which silently disables every child

Bindings live in `dts/bindings/**.yaml` and are matched by `compatible`.
A binding is what turns a property in the tree into a macro the driver can
read; without one, a syntactically perfect node produces nothing and no
error.

## Reaching the tree from C

| Macro | Use |
| --- | --- |
| `DT_NODELABEL(spi0)` | By the `spi0:` label in the DTS |
| `DT_ALIAS(led0)` | By alias — how sample apps stay board-agnostic |
| `DT_CHOSEN(zephyr_console)` | System-wide selections |
| `DEVICE_DT_GET(...)` | The `struct device *` for a node |
| `DT_INST_*` | Inside a driver, per instance of its `compatible` |

`aliases` and `chosen` are the reason an unmodified sample blinks on a new
board: define `led0` and `zephyr,console` and someone else's code works
untouched. Worth defining on a custom board for exactly that reason.

## Ordering trap

`DEVICE_DT_GET` resolves at compile time and will happily hand back a
pointer to a device that has not initialised yet. `device_is_ready()` is
the check, and skipping it produces a failure that looks like broken
hardware. Init order comes from `POST_KERNEL` levels and priorities, not
from the tree's shape.

## Where this gets used here

- [[ble-sensor-node-pcb]] — an out-of-tree board definition, the reason for
  this note
- [[thread-matter-smart-planter]] — same SoC and SDK, but on a stock DK, so
  the tree is inherited rather than written
- [[industrial-sensor-node-linux]] — the Linux side of the same syntax
