#!/usr/bin/env python3
"""
adversarial benchmark -- proves molt-verify.py's trust claim, doesn't just assume it.

Builds a synthetic decision log at scale, injects one known corruption per case
(each mirroring a real failure mode), and asserts molt-verify.py's exit code and
verdict match what's expected: FAIL for every corrupted case, PASS for the clean
control. This is item 5 of ../../SCALE-SPEC.md, made permanent and re-runnable
instead of a one-off manual pass. If someone reverts a fail-vs-warn severity
change by accident, or a future edit to molt-verify.py's parser breaks a check,
this is what catches it before the real project's log does.

No dependencies beyond Python stdlib. No network. Nothing here touches the real
molt/ project; everything runs in a temp directory and is cleaned up after,
unless --keep is passed.

Usage:
    python3 benchmarks/adversarial/run.py [--n 300] [--keep] [--no-color]

Exit code 0 = every case behaved exactly as expected (the trust claim holds).
Exit code 1 = at least one case did not behave as expected (the trust claim
              has a hole; that's the finding, not a bug in this script).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOLT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))  # molt/
VERIFY_SCRIPT = os.path.join(MOLT_ROOT, "molt-verify.py")
CLAUDE_MD = os.path.join(MOLT_ROOT, "CLAUDE.md")

TITLES = [
    "Adopted append-only log for decision {i}",
    "Reworked onboarding protocol, pass {i}",
    "Pruned a stale rule from CLAUDE.md, round {i}",
    "Split a domain bucket into two, iteration {i}",
    "Fixed a mirror drift caught by audit, case {i}",
]


def entry_block(date, title, idx):
    return (
        "## %s · %s\n"
        "**Decision:** Synthetic decision body number %d for benchmark purposes, kept short.\n"
        "**Reasoning:** Synthetic reasoning body number %d, exists only to give molt-verify.py real text to parse.\n"
        "**Reversible:** Yes, this is synthetic data, entry %d.\n"
        "**Review:** Revisit if this synthetic entry ever needs to mean something, entry %d.\n"
    ) % (date, title, idx, idx, idx, idx)


def build_synthetic_root(n):
    """Create a temp Molt root with CLAUDE.md, molt-verify.py, and an n-entry
    memory/ that molt-verify.py should judge TRUSTWORTHY, unmodified."""
    root = tempfile.mkdtemp(prefix="molt-adversarial-")
    os.makedirs(os.path.join(root, "memory"))
    shutil.copy(VERIFY_SCRIPT, os.path.join(root, "molt-verify.py"))
    shutil.copy(CLAUDE_MD, os.path.join(root, "CLAUDE.md"))

    import datetime
    start = datetime.date(2025, 1, 1)
    entries = []
    for i in range(n):
        d = start + datetime.timedelta(days=i)
        title = TITLES[i % len(TITLES)].format(i=i)
        entries.append((d.isoformat(), title))
    entries_desc = list(reversed(entries))  # newest first

    log_lines = ["# Decision log\n", "> Synthetic benchmark log, append-only, newest first.\n\n"]
    real_tokens = []  # per-entry estimate matching molt-verify.py's own formula,
                       # so the INDEX.md ~tokens column starts honest instead of
                       # a flat guess that would itself trip check_token_efficiency
                       # on a supposedly clean control case
    for i, (date, title) in enumerate(entries_desc):
        block = entry_block(date, title, i)
        log_lines.append(block)
        log_lines.append("\n")
        body = block.split("\n", 1)[1] if "\n" in block else ""
        real_tokens.append(round(len(body.split()) * 1.35))
    log_lines.append("<!-- Add new entries above this line. Keep the oldest at the bottom. -->\n")
    with open(os.path.join(root, "memory", "decisions.md"), "w", encoding="utf-8") as f:
        f.writelines(log_lines)

    index_lines = ["# Memory index\n\n", "| Date | Type | Title | ~tokens |\n", "|---|---|---|---|\n"]
    for (date, title), tok in zip(entries_desc, real_tokens):
        index_lines.append("| %s | build | %s | ~%d |\n" % (date, title, tok))
    # empty handoffs table + domain buckets heading, mirroring the real project's
    # convention, so check_index_sections and check_handoffs have something to check
    index_lines.append("\n## handoffs/\n\n")
    index_lines.append("| Date | File | ~tokens |\n")
    index_lines.append("|---|---|---|\n")
    index_lines.append("\n## domain buckets\n\nEmpty until real use fills them in.\n")
    with open(os.path.join(root, "memory", "INDEX.md"), "w", encoding="utf-8") as f:
        f.writelines(index_lines)

    os.makedirs(os.path.join(root, "memory", "handoffs"))
    with open(os.path.join(root, "memory", "handoffs", "TEMPLATE.md"), "w", encoding="utf-8") as f:
        f.write("# Handoff template\n\nCopy this file, don't edit it.\n")

    return root


# ---------------------------------------------------------------- injectors
def inject_phantom_index_row(root):
    p = os.path.join(root, "memory", "INDEX.md")
    with open(p, "a", encoding="utf-8") as f:
        f.write("| 2099-01-01 | build | Entry that does not exist in the log | ~50 |\n")


def inject_missing_index_row(root):
    p = os.path.join(root, "memory", "INDEX.md")
    lines = open(p, encoding="utf-8").readlines()
    del lines[6]  # first real data row after the 3-line header
    open(p, "w", encoding="utf-8").writelines(lines)


def inject_out_of_order_entry(root):
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    blocks = re.split(r"(?=^## )", text, flags=re.M)
    blocks[1], blocks[2] = blocks[2], blocks[1]  # swap the two newest entries
    open(p, "w", encoding="utf-8").write("".join(blocks))


def inject_malformed_entry(root):
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    text2, count = re.subn(r"\*\*Reversible:\*\* [^\n]*\n", "", text, count=1)
    assert count == 1, "adversarial injector itself is broken: no Reversible field found to strip"
    open(p, "w", encoding="utf-8").write(text2)


def inject_missing_anchor(root):
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    anchor = "<!-- Add new entries above this line. Keep the oldest at the bottom. -->\n"
    assert anchor in text, "adversarial injector itself is broken: anchor not found"
    open(p, "w", encoding="utf-8").write(text.replace(anchor, ""))


def inject_mirror_drift(root):
    mdir = os.path.join(root, "mirror", "memory")
    os.makedirs(mdir)
    src = os.path.join(root, "memory", "decisions.md")
    dst = os.path.join(mdir, "decisions.md")
    shutil.copy(src, dst)
    text = open(dst, encoding="utf-8").read()
    needle = "Synthetic reasoning body number 0, exists only to give molt-verify.py real text to parse.\n"
    replacement = needle.rstrip("\n") + ", plus a sentence the real log never contained.\n"
    assert needle in text, "adversarial injector itself is broken: needle text not found in entry 0"
    open(dst, "w", encoding="utf-8").write(text.replace(needle, replacement, 1))


def inject_heading_in_body(root):
    """Not a real corruption: pastes a '## '-looking line mid-paragraph inside
    an entry's own Reasoning field, with no blank line before it. A correct
    parser must NOT read this as a new entry. This is the regression test for
    the parser fragility found while building this benchmark: the old parser
    would have split here, silently turning one real entry into two."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    needle = "**Reasoning:** Synthetic reasoning body number 0, exists only to give molt-verify.py real text to parse.\n"
    assert needle in text, "adversarial injector itself is broken: needle text not found"
    replacement = needle + "## This looks like a heading but it is not one, no blank line precedes it.\n"
    open(p, "w", encoding="utf-8").write(text.replace(needle, replacement, 1))


