# 🦎 Molt

### The memory your AI agent can't fake.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#why-its-built-the-way-it-is)
[![Python 3, stdlib only](https://img.shields.io/badge/python-3%2C%20stdlib%20only-3776AB)](#why-its-built-the-way-it-is)
[![Self-auditing](https://img.shields.io/badge/self--auditing-43%2F43%20adversarial%20cases-success)](#the-part-nobody-else-does-it-tests-itself)
[![Works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Cowork%20%7C%20Cursor%20%7C%20Copilot%20%7C%20Aider-orange)](#use-it-with)

**One command. Zero dependencies. Your AI agent (Claude Code, Cursor, Copilot, whatever you use) remembers everything, correctly, forever, and proves it isn't lying about it.**

```sh
curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -
```

Copy that. Paste it into a terminal, or straight into a Claude Code / Cowork session, wherever your project lives. Hit enter. You now have a memory system for your AI agent that survives model swaps, never silently drifts, and audits itself for tampering, hallucination, and lies. Nothing else to install. Read on for what that actually means, in plain English.

---

## The problem this solves

You've been working with an AI coding agent for weeks. It knows your codebase's quirks, the decisions you made and why, the conventions your team settled on. Then one of these happens:

- **The model gets upgraded or swapped.** All that accumulated context lives in one model's weights and conversation history. New model, new session: you're explaining everything from scratch again.
- **You come back after a break.** A week off, a new teammate, a new agent session. Nobody remembers what was decided or why, and nothing forces the agent to check.
- **Your agent tells you it "already handled that."** Maybe it did. Maybe it's confidently wrong. There's no way to check, because nothing about most agent memory is verifiable, it's just text the model asserts is true.

Molt fixes all three. It puts your agent's judgment into plain text files you own (not a database, not a vendor's servers), and it comes with a built-in checker that mechanically proves those files are internally consistent, in order, and haven't been quietly altered. If something's wrong, it fails loudly instead of staying quiet.

Every other AI-memory project competes on **capacity**: bigger context windows, vector search, knowledge graphs. Molt competes on **trust**: a memory you can actually believe. That's a different, and mostly unaddressed, problem.

## See it run

This is real output from a fresh install, not a mockup:

```
$ curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -

molt-init: scaffolding .
  molt-verify.py                     created
  molt-chain-append.py               created
  molt-redact.py                     created
  .githooks/pre-commit               created
  .github/workflows/molt-verify.yml  created
  CLAUDE.md                          created
  AGENTS.md                          created
  memory/INDEX.md                    created
  memory/decisions.md                created
  memory/handoffs/TEMPLATE.md        created
  .gitignore                         created
  .gitattributes                     created

============================
  MOLT . self-audit
============================
structure                          PASS  found CLAUDE.md, memory/INDEX.md, memory/decisions.md
merge conflict markers             PASS  no unresolved markers
apex file                          PASS  CLAUDE.md is 56 lines (budget 300)
cross-tool file (AGENTS.md)        PASS  byte-matches CLAUDE.md
gitignore sanity                   PASS  no shared file accidentally excluded
memory: index <-> log              PASS  index matches the log exactly, no phantoms, no gaps
token efficiency                   PASS  every index estimate is honest
hash chain (tamper-evidence)       (opt-in, skipped until adopted)
git anchor (local tamper check)    (opt-in, skipped until this is a git repo)
molt-init.py embed consistency     PASS  embedded copies byte-match the real files
----------------------------------------------------
VERDICT: TRUSTWORTHY (with notes)   14 pass / 1 warn / 0 fail
```

Every `PASS` above is a real, mechanical check, not a model's opinion of itself.

## Who this is for (zero to hero, no jargon)

You don't need to know what a hash chain or an append-only log is to get value from this. If any of these sound like you, Molt is for you:

- **"I just started using Claude Code / Cursor / Copilot and want it to actually remember things."** Run the one-liner above in your project. Done, you have memory now.
- **"My AI agent keeps re-asking things I already told it."** That's because the answer lived in a chat window, not a file. Molt moves it into a file the agent reads every session.
- **"I switched models (or my team uses different tools) and lost all context."** Molt's files are plain markdown, read natively by Claude Code and Cowork, and mirrored automatically for Cursor, Copilot, Aider, Windsurf, Zed, and Gemini CLI. Switch tools, keep your memory.
- **"I don't trust that my agent actually did what it says it did."** Every real decision gets logged with its reasoning, and a script proves the log wasn't quietly edited or contradicted later.
- **"I'm on a team and we all use AI agents on the same repo."** Molt handles two people (or two agent sessions) appending memory at the same time without a manual merge fight, and blocks a commit that would corrupt the log.

You go from a brand-new Claude/Cursor setup to a fully verified, tamper-evident memory system in one command. Zero to hero, one paste.

## What's actually in the box

```
your-project/
├── CLAUDE.md                        the rules Claude Code / Cowork read every session
├── AGENTS.md                        the same rules, byte-identical, for every other tool
├── molt-verify.py                   ⭐ the self-audit: 13 checks, zero dependencies
├── molt-chain-append.py             adds tamper-evident hashes to new entries (opt-in)
├── molt-redact.py                   the sanctioned way to remove sensitive content
├── .githooks/pre-commit             blocks a commit if the audit fails
├── .github/workflows/molt-verify.yml   blocks a PR if the audit fails
└── memory/
    ├── INDEX.md                     cheap-to-read table of what exists (progressive disclosure)
    ├── decisions.md                 append-only decision log, one real reason per entry
    └── handoffs/                    session handoff notes, only opened when resuming one
```

Everything above gets created by the single `molt-init.py` script, which carries its own copies of all of it baked in. No other file needs to exist first; that's the whole point of the one-liner.

## The part nobody else does: it tests itself

`molt-verify.py` runs 13 mechanical checks: the index matches the log exactly, entries are well-formed and newest-first, no merge-conflict markers snuck into a commit, cross-tool files stay byte-identical, a hash chain (if adopted) verifies unbroken from genesis to newest, a local git-anchor check flags a rewritten history before it's committed over, and more.

This isn't asserted, it's proven with a permanent adversarial benchmark: **43 simulated attacks and corruptions** (a tampered hash, a phantom log entry, a forged date, a stealthily edited mirror, an unresolved merge conflict, a stale embedded copy, and more), each checked against the exact expected verdict, at both small and large scale (300 and 3,000 synthetic entries). All 43 pass. Every time this project adds a feature, it adds the adversarial case that would have caught the bug that motivated it.

Wire the audit in so drift can't sneak past you:

```sh
git config core.hooksPath .githooks   # blocks a bad commit locally, one-time setup
# .github/workflows/molt-verify.yml already blocks a bad PR in CI
```

## Why it's built the way it is

**Rules vs. state.** `CLAUDE.md` holds only rules that don't change, so it stays short and cheap to read every session. Everything that changes lives in `memory/`. Mixing the two is what makes most `CLAUDE.md` files balloon into thousand-line context hogs.

**Progressive disclosure.** You don't read the whole decision log every session. You read a one-line-per-entry index, then open only the entry you actually need. This is the single biggest token saver as your memory grows.

**Append-only truth.** Decisions are never rewritten, only superseded by newer entries. Your reasoning history stays intact and auditable, and there's a sanctioned tool (`molt-redact.py`) for the one legitimate case where something really does need to come out.

**Verification, not hope.** `molt-verify.py` mechanically checks that the index matches the log, the log is well-formed and newest-first, the hash chain (if adopted) is unbroken, and, if you keep a human-readable mirror (an Obsidian vault, a wiki), every mirrored file byte-matches its source. It exits non-zero on drift.

## The bug that made this real

The mirror check isn't hypothetical. While Molt was being built, a hand-written "mirror" copy of the decision log gained a sentence the real log never contained. It looked authoritative, so it would have been trusted. A byte-diff caught it; re-reading and assuming had not. The rule that came out of it, *never hand-edit a mirror, regenerate it from the source and verify*, is now enforced mechanically instead of remembered. That's the whole philosophy in one story: **good intentions drift; a check doesn't.**

## How it compares

| | typical `CLAUDE.md` | vector/graph agent memory | **Molt** |
|---|---|---|---|
| Survives a model swap | sometimes | yes | **yes** |
| Setup cost | none | database / service | **one command** |
| Dependencies | none | many | **none (stdlib Python)** |
| Detects its own drift / fabrication | no | no | **yes, mechanically** |
| Tested against adversarial corruption | no | rarely | **yes, 43 cases, two scales** |
| Readable & forkable by a human | yes | rarely | **yes** |
| Right at massive autonomous scale (thousands of long-running sessions) | no | **yes** | no |

Molt is deliberately the wrong tool if you're running thousands of long autonomous agent sessions; use a real graph- or embedding-backed memory then. It's the right tool for the enormous middle: individuals, teams, and startups who want AI-agent memory they can actually read, trust, and check.

## Use it with

Any agent that reads a root instructions file: **Claude Code**, **Cowork**, **Cursor**, **GitHub Copilot**, **Codex CLI**, **Gemini CLI**, **Aider**, **Windsurf**, **Zed**, or anything else in the growing list of AI coding agents. `CLAUDE.md` and `AGENTS.md` (the open cross-tool convention) are kept byte-identical automatically, so switching tools doesn't mean losing memory. Nothing here is locked to one vendor: it's markdown files and one stdlib Python script.

## FAQ

**Do I need git for this?** No. Everything works in a plain folder. If you *are* in a git repo, one extra check (the local tamper-evidence anchor) turns on automatically.

**Does this send my data anywhere?** No. No network calls, no telemetry, no accounts, no API keys. It's your files, on your disk, checked by a script you can read top to bottom in ten minutes.

**Is `molt-verify.py` slow?** It reads a handful of markdown files. It's instant.

**What if I already have a `CLAUDE.md`?** The installer won't overwrite it. It reads your existing file and mirrors it into `AGENTS.md`, so nothing you've already written gets lost.

**I don't want the git hook / CI enforcement, just the memory files.** That's fine, both are optional add-ons; skip `git config core.hooksPath` and don't add the workflow file, and everything else still works.

## Want the deep-dive docs, or to browse/contribute to the source?

The one-liner above is all you need to *use* Molt. If you want the full rationale (`ARCHITECTURE.md`), the repeatable workflows (`PROTOCOLS.md`), or to poke at the adversarial benchmark yourself:

```sh
git clone https://github.com/AnuvindAkral/molt && cd molt
python3 molt-init.py /path/to/your/project   # same installer, run from a full checkout
```

## Contributing

Issues and PRs welcome. If you find a way to fool `molt-verify.py`, that's the most valuable bug report you can file, add it as a permanent adversarial case in `benchmarks/adversarial/run.py` and it protects everyone who adopts Molt afterward.

## License

MIT. Use it, fork it, rename it, gut it, no attribution required (though a star is appreciated, it's how other people find this).

Built by [Anuvind Akral](https://github.com/AnuvindAkral).

---

<sub>**Repo description:** A self-verifying, dependency-free memory system for AI coding agents (Claude Code, Cursor, Copilot, Aider) that survives model changes and mechanically proves it isn't drifting, hallucinating, or lying, tested against 43 adversarial attacks.</sub>

<sub>**Topics:** `claude-code` `claude` `ai-agents` `agent-memory` `cursor` `context-engineering` `llm` `llm-memory` `developer-tools` `cowork` `ai-coding-assistant` `prompt-engineering` `github-copilot` `aider` `windsurf` `open-source`</sub>
