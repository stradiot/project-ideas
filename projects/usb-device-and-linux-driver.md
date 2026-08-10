---
tags: [project, embedded, linux, kernel, usb]
status: idea
depends: []
created: 2026-08-07
---

# Custom USB Device and Its Linux Driver

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Understand USB properly — not one peripheral, but the subsystem: how a
device describes itself, how a host claims it, how Linux presents both roles,
and how power is negotiated on a wire that also carries data.

Learning goals:
- USB descriptors, endpoints and transfer types, written by hand
- The Linux USB driver model — `usb_driver`, probe/disconnect, URBs
- Asynchronous I/O in kernel space: submit, complete, resubmit
- Linux as a USB *device* — the gadget framework, configfs, FunctionFS
- Dual-role: one port, both directions, and what negotiates that
- USB Power Delivery, which is a separate protocol on separate wires

Deliberately out of scope: writing a class driver for a class that already
has one, and SuperSpeed — nothing available here does 5 Gbps.

### Three vehicles, because no single one covers it

This is the correction that shapes the whole project. The obvious plan —
put USB on the custom board and learn it there — covers about a third of the
above, because the nRF52840's USB is **full-speed, device-only**. No host,
no dual-role, no Power Delivery, and 12 Mbps rather than 480.

| Vehicle | Covers | Why it |
| --- | --- | --- |
| The board from [[ble-sensor-node-pcb]] | Descriptors, endpoints, transfer types, composite devices, Zephyr's USB stack | Native USB already routed; no new hardware |
| The BeagleBone Green | Gadget mode, dual-role, the host-side driver, high speed | AM335x MUSB does host *and* device on one port |
| A FUSB302 breakout, ~5 € | Power Delivery, Linux's Type-C/TCPM subsystem | PD needs a PD PHY; nothing else here has one |

The BeagleBone is the interesting one and it costs nothing — it is already
on the bench for [[embedded-linux-course]]. It can present itself as a USB
device to a laptop *and* enumerate devices as a host, which means both ends
of the wire can be mine without a second board existing.

### The device itself

A rotary encoder, a few buttons and a small display — a desk peripheral
that ends up controlling volume, workspace switching, or whatever else it
earns. Deliberately mundane: the value is in the plumbing.

The interrupt endpoint carries encoder and button events upward. The bulk
endpoints carry bulk data both ways — display contents down, logged samples
up. Both transfer types in one device, on purpose.

It is vendor-specific, so it works only on a machine with my driver loaded.
That is the point rather than a flaw — HID would work with no driver at all,
which removes the entire exercise — but it is also a real limit, and the
honest consequence is that this is bench equipment that happens to sit on a
desk, not a peripheral to depend on. A kernel upgrade means rebuilding the
module.

### Device side

Vendor-specific class, so the host has no idea what it is until my driver
claims it. Own VID/PID pair from a test range, own descriptors, no class
driver doing the work invisibly.

### Host side

| Step | What it exercises |
| --- | --- |
| `usb_driver` registration + ID table | How the kernel matches a driver to a device |
| `probe()` | Walking the interface descriptor, finding endpoints by direction and type |
| URB allocation and submit | Asynchronous transfers, completion callbacks |
| Char device on top | `file_operations` — the same interface as in [[industrial-sensor-node-linux]] |
| `disconnect()` | Teardown while transfers are in flight, without panicking |

### What I get to break

Owning the firmware is the point. Failures that are impossible to stage
with someone else's hardware:

- Stall an endpoint deliberately, see how the host recovers
- Return a short packet where the driver expects a full one
- Unplug mid-transfer and confirm `disconnect()` unwinds cleanly
- Ship a malformed descriptor and watch enumeration fail
- Make the device stop responding, and find out what a hung URB does

Getting `disconnect()` right while URBs are in flight is where most of the
real learning is, and it is the one thing a tutorial driver never covers.

### Linux as the device — the gadget side

The half that needs no firmware at all. Linux can *be* a USB device, and the
BeagleBone's port is wired for it: compose a gadget in configfs from
functions the kernel already has (`ecm`, `acm`, `mass_storage`, `hid`), plug
it into a laptop, and it appears as whatever was composed. Then **FunctionFS**
moves the implementation into userspace — a vendor-specific device whose
endpoints are serviced by a normal program.

