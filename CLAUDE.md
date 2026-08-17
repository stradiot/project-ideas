# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An Obsidian vault of prose notes — hardware, embedded and RF project plans. There
is no code, no build, no tests, no linter. Every change is a markdown edit, and
`git` is the only tooling. The remote is SSH (`git@github.com:stradiot/project-ideas.git`);
the same vault is edited from Obsidian mobile over an HTTPS remote, so treat the
working tree as something another device may have written to — pull before
editing, and never force-push.

Text only. No binaries, no LFS. `.obsidian/` is tracked except for the
workspace/cache files listed in `.gitignore`.

## Why it exists

This replaces a bought course, and the reasoning is load-bearing for the rest
of the design. A commercial course is generic by construction — it serves
everyone who buys it, so it covers a lot that is not wanted here, skips things
that are, and assumes a level that is someone else's. Planning the projects
here instead gives a syllabus that is only the interesting parts, work that is
hands-on rather than watched, and a level that matches what is actually known.
It costs the time to write the plans down; the money goes on hardware that
would have been bought anyway, which is why the embedded Linux course budget
is 58 € of parts and no tuition.

The half a course cannot supply is being answered back, and that is what the
SessionStart hook is for. It tells every session to explain the mechanism
before writing code for anything non-trivial, and to cover a missing
foundation rather than route around it. **Learning before doing is therefore
the standing preference here, not a per-session request** — where there is a
choice between handing over a finished answer and walking through why it is
the answer, walk through it. `## Learning value` being the section written
first in every project note is the same rule applied to planning, and the
session log being a study document is the same rule applied to the record:
the log is built out of the explanations given during the session, so an
unexplained session produces a worse note.

The cost of the arrangement is that nothing here is reviewed. No instructor
marks the work, no peer reads the notes, no maintainer rejects a patch, and a
wrong explanation reads exactly like a right one. What limits the damage is
that most of this work ends in a physical result that does not care what
anyone believed — a measured number, a frame a real receiver accepts, an
airframe that flies. That check is real but partial: it only covers what the
build exercises, and it can arrive late. The collar remote beeped about 70% of
the time for months, and the first explanation for why was convincing and
wrong.

So **"it works" and "I understand why it works" are separate claims here**, and
the notes are written to keep them apart. A hypothesis stays labelled as one
until something measured it, a number carries where it came from, and a killed
hypothesis is recorded next to the answer that replaced it rather than quietly
dropped. Those conventions are not stylistic — they are the only review this
work gets.

## Layout and note conventions

- `projects/` — one note per project, from `templates/project.md`. Frontmatter is
  `tags: [project, …]`, `status:`, `depends:`, `created:` (ISO date), and
  optionally `repo:` / `github:` (see below). Body sections in order: Now,
  Lessons, Goal, Learning value, Practical value, Architecture, Tools, Budget,
  Software / firmware, Plan, Build log. `Lessons` is absent until there is one
  — the hook creates it, directly under `Now`.
- `projects/logs/` — one `<slug>-log.md` per project, holding the dated session
  entries, **newest first**. Frontmatter is `tags: [log, <slug>]` and
  `project: <slug>`. Every project has one, created empty, so the pointer in the
  note never dangles and the SessionEnd hook always has an existing file to
  write into.
- `notes/` — reference notes and deep dives, linked from projects, from
  `templates/note.md`. Frontmatter is `tags: [note, …]` and `created:`; no
  `status:`, no plan, no build log — these are subject notes, not work.
- `journal/` — daily notes, `journal/YYYY-MM-DD.md`. Written by automation (below).
- `templates/` — note templates.

Cross-references are wikilinks: `[[subghz-linux-router]]` resolves to
`projects/subghz-linux-router.md`, or to `notes/<name>.md` for reference
notes. The graph is deliberately connected — every note has both inbound and
outbound links, and a cross-reference states *why* the two are related (shared
hardware, a prerequisite skill, the same problem solved differently), never just
that they are. Check both directions after adding a note:

```
grep -oh "\[\[[^]]*\]\]" projects/*.md projects/logs/*.md notes/*.md | sed 's/\[\[\(.*\)\]\]/\1/' | sort -u
```

`README.md` carries the full project list grouped by track (RF, Embedded firmware,
Embedded Linux, Mechanical, Control), ordered so that each project roughly depends
on skills or hardware from the one above it. Every note in `projects/` has a
one-line entry there. A new project note means a new README line in the right
track and position.

## State: `status:`, `depends:`, `## Now`, `## Plan`

These four carry all the tracking. They exist because this vault outgrew being a
list of ideas — it is where work in progress is followed.

