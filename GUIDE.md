# Travel Tracker — How To Use Everything

This is the day-to-day guide for the system in this folder. For the why/options behind it,
see `PLAN.md`. For a quick file map, see `README.md`.

## What you have

```
travel-tracker/
├── trips/                 one YAML file per trip — your single source of truth
│   └── 2026-japan.yaml    a worked sample
├── generate.py            turns trips/ into the website + calendar feeds
├── docs/                  generated output (published by GitHub Pages)
│   ├── index.html         overview of all trips
│   ├── <slug>.html        a timeline page per trip
│   ├── <slug>.ics         calendar feed per trip
│   └── all.ics            every trip in one calendar
├── apps-script/Code.gs    optional: auto-pull bookings from Gmail into a shared calendar
├── .github/workflows/build.yml  auto-builds + publishes the site on every push
├── README.md              file map + setup
├── PLAN.md                options analysis
└── GUIDE.md               this file
```

There are two halves you can use together or separately:

- **The repo (YAML → site + .ics):** you enter trips, get a shareable webpage and calendar.
- **The Gmail automation (Apps Script):** confirmation emails flow straight onto a shared
  calendar with no typing.

---

## Part 1 — Adding and updating trips (the repo)

### Add a new trip
1. Copy `trips/2026-japan.yaml` to a new file, e.g. `trips/2027-fiji.yaml`.
2. Set `trip.slug` to something URL-safe and unique (e.g. `2027-fiji`). This becomes the page
   URL (`2027-fiji.html`) and calendar filename (`2027-fiji.ics`).
3. Fill in the sections you have. Any section can be empty or omitted.

### Rebuild
```bash
pip install pyyaml      # first time only
python generate.py
```
Then commit and push. If GitHub Pages is on (Part 3), the site updates itself.

### Editing rules that matter
- **Times are local** to where the event happens, written `YYYY-MM-DD HH:MM` (24-hour).
- Each time needs a **`tz`** — an IANA timezone like `Pacific/Auckland`, `Asia/Tokyo`,
  `Australia/Sydney`, `America/Los_Angeles`. This is what makes overnight/cross-timezone
  flights show the correct hours on every phone.
- `confirmation`, `seat`, `link`, `address`, `notes` are optional but show up in the calendar
  event description — handy at the airport or check-in desk.

---

## Part 2 — Adding additional resource types

The three built-in types are **flights**, **stays**, and **cars**. To add more of the same
type, just add another list item under that heading. Examples:

### Another flight (multi-leg trip)
```yaml
flights:
  - confirmation: NZ-XYZ
    airline: Air New Zealand
    flight_no: NZ5
    from: { airport: AKL, city: Auckland, tz: Pacific/Auckland }
    to:   { airport: NAN, city: Nadi,     tz: Pacific/Fiji }
    depart: 2027-07-01 19:30
    arrive: 2027-07-01 23:05
    booked_via: Air New Zealand app
```

### A campervan (use the `cars` section)
```yaml
cars:
  - confirmation: ENT-4456
    vendor: Entero
    type: 4-berth campervan
    pickup:  { place: Christchurch Depot, tz: Pacific/Auckland, time: 2027-07-02 10:00 }
    dropoff: { place: Queenstown Depot,   tz: Pacific/Auckland, time: 2027-07-09 16:00 }
    booked_via: Entero
    link: https://...
```

### A brand-new category (e.g. trains, tours, ferries)
The generator currently understands `flights`, `stays`, `cars`. To add a genuinely new type
(say `trains`), two small edits in `generate.py`:
1. In `trip_events()`, add a loop over `data.get("trains")` that builds events the same way the
   `cars` loop does (parse a start time + end time, set a `summary`, `desc`, `location`, and a
   `kind`).
2. Optionally add a colour for `.ev.train` in the `PAGE_CSS` block so it's visually distinct.

If you'd like, I can add a `trains`/`tours`/`activities` section for you — just say which.

---

## Part 3 — Publishing and sharing

### Turn on GitHub Pages (once)
1. Push this folder to a GitHub repo.
2. **Settings → Pages → Source: GitHub Actions** (this matches `.github/workflows/build.yml`).
3. Every push that touches `trips/`, `generate.py`, or the workflow rebuilds and republishes
   automatically. You can also run it by hand from the **Actions** tab (Run workflow).

Your site lives at `https://<your-user>.github.io/<repo>/`.

### Share with your wife
Send her the Pages URL, and have you both **subscribe to `all.ics` by URL** so any update
syncs to both calendars automatically:
- **iPhone:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar →
  paste the `all.ics` URL.
- **Google Calendar (web):** Other calendars → **+** → From URL → paste the `all.ics` URL.

Subscribe once; you never resend anything.

---

## Part 4 — The Gmail automation (Apps Script)

This is optional and independent of the repo. It reads booking confirmations from Gmail and
writes them onto a Google Calendar you share with your wife.

### Setup (once)
1. **Make a shared calendar:** Google Calendar → create "Travel" → share it with your wife →
   open its Settings → copy the **Calendar ID** into `TARGET_CALENDAR_ID` in `apps-script/Code.gs`.
2. **Make the Gmail filter** (see next section).
3. Go to **script.google.com → New project**, paste `Code.gs`, run `processTravelMail` once to
   authorise, then **Triggers → add a time-driven trigger** (e.g. hourly) for `processTravelMail`.

### Do I need to move emails into a Gmail Travel folder/label?
**No — let a filter do it automatically.** That's the whole point. Create one Gmail filter:

- Gmail search box → **Show search options** → in **From** put your senders, e.g.
  `airnewzealand.co.nz OR booking.com OR expedia.com OR entero` → **Create filter** →
  tick **Apply the label: Travel** (create the label if needed).
- Optionally tick "Also apply to matching conversations" to backfill existing emails.

After that, matching confirmations get the `Travel` label on arrival with zero effort, and the
script picks them up on its schedule. (Gmail "labels" are the same thing as folders here.)

**Manual fallback:** you can always just click a confirmation email and apply the `Travel`
label by hand — the script treats hand-labelled and filter-labelled emails identically. So
move/label an email manually only when it slips past your filter.

### Adding more booking sites later
Just add the sender to the filter's **From** list (e.g. add `jucy.co.nz`). The parser is
sender-agnostic — it reads whatever structured reservation data the email contains, so no code
change is needed. Entero is already included.

### What happens to emails it can't read
Not every confirmation embeds machine-readable data. Those threads get a `Travel/Needs-Review`
label so nothing is silently lost — review them and either add the trip to a YAML file by hand,
or ask me to write a small text-parsing rule for that sender (paste a sample and I'll do it).

---

## Quick reference

| I want to… | Do this |
|---|---|
| Add a trip | Copy a file in `trips/`, edit, `python generate.py`, push |
| Add a flight/stay/car | Add a list item under that heading in the trip's YAML |
| Add campervan | Add an item under `cars` |
| Add a new category (trains, tours) | Edit `generate.py` (or ask me) |
| Publish the site | Push — the GitHub Action does the rest |
| Share with wife | Send Pages URL + both subscribe to `all.ics` |
| Auto-capture a new booking site | Add its sender to the Gmail `Travel` filter |
| Handle an email with no data | It lands in `Travel/Needs-Review`; add by hand |
