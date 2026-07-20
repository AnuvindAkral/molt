#!/bin/bash
# Molt SessionEnd hook (Claude Code): one more integrity check as the
# session closes, so drift introduced during this session is caught
# immediately instead of waiting for the next session start, the next
# commit, or CI.
#
# SessionEnd hooks can't block anything and Claude never sees this (Claude
# Code's hooks reference lists SessionEnd under events with "no decision
# control... used for side effects like logging or cleanup," and its exit
# code 2 behavior is "Shows stderr to user only"). This is purely a
# heads-up to the person at the keyboard, written to stderr, not a
# mechanism the agent can react to.
#
# Claude Code specific, same as molt-session-start.sh: does nothing for
# Cursor, Copilot, or any other tool.
#
# Found by adversarial testing of this hook itself, not by inspection: if
# molt-verify.py crashes, or python3 isn't on PATH, there's no VERDICT line
# to parse, and the original "only warn on DRIFT DETECTED" check silently
# printed nothing at all, the same false-confidence gap as the start hook,
# just silent instead of falsely reassuring. An empty/missing VERDICT now
# gets its own explicit warning too.

ROOT="${CLAUDE_PROJECT_DIR:-.}"
VERIFY="$ROOT/molt-verify.py"

if [ ! -f "$VERIFY" ]; then
  exit 0
fi

OUTPUT=$(python3 "$VERIFY" --no-color "$ROOT" 2>&1)
STATUS=$?
VERDICT=$(echo "$OUTPUT" | grep -m1 "^VERDICT:")

if [ -z "$VERDICT" ]; then
  echo "molt: could not verify memory at session end -- molt-verify.py exited $STATUS with no VERDICT line (it may have crashed, or python3 isn't available). Run 'python3 molt-verify.py' before your next session." >&2
elif echo "$VERDICT" | grep -q "DRIFT DETECTED"; then
  echo "molt: $VERDICT at session end -- something in memory/ is inconsistent. Run 'python3 molt-verify.py' before your next session." >&2
fi

exit 0
