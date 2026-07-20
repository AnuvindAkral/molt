# Molt, architecture

## The name

When an animal molts, it sheds the shell it has outgrown and keeps the organism inside. The new shell is soft and vulnerable at first, so the moult only works if what emerges is sound. That's the whole design in one word: your agent sheds models (the shell) and keeps its judgment (the organism), and the system verifies that what emerges is sound rather than assuming it.

## Why this exists

Models get deprecated, retired, replaced, or swapped for a better one. Whatever felt right about working with a specific model, its tone, its judgment, the way it handled ambiguity, cannot live only inside that model, because it disappears with the model. The fix is to move judgment out of the model and into files: a short apex file for rules that don't change, and a memory layer for facts that do. Any model reading these files should produce close to the same behavior, because the behavior is written down, not inferred from one model's defaults.

## What makes it different, specifically

Most agent-memory projects compete on capacity: embeddings, vector stores, graph databases, retrieval pipelines, background summarizers. Those are the right tools when an agent runs thousands of long autonomous sessions. Molt is built for the far more common case, a person or small team who wants their agent to stay consistent, and who wants that consistency to survive a model change, and it competes on a different axis entirely: trust. It is the memory that proves it isn't lying to you.

That guarantee is not a promise, it's a script. `molt-verify.py` mechanically checks that the index matches the log, the log is append-only and well-formed, and any human-readable mirror byte-matches its source. It has no dependencies, so nothing it relies on can itself rot.

## The split

- **`CLAUDE.md`**: stable rules only. Read every session, kept short so that's cheap.
- **`PROTOCOLS.md`**: the repeatable procedures (onboard, decide, hand off, verify, prune). Read the one you need.
- **`memory/`**: everything that changes. Facts, decisions and why, per-session handoffs. Append-only where it matters (`decisions.md`), so nothing gets silently rewritten.
- **`molt-verify.py`**: the auditor that makes the above trustworthy instead of merely hopeful.

## Progressive disclosure

Don't read `memory/decisions.md` top to bottom by default. Read `memory/INDEX.md` first, a table of each entry's date, type, title, and approximate token cost, then open only the one entry the task needs. At a handful of entries this barely matters; past 15-20 it's the difference between a cheap lookup and re-reading a growing file every session. Re-check the tradeoff as entries accumulate; don't keep the index out of habit if reading the whole log is genuinely still cheaper.

## Tool independence, concretely

Model independence and tool independence are different problems that look
similar. A model can read `CLAUDE.md` regardless of which model it is; the
open question was whether the *tool* around that model auto-loads a file with
that exact name. Claude Code and Cowork do. Cursor, GitHub Copilot, Codex CLI,
Gemini CLI, Aider, Windsurf, and Zed instead converged on `AGENTS.md` as the
open cross-tool convention as of 2026. Rather than keep two sets of rules that
can quietly drift, `AGENTS.md` is a byte-identical copy of `CLAUDE.md`, using
the exact mechanism the mirror check already proved: `molt-verify.py` fails if
the two files stop matching. Edit `CLAUDE.md`; regenerate `AGENTS.md` from it,
never the reverse.

## Nested apex files, for monorepos

