#!/usr/bin/env python3
"""Generate the AOG interior pages from one shared shell.

Lives outside public/ so it is never served — same principle as README.md.

The home page (public/index.html) is hand-maintained; everything else is
emitted here so the header, footer and design system can only ever be
defined once.

Press-release copy is extracted ONCE from the original WordPress export
into content/releases.json, and every build thereafter reads that file.
This matters: the generator writes to the same paths it reads from, so
parsing the live pages on every run would mean the second run scraped its
own output and emitted empty articles. The JSON is the source of truth —
edit it, not the generated HTML.

Run:  python3 build.py
"""

import glob
import html
import json
import struct
import io
import os
import re
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')

# Stamped onto the stylesheet URL. Browsers cache aog.css hard, so without a
# version token a deploy can leave visitors on the previous design.
ASSET_V = time.strftime('%Y%m%d%H%M')

# Absolute origin, needed for canonicals, og:url and JSON-LD. If the site
# moves to aoginc.com this is the single line to change.
SITE = 'https://associateownersgroup.com'

ANALYTICS = """<!-- Google tag (gtag.js) — restored from the original WordPress head.
     The Site Kit plumbing that surrounded it there (developer_id, the
     _googlesitekit event throttler) is dropped: it only existed to serve the
     WordPress plugin, which is gone. -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GT-PJ79P9DK"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('set', 'linker', { domains: ['associateownersgroup.com'] });
  gtag('js', new Date());
  gtag('config', 'GT-PJ79P9DK');
</script>"""


NAV = [('/', 'Home'), ('/our-team/', 'Leadership'), ('/partners/', 'Partners'),
       ('/press/', 'Press'), ('/events/', 'Events'), ('/contact/', 'Contact')]

FOOTER = """<footer class="ftr">
  <div class="wrap">
    <div class="ftr__g">
      <div>
        <div class="ftr__logo"><img src="/assets/logo-white.svg" alt="Associate Owners Group" width="178" height="42"></div>
        <p class="ftr__note">Built for Associates. Built for the Future.</p>
      </div>
      <div>
        <h4>Company</h4>
        <ul>
          <li><a href="/our-team/">Leadership</a></li>
          <li><a href="/partners/">Partners</a></li>
          <li><a href="/press/">Press</a></li>
        </ul>
      </div>
      <div>
        <h4>Engage</h4>
        <ul>
          <li><a href="/join/">Join AOG</a></li>
          <li><a href="/events/">Events</a></li>
          <li><a href="/contact/">Contact Us</a></li>
        </ul>
      </div>
      <div>
        <h4>Contact</h4>
        <ul>
          <li><a href="mailto:info@aoginc.com">info@aoginc.com</a></li>
          <li><a href="tel:+18017388858">+1 801-738-8858</a></li>
          <li>620 S 400 E, Suite 404<br>St. George, Utah 84770</li>
          <li style="opacity:.7">Mon&ndash;Fri, 9am&ndash;5pm MST</li>
        </ul>
      </div>
    </div>
    <div class="ftr__bar"><span>&copy; 2026 Associate Owners Group, Inc. All rights reserved.</span></div>
  </div>
</footer>"""

SCRIPT = """<script>
(function () {
  var hdr = document.getElementById('hdr');
  var onScroll = function () { hdr.classList.toggle('stuck', scrollY > 30); };
  onScroll(); addEventListener('scroll', onScroll, { passive: true });

  var burger = document.getElementById('burger'), nav = document.getElementById('nav');
  burger.addEventListener('click', function () {
    burger.setAttribute('aria-expanded', String(nav.classList.toggle('open')));
  });
  nav.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') { nav.classList.remove('open'); burger.setAttribute('aria-expanded','false'); }
  });

  var items = document.querySelectorAll('.r');
  var showAll = function () { items.forEach(function (el) { el.classList.add('on'); }); };
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) { showAll(); }
  else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('on'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -6% 0px', threshold: .05 });
    items.forEach(function (el) { io.observe(el); });
    // Observers do not fire in hidden tabs; never leave the page invisible.
    setTimeout(function () { if (!document.querySelector('.r.on')) showAll(); }, 1200);
  }
})();
</script>"""


