---
tags: [note, course, embedded, hardware, schematic, electronics]
created: 2026-08-17
---

# Reading a Schematic

Reference note. The module that [[embedded-learning-curriculum]] does not
currently have, and the one every course in it quietly assumes. It came out of
[[home-assistant-rotary-controller]], where two sessions were spent recovering
a thirteen-pin map from a vendor PDF and the limiting factor was never the
board — it was not knowing what the drawing was saying.

The question it answers: **what is actually on this PCB, what will the silicon
let firmware do with it, and how do I find either out without trusting
anyone?**

Both halves, because neither is sufficient. The schematic says which pad a
signal reaches; the chip decides what that pad is permitted to be. A pin map
is the intersection, and every course downstream starts from one.

## Where it sits: module zero

**A prerequisite that runs before the first course and belongs to none of
them.** Not a sixth course — it is a week of evenings, not an arc — and not a
module inside hardware design, for the reasons below.

The nearest precedent in the curriculum is USB, the other subject that does
not fit the arc shape, and that one is resolved by *splitting* across three
courses. The resolution does not transfer. USB decomposes because its thirds
are genuinely different subjects; this does not decompose at all, because all
five courses need the identical skill. Splitting it would teach it five times.

The argument that actually decides the position is practical. The curriculum
records a specific stall risk — RF is first, is still an outline, *and an
outline cannot be started.* This module needs no hardware, no fab run and no
new writing, and every course downstream is blocked on it in a way none of
them notices. **It is the thing to do during that stall.** It also front-loads
RF correctly: modules one and two there are a crystal set and a regenerative
receiver, which are circuits to be read before they are built.

## Why it is not part of hardware design

The fourth course in the curriculum covers schematic capture, the power tree,
footprints, stackup and layout. That is *authoring* a board. This is *reading*
one, and they come apart for three reasons worth writing down, because the
instinct is to fold them together and wait.

**It is needed far earlier than it is scheduled.** Every course already
depends on it. Bare-metal firmware starts with a pin map that only a schematic
supplies. The RF course's matching networks are read before they are designed.
The Linux course's own opening module, [[reading-a-soc-trm]], already says it
out loud: *the SoC datasheet says a pin can be `spi0_d0`; only the board
schematic says whether it is wired to P9 pin 21 or to nothing at all.* That
sentence describes a skill the curriculum never teaches.

**It costs nothing.** No KiCad, no fab run, no two-week feedback loop. The
material is boards already on the bench and their published schematics, and
the feedback loop is a multimeter and an afternoon. The fourth course is
expensive and slow; this half of it is neither, and there is no reason for the
cheap half to wait behind the costly one.

**It scores higher than the course it was buried in.** Against the durability
criterion the curriculum is ordered by, authoring skill is split — the physics
is durable, KiCad is disposable. Reading is not split. A schematic is a claim
about where copper goes on one specific board, recoverable from no text that
exists anywhere else, and it is the hardware instance of the one item that
note ranks as *rising*: reading and judging a system I did not write. The
generated-code argument applies with full force. An agent will produce a
plausible pin map for a board it has never seen, in the same confident prose
as a correct one, and nothing but the schematic and a meter can tell them
apart.

So: run it as a short standalone module, early, and leave capture and layout
in the fourth course where they belong.

## What a schematic is, and the four things it is not

A schematic is a **netlist drawn for humans**. It says which pins are
electrically common. That is all it says, and almost every beginner error is
reading something else into it.

It is **not a map of the board.** Position on the page carries no information
about position on the PCB. Sheets are organised by function, and a part drawn
next to another may be at the opposite corner.

It is **not a picture of the wires.** Connectivity is carried by **net
labels**, not by drawn lines. A sheet does not route a line across three pages
to the LCD; it writes `LCD_DC` at both ends, and *the label is the wire*. This
is the single fact that turns pin-map recovery from hunting into a procedure,
and not knowing it is what makes a first schematic feel unreadable.

It is **not a description of what was built.** A schematic describes a design;
a board describes one *build* of it. Which parts are actually fitted is the
BOM's business, and the schematic only hints at it — see the annotations
below.

It is **not physics.** Trace width, layer stackup, return path, coupling and
loop area are invisible here and decide whether the thing works. That is the
fourth course's subject, and the reason a schematic can be perfectly correct
and the board still fail.

### The mechanics, in one pass

