---
tags: [note, hardware, procurement]
created: 2026-08-16
---

# Where to Buy the Parts — AliExpress and the Alternatives

Reference note covering every `## Budget` table in the vault at once. What
sent me here: nineteen project notes each carry a budget in euros and none
of them say where the money is spent, so the same question — is this line
safe to order from AliExpress — was going to be answered nineteen times,
badly, one order at a time.

The totals make it worth answering once. Adding up the tables, the parts
that are neither already owned nor deferred come to roughly 900–1400 €
across the whole vault, and something close to half of that is commodity
modules, motors, passives and wire where AliExpress is three to ten times
cheaper than a European distributor and is often the only place the part is
still sold at all. Ferrite rods and air-spaced variable capacitors for
[[analog-am-transmitter-receiver]] are the clearest case: Farnell does not
stock them, and a surplus dealer wants more for one than AliExpress wants
for five.

## The rule that decides each line

Price is not the criterion, and neither is trust in the seller. The question
that separates the two lists is **what a wrong part looks like at the moment
it fails**.

A part whose failure is loud costs a return and three weeks. A motor that
does not spin, an OLED that stays dark, a LoRa module that never gets an
ACK — all of these announce themselves on the first power-up, before any
conclusion has been built on top of them. The bad unit is identified as the
bad unit, which is the only property that matters. Buy those wherever they
are cheapest.

A part whose failure is *quiet* is a different thing entirely, because it
does not present as a bad part. It presents as a bug in whatever is being
learned. A microSD card that silently drops writes above some address shows
up as U-Boot failing to load a kernel — which is exactly the symptom module
2 of [[embedded-linux-course]] exists to teach the diagnosis of, so the
diagnosis proceeds, into the boot chain, for a day. A diode sold as
germanium and actually silicon shows up as a crystal set that is simply
mute, and the search goes to the coil, the antenna and the earpiece, none of
which are wrong. A relabelled STM32 die whose flash controller differs from
the reference manual shows up as a bootloader that writes a sector and reads
back garbage, in a project whose entire content is writing sectors.

That failure mode is already documented here under another name. The collar
remote beeped 70% of the time for months and the first explanation — a
damaged capture — was convincing, internally consistent and wrong, and it
survived a whole session before hand measurement killed it
([[subghz-collar-remote-clone]]). A counterfeit part manufactures that
situation deliberately: a false premise underneath an otherwise correct
chain of reasoning. The vault's whole method is keeping "it works" and "I
understand why it works" apart, and a part that lies about what it is
attacks the second one specifically.

So the test is: **if this part were subtly wrong, would I find out, or would
I blame my own work?** Everything below sorts on that.

## Buy from AliExpress

Loud failures, commodity parts, no downstream reasoning resting on the part
being genuine.

