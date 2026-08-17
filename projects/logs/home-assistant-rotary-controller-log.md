---
tags: [log, home-assistant-rotary-controller]
project: home-assistant-rotary-controller
---

# home-assistant-rotary-controller — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[home-assistant-rotary-controller]].

### 2026-08-17

Picked the schematic back up where the last session stopped, on the four
pins still unread: `PWR_EN`, and the LCD backlight-enable, DC and reset
trio. Only got through `PWR_EN` this session, but tracing that one net
pulled in the whole power tree, and untangling it took most of the time.

The first thing that didn't make sense was USB routing through the charger
IC (a BQ25896) instead of straight to a regulator. The naive wiring —
USB and battery diode-ORed onto one rail — breaks four ways: the rail swings
5V on USB down to 3V on battery with nothing downstream able to ignore that;
charge-termination current becomes unmeasurable once system load shares the
same wire; a flat cell clamps the rail and refuses to boot on USB; and
nothing enforces the current limit a USB host actually negotiates. The
BQ25896 is a power-path controller before it is a charger: it holds the
system rail (`VSYS`) at a floor voltage a little above the battery, feeds it
from USB when USB is present and only diverts the surplus into the cell, and
switches to drawing from the battery the instant USB drops, with no
brownout. That floor is a voltage floor, not a power budget, which answers
what I'd assumed was a real risk — that a Wi-Fi TX burst would starve
against some allocated minimum. Peaks are covered by "supplement mode": the
battery FET conducts backwards and the cell plus the bulk capacitors supply
the transient while the input only has to cover the average. The corollary
worth keeping is that a board like this is least stable on USB with the
battery removed, since nothing but the caps is left to absorb a peak, and
that failure looks exactly like a firmware brownout bug.

Two LDOs downstream of `VSYS` turned out to be the switch that actually
matters for firmware. I first guessed `PWR_EN` was a soft-latch — the SoC
enabling its own supply — but the LDO's part number (ME6217, active-high
chip-enable, no internal pull-up) rules that out: a chip cannot enable the
rail that powers it. Getting the two LDOs' output net names settled it —
one (`U12`) is hardwired always-on and feeds `VDD3V3`, which is what the S3
module itself sits on; the other (`U2`) is gated by `PWR_EN` (GPIO15) and
feeds a second rail, `VCC3V3`, which the audio amp, the CC1101, the IR
receiver and the RGB LED sit on. The two names differ by one letter and mean
opposite things, which is exactly the kind of misreading that costs an
afternoon later. The pattern behind the split isn't importance, it's whether
a part can turn itself off in software: everything on `VDD3V3` has some kind
of sleep or power-down command of its own (the LCD controller, the SD card,
the NFC reader, the microphone, the encoder — passive contacts anyway), and
everything on `VCC3V3` doesn't — an IR receiver is a live analog demodulator
with no register interface, an addressable LED idles its controller even
showing black. `PWR_EN` exists because those parts have no other way off.

That split has a real firmware consequence: `PWR_EN` has to go high, and the
rail has to settle, before any SPI or GPIO traffic reaches a peripheral on
`VCC3V3` — not merely before the first real transaction. An SPI master has
no way to know whether anything is listening; it clocks bits out and reports
success regardless, so a chip that's simply unpowered looks indistinguishable
from a wrong pin number. Worse, driving a peripheral's input pins while its
rail is at 0V pushes current into the chip through its own ESD clamp diodes
(back-powering) — the safe direction is only ever "rail up first."

Also confirmed `USER_BTN` and both I2C lines while on those sheets, plus
caught something the last session's UI premise didn't account for: there's
a fourth physical control on the board (`SW3`, the user key) beyond the
knob and the RST/PWR buttons on the case, which contradicts the project's
"one knob, one button" framing and needs a decision, not more tracing.
Corrected the AO3400's on-resistance in `board_pins.h` from ~10 mΩ to the
right ~26 mΩ while I was at it. Board pin count: 13 of 16 confirmed, up
from 9. `BOARD_LCD_BL_EN`, `BOARD_LCD_DC`, `BOARD_LCD_RST` and the panel
offsets are what's left.

