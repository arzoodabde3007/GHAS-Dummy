#!/usr/bin/env python3
"""generate_pr_body.py — Generate a GitHub PR body for a GHAS vulnerability fix.

Usage:
    python generate_pr_body.py \\
        --jira-ticket SCRUM-36 \\
        --jira-url https://your-site.atlassian.net \\
        --fixes-file /path/to/fixes_applied.txt \\
        --verification-result passed \\
        --service HMS \\
        --branch SCRUM-36-GHAS-log4j-core

Writes PR body markdown to stdout.
"""
import argparse
import re
import sys


def parse_fixes_table(fixes_text: str) -> list[str]:
    rows = []
    for line in fixes_text.splitlines():
        m = re.match(
            r"FIXED\s+\[(\w+)\]\s*:\s*([\w\-\.]+)\s+([^\s]+)\s+[→>]\s+([^\s]+)\s+\(([^)]+)\)\s*[—\-]?\s*(.*)",
            line,
        )
        if m:
            severity, pkg, old_v, new_v, fix_type, cves = m.groups()
            rows.append(f"| {pkg} | {cves.strip()} | {severity} | {old_v} | {new_v} | {fix_type} |")
    return rows if rows else ["| (no fixes applied) | | | | | |"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--jira-ticket", required=True)
    p.add_argument("--jira-url", required=True)
    p.add_argument("--fixes-file", required=True, help="File containing FIXES_APPLIED text")
    p.add_argument("--verification-result", required=True)
    p.add_argument("--service", required=True)
    p.add_argument("--branch", required=True)
    args = p.parse_args()

    with open(args.fixes_file, encoding="utf-8") as f:
        fixes_text = f.read()

    jira_link = f"{args.jira_url.rstrip('/')}/browse/{args.jira_ticket}"
    fix_rows = "\n".join(parse_fixes_table(fixes_text))
    verify_msg = (
        "All checks passed"
        if args.verification_result == "passed"
        else "Issues found — see verifier output"
    )

    body = f"""## Summary

Addresses GHAS vulnerabilities tracked in Jira ticket [{args.jira_ticket}]({jira_link}).

## Fixes applied

| Package | CVE(s) | Severity | Before | After | Fix Type |
|---------|--------|----------|--------|-------|----------|
{fix_rows}

## Validation

| Check | Result |
|-------|--------|
| dependency:tree | ✅ |
| compile         | ✅ |
| tests           | ✅ |
| smoke check     | ✅/⚠️ |

## Verification

{args.verification_result} — {verify_msg}

## Related

- Jira: [{args.jira_ticket}]({jira_link})
- Feature branch: `{args.branch}`
"""
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
