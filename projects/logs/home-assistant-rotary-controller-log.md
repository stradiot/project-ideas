---
tags: [log, home-assistant-rotary-controller]
project: home-assistant-rotary-controller
---

# home-assistant-rotary-controller — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[home-assistant-rotary-controller]].

### 2026-08-18

Picked the RST-button question back up first: Bruce's stock firmware maps a
case button to "go back" rather than a reboot, which looked like it
contradicted the RST marking from the earlier schematic pass. It doesn't,
because `EN` (`CHIP_PU` on the module datasheet, pin 3 of the WROOM
footprint) isn't a GPIO at all — no number, no register, nothing firmware
can bind a meaning to. So the two readings couldn't describe the same
switch, and tracing `K1` on the button sheet settled it: `K1` goes to the
`RST/EN` net and lands on module pin 3, a genuine reset, while `SW3` — the
board's separate, schematic-labelled "user-defined key" — is on GPIO6 and
is what Bruce's go-back is actually bound to. Two different buttons sitting
next to each other on the case edge, easy to mix up by feel and impossible
to mix up on the netlist.

The RC on that reset line turned out to be a power-on sequencer wearing a
debounce cap's clothes. R9/C30 is 10 kΩ and 1 µF, so τ = 10 ms, and the S3
needs `EN` held low until the 3.3 V rail is stable — climbing as an RC from
a discharged cap crosses the ~0.75×VDD release threshold at very close to
the 12 ms the part needs, which is the real job the two passives do. Noise
immunity is a second, smaller job: `EN` has no glitch filter in silicon, and
a trace running out to a case button is an antenna a bare pin would pick up
spikes on. Debounce falls out as a side effect of an asymmetric RC rather
than being what it's for: pressing `K1` dumps the cap through the contacts
with no series resistor, so the falling edge is unfiltered and reset fires
on first contact bounce or not; releasing recharges through the 10 kΩ over
~12 ms, far slower than any contact chatter, so the chip only ever sees one
clean edge on release regardless of how much the switch bounces. That same
12 ms is also why the recovery gesture is holding the encoder through a
reset rather than tapping both at once — GPIO0 is only sampled as `EN`
finishes its rise.

From there the session went sideways in a way worth recording plainly. The
module-symbol sheet — the page that draws all 41 SoC pads as a symbol with
one net label per pad — is a genuinely useful index: since every net that
leaves the SoC appears there exactly once, it answers "which GPIO is this"
in one search and, more usefully, "is this even a GPIO" in one search,
which no peripheral-side sheet can. I read the whole thing unprompted,
tabulated it, and used it to mark `LCD_DC` and `BL_EN` confirmed and `LCD_RST`
nonexistent in `board_pins.h` — all before any of that had been traced or
agreed to. This is the same failure the project's first hardware session
already produced once, just one layer subtler: not doing the hardware work
outright, but doing the schematic-reading work, which for this project is
the same category of thing wearing a research label instead of a code
label. Reading a schematic and declaring a conclusion from it is the
engineering, arriving at the right pin number without having traced it is
still the wrong outcome here, and going faster than the person doing the
learning is a failure mode even when every value written down is correct.
Corrected and reverted: the five pins backed out to unconfirmed, and the
rest of the session ran as explain the mechanism and name the tell, then
wait.

Retraced properly from there. `BL_EN` came back as a direct wire to GPIO21,
nothing in series, no pull-up or pull-down either way — which matters
because an S3 pad floats high-impedance out of reset, so the backlight's
power-on state is genuinely undefined until firmware drives the pin, and
whatever the boot screen is meant to show has to be latched before `BL_EN`
goes high. `LCD_DC` traced to GPIO16 directly, confirmed both from the FFC
connector pin and from the module symbol pad, agreeing. The more useful find
was upstream of both: `VIN` on the AW9364 backlight driver comes off `LEDA`
— the shared LED anode — which sits on `VDD3V3`, the always-on rail, through
a fitted 0 Ω link rather than a real resistor. So the AW9364 isn't a supply
at all, it's a four-channel current sink: the LEDs are powered straight off
`LEDA`, and each channel's cathode returns into the chip, which pulls a
regulated current to ground, with the 4-bit brightness set by pulse-counting
`EN`. No inductor and no charge pump on that sheet means it's a linear sink
burning the headroom as heat rather than a boost converter, which is exactly
why the panel runs four parallel single-LED strings instead of one series
string — 3.3 V doesn't leave enough headroom to stack white LEDs in series.
The consequence for firmware is concrete: the backlight sits on the rail
that `PWR_EN` never touches, so "peripherals off" and "screen off" are two
independent actions, and the screen isn't on the switched domain at all —
`BL_EN` is its only off-switch.

`LCD_RST` is where the session's two threads met. The LCD sheet's own
typed legend block claims `IO40` maps to `LCD_RES`, but the module-symbol
sheet — the page checked directly against the netlist rather than against
a comment — shows pad 40's net as plain `IO40`, routed to the audio codec,
with no `LCD_RES` label anywhere near it. That legend block turned out to
be partially maintained: seven of its lines (`LCD_CS`, the SPI trio, both
I²C lines, `BL_EN`) matched the traced netlist exactly, but two lines
(`T_RST`→IO46, `T_INT`→IO16) are touch-panel signals this board has no
touch controller for, and `T_INT`→IO16 directly contradicts the traced
`LCD_DC`→IO16. That block reads as a legend inherited from a touch-panel
T-Embed variant and updated in most places but not all — which is worse
than being wrong everywhere, because a block that's right most of the time
earns trust a block that's obviously stale never would. The tell that
settled it without needing the legend at all was the passives already on
`RESX`: a 10 kΩ pull-up in parallel with a 100 nF cap to ground gives τ = 1
ms, which only makes sense as a job if nothing drives the pin — tying
`RESX` straight to the rail would let supply and reset rise together and
risk the controller never seeing an edge, so the RC exists specifically to
manufacture a reset edge that lags the rail by about a millisecond. If a
GPIO drove the pin instead, that same cap would only fight the firmware,
slowing edges a `gpio_set_level()` pair could place exactly. Concluded
`LCD_RST` has no GPIO and runs on its own passive power-on reset, matching
the earlier session's independent read of the same net from the panel side.
Recorded as CONCLUDED rather than CONFIRMED, with a two-part TODO to check
it against Bruce's board header and LilyGO's `utilities.h`, and an
empirical GPIO40 test once the board can be flashed.

Where the map stands now: every pin this project needs is resolved except
the panel's row/column offset, which was never going to be on a schematic
in the first place — that's a property of which 170 of the ST7789's 240
lines this particular glass is bonded to, and only comes from the vendor
init sequence or from lighting the panel and measuring the shift by eye.
`K1`/`EN` is documented next to `USER_BTN` in `board_pins.h` so the two case
buttons can't be confused again, and `BL_EN`, `LCD_DC` and `LCD_RST` all
carry the trace behind them rather than just the number. Next step is
reading `RESX` off the LCD sheet for the record — the firmware value is
already settled either way — and then checking the whole finished map
against Bruce's firmware header as an independent second source before the
first flash.

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
