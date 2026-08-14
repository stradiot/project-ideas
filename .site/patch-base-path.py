#!/usr/bin/env python3
"""Teach the client-side plugins that the site is served under a path.

Quartz core is subpath-clean: it emits every server-rendered link relative to
the page's own depth, and inlines a `fetchData` promise with a path worked out
the same way. The explorer, search and graph plugins do not use any of that.
They build URLs in the browser by sticking "/" on the front of a slug, which is
only correct when the site sits at a domain root. Served at
stradiot.github.io/project-ideas, every one of them points a segment too high:
the content index 404s, so the sidebar, graph and search come up empty, and the
links they do build land on stradiot.github.io/projects/... — a GitHub 404 page.

`quartz build --baseDir` does not reach any of this.

Patching each plugin's readable src/ and rebuilding it is what this does, in
preference to rewriting the minified dist/ that plugin install produced. The
strings below are stable because QUARTZ_TAG pins the plugin commits, and every
one is asserted: if a substitution stops matching, the build fails rather than
silently publishing a site whose navigation is broken again.

Usage: patch-base-path.py <plugins dir> <base>     e.g. ... .quartz/plugins /project-ideas

Prints the name of each plugin it changed, one per line, so the caller knows
which ones to rebuild.
"""

import sys
from pathlib import Path

# (plugin, path within the plugin, original, replacement-with-{base})
# Every entry must match at least once, or the build stops.
EDITS = [
    # --- the content index fetch: empties explorer, graph and search ---
    (
        "explorer",
        "src/components/scripts/explorer.inline.ts",
        'fetch("/static/contentIndex.json")',
        'fetch("{base}/static/contentIndex.json")',
    ),
    (
        "search",
        "src/components/scripts/search.inline.ts",
        'fetch("/static/contentIndex.json")',
        'fetch("{base}/static/contentIndex.json")',
    ),
    (
        "graph",
        "src/components/scripts/graph.inline.ts",
        'fetch("/static/contentIndex.json")',
        'fetch("{base}/static/contentIndex.json")',
    ),
    # --- the links themselves ---
    (
        "explorer",
        "src/components/scripts/explorer.inline.ts",
        'folderLink.href = "/" + (folderHref || "");',
        'folderLink.href = "{base}/" + (folderHref || "");',
    ),
    (
        "explorer",
        "src/components/scripts/explorer.inline.ts",
        'link.href = "/" + node.data.slug;',
        'link.href = "{base}/" + node.data.slug;',
    ),
    (
        "search",
        "src/components/scripts/search.inline.ts",
        'const targetUrl = new URL("/" + slug, window.location.origin).toString();',
        'const targetUrl = new URL("{base}/" + slug, window.location.origin).toString();',
    ),
    (
        "search",
        "src/components/scripts/search.inline.ts",
        'itemTile.href = "/" + item.slug;',
        'itemTile.href = "{base}/" + item.slug;',
    ),
]

# resolvePath() is what the graph navigates with on a node click. It lives in
# the shared utils package rather than in any plugin's own source, already
# compiled, and is bundled into the plugin at build time — so it is patched in
# place in whichever plugin's node_modules carries it.
RESOLVE_PATH_ORIG = """function resolvePath(to) {
  if (to.startsWith("/")) return to;
  return "/" + to;
}"""
RESOLVE_PATH_NEW = """function resolvePath(to) {
  if (to.startsWith("/")) return "{base}" + to;
  return "{base}/" + to;
}"""


def main() -> int:
    plugins = Path(sys.argv[1])
    base = sys.argv[2].rstrip("/")
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
        path.write_text(text.replace(old, new.replace("{base}", base)), encoding="utf-8")
        touched.add(plugin)

    # The shared helper, in every plugin that bundles a copy of it.
    resolve_hits = 0
    for path in plugins.glob("*/node_modules/@quartz-community/utils/dist/*.js"):
        text = path.read_text(encoding="utf-8")
        if RESOLVE_PATH_ORIG not in text:
            continue
        path.write_text(
            text.replace(RESOLVE_PATH_ORIG, RESOLVE_PATH_NEW.replace("{base}", base)),
            encoding="utf-8",
        )
        resolve_hits += 1
        touched.add(path.relative_to(plugins).parts[0])

    if resolve_hits == 0:
        raise SystemExit("resolvePath() was not found in any utils package — upstream changed")

    print(f"base-path patch: {len(EDITS)} source edit(s), {resolve_hits} resolvePath copy(ies)", file=sys.stderr)
    for name in sorted(touched):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
