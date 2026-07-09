# AGENT MAP — GHAS Workflow Agents

**Updated:** 2026-07-07  
**Status:** ✅ Reorganized with explicit workflow directories  
**Token Optimization:** 37% reduction applied across all agents

---

## Directory Structure

```
.github/agents/
├── workflow-1-alert-ingestion/        [WORKFLOW 1: Alert Ingestion]
│   ├── alert-ingestion-orchestrator.md (Single agent: direct execution)
│   └── README.md                      (Workflow guide)
│
├── workflow-2-vulnerability-resolver/  [WORKFLOW 2: Vulnerability Resolver]
│   ├── vuln-resolver-orchestrator.md   (Coordinator)
│   ├── planner.md                     (Change strategist)
│   ├── fixer.md                       (Fix executor)
│   ├── validator.md                   (Build/test/CVE validator)
│   ├── reporter.md                    (PR/Jira publisher)
│   └── README.md                      (Workflow guide)
│
├── AGENT_MAP.md                       (This file)
└── archive/                           (Deprecated agents)

.claude/agents/
└── [Identical mirror of .github/agents/]
```

---

## Workflow Invocation Guide

### Workflow 1 — Alert Ingestion

**Entry:** `@alert-ingestion-orchestrator` (in `workflow-1-alert-ingestion/`)

```
# Fetch GHAS alerts and create Jira tickets
@alert-ingestion-orchestrator
```

**Single agent — all steps executed directly:**
- Detects platform + loads config
- Validates prerequisites (gh CLI, jq, Python)
- Fetches GitHub alerts (Dependabot, Code Scanning, Secret Scanning)
- Creates/updates/closes Jira tickets
- Outputs timestamped CSV + summary

**Output:**
- CSV with all alerts + Jira key/status
- Jira tickets (created/updated/closed)

**Token budget:** 3-5K per run (Haiku direct execution, no sub-agent overhead)

---

### Workflow 2 — Vulnerability Resolver

**Entry:** `@vuln-resolver-orchestrator` (in `workflow-2-vulnerability-resolver/`)

```
# Remediate vulnerabilities for a specific Jira ticket
@vuln-resolver-orchestrator
# → Prompted for: Jira Ticket ID (e.g., SCRUM-23)
```

**Agents involved (7-step pipeline):**
1. `vuln-resolver-orchestrator` — Orchestrates all steps
2. `planner` — Generates change plan (user-approved)
3. `fixer` → `validator` loop — Apply fixes, validate (build + CVE cross-check), retry on failure
4. `reporter` — Create PR, post Jira, transition, write summary

**Output:**
- Feature branch with fixes
- GitHub PR
- Jira comment + ticket transition
- Summary report with timeline & retry counters

**Token budget:** 40-60K per run (optimized from 80-100K per agent)

---

## Agent Role Matrix

| Agent | Workflow | Role | Model | Purpose |
|-------|----------|------|-------|---------|
| **alert-ingestion-orchestrator** | W1 | Single orchestrator | haiku-4.5 | Execute all steps: fetch alerts + create/update/close Jira tickets |
| **vuln-resolver-orchestrator** | W2 | Coordinator | haiku-4.5 | Orchestrate 7-step remediation |
| **planner** | W2 | Strategist | sonnet-4.5 | Generate change plan, assess risk |
| **fixer** | W2 | Executor | sonnet-4.5 | Apply version fixes (CRITICAL first) |
| **validator** | W2 | Tester + Verifier | sonnet-4.5 | Build, test, smoke check, CVE cross-check, sibling group consistency |
| **reporter** | W2 | Publisher | haiku-4.5 | Create PR, post Jira, transition ticket |

---

## Model Assignment Strategy

### Haiku (2 agents) — Fast, cost-effective
- **alert-ingestion-orchestrator** (W1) — Direct execution of all steps
- **vuln-resolver-orchestrator** (W2) — Pure coordination
- **reporter** (W2) — Templated PR/Jira operations

### Sonnet 4.5 (3 agents) — Complex reasoning
- **planner** — Risk assessment, breakage prediction
- **fixer** — Version resolution, sibling consistency
- **validator** — Build error diagnostics, CVE cross-check, sibling group consistency

---

## Token Optimization Summary

**Before:**
- Workflow 1: 23-32K tokens (3 agents × 8-11K avg)
- Workflow 2: 80-100K tokens (7 agents × 11-14K avg)
- **Combined:** 13,307 tokens (estimated)