| Part | Projects | Note |
| --- | --- | --- |
| CC1101 module, 868 MHz | [[subghz-linux-router]], [[subghz-collar-remote-clone]] | 3–5 €. Already proven — the built device runs one. The 433 and 868 variants look identical and differ only in the matching network, so buy the labelled band |
| ESP32 / ESP32-C3 / ESP32-C6 dev boards | [[freertos-pocket-console]], [[thread-matter-noise-sensor]], [[uwb-precision-locator]] | 6–15 €. Check flash size and that USB-Serial-JTAG is routed on the C6 |
| LilyGO T-Embed CC1101 Plus | [[home-assistant-rotary-controller]] | 50–80 €, and LilyGO's AliExpress store is the manufacturer's own channel. The largest single line in the vault that is *correctly* bought there |
| Ferrite rods, enamelled wire, polyvaricon and air-spaced variable caps | [[analog-am-transmitter-receiver]] | 10–15 € for all of it. Essentially the only affordable source left |
| Passive assortments, small-signal transistors, 27 MHz crystals | [[analog-am-transmitter-receiver]] | The note already says nothing here needs a tolerance worth paying for, which makes this the one project where cheap parts are the *designed* choice rather than a compromise. Buy several crystals; frequency spread is wide |
| INMP441 I2S microphone | [[thread-matter-noise-sensor]] | 3–6 €, commodity |
| MPU6050 breakout | [[custom-flight-controller-drone]], [[lora-dog-collar-telemetry]] | 3–5 €. The ICM-42688 upgrade the notes prefer later is more variable — buy that one from a named vendor |
| HC-SR501 PIR | [[embedded-linux-course]], [[industrial-sensor-node-linux]] | ~2 €. A rising edge is a rising edge |
| Capacitive soil moisture sensors | [[thread-matter-growbox]] | 1–2 € each. Some v1.2 batches ship with a dead regulator; the note already budgets spares, which covers it |
| SSD1306 / SH1106 OLED | [[freertos-pocket-console]], [[usb-device-and-linux-driver]] | 5–10 €. Listings mislabel which of the two controllers is fitted; both are supported, just probe for it |
| Rotary encoders, buttons, protoboard, breadboard, jumpers, headers, M3 standoffs | most projects | Buy in bulk once, not per project |
| SMD practice board | [[ble-sensor-node-pcb]] | 2–5 €. The note already specifies AliExpress for this |
| ST-Link V2 clone | [[bare-metal-bootloader]] | 5–10 €. Buy one with upgradeable firmware and SWO broken out — the €2 dongles have a locked MCU and no SWO, and SWO is what ITM tracing needs |
| USB-UART converter | [[embedded-linux-course]], [[bare-metal-bootloader]] | Buy CH340 or CP2102 deliberately. Avoid anything sold as FTDI — the clones are the ones FTDI's driver has historically bricked |
| 8-channel USB logic analyzer | [[embedded-linux-course]], [[industrial-sensor-node-linux]], [[rc-car-custom-controller]] | 12 €, the FX2LP clone, supported by `sigrok`. Real ceiling is 24 MSa/s: fine for SPI, I²C, PPM and servo pulses, marginal for sub-µs jitter and not a substitute for a scope |
| Brushless motors, 4-in-1 ESC, servos, props, brushed ESC, chassis, pushrods, horns, hinges | [[custom-flight-controller-drone]], [[printed-rc-plane]], [[rc-car-custom-controller]] | The category AliExpress genuinely owns. Buy from the manufacturers' own stores — BetaFPV, Happymodel, EMAX. For the drone the ESC must have documented DShot, so a named brand rather than an unbranded 4-in-1 |
| RC transmitter + receiver set | [[rc-car-custom-controller]], then reused twice | 40–80 €, and RadioMaster and Jumper both sell direct. Bought once for three projects, so it is the biggest single saving in the vault. Take the 2.4 GHz version — it sidesteps the EU LBT firmware question that the 868/915 ExpressLRS hardware raises |
| SX1262 LoRa modules | [[lora-dog-collar-telemetry]] | 20–30 € the pair, from Ebyte or Heltec direct. Confirm the 868 MHz EU variant and the antenna connector type |
| MOSFETs, connectors, tubing, fans, pumps, LED grow strip | [[thread-matter-growbox]] phase 2 | Everything in that phase except the 12 V supply and the pH probe |
| WS2812 strip | [[beaglebone-pru-realtime]] | 15–30 €, BTF-Lighting direct. One catch that matters here specifically: WS2812B, WS2812B-V5 and SK6812 have different timing windows, and this project's entire claim is a timing figure — so buy a strip whose exact part number is stated, not "WS2812 compatible" |
| USB-C breakout with CC lines exposed | [[usb-device-and-linux-driver]] | ~5 €, passive board, nothing to fake |
| Telescopic and whip antennas | [[analog-am-transmitter-receiver]], [[subghz-linux-router]] | ~10 € |

## Buy from AliExpress, but test on arrival

These are cheap enough to be worth the risk, and each has a specific check
that takes a minute and settles it before anything is built on top.

- **BME280 breakout**, 3–6 €, for [[thread-matter-growbox]] and
  [[embedded-linux-course]]'s IIO exercise. Listings very often ship a
  BMP280 instead — same package, same address, no humidity channel. The
  chip-ID register at `0xD0` distinguishes them: `0x60` is a BME280, `0x58`
  a BMP280. Read it first, before writing any driver code, because a driver
  that reads humidity from a part that has none produces a plausible
  constant rather than an error.
- **u-blox GPS module**, 15–25 €, for [[lora-dog-collar-telemetry]].
  Recycled and relabelled u-blox dies are common and mostly still get a fix,
  which is all this project needs. `u-center` reports the ROM and firmware
  version, and a counterfeit usually reports a combination that does not
  exist. Worth knowing which one is on the collar before blaming the antenna
  for a slow fix.
- **STM32F411 "Black Pill"**, 8–12 €. Fine for
  [[custom-flight-controller-drone]], where the chip runs a control loop and
  a wrong one fails loudly. **Not** fine for [[bare-metal-bootloader]],
  which is the counterexample worth stating: relabelled dies sold as STM32
  (CKS32, CS32 and similar) differ in the flash controller and the option
  bytes, and that project's whole content is erasing sectors, writing them
  and setting option bytes for A/B rollback. A divergence there is invisible
  and looks exactly like a bug in my own code. For the bootloader, a genuine
  Nucleo or Discovery from TME at 12–20 € removes the only variable that
  cannot be debugged.
