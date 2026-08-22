#!/usr/bin/env python3
"""Builds the static site into ./docs.

Run:  python3 build.py
Edit photos.py to change which photographs appear and in what order.

Your full-size photographs live in ./images and stay on this machine. The
build makes the web copies in docs/images itself, capped at MAX_EDGE.
"""

import html
import os
import shutil
import subprocess
import captions
import photos

# The published folder. Named "docs" because GitHub Pages will only serve
# the repository root or a folder called docs/ — nothing else.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

# Where images come from.
#   "wix"   -> served from Wix's CDN (works right now, before you cancel)
#   "local" -> served from ./images/<filename> in this folder
SOURCE = "local"

WIX_PREFIX = "https://static.wixstatic.com/media/7dafb7_"
SITE_URL = "https://maximilienbozon.com"
EMAIL = "maximilien.bozon@gmail.com"  # <-- change to your real address

WIDTHS = [720, 1200, 1800, 2400]

# Where the full-size photographs live, and how big a copy the site is
# allowed to serve. The widest plate in the layout is 76rem — about 1216
# CSS pixels — so 2000 covers even a high-density screen with room spare.
# Serving the 2400px masters would hand every visitor a print-quality file
# for nothing in return.
MASTERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
MAX_EDGE = 2000

# The index strip at the top of a series page draws each plate about
# 90px tall, so 400 covers a high-density screen and nothing more.
THUMB_EDGE = 400
COPYRIGHT = "© Maximilien Bozon"


def src(fname, width=1800):
    if SOURCE == "local":
        return "images/" + fname.replace("~mv2", "")
    return "%s%s/v1/fit/w_%d,h_%d,q_88/f.jpg" % (WIX_PREFIX, fname, width, width)


def srcset(fname):
    if SOURCE == "local":
        return ""
    parts = ["%s %dw" % (src(fname, w), w) for w in WIDTHS]
    return ' srcset="%s" sizes="(max-width: 900px) 100vw, 80vw"' % ", ".join(parts)


def thumb(fname):
    """The small copy used by the index at the top of a series page.

    A series index shows every plate at once, so it must never load the
    plates themselves — forty 2000px photographs above the fold would undo
    the whole point of lazy-loading the column below.
    """
    if SOURCE == "local":
        return "images/thumbs/" + fname.replace("~mv2", "")
    return src(fname, THUMB_EDGE)


ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def roman(n):
    out = ""
    for value, sym in ROMAN:
        while n >= value:
            out += sym
            n -= value
    return out


NAV = [
    ("shadow.html", "Shadow"),
    ("light.html", "Light"),
    ("monochrome.html", "Monochrome"),
    ("projects.html", "Projects"),
    ("about.html", "About"),
    ("contact.html", "Contact"),
]


def masthead(current):
    links = []
    for href, label in NAV:
        aria = ' aria-current="page"' if href == current else ""
        links.append('<a href="%s"%s>%s</a>' % (href, aria, label))
    return """<header class="masthead">
  <a class="masthead__mark" href="index.html">MB</a>
  <nav class="masthead__nav" aria-label="Primary">%s</nav>
</header>""" % "".join(links)


def colophon():
    return """<footer class="colophon shell">
  <span>&copy; Maximilien Bozon</span>
  <span>Wildlife photography &middot; Paris &amp; London</span>
  <a href="mailto:%s">%s</a>
</footer>""" % (EMAIL, EMAIL)


# The overture: the black panel that types the name in and then lifts, once
# per visit. It is armed in <head> so it never flashes the page behind it, and
# it is armed *only* if this browser both runs the snippet and has not already
# seen it this session. If site.js never arrives the failsafe timer drops the
# panel on its own.
OVERTURE_ARM = """
  <script>
    (function () {
      var d = document.documentElement;
      try { if (sessionStorage.getItem('mb-overture') === 'seen') return; } catch (e) {}
      d.classList.add('overture-armed');
      setTimeout(function () { d.classList.remove('overture-armed'); }, 4600);
    })();
  </script>"""

