---
tags: [log, home-assistant-rotary-controller]
project: home-assistant-rotary-controller
---

# home-assistant-rotary-controller — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[home-assistant-rotary-controller]].

### 2026-08-19

Picked the render-loop question back up and got two things explained before
stalling on a bigger one. First, what a "managed component" actually is in
ESP-IDF: everything in the build — mine or Espressif's — is a component, a
directory with a `CMakeLists.txt` calling `idf_component_register()`; `main`
is the one special case that implicitly links every other component in the
build, which is why `main/CMakeLists.txt` names no dependencies and still
pulls in LVGL. What the component manager adds on top is declare-and-resolve
instead of hand-vendoring: `main/idf_component.yml` states a version
constraint, a Python tool the CMake configure step invokes resolves and
downloads a matching release from Espressif's registry into
`managed_components/`, and `dependencies.lock` records both the resolved
version and a hash of what actually landed, checked against the package's own
`CHECKSUMS.json`. The directory name (`lvgl__lvgl`) is the namespace/name pair
flattened with `__`, and it's that directory name the build system treats as
the component's own name.

Then back to the render loop. LVGL 9 keeps all its mutable state — display
list, timer list, object tree, its own TLSF heap — behind one global struct
with no internal locking unless `LV_USE_OS` is set, so two tasks calling into
it concurrently don't race an int, they corrupt a free list or a display's
invalidated-area array, and the failure surfaces later as a wild pointer
rather than at the racing call. Between the two ways to make that safe — a
recursive mutex around every call site, or letting only the render task ever
touch `lv_*` and having everything else post to a queue — the ownership model
won on the grounds that it makes the wrong thing structurally impossible
rather than merely wrong at every site forever, including ones not written
yet. That settled, the queue's payload shape needed deciding: a message can
describe an operation on a widget ("set label text") or a fact about the
world ("entity N now reads X"), and the second is the one worth having,
because its type count is bounded by the number of data sources rather than
the number of widgets — the render task alone knows the widget tree exists,
and adding a screen adds zero message types. Doorbell-plus-cache followed
from that: the network task doesn't hand the render task data, it writes
into a shared cache and rings a fixed, cheap "something changed" doorbell;
the render task decides what to redraw by reading the cache, not from what's
in the message.

That's where it stalled. The payload-length question — fixed struct per
message vs. something that needs a pointer and a lifetime — turned out to
depend entirely on what fields the screen shows and how entities get named,
and none of that is decided anywhere. It surfaced concretely: HA's
per-domain attributes that a real profile table needs (`source_list` on a
`media_player`, `fan_modes` and `hvac_modes` on a `climate` entity,
`effect_list` on a `light`) are all variable-length arrays of strings, not
scalars, and the plan's own stated requirement — bind an entity by something
stable in Home Assistant rather than hardcode its `entity_id`, so replacing a
sensor is an HA config change rather than a reflash — makes `entity_id`
itself a piece of runtime string data with an unknown length, resolved at
connect time rather than known at compile time. Three sessions deep into
board bring-up and one session into LVGL, there still isn't a written answer
for what domains this device controls, what's on the glass for each, or how
staleness and rejected optimistic updates get shown — the render-loop and
message-shape questions are all downstream of that and were being decided by
implementation convenience instead.

So the session stopped there rather than pushing a data-model decision that
would only have to be redone. What got built instead is a 27-question
requirements questionnaire, seven sections, each question offering lettered
options plus a free-answer row and a line naming what the answer downstream
decides — entity set and domains, binding mechanism, the one-knob-one-button
state machine, the on-screen field list, staleness/reconciliation behavior,
and scope boundaries. Four of the questions can't fully close without the
plan's own `websocat`-against-HA session first, since they depend on what the
WebSocket API actually returns rather than what's assumed.

Nothing in the repo changed this session — no commits, no code. The
render-loop and message-shape work from earlier in the day stands as
written, just confirmed as premature. Next step is the requirements session
itself, working through the questionnaire before touching the render loop
again.

### 2026-08-19