def inject_homoglyph_date_separator(root):
    """Swap the real middle dot (·, U+00B7) for a visually similar lookalike
    (∙, U+2219 BULLET OPERATOR) in one entry's heading. Should still be caught,
    just via a date/title mismatch, since the split on '·' silently fails and
    the entry's date becomes None."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    blocks = re.split(r"(?=^## )", text, flags=re.M)
    m = re.match(r"^(## [0-9]{4}-[0-9]{2}-[0-9]{2}) · (.*)", blocks[2])
    assert m, "adversarial injector itself is broken: couldn't find second entry heading"
    blocks[2] = blocks[2].replace(m.group(0), "%s ∙ %s" % (m.group(1), m.group(2)), 1)
    open(p, "w", encoding="utf-8").write("".join(blocks))


def inject_zero_width_title(root):
    """Insert an invisible zero-width space (U+200B) into one INDEX.md title,
    so it reads identically to a human but differs from the log by one
    character no one can see."""
    p = os.path.join(root, "memory", "INDEX.md")
    text = open(p, encoding="utf-8").read()
    needle = TITLES[0].format(i=0)
    assert needle in text, "adversarial injector itself is broken: title not found"
    parts = needle.split(" ", 1)
    poisoned = parts[0] + "​ " + parts[1]
    text2 = text.replace(needle, poisoned, 1)
    assert text2 != text
    open(p, "w", encoding="utf-8").write(text2)


def inject_duplicate_entry(root):
    """Copy-paste an entire real entry a second time, with a matching
    duplicated index row. The exact same decision, logged twice. Set-based
    matching alone can't see this: two identical entries collapse to one
    set member and look like perfect agreement."""
    dpath = os.path.join(root, "memory", "decisions.md")
    ipath = os.path.join(root, "memory", "INDEX.md")
    dtext = open(dpath, encoding="utf-8").read()
    blocks = re.split(r"(?=^## )", dtext, flags=re.M)
    blocks.insert(2, blocks[1])
    open(dpath, "w", encoding="utf-8").write("".join(blocks))

    itext = open(ipath, encoding="utf-8").read()
    lines = itext.splitlines(keepends=True)
    header_end = 4  # title, blank, column header, separator -> first data row
    lines.insert(header_end, lines[header_end])
    open(ipath, "w", encoding="utf-8").writelines(lines)


def inject_fullwidth_digit_date(root):
    """Insert a forged entry at the very top whose date is built from
    full-width Unicode digits (１２３...), which satisfy a naive \\d{4}-\\d{2}-\\d{2}
    check but sort as a completely different string than real ASCII dates,
    letting a forged entry always compare as 'newest' regardless of position."""
    dpath = os.path.join(root, "memory", "decisions.md")
    ipath = os.path.join(root, "memory", "INDEX.md")
    dtext = open(dpath, encoding="utf-8").read()
    fake_date = "２０２６-０７-２０"  # looks like 2026-07-20
    fake = (
        "## %s · Forged newest entry using lookalike digits\n"
        "**Decision:** Forged.\n**Reasoning:** Forged.\n**Reversible:** Yes.\n**Review:** None.\n\n"
    ) % fake_date
    marker = "# Decision log\n> Synthetic benchmark log, append-only, newest first.\n\n"
    assert marker in dtext, "adversarial injector itself is broken: header marker not found"
    open(dpath, "w", encoding="utf-8").write(dtext.replace(marker, marker + fake, 1))

    itext = open(ipath, encoding="utf-8").read()
    idx_marker = "| Date | Type | Title | ~tokens |\n|---|---|---|---|\n"
    assert idx_marker in itext, "adversarial injector itself is broken: index header not found"
    fake_row = "| %s | build | Forged newest entry using lookalike digits | ~50 |\n" % fake_date
    open(ipath, "w", encoding="utf-8").write(itext.replace(idx_marker, idx_marker + fake_row, 1))


def inject_entry_below_anchor(root):
    """Smuggle a real-looking entry in below the append-only anchor, the
    exact marker that says 'add new entries above this line.' Nothing
    previously tied that anchor to actually being the last thing in the file."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    anchor = "<!-- Add new entries above this line. Keep the oldest at the bottom. -->\n"
    assert anchor in text, "adversarial injector itself is broken: anchor not found"
    smuggled = (
        "\n## 2020-01-01 · Smuggled entry placed below the append-only anchor\n"
        "**Decision:** Smuggled.\n**Reasoning:** Smuggled.\n**Reversible:** Yes.\n**Review:** None.\n"
    )
    open(p, "w", encoding="utf-8").write(text.replace(anchor, anchor + smuggled, 1))


