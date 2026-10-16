---
tags: [project, automotive, can, uds, linux, python]
status: idea
depends: []
created: 2026-10-13
---

# DIY VAG UDS Coding Tool

## Now

Not started. Nothing here is in progress — the plan below is the whole of it.

## Goal

A small tool, built on open-source libraries, that runs on a BeagleBone Green
I already own, using its processor's built-in CAN controller and a 3.3 V
transceiver. A laptop is only a terminal into it. It reads and clears fault
codes, and
reads and writes coding and adaptation values, on my own car: a 2018 VW
Touran 5T. It replaces a paid
subscription (OBDeleven) or an expensive interface (VCDS, roughly 200–400 €)
for the handful of changes I actually want. It also backs up everything it
touches, so every change can be undone with my own tool.

v1 is the Touran only. It is done when:

- the tool reads fault codes from every module behind the gateway, and
  clears them once they have been saved;
- interior monitoring stays off on a normal single lock, and the perimeter
  alarm still triggers;
- start-stop comes back in the state it was left in at the last ignition-off.
  If the car offers no last-mode setting, it stays off permanently instead;
- the cluster runs a fixed 15 000 km / 1 year service interval, and the tool
  resets the service reminder after an oil and filter change;
- after a battery replacement, the tool registers the new battery with the
  car's battery monitoring, and reading the value back shows it took;
- every change can be undone from stored backups using my own tool.

Later, after v1, come two more family cars: a 2017 Škoda Kodiaq and a 2017
Škoda Fabia III. Each one gets its own profile and its own discovery.
The code should not need to change for them.

Deliberately out of scope:

- The family's 2010 Passat. It is on the older PQ46 platform, whose modules
  mostly speak KWP2000 (the protocol before UDS) over VW TP 2.0 (VW's own
  transport, not ISO-TP). That is unverified, from community documentation.
  If it holds, it means a second protocol stack under the same tool for one
  car, which is more than that car is worth here.
- A standalone device with its own screen, or a phone app. The BeagleBone
  is driven from a terminal.
- Flashing, and entering the programming session (`0x10 0x02`) at all.
- Reverse engineering or decrypting VCDS label files, ROD files or any other
  proprietary data. What I know about a car's modules comes from three places
  only: traffic on its own bus, DID scans of its own modules, and public
  community documentation.

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
- Working out undocumented data from my own car's answers, with no
  reference tool to copy, which is what [[subghz-collar-remote-clone]] did
  over the air.

## Practical value

Real, and the reason the project exists. Four wants drive it:

- **The alarm.** The dog travels in the boot, and interior monitoring reads
  it as an intruder, so the alarm goes off. The current workaround is to lock
  twice within about two seconds, by key or the KESSY handle, which disarms
  interior monitoring for that one locking. It works, but it has to be
  remembered every time.
- **Start-stop.** It comes back on at every ignition and has to be switched
  off by button on every drive.
- **The service interval.** I do my own oil and filter service, so I want a
  fixed 15 000 km / 1 year interval instead of LongLife's flexible schedule,
  and the reminder needs resetting after every change. The Touran's
  infotainment menu already does the reset (CAR → Settings → Service &
  checks → Reset). The tool repeats that operation over UDS, which matters
  less on this car than on the ones that come after it.
- **Battery registration.** A replacement battery has to be registered, or
  the car's energy management keeps treating it as the old, worn one. The
  car has no menu for it, so today it means a workshop.

The honest objection is that an OBDeleven or a VCDS interface would make
every one of these changes in minutes, from data VW's own tools use. I have
neither and borrow neither, so my own tool is the only route here. The price
is that every write rests on public community documentation and on reads from
my own car, not on a capture of a tool known to work. That is what the
discovery approach and the safety rules below are built around. What the
tool gives me:

- the changes themselves;
- my own backups of the original coding and adaptation values;
- reading them back to verify;
- undoing or re-applying any change;
- the service reset at every oil change, and battery registration at every
  battery replacement.

It does not replace OBDeleven in general. It replaces it for these five
items on cars I can test on. For start-stop alone, the thing to buy instead
is an aftermarket memory plug: it sits in the OBD port and sends the "off"
press at every start, with no coding. It covers one of the five items.

### Has it been done already?

Checked on 2026-10-16, before committing to the project: not for these items.
The closest open-source project, orviwan/vibesODB2, does the easy half and
has explicitly withdrawn the hard half.

