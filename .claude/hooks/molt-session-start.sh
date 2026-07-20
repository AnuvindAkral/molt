#!/bin/bash
# Molt SessionStart hook (Claude Code): verifies memory integrity
# automatically at the start of every session, instead of relying on the
# agent to remember to run molt-verify.py itself. This is the mechanical
# version of CLAUDE.md's own <verification> instruction: enforced by a
# hook, not hoped for by a prompt.
#
# SessionStart hooks have their plain stdout added as context Claude sees
# before the first prompt (Claude Code's hooks reference: "Since plain
# stdout already reaches Claude for this event, a hook that only loads
# context can print to stdout directly without building JSON"), so this
# prints one short, honest status line rather than the full 13-check
# report. The full report is one command away if something looks wrong.
#
# Claude Code specific: this hook does nothing for Cursor, Copilot, or any
# other tool, since none of them run Claude Code's hook lifecycle. It's an
# optional bonus for Claude Code users, not part of Molt's core, tool-
# agnostic guarantee.
#
# Found by adversarial testing of this hook itself, not by inspection: if
# molt-verify.py crashes, or python3 isn't on PATH, there's no VERDICT line
# to parse, and a naive "else -> trustworthy" branch silently reports
# everything is fine when it has no idea whether that's true. That's
# exactly the failure mode Molt exists to catch, so an empty/missing
# VERDICT is its own explicit, unambiguous case below, not a fallthrough.

ROOT="${CLAUDE_PROJECT_DIR:-.}"
VERIFY="$ROOT/molt-verify.py"

if [ ! -f "$VERIFY" ]; then
  exit 0  # not a Molt project (or molt-verify.py was moved/removed) -- stay silent
fi

OUTPUT=$(python3 "$VERIFY" --no-color "$ROOT" 2>&1)
STATUS=$?
VERDICT=$(echo "$OUTPUT" | grep -m1 "^VERDICT:")

if [ -z "$VERDICT" ]; then
  echo "MOLT: could not verify memory -- molt-verify.py exited $STATUS with no VERDICT line (it may have crashed, or python3 isn't available). Do not treat memory/ as trustworthy until this is understood. Last output: $(echo "$OUTPUT" | tail -3 | tr '\n' ' ')"
elif echo "$VERDICT" | grep -q "DRIFT DETECTED"; then
  echo "MOLT: $VERDICT -- memory/decisions.md and memory/INDEX.md disagree, or another check failed. Do not treat memory/ as trustworthy until this is fixed. Run 'python3 molt-verify.py' for the full report before relying on any past decision."
else
  echo "MOLT: $VERDICT -- memory verified at session start, safe to read memory/INDEX.md and memory/decisions.md as-is."
fi

exit 0