Moved from proven hardware to LVGL's architecture, without writing any
application code yet. The first question was what LVGL actually owns: not
the framebuffer — the ST7789 keeps its own GRAM and refreshes the glass from
it independently — but a draw buffer, a staging area LVGL renders into and
hands off through a flush callback, one chunk at a time. Its size is the
whole design decision. Worked the numbers from both ends: 320×170×2 bytes is
108,800 bytes for a full RGB565 frame, and at the crossbar-routed bus's
current 20 MHz that's 43.5 ms to shift out, 46 fps ceiling. Against that,
LVGL's own recommendation for partial mode is roughly a tenth of the screen,
10,880 bytes, close to the 20,480-byte strip buffer already built for the
tearing fix. Landed on partial render mode, two buffers of about 1/10th
screen in internal SRAM, no PSRAM — the arithmetic (11 KB at 20 MHz is 4.4
ms per chunk, 227 chunks/s, 22.7 full screens/s) held up on its own, and 22
KB is noise against the roughly 280–300 KB of internal heap expected free
after Wi-Fi and TLS.

The more useful correction landed on top of that number. Partial mode
doesn't render a fixed fraction of the screen every frame — LVGL tracks
dirty rectangles, so a widget that changes invalidates only its own
bounding box, and the 43.5 ms full-frame figure is the cost of a screen
*transition*, not steady state. A label ticking from `21.5` to `22.0`
invalidates maybe 8,000 bytes, one chunk, ~1.6 ms — a fiftieth of the
worst case. That reframes the buffer choice: it isn't a compromise against
a bigger one, because a bigger buffer would only help the transition case,
which is rare. Two things still cost more than the ideal and are within my
control later: invalidation is bounding-box granularity, not pixel-exact,
so a full-width row with three changed digits invalidates the whole row;
and any transparency forces LVGL to recompose everything underneath it, so
opaque backgrounds are the cheap default. `LV_USE_REFR_DEBUG` tints redrawn
regions on the panel itself, which is the tool for actually seeing this
rather than reasoning about it.

From there the question became power, since this is a handheld remote and
whatever runs the render loop runs indefinitely. The reflex answer —
hand-wire LVGL instead of using `esp_lvgl_port` — needed justifying rather
than assuming, so I read the port layer's actual source instead of guessing
from memory, and one thing I'd said before reading it turned out wrong: its
task loop isn't a fixed-rate poller, it blocks on a FreeRTOS event group and
wakes on input, which is already the good shape. What's actually different
is the tick. LVGL needs wall-clock time, and there are two ways to supply
it. The port layer *pushes*: a periodic `esp_timer` fires every 5 ms,
forever, calling `lv_tick_inc()`, whether or not anything is happening on
screen. LVGL 9 also supports *pull*, `lv_tick_set_cb()`, where LVGL asks for
elapsed time via a callback backed by `esp_timer_get_time()` — a counter
that's running anyway — so no periodic timer exists at all. The port layer
still uses push because it also has to support LVGL 8, where the pull API
didn't exist.

That distinction turned out to gate something structural rather than
marginal. ESP-IDF's automatic light sleep rides on FreeRTOS tickless idle,
which only engages once the idle task can prove a run of
`CONFIG_FREERTOS_IDLE_TIME_BEFORE_SLEEP` ticks (default 3) with nothing
pending — 30 ms at the stock 100 Hz tick rate. A timer due in 5 ms caps the
provable idle window at 5 ms, which never satisfies 30 ms, so light sleep
never engages at all — not degraded, switched off. The pull tick removes
the wake source itself rather than requiring a `lvgl_port_stop()` to be
remembered later, which settled hand-wiring LVGL as the call.

Chasing the same source turned up why the port loop ends in
`vTaskDelay(1)`, which matters because a hand-wired loop has to solve the
same problem. Its blocking call, `xEventGroupWaitBits`, is level-triggered
and sticky: it returns immediately if a requested bit is already set,
which under sustained input (a knob spun hard) means the producer sets bits
faster than the loop clears them and the wait stops blocking at all. LVGL
runs at priority 4 by default, and FreeRTOS never preempts a runnable task
for a lower-priority one, so a spinning priority-4 task starves everything
below it, including the idle task — which is exactly what the task
watchdog (`CONFIG_ESP_TASK_WDT_TIMEOUT_S=5`, watching IDLE0) exists to
catch. `vTaskDelay(1)` is a blunt fix applied at the bottom of the loop
rather than at the cause — but it's *also* a value in ticks, not
milliseconds, and the component's own test config runs at
`CONFIG_FREERTOS_HZ=1000`, where that's 1 ms. On ESP-IDF's stock 100 Hz
default it's 10 ms per iteration: identical line, ten times the cost, a
correct-on-my-machine bug hiding in one call. The takeaway for the loop
still to be written: block on a queue rather than an event group, since a
queue is edge-triggered and drains one item per receive, which bounds the
work per wake regardless of producer speed.

