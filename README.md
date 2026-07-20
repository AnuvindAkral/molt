# 🦎 Molt

### The memory your AI agent can't fake.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#why-it-works-the-way-it-does)
[![Python 3, stdlib only](https://img.shields.io/badge/python-3%2C%20stdlib%20only-3776AB)](#why-it-works-the-way-it-does)
[![Self-auditing](https://img.shields.io/badge/self--auditing-43%2F43%20adversarial%20cases-success)](#the-part-nobody-else-does-it-tests-itself)
[![Works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Cowork%20%7C%20Cursor%20%7C%20Copilot%20%7C%20Aider-orange)](#works-with-whatever-you-already-use)

**Right now, your AI agent's memory is just something it tells you. There's no way to check if it's true. Molt fixes that: one command gives your agent a memory made of plain files, and a built-in checker that proves the memory is honest, in order, and hasn't been quietly changed.**

```sh
curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -
```

Copy that line. Paste it into a terminal, or straight into a Claude Code / Cowork session, in whatever folder your project lives in. Press enter. That's the entire setup. Keep reading for what you just got, in plain words.

---

## The problem, in one sentence

**AI agents forget things, or worse, they say they remember something that isn't true, and you have no way to check.**

Think about how this actually shows up:

- You spend an hour teaching your agent the quirks of your project. Tomorrow, or the moment you switch models, that hour is gone. You start over.
- You come back after a week off. A new session, maybe a new teammate. Nobody, and nothing, remembers what was decided or why.
- Your agent says "I already fixed that." Maybe it did. Maybe it's just confidently wrong. There is no button to press that tells you which.

None of this is really an "AI" problem. It's a **trust** problem: memory that can't be checked isn't memory, it's just a claim. Every other memory tool out there tries to make the claim bigger (more context, smarter search, fancier retrieval). Molt does something different: it makes the claim provable.

## What Molt actually does

It gives your AI agent memory made of plain text files on your own computer, not a database, not someone else's server. Then it hands you a small script that checks those files the way an auditor checks a ledger: does everything add up, is the order right, has anything been quietly rewritten. If yes, it says so clearly. If no, it fails loudly instead of staying quiet. That's the whole idea.

## See it for real

This is actual output from a real, fresh install. Nothing here is staged:

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

Every line that says `PASS` is a real check that ran against real files, not a model describing itself.

## Real situations this actually fixes

These aren't hypothetical. They're the exact reasons this exists.

**"I switched from one AI model to another and lost everything."** Your agent's understanding of your project lived inside a chat history tied to one model. Swap models, and it's gone. Molt keeps that understanding in files your next agent, on any model, reads on day one.

**"My agent keeps asking me things I already explained."** That's what happens when the answer only ever existed in a conversation that scrolled away. Molt puts the answer in a file the agent is supposed to check before asking again.

**"I came back to this project after a few weeks and had no idea where things stood."** One glance at `memory/INDEX.md` tells you, and any new agent session, exactly what was decided and why, without reading a single old chat log.

**"My agent told me it finished something, and it hadn't."** With Molt, real decisions get written down with the actual reasoning behind them, and a script checks that record hasn't been silently rewritten to match a story that isn't true.

**"Two of us (or two of our agents) are working on the same project and stepping on each other."** Two people, or two agent sessions, can add to the memory at the same time without a messy conflict. Molt is built so those additions merge cleanly instead of overwriting each other.

**"I want my whole team's AI agents to behave the same way, whatever tool each person uses."** One person's on Claude Code, another's on Cursor, a third's on Copilot. Molt keeps the same rules file byte-for-byte identical across all of them, automatically.

## Why this can be a genuine game changer

Not because it's clever. Because of what it removes: the need to just take your AI agent's word for it.

Right now, almost everyone using an AI coding agent has felt at least one of the moments above. Most people shrug and re-explain things, or quietly stop fully trusting what the agent tells them. Molt turns "trust me" into "check me." That's a small idea with a big effect once you've actually felt the alternative: an agent memory that's provably not lying is worth more than one that's merely bigger.

And the setup cost for that is one line pasted into a terminal. That gap, huge payoff, tiny effort, is exactly what makes something worth sharing with the next person who complains about their AI agent forgetting things.

## Zero to hero, in one command

You don't need to understand anything below this line to get the benefit. If you can copy and paste, you can set this up:

```sh
curl -fsSL https://raw.githubusercontent.com/AnuvindAkral/molt/main/molt-init.py | python3 -
```

That single line builds the entire system: the memory files, the checker script, a safety hook, a CI check, all of it, right there in your project. Then it runs the checker itself and tells you the result. No accounts, no signup, no dependency to install first.

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
└── memory/
    ├── INDEX.md                     a short table of what exists, cheap to read
    ├── decisions.md                 the real decision log, one honest reason per entry
    └── handoffs/                    notes for picking up a session where it left off
```

All of it comes from running one file, `molt-init.py`. Nothing else needs to exist first, that's the entire point of the one-liner above.

## The part nobody else does: it tests itself

`molt-verify.py` runs 13 checks: does the index match the log exactly, is every entry complete and in the right order, are there any leftover merge-conflict markers, do the cross-tool files still match, does the tamper-proof fingerprint chain (if you turned it on) still hold together, and more.

Here's the part that matters more than the list: this isn't just claimed, it's tested. There's a permanent set of **43 simulated attacks**, a faked fingerprint, a fake log entry, a forged date, a secretly edited backup copy, an unresolved merge conflict, and more, each one checked against exactly what the result should be, run at both a small scale and a scale of 3,000 entries. All 43 are caught, every time. Whenever a new problem gets found and fixed, it gets added permanently to this list, so it can never quietly come back.

Turn on the safety net so a mistake can't slip through:

```sh
git config core.hooksPath .githooks   # one-time setup, blocks a bad commit locally
# the GitHub Actions workflow already blocks a bad pull request automatically
```

## Why it works the way it does

**Rules and facts are kept separate.** `CLAUDE.md` only holds things that don't change, so it stays short. Everything that does change lives in `memory/`. Mixing the two is why most AI rules files eventually turn into a giant, unreadable wall of text.

**You never read the whole history just to check one thing.** `memory/INDEX.md` is a short table. You glance at it, then open only the one entry you actually need. This is the biggest reason Molt stays cheap to use even as the memory grows.

**Nothing gets secretly rewritten.** Old decisions never get edited, only added to. If something really does need to be removed later, there's a dedicated, honest tool for that (`molt-redact.py`) instead of quietly deleting history.

**It checks instead of assuming.** `molt-verify.py` proves the files agree with each other and haven't been tampered with. It doesn't just hope they're fine.

## The bug that made this real

This isn't a hypothetical worry. While building Molt, a hand-copied backup of the decision log picked up a sentence that never existed in the real one. It looked completely normal. It would have been believed. A simple byte-by-byte comparison caught it; just reading it over again had not. The rule that came out of that moment, never hand-edit a copy, always regenerate it and check it, is the whole philosophy of this project in one sentence: **good intentions drift. A check doesn't.**

## How it stacks up

| | a typical AI rules file | vector/graph-based memory tools | **Molt** |
|---|---|---|---|
| Survives switching models | sometimes | yes | **yes** |
| Setup effort | none | a database or paid service | **one command** |
| Extra software needed | none | usually a lot | **none, just Python** |
| Can prove it isn't lying to you | no | no | **yes** |
| Actually tested against fake corruption | no | rarely | **yes, 43 cases, two scales** |
| Easy for a human to read and fork | yes | rarely | **yes** |
| Built for thousands of long, fully autonomous agents | no | **yes** | no |

That last row matters: if you're running an enormous fleet of autonomous agents non-stop, you want a real database-backed memory system, not this. For everyone else, individuals, small teams, and startups who want to actually trust and read their AI agent's memory, this is built for exactly that.

## Works with whatever you already use

Claude Code, Cowork, Cursor, GitHub Copilot, Codex CLI, Gemini CLI, Aider, Windsurf, Zed, or anything else that reads a rules file at the root of your project. `CLAUDE.md` and `AGENTS.md` (the shared convention most of these tools already understand) are kept perfectly identical automatically, so switching tools never means losing your memory. It's just markdown files and one small Python script, nothing here locks you into any one company's product.

## Questions people actually ask

**Do I need to know git for this?** No. It works in a plain folder. If you happen to be using git, one extra safety check turns on by itself.

**Does any of my data leave my computer?** No. No network calls, no accounts, no tracking. Your files stay on your disk, and you can read the entire checking script yourself in about ten minutes.

**Is running the checker slow?** No, it reads a handful of small text files. It's instant.

**I already have a `CLAUDE.md`, will this overwrite it?** No. It reads what you already have and copies it, unchanged, into `AGENTS.md` so other tools see the same rules. Nothing you wrote gets lost.

**Can I skip the safety hook and CI check and just use the memory files?** Yes, both are optional extras. Skip them and everything else still works exactly the same.

## Want the deeper docs, or to look at the source?

The one-liner above is genuinely all you need to use Molt. If you'd rather read the full reasoning (`ARCHITECTURE.md`), the repeatable workflows (`PROTOCOLS.md`), or poke at the test suite yourself:

```sh
git clone https://github.com/AnuvindAkral/molt && cd molt
python3 molt-init.py /path/to/your/project
```

## Contributing

Issues and pull requests are welcome. The single most valuable thing you can do is try to trick `molt-verify.py` into saying everything's fine when it isn't. If you find a way, that's a real find, report it, or better, add it as a permanent test case so it protects everyone who uses this afterward. Full guide in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. Use it, fork it, rename it, take it apart, no credit required (though a star helps other people find it, which is the only reason to ask).

Built by [Anuvind Akral](https://github.com/AnuvindAkral).

---

<sub>**Repo description:** A self-verifying, dependency-free memory system for AI coding agents (Claude Code, Cursor, Copilot, Aider) that survives model changes and mechanically proves it isn't drifting, hallucinating, or lying. Tested against 43 adversarial attacks.</sub>

<sub>**Topics:** `claude-code` `claude` `ai-agents` `agent-memory` `cursor` `context-engineering` `llm` `llm-memory` `developer-tools` `cowork` `ai-coding-assistant` `prompt-engineering` `github-copilot` `aider` `windsurf` `open-source`</sub>