| Thing | What it means |
| --- | --- |
| **Net label** | The connection itself. Same text anywhere in the document = same copper. |
| **Reference designator** | `R` resistor, `C` capacitor, `L` inductor, `FB` ferrite bead, `U` integrated circuit, `Q` transistor, `D` diode, `K`/`SW` switch, `J`/`P` connector, `TP` test point. |
| **Value** | What is fitted. `0R` is a wire. `10K` is a resistor. |
| **`NC` / `DNP`** | Not Connected / Do Not Populate. **Footprint on the PCB, nothing placed on it.** |
| **Dashed box** | An option. Usually two parallel paths where exactly one is fitted. |
| **Symbol pin numbers** | The *package* pin, not the signal. A module symbol often prints both, and mistaking one for the other is a standing trap. |
| **Off-page connector** | An arrow or flag carrying a net to another sheet. |

The `0R`-versus-`NC` pair deserves its own line because they are drawn
identically and mean opposite things. Two footprints feeding one node, one
holding a zero-ohm link and one empty, is an **assembly-time build option**:
one PCB layout, several products, selected by what the pick-and-place machine
puts down. Read the value before believing the connection.

## The patterns that cover most of a board

Roughly a dozen idioms account for the overwhelming majority of the passive
components on any embedded PCB. Recognising them is what turns a wall of
resistors into four or five decisions.

### Power

- **LDO.** Linear regulator, VIN/GND/EN/VOUT, sometimes a `BP`/`NR` bypass pin
  taking a small capacitor to filter the internal reference. Cheap, quiet,
  and dissipates the whole voltage difference as heat. Fine for small loads.
- **Switching regulator.** An inductor, a diode or synchronous FET, and bulk
  capacitance. Efficient, noisy, and always identifiable by the inductor.
- **Rail domains and enable pins.** More than one regulator means more than
  one power domain, and an `EN` pin on a GPIO means firmware gates that
  domain. **The rails are where the product's power model is written down**,
  and the domain boundaries tell you which parts can sleep and which have to
  be unpowered.
- **Power-path charger.** For anything with a battery, the "charger" is really
  the system power multiplexer: input, battery and system are three ports it
  arbitrates between, and the system rail is a third thing synthesised from
  whichever source is available — not simply one or the other.
- **Decoupling capacitors.** ~100 nF next to every IC supply pin plus bulk of
  a few µF per rail. Not optional and not noise reduction in the vague sense:
  a supply trace is inductive, an IC's current demand changes in nanoseconds,
  and the local capacitor is the only source fast enough to serve it. Ignore
  them when reading — they are the same everywhere — but notice when they are
  *absent*.
- **Ferrite bead.** ~0 Ω at DC, hundreds of ohms at 100 MHz. Isolates a noisy
  load's supply, or keeps rail noise out of something sensitive. A bead in a
  supply line names the designer's noise worry.

### Protection and switching

- **Reverse-polarity FET.** An N-channel MOSFET in the **negative return**,
  gate on the positive rail. Correct polarity turns it hard on at tens of
  milliohms; a reversed cell turns it off *and* points the body diode against
  the fault. It goes low-side because an N-FET in the high side needs a gate
  above the rail, i.e. a charge pump. One transistor protects an entire board,
  because all current must return through it.
- **Load switch.** A FET gating a rail, often P-channel high-side driven by a
  small N-channel from a GPIO — the level-shift-and-invert pair.
- **ESD clamp diodes.** To rail and to ground on exposed connectors. They also
  exist *inside* every CMOS input, which is why **driving a signal into an
  unpowered chip back-powers it through those diodes** — the rule that decides
  peripheral-rail sequencing.
- **Series resistor on an LED or a signal.** Current limiting, or edge-rate
  damping on a fast line. The value tells you the intended current.

### Signals and configuration

- **Pull-up / pull-down.** The default state of a line nobody is driving.
  10 kΩ for a button, 2.2–4.7 kΩ for an open-drain bus, and a floating input
  is a bug rather than a state.
- **Open-drain bus pull-ups.** I²C and shared interrupt lines can only be
  pulled *low* by their devices; the high level exists solely because of the
  resistor. That is what makes wired-AND, multi-master, clock stretching and
  ACK possible without contention. The resistor value encodes the intended
  speed, since rise time is R × C<sub>bus</sub> against a 400 pF budget:
  ~4.7 kΩ for 100 kHz, ~2.2 kΩ for 400 kHz, ~1 kΩ for 1 MHz.