- **What it is.** An MIT-licensed browser app with a Python CLI, started in
  September 2026 and labelled alpha. It talks UDS through BLE ELM327-type
  adapters to PQ25, PQ35/PQ46 and MQB cars.
- **What it does.** It reads and clears fault codes. It toggles long-coding
  bits in 09 and 17 against bundled bit maps, with a backup keyed by VIN and
  a read after every write to check it.
- **What it does not do.** No item on my list is in its MQB maps, and none
  of its features is verified on any vehicle. It does not perform
  SecurityAccess, so nothing behind a login can be written. Service reset,
  battery registration and start-stop were in earlier builds and were removed
  on 2026-09-17. Their identifiers had been guessed: the tool tried candidate
  DIDs until one accepted a write. Its `docs/REMOVED_FEATURES.md` records
  that, and it is the clearest description I have found of how this project
  goes wrong.

Everything else found is either closed and commercial (OBDeleven, VCDS,
Carista, CarCoding), a library or tool rather than a solution (listed under
Prior art below), or one of several GitHub organisations named after VCDS
that look like lure repositories and are not prior art. So what this project
adds that nothing public has is identifiers and a security access method
verified on one named car. That is also what makes Phase 5 worth doing.

## Architecture

### The car

- VW Touran 5T, 2018, 1.8 TSI (EA888), MQB platform.
- Pre-SFD, so UDS coding should be possible locally. SFD (Schutz Fahrzeug
  Diagnose) is VW's scheme that puts signed, online-only write access in front
  of the gateway, and this car predates it.
- Factory alarm with interior monitoring and a tilt sensor; KESSY keyless
  entry.
- Diagnostic CAN on OBD-II pins 6 (CAN-H) and 14 (CAN-L), 500 kbit/s, 11-bit
  identifiers, reaching the modules through the gateway (module 19).

### What the tool does

0. **Read and clear fault codes.** UDS `0x19` ReadDTCInformation on every
   module behind the gateway, then `0x14` ClearDiagnosticInformation. Clearing
   wipes the stored record, including the freeze-frame data (the conditions
   when the fault was set), and that is the evidence for diagnosing anything
   that comes back. So the tool saves the full read to a file before it
   clears, the same way it backs up coding before a write.
1. **Disable alarm interior monitoring permanently.** Module 09, Central
   Electronics, adaptation group "DWA / Anti-theft alarm system". The
   community reference is parameter IDE04928, "Anti-theft protection –
   Anti-theft alarm system", from a SeatCupra forum thread. The security
   access login for 09 adaptations is reported as 31347 on a Golf 7 —
   **unverified for the Touran 5T**. How a five-digit login becomes a UDS
   SecurityAccess (`0x27`) exchange is a separate open question.
   vibesODB2 records that sending it as a two-byte key is wrong and risks
   locking the module out. The perimeter alarm (doors, bonnet,
   boot) stays armed; only interior monitoring and, ideally, the tilt sensor
   go off.
2. **Start-stop: last-mode memory, or permanently off.** Last-mode memory is
   preferred, because it keeps start-stop available and only stops it from
   coming back on by itself. Community documentation puts the setting in the
   gateway (19) on some MQB cars and in 09 on others. Not looked up for this
   car yet, nor whether its gateway offers a last-mode option at all.
3. **Service interval.** Module 17, Instrument cluster, adaptation. This
   covers two things:
   - switching the interval from LongLife to fixed (15 000 km / 1 year);
   - resetting the service reminder after an oil change.

   No public DID found for either yet, so both have to be discovered.
4. **Battery registration.** Module 61, Battery regulation, according to
   community documentation for MQB cars; not checked on this car. The battery
   monitoring control unit (J367, on the negative terminal) estimates how worn
   the battery is, and the energy management decides charging and start-stop
   availability from that estimate. Registration is an adaptation that writes
   the new battery's identification, and that write is what resets the
   estimate. Reported by the community and unverified: an unregistered new
   battery is charged as if it were the old one, and start-stop is held back.
   So this item is tied to item 2 — a start-stop that stops working after a
   battery change may be this, not a coding fault.

### Safety rules

A module that accepts a wrong value does not report it as wrong; it simply
behaves differently, and on a car that can mean an alarm that never arms. So
the rules are the design rather than a footnote:

