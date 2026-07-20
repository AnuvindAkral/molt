# Molt, scale spec (v2 candidate)

> Trust-first, still. Enough capacity added to survive real competitors at scale.
> Nothing here replaces `molt-verify.py`; everything here answers to it.

## What this file is

The first entry in `memory/decisions.md` names its own trigger: "If entries ever
grow into the thousands, or the memory spans many machines, revisit whether a
real database belongs underneath." This is that revisit, done ahead of the
trigger rather than after, because researching agentmemory, Headroom, and
claude-mem already made the scale question real instead of hypothetical.

## The three named threats and what Molt adds, not swaps

| Competitor | Where it wins today | What Molt adds |
|---|---|---|
| agentmemory | Recall at thousands of observations, ~1,900 tokens/session at scale | Sharded, still-auditable log + deterministic recall index |
| Headroom | Compresses tool output/logs before they hit the model | Optional digest layer, checksummed against source, never silent |
| claude-mem | Zero manual effort, AI decides what's relevant | Assisted drafting; human confirms every append, nothing auto-commits |

## 1. Sharded decisions log (answers agentmemory's scale)

Problem: one flat `decisions.md` stops being cheap past a few hundred entries,
even with the index pointing at it. Re-reading grows linear no matter how good
the pointer is.

Fix: shard by month, `memory/decisions/2026-07.md`, `2026-08.md`, and so on.
`INDEX.md` keeps one row per entry, same as now, plus which shard it lives in.
`molt-verify.py` gains one job: confirm every shard is itself newest-first and
well-formed, and that each index row's shard pointer actually resolves.
Still grep-able files. Still zero dependencies. Still auditable by eye.

This is the minimum that survives thousands of entries, not a rebuild. If it
still isn't enough, that's the real signal to reach for the database the
original entry already named as the escape hatch, not before.

## 2. Deterministic recall index (answers agentmemory's semantic search)

Problem: agentmemory's real edge over flat grep is finding the right memory
without knowing the exact words used.

Fix, not a copy: a single `memory/TERMS.md`, machine-generated, append-only,
mapping keyword to (shard, entry). Built by a plain script, tokenize only, no
embeddings, no model call, so the mapping is itself auditable: regenerate it
from the shards and diff, exactly like the mirror check already does. This is
deliberately worse at fuzzy recall than vector search and deliberately better
at one thing no competitor here can claim: you can prove why an entry matched,
because the match is a string, not a hidden vector. Trust over recall quality,
same axis Molt already picked.

## 3. Optional digest layer (answers Headroom)

Problem: old handoff notes and aged decisions bloat over time the same way
tool output bloats for Headroom's users.

Fix: an opt-in `molt-digest.py` that summarizes an old shard once it's aged out
of active use, but never deletes or replaces the source, writes the digest as
a separate file, and stores a checksum of the source alongside it.
`molt-verify.py` checks the checksum, so a digest that's drifted from its
source fails the build exactly like a drifted mirror does today. Headroom
compresses and trusts the compression. Molt compresses and proves the
compression still matches its source.

## 4. Assisted drafting, human confirms (answers claude-mem)

Problem: claude-mem's real advantage is zero manual effort. Molt's real
defense is that a human decided what got kept.

Fix: an agent may propose a `decisions.md`-shaped entry after a session, but it
lands in `memory/pending/`, not the log. Nothing enters `decisions.md` without
a human copying it across, which is also the moment they can edit it.
`molt-verify.py` refuses to treat anything in `pending/` as part of the
audited log. This keeps claude-mem's convenience without inheriting its actual
risk: an AI deciding unsupervised what's worth remembering.

## 5. Adversarial verification benchmark (proves the trust claim itself)

Everything above adds capacity. None of it is worth anything if the trust
claim has never actually been tested against a memory that's large and
actively working against the audit, not just a well-behaved one.

