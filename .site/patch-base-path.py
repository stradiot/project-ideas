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

# getFullSlugFromUrl() reads the slug back off the address bar, stripping only
# the leading "/". Under /project-ideas it therefore returns
# "project-ideas/projects/logs/foo" while the content index is keyed
# "projects/logs/foo", so the lookup misses. The graph is the only consumer,
# and a missed lookup is why it drew a single stray node instead of a
# neighbourhood.
#
# The fix does not need to know the base at all: Quartz core already stamps the
# correct slug on the body as data-slug, and the sibling helper getFullSlug()
# reads exactly that. Preferring it is right at a domain root and under any
# path, so this substitution stays correct if the site ever moves.
FULL_SLUG_ORIG = """function getFullSlugFromUrl() {
  let rawSlug = window.location.pathname;"""
FULL_SLUG_NEW = """function getFullSlugFromUrl() {
  const fromBody = window.document.body.dataset.slug;
  if (fromBody) return fromBody;
  let rawSlug = window.location.pathname;"""


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

    # The shared helpers, in every plugin that bundles a copy of them.
    resolve_hits = 0
    slug_hits = 0
    for path in plugins.glob("*/node_modules/@quartz-community/utils/dist/*.js"):
        text = path.read_text(encoding="utf-8")
        original = text
        if RESOLVE_PATH_ORIG in text:
            text = text.replace(
                RESOLVE_PATH_ORIG, RESOLVE_PATH_NEW.replace("{base}", base)
            )
            resolve_hits += 1
        if FULL_SLUG_ORIG in text:
            text = text.replace(FULL_SLUG_ORIG, FULL_SLUG_NEW)
            slug_hits += 1
        if text != original:
            path.write_text(text, encoding="utf-8")
            touched.add(path.relative_to(plugins).parts[0])

    if resolve_hits == 0:
        raise SystemExit("resolvePath() was not found in any utils package — upstream changed")
    if slug_hits == 0:
        raise SystemExit("getFullSlugFromUrl() was not found in any utils package — upstream changed")

    print(
        f"base-path patch: {len(EDITS)} source edit(s), "
        f"{resolve_hits} resolvePath, {slug_hits} getFullSlugFromUrl",
        file=sys.stderr,
    )
    for name in sorted(touched):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
