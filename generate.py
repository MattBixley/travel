#!/usr/bin/env python3
"""
Travel tracker generator.

Reads every trips/*.yaml file and writes, into docs/ (GitHub Pages root):
  - docs/index.html        an overview linking to each trip
  - docs/<slug>.html       a clean timeline page per trip
  - docs/<slug>.ics         a calendar feed per trip (subscribe in your phone)
  - docs/all.ics            every event across all trips in one feed

No third-party services. Only dependency: PyYAML  (pip install pyyaml)

Run:  python generate.py
"""

from __future__ import annotations
import html
import glob
import os
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:
    raise SystemExit("Missing dependency. Run: pip install pyyaml")

ROOT = os.path.dirname(os.path.abspath(__file__))
TRIPS_DIR = os.path.join(ROOT, "trips")
DOCS_DIR = os.path.join(ROOT, "docs")

# ---------------------------------------------------------------- helpers

def parse_local(s: str, tz: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' (or with seconds) as tz-aware datetime."""
    s = str(s).strip()
    fmt = "%Y-%m-%d %H:%M:%S" if s.count(":") == 2 else "%Y-%m-%d %H:%M"
    return datetime.strptime(s, fmt).replace(tzinfo=ZoneInfo(tz))


def to_utc_stamp(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")


def ics_escape(text: str) -> str:
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def fold(line: str) -> str:
    """RFC5545 line folding at 75 octets."""
    out, cur = [], line
    while len(cur.encode("utf-8")) > 75:
        # find a safe cut <= 75 bytes
        cut = 75
        while len(cur[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(cur[:cut])
        cur = " " + cur[cut:]
    out.append(cur)
    return "\r\n".join(out)


# ---------------------------------------------------------------- model

def trip_events(data: dict) -> list[dict]:
    """Flatten a trip dict into a list of calendar events."""
    events = []
    slug = data["trip"]["slug"]

    for f in data.get("flights") or []:
        dep = parse_local(f["depart"], f["from"]["tz"])
        arr = parse_local(f["arrive"], f["to"]["tz"])
        summary = f"✈ {f['flight_no']} {f['from']['airport']}→{f['to']['airport']}"
        desc = (f"{f.get('airline','')} {f['flight_no']}\n"
                f"{f['from']['city']} ({f['from']['airport']}) -> "
                f"{f['to']['city']} ({f['to']['airport']})\n"
                f"Seat: {f.get('seat','-')}\n"
                f"Confirmation: {f.get('confirmation','-')}\n"
                f"Booked via: {f.get('booked_via','-')}\n"
                f"{f.get('link','')}")
        events.append(dict(uid=f"{slug}-flight-{f.get('confirmation','')}-{f['flight_no']}-{to_utc_stamp(dep)}",
                           start=dep, end=arr, summary=summary, desc=desc,
                           location=f"{f['from']['city']} {f['from']['airport']}",
                           kind="flight"))

    for s in data.get("stays") or []:
        ci = parse_local(s["check_in"], s["tz"])
        co = parse_local(s["check_out"], s["tz"])
        summary = f"\U0001f3e8 {s['name']}"
        desc = (f"{s['name']}, {s.get('city','')}\n"
                f"{s.get('address','')}\n"
                f"Check-in {s['check_in']} / Check-out {s['check_out']}\n"
                f"Confirmation: {s.get('confirmation','-')}\n"
                f"Booked via: {s.get('booked_via','-')}\n"
                f"{s.get('link','')}")
        # one all-stay event spanning the nights
        events.append(dict(uid=f"{slug}-stay-{s.get('confirmation','')}-{to_utc_stamp(ci)}",
                           start=ci, end=co, summary=summary, desc=desc,
                           location=s.get("address", s.get("city", "")),
                           kind="stay"))

    for c in data.get("cars") or []:
        pu = parse_local(c["pickup"]["time"], c["pickup"]["tz"])
        do = parse_local(c["dropoff"]["time"], c["dropoff"]["tz"])
        summary = f"\U0001f697 {c['vendor']} ({c.get('type','car')})"
        desc = (f"{c['vendor']} - {c.get('type','')}\n"
                f"Pickup: {c['pickup']['place']} {c['pickup']['time']}\n"
                f"Dropoff: {c['dropoff']['place']} {c['dropoff']['time']}\n"
                f"Confirmation: {c.get('confirmation','-')}\n"
                f"Booked via: {c.get('booked_via','-')}\n"
                f"{c.get('link','')}")
        events.append(dict(uid=f"{slug}-car-{c.get('confirmation','')}-{to_utc_stamp(pu)}",
                           start=pu, end=do, summary=summary, desc=desc,
                           location=c["pickup"]["place"], kind="car"))

    events.sort(key=lambda e: e["start"])
    return events


# ---------------------------------------------------------------- ics

def build_ics(events: list[dict], cal_name: str) -> str:
    now = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//travel-tracker//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", fold(f"X-WR-CALNAME:{ics_escape(cal_name)}")]
    for e in events:
        lines += ["BEGIN:VEVENT",
                  fold(f"UID:{e['uid']}@travel-tracker"),
                  f"DTSTAMP:{now}",
                  f"DTSTART:{to_utc_stamp(e['start'])}",
                  f"DTEND:{to_utc_stamp(e['end'])}",
                  fold(f"SUMMARY:{ics_escape(e['summary'])}"),
                  fold(f"DESCRIPTION:{ics_escape(e['desc'])}"),
                  fold(f"LOCATION:{ics_escape(e['location'])}"),
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- html

PAGE_CSS = """
*{box-sizing:border-box} body{font:16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;
margin:0;color:#1a1a1a;background:#f6f7f9} .wrap{max-width:760px;margin:0 auto;padding:24px}
h1{margin:.2em 0} a{color:#0a58ca} .meta{color:#666;margin-bottom:1.5em}
.ev{background:#fff;border:1px solid #e3e6ea;border-radius:12px;padding:14px 16px;margin:10px 0;
border-left:5px solid #999} .ev.flight{border-left-color:#0a58ca}
.ev.stay{border-left-color:#1a9e6c} .ev.car{border-left-color:#d97706}
.ev h3{margin:0 0 4px} .ev .when{color:#444;font-size:.92em} .ev .det{color:#555;
font-size:.9em;white-space:pre-line;margin-top:6px} .sub{margin:1em 0;padding:12px 16px;
background:#eef3ff;border-radius:10px;font-size:.92em} .card{display:block;background:#fff;
border:1px solid #e3e6ea;border-radius:12px;padding:16px;margin:10px 0;text-decoration:none;color:inherit}
.card:hover{border-color:#0a58ca}
"""

def fmt_when(e: dict) -> str:
    s, en = e["start"], e["end"]
    if s.date() == en.date():
        return f"{s.strftime('%a %d %b %Y, %H:%M')} – {en.strftime('%H:%M')}"
    return f"{s.strftime('%a %d %b %Y, %H:%M')} → {en.strftime('%a %d %b %Y, %H:%M')}"


def trip_html(data: dict, events: list[dict]) -> str:
    t = data["trip"]
    slug = t["slug"]
    rows = []
    for e in events:
        rows.append(
            f'<div class="ev {e["kind"]}"><h3>{html.escape(e["summary"])}</h3>'
            f'<div class="when">{html.escape(fmt_when(e))}</div>'
            f'<div class="det">{html.escape(e["desc"])}</div></div>')
    travellers = ", ".join(t.get("travellers", []))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t['name'])}</title><style>{PAGE_CSS}</style></head><body><div class="wrap">
<p><a href="index.html">&larr; All trips</a></p>
<h1>{html.escape(t['name'])}</h1>
<div class="meta">{html.escape(str(t.get('start','')))} &ndash; {html.escape(str(t.get('end','')))}
&middot; {html.escape(travellers)}</div>
<div class="sub">Subscribe in your phone's calendar (and share with your wife):
<br><code>{slug}.ics</code> &mdash; add by URL so updates sync automatically.</div>
{''.join(rows)}
<p class="meta">{html.escape(t.get('notes',''))}</p>
</div></body></html>"""


def index_html(trips: list[dict]) -> str:
    cards = []
    for t in sorted(trips, key=lambda x: str(x["trip"].get("start", ""))):
        tr = t["trip"]
        cards.append(
            f'<a class="card" href="{tr["slug"]}.html"><h3>{html.escape(tr["name"])}</h3>'
            f'<div class="meta">{html.escape(str(tr.get("start","")))} &ndash; '
            f'{html.escape(str(tr.get("end","")))} &middot; '
            f'{html.escape(", ".join(tr.get("travellers", [])))}</div></a>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Our Travel</title><style>{PAGE_CSS}</style></head><body><div class="wrap">
<h1>Our Travel</h1>
<div class="sub">Subscribe to <code>all.ics</code> for every trip in one calendar.</div>
{''.join(cards)}
</div></body></html>"""


# ---------------------------------------------------------------- main

def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(TRIPS_DIR, "*.yaml")) +
                   glob.glob(os.path.join(TRIPS_DIR, "*.yml")))
    if not files:
        raise SystemExit(f"No trip files found in {TRIPS_DIR}")

    all_events, trips = [], []
    for fp in files:
        with open(fp, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        trips.append(data)
        evs = trip_events(data)
        all_events += evs
        slug = data["trip"]["slug"]
        with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(trip_html(data, evs))
        with open(os.path.join(DOCS_DIR, f"{slug}.ics"), "w", encoding="utf-8") as fh:
            fh.write(build_ics(evs, data["trip"]["name"]))
        print(f"  {slug}: {len(evs)} events")

    all_events.sort(key=lambda e: e["start"])
    with open(os.path.join(DOCS_DIR, "all.ics"), "w", encoding="utf-8") as fh:
        fh.write(build_ics(all_events, "Our Travel"))
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html(trips))

    print(f"Done. {len(trips)} trip(s), {len(all_events)} events -> {DOCS_DIR}")


if __name__ == "__main__":
    main()
