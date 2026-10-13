---
tags: [project, automotive, can, uds, linux, python]
status: idea
depends: []
created: 2026-10-13
---

# DIY VAG UDS Coding Tool for the Touran

## Now

Not started. Nothing here is in progress — the plan below is the whole of it.

## Goal

A small tool, built on open-source libraries, that reads and writes coding
and adaptation values on my own car: a 2018 VW Touran 5T. It replaces a paid
subscription (OBDeleven) or an expensive interface (VCDS, roughly 200–400 €)
for the two changes I actually want, and it keeps a backup of everything it
touches so either change can be undone with my own tool.

Done when:

- interior monitoring stays off on a normal single lock, and the perimeter
  alarm still triggers;
- the cluster shows a fixed service interval;
- both changes are reversible from stored backups using my own tool.

Deliberately out of scope: any car other than this one; flashing, or entering
the programming session (`0x10 0x02`) at all; and reverse engineering or
decrypting VCDS label files, ROD files or any other proprietary data. What I
know about this car's modules comes from three places only — traffic on its
own bus, DID scans of its own modules, and public community documentation.

## Learning value

Secondary, and said plainly. Every other note in this vault exists for what
it teaches, with use as the second constraint; this one is the other way
round. It is a standalone project for configuring my own car, it sits in
none of the tracks, and it is not the start of an automotive curriculum —
I do not plan to go further into automotive than this car needs.

What it teaches is still worth taking where it falls, because it is real
material and the car makes it concrete:

- CAN at the frame level — 11-bit identifiers, 500 kbit/s, and what a busy
  bus looks like in `candump` before anything above it makes sense.
- ISO-TP (ISO 15765-2), the transport that carries messages longer than
  eight bytes over CAN: segmentation and flow control. It is the same problem
  as "fragmentation for an MTU that does not fit" in
  [[subghz-linux-router]], solved by a standard and already sitting in the
  kernel.
- UDS (ISO 14229) as a request/response protocol: sessions, security access,
  read and write by identifier, negative response codes, and why a module
  refuses a write.
- SocketCAN, where a CAN controller is a `net_device` like any other —
  `can0` configured over netlink with `ip link`, which is the argument in
  [[linux-networking-and-netdev]] made by a subsystem somebody else already
  wrote.
- Working out an undocumented protocol from captures of my own traffic,
  which is what [[subghz-collar-remote-clone]] did over the air.

## Practical value

Real, and the reason the project exists. The dog travels in the boot, and
the interior monitoring reads it as an intruder, so the alarm goes off. The
current workaround — locking twice within about two seconds, by key or the
KESSY handle, disarms interior monitoring for that one locking — works, but
has to be remembered every time. The service interval is a smaller want:
fixed at 15 000 km / 1 year instead of LongLife's flexible schedule.

The honest objection is that a borrowed OBDeleven would make both changes in
five minutes, and Phase 2 borrows one anyway. Sniffing the change while the
borrowed tool makes it means the car has both changes the moment the capture
is finished. What the tool adds after that is ownership rather than the
change itself: my own backups of the original coding and adaptation values,
the ability to read them back and verify, and the ability to reverse or
re-apply either change without borrowing anything again. That is a smaller
claim than "replaces OBDeleven", and it is the accurate one.

## Architecture

### The car

- VW Touran 5T, 2018, 1.8 TSI (EA888), MQB platform.
- Pre-SFD — no online gateway lock (Schutz Fahrzeug Diagnose, VW's scheme
  for signed write access through the gateway), so UDS coding should be
  possible locally.
- Factory alarm with interior monitoring and a tilt sensor; KESSY keyless
  entry.
- Diagnostic CAN on OBD-II pins 6 (CAN-H) and 14 (CAN-L), 500 kbit/s, 11-bit
  identifiers, reaching the modules through the gateway (module 19).

### The two changes

1. **Disable alarm interior monitoring permanently.** Module 09, Central
   Electronics, adaptation group "DWA / Anti-theft alarm system". The
   community reference is parameter IDE04928, "Anti-theft protection –
   Anti-theft alarm system", from a SeatCupra forum thread. The security
   access login for 09 adaptations is reported as 31347 on a Golf 7 —
   **unverified for the Touran 5T**. The perimeter alarm (doors, bonnet,
   boot) stays armed; only interior monitoring and, ideally, the tilt sensor
   go off.
2. **Switch the service interval from LongLife to fixed** (15 000 km /
   1 year). Module 17, Instrument cluster, adaptation. No public DID found
   yet; it has to be discovered.

The service reset itself is not the tool's job — the infotainment menu does
it: CAR → Settings → Service & checks → Reset.

### Safety rules

A module that accepts a wrong value does not report it as wrong; it simply
behaves differently, and on a car that can mean an alarm that never arms. So
the rules are the design rather than a footnote:

- A battery charger is connected during any write session.
- Read-only first (`0x22` ReadDataByIdentifier, `0x19` ReadDTCInformation).
  Writes (`0x2E` WriteDataByIdentifier, coding) only for DIDs that are fully
  understood.
- The original long coding (DID `0x0600`) and adaptation values are backed up
  before anything is written.
- No flashing and no programming session (`0x10 0x02`).
- DID scans are rate-limited, and done from the default session where
  possible.

This is the same lesson [[subghz-collar-remote-clone]] paid for with a year
at 70%: replaying something not understood works until it does not, and then
there is nothing to debug against. There the cost was a missed beep. Here a
write is persistent, so "fully understood" comes before the first `0x2E`
rather than after the first failure.

