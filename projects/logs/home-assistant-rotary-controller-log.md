---
tags: [log, home-assistant-rotary-controller]
project: home-assistant-rotary-controller
---

# home-assistant-rotary-controller — build log

Session entries, newest first. Written by the SessionEnd hook.
The project note is [[home-assistant-rotary-controller]].

### 2026-08-31

Measured the command-to-`state_changed` latency the last session deferred, and
it came back as three numbers rather than the two expected. The measurement
then settled how the outbound command path is clocked: **self-clocked on the
`result` frame, one command in flight per entity, with a per-domain period as a
floor.** Nothing in the repo changed. `main.c` is still the stage-5 encoder jig,
and the transport decision these numbers were supposed to inform is still not
made, so no plan box is ticked.

The harness was a zsh script driving `websocat` through a FIFO held open on a
dedicated file descriptor — websocat closes the connection on stdin EOF, so
writing each command with a fresh redirect would tear the socket down after the
first one. Arrival timestamps came from one long-lived `python3 -u` reading the
pipe; send timestamps from zsh's `$EPOCHREALTIME`, which is a shell parameter
and costs no fork. That detail matters more than it looks: spawning `python3`
per timestamp would have charged about 30 ms of process startup to the very
number being measured. Both stamps are `CLOCK_REALTIME` on the same machine, so
the two directions subtract directly and nothing depends on this machine and HA
agreeing about time — unlike the `last_updated` fields inside the payload, which
are HA's clock. `-B 2000000` carried over from 2026-08-30.

**The first run measured nothing and was still worth having.** It went out with
the placeholder entity id from the example line, `light.your_bulb`. Both
`call_service` calls returned `{"success":true}` with fresh context ids, and no
events arrived at all. Home Assistant's service layer does not validate that a
target entity exists: an unmatched `entity_id` matches zero entities, the
handler returns cleanly, and the success frame reports that the call was
dispatched rather than that anything happened. It is the same shape as the SPI
note in `board_pins.h` — a master clocks bits out and reports `ESP_OK` whether
or not anything is listening. What made the silence readable rather than
ambiguous was the second command, sent 8 s after the first: its `result` came
back, so the pipe was demonstrably alive across the quiet stretch. That run also
handed over a baseline which turned out to be load-bearing — **25 ms** for the
round trip with nothing dispatched to any device.

**The real capture, one command at a time**, against `light.kajplats_gu10_ws_575lm`,
a single bulb rather than a group. TX to `result` was 111 ms and 112 ms; TX to
the confirming event 223 ms and 233 ms. So three numbers, not two: 25 ms of API
round trip, ~111 ms to the ACK, ~223 ms to the reported value. Two details in
the payload are worth keeping. Brightness 64 was commanded and 63 confirmed,
while 200 came back exactly — so whatever sits between the service call and the
reported value does not round-trip every integer. And `last_changed` stayed
pinned across both commands while `last_updated` and `last_reported` moved,
because `state` never left `"on"`; that is the attribute-only mechanism from the
last session visible in the payload's own timestamps.

**My first reading of the 111/223 split was wrong**, and the 25 ms baseline is
what killed it. I read the ACK as the controller's leg and the event as the
world's, and concluded the coalescing interval should come from the ACK because
the real-world action is not the controller's responsibility. But `call_service`
is awaited with `blocking=True`, so the `result` frame is not sent until the
integration's coroutine returns — which for this bulb means the device command
was transmitted and acknowledged at the radio layer. The unmatched-entity run
isolates that: same frame, same socket, same parse and dispatch, 25 ms, with
nothing handed to any device. The 86 ms on top of it in a real run is the far
side, not HA bookkeeping. The line between numbers two and three is not
controller-versus-world; it is **commanded versus reported**.

That is also why number two cannot be a firmware constant. It is a property of
whatever sits behind one entity, and nothing on the wire names the integration —
the event carries the entity, the domain and the attributes, never the
transport. A `light` may be a local Thread bulb at 220 ms or a cloud-routed one
at two seconds, so a per-domain column cannot carry the far side's speed even
though it looks like the natural place for it.

I argued for a while that the interval should instead be derived from what the
device can afford to receive, since each command comes back as roughly 1.6 KB of
event plus a 159 B result, and 80 commands during a two-second spin would be
about 200 KB of JSON arriving at a 512 KiB device that is also rendering. That
argument lost, and it lost cleanly: inbound volume is not self-controlled. A
group's membership is invisible until its events arrive, and the other person in
the flat, or any automation, can move a subscribed entity at any moment. The
receive path therefore has to survive a burst it did not cause, which makes
inbound robustness a requirement that exists independently of the send rate —
so sizing the interval to protect it buys nothing that is not already
mandatory. What survives from that line of reasoning is narrow but real: these
are absolute service calls (`brightness: 200`, not a relative step), so a value
superseded by another detent before it was ever sent is not traffic worth
economising, it is a command nobody wanted.

**The burst run** sent six commands about 116 ms apart. ACKs came back in
101–156 ms with no upward trend, so nothing backed up over six. Five events came
back for six commands: every commanded value was reported, in order, except
**100**, which never appeared at all. The far side samples and drops
intermediates on its own when it is outrun, which is worth knowing before
designing a scheme whose whole purpose is to stream them.

The burst also killed a mechanism I had offered earlier in the session. I had
proposed `context.id` as the way to tell an event caused by one's own command
from a foreign change — the service call returns its context, the state write
carries it, and in the isolated captures the match was exact. Under a burst it
is not: the event reporting brightness 20, a value only the first command asked
for, wore the *second* command's context, and the last two events of the run
shared the sixth's. The context stamped on a state write appears to be whichever
service call was in flight when the report landed, not the one whose value it
is. Q21 already recorded that nothing in the message separates a pre-command
event from an external change mid-command; that note stands, with one fewer
candidate.

**Period against trailing edge turned out to be one mechanism, not two.**
"Fire one request when the input stops" is the same coalescer with a
trailing-edge fire rule instead of a periodic one, and any correct version needs
the trailing edge regardless — a purely periodic timer can fire just before the
last few detents arrive, leaving the value the user actually chose unsent.
Sorting by turn speed is what separates them. Turning slowly, one detent at a
time, trailing-edge fires a fixed delay after each detent while a period makes
the same detent wait 0 to P depending on phase. Sweeping fast, trailing-edge
collapses the sweep to one command while a period streams a ramp the far side is
already dropping values from. The band where a period genuinely wins is the
middle one — a steady turn with detents arriving just inside the idle timeout,
where the timer never expires and nothing goes out until the backstop. That band
is what prices the two constants against each other: if the backstop is not much
larger than the idle timeout, it shrinks to nothing, and the two options
converge on a throttle with a trailing flush.

Before going further I read Q18 and Q21 in the spec rather than recalling them,
because the question on the table was whether these findings reopen the
interaction design — whether a button confirmation or a settle timeout would be
better than firing during the turn. They do not. Q18 already put numeric level 4
on commit-on-detent and named the reason: commit-on-detent is required exactly
where the target cannot be known in advance and has to be felt for — brightness
by eye, volume by ear, temperature by the room — whereas an enum's target is a
name known before the knob is touched. Nothing measured today bears on that
reason, so a button confirmation for a numeric would reverse Q18 rather than
refine it. Q21 had separately rejected waiting for confirmation before showing a
value, on the grounds that at ~300 ms confirmation and 10–30 detents/s six
clicks pass before the first is visible. Today's numbers are that estimate
measured: 101–156 ms to ACK, 220–260 ms to the reported value.

**The decision.** The sender holds at most one command in flight per entity and
sends the next only when the previous `result` has returned, with a per-domain
period as a floor. Clocking on the ACK makes the far side's speed an observation
rather than a setting: fast for the Thread bulb, slow for a cloud AC, nothing
configured and nothing calibrated. It also collapses one of the two constants,
because the slot's release *is* the trailing edge — when the `result` returns
the coalescer sends the latest `desired` if it differs from the last value sent,
whether or not another detent has arrived, so the final value always goes out
and there is no idle timeout to size. The per-domain floor survives, but its
meaning changes: it no longer claims to know how fast a domain's devices are,
which it cannot, and instead says how fluent that domain should be. That is
policy, and policy genuinely is per-domain — `climate` has no fluency
requirement at all and every setpoint may start real HVAC action.

