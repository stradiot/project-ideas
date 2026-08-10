---
tags: [note, course, embedded, linux, systemd, dbus]
created: 2026-08-10
---

# systemd and D-Bus on Embedded

Reference note. Module 9 of [[embedded-linux-course]]. The drivers work; this
is the module about what runs on top of them and how it stays running.

The question it answers: what is the difference between a daemon and a
supervised service, and why does it matter on a device nobody can log into?

## PID 1's actual job

Three things, and only the first is obvious:

1. Start everything else.
2. **Reap orphans.** When a process's parent dies, its children are
   re-parented to PID 1, which must `wait()` on them or the process table
   fills with zombies. A shell script as PID 1 does not do this.
3. Never exit. If PID 1 dies the kernel panics.

The options: BusyBox init (tiny, an inittab, no dependencies between
services), sysvinit (shell scripts, sequential, slow), and systemd.

systemd won on embedded, and the reason is not boot speed — it is that the
things a device needs are built in rather than reimplemented per project:
dependency-ordered startup, restart policies, watchdogs, resource limits,
socket activation, logging, and a device manager that agrees with all of it.
The cost is size, roughly 5–10 MB, which is fine on this board and genuinely
is not on a 16 MB flash part. That is the real decision line, and BusyBox
init remains correct below it.

## Units

A unit is a declarative description of a thing that can be started.
`.service`, `.socket`, `.timer`, `.target`, `.mount`, `.device`.

```ini
[Unit]
Description=Sensor daemon
After=sensor-driver.service

[Service]
Type=notify
ExecStart=/usr/bin/sensord
WatchdogSec=30
Restart=on-failure
MemoryMax=16M
CPUQuota=10%

[Install]
WantedBy=multi-user.target
```

Every line there replaces something that would otherwise be hand-written and
subtly wrong.

### The four features that matter on a device

**Socket activation.** systemd holds the listening socket and starts the
daemon only when something connects, passing the already-open file descriptor
in. Consequences: the daemon costs nothing while idle, startup ordering
stops mattering because the socket exists from boot, and clients never get
connection-refused during a restart. This is what
[[industrial-sensor-node-linux]] describes and it is the most underused
feature in the list.

**Watchdog.** `Type=notify` plus `WatchdogSec` means the daemon must call
`sd_notify(0, "WATCHDOG=1")` periodically or be killed and restarted. Chain
it to the hardware watchdog — systemd can also be configured to ping the SoC
watchdog — and a hung *system* reboots too. On a sealed device on a wall,
this is the difference between a glitch and a site visit.

The subtlety worth knowing: ping the watchdog from the work loop, not from a
timer thread. A timer thread happily pings while the work loop is deadlocked,
which produces a device that is confidently reporting health while doing
nothing.

**Resource control.** `MemoryMax`, `CPUQuota`, `TasksMax`, `IOWeight` are
cgroup v2 limits expressed declaratively. A leaking daemon hits its cap and
gets OOM-killed and restarted, rather than taking down the whole board by
triggering the global OOM killer, which kills something arbitrary and
usually more important.

**Sandboxing.** `ProtectSystem=strict`, `PrivateTmp`, `NoNewPrivileges`,
`CapabilityBoundingSet`, `DeviceAllow`. A daemon that needs one GPIO
character device and nothing else can be confined to exactly that, in the
unit file, with no code changes. This is nearly free and almost nobody does
it.

### Boot time

`systemd-analyze time`, `blame`, and `critical-chain`. `blame` lists slow
units; `critical-chain` shows what was actually on the critical path, which
is the more useful of the two — a slow unit nothing waits on costs nothing.

On embedded the wins are usually: remove services that exist for desktops,
avoid `network-online.target` as a dependency unless truly required, and use
socket activation to move work off the boot path entirely. The baseline from
[[linux-kernel-build-and-config]] exercise 5 is what this gets measured
against.

## udev

The kernel emits a uevent when a device appears; udev applies rules and
creates the node — the loose coupling noted in
[[linux-char-drivers-and-irqs]].

Rules matter for two reasons on a device. **Stable naming**: two identical
USB serial adapters get `ttyUSB0` and `ttyUSB1` in whatever order they
enumerate, which changes between boots. A rule matching on a serial number or
a physical port path creates `/dev/radio` that is always the right one.
**Permissions**: rather than running a daemon as root because it needs a
device node, a rule sets the group and the daemon drops privileges.

```
SUBSYSTEM=="tty", ATTRS{serial}=="A1B2C3", SYMLINK+="radio", GROUP="sensord"
```

`udevadm info -a -n /dev/ttyUSB0` shows every attribute available to match
on, and `udevadm test` explains what the rules did.

## D-Bus

A local IPC bus: processes register objects at paths, objects implement
interfaces, interfaces have methods, signals and properties.

Why a bus rather than a socket: **discovery** (a client finds the service by
a well-known name, no port numbers or paths agreed in advance),
**introspection** (a service describes its own API at runtime, so generic
tools work against a service they have never seen), **signals** (one
publisher, many subscribers, no fan-out code), and **policy** (who may call
what, in configuration rather than in the service).

