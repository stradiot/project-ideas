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

## Layout and note conventions

- `projects/` — one note per project, from `templates/project.md`. Frontmatter is
  `tags: [project, …]`, `status:`, `depends:`, `created:` (ISO date), and
  optionally `repo:` / `github:` (see below). Body sections in order: Now, Goal,
  Architecture, Tools, Budget, Software / firmware, Plan, Build log.
- `projects/logs/` — one `<slug>-log.md` per project, holding the dated session
  entries. Frontmatter is `tags: [log, <slug>]` and `project: <slug>`. Every
  project has one, created empty, so the pointer in the note never dangles and
  the SessionEnd hook always has an existing file to append to.
- `notes/` — reference notes and deep dives, linked from projects, from
  `templates/note.md`. Frontmatter is `tags: [note, …]` and `created:`; no
  `status:`, no plan, no build log — these are subject notes, not work.
- `journal/` — daily notes, `journal/YYYY-MM-DD.md`. Written by automation (below).
- `templates/` — note templates.

Cross-references are wikilinks: `[[subghz-fixed-code-repeater]]` resolves to
`projects/subghz-fixed-code-repeater.md`, or to `notes/<name>.md` for reference
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

The machinery lives **outside this repo**, in three scripts under
`~/.local/bin`, which is its own git repo — <https://github.com/stradiot/claude-hooks>,
private — so they have a history. Read it there when the behaviour described
below and the behaviour you observe disagree; the scripts are the authority and
this section is a description of them. They are wired
by absolute path into `~/.claude-personal/settings.json` — the config dir the
`claude-personal` alias selects. There is no default `~/.claude` dir and there
should never be one; `~/.zshrc` aliases bare `claude` to a warning precisely so
nothing lands there. (`~/.claude-work` also calls `claude-session-notes.sh` on
SessionEnd, but a work cwd is outside `~/Documents/personal`, so
`personal_repo_from_cwd` rejects it and no vault write happens.)

- `~/.local/bin/claude-personal-project-lib.sh` — `personal_repo_from_cwd` (maps a
  cwd under `~/Documents/personal` to a repo name, excluding the vault itself) and
  `note_for_repo` (frontmatter `repo:` lookup).
- `~/.local/bin/claude-personal-project-start.sh` — SessionStart: pulls the vault
  and injects the linked project note into that session's context.
- `~/.local/bin/claude-session-notes.sh` — SessionEnd: a detached headless Claude
  writes the journal, then the shell commits and pushes (`journal: <repo> <date>`).

What it writes, per session in a linked repo:

- a `### YYYY-MM-DD` entry appended to `projects/logs/<slug>-log.md`, newest last;
- the note's `## Now` paragraph, replaced with where the project stands;
- a tick on any `## Plan` item the session actually finished — wording untouched;
- one line in `journal/<date>.md`: `- [[note-slug]] — one-line summary`.

Everything else in the note is off limits: frontmatter, Goal, Architecture,
Tools, Budget, and the text of plan items. `status:` in particular is a
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
log file, `## Now`, plan ticks and the daily note. Frontmatter, Goal,
Architecture and the *wording* of plan items are never rewritten by automation —
a change to those is a deliberate human (or explicitly requested) edit.

Automation activity is logged to `$CLAUDE_CONFIG_DIR/.session-notes-state/log.txt`.
Everything here is a personal project, so in practice that is
**`~/.claude-personal/.session-notes-state/log.txt`** — not `~/.claude/`, which is
the wrong place to look and is empty. Check it when a journal entry or a push
seems to have gone missing; the failure is silent from the phone's side, since a
stranded commit looks exactly like a session that wrote nothing.
