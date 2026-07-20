#!/usr/bin/env python3
"""
molt-verify -- the self-audit that makes a Molt memory trustworthy.

An AI memory you can't trust is worse than no memory, because you rely on it.
This script is the thing that makes Molt different from every other agent-memory
setup: it proves the memory isn't lying to you. No dependencies, no network, no
services. Just Python 3 and your files.

It checks, in order:
  0. no tracked memory/apex file contains an unresolved git merge conflict
     marker (a real risk once memory/decisions.md is shared and edited
     concurrently) -- checked first, since a stray marker would corrupt
     every check downstream, and the goal is one clear failure, not a
     confusing cascade;
  1. the index lists exactly the decisions the log actually contains (no phantom
     rows, no missing rows) -- catches an index that has drifted from the truth;
  2. the log is newest-first and every entry is well-formed;
  3. the append-only anchor is still in place;
  4. the apex file hasn't bloated past its own stated budget;
  5. if AGENTS.md exists (the open cross-tool convention read natively by
     Cursor, Copilot, Codex CLI, Gemini CLI, Aider, Windsurf, and Zed), it
     byte-matches CLAUDE.md, so every tool sees the same rules instead of two
     copies quietly drifting apart;
  6. if .gitignore exists, CLAUDE.md/AGENTS.md/memory/ are never accidentally
     excluded from it (the shared rules silently stop syncing), and if a
     personal CLAUDE.local.md exists, it IS excluded (no personal leakage);
  7. nested CLAUDE.md/AGENTS.md files in domain subdirectories (a monorepo's
     backend/, frontend/, a subsystem) never redeclare the root-only tags
     <never>/<verification>/<before_declaring_done>, and a domain's own
     CLAUDE.md and AGENTS.md pair byte-match each other;
  7b. INDEX.md's ~tokens estimate for each entry is honest (within tolerance
     of a freshly computed estimate), and no single entry has grown past a
     verbosity budget -- progressive disclosure only works if the number a
     session uses to decide "is this cheap to open" is actually true;
  8. if any entry carries a **Hash:** field (opt-in), every entry must, and
     the chain, sha256(entry + previous entry's hash), must verify oldest to
     newest -- altering any historical entry invalidates every hash after it,
     even with no mirror kept. See molt-chain-append.py to adopt this. IMPORTANT
     BOUNDARY: this proves the log is internally self-consistent, not that no
     one who understands the mechanism rewrote it -- see check 9 and
     ARCHITECTURE.md's "What the hash chain does and doesn't prove";
  9. (local, best-effort, opt-in) if this is a git repository, the working
     copy of memory/decisions.md is compared against the version at the last
     commit (HEAD); an uncommitted change to anything other than new entries
     added on top gets flagged before it can be committed over. No network,
     no push required, matches Molt's own dependency-free design. This is a
     mitigation for check 8's limitation, not a replacement for it: a rewrite
     that has ALREADY been committed can't be caught this way, that needs a
     signing key or a remote with branch protection;
  10. INDEX.md's own structural sections (handoffs/, domain buckets) haven't
     silently vanished;
  11. if real handoff files exist in memory/handoffs/, INDEX.md's handoffs
      table lists exactly those files, no phantoms, no gaps;
  12. (the one nobody else does) if you keep a human-readable MIRROR of these
     files, every mirror byte-matches its source -- catches a mirror that has
     quietly gained, lost, or invented a line. This exact check caught a
     fabricated sentence during Molt's own development.
  13. if molt-init.py exists alongside real copies of the files it embeds
     (molt-verify.py, molt-chain-append.py, molt-redact.py, the pre-commit
     hook, the CI workflow), its embedded base64 copies byte-match the real
     files -- molt-init.py must work standalone with nothing else present
     (see its own docstring), which means it carries its own copies rather
     than reading siblings at runtime, and a carried copy that's gone stale
     the moment someone edits molt-verify.py and forgets to run
     scripts/build-molt-init.py is exactly the kind of silent drift this
     whole project exists to catch. Opt-in: skipped if molt-init.py or any
     given sibling isn't present in this root at all.

The log parser also refuses to treat a '## '-looking line as a new entry unless
it's preceded by a blank line, so a heading pasted or written inside an entry's
own body (a quoted code review, a copied doc excerpt) can't silently split or
merge real entries. Found by the adversarial benchmark, not by inspection.

TRUSTWORTHY means structural integrity: the files agree with each other and
haven't been silently altered by the mechanisms this script knows how to
check. It does NOT mean the content is honest, accurate, or the right
decision; a well-formed, internally consistent log can still contain a lie a
human typed on purpose. See ARCHITECTURE.md for the full boundary.

Exit code 0 = trustworthy (failures = 0). Exit code 1 = drift detected.
Warnings never fail the build; failures do. Wire it into CI or a pre-commit hook.

Usage:
    python3 molt-verify.py [ROOT]            # ROOT defaults to the current dir
    python3 molt-verify.py --mirror DIR      # explicit mirror dir (else auto)
    python3 molt-verify.py --no-color
"""

import base64
import fnmatch
import hashlib
import os
import re
import subprocess
import sys