One wrong step on the way there, corrected: the burst's attribution failure got
carried over to the ACK, and it does not apply. Two different bindings were on
trial. Event to command binds only through `context.id` and failed. `result` to
command binds through the `id` the client assigned, which the API echoes by
definition, and it held across both bursts — six results carrying ids 10 through
15, in order, each matching its command. The binding that survives a burst is
exactly the one the sender needs; the one that fails is needed only by the
display path.

The real gap in self-clocking is elsewhere, and it is worth carrying: **the ACK
is only as honest as the integration's `await`.** Today's 111 ms was long
because that integration does not return until the device has acknowledged. An
integration that hands off to a vendor cloud and returns immediately would ACK
in 25 ms however slow the device is, and the sender would clock at full rate
into something that cannot keep up — degrading to a plain period exactly where
the mechanism was supposed to help.

What this costs in the cache is three fields beside `desired` and `confirmed`:
the last value sent, the in-flight command id, and the timestamp of the last
send. Q24's finding is untouched — still no outbound queue, still one
latest-value slot. What it leaves open is the release rule when a `result` never
arrives, which Q21 already lists as open for the pending mark and which is now
also what stops a lost result wedging an entity's knob permanently; one timeout
serving both is an argument for it being a single rule. And ids are per
connection, so a reconnect resets the numbering: any in-flight slot has to be
released when the socket is remade, since a command whose `result` was lost to
the drop can never be matched and its id may be reused.

Two hours of tooling cost, both self-inflicted. The capture script wrote the
socket's output with `tee $OUT` from inside the pipeline and its own TX lines
with `tee -a $OUT` from the shell; the long-lived pipeline `tee` holds the file
open from offset zero and keeps its own position, so every appended TX line was
overwritten as it wrote past it. The first burst capture came out with the
receive half intact and the send half gone. Opening both writers `O_APPEND`
fixes it, and the general form is that two writers on one file only compose if
both append. The other was running the example command line verbatim with its
placeholder entity id, which is what produced the first null run — cheap, and it
bought the 25 ms baseline.

Carried forward. The transport decision from 2026-08-30 is still unmade and is
now fully informed: `get_states` against per-entity REST against the registry
for the snapshot, `subscribe_events` against `subscribe_trigger` for the stream,
and group against members. Q25 remains the one open questionnaire item and is
blocked on that decision. Bench, unchanged: the I2C scan with the BQ25896 and
BQ27220 as positive control, board deep-sleep current, and the encoder's resting
levels at successive detents.

### 2026-08-30

Opened plan item two — the `websocat` session against Home Assistant — and got
the whole transport measured except the one number that needs a stopwatch.
Nothing in the repo changed; `main.c` is still the stage-5 encoder jig. No plan
box is ticked, because the latency measurement and the transport decision it
feeds are both still open.

The session opened on a stale pending-failure warning, which turned out to
belong to a different project: the 2026-08-28 SessionEnd writer exited 1 with
`You've hit your session limit`, on a `fire-housing-sim` session logged
`vault=none`. Nothing was owed to this vault and nothing was unpushed. What the
check did turn up was the opposite failure — 95 uncommitted lines in
`notes/home-assistant-rotary-controller-spec.md`, mtime 2026-08-26 14:00,
holding the Q24/Q26/Q27 answers that closed the questionnaire. That day's hook
run committed the journal, log and project note and left the spec behind, so the
decisions the session existed to produce were the one part of it that never
reached the remote. Committed as `03c6f78`. Worth knowing that the hook stages a
fixed set of paths rather than the working tree, so a note edited mid-session
outside that set is silently left.

**The auth handshake failed silently the first time, and the silence was the
interesting part.** HA speaks first on connect — `auth_required` arrives
unprompted — and a rejected token is answered loudly with
`{"type":"auth_invalid","message":"Invalid access token or password"}` followed
by a proper close frame. What I got instead was nothing at all, and then
`websocat: WebSocketError: I/O failure` on the next write, which is just
websocat discovering the socket had already gone. Pasting a long token by hand
and hunting for Enter loses a race: the unauthenticated connection has a
deadline, and when it expires HA disconnects with nothing to say, because
nothing was rejected — the client simply never showed up. Having the shell emit
the auth line the instant the socket opened produced `auth_ok` with the same
token. The run that fixed it changed two things at once, though — instant send
*and* no hand-typing — so it establishes the problem is gone rather than which
half caused it. The control is what makes the reading defensible: a deliberately
wrong token, sent the same fast way, printed `auth_invalid` and a close message,
proving the setup could show a rejection if there had been one.

**`get_states` returns 134,043 bytes for 284 entities**, and there is no
argument to narrow it — no entity filter, no domain filter, no pagination. That
is not an oversight but a fact about who the API was built for: its primary
consumer is HA's own frontend, a browser tab with hundreds of megabytes that
genuinely wants everything. The domain histogram put 22 of those 284 entities
in the four domains this device controls — 14 `light`, 4 `media_player`,
3 `cover`, 1 `climate` — weighing 13,566 bytes. About a tenth. Most of the
remainder is `sensor` (67), `number` (60), `button` (36) and `update` (30),
much of it a Xiaomi robovac integration. Tidying HA would move the number and
not the shape, since a constraint that depends on the instance staying tidy is
not a constraint.

The size matters because of how cJSON works rather than because of the network.
cJSON is a DOM parser: it takes a complete NUL-terminated document and builds a
tree of structs, one per value, each with a type tag, pointers and its own copy
of every string, all live at once and several times the input. A WebSocket
message is also not a frame — the sender may fragment one message across many,
and the receiver must reassemble before the message means anything — so the
134 KB has to exist contiguously somewhere before parsing even starts. Against
512 KiB of internal SRAM already carrying Wi-Fi buffers, LVGL draw buffers and
task stacks, that is the whole argument for PSRAM, and the reminder that fitting
is not solving. The alternative shape is a streaming parse that acts on each
token and discards the rest — bounded memory regardless of input, paid for in a
hand-written state machine.

**`subscribe_events` filters by event type, not by entity**, which is worse than
it first reads: the ongoing stream is unfiltered too, not just the connect-time
snapshot. Every `state_changed` in the instance arrives forever, and each event
carries both `old_state` and `new_state` in full, so an event is roughly twice
an entity's weight in the snapshot.

The entity filter does exist, and it is `subscribe_trigger`. That took
understanding what a trigger actually is, because the automation UI makes it
look like a kind of object HA emits. It is not. HA's core is an event bus, and
`subscribe_events` is a raw tap on it. A trigger is a **listener specification**
— the same declarative config an automation's trigger block holds, which the
automation engine compiles into a bus subscription plus a predicate. A `state`
trigger with `entity_id` and `to:` subscribes internally to `state_changed` and
asks, per event, whether this entity is in my list and whether old→new matches.
`subscribe_trigger` is HA letting a WebSocket client instantiate one *without an
automation attached*, and receive the firings directly. The predicate exists
either way; the only question is which side of the network it runs on. Its
`entity_id` takes a list, so one subscription covers the lot. It is not cheaper
per event — the payload wraps everything in `event.variables.trigger` and adds
`id`, `idx`, `platform`, `for`, `attribute` and `description` on top of full
`from_state` and `to_state` — so the entire saving is in the events never sent,
which means its value is exactly the 262-to-22 ratio and improves with every
chatty integration added.

`config/entity_registry/list_for_display` is the other find, and it lines up
with a decision already made. It returns abbreviated registry entries — `ei`
entity id, `ai` area, `en` name, and `lb` **labels**, which is the tagging
mechanism the sync was specified against — and carries no `state` and no
`attributes` at all. That is the 2026-08-20 topology/state split appearing in
HA's own API design: the registry and the state machine are separate endpoints
because they change on completely different timescales. The split was not merely
convenient for a sleeping device; it is the seam the platform already has.

**Measured, not assumed: a bare `state` trigger fires on attribute-only
changes.** This decides whether the whole path is usable, because what this
device controls lives in attributes — brightness, volume, target temperature —
while an entity's `state` is only the string, and a lamp going 40% to 80% never
changes it. Subscribing to one light with no `from`/`to` and moving only the
brightness produced events with `state` steady at `"on"` and `brightness`
moving; toggling it off and on fired too, which was the positive control.