OVERTURE = """<div class="overture" data-overture>
  <div class="overture__glow" aria-hidden="true"></div>
  <div class="overture__inner">
    <p class="overture__mark">M B</p>
    <p class="overture__name">
      <span class="overture__line"><i>Maximilien</i></span>
      <span class="overture__line"><i>Bozon</i></span>
    </p>
    <p class="overture__sub">Wildlife photography &middot; Paris &amp; London</p>
  </div>
  <button class="overture__enter" type="button" data-enter>
    <span>Enter</span>
    <span class="overture__meter" aria-hidden="true"></span>
  </button>
</div>
"""


def page(title, desc, body, current, hero_image=None, intro=False):
    og = ""
    if hero_image:
        og = '\n  <meta property="og:image" content="%s">' % src(hero_image, 1200)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%(title)s</title>
  <meta name="description" content="%(desc)s">
  <meta property="og:title" content="%(title)s">
  <meta property="og:description" content="%(desc)s">
  <meta property="og:type" content="website">%(og)s
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600&family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;1,6..96,400;1,6..96,500&family=Spectral:ital,wght@0,200;0,300;0,400;1,300&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%%2307080a'/><text x='16' y='23' font-family='Georgia,serif' font-size='19' fill='%%23e9e4d9' text-anchor='middle'>M</text></svg>">
  <link rel="stylesheet" href="assets/css/site.css">
  <script>
    /* Hide-then-reveal is only safe if the script that reveals actually loads.
       If it hasn't run within 2.5s, drop back to a plain, fully visible page. */
    document.documentElement.classList.add('js');
    setTimeout(function () {
      if (document.documentElement.dataset.enhanced !== '1') {
        document.documentElement.classList.remove('js');
      }
    }, 2500);
  </script>%(arm)s
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
%(overture)s%(masthead)s
<main id="main">
%(body)s
</main>
%(colophon)s
<script src="assets/js/site.js" defer></script>
</body>
</html>
""" % {
        "title": title, "desc": desc, "og": og,
        "arm": OVERTURE_ARM if intro else "",
        "overture": OVERTURE if intro else "",
        "masthead": masthead(current), "body": body, "colophon": colophon(),
    }


# ---------------------------------------------------------------- plates

RHYTHM = ["full", "small", "mid", "wide", "right", "mid", "left", "full", "small", "wide"]


PORTRAIT_RHYTHM = ["small", "mid", "small", "left", "small", "right"]


def esc(text):
    """Safe inside both an attribute and a text node."""
    return html.escape(text, quote=True)


def plate(fname, index, series, ratios=None, caps=None, numeral=None, home=None):
    """One plate.

    `index` sets the layout rhythm and, normally, the plate number. A study
    passes `numeral` and `home` instead, so a photograph borrowed onto
    another page still shows the number and series it was published under
    and links back to it. A plate has exactly one identity wherever it
    appears.
    """
    ar_frame = ""
    ar_fig = ""
    cls = RHYTHM[index % len(RHYTHM)]

    dims = (ratios or {}).get(fname[:6])
    if dims:
        w, h = dims
        ar_frame = ' style="aspect-ratio: %d / %d"' % (w, h)
        ar_fig = ' style="--ar: %.4f"' % (w / float(h))
        if h > w:  # tall plates get the narrow rhythm, never a full-bleed slot
            cls = PORTRAIT_RHYTHM[index % len(PORTRAIT_RHYTHM)]

    numeral = numeral or roman(index + 1)
    title, brief = (caps or {}).get(fname[:6], ("", ""))

    # The caption doubles as the alt text — it is the best description of the
    # picture there is. Plates without a caption fall back to the old wording.
    if title:
        alt = "%s — %s" % (title, brief)
        heading = '<h2 class="plate__title">%s</h2>' % esc(title)
        note = '<p class="plate__brief">%s</p>' % esc(brief)
        expand_label = "Expand plate %s, %s" % (numeral, title)
    else:
        alt = "%s photograph, plate %s" % (series, numeral)
        heading = ""
        note = ""
        expand_label = "Expand plate %s" % numeral

    # Anchored on the id prefix rather than the number, so a link into a
    # plate survives the series being reordered.
    mark = ('<a class="plate__series" href="%s">%s &rarr;</a>' % (home, series)
            if home else '<span class="plate__series">%s</span>' % series)

    return """  <figure class="plate plate--%(cls)s reveal" id="plate-%(anchor)s"%(ar_fig)s
    data-title="%(title)s" data-brief="%(brief)s" data-plate="%(numeral)s"
    data-series="%(series)s" data-full="%(full)s">
    <div class="plate__frame"%(ar_frame)s>
      <img src="%(src)s"%(srcset)s alt="%(alt)s" loading="lazy" decoding="async">
      <a class="plate__expand" href="%(full)s" data-expand aria-label="%(label)s">
        <span class="plate__expand-glyph" aria-hidden="true"></span>
        <span>Expand</span>
      </a>
    </div>
    <figcaption class="plate__caption">
      <span class="plate__rule" aria-hidden="true"></span>
      <p class="plate__index">Plate %(numeral)s</p>
      %(heading)s
      %(note)s
      %(mark)s
    </figcaption>
  </figure>""" % {
        "cls": cls, "ar_fig": ar_fig, "ar_frame": ar_frame,
        "src": src(fname), "srcset": srcset(fname), "full": src(fname, 2400),
        "alt": esc(alt), "label": esc(expand_label), "numeral": numeral,
        "series": series, "title": esc(title), "brief": esc(brief),
        "heading": heading, "note": note, "mark": mark,
        "anchor": fname[:6],
    }


# A grouped index is only worth the space when the series genuinely holds
# several kinds of animal. One group of twenty-two birds beside three
# groups of one is not a classification, it is a list with headings on it —
# so a series like that gets the same strip, ungrouped.
GROUP_MIN = 3
GROUPS_NEEDED = 2


def grouped(files):
    """The plates of a series arranged by animal group, or None for a flat
    index. Returns [(label, [(fname, plate number), ...]), ...] in the fixed
    order set by photos.GROUPS, so two series never disagree about it."""
    buckets = {}
    for i, f in enumerate(files):
        buckets.setdefault(photos.SPECIES.get(f[:6], "other"), []).append((f, i + 1))

    shown = []
    for keys, label in photos.GROUPS:
        if isinstance(keys, str):
            keys = (keys,)
        items = sorted((pair for k in keys for pair in buckets.get(k, [])),
                       key=lambda pair: pair[1])
        if items:
            shown.append((label, items))

    # The threshold is measured on the groups as they would appear, not on
    # the raw keys behind them — what matters is what the visitor sees.
    if len([1 for _label, items in shown if len(items) >= GROUP_MIN]) < GROUPS_NEEDED:
        return None
    return shown


def index_thumb(fname, number, ratios, caps):
    dims = (ratios or {}).get(fname[:6], (3, 2))
    title = (caps or {}).get(fname[:6], ("", ""))[0]
    numeral = roman(number)
    label = "Plate %s%s" % (numeral, " — " + title if title else "")
    return ('<a class="pindex__item" href="#plate-%s" title="%s" '
            'style="--ar: %.4f">'
            '<img src="%s" alt="" loading="lazy" decoding="async">'
            '<span class="pindex__num">%s</span>'
            '<span class="visually-hidden">%s</span></a>'
            % (fname[:6], esc(label), dims[0] / float(dims[1]),
               thumb(fname), numeral, esc(label)))


def plate_index(files, ratios, caps):
    """The contact sheet above the plates.

    It is navigation and nothing else: every plate keeps its number and its
    place in the single run below, and the grouping exists only here, where
    it helps somebody find a picture rather than telling them what the
    series is about.
    """
    groups = grouped(files)

    if groups is None:
        strip = "".join(index_thumb(f, i + 1, ratios, caps)
                        for i, f in enumerate(files))
        blocks = '<div class="pindex__strip">%s</div>' % strip
    else:
        blocks = "\n".join(
            '<div class="pindex__group">'
            '<p class="pindex__label label">%s <span>%d</span></p>'
            '<div class="pindex__strip">%s</div></div>'
            % (esc(label), len(items),
               "".join(index_thumb(f, n, ratios, caps) for f, n in items))
            for label, items in groups)

    return """<nav class="pindex shell reveal" aria-label="Plate index">
