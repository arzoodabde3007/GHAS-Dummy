#!/usr/bin/env python3
"""source_scanner.py — Scan Java source files for vulnerable package imports.

Usage:
    python source_scanner.py <source_root>

Prints one line per package: "<package>: FOUND | NOT_FOUND"
followed by matching file paths (indented) when FOUND.

Exits 0 on success, 1 on bad arguments.
"""
import os
import re
import sys

PATTERNS: dict[str, str] = {
    "log4j":               r"import org\.apache\.logging\.log4j",
    "commons-collections": r"import org\.apache\.commons\.collections",
    "jackson-databind":    r"import com\.fasterxml\.jackson",
    "guava":               r"import com\.google\.common",
    "gson":                r"import com\.google\.gson",
    "commons-text":        r"import org\.apache\.commons\.text",
    "snakeyaml":           r"import org\.yaml\.snakeyaml",
    "h2":                  r"import org\.h2",
    "xstream":             r"import com\.thoughtworks\.xstream",
    "netty":               r"import io\.netty",
}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: source_scanner.py <source_root>", file=sys.stderr)
        return 1

    source_root = sys.argv[1]
    results: dict[str, list[str]] = {pkg: [] for pkg in PATTERNS}

    for root, _, files in os.walk(source_root):
        for fname in files:
            if not fname.endswith(".java"):
                continue
            path = os.path.join(root, fname)
            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for pkg, pat in PATTERNS.items():
                if re.search(pat, content):
                    results[pkg].append(path)

    for pkg, matched in results.items():
        status = "FOUND" if matched else "NOT_FOUND"
        print(f"{pkg}: {status}")
        for fp in matched:
            print(f"  {fp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
