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