%s
</nav>""" % blocks


def gallery_page(slug, title, note, files, ratios=None, nxt=None, caps=None):
    plates = "\n".join(plate(f, i, title, ratios, caps) for i, f in enumerate(files))
    onward = ""
    if nxt:
        label = "Next series" if nxt[0].endswith(tuple(
            s[0] for s in SERIES)) else "Beyond the series"
        onward = """<div class="onward shell">
  <span class="label">%s</span>
  <a href="%s">%s &rarr;</a>
</div>""" % (label, nxt[0], nxt[1])

    body = """<section class="pagehead shell">
  <p class="label">Series</p>
  <h1 class="pagehead__title">%s</h1>
  <p class="pagehead__note">%s</p>
  <div class="pagehead__rule"><span class="label">%d plates</span><hr class="hairline"></div>
</section>

%s

<section class="plates shell">
%s
</section>

%s""" % (title, note, len(files), plate_index(files, ratios, caps),
         plates, onward)

    write(slug, page(
        "%s — Maximilien Bozon" % title,
        note, body, slug, files[0] if files else None))


def write(name, html):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(html)


# ---------------------------------------------------------------- content

SERIES = [
    ("shadow.html", "Shadow", photos.SHADOW,
     "Animals held in near-darkness, where a single light decides how much of a body we are allowed to see.",
     photos.SHADOW_AR, captions.SHADOW),
    ("light.html", "Light", photos.LIGHT,
     "The same subjects turned toward the source: form described by illumination rather than concealed by it.",
     photos.LIGHT_AR, captions.LIGHT),
    ("monochrome.html", "Monochrome", photos.MONOCHROME,
     "Colour removed, leaving line, texture and anatomy to carry the picture on their own.",
     None, captions.MONOCHROME),
]


# The three series above are one axis: how the light is handled. Every
# photograph sits at exactly one point on it, which is what keeps the
# navigation legible.
#
# Projects are the second tier, and deliberately a different kind of thing.
# A project can be an edition, a study, a commission — anything with its own
# reason to exist. To add one, append an entry here and nothing else: the
# index page, the home page band and the sitemap all read from this list.
#
#   slug   the page it builds
#   title  what it is called
#   kind   the small label above the title (Study, Limited edition, ...)
#   note   one sentence, used on the index and in the page description
#   cover  the photograph that stands for it
#   plates a list of photographs to build a study page from, drawn from the
#          series — or None, when the project brings its own page builder
#   build  a function writing the page itself, for projects that are not
#          simply a set of plates
#
PROJECTS = [
    ("notice-it.html", "Notice it", "Limited edition",
     "A hand-numbered edition of 100 pages of arthropod photography, made for "
     "anyone curious enough to look at the creatures most people look away from.",
     photos.BOOK[0], None, "build_book"),
    ("dragonflies.html", "Dragonflies", "Study",
     "Odonata: two pairs of wings held open in the dark, and the oldest flying "
     "design still in the air.",
     photos.ODONATA[0], photos.ODONATA, None),
]


def home_of(fname):
    """Which series publishes this photograph, and as which plate.

    Returns (slug, series title, numeral, ratios, captions) so a study can
    borrow a plate without inventing a second number for it.
    """
    for slug, title, files, _note, ratios, caps in SERIES:
        for i, f in enumerate(files):
            if f[:6] == fname[:6]:
                return slug, title, roman(i + 1), ratios, caps
    return None


def study_page(slug, title, kind, note, files):
    """A project built from plates that already live in a series."""
    plates = []
    own = 0
    for i, fname in enumerate(files):
        found = home_of(fname)
        if found:
            home_slug, series, numeral, ratios, caps = found
            home = "%s#plate-%s" % (home_slug, fname[:6])
        else:
            # Published here and nowhere else. The study is this plate's only
            # home, so it numbers the picture itself instead of borrowing a
            # number — still exactly one identity, just not a series one.
            own += 1
            series, numeral, home = title, roman(own), None
            ratios, caps = photos.STUDY_AR, captions.STUDY
        plates.append(plate(fname, i, series, ratios, caps,
                            numeral=numeral, home=home))

    # Only claim the plates came from the series when all of them did.
    count = ("%d plates, drawn from the series" % len(plates) if not own
             else "%d plates" % len(plates))

    body = """<section class="pagehead shell">
  <p class="label">%s</p>
  <h1 class="pagehead__title">%s</h1>
  <p class="pagehead__note">%s</p>
  <div class="pagehead__rule">
    <span class="label">%s</span><hr class="hairline">
  </div>
