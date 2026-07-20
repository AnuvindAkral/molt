# 🦎 Molt

**The memory your AI agent can't fake.**

Molt is a tiny, portable memory system for AI coding agents (Claude Code, Cowork, Cursor, and anything else that reads a root rules file). It does two things nothing else does together:

1. **Survives model changes.** Your agent's judgment lives in plain files you own, not in one model's weights. When the model gets deprecated or swapped, you don't start over.
2. **Proves it isn't lying to you.** A dependency-free audit checks that the memory is internally consistent, append-only, and free of drift, and fails loudly when it isn't.

An agent memory you can't trust is worse than no memory, because you act on it. Every other agent-memory project competes on *capacity* (embeddings, graphs, retrieval). Molt competes on *trust*. That's the niche.

```
$ python3 molt-verify.py

=====================
  MOLT . self-audit
=====================
structure
  PASS found CLAUDE.md
  PASS found memory/INDEX.md
  PASS found memory/decisions.md
apex file
  PASS CLAUDE.md is 55 lines (budget 300)
memory: index <-> log
  PASS all 1 log entry is well-formed (Decision/Reasoning/Reversible/Review)
  PASS log is newest-first (1 dated entry)
  PASS index matches the log exactly (1 entry, no phantoms, no gaps)
  PASS append-only anchor present
mirror (drift catch)
  PASS all 3 mirrored file(s) byte-match their source
----------------------------------------------------
VERDICT: TRUSTWORTHY   9 pass / 0 warn / 0 fail
index, log, and mirror all tell the same story
```

## The one-command install, straight from GitHub

No cloning, no download step, nothing to fill in. Copy this straight off the repo page, paste it into a terminal (or a Claude Code / Cowork session), and run it right where you already are:

```sh
curl -fsSL https://raw.githubusercontent.com/<you>/molt/main/molt-init.py | python3 -
```

That's the whole setup. It pulls down `molt-init.py` and runs it immediately in the current directory, no path to type, nothing to check out first. It carries its own copies of everything Molt needs baked in, so this one command creates the whole system: the audit script, the memory files, the git hook, the CI workflow, all of it, then runs the audit and prints TRUSTWORTHY.

Want it set up somewhere else instead of the current directory? Add the path: `curl -fsSL ... | python3 - /path/to/your/project`.

## Cloning it instead

```sh
git clone https://github.com/<you>/molt && cd molt
./install.sh /path/to/your/project
```

That scaffolds the whole system into your project and runs the audit. No packages, no services, no API keys. If you have `python3`, you have everything Molt needs.

Prefer to do it by hand? Copy `CLAUDE.md`, `ARCHITECTURE.md`, `PROTOCOLS.md`, `molt-verify.py`, and the `memory/` folder into your repo root. Done.

## What's in the box

```
molt/
├── CLAUDE.md              apex rules — read every session, kept short on purpose
├── PROTOCOLS.md           the 5 repeatable moves: onboard, decide, hand off, verify, prune
├── ARCHITECTURE.md        why it's built this way (read on demand)
├── molt-verify.py         ⭐ the self-audit — the thing that makes the memory trustworthy
├── install.sh             one-command scaffolder
└── memory/
    ├── INDEX.md           progressive-disclosure index — cheap to read, tells you what to open
    ├── decisions.md       append-only decision log — read one entry at a time
    └── handoffs/
        └── TEMPLATE.md    copy this when a session ends mid-thread
```

Four concepts, and you already understand all of them.

## Why it's built the way it is

**Rules vs. state.** `CLAUDE.md` holds only rules that don't change, so it stays short and cheap to read every session. Everything that changes lives in `memory/`. Mixing the two is what makes most `CLAUDE.md` files balloon into thousand-line context hogs.

**Progressive disclosure.** You don't read the whole decision log every session. You read a one-line-per-entry index, then open only the entry you need. This is the single biggest token saver as your memory grows.

**Append-only truth.** Decisions are never rewritten, only superseded by newer entries. Your reasoning history stays intact and auditable.

**Verification, not hope.** `molt-verify.py` mechanically checks that the index matches the log, the log is well-formed and newest-first, and, if you keep a human-readable mirror (an Obsidian vault, a wiki), every mirrored file byte-matches its source. It exits non-zero on drift, so drop it in CI or a pre-commit hook:

```sh
# .git/hooks/pre-commit
python3 molt-verify.py || { echo "molt: drift detected, commit blocked"; exit 1; }
```

## The bug that made this real

The mirror check isn't hypothetical. While Molt was being built, a hand-written "mirror" copy of the decision log gained a sentence the real log never contained. It looked authoritative, so it would have been trusted. A byte-diff caught it; re-reading and assuming had not. The rule that came out of it, *never hand-edit a mirror, regenerate it from the source and verify*, is now enforced mechanically instead of remembered. That's the whole philosophy in one story: **good intentions drift; a check doesn't.**

## How it compares

| | typical `CLAUDE.md` | vector/graph agent memory | **Molt** |
|---|---|---|---|
| Survives a model swap | sometimes | yes | **yes** |
| Setup cost | none | database / service | **one file copy** |
| Dependencies | none | many | **none (stdlib Python)** |
| Detects its own drift / fabrication | no | no | **yes** |
| Readable & forkable by a human | yes | rarely | **yes** |
| Right at massive autonomous scale | no | **yes** | no |

Molt is deliberately the wrong tool if you're running thousands of long autonomous agent sessions, use a real graph- or embedding-backed memory then. It's the right tool for the enormous middle: individuals and small teams who want consistency they can trust and read.

## Use it with

Any agent that reads a root instructions file: **Claude Code**, **Cowork**, **Cursor**, and similar. The memory layer and the audit are just files and one stdlib script, so nothing is locked to a single vendor.

## FAQ

**Do I need the Obsidian mirror?** No. It's opt-in. The audit skips the mirror check entirely if there's no mirror folder. If you do keep one, Molt is what keeps it honest.

**Does this send my data anywhere?** No. No network, no telemetry, no accounts. It's your files on your disk.

**Is `molt-verify.py` slow?** It reads a handful of markdown files. It's instant.

## License

MIT. Use it, fork it, rename it, gut it, no attribution required (though a star is appreciated).

Built by Anuvind Akral.

---

<sub>Suggested repo description: *A tiny, dependency-free memory system for AI coding agents that survives model changes and audits itself for drift.* &nbsp; Topics: `claude-code` `claude` `ai-agents` `agent-memory` `cursor` `context-engineering` `llm` `developer-tools` `cowork`</sub>