- The battery is fully charged before any write session. No charger is
  connected, so long DID scans with the ignition on are split across
  sessions rather than run until the battery sags.
- Read-only first (`0x22` ReadDataByIdentifier, `0x19` ReadDTCInformation).
  Writes (`0x2E` WriteDataByIdentifier, coding) only for DIDs that are fully
  understood.
- The original long coding (DID `0x0600`) and adaptation values are backed up
  before anything is written, and fault codes are saved before they are
  cleared.
- No write without a cross-check: the value read from the car has to match
  what the documentation says the default is. If it does not, the
  documentation is describing a different car.
- No flashing and no programming session (`0x10 0x02`).
- DID scans are rate-limited, and done from the default session where
  possible.

This is the same lesson [[subghz-collar-remote-clone]] paid for with a year
at 70%: replaying something not understood works until it does not, and then
there is nothing to debug against. There the cost was a missed beep. Here a
write is persistent, so "fully understood" comes before the first `0x2E`
rather than after the first failure.

### Discovery without a reference tool

No OBDeleven or VCDS is available to capture, so the DIDs and logins have to
come from the car and from public sources. There are three routes, and which
one fits each item is decided in Phase 2, not here:

- **Public long-coding bit maps.** Long coding is one DID (`0x0600`) holding
  a string of bytes, and community guides describe changes as "byte N, bit
  M". That is directly usable: read, flip the bit, write, read back. No
  proprietary data is involved.
- **Public adaptation names.** Guides name adaptation channels (IDE04928) by
  labels from VW's own data files. A name is only usable once some public
  source gives the raw DID behind it (mqbcan does for some), or one of the
  read-only routes below finds it.
- **Read-only DID scans of my own modules.** One variant reads every DID
  before and after a change made through the infotainment menu and diffs the
  two. It only finds what the menu can change. The other searches a scan for
  a value I already know, one shown on the cluster or printed on a part. A
  DID is 16-bit, so a full scan is up to 65 536 reads per module.

One route is rejected, unverified: sniffing at the OBD port while pressing
buttons or using menus. On MQB the gateway (19) is reported not to forward
internal bus traffic to the OBD port, which stays silent unless a tester
talks to it. Even behind the gateway, a button press is an ordinary
application frame, not UDS, so it shows how the button is signalled, not
where the setting is stored. Phase 1's first `candump` on the OBD port
checks the first half.

### Per-car profiles

More cars are expected after v1, so the per-car knowledge lives in a data file
for each car rather than in the code. That covers module addresses,
request/response CAN IDs, DIDs and login codes. The code knows UDS; the profile
knows the car. v1 has exactly one profile.

What the later cars are expected to be, all unverified until each one's own
bring-up:

| Car | Platform | Expected protocol |
| --- | --- | --- |
| Touran 5T 2018 | MQB | UDS on CAN, pre-SFD |
| Škoda Kodiaq 2017 | MQB | UDS on CAN, pre-SFD |
| Škoda Fabia III 2017 | PQ26, with MQB-derived electronics | Probably UDS — to verify first |

A profile is only as good as the discovery behind it. A DID that works on the
Touran is not assumed for the Kodiaq: each car gets its own read-only
bring-up and its own discovery before anything is written to it.

### Hardware — BeagleBone Green DCAN

The BeagleBone Green's AM335x has two on-chip CAN controllers. TI calls them
DCAN, and the mainline Linux driver is `c_can`. A controller does the
bit-level work of a CAN node in hardware: bit timing, arbitration,
acknowledgement and error counting. What the board lacks is the physical
layer, so it needs:

- **A 3.3 V transceiver breakout** (SN65HVD230 or similar). It turns the
  controller's 3.3 V TX/RX logic into the CAN-H/CAN-L differential pair. Two
  traps come with it:
  - The common cheap "CAN module" is an MCP2515 with a TJA1050. That is a
    second controller plus a 5 V transceiver, and its 5 V RX output can
    damage a 3.3 V pin.
  - Breakouts usually have a 120 Ω termination resistor fitted. The car's bus
    is already terminated at both ends, so it comes off.
