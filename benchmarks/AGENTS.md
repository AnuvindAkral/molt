# benchmarks/CLAUDE.md — domain apex file
> Adds to the root CLAUDE.md; does not replace it. Read the root file first.

This directory holds `molt-verify.py`'s own regression suite. Everything in
`<never>`, `<verification>`, and `<before_declaring_done>` in the root
`CLAUDE.md` still applies here unchanged, this file only adds rules specific
to writing adversarial test cases, it never redeclares those root tags
(`molt-verify.py`'s `check_nested_apex_consistency` fails the build if it
ever does).

<benchmark_specific>
- Every new case in `adversarial/run.py` needs both a real injector function
  and an entry in `CASES`; a case with no assertion isn't a test.
- Never let a case touch the real project's own `memory/` or `CLAUDE.md`;
  everything must run inside a temp directory built by `build_synthetic_root`
  or `build_chained_synthetic_root`.
- If a case is expected to pass (`TRUSTWORTHY`), it exists to prove a good
  path works, not just to pad the count; state in its docstring what would
  have broken without it.
- Keep this directory dependency-free, same as the rest of Molt: stdlib
  only, no network calls, no external packages.
</benchmark_specific>
