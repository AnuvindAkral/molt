#!/bin/sh
# molt installer — scaffold a self-verifying memory system into any repo.
# No dependencies beyond POSIX sh + (optionally) python3 for the final audit.
#
#   ./install.sh [TARGET_DIR]     # default: current directory
#   ./install.sh . --force        # overwrite existing molt files
#
# Run it from inside the molt/ folder (it copies from next to itself). Once you've
# pushed molt to your own GitHub, you can wire up a curl one-liner; see README.

set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="."
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) TARGET="$arg" ;;
  esac
done

mkdir -p "$TARGET/memory/handoffs"

copy() {
  # copy() SRC_REL DEST_REL
  _src="$SRC/$1"
  _dst="$TARGET/$2"
  if [ -e "$_dst" ] && [ "$FORCE" -ne 1 ]; then
    echo "  skip (exists): $2   [--force to overwrite]"
    return 0
  fi
  cp "$_src" "$_dst"
  echo "  add: $2"
}

echo "molt -> $TARGET"
copy CLAUDE.md            CLAUDE.md
copy ARCHITECTURE.md      ARCHITECTURE.md
copy PROTOCOLS.md         PROTOCOLS.md
copy molt-verify.py       molt-verify.py
copy memory/INDEX.md      memory/INDEX.md
copy memory/decisions.md  memory/decisions.md
copy memory/handoffs/TEMPLATE.md memory/handoffs/TEMPLATE.md

echo ""
echo "done. next:"
echo "  1. open $TARGET/CLAUDE.md and make the <domains> yours"
echo "  2. replace the example entry in memory/decisions.md with a real first decision"
echo "  3. run the audit:  python3 $TARGET/molt-verify.py $TARGET"
echo ""

if command -v python3 >/dev/null 2>&1; then
  echo "running the audit now:"
  python3 "$SRC/molt-verify.py" "$TARGET" || true
else
  echo "(python3 not found — install it to run the self-audit)"
fi
