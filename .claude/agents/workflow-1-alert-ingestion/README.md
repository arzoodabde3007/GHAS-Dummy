# Workflow 1 — Alert Ingestion

**Purpose:** Fetch GHAS alerts from GitHub and create/update consolidated Jira tickets

## Entry Point
```
@alert-ingestion-orchestrator
```

**Run directly with bash tool — no sub-agents.**

## Single Agent

| Agent | Model | Approach |
|-------|-------|----------|
| **alert-ingestion-orchestrator** | haiku-4.5 | Execute all 5 steps directly in bash. Cross-platform (macOS/Linux/Windows/Git Bash). |

## Execution Flow

```
Step 0: Detect platform + load repo root
  ↓
Step 1: Validate config (ghas-w1-config.yml)
  ↓
Step 2: Verify prerequisites (gh CLI, jq)
  ↓
Step 3: Fetch GitHub alerts (via fetch_alerts.sh)
  ↓
Step 4: Resolve CSV + derive services
  ↓
Step 5: Create/update Jira tickets (via jira_ticket_manager.py process-all)
  ↓
Final: Output summary
```

## Key Features

- ✅ **Single Step Agent:** All logic in alert-ingestion-orchestrator (no sub-agents)
- ✅ **Bash-based:** Cross-platform compatible (macOS, Linux, Windows/Git Bash)
- ✅ **External Scripts:** fetch_alerts.sh for GitHub, jira_ticket_manager.py for Jira
- ✅ **Consolidated CSV:** Single CSV from all alerts
- ✅ **Deduplication:** Existing active tickets updated with new CVEs
- ✅ **Token Optimized:** Haiku model with direct execution (no agent overhead)

## Configuration

**File:** `.github/config/ghas-w1-config.yml`

**Key sections:**
- `environment` — repo owner, repo name, repo root
- `jira` — project key, parent ticket, search labels, skip statuses
- `services` — array of services to scan (name, github_repo)
- `tools` — paths to gh CLI, Python, scripts

## Prerequisites

- **GitHub CLI:** Authenticated via `gh auth login` (scopes: repo, read:org)
- **jq:** Available on PATH
- **Python 3:** For config validation and Jira operations
- **Git Bash (Windows only):** Run Claude Code from Git Bash terminal

## Output

- Timestamped CSV: `github_alerts_<YYYYMMDD_HHMMSS>.csv` with Jira key + status columns
- Jira tickets created (new): One per service with all CVEs consolidated
- Jira tickets updated (existing): Description updated with new CVEs
- Summary report with counts

## Token Budget

- Per-run: **3-5K tokens** (Haiku direct execution, no sub-agent overhead)

## Failure Handling

- GitHub CLI auth missing → Stop, prompt `gh auth login`
- Config invalid → Stop with validation error
- Prerequisites missing → Stop with install instructions
- GitHub API failure → Stop with exact error
- CSV resolution fails → Stop, no CSV created
- Jira operation fails → Stop with error context

---

*Last Updated: 2026-07-08*  
*Status: ✅ Consolidated (bash-based, single agent, cross-platform)*