def inject_agents_md_drift(root):
    """AGENTS.md (the cross-tool convention read by Cursor, Copilot, Codex
    CLI, Gemini CLI, Aider, Windsurf, Zed) exists but has drifted from
    CLAUDE.md, meaning those tools would see different rules than Claude
    Code/Cowork does."""
    cpath = os.path.join(root, "CLAUDE.md")
    apath = os.path.join(root, "AGENTS.md")
    shutil.copy(cpath, apath)
    with open(apath, "a", encoding="utf-8") as f:
        f.write("\nSomeone hand-edited AGENTS.md without touching CLAUDE.md.\n")


def inject_nested_memory_named_dir_shadow(root):
    """A real domain subdirectory happens to be named "memory" (e.g. a
    caching subsystem), NOT Molt's own root memory/, and contains a genuine
    reserved-tag violation. This must not be silently skipped just because
    it shares a name with the root's special directory."""
    d = os.path.join(root, "packages", "memory")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(
            "# packages/memory/CLAUDE.md\n\n"
            "<never>\n- Should be caught even though this dir is named 'memory'.\n</never>\n"
        )


def inject_nested_apex_correct(root):
    """Not a corruption: a domain subdirectory gets its own CLAUDE.md and
    AGENTS.md, byte-identical to each other, adding domain-specific rules
    without redeclaring any root-only tag. Should pass clean."""
    d = os.path.join(root, "backend")
    os.makedirs(d, exist_ok=True)
    content = "# backend/CLAUDE.md\n\nBackend-specific note, mentions `<never>` in prose only, not as a section.\n"
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(content)
    with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write(content)


