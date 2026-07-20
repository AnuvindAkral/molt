#!/usr/bin/env python3
"""
molt-init -- one command to adopt Molt in an existing repo.

Without this, adopting Molt means manually copying molt-verify.py,
molt-chain-append.py, molt-redact.py, the pre-commit hook, the CI workflow,
CLAUDE.md/AGENTS.md, and hand-writing memory/INDEX.md and memory/decisions.md
before getting any value at all. That friction is real; this removes it.

What it does, in one run:
  - Copies the framework itself (molt-verify.py, molt-chain-append.py,
    molt-redact.py, ARCHITECTURE.md, CLAUDE.local.md.example) from this
    script's own directory into TARGET, unchanged -- these are the shared
    mechanism, not project-specific data, safe to reuse as-is.
  - Copies .githooks/pre-commit and .github/workflows/molt-verify.yml, so
    enforcement is opt-in-by-one-command from the start, not an afterthought.
  - Generates FRESH starter CLAUDE.md/AGENTS.md, memory/INDEX.md, and
    memory/decisions.md -- NOT copies of this project's own filled-in
    files. A brand-new adopter gets a clean, real example entry using the
    YYYY-MM-DD placeholder molt-verify.py already knows to warn about, not
    this project's entire decision history.
  - Ensures .gitignore protects CLAUDE.local.md/AGENTS.local.md without
    clobbering an existing .gitignore.
  - Never overwrites a file that already exists, unless --force is passed.
    Reports created vs. skipped so nothing is silently lost.
  - Runs molt-verify.py against TARGET at the end and prints the verdict,
    plus the one remaining manual step (git config core.hooksPath).

Usage:
    python3 molt-init.py TARGET_DIR [--force]

TARGET_DIR must already exist (an existing repo you're adopting Molt into,
or an empty directory for a fresh one). This script does not run `git init`
for you; that's your call to make, not this script's.
"""

import os
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Files copied verbatim from this script's own directory: the framework
# itself, identical across every adopter, not project-specific data.
COPY_FILES = (
    "molt-verify.py",
    "molt-chain-append.py",
    "molt-redact.py",
    "ARCHITECTURE.md",
    "CLAUDE.local.md.example",
    os.path.join(".githooks", "pre-commit"),
    os.path.join(".github", "workflows", "molt-verify.yml"),
)

CLAUDE_MD_TEMPLATE = """# CLAUDE.md — apex file
> Stable rules only. Target: under 300 lines. Read this every session.
> It should tell a brand-new model everything it needs to behave like the last one did.

<why_this_exists>
Models get deprecated, retired, or swapped for a better one. Whatever judgment, tone, or discipline you built up with one model cannot live only in that model's behavior, because it disappears when the model does. The fix: put the judgment in files. Any model reading these files should produce close to the same behavior, because the behavior is written down, not inferred from a specific model's defaults. And because a memory you can't trust is worse than none, the system verifies itself (see `<verification>`).
</why_this_exists>

<how_to_load_this>
This file auto-loads at your project root with Claude Code and Cowork. Most other coding agents (Cursor, GitHub Copilot, Codex CLI, Gemini CLI, Aider, Windsurf, Zed) instead auto-load a file named `AGENTS.md`, the open cross-tool convention as of 2026. Rather than keep two sets of rules, `AGENTS.md` in this project is a byte-identical copy of this file. Edit `CLAUDE.md`, never `AGENTS.md` directly; `molt-verify.py` fails if they drift apart. Load order, just-in-time, not all at once: this file first, always, then `memory/INDEX.md`'s table (titles and sizes only), then fetch only the one `memory/decisions.md` entry the current task actually needs. Reading `decisions.md` top to bottom by default is exactly the waste this ordering avoids.
</how_to_load_this>

<never>
- Fabricate a fact to fill a gap: a date, a preference, a number, a citation that hasn't actually been stated in these files or the current conversation. Say "I don't have that" instead.
- Silently pick one reading among several plausible ones. State the assumption out loud, or name the readings and ask.
- Rewrite or reorder an existing `memory/decisions.md` entry. A changed mind gets a NEW entry that supersedes the old one; the old one stays exactly as written.
- Edit a mirror by hand (if you keep one). Regenerate it from the source and verify, per `<verification>`.
</never>

<workflow>
- Ask before anything with real consequences (money, sending something, deleting something) if it isn't already obvious from context.
- State assumptions before acting on them. If more than one reading is plausible, name them rather than picking silently.
- When a real tradeoff exists, name the options and the reasoning; don't just pick.
</workflow>

<verification>
This system checks itself. `molt-verify.py` confirms the index matches the log, the log is newest-first and well-formed, and any mirror byte-matches its source. Run it after any change to `memory/` or the apex files, and before declaring work done. This is enforced, not just available: `git config core.hooksPath .githooks` (one-time, per clone) blocks any commit that drifts, and `.github/workflows/molt-verify.yml` blocks any PR that does. `git commit --no-verify` bypasses the local hook in a genuine emergency; CI still catches it.
</verification>

<domains>
Starting shape, not fixed. Add or remove a bucket in `memory/INDEX.md` as real use shows what actually recurs.
</domains>

<references>
Do NOT auto-load. Read only the one you actually need.

- `ARCHITECTURE.md` → only if asked "why is this built this way."
- `memory/INDEX.md` → always, second.
- `memory/decisions.md` → only the specific entry the index points you to.
- `memory/handoffs/` → only the one dated file for the thread being resumed.
</references>

<ponytail>
Before adding a new file, section, or rule, climb this ladder and stop at the first rung that holds: (1) does this need to exist at all, (2) does an existing file already cover it, extend it instead, (3) only then add the minimum that works.
</ponytail>

<before_declaring_done>
Before calling any change to this system finished: did a real decision get logged in `memory/decisions.md`; did `memory/INDEX.md`'s table get a matching row; did `molt-verify.py` pass.
</before_declaring_done>

<token_efficiency>
Progressive disclosure only works if the numbers it relies on are honest and the things it points to stay small. Keep a decision entry tight. `molt-verify.py` warns if an entry has grown past its verbosity budget, or if `memory/INDEX.md`'s `~tokens` estimate has drifted from the entry's real size.
</token_efficiency>

<memory_boundary>
This file holds stable rules only. Facts, decisions, and things that happened live in `memory/`. Promotion: a fact relevant for 6+ weeks becomes a rule here. Pruning: a rule that hasn't fired in 3 months gets removed. Review monthly.
</memory_boundary>
"""

