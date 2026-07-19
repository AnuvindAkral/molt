#!/usr/bin/env python3
"""
molt-verify -- the self-audit that makes a Molt memory trustworthy.

An AI memory you can't trust is worse than no memory, because you rely on it.
This script is the thing that makes Molt different from every other agent-memory
setup: it proves the memory isn't lying to you. No dependencies, no network, no
services. Just Python 3 and your files.

It checks, in order:
  1. the index lists exactly the decisions the log actually contains (no phantom
     rows, no missing rows) -- catches an index that has drifted from the truth;
  2. the log is newest-first and every entry is well-formed;
  3. the append-only anchor is still in place;
  4. the apex file hasn't bloated past its own stated budget;
  5. (the one nobody else does) if you keep a human-readable MIRROR of these
     files, every mirror byte-matches its source -- catches a mirror that has
     quietly gained, lost, or invented a line. This exact check caught a
     fabricated sentence during Molt's own development.

Exit code 0 = trustworthy (failures = 0). Exit code 1 = drift detected.
Warnings never fail the build; failures do. Wire it into CI or a pre-commit hook.

Usage:
    python3 molt-verify.py [ROOT]            # ROOT defaults to the current dir
    python3 molt-verify.py --mirror DIR      # explicit mirror dir (else auto)
    python3 molt-verify.py --no-color
"""

import os
import re
import sys

REQUIRED_FIELDS = ("Decision:", "Reasoning:", "Reversible:", "Review:")
APPEND_ANCHOR = "Add new entries above this line"
APEX_LINE_BUDGET = 300          # matches CLAUDE.md's own stated target
MIRROR_DIR_CANDIDATES = ("mirror", "Mirror", "Obsidian-Vault", "vault")
PLACEHOLDER_DATE = "YYYY-MM-DD"
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ------------------------------------------------------------------ reporting
class Report:
    def __init__(self, color=True):
        self.oks = 0
        self.warns = 0
        self.fails = 0
        self.color = color

    def _c(self, code, text):
        if not self.color:
            return text
        return "\033[%sm%s\033[0m" % (code, text)

    def ok(self, msg):
        self.oks += 1
        print("  %s %s" % (self._c("32", "PASS"), msg))

    def warn(self, msg):
        self.warns += 1
        print("  %s %s" % (self._c("33", "WARN"), msg))

    def fail(self, msg):
        self.fails += 1
        print("  %s %s" % (self._c("31", "FAIL"), msg))

    def section(self, title):
        print("\n" + self._c("1", title))


# ------------------------------------------------------------------ parsing
def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def parse_decisions(text):
    """Return a list of entries: {date, title, body, fields, order_index}."""
    entries = []
    lines = text.splitlines()
    current = None
    for line in lines:
        m = re.match(r"^##\s+(.*\S)\s*$", line)
        if m:
            if current:
                entries.append(current)
            heading = m.group(1).strip()
            # heading form: "DATE · Title"  (middle dot separator)
            if "·" in heading:
                date_part, title_part = heading.split("·", 1)
                date, title = date_part.strip(), title_part.strip()
            else:
                date, title = None, heading
            current = {"date": date, "title": title, "body": ""}
        elif current is not None:
            current["body"] += line + "\n"
    if current:
        entries.append(current)
    for i, e in enumerate(entries):
        e["fields"] = [f for f in REQUIRED_FIELDS if ("**%s**" % f) in e["body"] or f in e["body"]]
        e["order_index"] = i
    return entries


def parse_index_rows(text):
    """Return list of (date, title) from any markdown table rows whose first
    cell is a date (ISO or the YYYY-MM-DD placeholder)."""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        first = cells[0]
        if ISO_DATE.match(first) or first == PLACEHOLDER_DATE:
            # title is the last non-token cell before an approx-tokens column;
            # convention: | Date | Type | Title | ~tokens |
            title = cells[2] if len(cells) >= 4 else cells[-1]
            rows.append((first, norm(title)))
    return rows


# ------------------------------------------------------------------ checks
def check_structure(root, rep):
    rep.section("structure")
    ok = True
    for rel in ("CLAUDE.md", "memory/INDEX.md", "memory/decisions.md"):
        if os.path.isfile(os.path.join(root, rel)):
            rep.ok("found %s" % rel)
        else:
            rep.fail("missing %s (is this a Molt root?)" % rel)
            ok = False
    return ok


def check_apex_budget(root, rep):
    rep.section("apex file")
    path = os.path.join(root, "CLAUDE.md")
    if not os.path.isfile(path):
        return
    n = len(read(path).splitlines())
    if n <= APEX_LINE_BUDGET:
        rep.ok("CLAUDE.md is %d lines (budget %d)" % (n, APEX_LINE_BUDGET))
    else:
        rep.warn("CLAUDE.md is %d lines, over its %d-line budget -- prune or promote to memory"
                 % (n, APEX_LINE_BUDGET))