</section>

<section class="plates shell">
%s
</section>

<div class="onward shell">
  <span class="label">More work</span>
  <a href="projects.html">All projects &rarr;</a>
</div>""" % (kind, title, note, count, "\n".join(plates))

    write(slug, page("%s — Maximilien Bozon" % title, note, body,
                     "projects.html", files[0] if files else None))


def project_cards():
    """The project list, used on both the home page and the index."""
    items = []
    for i, (slug, title, kind, note, cover, _plates, _fn) in enumerate(PROJECTS):
        items.append("""  <a class="series__item reveal" href="%s">
    <span class="series__numeral">%s</span>
    <div>
      <p class="label">%s</p>
      <h3 class="series__title">%s</h3>
      <p class="series__note">%s</p>
    </div>
    <figure class="series__figure">
      <img src="%s" alt="From %s" loading="lazy" decoding="async">
    </figure>
  </a>""" % (slug, roman(i + 1), kind, title, note, src(cover, 1200), title))
    return "\n".join(items)


def build_projects():
    body = """<section class="pagehead shell">
  <p class="label">Beyond the series</p>
  <h1 class="pagehead__title">Projects</h1>
  <p class="pagehead__note">Editions, studies and bodies of work that follow a
  subject rather than a quality of light.</p>
  <div class="pagehead__rule">
    <span class="label">%d projects</span><hr class="hairline">
  </div>
