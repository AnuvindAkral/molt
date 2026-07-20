# Contributing to Molt

Molt is small on purpose. Before adding anything, ask: does this need to exist at all, does an existing file already cover it, and only then add the minimum that works (see `CLAUDE.md`'s `<ponytail>` rule; it applies to this project's own development, not just to what it teaches).

## The highest-value contribution: break it

`molt-verify.py` claims to catch drift, tampering, and fabrication. The single most useful thing you can do is try to fool it.

1. Find a way to corrupt `memory/decisions.md`, `memory/INDEX.md`, a mirror, the hash chain, or anything else Molt checks, such that `molt-verify.py` still says `TRUSTWORTHY`.
2. If you succeed, open an issue with the exact steps. That's a real finding, not a nitpick.
3. Even better: add it as a permanent case in `benchmarks/adversarial/run.py` (see the existing `inject_*` functions for the pattern) and submit a PR with both the fix and the case. Every real gap this project has ever closed was found and locked in exactly this way.

## Reporting a bug

Open an issue with:
- what you ran (the exact command)
- what you expected `molt-verify.py` to say
- what it actually said
- your Python version and OS

No repro, no fix. A traceback and a one-line description are usually enough.

## Submitting a change

1. Fork, branch, make the change.
2. Run the full check before opening a PR:
   ```sh
   python3 molt-verify.py .
   python3 benchmarks/adversarial/run.py --n 300
   python3 benchmarks/adversarial/run.py --n 3000
   ```
   All three should be clean (0 fail). CI runs the same three checks on every PR.
3. If you touched `molt-verify.py`, `molt-chain-append.py`, `molt-redact.py`, the pre-commit hook, or the CI workflow, also run:
   ```sh
   python3 scripts/build-molt-init.py
   ```
   `molt-init.py` carries its own embedded copies of those files; this keeps them in sync. `molt-verify.py`'s `check_init_embed_consistency` will fail your PR if you forget.
4. If the change is a real decision (not just a typo fix), add an entry to `memory/decisions.md` and a matching row in `memory/INDEX.md`, the project uses its own system on itself.

## What won't be merged

- A dependency. Molt's entire value proposition is zero dependencies, stdlib Python only.
- A network call of any kind, even an "optional" one.
- Anything that makes `molt-verify.py` softer (turning a FAIL into a WARN) without a specific, argued reason in the PR description. A verification tool that quietly gets more lenient over time is the exact failure mode this project exists to prevent.

## Code of conduct

Be direct, be kind, assume good faith. Disagree about the work, not the person.