- **USB Wi-Fi dongle**, 12 €, for [[embedded-linux-course]]'s networking
  module. The chipset *is* the specification here — the module is about
  `mac80211`, and a dongle needing an out-of-tree vendor driver teaches
  none of it. Sellers silently revise the chipset under an unchanged listing
  and photo, so this is only safe if the listing states the VID:PID and the
  seller takes returns. `ath9k_htc` hardware is getting genuinely hard to
  find; `rtl8xxxu` is the realistic fallback.

## Do not buy from AliExpress

Quiet failures, or a downstream conclusion that rests on the part being what
it says.

- **microSD cards**, 12 € for three, [[embedded-linux-course]]. The worst
  part in the vault to get wrong. The module's design is one card to break,
  one known-good and one for A/B slots — the known-good card is the control
  variable in every boot-chain experiment, and a card that lies about
  capacity or drops writes destroys the experiment while presenting as a
  boot bug. Genuine SanDisk or Samsung from a shop with returns. This is a
  4 € saving against a day of debugging the wrong layer.
- **Germanium diodes**, [[analog-am-transmitter-receiver]] stage 1. A
  crystal set has no power supply at all; the only energy in the circuit is
  what the antenna collects, so the detector has to rectify at millivolt
  level. Germanium does, at 0.2–0.3 V forward and with usable curvature well
  below that. Silicon needs ~0.6 V and simply does not conduct on a
  microwatt signal. Listings for 1N34A and OA90 are routinely relabelled
  silicon, and the resulting set is silent with no visible cause. Two ways
  out: buy from a European surplus dealer and check the forward drop on a
  meter's diode range on arrival (0.2–0.35 V germanium, 0.55–0.7 V silicon),
  or use a BAT85 Schottky instead — ~0.2 V, cents from TME, genuine, and a
  perfectly conventional crystal-set detector. The second is the better
  answer and the note should say so.
- **LiPo cells and chargers**, across [[custom-flight-controller-drone]],
  [[printed-rc-plane]], [[lora-dog-collar-telemetry]],
  [[thread-matter-growbox]], [[freertos-pocket-console]] and
  [[uwb-precision-locator]] — 10–55 € a project. Loose lithium cells are
  restricted air cargo, so the ones that do ship come by routes with no
  cell-level QC, and stated capacity is regularly overstated two- or
  threefold. That is fatal to a specific claim rather than merely annoying:
  the growbox's phase 1 deliverable *is* a current figure, and
  [[freertos-pocket-console]]'s v2 lives or dies on a battery number. A pack
  of unknown real capacity makes the measurement meaningless while still
  producing a number. EU hobby shops for RC packs, a real distributor for
  cells.
- **Mains-connected supplies** — the 5 V 2 A for [[embedded-linux-course]],
  the 12 V for [[thread-matter-growbox]], the strip supply for
  [[beaglebone-pru-realtime]]. Isolation and certification on an unbranded
  supply are claims on a sticker, and these run unattended in a flat. There
  is a second reason in the course's own note: the supply is on that BOM
  precisely because *USB power browns out and looks exactly like a boot
  bug*, so a cheap supply that sags under load defeats the only purpose it
  was bought for. Mean Well from TME or Reichelt, or a branded USB PSU.
- **nRF52840 DK**, 45–60 €, [[ble-sensor-node-pcb]]. It is the debug probe
  for three projects and the reason it is bought is the Debug Out header.
  Listings at that price are either the genuine board at no discount or a
  different product — a dongle, or a clone whose SEGGER J-Link firmware is
  exactly what is missing. Mouser, Farnell, DigiKey or TME.
- **DWM3000EVB and DWM3001CDK**, 40–90 €, [[uwb-precision-locator]]. A
  counterfeit UWB module would not announce itself; it would range with an
  unknown constant offset, and the project's phase 1 is a calibration
  against a tape measure, which would absorb the offset and hide it. Qorvo
  distributors, or Makerfabs direct for the EVB.
- **FUSB302 breakout**, ~5 €, [[usb-device-and-linux-driver]]. The chip is
  bought to drive Linux's Type-C/TCPM subsystem, so the register map has to
  match the datasheet the kernel driver was written against. Breakouts with
  a substituted PD controller do not bind, in a way that reads as a
  devicetree mistake. Genuine FUSB302BMPX from LCSC or Mouser is under 2 €;
  put it on the [[ble-sensor-node-pcb]] JLCPCB order rather than buying a
  board.
- **Thread radio dongle for the border router**, 25–40 €,
  [[thread-matter-growbox]]. Connect ZBT-1 from a European reseller. The
  nRF52840 dongle alternative is fine in principle but the AliExpress clones
  vary in flash size and antenna, and the RCP firmware assumes neither.
