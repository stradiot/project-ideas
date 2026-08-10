---
tags: [note, course, embedded, linux, networking, kernel, wifi]
created: 2026-08-10
---

# Networking and `net_device`

Reference note. Module 10 of [[embedded-linux-course]]. The last driver
module, and the one where a radio stops being a device you talk to and
becomes a network interface the whole system can use.

The question it answers: what does it take for `ping` to work over something
you built?

## The stack, from the bottom

```
driver  →  netif_rx / napi_gro_receive
           ↓
        protocol handlers (IP, ARP, …)
           ↓
        netfilter hooks, routing
           ↓
        sockets  →  userspace
```

Downward it is the reverse, with `ndo_start_xmit()` as the driver's send
entry point, a qdisc queueing and scheduling in front of it, and netfilter
hooks on the way.

Two structures carry everything:

- **`sk_buff`** — one packet, plus metadata. Its design is the interesting
  part: the buffer has headroom reserved at the front so each layer can push
  its header on without copying, which is why `skb_reserve` and `skb_push`
  exist and why a driver must allocate with headroom. This is the networking
  answer to everything in [[linux-memory-and-dma]] — clone, share, and
  fragment without copying payload.
- **`net_device`** — one interface, and a `net_device_ops` table that is
  recognisably the same pattern as `file_operations`:
  `ndo_open`, `ndo_stop`, `ndo_start_xmit`, `ndo_get_stats64`.

Writing one is straightforward: `alloc_netdev`, fill in the ops, set the
type and MTU and flags, `register_netdev`. From that moment `ip link` sees
it, an address can be assigned, and the entire IP stack — routing, TCP, DNS,
sockets, tools that have never heard of your hardware — works over it. That
is the payoff for using a subsystem rather than inventing an interface, made
about as concrete as it gets, and the argument from
[[linux-driver-model-and-subsystems]] in its strongest form.

### NAPI

The naive receive path takes an interrupt per packet. Under load that
becomes an interrupt storm where the CPU does nothing but enter and leave
interrupt context — a receive livelock, where throughput collapses as load
rises.

NAPI is the fix: on the first packet, disable receive interrupts and schedule
a poll; drain the queue in that poll with a budget; re-enable interrupts when
the queue is empty. Interrupt-driven when idle, polled when busy, chosen
automatically. Any driver expecting real traffic implements it — for an
868 MHz link at a few kbit/s it is not needed, but implementing it once is
how the mechanism gets understood.

## netlink, and why ioctl is the wrong answer

Configuration is not the data path. The old way was `ioctl` on a socket, with
fixed-size structs — no extensibility, no notification, no way to add a field
without breaking the ABI.

**netlink** replaced it: a socket protocol carrying TLV-encoded attributes,
which means new attributes can be added without breaking old clients, it is
inherently asynchronous, and it supports multicast so subscribers get told
about changes rather than polling. `rtnetlink` covers links, addresses and
routes — it is what `ip` uses, and why `ip` can do things `ifconfig` cannot.
**Generic netlink** is the framework for a subsystem to define its own
protocol, and `nl80211` is the well-known example.

For a driver with its own configuration — the radio's frequency, data rate,
output power — generic netlink is the right channel and a custom ioctl or a
pile of sysfs files is the wrong one. This is directly what
[[subghz-linux-router]] describes.

## Wireless, which is a stack of its own

The single most important distinction, and the one that decides how much
control you have:

- **SoftMAC** — the device does the radio; **`mac80211`** in the kernel
  implements the 802.11 MAC: association, retries, aggregation, power save.
  Drivers here are large but the MAC is Linux's, so behaviour is consistent
  and hackable. `ath9k` is the reference example.
- **FullMAC** — the MAC lives in the device's firmware. The driver is a thin
  shim passing commands to a black box. Most modern Wi-Fi, especially in
  phones and cheap dongles.

Above both sits **`cfg80211`**, the kernel's configuration API, exposed to
userspace as **`nl80211`** over generic netlink. `iw` speaks it; `wpa_supplicant`
speaks it and does the authentication and key management that the kernel
deliberately does not.

**Monitor mode** — receiving every frame including management and control,
with a radiotap header carrying signal strength and rate — is only really
available on SoftMAC hardware, which is why the dongle recommendation
matters. It is also the direct analogue of what an RTL-SDR does in
[[subghz-collar-remote-clone]], one layer up: raw frames instead of raw
samples.

**Regulatory domain** is not optional and is genuinely enforced: allowed
channels and power limits by country, from CRDA and the device's own
regulatory hints. `iw reg get`. The same class of constraint as the 868 MHz
duty-cycle limits that bound [[subghz-linux-router]] — a legal boundary
enforced partly by the stack and partly by the engineer.