- **RC on a reset line.** 10 kΩ × 1 µF = 10 ms of delay, holding reset until
  the rails settle, and debouncing the button for free.
- **Voltage divider.** Two resistors making a fraction of a rail. Used for
  battery sensing into an ADC, for setting a chip's configuration by resistor,
  and for **faking a sensor** — a 10 kΩ/10 kΩ divider on a charger's
  temperature-sense pin is a permanent "normal temperature" for a pack that
  has no thermistor. Recognising a defeated safety input is a real skill.
- **Current-sense shunt.** A very low value in a power path — 0.01 Ω, in its
  own footprint, with two sense lines going to a gauge or amplifier. The
  physical basis of every coulomb counter.
- **Strapping pins.** Pins sampled once at reset to configure boot, and used
  as ordinary GPIO afterwards. A pull-up or pull-down on one is a boot
  decision, not a signal.
- **Test points and unfitted headers.** Where the designer expected to debug.
  Worth finding before you need them.

## The electronics that is actually load-bearing

Not a course in electronics — the short list of ideas that the patterns above
are made of, and without which they are memorised rather than understood.

- **Current is a loop.** Everything else follows. It is why one low-side FET
  protects a whole board, why grounds are a subject rather than a symbol, and
  why a return path you did not think about is the fourth course's most
  expensive lesson.
- **Ohm's law and the divider.** Most resistor questions on a schematic are
  one or the other. If a resistor's purpose is unclear, compute the current
  through it and the answer usually appears.
- **A capacitor passes change and blocks DC; an inductor is the opposite.**
  Decoupling, filtering, beads and the RC delay are all this one sentence.
  τ = RC is the only formula needed for most of it.
- **The MOSFET as a switch.** V<sub>GS</sub> versus threshold, "logic-level"
  meaning fully on at 2.5 V rather than 10 V, R<sub>DS(on)</sub> in
  milliohms, and the **body diode** — a parasitic diode inherent to the
  structure, which conducts whenever the channel is off and the polarity suits
  it. Half the FET patterns above are really statements about which way that
  diode points.
- **The BJT as a switch.** Current-controlled, so a base resistor and usually
  a pull-down to hold it off. The 1 kΩ/10 kΩ pair on a transistor base is this
  and nothing more.
- **Diode drops.** ~0.3 V Schottky, ~0.7 V silicon. The reason a FET beats a
  diode in a battery path is the drop times the current, permanently.
- **Power is I²R.** Why 10 mΩ of FET is nothing and 300 mV of diode is real,
  and how to tell whether a component is being asked to dissipate more than it
  can.

## The other side of the pad

A schematic says which pad a signal reaches. It does not say what that pad is
*allowed to be*, and that half is a fact about the silicon. The two together
are what a pin map actually is, and neither alone is enough.

### Three architectures, and all three are on the bench

How a chip's internal peripherals reach physical pins has essentially three
answers, and the boards already owned happen to cover all of them.

| Architecture | Example | What you get |
| --- | --- | --- |
| **None** | ATmega328P (Arduino Uno) | Each pin has one alternate function, fixed in silicon. SPI is on those three pins, permanently. |
| **Fixed table** | AM335x (BeagleBone), most STM32 | Each ball has a menu of up to ~8 modes; pick one per pin. A menu, not a free choice. |
| **Crossbar** | ESP32-S3 / C3 / C6 | A matrix routes almost any peripheral signal to almost any pad, by register. |

The tradeoffs are real and they run in both directions:

- **No mux** is the simplest silicon and the fastest path — a dedicated wire
  has no routing logic in it — but the *board* is then dictated by the chip.
  Two peripherals whose pins collide simply cannot both be used.
- **A fixed table** is the compromise, and its characteristic failure is the
  conflict: the peripherals you want are each available, but not on pins that
  are simultaneously free. This is the entire reason a pin-planning tool like
  STM32CubeMX exists and has a conflict solver. On these parts **pin
  assignment is schematic-time work** — you plan the mux before the layout,
  because afterwards it is a respin.
- **A crossbar** buys routing freedom with silicon area and propagation delay.
  The signal crosses a matrix instead of a wire, and often gets resynchronised
  on the way, which costs both time and jitter.

