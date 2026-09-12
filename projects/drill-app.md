---
tags: [project, software, web, learning]
status: idea
depends: []
created: 2026-09-12
---

# Drill App

## Now

Not started, and mostly not decided either. Three Anki decks were generated
and used for a few evenings; that established what the app is *for* and
produced a set of authoring rules the hard way. Everything about how it would
be built is a sketch and should be argued with before any of it is taken as
settled.

## Goal

A phone-first drill app for short, interrupted sessions — a bus ride, a
queue, ten minutes in a waiting room. Duolingo's interaction model, this
vault's subject matter.

Stated boundaries:

- **Not for teaching new material.** The five courses in
  [[embedded-learning-curriculum]] are done at a desk, with hardware, in
  Claude Code. The app goes alongside the courses, not ahead of them. New
  material may appear, but as a side effect of practising rather than the
  point.
- **Nothing requiring a tool.** No URH (Universal Radio Hacker), no SDR, no
  multimeter, no shell. Solvable in the head with a thumb, or it does not
  belong.
- **Practice over recall.** Reviewing past work is wanted too, but the
  primary thing is exercises, not remembering what a note said.

That first boundary is the load-bearing one, because it is what stops this
from turning into a sixth course. A course module here is theory and then
exercises on hardware; a drill is a question answered with a thumb on a bus.
Those are different activities and the app only does the second.

