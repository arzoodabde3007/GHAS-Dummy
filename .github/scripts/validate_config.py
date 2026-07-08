#!/usr/bin/env python3
"""
validate_config.py — GHAS Workflow Configuration Validator

Called by orchestrators before any agent is invoked.
Exits 0 on success, non-zero with clear error messages on failure.

Supports workflow-specific config files:
  ghas-w1-config.yml  (workflow_type: w1) — Workflow 1 Alert Ingestion
  ghas-w2-config.yml  (workflow_type: w2) — Workflow 2 Vulnerability Resolver

When workflow_type is absent (legacy combined config), all checks are applied.

Usage:
    python validate_config.py <path-to-config.yml>
"""

import sys
import os

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def get_nested(data: dict, dotted_key: str):
    """Retrieve a value from a nested dict using dot notation."""
    keys = dotted_key.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current


def validate(config_path: str) -> bool:
    if not os.path.isfile(config_path):
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return False

    with open(config_path, encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"ERROR: Invalid YAML in {config_path}: {e}", file=sys.stderr)
            return False

    if not cfg:
        print("ERROR: Config file is empty.", file=sys.stderr)
        return False

    errors = []

    # ── Workflow type detection ───────────────────────────────────
    workflow_type = cfg.get("workflow_type") or "both"
    if workflow_type not in ("w1", "w2", "both"):
        errors.append(f"  [INVALID] workflow_type must be 'w1' or 'w2', got '{workflow_type}'")
        workflow_type = "both"

    # ── Required fields ───────────────────────────────────────────
    required_fields = get_nested(cfg, "validation.required_fields") or [
        "environment.repo_owner",
        "environment.repo_name",
        "environment.service_name",
        "environment.repo_root",
        "jira.site_url",
        "jira.project_key",
    ]
    for field in required_fields:
        value = get_nested(cfg, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"  [MISSING] {field} — required but not set")

    # ── Required paths ────────────────────────────────────────────
    required_paths = get_nested(cfg, "validation.required_paths") or [
        "environment.repo_root",
    ]
    for path_field in required_paths:
        path_val = get_nested(cfg, path_field)
        if path_val and not os.path.exists(path_val):
            errors.append(f"  [PATH NOT FOUND] {path_field} = '{path_val}'")

    # ── Always-on semantic checks ─────────────────────────────────
    jira_url = get_nested(cfg, "jira.site_url") or ""
    if jira_url and not jira_url.startswith("http"):
        errors.append(f"  [INVALID] jira.site_url must start with http/https, got '{jira_url}'")

    # ── Workflow 1 checks ─────────────────────────────────────────
    if workflow_type in ("w1", "both"):
        services = get_nested(cfg, "services")
        fetch_script = get_nested(cfg, "scripts.fetch_alerts")
        # Two supported modes:
        #   config-driven : `services` lists the repos to scan
        #   script-driven : the repo list lives inside the fetch script
        # Only fail when neither source of repositories is available.
        if not services and not fetch_script:
            errors.append(
                "  [MISSING] services — provide a `services` list, or set "
                "`scripts.fetch_alerts` for script-driven mode (W1)"
            )

        valid_columns = {"ghsa_id", "cve_id", "title", "severity", "created", "due", "ageDays", "nonCompliant", "url"}
        ticket_table_columns = get_nested(cfg, "jira.ticket_table_columns")
        if ticket_table_columns is not None:
            if not isinstance(ticket_table_columns, list) or len(ticket_table_columns) == 0:
                errors.append("  [INVALID] jira.ticket_table_columns must be a non-empty list")
            else:
                unknown = [c for c in ticket_table_columns if c not in valid_columns]
                if unknown:
                    errors.append(
                        f"  [INVALID] jira.ticket_table_columns contains unknown column(s): {unknown}. "
                        f"Valid values: {sorted(valid_columns)}"
                    )

        summary_template = get_nested(cfg, "jira.ticket_summary_template")
        if summary_template is not None:
            if "{service_name}" not in summary_template:
                errors.append("  [INVALID] jira.ticket_summary_template must contain the '{service_name}' placeholder")
            if "{severity_summary}" not in summary_template:
                errors.append("  [INVALID] jira.ticket_summary_template must contain the '{severity_summary}' placeholder")

    # ── Workflow 2 checks ─────────────────────────────────────────
    if workflow_type in ("w2", "both"):
        build_tool = get_nested(cfg, "workflow2.build_tool")
        if build_tool and build_tool not in ("maven", "gradle"):
            errors.append(f"  [INVALID] workflow2.build_tool must be 'maven' or 'gradle', got '{build_tool}'")

        retry_limits = get_nested(cfg, "retry_limits")
        if retry_limits:
            for limit_key in ("plan_revision_max", "build_failure_max", "verify_fix_max", "review_fix_max"):
                val = retry_limits.get(limit_key)
                if val is not None:
                    try:
                        int_val = int(val)
                        if int_val < 1:
                            errors.append(f"  [INVALID] retry_limits.{limit_key} must be >= 1, got '{val}'")
                    except (ValueError, TypeError):
                        errors.append(f"  [INVALID] retry_limits.{limit_key} must be a positive integer, got '{val}'")

    if errors:
        print(f"\nConfig validation FAILED ({len(errors)} error(s)):\n", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\nFix the errors in: {config_path}\n", file=sys.stderr)
        return False

    # ── Success ───────────────────────────────────────────────────
    repo_owner   = get_nested(cfg, "environment.repo_owner")
    repo_name    = get_nested(cfg, "environment.repo_name")
    service_name = get_nested(cfg, "environment.service_name")
    project_key  = get_nested(cfg, "jira.project_key")
    wf_label     = {"w1": "W1", "w2": "W2", "both": "W1+W2"}.get(workflow_type, workflow_type)
    print(f"Config OK [{wf_label}] — repo={repo_owner}/{repo_name}  service={service_name}  jira={project_key}")
    return True


def get_value(config_path: str, key: str, sep: str = ",") -> int:
    """Print a single config value by dot-notation key and exit.

    Lists are joined with *sep* (default ',').
    Returns 0 on success, 1 on error.
    Prints an empty string (exit 0) when the key exists but is None / unset —
    so callers can distinguish 'missing file' (exit 1) from 'key not set' (empty output).
    """
    if not os.path.isfile(config_path):
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1

    with open(config_path, encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"ERROR: Invalid YAML in {config_path}: {e}", file=sys.stderr)
            return 1

    if not cfg:
        print("ERROR: Config file is empty.", file=sys.stderr)
        return 1

    value = get_nested(cfg, key)

    if value is None:
        print("")           # key not set — empty output, still success
    elif isinstance(value, list):
        print(sep.join(str(v) for v in value))
    elif isinstance(value, bool):
        print(str(value).lower())
    else:
        print(str(value).strip())

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python validate_config.py <config.yml>\n"
            "  python validate_config.py <config.yml> --get KEY [--sep SEP]",
            file=sys.stderr,
        )
        sys.exit(1)

    config_path = sys.argv[1]

    # ── --get mode: print a single config value ───────────────────
    if "--get" in sys.argv:
        idx = sys.argv.index("--get")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --get requires a KEY argument", file=sys.stderr)
            sys.exit(1)
        key = sys.argv[idx + 1]
        sep = ","
        if "--sep" in sys.argv:
            sep_idx = sys.argv.index("--sep")
            if sep_idx + 1 < len(sys.argv):
                sep = sys.argv[sep_idx + 1]
        sys.exit(get_value(config_path, key, sep))

    # ── Normal validation mode ────────────────────────────────────
    ok = validate(config_path)
    sys.exit(0 if ok else 1)