**And the crossbar's cost is the thing that bites.** Because the matrix is
slow, these chips keep a bypass — a direct, hard-wired path for one specific
pin per peripheral signal, which is what the ESP32 calls IO_MUX. Take it and
the bus runs at full speed; miss it by even one signal and the whole bus falls
back to the crossbar at roughly half. That is not hypothetical here: on the
T-Embed the SPI clock landed on GPIO11, which is the MOSI slot rather than the
CLK slot, so the display bus is crossbar-routed and capped near 40 MHz instead
of 80. Nothing in the firmware says so.

**The generalisation worth keeping: the signals a crossbar *cannot* carry tell
you where the timing is tight.** USB D+/D−, the crystal inputs, the octal
PSRAM and flash lanes, the ADC channels — none of these are muxable on any of
these parts, because a matrix cannot meet their timing or their analog
requirements. Muxing exists exactly where timing is loose. When you find a
signal that is pinned down on an otherwise flexible chip, that is the
datasheet telling you something about physics.

The consequence for reading a board is the one this project learned the hard
way: **on a crossbar part, "which pin drives the LCD chip-select" is answered
only by the schematic or the running board, never by the datasheet.** On a
fixed-table part the datasheet narrows it to a menu, and on the ATmega it
answers outright. Knowing which kind of chip you are holding tells you how
much discovery the job needs.

### What the datasheet's pin table actually has columns for

"GPIO number" is one column of many, and the others are where the surprises
live. Any given pad may or may not be:

- **Analog-capable**, and often only for one specific ADC unit
- **5 V tolerant** — a property of the pad's clamp structure, not of the chip
- **High-drive**, able to source more current than its neighbours
- **RTC- or wake-capable**, which decides whether it can wake the part from
  deep sleep, and whether it can hold a level while asleep
- **A strapping pin**, sampled once at reset to configure boot
- **Bonded to internal flash or PSRAM** and never brought out at all — on an
  ESP32-S3 with octal PSRAM this costs a dozen pins that appear in the
  numbering and do not exist on the package

### What firmware configures that no schematic shows

Every one of these is invisible in the drawing and changes the electrical
behaviour of a pin:

- **Direction, and open-drain mode** — an output that can only pull low
- **Internal pull-up / pull-down.** Typically 30–50 kΩ and loosely specified,
  which is *why* external resistors exist anyway: a 10 kΩ external is
  predictable, and an I²C bus at 400 kHz cannot be pulled up by 45 kΩ at all.
- **Drive strength**, which sets edge rate — and edge rate sets both ringing
  and radiated emissions. Turning drive strength down is a real EMC fix.
- **Slew rate limiting**, same family
- **Input hysteresis (Schmitt trigger).** Without it a slow edge crosses the
  threshold repeatedly and one button press becomes eleven interrupts.
- **Hold during sleep.** Pad state is released when the part sleeps unless
  latched; a peripheral rail that drops in light sleep is this bug.

**Reset state is high-impedance input**, on essentially every part. That is
the fact behind board bring-up: at power-on nothing is driven, so anything
that must be at a defined level needs an external resistor, and anything
firmware must assert is not asserted yet.

## What else lives at this boundary

The map of adjacent subjects — things that are neither schematic nor firmware
but decide whether firmware works. Listed with the *bug each one produces*,
because that is how they will first be met.

- **Clock gating.** Peripherals wake up with their clocks off. A register
  write to a gated peripheral is silently discarded, or reads back zero, and
  the peripheral looks broken. This is the single most common "my driver does
  nothing" bug on every SoC, and it is why [[reading-a-soc-trm]] insists the
  integration section is the part not to skip.
- **Oscillator accuracy.** An internal RC oscillator is ±1–2 % over
  temperature; a crystal is tens of ppm. UART tolerates roughly 2 % total
  error before framing breaks, USB tolerates 0.25 % and therefore *cannot*
  run from an RC. A board with no crystal has already decided things about
  what its firmware can do.
- **Brownout and supply transients.** A CPU resets when the rail dips, and the
  dip is usually caused by the firmware's own radio burst. The bug presents as
  a random reboot in unrelated code, which is why the power section matters to
  software people.
- **Bus recovery.** I²C can wedge: a slave interrupted mid-byte holds SDA low
  forever, and no amount of driver retry helps. The fix is to clock SCL nine
  times by bit-banging to flush the slave's shift register. Likewise an
  unpowered device on a shared bus drags it through its own clamp diodes.
