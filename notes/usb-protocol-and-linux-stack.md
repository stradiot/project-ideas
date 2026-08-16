---
tags: [note, usb, embedded, linux, kernel, hardware]
created: 2026-08-15
---

# USB — Protocol, Classes and the Linux Stack

Reference note. The subject behind [[usb-device-and-linux-driver]], which is
the work; this is the material that project assumes and never states.

What sent me here: the 2026-08-15 session on
[[subghz-collar-remote-clone]], where flashing the perfboard prototype
needed a serial console and `/dev/cu.usbmodem101` turned out to involve no
UART anywhere in the path. The baud rate was decorative, DTR and RTS were
not wires, and the two facts had the same cause. Working out what that cause
was is most of this note.

## The misconception this exists to correct

**USB is not a faster serial port.** It is a host-mastered, polled bus, and
a device never transmits a bit that was not solicited. The host sends a
token packet naming a device address and an endpoint; only then does data
move, and only in the direction that token named. There is no such thing as
a device deciding to speak.

Everything below follows from that one property:

- The host must know what to ask for and how often, so the device has to
  describe itself in advance — **descriptors** and **enumeration**.
- Bus time has to be divided up before the fact — the four **transfer
  types**, which differ in what they guarantee rather than in how fast they
  are.
- A device that is not ready cannot hold the line, it has to answer
  something — **NAK**, which is flow control in band, and the reason USB
  needs no RTS/CTS wires.
- A bus where the device announces what it is can bind a driver with no
  prior knowledge — **classes**, and the reason a keyboard works on a
  machine that has never seen it.

An RS-232 port has none of that. It cannot report what is attached, it
cannot negotiate anything, and its only discovery mechanism is a human
knowing what they plugged in.

## The wire

D+ and D− are one differential pair, **half duplex** — one conversation at a
time, in whichever direction the current token said. There is no clock line.
The receiver recovers timing from the data itself, and two mechanisms make
that possible.

**NRZI**: a `0` is encoded as a transition on the pair, a `1` as no
transition. Backwards from the obvious choice, and deliberately so — it
means a long run of zeros is a long run of edges rather than a flat line.

**Bit stuffing**: after six consecutive `1` bits the transmitter inserts a
`0`, which under NRZI forces a transition. Without it, seven idle-looking
`1`s in a payload would be seven bit-times with no edge and the receiver's
clock recovery would drift off. The stuffed bit is removed on the other
side and never reaches the payload. This is the whole answer to "where is
the clock" — there is none, and bit stuffing is the price of not having one.

### Speed, and how it is detected before anything is configured

Speed is signalled by a resistor, before a single packet is exchanged:

| Speed | Rate | How the host learns it |
| --- | --- | --- |
| Low | 1.5 Mbit/s | 1.5 kΩ pull-up on **D−** |
| Full | 12 Mbit/s | 1.5 kΩ pull-up on **D+** |
| High | 480 Mbit/s | Attaches as full speed, then chirps |
| SuperSpeed | 5 Gbit/s and up | Separate pairs entirely — see the variants below |

The pull-up does two jobs at once: it tells the hub something is attached at
all, and which speed it is. A device that wants to disappear from the bus
without being unplugged simply drops its pull-up, which is how software-
controlled re-enumeration works after a firmware update.

High speed is a negotiation grafted onto that. The device attaches as full
speed, then during bus reset drives a **chirp K**; a high-speed-capable hub
answers with alternating K-J chirps; the device removes its pull-up and both
ends switch to current-mode signalling into 45 Ω terminations. A high-speed
device on a full-speed-only hub simply never hears the answer and stays at
12 Mbit/s — which is why the same device can be fast on one port and slow on
another with nothing wrong anywhere.

Clock accuracy is a hardware consequence worth carrying: ±1.5% at low speed,
**±0.25% at full speed**, ±0.05% at high speed. That 0.25% is why native USB
on a microcontroller usually means a crystal — the nRF52840 will not run its
USB peripheral without the 32 MHz HFXO. Crystal-less USB parts exist and
work by trimming an internal oscillator against the host's start-of-frame
packets, which arrive on a known 1 ms period.

### USB-C, and the resistor that decides whether a board works at all

USB-C added a pair of **CC** (Configuration Channel) pins that carry no data
in the USB 2.0 sense. A device that wants to be a sink presents **5.1 kΩ to
ground on each CC line** — `Rd`. A source presents a pull-up, `Rp`, whose
value advertises how much current it can supply. Which of CC1 or CC2 sees
the resulting divider is how orientation is detected, and that is the whole
reason a reversible connector is possible.