</section>

<section class="band shell" style="padding-top:0">
  <div class="series series--projects">
%s
  </div>
</section>

<div class="onward shell">
  <span class="label">Prints, commissions, enquiries</span>
  <a href="contact.html">Get in touch &rarr;</a>
</div>""" % (len(PROJECTS), project_cards())

    write("projects.html", page(
        "Projects — Maximilien Bozon",
        "Editions, studies and bodies of work by Maximilien Bozon, following a "
        "subject rather than a quality of light.",
        body, "projects.html", PROJECTS[0][4] if PROJECTS else None))


def build_home():
    hero = "12ad2e67eee04925be2658b93826a003~mv2.jpg"
    covers = {
        "Shadow": "daee257aaeb34d86b1129567e57f718b~mv2.jpg",
        "Light": "c1858d4ef6b741ba9b716e1027a61439~mv2.jpg",
        "Monochrome": "99cfbdae96ab4805b8a1b6f457069e85~mv2.jpg",
    }

    items = []
    for i, (slug, title, files, note, _, _caps) in enumerate(SERIES):
        items.append("""  <a class="series__item reveal" href="%s">
    <span class="series__numeral">%s</span>
    <div>
      <h3 class="series__title">%s</h3>
      <p class="series__note">%s</p>
      <span class="series__count">%d plates</span>
    </div>
    <figure class="series__figure">
      <img src="%s" alt="From the %s series" loading="lazy" decoding="async">
    </figure>
  </a>""" % (slug, roman(i + 1), title, note, len(files), src(covers[title], 1200), title))

    body = """<section class="hero">
  <div class="hero__bg">
    <img src="%(hero)s" alt="" aria-hidden="true" fetchpriority="high">
  </div>
  <div class="hero__inner">
    <h1 class="hero__name"><span>Maximilien</span><span>Bozon</span></h1>
    <div class="hero__meta">
      <p class="label">Wildlife photography &middot; Paris &amp; London</p>
      <p class="hero__line">Animals emerging from darkness, where light reveals form, structure and fragility.</p>
    </div>
  </div>
  <p class="hero__cue">Scroll</p>
</section>

<section class="band shell">
  <div class="statement reveal">
    <p class="label">Statement</p>
    <div class="statement__body">
      <p class="statement__lede">Maximilien Bozon is a photographer and veterinarian based between Paris and London.</p>
      <p>Influenced by his scientific background, he approaches animal bodies both as living beings and as anatomical forms.</p>
      <p>Through minimal compositions and controlled light, his images oscillate between observation and abstraction. By isolating his subjects in shadow, he invites the viewer to reconsider the way we perceive animals &mdash; not only as species, but as physical presences.</p>
    </div>
  </div>
</section>

<section class="band shell" style="padding-top:0">
  <div class="pagehead__rule pagehead__rule--section reveal" style="margin-bottom:1rem">
    <span class="label">The work</span><hr class="hairline">
  </div>
  <div class="series">
