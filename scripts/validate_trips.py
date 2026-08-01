#!/usr/bin/env python3
"""Validate trip YAML files before they reach a commit or the CI build.

Checks the things that have actually broken the build:
  1. the file is parseable YAML
  2. every `tz` is an IANA name that ZoneInfo can load (not NZST/AEST)
  3. every date-time parses as "YYYY-MM-DD HH:MM"
  4. the keys generate.py dereferences are present

It also warns — without failing — about locations that have no coordinates in
places.yaml, since those are silently left off the trip map.

Usage:
    validate_trips.py                 # check trips/*.yaml in the working tree
    validate_trips.py FILE [FILE...]  # check specific files
    validate_trips.py --staged        # check the staged content of trips/*.yaml
"""
import glob
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yaml
except ImportError:
    raise SystemExit("Missing dependency. Run: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_tz(tz, where, errors):
    if not isinstance(tz, str) or not tz.strip():
        errors.append(f"{where}: tz is empty")
        return
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        errors.append(
            f"{where}: tz {tz!r} is not an IANA timezone "
            f"(use e.g. Pacific/Auckland, Australia/Brisbane — not NZST/AEST)"
        )


def check_time(value, where, errors):
    s = str(value).strip()
    fmt = "%Y-%m-%d %H:%M:%S" if s.count(":") == 2 else "%Y-%m-%d %H:%M"
    try:
        datetime.strptime(s, fmt)
    except ValueError:
        errors.append(f"{where}: {value!r} is not 'YYYY-MM-DD HH:MM'")


def get(mapping, key, where, errors):
    """Fetch a required key, recording an error if it is missing."""
    if not isinstance(mapping, dict):
        errors.append(f"{where}: expected a mapping, got {type(mapping).__name__}")
        return None
    if key not in mapping:
        errors.append(f"{where}: missing required key {key!r}")
        return None
    return mapping[key]


def check_data(data, errors):
    trip = get(data, "trip", "top level", errors)
    if trip is not None:
        get(trip, "slug", "trip", errors)
        get(trip, "name", "trip", errors)

    for i, f in enumerate(data.get("flights") or [], 1):
        w = f"flights[{i}]"
        for end in ("from", "to"):
            side = get(f, end, w, errors)
            if side is not None:
                get(side, "airport", f"{w}.{end}", errors)
                tz = get(side, "tz", f"{w}.{end}", errors)
                if tz is not None:
                    check_tz(tz, f"{w}.{end}", errors)
        for field in ("depart", "arrive"):
            t = get(f, field, w, errors)
            if t is not None:
                check_time(t, f"{w}.{field}", errors)

    for i, s in enumerate(data.get("stays") or [], 1):
        w = f"stays[{i}]"
        tz = get(s, "tz", w, errors)
        if tz is not None:
            check_tz(tz, w, errors)
        for field in ("check_in", "check_out"):
            t = get(s, field, w, errors)
            if t is not None:
                check_time(t, f"{w}.{field}", errors)

    for i, raw in enumerate(data.get("activities") or [], 1):
        w = f"activities[{i}]"
        get(raw, "name", w, errors)
        # Two shapes are allowed: start/end/tz, or pickup/dropoff like `cars`.
        try:
            import places
            a = places.normalise_activity(raw)
        except Exception:
            a = raw
        if not isinstance(a, dict):
            continue
        if a.get("start") is None:
            errors.append(f"{w}: needs either `start:` or a `pickup:` block")
        else:
            check_time(a["start"], f"{w}.start", errors)
        if a.get("start_tz") is None:
            errors.append(f"{w}: missing a timezone — either `tz:` on the activity "
                          f"or `tz:` inside `pickup:`")
        else:
            check_tz(a["start_tz"], w, errors)
        # `end` is optional; generate.py gives it an hour if it's absent.
        if a.get("end") is not None:
            check_time(a["end"], f"{w}.end", errors)
            if a.get("end_tz") is not None:
                check_tz(a["end_tz"], f"{w} (end)", errors)

    for i, c in enumerate(data.get("cars") or [], 1):
        w = f"cars[{i}]"
        for end in ("pickup", "dropoff"):
            leg = get(c, end, w, errors)
            if leg is not None:
                get(leg, "place", f"{w}.{end}", errors)
                tz = get(leg, "tz", f"{w}.{end}", errors)
                if tz is not None:
                    check_tz(tz, f"{w}.{end}", errors)
                t = get(leg, "time", f"{w}.{end}", errors)
                if t is not None:
                    check_time(t, f"{w}.{end}.time", errors)


def map_warnings(data):
    """Locations with no coordinates. Not an error — they're just left off the map."""
    try:
        import places
    except Exception:
        return []
    try:
        _, misses = places.trip_points(data, places.load_places())
    except Exception:
        # A bad date or tz already shows up as a hard error above; don't
        # double-report it as a map problem.
        return []
    return [f"no coordinates for {m!r} — it will be missing from the map "
            f"(run: python scripts/geocode.py)" for m in misses]


def check_source(label, text):
    """Return (errors, warnings) for one trip file."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return [f"YAML will not parse:\n{e}"], []
    if data is None:
        return ["file is empty"], []
    if not isinstance(data, dict):
        return [f"top level must be a mapping, got {type(data).__name__}"], []
    errors = []
    check_data(data, errors)
    return errors, ([] if errors else map_warnings(data))


def staged_trip_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", "trips"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [p for p in out.split("\n") if p.endswith((".yaml", ".yml"))]


def read_staged(path):
    return subprocess.run(
        ["git", "show", f":{path}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout


def main(argv):
    staged = "--staged" in argv
    paths = [a for a in argv if not a.startswith("-")]

    if staged:
        sources = [(p, read_staged(p)) for p in staged_trip_files()]
    else:
        if not paths:
            paths = sorted(glob.glob(os.path.join(ROOT, "trips", "*.yaml")))
            paths += sorted(glob.glob(os.path.join(ROOT, "trips", "*.yml")))
        sources = [(p, open(p, encoding="utf-8").read()) for p in paths]

    if not sources:
        return 0

    failed = 0
    for label, text in sources:
        errors, warnings = check_source(label, text)
        rel = os.path.relpath(label, ROOT) if os.path.isabs(label) else label
        if errors:
            failed += 1
            print(f"FAIL {rel}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"ok   {rel}")
        for w in warnings:
            print(f"  warning: {w}")

    if failed:
        print(f"\n{failed} trip file(s) would break the build.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
