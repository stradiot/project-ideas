---
tags: [project, embedded, linux, kernel, usb]
status: idea
depends: [industrial-sensor-node-linux]
created: 2026-08-07
---

# Custom USB Device and Its Linux Driver

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Build a USB peripheral and the kernel driver that talks to it — both ends
of the wire mine. Plug it into any other machine and it does nothing,
because the driver that understands it only exists here.

Learning goals:
- USB descriptors, endpoints and transfer types, written by hand
- The Linux USB driver model — `usb_driver`, probe/disconnect, URBs
- Asynchronous I/O in kernel space: submit, complete, resubmit

Deliberately out of scope: making it a HID device. HID would work with no
driver at all, which defeats the entire exercise.

## Architecture

| Side | Implementation |
| --- | --- |
| Device | nRF52840 or STM32 with native USB, vendor-specific class |
| Descriptors | Written by hand — device, configuration, interface, endpoints |
| Transport | Bulk IN/OUT for data, interrupt IN for events |
| Host | Out-of-tree kernel module, exposing a char device |
| Userspace | Small tool that opens the char device and drives the peripheral |

### The device itself

A rotary encoder, a few buttons and a small display — a desk peripheral
that ends up controlling volume, workspace switching, or whatever else it
earns. Deliberately mundane: the value is in the plumbing, and a device
that gets used daily is a device whose driver bugs get found.

The interrupt endpoint carries encoder and button events upward. The bulk
endpoints carry bulk data both ways — display contents down, logged samples
up. Both transfer types in one device, on purpose.

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

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Device | nRF52840 DK, or the board from [[ble-sensor-node-pcb]] | Native USB already routed |
| Firmware | Zephyr USB device stack, or bare STM32 | |
| Capture | `usbmon` + Wireshark | Every packet, both directions |
| Inspection | `lsusb -v`, `/sys/kernel/debug/usb/devices` | Confirm descriptors are what I wrote |
| Debug | `dmesg`, ftrace | |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Dev board with native USB (if not already owned) | 10–25 € |
| Rotary encoder, buttons, small OLED | 10–20 € |
| USB cable, breakout, enclosure | ~10 € |

Effectively free if the board from [[ble-sensor-node-pcb]] already exists —
that board has the USB-C connector, ESD protection and the nRF52840 on it.

## Software / firmware

- Device firmware: descriptor set, endpoint handlers, event generation
- Kernel module, out of tree, built against local kernel headers
- Userspace tool over the char device, plus a udev rule so the node appears
  with sane permissions rather than requiring root

## Plan

- [ ] Firmware enumerates as a vendor-specific device, verify with `lsusb -v`
- [ ] Capture enumeration in Wireshark, read my own descriptors off the wire
- [ ] Kernel module that only probes and prints the endpoints it found
- [ ] Interrupt IN URB, resubmitted on completion — events reach `dmesg`
- [ ] Bulk transfers both directions
- [ ] Char device interface, userspace tool driving the display
- [ ] `disconnect()` under load — unplug mid-transfer, confirm clean teardown
- [ ] udev rule, then actually use it as a desk peripheral

## Build log

Session entries live in [[usb-device-and-linux-driver-log]].
