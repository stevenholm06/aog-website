# associateownersgroup.com

A hand-built static site. No framework, no build toolchain, no WordPress.

**Deploy `public/` as the web root.** There is no build step — `netlify.toml`
already sets the publish directory. This file lives outside `public/`, so it is
never served.

---

## Layout

| Path | What it is |
|---|---|
| `public/` | **The deployable site.** Point the host's publish directory here. |
| `public/assets/` | Stylesheet, logos, favicons, video, share image. |
| `build.py` | Generates every page except the home page. |
| `content/releases.json` | Press-release copy. The source of truth. |

## Editing

**The home page** (`public/index.html`) is maintained by hand.

**Every other page** is generated. Edit `build.py`, then:

```bash
python3 build.py
```

That rewrites all 24 interior pages from one shared shell — header, footer,
palette, type and page header are defined once so they cannot drift apart.

> **Do not hand-edit the generated pages.** The next build overwrites them.

### Press releases

Copy lives in `content/releases.json`, extracted once from the original
WordPress export. Edit the JSON, not the HTML.

The generator writes to the same paths it reads from, so if it ever parsed the
live pages a second run would scrape its own output and emit empty articles. It
did exactly that once. The JSON exists to prevent it, and the build now fails
loudly if the JSON is missing while the sources are already generated.

### The family of companies

The roster is the `PARTNERS` list in `build.py`. It feeds both the home page
marquee and `/partners/`, so the two cannot disagree.

Logos are bucketed by shape automatically — the build reads each file's own
viewBox or PNG header and sizes wide wordmarks shorter than stacked crests, so
a 7:1 mark and a 1:1 mark carry similar optical weight. Add a logo and it sorts
itself out.

The home page marquee is rewritten between the `<!-- LOGOS:START -->` and
`<!-- LOGOS:END -->` markers on every build. Everything outside those markers
is hand-maintained.

Logos should be sized for how they are displayed. One arrived as a 583x756
bitmap wrapped in an SVG, 191KB to draw a 51x66 mark; exported at 2x it is
18KB and looks identical.

### Local preview

```bash
python3 -m http.server 8790 --directory public
```

## Design

Gunmetal `#2B3439` and gold `#F0B743`, AOG's own brand colours. Proxima Nova via
the Adobe Fonts web project (kit `ucl6kcm`), with IBM Plex Mono for the
blueprint-style section labels.

Stylesheet URLs carry a version stamp. Browsers cache `aog.css` hard enough that
a deploy would otherwise leave visitors on the previous design.

## Things worth knowing

- **Analytics is live.** `GT-PJ79P9DK` on every page. A hosted copy sends real
  traffic to that property.
- **The Copper forms are live.** `/contact/` and `/join/` submit to a real
  Copper account and work wherever this is hosted.
- **Both films are self-hosted**, click-to-play at `preload="none"`, so nothing
  transfers until a visitor presses play. The announcement is 68MB with no
  adaptive streaming — everyone who plays it pulls the lot.
- **Neither film has captions.** Both carry narration with no `<track>`.
- **`/carrier-resources/` does not exist.** It was on the original WordPress
  site but the crawl never captured it. It 404s.
- **`/annual-meeting/` is gone**, 301'd to `/events/` in `netlify.toml`, since
  the April 2026 meeting has passed.

## Caching

`netlify.toml` sets `Cache-Control` for assets. The stylesheet is immutable
for a year because its URL carries a digest of its contents. Logos get a day
and video a week, both with `stale-while-revalidate` - they are not
version-stamped, so that window is how long a returning visitor can see an
old logo after it is swapped.

HTML is deliberately left on Netlify's default so deploys land immediately.

There is no Content-Security-Policy. The pages load Adobe Fonts, Google
Fonts, gtag and the Copper form embed, and a policy written without checking
those origins against the live site would break the forms.

## If the domain changes

`SITE` in `build.py` is the single origin used for canonicals, `og:url`,
JSON-LD and the sitemap. Change that line, rerun the build, and regenerate
`sitemap.xml` and `robots.txt`.

Note that email moved to `aoginc.com` while the site domain did not — that is
deliberate as of this writing, not an oversight.

## Before cutover

- **Back up the live WordPress site.** This repo is not a backup: no database,
  no admin.
- **Export all DNS records first**, especially **MX, SPF, DKIM, DMARC**.
  Moving nameservers without carrying those over silently kills company email.
- Lower DNS TTLs to ~300s a day ahead.
- Confirm the host serves `index.html` for directory requests, and `404.html`
  for unmatched paths.
- Redirect `www` to the apex or the reverse — pick one, so URLs do not split.
