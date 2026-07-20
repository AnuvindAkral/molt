#!/usr/bin/env python3
"""
build-molt-init -- regenerates molt-init.py from the real framework files.

molt-init.py must work as a single, self-contained file: someone with a
clean setup and nothing else should be able to copy just that one file
anywhere and run it. That means it can't rely on copying sibling files from
a checked-out repo; it has to carry its own copies of molt-verify.py,
molt-chain-append.py, molt-redact.py, the pre-commit hook, and the CI
workflow, embedded as base64 (avoids every quoting/escaping problem those
files' own docstrings, regexes, and backslashes would otherwise cause).

The real risk this creates: two copies of the same file (the real one, and
the embedded one) that can silently drift apart the moment someone edits
molt-verify.py and forgets to run this script, the exact shape of bug this
project has already found and fixed for AGENTS.md/CLAUDE.md and for
mirrors. molt-verify.py's check_init_embed_consistency checks for this
drift; run this script whenever any embedded file changes, then re-run
molt-verify.py to confirm the embed matches again.

Usage:
    python3 scripts/build-molt-init.py
"""

import base64
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # molt/

EMBED_FILES = {
    "MOLT_VERIFY_PY": "molt-verify.py",
    "MOLT_CHAIN_APPEND_PY": "molt-chain-append.py",
    "MOLT_REDACT_PY": "molt-redact.py",
    "PRE_COMMIT_HOOK": os.path.join(".githooks", "pre-commit"),
    "CI_WORKFLOW_YML": os.path.join(".github", "workflows", "molt-verify.yml"),
}

MOLT_INIT_PATH = os.path.join(ROOT, "molt-init.py")


def b64(path):
    with open(path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode("ascii")
    # wrap at 76 chars so the generated file stays readable, not one giant line
    lines = [encoded[i:i + 76] for i in range(0, len(encoded), 76)]
    return "\n".join(lines)


def main(argv):
    dest_path = os.path.join(HERE, "_molt_init_output.py")

    blobs = {}
    for const_name, rel_path in EMBED_FILES.items():
        src = os.path.join(ROOT, rel_path)
        if not os.path.isfile(src):
            print("missing source file, aborting: %s" % src)
            return 1
        blobs[const_name] = b64(src)

    if not os.path.isfile(MOLT_INIT_PATH):
        print("molt-init.py not found at %s -- nothing to update" % MOLT_INIT_PATH)
        return 1

    text = open(MOLT_INIT_PATH, encoding="utf-8").read()
    for const_name in EMBED_FILES:
        pattern = re.compile(
            r"(%s_B64 = \"\"\"\n).*?(\n\"\"\")" % re.escape(const_name),
            re.S,
        )
        replacement = r"\g<1>" + blobs[const_name].replace("\\", "\\\\") + r"\g<2>"
        new_text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            print("could not find embed block for %s in molt-init.py -- aborting, "
                  "no changes made" % const_name)
            return 1
        text = new_text

    with open(MOLT_INIT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print("regenerated embedded blobs in molt-init.py for: %s" % ", ".join(EMBED_FILES))
    print("run molt-verify.py's check_init_embed_consistency to confirm they now match.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
