---
tags: [note, spec, home-assistant, embedded, esp32, ui]
created: 2026-08-21
---

# Knob Spec — Answers

Reference note for [[home-assistant-rotary-controller]]. The running answer
sheet for the 27-question requirements questionnaire (the *Knob Spec
Worksheet* artifact), which is being worked through in chat one question at a
time because the artifact was published as static HTML and cannot be filled in.

**State: 23 of 27 answered.** Sections 1–3 closed 2026-08-20; Q11–Q17 closed
2026-08-21; Q18–Q23 closed 2026-08-24. Q24 is pre-answered by Q23 and needs
only confirming. Q25 is blocked on the `websocat` session; Q26–Q27 not reached.

The reasoning behind each answer lives in the dated log entries
([[home-assistant-rotary-controller-log#2026-08-20]],
[[home-assistant-rotary-controller-log#2026-08-21]]). This note is the
decisions themselves, so the firmware has one place to read them from.

---

## Section 1 — What the object is

**Q01 = C.** Carried around the flat. Active while in use, light sleep on a
short timeout, deep sleep on a longer one, and in deep sleep upward of 99% of
the time.

**Q02 = A.** Two expert users, no guests. Discoverability is not a
requirement; consistency is, because memory is per-frequency. The device's
justification is a latency benchmark: it must beat *unlock phone → open app →
find entity → tap*, and the deep-sleep reconnect sits inside that budget.

**Q03 = A.** Screen fully off. Wake on an encoder turn or either button, and
the wake turn is swallowed — forced by hardware, since PCNT does not survive
deep sleep and a counted wake-turn would count an arbitrary fraction of the
motion. `ext1` wake is level-triggered, which makes the encoder's resting
levels per detent the fact that decides whether wake-on-turn works at all.
Unmeasured.

## Section 2 — The set of things it controls

**Q04 = B.** About six things: three light groups, TV, AC, blinds. Navigation
is a four-level carousel, one item per screen — device type, device,
attribute, value. Encoder rotates, GPIO0 descends, GPIO6 ascends. Settings at
the end of level 1.

**Q05 = A–D.** `light`, `media_player`, `climate`, `cover`. A Xiaomi robovac
and the d-control ESPHome remote are known to be coming and break the shape in
different directions. Three widget shapes are needed: bounded numeric,
enumerated choice, and action.

**Q06 = A.** Display only what the room can't tell you. No per-domain context
attributes; level 4 shows exactly one value. Values are null on boot and on
wake, never the last remembered ones — which deletes wake-time reconciliation
entirely. Notifications are a popup where the action is taken; continuous
facts (battery, link, staleness) live in a persistent status strip.

**Q07 = scenes and scripts in, automations out.** Logic lives in HA, the
controller only triggers it. A scene is a pure state assignment; anything with
sequences, delays or conditions needs a script. Unit trap: scenes store raw
`brightness` 0–255 while service calls take `brightness_pct`. A script's
default `mode: single` drops a re-entrant call *while still returning
success*.

## Section 3 — How a thing is named

**Q08 = C's discovery mechanism feeding B's storage.** A label chosen in HA,
resolved to an `entity_id` by an explicit manual sync, stored in NVS with the
friendly name, domain and area, and never re-resolved automatically. Startup
therefore has no resolve phase. Domain is stored as a small integer. Cost
accepted: drift between syncs.

**Q09 = C.** `unavailable` (device offline) is transient and shows as a dimmed
entry; an entity gone from HA entirely never arrives, means NVS has drifted,
and gets a popup.

**Q10 = C + D, plus a reversal.** HA owns the configuration, the knob triggers
the sync. Schema validation on boot with an actionable popup whose re-sync
action is pre-selected — invalidation, not migration. `idf.py flash` does not
erase NVS. Topology needs its own NVS namespace or every flash re-provisions
Wi-Fi. Schema-mismatch and never-synced are the same state.

---

## Section 4 — One knob, one button

**Q11 = type-first; `area` is not a level.** Level 1 is the domain carousel —
Lights, Media, Climate, Blinds, plus Settings. Level 2 is the device
("Bedroom lights"), level 3 the attribute, level 4 the value.

Mechanism: the carousel is not four data structures. It is one flat array of
NVS topology records plus a selection path (level index + cursor per level);
each level is a filter over that array and a projection of the distinct values
of one key. Q11 chose which key level 1 projects. `domain` is a small integer
from a compile-time-bounded set, so its labels are static strings in flash
with no per-entity storage; `area` would have needed a normalised area table.

Three or four rooms across six devices buys nothing at level 1, and the
friendly name already carries the room because that is how things get named in
a small flat. Room name rejected as a level-2 sub-label — not on uniformity
grounds (a second line adds no carousel item and changes nothing a turn does)
but on **Q06**: the room is the single most redundant thing on the glass,
because you are standing in it.

*Loose end:* `area` is now stored in NVS with no consumer.

**Q12 = plain short press only, on both buttons.** No long-press, no
double-press anywhere in the grammar.

Mechanism: with short-press as the only meaning, dispatch happens on the
**down** edge and the up edge is discarded. Any duration-based second meaning
makes that impossible — at down-edge time you don't yet know which gesture it
is, so every short press on that button becomes late by the full hold
threshold (300–500 ms). Input queue message is `{which button}`, nothing else.
Gives up press-and-hold-to-repeat.

**Q13 = no separate inactivity timer.** One 30 s one-shot: light sleep, screen
off, and a pop from level 4 up to level 3 as part of the same event.

Rationale: a position reset buys exactly one thing — it disarms the knob,
since levels 1–3 only move a cursor and only level 4 sends a service call. A
*separate, shorter* lit-screen pop would shorten the armed window by ~20 s at
the cost of a screen that moves without input, which is the failure mode a
single-control interface actually dies of.

Consequences:

- **The state machine has no timer-driven transitions at all.** Every
  transition is a button, a detent or a network event. The render task's timer
  list stays empty of UI timers; the only one-shot belongs to the power
  manager.
- **Deep sleep wipes RAM so the path is gone for free; light sleep keeps it,
  so landing on level 3 is a choice.** Making the pop part of sleep entry
  means both wake paths land identically.
- **Do the pop at sleep entry, not at wake.** The ST7789 holds its own GRAM
  and refreshes the glass independently, so a screen flushed before the
  backlight drops is still there when it comes back — wake costs one GPIO
  write to `BL_EN`, with no screen transition inside time-to-first-pixel.
- Wake (from either tier) lands on the default level-1 screen. No
  `RTC_DATA_ATTR` cursor; boot path and wake path are one path.

**Q14 = no acceleration ever. Per-domain default step, overridden by HA where
HA reports one.**

HA supplies `target_temp_step` (with `min_temp`/`max_temp`) on `climate` and
`step`/`min`/`max` on `number`. It supplies no step for `light`,
`media_player` or `cover` — brightness is 0–255, `volume_level` is a float
0.0–1.0, position is an integer 0–100. So the profile table carries a default
step per domain and attribute and HA's value wins when present. The table is
needed either way, because a `climate` entity can omit the attribute.

- Step, min and max are **state, not topology** — they arrive in the state
  object and are null on wake like the value, so none of them go in NVS. Self
  consistent: with a null value there is nothing to nudge anyway.
- Unit trap, same shape as `brightness` 0–255 vs `brightness_pct`:
  `volume_level` is a float 0.0–1.0, so a 2% step is `0.02` and the percentage
  on screen is computed for display. The conversion lives in one place.
- Encoder queue message stays a plain accumulated delta — **no timestamp**.
  (Acceleration would not have needed per-edge timestamps either: PCNT cannot
  timestamp, but one `esp_timer_get_time()` per batch read gives velocity as
  `delta / elapsed`. It was rejected on behaviour, not cost.)
- Full-travel moves are **actions, not turns**. `cover` exposes
  `open_cover`/`close_cover`/`stop_cover` — no argument, one call — with
  `set_cover_position` secondary. Turning a blind to a position is bad
  independently of step size, because a cover takes 10–20 s to travel and
  reports a position that lags the knob for the whole gesture.
- Domain-native actions are **free and undiscovered-able-by-config**: they are
  properties of the domain, so they live in the profile table as static flash
  data keyed by the domain integer. Arbitrary presets ("blinds at 40%") are
  instance-specific, and per Q07 they belong in HA as a scene, not in the
  controller.

**Q15 = the knob's meaning is always on the glass.** Level 3 already *is* the
sub-mode selector, so sub-modes do not exist as a separate concept — colour
temperature, source and volume are sibling entries in one entity's attribute
list.

Affordance design: large `<` `>` at the left and right screen edges. At levels
1–3 they mean *there is more this way*. At level 4 they become the unit — `-0.5`
and `+0.5` flanking `23` — answering "what is one detent worth", which nothing
else on the screen answers. Enums fall back to plain `<` `>` because the step
in a list is "one item".

- The chevrons need the **profile table default step** to draw before state
  arrives (step is state, so it is null on wake).
- They show granularity, not identity. `-5 · 40 · +5` could be brightness or
  volume. The residual ambiguity is two enum attributes on the same entity —
  an AC's `hvac_mode` and `fan_mode` both render as a bare string with `<` `>`.
  *Unresolved.*

*Loose end:* the chevrons at levels 1–3 imply an answer to whether the
carousel wraps or clamps at the ends. If it wraps they are decoration; if it
clamps they carry real position information.

## Section 5 — What is on the glass

**Q16 = value plus unit, nothing else — amended 2026-08-24 to "plus
conditional status chrome in the corners".** No secondary state, no age, no bar
in v1. Q20 added link/battery/system indicators in the corners, shown only while
a condition is unhealthy; they overlay rather than reserve space, which is free
*because* this answer keeps the centre minimal and the corners genuinely empty.

- Bar/arc dropped for readability on a 170 px panel. The argument reverses
  for brightness and volume, which are percentages of a range you can't feel
  — but `min`/`max` arrive with state regardless, so adding it later is a
  render-only change with no data-model cost.
- Secondary state (a *second* fact from the same entity — `hvac_action`
  "heating" vs the `hvac_mode` you set, a media player's `playing`/`paused`)
  is out on two grounds. Q06 covers it partially; the stronger and more
  general reason is **this is a remote, not a monitor**, which also excludes
  facts the room *can't* tell you.
- The *Decides* line hoped this would settle whether unbounded strings exist.
  It does not: enums still put a wire string on the glass.

**Q17 = capped fixed buffer, scrolled when it overflows. No pointers.**
Running text (`media_title`, `app_name`, `source`) is in v1.

- Truncate-vs-scroll is a **rendering** decision; cap-vs-heap is a **storage**
  decision. They are independent — `LV_LABEL_LONG_SCROLL` scrolls a `char[N]`
  perfectly well. Only "no maximum length at all" forces a pointer.
- Why pointers are worth avoiding: with every field fixed-size the cache is a
  plain struct array, a write is a `memcpy`, the worst case is truncation, and
  the render task can read at any moment with no coordination. One heap
  pointer means malloc/swap/free racing a render task that may be mid-draw on
  the old pointer — a lock, refcounting or deferred free, and the
  "never coordinate" property is gone. That is the exact lifetime question the
  render-loop design stalled on.
- Storage cost of a generous cap is negligible (six entities × a couple of
  string fields × 64 B against ~300 KB free internal heap).
- Scrolling costs wake-ups: an LVGL animation timer firing every
  `LV_DEF_REFR_PERIOD` (33 ms) while the label is on screen and overflowing,
  invalidating and redrawing each time. Accepted because it only happens while
  the screen is lit, and the AW9364 backlight's tens of milliamps dominate a
  CPU waking 30×/s. It stops at the 30 s light-sleep boundary.
- Font auto-scaling rejected in favour of scrolling. "Legible across the room"
  is the wrong criterion for something held in the hand — which makes Q27's
  option C unlikely to be the answer there.

**Q18 = B — a list rotated through, press to select. Commit semantics are
per-datatype.** Numeric attributes commit on the detent; enum attributes move a
candidate and commit on the button, with ascend discarding it.

- Not an exception to the gesture grammar — the *rule*. Levels 1–3 already are
  "detents move a cursor over an array, the button commits, nothing leaves the
  device while rotating". An enum at level 4 is a fourth carousel level obeying
  that. It needs no new code shape: the selection path already carries a cursor
  per level; entry costs one string match to place it on the current value.
- The genuinely anomalous case is **numeric level 4** — the one place a detent
  has an outward effect. Earned by: commit-on-detent is required exactly where
  the target cannot be known in advance and has to be felt for (volume by ear,
  brightness by eye, temperature by the room). An enum's target is a *name*,
  known before the knob is touched.
- Mirror argument on intermediates: every value passed on a numeric sweep is a
  legal, cheap, on-the-way state; every intermediate in an enum list is a
  **destination**. Scrolling past `Netflix` to reach `HDMI 2` actually switches
  the TV to Netflix. Coalescing does not rescue this — the failure case is a
  *slow, deliberate* scroll, which is what reading unfamiliar names looks like.
- Option A (blind cycle) was never cheaper: there is no `next_source` service,
  so advancing one still needs the ordered array plus a string match to find the
  current position. A and B store the same thing.
- B produces **cancel** for free (ascend = discard candidate). A cannot have one.
- Enum shapes on the wire: `media_player` has `attributes.source` +
  `attributes.source_list`, set by `media_player.select_source`. For `climate`
  the HVAC mode *is* the entity's `state` with `attributes.hvac_modes` listing
  the set; fan speed is `attributes.fan_mode` + `attributes.fan_modes`. Confirm
  on the wire.
- Cap is still a **correctness** bound, not display: `select_source` takes the
  name string exactly as HA gave it, no index form. Cap ≥ longest real option.

**Q19 = A. No age on the glass, ever.** A local arrival timestamp per entity is
kept but never rendered.

- Under `subscribe_events` nothing is polled — HA pushes on change and is silent
  otherwise. So **age measures how often a value changes, not whether it can be
  trusted**; silence is the healthy case.
- That kills B on better grounds than redundancy: an untouched lamp and a socket
  dead an hour accumulate age identically, so B warns about healthy entities and
  stays silent about the only case that matters. A false signal, not a duplicate.
- The honest instrument is therefore **per-connection, not per-entity** — one
  number, resolution bounded by the keepalive interval.
- HA's `last_changed`/`last_updated` are ISO 8601 on HA's clock: rendering an age
  from them needs SNTP and two clocks agreeing. `esp_timer_get_time()` needs
  neither.
- The stored stamp's stated purpose is the tick-to-`state_changed` latency
  measurement that sizes the coalescing interval and Q21's settle window. It is
  not to be rendered.
- Residual, closed by Q20: link state must survive a half-open socket, which
  needs an application ping (`{"type":"ping"}` → `pong`). That timer lives in the
  network task and emits an event, so the render loop still has no clock.

**Q20 = B, generalised into a conditional status bar.** Link upper-left, battery
upper-right, other system state upper-middle. On every level. Overlaid, never
reflowing. Nothing shown while healthy.

- **Nothing is latched. Every entry is derived from current state at render
  time.** Reason: on a device asleep >99% of the time an event-latched
  notification fires into a dark screen with nobody to deliver it to. A battery
  crossing 20% is the canonical case.
- A pop-up is that same state's **first-observation presentation**, not a
  separate object. An ACK clears the presentation, never the condition. Sleeping
  on an unread warning costs nothing — it re-presents at the next wake.
- Informational pop-ups ("sync successful") have no persisting condition, so they
  are restricted to **the direct result of an action just taken**, where the
  screen is lit by construction. Nothing unprompted.
- Pop-up grammar: either button ACKs, knob scrolls the text, never auto-dismissed
  (a timer would reintroduce the timer-driven transition Q13 removed). Collapsing
  both buttons to one meaning means **no press can be wrong** — the mode cannot be
  mispredicted, which is stronger than signposting it.
- The gate needs no repeat rule: a detent while a pop-up is up scrolls the
  message, so a second gate is unreachable without dismissing the first.
  Self-limiting by construction.
- **No reconnect pop-up.** The link indicator already separates
  blanks-because-arriving from blanks-because-broken, and a pop-up on every wake
  gives up Q13's one-GPIO-write wake (the ST7789 holds the finished screen in its
  own GRAM through sleep).
- Connect ladder, for reference: Wi-Fi + IP → TCP + WS upgrade → HA's
  `auth_required`/`auth`/`auth_ok` → `subscribe_events` acked → recently ponged.
  Trustworthy only from rung 4. `auth_invalid` is **terminal**; rungs 1, 2, 5 are
  transient. A revoked token must not look like a two-second blip.
- Open: keepalive interval × missed-ping threshold = worst-case window for
  displaying something untrue. Pick a number.

## Section 6 — When it stops knowing the truth

**Q21 = C. Immediate local application, visible pending mark until HA confirms.**
Cache holds `desired` and `confirmed` per entity.

- A service call produces **two** returns and they are different claims. A
  `result` carries the `id` I assigned and says HA *accepted* it. A
  `state_changed` says the world *changed*, carries **no `id`**, and is the same
  event every other client sees. They can disagree (a bulb rounds 200→198, a
  Zigbee frame is lost, a cloud-routed AC takes seconds).
- The *Decides* line splits **B from {A, C}**, not A from C. Even A needs an
  in-flight notion, or a `state_changed` generated before the command landed
  snaps the screen backwards through the old value. So A and C need the identical
  pair and differ only in whether the difference is drawn — a display decision,
  cheap to reverse.
- B rejected: at ~300 ms confirmation and 10–30 detents/s, six clicks pass before
  the first shows. Loss of control, not sluggishness. Same closed-loop argument
  as Q18.
- **The mark means "I asked for this and have not heard back"** — never "this
  value is uncertain". An externally-originated change (the TV's own remote)
  arrives as a plain `state_changed`, updates the value, renders unmarked. This
  definition is what kills Q23's option A.
- Coalescing is **orthogonal** — required under all three options.
- Open: the resolution rule when confirmation never arrives; and the settle
  window. Two requirements pull opposite ways — an external change mid-command
  must be accepted, a pre-command event must be rejected, and nothing in the
  message separates them. Ordering by `last_updated` against the last stored one
  handles duplicates and reordering (HA timestamps compared only to other HA
  timestamps, no wall clock), but not this. Needs a local window sized to the
  measured latency.

**Q22 = D. HA's `message` verbatim**, into a single global capped buffer.

- Rejection is the one message unambiguously mine: `result` with my `id`,
  `success: false`, `error: {code, message}`.
- B is dominated — its whole content ("this was an explicit reject") is a subset
  of D's.
- C dies twice, independently: the table needs hand maintenance, *and* HA's
  `code` is coarse enough that integration failures surface as something generic
  with the specifics only in `message`, so the lookup mostly resolves to "unknown
  error" for exactly the failures worth explaining.
- **One global buffer, not per-entity** — only one error shows at a time, so it
  can afford to be generous (128–256 B). Transient; never NVS; dropped on ACK.
- Truncation is safe here in the way Q18's was not: displayed, never sent back.
  Two traps — cut on a **UTF-8 codepoint boundary**, not a byte, or LVGL gets an
  invalid sequence; and the font is built with a chosen character subset, so
  anything outside it renders as boxes and reads as corruption.
- One-branch fallback to `code` when `message` is empty. Not a translate table.
- D surfaces firmware bugs on the panel too. Under Q02 (two expert users,
  discoverability explicitly not required) that is a feature.
- D is what gives the scrolling pop-up body something to scroll.
- The *silent* failure (`success: true`, no `state_changed` — an unreachable
  Zigbee bulb) is not covered here. That is Q21's pending-mark timeout, still
  open, and probably the more common failure.

**Q23 = B, extended.** Link down is read-only *towards the network*, not dead.

- Two options were already closed: Q19 killed per-value staleness marks (so A and
  B share identical marking, which lives in the corner chrome), and C would
  reverse Q20's choice of chrome over a takeover screen. **No disconnected screen
  variant anywhere** — chrome, a dim, and a pop-up, all layered over existing
  screens.
- A rejected on **stale intent**: a queued command was correct when formed and
  wrong when it lands. Turn the TV on with the link down, turn it on then off
  with the real remote, and the queued command switches it back on. HA has no
  compare-and-swap in its service API — but the check *is* available device-side
  (store `last_updated` at queue time, compare on reconnect, discard if it moved).
  So A dies on cost, not impossibility.
- A also breaks the pending mark's definition: with the link down nothing was
  asked, so the mark would assert something untrue about the device's own I/O.
- Behaviour: a level-4 commit attempt **stores nothing, changes nothing, sends
  nothing**, and raises a pop-up that ACKs away and re-arms for the next attempt.
  Generalised to every blocking condition.
- This gives Q20's blocker/non-blocker split its operational definition: **a
  blocker is a condition that gates a commit.** Link down blocks. Config drift
  blocks, for affected entities. Battery <20% does not.
- Values freeze and **dim**, reusing Q09's `unavailable` treatment. Blank is
  unavailable as a signal — already taken by never-acquired at a cold wake, and
  conflating "never knew" with "knew, cannot verify" collides exactly where the
  difference matters.
- Dimming is a binary signal for a continuous decay. Not a flaw in this answer —
  the price Q19 quoted when it declined to render age.
- Navigation on levels 1–3 is unaffected (NVS topology). **A settings page will
  exist** holding local device-only config, writable with the link down; contents
  and location in the carousel undecided.

**Q24 — pre-answered by Q23.** Its option D is literally "the question can't
arise — the knob is inert while disconnected". Confirm, do not re-derive.

**Q25 — blocked on the wire.** Reconnect resync path.

## Section 7 — not reached

**Q26–Q27** scope boundary and the single tiebreaker.

Provisional signal on **Q27**: option C ("readable and operable from across
the room") looks unlikely, per Q17.

---

## Carried forward

**Bench, unmeasured:**

- I²C scan with the BQ25896 charger and BQ27220 gauge as the positive control
  — is there an IMU to wake on?
- Board deep-sleep current.
- The encoder's resting levels at successive detents, which decides whether
  `ext1` wake-on-turn is possible at all.

**Needs the `websocat` session (plan item 2):**

- Whether `target_temp_step` actually appears in the AC's `attributes` object
  — the tell that proves the override path.
- The longest option string across the real `source_list` / `fan_modes` /
  `hvac_modes`, which sets the enum cap.
- Whether any of the six devices exposes attributes as separate
  `number`/`select` entities instead.
- HA labels live in the entity registry rather than in state, and registry
  commands may want an admin token.
- Whether `hvac_mode` really is the entity's `state` rather than an attribute.
- Whether HA's error `code` is as coarse as expected, i.e. whether integration
  failures land as something generic with the detail only in `message`.
- The command-to-`state_changed` latency, which sizes both the coalescing
  interval and Q21's settle window.

**Design, open:**

- Q24 confirm, then Q26–Q27. Q25 after the wire.
- The settings page: what it holds, and where it attaches in a carousel with no
  level for something that is not a domain, entity or attribute.
- Keepalive interval and missed-ping threshold — together the worst-case window
  for confidently displaying something untrue.
- The pending mark's resolution rule when confirmation never arrives, and whether
  a silent failure should look different from a rejection now that rejections
  carry text.
- Whether the pending mark should vary per domain — the room confirms a TV volume
  change faster than a glyph can, but not a 5% brightness step.
- Does the carousel wrap or clamp at the ends of a level?
- The level-4 ambiguity between two enum attributes of the same entity.
- `area` is stored in NVS with no consumer.
- When the config-drift popup fires, given it arrives unprompted during the
  wake window; what it says when an integration removes fifteen entities at
  once; what a press does on a dimmed entry.
- The Wi-Fi provisioning path that "credentials persisted across updates"
  quietly assumes.
- Power is its own later pass: `WIFI_PS_MIN_MODE`, backlight timeout,
  `CONFIG_PM_ENABLE`.
