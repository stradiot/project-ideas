#!/usr/bin/env python3
"""Lift each note's leading H1 into frontmatter `title:` and drop the heading.

Every note in this vault opens with an H1 ("# BeagleBone Green Case"), because
that is how the notes read in Obsidian. Quartz instead renders a title of its
own above the body, derived from frontmatter `title:` or, failing that, from the
filename. With no `title:` anywhere in the vault, every page came out with two
headings: the slug, then the note's real H1.

Adding `title:` to 59 files would be a field a human has to keep in step with
the H1, which this vault refuses to have. So the lift happens here, on the copy
under .site/.work/content — the vault files are never touched.

Files with no H1 are left alone: the journal notes have none, and their filename
is already the date that belongs in the title.
"""

import re
import sys
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
H1 = re.compile(r"^# (.+?)[ \t]*$", re.MULTILINE)


def yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lift(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")

    fm = FRONTMATTER.match(text)
    body_start = fm.end() if fm else 0
    body = text[body_start:]

    h1 = H1.search(body)
    if not h1:
        return False

    # Only lift a heading that opens the note. Anything after the first `##`
    # is a section heading that happens to use one hash, and belongs in place.
    first_h2 = body.find("\n## ")
    if first_h2 != -1 and h1.start() > first_h2:
        return False

    title = h1.group(1).strip()
    if "title:" in (fm.group(1) if fm else ""):
        return False

    # Drop the heading line and the blank line that follows it.
    body = body[: h1.start()] + re.sub(r"\A\n+", "", body[h1.end():])

    if fm:
        head = f"---\n{fm.group(1)}\ntitle: {yaml_quote(title)}\n---\n"
    else:
        head = f"---\ntitle: {yaml_quote(title)}\n---\n"

    path.write_text(head + body, encoding="utf-8")
    return True


def main() -> int:
    root = Path(sys.argv[1])
    lifted = sum(lift(p) for p in sorted(root.rglob("*.md")))
    print(f"lifted {lifted} title(s) into frontmatter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
