#!/usr/bin/env python3
"""
molt-chain-append -- adopt or extend hash-chained tamper-evidence for
memory/decisions.md, without deciding, summarizing, or judging anything.

A human still writes every decision entry, in full, in the same
Decision/Reasoning/Reversible/Review shape Molt has always used. This script's
only job is to append a deterministic **Hash:** field to any entry that's
missing one, sha256(that entry's own content + the previous entry's hash),
oldest to newest. That's the whole mechanism: altering any historical entry
after it's been hashed changes its hash, which changes every hash after it,
so tampering is detectable even with no mirror kept. Same principle as the
IETF's 2026 "Agent Audit Trail" draft, applied with stdlib hashlib only.

Run this:
  - Once, to adopt hash-chaining on an existing log (backfills every entry).
  - After writing a new entry, before running molt-verify.py, to extend the
    chain to cover it.

It refuses to touch any entry that already has a Hash field; those are
left byte-for-byte untouched. If it can't safely locate an entry's exact
text in the file, it aborts with no changes rather than guessing.

TRUST BOUNDARY: this script loads and executes molt-verify.py from ROOT via
importlib (see load_verify_module below). Only run it against a Molt root
you trust; it is not safe to point at an untrusted directory.

LIMITATION, stated plainly: this script fills in MISSING hashes. If someone
tampers with an old entry and strips its Hash field and every one after it,
re-running this script produces a fresh, internally-consistent chain with no
failures -- the tampering is laundered, not caught. This is a real limitation
of a self-contained local hash chain with no external anchor, documented in
ARCHITECTURE.md's "What the hash chain does and doesn't prove". Two local,
dependency-free mitigations exist: molt-verify.py's check_git_anchor compares
the working copy against the last git commit (catches this attack as long as
it hasn't been committed yet), and committing/pushing often narrows the
window an uncommitted rewrite can hide in. If content genuinely needs to be
removed (PII, a leaked secret), use molt-redact.py instead of hand-editing;
it documents the change instead of hiding it.

Usage:
    python3 molt-chain-append.py [ROOT]   # ROOT defaults to the current dir
"""

import importlib.util
import os
import re
import sys


def load_verify_module(root):
    path = os.path.join(root, "molt-verify.py")
    if not os.path.isfile(path):
        raise FileNotFoundError("molt-verify.py not found at %s -- is this a Molt root?" % root)
    spec = importlib.util.spec_from_file_location("molt_verify_for_chain", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: __name__ != "__main__" here, main() does not run
    return mod


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    mv = load_verify_module(root)

    dpath = os.path.join(root, "memory", "decisions.md")
    if not os.path.isfile(dpath):
        print("no memory/decisions.md found at %s" % root)
        return 1

    dtext = mv.read(dpath)
    entries = mv.parse_decisions(dtext)  # newest-first, matches file order
    if not entries:
        print("no entries found in memory/decisions.md, nothing to hash")
        return 0

    oldest_first = list(reversed(entries))
    prev = mv.CHAIN_GENESIS
    new_dtext = dtext
    appended = []

    for e in oldest_first:
        stored = mv.parse_stored_hash(e)
        if stored is not None:
            prev = stored
            continue

        h = mv.entry_hash(e, prev)
        old_body = e["body"]

        m = re.search(r"(\*\*Review:\*\*[^\n]*\n)", old_body)
        if not m:
            print("entry '%s' has no **Review:** line to anchor the hash after -- "
                  "aborting, no changes made" % e["title"][:60])
            return 1

        insert_at = m.end()
        new_body = old_body[:insert_at] + ("**Hash:** %s\n" % h) + old_body[insert_at:]

        if old_body not in new_dtext:
            print("could not locate entry '%s' verbatim in the file -- "
                  "aborting, no changes made" % e["title"][:60])
            return 1

        new_dtext = new_dtext.replace(old_body, new_body, 1)
        appended.append(e["title"][:60])
        prev = h

    if not appended:
        print("every entry already has a Hash field, chain already complete "
              "(%d entries)" % len(entries))
        return 0

    with open(dpath, "w", encoding="utf-8") as f:
        f.write(new_dtext)

    print("appended %d hash(es), chain now covers all %d entries:" % (len(appended), len(entries)))
    for title in appended:
        print("  + %s" % title)
    print("\nRun molt-verify.py to confirm the chain verifies end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
