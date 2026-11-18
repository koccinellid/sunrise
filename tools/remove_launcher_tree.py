#!/usr/bin/env python3
"""Remove `launcher/` (it lives in sunrise-org/sunrise-launcher now) and repoint prose references.

Steps:
1. `git rm -r launcher/`.
2. In Markdown files and in `//`, `///` and `//!` comment lines of Rust files, rewrite each
   `launcher/<path>` (also `../launcher/<path>`) into a link to the same path in
   https://github.com/sunrise-org/sunrise-launcher (the old `launcher/` folder is that repository's root).
3. Print every `launcher/` reference still left, for hand fixes.

Files that carry rules, history or build logic (AGENTS.md, CONTRIBUTING.md, GOVERNANCE.md, the sync
decision notes, CI, tools, tests) are not rewritten here; they are fixed by hand and listed in step 3.

Usage: python3 tools/remove_launcher_tree.py [--dry-run]
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/sunrise-org/sunrise-launcher"
ROOT = Path(__file__).resolve().parent.parent
SKIP = {"AGENTS.md", "CONTRIBUTING.md", "GOVERNANCE.md"}
SKIP_PREFIXES = ("docs/sync-", "launcher/", "tests/fixtures/")

# `launcher/` not preceded by a path character (so `tools/lang_review/launcher/` and
# `public/media/launcher/` stay), optional `../`, then a path that ends in a word character or `/`
# and is not a glob or placeholder (`{`, `<`, `*` right after it).
REF = re.compile(r"(?<![\w/.\-])(?:\.\./)*launcher/((?:[\w.\-]+/)*[\w.\-]*\w|(?:[\w.\-]+/)+)?(?![\w{<*/])")


def link(match: re.Match) -> str:
    path = match.group(1) or ""
    if not path:
        return REPO
    kind = "tree" if path.endswith("/") or "." not in path.rsplit("/", 1)[-1] else "blob"
    return f"{REPO}/{kind}/main/{path}"


def rewrite(path: str, text: str) -> str:
    if path.endswith(".md"):
        return REF.sub(link, text)
    out = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("//"):
            line = REF.sub(link, line)
        out.append(line)
    return "\n".join(out)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def main() -> None:
    dry = "--dry-run" in sys.argv
    tracked = git("ls-files").splitlines()
    changed = []
    for path in tracked:
        if path in SKIP or path.startswith(SKIP_PREFIXES) or not path.endswith((".md", ".rs")):
            continue
        file = ROOT / path
        text = file.read_text(encoding="utf-8")
        new = rewrite(path, text)
        if new != text:
            changed.append(path)
            if not dry:
                file.write_text(new, encoding="utf-8")
    if not dry:
        git("rm", "-r", "-q", "launcher")
    print(f"rewrote {len(changed)} files; {'would remove' if dry else 'removed'} launcher/")
    left = subprocess.run(
        ["git", "grep", "-n", "launcher/", "--", ".", ":!*.lock"] + ([] if dry else [":!launcher/"]),
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    print("references left (not handled here):")
    print(left, end="")


if __name__ == "__main__":
    main()
