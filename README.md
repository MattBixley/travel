# Travel Tracker (own-it path)

One source of truth for your trips → a shareable GitHub Pages site **and** a calendar
feed you and your wife subscribe to. Optionally auto-fed from Gmail. No servers, all free.

```
travel-tracker/
├── trips/              one YAML file per trip  (edit these)
│   └── 2026-japan.yaml sample
├── generate.py         builds docs/ from trips/
├── docs/               GitHub Pages output (HTML pages + .ics feeds)
└── apps-script/Code.gs Gmail → Google Calendar automation (optional)
```

## 1. Add a trip
Copy `trips/2026-japan.yaml`, rename it, fill in flights / stays / cars. Times are
local with an IANA `tz` (e.g. `Asia/Tokyo`, `Pacific/Auckland`) so cross-timezone
flights land correctly.

## 2. Generate
```bash
pip install pyyaml        # once
python generate.py
```
Produces in `docs/`:
- `index.html` — overview of all trips
- `<slug>.html` — a clean timeline page per trip
- `<slug>.ics` — per-trip calendar feed
- `all.ics` — every trip in one feed

## 3. Publish (GitHub Pages — same as your mattbixley/spain workflow)
1. Push this folder to a GitHub repo.
2. Repo **Settings → Pages → Source: GitHub Actions**. The included workflow
   (`.github/workflows/build.yml`) runs `generate.py` and publishes `docs/` on every push.
3. Your site is at `https://<user>.github.io/<repo>/`.
   - Want it private? Use a **private repo with Pages enabled** (GitHub paid tiers), or
     keep trips non-sensitive. The `.ics` URL is unguessable-ish but not secret.

## 4. Share with your wife (the important bit)
Send her the Pages URL, and have you both **subscribe to the `.ics` by URL** in your
phone calendars — that way every regenerate/push updates both calendars automatically:
- **iPhone:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed
  Calendar → paste the `all.ics` URL.
- **Google Calendar (web):** Other calendars → **+** → From URL → paste the `all.ics` URL.

## 5. (Optional) Automate from Gmail — Option A3
See `apps-script/Code.gs`. It runs inside your Google account on a schedule, reads a
Gmail `Travel` label, parses Schema.org reservation data embedded in confirmation
emails (Air NZ / Booking.com / Expedia / Entero and any others), and writes events
straight to a shared Google Calendar. Setup steps are in the file header.

Add senders by editing the Gmail filter's `from:` list, e.g.
`from:(airnewzealand.co.nz OR booking.com OR expedia.com OR entero)` — the parser
is sender-agnostic, so any operator whose confirmations carry structured data flows
through automatically once the label is applied.

Two ways to combine with this repo:
- **Calendar-only:** let Apps Script populate the shared calendar directly; the YAML repo
  becomes your nicely-formatted webpage for the trips you want to write up.
- **Repo-as-truth:** keep entering trips in YAML (full control, archived in git) and use
  Apps Script just to catch bookings you'd otherwise forget.

## Tips
- Re-run `generate.py` after editing any trip; commit and push to update the live site.
- A GitHub Action can run `generate.py` on every push so you never run it locally.
- Not every confirmation email contains parseable structured data — the script labels
  those `Travel/Needs-Review` so you can add them by hand (or paste into a YAML file).
