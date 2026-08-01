# Travel Tracker

A personal travel tracker: describe each trip in a small YAML file, and a script turns it
into a shareable website, a route map, and a calendar feed. Optionally auto-fed from Gmail or
paired with TripIt. No servers, all free.

Live site: **https://mattbixley.github.io/travel/**

## Read this first

**[HOWTO.md](HOWTO.md) is the complete guide** — adding trips, publishing, sharing,
TripIt setup, Gmail automation, and troubleshooting. Start there.

## 30-second version

```bash
cd /mnt/c/Users/MattBixley/Code/travel-tracker
cp trips/EXAMPLE-japan.yaml trips/2026-fiji.yaml   # copy the template
# edit the new file with your real bookings
git add trips/2026-fiji.yaml && git commit -m "Add Fiji 2026" && git push
```
The push triggers a GitHub Action that rebuilds and republishes the site automatically.

Share the site URL with your wife, and both subscribe to
`https://mattbixley.github.io/travel/all.ics` in your phone calendars.

> `trips/EXAMPLE-japan.yaml` is fake sample data showing the format — delete it once you've
> added a real trip.

## Layout

```
trips/            one YAML file per trip   ← you edit these
generate.py       builds docs/ from trips/
places.py         resolves place names to map coordinates
places.yaml       coordinate cache for the maps   ← commit this
scripts/          geocode.py (fill places.yaml) + validate_trips.py (pre-push checks)
docs/             generated site (published by GitHub Pages)
apps-script/      optional Gmail → Google Calendar automation
HOWTO.md          the full guide
```

After adding a trip, run `python scripts/geocode.py` once to look up coordinates for the new
places, and commit `places.yaml`. The build itself never geocodes.