REQUIRED_FIELDS = ("Decision:", "Reasoning:", "Reversible:", "Review:")
APPEND_ANCHOR = "Add new entries above this line"
APEX_LINE_BUDGET = 300          # matches CLAUDE.md's own stated target
MIRROR_DIR_CANDIDATES = ("mirror", "Mirror", "Obsidian-Vault", "vault")
PLACEHOLDER_DATE = "YYYY-MM-DD"
# Hash-chaining: each entry's optional **Hash:** field commits to that entry's
# own content plus the previous (older) entry's hash, SHA-256 hex, so altering
# any historical entry invalidates every hash from that point forward, the
# same principle as the IETF's 2026 Agent Audit Trail draft. Genesis is the
# hash "before" the oldest entry in the file.
CHAIN_GENESIS = "0" * 64
# [0-9], not \d: Python's \d matches any Unicode decimal digit, including
# lookalikes like full-width digits (１２３). Those pass \d{4}-\d{2}-\d{2} but
# sort as a completely different string, so a forged date built from them can
# make an old or fake entry always compare as "newest" without ever tripping
# the newest-first check. [0-9] only matches literal ASCII digits.
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


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
    """Return a list of entries: {date, title, body, fields, order_index}.

    A line only starts a new entry if it looks like a '## ' heading AND is
    preceded by a blank line (or is the very first line). Every real entry in
    this file's own convention is separated from the previous one by a blank
    line, so this guard is free for well-formed logs. Its job is to stop a
    '## something' line pasted or written *inside* an entry's own body, for
    example a quoted code review or a copied doc excerpt in a Reasoning field,
    from being misread as a second entry and silently splitting or merging
    real content. Caught during the adversarial benchmark, not by inspection.
    """
    entries = []
    lines = text.splitlines()
    current = None
    prev_blank = True  # start of file counts as "preceded by blank"
    for line in lines:
        m = re.match(r"^##\s+(.*\S)\s*$", line)
        if m and prev_blank:
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
        prev_blank = (line.strip() == "")
    if current:
        entries.append(current)
    for i, e in enumerate(entries):
        e["fields"] = [f for f in REQUIRED_FIELDS if ("**%s**" % f) in e["body"] or f in e["body"]]
        e["order_index"] = i
    return entries


def parse_index_table(text):
    """Parse every markdown table in an INDEX.md-shaped file into a list of
    row dicts keyed by that table's own header names (e.g. 'Date', 'Type',
    'Title', '~tokens', 'Gist'), for any pipe-line whose first cell is a real
    ISO date or the YYYY-MM-DD placeholder. Column-NAME driven when a header
    can be matched, not positional: an earlier version hardcoded
    cells[2]/cells[3], so adding an optional column (like 'Gist', a one-line
    summary that lets most lookups skip opening decisions.md at all) would
    have silently broken title and token parsing instead of just working.

    A date-like row with no matching header in scope (wrong column count, or
    genuinely outside any recognized table, e.g. pasted after prose with no
    blank-line table structure around it) still produces a minimal
    {'Date', 'Title'} guess via positional fallback (title = 3rd cell),
    rather than being silently dropped. This isn't cosmetic: an earlier,
    stricter version of this parser required strict header adjacency, and a
    phantom row appended past the end of the real table (still date-shaped,
    still misleading to a reader) went completely unrecognized as a result,
    a real regression found by this project's own adversarial benchmark
    catching itself. The floor this project starts from is 'find any
    date-shaped row anywhere', richer parsing is a bonus on top of that
    floor, never a replacement for it."""
    lines = text.splitlines()
    header = None
    prev_cells = None
    rows = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            prev_cells = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if prev_cells is not None and len(cells) == len(prev_cells) and all(
            re.match(r"^:?-+:?$", c) for c in cells
        ):
            header = prev_cells
            prev_cells = None
            continue
        first = cells[0]
        if ISO_DATE.match(first) or first == PLACEHOLDER_DATE:
            if header is not None and len(cells) == len(header):
                rows.append(dict(zip(header, cells)))
            else:
                rows.append({"Date": first, "Title": cells[2] if len(cells) >= 3 else cells[-1]})
        prev_cells = cells
    return rows


def parse_index_rows(text):
    """Return list of (date, title) for every decisions-table row (any row
    with a 'Title' column), regardless of what other columns exist."""
    return [
        (row["Date"], norm(row["Title"]))
        for row in parse_index_table(text)
        if "Title" in row
    ]


def parse_index_token_estimates(text):
    """Return {(date, title): claimed_tokens_int} for decisions-table rows
    whose '~tokens' cell parses as a number (with or without a leading '~')."""
    out = {}
    for row in parse_index_table(text):
        if "Title" not in row or "~tokens" not in row:
            continue
        m = re.match(r"~?\s*([0-9]+)", row["~tokens"])
        if m:
            out[(row["Date"], norm(row["Title"]))] = int(m.group(1))
    return out


def estimate_tokens(text):
    """Rough, dependency-free token estimate: ~1.35 tokens per whitespace-
    separated word, a reasonable approximation for English prose. Not a real
    tokenizer -- pulling one in would add a dependency for a number whose
    only job is to help a session decide whether opening an entry is cheap,
    not to be exact."""
    words = len(text.split())
    return round(words * 1.35)


ENTRY_TOKEN_BUDGET = 600          # WARN threshold: a single entry this large
                                  # undermines progressive disclosure's whole
                                  # point, one "cheap lookup" stops being cheap
INDEX_TOKEN_DRIFT_RATIO = 0.25    # WARN if claimed vs actual differ by more
INDEX_TOKEN_DRIFT_ABS = 50        # than both this fraction AND this many
                                  # tokens (avoids noise on tiny entries)


