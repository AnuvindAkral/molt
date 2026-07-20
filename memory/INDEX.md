# Memory index

Read this whole file; it's the index, cheap by design. It shows what exists and its
approximate retrieval cost so a session can decide what to actually open, rather than
reading `decisions.md` top to bottom by default. (Progressive disclosure; see
`../CLAUDE.md`'s `<how_to_load_this>` and `../PROTOCOLS.md`'s onboarding protocol.)

## decisions.md entries (newest first)

| Date | Type | Title | ~tokens |
|---|---|---|---|
| 2026-07-20 | fix | Fixed every finding from an external-style security review, including one CRITICAL | ~520 |
| 2026-07-20 | fix | Stress-tested the three newest features and fixed a real leak | ~280 |
| 2026-07-20 | build | Added nested apex file support for monorepos, with a real working example | ~290 |
| 2026-07-20 | build | Added CLAUDE.local.md as a verified personal layer on top of the shared apex file | ~300 |
| 2026-07-20 | build | Added hash-chained tamper-evidence for memory/decisions.md | ~310 |
| 2026-07-20 | build | Added AGENTS.md as a verified cross-tool mirror of CLAUDE.md | ~280 |
| 2026-07-20 | fix | Fixed a crash and a robustness gap found by testing common, non-adversarial breakage | ~250 |
| 2026-07-20 | fix | Found and fixed two new real gaps via a second adversarial pass, plus a crash in the first pass's own fix | ~300 |
| 2026-07-20 | fix | Made same-day entry ordering visible instead of silently unenforceable | ~210 |
| 2026-07-20 | fix | Fixed parser fragility and added handoffs/domain-buckets structural checks | ~260 |
| 2026-07-20 | build | Made the adversarial benchmark permanent at benchmarks/adversarial/run.py | ~230 |
| 2026-07-20 | fix | Ran the adversarial benchmark from SCALE-SPEC.md and tightened two soft checks to hard failures | ~220 |
| 2026-07-20 | build | Scoped a scale spec to compete with agentmemory, Headroom, and claude-mem without abandoning trust-first design | ~260 |
| 2026-07-19 | build | Rebuilt Molt around a self-audit that catches the agent's own drift | ~180 |

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
Review cadence: monthly. When reviewing, re-check the whole-file-vs-index tradeoff above;
it changes as entries accumulate.
