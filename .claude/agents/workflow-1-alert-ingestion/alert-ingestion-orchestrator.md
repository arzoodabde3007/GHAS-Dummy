---
description: Workflow 1 — GHAS Alert Ingestion. Fetches open GitHub Dependabot, Code Scanning, and Secret Scanning alerts then creates or updates Jira tickets. Cross-platform: runs natively on macOS/Linux; runs inside Git Bash on Windows. All steps execute directly — no sub-agents. All Jira operations use jira_ticket_manager.py — no MCP.
model: claude-haiku-4-5-20251001
tools:
  - bash
---

# Workflow 1 — Alert Ingestion

Execute every step directly with the `bash` tool. **Do NOT spawn sub-agents.**
Never simulate or fabricate command output — run the real commands and show real output.
Stop immediately on any unrecoverable failure.

**🚫 HARD RULE — NEVER CLOSE ANYTHING.**
This workflow only CREATES new tickets or UPDATES existing ones.
Never call `jira_ticket_manager.py transition`, never use any Jira MCP transition tool,
never close/resolve/cancel/move any ticket to Done — under any circumstance.

## Progress Format

```
🔄 [W1] <step description>...
✅ [W1] <success summary>
❌ [W1] FAILED at <step>: <exact error output>
```

---

## Step 0 — Detect Platform + Repo Root

```bash
export REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
eval "$(sh "$REPO_ROOT/.github/scripts/detect_env.sh")"
echo "REPO_ROOT=$REPO_ROOT"
echo "PLATFORM=$PLATFORM  PYTHON_CMD=$PYTHON_CMD"
```

`detect_env.sh` sets three exported variables:
- `PLATFORM`    — `macos`, `linux`, or `windows` (detected via `uname -s`)
- `PYTHON_CMD`  — `python3` (macOS/Linux) or `python` (Windows/Git Bash)
- `REPO_ROOT`   — absolute path to the git repository root

On **Windows**: run Claude Code from a Git Bash terminal so the `bash` tool resolves correctly.
Inside Git Bash, `uname -s` returns `MINGW*` / `MSYS*` — detection is automatic.

If `REPO_ROOT` is empty → STOP, tell user to run from inside the git repository.

Emit: `✅ [W1] Platform: $PLATFORM | Python: $PYTHON_CMD | Root: $REPO_ROOT`

---

## Step 1 — Load + Validate Config

```bash
export CONFIG_PATH="$REPO_ROOT/.github/config/ghas-w1-config.yml"
export SCRIPTS="$REPO_ROOT/.github/scripts"

echo "🔄 [W1] Step 1/5 — Validating config: $CONFIG_PATH"
"$PYTHON_CMD" "$SCRIPTS/validate_config.py" "$CONFIG_PATH"
```

If validation fails (exit code ≠ 0) → STOP immediately. Fix the reported errors in the config file.

On success, load all required values:

```bash
export REPO_OWNER=$("$PYTHON_CMD" "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get environment.repo_owner)
export GH_CMD=$("$PYTHON_CMD"     "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get tools.gh)
export JIRA_PROJECT=$("$PYTHON_CMD" "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get jira.project_key)
export PARENT_JIRA=$("$PYTHON_CMD"  "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get jira.parent_jira)
export SEARCH_LABELS=$("$PYTHON_CMD" "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get jira.search_labels)
export SKIP_STATUSES=$("$PYTHON_CMD" "$SCRIPTS/validate_config.py" "$CONFIG_PATH" --get jira.skip_statuses_for_duplicate_check)
export CSV_OUT_DIR="$REPO_ROOT"

echo "owner=$REPO_OWNER  project=$JIRA_PROJECT  parent=$PARENT_JIRA"
echo "search_labels=$SEARCH_LABELS"
echo "skip_statuses=$SKIP_STATUSES"
```

Emit: `✅ [W1] Config loaded: owner=$REPO_OWNER  jira=$JIRA_PROJECT`

---

## Step 2 — Verify Prerequisites

### GitHub CLI authentication

```bash
"$GH_CMD" auth status
```

Look for `Logged in to github.com` with scopes including `repo` and `read:org`.
If not authenticated → STOP, tell user to run `gh auth login`.

### jq availability

```bash
jq --version 2>/dev/null || echo "jq not found"
```

If jq is missing → STOP. Install instructions:
- macOS: `brew install jq`
- Linux: `sudo apt-get install jq` / `sudo yum install jq`
- Windows (Git Bash): download from https://jqlang.github.io/jq/ and add to PATH

Emit: `✅ [W1] Prerequisites verified`

---

## Step 3 — Fetch GitHub Alerts

