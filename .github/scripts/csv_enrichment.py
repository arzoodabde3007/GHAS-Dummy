#!/usr/bin/env python3
"""csv_enrichment.py — Extract alert enrichment data for a service from a GHAS alerts CSV.

Usage:
    python csv_enrichment.py <csv_glob_pattern> <service_name>

Prints a summary of Dependabot, Code Scanning, and Secret Scanning rows
for the given service, including SLA overdue status.

Exits 0 always — missing CSV is treated as a warning, not an error.
"""
import csv
import glob
import os
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: csv_enrichment.py <csv_glob> <service_name>", file=sys.stderr)
        return 1

    csv_glob = sys.argv[1]
    service = sys.argv[2]

    files = sorted(glob.glob(csv_glob), key=os.path.getmtime, reverse=True)
    if not files:
        print("[WARN] No github_alerts_*.csv found — skipping CSV enrichment")
        return 0

    csv_path = files[0]
    print(f"[INFO] Reading CSV: {csv_path}")

    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:
        print(f"[WARN] Could not read CSV {csv_path}: {exc}")
        return 0

    svc_rows = [r for r in rows if r.get("service", "").strip().lower() == service.lower()]
    dep_rows = [r for r in svc_rows if r.get("type") == "dependabot"]
    cs_rows  = [r for r in svc_rows if r.get("type") == "code-scanning"]
    ss_rows  = [r for r in svc_rows if r.get("type") == "secret-scanning"]

    print(f"Dependabot rows : {len(dep_rows)}")
    print(f"Code Scanning   : {len(cs_rows)}")
    print(f"Secret Scanning : {len(ss_rows)}")

    overdue = [r for r in dep_rows if r.get("nonCompliant", "0") == "1"]
    print(f"Overdue (past SLA): {len(overdue)}")
    for r in dep_rows:
        print(
            f"  [{r.get('severity','').upper()}] {r.get('cve_id','')} "
            f"| age={r.get('ageDays','')}d | due={r.get('due','')} "
            f"| overdue={r.get('nonCompliant','')}"
        )

    cs_counts: dict[str, int] = {}
    for r in cs_rows:
        sev = r.get("severity", "unknown").upper()
        cs_counts[sev] = cs_counts.get(sev, 0) + 1
    print(f"Code Scanning by severity: {cs_counts}")
    for r in cs_rows:
        print(f"  [{r.get('severity','').upper()}] {r.get('title','')} | {r.get('url','')}")

    print(f"Secret Scanning alerts: {len(ss_rows)}")
    for r in ss_rows:
        print(f"  {r.get('title','')} | {r.get('url','')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
