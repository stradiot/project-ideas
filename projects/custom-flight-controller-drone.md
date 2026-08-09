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

Deliberately out of scope: GPS hold, autonomous flight, and anything beyond
attitude stabilisation. Hover is the bar.

### Order of spend

The airframe, LiPo, ESCs and radio are the expensive, breakable part, and
none of them are needed to find out whether the control loop works. So they
are bought last.

The radio link, failsafe, ESC signalling and PID tuning are all learned on
[[rc-car-custom-controller]] first, where a mistuned loop makes a car surge
instead of destroying a set of props. What remains genuinely new here is
the attitude loop — the IMU, the filter, and closing a loop around an angle
rather than a speed. That part gets proven on a bench rig before anything
flies.

## Architecture

| Block | Implementation |
| --- | --- |
| IMU | MPU6050 over I2C/SPI, sampled at loop rate |
| Filtering | Complementary filter fusing accelerometer and gyro |
| Control | PID per axis — roll, pitch, yaw |
| Output | PWM / DShot to four ESCs |
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
| Frame, motors, ESCs, props | 60–120 € |
| MCU board | 10–20 € |
| IMU | 3–10 € |
| LiPo + charger | 30–50 € |
| Radio TX/RX | 0–80 € |
| Spare props and one spare frame | 20 € |

The radio set is zero if [[rc-car-custom-controller]] came first — it is
the same transmitter and receiver.

Budget for crashes. The first hover attempt rarely leaves the props intact.

## Software / firmware

- Bare-metal or minimal RTOS — the loop must not be at anyone else's mercy
- IMU driver, calibration routine for gyro bias and accelerometer offsets
- Complementary filter, then PID, then motor mixing
- Telemetry stream for offline tuning

## Plan

Nothing on the airframe is bought until step 6.

- [ ] Read raw IMU data, calibrate bias — MCU board only
- [ ] Complementary filter, validate attitude by tilting the board by hand
- [ ] 1 kHz timer loop, measure jitter on a scope
- [ ] Single-axis rig — one arm on a hinge, two motors, tune roll PID alone
- [ ] Confirm the loop holds angle against a shove, and recovers
- [ ] Only now: frame, ESCs, LiPo, props — motor mixing with props off
- [ ] All axes, tethered
- [ ] Free hover

Once attitude control works, the same loop plus the servo experience from
[[rc-car-custom-controller]] is most of a fixed-wing controller — the
eventual RC plane, where the airframe is built rather than bought.

## Build log

Session entries live in [[custom-flight-controller-drone-log]].
