---
tags: [project, embedded, arm, bare-metal]
status: idea
depends: []
created: 2026-08-07
---

# Bare-metal Bootloader from Scratch

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Understand exactly what happens between power-on and `main()` — by writing
every step of it myself, then turning that knowledge into a bootloader that
can flash new firmware over a serial line.

Deliberately out of scope: vendor HAL, CMSIS startup files, any SDK. That
is the entire point.

## Learning value

- Reset handler, vector table, linker script, memory map
- What the startup code in every vendor SDK is actually doing
- Flash writing from running code, and jumping into a second image

## Practical value

None, and it would be dishonest to claim otherwise. Every MCU ecosystem
already ships a bootloader better than this one will be, MCUboot is free
and audited, and nothing else in the vault is going to depend on the
artifact this produces.

What it produces instead is the ability to read a linker script without
flinching and to know what the SDK startup file was doing all along —
which turns up in every firmware project here, none of which would teach
it, because using a bootloader teaches nothing about writing one.

## Architecture

### Phase 1 — Startup by hand

No standard libraries. In ARM assembly and plain C:

- Vector table at the right address, with the initial stack pointer and the
  reset handler as the first two entries
- Reset handler: copy `.data` from Flash to RAM, zero `.bss`, set up the
  stack, call `main`
- Linker script defining Flash and RAM regions and the section symbols the
  startup code relies on

### Phase 2 — The bootloader itself

| Step | Behaviour |
| --- | --- |
| Boot | Initialise clocks and UART |
| Prompt | Print a banner, wait a few seconds for input |
| Timeout | No input → jump straight to the application image |
| Update | Input → receive a binary over XMODEM, write it to the app region |
| Jump | Set VTOR to the app vector table, load its stack pointer, jump |

Flash is split into two regions: bootloader at the reset vector, application
higher up. The application is built with its own linker script that places
it at the application base address.

### Failure modes to handle

- Power loss mid-write — the application region is invalid, and the
  bootloader has to notice rather than jump into garbage
- Simple integrity check (CRC or magic word) before jumping
- Never let the update path overwrite the bootloader itself

### Phase 3 — A/B slots and rollback

A single application region means a bad image bricks the board until a
programmer is attached. That is the difference between an exercise and
something I would actually deploy, so it gets fixed:

| Element | Behaviour |
| --- | --- |
| Two slots | New image is written to the inactive slot; the running one is never touched |
| Trial boot | After an update, the new slot is marked "on trial" and booted once |
| Confirmation | The application sets a confirmed flag once it is healthy |
| Rollback | Reboot without confirmation → the bootloader reverts to the previous slot |

The cost is flash: two application slots plus the bootloader. On a small
part that is the real constraint, and deciding whether to pay it is part of
the exercise.

### Where to stop

Writing this from scratch is worth doing once, for the understanding.
Deploying it forever is not — for anything nRF-based, MCUboot already does
all of the above, signed, with a much larger set of eyes on it. The honest
plan is to build this one, then use MCUboot on [[ble-sensor-node-pcb]] and
[[thread-matter-growbox]] knowing exactly what it is doing.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| MCU | STM32 / any Cortex-M board | Something with a datasheet worth reading |
| Toolchain | `arm-none-eabi-gcc`, plain Makefile | No IDE, no code generator |
| Debug | ST-Link + OpenOCD/GDB | Only for developing the bootloader itself |
| Transfer | `sx` / minicom XMODEM | Host side of the update path |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Cortex-M dev board | 10–25 € |
| USB-UART converter | 5–10 € |
| ST-Link clone (if not already owned) | 5–10 € |

## Software / firmware

- `startup.s` — vector table and reset handler
- `linker.ld` — memory regions and section placement, one per image
- Bootloader in C: UART, XMODEM receiver, flash driver, jump logic
- Slot metadata in flash — which slot is active, which is on trial, CRCs
- Trivial application image (blink at a distinctive rate) to prove the jump

## Plan

- [ ] Blink with no SDK — startup code and linker script written by hand
- [ ] Verify `.data` and `.bss` handling with an initialised global
- [ ] UART output, then UART input
- [ ] Flash erase/write driver, tested on a scratch page
- [ ] XMODEM receive into RAM, then into flash
- [ ] Jump into the application, confirm interrupts work there (VTOR)
- [ ] Integrity check and the "no valid app" path
- [ ] A/B slots, trial boot and confirmation flag
- [ ] Flash a deliberately broken image, watch it roll back on its own

Result: my own firmware update mechanism, no external programmer needed
after the first flash.

Its first real user is [[rc-car-custom-controller]] — same Cortex-M, and the
telemetry UART it already carries is the transport, so nothing new gets
wired. PID tuning is an iterate-twenty-times loop where reconnecting a
programmer is genuine friction, and a failed update there rolls a car to a
stop. That makes it the safe place to prove rollback actually works before
[[custom-flight-controller-drone]] inherits the same code on something that
falls out of the air.

Not the pocket console, which is an ESP32: no VTOR, no ARM vector table, and
ESP-IDF ships its own second-stage bootloader and OTA scheme. Nothing here
runs on Xtensa. What that project takes from this one is knowing what an A/B
update mechanism is doing underneath, which is the same thing
[[thread-matter-growbox]] takes from it before trusting MCUboot with a
sealed box.

## Build log

Session entries live in [[bare-metal-bootloader-log]].
