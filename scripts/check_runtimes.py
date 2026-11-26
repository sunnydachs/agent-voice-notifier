#!/usr/bin/env python3
"""Fail when the CI matrix tests a runtime that no longer receives security patches.

    python3 scripts/check_runtimes.py

Exit 0 when every listed version is still supported. If the schedule cannot be
fetched (offline, API down, rate limited) it reports that and exits 0 — a
third-party outage must not fail a build.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

SCHEDULES = {
    "python-version": ("python", "https://endoflife.date/api/python.json"),
}


def listed_versions(key: str) -> dict[str, set[str]]:
    """{workflow file: {cycle, ...}} for every matrix entry using this key."""
    pattern = re.compile(r"^\s*" + re.escape(key) + r":\s*\[([^\]]*)\]", re.MULTILINE)
    found: dict[str, set[str]] = {}
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text()
        cycles: set[str] = set()
        for match in pattern.finditer(text):
            for raw in match.group(1).split(","):
                entry = raw.strip().strip("'\"")
                if entry:
                    cycles.add(entry.removesuffix(".x"))
        if cycles:
            found[path.name] = cycles
    return found


def fetch_schedule(url: str) -> dict[str, dt.date | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "check-runtimes/1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode())
    schedule: dict[str, dt.date | None] = {}
    for entry in data:
        eol = entry.get("eol")
        if eol is True:
            schedule[str(entry["cycle"])] = dt.date(1970, 1, 1)  # already EOL
        elif eol is False or eol is None:
            schedule[str(entry["cycle"])] = None
        else:
            try:
                schedule[str(entry["cycle"])] = dt.date.fromisoformat(str(eol))
            except ValueError:
                schedule[str(entry["cycle"])] = None
    return schedule


def main() -> int:
    today = dt.date.today()
    failures: list[str] = []
    checked = 0

    for key, (product, url) in SCHEDULES.items():
        versions = listed_versions(key)
        if not versions:
            continue
        try:
            schedule = fetch_schedule(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"{product}: could not read the release schedule ({exc}) - skipping check")
            continue

        for workflow, cycles in sorted(versions.items()):
            for cycle in sorted(cycles, key=lambda c: [int(part) for part in c.split(".")]):
                checked += 1
                if cycle not in schedule:
                    print(f"  {workflow}: {product} {cycle} not in the schedule - check it manually")
                    continue
                eol = schedule[cycle]
                if eol is None:
                    print(f"  {workflow}: {product} {cycle} supported")
                elif eol <= today:
                    print(f"  {workflow}: {product} {cycle} reached end of life on {eol}; drop it")
                    failures.append(f"{workflow}: {product} {cycle} EOL {eol}")
                else:
                    print(f"  {workflow}: {product} {cycle} supported until {eol}")

    if failures:
        print(f"\n{len(failures)} version(s) in the CI matrix are end-of-life:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print(f"\nall {checked} matrix version(s) are still supported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