## Userspace, and what to run on a device

`ip` for everything (`ifconfig`, `route` and `brctl` are deprecated and less
capable). `nftables` rather than `iptables`. `ss` rather than `netstat`.

Network management on embedded is a real choice: **systemd-networkd** for
static or DHCP configuration that does not change — declarative, tiny, no
daemon to talk to; **connman** or **NetworkManager** when Wi-Fi networks get
selected at runtime and credentials are entered by a user. Static
configuration should not drag in a network manager, and frequently does.

Time is worth a mention because it breaks things silently: chrony or
systemd-timesyncd, and the fact that a board with no RTC boots in 1970,
which makes TLS certificate validation fail in a way that looks like a
network problem and is not.

## Exercises

1. **A virtual `net_device`.** No hardware — a driver that registers an
   interface, loops transmitted packets back to receive. Assign an address,
   ping it. *Success: `ping` gets replies over a driver you wrote.*

2. **Statistics.** Implement `ndo_get_stats64`, verify against `ip -s link`.
   *Success: counters that match what you sent.*

3. **Deliberate breakage — forget the headroom.** Allocate skbs without
   `skb_reserve` and watch a header push corrupt things. *Success: the
   corruption, and an explanation of the layout.*

4. **NAPI.** Convert the receive path. *Success: the same behaviour, with a
   budgeted poll, and an explanation of what livelock it would prevent.*

5. **netlink configuration.** Define a small generic netlink family for the
   driver's parameters, and a userspace tool to set them. *Success: the
   parameter changes from the command line, with no ioctl and no sysfs.*

6. **`rf0`.** Wire the CC1101 driver from
   [[linux-driver-model-and-subsystems]] underneath a `net_device`. Frames in
   and out over 868 MHz, a second board or the existing ESP32 device as the
   other end. *Success: `ping` across the radio link.*

7. **Be honest about it.** Measure throughput, latency and loss on that link.
   *Success: numbers, and a written statement of what this is and is not good
   for.* Carrying IP over a duty-cycle-limited sub-GHz link at a few kbit/s
   is educational rather than sensible — which
   [[subghz-linux-router]] already says openly, and this is the measurement
   that proves it.

8. **Monitor mode.** Dongle into monitor mode with `iw`, capture with
   `tcpdump`, read the radiotap header. *Success: management frames captured,
   with signal strength per frame.*

9. **Regulatory domain.** `iw reg get`, then set it to a different country
   and observe which channels and power levels appear and disappear.
   *Success: an understanding of what is enforced where.*

10. **Trace a packet.** With ftrace, follow one packet from the driver's
    receive to the socket. *Success: a call path, end to end.* This is
    [[linux-kernel-debugging]] applied, and it is the exercise that makes the
    stack stop being abstract.

11. **Configure the network properly.** systemd-networkd for a static
    address, with the daemon from [[systemd-dbus-embedded]] depending on it
    correctly. *Success: it comes up in the right order, every boot,
    including when the cable is unplugged at boot.*

## What industry expects here

Most embedded roles do not write network drivers. Nearly all of them debug
networking, and the expectation is a mental model good enough to say where a
problem is: driver, stack, configuration, or the other end.

Specifically probed:

- **`sk_buff` and the headroom design** — the standard question for anyone
  claiming networking experience.
- **NAPI and why it exists.** Interrupt-per-packet as a scaling failure is a
  concept that generalises well beyond networking.
- **netlink versus ioctl**, and the extensibility argument.
- **SoftMAC versus FullMAC**, because it determines what is even possible
  when a Wi-Fi problem is in the MAC layer.
- **Regulatory compliance**, which is a real constraint on any product with
  a radio in it and one that engineers routinely discover too late.
- Debugging fluency: `ip`, `ss`, `tcpdump`, and knowing that
  `/proc/net/` exists.

## Where this leads

- [[embedded-linux-course]] — the course this is module 10 of
- [[linux-driver-model-and-subsystems]] — `net_device` as the subsystem the
  CC1101 finally belongs in
- [[linux-memory-and-dma]] — `sk_buff` as the networking answer to buffer
  management
- [[linux-kernel-debugging]] — tracing a packet through the stack
- [[subghz-linux-router]] — phase 3, reached
- [[subghz-collar-remote-clone]] — monitor mode is the same idea as an SDR
  capture, one abstraction layer higher
- [[analog-am-transmitter-receiver]] — transmit power and filtering as the
  same species of legal constraint as the regulatory domain, one layer down
