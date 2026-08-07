# Project Ideas

Personal vault for hardware, embedded and infrastructure projects.

## Structure

- `projects/` — one note per project
- `notes/` — reference notes, deep dives, linked from projects
- `journal/` — daily notes
- `templates/` — note templates

## Projects

Grouped by track. Within each, roughly in the order they make sense to
build — several depend on skills or hardware from the one above.

**RF**

- `analog-am-transmitter-receiver` — crystal set → regenerative RX → 27 MHz walkie-talkie pair
- `subghz-linux-router` — SDR capture, own decoder, CC1101 kernel driver, `net_device`
- `subghz-fixed-code-repeater` — store-and-forward range extender for the blinds
- `lora-dog-collar-telemetry` — GPS + IMU collar, hand-packed binary protocol

**Embedded firmware**

- `bare-metal-bootloader` — ARM startup by hand, then a serial bootloader with A/B rollback
- `freertos-pocket-console` — RTOS tasks and queues; ends up as the collar's ground station
- `ble-sensor-node-pcb` — custom nRF52840 carrier board in KiCad, Zephyr board port
- `thread-matter-smart-planter` — Zephyr, Thread Border Router, Matter into Home Assistant
- `thread-matter-noise-sensor` — I2S mic on ESP32-C6, noise events over Thread, live listen over Wi-Fi
- `home-assistant-rotary-controller` — T-Embed as a physical HA controller, encoder + display

**Embedded Linux**

- `industrial-sensor-node-linux` — device tree, IRQ driver, systemd, D-Bus, into Home Assistant
- `usb-device-and-linux-driver` — own USB peripheral and the kernel driver that claims it
- `beaglebone-pru-realtime` — deferred

**Control**

- `rc-car-custom-controller` — RC link decode, actuators, failsafe, a real PID — cheaply
- `custom-flight-controller-drone` — attitude loop and hover; airframe bought last

Deployment target for most of the connected ones is the local Home
Assistant instance. A project that does not end up as something used is a
project that ends up in a drawer.

## Workflow

- Mac: nvim + obsidian.nvim, plain git
- Android: Obsidian mobile + Git plugin (HTTPS remote), pull before editing, push after
- Text only. No binaries, no LFS in this repo.