ORG_JSONLD = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Associate Owners Group",
  "alternateName": "AOG",
  "url": "%(site)s/",
  "logo": "%(site)s/assets/icon-512.png",
  "image": "%(site)s/assets/og-image.png",
  "description": "AOG unites insurance agencies, broker-dealers, RIAs and vendors under a shared equity structure, so the people who build the business own it.",
  "slogan": "Built for Associates. Built for the Future.",
  "email": "info@aoginc.com",
  "telephone": "+1-801-738-8858",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "620 S 400 E, Suite 404",
    "addressLocality": "St. George",
    "addressRegion": "UT",
    "postalCode": "84770",
    "addressCountry": "US"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "contactType": "sales",
    "email": "info@aoginc.com",
    "telephone": "+1-801-738-8858",
    "areaServed": ["US", "CA"]
  }
}
</script>""" % {'site': SITE}


def shell(title, desc, body, canonical, og_type='website'):
    nav = '\n      '.join(
        '<a href="%s">%s</a>' % (href, label) for href, label in NAV)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/assets/site.webmanifest">
<meta name="theme-color" content="#2B3439">
<link rel="canonical" href="%(site)s%(canonical)s">

<!-- Social cards. Without these a shared link renders as a bare URL. -->
<meta property="og:type" content="%(ogtype)s">
<meta property="og:site_name" content="Associate Owners Group">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(site)s%(canonical)s">
<meta property="og:image" content="%(site)s/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Associate Owners Group — Built for Associates. Built for the Future.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(desc)s">
<meta name="twitter:image" content="%(site)s/assets/og-image.png">
<link rel="preconnect" href="https://use.typekit.net">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Proxima Nova, the brand face, via the AOG Adobe Fonts web project. -->
<link rel="stylesheet" href="https://use.typekit.net/ucl6kcm.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap">
<script>document.documentElement.classList.add('js')</script>
<link rel="stylesheet" href="/assets/aog.css?v=%(v)s">
%(analytics)s
</head>
<body>

<a class="skip" href="#main">Skip to content</a>

<header class="hdr" id="hdr">
  <div class="wrap">
    <a class="hdr__logo" href="/" aria-label="Associate Owners Group — home">
      <img src="/assets/logo-white.svg" alt="Associate Owners Group" width="190" height="45">
    </a>
    <button class="burger" id="burger" aria-label="Menu" aria-expanded="false" aria-controls="nav"><i></i><i></i><i></i></button>
    <nav class="nav" id="nav">
      %(nav)s
      <a class="btn btn--y" href="/join/">Become a Partner</a>
    </nav>
  </div>
</header>

<main id="main">
%(body)s
</main>

%(footer)s
%(orgjsonld)s
%(script)s
</body>
</html>
""" % dict(title=title, desc=desc, canonical=canonical, nav=nav,
           body=body, footer=FOOTER, script=SCRIPT, v=ASSET_V,
           analytics=ANALYTICS, site=SITE, ogtype=og_type,
           orgjsonld=ORG_JSONLD)



def _intrinsic_ratio(src):
    """Width/height of a logo file, read from the SVG viewBox or PNG header."""
    path = os.path.join(ROOT, src.lstrip('/'))
    try:
        if src.endswith('.svg'):
            head = io.open(path, encoding='utf-8', errors='ignore').read(4000)
            m = re.search(r'viewBox="([\d.\-\s]+)"', head)
            if m:
                box = [float(v) for v in m.group(1).split()]
                if box[3]:
                    return box[2] / box[3]
        elif src.endswith('.png'):
            with open(path, 'rb') as fh:
                fh.read(16)
                w, h = struct.unpack('>II', fh.read(8))
            if h:
                return w / h
    except Exception:
        pass
    return 3.0


def _size_class(src):
    """Bucket a logo by shape so all marks carry similar optical weight.

    Rendering every logo at one height sounds fair but is not: the set spans
    0.77:1 (Logos Wealth, stacked) to 7.27:1 (DebtMedic, a long wordmark), so
    a single height left the widest with roughly ten times the ink of the
    narrowest. Shorter for wide marks, taller for stacked ones.
    """
    r = _intrinsic_ratio(src)
    if r >= 4.0:
        return ' marquee__item--wide'
    if r >= 2.4:
        return ''
    if r >= 1.8:
        return ' marquee__item--squarish'
    return ' marquee__item--stacked'


def marquee():
    """The family of companies as a continuous loop.

    The list is emitted twice and the track slides exactly one copy's width,
    so the seam is invisible and there is no visual first or last. Only the
    first copy is exposed to assistive tech and crawlers.
    """
    def run(hidden):
        return '\n        '.join(
            '<div class="marquee__item%s"><img src="%s" alt="%s" loading="lazy"></div>'
            % (_size_class(src), src, '' if hidden else alt) for src, alt in PARTNERS)

    return """      <div class="marquee r">
        <div class="marquee__track">
        %s
        </div>
      </div>""" % (run(False) + '\n        ' +
                   '<div aria-hidden="true" style="display:contents">' + run(True) + '</div>')


