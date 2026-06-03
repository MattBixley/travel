# Travel Tracker — Options & Plan

A personal app/calendar to consolidate flights, accommodation, and rental car/campervan
reservations booked across Air New Zealand, Booking.com, Expedia, and other sites — and
share it easily with my wife.

## Goals & constraints

- **Consolidate** bookings from many sources into one trip view.
- **Shareable** with my wife (ideally read access on her phone, low friction).
- **Calendar-friendly** — reservations show up on phone calendars with times/locations.
- **Low maintenance** — I don't want a heavy backend to babysit.
- **Builds on what I know** — I've published travel writeups before via GitHub Pages
  (`github.com/mattbixley/spain`), so a static-site approach is comfortable territory.

## The data problem (read this first)

None of these providers offer a clean, free, unified API for *your* bookings:

- **Air New Zealand** — no public bookings API. Confirmation emails + the app are the source.
- **Booking.com** — partner/affiliate APIs exist but are for property/listing search, not
  pulling your own reservations.
- **Expedia** — same story (affiliate/partner APIs, not personal itinerary access).
- **Campervan sites** — vary; mostly email confirmations only.

**Conclusion:** the realistic, reliable input is the **confirmation email**, not a live API.
Every option below is really a question of *how you get booking details into one place*.
Three input strategies:

1. **Email forwarding/parsing** — forward confirmations to a service that parses them
   (this is exactly how TripIt works).
2. **Manual entry** — you type/paste each booking. Most control, most effort.
3. **`.ics` calendar feed** — many confirmations already include a calendar attachment, or
   you generate one. Calendars are the natural sharing format.

---

## Option A — Use an existing app (lowest effort) — *can Gmail be automated? Yes.*

Short answer: **yes, your Gmail confirmation emails can be fully automated — no manual
forwarding required.** There are three levels of automation:

### A1. TripIt Inbox Sync (recommended automation route)
TripIt connects directly to your Gmail (also Google Workspace, Outlook/Microsoft 365, Yahoo)
via **Inbox Sync**. Once authorised, it automatically scans incoming mail, detects travel
confirmations from Air NZ / Booking.com / Expedia / campervan operators, and builds the
itinerary with **no forwarding needed**. Turn it on via the Inbox Sync toggle in the app, or
"Activate Inbox Sync" on the website.
- Fallback that always works: forward any confirmation to `plans@tripit.com` and it's parsed
  into a trip.
- Caveat: if your Google account has **Advanced Protection Program** enabled, Inbox Sync is
  blocked — you'd disable it or fall back to forwarding.
- Sharing with your wife is built in; itineraries export to calendar (so this feeds Option B).
- **Pros:** zero build, broad provider coverage, fully hands-off once connected.
- **Cons:** data lives with a third party; richer features (alerts) are on the paid tier.

### A2. Google itself
**Google Travel / "Trips"** already auto-detects booking emails in Gmail and shows them in
Google Maps and search — no setup. Least effort, but least control and hard to share cleanly.

### A3. DIY Gmail automation (feeds Options B & C — best if you want to own it)
If you'd rather keep your own pipeline, Gmail is very automatable:
- **Gmail filter → label** all travel confirmations (e.g. label `Travel`).
- A **Google Apps Script** (runs free on a schedule inside your Google account) reads that
  label, extracts the details, and writes events straight into your shared Google Calendar
  and/or generates an `.ics`. No server to host.