`status:` is `idea` → `planning` → `active` → `built`, plus `deferred`. `built`
means it exists and is in use; `active` means hands are on it *now*. Conflating
those two was the original flaw — a deployed device sat at `active` indefinitely.

`depends:` is a directed list of project slugs that must reach `built` before
this one can start. It is deliberately *not* the wikilink graph: wikilinks are
symmetric and say "related", and every note links to five others, so they can
never answer "what next". Keep `depends:` to true prerequisites — a skill or a
piece of hardware this project cannot proceed without.

The bar is deliberately high, because the graph was once authored as a
curriculum and drifted into asserting difficulty ordering as dependency. An
edge earns its place only if the dependent cannot begin without an artifact,
a piece of hardware or a load-bearing skill the other project produces. Not
enough: the same track, the same chip family, ascending difficulty, thematic
adjacency, or "I would learn that there first". **Using a thing is not the
same as having built it** — every Linux board has a bootloader, and that does
not put every Linux project behind the bootloader project. Courses are never
a `depends:` for the same reason: they teach a skill, they do not produce an
artifact anything consumes. Six edges across nineteen projects is the current
state, and it should stay closer to that than to one edge per note.

That rule runs in both directions, and the second half is the one that is easy
to break because `depends:` does not model it. **A course module may not
require a project either.** A module is theory and then exercises that start
and finish inside the module, on hardware the course's own budget already
covers — a course is picked up on a Tuesday evening, a module at a time. A
project can be a module's source material, the specification an exercise is
the first step of, or where the skill is practised for real afterwards; it is
never a step in the arc and never the exercise itself. Writing a module *as* a
project is what once put the second course behind the fourth, through a board
neither of them owned. `notes/embedded-learning-curriculum.md` holds the rule
and the case.

A project is **ready** when every entry in its `depends:` is `built`. That set is
what `README.md`'s "Up next" section lists, and it is derived, not authored —
recompute it after any `status:` or `depends:` change:

```
for f in projects/*.md; do
  printf '%s|%s|%s\n' "$(basename "$f" .md)" \
    "$(awk -F': *' '/^status:/{print $2; exit}' "$f")" \
    "$(awk -F'[][]' '/^depends:/{print $2; exit}' "$f")"
done
```

`## Now` is one short paragraph at the very top of the note: where this project
actually stands. It is the first thing visible on a phone, and it is written by
the SessionEnd hook, not by hand.

`## Plan` is the whole arc in build order, as checkboxes. The hook ticks items it
finished. It never rewrites the *wording* of an item — inventing or editing plan
text is how a plan stops being the plan. An unticked box therefore means not
done, rather than merely unrecorded.

`## Lessons` sits directly under `## Now` and is the other thing the hook
maintains. It exists because the reusable half of a project ends up buried in
its log: how the capture was actually measured, which tool lied and by how
much, which hypothesis was convincing and wrong. Finding that again means
re-reading a few hundred lines of dated prose, so it is lifted out — one bullet
per finding, the claim first, then the mechanism that makes it true, then a
link to the log entry or note holding the detail
(`[[<slug>-log#YYYY-MM-DD]]`).

Three properties make it work, and dropping any one turns it back into a
summary nobody reads:

- **It is written as the work happens, not composed at the end.** A lesson
  recorded the day it was learned has the numbers in it. Reconstructed six
  months later it has adjectives.
- **It is revised in place, never stacked.** When later work overturns an
  earlier lesson, that bullet is rewritten to state the corrected mechanism
  *and* what the wrong hypothesis was — see the 70% entry in
  [[subghz-collar-remote-clone]], where the capture-damage answer was
  convincing for a whole session before hand measurement killed it. Deleting
  the wrong answer silently would throw away the more useful half.
- **It stays short.** Roughly three to seven bullets, held to the same bar as
  everything else here: it earns its place if it would save an hour or stop a
  repeated dead end. Everything else stays in the log.

It is not a status report — `## Now` is where status lives, and a lesson that
stops being true in a month was never a lesson. `built` is not the trigger
either; the section is kept current before that status and after it.

There is one hard rule behind all of this: **nothing in this vault is maintained
by hand.** It is read on Obsidian mobile and written by Claude, so any field that
needs a human to keep it current will simply go stale. Before adding one, decide
which side of that line it is on. The 152 checkboxes that sat unticked through
the vault's entire history are the evidence.

Prose voice throughout: first person or no subject, past tense in logs, plain
sentences rather than bullet dumps. Notes state what is deliberately *out* of
scope and where the build-it/buy-it line sits — keep that when editing.