def phead(tag, num, h1, lede=''):
    return """  <section class="phead">
    <img class="phead__mark" src="/assets/rhino-white.svg" alt="" aria-hidden="true">
    <div class="wrap">
      <p class="tag"><b>%s</b> %s</p>
      <h1>%s</h1>
      %s
    </div>
  </section>
""" % (num, tag, h1, ('<p class="phead__lede">%s</p>' % lede) if lede else '')


CLOSER = """  <section class="band dark">
    <div class="wrap">
      <div class="closer r">
        <div>
          <p class="tag"><b>&rarr;</b> Get Started</p>
          <h2>Ready to join <span>the network?</span></h2>
          <p>Discover how AOG can help your agency thrive through collaboration and shared success.</p>
        </div>
        <div class="closer__c">
          <a class="btn btn--y" href="/join/">Join AOG <i>&rarr;</i></a>
          <a class="btn btn--linew" href="/contact/">Get in Touch</a>
        </div>
      </div>
    </div>
  </section>
"""

# The AOG family of companies. Vector where the brand supplied vector; the
# 2026 brochure artwork supersedes the older WordPress uploads wherever both
# exist (Canyon, Wellthplan, TKT, Rhino RE, JavanShield, Copper, Experior).
# Paths are absolute because the set spans two directories.
PARTNERS = [
    ('/assets/logos/common-sense-financial.png', 'Common Sense Financial'),
    ('/assets/logos/experior.png',                    'Experior Financial Group'),
    ('/wp-content/uploads/your-ia-logo-new.png',      'Your IA'),
    ('/assets/logos/wellthplan.svg',                  'Wellthplan'),
    ('/assets/logos/aog-realty-holdings.svg',         'AOG Realty Holdings'),
    ('/assets/logos/rhino-re.svg',                    'Rhino RE'),
    ('/assets/logos/canyon-insurance.png',            'Canyon Insurance'),
    ('/wp-content/uploads/netexit-logo.png',          'NetExit Insurance Services'),
    ('/wp-content/uploads/insurtech-hub-logo.png',    'InsurTech Hub'),
    ('/assets/logos/javanshield.svg',                 'JavanShield'),
    ('/assets/logos/tkt.svg',                         'TKT Consulting'),
    ('/assets/logos/groupe-financier-signature.png',  'Groupe Financier Signature'),
    ('/assets/logos/colab-capital.png',               'COLAB Capital'),
    ('/assets/logos/bachmann-financial.png',          'Bachmann Financial Group'),
    ('/assets/logos/ith-life.png',                    'ITH Life'),
    ('/assets/logos/debt-medic.png',                  'Debt Medic'),
    # Alt text carries the SIPC/FINRA line: at marquee scale it renders about
    # 4.6px tall in the artwork, so it is legible to assistive tech and search
    # even though the eye cannot read it there.
    ('/assets/logos/first-asset-financial.svg',       'First Asset Financial — Member SIPC | FINRA'),
    ('/assets/logos/fisher-group.png',                'Fisher Group'),
    ('/assets/logos/agency-contracting-services.png', 'Agency Contracting Services'),
    ('/assets/logos/logos-wealth.svg',                'Logos Wealth Management'),
    ('/assets/logos/copper.svg',                      'Copper CRM'),
]

TEAM = [
    ('monte-holm-headhot-charcoal-480x480.jpg', 'Monte Holm', 'Founder &amp; Chairman'),
    ('jerry-vahl-headshot-charcoal-480x480.jpg', 'Jerry Vahl', 'Chief Executive Officer'),
    ('colby-clark-headshot-charcoal-480x480.jpg', 'Colby Clark', 'Chief Legal Officer'),
    ('colby-haupt-headshot-charcoal-480x480.jpg', 'Colby Haupt', 'Chief Operating Officer'),
]


# --------------------------------------------------------------------------
# Press releases: read title, date and body out of the WordPress export so
# the published copy is carried over verbatim.
# --------------------------------------------------------------------------