**A group entity multiplies the event stream by its member count.** The first
capture was noisy and the obvious explanation was the brightness slider sending
many values, which is half of it. The tell the slider cannot explain is the
interleaved zeros — `192 → 0 → 96 → 0 → 64 → 0 …`, all with `state: "on"` — and
the entity's own attributes, where `entity_id` is a five-element list of member
bulbs. `light.living_room_lights` is a group, and a group has no state of its
own: it recomputes an aggregate and re-emits the whole thing every time any one
member reports. Subscribing to the group and one member at once, so a single
drag produced both streams, gave 15 group events to 3 member events — exactly
3 reports × 5 members. 34,914 bytes for one dim of one lamp. The group's
messages are also the fatter ones, since each carries the member list twice, in
`from_state` and `to_state`.

That reframes something the design already half-knows. Command flooding was
scoped as an outbound problem — encoder ticks coalesced into one `call_service`
— and this is the same problem pointed inbound, which nothing has looked at:
roughly 15 messages of ~2.5 KB inside 400 ms for one human gesture. Q21's
`desired`/`confirmed` pair has to survive those zeros too, since a device
rendering each confirmed value as it lands would show its own brightness
snapping to 0 and back during a change it initiated.

Two tool facts cost time. `websocat`'s read buffer defaults to 64 KiB and
*splits* a longer message into parts, injecting a newline between them in line
mode — so the 134 KB snapshot landed as three chunks of a JSON document chopped
mid-string, and `jq` failed at "Unfinished string at EOF" while `grep | wc -c`
returned exactly 65536. `-B 2000000` fixes it. And zsh's builtin `echo`
interprets backslash escapes by default, the way `echo -e` does in bash, so
piping JSON through it silently ate nine bytes of `\"` and `\u` sequences and
broke parsing 126 KB in — not an error, just a slightly shorter string.
`printf '%s'` is escape-clean; keeping the document in a file avoids the
question.

Carried forward. The measurement left undone is the command-to-`state_changed`
latency on a single bulb, and the burst data already shows it is two numbers
rather than one: time to first confirming event, which sizes the coalescing
interval, and time until the value stops moving, which decides how long the
device keeps believing its optimistic value before treating an arrival as the
truth. Reading the first arrival as final would snap the display to an
intermediate. With that in hand the transport decision is fully informed —
`get_states` against per-entity REST against the registry for the snapshot,
`subscribe_events` against `subscribe_trigger` for the stream, and group against
members — and it is not made yet. Q25 remains open. Bench, unchanged: the I²C
scan with the BQ25896 and BQ27220 as positive control, board deep-sleep current,
and the encoder's resting levels at successive detents.

### 2026-08-26

Closed the requirements questionnaire except for the one question that needs
hardware: Q24, Q26 and Q27 answered, taking it to twenty-six of twenty-seven.
Nothing in the repo changed — `main.c` is still the stage-5 encoder jig.

All three are constraint questions rather than design questions, and the same
mechanism decided each of them: **a constraint is only worth writing down if
something would otherwise enforce the opposite.** A refusal the data model
already makes impossible protects nothing. A criterion that can never be
contested arbitrates nothing. Sorting the candidates by that test is what made
these quick, and it is also what exposed two eliminations of my own that were
confidently wrong.

**Q24 is D, and it closes with no new data structure.** Q23 had already made a
level-4 commit attempt with the link down store nothing, change nothing, send
nothing and raise a pop-up, so the only live question was whether that pop-up is
D's inert knob or A's "discarded, and the device says so". It is D: the pop-up
is the gate firing on the *input* path, before any command is formed, not the
funeral of one that was. Nothing is serialised, nothing acquires a lifetime,
nothing needs a reconnect policy. The distinction matters because A implies a
command object that exists long enough to be dropped, which is a queue with one
slot and a discard rule, and D implies the code path returns before construction.

The consequence worth carrying is that **there is no outbound queue.** The only
latest-value slot in the firmware is the connected coalescer already living
inside Q21's `desired`/`confirmed` pair, and its lifetime is one coalescing
window. Q24's *Decides* line asked whether a queue exists at all and whether it
is a queue or a per-entity slot; the answer is neither, plus a slot that was
already there for a different reason.

**Q26 sorts into three groups once "would the code drift towards this" is the
test.** Option A, refusing any hierarchy deeper than two levels, is not available
— the carousel is domain → entity → attribute → value, settled across Q11 to
Q18, so it is already violated and cannot be refused. Options C and E are not
enforceable in firmware at all, for different reasons. C, refusing anything with
a safety consequence, cannot be held by the code because what this device
controls is decided by which entities carry the tag in Home Assistant; a domain
in the firmware is a small integer and a label in flash, and nothing there
distinguishes a lock from a lamp in the safety sense. It is a policy about which
tags get applied, enforced in HA's own UI — and it was declined on the merits
anyway, since heating is wanted later. E, refusing any interaction longer than
about three seconds, has no structure preventing it either; it would be found out
by timing one, and the three-second argument in the project note was always about
*control* actions rather than about a sync or a screen test.

That leaves the two with teeth. **D, browsing entities it was not configured for,
is refused outright**, and it costs nothing still wanted: the tag-based sync is a
filter applied at sync time, so the topology in NVS never contains anything
untagged, and the plan's stretch item — "an entity picker on the device, so the
list is not compiled in" — is already half-obsolete, because the tag sync
achieves "not compiled in" without any browsing. What D forbids is the unfiltered
picker and the on-the-spot bind specifically. **B, text entry, is refused on the
control path with the settings page exempt.** B is the one the code is actively
pulling towards, and the reason is exact: text entry on a single rotary encoder
is a character carousel — rotate an alphabet, press to commit, plus a backspace
and a done — which is *the level-4 enum carousel with a bigger array*. Q18 built
that shape already. It is not a feature away, it is an array away, which is
precisely the "the code already almost does it" case a written boundary exists
for.

The settings exemption picked up a second consumer: the tag value itself becomes
a configurable field rather than a compile-time constant. That is cheap, but not
because it is small — it is cheap because it reuses a path already committed to.
Changing the tag invalidates every topology record in NVS, since they were all
written by a filter that no longer applies, and the erase / mark-empty / prompt
for re-sync mechanism was already chosen on 2026-08-20 for the fact that
`idf.py flash` does not erase NVS. A tag change is a second trigger into a
handler that has to exist regardless. It also does not weaken the D refusal,
which was the obvious objection: swapping the tag changes the filter wholesale,
and every entity that appears still got there by being tagged in Home Assistant,
whereas D refuses *per-entity* selection on the device.

One new open item falls out of it. A mistyped tag syncs zero entities and
produces an empty carousel with the link perfectly healthy — and under Q23's
operational definition, where a blocker is a condition that gates a commit, this
is not a blocker, so nothing in the current status model would explain it.

**Q27 is B — what it shows is true, or it says it doesn't know.** Two of the four
went out on prior answers. C, readable and operable from across the room, was
provisionally doubted at Q17 on rendering grounds ("legible across the room is
the wrong criterion for something held in the hand", which is why font
auto-scaling lost to scrolling there) and is now settled on the form factor
itself: the device is handheld. D, usable by someone who has installed nothing,
cannot be the criterion whose failure makes the device pointless because Q02
fixed the audience at two expert users and put discoverability explicitly outside
the requirements. A user manual in the repo is worth having and changes nothing
about that.

The two corrections are the part of this session worth keeping, because both
eliminations were confident.

I first ruled out **A** — a turn produces a visible response instantly, every
time — on the grounds that the first input out of deep sleep is swallowed
anyway. That is the wrong step. What the PCNT lesson establishes is that the
*counts* from the waking turn are lost, because the pulse counter lives in the
digital power domain and does not survive deep sleep. The turn still produces a
visible response, and an instant one: the screen comes on. The swallowed turn is
a counterexample only under the reading "response" = "the number moves", not
under "response" = "something happens". What is defensible in the objection is
the word *every*, since A is stated absolutely and a deliberate structural
carve-out sits awkwardly with that — but that is an argument about how tightly A
is worded, not evidence that A had already failed, which is how I was using it.

