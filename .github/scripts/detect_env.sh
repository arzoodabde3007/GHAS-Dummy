#!/bin/sh
# detect_env.sh — GHAS cross-platform environment detection
# ===========================================================
# Detects the current OS and outputs shell variable assignments
# for PLATFORM, PYTHON_CMD, and REPO_ROOT.
#
# Usage (from an agent or script):
#   eval "$(sh "$REPO_ROOT/.github/scripts/detect_env.sh")"
#   # Now $PLATFORM, $PYTHON_CMD, $REPO_ROOT are set in the calling shell.
#
# PLATFORM values : macos | linux | windows
# PYTHON_CMD      : python3 (macOS/Linux) | python (Windows/Git Bash)
# REPO_ROOT       : absolute path to the git repository root
#
# Platform detection logic:
#   macOS            → uname -s returns "Darwin"
#   Linux            → uname -s returns "Linux"
#   Windows/Git Bash → uname -s returns "MINGW*", "CYGWIN*", or "MSYS*"
#                      (Git for Windows exposes uname inside its bash shell)
# ===========================================================

OS_RAW=$(uname -s 2>/dev/null || echo "Windows_NT")
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

case "$OS_RAW" in
  Darwin)
    PLATFORM=macos
    PYTHON_CMD=python3
    ;;
  Linux)
    PLATFORM=linux
    PYTHON_CMD=python3
    ;;
  MINGW*|CYGWIN*|MSYS*)
    # Running inside Git Bash on Windows
    PLATFORM=windows
    PYTHON_CMD=python
    ;;
  *)
    # Fallback: assume POSIX-like, try python3
    PLATFORM=unknown
    PYTHON_CMD=python3
    ;;
esac

printf 'export PLATFORM=%s\n'   "$PLATFORM"
printf 'export PYTHON_CMD=%s\n' "$PYTHON_CMD"
printf 'export REPO_ROOT=%s\n'  "$REPO_ROOT"