The practical consequence is blunt: **a self-designed USB-C device without
those two 5.1 kΩ resistors does not enumerate, and looks exactly like a dead
board.** A host with no `Rd` to see never turns VBUS on. It is the single
most common failure on a first hand-drawn USB-C schematic, and it is
invisible in a schematic review that is looking at D+/D−.

## Packets, transactions, transfers

Three layers, and confusing them is where most of the vocabulary trouble
lives.

A **packet** is SYNC, a PID, an optional payload, a CRC and an end-of-packet.
The PID falls in one of three groups:

| Group | PIDs | Meaning |
| --- | --- | --- |
| Token | `IN`, `OUT`, `SETUP`, `SOF` | The host naming a device, an endpoint and a direction |
| Data | `DATA0`, `DATA1` | The payload, with an alternating toggle |
| Handshake | `ACK`, `NAK`, `STALL`, `NYET` | The receiver's verdict |

A **transaction** is the usual three of those in sequence: token, data,
handshake. A **transfer** is a sequence of transactions that means something
to software — one control transfer is a `SETUP` transaction, optional data
transactions, and a status transaction in the opposite direction.

### The data toggle, and why retries are safe

`DATA0` and `DATA1` alternate on every successful transaction. If a device
receives data and its `ACK` is lost on the way back, the host retries the
same packet with the *same* toggle. The device sees a toggle it has already
consumed, discards the duplicate and re-acknowledges. One bit turns a naive
retry into an idempotent one, with no sequence numbers and no timestamps.

Worth knowing where the toggle resets, because getting it wrong desynchronises
an endpoint permanently: `SET_CONFIGURATION`, `SET_INTERFACE`, and clearing a
halt with `CLEAR_FEATURE(ENDPOINT_HALT)` all reset it to `DATA0`.

### NAK and STALL — flow control without wires

**`NAK`** means "not now, ask again". It is not an error and nothing is
retried at a higher level; the host simply reissues the token later. This is
the entire flow-control mechanism, and it is why USB has no equivalent of
RTS/CTS: a busy device answers every poll with `NAK` until it is ready. A
device that NAKs forever is not broken from the bus's point of view, merely
slow — which makes "it enumerates but transfers nothing" a distinct and
common failure mode.

**`STALL`** means "this endpoint is in an error state and will not proceed
until cleared". On EP0 it is the standard answer to a request the device does
not implement, and the host treats it as a normal negative reply. On any other
endpoint it is sticky, and stays until the host issues
`CLEAR_FEATURE(ENDPOINT_HALT)`.

### Frames

The host emits a start-of-frame every 1 ms at full speed, every 125 µs
(a microframe) at high speed. Bandwidth is budgeted inside those: at full
speed, control transfers are guaranteed 10% and the periodic types may claim
at most 90%, with bulk taking whatever is left. This is the machinery behind
the guarantees in the next section — a periodic endpoint is admitted at
configuration time or the configuration is rejected.

## Endpoints and the four transfer types

An **endpoint** is a buffer in the device with a number (0–15) and a fixed
direction, named from the host's point of view: `IN` means towards the host.
Endpoint 0 is special — it always exists, it is bidirectional, and it carries
control transfers including every one of the enumeration requests. An address
on the bus is therefore a triple: device address, endpoint number, direction.

| Type | Guarantee | Retries | Typical use |
| --- | --- | --- | --- |
| **Control** | Reserved share of bandwidth | Yes | Enumeration; any command-shaped operation |
| **Bulk** | None — gets what is left | Yes | Bulk data: storage, CDC payload, my own logging |
| **Interrupt** | Polled at least every `bInterval` | Yes | Small, latency-bounded events: keys, encoder ticks |
| **Isochronous** | Fixed bandwidth every frame | **No** | Audio, video — where late is worse than lost |

The thing to internalise is that **the transfer type is chosen by failure
mode, not by throughput**. Isochronous does not retry, on purpose: a
retransmitted audio sample arriving two frames late is worse than a dropped
one. Bulk is the fastest type on an idle bus and offers no promise at all on
a busy one. Interrupt trades throughput for a bounded worst case. Picking
bulk because it sounds big is how a peripheral ends up with unpredictable
latency behind a webcam.

`bInterval` is where the polling rate is declared, and its units differ by
speed: frames (1–255 ms) for full-speed interrupt endpoints, and
`2^(bInterval−1)` microframes at high speed. Asking for 1 ms polling on
sixteen endpoints is how a configuration gets refused for want of bandwidth.

## Descriptors and enumeration

Descriptors are the device's self-description, and they form a tree read
top-down by the host:

```
Device                       ← VID, PID, class, EP0 max packet size
 └── Configuration           ← power draw, self- or bus-powered
      └── Interface          ← one function; class/subclass/protocol
           ├── [alt setting] ← same interface, different bandwidth
           └── Endpoint      ← number, direction, type, bInterval
```

Plus string descriptors for the human-readable names, class-specific
descriptors interleaved where a class defines them, and — for a device with
more than one function — an **Interface Association Descriptor**, which
groups several interfaces into one logical function. An IAD is what makes a
CDC-ACM device's two interfaces, control and data, bind as a single serial
port rather than as two unrelated things.

Enumeration, in the order it happens:

1. The pull-up appears; the hub reports a port change.
2. The host resets the port. The device is now at address 0.
3. The host reads the **first 8 bytes** of the device descriptor — enough to
   learn EP0's maximum packet size, which it needs before it can read
   anything longer.
4. `SET_ADDRESS` moves the device off address 0, so the next one can attach.
5. The full device descriptor, then the configuration descriptors — each
   fetched twice, once for the length and once for the whole thing.
6. `SET_CONFIGURATION` — the device is now *configured*, may draw its full
   declared current, and its non-zero endpoints come alive.
7. The host binds a driver per **interface**.

Two consequences of that sequence are worth carrying. A device may draw only
100 mA before step 6, whatever `bMaxPower` says, so a board that powers up
its radio too early browns out during enumeration and reads as a flaky cable.
And a descriptor bug shows up as a failure at a specific numbered step, which
is what makes `usbmon` capture the fastest way to debug one — the last
successful request names the problem.

**VID and PID** are the matching key, sixteen bits each. A USB-IF vendor ID
costs real money annually, which is why hobby and test hardware uses the
`pid.codes` allocation under VID `0x1209`. Worth remembering that Windows
caches descriptors keyed on VID/PID, so changing a descriptor without moving
the PID can leave a machine behaving from a stale copy.

## Classes, and the compatibility bargain

The class/subclass/protocol triple in the interface descriptor is what lets
a device work with no driver installed. HID, CDC (serial, ethernet), mass
storage, audio, video, DFU: the host already has code for each, and the
device gets to be generic hardware.

Class `0xFF` is **vendor-specific** — no generic driver will touch it, and
something has to be written. That is the deliberate choice in
[[usb-device-and-linux-driver]]: HID would work with no driver at all, which
removes the entire exercise.

### The two ways a USB device looks like a serial port

These get conflated constantly and they are not the same thing:

| | USB-to-UART bridge | Native CDC-ACM |
| --- | --- | --- |
| Examples | FT232R, CP2102, CH340 | ESP32-C3 USB Serial/JTAG, nRF52840, RP2040 |
| Is there a UART? | Yes, real pins on the far side | **No.** Nothing anywhere |
| Baud rate | Genuinely reprogrammes a UART | Accepted and discarded |
| DTR / RTS | Drives real output pins | Two bits in a control request |
| Linux driver | Vendor: `ftdi_sio`, `cp210x` | Class: `cdc_acm` |

**CDC-ACM** is Communications Device Class, Abstract Control Model, and the
name is archaeology: the model it abstracts is a *modem*. That is why the
control interface carries `SET_LINE_CODING` (baud, parity, stop bits) and
`SET_CONTROL_LINE_STATE` (DTR, RTS) as control requests on EP0, why the
modem status lines DCD, DSR and RI come back as notifications on an
interrupt endpoint, and why the bytes themselves ride a pair of bulk
endpoints where no timing is promised.

On a native part, `SET_LINE_CODING` has nothing to apply itself to and is
accepted and ignored — which is exactly what the C3 does. The bytes move at
whatever the 12 Mbit/s bus has spare regardless of the number requested.
`SET_CONTROL_LINE_STATE` is where the ESP32 boot circuit lives: DTR and RTS,
which were RS-232 modem wires, then became two bits in a USB control
request, and are now watched by silicon that drives the reset and boot-mode
logic the way a discrete transistor pair once did. Three layers of
pretending, each faithful to the one above it, and the result is that a
programmer written for a 1985 serial port still resets the board.