def inject_nested_apex_reserved_tag(root):
    """A nested CLAUDE.md actually redeclares <never> as its own section,
    not just mentioning it in prose, which could silently weaken the root's
    shared governance for anyone reading only the domain file."""
    d = os.path.join(root, "backend")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("# backend/CLAUDE.md\n\n<never>\n- Redeclaring this for real, not just mentioning it.\n</never>\n")


def inject_nested_apex_pair_drift(root):
    """A domain directory keeps both CLAUDE.md and AGENTS.md, but they've
    drifted apart, so cross-tool agents in that directory see different
    rules than Claude Code does."""
    d = os.path.join(root, "backend")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("# backend/CLAUDE.md\n\nOriginal note.\n")
    with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write("# backend/AGENTS.md\n\nA different, drifted note.\n")


def inject_local_apex_correct(root):
    """Not a corruption: a personal CLAUDE.local.md exists and is correctly
    excluded by .gitignore. Should pass clean."""
    with open(os.path.join(root, ".gitignore"), "a", encoding="utf-8") as f:
        f.write("\nCLAUDE.local.md\n")
    with open(os.path.join(root, "CLAUDE.local.md"), "w", encoding="utf-8") as f:
        f.write("# personal preferences, correctly ignored\n")


def inject_local_apex_leak(root):
    """A personal CLAUDE.local.md exists but nothing excludes it from git --
    personal preferences could get committed and shared with the team."""
    with open(os.path.join(root, "CLAUDE.local.md"), "w", encoding="utf-8") as f:
        f.write("# personal preferences, forgot to gitignore this\n")


def inject_gitignore_excludes_shared(root):
    """.gitignore accidentally excludes memory/, the single most common real
    mistake with the shared-vs-personal apex convention: the team's rules
    silently stop syncing."""
    with open(os.path.join(root, ".gitignore"), "a", encoding="utf-8") as f:
        f.write("\nmemory/\n")


def inject_agents_md_correct(root):
    """Not a corruption: AGENTS.md added as a correct, byte-identical copy of
    CLAUDE.md. Should pass clean, proving the good path works, not just the
    failure path."""
    shutil.copy(os.path.join(root, "CLAUDE.md"), os.path.join(root, "AGENTS.md"))


def inject_binary_file_in_mirror(root):
    """Not an attack on the data, an attack on the script's own robustness: a
    mirror directory can hold anything, and a binary file dropped into it
    used to crash the whole audit with an unhandled UnicodeDecodeError
    instead of reporting a clean failure. Found via common breakage, not
    deliberate adversarial construction."""
    mdir = os.path.join(root, "mirror", "memory")
    os.makedirs(mdir, exist_ok=True)
    with open(os.path.join(mdir, "decisions.md"), "wb") as f:
        f.write(bytes(range(256)) * 4)