With the pin work paused there, I turned to something the session surfaced
rather than caused: I have a real gap in reading PCB schematics and in the
basic electronics underneath them, and it's worth its own course material
rather than being picked up piecemeal project by project. Wrote
`notes/reading-a-schematic.md` in the vault to hold it — the net-label
model (a schematic carries connectivity in text labels, not drawn wires,
so finding a net means text-searching its label from the peripheral end to
the module-symbol end), the dashed-box idiom (two footprints on one node,
one populated and one left `NC`, is how a board records "decided at
assembly time" — misreading `NC` as connected inverts the whole story), and
a second half on pin-mux architectures, since the three families I actually
own hardware for — none (ATmega328P), a fixed alternate-function table
(the S3's crossbar cousin, and BeagleBone/STM32-style parts), and a full
crossbar (the ESP32-S3 itself) — are a real spread. Placed the note as a
prerequisite ahead of the five courses in the embedded curriculum rather
than folding it into any one of them, since all five assume the skill and
none of them teach it, and extended its exercises into a board ladder
across the Arduino clone, an ESP32 devkit, the C3/C6, this board and the
BeagleBone Green, ordered by how much each one hides.

Next step is the LCD sheet for the three remaining pins, then checking the
finished map against Bruce's firmware header as an independent second
source before the first flash.

### 2026-08-16

First session with the board actually on the desk. Home Assistant was already
up at `homeassistant.local` (`192.168.100.10:8123`), and the chip enumerated
over USB as Espressif's own **USB Serial/JTAG** peripheral rather than a
CH340/CP210x bridge — meaning the ESP32-S3 does its own USB-to-download-mode
handling in silicon, with no separate converter chip on the board. That
detail turns out to matter later.

Toolchain first: ESP-IDF v5.5.5, not the newer v6.0.2 tag. v6.0 dropped
deprecated APIs and shifted defaults, and essentially every T-Embed example
and the LVGL glue components target the 5.x API, so 6.0 would mean debugging
IDF's port layer instead of the actual board. Installed to `~/esp/esp-idf`.
`esptool.py flash_id` against the running board confirmed the module is an
`ESP32-S3-WROOM-1U-N16R8`: an ESP32-S3 with 8 MB of PSRAM bonded into the
same package (the R8) and 16 MB of flash on the module PCB (the N16). Before
touching anything else, took a full 16 MB factory dump of the board's
current firmware (Bruce) — read-only, and it now lives outside the repo with
its sha256 recorded, so there's a way back to stock if anything later
bricks it. Then built (not flashed) a stage-2 firmware that touches no GPIO
at all — it only reads back `esp_chip_info` and prints it — on the reasoning
that a build like that can only fail for toolchain or target-config reasons,
which separates "the toolchain works" from "my pin numbers are right" before
either gets tested together.

I ran all of that autonomously — cloned the SDK, wrote the skeleton, kicked
off the backup and the build — while waiting on a Home Assistant access
token. That was the wrong call. This project's whole premise is doing the
engineering personally rather than watching it happen, and board discovery
is exactly the engineering in question. Got stopped and corrected partway
through the backup: the working agreement from here is that mechanism gets
explained and the command gets handed over with what to look for, hardware
gets operated by hand, and code only gets written once a decision has
actually been made. Blanked `main/board_pins.h` back down to guesses marked
`/* unconfirmed */`, to be replaced one at a time as each pin was actually
confirmed rather than assumed.

Confirming an ESP32 pin map is a real discovery problem, not a lookup,
because the S3 has a GPIO matrix — a crossbar that can route almost any
peripheral signal to almost any pad by register, unlike an STM32's fixed
alternate-function table. So which pin drives the LCD chip-select is a fact
about how LilyGO routed the copper, not about the chip, and only the
schematic (or the running board) can answer it. Went through the vendor PDF
net by net. The clock line landed the interesting way: `SPI_SCK` is on
GPIO11, which is the MOSI slot in the S3's IO_MUX direct-routing table, not
the CLK slot (GPIO12). Since the IDF docs say a shared SPI bus routes
entirely through the crossbar the moment even one of its signals isn't on
its IO_MUX-direct pin, this bus is capped at ~40 MHz rather than the ~80 MHz
IO_MUX-direct ceiling. Ran the arithmetic rather than guessing whether that
matters: 320×170 at 16 bpp is 870,400 bits per full frame, giving a ~46 fps
ceiling at 40 MHz — plenty for a knob-driven UI that mostly redraws small
regions, so the constraint is real but not a problem here.

The backlight turned up a genuine trap. `BL_EN` doesn't drive the panel
directly — it goes through an AW9364, a four-channel LED driver that reads
*pulse count* on its enable pin as a 4-bit brightness command rather than
taking a PWM duty cycle. Put ordinary `ledc` PWM on that pin later and every
pulse edge would get counted as a dimming step, producing brightness that
looks like a hardware fault. Display sleep/dimming has to bit-bang pulses
with gaps under 500 µs instead.

Misread a ground symbol near the encoder's switch pin as a debounce
capacitor at first — corrected on a closer look at the schematic. There's no
RC filtering anywhere on the encoder: pins 1–3 get 10 kΩ pull-ups only, pin
4 is a shared ground return, and all debouncing is firmware's problem. The
encoder's push switch is also the board's only BOOT strap — there's no
separate button, because the WROOM-1U is a bare module with no built-in
buttons at all (that only exists on a devboard like the DevKitC); LilyGO
wired the encoder switch to GPIO0 and calls it BOOT in the schematic as an
annotation, not a second component. That works as a recovery path regardless
of what firmware is in flash, because GPIO0 is latched by mask ROM — code
burned into the silicon at fabrication — before a single instruction of
whatever's in flash ever runs.

Identified the "Lora" component in the schematic (labelled `HPD24A2`,
unsearchable as a part) as the CC1101 by its pin signature rather than its
label: four-wire SPI plus exactly two GPIOs named `IO0`/`IO2`, which is the
CC1101's GDO0/GDO2 pair, plus an antenna-band-switch pair that only a
multi-band sub-GHz part needs. The general technique — most SPI/I²C parts
answer an identifying register over the bus itself, `PARTNUM`/`VERSION` at
0x30/0x31 for the CC1101 — is the definitive check if the pin signature
ever isn't enough.

Nine of thirteen pins are now confirmed from the schematic rather than
guessed: encoder A/B/switch, SPI SCK/MOSI/MISO, LCD_CS, SD_CS, and the
CC1101's CS/GDO0/GDO2/SW0/SW1. Four remain to read off the PDF by hand:
`BOARD_PWR_EN`, `BOARD_LCD_BL_EN`, `BOARD_LCD_DC`, `BOARD_LCD_RST` — the
power latch is the one most worth getting right before any flashing, since a
wrong value there means the board runs fine on USB and only dies the first
time it's unplugged. ESP-IDF is installed and the no-GPIO build compiles
clean at 178 KB; nothing has been flashed yet, and the board is still
running its factory firmware. Next step is finishing those four pins by
hand, then deciding — by hand, not by having it decided for me — whether to
run the stage-2 flash test before writing any pin-touching code.
