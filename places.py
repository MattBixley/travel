#!/usr/bin/env python3
"""Turn the places in a trip file into map coordinates.

Lookups are offline — generate.py never touches the network. Coordinates come from
one of two places, in this order:

  1. an explicit `coords: [lat, lon]` on the item itself
  2. places.yaml, the committed coordinate cache

`scripts/geocode.py` fills places.yaml in for you. Anything that can't be resolved
is reported as a miss and simply left off the map.
"""
from __future__ import annotations

import os

try:
    import yaml
except ImportError:
    raise SystemExit("Missing dependency. Run: pip install pyyaml")

ROOT = os.path.dirname(os.path.abspath(__file__))
PLACES_FILE = os.path.join(ROOT, "places.yaml")

# Marker colours, matching the timeline's left borders in PAGE_CSS.
KIND_COLOURS = {"flight": "#0a58ca", "stay": "#1a9e6c",
                "car": "#d97706", "activity": "#7c3aed", "other": "#0891b2"}

# Top-level keys with dedicated handling. Anything else that looks like a list of
# bookings is mapped generically, so adding a section to a trip file puts pins on
# the map without needing a code change here.
KNOWN_SECTIONS = {"trip", "flights", "stays", "cars", "activities"}


def generic_sections(data: dict) -> list[tuple[str, list[dict]]]:
    """(name, items) for every top-level section we have no special case for."""
    out = []
    for key, value in (data or {}).items():
        if key in KNOWN_SECTIONS or not isinstance(value, list):
            continue
        items = [i for i in value if isinstance(i, dict)]
        if items:
            out.append((key, items))
    return out


def norm(s) -> str:
    """Normalise a place name so 'Kyoto  Station' and 'kyoto station' agree."""
    return " ".join(str(s).strip().lower().split())


def as_latlon(value):
    """Coerce [lat, lon] or {lat:, lon:} into a (lat, lon) tuple, or None."""
    if value is None:
        return None
    if isinstance(value, dict):
        if "lat" not in value or "lon" not in value:
            return None
        value = [value["lat"], value["lon"]]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat, lon = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return (lat, lon)


def load_places(path: str = PLACES_FILE) -> dict:
    """Read places.yaml into {'airports': {CODE: (lat,lon)}, 'places': {norm: (lat,lon)}}."""
    out = {"airports": {}, "places": {}}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    for code, v in (raw.get("airports") or {}).items():
        ll = as_latlon(v)
        if ll:
            out["airports"][str(code).strip().upper()] = ll
    for name, v in (raw.get("places") or {}).items():
        ll = as_latlon(v)
        if ll:
            out["places"][norm(name)] = ll
    return out


def save_places(data: dict, path: str = PLACES_FILE) -> None:
    """Write the cache back out, sorted, so diffs stay readable."""
    body = {
        "airports": {k: [round(v[0], 6), round(v[1], 6)]
                     for k, v in sorted(data.get("airports", {}).items())},
        "places": {k: [round(v[0], 6), round(v[1], 6)]
                   for k, v in sorted(data.get("places", {}).items())},
    }
    header = (
        "# Coordinate cache for the maps on each trip page.\n"
        "# Airports are keyed by IATA code, everything else by name (case-insensitive).\n"
        "# Values are [lat, lon]. Extend with: python scripts/geocode.py\n"
        "# Hand-editing is fine — nudge a marker by editing its numbers.\n\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(body, fh, sort_keys=True, allow_unicode=True,
                       default_flow_style=None)


def _lookup(places: dict, candidates: list[str]):
    """First candidate name with a cached coordinate wins."""
    for c in candidates:
        if not c:
            continue
        ll = places["places"].get(norm(c))
        if ll:
            return ll
    return None


def flight_endpoint_queries(side: dict) -> list[str]:
    """Names worth trying for one end of a flight, best first.

    The IATA code comes first on purpose: cities with more than one airport make
    '<city> Airport' ambiguous — 'Tokyo Airport' geocodes to Narita, so an HND
    flight would land a marker at the wrong airport.
    """
    city, airport = side.get("city"), side.get("airport")
    out = []
    if airport:
        out.append(f"{airport} Airport")
    if city:
        out.append(f"{city} Airport")
        out.append(str(city))
    return out


