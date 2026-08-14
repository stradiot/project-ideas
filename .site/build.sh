#!/usr/bin/env bash
#
# Build the vault as a static site with Quartz.
#
# Quartz is not vendored into this repo: it is cloned into .site/.work at a
# pinned tag, handed a content/ directory copied out of the vault, and built
# there. Nothing Quartz-shaped ends up in the vault itself, so Obsidian's file
# explorer, search and graph stay clean.
#
# The published surface is defined here, by what gets copied — projects/,
# notes/, journal/ and README.md. Everything else (CLAUDE.md, templates/,
# .obsidian/, anything loose at the root) is excluded by never being copied,
# which means no ignore rule has to be maintained as files come and go.
#
#   .site/build.sh            build once into .site/.work/public
#   .site/build.sh --serve    build and serve on http://localhost:8080
#
# Any arguments are passed through to `quartz build`.

set -euo pipefail

# Bumping this means re-deriving .site/quartz.config.yaml from that tag's
# quartz.config.default.yaml — the plugin source syntax and the plugin set both
# changed between v5.0.0 and the v5 branch head.
QUARTZ_TAG=v5.0.0

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$VAULT/.site/.work"

rm -rf "$WORK"
git clone --quiet --depth 1 --branch "$QUARTZ_TAG" \
  https://github.com/jackyzha0/quartz.git "$WORK"

cp "$VAULT/.site/quartz.config.yaml" "$WORK/quartz.config.yaml"

rm -rf "$WORK/content"
mkdir -p "$WORK/content"
cp -R "$VAULT/projects" "$VAULT/notes" "$VAULT/journal" "$WORK/content/"
# Quartz serves content/index.md at the root URL, and the README already holds
# the track-grouped project list. Copying it here avoids adding an index.md to
# the vault that would then need maintaining alongside the README.
cp "$VAULT/README.md" "$WORK/content/index.md"

# Operates on the copy, never on the vault. See the script for why.
python3 "$VAULT/.site/lift-titles.py" "$WORK/content"

cd "$WORK"
npm ci
# At v5.0.0 this installs strictly from quartz.lock.json, which is why
# quartz.config.yaml must not name a plugin the tag's default config lacks.
npx quartz plugin install
npx quartz build "$@"
