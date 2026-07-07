# Agent Organization & Naming Reference

## Directory Structure

```
.github/agents/
├── alert-ingestion/          ← Workflow 1 (W1) agents
│   ├── fetcher.md            Fetches GitHub alerts
│   ├── orchestrator.md       Entry point for Workflow 1
│   └── jira-manager.md       Handles Jira ticket operations
├── vulnerability-resolver/   ← Workflow 2 (W2) agents
│   ├── orchestrator.md       Entry point for Workflow 2
│   ├── context-builder.md    Discovers & analyzes context
│   ├── planner.md            Generates change plan
│   ├── fixer.md              Applies vulnerability fixes
│   ├── validator.md          Validates fixes (build/test)
│   ├── verifier.md           Comprehensive verification
│   └── reporter.md           Creates PR & posts reports
└── archive/
    └── sorter.md             ⚠️ DEPRECATED (no longer used)
```

**`.claude/agents/`** — Identical mirror for Claude Code compatibility

---

## Invocation Guide

### Workflow 1 — Alert Ingestion

**Command:**
```bash
@alert-ingestion-orchestrator
```

**Auto-invokes:**
- `alert-ingestion/fetcher.md` (fetches alerts)
- `alert-ingestion/jira-manager.md` (handles Jira ops)

**Execution time:** 15-30 min  
**Token budget:** 158K-257K (includes fetcher: 40-80K)

---

### Workflow 2 — Vulnerability Resolver

**Command:**
```bash
@vulnerability-resolver-orchestrator <JIRA_TICKET_ID>
```

Example: `@vulnerability-resolver-orchestrator HMS-16`

**Auto-invokes (in order):**
1. `vulnerability-resolver/context-builder.md`
2. `vulnerability-resolver/planner.md`
3. `vulnerability-resolver/fixer.md` (fix loop)
4. `vulnerability-resolver/validator.md` (validation loop)
5. `vulnerability-resolver/verifier.md` (verification)
6. `vulnerability-resolver/reporter.md` (PR + reporting)

**Execution time:** 45-90 min  
**Token budget:** 632K-958K

---

## Old → New Name Mapping

### Workflow 1

| Old | New Path | New Name |
|---|---|---|
| `w1-fetcher.md` | `alert-ingestion/` | `fetcher.md` |
| `alert-ingestion-orchestrator.md` | `alert-ingestion/` | `orchestrator.md` |
| `w1-jira-manager.md` | `alert-ingestion/` | `jira-manager.md` |
| `w1-sorter.md` | REMOVED | (deprecated) |

### Workflow 2

| Old | New Path | New Name |
|---|---|---|
| `vuln-resolver-orchestrator.md` | `vulnerability-resolver/` | `orchestrator.md` |
| `w2-context-builder.md` | `vulnerability-resolver/` | `context-builder.md` |
| `w2-planner.md` | `vulnerability-resolver/` | `planner.md` |
| `w2-fixer.md` | `vulnerability-resolver/` | `fixer.md` |
| `w2-validator.md` | `vulnerability-resolver/` | `validator.md` |
| `w2-verifier.md` | `vulnerability-resolver/` | `verifier.md` |
| `w2-reporter.md` | `vulnerability-resolver/` | `reporter.md` |

---

## Single Responsibility

Each agent handles **one** concern:

### Alert Ingestion
- **fetcher** — Fetches alerts only
- **orchestrator** — Coordination, step sequencing
- **jira-manager** — Jira operations only (search, create, update, transition)

### Vulnerability Resolver
- **orchestrator** — Coordination, retry logic, step sequencing
- **context-builder** — Discovers alerts & pom.xml files; classifies dependencies
- **planner** — Generates change plan; estimates risk
- **fixer** — Applies version fixes only
- **validator** — Validates fixes (build, test, smoke check)
- **verifier** — Comprehensive verification (CVE, regression, coverage)
- **reporter** — Creates PR, posts reports, transitions ticket

---

## Token Savings

| Workflow | Before | After | Savings |
|---|---|---|---|
| W1 | 150-220K | 158-257K* | +8-15% (fetcher added) |
| W2 | 800K-1.2M | 632K-958K | **21%** |
| Combined | 950K-1.42M | 790K-1.215M | ~17% |

*W1 now includes fetcher agent (40-80K), previously separate

---

## Notes

- ✅ All agents optimized headers with token budgets
- ✅ Single config parse by orchestrators
- ✅ Removed 40+ redundant comments per agent
- ✅ Single Responsibility Principle applied
- ✅ **No w1/w2 prefixes in agent names**
- ✅ **All agents now in workflow directories**
- ✅ **Fetcher agent reorganized**
- ✅ **w1-sorter.md removed (deprecated)**
- ✅ **All root agent files deleted**
- 📝 See `OPTIMIZATION_COMPLETE.md` for full details