def check_decisions_and_index(root, rep):
    rep.section("memory: index <-> log")
    dpath = os.path.join(root, "memory/decisions.md")
    ipath = os.path.join(root, "memory/INDEX.md")
    if not (os.path.isfile(dpath) and os.path.isfile(ipath)):
        return
    dtext, itext = read(dpath), read(ipath)
    entries = parse_decisions(dtext)
    rows = parse_index_rows(itext)

    if not entries:
        rep.warn("no decision entries found yet (empty log)")
    # well-formed
    for e in entries:
        missing = [f.rstrip(":") for f in REQUIRED_FIELDS if f not in [x for x in e["fields"]]]
        if missing:
            rep.warn("entry '%s' missing field(s): %s" % (e["title"][:48], ", ".join(missing)))
    if entries and all(len(e["fields"]) == len(REQUIRED_FIELDS) for e in entries):
        rep.ok("all %d log entr%s well-formed (Decision/Reasoning/Reversible/Review)"
               % (len(entries), "y is" if len(entries) == 1 else "ies are"))

    # newest-first ordering among real-dated entries
    dated = [(e["date"], e["order_index"], e["title"]) for e in entries if e["date"] and ISO_DATE.match(e["date"])]
    out_of_order = []
    for i in range(1, len(dated)):
        if dated[i][0] > dated[i - 1][0]:
            out_of_order.append((dated[i - 1], dated[i]))
    if out_of_order:
        for older, newer in out_of_order:
            rep.fail("log not newest-first: %s appears above %s" % (older[0], newer[0]))
    elif dated:
        rep.ok("log is newest-first (%d dated entr%s)" % (len(dated), "y" if len(dated) == 1 else "ies"))

    # index <-> log set equality (by date + normalized title)
    log_keys = set((e["date"], norm(e["title"])) for e in entries)
    idx_keys = set(rows)
    phantom = idx_keys - log_keys        # in index, not in log = index is lying
    missing = log_keys - idx_keys        # in log, not in index = index is stale
    if not rows:
        rep.warn("index has no decision rows -- add one row per log entry")
    if phantom:
        for d, t in sorted(phantom):
            rep.fail("index lists an entry the log does NOT contain: [%s] %s" % (d, t[:60]))
    if missing:
        for d, t in sorted(missing):
            rep.fail("log entry missing from the index: [%s] %s" % (d, t[:60]))
    if rows and not phantom and not missing:
        rep.ok("index matches the log exactly (%d entr%s, no phantoms, no gaps)"
               % (len(rows), "y" if len(rows) == 1 else "ies"))

    # append anchor
    if APPEND_ANCHOR.lower() in dtext.lower():
        rep.ok("append-only anchor present")
    else:
        rep.warn("append-only anchor missing -- add '<!-- %s ... -->' to guard ordering" % APPEND_ANCHOR)

    # leftover placeholder
    if PLACEHOLDER_DATE in dtext or PLACEHOLDER_DATE in itext:
        rep.warn("example placeholder (%s) still present -- replace with a real first entry" % PLACEHOLDER_DATE)


def find_mirror_dir(root, explicit):
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    for name in MIRROR_DIR_CANDIDATES:
        p = os.path.join(root, name)
        if os.path.isdir(p):
            return p
    return None


def check_mirror(root, rep, explicit):
    rep.section("mirror (drift catch)")
    mdir = find_mirror_dir(root, explicit)
    if not mdir:
        print("  (no mirror directory found -- skipped; this check is opt-in)")
        return
    rel_mirror = os.path.relpath(mdir, root)
    drift = 0
    checked = 0
    for dirpath, _dirs, files in os.walk(mdir):
        for fn in files:
            mpath = os.path.join(dirpath, fn)
            rel = os.path.relpath(mpath, mdir)
            src = os.path.join(root, rel)
            checked += 1
            if not os.path.isfile(src):
                rep.fail("mirror has a file with no source counterpart: %s/%s" % (rel_mirror, rel))
                drift += 1
                continue
            if read(src) != read(mpath):
                rep.fail("mirror OUT OF SYNC with source: %s (run your sync, do not hand-edit)" % rel)
                drift += 1
    if checked == 0:
        print("  (mirror dir is empty -- nothing to compare)")
    elif drift == 0:
        rep.ok("all %d mirrored file(s) byte-match their source" % checked)


# ------------------------------------------------------------------ main
def main(argv):
    root = "."
    explicit_mirror = None
    color = sys.stdout.isatty()
    args = argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--mirror" and i + 1 < len(args):
            explicit_mirror = args[i + 1]
            i += 2
        elif a == "--no-color":
            color = False
            i += 1
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            root = a
            i += 1

    rep = Report(color=color)
    title = "MOLT . self-audit"
    bar = "=" * (len(title) + 4)
    print(rep._c("1", bar))
    print(rep._c("1", "  " + title))
    print(rep._c("1", bar))
    print("root: %s" % os.path.abspath(root))

    if not check_structure(root, rep):
        print("\n" + rep._c("31", "Not a Molt root. Nothing else to check."))
        return 1

    check_apex_budget(root, rep)
    check_decisions_and_index(root, rep)
    check_mirror(root, rep, explicit_mirror)

    print("\n" + "-" * 52)
    if rep.fails:
        verdict = rep._c("31", "DRIFT DETECTED")
        tail = "fix at the source, re-run, do not paper over"
    elif rep.warns:
        verdict = rep._c("33", "TRUSTWORTHY (with notes)")
        tail = "no lies, a few things worth tidying"
    else:
        verdict = rep._c("32", "TRUSTWORTHY")
        tail = "index, log, and mirror all tell the same story"
    print("VERDICT: %s   %d pass / %d warn / %d fail" % (verdict, rep.oks, rep.warns, rep.fails))
    print("%s" % tail)
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
