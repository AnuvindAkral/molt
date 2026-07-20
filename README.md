# 🦎 Molt

### The memory your AI agent can't fake.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#why-it-works-the-way-it-does)
[![Self-auditing](https://img.shields.io/badge/self--auditing-43%2F43%20adversarial%20cases-success)](#the-part-nobody-else-does-it-tests-itself)
[![Works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Cursor%20%7C%20Copilot%20%7C%20Aider-orange)](#works-with-whatever-you-already-use)
[![Token-efficient](https://img.shields.io/badge/token%20use-minimal%2C%20by%20default-blueviolet)](#why-it-works-the-way-it-does)

**Right now, your AI agent's memory is just something it tells you. There's no way to check if it's true. Molt fixes that: one command gives your agent a memory made of plain files, and a built-in checker that proves the memory is honest, in order, and hasn't been quietly changed.**

```sh
curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -
```

Copy that line. Paste it into a terminal, or straight into a Claude Code / Cowork session, in whatever folder your project lives in. Press enter. That's the entire setup, no accounts, no signup, nothing else to install first.

> **Full disclosure:** this is my first-ever public GitHub project. It also has 13 mechanical checks and 43 tests that try to break it on purpose. I skipped "hello world" and went straight to "prove it." No regrets.

---

## The problem, in one sentence

**AI agents forget things, or worse, they say they remember something that isn't true, and you have no way to check.** You spend an hour teaching your agent your project's quirks, then switch models and lose it. You come back after a break and nothing remembers what was decided or why. Your agent says "I already fixed that," maybe it did, maybe it's confidently wrong, and there's no button that tells you which.

That's not really an AI problem, it's a **trust** problem: memory that can't be checked isn't memory, it's just a claim. Every other agent-memory tool tries to make the claim bigger (more context, smarter search). Molt makes the claim provable instead: plain text files on your own computer, checked the way an auditor checks a ledger, not hoped to be fine.

## See it for real

Actual output from a fresh install, nothing here is staged:

```
$ curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -

molt-init: scaffolding .
  molt-verify.py, molt-chain-append.py, molt-redact.py    created
  .githooks/pre-commit, .github/workflows/molt-verify.yml  created
  CLAUDE.md, AGENTS.md, memory/INDEX.md, memory/decisions.md  created

============================
  MOLT . self-audit
============================
structure                          PASS  found CLAUDE.md, memory/INDEX.md, memory/decisions.md
merge conflict markers             PASS  no unresolved markers
memory: index <-> log              PASS  index matches the log exactly, no phantoms, no gaps
token efficiency                   PASS  every index estimate is honest
molt-init.py embed consistency     PASS  embedded copies byte-match the real files
----------------------------------------------------
VERDICT: TRUSTWORTHY (with notes)   14 pass / 1 warn / 0 fail
```

Every `PASS` above ran against real files. Not a model describing itself and hoping you don't ask follow-up questions.

## Who this is for, and what it actually fixes

This isn't only a fresh-start tool. It works the same way whether you installed your AI agent five minutes ago or you've had Claude Code, Cursor, or Copilot running on this project for months.

**If you just picked up Claude, Cursor, or any AI coding tool:** most people set one up with nothing, hit the usual pain weeks later (re-explaining things, losing context, not trusting what it says), then go looking for a fix. Run this first and skip that whole phase, your day-one setup is already the good one.

**If you've been using one of these tools for a while already:** dropping Molt in today doesn't erase anything. It reads your existing `CLAUDE.md` if you have one and never overwrites it, so the months of rules you've already written stay exactly as they are, they just get memory and a checker added on top, retroactively.

**Either way,** here's what it actually fixes, day one or day two hundred:

- Switched models and lost all your project context? Molt keeps it in files any model reads on day one.
- Agent keeps re-asking things you already explained? That answer now lives in a file it's supposed to check first.
- Came back after weeks away with no idea where things stood? One glance at `memory/INDEX.md` tells you.
- Agent claimed it finished something it hadn't? Real decisions get logged with real reasoning, and a script proves the log wasn't quietly rewritten to match a story that isn't true.
- Two people (or two agent sessions) editing memory at once? It merges cleanly instead of a conflict.

Not because the engineering is clever. Because it removes the need to just take your agent's word for it, the same way you'd take a coworker's word for it, except this coworker can't actually remember Tuesday and will say so with total confidence anyway. That's "trust me" turned into "check me," for the cost of one pasted command.

## What's actually in the box

```
your-project/
├── CLAUDE.md                        the rules your AI agent reads every session
├── AGENTS.md                        the same rules, identical, for every other tool
├── molt-verify.py                   ⭐ the checker: 13 tests, zero dependencies
├── molt-chain-append.py             adds tamper-proof fingerprints to entries (opt-in)
├── molt-redact.py                   the proper way to remove something sensitive
├── .githooks/pre-commit             stops a bad commit before it happens
├── .github/workflows/molt-verify.yml   stops a bad pull request before it merges
├── .claude/hooks/                   Claude Code only: auto-runs the checker each session
├── .claude/settings.json            registers those two hooks, merges into yours if you have one
└── memory/
    ├── INDEX.md                     a short table of what exists, cheap to read
    ├── decisions.md                 the real decision log, one honest reason per entry
    └── handoffs/                    notes for picking up a session where it left off
```

All of it comes from running one file, `molt-init.py`, which carries its own copies of everything baked in. Nothing else needs to exist first, that's the entire point of the one-liner above.

## The part nobody else does: it tests itself

`molt-verify.py` runs 13 checks: index-vs-log agreement, well-formed and ordered entries, no leftover merge-conflict markers, cross-tool files staying identical, a tamper-proof fingerprint chain (if you turn it on), and more.

This isn't just claimed, it's tested: a permanent set of **43 simulated attacks** (a faked fingerprint, a fake log entry, a forged date, a secretly edited backup, an unresolved merge conflict, and more), each checked against exactly what the result should be, run at both a small scale and 3,000 entries. All 43 are caught, every time. Every real bug found gets added permanently to this list so it can't quietly come back.

```sh
git config core.hooksPath .githooks   # one-time, blocks a bad commit locally
# the GitHub Actions workflow already blocks a bad pull request automatically
```

**If you use Claude Code specifically**, `molt-init.py` also registers a `SessionStart` and a `SessionEnd` hook in `.claude/settings.json`, so `molt-verify.py` runs automatically at the beginning and end of every session, not only at commit time. If it finds drift, Claude sees a warning before you even ask it anything. This is Claude Code's own hook mechanism, so it's specific to Claude Code, it does nothing for Cursor, Copilot, or any other tool; the pre-commit hook and CI workflow above are the parts that actually work everywhere. It never overwrites hooks you already have configured, it merges in alongside them.

## Why it works the way it does

**Rules and facts are kept separate.** `CLAUDE.md` only holds things that don't change, so it stays short. Everything that changes lives in `memory/`, which is why most AI rules files don't balloon into unreadable walls of text here.

**Low token use isn't a setting, it's the default.** You never read the whole history to check one thing: `memory/INDEX.md` is a short table, you open only the one entry you actually need. This isn't just a suggestion either, `molt-verify.py` mechanically checks that INDEX.md's size estimates are honest and that no single entry has quietly grown past its budget, so the system can't drift into being expensive without you finding out.

**Nothing gets secretly rewritten.** Old decisions never get edited, only added to. `molt-redact.py` is the honest, sanctioned way to remove something later.

**It checks instead of assuming.** `molt-verify.py` proves the files agree with each other. It doesn't hope they're fine.

## The bug that made this real

While building Molt, a hand-copied backup of the decision log picked up a sentence that never existed in the real one. It looked completely normal. It would have been believed, confidently, by everyone, forever. A byte-by-byte comparison caught it; re-reading it had not, which is exactly the point. The rule that came out of it, never hand-edit a copy, regenerate and check it, is the whole philosophy in one sentence: **good intentions drift. A check doesn't.**

## How it stacks up

| | a typical AI rules file | vector/graph-based memory tools | **Molt** |
|---|---|---|---|
| Survives switching models | sometimes | yes | **yes** |
| Setup cost | none | a database or paid service | **one command, no dependencies** |
| Can prove it isn't lying to you | no | no | **yes** |
| Tested against fake corruption | no | rarely | **yes, 43 cases, two scales** |
| Built for thousands of autonomous agents | no | **yes** | not the goal |

That last row is honest, not modest: for a huge fleet of autonomous agents, use a real database-backed system. Adding one would mean giving up the zero dependencies and plain markdown files that make the rest of this table true. For individuals, small teams, and startups who want memory they can actually read and trust, this is built for exactly that. The fuller reasoning, including where the line actually gets drawn against tools that do chase that scale, is in [SCALE-SPEC.md](SCALE-SPEC.md).

## Works with whatever you already use

Claude Code, Cowork, Cursor, GitHub Copilot, Codex CLI, Gemini CLI, Aider, Windsurf, Zed, or anything that reads a rules file at the root of a project. `CLAUDE.md` and `AGENTS.md` stay identical automatically, so switching tools never means losing your memory. It's markdown files and one small Python script, nothing here locks you to one vendor.

## Questions people actually ask

**Do I need git?** No. If you are using git, one extra safety check turns on by itself.

**Does any data leave my computer?** No. No network calls, no accounts, no tracking.

**Is the checker slow?** No, it reads a handful of small text files. Instant.

**I already have a `CLAUDE.md`, will this overwrite it?** No, it copies your existing one into `AGENTS.md` unchanged.

**Can I skip the git hook / CI and just use the memory files?** Yes, both are optional extras.

**Is this really your first GitHub project?** Yes. Figured if I was going to jump in, I might as well build something whose entire job is catching me if I get something wrong. Good policy for a first project, or honestly any project.

## Want the deeper docs, or to look at the source?

The one-liner above is genuinely all you need to use Molt. For the full reasoning (`ARCHITECTURE.md`), the repeatable workflows (`PROTOCOLS.md`), or the test suite itself:

```sh
git clone https://github.com/AnuvindAkral/molt && cd molt
python3 molt-init.py /path/to/your/project
```

## Contributing

Issues and pull requests welcome. The single most valuable thing you can do is try to trick `molt-verify.py` into saying everything's fine when it isn't. Found a way? Report it, or better, add it as a permanent test case. Full guide in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. Use it, fork it, rename it, take it apart, no credit required (though a star helps other people find it, which is the only reason to ask).

Built by [Anuvind Akral](https://github.com/AnuvindAkral), repo #1. If you're reading this and it's still standing, the 43 tests did their job.

---

<sub>**Repo description:** A self-verifying, dependency-free memory system for AI coding agents (Claude Code, Cursor, Copilot, Aider) that survives model changes and mechanically proves it isn't drifting, hallucinating, or lying. Tested against 43 adversarial attacks.</sub>

<sub>**Topics:** `claude-code` `claude` `ai-agents` `agent-memory` `cursor` `context-engineering` `llm` `llm-memory` `developer-tools` `cowork` `ai-coding-assistant` `prompt-engineering` `github-copilot` `aider` `windsurf` `open-source`</sub>