I then kept **B** alive with a fallback that does not survive the data model: that
even without knowing an entity's current value the device is still useful blind,
because an enum can be chosen by name regardless of where it currently sits. It
cannot. The 2026-08-20 topology/state split put `source_list`, `fan_modes`,
`hvac_modes` and `effect_list` on the **state** side — they arrive inside the
entity's state object and are null on wake — so a device that does not know the
current value does not have the candidate list either, and there is nothing to
rotate through. The numeric case fails for a related reason: the commands are
absolute (`volume_set`, `set_temperature`), computed from a `desired` value
seeded by the confirmed one, so with no baseline there is no command to form.
Q23 had already made this literal rather than hypothetical — link down means
commits are gated and values freeze. **This device does not degrade into a blind
controller; it declines.**

Removing that fallback is what forced B to be argued on its actual failure, and
that turned out to be narrower than the intuition. B is two clauses joined by
*or*, and the second one is the escape hatch: a missing `state_changed` only
fails B if the device goes on presenting the value as good, and the design
already wires the alternative — values freeze, dim and gate commits, which *is*
saying it does not know. Propagation delay does not fail it either; it is bounded
and short, and the device has no reason to doubt what it holds during it. What
fails B is the device being **confident and wrong**, and both instances of that
are already on the open list: the half-open TCP connection, silent for up to
keepalive × missed-ping threshold in exactly the way health is silent, and the
silent service failure — `success: true`, no `state_changed` ever, an unreachable
Zigbee bulb.

So B is not unachievable and it is not about latency. It is a criterion with a
number attached, and choosing it commits to making that number small.

The pick reads as though it contradicts Q21, which chose immediate local
application over waiting for HA to confirm, and it does not — because Q21 also
bought the pending mark. The optimistic value is drawn *and labelled as
unconfirmed*, which is A's speed with B's honesty intact, paid for with a glyph.
The one place the two criteria collided head-on, the design satisfied both rather
than choosing.

What B decides going forward, since a tiebreaker is only worth having if it
settles open questions: the keepalive interval and missed-ping threshold get the
aggressive number and pay the wake-ups, rather than the lazy one and pay the
window in which the device is confident and wrong; and the pending mark's
resolution when confirmation never arrives resolves towards "I do not know",
never quietly into a confident value. It does not reopen Q19, which is the
question it looks most like — Q19 found that a per-entity age is a *false* signal
under a push subscription, since a lamp untouched since morning and a dead socket
accumulate age identically, so the per-connection indicator is B's instrument and
rendering age would be a worse one.

One asymmetry noted and deliberately not treated as decisive, because it cuts
both ways: A is a property of the device alone and can be guaranteed by
construction, while B is a property of a distributed system over a lossy link and
can only ever be bounded. That argues for B, since a criterion that is simply
satisfied never has to arbitrate anything; and it argues for A, since the
trade-offs that have actually come up were decided A's way.

Carried forward. Everything remaining is blocked on the same thing — plan item
two, the `websocat` session against Home Assistant, which unblocks Q25 and seven
of the wire questions in one sitting: whether `target_temp_step` appears in the
AC's attributes, the longest option string across the real `source_list` and mode
lists, whether any device exposes attributes as separate `number`/`select`
entities, whether registry access for labels needs an admin token, whether HA's
error `code` is as coarse as expected, whether `hvac_mode` really is the entity's
`state` rather than an attribute, and the command-to-`state_changed` latency that
sizes both the coalescing interval and Q21's settle window. Bench, unchanged: the
I²C scan with the BQ25896 and BQ27220 as positive control, board deep-sleep
current, and the encoder's resting levels at successive detents. Design, open:
the same list as before, plus the empty-carousel-from-a-mistyped-tag case, minus
Q26 and Q27.

### 2026-08-24

Re-took Q18 and ran the questionnaire through to Q23, taking the count to
twenty-three of twenty-seven. Section 5 is closed and section 6 is half done.
Nothing in the repo changed; all of it is specification.

The session opened on a question about when a detent commits and everything
after it turned out to be the same question from a different side: what the
device is allowed to claim while it does not know something. Five of the six
answers are about the honesty budget, and most of them were settled by deleting
a mechanism rather than adding one.

**Q18 is B — a list rotated through, press to select — with commit semantics
that depend on the attribute's type.** Numeric attributes commit on the detent;
enum attributes move a candidate and commit on the button. I first framed that
as trading consistency for usability and it is the other way round. Levels 1 to
3 already work exactly one way — detents move a cursor over an array, the button
commits, nothing leaves the device while rotating — so an enum at level 4 is a
fourth carousel level obeying the rule the first three already obey. It needs no
new code shape at all: the selection path already carries a cursor per level,
and entering the attribute costs one string match to place that cursor on the
current value. The genuinely anomalous case in this interface is the *numeric*
level 4, the one place where a detent has an outward effect.

That exception is earned by a specific property, and naming it is what made the
answer hold: **commit-on-detent is required exactly where the target cannot be
known in advance and has to be felt for.** Volume is judged by ear, brightness
by eye, temperature by the room; "right" is not a number nameable beforehand, so
withholding the change until a press removes the signal being steered by. An
enum is the opposite — the target is a name, known before the knob is touched.
The same property runs the other way for the intermediates: every value passed
through on a numeric sweep is a legal, cheap, on-the-way state, whereas every
intermediate in an enum list is a **destination**. Scrolling past `Netflix` to
reach `HDMI 2` means actually switching the TV to Netflix, which takes seconds
and sometimes launches an app. Coalescing does not rescue that, because the
failure case is a slow deliberate scroll — exactly what reading unfamiliar
option names looks like.

Option A, the blind cycle, was never the cheaper option it appeared to be.
There is no `next_source` service, so advancing one still requires the ordered
array and a string match to find the current position; A and B store the same
thing and differ only in whether the candidate is visible before it is
committed. B also produces a cancel for free — Q12 gave both buttons fixed,
level-independent meanings, so ascend out of an enum level 4 discards the
candidate. Scrolling a source list, finding nothing wanted and leaving the TV
alone is possible only because rotation was not already committing.

**Q19 is A — no age on the glass, ever — and it killed an assumption the
project has been carrying since the note was written.** The reasoning I brought
to it was that this is a controller and not a monitor: knowing when the AC was
last set, or when the value arrived, changes no action I would take. What
matters is whether the value on screen is current, and that is the link's
business. The mechanism underneath turned out to be sharper than that. Under
`subscribe_events` nothing is polled — Home Assistant pushes on change and is
silent otherwise — so **the age of a value measures how often it changes, not
whether it can still be trusted.** A lamp untouched since morning has a local
arrival age of hours and is perfectly true. Silence is the healthy case.

That is what disposes of option B, the stale-past-a-threshold mark, and on
better grounds than redundancy: a lamp nobody has touched and a socket that died
an hour ago accumulate age identically, so B raises a warning on healthy
entities and stays silent about the one case that matters until link state
reports it anyway. It is a false signal rather than a duplicate one. The corollary
is that **the honest instrument is per-connection, not per-entity** — one number,
not six — and its resolution is bounded by the keepalive interval rather than by
anything in the data.

Two smaller things came out of it. HA's own `last_changed` and `last_updated`
are ISO 8601 strings on HA's clock, so rendering an age from them needs SNTP, a
timezone and the assumption that the two clocks agree; a local arrival stamp from
`esp_timer_get_time()` needs none of that. The local stamp is kept anyway, unrendered,
because the project note already wants the coalescing interval derived from a
measured tick-to-`state_changed` latency rather than a guessed 100 ms, and that
measurement is exactly an arrival timestamp against a send time.

**Q20 is B generalised into a conditional status bar, and the generalisation is
the useful half.** Nothing is shown while everything is healthy; link state goes
upper-left, battery upper-right, other system state upper-middle, on every level,
overlaid in the corners rather than reserving vertical space — which is free only
because Q16 keeps the centre to a value and a unit, so the corners are genuinely
empty and nothing reflows when the bar appears.

