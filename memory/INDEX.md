# Memory index

Read this whole file; it's the index, cheap by design. It shows what exists and its
approximate retrieval cost so a session can decide what to actually open, rather than
reading `decisions.md` top to bottom by default. (Progressive disclosure; see
`../CLAUDE.md`'s `<how_to_load_this>` and `../PROTOCOLS.md`'s onboarding protocol.)

## decisions.md entries (newest first)

| Date | Type | Title | ~tokens |
|---|---|---|---|
| 2026-07-19 | build | Rebuilt Molt around a self-audit that catches the agent's own drift | ~180 |

When this table and the log disagree, that's drift, and `molt-verify.py` will fail the
build until they agree again. Add one row here for every entry you append to the log.

## handoffs/

Empty except `TEMPLATE.md` (the shape; copy, don't edit). Add a row here the first time a
real handoff file exists, same table shape as above.

## domain buckets

Empty until real use fills them in. Add a short section per bucket as it becomes a real
recurring thing, with a one-line pointer to wherever its detail actually lives.

## lifecycle

Promotion: a fact or pattern relevant for 6+ weeks moves from here into a rule in `../CLAUDE.md`.
Pruning: a bucket or entry untouched for 3+ months gets reviewed for removal.
Review cadence: monthly. When reviewing, re-check the whole-file-vs-index tradeoff above;
it changes as entries accumulate.
