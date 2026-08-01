#!/usr/bin/env node
/**
 * Load every generated page in a real headless browser and fail if the map is
 * broken. Static HTML checks can't catch this: the markup was perfectly valid on
 * the day every marker silently failed to draw, because Leaflet threw while
 * adding vector layers to a map that had no view yet.
 *
 * For each docs/<slug>.html that contains a map, this asserts:
 *   - no uncaught JS error on the page
 *   - Leaflet actually loaded
 *   - the number of rendered SVG paths matches the points the generator emitted
 *     (markers + the route line), so a partial failure is caught too
 *   - the layer toggle lists every category present
 *
 * Usage:  node scripts/render_check.js [--headful]
 * Needs:  npm install --no-save puppeteer   (and network, for Leaflet + tiles)
 */
'use strict';

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const ROOT = path.dirname(path.dirname(path.resolve(__filename)));
const DOCS = path.join(ROOT, 'docs');

// A 404 for a favicon we never ship is noise, not a failure.
const IGNORABLE = [/favicon\.ico/i];

function expectationsFor(html) {
  const m = html.match(/var PTS = (\[[\s\S]*?\]);/);
  if (!m) return null;                       // page has no map
  const pts = JSON.parse(m[1]);
  const kinds = new Set(pts.map((p) => p.kind));
  return {
    points: pts.length,
    // one <path> per circleMarker, plus one for the dashed route when >1 point
    paths: pts.length + (pts.length > 1 ? 1 : 0),
    // one control row per kind, plus the route row
    controlRows: kinds.size + (pts.length > 1 ? 1 : 0),
  };
}

async function checkPage(browser, file) {
  const html = fs.readFileSync(file, 'utf8');
  const want = expectationsFor(html);
  const name = path.basename(file);
  if (!want) return { name, skipped: 'no map on this page' };

  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 800 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message)));
  page.on('requestfailed', (r) => {
    if (!IGNORABLE.some((re) => re.test(r.url()))) {
      errors.push(`request failed: ${r.url()} (${(r.failure() || {}).errorText})`);
    }
  });

  await page.goto('file://' + file, { waitUntil: 'networkidle2', timeout: 60000 });
  const got = await page.evaluate(() => ({
    leaflet: typeof window.L,
    mapHeight: (document.getElementById('map') || {}).clientHeight || 0,
    // Only the vector pane — Leaflet 1.9's attribution control contains its own
    // inline SVG flag, which would otherwise inflate the count.
    paths: document.querySelectorAll('#map .leaflet-overlay-pane svg path').length,
    controlRows: document.querySelectorAll('.leaflet-control-layers label').length,
  }));
  await page.close();

  const problems = [];
  if (errors.length) problems.push(...errors.map((e) => `JS error: ${e}`));
  if (got.leaflet !== 'object') problems.push('Leaflet did not load (window.L missing)');
  if (got.mapHeight < 50) problems.push(`map container is ${got.mapHeight}px tall`);
  if (got.paths !== want.paths) {
    problems.push(`drew ${got.paths} of ${want.paths} expected shapes ` +
                  `(${want.points} points + route line)`);
  }
  if (got.controlRows !== want.controlRows) {
    problems.push(`layer toggle has ${got.controlRows} rows, expected ${want.controlRows}`);
  }
  return { name, want, got, problems };
}

(async () => {
  const files = fs.readdirSync(DOCS)
    .filter((f) => f.endsWith('.html'))
    .map((f) => path.join(DOCS, f))
    .sort();
  if (!files.length) {
    console.error(`No HTML in ${DOCS} — run generate.py first.`);
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    headless: process.argv.includes('--headful') ? false : 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  let failed = 0;
  for (const file of files) {
    const r = await checkPage(browser, file);
    if (r.skipped) {
      console.log(`--   ${r.name}: ${r.skipped}`);
    } else if (r.problems.length) {
      failed++;
      console.log(`FAIL ${r.name}`);
      r.problems.forEach((p) => console.log(`  - ${p}`));
    } else {
      console.log(`ok   ${r.name}: ${r.got.paths} shapes, ` +
                  `${r.got.controlRows} layer rows`);
    }
  }
  await browser.close();

  if (failed) {
    console.log(`\n${failed} page(s) render incorrectly.`);
    process.exit(1);
  }
  console.log('\nAll pages render with their maps intact.');
})().catch((e) => {
  console.error('render check crashed:', e.message);
  process.exit(1);
});
