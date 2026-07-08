#!/bin/sh
# find_latest_csv.sh — Resolve the most recently written GHAS alerts CSV
# ========================================================================
# Usage:
#   sh find_latest_csv.sh <directory>
#
# Prints the full path of the most recently modified github_alerts_*.csv
# file in <directory>. Exits 1 with an error message if no file is found.
#
# Used by alert-ingestion-orchestrator to locate the CSV produced by
# fetch_alerts.sh without platform-specific glob/sort commands.
# ========================================================================

dir="${1:-.}"

result=$(ls -t "$dir"/github_alerts_*.csv 2>/dev/null | head -1)

if [ -z "$result" ]; then
  printf 'ERROR: No github_alerts_*.csv found in: %s\n' "$dir" >&2
  exit 1
fi

printf '%s\n' "$result"