def inject_same_day_entries(root):
    """Two entries share a date. Not a corruption, an unenforceable ambiguity:
    date alone can't verify their relative order. Should surface as a warning,
    not pass silently as if order were confirmed."""
    dpath = os.path.join(root, "memory", "decisions.md")
    ipath = os.path.join(root, "memory", "INDEX.md")
    dtext = open(dpath, encoding="utf-8").read()
    itext = open(ipath, encoding="utf-8").read()

    blocks = re.split(r"(?=^## )", dtext, flags=re.M)
    m1 = re.match(r"^## (\d{4}-\d{2}-\d{2}) · ", blocks[1])
    m2 = re.match(r"^## (\d{4}-\d{2}-\d{2}) · ", blocks[2])
    assert m1 and m2, "adversarial injector itself is broken: couldn't find two dated entries"
    newest_date, second_date = m1.group(1), m2.group(1)
    blocks[2] = blocks[2].replace("## %s ·" % second_date, "## %s ·" % newest_date, 1)
    open(dpath, "w", encoding="utf-8").write("".join(blocks))

    marker = "| %s |" % second_date
    assert marker in itext, "adversarial injector itself is broken: index row not found"
    open(ipath, "w", encoding="utf-8").write(itext.replace(marker, "| %s |" % newest_date, 1))


CHAIN_APPEND_SCRIPT = os.path.join(MOLT_ROOT, "molt-chain-append.py")


def build_chained_synthetic_root(n):
    """A synthetic root identical to build_synthetic_root(n), but with every
    entry's hash-chain field backfilled, so the hash-chain tests have a real,
    valid chain to tamper with, instead of an empty control."""
    root = build_synthetic_root(n)
    proc = subprocess.run(
        [sys.executable, CHAIN_APPEND_SCRIPT, root],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        "adversarial benchmark itself is broken: molt-chain-append.py failed "
        "while building the chained base root:\n%s\n%s" % (proc.stdout, proc.stderr)
    )
    return root


def _git(root, *args):
    proc = subprocess.run(
        ["git"] + list(args), cwd=root, capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        "adversarial benchmark itself is broken: git %s failed in %s:\n%s\n%s"
        % (" ".join(args), root, proc.stdout, proc.stderr)
    )
    return proc


def build_chained_git_synthetic_root(n):
    """A chained root (see build_chained_synthetic_root), additionally a real
    git repository with everything committed. This is the base for the
    git-anchor check (item 9), the local, best-effort mitigation for the
    CRITICAL finding in this project's own security review: a hash chain
    alone can be laundered by stripping hashes and regenerating them, this
    check catches that specific attack as long as it hasn't been committed."""
    root = build_chained_synthetic_root(n)
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=bench@test.local", "-c", "user.name=bench",
         "commit", "-q", "-m", "baseline, chain intact")
    return root


