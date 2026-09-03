# AOG static site — deployment notes

**Deploy the `public/` folder as the web root.** It is drop-in ready: set the
host's publish directory to `public` so `public/index.html` answers
`https://associateownersgroup.com/`. There is no build step.

This file deliberately lives *outside* `public/`, so deployment notes are never
served from the live site.

This is a **stopgap**. It is a frozen snapshot of the WordPress site — no admin,
no database, no way to edit content except by hand-editing HTML.

---

## Folders here

| Path | What it is |
|---|---|
| `public/` | **The deployable site.** Point the host's publish directory here. |
| `README.md` | This file. Outside the web root, so it is never served. |

## Host setup, in short

Netlify / Vercel / Cloudflare Pages: connect the repo, leave the build command
empty, set the **publish directory to `public`**, and set the 404 page to
`/404.html` if asked.

## What was fixed to make it hostable

- **All URLs are root-relative** (`/our-team/`, `/wp-content/...`). The mirror used
  `../` paths that escaped the site folder; nothing does now.
- **Live URLs preserved.** Links point at `/our-team/`, not `/our-team/index.html`,
  so existing indexed URLs keep working. Requires a host that serves `index.html`
  for directory requests — essentially all of them do.
- **Canonicals corrected.** Every page had `<link rel="canonical" href="index.html">`
  — relative and identical across all 24 pages, which would have been actively
  harmful. Each now points at its real absolute URL.
- **Filenames are ASCII.** 29 files had lookalike Unicode standing in for URL
  punctuation (`﹖` U+FE56 for `?`). Renamed and all references rewritten, so no
  host, CI runner, or CDN can mangle them.
- **Third-party scripts load from their real origins** — YouTube, jsDelivr, and
  Google Tag Manager, rather than stale captured copies.
- **Added** `robots.txt`, `sitemap.xml` (24 URLs, excludes the noindex author
  archive), and a styled `404.html`.
- **Removed** the `wp-json/` oEmbed tree, the dead Cloudflare Turnstile capture,
  WordPress API/EditURI/xmlrpc link tags, and the crawler's `_downloads.html`.

## WordPress leftovers — what was audited

Kept, because it is load-bearing:

- `bricks.min.js` (188K) — the theme's JavaScript. Every page needs it.
- `splide.min.js` — the partner-logo carousel on the home page.
- `wp-embed.min.js` — loaded on one press release only, which embeds
  `debtmedic.com` via oEmbed. It resizes that iframe; without it the embed
  stays hidden. Verified working.
- **Gutenberg block CSS** (`global-styles`, `classic-theme-styles`). The press
  releases were authored in the block editor and use `wp-block-paragraph`,
  `wp-block-quote`, `wp-block-image` and `wp-block-columns`.
- `/author/mgutierrez/` — linked as a byline from 17 press releases.
- `breeze-prefetch-links.min.js` — from a WordPress caching plugin, but it is
  self-contained hover-prefetch and still works. Optional; harmless to drop.

Removed, because nothing was left to serve it:

- **Yoast's `SearchAction`** in the JSON-LD told search engines the site had a
  search endpoint at `/?s=`. No WordPress, no search. Stripped from all 26 pages.
- **All three RSS feeds** (`/feed/`, `/comments/feed/`, the author feed) plus the
  `<link rel="alternate">` tags pointing at them. Every one contained **zero
  items** — advertising an empty feed is worse than having none.

Also fixed: the `Switzer-Regular.woff2` preload was missing `crossorigin`, so
browsers fetched the font twice and warned about it.

Still tied to a decision you need to make: `gtag` and the Google Site Kit event
script load on all 26 pages. Both stay or both go with the analytics call below.

Verified by crawling all 25 pages: **85 unique local URLs, all returning 200.**

## Host setup

Any static host works — Netlify, Vercel, Cloudflare Pages, S3+CloudFront, plain nginx.

1. Point the web root at `public/`.
2. Set the 404 document to `/404.html`.
3. Confirm directory requests serve `index.html`.
4. Enable HTTPS for both apex and `www`, and redirect `www` → apex (or the reverse —
   just pick one and redirect the other, so URLs don't split).

To preview locally, from inside `public/`:

    python3 -m http.server 8788

## Before cutover

- **Back up the live WordPress site.** This folder is not a backup — no database,
  no admin, and it is missing at least one page (see below).
- **Export all DNS records first**, especially **MX, SPF, DKIM, DMARC**.
  `info@associateownersgroup.com` is published on this site; moving nameservers
  without carrying those over silently kills company email.
- Lower DNS TTLs to ~300s a day ahead.
- Decide whether WordPress keeps running somewhere so content stays editable.

## Known gaps

- **`/carrier-resources/` is missing.** It exists on the live site — it is named in
  the site's own prefetch config — but the crawler never captured it. It will 404.
  Either capture it before cutover or add a redirect.
- **Google Analytics is live** (`GT-PJ79P9DK`) on all pages. A hosted copy sends real
  traffic to that property. Remove the gtag snippet if that isn't wanted.
- **Content is frozen** as of the capture. Nothing here updates.
- **Search is gone.** The WordPress search endpoint no longer exists.
- The **Copper forms on `/contact/` and `/join/` are live** and submit to a real
  Copper account — those keep working wherever this is hosted.
- The membership form's heading reads "Apply for Membersip" (missing *h*). That
  text lives in Copper, not in these files; fix it in the Copper form builder.