A domain subdirectory (`backend/`, `frontend/`, a subsystem) may keep its own
`CLAUDE.md`/`AGENTS.md` for rules specific to that area, a real 2026 monorepo
convention. `molt-verify.py` can't judge semantic contradiction between a
nested file and the root, that would need an LLM, not deterministic code, so
it checks two mechanical things instead: a nested file must never redeclare
`<never>`, `<verification>`, or `<before_declaring_done>` as an actual section
(mentioning them in prose is fine; redefining them isn't), and if a domain
directory keeps both `CLAUDE.md` and `AGENTS.md`, they must byte-match each
other, the same mirror mechanism used at the root. `benchmarks/CLAUDE.md` in
this project is a real, working example, not just documentation of the idea.

## What TRUSTWORTHY does and doesn't mean

`molt-verify.py`'s "TRUSTWORTHY" verdict means structural integrity: the
index agrees with the log, the log is well-formed and append-only, any
mirror byte-matches its source, and (if adopted) the hash chain is unbroken.
It does not mean the content is honest, accurate, or the right decision. A
human can type a real lie into a well-formed, internally consistent entry,
and every check here will still pass, because none of them can judge whether
a sentence is true, only whether the files agree with each other and haven't
been silently altered by a mechanism this script knows how to check. Trust
the mechanism; still read the content with judgment.

## What the hash chain does and doesn't prove

The hash chain (`**Hash:** sha256(entry + previous entry's hash)`) proves the
log is internally self-consistent: if every stored hash matches its
recomputed value from genesis forward, no entry was altered *after being
hashed*, without needing a mirror kept elsewhere. It does not, by itself,
prove non-repudiation. This project's own security review demonstrated the
gap directly: tamper with an old entry, strip its Hash field and every one
after it, then run `molt-chain-append.py` again. The tool fills in missing
hashes, so it produces a fresh, fully self-consistent chain, and
`molt-verify.py` reports it TRUSTWORTHY. The hash chain alone cannot tell the
difference between "this log has always been this way" and "someone with
the same tools rewrote it and regenerated a matching chain," because both
produce an identical, internally valid result. A self-contained local chain
with no anchor outside the log-writer's own control cannot close this gap;
that needs a signing key the day-to-day writer doesn't hold, or a remote
with branch protection the writer can't override. Neither fits a
dependency-free, local-only tool, and this project deliberately keeps that
tradeoff rather than quietly adding a signing service or a network call to
paper over it.

What `check_git_anchor` adds, honestly: if the Molt root is a git
repository, it compares the working copy of `memory/decisions.md` against
the version at the last commit (`HEAD`). A change to anything other than
new entries added on top is flagged before it can be committed over. This
is local only, no push, no remote, no network call, same dependency-free
design as everything else here. It catches the exact laundering attack
above as long as the rewrite hasn't already been committed; once it has,
`check_git_anchor` sees the committed (laundered) version as the new normal
and can't tell. Commit real entries often, so the window a rewrite can hide
in stays small. This is a mitigation, not a fix; the honest boundary is
stated here rather than implied away.

## Removing sensitive content without lying about it

An append-only, hash-chained log has no built-in way to remove content that
should never have been logged (PII, a leaked secret) short of two bad
options: leaving it there forever, or hand-editing history, which
`molt-verify.py` would then correctly flag as tampering. `molt-redact.py` is
the sanctioned third option: it replaces one entry's four required fields
with a fixed, visible placeholder, keeps that entry's heading exactly as it
was, appends a new top entry documenting the redaction itself in plain text
(what, when, why), and regenerates the hash chain from the redacted entry
forward, because that content genuinely, legitimately changed. Anyone
reading the log, or running `molt-verify.py`, can see a redaction happened,
even if not what was removed. Log the redaction as a real `INDEX.md` row
like any other entry.

## Model independence, concretely

Every rule in `CLAUDE.md` is checkable by inspection: a model either follows it or doesn't, with no dependence on that model's personality. No rule says "respond the way you normally would." No fact from a past session is assumed remembered, because a new model has no access to a prior model's history; anything worth remembering is in `memory/`. The never-list bans inventing facts to fill a gap, which is the exact failure that shows up when an unfamiliar model tries to sound like it remembers something it doesn't.

## The lesson that shaped this

The mirror check exists because of a real bug during Molt's own development. A hand-written "mirror" note, meant to be a faithful copy of the live log, gained a sentence the live log never contained. It looked authoritative, so it would have been believed. A byte-diff caught it; re-reading and assuming had not. The fix that held: never hand-paraphrase a mirror, transcribe it from the source and verify. `molt-verify.py` is that verification made mechanical, and `CLAUDE.md`'s `<before_declaring_done>` makes running it non-optional.

## The ponytail ladder

Before adding any file, section, or rule: does it need to exist at all, does an existing file already cover it, and only then add the minimum that works. Molt has pruned itself by this rule before, an earlier draft added a separate graph-index file that failed rung two and was removed the same day. Source: github.com/DietrichGebert/ponytail.

## What this is not

It is not a database or a retrieval engine, and at very large scale it's the wrong tool; reach for a real agent-memory system then. It does not replace your judgment; it's a place to keep judgment you've already exercised so it doesn't evaporate when the model does.

## Maintenance

Re-check this system whenever a model transition happens, or whenever a session feels like it's leaning on something not written down; that feeling is the signal a rule is missing, not a reason to wait for a better model. Run the verify protocol after any change.