def inject_git_anchor_laundering_attack(root):
    """The exact CRITICAL attack from this project's own security review,
    reproduced here as a permanent regression case: tamper the OLDEST
    entry's Decision text, strip every entry's Hash field (not just the
    tampered one), then regenerate the whole chain with molt-chain-append.py.
    The hash chain re-verifies clean (that's the vulnerability); this case
    exists to prove check_git_anchor catches it anyway, as long as it hasn't
    been committed yet -- which it hasn't, in this test."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    needle = "Synthetic decision body number 0 for benchmark purposes, kept short."
    assert needle in text, "adversarial injector itself is broken: oldest entry's Decision text not found"
    text = text.replace(needle, "TAMPERED BY ATTACKER. " + needle, 1)
    text = re.sub(r"\*\*Hash:\*\* [0-9a-f]{64}\n", "", text)
    open(p, "w", encoding="utf-8").write(text)
    proc = subprocess.run(
        [sys.executable, CHAIN_APPEND_SCRIPT, root], capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        "adversarial injector itself is broken: molt-chain-append.py failed while "
        "laundering the tampered chain:\n%s\n%s" % (proc.stdout, proc.stderr)
    )


def inject_git_anchor_legitimate_addition(root):
    """Not a corruption: a real new entry added on top (the normal workflow),
    hashed, uncommitted. check_git_anchor must NOT flag this, since flagging
    every ordinary new entry before its first commit would make the check
    useless noise instead of a real signal.

    The new entry's date must be strictly newer than every existing synthetic
    entry regardless of --n, or this injector creates an unrelated newest-
    first-ordering failure that has nothing to do with git-anchor and makes
    the case fail for the wrong reason. Found at n=3000 with an earlier,
    hardcoded date that was newest only up to a few hundred entries."""
    import datetime
    dpath = os.path.join(root, "memory", "decisions.md")
    ipath = os.path.join(root, "memory", "INDEX.md")
    dtext = open(dpath, encoding="utf-8").read()
    existing_dates = re.findall(r"^## ([0-9]{4}-[0-9]{2}-[0-9]{2}) · ", dtext, re.M)
    assert existing_dates, "adversarial injector itself is broken: no dated entries found"
    newest_existing = max(datetime.date.fromisoformat(d) for d in existing_dates)
    new_date = (newest_existing + datetime.timedelta(days=1)).isoformat()

    first_heading = re.search(r"^##\s+\S.*$", dtext, re.M)
    assert first_heading, "adversarial injector itself is broken: no entry heading found"
    new_entry = (
        "## %s · A legitimate new entry added on top, not yet committed\n"
        "**Decision:** Real.\n**Reasoning:** Real.\n**Reversible:** Yes.\n**Review:** None.\n\n"
    ) % new_date
    insert_at = first_heading.start()
    dtext2 = dtext[:insert_at] + new_entry + dtext[insert_at:]
    open(dpath, "w", encoding="utf-8").write(dtext2)

    itext = open(ipath, encoding="utf-8").read()
    marker = "| Date | Type | Title | ~tokens |\n|---|---|---|---|\n"
    assert marker in itext, "adversarial injector itself is broken: index header not found"
    row = "| %s | build | A legitimate new entry added on top, not yet committed | ~30 |\n" % new_date
    open(ipath, "w", encoding="utf-8").write(itext.replace(marker, marker + row, 1))

    proc = subprocess.run(
        [sys.executable, CHAIN_APPEND_SCRIPT, root], capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        "adversarial injector itself is broken: molt-chain-append.py failed while "
        "hashing the new legitimate entry:\n%s\n%s" % (proc.stdout, proc.stderr)
    )


def inject_hash_chain_tamper(root):
    """Alter the OLDEST entry's Decision text after it's already been hashed.
    Should break the chain from that point forward, catching tampering that a
    mirror-less setup would otherwise never detect."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    needle = "Synthetic decision body number 0 for benchmark purposes, kept short."
    assert needle in text, "adversarial injector itself is broken: oldest entry's Decision text not found"
    text2 = text.replace(needle, "Tampered after hashing. " + needle, 1)
    assert text2 != text
    open(p, "w", encoding="utf-8").write(text2)


def inject_hash_chain_incomplete(root):
    """Remove the Hash field from one middle entry only, leaving the rest
    intact. A partially-adopted chain should fail, not silently pass the
    entries that do have hashes."""
    p = os.path.join(root, "memory", "decisions.md")
    lines = open(p, encoding="utf-8").readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("**Hash:**"):
            del lines[i]
            break
    else:
        raise AssertionError("adversarial injector itself is broken: no Hash line found to remove")
    open(p, "w", encoding="utf-8").writelines(lines)


def inject_index_token_drift(root):
    """The FIRST entry's INDEX.md ~tokens estimate is forced down to ~5,
    far below its real size. Progressive disclosure relies on this number
    being honest; a session deciding "cheap to open" based on a lie defeats
    the whole point. Found via direct measurement against this project's own
    INDEX.md, not suspicion: every existing estimate was 30-50% low before
    this check existed. Uses a regex on the first data row rather than a
    hardcoded value, since build_synthetic_root now computes a real,
    per-entry estimate instead of a flat placeholder."""
    p = os.path.join(root, "memory", "INDEX.md")
    text = open(p, encoding="utf-8").read()
    text2, count = re.subn(r"(\| Date \| Type \| Title \| ~tokens \|\n\|---\|---\|---\|---\|\n\|[^\n]*\| )~[0-9]+( \|)",
                            r"\1~5\2", text, count=1)
    assert count == 1, "adversarial injector itself is broken: no first data row found to alter"
    assert text2 != text
    open(p, "w", encoding="utf-8").write(text2)