- **Level shifting.** Two voltage domains meeting need a translator, and for
  open-drain buses the standard answer is one MOSFET per line rather than a
  logic buffer — because the shifter must be bidirectional without knowing
  who is driving.
- **The ADC front end.** A reference voltage, an input impedance and a sample
  capacitor that must charge through the source. A battery divider built from
  1 MΩ resistors reads low and drifts, and the code is fine.
- **Debug transport.** SWD or JTAG runs on pins that can usually be
  reconfigured away — and firmware that does so on boot locks you out of your
  own board. Knowing the recovery path before it is needed is the lesson, and
  it is the same lesson as the strapping pins.
- **eFuses and OTP.** One-way configuration burned into the part: flash
  encryption, secure boot, disabling the download stub. Irreversible, and the
  place where a wrong bit ends the board's life.
- **Reset sources and watchdogs.** Which of power-on, brownout, watchdog,
  software or debugger caused the last boot is readable, and is the first
  question to ask about any unexplained restart. It is also occasionally
  lied to by the tooling.
- **EMC.** Emissions come from edges and loop area, and both are things
  firmware can change — clock frequency, drive strength, whether a peripheral
  runs at all. A device that fails certification is failing on decisions taken
  in code as much as in copper.

## Ground truth

The vault's rule is that a tool which has not been run against a known answer
is not evidence. A schematic is a tool in exactly that sense: it is a document
about a board, written by someone else, possibly for a different revision. The
T-Embed work already found a published pin that was flatly wrong, and the
whole point of that catch was that it was checked.

Five ways to check a reading, in rough order of how conclusive they are:

1. **Continuity on the actual board.** A multimeter in continuity or diode
   mode settles "is this net really that pin" in seconds, and it is the only
   method that tests the board in hand rather than the drawing.
2. **Ask the chip.** Most SPI and I²C parts answer an identifying register —
   the CC1101's `PARTNUM`/`VERSION` at 0x30/0x31, for instance. A part that
   identifies itself over the bus proves the bus, the chip select and the
   pin map all at once.
3. **Measure a rail with the peripheral domain toggled.** Proves an enable pin
   does what the schematic claims.
4. **Photograph the PCB against the DNP list.** An unpopulated footprint is
   visible to the eye. This is the direct test of every build-option claim.
5. **A second independent source.** Vendor firmware headers, another board
   revision. Useful, and weakest of the five: it is somebody else's reading,
   not a measurement — and its value is entirely in whether it *disagrees*.

The habit that matters: **write down where each fact came from, next to the
fact.** A pin annotated with the net name and sheet it was read from can be
argued with later. A bare number cannot.

## Exercises

No new hardware. Everything below runs on boards already owned and their
published schematics, plus a multimeter.

The core is one board read completely, because depth on one beats a survey of
five. The ladder after it is the survey, and it is what turns a list of
patterns into judgement — the same four problems solved five different ways,
by teams under different constraints.

### Core: one board, completely

The T-Embed CC1101 Plus and LilyGO's schematic.

1. **Finish a pin map from a vendor PDF.** Recover every GPIO assignment on
   the board, and for each one record the net name and the sheet it was read
   from. *Success: a header where no entry is a guess, and every entry can be
   defended by pointing at a page.*

2. **Draw the power tree from memory.** After reading it once, redraw it
   closed-book: sources, regulators, every rail, every enable, and which
   domain each peripheral is on. *Success: a diagram that survives being
   checked against the PDF.* This is the exercise that converts a page of
   symbols into a model.

3. **Explain the rail split.** For a board with more than one 3.3 V domain,
   say *why* each peripheral is on the domain it is on. *Success: a rule that
   predicts the assignment of a part you have not looked up yet.* On the
   T-Embed the rule is "can this part turn itself off?" — parts with a
   software low-power mode sit on the always-on rail, parts with no off at all
   get the rail cut.

4. **Find every build option.** Locate all `NC`/`DNP` parts and dashed-box
   alternatives, then photograph the corresponding footprints on the real
   board. *Success: an empty pad matched to each NC, and at least one case
   where the schematic alone would have given the wrong answer.*

5. **Verify three claims with a meter.** Pick three schematic assertions — a
   continuity, a pull-up's presence, a rail's voltage with an enable toggled.
   *Success: three measurements, and a note on any that disagreed.*