- **Pinmux.** The header pins are switched from their default function to
  DCAN. The stock BeagleBoard.org images are believed to ship a prebuilt
  `BB-CAN1` overlay, enabled by one line in `uEnv.txt` (unverified on my
  board's image). The fallback is my own devicetree in a Yocto image, which
  is the same work as [[embedded-linux-course]].
- **An OBD-II pigtail** to the transceiver (pins 6, 14 and ground).

The application runs on the BeagleBone itself: Python, udsoncan, can-utils
and the backups all live on the board. That follows from what Linux offers.
A CAN interface cannot be handed to another machine the way USB passthrough
hands over a device, and tunnelling it (`socketcand`, `cannelloni`) adds a
layer for nothing. Power comes from the terminal side's USB port. Running it
from the car's 12 V would need a step-down converter, and that is not in v1.

The link to the board is SSH over USB networking. The stock images present
the board to the laptop as a USB Ethernet device, which is a point-to-point
link with no router and no internet, so it works offline in a parking lot.
The same link carries `scp` for copying backups off the board, and a capture
piped into Wireshark on the laptop.

Two options lost:

- **A serial console**, either as a USB serial device over the same cable or
  on the debug UART header with a 3.3 V USB-UART cable. It gives a shell and
  nothing else, so moving backup files off the board would need another
  route.
- **Wi-Fi to a phone hotspot.** The board has none; that is the BeagleBone
  Green *Wireless*.

Candidates that lost:

- **CANable / candleLight** — a USB-CAN adapter running `gs_usb` firmware,
  which appears as `can0` with no setup. It cost 15–30 € more for hardware.
  On this macOS laptop it would also have needed a Linux VM with the adapter
  passed through over USB, because SocketCAN, the kernel ISO-TP module and
  can-utils exist only on Linux. The BeagleBone is already owned, and this
  project's reuse is too uncertain to justify buying anything that isn't
  needed.
- **ELM327 dongles** — the cheap OBD sticks. They run a command interpreter
  that gives OBD-style request/response with small buffers, not raw CAN. They
  cannot reliably show the whole bus and do not appear as `can0`, which rules
  out can-utils and the scans in Phase 2.
- **ESP32 + CAN transceiver** running Switchleg1/esp32-isotp-ble-bridge
  (ISO-TP over BLE). That only makes sense for a phone variant, which is out
  of scope. It is also not a SocketCAN interface, so none of the can-utils
  tooling would work on the car side.

### Open questions

- The exact request/response CAN IDs for modules 09, 17, 19 and 61 on this
  car.
- The security access method and level for writes to 09, 17, 19 and 61 on a
  Touran 5T.
- The DID or DIDs behind DWA interior monitoring and the tilt sensor
  adaptation.
- Which module holds the start-stop setting on this car, and whether a
  last-mode option exists or only permanent off.
- The DIDs for the service interval mode (LongLife against fixed) and for the
  service reset in 17.
- The battery registration DIDs in 61. Also whether a replacement with a
  different capacity or technology (EFB against AGM) needs a coding change,
  not just the identification adaptation.
- Whether the BeagleBone's image has a kernel with `CAN_ISOTP` (5.10 or
  newer) and the `BB-CAN1` overlay, or whether this needs a Yocto image.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Host and bus access | BeagleBone Green, DCAN + 3.3 V transceiver | `c_can`, appears as `can0`; runs the tool |
| Terminal | Laptop over USB | SSH over USB networking |
| Bus tooling | can-utils — `candump`, `isotpdump`, `cansniffer` | `candump -l` for logs worth keeping |
| Transport | Kernel ISO-TP module (5.10+) | `CAN_ISOTP` sockets |
| Analysis | Wireshark on the laptop | Capture taken on the board; decodes ISO-TP and UDS |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| BeagleBone Green | 0 € — already owned |
| 3.3 V CAN transceiver breakout (SN65HVD230 or similar) | ~3 € |
| OBD-II pigtail | ~5 € |

Roughly 8 €. That is the comparison that matters: a VCDS interface is
200–400 €, and OBDeleven's write functions are a subscription. The later cars
add no hardware.

## Software / firmware

- On the BeagleBone: Linux SocketCAN, the kernel ISO-TP module and
  can-utils. The stock Debian image first, a Yocto image if its kernel or
  overlays fall short.
- Python: python-can, can-isotp, udsoncan.
- A CLI on udsoncan with `backup`, `read-dtc`, `clear-dtc`, `read-did`,
  `write-did`, `read-coding`, `write-coding`, `service-reset` and
  `battery-register`. Every write sits behind a
  mandatory backup, a confirm prompt and a read afterwards to verify it.