The argument that decided the battery half is worth keeping, because it
generalises well beyond batteries. A warning that fires when the charge crosses
20% fires while the device is dark in a drawer, and there is nobody to deliver it
to. **On a device asleep upward of 99% of the time, an event-latched notification
is structurally undeliverable; only state evaluated at wake works.** So the rule
became: nothing is latched, every status entry is derived from current state at
render time, and a pop-up is that same state's first-observation presentation
rather than a separate object with its own lifetime. An ACK dismisses the
presentation and never the condition. That also disposes of the un-ACKed pop-up
at the thirty-second sleep boundary — sleeping on an unread warning costs nothing,
because the condition still holds and re-presents itself at the next wake.

The one class that breaks the model is informational — "sync successful" has no
persisting condition to derive from — so those are restricted to the direct
result of an action just taken, where the screen is lit and someone is looking by
construction. Anything the device wants to say unprompted has to be a condition
in the bar instead.

Pop-ups got a universal grammar: either button acknowledges, the knob scrolls
the text, and nothing auto-dismisses on a timer. Collapsing both buttons to one
meaning is what defuses the modality trap rather than merely signposting it — a
pop-up has nothing to navigate into or out of, so the two buttons have nothing
left to distinguish, and **no press can be wrong.** That is a stronger property
than an indicated mode, because the mode cannot be mispredicted. It also closed
a gap I had raised a turn earlier: I thought the level-4 gate needed an explicit
repeat rule or a spin would produce a pop-up per detent, and it does not, because
a detent while a pop-up is up scrolls the message rather than attempting an
action. A second gate cannot be reached without dismissing the first, so the
sequence is self-limiting by construction.

The reconnect pop-up was cut. A wake from deep sleep climbs the whole ladder —
Wi-Fi association, TCP, the WebSocket upgrade, HA's `auth_required`/`auth`/`auth_ok`
exchange, then `subscribe_events` — and only from the last rung is the cache
trustworthy, but the whole thing is quick and the link indicator already
distinguishes blanks-because-arriving from blanks-because-broken. A pop-up that
appears and vanishes within two seconds on every single wake is noise on the most
common interaction the device has, and it would give up what Q13 bought: a wake
costing one GPIO write, because the ST7789 holds the finished screen in its own
GRAM through sleep.

**Q21 is C — immediate local application with a visible pending mark.** The
protocol fact that shapes it is that a service call produces **two** returns and
they are not the same claim. A `result` message carries the `id` assigned to the
command and says HA *accepted* it; a `state_changed` event says the world
*changed*, carries no `id`, and is the same event every other HA client sees.
They can disagree — a bulb rounds 200 to 198, a Zigbee frame is lost, an AC
routing through a vendor cloud takes seconds — so "confirmed" is ambiguous until
it is said which return counts.

The `Decides` line asked whether a cache entry holds one value or two, and the
answer splits B from A and C rather than A from C. Even A needs an in-flight
notion, because a `state_changed` generated before the command landed will
otherwise snap the screen backwards through the old value — the visible failure
the project note names. Since `state_changed` carries no correlation id, A and C
need the identical desired/confirmed pair and differ only in whether the
difference is drawn, which makes this a display decision and cheap to reverse.

Pinning down what the mark asserts mattered more than choosing it. It means
**"I asked for this and have not heard back"**, never "this value is uncertain" —
so a change made from the TV's own remote arrives as a plain `state_changed`,
updates the value and renders unmarked, which is right. That definition is also
what later killed option A of Q23.

The open problem the answer surfaces is that two requirements pull opposite
ways: an external change arriving mid-command must be accepted, and a
pre-command event must be rejected, and nothing in the message separates them.
Ordering by HA's `last_updated` against the last one stored handles duplicates
and out-of-order delivery, and needs no wall clock because HA timestamps are only
ever compared to other HA timestamps — but it does not separate these two, since
a pre-command event is still newer than its predecessor. That needs a local settle
window sized to the measured command-to-`state_changed` latency.

**Q22 is D — HA's own message verbatim.** A rejection is the one message in this
protocol that is unambiguously mine: it comes back as a `result` with my `id`,
`success: false`, and an `error` object carrying `code` and `message`. B dies
because its entire information content, "this was an explicit reject", is a strict
subset of D's. C dies twice over and the two reasons are independent — the table
would have to be maintained by hand, and HA's `code` is coarse enough that
integration failures surface as something generic with all the specifics in
`message`, so the lookup would mostly resolve to "unknown error" for exactly the
failures worth explaining.

Storage is one global capped buffer rather than a per-entity field, since only
one error can be presented at a time, which is what makes it affordable to be
generous — 128 or 256 bytes is the difference between a sentence and a fragment.
Truncation is safe here in the way Q18's enum cap was not, because the text is
displayed and never sent back. Two traps follow from truncating it: the cut has
to land on a UTF-8 codepoint boundary rather than a byte, or LVGL is handed an
invalid sequence, and the font is compiled with a chosen character subset, so
anything outside it renders as boxes — which reads as corruption rather than as a
missing glyph. A one-branch fallback to `code` when `message` is empty costs
nothing and is not the translate table that was rejected.

D also means firmware bugs surface on the panel — a malformed message or an
out-of-range command now shows HA's protocol error text on the glass. Under Q02,
two expert users and discoverability explicitly not a requirement, that is a
feature rather than a cost. And it retroactively justifies the scrolling pop-up
body: without D every message would be a compile-time string written to fit, and
the knob would have nothing to scroll.

**Q23 is B extended with the pop-up as its explanation, which is C's
informational value without C's new screen.** Two of the three options were
already closed — Q19 killed per-value staleness marks, so the marking half of A
and B is identical and lives in the corner chrome, and C would reverse Q20's
choice of chrome over a takeover screen. What was actually live was whether the
knob means anything when nothing is listening.

The argument against A was mine and it is the stale-intent problem: a command
queued while disconnected was correct when formed and wrong by the time it lands.
Turn the TV on with the link down, turn it on and then off with the real remote,
and the queued command switches it back on when the link returns. I said that
would have to be resolved on HA's side, and that step is wrong — HA has no
compare-and-swap in its service API, but the check is available on the device
using the mechanism Q21 already established: store the entity's `last_updated`
as of queueing, compare it to what comes back on reconnect, discard if it moved.
The conclusion survives anyway, on cost rather than impossibility — a stored
timestamp per queued command and a discard policy, buying a delayed action that
has stopped being expected.

A also breaks the pending mark's definition. With the link down nothing was
asked, so a mark meaning "I asked and have not heard back" would be asserting
something untrue about the device's own I/O — the one category of statement Q19
decided it would always be honest about. The answer sidesteps it instead of
patching it: a level-4 commit attempt stores nothing, changes nothing, sends
nothing, and raises a pop-up that acknowledges away and re-arms for the next
attempt.

Generalising that to every blocking condition gave Q20's blocker/non-blocker
split an operational definition it did not have: **a blocker is a condition that
gates a commit.** Link down blocks. Config drift blocks, for the affected
entities. Battery below 20% is real, belongs in the bar, and stops nothing.
Values freeze and dim while the link is down, reusing the treatment Q09 already
gave `unavailable`; blank is not available because it is already taken by the
never-acquired state at a cold wake, and conflating "never knew" with "knew,
cannot verify" would collide exactly where the difference matters. Dimming is a
binary signal for a decay that is continuous — a value is nearly true one second
after the drop and worthless ten minutes later, and the dim looks the same
throughout — which is not a flaw in this answer but the price Q19 quoted when it
decided not to render age.

I first called the result read-only, and that is too broad. A settings page is
going to exist holding local device-only configuration, and nothing that never
leaves the board should care about HA's reachability. The gate is on **outbound
network actions**; navigation on levels 1 to 3 runs from NVS topology and is
unaffected. What that page contains, and where it lives in a four-level carousel
that has no room for something which is not a domain, an entity or an attribute,
is undecided and new.

Two things I got wrong and corrected mid-session, both worth keeping because
both were confident. I claimed the pending mark had already been chosen in the
Q11 reasoning; it had not — it appeared there as a test case against a bad
argument, and it survives either answer. And I read Q13 as having established
that the screen never changes without input, which it did not: it protected the
meaning of the *next input*, which a position reset changes and a value update
does not. Notifications, status chrome and `get_states` filling in blanks at wake
all change the screen and move no cursor, so there was never a conflict to
resolve.

