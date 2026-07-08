#!/bin/sh
set -eu

# ==============================================================
# fetch_alerts.sh — GHAS Workflow 1 Alert Fetcher
# --------------------------------------------------------------
# Usage: fetch_alerts.sh [output_dir] [owner]
#   output_dir  Directory to write the CSV into (default: current dir).
#   owner       GitHub owner/org that hosts the repositories below
#               (default: mckesson).
#
# Writes a single timestamped file github_alerts_<timestamp>.csv
# (matches csv.glob_pattern in ghas-w1-config.yml) containing the
# open Dependabot, Code Scanning, and Secret Scanning alerts for
# every repository in the REPOS list below.
# ==============================================================

# Default GitHub owner/org for production repositories.
DEFAULT_OWNER="mckesson"

if [ "$#" -gt 2 ]; then
  echo "Usage: $0 [output_dir] [owner]" >&2
  exit 2
fi

out_dir="${1:-.}"
OWNER="${2:-$DEFAULT_OWNER}"

mkdir -p "$out_dir"

timestamp="$(date +%Y%m%d_%H%M%S)"
out_path="${out_dir%/}/github_alerts_${timestamp}.csv"

printf '%s\n' 'service,type,ghsa_id,cve_id,title,severity,created,due,url,Application,nonCompliant,ageDays' > "$out_path"

_gh_out=$(mktemp)
_gh_err=$(mktemp)
trap 'rm -f "$_gh_out" "$_gh_err"' EXIT

# --------------------------------------------------------------
# REPOS — production repositories to scan (single source of truth).
# Format: "<repo_name> <application_label>"
# --------------------------------------------------------------
REPOS='
GHAS-Dummy HMS
'

_gh_out=$(mktemp)
_gh_err=$(mktemp)
trap 'rm -f "$_gh_out" "$_gh_err"' EXIT

printf '%s\n' "$REPOS" | while IFS= read -r entry; do
  [ -z "$entry" ] && continue

  svc="${entry%% *}"
  Application="${entry#* }"

  echo "Fetching alerts for service: $svc (owner: $OWNER)" >&2

  # =======================
  # Dependabot
  # =======================
  if gh api "repos/${OWNER}/${svc}/dependabot/alerts?state=open&per_page=100" --paginate \
    --jq '.[] |
      .created_at as $created |
      (.security_advisory.severity // "") as $s |
      (if $s == "critical" then ($created | fromdateiso8601 + 1296000 | strftime("%Y-%m-%d"))
       elif $s == "high" then ($created | fromdateiso8601 + 2592000 | strftime("%Y-%m-%d"))
       elif $s == "medium" then ($created | fromdateiso8601 + 7776000 | strftime("%Y-%m-%d"))
       elif $s == "low" then ($created | fromdateiso8601 + 10368000 | strftime("%Y-%m-%d"))
       else "" end) as $due |
      (((now - ($created | fromdateiso8601)) / 86400) | floor) as $age |
      {
        type: "dependabot",
        ghsa_id: (.security_advisory.ghsa_id // ""),
        cve_id: ((.security_advisory.identifiers[]? | select(.type=="CVE") | .value) // ""),
        title: (.security_advisory.summary // ""),
        severity: $s,
        created: ($created | fromdateiso8601 | strftime("%Y-%m-%d")),
        due: $due,
        url: (.html_url // ""),
        non_compliant: (if $s=="critical" and $age>15 then 1
                        elif $s=="high" and $age>30 then 1
                        elif $s=="medium" and $age>90 then 1
                        elif $s=="low" and $age>120 then 1 else 0 end),
        age_days: $age
      }' > "$_gh_out" 2>"$_gh_err"; then

    jq -rc --arg svc "$svc" --arg Application "$Application" \
      '. | [$svc,.type,.ghsa_id,.cve_id,.title,.severity,.created,.due,.url,$Application,.non_compliant,.age_days] | @csv' \
      "$_gh_out" >> "$out_path"
  fi

  # =======================
  # Code Scanning
  # =======================
  if gh api "repos/${OWNER}/${svc}/code-scanning/alerts?state=open&per_page=100" --paginate \
    --jq '.[] |
      .created_at as $created |
      ((.rule.security_severity_level // .rule.severity // .severity //"") | ascii_downcase) as $s |
      (((now - ($created | fromdateiso8601)) / 86400) | floor) as $age |
      {
        type:"code-scanning",
        ghsa_id:"",
        cve_id:"",
        title:(.rule.description // .rule.name // ""),
        severity:$s,
        created:($created | fromdateiso8601 | strftime("%Y-%m-%d")),
        due:"",
        url:(.html_url // ""),
        non_compliant:0,
        age_days:$age
      }' > "$_gh_out" 2>"$_gh_err"; then

    jq -rc --arg svc "$svc" --arg Application "$Application" \
      '. | [$svc,.type,.ghsa_id,.cve_id,.title,.severity,.created,.due,.url,$Application,.non_compliant,.age_days] | @csv' \
      "$_gh_out" >> "$out_path"
  fi

  # =======================
  # Secret Scanning
  # =======================
  if gh api "repos/${OWNER}/${svc}/secret-scanning/alerts?state=open&per_page=100" --paginate \
    --jq '.[] |
      .created_at as $created |
      ((.severity // .rule.severity //"") | ascii_downcase) as $s |
      (((now - ($created | fromdateiso8601)) / 86400) | floor) as $age |
      {
        type:"secret-scanning",
        ghsa_id:"",
        cve_id:"",
        title:(.secret_type_display_name // .secret_type // ""),
        severity:$s,
        created:($created | fromdateiso8601 | strftime("%Y-%m-%d")),
        due:"",
        url:(.html_url // ""),
        non_compliant:0,
        age_days:$age
      }' > "$_gh_out" 2>"$_gh_err"; then

    jq -rc --arg svc "$svc" --arg Application "$Application" \
      '. | [$svc,.type,.ghsa_id,.cve_id,.title,.severity,.created,.due,.url,$Application,.non_compliant,.age_days] | @csv' \
      "$_gh_out" >> "$out_path"
  fi

done

# Full set of repositories that were scanned (regardless of alert count),
# used by the orchestrator to close resolved tickets for zero-alert repos.
scanned_services="$(printf '%s\n' "$REPOS" | while IFS= read -r entry; do
  [ -z "$entry" ] && continue
  printf '%s,' "${entry%% *}"
done)"
scanned_services="${scanned_services%,}"

printf '%s\n' "Wrote CSV to: $out_path"
printf 'CSV_PATH=%s\n' "$out_path"
printf 'SCANNED_SERVICES=%s\n' "$scanned_services"