- One profile file per car, selected by VIN, holding everything car-specific.

The code goes in its own public repository. Captures, scans and backups
carry the VIN and the car's coding, so they live in that repository
sops-encrypted, and never in this vault. That is the same problem
[[subghz-collar-remote-clone]] solved with sops and a commit hook. The repo
does not exist yet; its directory name goes into this note's `repo:` field
once it does.

Prior art, read as reference rather than used as the tool:

- orviwan/vibesODB2 — see "Has it been done already?" above. Its write
  path and its removed-features record are both worth reading before the
  first write. It also publishes the CAN IDs it uses for 09 and 17, which is
  a cross-check for Phase 1, not a substitute for it.
- caringcaribou — a CAN security toolkit whose UDS module discovers ECUs
  and dumps DIDs. Prior art for the Phase 2 scans.
- jrjoaoramos/mqbcan — MQB CAN analysis; documents reading and writing long
  coding and adaptations with and without security access (Leon 5F, applies
  to MQB).
- bluetoothbeijing/MQB-sniffer — a Golf 7 sniffing log taken with OBDeleven
  and an MCP2515 through a splitter. Someone else's capture of a real tool's
  sequences, which is as close to a reference as this project gets.
- bri3d/VW_Flash — a Python VAG UDS stack, flashing-focused, useful for how
  it structures sessions and security access.
- pylessard/python-udsoncan — the UDS implementation (MIT).
- LateAlways/mibwiki-mirror — a public list of MQB security access codes per
  module, 31347 among those for 09.
- MartijnD92/PyVCDS — **not applicable**: VW TP 2.0 and KWP2000 for older
  cars, not UDS. It would have been the reference for the Passat, which is
  out of scope.
- The SeatCupra forum thread "code out interior monitoring" — the DWA
  adaptation in module 09.

## Plan

**Phase 1 — Bring-up on the Touran (read-only)**

- [ ] Wire a 3.3 V CAN transceiver to the BeagleBone Green's DCAN pins, termination removed
- [ ] Enable DCAN pinmux and confirm a kernel with CAN_ISOTP (stock overlay, or own Yocto image)
- [ ] Get can0 working at 500k
- [ ] Enumerate modules behind the gateway, identify request/response CAN IDs for 09, 17, 19 and 61
- [ ] Read fault codes (0x19) from every module
- [ ] Read identification DIDs (part number, SW version) and long coding (0x0600) of 09, 17, 19 and 61; store backups

**Phase 2 — Discovery on the Touran**

- [ ] Check with `candump` whether the OBD port carries any traffic without a tester
- [ ] Map each target change to a discovery route: long-coding bit map, published DID, menu diff, or known-value search
- [ ] Baseline DID scan (0x22) of 09, 17, 19 and 61, rate-limited, stored with the backups
- [ ] Find the DID or coding bit for each change, and the security access needed to write it
- [ ] Cross-check each value read from the car against its documented default

**Phase 3 — Implementation (v1)**

- [ ] CLI tool on udsoncan: `backup`, `read-dtc`, `clear-dtc`, `read-did`, `write-did`, `read-coding`, `write-coding`, `service-reset`, `battery-register`
- [ ] Per-car profile file, with the Touran 5T as the only profile
- [ ] Mandatory backup + confirm prompt + verify-after-write; fault codes saved before every clear
- [ ] Apply change 1 (interior monitoring), test alarm behavior with dog/boot, verify perimeter still armed
- [ ] Apply change 2 (start-stop), verify the state survives ignition off and on
- [ ] Apply change 3 (fixed service interval), verify in cluster
- [ ] Reset the service reminder from the tool after an oil change, verify in cluster
- [ ] Register a replacement battery from the tool, verify by reading the adaptation back

**Phase 4 — Other family cars**

- [ ] Kodiaq 2017: confirm UDS and a pre-SFD gateway, read-only bring-up, own discovery, own profile
- [ ] Fabia III 2017: confirm the protocol first, then read-only bring-up, own discovery, own profile

**Phase 5 — Optional**

- [ ] Publish findings (DIDs, sequences) for Touran 5T

## Build log

Session entries live in [[vag-uds-coding-tool-log]].