Carried forward. Bench, unchanged: the I2C scan with the BQ25896 charger and
BQ27220 gauge as positive control, board deep-sleep current, and the encoder's
resting levels at successive detents. Wire, now with three more: whether
`target_temp_step` appears in the AC's attributes, the longest option string
across the real `source_list` and mode lists, whether any device exposes
attributes as separate `number`/`select` entities, whether registry access for
labels needs an admin token, whether HA's error `code` is as coarse as expected,
whether `hvac_mode` really is the entity's `state` rather than an attribute, and
the command-to-`state_changed` latency that sizes both the coalescing interval and
the settle window. Design, open: the settings page and where it attaches; the
keepalive interval and missed-ping threshold, which together are the worst-case
window for displaying something untrue; the pending mark's resolution rule when
confirmation never arrives, and whether a silent failure should look different
from a rejection given the rejection now carries text; whether the pending mark
should vary per domain, since the room already confirms a TV volume change faster
than a glyph can; whether the carousel wraps or clamps; the level-4 ambiguity
between two enum attributes of one entity; `area` stored in NVS with no consumer;
and the Wi-Fi provisioning path that persisted credentials quietly assume.

Q24 is effectively pre-answered — its option D is the inert-knob case Q23 chose —
so next session confirms it rather than deriving it, then Q26 and Q27. Q25 stays
blocked on the `websocat` session.

### 2026-08-21

Carried on through the requirements questionnaire in chat, Q11 to Q17, taking
the count to seventeen of twenty-seven. Section 4 is closed, section 5 is
closed bar its last two, and Q18 was answered and then reopened for a re-take.
One process correction landed early and is worth recording because it changed
the rest of the session: I had been paraphrasing each question's options
rather than reading them out, which meant the answer was being given to my
interpretation of the choice rather than the choice. Read verbatim from there
on. The same applies to Home Assistant itself — none of its API, entity model
or hierarchy has been studied yet, so it gets explained from the bottom rather
than assumed.

The thread running through all seven answers is that the shape of the
interface turned out to decide the shape of the data model, and mostly by
deletion.

**Q11, the top level, is type-first, and rooms are not a level at all.** The
mechanism that makes this a small question rather than a large one is that the
four-level carousel is not four data structures. It is one flat array of the
topology records written into NVS at sync — `entity_id`, friendly name, domain,
area — plus a selection path, meaning a level index and a cursor per level.
Each level is a filter over that array and a projection of the distinct values
of one key. So the question is only which key level 1 projects. `domain` is a
small integer drawn from a set bounded at compile time, so its labels are
static strings in flash with nothing stored per entity; `area` would have
needed de-duplicating into a normalised table with entities holding an index.
Three or four rooms across six devices buys nothing at the top, and the
friendly name already carries the room because that is how things get named in
a small flat — "Bedroom lights" is both the entity and its location. I first
rejected showing the room as a second line on level 2 on the grounds that it
breaks one-item-per-screen, and that reason does not hold: the uniformity that
matters is the gesture grammar, and a second line inside an item adds no
carousel item and changes nothing a detent does. The reason that does hold is
Q06's own principle — display only what the room cannot tell you — under which
the room name is the most redundant thing that could be on the glass, because
I am standing in it. Worth keeping the distinction: the weaker argument would
also have banned the units and the pending mark.

**Q12 is plain short presses only, on both buttons.** The worksheet wrote this
question for a single-button device; there are two, GPIO0 to descend and GPIO6
to ascend, so long-press-as-back was never needed. What the question is really
about underneath is the button's event vocabulary, and the cost of a
duration-based second meaning is not the timer. A press is two interrupts, and
if short press is the only meaning it dispatches on the **down** edge and the
up edge is discarded. The moment any gesture depends on how long the button is
held, dispatch cannot happen on the down edge any more, because at that instant
it is not yet known which gesture this is — so every short press on that button
becomes late by the whole hold threshold, typically 300 to 500 ms. Acting on
the down edge and undoing it if the threshold arrives is worse, because the
screen then shows something it takes back. The input queue message is therefore
`{which button}` and nothing else. Press-and-hold-to-repeat is what this gives
up.

**Q13 took two attempts to even parse, and the confusion was mine but useful.**
I read it as "what screen does a wake land on" and answered that instead —
which turned out to answer a real question anyway: the selection path is not
preserved across sleep, so wake lands on the same default level-1 screen as a
cold boot, meaning no `RTC_DATA_ATTR` cursor and one entry point rather than
two. The question actually asked about the awake device with the screen still
lit and no input arriving. Two independent timers were hiding in it: the power
timeout that Q03 already settled, and a position timeout that would reset where
you are in the tree. Deep sleep wipes RAM so the path dies for free there, but
light sleep keeps RAM, the socket and the subscription, so landing at the top
after a light-sleep wake is a choice and not a consequence.

What a position reset buys is exactly one thing, and naming it is what settled
the question: it disarms the knob. Levels 1 to 3 only move a cursor; level 4 is
the only place where a detent becomes a service call, so a device parked at
level 4 with the screen lit is one where a bump changes a real lamp. A
separate, shorter lit-screen timer would cut that armed window from thirty
seconds to ten, at the cost of a screen that moves while being looked at — and
a screen that changes without input is the failure a single-control interface
actually dies of, since the next detent then means something different from
what it meant three seconds earlier. So: **no separate inactivity timer.** One
thirty-second one-shot that pops level 4 up to level 3, drops the backlight and
enters light sleep as a single event.

Two things fall out of that. The first is that **the state machine now has no
timer-driven transitions at all** — every transition is a button, a detent or a
network event, the render task's timer list stays empty of UI timers, and the
only one-shot in the system belongs to the power manager. That is precisely
what the question was for. The second is a hardware consequence: the pop should
happen at sleep *entry*, not at wake. The ST7789 holds its own GRAM and
refreshes the glass from it independently of the SoC — LVGL never owned a
framebuffer — so a screen flushed before `BL_EN` goes low is still sitting in
the panel through the whole sleep. Wake then costs one GPIO write and the right
screen is already there. Doing it at wake instead would put a full screen
transition, the 43.5 ms worst case measured on 2026-08-19, inside the
time-to-first-pixel that Q02 said is being benchmarked against the phone.

**Q14 is no acceleration, ever, with a per-domain default step that HA
overrides where HA reports one.** Home Assistant carries `target_temp_step`
alongside `min_temp` and `max_temp` on a `climate` entity, and `step`/`min`/`max`
on the `number` domain; it carries no step at all for `light`, `media_player`
or `cover`, where brightness is simply 0–255, `volume_level` a float 0.0–1.0
and position an integer 0–100. So both halves of the conditional I wrote are
true simultaneously across different domains, and the profile table needs the
default column regardless, because a `climate` entity can omit the attribute
and the knob cannot be allowed to do nothing when it does. Step, min and max
all arrive inside the state object, which makes them **state rather than
topology** — none of them go into NVS and all of them are null on wake, which
is self-consistent, since with a null value there is nothing to nudge anyway.
And a second unit trap of the same shape as the `brightness` 0–255 versus
`brightness_pct` one found on 2026-08-20: `volume_level` is a float from 0 to
1, so a two-percent step is `0.02` and the percentage on the glass is something
the controller computes for display. Two representations of one quantity in one
firmware, and the conversion goes in exactly one place or it goes in five.

The genuinely wrong step in my own reasoning here was the exception I built the
case on. I argued that most adjustment is local nudging around a remembered
value — true, and it is why acceleration buys so little — but then made blinds
the counter-example, on the grounds that they go end to end. They do not do it
by turning: `cover` exposes `open_cover`, `close_cover` and `stop_cover`, which
take no argument at all, with `set_cover_position` as the secondary control. So
full travel was already one service call and never a step-size problem. It is
also a bad interaction independently of step size, because a cover takes ten or
twenty seconds to travel and reports a position that lags the knob for the
whole gesture. That correction found the third widget shape — bounded numeric,
enumerated choice, **action** — which the 2026-08-20 entry predicted would be
absent from v1's domains and retrofitted painfully. It is not absent; it is
inside `cover`, and it was being modelled as an awkward number. Domain-native
actions cost nothing to discover because they are properties of the domain, not
of the instance, so they live in the profile table as static flash data keyed by
the domain integer already stored. Arbitrary presets like "blinds at 40%" are
the opposite — instance-specific, invented by me, nothing in HA implies them —
and Q07 already said where those live: a scene in HA, triggered by the
controller.

