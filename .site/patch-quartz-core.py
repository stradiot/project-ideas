#!/usr/bin/env python3
"""Backport fixes from the v5 branch head onto the pinned Quartz tag.

QUARTZ_TAG is held at v5.0.0 deliberately: the tag and the branch head disagree
on plugin source syntax and on which plugins exist, so bumping it means
re-deriving .site/quartz.config.yaml from scratch. That is the right trade for a
release, and the wrong one for a single upstream one-liner — hence this file.

Unlike patch-base-path.py, which edits the community plugins' src/ and has to
rebuild each one with tsup, everything here is Quartz core. `quartz build`
compiles core from source on every run, so an edit is enough.

Every entry is asserted: if a substitution stops matching, the build fails
rather than quietly publishing the bug again. Drop an entry when QUARTZ_TAG
moves past the commit that fixed it upstream.

Usage: patch-quartz-core.py <work dir>     e.g. ... .site/.work

--- the folder-page listing, rendered twice ---

PageTypeDispatcher renders each virtual page's body once up front, so that a
![[...]] transclusion of a folder or tag page has HTML to inline. At v5.0.0 that
pre-render is written back to two places: vfile.data.htmlAst, which is what
transclusion reads, and the page's own hast tree, which nothing wanted. The real
render then runs the same component again and hands it that polluted tree, and
FolderContent renders `tree` as the folder's own prose whenever it is non-empty
-- so the page came out as its previous self wrapped in an <article>, with a
second copy of the listing appended after it. /journal/ showed all nine notes
twice.

The v5 branch head drops the tree assignment and keeps the htmlAst one, which is
the fix taken here. Transclusion is unaffected; the virtual page's tree goes
back to being empty, so FolderContent falls through to its description branch.
"""

import sys
from pathlib import Path

# (path within the work dir, original, replacement)
EDITS = [
    (
        "quartz/plugins/pageTypes/dispatcher.ts",
        """      const htmlAst = fromHtml(htmlString, { fragment: true }) as HtmlRoot
      ve.tree.children = htmlAst.children
      ve.vfile.data.htmlAst = htmlAst""",
        """      const htmlAst = fromHtml(htmlString, { fragment: true }) as HtmlRoot
      ve.vfile.data.htmlAst = htmlAst""",
    ),
]


def main() -> int:
    work = Path(sys.argv[1])

    for rel, old, new in EDITS:
        path = work / rel
        if not path.exists():
            raise SystemExit(f"expected file is missing: {path}")
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(
                f"{rel}: expected source not found, upstream changed:\n  {old}"
            )
        path.write_text(text.replace(old, new), encoding="utf-8")

    print(f"core patch: {len(EDITS)} edit(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
