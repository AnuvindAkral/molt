# PROTOCOLS.md — the repeatable moves

> Five procedures the agent runs so behavior stays identical across models and sessions.
> Each is short on purpose. Read the one that matches what you're doing; don't read all five.
> These are the "how"; `CLAUDE.md` is the "what" and the hard rules.

## 1. Onboard (start of every session)

The first thing any model does, before touching the task:

1. Read `CLAUDE.md` in full. It's short by design and it's the whole rules surface.
2. Read `memory/INDEX.md`, the table only. Now you know what's been decided and roughly what each costs to open.
3. Read ONLY the specific `memory/decisions.md` entry or `memory/handoffs/` file the current task needs. Not the whole log.
4. If resuming a named thread, read its one dated handoff file and nothing else from that folder.

You are now current. You did not read everything; you read the index and then exactly what mattered. That is the point.

## 2. Decide (whenever a real choice gets made)

A "real choice" is anything a future session would otherwise re-litigate or get wrong.

1. Append a new entry to the TOP of `memory/decisions.md`. Never edit an old one; a changed mind is a new entry that supersedes.
2. Four fields, every time: **Decision**, **Reasoning**, **Reversible**, **Review** (what would make you revisit, a trigger, not a vague "later").
3. Add one matching row to `memory/INDEX.md`'s table: date, type, title (identical wording to the entry heading), approximate tokens.
4. Run the verify protocol.

If it wasn't logged, it didn't happen. The next model has no other way to know.

## 3. Hand off (when a session ends mid-thread)

1. Copy `memory/handoffs/TEMPLATE.md` to `memory/handoffs/YYYY-MM-DD-short-topic.md`.
2. Fill in what's in progress, what's done, the exact next step, and what NOT to redo.
3. Write the next step concretely enough that a cold model, on a different day, could act on it without asking "what did you mean."
4. Add a row to the handoffs section of `memory/INDEX.md`.

## 4. Verify (after any change, before saying "done")

1. Run `python3 molt-verify.py` from the repo root.
2. Green (exit 0): the index, the log, and any mirror all tell the same story. Done.
3. Red (exit 1): fix at the SOURCE, then re-run. Do not paper over a failure, and do not hand-edit a mirror to make it match, that hides the drift instead of fixing it.
4. Trust the audit over your own memory of what you changed. Memory of one's own edits is exactly the thing that fails.

Wire this into a pre-commit hook or CI so it can't be skipped:

```sh
# .git/hooks/pre-commit
python3 molt-verify.py || { echo "molt: drift detected, commit blocked"; exit 1; }
```

## 5. Prune (monthly, or when the apex file starts feeling heavy)

1. Promote: a fact or pattern in `memory/` that's stayed relevant 6+ weeks becomes a rule in `CLAUDE.md`.
2. Prune: a rule that hasn't fired in 3 months, or a memory bucket untouched for 3, gets reviewed for removal.
3. Re-check the index-vs-whole-file tradeoff noted in `memory/INDEX.md`; it shifts as entries accumulate.
4. Apply the ponytail ladder to anything you're tempted to add. Bloat is the failure mode that made rules-vs-state worth splitting in the first place.
5. Run the verify protocol when you're done.