Acceleration would not, incidentally, have been expensive. PCNT cannot
timestamp anything, but one `esp_timer_get_time()` per batch read gives
velocity as `delta / elapsed` without per-edge stamps. It lost on behaviour:
the same physical gesture producing different results by wrist speed makes
overshoot correction require a deliberately slow turn. The encoder queue message
stays a plain accumulated delta with no timestamp in it.

**Q15 is that the knob's meaning is always on the glass**, and the carousel had
already dissolved the question it was asking — level 3 *is* the sub-mode
selector, so colour temperature, source and volume are sibling attributes of
one entity rather than modes to design. What survives is the failure the
question exists for, a mode whose indicator is off-screen, since in this
structure the knob's meaning is established by the path taken and a path is a
memory. The answer is large `<` and `>` at the screen edges: at levels 1 to 3
they mean *there is more this way*, and at level 4 they stop being navigation
and become the unit, `-0.5` and `+0.5` flanking `23`. That answers "what is one
detent worth", which nothing else on the screen answers. Enums fall back to
plain chevrons, because an enum in HA is a current value plus a companion list —
`hvac_mode` out of `hvac_modes`, `source` out of `source_list` — so the step in
a list is "one item" and there is no delta to print. Two consequences: the
chevrons need the profile table's default step to draw anything before state
arrives, giving that constant a second consumer; and they show granularity, not
identity, so `-5 · 40 · +5` could be brightness or volume. The residual
ambiguity is two enum attributes on one entity — an AC's `hvac_mode` and
`fan_mode` both render as a bare string between chevrons. Left unresolved.

**Q16 is value plus unit and nothing else.** The bar or arc went out for
readability on a 170 px panel, with the argument noted as reversing for
brightness and volume, which are percentages of a range that cannot be felt
until the device responds; `min` and `max` arrive with state anyway, so adding
it later is render-only with no data-model cost. Secondary state went out on
two arguments and the second is the better one. Q06 covers it partially, but
"this is a remote, not a monitor" covers more, because it also excludes facts
the room genuinely cannot tell you — whether the AC two rooms away is actively
cooling. HA models these as separate fields and it is a real distinction:
`hvac_action` reports heating or idle while `hvac_mode` reports what was asked
for, and a unit set to heat can sit idle because it reached the setpoint.

**Q17 is a capped fixed buffer, scrolled when it overflows, no pointers
anywhere.** I assumed at first that scrolling implied a heap pointer, and it
does not: truncate-versus-scroll is a rendering decision and cap-versus-heap is
a storage one. `LV_LABEL_LONG_SCROLL` scrolls a `char[N]` perfectly well, and
the only thing that forces a pointer is deciding the text has no maximum length
at all. That matters because with every field fixed-size the cache stays a plain
struct array — a write is a `memcpy` into storage that already exists, the worst
case is truncation, and the render task can read at any moment with no
coordination. One heap pointer means malloc, swap and free racing a render task
that may be mid-draw on the old pointer, which needs a lock, refcounting or
deferred free, and the never-coordinate property is gone. That is the exact
lifetime question the render loop stalled on back on 2026-08-19.

I also overstated the cost of scrolling and had to walk it back. It is real —
an LVGL animation timer fires every `LV_DEF_REFR_PERIOD`, 33 ms, invalidating
and redrawing the label for as long as it is on screen and overflowing, which
is structurally the same shape as the periodic-tick problem already solved for
light sleep. But it only happens while the screen is lit, and a lit screen means
the AW9364 backlight is drawing tens of milliamps, against which waking the CPU
thirty times a second is noise. It also stops dead at the thirty-second sleep
boundary. Font auto-scaling was rejected in its favour, and the reason kills a
criterion I had been carrying: "legible from across the room" is the wrong test
for something held in the hand, which makes option C an unlikely answer to Q27
when that arrives.

**Q18 was reached, explained and then deliberately reopened** rather than
answered in a hurry at the end. What is on the table is that an enum attribute
arrives with a companion array whose string lengths *and* element count are both
unknown, so storing one costs `char options[MAX_OPTS][MAX_LEN]` plus a count
and a policy for HA reporting more than fits. The trap is on the way out:
`select_source` takes the source **name string**, exactly as HA gave it, with no
index — HA does not accept "option 3". So a string truncated for display cannot
be sent back, which makes the cap a hard correctness bound rather than a display
convenience, and it must be at least as long as the longest option name the real
devices report. That number is a `websocat` question. Enums are the only place
in the design where what was stored has to be byte-exact; numeric attributes go
out as numbers and display never affects correctness.

Nothing in the repo changed — no code, no commits. The one artifact produced is
[[home-assistant-rotary-controller-spec]], a vault note holding all seventeen
answers with the mechanism each turned on, written because the answers had been
accumulating only in log prose and the firmware needs one place to read them
from. Q18 is marked in it as answered-then-reopened.

Carried forward, unchanged from yesterday except where noted. Bench: the I²C
scan with the BQ25896 charger and BQ27220 gauge as positive control, board
deep-sleep current, and the encoder's resting levels at successive detents.
Wire: whether `target_temp_step` actually appears in the AC's `attributes`
object, the longest option string across the real `source_list` and mode lists,
whether any device exposes attributes as separate `number`/`select` entities,
and whether registry access for labels needs an admin token. Design, newly
open: whether the carousel wraps or clamps at the ends of a level, which the
chevrons imply an answer to; the level-4 ambiguity between two enum attributes
of one entity; and `area`, which is now stored in NVS with no consumer at all.

### 2026-08-20

Ran the requirements questionnaire built last session — in chat, one question
at a time, rather than in the worksheet artifact, because the worksheet turned
out to be unfillable. It was published as static HTML in a sandbox: the A/B/C
letters in front of the options are CSS counters
(`content: counter(opt, upper-alpha)`), the "own answer" row is another `<li>`
with a dashed border, and there is no `<input>`, `<label>` or `<script>`
anywhere in the file. Swapping the list items for radio buttons would have made
them clickable, but the selection would live only in that tab's DOM and never
come back — a genuinely fillable sheet needs a declared runtime storage
capability, not a markup fix. Going question by question in chat also puts the
reasoning where the spec actually wants to be, which is this log.

Ten of the twenty-seven answered; sections 1–3 closed.

**Section 1, what the object is.** It's carried, not fixed (Q01 = C): active
while in use, then light sleep on a short timeout, then deep sleep on a longer
one, and in deep sleep upward of 99% of the time. The reason that's question
one is that the HA WebSocket API is push-based — authenticate once, subscribe,
and events arrive — but the subscription exists only as long as the TCP
connection does. Modem-sleep and light sleep keep the association, the IP and
the socket, so the subscription survives and wake is sub-millisecond. Deep
sleep resets the SoC: socket, TLS session, association and DHCP lease are all
gone, and waking means a full re-association, handshake and auth before
anything on the glass is true. So the deep-sleep tier's real cost isn't
current, it's time-to-truthful-screen — and the TV-remote analogy stops there,
because a remote transmits and displays nothing while this device's whole job
is to show state. Q02 = A: only me and my partner, both expert users, no
guests. That removes discoverability as a requirement but not consistency,
because memory is per-frequency — a mode used every evening is free, one used
twice a winter is forgotten — so the modality budget is generous on daily
paths and near zero on rare ones, which argues for a uniform gesture grammar
across domains rather than per-device idioms. The scope note attached to it is
more load-bearing than the answer: the device's justification is that it beats
*unlock phone → open app → find entity → tap*. That's a latency benchmark, and
the deep-sleep reconnect sits inside it. Q03 = A: screen fully off, wake on an
encoder turn or either button, and the wake turn is swallowed. Half of that is
forced by hardware rather than chosen — PCNT lives in the digital power domain
and doesn't survive deep sleep, so every edge between the wake and the point
where PCNT is reconfigured lands on an unconfigured peripheral; a "counted"
wake turn would count an arbitrary fraction of the motion. All four candidate
wake pins are usable: encoder A/B on GPIO4/5, the encoder press on GPIO0 and
SW3 on GPIO6 are inside the RTC range 0-21, and their 10K pull-ups go to
`VDD3V3`, the always-on rail, so their levels stay meaningful while the SoC is
down. The trap is that `ext1` is level-triggered, which turns the encoder's
resting levels per detent into the fact that decides whether wake-on-turn works
at all — unmeasured, now on the bench list. Also asked and not settled: whether
there's an IMU to wake on. Nothing in the traced rails or on the I²C bus (the
BQ25896 charger and BQ27220 gauge, and nothing else) says yes, but that trace
wasn't looking for one, so the answer is an I²C scan with those two parts as
the positive control.