def inject_oversized_entry(root):
    """One entry's Decision field balloons past the verbosity budget. Not a
    correctness problem (still well-formed, still hashable), a token-cost
    problem: progressive disclosure stops paying off once a single lookup
    costs hundreds of extra tokens nobody accounted for."""
    p = os.path.join(root, "memory", "decisions.md")
    text = open(p, encoding="utf-8").read()
    needle = "Synthetic decision body number 0 for benchmark purposes, kept short."
    assert needle in text, "adversarial injector itself is broken: needle not found"
    padding = " Extra padding word." * 400
    text2 = text.replace(needle, needle + padding, 1)
    assert text2 != text
    open(p, "w", encoding="utf-8").write(text2)


def inject_gitignore_negation_pattern(root):
    """.gitignore contains a '!' negation pattern, which check_gitignore_sanity
    deliberately does not evaluate (a real gitignore engine is a large
    addition for a narrow edge case). Should surface as a WARN, loud enough
    to prompt a human to check by hand, not fail silently or fail the build."""
    with open(os.path.join(root, ".gitignore"), "a", encoding="utf-8") as f:
        f.write("\n!CLAUDE.md\n")


def inject_phantom_handoff_row(root):
    """Add a row to INDEX.md's handoffs table pointing at a file that doesn't
    exist in memory/handoffs/."""
    p = os.path.join(root, "memory", "INDEX.md")
    text = open(p, encoding="utf-8").read()
    marker = "| Date | File | ~tokens |\n|---|---|---|\n"
    assert marker in text, "adversarial injector itself is broken: handoffs table header not found"
    text2 = text.replace(marker, marker + "| 2026-07-20 | 2026-07-20-nonexistent.md | ~50 |\n", 1)
    open(p, "w", encoding="utf-8").write(text2)


def inject_missing_handoff_row(root):
    """Create a real handoff file with no corresponding INDEX.md row."""
    hdir = os.path.join(root, "memory", "handoffs")
    with open(os.path.join(hdir, "2026-07-20-untracked-session.md"), "w", encoding="utf-8") as f:
        f.write("# Handoff, 2026-07-20\n\nReal file, deliberately not indexed.\n")


CASES_PLAIN = "plain"
CASES_CHAINED = "chained"
CASES_CHAINED_GIT = "chained_git"