def stay_queries(stay: dict) -> list[str]:
    name, city, addr = stay.get("name"), stay.get("city"), stay.get("address")
    out = []
    if name and city:
        out.append(f"{name}, {city}")
    if name:
        out.append(str(name))
    if addr:
        out.append(str(addr))
    if city:
        out.append(str(city))
    return out


def car_queries(leg: dict, car: dict) -> list[str]:
    """Names worth trying for a car depot, most specific first.

    Depot names carry a trailing qualifier that geocoders choke on
    ('Brisbane Airport, Terminal Building' matches nothing), so fall back to the
    leading chunk of the name before giving up.
    """
    place = leg.get("place")
    out = []
    if place:
        out.append(str(place))
        parts = [p.strip() for p in str(place).split(",") if p.strip()]
        if len(parts) > 1:
            out.append(parts[0])
    return [q for i, q in enumerate(out) if q not in out[:i]]


def normalise_activity(act: dict) -> dict:
    """Flatten either shape of activity entry into one form.

    Two spellings are accepted, because both are natural to write:

        start: 2026-08-23 08:00        # simple form
        end:   2026-08-23 16:00
        place: Great Barrier Reef
        tz:    Australia/Brisbane

        pickup:  { place: ..., tz: ..., time: ... }    # same shape as `cars`
        dropoff: { place: ..., tz: ..., time: ... }

    Returns a dict with start/end/start_tz/end_tz/place plus the original's other
    keys. `end` may be None, which generate.py turns into an hour.
    """
    out = dict(act)
    # `time:` is accepted as an alias for `start:` — it's what people reach for
    # when a section only has one moment in it.
    if out.get("start") is None and out.get("time") is not None:
        out["start"] = out["time"]
    pickup, dropoff = act.get("pickup"), act.get("dropoff")
    if isinstance(pickup, dict):
        out.setdefault("place", pickup.get("place"))
        out["start"] = pickup.get("time", out.get("start"))
        out["start_tz"] = pickup.get("tz", act.get("tz"))
        if isinstance(dropoff, dict):
            out["end"] = dropoff.get("time")
            out["end_tz"] = dropoff.get("tz", out["start_tz"])
            out.setdefault("place", dropoff.get("place"))
        else:
            out["end"] = act.get("end")
            out["end_tz"] = out["start_tz"]
    else:
        out["start_tz"] = act.get("tz")
        out["end_tz"] = act.get("tz")
    return out


def activity_queries(act: dict) -> list[str]:
    """Names worth trying for an activity, most specific first."""
    act = normalise_activity(act)
    name, place = act.get("name"), act.get("place")
    addr, city = act.get("address"), act.get("city")
    out = []
    if place and city:
        out.append(f"{place}, {city}")
    if place:
        out.append(str(place))
    if addr:
        out.append(str(addr))
    if name and city:
        out.append(f"{name}, {city}")
    if city:
        out.append(str(city))
    return [q for i, q in enumerate(out) if q not in out[:i]]


def resolve_side(side: dict, places: dict):
    """Coordinates for one end of a flight: explicit coords, then airport code, then name."""
    ll = as_latlon(side.get("coords"))
    if ll:
        return ll, None
    code = str(side.get("airport", "")).strip().upper()
    if code and code in places["airports"]:
        return places["airports"][code], None
    ll = _lookup(places, flight_endpoint_queries(side))
    if ll:
        return ll, None
    return None, flight_endpoint_queries(side)[0] if flight_endpoint_queries(side) else "?"


