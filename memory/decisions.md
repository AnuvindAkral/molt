# Decision log

> Append-only. Newest entry at top. Each entry: date, decision, reasoning, reversibility.
> Never rewrite or reorder an existing entry; a changed mind gets a new entry that supersedes the old one.
> This file ships with one real worked entry so you can see the shape. Keep it or delete it.

## 2026-07-19 · Rebuilt Molt around a self-audit that catches the agent's own drift
**Decision:** Made the self-audit (`molt-verify.py`) the center of the system rather than an add-on. The audit checks that the index matches the log exactly, that the log is newest-first and well-formed, and, if a mirror exists, that every mirrored file byte-matches its source. Kept the whole thing dependency-free (Python stdlib only) so nothing it relies on can itself rot.
**Reasoning:** An agent memory you can't trust is worse than none, because you act on it. Most agent-memory projects compete on capacity (embeddings, graphs, retrieval); none prove they aren't lying to you. That gap is the whole reason to pick this. The mirror check specifically exists because a hand-written "mirror" note once gained a sentence the real log never contained, and only a byte-diff caught it. Mechanical verification beats good intentions.
**Reversible:** Yes. The audit is one file; delete it and you still have a plain, working memory system. Nothing else depends on it at runtime.
**Review:** If entries ever grow into the thousands, or the memory spans many machines, revisit whether a real database belongs underneath. That is the named trigger, not a date.

<!-- Add new entries above this line. Keep the oldest at the bottom. -->
