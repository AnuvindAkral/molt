# Memory index

Read this whole file; it's the index, cheap by design. It shows what exists and its
approximate retrieval cost so a session can decide what to actually open, rather than
reading `decisions.md` top to bottom by default. (Progressive disclosure; see
`../CLAUDE.md`'s `<how_to_load_this>` and `../PROTOCOLS.md`'s onboarding protocol.)

## decisions.md entries (newest first)

| Date | Type | Title | Gist | ~tokens |
|---|---|---|---|---|
| 2026-07-20 | fix | Fixed a placeholder-detection false positive, found by this project's own log tripping its own check | The "YYYY-MM-DD still present" check false-positived on prose mentioning the string; fixed to check real entry/row dates only, not a blind substring search. | ~285 |
| 2026-07-20 | build | Built molt-init.py, and closed the concurrent-edit gap with union merge + a conflict-marker check | One-command scaffold for new adopters (fixed a real AGENTS.md drift bug found while testing it); union-merge for concurrent decisions.md edits + a conflict-marker check that runs first. | ~570 |
| 2026-07-20 | build | Made verification mandatory (pre-commit hook + CI) and fixed a real nested-repo bug in the git anchor | Added .githooks/pre-commit + GitHub Actions blocking drift; fixed check_git_anchor silently no-oping when Molt's root isn't the git top-level. | ~520 |
| 2026-07-20 | build | Researched real agent-memory token-efficiency practice and added a Gist column, deliberately declining vector search | Added an INDEX.md Gist column so most lookups skip decisions.md entirely; declined embeddings/vector search as a dependency that also isn't exact. Fixed 2 masked check gaps found along the way. | ~510 |
| 2026-07-20 | build | Made token-efficiency claims self-verifying instead of just asserted | Fixed stale ~tokens estimates (was 30-50% low); added a check that WARNs on index drift and on entries over a 600-token budget. | ~470 |
| 2026-07-20 | fix | Fixed every finding from an external-style security review, including one CRITICAL | Added local git-anchor check (mitigates hash-chain laundering), molt-redact.py (sanctioned redaction), gitignore-negation WARN, symlink guards. | ~820 |
| 2026-07-20 | fix | Stress-tested the three newest features and fixed a real leak | Found/fixed a real bug: a directory literally named `memory` anywhere else in the tree was silently skipped by the nested-apex check. | ~450 |
| 2026-07-20 | build | Added nested apex file support for monorepos, with a real working example | Domain subdirectories (backend/, frontend/) can have their own CLAUDE.md/AGENTS.md; checked for reserved-tag redeclaration and pair drift. | ~410 |
| 2026-07-20 | build | Added CLAUDE.local.md as a verified personal layer on top of the shared apex file | Gitignored personal preferences layer on top of the shared, committed apex file; can't weaken shared governance tags. | ~400 |
| 2026-07-20 | build | Added hash-chained tamper-evidence for memory/decisions.md | Each entry hashes its own content + the previous entry's hash; altering any past entry breaks the chain forward. | ~510 |
| 2026-07-20 | build | Added AGENTS.md as a verified cross-tool mirror of CLAUDE.md | Byte-identical copy for Cursor/Copilot/Codex CLI/Gemini CLI/Aider/Windsurf/Zed, which don't read CLAUDE.md natively. | ~370 |
| 2026-07-20 | fix | Fixed a crash and a robustness gap found by testing common, non-adversarial breakage | Fixed a sort crash on malformed entries and an anchor-position false positive; added a safety net so no check can crash the whole audit. | ~360 |
| 2026-07-20 | fix | Found and fixed two new real gaps via a second adversarial pass, plus a crash in the first pass's own fix | Fixed a duplicate-entry blind spot and a binary-file-in-mirror crash. | ~480 |
| 2026-07-20 | fix | Made same-day entry ordering visible instead of silently unenforceable | Two entries sharing a date now WARN instead of silently passing as "in order." | ~320 |
| 2026-07-20 | fix | Fixed parser fragility and added handoffs/domain-buckets structural checks | Heading-in-body no longer misparsed as a new entry; added checks for INDEX.md's own required sections. | ~440 |
| 2026-07-20 | build | Made the adversarial benchmark permanent at benchmarks/adversarial/run.py | Synthetic decision logs at scale (n=300/3000), one injected corruption per case, asserting molt-verify.py's exact verdict. | ~330 |
| 2026-07-20 | fix | Ran the adversarial benchmark from SCALE-SPEC.md and tightened two soft checks to hard failures | Two checks that were WARN became FAIL, since a half-adopted guarantee gives false confidence. | ~370 |
| 2026-07-20 | build | Scoped a scale spec to compete with agentmemory, Headroom, and claude-mem without abandoning trust-first design | Chose "stay trust-first, add just enough scale" over building all four speculative capacity items (see SCALE-SPEC.md). | ~350 |
| 2026-07-19 | build | Rebuilt Molt around a self-audit that catches the agent's own drift | The original decision: molt-verify.py mechanically checks index/log/mirror agreement instead of trusting the model's word. | ~290 |

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
