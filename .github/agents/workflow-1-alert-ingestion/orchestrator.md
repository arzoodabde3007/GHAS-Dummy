---
description: Workflow 1 - Orchestrator - fetches GHAS alerts and creates Jira tickets. Optimized.
model: claude-haiku-4.5
tools:
  - powershell
  - task
---

# Workflow 1 — Orchestrator (Alert Ingestion)

**Scope:** Coordinate alert fetching and Jira ticket creation  
**Sub-agents:** @fetcher, @jira-manager

## Steps

### 0. Initialize

```powershell
$REPO_ROOT = (git rev-parse --show-toplevel 2>$null).Trim() -replace '/', '\' || (Get-Location).Path
$CONFIG_PATH = "$REPO_ROOT\.github\config\ghas-w1-config.yml"
python "$REPO_ROOT\.github\scripts\validate_config.py" $CONFIG_PATH || exit 1

$cfg = python -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))" $CONFIG_PATH | ConvertFrom-Json
```