```bash
export FETCH_SCRIPT="$REPO_ROOT/.github/scripts/fetch_alerts.sh"
echo "🔄 [W1] Step 3/5 — Fetching alerts for all repos under: $REPO_OWNER"

# Cross-platform: on macOS/Linux and Windows/Git Bash, bash is on PATH.
# The fetch_alerts.sh is a POSIX sh script — runs identically on all platforms.
bash "$FETCH_SCRIPT" "$CSV_OUT_DIR" "$REPO_OWNER"
```

The script fetches open Dependabot, Code Scanning, and Secret Scanning alerts for every
repository in the `REPOS` list inside `fetch_alerts.sh` (under `$REPO_OWNER`) via `gh api`
and writes a single timestamped `github_alerts_<timestamp>.csv`.

Capture and display the full output. On non-zero exit → STOP with the exact error.

Emit: `✅ [W1] Step 3/5 — fetch_alerts.sh complete`

---

## Step 4 — Resolve CSV + Derive Services

```bash
# Find the CSV written by fetch_alerts.sh (most recent match)
export CSV_PATH=$(sh "$SCRIPTS/find_latest_csv.sh" "$CSV_OUT_DIR")
if [ -z "$CSV_PATH" ]; then
  echo "❌ [W1] FAILED at Step 4: no github_alerts_*.csv found in $CSV_OUT_DIR"
  exit 1
fi
echo "CSV_PATH=$CSV_PATH"

# Count data rows (excluding header line)
export TOTAL_ALERT_COUNT=$(tail -n +2 "$CSV_PATH" 2>/dev/null | wc -l | tr -d ' ')
echo "TOTAL_ALERT_COUNT=$TOTAL_ALERT_COUNT"

# Derive the set of services that have alert rows
export ALERT_SERVICES=$("$PYTHON_CMD" "$SCRIPTS/parse_csv_services.py" "$CSV_PATH")
echo "ALERT_SERVICES=$ALERT_SERVICES"
```

If `TOTAL_ALERT_COUNT` = 0:
- Report "No open alerts found — nothing to create or update."
- STOP with success. (Tickets are NEVER closed by this workflow.)

Emit: `✅ [W1] Step 4/5 — CSV: $TOTAL_ALERT_COUNT alerts across: $ALERT_SERVICES`

---

## Step 5 — Create / Update Jira Tickets

```bash
export JIRA_SCRIPT="$REPO_ROOT/.github/scripts/jira_ticket_manager.py"
echo "🔄 [W1] Step 5/5 — Running process-all for services: $ALERT_SERVICES"

"$PYTHON_CMD" "$JIRA_SCRIPT" process-all \
  --project  "$JIRA_PROJECT" \
  --csv      "$CSV_PATH" \
  --labels   "$SEARCH_LABELS" \
  --parent   "$PARENT_JIRA" \
  --statuses "$SKIP_STATUSES" \
  --services "$ALERT_SERVICES"
```

`process-all` performs in one Python process:
1. A single JQL search for all candidate GHAS tickets (replaces per-service searches)
2. Per service: **create** (no active ticket) / **update** description (new CVEs) / **skip** (no change)
3. Writes `jira_key` + `jira_status` back into the CSV

The command prints per-service progress to stderr (`CREATED` / `UPDATED` / `SKIP` / `FAILED`)
and a final JSON summary to stdout: `{"created":[...],"updated":[...],"skipped":[...],"failed":[...]}`.

Parse the JSON summary line from stdout and extract counts.

On non-zero exit → show exact error and STOP.
Individual per-service failures appear in the `failed` array and do NOT abort the batch.

Emit: `✅ [W1] Step 5/5 — Jira tickets processed`

---

## Final Output

```
╔══════════════════════════════════════════════════════╗
║      WORKFLOW 1 — ALERT INGESTION COMPLETE           ║
╠══════════════════════════════════════════════════════╣
║  Services processed   : <N> (<comma-list>)           ║
║  Total alerts         : <N>                          ║
║  Jira tickets created : <N>  → [HMS-XX, ...]         ║
║  Jira tickets updated : <N>  → [HMS-XX, ...]         ║
║  Jira tickets skipped : <N>  (no new CVEs)           ║
╚══════════════════════════════════════════════════════╝
```

(No "auto-closed" line — this workflow never closes tickets.)

---

## Rules

- Execute all steps with the `bash` tool — **never spawn sub-agents**
- Never simulate or fabricate command output
- Stop immediately when any step fails with non-zero exit code
- Always pass `--services "$ALERT_SERVICES"` to `process-all` — never process zero-alert services
- **NEVER close, transition, resolve, cancel, or move any ticket to Done — only create or update**
- On Windows: requires running Claude Code from a Git Bash terminal (not PowerShell / cmd)