def strip(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', x))).strip()


def read_release(path):
    s = io.open(path, encoding='utf-8').read()
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    date = re.search(r'>([A-Z][a-z]+ \d{1,2}, \d{4})<', s)
    seg = re.search(r'brxe-post-content[^>]*>(.*?)</section>', s, re.S)
    paras = []
    if seg:
        for p in re.findall(r'<p[^>]*>(.*?)</p>', seg.group(1), re.S):
            txt = strip(p)
            if len(txt) > 25:
                paras.append(txt)
    return dict(slug=path.split(os.sep)[-2],
                title=strip(h1.group(1)) if h1 else 'Press Release',
                date=date.group(1) if date else '',
                paras=paras)


def sort_key(r):
    months = ('January February March April May June July August September '
              'October November December').split()
    m = re.match(r'([A-Z][a-z]+) (\d{1,2}), (\d{4})', r['date'] or '')
    if not m:
        return (0, 0, 0)
    return (int(m.group(3)), months.index(m.group(1)) + 1, int(m.group(2)))


DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'releases.json')


def load_releases():
    """Return the releases, extracting from the WordPress export only once.

    Once content/releases.json exists it is authoritative. Re-extracting on
    every run would scrape this script's own generated pages.
    """
    if os.path.exists(DATA):
        with io.open(DATA, encoding='utf-8') as fh:
            return json.load(fh)

    rows = []
    for path in glob.glob(os.path.join(ROOT, 'press-release', '*', 'index.html')):
        src = io.open(path, encoding='utf-8').read()
        if 'brxe-post-content' not in src:
            raise SystemExit(
                'Cannot build: %s is already generated and content/releases.json '
                'is missing, so the original copy is unavailable. Restore the '
                'press-release pages from git first.' % path)
        rows.append(read_release(path))

    rows.sort(key=sort_key, reverse=True)
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with io.open(DATA, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(rows, indent=2, ensure_ascii=False))
    print('extracted %d releases -> %s' % (len(rows), os.path.relpath(DATA)))
    return rows


def write(relpath, text):
    full = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    io.open(full, 'w', encoding='utf-8').write(text)
    return relpath