Problem: `molt-verify.py` currently passes on one real entry in a friendly log.
That proves the script runs. It doesn't prove the claim, "an agent memory
that can't lie to you," under any real pressure. Nobody, Molt included, has
run this against a large adversarial memory yet.

Fix: a `benchmarks/adversarial/` harness that generates a synthetic log at
scale (hundreds to low thousands of entries across shards) and injects one
corruption type per run, each mirroring a real failure mode: a phantom index
row with no matching log entry, a log entry missing from the index, an
out-of-order date, a hand-edited digest whose checksum no longer matches its
source, a mirror file with an added or dropped sentence, a malformed entry
missing one of the four required fields. The benchmark asserts `molt-verify.py`
catches every single injected fault, at every scale tested, with zero false
negatives, and reports runtime so the audit's own cost is known, not assumed.

This is the actual differentiator to publish, not a comparison table against
agentmemory, Headroom, or claude-mem. Anyone can claim trustworthy memory.
Few can show a reproducible harness where the memory was deliberately made to
lie and the audit caught it every time, at scale. That's a receipt, not a
claim.

## What doesn't change

No embeddings, no vector store, no network calls, no service to run. Still
Python stdlib only. The ponytail ladder still applies to all four additions:
each was checked against "does this need to exist" before being written down.
No shards until a log is actually large. No digest until a shard actually ages
out. No `pending/` until agent-assisted drafting is actually turned on.

## Honest gap this doesn't close

This doesn't make Molt faster to adopt than claude-mem, better at fuzzy recall
than agentmemory's real vector search, or as good at raw token compression as
Headroom's benchmarks claim. It closes the one gap that mattered: none of the
three survive thousands of entries at Molt's current design, and this does,
without giving up the one thing none of them have, a build that fails loudly
when it's lying to you.

## Status

Item 5 (adversarial verification benchmark) is built and passing:
`benchmarks/adversarial/run.py`, verified at n=300 and n=3000, 0.24s at the
larger size, no degradation. It also caught a real gap on first run, a
malformed entry and a missing append-only anchor both scored as warnings
instead of failures, since fixed in `molt-verify.py`.

Items 1-4 (sharded log, deterministic recall index, digest layer, assisted
drafting) remain design-only. Per the review note on the fix entry in
`memory/decisions.md`, none of them get built until the benchmark or a real
entry count actually forces it, not before.

## What Mem0 and Letta do, and why Molt doesn't copy it

A later pass researched the current state of agent-memory token efficiency
specifically (Mem0, Letta/MemGPT, Zep). Their headline numbers are real: Mem0
reports ~1.8K tokens per query versus ~26K for full-context recall on the
LOCOMO benchmark, largely by compressing and re-embedding memories into a
vector store at write time, then doing semantic (approximate) retrieval at
read time. Two things follow from that architecture, and both conflict with
what Molt is actually for.

First, an embedding-and-vector-store layer is a dependency, and a service:
something to install, run, and keep available, which is the exact tradeoff
Molt's zero-dependency, no-network design exists to avoid. Second, and more
fundamentally, semantic retrieval is approximate by construction: an
embedding similarity search can plausibly return the "closest" memory
instead of the exact one, which is fine for a chatbot's fuzzy recall and
disqualifying for a system whose entire premise is "this proves it isn't
lying to you." Molt's exact-match, deterministic lookup (a specific dated
entry, or nothing) is slower to fuzzy-search at genuine scale, and that's
the trade this project keeps making on purpose, the same one named in
"Honest gap this doesn't close" above.

What WAS worth adopting, and did get built (see the token-efficiency fix in
`memory/decisions.md`): the industry's real, transferable insight isn't the
embeddings, it's "compress at write time, verify the compression is honest,
and let most lookups resolve from a cheap index without ever fetching the
full record." `molt-verify.py`'s `check_token_efficiency` and INDEX.md's
`Gist` column are exactly that principle, implemented with a word-count
heuristic instead of a vector index, zero dependencies, no service to run.
