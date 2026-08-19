#!/usr/bin/env python3
"""Give the log and journal notes a `created:` date, on the copy.

Quartz sorts a folder listing by `dates.created`, which CreatedModifiedDate
fills from frontmatter first and the filesystem second. Every note under
projects/ and notes/ carries `created:`, so those pages sort correctly. The
journal notes and the build logs carry none, and the filesystem fallback is
worthless here for two separate reasons:

  - `created` comes from birthtimeMs, and build.sh copies the vault into a
    scratch clone, so every file's birthtime is the instant of the copy. The
    nine journal notes came out spread across a single millisecond, and sorted
    in whatever order that landed in -- 16, 17, 18, then 09 through 15.
  - `cp -p` would not rescue it. It preserves mtime, not birthtime. And on CI
    it would not help even then: git stores no timestamps, so actions/checkout
    stamps every file with the checkout time.

Nor can the plugin's `git` priority stand in, whatever the copy is arranged to
look like: that source only ever sets `modified`, never `created`.

So the date is synthesised here, from what the file itself already states.
Adding it to the vault instead would mean a `created:` field on every daily
note, kept in step by hand -- the same field this vault refuses to have, and
the same reason lift-titles.py runs beside this one. The vault is not touched.

  journal/YYYY-MM-DD.md   the date in the filename.
  <slug>-log.md           its newest `### YYYY-MM-DD` entry, so projects/logs/
                          reads most-recently-worked first. A log with no
                          entries yet takes its project note's `created:`,
                          which sorts the empty ones by project age rather
                          than bunching them at today.

Anything that already has `created:` is left alone. Run after lift-titles.py,
which is what puts a frontmatter block on the files that lacked one.

Usage: stamp-dates.py <content dir>     e.g. ... .site/.work/content
"""

import re
import sys
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
CREATED = re.compile(r"^created:", re.MULTILINE)
ENTRY = re.compile(r"^### (\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE)
PROJECT = re.compile(r"^project: *(\S+)", re.MULTILINE)
JOURNAL_NAME = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


def split(text: str) -> tuple[str, str]:
    """(frontmatter body without the --- fences, note body)."""
    fm = FRONTMATTER.match(text)
    return (fm.group(1), text[fm.end():]) if fm else ("", text)


def created_of(path: Path) -> str | None:
    if not path.exists():
        return None
    head, _ = split(path.read_text(encoding="utf-8"))
    m = re.search(r"^created: *(\d{4}-\d{2}-\d{2})", head, re.MULTILINE)
    return m.group(1) if m else None


def date_for(path: Path, root: Path, head: str, body: str) -> str | None:
    if path.parent.name == "journal" and JOURNAL_NAME.match(path.stem):
        return path.stem

    if path.stem.endswith("-log"):
        entries = ENTRY.findall(body)
        if entries:
            return max(entries)
        slug = PROJECT.search(head)
        if slug:
            return created_of(root / "projects" / f"{slug.group(1)}.md")

    return None


def stamp(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    head, body = split(text)

    if CREATED.search(head):
        return False

    date = date_for(path, root, head, body)
    if not date:
        return False

    head = f"{head}\ncreated: {date}" if head else f"created: {date}"
    path.write_text(f"---\n{head}\n---\n{body}", encoding="utf-8")
    return True


def main() -> int:
    root = Path(sys.argv[1])
    stamped = sum(stamp(p, root) for p in sorted(root.rglob("*.md")))
    print(f"stamped created: on {stamped} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
