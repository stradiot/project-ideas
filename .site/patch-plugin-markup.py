#!/usr/bin/env python3
"""Markup and default-state edits the stylesheet cannot make for itself.

.site/custom.scss carries the whole visual layer, and CSS reaches everything
except two things — what a value *says*, and what the page decides before any
stylesheet runs. One patch each, both in community plugins.

Like patch-base-path.py this edits each plugin's readable src/ and leaves the
caller to rebuild it with tsup, and every substitution is asserted: if one stops
matching, the build fails rather than publishing a page that quietly lost a
feature. It prints the name of each plugin it changed, one per line.

Usage: patch-plugin-markup.py <plugins dir>     e.g. ... .quartz/plugins

--- note-properties: the value has to reach the selector ---

`status:` is the field this vault actually tracks — idea, planning, active,
built, deferred — and it renders as a bare <span> holding the word. CSS cannot
select on text content, so a badge coloured by state is impossible from the
stylesheet alone no matter how it is written. Stamping the key and the value
onto the row as data attributes is the smallest thing that fixes that, and it
adds nothing to a page that does not use it.

--- darkmode: dark has to be the default, not the fallback ---

The theme resolves to localStorage first and prefers-color-scheme second, so a
visitor whose system is set to light gets the light palette even though this
site is designed dark-first. Only the second half is changed: an explicit
choice already made with the toggle still wins, and still persists.
"""

import sys
from pathlib import Path

# (plugin, path within the plugin, original, replacement)
EDITS = [
    (
        "note-properties",
        "src/components/NoteProperties.tsx",
        """              <tr key={key} class="note-properties-row">""",
        """              <tr
                key={key}
                class="note-properties-row"
                data-key={key}
                data-value={typeof value === "string" ? value : undefined}
              >""",
    ),
    (
        "darkmode",
        "src/components/scripts/darkmode.inline.ts",
        """const userPref = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
const currentTheme = localStorage.getItem("theme") ?? userPref;""",
        """const currentTheme = localStorage.getItem("theme") ?? "dark";""",
    ),
]


def main() -> int:
    plugins = Path(sys.argv[1])
    touched: set[str] = set()

    for plugin, rel, old, new in EDITS:
        path = plugins / plugin / rel
        if not path.exists():
            raise SystemExit(f"expected file is missing: {path}")
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(
                f"{plugin}/{rel}: expected source not found, upstream changed:\n  {old}"
            )
        path.write_text(text.replace(old, new), encoding="utf-8")
        touched.add(plugin)

    print(f"markup patch: {len(EDITS)} edit(s)", file=sys.stderr)
    for name in sorted(touched):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