That pointed at raising the tick rate, which needed its own cost check
before going in the config. Each tick is an interrupt plus a possible
context switch, order ~3 µs, run per core on the dual-core S3. Going from
100 Hz to 1000 Hz adds 900 ticks/s/core, ~2.7 ms/s, about 0.27% CPU duty
per core — bounded from above at roughly 0.1 mA against an ~80 mA active
budget, under 0.15%. The more interesting effect points the other way:
`IDLE_TIME_BEFORE_SLEEP`'s 3-tick window drops from 30 ms to 3 ms, and an
encoder's inter-detent gaps (tens of milliseconds of nothing happening)
are long enough to start qualifying for light sleep at the higher rate but
never do at 30 ms — so 1000 Hz plausibly makes active duty *cheaper* once
`CONFIG_PM_ENABLE` is actually on, though that's a measurement rather than
something the arithmetic alone proves. Settled on `CONFIG_FREERTOS_HZ=1000`
on the strength of the bounded direct cost alone, with the second-order
claim left for a later USB-power-meter session.

That closed out the design pass, so I built the scaffolding it was blocking:
LVGL 9.5.0 pinned in a new `main/idf_component.yml`, resolved via the IDF
component manager into `managed_components/` (gitignored, nothing vendored);
`sdkconfig.defaults` gained `CONFIG_FREERTOS_HZ=1000` and
`CONFIG_LV_COLOR_DEPTH_16` (already LVGL's default, pinned because every
buffer size upstream derives from it); the old `sdkconfig` was deleted and
regenerated so the new default actually took effect, and diffing confirmed
the tick rate was the only real change. Build stayed green, LVGL compiles
but nothing references it yet so the linker drops it entirely — the right
shape for an empty scaffold. Wrote all of the above into `README.md` before
it existed only in this conversation.

Before any of that could go up, a repo-wide check turned up something that
would have mattered a lot more than a stale comment: `.secrets.yaml`,
holding the Home Assistant long-lived token, was untracked but *not*
ignored. `.gitignore` covered `secrets.h`, `credentials.h`, `.env`,
`*.token` — plausible secret patterns, just not this filename — so a plain
`git add -A` would have pushed a live token to a public repo. Caught by
scanning `git add -An .`'s actual output rather than trusting the existing
ignore rules, fixed with a `*secrets.yaml`/`*secrets.yml` pattern, file
left on disk untouched. With that closed, pushed the repo for the first
time: nine files, `b506b28..cfae925`, verified afterward with a full-history
grep that no secret-shaped file ever entered any commit, including the
first one.

Last thing this session: two comments that earlier decisions had made
quietly false. `sdkconfig.defaults` still said PSRAM "arrives at stage 5" —
stage 5 was the encoder, already done, without it — and now explains the
actual reason PSRAM stays off: partial-mode rendering into two ~11 KB SRAM
buffers doesn't want it, and what will trigger enabling it later is the
entity cache, on its own commit with heap numbers either side. `README.md`'s
IDF-5.5-over-6.0 argument had led with `esp_lvgl_port` targeting the 5.x
API, which is no longer being used at all — rewrote it to rest on `esp_lcd`'s
ST7789 driver and PCNT instead, which is what's actually load-bearing.

Where it stands: the repo is pushed and clean, LVGL resolves as a managed
dependency but is linked into nothing yet, and `main.c` is still the
stage-5 encoder jig. The one real fork left open — what the render loop
blocks on, its priority, and whether other tasks touch LVGL under a mutex
or only through a queue — got set aside deliberately as needing more
thought than a keyboard session allows. Power is its own separate later
pass: Wi-Fi power-save mode, backlight timeout, and `CONFIG_PM_ENABLE` with
light sleep against a live socket.

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
