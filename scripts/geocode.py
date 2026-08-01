#!/usr/bin/env python3
"""Fill places.yaml with coordinates for anything the maps are missing.

Run this by hand after adding a trip, then commit places.yaml. The build itself
never geocodes — it only reads the cache — so CI stays offline and repeatable.

    python scripts/geocode.py              # look up what's missing, write places.yaml
    python scripts/geocode.py --dry-run    # show what it would look up
    python scripts/geocode.py --force      # re-look-up entries already cached

Uses Nominatim, which asks for no more than one request per second and a real
User-Agent. Both are honoured below. Be kind to it: this only ever runs for the
handful of places you just added.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402  (after sys.path fix)

from places import (  # noqa: E402
    ROOT, all_queries, load_places, norm, save_places,
)

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "travel-tracker/1.0 (+https://github.com/MattBixley/travel)"
DELAY_SECONDS = 1.1


def geocode(query: str):
    """One Nominatim lookup. Returns (lat, lon) or None."""
    url = f"{NOMINATIM}?" + urllib.parse.urlencode(
        {"format": "json", "limit": "1", "q": query})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            results = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"    ! request failed: {e}")
        return None
    except json.JSONDecodeError:
        print("    ! bad response")
        return None
    if not results:
        return None
    return (float(results[0]["lat"]), float(results[0]["lon"]))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be looked up, make no requests")
    ap.add_argument("--force", action="store_true",
                    help="look up names even if they are already cached")
    args = ap.parse_args(argv)

    cache = load_places()
    files = sorted(glob.glob(os.path.join(ROOT, "trips", "*.yaml")) +
                   glob.glob(os.path.join(ROOT, "trips", "*.yml")))

    # Collect one work item per unresolved location: (airport_code, [queries]).
    wanted = []
    for fp in files:
        with open(fp, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if data:
            wanted += all_queries(data)

    todo = []
    for code, queries in wanted:
        if not queries:
            continue
        if not args.force:
            if code and code in cache["airports"]:
                continue
            if any(norm(q) in cache["places"] for q in queries):
                continue
        key = ("airport", code) if code else ("place", norm(queries[0]))
        if key not in [k for k, _ in todo]:
            todo.append((key, queries))

    if not todo:
        print("Nothing to look up — every location already has coordinates.")
        return 0

    print(f"{len(todo)} location(s) to look up:")
    for _, queries in todo:
        print(f"  - {queries[0]}")
    if args.dry_run:
        print("\n--dry-run: no requests made, places.yaml untouched.")
        return 0

    print()
    requests_made = 0
    failed = []
    for (kind, key), queries in todo:
        ll, used = None, None
        # Walk the candidates: 'HND Airport' before 'Tokyo Airport', hotel name
        # before bare city, so we cache the most specific match available.
        for q in queries:
            if requests_made:
                time.sleep(DELAY_SECONDS)
            requests_made += 1
            ll = geocode(q)
            if ll:
                used = q
                break
        if not ll:
            print(f"  {queries[0]} ... no match")
            failed.append(queries[0])
            continue
        via = "" if used == queries[0] else f'  (matched "{used}")'
        print(f"  {queries[0]} ... {ll[0]:.5f}, {ll[1]:.5f}{via}")
        if kind == "airport":
            cache["airports"][key] = ll
        else:
            cache["places"][key] = ll

    save_places(cache)
    print(f"\nWrote {os.path.relpath(os.path.join(ROOT, 'places.yaml'), ROOT)}: "
          f"{len(cache['airports'])} airport(s), {len(cache['places'])} place(s).")
    if failed:
        print("\nNo match for these — add coordinates by hand, either in places.yaml\n"
              "or as `coords: [lat, lon]` on the item in the trip file:")
        for q in failed:
            print(f"  - {q}")
    print("\nCommit places.yaml so the build can use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