%(items)s
  </div>
</section>

<section class="band shell" id="projects">
  <div class="pagehead__rule pagehead__rule--section reveal" style="margin-bottom:1rem">
    <span class="label">The projects</span><hr class="hairline">
  </div>
  <div class="series series--projects">
%(projects)s
  </div>
</section>

<div class="onward shell">
  <span class="label">Prints, commissions, enquiries</span>
  <a href="contact.html">Get in touch &rarr;</a>
</div>""" % {"hero": src(hero, 2400), "items": "\n".join(items),
             "projects": project_cards()}

    write("index.html", page(
        "Maximilien Bozon — Wildlife photography",
        "Wildlife photography by Maximilien Bozon, photographer and veterinarian based between Paris and London. Animals emerging from darkness.",
        body, "index.html", hero, intro=True))


def build_book():
    grid = "\n".join(
        '    <img src="%s" alt="A page from Notice it" loading="lazy" decoding="async">'
        % src(f, 1200) for f in photos.BOOK[1:])

    inclusions = [
        "100 pages of arthropod photography",
        "The matching &lsquo;Notice it&rsquo; clamshell box",
        "Fine art paper throughout",
        "A turning-page glove",
        "A magnifying glass, for the most subtle details",
        "A certificate of authenticity",
        "A hand-made signature with the number of the book",
        "Delivery worldwide",
    ]
    spec = "\n".join(
        "    <li><span>%02d</span>%s</li>" % (i + 1, t)
        for i, t in enumerate(inclusions))

    body = """<section class="pagehead shell">
  <p class="label">Limited edition</p>
  <div class="litany reveal">
    <p>Notice a world many see but very few perceive.</p>
    <p>Notice those dancing shapes and colours.</p>
    <p>Notice the grace that goes unnoticed.</p>
    <p>Notice this unexpected beauty.</p>
    <p>Notice what&rsquo;s hidden.</p>
    <p>Notice it.</p>
  </div>
</section>

<section class="shell">
  <figure class="plate plate--full reveal" style="margin:0 0 clamp(3rem,8vh,6rem)">
    <div class="plate__frame">
      <img src="%(cover)s" alt="The book Notice it" loading="lazy" decoding="async">
    </div>
  </figure>
</section>

<section class="band shell" style="padding-top:0">
  <div class="split reveal">
    <div>
      <h2 class="statement__lede">A new perspective on beauty</h2>
      <p>This book is for those with the curiosity to uncover a hidden world of beauty that most people miss.</p>
      <p>Arthropods often make people uncomfortable, but if you take the time to really look, there is so much to appreciate: colours, shapes and details that are impossible to notice with the naked eye.</p>
      <p>My goal is simple &mdash; to help you discover a side of these creatures you have never seen before. It is an invitation to step into a world that is unfamiliar, but full of wonder and subtle beauty.</p>
    </div>
    <div>
      <p class="label">What arrives</p>
      <ul class="spec">
%(spec)s
      </ul>
    </div>
  </div>

  <div class="bookgrid reveal">
%(grid)s
  </div>
</section>

<div class="onward shell">
  <span class="label">Editions are numbered and signed by hand</span>
  <a href="contact.html">Reach out to get one &rarr;</a>
</div>""" % {"cover": src(photos.BOOK[0], 2400), "spec": spec, "grid": grid}

    write("notice-it.html", page(
        "Notice it — a limited edition by Maximilien Bozon",
        "A hand-numbered limited edition of 100 pages of arthropod photography, with clamshell box, fine art paper and certificate of authenticity.",
        body, "projects.html", photos.BOOK[0]))


def build_about():
    body = """<section class="pagehead shell">
  <p class="label">About</p>
  <h1 class="pagehead__title">Maximilien<br>Bozon</h1>
</section>

