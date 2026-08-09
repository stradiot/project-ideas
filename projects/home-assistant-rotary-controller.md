---
tags: [project, hardware, embedded, esp32, home-assistant, ui]
status: idea
depends: [freertos-pocket-console]
created: 2026-08-07
---

# Home Assistant Rotary Controller

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Turn a LilyGO T-Embed CC1101 Plus into a physical controller for the flat.
Pick a device with the encoder, push to enter it, and the knob then means
whatever that device needs — volume for the TV, temperature for the AC,
brightness for a light. One control, different meaning per device.

Learning goals:
- The Home Assistant WebSocket API written by hand — authentication, event
  subscription, a local state cache
- Designing a usable interface where the only input is one knob and one
  button
- LVGL on a colour display, driven from ESP-IDF
- Keeping a networked UI honest when the connection is not there

Deliberately out of scope: the board's CC1101, IR and NFC. Everything goes
through Home Assistant, which already owns these devices. Also out of
scope: a general-purpose dashboard — this controls a handful of things
well.

Leaving the CC1101 unused on a board named after it is a deliberate call,
not an oversight. That radio is the whole subject of
[[subghz-linux-router]] and [[subghz-fixed-code-repeater]], and it is worth
more there — attacked properly, from the samples up — than as a second way
to reach a `cover` entity this controller can already command over Wi-Fi.
Two projects on one board would also mean neither can be reflashed without
losing the other.

## Architecture

| Block | Implementation |
| --- | --- |
| Board | T-Embed CC1101 Plus — ESP32-S3, 16 MB flash, 8 MB PSRAM |
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
[[thread-matter-smart-planter]] and [[thread-matter-noise-sensor]].

## Build log

Session entries live in [[home-assistant-rotary-controller-log]].