That gives a second, entirely different route to "both ends of the wire are
mine", with no microcontroller in the picture. It is also how a great many
real products present a management interface, and it is worth knowing
exists before writing firmware to do the same job.

**Dual-role** closes it: the same port, host or device, decided by what is
plugged in. The AM335x supports it, Linux implements it, and watching a port
change roles is the clearest demonstration there is that "USB host" and "USB
device" are software positions rather than physical facts.

### Power Delivery, which is not the data path

PD is easy to assume is part of USB and it is not. It is a separate protocol,
BMC-encoded on the **CC lines**, negotiating voltage and current between a
source and a sink — completely independent of D+/D− and of anything the data
stack does.

It needs its own silicon: a PD PHY. A **FUSB302** breakout at about 5 € on
I²C is the hackable one, and it is supported by Linux's **Type-C/TCPM**
subsystem — a real, readable in-kernel state machine implementing the PD
specification. Source capabilities, sink requests, PDOs and RDOs,
explicit contracts, and what happens when a negotiation fails.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Device end | The board from [[ble-sensor-node-pcb]] | Native USB routed; full-speed, device-only |
| Both ends | BeagleBone Green | AM335x MUSB — high-speed host *and* device, dual-role |
| Firmware | Zephyr USB device stack | On the nRF side |
| Gadget | configfs, FunctionFS | On the BeagleBone; no firmware involved |
| Power Delivery | FUSB302 breakout on I²C | Drives Linux's Type-C/TCPM subsystem |
| Capture | `usbmon` + Wireshark | Every packet, both directions |
| Inspection | `lsusb -v`, `/sys/kernel/debug/usb/devices` | Confirm descriptors are what I wrote |
| Debug | `dmesg`, ftrace | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Device end | free — the board from [[ble-sensor-node-pcb]] |
| Host, gadget and dual-role | free — the BeagleBone Green |
| FUSB302 breakout | ~5 € |
| USB-C breakout board with CC lines exposed | ~5 € |
| Rotary encoder, buttons, small OLED | 10–20 € |
| USB cables, OTG adapter, enclosure | ~10 € |

Around 30 € for the whole subsystem, because both computers involved already
exist. The nRF board has the USB-C connector, ESD protection and native USB
already routed; the BeagleBone has a dual-role port and a mainline MUSB
driver.

## Software / firmware

- Device firmware: descriptor set, endpoint handlers, event generation
- Kernel module, out of tree, built against local kernel headers
- Userspace tool over the char device, plus a udev rule so the node appears
  with sane permissions rather than requiring root

## Plan

**Device end — the nRF52840 board**

- [ ] Firmware enumerates as a vendor-specific device, verify with `lsusb -v`
- [ ] Capture enumeration in Wireshark, read my own descriptors off the wire
- [ ] Interrupt IN and bulk both directions, from hand-written descriptors
- [ ] A composite device — two interfaces, one cable, and what an IAD is for

**Host end — the driver**

- [ ] Kernel module that only probes and prints the endpoints it found
- [ ] URB allocation, submit, completion, resubmit
- [ ] Char device interface, userspace tool driving the display
- [ ] `disconnect()` under load — unplug mid-transfer, confirm clean teardown
- [ ] Break it on purpose: stall, short packet, malformed descriptor, hung URB
- [ ] udev rule so the node appears without root

**Gadget and dual-role — the BeagleBone**

- [ ] Compose a gadget in configfs, plug it into a laptop, see it enumerate
- [ ] Swap the function set — serial, ethernet, storage — without reflashing
- [ ] FunctionFS: a vendor-specific gadget serviced from userspace
- [ ] Point my own host driver at my own gadget — both ends, no firmware
- [ ] Dual-role: the same port as host, then as device, and what decides

**Power Delivery**

- [ ] FUSB302 on I²C, register access working
- [ ] Read the CC lines: orientation, attach and detach
- [ ] Sink negotiation through Linux's TCPM — request a voltage and get it
- [ ] Read the advertised PDOs from a charger and explain each one
- [ ] Refuse a contract deliberately and watch the state machine recover

The host side assumes the driver model — `probe()`, match tables, `devm_`,
deferred probe — plus the buffer and DMA handling URBs sit on top of, which
are modules 6 and 7 of [[embedded-linux-course]]. The gadget and dual-role
work happens on the same BeagleBone that course uses, so it lands naturally
after those modules rather than needing its own board.

## Build log

Session entries live in [[usb-device-and-linux-driver-log]].
