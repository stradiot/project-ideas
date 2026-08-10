---
tags: [project, hardware, embedded, control, imu]
status: idea
depends: [rc-car-custom-controller]
created: 2026-08-07
---

# Custom Flight Controller — Drone That Hovers

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Write a flight controller from scratch instead of flashing Betaflight: read
the IMU, filter it, close a PID loop, and generate PWM for the ESCs at a
steady 1 kHz. Success is a drone that holds a stable hover.

Learning goals:
- Real-time control loops with hard timing requirements
- Sensor filtering — complementary filter against vibration noise
- PID tuning on a system that punishes mistakes immediately

Deliberately out of scope: GPS hold, autonomous flight, a camera, and
anything beyond attitude stabilisation. Hover is the bar.

### This one is last, and it is small

This is the last project in the vault, deliberately. Not because anything
blocks it — nothing does — but because it is the one that most rewards
already knowing what you are doing. Every other project here teaches
something it needs: the loop from [[rc-car-custom-controller]], the airframe
sense from [[printed-rc-plane]], the timing discipline from everything else.

It is also built as cheaply as a flying machine can be. A printed ducted
whoop, 65–75 mm, one cell — the class where a crash costs a reprinted duct
rather than a set of motors, where the props cannot reach fingers or walls,
and where the whole thing can be tuned indoors in winter. Around 75 €
against the 150–300 € a 5" build would cost, and none of the learning is
lost: the IMU, the filter, the 1 kHz loop, motor mixing and DShot are
identical at any size.

The frame is printed in PETG rather than PLA. PLA shatters on impact; PETG
bends and survives, and a duct that absorbs a wall strike is the reason this
class is safe to fly inside.

### Why not Betaflight

Betaflight exists, it is free, it is better than anything written here will
be, and it would have this airframe flying in an afternoon. That is not an
argument against writing one — it is the same situation as
[[beaglebone-pru-realtime]], where a €10 logic analyzer already exists — but
it does decide what the project is *for*.

So: the deliverable is understanding, and the honest measure of success is
being able to read Betaflight's source afterwards and recognise every part
of it. The drone flying is the proof, not the product. If a flying machine
that works well is ever the actual want, the answer is to flash Betaflight
onto this same airframe and enjoy it.

### Order of spend

The airframe, LiPo, ESCs and radio are the expensive, breakable part, and
none of them are needed to find out whether the control loop works. So they
are bought last.

The radio link, failsafe, ESC signalling and PID tuning are all learned on
[[rc-car-custom-controller]] first, where a mistuned loop makes a car surge
instead of destroying a set of props. What remains genuinely new here is
the attitude loop — the IMU, the filter, and closing a loop around an angle
rather than a speed. That part gets proven on a bench rig before anything
flies, and by then [[printed-rc-plane]] has already flown one in an aircraft
that glides when the loop is wrong.

## Architecture

| Block | Implementation |
| --- | --- |
| Class | 65–75 mm ducted whoop, 1S — small, safe, indoor-tunable |
| Frame | Printed in PETG on the Prusa; ducts printed with it |
| Motors | 0802 / 1102 brushless, four |
| ESC | Tiny 4-in-1, DShot |
| MCU | STM32F411 board — enough headroom for a 1 kHz loop |
| IMU | MPU6050 over I2C/SPI, sampled at loop rate; ICM-42688 later |
| Filtering | Complementary filter fusing accelerometer and gyro |
| Control | PID per axis — roll, pitch, yaw |
| Output | DShot to four ESCs |
| Loop | Fixed 1000 Hz, timer-driven, jitter measured not assumed |

The loop period is a contract: if the loop ever overruns, the drone finds
out before I do. Loop time gets measured on a GPIO pin with a scope.

### Filtering

Accelerometer gives absolute attitude but is drowned in vibration noise from
the motors; the gyro is clean short-term but drifts. The complementary
filter takes the useful half of each. Getting this wrong is the most common
reason a self-built controller cannot hover.

### Safety

- Arming sequence, motors never spin on power-up
- Failsafe on lost radio link — cut throttle
- Props off for every bench test, and a tethered first flight
- Ducts, which are most of why this class was chosen: a prop that cannot
  reach a wall cannot reach a hand either

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| MCU | STM32 (F4 class) | Enough headroom for a 1 kHz loop |
| IMU | MPU6050, later ICM-42688 | Shared with [[lora-dog-collar-telemetry]] |
| Debug | Scope on a GPIO toggled each loop | Real jitter measurement |
| Telemetry | UART logging of attitude for offline plots | Tuning without guessing |

## Budget

Rough estimates.

| Item | Cost |
| --- | --- |
| Frame and ducts | ~2 € of PETG |
| Motors, 4× 0802/1102 brushless | 20–30 € |
| 4-in-1 ESC, DShot | 15–25 € |
| MCU board (STM32F411) | 8–12 € |
| IMU | 3–10 € |
| 1S LiPo ×3 + charger | 12–20 € |
| Props, several sets | ~5 € |
| Radio TX/RX | 0–80 € |
| **Total** | **~65–105 €**, or ~75 € with the radio already owned |

The radio set is zero if [[rc-car-custom-controller]] or
[[printed-rc-plane]] came first — it is the same transmitter and receiver,
bought once for all three.

Budget for crashes, but not for much: at this size a bad landing costs a
reprinted duct. Motors are the consumable, and they are a few euros each.

## Software / firmware

- Bare-metal or minimal RTOS — the loop must not be at anyone else's mercy
- IMU driver, calibration routine for gyro bias and accelerometer offsets
- Complementary filter, then PID, then motor mixing
- Telemetry stream for offline tuning

## Plan

Nothing on the airframe is bought until step 7.

- [ ] Read raw IMU data, calibrate bias — MCU board only
- [ ] Complementary filter, validate attitude by tilting the board by hand
- [ ] 1 kHz timer loop, measure jitter on a scope
- [ ] Print the frame and ducts, weigh them, check stiffness by hand
- [ ] Single-axis rig — one arm on a hinge, two motors, tune roll PID alone
- [ ] Confirm the loop holds angle against a shove, and recovers
- [ ] Only now: ESCs, LiPo, props — motor mixing with props off
- [ ] DShot to all four, arming sequence, failsafe proven on the bench
- [ ] All axes, tethered
- [ ] Free hover, indoors, inside the ducts
- [ ] Read Betaflight's filtering and mixer code, and recognise all of it

That last box is the actual deliverable. Hovering proves the loop works;
being able to read someone else's flight controller and know why every line
is there is the thing that lasts.

Once attitude control works, the same loop plus the servo experience from
[[rc-car-custom-controller]] is most of a fixed-wing controller — which
[[printed-rc-plane]] puts to use on an airframe that glides rather than
falls when the tuning is wrong.

## Build log

Session entries live in [[custom-flight-controller-drone-log]].
