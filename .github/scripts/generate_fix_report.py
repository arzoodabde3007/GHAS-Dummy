#!/usr/bin/env python3
"""generate_fix_report.py — Write a GHAS fix report markdown file.

Reads report data from a JSON file (--data-file) and writes markdown to --output.

Expected JSON fields:
  jira_ticket, pr_url, feature_branch, service, repo_owner, repo_name,
  verification_result, fixes_applied, validation_results, coverage_summary,
  gate4_decision, gate4_feedback, gate8_decision, gate8_review_comments,
  plan_revision_attempts, build_failure_attempts, verify_fix_attempts,
  review_fix_attempts, max_plan_revision, max_build_failure,
  max_verify_fix, max_review_fix, build_failure_details, verify_issues_detail

Usage:
    python generate_fix_report.py --data-file report_data.json --output fix-reports/SECURITY_FIX_...md
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone


def parse_fix_table(fixes_text: str) -> list[str]:
    rows = []
    for line in (fixes_text or "").splitlines():
        m = re.match(
            r"FIXED\s+\[(\w+)\]\s*:\s*([\w\-\.]+)\s+([^\s]+)\s+[→>]\s+([^\s]+)\s+\(([^)]+)\)\s*[—\-]?\s*(.*)",
            line,
        )
        if m:
            severity, pkg, old_v, new_v, fix_type, cves = m.groups()
            rows.append(f"| {pkg} | {old_v} | {new_v} | {fix_type} | {cves.strip()} |")
    return rows if rows else ["| (none) | | | | |"]


def gate_outcome(decision: str, attempts: int, fallback: str = "N/A") -> str:
    d = decision or fallback
    if d in ("approved",):
        return "✅ Approved"
    if d == "auto-approved":
        return "✅ Auto-approved by config flag"
    if d == "aborted":
        return "❌ Aborted by user"
    if "N/A" in d:
        return "N/A — not reached"
    if attempts > 0:
        return f"⚠️ {d} — {attempts} revision(s) used"
    return d


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-file", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    with open(args.data_file, encoding="utf-8") as f:
        d = json.load(f)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verif = d.get("verification_result", "")
    run_status = "COMPLETED" if verif == "passed" else "COMPLETED — issues found"

    fix_rows = "\n".join(parse_fix_table(d.get("fixes_applied", "")))

    fixes_text = d.get("fixes_applied", "") or ""
    skipped_bom = "\n".join(l for l in fixes_text.splitlines() if l.startswith("SKIPPED") and "BOM" in l) or "none"
    skipped_unapproved = "\n".join(l for l in fixes_text.splitlines() if l.startswith("SKIPPED") and "not approved" in l) or "none"

    gate4        = d.get("gate4_decision", "")
    gate8        = d.get("gate8_decision", "N/A — not reached")
    plan_rev     = int(d.get("plan_revision_attempts", 0))
    build_fail   = int(d.get("build_failure_attempts", 0))
    verify_fix   = int(d.get("verify_fix_attempts", 0))
    review_fix   = int(d.get("review_fix_attempts", 0))
    max_plan     = int(d.get("max_plan_revision", 3))
    max_build    = int(d.get("max_build_failure", 3))
    max_verify   = int(d.get("max_verify_fix", 3))
    max_review   = int(d.get("max_review_fix", 3))

    build_step = (
        f"⚠️ Passed after {build_fail} build failure(s)" if build_fail > 0
        else "✅ Passed on first attempt"
    )
    verify_step = (
        f"⚠️ {verif} after {verify_fix} fix cycle(s)" if verify_fix > 0
        else f"✅ {verif} on first attempt"
    )
    retry_step = (
        f"🔁 {verify_fix} cycle(s) used" if verify_fix > 0
        else "✅ No retries needed"
    )

    issues_sections = []
    if d.get("build_failure_details"):
        issues_sections.append(f"### Build Failures\n{d['build_failure_details']}")
    if d.get("verify_issues_detail"):
        issues_sections.append(f"### Verification Issues\n{d['verify_issues_detail']}")
    issues_block = "\n\n".join(issues_sections) if issues_sections else "_No issues encountered._"

    content = f"""# GHAS Fix Report — {d.get('jira_ticket')} — {now}

**Status:** {run_status}
**PR:** {d.get('pr_url', '(none)')}
**Branch:** {d.get('feature_branch')}
**Service:** {d.get('service')}

---

## 0. Workflow Steps

| Step | Description | Outcome |
|------|-------------|---------|
| 1 | Context building | ✅ Completed |
| 2 | Feature branch creation | ✅ Created: {d.get('feature_branch')} |
| 3 | Change plan generation | ✅ Completed |
| 4 | Plan review | {gate_outcome(gate4, plan_rev)} |
| 5 | Fix implementation + validation | {build_step} |
| 6 | Verification | {verify_step} |
| 7 | Verification retry loop | {retry_step} |
| 8 | Human implementation review | {gate_outcome(gate8, review_fix)} |
| 9 | PR creation + Jira update | ✅ {d.get('pr_url', '(none)')} |

---

## 1. Dependencies Fixed

| Dependency | Old Version | New Version | Strategy | CVEs Resolved |
|---|---|---|---|---|
{fix_rows}

**Skipped (BOM-managed):** {skipped_bom}
**Skipped (not approved):** {skipped_unapproved}

---

## 2. Human Gate Decisions

### Step 4 — Plan Approval
- **Decision:** {gate4}
- **Revisions used:** {plan_rev} / {max_plan}
- **Feedback given (if any):**
  > {d.get('gate4_feedback') or 'N/A'}

### Step 8 — Implementation Review
- **Decision:** {gate8}
- **Review fixes used:** {review_fix} / {max_review}
- **Review comments (if any):**
  > {d.get('gate8_review_comments') or 'N/A'}

---

## 3. Build & Validation Results

{d.get('validation_results', '(not available)')}

---

## 4. Verification Results

**Overall:** {verif}

{d.get('coverage_summary', '(not available)')}

---

## 5. Retry Counters

- Plan revisions: {plan_rev} / {max_plan}
- Build failures: {build_fail} / {max_build}
- Verify fixes: {verify_fix} / {max_verify}
- Review fixes: {review_fix} / {max_review}

---

## 6. Issues Encountered

{issues_block}

---
"""

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fix report written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