- For parsing, options range from simple (many airline/hotel emails embed **Schema.org
  `FlightReservation` / `LodgingReservation` JSON-LD** that's trivial to read reliably) to
  robust (the open-source **flight-reservation-emails** project, or a paid **AwardWallet Email
  Parsing API** that handles flights/hotels/cars/cruises across thousands of formats).

**Verdict on automation:** Air NZ, Booking.com, and Expedia all send standard confirmation
emails to Gmail, so all three are automatable. The fastest path is **A1 (TripIt Inbox Sync)**;
the own-it path is **A3 (Gmail label + Apps Script)**, which plugs directly into the C + B plan
below.

---

## Option B — Shared calendar (.ics) feed (best effort-to-value ratio)

Treat each reservation as a calendar event. Maintain one calendar; share it with your wife;
it appears in her phone's native calendar app alongside everything else.

How:
- Create a dedicated Google Calendar "Travel" → share it with your wife (read or edit).
- Add events manually, **or** generate an `.ics` file programmatically and import/subscribe.
- Flights become events with departure/arrival times; hotels as multi-day or check-in/out
  events; rental/campervan pickup & dropoff as events.

- **Pros:** native on every phone, trivially shareable, no app to build, works offline.
- **Cons:** calendars aren't great for rich detail (confirmation #s, links, notes) — though
  you can stuff those in the event description.
- **Best if:** you mostly want "where are we and when," shared effortlessly.

A nice hybrid: a small script that reads your booking details (a YAML/JSON file you maintain)
and outputs an `.ics` you publish to a URL — both you and your wife *subscribe* to that URL,
so updates propagate automatically.

---

## Option C — Static site on GitHub Pages (builds on what you've done)

Since you've already published with GitHub Pages, extend that pattern: a repo where each trip
is a data file (YAML/Markdown), and a static-site generator renders a clean trip page with a
timeline of flights/stays/cars. Share by sending the URL.

Two flavours:
- **Plain HTML/JS** — a single page that reads a `trips.json` and renders a timeline. Minimal.
- **Static-site generator** (Jekyll — already what GitHub Pages uses natively, or Astro/Eleventy)
  — nicer templating, multiple trips, easy to keep adding.

Add-ons:
- Generate an `.ics` per trip from the same data file (so you get Option B for free).
- Make the repo private and use a private Pages deploy, or just keep trips non-sensitive.

- **Pros:** you own it, free hosting, reuses your existing workflow, infinitely customizable,
  doubles as your travel-writeup home.
- **Cons:** manual data entry, public-by-default unless you set up private Pages, no live alerts.
- **Best if:** you enjoy tinkering and want a durable personal travel home you control.

---

## Option D — Lightweight web app with a real backend (most powerful, most work)

A small app (e.g. Next.js + a hosted DB like Supabase, or just a Google Sheet as the backend)
with a login for you and your wife, forms to add bookings, a calendar view, and `.ics` export.
Optionally an email inbox that parses forwarded confirmations.

- **Pros:** real multi-user editing, can grow (alerts, maps, packing lists, budget).
- **Cons:** most effort, something to maintain, accounts/auth, ongoing (small) cost possible.
- **Best if:** this becomes a genuine hobby project, not just a utility.

---

## Recommendation

Start with **Option B layered on Option C**:

1. Keep a per-trip data file (YAML) in a GitHub repo — your single source of truth.
2. A small script turns it into both (a) a clean static trip page on GitHub Pages and
   (b) an `.ics` feed.
3. You and your wife **subscribe** to the `.ics` in your phone calendars → effortless sharing,
   native experience, always current.

This reuses your GitHub Pages skills, keeps you in control of the data, costs nothing, and
solves the sharing problem the way phones already expect (calendar subscriptions).

To remove manual entry, add automation from Option A:
- **Quickest:** turn on **TripIt Inbox Sync (A1)** and let it watch Gmail and push to a shared
  calendar — done in minutes.
- **Own-it:** add a **Gmail label + Google Apps Script (A3)** that parses confirmations and
  writes events into your shared calendar / regenerates the `.ics` automatically — no server,
  runs free inside your Google account, and feeds the same data your GitHub Pages site uses.

## Suggested next steps

1. Decide: pure off-the-shelf (TripIt) vs. own-it (GitHub Pages + ics).
2. If own-it: scaffold a `travel` repo with a sample trip YAML schema (flights, stays, cars).
3. Write the YAML → HTML + `.ics` generator (Python or Node — small).
4. Publish to GitHub Pages; set up the calendar subscription on both phones.
5. Backfill one upcoming trip as a test.

## Quick comparison

| Option | Effort | Shareable | Own your data | Live alerts | Cost |
|---|---|---|---|---|---|
| A. TripIt | Very low | Built-in | No | Paid tier | Free/paid |
| B. Shared calendar | Low | Excellent (native) | Yes | No | Free |
| C. GitHub Pages site | Medium | URL link | Yes | No | Free |
| D. Custom web app | High | Excellent | Yes | Buildable | Low/ongoing |