6. **Compute four passives.** Take four resistors on the board and derive what
   they are for from their value: the current through an I²C pull-up when the
   line is low, the current an LED series resistor sets, the voltage a shunt
   develops at full load and the power it dissipates, the delay of an RC.
   *Success: four numbers with units, and a sentence each on what would break
   if the value were ten times larger.*

7. **Identify a part by its pin signature.** Find an IC whose marking is
   unsearchable — module part numbers usually are — and name what is inside it
   from its pins alone. *Success: an identification, plus the register read
   that would confirm it definitively.*

8. **Predict a failure, then cause it.** Before writing any driver, predict
   what happens if the peripheral rail is never enabled: which calls fail,
   which succeed, and what the display does. Then run it. *Success: the
   prediction matches — including the uncomfortable part, that an SPI write
   into an unpowered chip returns success.* This is the exercise that teaches
   why "the API returned OK" is not evidence.

9. **Score yourself against the vendor's firmware.** Only after 1–8: diff your
   recovered pin map against the board's reference code. *Success: a count of
   agreements, and every disagreement resolved by measurement rather than by
   deferring to either source.*

### The board ladder

Five boards already on the bench, in increasing order of how much is hidden.
Each adds a class of pattern the previous one does not have, and the T-Embed
sits in the middle rather than at the end.

| Board | Adds | Why it is at this rung |
| --- | --- | --- |
| **Arduino Uno clone** | The basic passives, visible | One sheet, large parts, traceable by eye and meter without the PDF |
| **ESP32 devkit, microUSB** | Bridge chip, auto-reset logic | A circuit that implements a *decision* out of two transistors |
| **ESP32-C3 / C6 devkit** | The same problem, solved later | Design evolution — what the newer answer costs |
| **T-Embed CC1101 Plus** | Battery, power path, rail domains | A product rather than a devkit; multi-sheet |
| **BeagleBone Green** | PMIC, DDR, boot straps, multi-rail | A professional design with a System Reference Manual |

**10. Arduino Uno — the power mux and the reset capacitor.** Trace how the
board chooses between the barrel jack and USB: a comparator watching a divided
VIN against a reference, driving a P-channel MOSFET that gates the USB rail.
*Success: predict what happens with both plugged in, and explain why a diode
OR was not good enough.* Then find the 100 nF capacitor between the
USB-serial chip's DTR line and the ATmega's reset. *Success: explain why it is
a capacitor and not a wire — and what would break if it were a wire.* That one
component is "a capacitor passes change and blocks DC" made physical, and it
is the ancestor of every auto-reset circuit below. Finish by finding the
polyfuse and the crystal's load capacitors, and saying what each protects or
sets.

**11. Arduino Uno — verify without the schematic.** Pick five nets and
establish them by continuity alone, writing each down before opening the PDF.
*Success: five correct, or a specific reason for each miss.* This is the only
board where the copper is visible enough to make that honest, which is exactly
why it is the rung to do it on.

**12. ESP32 devkit — read a decision made out of two transistors.** The
auto-reset circuit cross-couples DTR and RTS through two NPN transistors onto
`EN` and `GPIO0`. *Success: the truth table of DTR/RTS against EN/IO0, and an
explanation of why the cross-coupling is necessary — neither line alone may be
able to hold both.* The whole circuit exists to defeat a race, and seeing that
is the point. While there, find the `EN` pull-up and its capacitor: the same
10 kΩ × 1 µF power-on-reset pattern that appears on the T-Embed's reset
button.

**13. ESP32 family — one problem, three answers.** Compare how the old ESP32
devkit, the C3/C6, and the T-Embed each get a host into download mode: bridge
chip plus transistor pair, native USB Serial/JTAG, or native USB with no
auto-reset at all. *Success: name what each answer costs.* The interesting one
is already recorded in this vault — native USB removes a part and a BOM line,
and gives up the ability to force a reset over DTR/RTS, because the USB
peripheral now lives inside the chip that has crashed. That is why the T-Embed
needs BOOT held by hand.

**14. BeagleBone Green — a power tree with a state machine in it.** The
TPS65217C PMIC replaces the discrete regulators of every board above. *Success:
every rail it produces, what each one feeds, and the power-up sequencing
requirement it enforces.* This is the step from "two LDOs and an enable pin" to
a device that must bring rails up in a specified order — and the first board
here where getting the order wrong damages something.