<section class="band shell" style="padding-top:clamp(2rem,5vh,3rem)">
  <div class="about reveal">
    <figure class="about__portrait" style="margin:0">
      <img src="%(portrait)s" alt="Maximilien Bozon" loading="lazy" decoding="async">
    </figure>
    <div class="statement__body">
      <p class="statement__lede">A photographer and veterinarian based between Paris and London.</p>
      <p>His work explores the presence of animals emerging from darkness, where light reveals form, structure and fragility.</p>
      <p>Influenced by his scientific background, he approaches animal bodies both as living beings and as anatomical forms.</p>
      <p>Through minimal compositions and controlled light, his images oscillate between observation and abstraction.</p>
      <p>By isolating his subjects in shadow, he invites the viewer to reconsider the way we perceive animals &mdash; not only as species, but as physical presences.</p>
      <p style="margin-top:2rem"><a class="btn" href="contact.html">Get in touch</a></p>
    </div>
  </div>
</section>

<div class="onward shell">
  <span class="label">Start with</span>
  <a href="shadow.html">Shadow &rarr;</a>
</div>""" % {"portrait": src(photos.PORTRAIT, 1200)}

    write("about.html", page(
        "About — Maximilien Bozon",
        "Maximilien Bozon is a photographer and veterinarian based between Paris and London, working with animals emerging from darkness.",
        body, "about.html", photos.PORTRAIT))


def build_contact():
    body = """<section class="pagehead shell">
  <p class="label">Contact</p>
  <h1 class="pagehead__title">Get in<br><em>touch</em></h1>
  <p class="pagehead__note">Prints, the Notice it edition, exhibitions and commissions. Write directly, or leave a message below.</p>
</section>

<section class="band shell" style="padding-top:clamp(1rem,3vh,2rem)">
  <div class="split reveal">
    <div>
      <p class="label">By email</p>
      <p><a class="contact__mail" href="mailto:%(email)s">%(email)s</a></p>
      <p style="color:var(--ash);margin-top:2rem">Based between Paris and London. Replies usually within a few days.</p>
    </div>
    <div>
      <p class="label">Or leave a message</p>
      <!-- With action="" left empty this form opens the visitor's mail app,
           prefilled. To collect submissions instead, make a free endpoint at
           formspree.io (or formsubmit.co) and paste it into action="". -->
      <form action="" method="POST" data-mailto="%(email)s" style="margin-top:1.5rem">
        <div class="field">
          <label for="name">Name</label>
          <input id="name" name="name" type="text" autocomplete="name" required>
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" name="email" type="email" autocomplete="email" required>
        </div>
        <div class="field">
          <label for="message">Message</label>
          <textarea id="message" name="message" rows="5" required></textarea>
        </div>
        <button class="btn" type="submit">Send message</button>
      </form>
    </div>
  </div>
</section>""" % {"email": EMAIL}

    write("contact.html", page(
        "Contact — Maximilien Bozon",
        "Contact Maximilien Bozon about prints, the Notice it edition, exhibitions and commissions.",
        body, "contact.html"))


def build_404():
    body = """<section class="pagehead shell" style="min-height:60svh">
  <p class="label">404</p>
  <h1 class="pagehead__title">Nothing<br><em>here</em></h1>
  <p class="pagehead__note">That page has gone dark. The work is still where you left it.</p>
  <p><a class="btn" href="index.html">Back to the beginning</a></p>
