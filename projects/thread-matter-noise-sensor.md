---
tags: [project, hardware, embedded, esp32, thread, matter, audio]
status: idea
depends: [thread-matter-smart-planter]
created: 2026-08-07
---

# Thread / Matter Noise Sensor

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Know whether the dog is disturbed when left alone. A mains-powered
microphone node that reports noise events into Home Assistant, can be
switched off from there, and can be listened to live when a notification
arrives and I want to know what is actually going on.

Learning goals:
- I2S audio capture, and turning a stream of samples into a usable level
- ESP-IDF and esp-matter, against the Zephyr / nRF Connect experience from
  [[thread-matter-smart-planter]] — same protocol, entirely different SDK
- Sharing one radio between two network stacks
- Designing a privacy boundary deliberately rather than by accident

Deliberately out of scope: identifying *what* made the noise. No
classification, no machine learning. The dog normally sleeps when left
alone, so a level and a duration answer the actual question.

## Architecture

| Block | Implementation |
| --- | --- |
| MCU | ESP32-C6 — Wi-Fi 6 and 802.15.4 in one part |
| Microphone | INMP441 over I2S, 16 kHz mono |
| Detection | RMS per frame → dBFS, hysteresis and a minimum duration |
| Sensor transport | Matter over Thread, joining the existing Border Router |
| Live audio | HTTP PCM stream over Wi-Fi, on demand only |
| Power | Mains over USB — always on, always listening when enabled |

### Detection

32 ms frames at 16 kHz. RMS converted to dBFS, then **two** thresholds
rather than one: rise above X for N consecutive frames to assert, fall
below Y for M frames to clear. A single threshold sits on the room's noise
floor and flaps continuously.

The thresholds get picked from measured data, not guessed. A diagnostic
HTTP endpoint serves the running level, so a quiet flat, a passing car, the
neighbour's door and the washing machine all become numbers before any
threshold is chosen. Guessing here means either a sensor that cries wolf or
one that never fires, and both are indistinguishable from broken.

### The radio handoff

This is the core of the project, and it is forced by the hardware.

The C6 has one 2.4 GHz RF module shared by Wi-Fi, BLE and 802.15.4,
arbitrated by time-division multiplexing — and 802.15.4 normal receive is
assigned the *lowest* priority. A sustained audio stream does not coexist
with Thread, it starves it. Espressif's own advice for genuinely
simultaneous operation is a two-chip design.

So the device has modes rather than coexistence:

| Mode | Radio | Behaviour |
| --- | --- | --- |
| Normal | 802.15.4 | Matter sensor, noise events to Home Assistant |
| Live listen | Wi-Fi | Audio stream; Thread parked and unreliable |

Home Assistant sets the "live listen" attribute over Thread, the device
acknowledges, and *then* switches.

Coming back is the more interesting half. A stop command cannot be trusted
to arrive over a starved Thread link, so **the stream's own TCP connection
is the control channel**: the client disconnects, Wi-Fi comes down, Thread
rejoins. A hard timeout backstops the case where the client vanishes
without closing cleanly. Worth measuring how long the Thread rejoin takes —
that number is the real cost of the handoff.

Honest counter-argument, because it deserves stating: the device is mains
powered, so plain Matter over Wi-Fi would sidestep all of this and is the
pragmatic engineering choice. Thread is here because it is the thing worth
learning, and because the handoff is the most interesting problem in the
build. It is not the optimal transport for this device.

### Matter has no sound sensor

There is no sound or noise device type in the Matter data model, so the
boolean has to borrow one. Contact Sensor over Boolean State is the most
semantically neutral candidate; Occupancy Sensor is the alternative. Either
way it gets renamed in Home Assistant, and checking which maps most cleanly
is a build step rather than something to assume.

Running into this is itself the lesson: a rigid, certifiable device-type
model is exactly what makes Matter interoperable, and exactly what leaves
no room for a device nobody standardised.

| Endpoint | Cluster | Purpose |
| --- | --- | --- |
| 1 | Boolean State (borrowed type) | Noise detected |
| 2 | On/Off | Listening enabled |
| 3 | On/Off | Live listen — triggers the Wi-Fi handoff |

The measured level itself stays off Matter — no cluster fits it — and lives
on the diagnostic endpoint instead.

### Audio and privacy

Nothing is recorded and nothing is stored. Audio leaves the device only
while a client is actively connected to the stream, and the whole capture
path is gated by the listening switch — off means the I2S peripheral is
stopped, not merely ignored.

16 kHz 16-bit mono is roughly 256 kbit/s, which is nothing over Wi-Fi, so
it goes out as raw PCM behind a WAV header. A browser or VLC plays it with
no client software written at all. mDNS advertises the device once Wi-Fi is
up, so the stream does not depend on a pinned address.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| MCU | ESP32-C6 DevKit | The 802.15.4 radio is the reason for this part |
| Microphone | INMP441 module | I2S, 24-bit, cheap and well documented |
| Firmware | ESP-IDF + esp-matter | Deliberately not Zephyr — the comparison is the point |
| Border Router | Existing OpenThread BR | Already built for [[thread-matter-smart-planter]] |
| Debug | `ot-ctl`, Thread sniffer, Wireshark | Mesh on one side, stream on the other |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| ESP32-C6 DevKit | 8–15 € |
| INMP441 microphone module | 3–6 € |
| USB supply, wiring, enclosure | 10–15 € |

The cheapest project in the vault, and the one most likely to be used
daily.

## Software / firmware

- I2S capture task, framing and RMS → dBFS
- Hysteresis state machine with assert and clear durations
- esp-matter application: three endpoints, attribute reporting
- HTTP server — diagnostic level endpoint, and the WAV/PCM stream
- Mode manager: Thread up, Wi-Fi up, teardown, rejoin — the part most
  likely to be subtly wrong

## Plan

- [ ] I2S capture from the INMP441, dump raw samples and confirm they move
- [ ] RMS → dBFS, serve the running level on an HTTP endpoint
- [ ] Log a full day of real levels, pick thresholds from the data
- [ ] Hysteresis and minimum duration, verify it does not flap overnight
- [ ] Matter over Thread, commissioned into Home Assistant
- [ ] Listening switch — confirm it actually stops the I2S peripheral
- [ ] Wi-Fi handoff on demand, stream playing in a browser
- [ ] Teardown on client disconnect, measure the Thread rejoin time
- [ ] Timeout backstop for a client that disappears
- [ ] Mount it, and get one notification that turns out to mean something

Same dog as [[lora-dog-collar-telemetry]] — that one tracks him outdoors,
this one listens indoors. The listening switch is also reachable from
[[home-assistant-rotary-controller]], which is the fastest way to mute it
on the way out of the door.

A noise event says something happened, but not where he was when it did.
[[uwb-precision-locator]] answers the other half: a single anchor in the
same room reports his position, so a bark at three in the morning comes
with whether he was on his bed or standing at the door. Neither number
means much alone; together they are close to an answer.

## Build log

Session entries live in [[thread-matter-noise-sensor-log]].