The ranking in [[embedded-learning-curriculum#What stays worth knowing]] is
what decides how much of the field is reachable this way, and the answer is
not much. Measurement and instrumentation, debugging where the model and the
hardware disagree, owning the specification, and architecture under physical
constraint — items one to four, and the four the note ranks highest — cannot
be drilled on a phone. They need an instrument, a board that is misbehaving,
or a decision with a cost attached. Not attempted.

## Learning value

Retrieval practice on the fifth item of that ranking: physics and arithmetic
with a long half-life. That is the layer that is both genuinely recallable
and genuinely useful, and the layer a desk session skips because it is not
where the interesting problem is that day. Working out a link budget is
never the point of an evening, so it gets done once, checked, and never
recalled again.

The awkward part is worth stating outright, because it is the argument
against the whole project: **the learning value is in the content, not in
the build.** A static page that renders six question types and shuffles a
list teaches nothing this vault is short of — it is text-mediated work in
the sense the curriculum note marks down, the kind an agent writes correctly
on the first attempt. Every other project here is justified by what building
it teaches. This one is not, and pretending otherwise would be the kind of
invented claim the `## Practical value` sections exist to prevent.

So the case for building it has to rest on something else, and whether it
holds is genuinely open. The case for: Anki cannot do multiple choice,
matching or ordering, and self-grading is unreliable on anything but a
numeric answer — so roughly half the exercise shapes that would suit this
material cannot be expressed at all. The case against: three decks already
exist, cost nothing to extend, and the sync, the scheduler and the phone
client are already written by somebody else. That decision is the first item
in the plan below and it is not made yet.

## Practical value

Replaces doomscrolling with something in the same shape — short loop, one tap
to start, trivially interruptible. That is the whole claim, and it stands or
falls on whether the app is actually opened. Unproven, and the Anki evenings
are weak evidence either way: a few evenings is novelty, not habit.

## What the Anki experiment established

This section is evidence rather than proposal. Each item is a failure that
was hit in use, and any design has to deal with it.

1. **Cards must be self-contained.** Decks shuffle, so "same, but a 1 MHz
   channel" has no referent. Applies to the explanation as much as the
   prompt — "fifteen times the FET above" fails the same way.
2. **Exactly one defensible answer, or self-grading breaks.** "Name one thing
   a crystal-less board cannot do" has at least four correct answers. "Is it
   worth doing?" has none that is checkable, because it depends on a cost the
   prompt does not state.
3. **Arithmetic must be trivial.** 10·log₁₀(200 000) is a barrier to testing
   the principle. Powers of ten and factors of two. Realistic messy values
   belong in the explanation.
4. **Givens must be complete.** A power-budget question without the sleep/
   active ratio cannot be answered, whatever the intent was.
5. **Explanations must not widen the claim.** A prompt about a radio node
   became a sentence about boards in general; a prompt about a generic bus
   became a claim about I²C.
6. **One quantity throughout.** τ, 10–90% rise time and I²C's `t_r` are three
   different numbers from the same circuit. A card asking for one and
   answering with another is wrong even when the arithmetic is right.
7. **Irrelevant-but-plausible givens are good.** A duty-cycle question that
   states 868 MHz when the frequency does not enter the calculation forces
   the reader to decide what matters. Fair as long as the value is one that
   would really appear in a specification.
8. **The default scheduler was wrong for this.** Anki re-showed cards within
   the same session and starved new ones. Wanted: everything once first,
   missed ones returning later.

Rules 1 through 6 are all constraints on *generated* content, which is the
thing that makes them expensive. A deck is generated in a batch, and a batch
is only as good as its worst card — one question with two defensible answers
trains the habit of arguing with the app instead of answering it. Whether any
of these can be checked mechanically is open. Rules 1 and 4 look tractable:
a prompt that references another card is detectable by looking for comparative
phrasing with no antecedent, and a numeric question whose stated givens do not
reach the answer could in principle be checked by working it. Rules 2 and 5
look like they need reading. That split decides whether a generated pool is
publishable unread, and it is the difference between this being cheap to feed
and being a second job.

## Architecture

All of this is sketch. None of it has been tried.

The shape being considered is a static site with no backend, hosted somewhere
like GitHub Pages, with app code and question content strictly separated —
the app knowing exercise *types* and no questions at all, content fetched as
JSON from one or more URLs.

| Block | Approach | Why this side of the line |
| --- | --- | --- |
| Renderers, one per exercise type | Built | The only part that is actually the app |
| Session assembly and scheduling | Built | Rule 8 rules out every default scheduler I would otherwise adopt |
| Question content | Generated, reviewed by hand until rule-checking is settled | The half with the value in it |
| Hosting, TLS, CDN | Taken as given — static host | Nothing to learn from re-deriving it, and it is free |
| Login, sync, a backend | Not built at all | One reader on one phone; a server would exist only to store a number |

The attraction of the app/content split is that adding questions becomes
publishing a file rather than a code change, which is what makes
agent-generated content practical. The cost is a schema that has to be right
early, because content authored against a schema is expensive to migrate and
the whole point is to end up with a lot of it.

Two things are undecided and both change the shape:

**Offline.** Whether it matters enough to justify a progressive web app and a
cache is unknown. A plain page that needs signal might be fine, or might kill
the whole idea in a tunnel — and a tunnel is exactly the ten minutes this is
aimed at. This is answerable by use rather than by argument, which is why the
plan puts a week of real use before any of it is built.

**Where mixing happens.** General drills and review of past work could be
merged in the app, by pulling several sources and weighting them, or in the
content, by publishing one pre-mixed pool. The first keeps the sources dumb
and the weights adjustable; the second is much less to build. Undecided.

**Correcting a published question** is the third open one and it is a schema
question rather than an app one. A card that was answered and is later found
wrong can be edited in place — cheap, but it silently rewrites history and
any record of having answered it now refers to a different question — or
superseded by a new id, which keeps the record honest and grows the pool with
dead entries in it. Given that the content is generated and rules 2 and 5 are
the ones hardest to check, corrections are going to happen often enough that
this is not hypothetical.

## Tools

Nothing chosen. Plain HTML, CSS and JavaScript is the assumption until
something makes a framework necessary.

| Purpose | Tool | Note |
| --- | --- | --- |
| App | Plain HTML/CSS/JS | Assumption, not a decision |
| Hosting | Static host, likely GitHub Pages | No backend to host |
| Content authoring | Claude, from the notes in this vault | The pool is generated; the rules above are what it is generated against |
| Client | Android phone, browser | The only target that matters — it is read on a bus |
| The thing it replaces | Anki, three decks | Still the fallback if this loses the argument in the plan |

## Budget

| Item | Cost |
| --- | --- |
| Hosting | Likely 0 € |
| Everything else | 0 € — hardware already owned |

## Software / firmware

No firmware. The software is the whole project, and it is three pieces: a set
of renderers, a question schema, and the session assembly that decides what is
shown next.

### Exercise types

A small fixed set, so the generator picks from a list rather than inventing
shapes. Candidates, none settled:

- single-answer multiple choice
- multiple correct from a list
- matching pairs across two columns
- ordering or ranking
- numeric entry
- a set of statements to mark true or false

Numeric entry is the only one needing a keyboard, which may rule it out on a
phone — or may be fine, since the answers are short by rule 3. It is also the
only type Anki already handles acceptably, so if it survives and the others do
not, the whole project collapses back into extending the decks.

### Content

Questions would be tagged by domain so the app can mix or filter. Domains
that already have material: RF and signals, power budgets, circuits, board
and pin behaviour, symptom-to-cause diagnosis, evidence and measurement
choice, Linux and Yocto. Several of those come straight out of work already
written up — the 869.525 MHz OOK material in [[subghz-collar-remote-clone]]
and [[urh-ook-capture-analysis]], the pin and pad behaviour in
[[reading-a-schematic]], the boot chain and Yocto material across
[[embedded-linux-course]].

A `level` field and Duolingo-style progressive gating is a possibility, not a
requirement. If levels are wanted eventually, the field is cheap to carry
from the start and expensive to backfill.

### Session assembly

Rule 8 is the whole specification here: everything once first, missed ones
returning later. That is not spaced repetition and should not be built as
if it were — spaced repetition optimises long-term retention of a large
stable deck, and this is a small pool being extended continuously, where the
failure to avoid is a new question sitting unseen behind a familiar one.

## Plan

Ordering is a guess and the early items are mostly decisions rather than
work.

- [ ] Decide whether this beats extending the Anki decks, and write down why
- [ ] Decide where content lives and what the question schema is
- [ ] Decide which exercise types are actually worth building
- [ ] Hand-write a small pool and test the rules above against it
- [ ] Build the renderers
- [ ] Session assembly: mixing, weighting, unseen-first ordering
- [ ] Deploy, install on the phone, use it for a week before adding anything
- [ ] Decide whether levels, gating and offline support are worth it

The fourth item is the one that decides the first. A hand-written pool tested
against the eight rules is what shows whether the rules can be met at volume
and whether the exercise types beyond numeric entry actually earn their
existence — and both of those are the argument for building anything rather
than opening Anki.

[[embedded-learning-curriculum]] is where this belongs in the map: it drills
the fifth item of that note's ranking and none of the first four, and it is
explicitly not a sixth course. [[subghz-collar-remote-clone]] is both the
best source of drillable RF material and the sharpest reminder of the
limit — the capture-damage hypothesis that survived a whole session was
killed by a hand measurement, and no phone question could have touched it.
[[embedded-linux-course]] is the other direction: a course module is where
the material is learned, and this is where the arithmetic from it is kept
warm afterwards.

## Build log

Session entries live in [[drill-app-log]].