- **pH probe and buffer solutions**, 45–60 €, [[thread-matter-growbox]]
  phase 2. Cheap probes drift within months and buffers of unknown age are
  worse than no calibration. Deferred anyway — phase 2 is a decision taken
  after phase 1 has run in a pot for a month.
- **Genuine ICs for the custom PCB**, [[ble-sensor-node-pcb]]. Not an
  AliExpress question at all: **LCSC** is the right answer here. Same
  shipping ecosystem and prices, but an actual distributor with genuine
  parts, and it shares a basket with the JLCPCB order the project already
  plans.
- **Raspberry Pi**, 40–80 €, [[industrial-sensor-node-linux]] — approved
  reseller. **BeagleBone Black**, 60–90 €, [[beaglebone-pru-realtime]] —
  distributor; the AM335x board ID EEPROM and the devicetree assume the real
  board. That project is deferred, so it is not a live decision.
- **LW-PLA**, 30–45 €, [[printed-rc-plane]]. The value of foaming PLA is
  entirely in a process-controlled foaming ratio, which unbranded "light
  weight PLA" does not have. eSun and Colorfabb are both real and both sell
  in the EU; filament is heavy and slow to ship from China, so the delivered
  price is usually no better anyway.
- **Pinecil V2**, [[ble-sensor-node-pcb]]. Pine64 have publicly flagged
  counterfeits. From Pine64 direct if it is not already on the bench.

## What I do not know yet

Named plainly rather than written around.

- **Whether an oscilloscope is owned.** [[analog-am-transmitter-receiver]]
  calls one non-negotiable — the AM envelope has to be seen — and
  [[beaglebone-pru-realtime]] wants one to prove its timing claim, but
  neither budget table has a line for it, unlike the RTL-SDR, which is
  marked already owned. If one has to be bought, Rigol, Owon and Hantek all
  sell through their own AliExpress stores at roughly 10–15% under an EU
  dealer, and that discount buys no warranty path and no returns on a
  200 €+ instrument. That is the one category where I would pay the EU
  premium without thinking about it.
- **The Nordic PPK2**, wanted by both [[freertos-pocket-console]] and
  [[thread-matter-growbox]] for µA-resolution current measurement, is in
  neither budget table. It is ~100 € from a distributor and has no
  AliExpress equivalent — a USB power meter does not resolve microamps, so
  there is no cheap substitute, only a different method. Both projects claim
  a current figure, so this is a real gap rather than a nice-to-have.
- **Whether the EU's €150 customs threshold still applies** by the time an
  order is placed. AliExpress is IOSS-registered, so VAT is collected at
  checkout and a consignment under the threshold clears without a handling
  fee; over it, the courier adds one. The EU has been legislating that
  exemption away and I do not know the state of it, so it is worth checking
  before splitting or combining a large order rather than assuming.

## How to actually order

Three practical consequences of the lists above.

Shipping time is the real cost, not money. Two to six weeks to Slovakia
means the constraint is ordering *early*, not ordering cheaply, and the
projects that stall are the ones waiting on a 3 € part. So the sensible
first order is not per project at all — it is a single bench-stock batch of
the things three or more projects share: the RC radio set, a couple of
CC1101s, a handful of ESP32 boards, the logic analyzer, the passive and
connector assortments, breadboard and jumpers. That covers the opening moves
of most of the vault for well under 150 €.

Buy the loud parts in quantity and the quiet ones once, properly. A second
CC1101 costs 4 € and removes "is the module dead" from every future
debugging session; a second microSD card of unknown provenance adds a
variable instead of removing one.

And buy against the order in README's *Up next* rather than against the
whole list. [[analog-am-transmitter-receiver]] and [[ble-sensor-node-pcb]]
are the two named as worth starting, and between them they need ferrite
rods, wire, variable capacitors, germanium diodes or Schottkys, passives,
the SMD practice board, and the nRF52840 DK — one AliExpress basket under
40 € and one distributor order for the DK.

## Where this sits

- [[embedded-learning-curriculum]] — the order the projects are worth doing
  in, which is what decides the order the parts are worth buying in
- [[analog-am-transmitter-receiver]] — the project with the largest gap
  between an AliExpress basket and a distributor one, and the only detector
  diode decision in the vault
- [[embedded-linux-course]] — the 58 € BOM, and the one where the cheapest
  line, the microSD, is the most dangerous
- [[ble-sensor-node-pcb]] — the JLCPCB and LCSC path, which is a different
  supply chain from all of this
- [[bare-metal-bootloader]] — the worked example of the same chip being a
  fine buy for one project and the wrong buy for another
- [[subghz-collar-remote-clone]] — where the failure mode this note sorts
  on is already documented: a convincing wrong premise underneath correct
  reasoning