def main():
    written = []

    releases = load_releases()

    # ---- Press release pages ---------------------------------------------
    for i, r in enumerate(releases):
        body_paras = '\n        '.join('<p>%s</p>' % html.escape(p) for p in r['paras'])
        nxt = releases[i + 1] if i + 1 < len(releases) else None
        more = ''
        if nxt:
            more = ('<p style="margin-top:38px"><a class="btn btn--line" href="/press-release/%s/">'
                    'Next: %s <i>&rarr;</i></a></p>' % (nxt['slug'], html.escape(nxt['title'][:58])))
        body = """  <section class="phead">
    <img class="phead__mark" src="/assets/rhino-white.svg" alt="" aria-hidden="true">
    <div class="wrap">
      <p class="tag"><b>PR</b> Press Release</p>
      <h1>%(title)s</h1>
    </div>
  </section>

  <section class="band">
    <div class="wrap">
      <a class="backlink" href="/press/"><i>&larr;</i> All press releases</a>
      <div class="article__meta"><time>%(date)s</time><span>Associate Owners Group</span></div>
      <div class="prose">
        %(paras)s
      </div>
      %(more)s
    </div>
  </section>
""" % dict(title=html.escape(r['title']), date=r['date'], paras=body_paras, more=more)
        desc = (r['paras'][0][:155] if r['paras'] else r['title'])
        written.append(write('press-release/%s/index.html' % r['slug'],
                            shell('%s — Associate Owners Group' % r['title'],
                                  html.escape(desc), body + CLOSER,
                                  '/press-release/%s/' % r['slug'], og_type='article')))

    # ---- Press index ------------------------------------------------------
    rows = '\n      '.join(
        '<a href="/press-release/%s/"><time>%s</time><h2>%s</h2><span>Read &rarr;</span></a>'
        % (r['slug'], r['date'], html.escape(r['title'])) for r in releases)
    body = phead('Press', 'PR', 'News from across the family of companies.',
                 'Announcements, acquisitions and industry insight from the AOG network.') + """  <section class="band">
    <div class="wrap">
      <div class="postlist r">
      %s
      </div>
    </div>
  </section>
""" % rows
    written.append(write('press/index.html',
                        shell('Press — Associate Owners Group',
                              'Announcements, acquisitions and industry insight from across the AOG family of companies.',
                              body + CLOSER, '/press/')))

    # ---- Leadership -------------------------------------------------------
    people = '\n        '.join(
        '<article class="who"><img src="/wp-content/uploads/%s" alt="%s" width="480" height="480" loading="lazy">'
        '<div class="who__b"><h3>%s</h3><span>%s</span></div></article>' % (img, name, name, role)
        for img, name, role in TEAM)
    body = phead('Leadership', '01', 'In service of the heroes of distribution.',
                 'AOG&rsquo;s leadership exists to support the Associates who write the business &mdash; '
                 'not the other way around.') + """  <section class="band">
    <div class="wrap">
      <div class="head r">
        <div>
          <p class="tag"><b>&mdash;</b> The Team</p>
          <h2>Dedicated to supporting the network.</h2>
        </div>
        <p>Experienced professionals dedicated to supporting our network of agency owners and driving the success of the Associate Owners Group.</p>
      </div>
      <div class="team r">
        %s
      </div>
    </div>
  </section>
""" % people
    written.append(write('our-team/index.html',
                        shell('Leadership — Associate Owners Group',
                              'The AOG leadership team exists to support the Associates who write the business.',
                              body + CLOSER, '/our-team/')))

    # ---- Partners ---------------------------------------------------------
    logos = marquee()
    body = phead('The Family of Companies', '02', 'Built alongside the best in the industry.',
                 'AOG is proud to collaborate with premier financial service firms across the '
                 'United States and Canada. Together we create opportunities for growth and excellence.') + """  <section class="band">
    <div class="wrap">
%s
    </div>
  </section>
""" % logos
    written.append(write('partners/index.html',
                        shell('Partners — Associate Owners Group',
                              'AOG collaborates with premier financial service firms across the United States and Canada.',
                              body + CLOSER, '/partners/')))

    # ---- Join (Copper form preserved) -------------------------------------
    body = phead('Membership', '03', 'Join the AOG network.',
                 'Become part of a premier network of independent financial service firms. '
                 'Together, we&rsquo;re stronger, smarter, and more successful.') + """  <section class="band">
    <div class="wrap">
      <div class="withform r">
        <div>
          <p class="tag"><b>&mdash;</b> What you get</p>
          <h2>Four foundations beneath one producer.</h2>
          <ul class="rules" style="margin-top:30px">
            <li><span>01</span><div><strong>Collaborative network.</strong> Join a community of successful agency owners sharing best practices and strategies.</div></li>
            <li><span>02</span><div><strong>Resources and scale.</strong> Access exclusive tools, resources and partnerships to grow your business.</div></li>
            <li><span>03</span><div><strong>Collective strength.</strong> Benefit from collective bargaining power and regulatory representation.</div></li>
            <li><span>04</span><div><strong>Strategic partnerships.</strong> Connect with leading carriers and service providers on preferential terms.</div></li>
          </ul>

          <p class="tag" style="margin-top:52px"><b>&mdash;</b> Membership requirements</p>
          <h2 style="font-size:clamp(24px,2.4vw,34px)">We are intentional about who joins.</h2>
          <p style="margin-top:16px">AOG seeks established agencies and firms committed to excellence, collaboration and mutual growth. Our members represent the best in the industry.</p>
          <ul class="rules" style="margin-top:22px">
            <li><span>01</span><div>Independent insurance agency or financial services firm</div></li>
            <li><span>02</span><div>Minimum three years in business</div></li>
            <li><span>03</span><div>Strong compliance and professional standards</div></li>
            <li><span>04</span><div>Commitment to network collaboration and growth</div></li>
            <li><span>05</span><div>Willingness to share best practices with peers</div></li>
          </ul>
        </div>

        <div>
          <p class="tag"><b>&mdash;</b> Apply</p>
          <div class="formcard">
            <iframe src="https://forms.copper.com/j/9VhnRumM7B7VWGmLAyTkuH?type=embed"
                    id="9VhnRumM7B7VWGmLAyTkuH" title="Apply for membership" height="850"
                    loading="lazy"></iframe>
          </div>
        </div>
      </div>
    </div>
  </section>
"""
    written.append(write('join/index.html',
                        shell('Join AOG — Associate Owners Group',
                              'Become part of a premier network of independent financial service firms.',
                              body, '/join/')))

    # ---- Contact (Copper form preserved) ----------------------------------
    body = phead('Contact', '04', 'Let&rsquo;s talk about ownership.',
                 'Interested in joining AOG or learning more about our services? '
                 'We&rsquo;d love to hear from you.') + """  <section class="band">
    <div class="wrap">
      <div class="withform r">
        <div>
          <p class="tag"><b>&mdash;</b> Contact information</p>
          <h2>Get in touch.</h2>
          <dl class="deflist" style="margin-top:28px">
            <div><dt>Email</dt><dd><a href="mailto:info@aoginc.com">info@aoginc.com</a></dd></div>
            <div><dt>Phone</dt><dd><a href="tel:+18017388858">+1 801-738-8858</a></dd></div>
            <div><dt>Office</dt><dd>620 S 400 E, Suite 404<br>St. George, Utah 84770</dd></div>
            <div><dt>Office hours</dt><dd>Monday&ndash;Friday, 9am&ndash;5pm MST<br>Saturday&ndash;Sunday, closed</dd></div>
          </dl>
        </div>

        <div>
          <p class="tag"><b>&mdash;</b> Send a message</p>
          <div class="formcard">
            <iframe src="https://forms.copper.com/j/dAudnbY8vtoGf1YXRaVfnN?type=embed"
                    id="dAudnbY8vtoGf1YXRaVfnN" title="Contact AOG" height="600"
                    loading="lazy"></iframe>
          </div>
        </div>
      </div>
    </div>
  </section>
"""
    written.append(write('contact/index.html',
                        shell('Contact — Associate Owners Group',
                              'Reach AOG by email, phone or the contact form. Offices in St. George, Utah.',
                              body, '/contact/')))

    # ---- Events -----------------------------------------------------------
    # The April 2026 Annual Meeting has taken place, so this no longer
    # promotes it. The recap lives in the press archive.
    body = phead('Events', '05', 'Nothing on the calendar right now.',
                 'Our next gathering has not been announced yet. Get in touch and '
                 'we will let you know as soon as dates are set.') + """  <section class="band">
    <div class="wrap">
      <div class="head r">
        <div>
          <p class="tag"><b>&mdash;</b> Stay in the loop</p>
          <h2>Be first to hear about the next one.</h2>
        </div>
        <p>AOG brings the family of companies together to connect with industry leaders, explore new ideas and share what is working. Ask to be added to the invitation list, or read the recap of our most recent meeting.<br><br>
          <a class="btn btn--line" href="/contact/">Get in Touch <i>&rarr;</i></a>
          <a class="btn btn--line" href="/press/" style="margin-left:10px">Read the Recap <i>&rarr;</i></a></p>
      </div>
    </div>
  </section>
"""
    written.append(write('events/index.html',
                        shell('Events — Associate Owners Group',
                              'AOG events. No gatherings are currently scheduled; get in touch to be added to the invitation list.',
                              body + CLOSER, '/events/')))

    # ---- 404 --------------------------------------------------------------
    body = phead('Error 404', '404', 'That page isn&rsquo;t here.',
                 'The link may be out of date, or the page may have moved.') + """  <section class="band">
    <div class="wrap">
      <div class="head head--solo r">
        <div>
          <p class="tag"><b>&mdash;</b> Try instead</p>
          <h2>Where would you like to go?</h2>
          <p style="margin-top:22px">
            <a class="btn btn--line" href="/">Home <i>&rarr;</i></a>
            <a class="btn btn--line" href="/press/" style="margin-left:10px">Press <i>&rarr;</i></a>
            <a class="btn btn--line" href="/contact/" style="margin-left:10px">Contact <i>&rarr;</i></a>
          </p>
        </div>
      </div>
    </div>
  </section>
"""
    written.append(write('404.html',
                        shell('Page not found — Associate Owners Group',
                              'That page could not be found.', body, '/404.html')))

    # ---- Author archive (linked as a byline from the press releases) ------
    rows = '\n      '.join(
        '<a href="/press-release/%s/"><time>%s</time><h2>%s</h2><span>Read &rarr;</span></a>'
        % (r['slug'], r['date'], html.escape(r['title'])) for r in releases)
    body = phead('Author', '&mdash;', 'Posts by M. Gutierrez.') + """  <section class="band">
    <div class="wrap">
      <div class="postlist r">
      %s
      </div>
    </div>
  </section>
""" % rows
    written.append(write('author/mgutierrez/index.html',
                        shell('M. Gutierrez — Associate Owners Group',
                              'Press releases from Associate Owners Group.', body, '/author/mgutierrez/')))

    print('%d pages written (%d press releases + %d others)'
          % (len(written), len(releases), len(written) - len(releases)))
    for w in written[len(releases):]:
        print('  ', w)


if __name__ == '__main__':
    main()