</section>"""
    write("404.html", page("Not found — Maximilien Bozon",
                           "This page could not be found.", body, "404.html"))


def build_extras():
    pages = (["", "shadow.html", "light.html", "monochrome.html",
              "projects.html"]
             + [p[0] for p in PROJECTS]
             + ["about.html", "contact.html"])
    urls = "\n".join(
        "  <url><loc>%s/%s</loc></url>" % (SITE_URL, p) for p in pages)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          "%s\n</urlset>\n" % urls)
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE_URL)

    # GitHub Pages reads the custom domain from this file. It lives in the
    # published folder, so writing it here means a rebuild can never drop
    # the domain and knock the site offline.
    write("CNAME", SITE_URL.split("//", 1)[1].rstrip("/") + "\n")

    # Tells GitHub Pages to publish these files exactly as they are instead
    # of running them through Jekyll. This site is written by hand, so Jekyll
    # has nothing to do here except invent surprises.
    write(".nojekyll", "")


def prepare_images():
    """Make the web copies in docs/images from the masters in ./images.

    Two things happen to every photograph: it is scaled so its longest side
    is MAX_EDGE, and a copyright field is written into its metadata.

    This does not stop anyone saving a picture — a browser cannot draw an
    image it has not been given, so the bytes are always on the visitor's
    machine. What it does is decide how good a copy that is. A screen-sized
    file is worth far less than a print-sized one, and it costs the page
    nothing, because the layout never displays more than this anyway.
    """
    dest = os.path.join(OUT, "images")
    os.makedirs(dest, exist_ok=True)

    if not os.path.isdir(MASTERS):
        print("  images: no ./images folder — leaving docs/images as it is")
        return

    if shutil.which("sips") is None:
        # sips ships with macOS. Elsewhere, publish the masters untouched
        # rather than silently serving nothing.
        print("  images: sips not found — copying masters at full size")
        for fname in _photographs(MASTERS):
            shutil.copy2(os.path.join(MASTERS, fname), os.path.join(dest, fname))
        return

    # A rebuild is forced when MAX_EDGE changes, otherwise the existing
    # copies would look current while being the wrong size.
    stamp = os.path.join(dest, ".max-edge")
    previous = None
    if os.path.exists(stamp):
        with open(stamp, encoding="utf-8") as fh:
            previous = fh.read().strip()
    forced = previous != str(MAX_EDGE)

    made = current = failed = 0
    for fname in _photographs(MASTERS):
        master = os.path.join(MASTERS, fname)
        target = os.path.join(dest, fname)

        if (not forced and os.path.exists(target)
                and os.path.getmtime(target) >= os.path.getmtime(master)):
            current += 1
            continue

        try:
            _run(["sips", "-Z", str(MAX_EDGE), master, "--out", target])
            _run(["sips", "-s", "copyright", COPYRIGHT, target])
            made += 1
        except subprocess.CalledProcessError:
            print("  images: FAILED %s" % fname)
            failed += 1

    with open(stamp, "w", encoding="utf-8") as fh:
        fh.write(str(MAX_EDGE) + "\n")

    print("  images: %d rebuilt, %d already current, capped at %dpx%s"
          % (made, current, MAX_EDGE, ", %d FAILED" % failed if failed else ""))

    _prepare_thumbs(dest)


def _prepare_thumbs(dest):
    """The small copies behind the plate index, in docs/images/thumbs."""
    out = os.path.join(dest, "thumbs")
    os.makedirs(out, exist_ok=True)

    stamp = os.path.join(out, ".thumb-edge")
    previous = None
    if os.path.exists(stamp):
        with open(stamp, encoding="utf-8") as fh:
            previous = fh.read().strip()
    forced = previous != str(THUMB_EDGE)

    made = current = 0
    for fname in _photographs(dest):
        source = os.path.join(dest, fname)
        target = os.path.join(out, fname)
        if (not forced and os.path.exists(target)
                and os.path.getmtime(target) >= os.path.getmtime(source)):
            current += 1
            continue
        _run(["sips", "-Z", str(THUMB_EDGE), source, "--out", target])
        _run(["sips", "-s", "copyright", COPYRIGHT, target])
        made += 1

    with open(stamp, "w", encoding="utf-8") as fh:
        fh.write(str(THUMB_EDGE) + "\n")

    print("  thumbs: %d rebuilt, %d already current, %dpx"
          % (made, current, THUMB_EDGE))


def _photographs(folder):
    return sorted(f for f in os.listdir(folder)
                  if not f.startswith(".")
                  and f.lower().endswith((".jpg", ".jpeg")))


def _run(cmd):
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    os.makedirs(OUT, exist_ok=True)
    prepare_images()
    build_home()
    for i, (slug, title, files, note, ratios, caps) in enumerate(SERIES):
        nxt = None
        if i + 1 < len(SERIES):
            nxt = (SERIES[i + 1][0], SERIES[i + 1][1])
        else:
            nxt = ("projects.html", "Projects")
        gallery_page(slug, title, note, files, ratios, nxt, caps)

    build_projects()
    for slug, title, kind, note, _cover, plates, fn in PROJECTS:
        if plates:
            study_page(slug, title, kind, note, plates)
        else:
            globals()[fn]()
    build_about()
    build_contact()
    build_404()
    build_extras()
    print("Built %d pages into %s (image source: %s)"
          % (len(os.listdir(OUT)), OUT, SOURCE))


if __name__ == "__main__":
    main()