def check_token_efficiency(root, rep):
    """Progressive disclosure (see ARCHITECTURE.md) only works if INDEX.md's
    ~tokens column is honest: a session decides what to open based on that
    number. Found by direct measurement, not suspicion: every existing
    estimate in this project's own INDEX.md was 30-50% below the entry's real
    size, silently undercounting the true cost of a lookup. Two checks: (1)
    an entry whose estimate has drifted from a freshly computed one beyond a
    tolerance; (2) a single entry that has grown past ENTRY_TOKEN_BUDGET,
    a verbosity-creep signal independent of whether the index agrees with it."""
    rep.section("token efficiency (progressive disclosure honesty)")
    dpath = os.path.join(root, "memory", "decisions.md")
    ipath = os.path.join(root, "memory", "INDEX.md")
    if not (os.path.isfile(dpath) and os.path.isfile(ipath)):
        return
    entries = parse_decisions(read(dpath))
    claimed = parse_index_token_estimates(read(ipath))
    if not entries:
        return

    drifted = []
    oversized = []
    for e in entries:
        actual = estimate_tokens(e["body"])
        if actual > ENTRY_TOKEN_BUDGET:
            oversized.append((e["title"][:55], actual))
        key = (e["date"], norm(e["title"]))
        if key not in claimed:
            continue
        claim = claimed[key]
        diff = abs(actual - claim)
        if claim == 0:
            continue
        if diff > INDEX_TOKEN_DRIFT_ABS and diff / claim > INDEX_TOKEN_DRIFT_RATIO:
            drifted.append((e["title"][:55], claim, actual))

    for title, claim, actual in drifted:
        rep.warn(
            "INDEX.md claims ~%d tokens for '%s' but it's actually ~%d -- "
            "progressive disclosure only works if this number is honest, refresh it"
            % (claim, title, actual)
        )
    for title, actual in oversized:
        rep.warn(
            "entry '%s' is ~%d tokens, over the %d-token verbosity budget -- "
            "a single lookup stops being cheap once entries grow like this"
            % (title, actual, ENTRY_TOKEN_BUDGET)
        )

    # Gist column (optional): a one-line summary short enough that most
    # lookups ("what did we decide about X") resolve from INDEX.md alone,
    # without opening the full entry. This is the single biggest lever real
    # agent-memory systems use for token efficiency (an index hit answers
    # most queries; a full fetch is the rare exception), so it's checked with
    # the same discipline as everything else here: opt-in, and once adopted,
    # an empty cell is a gap, not a style choice.
    index_rows = parse_index_table(read(ipath))
    has_gist_column = any("Gist" in row for row in index_rows)
    empty_gist = []
    if has_gist_column:
        for row in index_rows:
            if "Title" in row and "Gist" in row and not row["Gist"].strip():
                empty_gist.append(row["Title"][:55])
    for title in empty_gist:
        rep.warn(
            "INDEX.md has a Gist column but the row for '%s' leaves it empty -- "
            "an empty gist forces opening the full entry for something a one-line "
            "summary could have answered" % title
        )

    if not drifted and not oversized and not empty_gist:
        rep.ok("all %d entr%s' index estimates are accurate and within the verbosity budget%s"
               % (len(entries), "y" if len(entries) == 1 else "ies",
                  ", every Gist is filled in" if has_gist_column else ""))


def canonical_entry_text(e):
    """Deterministic text hashed for one entry: its own required-field lines,
    trailing whitespace stripped, blank lines dropped, in file order, with any
    existing **Hash:** line excluded (an entry can't hash its own hash)."""
    lines = []
    for line in e["body"].splitlines():
        s = line.rstrip()
        if not s:
            continue
        if s.lstrip().startswith("**Hash:**"):
            continue
        lines.append(s)
    return "\n".join(lines)


def entry_hash(e, prev_hash):
    text = canonical_entry_text(e) + "\n" + prev_hash
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_stored_hash(e):
    m = re.search(r"\*\*Hash:\*\*\s*([0-9a-f]{64})", e["body"])
    return m.group(1) if m else None


def check_hash_chain(root, rep):
    """If any entry carries a **Hash:** field, every entry must, and the
    chain must verify oldest to newest: this entry's hash must equal
    sha256(its own content + the previous entry's hash). A log with no Hash
    fields at all is untouched, hash-chaining is opt-in, same as the mirror
    check. A log with SOME entries hashed and others not has an incomplete
    chain, which is treated as a failure, not a warning: a half-adopted
    tamper-evidence scheme gives false confidence."""
    rep.section("hash chain (tamper-evidence)")
    dpath = os.path.join(root, "memory", "decisions.md")
    if not os.path.isfile(dpath):
        return
    entries = parse_decisions(read(dpath))
    if not entries:
        return
    has_any_hash = any(parse_stored_hash(e) is not None for e in entries)
    if not has_any_hash:
        print("  (no Hash fields found -- hash-chaining not adopted, optional, skipped)")
        return

    missing = [e for e in entries if parse_stored_hash(e) is None]
    if missing:
        for e in missing:
            rep.fail("entry has no Hash field but other entries in this log do -- "
                     "chain is incomplete: %s" % e["title"][:60])
        return

    oldest_first = list(reversed(entries))
    prev = CHAIN_GENESIS
    for e in oldest_first:
        stored = parse_stored_hash(e)
        computed = entry_hash(e, prev)
        if stored != computed:
            rep.fail(
                "hash chain broken at '%s' -- stored hash doesn't match its recomputed "
                "value; this entry or an earlier one was altered after being hashed"
                % e["title"][:60]
            )
            return
        prev = stored
    rep.ok("hash chain verified across %d entries, unbroken from genesis to newest" % len(entries))