**15. BeagleBone Green — boot order, written in resistors.** Find the SYSBOOT
straps and read the boot order they encode, then work out what the boot button
does electrically. *Success: the boot device order as a list, and a sentence on
what the button changes.* This is the direct hardware counterpart of
[[reading-a-soc-trm]] exercise 5 and the premise of
[[linux-boot-chain-uboot]] — the boot chain that module traces in software is
configured here, by passives, before any code runs. Also count the rails and
their voltages, and find the DDR3 termination reference: memory needs a supply
nothing else on the board needs, and it is worth knowing why before designing
anything.

### Capstone

**16. Three answers to pin muxing, on three boards you own.** Take one
peripheral — SPI — and answer the same question on each: *which pins can carry
it, and who decided?* On the ATmega328P the answer is a single fixed triple.
On the AM335x it is a menu per ball, found in the control module chapter. On
an ESP32 it is almost any pad, plus one privileged set that is faster.
*Success: three answers, and a statement of what each architecture costs the
board designer and what it costs the firmware.* Then find, on the ESP32, three
signals that **cannot** be muxed at all, and say what they have in common.
*Success: the observation that muxing exists exactly where timing is loose —
USB, crystals, PSRAM lanes and ADC inputs are pinned down because a matrix
cannot meet their requirements.*

**17. Catch a mux conflict before it is a respin.** On a fixed-table part,
pick three peripherals you would want simultaneously and find a pin assignment
that satisfies all of them — or prove none exists. *Success: either a working
assignment written down, or a demonstration of the conflict.* This is the work
that has to happen at schematic time on such parts, and it is the reason pin
planners have conflict solvers.

**18. Find the clock gate.** Take any peripheral on any of these boards, and
find in the reference manual every thing that must be true before a register
write to it does anything: clock enabled, reset released, pin muxed,
interrupt routed. *Success: a list, with the chapter each item lives in.*
They will be in three or four different chapters, and that separation is the
answer to why a correct-looking driver does nothing at all.

**19. The same four problems, five ways.** Build one table: rows are the five
boards, columns are *power in*, *protection*, *regulation*, *reset and
download*. Fill every cell from the schematics. *Success: for each column, an
explanation of why the answers differ that appeals to cost, size, battery or
production volume — not to one design being better.* This is where "design
pattern" stops meaning "thing I have seen" and starts meaning "choice under a
constraint", and it is not reachable from any single board.

**20. Cross the line into authoring, once.** Take a datasheet's typical
application circuit and redraw it as a schematic fragment with real
designators and values. *Success: a fragment you could hand to someone else.*
The handover point into the hardware design course, and the only exercise here
that needs a tool.

## What industry expects here

That a schematic is something you open rather than something you ask about.
The visible difference is at the first bug: an engineer who says "the driver
is fine, that peripheral's rail is gated by a GPIO nobody asserts" in ten
minutes is doing something an engineer who spends two days on the driver
cannot do at all.

Four specific things get probed. Being able to read a power tree, because
every battery product has one and every one of them has a sequencing bug in
it. Knowing that current returns, because the follow-up question after any
grounding answer is where the return path went. The DNP habit — having been
bitten once by a schematic that described a build the board in hand was not.

And the fourth is the most common debugging question in the field, asked in
some form in almost every embedded interview: **"the peripheral does nothing
and the code looks right — what do you check?"** The expected answer is a
list, not a guess: is its clock gated on, is its reset released, are the pins
muxed to it rather than to something else, is the rail that powers the far end
actually up. Every item on that list lives in a different chapter of a
different document, and none of them is visible in the code that is failing.

## Where this leads

- [[embedded-learning-curriculum]] — the note this module is missing from;
  the argument for pulling it out of the fourth course is at the top here
- [[reading-a-soc-trm]] — the same skill one level up, and the note whose
  "only the board schematic says whether it is routed" line this one answers
- [[linux-boot-chain-uboot]] — the boot order that module traces in software is
  set by the strap resistors in exercise 15, before any code runs
- [[ble-sensor-node-pcb]] — where the hardware design course's fragments
  become one board that is actually ordered, and where reading turns into
  authoring
- [[home-assistant-rotary-controller]] — where the gap was found, and the
  source of every worked example above
- [[subghz-linux-router]] — a board whose radio front end is the natural
  second schematic to read, once matching networks mean something
