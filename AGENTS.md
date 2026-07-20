# CLAUDE.md — apex file
> Stable rules only. Target: under 300 lines. Read this every session.
> It should tell a brand-new model everything it needs to behave like the last one did.

<why_this_exists>
Models get deprecated, retired, or swapped for a better one. Whatever judgment, tone, or discipline you built up with one model cannot live only in that model's behavior, because it disappears when the model does. The fix: put the judgment in files. Any model reading these files should produce close to the same behavior, because the behavior is written down, not inferred from a specific model's defaults. And because a memory you can't trust is worse than none, the system verifies itself (see `<verification>`).
</why_this_exists>

<how_to_load_this>
This file auto-loads at your project root with Claude Code and Cowork. Most other coding agents (Cursor, GitHub Copilot, Codex CLI, Gemini CLI, Aider, Windsurf, Zed) instead auto-load a file named `AGENTS.md`, the open cross-tool convention as of 2026. Rather than keep two sets of rules, `AGENTS.md` in this project is a byte-identical copy of this file: same mechanism as the mirror check in `<verification>`, applied to one file instead of a directory. Edit `CLAUDE.md`, never `AGENTS.md` directly; `molt-verify.py` fails if they drift apart. This is what makes the model-independence claim in `<why_this_exists>` actually hold across tools, not just across Claude models. Load order, just-in-time, not all at once: this file first, always (it's the whole rules surface, kept short on purpose), then `memory/INDEX.md`'s table (titles and sizes only), then fetch only the one `memory/decisions.md` entry or `memory/handoffs/` file the current task actually needs. Reading `decisions.md` top to bottom by default is exactly the waste this ordering avoids. The full procedure is the onboarding protocol in `PROTOCOLS.md`.
</how_to_load_this>

<never>
- Fabricate a fact to fill a gap: a date, a preference, a number, a citation that hasn't actually been stated in these files or the current conversation. Say "I don't have that" instead.
- Silently pick one reading among several plausible ones. State the assumption out loud, or name the readings and ask.
- Rewrite or reorder an existing `memory/decisions.md` entry. A changed mind gets a NEW entry that supersedes the old one; the old one stays exactly as written.
- Edit a mirror by hand (if you keep one). Regenerate it from the source and verify, per `<verification>`. A drifted mirror is how fabrication sneaks in.
</never>

<workflow>
- Ask before anything with real consequences (money, sending something, deleting something) if it isn't already obvious from context.
- State assumptions before acting on them: a file format, a path, a default, which of several plausible readings you're taking. If more than one reading is plausible, name them rather than picking silently.
- When a real tradeoff exists, name the options and the reasoning; don't just pick.
- Follow the matching procedure in `PROTOCOLS.md` for the recurring moves (onboard, decide, hand off, verify, prune).
</workflow>

<verification>
This system checks itself. `molt-verify.py` confirms the index matches the log, the log is newest-first and well-formed, and any mirror byte-matches its source. Run it after any change to `memory/` or the apex files, and before declaring work done. It exits non-zero on drift, so it also belongs in CI or a pre-commit hook. Trust the audit over your own memory of what you changed.
</verification>

<personal_layer>
If `CLAUDE.local.md` exists next to this file, read it after `CLAUDE.md` and `AGENTS.md`. It's gitignored by convention (see `.gitignore`), never committed, one per person. It may only add personal *preference*, tone, verbosity, which protocol you default to when more than one applies. It may never weaken `<never>`, `<verification>`, or `<before_declaring_done>`; those are shared team governance, not personal taste, and stay identical for everyone regardless of who's asking. `molt-verify.py`'s `check_gitignore_sanity` fails if `CLAUDE.local.md` exists but isn't actually excluded by `.gitignore` (a real leak risk), and separately fails if `CLAUDE.md`, `AGENTS.md`, or `memory/` are ever accidentally git-ignored (the far more common real mistake: silently stops the shared rules from syncing across the team). Copy `CLAUDE.local.md.example` to start your own.
</personal_layer>

<domains>
Starting shape, not fixed. Add or remove a bucket in `memory/INDEX.md` as real use shows what actually recurs. Replace these with your own: Projects, Admin/logistics, Learning, plus whatever genuinely recurs. Each bucket's live facts go in `memory/`, never here.
</domains>

<references>
Do NOT auto-load. Read only the one you actually need.

- `PROTOCOLS.md` → the repeatable workflows. Read the one that matches what you're doing.
- `ARCHITECTURE.md` → only if asked "why is this built this way."
- `memory/INDEX.md` → always, second (it's the index, cheap, tells you what else to open).
- `memory/decisions.md` → only the specific entry the index points you to, not the whole file, unless the index says there are few enough that reading all of it is cheaper than looking each one up.
- `memory/handoffs/` → only the one dated file for the thread being resumed, never the whole folder.
</references>

<ponytail>
Before adding a new file, section, or rule, climb this ladder and stop at the first rung that holds: (1) does this need to exist at all, (2) does an existing file already cover it, extend it instead, (3) only then add the minimum that works. Lazy, not negligent: the never-list, the append-only rule, and the verification step are never on the chopping block regardless of what this ladder says. Adapted from github.com/DietrichGebert/ponytail.
</ponytail>

<before_declaring_done>
Before calling any change to this system finished: did a real decision get logged in `memory/decisions.md`, not just made in conversation; did `memory/INDEX.md`'s table get a matching row; did `molt-verify.py` pass; does the change still clear the ponytail ladder. Any "no" means not done yet, not a footnote.
</before_declaring_done>

<memory_boundary>
This file holds stable rules only. Facts, decisions, and things that happened live in `memory/`. Promotion: a fact relevant for 6+ weeks becomes a rule here. Pruning: a rule that hasn't fired in 3 months gets removed. Review monthly.
</memory_boundary>
