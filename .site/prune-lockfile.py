#!/usr/bin/env python3
"""Drop plugins from quartz.lock.json that quartz.config.yaml has disabled.

`quartz plugin install` at v5.0.0 installs whatever the lockfile lists and pays
no attention to `enabled:`. Each plugin is cloned, npm-installed and compiled,
so the disabled ones cost the same as the used ones — the LaTeX plugin alone
pulls 153 MB for a vault with no math in it. Pruning first is what keeps the
deploy from spending most of its time building things this site never loads.

Usage: prune-lockfile.py <quartz.config.yaml> <quartz.lock.json>

The config is parsed by regex rather than with PyYAML, to avoid depending on a
module that may not be on a CI runner. That is only safe because the file being
read is ours and has a fixed shape; the assertions below fail the build rather
than let a mis-parse silently prune everything.
"""

import json
import re
import sys
from pathlib import Path

ENTRY = re.compile(
    r"-\s+source:\s*github:quartz-community/([\w-]+)(.*?)(?=\n  - source:|\Z)",
    re.S,
)
DISABLED = re.compile(r"^\s+enabled:\s*false", re.M)


def enabled_plugins(config: str) -> set[str]:
    body = config.split("\nplugins:", 1)[1].split("\nlayout:", 1)[0]
    entries = ENTRY.findall(body)
    if len(entries) < 20:
        raise SystemExit(
            f"parsed only {len(entries)} plugin entries from the config — "
            "the file's shape changed, refusing to prune on a bad parse"
        )
    return {name for name, block in entries if not DISABLED.search(block)}


def main() -> int:
    config_path, lock_path = Path(sys.argv[1]), Path(sys.argv[2])
    keep = enabled_plugins(config_path.read_text(encoding="utf-8"))

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    plugins = lock["plugins"]

    missing = keep - plugins.keys()
    if missing:
        raise SystemExit(
            "config enables plugins the lockfile does not pin: "
            + ", ".join(sorted(missing))
        )

    dropped = sorted(plugins.keys() - keep)
    lock["plugins"] = {name: plugins[name] for name in sorted(keep)}
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    print(f"lockfile pruned to {len(keep)} plugin(s), dropped {len(dropped)}: {', '.join(dropped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