INDEX_MD_TEMPLATE = """# Memory index

Read this whole file; it's the index, cheap by design. It shows what exists and its
approximate retrieval cost so a session can decide what to actually open, rather than
reading `decisions.md` top to bottom by default. (Progressive disclosure; see
`../CLAUDE.md`'s `<how_to_load_this>`.)

## decisions.md entries (newest first)

| Date | Type | Title | Gist | ~tokens |
|---|---|---|---|---|
| YYYY-MM-DD | build | Example: adopted Molt for this project's AI memory | Starter example entry; replace with your first real decision, then delete this row. | ~130 |

When this table and the log disagree, that's drift, and `molt-verify.py` will fail the
build until they agree again. Add one row here for every entry you append to the log.

## handoffs/

Empty except `TEMPLATE.md` (the shape; copy, don't edit). Add a row here the first time a
real handoff file exists. `molt-verify.py` cross-checks this table against the real files in
`memory/handoffs/` (excluding `TEMPLATE.md`); a file with no row, or a row with no file, fails.

| Date | File | ~tokens |
|---|---|---|

## domain buckets

Empty until real use fills them in. Add a short section per bucket as it becomes a real
recurring thing, with a one-line pointer to wherever its detail actually lives.

## lifecycle

Promotion: a fact or pattern relevant for 6+ weeks moves from here into a rule in `../CLAUDE.md`.
Pruning: a bucket or entry untouched for 3+ months gets reviewed for removal.
Review cadence: monthly.
"""

DECISIONS_MD_TEMPLATE = """# Decision log

> Append-only. Newest entry at top. Each entry: date, decision, reasoning, reversibility.
> Never rewrite or reorder an existing entry; a changed mind gets a new entry that supersedes the old one.
> This file ships with one example entry so you can see the shape. Replace it with your first real decision.

## YYYY-MM-DD · Example: adopted Molt for this project's AI memory
**Decision:** Adopted Molt, a self-verifying memory framework, so this project's AI agent stays consistent across sessions and model changes.
**Reasoning:** Replace this with the actual reasoning behind your first real decision -- why it was made, not just what was decided.
**Reversible:** Yes -- delete this file's content and Molt stops mattering, nothing else depends on it existing.
**Review:** Replace or delete this example entry once your first real decision is logged. `molt-verify.py` will keep warning about the YYYY-MM-DD placeholder until you do.

<!-- Add new entries above this line. Keep the oldest at the bottom. -->
"""

HANDOFF_TEMPLATE_MD = """# Handoff template

Copy this file, don't edit it. Name the copy YYYY-MM-DD-short-description.md.

## What was in progress

## What's done

## What's not done, and why

## Next step
"""

GITATTRIBUTES_ADDITION = "memory/decisions.md merge=union\n"


