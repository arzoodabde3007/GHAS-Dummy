#!/usr/bin/env python3
"""apply_fix.py — Apply a version fix to a Maven pom.xml file.

Strategy A (property-backed):
    Updates <property.name>OLD</property.name> in the <properties> block.

Strategy B (inline version):
    Updates <version>OLD</version> immediately following
    <artifactId>ARTIFACT</artifactId>.

Usage:
    # Strategy A
    python apply_fix.py --manifest pom.xml --strategy A \\
        --property-name log4j.version --old-version 2.14.1 --new-version 2.17.2

    # Strategy B
    python apply_fix.py --manifest pom.xml --strategy B \\
        --artifact-id log4j-core --old-version 2.14.1 --new-version 2.17.2

Exits 0 on success (prints "DONE: ..."), 1 on error.
"""
import argparse
import re
import sys


def strategy_a(content: str, prop_name: str, old_ver: str, new_ver: str) -> tuple[str | None, str | None]:
    escaped = re.escape(prop_name)
    pattern = rf"(<{escaped}>{re.escape(old_ver)}</{escaped}>)"
    replacement = f"<{prop_name}>{new_ver}</{prop_name}>"
    new_content = re.sub(pattern, replacement, content)
    if new_content == content:
        return None, f"Pattern not found: <{prop_name}>{old_ver}</{prop_name}>"
    return new_content, None


def strategy_b(content: str, artifact_id: str, old_ver: str, new_ver: str) -> tuple[str | None, str | None]:
    pattern = (
        rf"(<artifactId>{re.escape(artifact_id)}</artifactId>"
        rf"\s*<version>){re.escape(old_ver)}(</version>)"
    )
    replacement = rf"\g<1>{new_ver}\g<2>"
    new_content = re.sub(pattern, replacement, content)
    if new_content == content:
        return None, f"Pattern not found: artifactId={artifact_id} version={old_ver}"
    return new_content, None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True, help="Path to pom.xml")
    p.add_argument("--strategy", required=True, choices=["A", "B"])
    p.add_argument("--old-version", required=True)
    p.add_argument("--new-version", required=True)
    p.add_argument("--property-name", help="Required for strategy A")
    p.add_argument("--artifact-id", help="Required for strategy B")
    args = p.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        content = f.read()

    if args.strategy == "A":
        if not args.property_name:
            print("ERROR: --property-name required for strategy A", file=sys.stderr)
            return 1
        new_content, err = strategy_a(content, args.property_name, args.old_version, args.new_version)
    else:
        if not args.artifact_id:
            print("ERROR: --artifact-id required for strategy B", file=sys.stderr)
            return 1
        new_content, err = strategy_b(content, args.artifact_id, args.old_version, args.new_version)

    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    with open(args.manifest, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"DONE: {args.manifest} updated (strategy {args.strategy}: {args.old_version} → {args.new_version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