def trip_points(data: dict, places: dict) -> tuple[list[dict], list[str]]:
    """Every mappable location in a trip, in the order it happens.

    Returns (points, misses). A point is {lat, lon, kind, label, when, detail}.
    `misses` holds the best-guess query string for each location we had no
    coordinate for, so the caller can tell the user what to geocode.
    """
    # Imported here to avoid a circular import at module load.
    from generate import parse_local

    points, misses = [], []

    for f in data.get("flights") or []:
        dep = parse_local(f["depart"], f["from"]["tz"])
        arr = parse_local(f["arrive"], f["to"]["tz"])
        for side, when, role in ((f["from"], dep, "from"), (f["to"], arr, "to")):
            ll, miss = resolve_side(side, places)
            if not ll:
                misses.append(miss)
                continue
            verb = "Depart" if role == "from" else "Arrive"
            points.append(dict(
                lat=ll[0], lon=ll[1], kind="flight", when=when,
                label=f"{side.get('city', side.get('airport', ''))} "
                      f"({side.get('airport', '')})".strip(),
                detail=f"{verb} {f.get('flight_no', '')} — "
                       f"{when.strftime('%a %d %b, %H:%M')}"))

    for s in data.get("stays") or []:
        ci = parse_local(s["check_in"], s["tz"])
        ll = as_latlon(s.get("coords")) or _lookup(places, stay_queries(s))
        if not ll:
            misses.append(stay_queries(s)[0] if stay_queries(s) else "?")
            continue
        points.append(dict(
            lat=ll[0], lon=ll[1], kind="stay", when=ci,
            label=str(s.get("name", s.get("city", "Stay"))),
            detail=f"Check-in {s['check_in']} · check-out {s['check_out']}"))

    for c in data.get("cars") or []:
        seen = set()
        for end, time_key in (("pickup", "time"), ("dropoff", "time")):
            leg = c[end]
            when = parse_local(leg[time_key], leg["tz"])
            ll = as_latlon(leg.get("coords")) or _lookup(places, car_queries(leg, c))
            if not ll:
                misses.append(car_queries(leg, c)[0] if car_queries(leg, c) else "?")
                continue
            # Same depot for pickup and dropoff: one marker, both times.
            if ll in seen:
                for p in points:
                    if p["kind"] == "car" and (p["lat"], p["lon"]) == ll:
                        p["detail"] += f" · Dropoff {when.strftime('%a %d %b, %H:%M')}"
                        break
                continue
            seen.add(ll)
            points.append(dict(
                lat=ll[0], lon=ll[1], kind="car", when=when,
                label=f"{c.get('vendor', 'Car')} — {leg.get('place', '')}",
                detail=f"{end.title()} {when.strftime('%a %d %b, %H:%M')}"))

    for raw in data.get("activities") or []:
        a = normalise_activity(raw)
        st = parse_local(a["start"], a["start_tz"])
        ll = as_latlon(a.get("coords")) or _lookup(places, activity_queries(raw))
        if not ll:
            qs = activity_queries(raw)
            misses.append(qs[0] if qs else "?")
            continue
        detail = st.strftime("%a %d %b, %H:%M")
        if a.get("place"):
            detail += f" · {a['place']}"
        points.append(dict(
            lat=ll[0], lon=ll[1], kind="activity", when=st,
            label=str(a.get("name", "Activity")), detail=detail))

    for section, items in generic_sections(data):
        for raw in items:
            a = normalise_activity(raw)
            if a.get("start") is None or a.get("start_tz") is None:
                continue        # generate.py reports these; don't map a guess
            try:
                st = parse_local(a["start"], a["start_tz"])
            except Exception:
                continue
            ll = as_latlon(a.get("coords")) or _lookup(places, activity_queries(raw))
            if not ll:
                qs = activity_queries(raw)
                if qs:
                    misses.append(qs[0])
                continue
            detail = st.strftime("%a %d %b, %H:%M")
            if a.get("place"):
                detail += f" · {a['place']}"
            points.append(dict(
                lat=ll[0], lon=ll[1], kind="other", when=st,
                label=str(a.get("name") or section.rstrip("s").title()),
                detail=detail))

    points.sort(key=lambda p: p["when"])
    # Preserve order but drop duplicate miss queries.
    seen_miss, unique = set(), []
    for m in misses:
        if m not in seen_miss:
            seen_miss.add(m)
            unique.append(m)
    return points, unique


def all_queries(data: dict) -> list[str]:
    """Every name worth geocoding for one trip, best candidate first per location."""
    out = []
    for f in data.get("flights") or []:
        for side in (f["from"], f["to"]):
            if not as_latlon(side.get("coords")):
                out.append((str(side.get("airport", "")).strip().upper(),
                            flight_endpoint_queries(side)))
    for s in data.get("stays") or []:
        if not as_latlon(s.get("coords")):
            out.append((None, stay_queries(s)))
    for c in data.get("cars") or []:
        for end in ("pickup", "dropoff"):
            if not as_latlon(c[end].get("coords")):
                out.append((None, car_queries(c[end], c)))
    for a in data.get("activities") or []:
        if not as_latlon(a.get("coords")):
            out.append((None, activity_queries(a)))
    for _, items in generic_sections(data):
        for a in items:
            if not as_latlon(a.get("coords")):
                qs = activity_queries(a)
                if qs:
                    out.append((None, qs))
    return out