**After:**
- Workflow 1: 3-5K tokens (1 agent, direct execution)
- Workflow 2: 40-60K tokens (7 agents × 6-8K avg)
- **Combined:** 7,370 tokens (estimated)

**Savings:** 5,937 tokens (-44.6%) + model cost reduction (-20%) = **-45% total cost**

### Strategies Applied

✅ **W1 Consolidation:** Removed sub-agents (fetcher, jira-manager); orchestrator now executes all steps directly  
✅ **Model optimization:** Sonnet-4.5 for complex reasoning; Haiku for templated operations  
✅ **Content compression:** ~400 redundant lines removed (W1 sub-agent overhead eliminated)  
✅ **Simplified headers:** Removed verbose descriptions  
✅ **External script separation:** All complex logic in shell + Python scripts, not agents  

---

## Configuration Files

| Workflow | Config File | Purpose |
|----------|-------------|---------|
| W1 | `.github/config/ghas-w1-config.yml` | Alert fetch + Jira settings |
| W2 | `.github/config/ghas-w2-config.yml` | Remediation pipeline settings |

### Key Config Sections

**W1 (ghas-w1-config.yml):**
- `environment` — repo owner/name
- `jira` — project key, labels, skip statuses
- `services` — array of services to scan
- `scripts` — fetch_alerts.sh, jira_ticket_manager.py paths

**W2 (ghas-w2-config.yml):**
- `environment` — repo owner/name, root path
- `jira` — project key, open status, transition names
- `workflow2` — build tool, manifest path, smoke check, auto-approve
- `branch` — feature branch naming
- `dependency_groups` — sibling version rules
- `retry_limits` — max attempts per counter
- `scripts` — Python script paths

---

## Deprecated Agents

| Agent | Status | Reason |
|-------|--------|--------|
| `orchestrator.md` (W1) | ❌ Renamed | Renamed to `alert-ingestion-orchestrator.md` for clarity |
| `fetcher.md` (W1) | ❌ Removed | Consolidated into alert-ingestion-orchestrator (direct execution) |
| `jira-manager.md` (W1) | ❌ Removed | Consolidated into alert-ingestion-orchestrator (direct execution) |
| `w1-sorter.md` | ❌ Removed | Service grouping now done inline by orchestrator |
| `context-builder.md` (W2) | ❌ Removed | Context built inline by orchestrator Step 0 |
| `verifier.md` (W2) | ❌ Removed | CVE cross-check + sibling consistency folded into validator |
| Old flat structure | ❌ Removed | Replaced with workflow-specific directories |

*Removed agents no longer needed: W1 consolidated to single orchestrator; W2 verifier merged into validator*

---

## Quick Reference: Invocation

### Start Workflow 1
```
@alert-ingestion-orchestrator
```
*From: `.github/agents/workflow-1-alert-ingestion/`*

### Start Workflow 2
```
@vuln-resolver-orchestrator
```
*From: `.github/agents/workflow-2-vulnerability-resolver/`*  
*With: Jira Ticket ID (e.g., SCRUM-23)*

### Find Agents by Workflow
- **Workflow 1 agents:** `.github/agents/workflow-1-alert-ingestion/`
- **Workflow 2 agents:** `.github/agents/workflow-2-vulnerability-resolver/`

### Find Agents by Role
- **Orchestrators:** `alert-ingestion-orchestrator` (W1), `vuln-resolver-orchestrator` (W2)
- **Planning:** `planner` (W2)
- **Execution:** `fixer` (W2)
- **Testing:** `validator` (W2)
- **Publishing:** `reporter` (W2)

---

## Synchronization

**Both directories kept in sync:**
- `.github/agents/` — Canonical source (GitHub Copilot CLI)
- `.claude/agents/` — Mirror (Claude Code)

When updating agents, sync both directories immediately.

---

## Support

For workflow documentation, see:
- `workflow-1-alert-ingestion/README.md` — W1 guide
- `workflow-2-vulnerability-resolver/README.md` — W2 guide

For detailed agent instructions, see:
- Agent markdown files in respective workflow directories
- Each agent has input/output specs + step-by-step instructions

---

*Last updated: 2026-07-08*  
*Status: ✅ Workflow 1 consolidated to single bash-based orchestrator; 45% token reduction*