Linux completes the illusion by exposing the whole thing through the tty
layer as `/dev/ttyACM0`, so `termios`, `stty` and every program ever written
against RS-232 keep working. macOS adds the callin/callout split on top —
`tty.*` blocks in `open()` until DCD is asserted, because it is meant for a
line something dials *into*; `cu.*` is for a device the host initiates
against, which is every USB serial device without exception. Detail and
evidence in [[subghz-collar-remote-clone-log#2026-08-15]].

### What the emulation loses

Worth stating, because the abstraction is good enough to be trusted too far:
there is no line timing, so a break condition and inter-byte gaps are
approximations; latency is quantised by polling intervals and host buffering,
and an FTDI bridge defaults to a 16 ms latency timer that will flatten any
attempt to measure timing through it; and unplugging is a real, reported
event rather than a line going quiet, so the file descriptor dies where an
RS-232 program would have waited forever.

## How this differs from the other serial buses

| | Who starts | Addressing | Clock | Hot-plug | Discovery |
| --- | --- | --- | --- | --- | --- |
| **UART / RS-232** | Either, any time | None | Each side's own, agreed out of band | No | None |
| **SPI** | Master only | Chip-select wire | Master supplies SCK | No | None |
| **I²C** | Master (multi-master possible) | 7-bit address in the frame | Master supplies SCL | No | Address probing, by convention |
| **CAN** | Any node | Message ID, arbitrated on the wire | Recovered, bit stuffed | Yes | None |
| **USB** | Host only | Device address + endpoint | Recovered, bit stuffed | **Yes** | **Full self-description** |

Two columns carry the difference. USB is the only one of these where a
device tells the system what it is, and the only one designed around things
appearing and vanishing at arbitrary times. The rest of USB's apparent
complexity is what those two properties cost.

RS-232 is worth pinning down while nearby, since the terms get used
interchangeably: RS-232 is an *electrical* standard — ±3 V to ±15 V,
inverted, historically on a DB-9 — while a UART is the *peripheral* that
serialises bytes. A 3.3 V "UART" header on a board is neither one nor the
other, and connecting it to a real RS-232 port without a level shifter
destroys the pin.

## The Linux side

### Host: usbcore, `usb_driver`, URBs

`usbcore` is the bus in the driver-model sense of [[linux-driver-model-and-subsystems]]
— devices arrive from enumeration rather than from devicetree, and matching
is on VID/PID or class rather than on `compatible`. A driver registers a
`struct usb_driver` with an `id_table` built from `USB_DEVICE()` or
`USB_INTERFACE_INFO()` macros, and gets `probe()` and `disconnect()`.

The one thing to get right early: **binding is per interface, not per
device.** A composite device binds several drivers at once, and a driver's
`probe()` is handed one interface, not the whole thing.

I/O is the **URB**, the USB Request Block — a submitted-and-forgotten
descriptor of one transfer with a completion callback. `usb_alloc_urb`,
`usb_fill_bulk_urb`, `usb_submit_urb`, then the callback runs in interrupt
context when the transfer finishes, fails or is cancelled. The idiom for an
interrupt endpoint is that the completion handler resubmits the same URB,
so the polling loop sustains itself. `usb_control_msg` and `usb_bulk_msg`
are the synchronous convenience wrappers for the cases where blocking is
fine — enumeration-time setup, mostly.

Teardown is where the real difficulty is, and it is the part a tutorial
driver never reaches. `disconnect()` can be called with URBs in flight, and
their completion handlers will run *after* the device is gone. `usb_anchor`
exists for exactly this: anchor every submitted URB, and `usb_kill_anchored_urbs`
in `disconnect()` waits for all of them to complete or be cancelled before
anything they point at is freed.

### Device: the gadget framework

Linux can also be the device end. Below the API is a **UDC** driver for the
controller (`musb` on the AM335x in the BeagleBone), and above it a gadget
composed from functions the kernel already has — `acm`, `ecm`, `mass_storage`,
`hid` — assembled at runtime in **configfs** by making directories. No
compilation, no reflashing: the same board is a serial port, then a network
adapter, then a USB stick.

**FunctionFS** goes one step further and moves the implementation into
userspace: the kernel handles enumeration, a normal program reads and writes
the endpoints through file descriptors. That is a vendor-specific USB device
with no firmware and no kernel code, which is a genuinely surprising thing to
be able to do and the reason the gadget half of
[[usb-device-and-linux-driver]] needs no microcontroller at all.

**Dual-role** closes the loop — the same port as host or device, decided by
what is plugged in. It is the clearest possible demonstration that "host" and
"device" are software positions rather than physical facts.

### Type-C and Power Delivery: a separate subsystem, and a separate protocol

PD is not part of the data path and shares nothing with it. It is BMC-encoded
signalling on the **CC** line, half duplex, negotiating a contract: the source
advertises **PDOs** (Power Data Objects — the voltage/current pairs it can
supply), the sink picks one with an **RDO**, and until that exchange completes
the sink is limited to what the `Rp` resistor advertised.

It needs its own silicon — a PD PHY such as the FUSB302 — and Linux drives it
through **TCPM** (`drivers/usb/typec/tcpm/`), a readable in-kernel state
machine implementing the specification, with the `typec` class exposing
partners and contracts in sysfs. Being a state machine with a spec next to it
makes it unusually good reading for a subsystem.

### Tools

| Purpose | Tool |
| --- | --- |
| Every packet, both directions | `modprobe usbmon`, then Wireshark on `usbmonN` |
| What the device claims to be | `lsusb -v`, `lsusb -t` for the topology |
| Kernel's view | `/sys/kernel/debug/usb/devices`, `/sys/bus/usb/devices/` |
| Enumeration failures | `dmesg` — the last successful request names the problem |

## Designing a USB interface on a board of my own

The checklist this note exists to be able to produce, for the point where
[[ble-sensor-node-pcb]] or its successors get a connector:

1. **Native USB, a bridge chip, or neither.** Native costs a crystal
   (±0.25%) and firmware; a bridge chip costs ~1 € and a driver the host
   already has; neither is right if the only need is a debug console and an
   SWD probe is already there.
2. **Connector and CC.** USB-C even for a pure device. **5.1 kΩ Rd on CC1
   and CC2**, or nothing happens. A Micro-B device instead ties ID high.
3. **VBUS detection** as its own input if the device also runs on battery —
   the nRF52840 has `USBREGSTATUS` for this. Without it there is no way to
   know whether to bring the USB peripheral up, and a power path that
   guesses is a power path that fights the charger.
4. **ESD on D+, D− and VBUS.** A USBLC6-2SC6 or equivalent, placed at the
   connector rather than at the MCU — after the pair has been routed past
   it, the protection is decorative.
5. **Routing.** D+/D− as a tight pair, length matched, over an unbroken
   ground reference, away from switching regulators. 90 Ω differential is
   mandatory at high speed; at full speed it is forgiving, and doing it
   anyway costs nothing.
6. **Declare the power honestly.** `bMaxPower` in the configuration
   descriptor, and nothing above 100 mA drawn before `SET_CONFIGURATION`.
7. **Pick the class before writing anything.** If HID, CDC or MSC does the
   job, the driver problem disappears entirely. Vendor-specific is the right
   answer only when owning the driver *is* the point.
8. **Pick each endpoint's transfer type by failure mode** — see the table
   above — and check the polling intervals add up.
9. **Get a PID** from `pid.codes` rather than borrowing somebody's.
10. **Enumerate on all three hosts.** Linux, macOS and Windows disagree
    about malformed descriptors, and the one that accepts a mistake silently
    is the one that will hide it until later.

## Variants, and the naming

Worth knowing so that a datasheet's claim can be read for what it says:

- **USB 1.1 / 2.0** — low, full and high speed, everything above, one
  differential pair.
- **USB 3.x** — SuperSpeed is a *second, independent link* on additional
  wire pairs. The USB 2.0 pair stays and stays live, which is why a USB 3
  device still enumerates on a USB 2 port. The naming was then rewritten
  twice: what shipped as USB 3.0 (5 Gbit/s) is now "USB 3.2 Gen 1x1", and
  10 Gbit/s is "Gen 2x1".
- **USB4 / Thunderbolt** — tunnelling rather than a bus: PCIe, DisplayPort
  and USB traffic multiplexed over the Type-C pairs.
- **Type-C** — a connector and a CC-based configuration scheme, orthogonal
  to speed. A Type-C port may be USB 2.0 only, and often is.
- **Power Delivery** — a protocol on CC, orthogonal to both. Also carries
  **Alt Mode**, which reassigns the SuperSpeed pairs to something else
  entirely, such as DisplayPort.
- **OTG and dual-role** — OTG is the older Micro-AB and ID-pin scheme;
  Type-C replaces it with CC-based role detection and role swap.

The pattern behind the list: connector, speed, power and protocol are four
independent axes that marketing names collapse into one. "USB-C" says
nothing about speed, and "USB 3.1" says nothing about power.

## Where this sits

- [[usb-device-and-linux-driver]] — the project this is the subject matter
  for; three vehicles, because no single piece of hardware covers all of it
- [[subghz-collar-remote-clone]] — CDC-ACM in anger, and where the question
  came from
- [[linux-driver-model-and-subsystems]] — the same probe/match model with
  enumeration instead of devicetree as the source of devices
- [[linux-char-drivers-and-irqs]] — the `file_operations` a USB driver ends
  up presenting upward
- [[ble-sensor-node-pcb]] — the board the design checklist is aimed at
- [[embedded-learning-curriculum]] — where this fits among the five courses,
  which is awkwardly, because USB belongs to three of them
