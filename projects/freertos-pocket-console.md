---
tags: [project, embedded, freertos, esp32]
status: idea
depends: [bare-metal-bootloader]
created: 2026-08-07
---

# FreeRTOS Pocket Console

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Get real fluency with RTOS tasks, priorities and inter-task communication by
building something where scheduling mistakes are immediately visible: a
handheld console that must never drop a keypress or stutter the UI.

Learning goals:
- FreeRTOS tasks, priorities, and what starvation looks like
- Queues, semaphores and mutexes used for their actual purpose
- Keeping a rendering loop smooth while other work happens

Deliberately out of scope: a custom PCB or enclosure — breadboard and
protoboard are fine.

## Architecture

| Task | Priority | Responsibility |
| --- | --- | --- |
| Input | High | Button scanning and debouncing, never blocked by rendering |
| Logic | Medium | Game / application state machine |
| Display | Low–medium | Renders the current frame to the SPI OLED |

Tasks never touch each other's state directly. Input pushes key events into
a queue; logic consumes them and pushes render commands or a frame buffer
to the display task; the SPI bus is guarded by a mutex.

The design goal is stated as a testable property: switching between apps
must not lose game state, and no button press may be dropped even while the
display is mid-refresh.

### Applications

- Tetris — continuous timing pressure, makes any scheduling glitch obvious
- Calculator — trivial logic, but exercises the menu and input paths
- Ground station — the app that gives the device a reason to exist
- Finder — distance and bearing to a UWB tag, for [[uwb-precision-locator]]
- Menu system on top, switching between them without tearing anything down

### The app that keeps it alive

A console with two toy apps ends up in a drawer. The third app is the one
that matters: bolt a LoRa module on and it becomes the field handheld for
[[lora-dog-collar-telemetry]] — a screen showing the collar's position,
activity class and battery while out walking.

That also makes it a better RTOS exercise than the games do. Packets arrive
whenever the collar decides to send, asynchronously and at low priority,
while the UI must stay responsive — a fourth task, another queue, and a
real reason for the priorities to be right.

The same split — input task, state, render task, asynchronous events
arriving from outside — scales up to [[home-assistant-rotary-controller]],
where the event stream comes from the network rather than a radio.

The finder app is the same shape again with the timing turned up: ranging
exchanges for [[uwb-precision-locator]] complete on millisecond deadlines,
and a display task that blocks the radio task is not a dropped frame but a
wrong distance. It is also the app that gets carried into a car park and
either works or does not.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| MCU | ESP32 | FreeRTOS is built into ESP-IDF |
| Display | SPI OLED (SSD1306 / SH1106) | Small, cheap, fast enough |
| Input | Matrix keypad or discrete buttons | Debounced in software |
| Debug | ESP-IDF monitor, FreeRTOS trace facility | Task stats to catch starvation |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| ESP32 dev board | 6–12 € |
| SPI OLED | 5–10 € |
| Buttons / keypad, protoboard | 5–10 € |
| Battery + charger | 10 € |
| LoRa module for the ground-station app | 10–15 € |

## Software / firmware

- ESP-IDF project, tasks created explicitly with chosen stack sizes and
  priorities
- Queues for key events and render requests, mutex for the SPI bus
- Display driver — either a minimal one written by hand, or an existing one
  wrapped so all access goes through the display task

## Plan

- [ ] OLED over SPI, draw something static
- [ ] Debounced button reading in its own task, events into a queue
- [ ] Display task with a fixed frame rate, fed only from a queue
- [ ] Tetris logic as a separate task, state kept private
- [ ] Calculator app, sharing the same input and render contracts
- [ ] Menu and app switching with state preserved
- [ ] Deliberately overload a task and watch the priorities behave
- [ ] LoRa receive task, ground-station app — take it on an actual walk
- [ ] Stretch: field firmware updates over the [[bare-metal-bootloader]] path

## Build log

Session entries live in [[freertos-pocket-console-log]].
