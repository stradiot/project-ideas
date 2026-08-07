---
tags: [project, embedded, arm, bare-metal]
status: idea
created: 2026-08-07
---

# Bare-metal Bootloader from Scratch

## Goal

Understand exactly what happens between power-on and `main()` — by writing
every step of it myself, then turning that knowledge into a bootloader that
can flash new firmware over a serial line.

Learning goals:
- Reset handler, vector table, linker script, memory map
- What the startup code in every vendor SDK is actually doing
- Flash writing from running code, and jumping into a second image

Deliberately out of scope: vendor HAL, CMSIS startup files, any SDK. That
is the entire point.

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
- Trivial application image (blink at a distinctive rate) to prove the jump

## Next steps

- [ ] Blink with no SDK — startup code and linker script written by hand
- [ ] Verify `.data` and `.bss` handling with an initialised global
- [ ] UART output, then UART input
- [ ] Flash erase/write driver, tested on a scratch page
- [ ] XMODEM receive into RAM, then into flash
- [ ] Jump into the application, confirm interrupts work there (VTOR)
- [ ] Integrity check and the "no valid app" path

Result: my own firmware update mechanism, no external programmer needed
after the first flash. Directly useful for [[freertos-pocket-console]] and
any custom board.

## Build log
