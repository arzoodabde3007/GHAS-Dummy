#!/usr/bin/env python3
"""
parse_csv_services.py — Extract unique service names from a GHAS alerts CSV.

Usage:
    python parse_csv_services.py <csv_path>

Reads the CSV written by fetch_alerts.sh and prints a comma-separated,
sorted list of unique service names that have at least one alert row.

Exits:
    0  — success (prints result; empty string if CSV has no data rows)
    1  — file not found, unreadable, or missing 'service' column

The CSV is expected to have a header row with a 'service' column as the
first field (matches fetch_alerts.sh output format).
"""

import csv
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: parse_csv_services.py <csv_path>", file=sys.stderr)
        return 1

    csv_path = sys.argv[1]

    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)

            if not reader.fieldnames or "service" not in reader.fieldnames:
                print(
                    f"ERROR: CSV missing 'service' column: {csv_path}",
                    file=sys.stderr,
                )
                return 1

            services = {
                row["service"].strip()
                for row in reader
                if row.get("service", "").strip()
            }

    except FileNotFoundError:
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Could not read CSV {csv_path}: {exc}", file=sys.stderr)
        return 1

    # Print sorted, comma-separated list (empty string if no services)
    print(",".join(sorted(services)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