The system bus is where a sensor daemon belongs. `busctl` is the tool:
`busctl list`, `busctl introspect <name> <path>`, `busctl call`,
`busctl monitor`. Being able to explore a service entirely from `busctl`
before writing a client is the practical payoff of introspection.

For C, `sd-bus` — part of systemd, small, and no additional dependency on a
system that already has systemd. GDBus is the alternative and drags in GLib.

The honest caveat, which [[industrial-sensor-node-linux]] already makes:
D-Bus is the right *local* IPC layer and a terrible deployment. Nothing
outside the board speaks it. Getting the data somewhere useful means a bridge
— here, D-Bus to MQTT, which is what puts the device in Home Assistant and
is what stops it being switched off after the demo.

## Containers, briefly

`systemd-nspawn` and podman work on this board. The question is whether they
should.

Against: a container image is much larger than the application, the memory
overhead is real on 512 MB, and the update story now has two layers that both
need managing. For: genuine dependency isolation between applications from
different teams, and the ability to update one application without touching
the base image.

For a single-purpose device the answer is usually no — the whole image is the
unit and A/B updates in [[embedded-linux-production]] handle it better. For a
gateway running third-party workloads, the answer is often yes. Knowing which
situation is which is the actual skill; "containers on embedded" as a
position is not one.

## Exercises

Building on the PIR driver and BME280 from earlier modules.

1. **A daemon and a plain unit.** C daemon `poll()`ing the driver, logging
   events. `systemctl start`, `status`, `journalctl -u`. *Success: it runs,
   restarts on failure, and its logs are in the journal.*

2. **Kill it repeatedly.** With `Restart=on-failure` and then with
   `Restart=always`. Then make it fail instantly in a loop. *Success: you have
   met the start-limit burst logic and know how to configure it.*

3. **Socket activation.** Convert it: the daemon does not start at boot, and
   starts on first connection with the socket handed in. *Success: `systemctl
   status` shows inactive after boot, active after a `nc` to the port, and
   the daemon never called `bind()`.*

4. **Resource limits, then exceed them.** `MemoryMax=16M`, then make it leak.
   *Success: the cgroup OOM kill in the journal, and a restart — with the rest
   of the system unaffected.* Compare with what happens with no limit set.

5. **Watchdog.** `Type=notify`, `sd_notify` pings, `WatchdogSec=30`. Then hang
   the daemon deliberately. *Success: killed and restarted, unattended, with
   the reason in the journal.*

6. **Deliberate breakage — the lying watchdog.** Move the ping to a separate
   thread, then deadlock the work loop. *Success: the daemon reports healthy
   forever while doing nothing.* This is the failure mode that makes watchdogs
   worthless in the field, and it is worth having built once.

7. **Sandbox it.** `ProtectSystem=strict`, `PrivateTmp`, drop capabilities,
   allow only the device node it needs. *Success: it still works, and
   `systemd-analyze security` gives a materially better score.* Then confirm
   it genuinely cannot write outside its allowed paths.

8. **udev rule.** Stable symlink for a USB serial adapter matched on its
   serial number, plus a group that lets the daemon open it without root.
   *Success: the same name across reboots with two adapters plugged in in
   either order.*

9. **D-Bus interface.** Export the sensor over sd-bus: a property for the
   last reading, a signal on motion. *Success: `busctl introspect` describes
   it, `busctl monitor` shows signals as you wave at the PIR, and a `busctl
   call` reads the temperature — all without a client being written.*

10. **Boot time.** `systemd-analyze critical-chain`, then attack it. Target
    power-on to daemon-ready. *Success: a measured improvement over the
    baseline, and a written account of where the time went.*

11. **The bridge.** D-Bus to MQTT, into Home Assistant as motion and
    temperature entities. *Success: the board is on the wall and the entities
    update.* At this point [[industrial-sensor-node-linux]] is essentially
    built.

## What industry expects here

That a service is a unit file and not an init script, and that the unit file
is where operational behaviour lives — restart policy, limits, dependencies,
sandboxing — rather than being reimplemented inside the daemon.

Specifically probed: socket activation and what it buys; the watchdog chain
from application through systemd to the SoC, and the timer-thread trap;
cgroup limits as containment for the inevitable leak; and journald's
behaviour on a device with no disk, since the default is volatile and logs
that vanish across the reboot you are investigating are a common and
avoidable own goal.

The systemd-versus-BusyBox-init question gets asked, and the expected answer
is about flash size and requirements rather than preference. Below 16 MB of
flash, systemd is not an option and that is the end of it.

## Where this leads

- [[embedded-linux-course]] — the course this is module 9 of
- [[rootfs-buildroot-yocto]] — where the units and rules get packaged
- [[linux-char-drivers-and-irqs]] — the `poll` support this daemon depends on
- [[linux-kernel-debugging]] — when the daemon is slow rather than broken
- [[embedded-linux-production]] — the watchdog and the update path meeting
- [[industrial-sensor-node-linux]] — completed by exercise 11
- [[home-assistant-rotary-controller]] — the other end of the same Home
  Assistant integration, approached from a microcontroller instead