CASES = [
    ("control_clean", None, 0, "TRUSTWORTHY", CASES_PLAIN),
    ("phantom_index_row", inject_phantom_index_row, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("missing_index_row", inject_missing_index_row, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("out_of_order_entry", inject_out_of_order_entry, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("malformed_entry_missing_field", inject_malformed_entry, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("missing_append_anchor", inject_missing_anchor, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("mirror_drift", inject_mirror_drift, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("heading_in_body_not_new_entry", inject_heading_in_body, 0, "TRUSTWORTHY", CASES_PLAIN),
    ("phantom_handoff_row", inject_phantom_handoff_row, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("missing_handoff_row", inject_missing_handoff_row, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("same_day_entries", inject_same_day_entries, 0, "TRUSTWORTHY (with notes)", CASES_PLAIN),
    ("homoglyph_date_separator", inject_homoglyph_date_separator, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("zero_width_title", inject_zero_width_title, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("duplicate_entry", inject_duplicate_entry, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("fullwidth_digit_date", inject_fullwidth_digit_date, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("entry_below_anchor", inject_entry_below_anchor, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("binary_file_in_mirror", inject_binary_file_in_mirror, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("agents_md_correct", inject_agents_md_correct, 0, "TRUSTWORTHY", CASES_PLAIN),
    ("agents_md_drift", inject_agents_md_drift, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("hash_chain_control", None, 0, "TRUSTWORTHY", CASES_CHAINED),
    ("hash_chain_tamper", inject_hash_chain_tamper, 1, "DRIFT DETECTED", CASES_CHAINED),
    ("hash_chain_incomplete", inject_hash_chain_incomplete, 1, "DRIFT DETECTED", CASES_CHAINED),
    ("local_apex_correct", inject_local_apex_correct, 0, "TRUSTWORTHY", CASES_PLAIN),
    ("local_apex_leak", inject_local_apex_leak, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("gitignore_excludes_shared", inject_gitignore_excludes_shared, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("nested_apex_correct", inject_nested_apex_correct, 0, "TRUSTWORTHY", CASES_PLAIN),
    ("nested_apex_reserved_tag", inject_nested_apex_reserved_tag, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("nested_apex_pair_drift", inject_nested_apex_pair_drift, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("nested_memory_named_dir_shadow", inject_nested_memory_named_dir_shadow, 1, "DRIFT DETECTED", CASES_PLAIN),
    ("gitignore_negation_pattern", inject_gitignore_negation_pattern, 0, "TRUSTWORTHY (with notes)", CASES_PLAIN),
    ("index_token_drift", inject_index_token_drift, 0, "TRUSTWORTHY (with notes)", CASES_PLAIN),
    ("oversized_entry", inject_oversized_entry, 0, "TRUSTWORTHY (with notes)", CASES_PLAIN),
    ("git_anchor_control_committed", None, 0, "TRUSTWORTHY", CASES_CHAINED_GIT),
    ("git_anchor_laundering_attack", inject_git_anchor_laundering_attack, 1, "DRIFT DETECTED", CASES_CHAINED_GIT),
    ("git_anchor_legitimate_addition", inject_git_anchor_legitimate_addition, 0, "TRUSTWORTHY", CASES_CHAINED_GIT),
]


def run_case(base_root, name, injector, expected_exit, expected_verdict_substr, keep):
    case_root = tempfile.mkdtemp(prefix="molt-case-%s-" % name)
    shutil.rmtree(case_root)
    shutil.copytree(base_root, case_root)
    if injector is not None:
        injector(case_root)

    proc = subprocess.run(
        [sys.executable, "molt-verify.py", "--no-color"],
        cwd=case_root,
        capture_output=True,
        text=True,
    )
    verdict_line = next((l for l in proc.stdout.splitlines() if l.startswith("VERDICT:")), "")
    passed = (proc.returncode == expected_exit) and (expected_verdict_substr in verdict_line)

    if not keep:
        shutil.rmtree(case_root, ignore_errors=True)
    return passed, proc.returncode, verdict_line, case_root if keep else None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=300, help="number of synthetic decision entries (default 300)")
    ap.add_argument("--keep", action="store_true", help="keep temp case directories for inspection")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args(argv[1:])

    color = not args.no_color and sys.stdout.isatty()

    def c(code, s):
        return ("\033[%sm%s\033[0m" % (code, s)) if color else s

    print(c("1", "===================================="))
    print(c("1", "  MOLT . adversarial benchmark"))
    print(c("1", "===================================="))
    print("synthetic entries: %d" % args.n)
    print("verify script:     %s" % VERIFY_SCRIPT)

    base_root = build_synthetic_root(args.n)
    chained_root = build_chained_synthetic_root(args.n)
    chained_git_root = build_chained_git_synthetic_root(args.n)
    bases = {CASES_PLAIN: base_root, CASES_CHAINED: chained_root, CASES_CHAINED_GIT: chained_git_root}
    try:
        results = []
        for name, injector, expected_exit, expected_verdict, which_base in CASES:
            passed, code, verdict_line, kept_dir = run_case(
                bases[which_base], name, injector, expected_exit, expected_verdict, args.keep
            )
            results.append((name, passed, code, verdict_line, kept_dir))
    finally:
        shutil.rmtree(base_root, ignore_errors=True)
        shutil.rmtree(chained_root, ignore_errors=True)
        shutil.rmtree(chained_git_root, ignore_errors=True)

    print("\n%-32s %-6s %-6s %s" % ("CASE", "OK?", "EXIT", "VERDICT"))
    print("-" * 80)
    all_ok = True
    for name, passed, code, verdict_line, kept_dir in results:
        tag = c("32", "PASS") if passed else c("31", "FAIL")
        if not passed:
            all_ok = False
        print("%-32s %-6s %-6d %s" % (name, tag, code, verdict_line))
        if kept_dir:
            print("    kept at: %s" % kept_dir)

    print("-" * 80)
    if all_ok:
        print(c("32", "BENCHMARK PASSED") + ": every case behaved exactly as expected. The trust claim held at n=%d." % args.n)
        return 0
    else:
        print(c("31", "BENCHMARK FAILED") + ": at least one case did not behave as expected.")
        print("This means molt-verify.py has a real gap, not that this script is broken.")
        print("Do not paper over it: fix molt-verify.py, then re-run this benchmark.")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
