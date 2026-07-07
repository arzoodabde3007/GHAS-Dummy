# Workflow 1 — Alert Ingestion

**Purpose:** Fetch GHAS alerts from GitHub and create consolidated Jira tickets per service

## Entry Point
```
@orchestrator
```

## Agents (3)

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **orchestrator** | Coordinator | haiku-4.5 | Coordinate alert fetch + Jira ticket creation |
| **fetcher** | Data Collector | haiku-4.5 | Pull Dependabot, Code Scanning, Secret Scanning alerts via `gh` CLI |
| **jira-manager** | Integration | sonnet-4.5 | Upsert Jira tickets (create new or update existing with CVE deltas) |

## Execution Flow

```
Step 0: Load config (single parse, ~5K token savings)
  ↓
Step 1: @fetcher → Fetch alerts → CSV_PATH, ALERT_COUNT, SERVICES
  ↓
Step 2: @jira-manager (create mode) → Create/update tickets per service
  ↓
Step 2b: @jira-manager (close mode) → Close zero-alert tickets
  ↓
Final: Output summary (total alerts, services, tickets created/updated/closed)
```

## Key Features

- ✅ **Consolidated CSV:** Single CSV from all services
- ✅ **Deduplication:** Existing active tickets updated with new CVEs; no duplicate tickets
- ✅ **Dual-mode Jira:** Create mode (new/update), Close mode (zero-alert closure)
- ✅ **Token Optimized:** 37% reduction (single config parse, compressed instructions)
- ✅ **Model Mix:** Haiku for coordination/fetch, Sonnet 4.5 for JQL logic

## Configuration

**File:** `.github/config/ghas-w1-config.yml`

**Key sections:**
- `environment` — repo owner/name
- `jira` — project key, labels, skip statuses
- `services` — array of services to scan
- `scripts` — path to `fetch_alerts.sh`, `jira_ticket_manager.py`

## Input (from user)

None required — all configuration from YAML.

## Output

- Consolidated CSV with all alerts
- Jira tickets created/updated (one per service with all CVEs)
- Zero-alert tickets closed (if applicable)
- Summary report

## Token Budget

- Per-run: **8-12K tokens** (optimized from 23-32K)
- Breakdown: orchestrator (1.4K) + fetcher (850) + jira-manager (1.1K)

## Failure Handling

- GitHub auth fails → Stop, prompt `gh auth login`
- Script execution fails → Stop with exact error
- CSV parsing fails → Stop with error context
- Jira API fails → Log error, continue with remaining services

---

*Last Updated: 2026-07-07*  
*Status: ✅ Optimized (37% token reduction)*
