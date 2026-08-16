---
tags: [project, embedded, freertos, esp32]
status: idea
depends: []
created: 2026-08-07
---

# FreeRTOS Pocket Console

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Get real fluency with RTOS tasks, priorities and inter-task communication by
building something where scheduling mistakes are immediately visible — then
turn it into a device that actually gets carried: a handheld that must never
drop a keypress or stutter the UI, on dog walks, in the underground garage,
and in the forest.

Deliberately out of scope: cellular, GPS on the handheld itself, and any
kind of certification.

Two revisions, and the split is deliberate.

### v1 — protoboard

The RTOS project. Tasks, queues, priorities, starvation, a display that
never stutters. None of that is blocked by hardware, and doing it first is
what tells v2 what its board actually needs: real current draw, which inputs
get used and which were a nice idea, where the radio wants to sit, how much
flash the apps really take.

Designing a board around firmware that does not exist yet is how boards get
revised three times at 30–50 € and three weeks each.

### v2 — the device

A production handheld, and the point at which the earlier out-of-scope line
gets deliberately reversed:

- Custom PCB in KiCad — second board after [[ble-sensor-node-pcb]], so the
  layout skill is consolidated rather than learned twice
- Printed enclosure with a gasket, screen window and sealed button
  penetrations — splash-proof, not submersible
- LiPo with charging, protection and a fuel gauge that does not lie at 20%
- A real power switch, not a jumper
- ESD on anything exposed to a pocket
- ESP-IDF OTA with A/B partitions, so it updates without opening the case
- A lanyard point, and enough stiffness to survive being dropped on tarmac

The enclosure is not cosmetic. A flexing protoboard joint produces
intermittent faults that look exactly like task starvation — which is the
bug class this whole project exists to teach me to find. Field equipment
that fails ambiguously teaches nothing.

## Learning value

- FreeRTOS tasks, priorities, and what starvation looks like
- Queues, semaphores and mutexes used for their actual purpose
- Keeping a rendering loop smooth while other work happens
- Taking firmware that works on a bench and making it survive being carried

## Practical value

Split across the two revisions, which is the reason they are separate.

v1 has none. A protoboard with a display that does not stutter is a test
rig, and it stays on the bench.

v2 is a device that gets carried — on dog walks, in the underground garage,
in the forest — and everything that separates it from v1 is practical
rather than educational: a sealed enclosure, a fuel gauge that does not lie
at 20%, a real power switch, ESD on anything a pocket can reach, and OTA so
it updates without being opened. It is also the ground station for
[[lora-dog-collar-telemetry]], which is the job that decides whether it
was worth building.

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
| PCB, v2 | KiCad | Same workflow as [[ble-sensor-node-pcb]] |
| Enclosure, v2 | Fusion 360 + Prusa MK4IS | Printed, gasketed; same discipline as [[beaglebone-green-case]] |
| Power, v2 | Nordic PPK2 or a bench supply with µA resolution | A carried device lives or dies on the battery figure |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| **v1 — protoboard** | |
| ESP32 dev board | 6–12 € |
| SPI OLED | 5–10 € |
| Buttons / keypad, protoboard | 5–10 € |
| Battery + charger | 10 € |
| LoRa module for the ground-station app | 10–15 € |
| **v1 total** | **~36–57 €** |
| **v2 — the device** | |
| PCB, 5 pcs + assembly | 50–90 € |
| Components: charger, protection, fuel gauge, ESD, switch | 25–40 € |
| Display and connector | 10–20 € |
| Enclosure filament, gasket cord, inserts, screws | ~15 € |
| Second revision, assumed | 30–50 € |
| **v2 total** | **~130–215 €** |

v2 is the expensive half and it is spent on a device that gets carried, not
on the learning. Worth deciding after v1 has been used on a few walks and
the requirements are known rather than guessed.

Sourcing: [[parts-sourcing]] — the v1 modules are commodity buys and the
battery is not, because v2's whole claim is a runtime figure and a pack of
overstated capacity still produces a number.

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
- [ ] Write down what v1 got wrong: current draw, unused inputs, layout
- [ ] Schematic and layout in KiCad, informed by that list
- [ ] Enclosure in Fusion — gasket, screen window, sealed buttons
- [ ] Assemble v2, bring it up, measure the battery life for real
- [ ] ESP-IDF OTA with A/B partitions — update it without opening the case
- [ ] Ship a deliberately broken build and confirm it rolls back
- [ ] Carry it for a month and fix whatever the month finds

The OTA path is ESP-IDF's own, with its A/B partition scheme and rollback —
not the serial bootloader from [[bare-metal-bootloader]], which is Cortex-M
code built around VTOR and cannot run on an Xtensa part. What that project
gives this one is knowing what an A/B update mechanism is actually doing
before trusting a sealed case to one.

## Build log

Session entries live in [[freertos-pocket-console-log]].
