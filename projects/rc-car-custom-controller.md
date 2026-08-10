---
tags: [project, hardware, embedded, control, rc]
status: idea
depends: []
created: 2026-08-07
---

# RC Car on My Own Firmware

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Take a cheap RC chassis, throw away whatever electronics came with it, and
drive it on firmware I wrote — radio link decoded by hand, steering and
throttle driven directly, speed held by a control loop that I tuned.

Deliberately out of scope: autonomy, obstacle avoidance, anything with a
camera. A car that drives well under my control is the whole target.

## Learning value

- Decoding an RC receiver protocol from the timing up — PPM, then SBUS
- Servo and ESC control, and what those signals actually are
- A real PID loop, with a measurement, a setpoint and consequences
- Failsafe design where losing the link matters

## Practical value

Almost none as a vehicle. The chassis arrived with electronics that already
drove it, and those get thrown away here in order to arrive back at roughly
the same behaviour by a much longer route.

The value is that it is the cheapest possible place to be wrong about a
control loop and a failsafe. A mistuned PID makes a car surge into a wall
at walking pace; the same mistake on [[custom-flight-controller-drone]]
destroys a set of props and possibly the airframe. Everything learned here
about the radio link, ESC signalling and what to do when the link drops is
carried into that project, where it is no longer cheap to discover.

## Architecture

| Block | Implementation |
| --- | --- |
| Chassis | Cheap RC car, or a toy stripped of its original board |
| Radio | Hobby RC transmitter and receiver |
| Link decode | PPM pulse timing captured on input capture, then SBUS over UART |
| Steering | Standard servo, 50 Hz PWM |
| Throttle | Brushed ESC, or an H-bridge driven directly |
| Feedback | Wheel encoder — optical or hall |
| MCU | Any Cortex-M board with timers and a spare UART |

### Why this before the drone

Everything here transfers to [[custom-flight-controller-drone]] — the radio
link, the failsafe, the actuator signals, the PID. The difference is what
happens when the code is wrong. A badly tuned car surges and stops. A badly
tuned drone destroys a set of props and possibly the frame.

So the expensive, breakable parts get bought once the loop already works.

### Closed-loop speed control

Open-loop throttle is just a passthrough — the transmitter stick position
becomes a pulse width and nothing is learned. The encoder changes that: the
stick becomes a *speed request*, and the loop has to hold that speed
uphill, downhill and on carpet.

That is a genuine PID problem with an honest measurement, and the failure
modes are visible and harmless: overshoot on launch, oscillation when the
gain is too high, sag on a slope when it is too low.

### Failsafe

| Event | Behaviour |
| --- | --- |
| No valid frame for N ms | Throttle to neutral, steering centred |
| Startup | Motor stays disarmed until the throttle stick is seen at neutral |
| Encoder failure | Fall back to open loop rather than commanding full power |

That third one matters: a PID whose measurement drops to zero will wind up
and demand everything the motor has. Practising that here is cheap.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| MCU | STM32 or similar | Input capture and PWM on hardware timers |
| Radio | Hobby TX/RX set | Also used later by [[custom-flight-controller-drone]] |
| Debug | Logic analyzer | To read PPM and servo pulses directly |
| Telemetry | UART logging of setpoint vs. actual speed | Tuning without guessing |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Chassis, motor, steering servo | 25–50 € |
| Brushed ESC or H-bridge | 10–20 € |
| RC transmitter + receiver | 40–80 € |
| MCU board | 10–20 € |
| Wheel encoder, battery, wiring | 15–25 € |

The radio set is the largest line and is bought once — the drone reuses it.

## Software / firmware

- Input capture driver for PPM, later an SBUS parser on UART
- Servo and ESC output on timer PWM, with limits clamped in software
- Encoder counting, speed estimation, PID
- Failsafe state machine, sitting above everything else
- Telemetry stream for offline plotting — the same approach as the drone's

Telemetry packing carries over to [[lora-dog-collar-telemetry]] once it
moves off UART onto a radio link.

## Plan

- [ ] Capture the receiver's PPM output on the logic analyzer, decode by hand
- [ ] Input capture in firmware, print channel values
- [ ] Drive the steering servo from a stick, limits clamped
- [ ] Throttle open loop, arming sequence, wheels off the ground
- [ ] Failsafe — switch the transmitter off mid-drive, confirm it stops
- [ ] Wheel encoder, measure actual speed
- [ ] PID speed hold, tune it, log setpoint vs. actual
- [ ] Move from PPM to SBUS, same behaviour on a better protocol
- [ ] Stretch: telemetry back to the transmitter or a separate receiver

## Build log

Session entries live in [[rc-car-custom-controller-log]].
