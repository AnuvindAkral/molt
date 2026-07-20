#!/bin/sh
# Deprecated. Use molt-init.py instead: it's the fully self-contained,
# actively maintained scaffolder (embeds its own framework files, generates
# a *fresh* starter memory/, and is what the one-command GitHub install in
# README.md actually runs).
#
# This script used to copy memory/INDEX.md and memory/decisions.md straight
# from this project's own working copy -- meaning anyone running it from a
# real checkout would get THIS project's actual internal decision history
# copied into their project, not a fresh starter template. Found while
# rewriting the README to point at molt-init.py; molt-init.py never had
# this bug, since it always generates fresh templates rather than copying
# whatever happens to be sitting in memory/ at build time. Kept as a thin
# forwarding shim, not deleted outright, in case anything still calls it
# by name.
#
#   ./install.sh [TARGET_DIR] [--force]

set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SRC/molt-init.py" "$@"