**Learning value is the primary criterion for every project; practical use is
the second constraint, not the goal.** Where an easier route and a more
instructive one disagree, the notes take the instructive one and say why — see
the honest counter-arguments in `thread-matter-noise-sensor` (Thread is not the
optimal transport) and `subghz-linux-router` (Phase 3 is "openly the
education-only phase"). Suggestions that optimise away the hard part are
usually the wrong advice here; alternatives belong in the note as rejected
options with reasons.

Both halves of that are explicit sections in every project note rather than
something a reader has to infer from the prose. `## Learning value` is why
the project exists and is the section to write first. `## Practical value`
is what the finished thing is actually for, and **several projects have
none** — `bare-metal-bootloader`, `beaglebone-pru-realtime` and
`custom-flight-controller-drone` say so in those words, and
`subghz-linux-router` says its third phase runs out of it. That is the
point of the section: a stated "none" is what makes the claim in
`home-assistant-rotary-controller` or `subghz-collar-remote-clone` worth
believing. Never invent a use to fill the space — naming what would be
bought instead is the more useful sentence, and the note usually already
argues it (Betaflight, Tractive, a €10 logic analyzer).

## How contributions are written

Write for the person who has forgotten the context, because within a few
months that is who reads this. Everything below follows from that. A note or
a log entry earns its place if it would save that person an hour, or stop
them repeating a dead end. Nothing else is a reason to add text.

**These are study materials before they are records.** The reason to come
back to a note is to understand what was done and why it worked, not merely
to be reminded that it happened. So explain the mechanism, not only the
outcome: where a decision turned on how something actually behaves — a
peripheral, a protocol, a kernel path — say how it behaves, and say it in
the order that makes it follow. Expand a term the first time it appears,
hold one thread from start to finish rather than jumping between them, and
let each paragraph set up the next. This is not licence to pad: an
explanation earns its place when it saves the reader re-deriving something,
and `## Now` stays one short paragraph regardless. Explaining happens in the
same voice as everything else — first person or no subject, past tense in
logs — never as a lecture aimed at a reader.

**Record the reasoning, not just the conclusion.** A decision without its
alternatives is unreviewable later — the reader cannot tell whether the
other option was considered and rejected or never seen. Rejected options
go in with the reason they lost, which is the habit the existing notes
already have and the thing most worth protecting.

**Failure and negative results are content, not embarrassment.** The most
useful page in the vault is a log entry recording that five line encodings
were tested against a payload and *none* of them fit — that ruled out a
whole category and pointed at capture damage. Write the dead end, what it
eliminated, and what it cost. A log that only contains successes is a log
that will be re-read by someone about to repeat the failure.

**Name the gap in plain words.** "I do not know how X works yet" is a
sentence that belongs in the note, not a thing to write around. It is the
only way the vault stays an accurate map of where the work actually is, and
`notes/embedded-learning-curriculum.md` is where those gaps get collected
into an order worth closing them in. Vagueness is the failure mode to watch
for: a sentence that avoids admitting the gap will also fail to describe it.

**Be concrete or say nothing.** Numbers carry units and where they came
from — measured, from a datasheet, or estimated, and which. Commands,
register names and pin numbers as actually run, not paraphrased. "869.525
MHz, OOK, 200 µs base tick" is worth a paragraph of prose about radios.

**Study notes in `notes/` teach the mechanism, not the API surface.** The
reference manual already documents the call; what it does not say is why the
abstraction exists and what breaks without it. So: start from one concrete
instance and generalise from it afterwards, name the misconception the note
exists to correct, and carry one worked example with real values all the way
through. Where a topic is a standard interview question, saying so is
useful — several notes already do, and it marks what has to be explainable
out loud rather than merely recognised.

**Register.** Plain sentences, first person or no subject, past tense in
logs. No marketing adjectives — nothing is robust, powerful, seamless or
leveraged. No achievement framing; describe what was done and let it stand.
No second person lecturing in a log entry, and no third person either: the
entry is written by the person who did the work, not as a report about
someone else. Do not pad to look thorough. `## Now` stays one short
paragraph because it is read first and on a phone.

The failure mode there is specific and worth naming, because the log has
already fallen into it. An entry is written from a session transcript, and a
session is a conversation between two participants — so the natural thing is
to keep them apart, and the result is a page that reads "your three presses
agree to within 0.5 ms of my automated edge detection" and "the user pointed
out that 18% was never a designed target". Months later nobody can tell which
half was theirs, and it does not matter: the work was one piece of work. **The
entry has exactly one voice. Everything either participant did is "I".** Never
"you" or "your" for the vault's owner, never "the user", and no imperative
aimed at a reader — "do not trust it for base-tick work" is "it is not to be
trusted for base-tick work". The same holds for `## Now` and `## Lessons`.

**Never claim progress that did not happen.** Do not tick a `## Plan` item
that was not finished, do not promote `status:`, and do not describe a
half-working thing as working. An unticked box means not done rather than
merely unrecorded, and that guarantee is worth more than any individual
entry — one inflated tick makes every other box unreliable.

## The repo ↔ note link, and the journaling automation

A project note whose code lives in a sibling repo under `~/Documents/personal`
carries that directory name in its frontmatter:

```
repo: subghz-linux-router
```

That field is the only link. Matching is exact on the frontmatter block — nothing
is inferred from filenames, and a note without it is simply unlinked.

`repo:` is a local directory name and nothing else — never a URL, never an
`owner/name` pair. The hook greps the whole frontmatter line for exactly the
directory it derived from the session cwd, so anything else there unlinks the
repo silently and its journal entries fall back to the unlinked prose form. The
remote, where a note wants one, goes in a second field that the automation never
reads:

```
repo: d-control-400-remote
github: https://github.com/stradiot/d-control-400-remote
```

Full URL rather than `owner/name`, because Obsidian renders a URL-valued
property as a clickable link. `github:` is optional and decorative — add it only
to notes that already carry `repo:`, since a note with no code has no remote to
point at.

The machinery lives **outside this repo**, in the `claude` package of `~/dotfiles`
— <https://github.com/stradiot/dotfiles>, private — stowed into `~/.local/bin`, so
the entries there are symlinks and the file in the repo *is* the live hook. Read
it there when the behaviour described below and the behaviour you observe
disagree; the scripts are the authority and this section is a description of
them, with a README of its own and a test suite (`tests/test-session-notes.sh`,
30 checks against fixture config dirs and a stubbed model). The hooks are wired
by absolute path under `~/.local/bin` into `~/.claude-personal/settings.json` —
the config dir the `claude-personal` alias selects, itself a symlink into that
same package. There is no default `~/.claude` dir and there should never be one;
`~/.zshrc` aliases bare `claude` to a warning precisely so nothing lands there. A
session whose cwd is outside `~/Documents/personal` is rejected by
`personal_repo_from_cwd` and no vault write happens.

There are five scripts, split so that only the personal config loads any vault
code at all. The other config dir, `~/.claude-work`, runs a SessionEnd entry
point that shares the machinery and stops short of the vault, so a work session
cannot reach this repo or its remote by any route. That separation used to be a
runtime `cwd` check inside one shared script; it is now a question of which
files each config sources, which holds even if the check is wrong. The check
still runs, one layer in.

- `claude-session-notes-core.sh` — the half both configs need: work out which
  config dir the ending session belongs to, decide whether the session is worth
  writing up, build a digest of the transcript, spawn the writer. Sourced, never
  run directly, and it contains no vault code — that ignorance is the point.
- `claude-session-notes.sh` — SessionEnd for `~/.claude-work`: memory notes
  only. Sources the core and stops.
- `claude-session-notes-personal.sh` — SessionEnd for `~/.claude-personal`: the
  same memory note, plus the vault journal, after which the shell commits and
  pushes (`journal: <repo> <date>`).
- `claude-personal-project-lib.sh` — `personal_repo_from_cwd` (maps a cwd under
  `~/Documents/personal` to a repo name, excluding the vault itself) and
  `note_for_repo` (frontmatter `repo:` lookup). It pulls in the core, so the two
  personal hooks source one file rather than two.
- `claude-personal-project-start.sh` — SessionStart: pulls the vault, injects the
  linked project note into that session's context, and states how to work here —
  the learning-before-doing instruction above, plus what the SessionEnd hook will
  write, so the session is steered toward saying the things that make a good
  entry. It also surfaces any pending hook failure (below).

Two gates decide whether anything is written. A session with fewer than two
*real* user turns is skipped before any model is spawned — real excludes tool
results, system reminders and slash-command expansions, all of which the
transcript records as user turns — and the writer is told to reply
`NOTHING SIGNIFICANT` and write nothing when the session produced nothing
durable. Most sessions end one of those two ways, and an empty diff produces no
commit. The writer runs `sonnet` where there is journal prose and `haiku`
otherwise: deciding a finding belongs in `## Lessons`, noticing that today's
result overturns a bullet already there, and holding one voice across a
two-party transcript are judgement work, and `haiku` wrote entries that split
the session into "your measurements" and "my automated one".

It is given `Read,Write,Edit,Glob,Grep` and no Bash tool, with the vault and the
memory directory as its only writable roots. Every git operation below is
therefore plain shell running after the model has exited, rather than something
the model can improvise.

Alongside the journal, every session that clears the gate — work sessions
included — writes durable notes into that project's memory directory under its
own config dir, indexed by a `MEMORY.md` beside them. That half never touches
the vault.

What it writes, per session in a linked repo:

- a `### YYYY-MM-DD` entry in `projects/logs/<slug>-log.md`, written above every
  existing entry — newest first, so the top of the file is the latest work and a
  `[[<slug>-log#YYYY-MM-DD]]` link on a repeated date resolves to the newer one;
- the note's `## Now` paragraph, replaced with where the project stands;
- a tick on any `## Plan` item the session actually finished — wording untouched;
- a `## Lessons` bullet, added or revised, when the session produced a finding
  still worth knowing in a year — most sessions do not, and then nothing changes;
- one line in `journal/<date>.md`: `- [[note-slug]] — one-line summary`, likewise
  above what is already there.

Everything else in the note is off limits: frontmatter, Goal, Learning value,
Practical value, Architecture, Tools, Budget, and the text of plan items. `status:` in particular is a
deliberate edit — the hook does not promote a project to `built`, because
"finished" is a judgement call and a half-working device would claim it.

For a repo with no linked note, `projects/` is untouched and the daily note gets a
`## <repo-name>` heading with prose under it instead. Adding a `repo:` field to a
note is what switches that repo to the wikilink form.

Note names and repo names are independent on purpose — `subghz-collar-remote-clone`
carries `repo: d-control-400-remote`, and that frontmatter field is the only thing
connecting them. Two repos are linked: that one and `beaglebone-green-case`. The
rest under `~/Documents/personal` — `fire-housing-sim`, `homepage`, `office_clock`
— are deliberately not vault projects and journal under their own names.

Only `journal/` and `projects/` are staged — never `git add -A` here, which would
sweep in unrelated Obsidian edits. Because of that the pull is
`--rebase --autostash`: the hook ignores everything outside those two paths, so
unrelated dirty files must not be able to abort the rebase. Without it they did,
and the commit was stranded silently — that is what happened on 2026-08-09. A
genuinely *conflicting* pull still leaves the commit local and unresolved on
purpose, and is never force-pushed.

## Working in this repository

Sessions started *in this vault* are excluded from the automation
(`personal_repo_from_cwd` rejects the vault directory), so nothing is written or
pushed on your behalf here — commit deliberately.

When editing from a session in some other personal repo, do not touch the vault
mid-session; the SessionEnd hook owns those writes, and they are limited to the
log file, `## Now`, `## Lessons`, plan ticks and the daily note. Frontmatter, Goal,
Architecture and the *wording* of plan items are never rewritten by automation —
a change to those is a deliberate human (or explicitly requested) edit.

Automation activity is logged beside the config dir the ending session belonged
to, at `.session-notes-state/log.txt`. Everything here is a personal project, so
in practice that is **`~/.claude-personal/.session-notes-state/log.txt`** — not
`~/.claude/`, which is the wrong place to look and does not exist. Check it when
a journal entry or a push seems to have gone missing.

A failure no longer has to be found by looking, though, because the log was the
wrong place to keep one: everything after the session ends runs detached, so a
failure that only reached the log reached nobody. It is now reported twice — a
macOS banner at the moment it happens, and a line in
`.session-notes-state/failures.txt` that the SessionStart hook surfaces in the
next session started in a personal repo, then drains so it reports once rather
than nagging. Reported that way: the writer exiting non-zero, the writer being
killed by its 15-minute timeout, and each of the vault git steps.

The writer's exit code used to be discarded, which is what made this worth
building. A crashed, rate-limited or unauthenticated writer produced
`vault: nothing written, no commit` — byte for byte the line a genuinely quiet
session produces — so the likeliest failure was indistinguishable from normal
operation. Nothing bounded the writer either, so a wedged one sat there and the
log simply stopped after `spawned`. Both were invisible from the phone's side,
where a stranded commit looks exactly like a session that wrote nothing.

Which config dir that is gets read off the transcript path the hook is handed,
not from `CLAUDE_CONFIG_DIR`. A session lives at
`<config dir>/projects/<slug>/<session>.jsonl` with that project's `memory/`
beside it, so the transcript cannot be wrong about either, whereas the
environment variable can — and a wrong one would file a work session's notes
into the personal store. The variable is cross-checked only: a disagreement is
logged as a `warn` line and the transcript wins, and an unrecognised layout makes
the hook refuse rather than guess.
