"""Fail if any forbidden term appears in the files about to be published.

The list is never committed: it comes from the FORBIDDEN_TERMS environment variable (a CI
secret, one term per line or comma separated) or from a local, git-ignored `.forbidden-terms`
file (one term per line, `#` for comments). Matching is case-insensitive and on whole words
(a term never matches inside a longer word).

Usage:
    python tools/check_terms.py                   all tracked files
    python tools/check_terms.py --staged          files staged for commit (pre-commit hook)
    python tools/check_terms.py --message FILE    a commit message (commit-msg hook)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_terms() -> list[str]:
    raw = os.environ.get("FORBIDDEN_TERMS", "")
    local = ROOT / ".forbidden-terms"
    if local.exists():
        raw += "\n" + local.read_text(encoding="utf-8")
    terms = []
    for line in re.split(r"[\n,]", raw):
        term = line.split("#", 1)[0].strip()
        if term:
            terms.append(term)
    return terms


def files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def content(path: str, staged: bool) -> str:
    if staged:
        res = subprocess.run(["git", "show", f":{path}"], cwd=ROOT, capture_output=True, check=True)
        data = res.stdout
    else:
        data = (ROOT / path).read_bytes()
    return data.decode("utf-8", errors="ignore")


def main() -> int:
    staged = "--staged" in sys.argv
    message = sys.argv[sys.argv.index("--message") + 1] if "--message" in sys.argv else None
    terms = load_terms()
    if not terms:
        print("check_terms: no forbidden terms configured (FORBIDDEN_TERMS or .forbidden-terms)", file=sys.stderr)
        return 1 if os.environ.get("CI") else 0
    pattern = re.compile("|".join(rf"(?<!\w){re.escape(t)}(?!\w)" for t in terms), re.IGNORECASE)
    hits = []
    if message:
        text = Path(message).read_text(encoding="utf-8", errors="ignore")
        hits = [f"commit message:{n}" for n, line in enumerate(text.splitlines(), 1)
                if not line.startswith("#") and pattern.search(line)]
        if hits:
            print(f"check_terms: forbidden terms in the commit message: {', '.join(hits)}", file=sys.stderr)
            return 1
        return 0
    for path in files(staged):
        for target in (path, content(path, staged)):
            for n, line in enumerate(target.splitlines(), 1):
                if pattern.search(line):
                    where = f"{path}:{n}" if target is not path else f"{path} (file name)"
                    hits.append(where)
    if hits:
        # Never print the matched term: CI logs of a public repo are public too.
        print(f"check_terms: forbidden terms found in {len(hits)} place(s):", file=sys.stderr)
        for where in sorted(set(hits)):
            print(f"  {where}", file=sys.stderr)
        return 1
    print(f"check_terms: ok ({len(terms)} terms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