def check_git_anchor(root, rep):
    """Local, best-effort mitigation for the hash chain's real limitation
    (see ARCHITECTURE.md, "What the hash chain does and doesn't prove"): the
    chain alone proves internal self-consistency, not that no one who
    understands the mechanism rewrote history. If this is a git repository,
    the working copy of memory/decisions.md is compared against the version
    at the last commit (HEAD). A change to anything other than new entries
    added on top -- i.e. a historical entry's content differs from what was
    last committed -- is flagged before it gets committed over.

    This is entirely local: no push, no remote, no network call, same
    dependency-free design as the rest of Molt. It catches the exact attack
    this project's own security review demonstrated (tamper with an old
    entry, strip its Hash field and every one after it, regenerate a fresh,
    internally-consistent chain) as long as that tampering hasn't ALSO been
    committed yet. Once a rewrite is committed, this check alone can't see
    it; that needs a signing key or a remote with branch protection, both
    outside what a local, dependency-free script can guarantee. Documented
    honestly, not oversold. Opt-in: skipped entirely if this isn't a git
    repository, git isn't installed, or decisions.md has no commit yet.

    Detects "is this a git repo" via `git rev-parse --is-inside-work-tree`,
    not by checking for a literal `.git` directory inside ROOT: that
    directory-based check is wrong the moment Molt's root is a subdirectory
    of a larger repository (a monorepo, Molt vendored into an existing
    project), a real, confirmed deployment shape, not an edge case. It
    silently reported "not a git repository" in that shape, disabling the
    CRITICAL mitigation exactly where nesting makes it most likely someone
    would need it. Similarly, `HEAD:memory/decisions.md` is resolved by git
    relative to the repository's TOP LEVEL, not the current directory;
    `HEAD:./memory/decisions.md` (the `./` prefix) is the cwd-relative form,
    required for the same nested-root case."""
    rep.section("git anchor (local, best-effort -- not non-repudiation)")
    try:
        toplevel_proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
    except (OSError, FileNotFoundError):
        print("  (git binary not available -- skipped)")
        return
    except Exception as exc:  # noqa: BLE001 -- git invocation must never crash the audit
        print("  (git invocation failed unexpectedly (%s) -- skipped)" % exc.__class__.__name__)
        return
    if toplevel_proc.returncode != 0 or toplevel_proc.stdout.strip() != "true":
        print("  (not a git repository -- skipped, this check is opt-in)")
        return
    try:
        proc = subprocess.run(
            ["git", "show", "HEAD:./memory/decisions.md"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
    except (OSError, FileNotFoundError):
        print("  (git binary not available -- skipped)")
        return
    except Exception as exc:  # noqa: BLE001 -- git invocation must never crash the audit
        print("  (git invocation failed unexpectedly (%s) -- skipped)" % exc.__class__.__name__)
        return
    if proc.returncode != 0:
        print("  (memory/decisions.md not yet committed, or repo has no commits -- nothing to compare)")
        return
    head_text = proc.stdout
    dpath = os.path.join(root, "memory", "decisions.md")
    try:
        working_text = read(dpath)
    except (OSError, UnicodeDecodeError):
        return
    if head_text == working_text:
        rep.ok("memory/decisions.md matches the last git commit, no uncommitted rewrite")
        return
    head_entries = parse_decisions(head_text)
    head_bodies = [e["body"] for e in head_entries]
    if head_bodies and all(b in working_text for b in head_bodies):
        rep.ok(
            "uncommitted changes to memory/decisions.md are additive only (new "
            "entries added on top) -- nothing from the last commit was altered"
        )
    else:
        rep.fail(
            "memory/decisions.md has uncommitted changes to content that already "
            "existed at the last git commit -- review before committing; this is "
            "exactly what a history rewrite looks like, even if it isn't one. "
            "Commit legitimate new entries often so this check stays a tight anchor."
        )


GITIGNORE_MUST_STAY_TRACKED = ("CLAUDE.md", "AGENTS.md", "memory")
LOCAL_APEX_FILES = ("CLAUDE.local.md", "AGENTS.local.md")


def parse_gitignore_patterns(text):
    return [s.strip() for s in text.splitlines() if s.strip() and not s.strip().startswith("#")]


def gitignore_matches(patterns, name):
    """Small, deliberately non-exhaustive gitignore matcher: exact match or a
    simple glob, with or without a trailing slash. Good enough to catch the
    two real mistakes this check exists for, not a full gitignore engine."""
    target = name.rstrip("/")
    for p in patterns:
        p_clean = p.rstrip("/")
        if p_clean == target or fnmatch.fnmatch(target, p_clean):
            return True
    return False


def check_gitignore_sanity(root, rep):
    """Two real mistakes with the shared-vs-personal apex convention, per the
    2026 team-rules research this was built from: (1) CLAUDE.local.md exists
    but isn't actually gitignored, personal preferences leak into the shared
    repo; (2) CLAUDE.md, AGENTS.md, or memory/ get accidentally gitignored,
    silently stopping the team's shared rules from syncing at all, described
    as the single most common real mistake teams make with this pattern."""
    rep.section("gitignore sanity")
    gpath = os.path.join(root, ".gitignore")
    # No .gitignore at all is NOT a reason to skip this check: a personal
    # CLAUDE.local.md with zero protection is the worst version of the leak
    # this check exists to catch, not a pass-through case.
    patterns = parse_gitignore_patterns(read(gpath)) if os.path.isfile(gpath) else []

    # this matcher (exact match or a simple glob) doesn't evaluate '!'
    # negation lines at all -- a negation could silently re-include something
    # meant to stay ignored, or the check above could misjudge a pattern that
    # a real negation elsewhere modifies. Loud WARN rather than a wrong answer.
    negations = [p for p in patterns if p.startswith("!")]
    if negations:
        rep.warn(
            ".gitignore contains %d negation pattern(s) ('!...') -- this checker "
            "does not evaluate negation rules, verify by hand that nothing shared "
            "or personal is unintentionally re-included or excluded: %s"
            % (len(negations), ", ".join(negations[:3]))
        )

    leaked_shared = [name for name in GITIGNORE_MUST_STAY_TRACKED if gitignore_matches(patterns, name)]
    for name in leaked_shared:
        rep.fail(
            ".gitignore excludes '%s' -- this is shared team state and must stay tracked, "
            "the far more common real mistake with this convention" % name
        )

    any_local = False
    for local_name in LOCAL_APEX_FILES:
        if os.path.isfile(os.path.join(root, local_name)):
            any_local = True
            if gitignore_matches(patterns, local_name):
                rep.ok("%s exists and is correctly excluded by .gitignore" % local_name)
            else:
                rep.fail(
                    "%s exists but is NOT excluded by .gitignore -- personal preferences "
                    "could get committed and shared with the whole team" % local_name
                )

    if not leaked_shared and not any_local:
        rep.ok(".gitignore doesn't exclude any shared apex file or memory/")


RESERVED_ROOT_ONLY_TAGS = ("<never>", "<verification>", "<before_declaring_done>")
NESTED_APEX_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def find_nested_apex_files(root):
    """Yield (dirpath, filename) for every CLAUDE.md/AGENTS.md in a
    subdirectory of root (never the root itself). Skips Molt's own root
    memory/ *by exact path*, not by bare directory name, so a real domain
    subdirectory that happens to also be named "memory" elsewhere in the
    tree (e.g. packages/memory/, a caching subsystem) still gets checked.
    Skipping by name alone was a real bug: it silently let a genuine
    <never>-redeclaration violation inside such a directory go completely
    unchecked, found via testing, not by inspection."""
    root_memory = os.path.abspath(os.path.join(root, "memory"))
    # followlinks=False (the default) already stops os.walk from descending
    # INTO a symlinked directory; explicit here so that guarantee is never
    # accidentally lost by a future edit, since walking outside the intended
    # tree via a symlink is exactly how this check could be pointed at files
    # it was never meant to read.
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d for d in dirnames
            if d not in NESTED_APEX_SKIP_DIRS
            and not d.startswith(".")
            and os.path.abspath(os.path.join(dirpath, d)) != root_memory
        ]
        if os.path.abspath(dirpath) == os.path.abspath(root):
            continue
        for fn in ("CLAUDE.md", "AGENTS.md"):
            full = os.path.join(dirpath, fn)
            if fn in filenames and not os.path.islink(full):
                yield dirpath, fn


def check_nested_apex_consistency(root, rep):
    """Domain subdirectories in a monorepo (backend/, frontend/, a subsystem)
    may keep their own AGENTS.md/CLAUDE.md, a real 2026 convention. Two
    mechanical checks, since judging semantic contradiction would need an
    LLM, not deterministic code: (1) a nested apex file must not redeclare
    <never>, <verification>, or <before_declaring_done>, those are root-only
    shared governance, same principle as CLAUDE.local.md not being allowed
    to weaken them; (2) if a domain directory keeps both CLAUDE.md and
    AGENTS.md, they must be byte-identical, the same mirror mechanism as the
    root pair."""
    rep.section("nested apex files (monorepo)")
    found = list(find_nested_apex_files(root))
    if not found:
        print("  (no nested CLAUDE.md/AGENTS.md found -- optional, skipped)")
        return

    by_dir = {}
    for dirpath, fn in found:
        by_dir.setdefault(dirpath, []).append(fn)

    any_fail = False
    for dirpath, fns in sorted(by_dir.items()):
        rel_dir = os.path.relpath(dirpath, root)
        for fn in fns:
            text = read(os.path.join(dirpath, fn))
            # a tag only counts as "redeclared" if it's an actual section
            # opening, alone on its own line, the way real tags are written
            # in the root file. A prose mention like "see `<never>` in the
            # root file" is not a redeclaration and must not be flagged;
            # found as a false positive against this project's own real
            # nested example the first time this check ran.
            bad_tags = [
                t for t in RESERVED_ROOT_ONLY_TAGS
                if re.search(r"^\s*%s\s*$" % re.escape(t), text, re.M)
            ]
            if bad_tags:
                any_fail = True
                rep.fail(
                    "%s/%s redeclares root-only tag(s) %s -- domain files may add "
                    "sections, not redefine shared governance"
                    % (rel_dir, fn, ", ".join(bad_tags))
                )
        if "CLAUDE.md" in fns and "AGENTS.md" in fns:
            c_text = read(os.path.join(dirpath, "CLAUDE.md"))
            a_text = read(os.path.join(dirpath, "AGENTS.md"))
            if c_text == a_text:
                rep.ok("%s: nested CLAUDE.md and AGENTS.md byte-match" % rel_dir)
            else:
                any_fail = True
                rep.fail("%s: nested CLAUDE.md and AGENTS.md have drifted apart" % rel_dir)

    if not any_fail:
        rep.ok(
            "%d nested apex file(s) across %d director%s, no reserved-tag violations"
            % (len(found), len(by_dir), "y" if len(by_dir) == 1 else "ies")
        )


def check_agents_md(root, rep):
    """AGENTS.md is the open, cross-tool convention (Cursor, Copilot, Codex
    CLI, Gemini CLI, Aider, Windsurf, Zed all auto-load it) that Claude Code
    and Cowork don't use, they read CLAUDE.md instead. Rather than maintain
    two sets of rules, AGENTS.md is meant to be a byte-identical copy of
    CLAUDE.md, the same mirror mechanism this script already uses for a
    human-readable vault, applied to one file. This is what makes the
    model-independence claim actually hold across tools, not just models."""
    rep.section("cross-tool file (AGENTS.md)")
    apath = os.path.join(root, "AGENTS.md")
    cpath = os.path.join(root, "CLAUDE.md")
    if not os.path.isfile(apath):
        print("  (no AGENTS.md -- optional, skipped; add one for Cursor/Copilot/"
              "Codex CLI/Gemini CLI/Aider/Windsurf/Zed compatibility)")
        return
    if not os.path.isfile(cpath):
        rep.fail("AGENTS.md exists but CLAUDE.md is missing -- nothing for it to mirror")
        return
    try:
        same = read(apath) == read(cpath)
    except (UnicodeDecodeError, OSError) as exc:
        rep.fail("could not compare AGENTS.md against CLAUDE.md: %s: %s"
                 % (exc.__class__.__name__, str(exc)[:80]))
        return
    if same:
        rep.ok("AGENTS.md byte-matches CLAUDE.md (cross-tool agents see the same rules)")
    else:
        rep.fail("AGENTS.md has drifted from CLAUDE.md -- regenerate it from CLAUDE.md, "
                 "do not hand-edit either one out of sync")


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


MERGE_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
CONFLICT_CHECKED_FILES = (
    "CLAUDE.md", "AGENTS.md", "CLAUDE.local.md", "AGENTS.local.md",
    os.path.join("memory", "decisions.md"), os.path.join("memory", "INDEX.md"),
)


def check_merge_conflict_markers(root, rep):
    """Concurrent edits to a shared, append-only memory/decisions.md is a
    real scenario (two people, or two agent sessions, both add an entry at
    the top around the same time) and a real git merge conflict, since both
    sides touch the exact same anchor point. `.gitattributes` sets
    `merge=union` for memory/decisions.md so most such conflicts resolve
    automatically (both entries kept, order settled by the existing same-day
    WARN if ambiguous). Union merge can't cover every shape of conflict
    (e.g. if the file was hash-chained, since each side's Hash field commits
    to a different prev_hash), and a human resolving a REAL conflict by hand
    can always leave literal `<<<<<<<`/`=======`/`>>>>>>>` markers behind if
    they save mid-resolution or miss one. Those markers must never survive
    into a commit: they'd corrupt parsing of every check downstream, silently
    or not, so this runs first and fails loud, immediately, rather than
    letting a confusing cascade of unrelated-looking failures be the only
    signal something went wrong."""
    rep.section("merge conflict markers")
    found_any = False
    for rel in CONFLICT_CHECKED_FILES:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        try:
            text = read(path)
        except (OSError, UnicodeDecodeError):
            continue
        for marker in MERGE_CONFLICT_MARKERS:
            if any(line.startswith(marker) for line in text.splitlines()):
                found_any = True
                rep.fail(
                    "%s contains an unresolved merge conflict marker (%s) -- "
                    "finish resolving the merge before committing, then re-run "
                    "molt-chain-append.py if this file is hash-chained" % (rel, marker)
                )
    if not found_any:
        rep.ok("no unresolved merge conflict markers in any tracked memory/apex file")


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
            rep.fail("entry '%s' missing field(s): %s" % (e["title"][:48], ", ".join(missing)))
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

    # same-day entries: date alone can't verify their relative order, so make
    # that ambiguity visible rather than silently passing it as "in order"
    date_counts = {}
    for d, _, t in dated:
        date_counts.setdefault(d, []).append(t)
    dup_dates = sorted(d for d, titles in date_counts.items() if len(titles) > 1)
    for d in dup_dates:
        titles = date_counts[d]
        rep.warn(
            "%d entries share date %s: relative order between them can't be "
            "verified by date alone -- %s"
            % (len(titles), d, "; ".join(t[:40] for t in titles))
        )

    # duplicate entries: the same decision logged (or indexed) more than once.
    # Checked before set-based matching below, because two identical entries
    # collapse to one set member and would otherwise look like perfect
    # agreement, exactly the gap an adversarial pass found: a real decision
    # copy-pasted twice passed as clean.
    from collections import Counter
    log_key_counts = Counter((e["date"], norm(e["title"])) for e in entries)
    # sort by (date-is-missing, date-or-empty, title) -- a plain sorted() on
    # (None, str) tuples crashes, since None and str aren't comparable. Found
    # by the adversarial benchmark: an entry with a malformed heading (no
    # real date) triggered this the moment duplicate-checking was added.
    for (d, t), n in sorted(log_key_counts.items(), key=lambda kv: (kv[0][0] is None, kv[0][0] or "", kv[0][1])):
        if n > 1:
            rep.fail("entry appears %d times in the log, should be once: [%s] %s" % (n, d, t[:60]))
    idx_key_counts = Counter(rows)
    for (d, t), n in sorted(idx_key_counts.items()):
        if n > 1:
            rep.fail("INDEX.md lists the same entry %d times, should be once: [%s] %s" % (n, d, t[:60]))

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

    # append anchor: must exist, AND nothing real may follow it. Checking only
    # for presence, not position, was itself a gap: an entry smuggled in below
    # the "add new entries above this line" marker parsed and indexed fine,
    # since nothing tied the anchor to where the file actually ends.
    anchor_idx = dtext.lower().find(APPEND_ANCHOR.lower())
    if anchor_idx == -1:
        rep.fail("append-only anchor missing -- add '<!-- %s ... -->' to guard ordering" % APPEND_ANCHOR)
    else:
        # find the actual close of the anchor's own HTML comment, not just the
        # end of the search phrase, otherwise the rest of the anchor's own
        # comment text (". Keep the oldest at the bottom. -->") gets mistaken
        # for smuggled content below it.
        close_idx = dtext.find("-->", anchor_idx)
        scan_from = close_idx + 3 if close_idx != -1 else anchor_idx + len(APPEND_ANCHOR)
        after_anchor = dtext[scan_from:].strip()
        if after_anchor:
            rep.fail(
                "content found BELOW the append-only anchor -- entries must be added "
                "above '%s', not after it: %r" % (APPEND_ANCHOR, after_anchor[:80])
            )
        else:
            rep.ok("append-only anchor present, nothing follows it")

    # leftover placeholder: check whether a REAL entry or index row's date is
    # literally the placeholder, not a blind substring search across the
    # whole file. A raw "PLACEHOLDER_DATE in dtext" check false-positives
    # the moment any entry's own prose merely MENTIONS "YYYY-MM-DD" (for
    # example, describing the placeholder convention itself, exactly what
    # happened here) -- found by this project's own log tripping its own
    # check, the same shape of bug as the nested-apex reserved-tag false
    # positive fixed earlier.
    placeholder_entry = any(e["date"] == PLACEHOLDER_DATE for e in entries)
    placeholder_row = any(d == PLACEHOLDER_DATE for d, _ in rows)
    if placeholder_entry or placeholder_row:
        rep.warn("example placeholder (%s) still present -- replace with a real first entry" % PLACEHOLDER_DATE)


REQUIRED_INDEX_SECTIONS = ("handoffs/", "domain buckets")


def check_index_sections(root, rep):
    rep.section("index structural sections")
    ipath = os.path.join(root, "memory", "INDEX.md")
    if not os.path.isfile(ipath):
        return
    itext = read(ipath)
    headings = set(
        m.group(1).strip().lower() for m in re.finditer(r"^##\s+(.*\S)\s*$", itext, re.M)
    )
    for name in REQUIRED_INDEX_SECTIONS:
        if name.lower() in headings:
            rep.ok("INDEX.md still documents '%s'" % name)
        else:
            rep.warn("INDEX.md is missing its '%s' section -- was it deleted or renamed?" % name)


def parse_handoff_rows(text):
    """Rows in the '## handoffs/' table. Convention: | Date | File | ~tokens |,
    where File is the exact filename in memory/handoffs/."""
    rows = []
    in_section = False
    for line in text.splitlines():
        if re.match(r"^##\s+handoffs/?\s*$", line.strip(), re.I):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if not in_section:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        first = cells[0]
        if ISO_DATE.match(first) or first == PLACEHOLDER_DATE:
            rows.append(cells[1])
    return rows


def check_handoffs(root, rep):
    """A real, pre-existing gap, found only after parse_index_rows stopped
    being scope-agnostic (see parse_index_table): this check used to bail
    out entirely the moment memory/handoffs/ had zero real files, before ever
    looking at whether INDEX.md's handoffs table claimed any anyway. A
    phantom row in that table (a file that was never real) went unchecked on
    its own terms in exactly that case, previously only caught by accident,
    because the old date-shaped-row parser didn't respect table boundaries
    and mistakenly attributed a handoffs-table phantom row to the decisions
    table's own phantom-detection instead. Now checked directly: phantom
    rows are flagged whether or not any real file exists; only a genuinely
    empty INDEX.md table with zero real files has nothing to report."""
    rep.section("handoffs (structural check)")
    hdir = os.path.join(root, "memory", "handoffs")
    ipath = os.path.join(root, "memory", "INDEX.md")
    if not os.path.isdir(hdir):
        print("  (no memory/handoffs/ directory -- skipped)")
        return
    real_files = sorted(
        fn for fn in os.listdir(hdir)
        if fn.lower() != "template.md"
        and not fn.startswith(".")
        and os.path.isfile(os.path.join(hdir, fn))
    )
    if not os.path.isfile(ipath):
        if real_files:
            rep.fail("real handoff files exist but memory/INDEX.md is missing")
        else:
            print("  (no real handoff files and no memory/INDEX.md -- skipped)")
        return
    indexed = parse_handoff_rows(read(ipath))
    if not real_files and not indexed:
        print("  (no real handoff files yet, and INDEX.md's handoffs table is empty -- skipped)")
        return
    real_set, idx_set = set(real_files), set(indexed)
    phantom = idx_set - real_set   # indexed, file doesn't exist
    missing = real_set - idx_set   # real file, not indexed
    if phantom:
        for f in sorted(phantom):
            rep.fail("INDEX.md handoffs table references a file that doesn't exist: %s" % f)
    if missing:
        for f in sorted(missing):
            rep.fail("real handoff file missing from INDEX.md's handoffs table: %s" % f)
    if not phantom and not missing:
        rep.ok("all %d real handoff file(s) are indexed, no phantoms, no gaps" % len(real_files))


INIT_EMBED_MAP = {
    "MOLT_VERIFY_PY": "molt-verify.py",
    "MOLT_CHAIN_APPEND_PY": "molt-chain-append.py",
    "MOLT_REDACT_PY": "molt-redact.py",
    "PRE_COMMIT_HOOK": os.path.join(".githooks", "pre-commit"),
    "CI_WORKFLOW_YML": os.path.join(".github", "workflows", "molt-verify.yml"),
    "SESSION_START_HOOK": os.path.join(".claude", "hooks", "molt-session-start.sh"),
    "SESSION_END_HOOK": os.path.join(".claude", "hooks", "molt-session-end.sh"),
}


def check_init_embed_consistency(root, rep):
    """molt-init.py is meant to work with nothing else present (see its own
    docstring): copy that one file anywhere and it bootstraps the whole
    setup. That only works because it carries its own base64 copies of
    molt-verify.py, molt-chain-append.py, molt-redact.py, the pre-commit
    hook, and the CI workflow instead of reading siblings at runtime. A
    carried copy is only trustworthy if it's kept in sync; this check
    decodes what molt-init.py actually embeds and compares it, byte for
    byte, against the real file, whenever this project's own repo (or
    anyone else's fork of it) has both molt-init.py and the real files
    checked out side by side. An adopter who only has molt-init.py, with
    none of the real siblings present, has nothing for this check to
    compare against, so it skips cleanly rather than failing on an absence
    that isn't drift."""
    rep.section("molt-init.py embed consistency")
    init_path = os.path.join(root, "molt-init.py")
    if not os.path.isfile(init_path):
        print("  (no molt-init.py in this root -- skipped, opt-in)")
        return
    init_text = read(init_path)
    any_sibling_present = any(
        os.path.isfile(os.path.join(root, rel)) for rel in INIT_EMBED_MAP.values()
    )
    if not any_sibling_present:
        print("  (molt-init.py present but none of its embedded siblings are -- "
              "nothing to compare, skipped)")
        return
    checked = 0
    drifted = 0
    for const_name, rel in INIT_EMBED_MAP.items():
        sibling_path = os.path.join(root, rel)
        if not os.path.isfile(sibling_path):
            continue
        m = re.search(
            r"%s_B64\s*=\s*\"\"\"\n(.*?)\n\"\"\"" % re.escape(const_name),
            init_text, re.S,
        )
        if not m:
            rep.fail("molt-init.py has no embedded %s_B64 block for %s -- "
                      "run scripts/build-molt-init.py" % (const_name, rel))
            drifted += 1
            continue
        try:
            embedded_bytes = base64.b64decode("".join(m.group(1).split()))
        except (ValueError, TypeError) as exc:
            rep.fail("molt-init.py's %s_B64 block for %s doesn't decode as base64: %s"
                      % (const_name, rel, str(exc)[:80]))
            drifted += 1
            continue
        with open(sibling_path, "rb") as f:
            real_bytes = f.read()
        checked += 1
        if embedded_bytes != real_bytes:
            rep.fail(
                "molt-init.py's embedded copy of %s is stale (doesn't byte-match the "
                "real file) -- run scripts/build-molt-init.py to resync" % rel
            )
            drifted += 1
    if checked and not drifted:
        rep.ok("molt-init.py's %d embedded file(s) byte-match their real siblings" % checked)


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
    for dirpath, _dirs, files in os.walk(mdir, followlinks=False):
        for fn in files:
            mpath = os.path.join(dirpath, fn)
            rel = os.path.relpath(mpath, mdir)
            if os.path.islink(mpath):
                rep.warn("mirror file is a symlink, skipped (could point outside the "
                         "intended tree): %s/%s" % (rel_mirror, rel))
                continue
            src = os.path.join(root, rel)
            checked += 1
            if not os.path.isfile(src):
                rep.fail("mirror has a file with no source counterpart: %s/%s" % (rel_mirror, rel))
                drift += 1
                continue
            try:
                same = read(src) == read(mpath)
            except (UnicodeDecodeError, OSError) as exc:
                # a mirror directory can hold anything; something that isn't
                # plain UTF-8 text (a binary file, a corrupt save) must not be
                # able to crash the whole audit. Report it as drift, not a
                # traceback. Found by testing common real-world breakage, not
                # a deliberate attack.
                rep.fail("could not compare mirror file against its source: %s (%s: %s)"
                         % (rel, exc.__class__.__name__, str(exc)[:80]))
                drift += 1
                continue
            if not same:
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

    # Every check below reads files this script doesn't control the contents
    # of. A tool whose entire job is to always deliver a verdict must not be
    # able to crash into a raw traceback instead of one, so any unexpected
    # failure inside a single check is caught, reported as drift, and the
    # remaining checks still run.
    checks = (
        check_merge_conflict_markers,
        check_apex_budget,
        check_agents_md,
        check_gitignore_sanity,
        check_nested_apex_consistency,
        check_decisions_and_index,
        check_token_efficiency,
        check_hash_chain,
        check_git_anchor,
        check_index_sections,
        check_handoffs,
        check_init_embed_consistency,
        lambda r, rp: check_mirror(r, rp, explicit_mirror),
    )
    for check in checks:
        try:
            check(root, rep)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, see comment above
            rep.fail("%s crashed instead of returning a verdict: %s: %s"
                     % (check.__name__ if hasattr(check, "__name__") else "a check",
                        exc.__class__.__name__, str(exc)[:120]))

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
