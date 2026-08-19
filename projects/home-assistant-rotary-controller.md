---
tags: [project, hardware, embedded, esp32, home-assistant, ui]
status: idea
depends: []
created: 2026-08-07
repo: t-embed-ha-controller
github: https://github.com/stradiot/t-embed-ha-controller
---

# Home Assistant Rotary Controller

## Now

The render-loop and message-model design (single task owns LVGL, fact
messages over commands, doorbell-plus-cache) got three decisions deep before
the spec question surfaced: none of it can be finished without knowing what
domains this device controls, what's on screen per domain, and how entities
get bound to Home Assistant. A 27-question requirements questionnaire exists
to answer that, organised into what the object is, the entity set, binding,
the one-knob-one-button model, the display fields, staleness handling, and
scope — going through it together is the next session, ahead of resuming the
render loop. `main.c` is still the stage-5 encoder jig; plan item one is
still open.

## Lessons

- **A message or data model designed before the requirements exist gets
  derived from implementation convenience, not need — and the tell is
  answering "fixed or variable length" before answering "what does the
  screen show".** Three plausible-looking decisions (ownership model over a
  lock, fact messages over commands, doorbell-plus-cache over inline
  payloads) all landed correctly in isolation, but the payload-length
  question underneath them turned out to depend on domain-specific HA
  attributes (`source_list`, `fan_modes`, `effect_list` — all
  variable-length string arrays) and on the entity-binding requirement
  itself, since binding by something other than a hardcoded `entity_id`
  makes the ID a piece of runtime string data. None of that is answerable
  without a written spec of what domains the device controls and what each
  screen shows. [[home-assistant-rotary-controller-log#2026-08-19]]
- **A periodic tick timer, not the render loop, is what actually blocks
  light sleep.** `esp_lvgl_port`'s task loop already blocks on a FreeRTOS
  event group and wakes on input rather than polling — that part is fine.
  What isn't is its 5 ms periodic `esp_timer` pushing `lv_tick_inc()`
  forever: FreeRTOS tickless idle only engages once the idle task can prove
  a run of `CONFIG_FREERTOS_IDLE_TIME_BEFORE_SLEEP` ticks (3, i.e. 30 ms at
  100 Hz) with nothing pending, and a timer due in 5 ms caps the provable
  window below that unconditionally — not degraded sleep, no sleep at all.
  LVGL 9's `lv_tick_set_cb()` (pull: LVGL asks for elapsed time via
  `esp_timer_get_time()`, a counter already running) removes the wake
  source instead of requiring it to be stopped and remembered later.
  [[home-assistant-rotary-controller-log#2026-08-19]]
- **`esp_lcd_panel_draw_bitmap()` queues a DMA transaction and returns; it
  only blocks once the transaction-queue pool is exhausted.** Reusing one
  shared strip buffer for the next draw before the previous DMA transfer has
  finished reading it corrupts whatever is still in flight — and the damage
  shows up as doubled edges and truncated regions at strip boundaries, which
  reads exactly like a row-offset or geometry bug rather than a timing one.
  The fix is waiting on the `on_color_trans_done` callback (a semaphore is
  enough for a test pattern; LVGL's own double-buffer-plus-flush-callback
  exists to solve the same problem for real UI). Cost most of a session
  before the cause separated from the genuine geometry measurement running
  in parallel. [[home-assistant-rotary-controller-log#2026-08-19]]
- **A rotary encoder needs no debounce because its value is an integral of
  change, not an instantaneous state — and the cancellation is exact
  arithmetic, not a statistical tendency.** A button's reading *is* its
  current level, so a bounce burst is indistinguishable from repeated
  presses and can only be removed by waiting out time. A quadrature
  decoder's count only changes by +1/-1 pairs during contact chatter on one
  line while the other holds steady, so those pairs cancel regardless of how
  long the bounce lasts or how it's sampled — measured directly on this
  encoder as 780 raw edges, 522 net counts, 258 cancelled, against exactly
  261 genuine edges per line. The one thing this guarantees is that the
  *sum* is right, not that the *sequence* is glitch-free — a poll that lands
  mid-burst reads a value strictly between the pre- and post-transition
  counts, never a wrong one, so it can only appear stale for up to one poll
  period, never spuriously reversed. [[home-assistant-rotary-controller-log#2026-08-19]]
- **A vendor schematic's typed annotation blocks are documentation, not
  netlist, and a partially-updated one is more dangerous than a wholly wrong
  one.** Only symbols, wires and net labels carry real connectivity in the
  EDA tool; a legend box of hyphens-and-arrows has none, so it can claim two
  nets are the same without making them so, and nothing checks it the way
  DRC checks the netlist. On the LCD sheet the legend was right about seven
  of ten lines — matching the traced `LCD_CS`, SPI trio, I²C pair and
  `BL_EN` exactly — which is what made the two wrong ones (leftover
  touch-panel signals from a different T-Embed variant, one of them
  contradicting the traced `LCD_DC`) worth believing until the netlist was
  checked directly. [[home-assistant-rotary-controller-log#2026-08-18]]
- **`PWR_EN` gates a second, switched rail (`VCC3V3`) that only the parts
  with no software off-switch sit on — not a latch on the SoC's own
  supply.** The LDO feeding it (ME6217) has an active-high enable with no
  internal pull-up, so it can't be the rail powering the S3 that drives it
  — a chip can't enable its own supply. The always-on rail (`VDD3V3`)
  carries the S3 and everything with its own sleep or power-down command;
  `VCC3V3` carries the radio, audio amp, IR receiver and RGB LED, none of
  which have one. The firmware consequence: `PWR_EN` must go high, and the
  rail must settle, before any SPI or GPIO traffic touches a `VCC3V3`
  peripheral, not merely before the first real transaction — an SPI master
  reports success whether or not anything is listening, and driving an
  unpowered chip's input pins back-powers it through its own ESD clamp
  diodes. [[home-assistant-rotary-controller-log#2026-08-17]]
- **A shared SPI bus is capped by its worst-routed signal.** The S3's
  IO_MUX gives a direct, low-latency path to 80 MHz for a fixed pin per
  peripheral signal, but IDF documents that once any one signal on a bus
  isn't on its IO_MUX-direct pin, the whole bus routes through the GPIO
  matrix crossbar instead, capping around 40 MHz. On this board `SPI_SCK`
  landed on GPIO11 (the MOSI slot), not GPIO12, so the LCD/SD/CC1101 bus
  is crossbar-routed — not a problem here (46 fps ceiling on a 320×170
  panel is plenty), but worth checking on any board before assuming 80 MHz.
  [[home-assistant-rotary-controller-log#2026-08-16]]
- **A pin map is a fact about the PCB, not the chip, and has to be
  discovered accordingly.** The ESP32-S3's GPIO matrix lets almost any
  peripheral signal route to almost any pad, unlike an STM32's fixed
  alternate-function table, so "which pin drives the LCD chip-select" is
  answered by the schematic or the running board, never by the datasheet
  alone. [[home-assistant-rotary-controller-log#2026-08-16]]

## Goal

Turn a LilyGO T-Embed CC1101 Plus into a physical controller for the flat.
Pick a device with the encoder, push to enter it, and the knob then means
whatever that device needs — volume for the TV, temperature for the AC,
brightness for a light. One control, different meaning per device.

Deliberately out of scope: every radio on the board — the CC1101 sub-GHz
transceiver, the nRF24L01 2.4 GHz transceiver, the PN532 NFC reader and the
IR. Everything goes through Home Assistant over Wi-Fi, which already owns
these devices. Also out of scope: a general-purpose dashboard — this
controls a handful of things well.

The board in hand is the variant LilyGO codes `K268` on the box — their own
product number for the T-Embed CC1101 Plus, distinguishing the antenna and
housing options rather than anything electrical. It has no bearing on the
firmware and is recorded here only so the box and the note can be matched
up later.

### Why a knob rather than the phone

The phone can already do all of this, so the argument has to be about the
few seconds either side of the action. Unlocking a phone, finding the app,
waiting for it to connect and locating the right control is perhaps eight
seconds and full attention. Reaching out and turning something is one
second and none — and it works with wet hands, in the dark, while carrying
something, and for anyone else in the flat who has not installed anything.

That is a small win repeated several times a day, which is exactly the
shape of thing worth building once. It is also why the scope stays narrow:
a controller that does four domains instantly beats a dashboard that does
everything slowly, and the moment it needs a menu tree it has lost the
argument it was built on.

Where it earns its place fastest is the one-second actions — muting the
noise sensor from [[thread-matter-noise-sensor]] on the way out of the door,
or knocking the AC down a degree without finding a phone.

Leaving the CC1101 unused on a board named after it is a deliberate call,
not an oversight. That radio is the whole subject of
[[subghz-linux-router]], and it is worth more there — attacked properly,
from the samples up — than as a second way to reach a `cover` entity this
controller can already command over Wi-Fi. Two projects on one board would
also mean neither can be reflashed without losing the other.

## Learning value

Secondary here, and worth saying so plainly: this is the rare project in
the vault built for what it does rather than for what it teaches, and the
Practical value section below is the argument for it. It is also not part
of any of the five courses in [[embedded-learning-curriculum]] and should
not be folded into one. The only candidate is bare-metal and RTOS, whose
whole premise is peripherals driven from the reference manual with no HAL,
on Cortex-M; this is ESP-IDF on Xtensa, which is the vendor HAL that course
exists to refuse, on a core where the serial bootloader half cannot run at
all. Nothing here is gated on knowing what happens before `main()`.

So the question is what to slow down for once the thing is being built
anyway, and the parts split unevenly. Three hold their value:

**Two copies of one value, with a lossy link between them.** A fast spin
produces encoder ticks faster than a WebSocket round trip completes, so the
knob and Home Assistant disagree for as long as the network takes. Sending
a `call_service` per tick makes the UI lag its own input; sending only on
release makes the knob feel dead. The answer — apply locally, coalesce, send
the latest value at a fixed rate, reconcile when `state_changed` comes
back — is optimistic concurrency with reconciliation, which is the same
shape as a game client predicting movement or an editor syncing text. What
makes it concrete here is that the failure is visible: the number on screen
snaps backwards when the reconciliation disagrees with the prediction.
That is measurable rather than arguable, and the coalescing interval should
come out of a measured tick-to-`state_changed` latency rather than a guessed
100 ms.

**A cache with no age is a lie.** Every entity value held on the device is a
copy of something that was true when it arrived, and nothing on screen
distinguishes a value confirmed a second ago from one last confirmed before
the Wi-Fi dropped. Storing a timestamp per entity and rendering the age is
the whole mechanism, and the reason it is worth doing deliberately is that
the failure mode is invisible until the link breaks — a controller
confidently showing stale numbers is worse than one admitting it does not
know, because the knob still turns and nothing happens. The test is to
break it on purpose: restart Home Assistant underneath it, pull the Wi-Fi.
Same problem and same answer as the ground station in
[[lora-dog-collar-telemetry]].

**One control, several meanings, and nowhere to put a mode indicator.**
Single-control interfaces fail by becoming modal without telling anyone
which mode they are in, and the 320×170 panel has to answer that at a
glance, from across a room, to someone who did not build it. This is
specification work rather than code — deciding what the device refuses to
do is most of it — and it is the part that cannot be recovered from any
document.

Two more are worth doing once, with the effort kept proportionate:

- **LVGL as a memory and timing problem rather than an API.** The numbers
  are what make it click: 320 × 170 at 16 bits is 108,800 bytes per full
  framebuffer, so double buffering wants ~212 KiB against the ESP32-S3's
  512 KiB of internal SRAM. That is why partial buffers and a flush callback
  exist at all, and why 8 MB of PSRAM changes the calculation. Worth deriving
  once; the widget API on top is not worth memorising.
- **A protocol read off the wire before it is implemented.** `websocat`
  against Home Assistant first, so the auth handshake, `get_states` and
  `subscribe_events` are things that have been watched rather than things
  taken from a tutorial. One number to take from that session: the actual
  byte size of the `get_states` response, since it returns every entity in
  the instance and cJSON parses into a DOM several times the size of its
  input. Getting away with that on 8 MB of PSRAM is not the same as solving
  it, and whether Home Assistant offers a filtered subscription instead is
  worth checking against its documentation rather than assuming.

The one piece of genuine peripheral work comes free with the encoder. The
ESP32-S3 has a hardware pulse counter with a glitch filter, so quadrature
can be decoded in hardware or in a GPIO interrupt handler, and the choice
has a real consequence: a software handler can miss ticks while a slow
render holds the CPU, and a hardware counter cannot. That is the one place
here where the datasheet decides something.

## Practical value

High, and unusually easy to state: it removes about eight seconds and all
of the attention from actions taken several times a day. Unlocking a phone,
finding the app, waiting for it to connect and locating the control is the
current cost; reaching out and turning something is one second. It also
works with wet hands, in the dark, while carrying something, and for anyone
else in the flat who has installed nothing.

The narrow scope is what protects that. A controller that does four domains
instantly beats a dashboard that does everything slowly, and the moment it
needs a menu tree it has lost the argument it was built on.

## Architecture

| Block | Implementation |
| --- | --- |
| Board | T-Embed CC1101 Plus (LilyGO `K268`) — ESP32-S3, 16 MB flash, 8 MB PSRAM, 1300 mAh cell |
| Display | 1.9" 320×170 ST7789, driven through LVGL |
| Input | Rotary encoder with push — the only input on the device |
| Transport | Home Assistant WebSocket API over Wi-Fi |
| Auth | Long-lived access token in NVS, never in the source tree |
| State | Local cache of the configured entities only |
| Behaviour | Per-domain UI profiles, held as data |

The PSRAM is what makes this comfortable — LVGL on a 320×170 colour panel
wants framebuffer space that a plain ESP32 would have to fight for.

### Per-device behaviour

| Domain | Rotate | Press | Long press |
| --- | --- | --- | --- |
| `media_player` (Google TV) | Volume | Play / pause | Navigation mode — rotate is up/down, press selects |
| `climate` (AC) | Target temperature | Cycle fan speed | Back |
| `light` | Brightness | Toggle | Colour temperature |
| `cover` | Position | Stop | Back |

Held as a table in data rather than a switch statement, so adding a device
is configuration rather than code. That constraint is worth keeping even
when a special case would be quicker — the moment it becomes code, every
new device means a reflash.

### One knob, one button

The entire interface is a small state machine: browsing the device list,
inside a device, inside a sub-mode. Long press is back, and an inactivity
timeout returns to the list so the thing is never left in a strange state.

Worth drawing on paper before writing any of it. Interfaces with a single
control fail by becoming modal without telling the user which mode they are
in, and the display has to answer that question at a glance.

### The two problems worth solving

**Command flooding.** A fast spin produces dozens of encoder ticks. Firing
a `call_service` per tick floods Home Assistant, and the UI ends up lagging
behind its own input. The answer is to apply the change locally, coalesce
the ticks, and send the latest value at a fixed rate — then reconcile when
the `state_changed` event comes back. Optimistic locally, authoritative
from HA.

**Stale state.** Wi-Fi drops, or Home Assistant restarts. A controller
confidently displaying last-known values it can no longer verify is worse
than one that admits it does not know: turning the knob then does nothing
while the screen says otherwise. Connection state stays visible and stale
values are marked as such.

That is the same honesty problem as the ground station in
[[lora-dog-collar-telemetry]], and it takes the same answer — show the age
of the information, not just the information.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Board | LilyGO T-Embed CC1101 Plus | Display, encoder, battery and charger all onboard |
| Firmware | ESP-IDF + LVGL | |
| JSON | cJSON | Bounded buffers — the event stream is chatty |
| Protocol learning | `websocat` against HA from the desktop | Understand the API before writing firmware for it |
| Auth | Long-lived access token | Generated in the HA profile page |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| T-Embed CC1101 Plus (if not already owned) | 50–80 € |
| USB-C cable, desk stand | ~10 € |

The board is effectively the entire cost — display, encoder, PSRAM, battery
and charging are already on it, which is why it is worth more than the sum
of parts here.

## Software / firmware

- WebSocket client: authenticate, `get_states` for the initial snapshot,
  `subscribe_events` for `state_changed`
- State cache, restricted to the configured entity list
- UI profile table mapping domain → what the encoder means
- Input state machine — selection, entry, sub-modes, timeout
- LVGL screens, redrawn from the cache rather than from events directly
- Reconnect with backoff, and stale marking while disconnected

## Plan

- [ ] Drive the display and encoder, LVGL hello world on the panel
- [ ] Talk to the HA WebSocket API from `websocat` — learn auth and
      `subscribe_events` before writing any firmware
- [ ] Firmware client: authenticate, `get_states`, subscribe
- [ ] State cache and a scrollable device list on screen
- [ ] `call_service` on encoder turn — one device working end to end
- [ ] Rate limiting and optimistic updates, spin the knob hard and watch HA
- [ ] Profile table, then the TV and the AC
- [ ] Reconnect and stale marking, tested by restarting HA underneath it
- [ ] Display sleep and battery indication
- [ ] Stretch: an entity picker on the device, so the list is not compiled in

Shares its input-queue and render split with [[freertos-pocket-console]] —
same problem one board class up, with a network event stream in place of
game logic. The devices at the other end include
[[thread-matter-growbox]] and [[thread-matter-noise-sensor]].

## Build log

Session entries live in [[home-assistant-rotary-controller-log]].