def log(msg):
    print(msg)


def copy_if_absent(src, dst, force):
    if os.path.isfile(dst) and not force:
        return "skipped (already exists)"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    # preserve exec bit for scripts/hooks that carry one
    src_mode = os.stat(src).st_mode
    if src_mode & stat.S_IXUSR:
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return "created"


def write_if_absent(path, content, force):
    if os.path.isfile(path) and not force:
        return "skipped (already exists)"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return "created"


def ensure_gitignore(target, force):
    path = os.path.join(target, ".gitignore")
    needed = ("CLAUDE.local.md", "AGENTS.local.md")
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(needed) + "\n")
        return "created"
    text = open(path, encoding="utf-8").read()
    missing = [n for n in needed if n not in text]
    if not missing:
        return "already protects CLAUDE.local.md/AGENTS.local.md"
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(missing) + "\n")
    return "appended %s" % ", ".join(missing)


def ensure_gitattributes(target, force):
    path = os.path.join(target, ".gitattributes")
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(GITATTRIBUTES_ADDITION)
        return "created (union-merge for memory/decisions.md, see decision log)"
    text = open(path, encoding="utf-8").read()
    if "memory/decisions.md" in text:
        return "already configured"
    with open(path, "a", encoding="utf-8") as f:
        f.write(GITATTRIBUTES_ADDITION)
    return "appended union-merge rule for memory/decisions.md"


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    target = os.path.abspath(argv[1])
    force = "--force" in argv[2:]

    if not os.path.isdir(target):
        print("TARGET_DIR does not exist: %s" % target)
        return 1

    report = []

    for rel in COPY_FILES:
        src = os.path.join(HERE, rel)
        if not os.path.isfile(src):
            report.append((rel, "SKIPPED -- not found next to molt-init.py (%s)" % src))
            continue
        dst = os.path.join(target, rel)
        report.append((rel, copy_if_absent(src, dst, force)))

    report.append(("CLAUDE.md", write_if_absent(os.path.join(target, "CLAUDE.md"), CLAUDE_MD_TEMPLATE, force)))
    # AGENTS.md must mirror whatever CLAUDE.md actually ends up containing,
    # not this script's own template: if CLAUDE.md already existed (a real
    # project adopting Molt into an existing repo, not a fresh one), writing
    # AGENTS.md from the template instead of the real CLAUDE.md content
    # guarantees instant drift, caught immediately by check_agents_md but
    # entirely avoidable. Found by testing this exact scenario, not by
    # inspection.
    claude_md_path = os.path.join(target, "CLAUDE.md")
    actual_claude_md = open(claude_md_path, encoding="utf-8").read()
    report.append(("AGENTS.md", write_if_absent(os.path.join(target, "AGENTS.md"), actual_claude_md, force)))
    report.append(("memory/INDEX.md", write_if_absent(os.path.join(target, "memory", "INDEX.md"), INDEX_MD_TEMPLATE, force)))
    report.append(("memory/decisions.md", write_if_absent(os.path.join(target, "memory", "decisions.md"), DECISIONS_MD_TEMPLATE, force)))
    report.append(("memory/handoffs/TEMPLATE.md", write_if_absent(os.path.join(target, "memory", "handoffs", "TEMPLATE.md"), HANDOFF_TEMPLATE_MD, force)))
    report.append((".gitignore", ensure_gitignore(target, force)))
    report.append((".gitattributes", ensure_gitattributes(target, force)))

    print("molt-init: scaffolding %s\n" % target)
    width = max(len(r[0]) for r in report)
    for name, status in report:
        print("  %-*s  %s" % (width, name, status))

    verify_path = os.path.join(target, "molt-verify.py")
    print("\n" + "-" * 60)
    if os.path.isfile(verify_path):
        proc = subprocess.run(
            [sys.executable, "molt-verify.py", "--no-color"],
            cwd=target, capture_output=True, text=True,
        )
        print(proc.stdout)
    else:
        print("molt-verify.py wasn't found at %s -- run this script from inside "
              "a Molt checkout so it has the framework files to copy." % HERE)

    print("-" * 60)
    print("Next steps:")
    print("  1. Replace the YYYY-MM-DD example entry in memory/decisions.md and memory/INDEX.md")
    print("     with your first real decision, once you have one.")
    print("  2. Review CLAUDE.md, it's a generic starting rule set, adjust it to fit your project.")
    if os.path.isdir(os.path.join(target, ".git")):
        print("  3. git config core.hooksPath .githooks   (one-time, makes molt-verify.py mandatory)")
    else:
        print("  3. Once this is a git repo: git config core.hooksPath .githooks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
