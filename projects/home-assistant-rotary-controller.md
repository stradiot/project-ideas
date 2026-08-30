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

Plan item two is underway and the transport is measured everywhere except
latency. `get_states` returns 134,043 bytes for 284 entities and takes no filter
argument of any kind; the 22 entities across the four controlled domains weigh
13,566 of them, about a tenth. `subscribe_events` filters by event type only, so
the ongoing stream is unfiltered too — the entity filter is `subscribe_trigger`,
which takes a list, runs the predicate inside HA, and does fire on the
attribute-only changes this device lives on. A group entity re-emits its whole
aggregate on every member report, measured at 15 events against a single
member's 3 for one dim. What is left is the command-to-`state_changed` latency,
which the burst data already shows is two numbers rather than one, and the
transport decision it feeds. `main.c` is still the stage-5 encoder jig and no
plan box is ticked.

## Lessons

- **Home Assistant's WebSocket API has no entity filter on either `get_states`
  or `subscribe_events` — the entity filter is `subscribe_trigger`, and finding
  it means understanding that a trigger is not a kind of event.** `get_states`
  takes no argument at all and returned 134,043 bytes for 284 entities, of which
  the four controlled domains were 13,566; `subscribe_events` filters by event
  *type*, so the ongoing stream is unfiltered too, and each `state_changed`
  carries both `old_state` and `new_state` in full. HA's core is an event bus and
  `subscribe_events` is a raw tap on it, which is why neither can select by
  entity. A trigger is a **listener specification** — the same declarative config
  an automation's trigger block holds, compiled by the automation engine into a
  bus subscription plus a predicate — so `subscribe_trigger` is HA letting a
  client instantiate one with no automation attached and take the firings
  directly. The predicate exists either way; the only question is which side of
  the network it runs on. It is not cheaper per event, since the payload wraps
  everything in `event.variables.trigger` on top of full `from_state` and
  `to_state`, so the whole saving is in the events never sent and its value is
  exactly the ratio of instance to interest.
  [[home-assistant-rotary-controller-log#2026-08-30]]
- **A group entity multiplies the push stream by its member count, because it
  has no state of its own and recomputes its whole aggregate on every single
  member report.** One brightness drag on a five-bulb group produced 15 group
  events against 3 from one member subscribed alongside it — exactly 3 reports
  times 5 members — and 34,914 bytes for one dim of one lamp. The group's
  messages are also the fatter ones, since each carries the member list twice, in
  `from_state` and `to_state`. The tell that separates this from a chatty slider
  is the interleaved zeros, `192 -> 0 -> 96 -> 0`, all with `state: "on"`: no
  slider produces those, an average recomputed over members mid-transition does.
  The consequence is that command flooding is not only an outbound problem —
  roughly 15 messages of ~2.5 KB inside 400 ms arrive for one human gesture, and
  the `desired`/`confirmed` pair has to survive rendering a confirmed zero during
  a change the device itself initiated.
  [[home-assistant-rotary-controller-log#2026-08-30]]
- **A refusal is only worth writing into a specification if the code is already
  pulling towards the thing being refused — everything else on the list is either
  already violated or not enforceable by the firmware at all.** Sorting five
  candidate scope boundaries by that test left one: text entry, because text entry
  on a single rotary encoder is a character carousel — rotate an alphabet, press
  to commit, plus a backspace and a done — which is the level-4 enum carousel with
  a bigger array, a shape the interface design had already built. It is an array
  away, not a feature away, which is exactly the case a written boundary exists
  for. The others failed the test in two distinct ways worth telling apart.
  "No hierarchy deeper than two levels" was already violated by a four-level
  carousel, so it could not be refused. "Nothing with a safety consequence" and
  "nothing slower than three seconds" cannot be held by the code at all, because
  what this device controls is decided by which entities carry a tag in Home
  Assistant rather than by anything in the firmware, where a domain is a small
  integer and a label in flash. A boundary the code cannot enforce is a
  resolution, and resolutions lose to a Tuesday evening when the feature is forty
  lines. [[home-assistant-rotary-controller-log#2026-08-26]]
- **Splitting entity data into topology and state has a consequence the split
  itself does not advertise: there is no blind-control fallback, because an
  enum's candidate list is state.** The intuition is that a controller which has
  lost track of a value is still useful for named choices — pick `HDMI 2` without
  needing to know what is selected now. It is not, and the reason is the split
  itself: `source_list`, `fan_modes`, `hvac_modes` and `effect_list` arrive inside
  the entity's state object and are null on wake, so a device that does not know
  the current value does not have the list of candidates either and there is
  nothing to rotate through. The numeric case fails for a neighbouring reason —
  the service calls are absolute (`volume_set`, `set_temperature`) and are computed
  from a desired value seeded by the confirmed one, so with no baseline there is
  no command to form. A device in this design does not degrade into a blind
  controller when it stops knowing the truth; it declines, which is what makes
  "what it shows is true, or it says it does not know" a criterion the whole
  design already leans on rather than an aspiration bolted to it.
  [[home-assistant-rotary-controller-log#2026-08-26]]
- **Under a push subscription the age of a value measures how often it changes,
  not whether it can still be trusted — so the honest instrument is
  per-connection, not per-entity.** `subscribe_events` pushes on change and is
  silent otherwise, which makes silence the healthy case: a lamp untouched since
  morning carries hours of arrival age and is perfectly true, while a socket that
  died an hour ago accumulates age identically. A per-entity staleness threshold
  therefore raises a warning on healthy entities and stays quiet about the only
  case that matters until link state reports it anyway — a false signal rather
  than a redundant one. Two corollaries. Home Assistant's own `last_changed` and
  `last_updated` are ISO 8601 on HA's clock, so rendering an age from them needs
  SNTP and the assumption that two clocks agree, whereas a local arrival stamp
  from `esp_timer_get_time()` needs neither and is still worth keeping unrendered,
  because the coalescing interval is supposed to come from a measured
  tick-to-`state_changed` latency. And the resolution of the honest signal is
  bounded by the keepalive interval rather than by anything in the data, because
  a half-open TCP connection is silent in exactly the way health is.
  [[home-assistant-rotary-controller-log#2026-08-24]]
- **On a device asleep upward of 99% of the time, an event-latched notification
  is structurally undeliverable; only state evaluated at wake works.** A battery
  crossing 20%, a sync result and a link drop all happen with the screen dark and
  nobody to deliver to, so latching them means a queue, a lifetime and a policy
  for a backlog. Deriving every status entry from current state at render time
  instead makes a pop-up the first-observation *presentation* of a condition
  rather than an object of its own — which is why an acknowledgement clears the
  presentation and never the condition, and why sleeping on an unread warning
  costs nothing, since the condition re-presents itself at the next wake. The one
  class that breaks the model is informational, because a success message has no
  persisting condition to derive from; those are restricted to the direct result
  of an action just taken, where the screen is lit and someone is looking by
  construction. [[home-assistant-rotary-controller-log#2026-08-24]]
- **Whether stored text is capped and whether it scrolls are independent
  decisions, and conflating them is what pushes a design onto heap pointers it
  does not need — while the one place a cap is genuinely load-bearing is
  correctness rather than display.** LVGL's `LV_LABEL_LONG_SCROLL` scrolls a
  `char[N]` as happily as a malloc'd string, so "the title does not fit"
  argues for a rendering mode and never for a lifetime. Keeping every field
  fixed-size is what keeps a state cache a plain struct array: a write is a
  `memcpy` into storage that already exists, the worst case is truncation, and
  the render task can read at any instant without coordinating — whereas one
  heap pointer means malloc, swap and free racing a task that may be mid-draw
  on the old pointer, which costs a lock, refcounting or a deferred free. The
  cap stops being cosmetic at Home Assistant's enums: `select_source` takes
  the option's name string exactly as HA supplied it and has no index form, so
  a string truncated to fit the panel cannot be sent back, and the cap has to
  be at least as long as the longest option the real devices report.
  [[home-assistant-rotary-controller-log#2026-08-21]]
- **Splitting an entity's data into topology and state — by how often each
  changes, not by where it comes from — is what makes a deep-sleeping display
  usable, and it dissolves the message-payload question rather than answering
  it.** What entities exist, what they are called, which area they are in and
  what shape they are changes when the HA config is edited, months apart;
  their values change constantly. Persisting the first in NVS across deep
  sleep while nulling the second on wake gives a carousel that is navigable
  the instant the screen lights — two levels deep before the socket is up —
  with values filling in behind it. The corollary is what it deletes:
  `source_list`, `hvac_modes`, `fan_modes` and `effect_list`, the
  variable-length string arrays that stalled the render-loop design, are
  state rather than topology, so they arrive inside the entity's state object
  and are null-on-wake like every other value. Nothing is remembered and
  re-displayed, so there is no wake-time reconciliation and the render
  queue's payload can be a cache index.
  [[home-assistant-rotary-controller-log#2026-08-20]]
- **Deep sleep on the ESP32-S3 does not pause the device, it deletes it — and
  both halves of "wake on knob turn" break on that in ways that look like UX
  choices.** PCNT lives in the digital power domain and does not survive deep
  sleep, so every edge between the wake and the point where PCNT is
  reconfigured lands on an unconfigured peripheral: a counted wake-turn would
  count an arbitrary fraction of the motion, which is worse than counting
  none, so swallowing it is forced rather than chosen. And `ext1` wake is
  *level*-triggered, not edge-triggered — it arms a pin mask and one polarity,
  and any pin already at the wake level on entry wakes immediately, giving a
  boot loop instead of rest. Contact-closed pulls these lines low, so the
  polarity has to be low, which makes the encoder's resting levels the fact
  that decides whether wake-on-turn is possible at all: this part detents
  every half quadrature cycle, so its resting states alternate between two of
  the four, and if one line rests low on alternate detents then half the knob
  positions make deep sleep impossible — a symptom that would depend on where
  the knob happened to stop last time. Not yet measured.
  [[home-assistant-rotary-controller-log#2026-08-20]]
- **`idf.py flash` does not erase NVS, so "wipe and re-sync by hand after a
  flash" is a policy with no mechanism behind it.** Flashing writes only the
  partitions in the flash args — bootloader, partition table, app — so new
  firmware boots straight onto records written by the previous layout and
  reads four fields out of a blob that now has five, filling the UI with
  garbage at exactly the moment you are least likely to remember. A schema
  version constant compared on boot buys *invalidation* — erase, mark empty,
  prompt for a re-sync — which is a handful of lines, as opposed to
  *migration*, which means keeping every old layout's reader alive forever.
  The scoping detail that makes the wipe safe is that Wi-Fi credentials live
  in NVS too: without a separate namespace for the topology, every flash
  re-provisions Wi-Fi as well.
  [[home-assistant-rotary-controller-log#2026-08-20]]
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
- **A pin map is a fact about the PCB, not the chip, and a vendor schematic's
  typed annotation blocks are documentation rather than netlist — so a
  partially-correct legend is more dangerous than a wholly wrong one.** The
  ESP32-S3's GPIO matrix routes almost any peripheral signal to almost any pad,
  unlike an STM32's fixed alternate-function table, so "which pin drives the LCD
  chip-select" is answered by the board or the schematic and never by the
  datasheet. And only symbols, wires and net labels carry connectivity in the EDA
  tool: a legend box of hyphens-and-arrows can claim two nets are the same
  without making them so, and nothing checks it the way DRC checks the netlist.
  On the LCD sheet the legend was right about seven of ten lines — matching the
  traced `LCD_CS`, SPI trio, I²C pair and `BL_EN` exactly — which is what made
  the two wrong ones (leftover touch-panel signals from a different T-Embed
  variant, one contradicting the traced `LCD_DC`) worth believing until the
  netlist was checked directly. [[home-assistant-rotary-controller-log#2026-08-16]],
  [[home-assistant-rotary-controller-log#2026-08-18]]

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

Session entries live in [[home-assistant-rotary-controller-log]]. The answers
to the requirements questionnaire — what the device controls, what each screen
shows, what the knob means and what it does when it stops knowing the truth —
are collected in [[home-assistant-rotary-controller-spec]], which is what the
firmware is written against rather than the log entries the answers were argued
out in.