### Hardware — open, three candidates

| Option | What it is | For | Against |
| --- | --- | --- | --- |
| CANable / candleLight | USB adapter, `gs_usb` firmware, SocketCAN on the laptop | Plug-and-play; `can0` appears with no work; laptop sits in the car | 15–30 € more hardware |
| BeagleBone Green DCAN | One of the AM335x's two on-chip CAN controllers (`c_can` driver) plus a 3.3 V transceiver | Board already owned; binding the controller is pinmux and devicetree work from [[embedded-linux-course]] | That work stands between me and the car; a board, a transceiver and a supply in the footwell |
| ESP32 + CAN transceiver | Switchleg1/esp32-isotp-ble-bridge — ISO-TP over BLE | The later phone variant | Not a SocketCAN interface, so none of the can-utils tooling on the car side |

Undecided on purpose. The first two both end at `can0` and the same Python
on top, so the choice only decides how much Linux work comes before the
first frame. The ESP32 belongs to Phase 4 whichever one wins.

An OBD-II Y-splitter goes alongside any of them for passive sniffing next to
the borrowed OBDeleven or VCDS.

### Open questions

- The exact request/response CAN IDs for modules 09 and 17 on this car.
- The security access method and level for writes to 09 and 17 on a
  Touran 5T.
- The DID or DIDs behind DWA interior monitoring and the tilt sensor
  adaptation.
- The DID for the service interval mode (LongLife against fixed) in 17.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Bus access | One of the three candidates above | Undecided |
| Bus tooling | can-utils — `candump`, `isotpdump`, `cansniffer` | `candump -l` for logs worth keeping |
| Transport | Kernel ISO-TP module (5.10+) | `CAN_ISOTP` sockets |
| Analysis | Wireshark on SocketCAN | Decodes ISO-TP and UDS |
| Passive capture | OBD-II Y-splitter | Beside the borrowed tool |
| Reference capture | OBDeleven or VCDS, borrowed once | Makes the changes while I record |
| Power | Battery charger | Connected during every write session |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| CANable / candleLight clone | 15–30 €, or 0 € if the BeagleBone's DCAN is used |
| CAN transceiver breakout (BeagleBone route only) | ~3 € |
| OBD-II Y-splitter / breakout cable | ~10 € |
| Borrowed OBDeleven or VCDS | 0 € |
| Battery charger | not costed — whether one is on hand is not recorded yet |

Somewhere between 13 € and 40 € depending on the bus adapter. That is the
comparison that matters: a VCDS interface is 200–400 €, and OBDeleven's write
functions are a subscription.

## Software / firmware

- Linux SocketCAN, the kernel ISO-TP module and can-utils.
- Python: python-can, can-isotp, udsoncan.
- A CLI on udsoncan with `backup`, `read-did`, `write-did`, `read-coding` and
  `write-coding` — every write behind a mandatory backup, a confirm prompt
  and a verify-after-write read.

Captures and backups carry the VIN and this car's coding, and none of it
belongs in this vault, which is public. They stay with the tool's code,
outside any public repository — the same problem
[[subghz-collar-remote-clone]] solved with sops and a commit hook.

Prior art, read as reference rather than used as the tool:

- jrjoaoramos/mqbcan — MQB CAN analysis; documents reading and writing long
  coding and adaptations with and without security access (Leon 5F, applies
  to MQB).
- bluetoothbeijing/MQB-sniffer — a Golf 7 sniffing log taken with OBDeleven
  and an MCP2515 through a splitter.
- bri3d/VW_Flash — a Python VAG UDS stack, flashing-focused, useful for how
  it structures sessions and security access.
- Switchleg1/esp32-isotp-ble-bridge — the ESP32 BLE↔ISO-TP firmware.
- pylessard/python-udsoncan — the UDS implementation (MIT).
- MartijnD92/PyVCDS — **not applicable**: VW TP 2.0 and KWP2000 for older
  cars, not UDS.
- The SeatCupra forum thread "code out interior monitoring" — the DWA
  adaptation in module 09.

## Plan

**Phase 1 — Bring-up (read-only)**

- [ ] Get CAN adapter working on can0 at 500k
- [ ] Enumerate modules behind the gateway, identify request/response CAN IDs for 09 and 17
- [ ] Read identification DIDs (part number, SW version) and long coding (0x0600) of 09 and 17; store backups

**Phase 2 — Discovery**

- [ ] Borrow OBDeleven or VCDS once; sniff via Y-splitter with `candump -l` while performing both target changes
- [ ] Decode ISO-TP/UDS sequence: session control, security access (seed/key or login), RDBI of old value, WDBI of new value
- [ ] Optional: DID scan (0x22) on 09 and 17, diff before/after menu changes to map additional DIDs

**Phase 3 — Implementation**

- [ ] CLI tool on udsoncan: `backup`, `read-did`, `write-did`, `read-coding`, `write-coding`
- [ ] Mandatory backup + confirm prompt + verify-after-write
- [ ] Apply change 1 (interior monitoring), test alarm behavior with dog/boot, verify perimeter still armed
- [ ] Apply change 2 (fixed service interval), verify in cluster

**Phase 4 — Optional**

- [ ] BLE/ESP32 variant for phone use
- [ ] Publish findings (DIDs, sequences) for Touran 5T

## Build log

Session entries live in [[vag-uds-coding-tool-log]].
