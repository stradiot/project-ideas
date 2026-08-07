---
tags: [project, hardware, embedded, control, imu]
status: idea
created: 2026-08-07
---

# Custom Flight Controller — Drone That Hovers

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
| Radio TX/RX | 40–80 € |
| Spare props and one spare frame | 20 € |

Budget for crashes. The first hover attempt rarely leaves the props intact.

## Software / firmware

- Bare-metal or minimal RTOS — the loop must not be at anyone else's mercy
- IMU driver, calibration routine for gyro bias and accelerometer offsets
- Complementary filter, then PID, then motor mixing
- Telemetry stream for offline tuning

## Next steps

- [ ] Read raw IMU data, calibrate bias
- [ ] Complementary filter, validate attitude by tilting the board by hand
- [ ] 1 kHz timer loop, measure jitter on a scope
- [ ] ESC calibration and motor mixing, props off
- [ ] Single-axis test on a gimbal or tether — tune roll PID alone
- [ ] All axes, tethered
- [ ] Free hover

## Build log
