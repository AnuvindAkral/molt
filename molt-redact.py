#!/usr/bin/env python3
"""
molt-redact -- the sanctioned way to remove sensitive content (PII, a leaked
secret, anything that should never have been logged) from a hash-chained
memory/decisions.md, without pretending nothing happened.

Molt's append-only rule forbids silently rewriting history (see CLAUDE.md's
<never>). This script doesn't violate that: it replaces one entry's
Decision/Reasoning/Reversible/Review text with a fixed, visible placeholder,
keeps that entry's heading (date + title) exactly as it was, appends a NEW
top entry that documents the redaction itself in plain text (what entry, when,
why, by whom if given), and regenerates the hash chain from the redacted
entry forward, since that content genuinely, legitimately changed. Anyone
reading the log, or running molt-verify.py, can see a redaction happened,
even if not what was removed.

This exists because of a real gap: an append-only, hash-chained log has no
sanctioned way to get PII or a leaked secret back out once it's in, short of
either leaving it there forever or hand-editing history (which molt-verify.py
would then correctly flag as tampering). This is the third option.

TRUST BOUNDARY: like molt-chain-append.py, this script loads and executes
molt-verify.py from ROOT via importlib. Only run it against a Molt root you
trust.

Usage:
    python3 molt-redact.py [ROOT] --match "text uniquely identifying the entry's title" --reason "why"
    python3 molt-redact.py [ROOT] --match "..." --reason "..." --by "who requested this"
"""

import argparse
import datetime
import importlib.util
import os
import re
import subprocess
import sys

PLACEHOLDER = "[REDACTED -- see the redaction entry above for reason and date]"


def load_verify_module(root):
    path = os.path.join(root, "molt-verify.py")
    if not os.path.isfile(path):
        raise FileNotFoundError("molt-verify.py not found at %s -- is this a Molt root?" % root)
    spec = importlib.util.spec_from_file_location("molt_verify_for_redact", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: __name__ != "__main__" here, main() does not run
    return mod


def main(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--match", required=True, help="substring uniquely identifying one entry's title")
    ap.add_argument("--reason", required=True, help="plain-text reason for the redaction, logged")
    ap.add_argument("--by", default=None, help="who requested/performed the redaction (optional, logged)")
    args = ap.parse_args(argv[1:])
    root = args.root

    mv = load_verify_module(root)
    dpath = os.path.join(root, "memory", "decisions.md")
    if not os.path.isfile(dpath):
        print("no memory/decisions.md found at %s" % root)
        return 1

    dtext = mv.read(dpath)
    entries = mv.parse_decisions(dtext)  # newest-first, order_index 0 = newest
    if not entries:
        print("no entries found in memory/decisions.md, nothing to redact")
        return 1

    matches = [e for e in entries if args.match.lower() in e["title"].lower()]
    if not matches:
        print("no entry title matched %r -- nothing redacted" % args.match)
        return 1
    if len(matches) > 1:
        print("more than one entry matched %r -- be more specific, nothing redacted:" % args.match)
        for e in matches:
            print("  - [%s] %s" % (e["date"], e["title"]))
        return 1
    target = matches[0]

    # 1. replace the four required fields' content with a fixed placeholder,
    # keep the heading (date + title) exactly as it was
    old_body = target["body"]
    new_body = old_body
    for field in mv.REQUIRED_FIELDS:
        new_body = re.sub(
            r"(\*\*%s\*\*)[^\n]*" % re.escape(field),
            r"\1 %s" % PLACEHOLDER,
            new_body,
            count=1,
        )
    if new_body == old_body:
        print("could not find required fields to redact in the matched entry -- "
              "aborting, no changes made")
        return 1
    if old_body not in dtext:
        print("could not locate the matched entry verbatim in the file -- "
              "aborting, no changes made")
        return 1
    new_dtext = dtext.replace(old_body, new_body, 1)

    # 2. strip the Hash field from the redacted entry and every entry NEWER
    # than it (order_index <= target's), since all of them transitively
    # depend on this entry's content via the chain. Entries older than the
    # redacted one are untouched, their hashes are still valid.
    target_order = target["order_index"]
    stripped_count = 0
    for e in entries:
        if e["order_index"] > target_order:
            continue
        body = new_body if e is target else e["body"]
        body2 = re.sub(r"\*\*Hash:\*\*\s*[0-9a-f]{64}\n?", "", body)
        if body2 != body:
            if body not in new_dtext:
                print("could not locate an entry needing hash removal verbatim -- "
                      "aborting, no changes made")
                return 1
            new_dtext = new_dtext.replace(body, body2, 1)
            stripped_count += 1

    # 3. prepend a new top entry documenting the redaction itself, in the
    # same Decision/Reasoning/Reversible/Review shape as every other entry
    today = datetime.date.today().isoformat()
    by_clause = " (requested by %s)" % args.by if args.by else ""
    redaction_entry = (
        "## %s · Redacted an entry for sensitive content\n"
        "**Decision:** Redacted the Decision/Reasoning/Reversible/Review text of the "
        "entry titled \"%s\" (originally dated %s)%s. Its heading is unchanged; its "
        "body now reads %s.\n"
        "**Reasoning:** %s\n"
        "**Reversible:** No, the original text is gone; this entry and the placeholder "
        "are the permanent record that a redaction happened and why.\n"
        "**Review:** N/A, this is a permanent correction, not a pending decision.\n\n"
    ) % (today, target["title"], target["date"] or "unknown date", by_clause, PLACEHOLDER, args.reason)

    # Insert immediately before the first real entry heading, whatever the
    # header block above it looks like (title line, blockquote description of
    # any length, comments). Do not try to specially parse the header's own
    # shape by regex; an earlier version of this script matched only one '>'
    # line of a multi-line blockquote and inserted the new entry INSIDE the
    # header instead of above the first entry. Finding the first '## '
    # heading and inserting right before it is simpler and can't misparse
    # a header of any length.
    first_heading = re.search(r"^##\s+\S.*$", new_dtext, re.M)
    insert_at = first_heading.start() if first_heading else 0
    new_dtext = new_dtext[:insert_at] + redaction_entry + new_dtext[insert_at:]

    with open(dpath, "w", encoding="utf-8") as f:
        f.write(new_dtext)

    print("redacted entry: %s" % target["title"][:60])
    print("appended a redaction-record entry dated %s" % today)
    print("stripped hash fields from %d entr%s, now rehashing..."
          % (stripped_count, "y" if stripped_count == 1 else "ies"))

    chain_append = os.path.join(root, "molt-chain-append.py")
    if not os.path.isfile(chain_append):
        print("molt-chain-append.py not found at %s -- rehash manually, "
              "memory/decisions.md is currently missing hashes for the redacted "
              "entry and everything newer" % root)
        return 1
    proc = subprocess.run([sys.executable, chain_append, root], capture_output=True, text=True)
    print(proc.stdout, end="")
    if proc.returncode != 0:
        print(proc.stderr, end="")
        print("chain re-hashing failed -- memory/decisions.md is left with the redaction "
              "applied but NOT fully rehashed; fix by hand, do not leave it half-hashed")
        return 1

    print("Run molt-verify.py to confirm the redacted log still verifies end to end. "
          "Do not forget to log this as a new, real entry in memory/INDEX.md too.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
