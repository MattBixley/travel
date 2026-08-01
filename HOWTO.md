# Travel Tracker — Complete How-To

Everything you need to run this system day to day. Your live site is at
**https://mattbixley.github.io/travel/**, built from this repo
(**https://github.com/MattBixley/travel**).

There are two independent ways to track travel here. Use either or both:

1. **The repo** — you describe each trip in a small text file; a script turns it into a
   shareable webpage and a calendar feed. You control everything; nothing is automatic.
2. **TripIt** — a free app that reads booking confirmations straight from Gmail and shares
   trips with your wife. Hands-off, but the data lives with a third party.

---

## Part 1 — How the repo works

```
travel-tracker/
├── trips/                    one YAML file per trip   ← you edit these
│   └── EXAMPLE-japan.yaml     fake sample showing the format
├── generate.py               turns trips/ into the website + calendar feeds
├── places.py                 resolves place names to map coordinates
├── places.yaml               coordinate cache for the maps  ← commit this
├── scripts/
│   ├── geocode.py             fills places.yaml (run by hand, needs internet)
│   └── validate_trips.py      checks trip files before they break the build
├── .githooks/pre-commit      runs the validator on staged trip files
├── docs/                     generated output (this is what GitHub Pages publishes)
│   ├── index.html             overview of all trips
│   ├── <slug>.html            a timeline page per trip, with a map
│   ├── <slug>-map.html        the same map, full page (the "new tab" link)
│   ├── <slug>.ics             calendar feed per trip
│   └── all.ics                every trip in one feed
├── apps-script/Code.gs       optional Gmail → Google Calendar automation
├── .github/workflows/build.yml   rebuilds + republishes the site on every push
├── HOWTO.md                  this file
├── GUIDE.md / README.md / PLAN.md   older notes (HOWTO supersedes them)
```

The flow is always: **edit a trip file → push to GitHub → the site rebuilds itself.**
You never have to run anything locally unless you want to preview before pushing.

> The `EXAMPLE-japan.yaml` trip is entirely invented (fake flights, hotels, and
> confirmation numbers) purely to show the format. Delete it once you've added a real trip.

---

## Part 2 — Adding a trip (the main thing you'll do)

### Step 1 — create the file
Copy the example and rename it. In your WSL terminal:

```bash
cd /mnt/c/Users/MattBixley/Code/travel-tracker
cp trips/EXAMPLE-japan.yaml trips/2026-fiji.yaml
```

(Or just duplicate the file in VS Code's Explorer and rename it.)

### Step 2 — fill it in
Open the new file and edit it. The structure has five parts — `trip`, `flights`, `stays`,
`cars`, `activities` — and any part can be left out if you don't have it.

```yaml
trip:
  name: Fiji 2026                 # shown as the page heading
  slug: 2026-fiji                 # page URL + calendar filename; keep it unique, no spaces
  start: 2026-07-01
  end: 2026-07-10
  travellers: [Matt, Sarah]
  notes: Family week on Denarau.

flights:
  - confirmation: NZ-REAL123
    airline: Air New Zealand
    flight_no: NZ56
    from: { airport: AKL, city: Auckland, tz: Pacific/Auckland }
    to:   { airport: NAN, city: Nadi,     tz: Pacific/Fiji }
    depart: 2026-07-01 19:30      # local time at departure airport
    arrive: 2026-07-01 23:05      # local time at arrival airport
    seat: 30A
    booked_via: Air New Zealand app
    link: https://www.airnewzealand.co.nz/manage-booking

stays:
  - confirmation: BDC-REAL456
    name: Sofitel Fiji Resort
    city: Denarau
    tz: Pacific/Fiji
    check_in: 2026-07-01 15:00
    check_out: 2026-07-10 11:00
    address: Denarau Island, Nadi, Fiji
    booked_via: Booking.com
    link: https://www.booking.com/mytrips

cars:
  - confirmation: ENT-REAL789
    vendor: Entero
    type: SUV
    pickup:  { place: Nadi Airport, tz: Pacific/Fiji, time: 2026-07-01 23:30 }
    dropoff: { place: Nadi Airport, tz: Pacific/Fiji, time: 2026-07-10 09:00 }
    booked_via: Entero
    link: https://...

activities:
  - name: Sunset reef cruise
    place: Port Denarau Marina
    city: Denarau
    tz: Pacific/Fiji
    start: 2026-07-03 16:30
    end: 2026-07-03 19:00       # optional — leave it out and you get an hour
    confirmation: ACT-REAL321
    booked_via: Viator
    notes: Check in 30 min early at the kiosk.
```

`activities` covers anything with a time and a place: tours, tickets, races, dinners,
meetings. It also accepts the same `pickup:`/`dropoff:` shape as `cars`, if that's more
natural for a full-day trip:

```yaml
activities:
  - name: Great Barrier Reef snorkelling
    pickup:  { place: Reef Fleet Terminal, tz: Australia/Brisbane, time: 2026-08-23 08:00 }
    dropoff: { place: Reef Fleet Terminal, tz: Australia/Brisbane, time: 2026-08-23 16:00 }
```

**Three rules that matter:**

- **Times are written in the local time of where the event happens**, as `YYYY-MM-DD HH:MM`
  (24-hour). A 7:30pm departure is `2026-07-01 19:30`.
- **Every time needs a `tz`** — an IANA timezone name. Common ones:
  `Pacific/Auckland`, `Pacific/Fiji`, `Australia/Sydney`, `Asia/Tokyo`, `Asia/Singapore`,
  `America/Los_Angeles`, `Europe/London`. This is what makes overnight and cross-timezone
  flights show the right hours on every phone.
- **`confirmation`, `seat`, `address`, `link`, `notes` are optional** but they appear in the
  calendar event details, which is handy at the airport or check-in desk.

To add a second flight leg, hotel, car, or activity, just add another `-` item under that
heading. A campervan goes under `cars` (set `type:` to e.g. `4-berth campervan`).

### Step 3 — publish
```bash
git add trips/2026-fiji.yaml
git commit -m "Add Fiji 2026"
git push
```
That's it. The push triggers the build, and a minute or two later your site updates at
`https://mattbixley.github.io/travel/`. You do **not** need to run `generate.py` or touch
the `docs/` folder yourself — the GitHub Action does that.

### Optional — preview locally first
```bash
pip install pyyaml          # once
python generate.py          # writes docs/
```
Then open `docs/index.html` in a browser. Useful if you want to check it before pushing.

### The map on each trip page

Every trip page opens with a map: one numbered marker per location, in the order you get
there, joined by a dashed route line. Blue markers are flights, green are stays, orange are
cars, purple are activities. Click a marker for the times, and use the box in the top-right
corner to show or hide each category. It's generated from the same YAML as the timeline, so
there's nothing extra to keep in sync.

Two ways to get a bigger map:

- **The ⤢ button** under the zoom controls fills the screen with the map, using the browser's
  own full-screen mode. Press it again or hit `Esc` to come back. On a phone this is the one
  you want.
- **"Open the map full screen in a new tab"**, the link under the map, opens
  `<slug>-map.html` — a page that is nothing but the map, with a link back to the timeline.
  Handy for a second monitor, or for sending someone just the map.

#### You don't have to do anything — pins appear by themselves

Coordinates are looked up from the names already in your trip file (`place`, `address`,
`city`, `name`, or the airport code). The build workflow does this for you: push a new
booking, and the Action geocodes anything it hasn't seen, saves it to `places.yaml`, and
commits that back to the repo so the next build doesn't ask again.

So the normal flow for a new hotel or tour is: write it, push it, done.

#### When you want the pin in an exact spot: `location:`

Automatic lookup puts the pin on whatever the geocoder thinks the name means, which can be
vague — "Great Barrier Reef" lands somewhere out at sea. To place it precisely, right-click
the spot in Google Maps, choose **Copy coordinates**, and paste it into `location:` on that
entry:

```yaml
activities:
  - name: Great Barrier Snorkeling
    place: Port Douglas
    location: -16.4846, 145.4636        # exactly here, no lookup
```

`location:` takes any of the forms Google Maps hands you, so you can paste without editing:

| What you paste | Example |
|---|---|
| Copied coordinates | `-16.4846, 145.4636` |
| Degrees/minutes/seconds | `16°29'04.6"S 145°27'49.1"E` |
| A Maps URL | `https://www.google.com/maps/@-16.4846,145.4636,15z` |
| A shared place URL | `https://www.google.com/maps/place/Port+Douglas/@-16.48,145.46,14z/data=!3d-16.4846!4d145.4636` |
| List form | `coords: [-16.4846, 145.4636]` |

`location:` works on any entry, including a flight's `from:`/`to:` and a car's
`pickup:`/`dropoff:`. It always wins over a name lookup, and a `location:` that isn't a
coordinate fails validation rather than quietly doing nothing.

#### Running the lookup yourself

You never need to, but it's there if you want to see the result before pushing:

```bash
python scripts/geocode.py             # looks up only what's missing
python scripts/geocode.py --dry-run   # just show what it would look up
python scripts/geocode.py --force     # re-look-up everything
```

`generate.py` itself never geocodes — it only reads `places.yaml` — so a build always gives
the same result from the same inputs. Anything with no coordinates is left off the map and
named in the build output, and the validator warns about it too.

To move an existing marker, edit its numbers in `places.yaml`, or add a `location:` to the
entry, which overrides the cache.

Two details that matter for accuracy:

- **Multi-airport cities**: the IATA code is looked up first, so an HND flight pins Haneda.
  `Tokyo Airport` would resolve to Narita.
- **The most specific name wins**: for an entry with `place: Port Douglas` and
  `address: Great Barrier Reef`, the lookup is on `place`. That's the pin you want.

**One caveat:** the map is the only part of the site that reaches outside the repo. A viewer's
browser loads Leaflet from unpkg.com and tiles from openstreetmap.org, so those two hosts see
requests for the page. Everything else — the timelines, the `.ics` files — is self-contained.

### Catching typos before you push

`scripts/validate_trips.py` checks every trip file for the mistakes that actually break the
build — unparseable YAML, a `tz` that isn't an IANA name (`AEST` instead of
`Australia/Brisbane`), a date that isn't `YYYY-MM-DD HH:MM`, or a missing key:

```bash
python scripts/validate_trips.py           # check everything
python scripts/validate_trips.py trips/2026-fiji.yaml
```

There's a pre-commit hook that runs it automatically on the files you're about to commit, so
a broken trip file never reaches GitHub. Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

The same check runs in CI, so the build fails with a readable error instead of a Python
traceback if the hook was skipped.

### What the GitHub Action actually does

You never build locally. Every push to `main` runs the whole chain and publishes the result —
the `docs/` folder committed in the repo is ignored by the deploy, so it doesn't matter that
it's stale.

1. **Validate** the trip files (`scripts/validate_trips.py`) — fails fast with a readable error.
2. **Geocode** any place it hasn't seen (`scripts/geocode.py`) and commit the result back to
   `places.yaml`, so new bookings get pins without you doing anything. This step can't fail
   the build: if the geocoder is unreachable, the place is just left off the map and reported.
3. **Build** the site (`generate.py`) — writes `docs/` fresh from `trips/`.
4. **Render-check** every page in a real headless browser (`scripts/render_check.js`) — loads
   each map, and fails the build on any JavaScript error or if the number of shapes drawn
   doesn't match the number of locations the generator emitted.
5. **Deploy** `docs/` to GitHub Pages.

Step 2 means the repo will occasionally get a commit from `github-actions[bot]` adding
coordinates. That's expected — `git pull` before your next edit.

Step 3 exists because the map is JavaScript, and valid HTML proves nothing about it. Every
marker on the site once failed to draw while the markup was perfectly well formed — Leaflet
threw because the map had no view set yet, and nothing in the build noticed. The render check
catches that class of bug, and it verified this specific one before the fix shipped.

### Adding a section the code has never heard of

You don't have to touch the Python to add a new kind of booking. Any top-level list is picked
up automatically: entries get a calendar event and a teal "Other" pin on the map, as long as
each has a place and a time.

```yaml
ferries:                                  # a section that doesn't exist in the code
  - name: Cairns to Fitzroy Island
    place: Reef Fleet Terminal
    city: Cairns
    tz: Australia/Brisbane
    start: 2026-08-22 09:00               # `time:` works too
    end: 2026-08-22 09:45                 # optional
```

The build prints a note telling you the section was handled generically, and the validator
warns about any entry missing a time or `tz` — those are skipped rather than silently
mangled. If a section deserves its own colour and icon, that's a small change in
`generate.py` (`trip_events`) and `places.py` (`KIND_COLOURS`).

---

## Part 3 — Publishing & GitHub Pages settings

This is already configured, but for reference / if it ever breaks:

- **Repo → Settings → Pages → Source** must be **GitHub Actions** (not "Deploy from a branch").
- The workflow `.github/workflows/build.yml` runs on **every push to `main`** and on manual
  runs (Actions tab → Run workflow). It installs PyYAML, runs `generate.py`, and deploys
  `docs/`.
- Live URL: **https://mattbixley.github.io/travel/**

**Privacy note:** the repo is public, so your trip pages and any confirmation numbers in the
YAML are publicly viewable. If that matters, either leave confirmation numbers out of the
YAML, or make the repo private (GitHub Pages on private repos needs a paid plan).

---

## Part 4 — Sharing with your wife

Two layers, use both:

- **The webpage:** just send her `https://mattbixley.github.io/travel/`. Nothing to install;
  she can bookmark it.
- **The calendar (better for daily use):** you both **subscribe to the combined feed** once,
  and it then updates automatically whenever you push a change.
  Feed URL: `https://mattbixley.github.io/travel/all.ics`
  - **iPhone:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar
    → paste the URL.
  - **Google Calendar (web):** Other calendars → **+** → From URL → paste the URL.

Subscribe once; you never resend anything.

---

## Part 5 — TripIt (the hands-off option)

TripIt reads booking confirmations from Gmail and builds itineraries automatically.

**Setup (your accounts — I can't do this for you):**

1. Install TripIt; create an account **with your Gmail address**.
2. Turn on **Inbox Sync**: in the app, Settings → Inbox Sync → connect Gmail and authorise.
   From then on it auto-detects Air NZ / Booking.com / Expedia / campervan confirmations as
   they arrive — no forwarding needed.
   - Manual fallback any time: forward a confirmation to `plans@tripit.com`.
   - If your Google account has **Advanced Protection** enabled, Inbox Sync is blocked — use
     the forwarding fallback instead.
3. **Share with your wife:** open a trip → Share → invite her by email. Or use TripIt's
   "add to calendar" to feed a shared calendar.

TripIt and the repo overlap. If you only want one, TripIt is the lower-effort choice for
everyday tracking; the repo is the one you fully own and curate.

---

## Part 6 — Gmail → Calendar automation (advanced, optional)

`apps-script/Code.gs` is a Google Apps Script that runs free inside your own Google account,
reads booking emails, and writes them onto a shared Google Calendar — a DIY alternative to
TripIt that keeps your data yours.

1. Create a Google Calendar "Travel", share it with your wife, copy its **Calendar ID** into
   `TARGET_CALENDAR_ID` in `Code.gs`.
2. In Gmail, make one filter that labels confirmations `Travel`:
   from `airnewzealand.co.nz OR booking.com OR expedia.com OR entero` → apply label `Travel`.
   (You don't need to move emails by hand — the filter labels them on arrival.)
3. script.google.com → New project → paste `Code.gs` → run `processTravelMail` once to
   authorise → add a time-driven trigger (e.g. hourly).

Emails it can't read are labelled `Travel/Needs-Review` so nothing is lost.

---

## Part 7 — Troubleshooting (things we actually hit)

**Site shows 404 / "There isn't a GitHub Pages site here."**
Pages source isn't set to GitHub Actions, or no build has run since you enabled it.
Fix: Settings → Pages → Source → GitHub Actions, then push any change (an empty commit works:
`git commit --allow-empty -m "rebuild" && git push`).

**Deploy job fails with `HttpError: Not Found (404)`.**
Same cause — Pages wasn't enabled with the GitHub Actions source when the deploy ran. Set the
source, then re-run the workflow (Actions tab) or push again.

**Pushed but no workflow ran.**
The workflow runs on pushes to `main`. If nothing appears in the Actions tab, check
Settings → Actions → General → Actions are allowed. You can also trigger it manually:
Actions → Build travel site → Run workflow.

**Build fails on a trip file** with a `yaml.parser.ParserError`, or a `ZoneInfoNotFoundError`.
Run `python scripts/validate_trips.py` — it names the line and the problem. The usual causes are
a list item indented one space instead of two, a value containing a comma that isn't quoted, or
a `tz` written as an abbreviation (`AEST`) instead of an IANA name (`Australia/Brisbane`).

**A location is missing from the map.** It has no coordinates yet. Run
`python scripts/geocode.py` and commit `places.yaml`. If the geocoder can't find it either, add
`coords: [lat, lon]` to that item in the trip file.

**The map is blank or grey.** The page loads Leaflet from unpkg.com and tiles from
openstreetmap.org, so a blocked CDN, an offline browser, or an ad-blocker filtering either host
will leave an empty box. The timeline underneath still works.

**WSL path confusion.** Your Windows folder is at `/mnt/c/Users/MattBixley/Code/travel-tracker`
inside WSL (not `~/...` and not `/c/...`).

**`fatal: unable to create '.git/index.lock': File exists`.**
A previous git command was interrupted. Remove the stray lock and retry:
`rm -f .git/index.lock && git <command>`

**Push rejected (`fetch first` / non-fast-forward).**
The remote has a commit you don't (e.g. a README created on GitHub).
`git pull --rebase origin main` then `git push`.

**Authentication prompt on push.** Use a GitHub **Personal Access Token** as the password
(Settings → Developer settings → Personal access tokens), or set up the GitHub CLI
(`gh auth login`).

---

## Quick reference

| I want to… | Do this |
|---|---|
| Add a trip | `cp trips/EXAMPLE-japan.yaml trips/<name>.yaml`, edit, commit, push |
| Add a flight / hotel / car / activity | Add a `-` item under `flights` / `stays` / `cars` / `activities` |
| Add a tour, race or dinner | Add under `activities` with `name`, `place`, `tz`, `start` |
| Add a campervan | Add under `cars` with `type: ... campervan` |
| Publish changes | `git push` — the Action rebuilds the site |
| Add map pins for a new trip | `python scripts/geocode.py`, then commit `places.yaml` |
| Check a trip file before pushing | `python scripts/validate_trips.py` |
| Preview before pushing | `python generate.py` then open `docs/index.html` |
| Share with wife | Send the site URL + both subscribe to `all.ics` |
| Remove the fake example | Delete `trips/EXAMPLE-japan.yaml`, commit, push |
| Auto-capture bookings | Set up TripIt (Part 5) or the Apps Script (Part 6) |
| Site is 404 | Pages source → GitHub Actions, then push |
