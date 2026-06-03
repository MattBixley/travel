/**
 * Gmail -> Google Calendar travel automation (Option A3).
 *
 * What it does, fully inside your own Google account (no server, free):
 *   1. Looks at Gmail threads under the label TRAVEL_LABEL.
 *   2. For each new message, tries to read structured Schema.org JSON-LD
 *      (FlightReservation / LodgingReservation / RentalCarReservation) that
 *      Air NZ, Booking.com, Expedia and many others embed in confirmations.
 *   3. Creates calendar events on TARGET_CALENDAR_ID (a calendar you share
 *      with your wife) and marks the message processed with a label so it
 *      never double-books.
 *
 * SETUP
 *   1. Gmail: make a filter that labels all booking confirmations "Travel".
 *      (Matches like
 *       from:(airnewzealand.co.nz OR booking.com OR expedia.com OR entero)
 *       subject:(confirmation OR itinerary OR booking).)
 *      Add any operator you book with (e.g. entero) to the from: list the same
 *      way — the parser itself is sender-agnostic, it reads whatever structured
 *      reservation data the email contains.
 *   2. Create a Google Calendar "Travel", share it with your wife (read or edit),
 *      open its Settings and copy its Calendar ID into TARGET_CALENDAR_ID below.
 *   3. script.google.com -> New project -> paste this file.
 *   4. Run processTravelMail once to authorise. Then Triggers -> add a
 *      time-driven trigger (e.g. every 1 hour) for processTravelMail.
 *
 * NOTE: JSON-LD parsing is reliable but not every email includes it. Messages
 * with no parseable booking are labelled NEEDS_REVIEW_LABEL so you can add them
 * by hand. Extend extractFromText() with regexes for senders you care about.
 */

const TRAVEL_LABEL        = 'Travel';
const PROCESSED_LABEL     = 'Travel/Synced';
const NEEDS_REVIEW_LABEL  = 'Travel/Needs-Review';
const TARGET_CALENDAR_ID  = 'PUT_YOUR_CALENDAR_ID_HERE@group.calendar.google.com';
const LOOKBACK_THREADS    = 50;   // how many recent labelled threads to scan

function processTravelMail() {
  const label = getOrCreateLabel_(TRAVEL_LABEL);
  const synced = getOrCreateLabel_(PROCESSED_LABEL);
  const review = getOrCreateLabel_(NEEDS_REVIEW_LABEL);
  const cal = CalendarApp.getCalendarById(TARGET_CALENDAR_ID);
  if (!cal) throw new Error('Calendar not found. Check TARGET_CALENDAR_ID.');

  const threads = label.getThreads(0, LOOKBACK_THREADS);
  let created = 0, reviewed = 0;

  threads.forEach(function (thread) {
    if (hasLabel_(thread, PROCESSED_LABEL)) return;
    let madeEvent = false;

    thread.getMessages().forEach(function (msg) {
      const events = extractEvents_(msg);
      events.forEach(function (ev) {
        if (eventExists_(cal, ev)) return;            // idempotent
        const e = cal.createEvent(ev.title, ev.start, ev.end, {
          description: ev.description, location: ev.location || ''
        });
        e.setTag('source', 'gmail-travel-sync');
        created++; madeEvent = true;
      });
    });

    if (madeEvent) { thread.addLabel(synced); thread.removeLabel(review); }
    else           { thread.addLabel(review); reviewed++; }
  });

  Logger.log('Created %s event(s); %s thread(s) need manual review.', created, reviewed);
}

/** Pull events from one Gmail message: JSON-LD first, then text fallback. */
function extractEvents_(msg) {
  const body = msg.getBody() || '';           // HTML body
  let events = extractFromJsonLd_(body);
  if (events.length === 0) {
    events = extractFromText_(msg.getPlainBody() || '', msg.getSubject() || '');
  }
  return events;
}

/** Parse Schema.org JSON-LD reservation blocks embedded in the email HTML. */
function extractFromJsonLd_(html) {
  const out = [];
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    let json;
    try { json = JSON.parse(m[1].trim()); } catch (e) { continue; }
    const items = Array.isArray(json) ? json : [json];
    items.forEach(function (it) {
      const types = [].concat(it['@type'] || []);
      types.forEach(function (type) {
        if (type === 'FlightReservation' && it.reservationFor) {
          const f = it.reservationFor;
          const dep = parseDate_(f.departureTime), arr = parseDate_(f.arrivalTime);
          if (dep && arr) out.push({
            title: '✈ ' + (f.flightNumber || 'Flight'),
            start: dep, end: arr,
            location: airportName_(f.departureAirport),
            description: 'Confirmation: ' + (it.reservationNumber || '-')
          });
        }
        if (type === 'LodgingReservation' && it.reservationFor) {
          const ci = parseDate_(it.checkinTime), co = parseDate_(it.checkoutTime);
          if (ci && co) out.push({
            title: '🏨 ' + (it.reservationFor.name || 'Hotel'),
            start: ci, end: co,
            location: addr_(it.reservationFor.address),
            description: 'Confirmation: ' + (it.reservationNumber || '-')
          });
        }
        if (type === 'RentalCarReservation') {
          const pu = parseDate_(it.pickupTime), dop = parseDate_(it.dropoffTime);
          if (pu && dop) out.push({
            title: '🚗 Rental car',
            start: pu, end: dop,
            location: addr_(it.pickupLocation && it.pickupLocation.address),
            description: 'Confirmation: ' + (it.reservationNumber || '-')
          });
        }
      });
    });
  }
  return out;
}

/**
 * Text fallback for emails without JSON-LD. Stub on purpose: add per-sender
 * regexes here as you discover formats you book often.
 */
function extractFromText_(text, subject) {
  return [];
}

// ---- helpers ---------------------------------------------------------------

function parseDate_(s) { if (!s) return null; const d = new Date(s); return isNaN(d) ? null : d; }
function airportName_(a) { return a ? (a.name || a.iataCode || '') : ''; }
function addr_(a) {
  if (!a) return '';
  if (typeof a === 'string') return a;
  return [a.streetAddress, a.addressLocality, a.addressCountry].filter(String).join(', ');
}

function eventExists_(cal, ev) {
  const found = cal.getEvents(new Date(ev.start.getTime() - 60000),
                              new Date(ev.start.getTime() + 60000));
  return found.some(function (e) { return e.getTitle() === ev.title; });
}

function getOrCreateLabel_(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}
function hasLabel_(thread, name) {
  return thread.getLabels().some(function (l) { return l.getName() === name; });
}
