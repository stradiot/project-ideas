---
tags: [log, home-assistant-rotary-controller]
project: home-assistant-rotary-controller
---

# home-assistant-rotary-controller — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[home-assistant-rotary-controller]].

### 2026-08-19

Picked LCD_RST back up with two independent cross-checks against the netlist
reading of "no GPIO at all": LilyGO's own `examples/utilities.h`, and Bruce's
`pins_arduino.h` — the firmware actually running on the board, so genuinely
third-party even if built on the same schematic. Bruce claimed GPIO40. So did
a LilyGO marketing pinmap image checked separately. But all three of those,
including the schematic's own typed legend from the previous session, also
assign GPIO40 to the I²S word clock a few lines later — the same self-contradiction,
copied three times rather than three independent witnesses. Only the
netlist and LilyGO's own header agreed with each other and with themselves.
That left one way to settle it: pulse GPIO40 low and watch whether the panel
dies.

The first version of that test was wrong in an instructive way. It pulsed the
pin three times, then ran a positive control (`SWRESET` over SPI) to prove the
test could detect a reset at all, then did a full re-init before the final
redraw — so the photographed end state was byte-identical whether or not
GPIO40 had actually done anything. A full re-init recovers a panel from any
reset, which means the only evidence that mattered lived in a transient nobody
was positioned to see. Rebuilt as a latched state machine instead: each phase
(baseline, pulsed-no-reinit, control-no-reinit) holds until the encoder button
advances it, so a still photo is a valid readout. That version gave a clean
answer — the pattern survived the GPIO40 pulse, then genuinely blanked on the
`SWRESET` control — so GPIO40 is not the panel reset, and `BOARD_LCD_RST` is
now `-1`, measured rather than concluded. The blank-but-backlit photo from the
control phase also confirmed something predicted purely from the schematic
back on 2026-08-18: the backlight sits on the AW9364, off the ST7789 entirely,
so killing the panel controller cannot darken it.

Alongside that, the same firmware measured the panel's column offset by
drawing a tick ruler and sweeping three candidate gap values rather than
reflashing one guess at a time — 35 came out clean, meaning the 170-column
glass sits centred in the controller's 240 columns. What looked at first like
a second, row-axis problem — a doubled top edge, shortened bottom corners,
irregular ticks — turned out not to be a geometry bug at all.
`esp_lcd_panel_draw_bitmap()` queues a DMA transaction and returns; it only
blocks once its transaction-queue pool is exhausted. The render loop was
refilling one shared strip buffer while DMA was still reading the previous
strip out of it, so what looked like a row-offset bug was strip 9's content
bleeding into strip 8's transmission. Waiting on the `on_color_trans_done`
callback with a semaphore before touching the buffer again made the artefacts
disappear completely, and the corners and rulers came out clean on the next
photo. Once both were separated from the geometry, the landscape prediction —
that the 35-column offset would move from `x_gap` to `y_gap` because MADCTL's
MV bit transposes which GRAM axis a given command addresses, and `esp_lcd`
applies the two gap arguments to fixed commands with no awareness of MV —
tested clean on the first try.

With the panel closed out, the session moved to the encoder, decoded with the
S3's hardware pulse counter (PCNT) rather than a GPIO interrupt, because a
software handler can miss an edge permanently under load — a slow render or a
disabled-interrupt SPI flush is a window where a quadrature transition arrives
and nothing observes it, and there is no way to resynchronise afterward.
Direction came out backwards on the first flash (a PCB fact — which physical
contact lands on GPIO4 versus GPIO5 isn't specified by any datasheet) and was
a one-line fix. Resolution came out at two counts per detent rather than the
four a naive x4 decode would suggest, and the interesting part was proving why
rather than accepting the number: a genuinely half-cycle-per-detent part and a
single dead PCNT channel both produce exactly 2, and direction still works
either way in the broken case, which is what makes it a real trap. Running two
extra single-line tally units alongside the decoder — one per contact,
counting every raw edge with no direction logic — showed both lines live and
roughly equal, closing that question empirically.

The most interesting result was arithmetic rather than a threshold. Logged the
timing of every bounce burst per contact and found the chatter here runs
tens of microseconds, not the textbook milliseconds — contact ringing, not
mechanical bounce — with contact A about six times noisier than B on this
specific unit. At one measured point the decoder had seen 780 raw edges
against 522 net counts and 261 real detents: 780 minus 522 is exactly 258
cancelled edges, and 261 genuine edges per line means bounce contributed
exactly 258 on its own. The books close to the edge, not approximately. That's
the whole argument for quadrature-plus-accumulator over debounce-then-count
made concrete: a button's value is its instantaneous state, so a bounce burst
is indistinguishable from repeated presses and has to be removed in time; an
encoder's value is an integral of change, so +1/-1 pairs cancel by arithmetic
alone regardless of timing, and the accumulator only reveals whatever it was
sampled at, never the bounce in between. A separate question — whether a slow
poll could catch a burst mid-flight and briefly report a wrong direction —
turned out to be impossible rather than merely unlikely: the count during a
one-line bounce burst is bounded strictly between the pre- and post-transition
values, so a poll landing inside one reads a slightly stale but never wrong
number. With that settled, raised the glitch filter from the example-code
default of 1 µs (an order of magnitude too small to touch anything, since
chatter here runs 4-40 µs) to 10 µs, cutting raw edge traffic by about a third
in hardware.

Two design calls got made and written down rather than left implicit. `SW3`,
the board's dedicated user key, becomes the back button instead of an
encoder long-press — a held gesture gives no feedback while it's building up,
which is the worst possible feel for "get me out of here," and a physical key
is instant. That also leaves encoder long-press entirely free, which matters
for a single-control UI: an unused gesture costs nothing, but a hidden mode
does. And the encoder's input API exposes a delta since the last poll with
the sub-detent remainder carried forward, rather than an absolute count — a
detent is two raw edges that can arrive tens of milliseconds apart, so
discarding the remainder at every poll would silently lose half of a slow,
steady turn. Paired with a decision that Home Assistant calls always use
absolute setters (`volume_set`, `set_temperature`, `brightness`,
`set_cover_position`) rather than step services, on the reasoning that a step
service is an irreversible instruction and would require every transient the
input path produces to be perfect forever, whereas sending the current target
value at a fixed rate makes anything that resolves within one transmit
interval invisible to Home Assistant entirely — correctness becomes a
property of the settled value, which is exactly what the quadrature math
guarantees and nothing more. Both went into `README.md`'s new "Decisions that
outlive their reasons" section since no HA client code exists yet to carry
the comment.

Closed the session by writing a `CLAUDE.md` for the repo, covering the build
commands, the single-port flash/monitor conflict (which cost three failed
flashes today — twice my own leftover capture process, once the user's own
`picocom` holding the port), and the hardware facts from `board_pins.h` worth
repeating because each produces a failure that reads as something else.

Where this leaves it: the display and the encoder are both now driven
directly against `esp_lcd` and PCNT, with every constant in `board_pins.h`
either traced from the netlist or measured on hardware — nothing inherited
from a vendor header anymore. LVGL hasn't been touched yet, so plan item one
isn't finished, only its two hardest sub-problems are. Next is LVGL on top of
proven-good hardware, or the HA WebSocket exploration with `websocat`, either
of which no longer has a suspect pin to rule out first.