**Section 2, the entity set.** Q04 = B, about six things — three light groups,
TV, AC, blinds — with the four-level carousel sketched: device type, then
device, then attribute, then value, one item per screen, encoder rotates,
GPIO0 selects, GPIO6 backs out, settings at the end of level 1. The correction
that mattered is at level 3: in HA those aren't separate entities. A `light` is
one entity whose state is on/off and which carries `brightness`,
`color_temp_kelvin` and `effect` as attributes of the same state object; a
`climate` carries `temperature`, `hvac_mode`, `fan_mode`. So level 3 picks an
*attribute* of an entity already selected — one subscription feeding several
screens, all updating together in a single `state_changed` event, rather than
several independent cache rows with their own staleness. The exception to watch
for is integrations that expose separate `number`/`select` entities for things
that look like attributes, which is a fact about this HA instance and belongs
to the `websocat` session. Q05 = A–D — `light`, `media_player`, `climate`,
`cover` — with a Xiaomi robovac and the d-control ESPHome remote known to be
coming. Those four are, not coincidentally, exactly the domains that fit one
shape: a bounded number the knob moves, with an enum or two attached. Both
future items break it in different directions — a vacuum has no number to turn,
only commands to fire, and the d-control's "Trigger Collar Beep" is momentary
despite arriving as a template `switch` (declared as an ESPHome `button:` it
would arrive as a `button` entity, so the shape the controller has to handle is
partly a choice made on the other device). The profile table therefore needs
three widget shapes — bounded numeric, enumerated choice, action — and the
third isn't in v1's domains at all, which is precisely how it gets designed out
and retrofitted painfully. Q06 = A, and the principle stated underneath it is
sharper than the option text: display only what the room can't tell you. The TV
shows what's playing, the lamp shows it's on, the blinds show where they are.
That initially kept `current_temperature` on the climate entity and then killed
it too, on the argument that the setpoint is absolute — 23 inside regardless of
what's outside — so level 4 shows exactly one value with no per-domain context
attributes anywhere. What survives for a different reason is the attribute
being edited: the encoder is *relative*, it reports change and not position, so
the value on screen is the cursor, not a readout. Two further decisions came
out of the same answer. Values are null on boot and on wake, never the last
remembered ones, which deletes the entire class of bug where the screen
confidently shows something that changed while it was asleep, and deletes
wake-time reconciliation with it. And notifications are a popup where the
action is taken, covering most of the screen, while continuous facts — battery
charge from the gauge, link status, staleness — live in a persistent status
strip: a clean condition-versus-event split. Null-on-wake collided head-on with
the dynamic hierarchy sketched in Q04, since a carousel fetched at connect time
means there's nothing to render on wake at all — no values *and* no items — and
that collision is what produced the topology/state split below. Q07 closed as
scenes and scripts in, automations out, with the logic living in HA and the
controller only triggering it. The route there was a real automation: a
"Bedroom lights day" that a Matter/Thread button triggers, whose action is
purely a state assignment and therefore converts to a scene — with the unit
trap that scenes store raw `brightness` 0-255 while service calls take
`brightness_pct`, so 70% is 179. What a scene can't absorb is sequences,
delays, conditions or any service that isn't a state assignment; those need a
script, which is also the escape hatch for keeping the automation's sun
condition out of the carousel instead of listing day and night variants
separately. The responsibility boundary is delivery: the controller's job ends
when HA has the call. One mechanism correction — that isn't an HTTP ACK, it's a
WebSocket command carrying an `id` and a `result` message coming back with the
same `id` and `success: true/false`, which is also how you know which of
several in-flight calls failed. And one behaviour to know: a script's default
`mode: single` drops a re-entrant call *while still returning success*, so a
stray double-press on a slow script looks like it worked and did nothing.

**Section 3, how a thing is named.** Q08 didn't match any option as written —
it's C's discovery mechanism feeding B's storage. The binding rule is: label
chosen in HA, resolved to an `entity_id` by an explicit manual sync, stored in
NVS along with the friendly name, domain and area, and never re-resolved
automatically. The consequence worth having deliberately is that startup has no
resolve phase at all — a cold boot goes from Wi-Fi straight to subscribing, and
every way that can fail has been moved onto one deliberate action taken while
standing in front of the screen, which is the best possible place for it. Under
a literal "resolve at connect", every wake would carry a registry round-trip
inside the latency budget being measured against the phone. The cost accepted
in exchange is drift: between syncs, NVS can name an entity HA no longer has.
Domain becomes a small integer known at sync time, so the profile lookup never
parses a domain string at runtime; the string caps fall out of the 320 px panel
rather than being guessed, and a truncation is visible during the sync. Q09 = C
splits the two failure modes along the same condition/event line: an entity
whose device is offline reports `unavailable`, is transient and shows as a
dimmed entry; an entity gone from HA entirely never arrives at all, means NVS
has drifted, and gets a popup. Q10 = C and D together — HA owns the
configuration, the knob triggers the sync — and then a reversal worth recording,
because it's the better answer: schema validation on boot, with a mismatch
raising an actionable popup whose re-sync action is pre-selected, rather than
"wipe and re-sync when I remember". What forced it is that `idf.py flash`
doesn't erase NVS, so new firmware boots onto records written by the old layout.
A version tag used for invalidation rather than migration is about five lines
and keeps no old-format parsers alive. Two things fell out: Wi-Fi credentials
also live in NVS, so the topology needs its own namespace or every flash
re-provisions Wi-Fi; and schema-mismatch and never-synced are the same state, so
the empty-topology screen isn't an edge case to handle grudgingly, it's the
genuine initial state every device passes through.

**What actually moved.** The previous session stalled on the render queue's
payload — fixed struct, or something needing a pointer and a lifetime — and it
stalled because the question wasn't answerable yet. It didn't get answered here
so much as dissolved, by three requirements decisions: topology (`entity_id`,
name, domain, area) is written once at sync, capped, into NVS, so it isn't
payload at all — it's in the cache before the socket exists; the
variable-length arrays that blocked it (`source_list`, `hvac_modes`,
`fan_modes`, `effect_list`) are state rather than topology, so they arrive
inside the entity's state object and are null-on-wake like everything else; and
null-on-wake means nothing is ever remembered and re-displayed, which removes
wake-time reconciliation entirely. The doorbell-plus-cache decision survives
intact, with a cache index as its payload. The runtime command vocabulary is
now closed too — authenticate, fetch state, subscribe to changes, call a
service, with registry access existing only inside the sync action — which is a
small enough fixed set to hand-roll rather than needing a general-purpose
client.

**Parked, carried forward.** Bench: the I²C scan with charger and gauge as
positive control; board deep-sleep current; the encoder's resting levels at
successive detents. Design: when the config-drift popup fires given it arrives
unprompted during the wake window, what it says when an integration takes out
fifteen entities at once, what a press does on a dimmed entry, whether the knob
moves between actions inside a popup, and the Wi-Fi provisioning path that
"credentials persisted across updates" quietly assumes. Needs the wire: HA
labels live in the entity registry rather than in state and registry commands
may want an admin token; and whether any of the six devices exposes attributes
as separate `number`/`select` entities.

Nothing in the repo changed — no code, no commits. Q11 (top level type-first as
sketched, or room-first on the locality argument, which is newly available for
free now that `area` is stored) was left open deliberately and gets re-taken
first thing next session, followed by the rest of section 4.

Written a day late, by hand: the SessionEnd writer died mid-response when the
Mac went to sleep, so this entry was reconstructed from the session digest.

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
